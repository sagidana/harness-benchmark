from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import websockets
from websockets import ServerConnection

from aidle.challenges import REGISTRY
from aidle.challenges.base import ActionResult, BaseChallenge
from aidle.session import Session, State

logger = logging.getLogger(__name__)

PROTOCOL_VERSION = "1.0"


def _envelope(msg_id: str | None, msg_type: str, payload: dict[str, Any]) -> str:
    return json.dumps({"wcgp": PROTOCOL_VERSION, "id": msg_id, "type": msg_type, "payload": payload})


def _push_envelope(msg_type: str, payload: dict[str, Any]) -> str:
    return _envelope(None, msg_type, payload)


def _error(msg_id: str | None, base_type: str, code: str, message: str, detail: dict | None = None, cost: dict | None = None) -> str:
    payload: dict[str, Any] = {
        "error": {"code": code, "message": message, "detail": detail or {}}
    }
    if cost is not None:
        payload["cost"] = cost
    return _envelope(msg_id, f"{base_type}.error", payload)


class ProtocolHandler:
    """Handles the WCGP protocol for a single WebSocket connection."""

    def __init__(self, websocket: ServerConnection) -> None:
        self._ws = websocket
        self._session = Session()

    async def run(self) -> None:
        addr = self._ws.remote_address
        logger.info("Client connected: %s", addr)
        try:
            await asyncio.gather(
                self._receive_loop(),
                self._push_loop(),
            )
        except websockets.ConnectionClosed:
            pass
        finally:
            self._session.leave() if self._session.state == State.IN_CHALLENGE else None
            logger.info("Client disconnected: %s", addr)

    # ------------------------------------------------------------------
    # Receive loop
    # ------------------------------------------------------------------

    async def _receive_loop(self) -> None:
        async for raw in self._ws:
            response = await self._dispatch(raw)
            if response:
                await self._ws.send(response)

    async def _dispatch(self, raw: str) -> str | None:
        # Parse envelope
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return _error(None, "error", "MALFORMED_MESSAGE", "Message is not valid JSON.", {})

        msg_id = msg.get("id")
        msg_type = msg.get("type")
        payload = msg.get("payload", {})

        if not isinstance(msg_type, str) or not msg_type:
            return _error(msg_id, "error", "MALFORMED_MESSAGE", "Required field 'type' is missing or invalid.")

        if msg.get("wcgp") != PROTOCOL_VERSION:
            received = msg.get("wcgp")
            return _error(msg_id, "error", "UNSUPPORTED_VERSION",
                          f"This server supports wcgp {PROTOCOL_VERSION} only.",
                          {"supported": [PROTOCOL_VERSION], "received": received})

        # Route by scope
        parts = msg_type.split(".", 1)
        scope = parts[0]

        if scope == "session":
            verb = parts[1] if len(parts) > 1 else ""
            return await self._handle_session(msg_id, msg_type, verb, payload)

        # Challenge-scoped
        if scope in REGISTRY:
            verb = parts[1] if len(parts) > 1 else ""
            return await self._handle_challenge_action(msg_id, msg_type, scope, verb, payload)

        return _error(msg_id, msg_type, "UNKNOWN_TYPE",
                      f"Unknown message type: {msg_type!r}.")

    # ------------------------------------------------------------------
    # Session handlers
    # ------------------------------------------------------------------

    async def _handle_session(self, msg_id: str | None, msg_type: str, verb: str, payload: dict) -> str:
        if verb == "list":
            return self._session_list(msg_id)
        if verb == "introspect":
            return self._session_introspect(msg_id, payload)
        if verb == "join":
            return await self._session_join(msg_id, payload)
        if verb == "actions":
            return self._session_actions(msg_id, msg_type)
        if verb == "cost":
            return self._session_cost(msg_id, msg_type)
        if verb == "objective":
            return self._session_objective(msg_id, msg_type)
        if verb == "leave":
            return self._session_leave(msg_id, msg_type)
        if verb == "end":
            return self._session_end(msg_id, msg_type)
        return _error(msg_id, msg_type, "UNKNOWN_TYPE", f"Unknown session verb: {verb!r}.")

    def _session_list(self, msg_id: str | None) -> str:
        challenges = [
            {
                "slug": cls.slug,
                "name": cls.name,
                "description": cls.description,
                "version": cls.version,
                "tags": cls.tags,
                "difficulty": cls.difficulty,
            }
            for cls in REGISTRY.values()
        ]
        return _envelope(msg_id, "session.list.ok", {"challenges": challenges})

    def _session_introspect(self, msg_id: str | None, payload: dict) -> str:
        slug = payload.get("challenge_slug")
        if slug not in REGISTRY:
            return _error(msg_id, "session.introspect", "UNKNOWN_CHALLENGE",
                          f"No challenge with slug {slug!r}.",
                          {"available_slugs": list(REGISTRY)})
        return _envelope(msg_id, "session.introspect.ok", REGISTRY[slug].introspect())

    async def _session_join(self, msg_id: str | None, payload: dict) -> str:
        if self._session.state == State.IN_CHALLENGE:
            return _error(msg_id, "session.join", "ALREADY_IN_CHALLENGE",
                          "You are already in a challenge. Leave or end it first.")

        slug = payload.get("challenge_slug")
        if slug not in REGISTRY:
            return _error(msg_id, "session.join", "UNKNOWN_CHALLENGE",
                          f"No challenge with slug {slug!r}.",
                          {"available_slugs": list(REGISTRY)})

        options = payload.get("options", {}) or {}
        challenge: BaseChallenge = REGISTRY[slug](options)
        self._session.join(challenge)

        # Start background task
        self._session._bg_task = asyncio.create_task(challenge.run_background())

        return _envelope(msg_id, "session.join.ok", {
            "challenge_slug": slug,
            "session_id": self._session.session_id,
            "initial_state": challenge.initial_state(),
            "cost": self._session.cost_block(),
        })

    def _require_in_challenge(self, msg_id: str | None, msg_type: str) -> str | None:
        if self._session.state != State.IN_CHALLENGE:
            return _error(msg_id, msg_type, "NOT_IN_CHALLENGE",
                          "You must join a challenge first.",
                          {"current_state": self._session.state.name, "required_state": "IN_CHALLENGE"})
        return None

    def _session_actions(self, msg_id: str | None, msg_type: str) -> str:
        if err := self._require_in_challenge(msg_id, msg_type):
            return err
        assert self._session.challenge
        return _envelope(msg_id, "session.actions.ok",
                         {"actions": self._session.challenge.available_actions()})

    def _session_cost(self, msg_id: str | None, msg_type: str) -> str:
        if err := self._require_in_challenge(msg_id, msg_type):
            return err
        return _envelope(msg_id, "session.cost.ok", {
            "cost": {
                "cumulative": round(self._session.cumulative(), 4),
                "breakdown": self._session.cost_breakdown(),
            }
        })

    def _session_objective(self, msg_id: str | None, msg_type: str) -> str:
        if err := self._require_in_challenge(msg_id, msg_type):
            return err
        assert self._session.challenge
        base_cost = 1.0
        self._session.record_action(base_cost)
        result = self._session.challenge.objective()
        result["cost"] = self._session.cost_block(action_cost=base_cost)
        return _envelope(msg_id, "session.objective.ok", result)

    def _session_leave(self, msg_id: str | None, msg_type: str) -> str:
        if err := self._require_in_challenge(msg_id, msg_type):
            return err
        session_id = self._session.session_id
        self._session.leave()
        return _envelope(msg_id, "session.leave.ok", {
            "session_id": session_id,
            "completed": False,
            "final_cost": {
                "cumulative": round(self._session.cumulative(), 4),
                "breakdown": self._session.cost_breakdown(),
            },
        })

    def _session_end(self, msg_id: str | None, msg_type: str) -> str:
        if err := self._require_in_challenge(msg_id, msg_type):
            return err
        assert self._session.challenge
        challenge = self._session.challenge
        slug = challenge.slug
        completed = challenge.reached_goal if hasattr(challenge, "reached_goal") else False
        session_id = self._session.session_id
        self._session.end()
        summary = challenge.end_summary()
        summary["elapsed_seconds"] = self._session.elapsed_seconds()
        return _envelope(msg_id, "session.end.ok", {
            "session_id": session_id,
            "challenge_slug": slug,
            "completed": completed,
            "score": {
                "total": round(self._session.cumulative(), 4),
                "breakdown": self._session.cost_breakdown(),
            },
            "summary": summary,
        })

    # ------------------------------------------------------------------
    # Challenge action handler
    # ------------------------------------------------------------------

    async def _handle_challenge_action(
        self, msg_id: str | None, msg_type: str, slug: str, verb: str, payload: dict
    ) -> str:
        if err := self._require_in_challenge(msg_id, msg_type):
            return err

        assert self._session.challenge
        if self._session.challenge.slug != slug:
            return _error(msg_id, msg_type, "WRONG_STATE",
                          f"You are in challenge {self._session.challenge.slug!r}, not {slug!r}.")

        self._session.record_message()

        try:
            result: ActionResult = await self._session.challenge.handle(verb, payload)
        except KeyError:
            return _error(msg_id, msg_type, "UNKNOWN_TYPE",
                          f"Challenge {slug!r} does not expose action {verb!r}. "
                          "See session.introspect for available actions.",
                          {"challenge_slug": slug, "requested_action": verb})

        cfg = self._session.challenge.cost_config()
        penalty = result.base_cost * cfg.invalid_action_multiplier if result.invalid else 0.0
        total_action_cost = result.base_cost + penalty

        self._session.record_action(result.base_cost, penalty)

        cost_block = self._session.cost_block(
            action_cost=result.base_cost,
            penalty=penalty,
            penalty_reason=result.invalid_reason,
        )

        if result.invalid:
            result.payload["cost"] = cost_block
            return _envelope(msg_id, f"{msg_type}.error", result.payload)

        result.payload["cost"] = cost_block
        return _envelope(msg_id, f"{msg_type}.ok", result.payload)

    # ------------------------------------------------------------------
    # Push event loop
    # ------------------------------------------------------------------

    async def _push_loop(self) -> None:
        while True:
            await asyncio.sleep(0.05)
            challenge = self._session.challenge
            if challenge is None or self._session.state != State.IN_CHALLENGE:
                continue
            # Drain all queued push events
            while not challenge._push_queue.empty():
                event = challenge._push_queue.get_nowait()
                await self._ws.send(_push_envelope(event["type"], event["payload"]))
