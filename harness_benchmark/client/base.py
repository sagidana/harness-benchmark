from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import uuid
from typing import Any

import websockets

logger = logging.getLogger(__name__)

PROTOCOL_VERSION = "1.0"


class WCGPClient:
    """
    Base client implementing the WCGP v1.0 generic protocol.

    Subclasses override `play()` to implement challenge-specific logic.
    Push events are delivered via `on_event()`, which subclasses can override.
    """

    def __init__(self, uri: str, username: str | None = None) -> None:
        self._uri = uri
        self._username = username
        self._ws: websockets.ClientConnection | None = None
        self._pending: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._running = False
        self.auth_info: dict[str, Any] = {}  # populated after authenticate()

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Open the WebSocket connection. Does NOT authenticate — call run() for that."""
        self._ws = await websockets.connect(self._uri)
        self._running = True
        logger.info("Connected to %s", self._uri)

    async def authenticate(self, username: str) -> dict[str, Any]:
        """Send auth.login and return the server response payload."""
        resp = await self.request("auth.login", {"username": username})
        payload = resp["payload"]
        self.auth_info = payload
        logger.info(
            "Authenticated as %r — resumed=%s session_state=%s",
            payload.get("username"),
            payload.get("resumed"),
            payload.get("session_state"),
        )
        return payload

    async def disconnect(self) -> None:
        self._running = False
        if self._ws:
            await self._ws.close()
            logger.info("Disconnected from %s", self._uri)

    async def run(self) -> None:
        """Connect, authenticate, run play(), then clean up."""
        await self.connect()
        recv_task = asyncio.create_task(self._receive_loop())
        try:
            if self._username:
                await self.authenticate(self._username)
            await self.play()
        finally:
            self._running = False
            recv_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await recv_task
            await self.disconnect()

    async def _receive_loop(self) -> None:
        assert self._ws
        try:
            async for raw in self._ws:
                msg = json.loads(raw)
                msg_id = msg.get("id")
                if msg_id and msg_id in self._pending:
                    self._pending[msg_id].set_result(msg)
                else:
                    # Push event or unsolicited message
                    await self.on_event(msg)
        except websockets.ConnectionClosed:
            pass
        finally:
            # Unblock any waiting callers
            for fut in self._pending.values():
                if not fut.done():
                    fut.cancel()

    # ------------------------------------------------------------------
    # Low-level send/receive
    # ------------------------------------------------------------------

    async def request(self, msg_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send a request and await the correlated response."""
        assert self._ws
        msg_id = str(uuid.uuid4())
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[dict[str, Any]] = loop.create_future()
        self._pending[msg_id] = fut
        await self._ws.send(json.dumps({
            "wcgp": PROTOCOL_VERSION,
            "id": msg_id,
            "type": msg_type,
            "payload": payload or {},
        }))
        try:
            return await fut
        finally:
            self._pending.pop(msg_id, None)

    # ------------------------------------------------------------------
    # Generic protocol actions
    # ------------------------------------------------------------------

    async def list_challenges(self) -> list[dict[str, Any]]:
        resp = await self.request("session.list")
        return resp["payload"]["challenges"]

    async def introspect(self, challenge_slug: str) -> dict[str, Any]:
        resp = await self.request("session.introspect", {"challenge_slug": challenge_slug})
        return resp["payload"]

    async def join(self, challenge_slug: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
        resp = await self.request("session.join", {"challenge_slug": challenge_slug, "options": options or {}})
        return resp["payload"]

    async def available_actions(self) -> list[dict[str, Any]]:
        resp = await self.request("session.actions")
        return resp["payload"]["actions"]

    async def get_cost(self) -> dict[str, Any]:
        resp = await self.request("session.cost")
        return resp["payload"]["cost"]

    async def get_objective(self) -> dict[str, Any]:
        resp = await self.request("session.objective")
        return resp["payload"]

    async def leave(self) -> dict[str, Any]:
        resp = await self.request("session.leave")
        return resp["payload"]

    async def end(self) -> dict[str, Any]:
        resp = await self.request("session.end")
        return resp["payload"]

    # ------------------------------------------------------------------
    # Hooks for subclasses
    # ------------------------------------------------------------------

    async def play(self) -> None:
        """Override in subclasses to implement challenge-specific logic."""
        raise NotImplementedError

    async def on_event(self, event: dict[str, Any]) -> None:
        """Called for every push event received from the server. Override to handle."""
        logger.debug("Event: %s %s", event.get("type"), event.get("payload"))
