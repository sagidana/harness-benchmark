from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from aidle.client.base import WCGPClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Event-buffering WebSocket client
# ---------------------------------------------------------------------------

class _BufferingClient(WCGPClient):
    """WCGPClient that buffers push events instead of logging them."""

    def __init__(self, uri: str) -> None:
        super().__init__(uri)
        self._event_buffer: list[dict[str, Any]] = []

    async def on_event(self, event: dict[str, Any]) -> None:
        self._event_buffer.append({
            "type": event.get("type"),
            "payload": event.get("payload", {}),
        })

    def drain_events(self) -> list[dict[str, Any]]:
        events, self._event_buffer = self._event_buffer, []
        return events

    # play() is not used — MCP drives everything via tool calls
    async def play(self) -> None:
        pass


# ---------------------------------------------------------------------------
# MCP server factory
# ---------------------------------------------------------------------------

def create_mcp_server(server_uri: str) -> FastMCP:
    mcp = FastMCP(
        "aidle",
        instructions=(
            "You are connected to an aidle challenge server. "
            "Use list_challenges to discover available challenges, "
            "join_challenge to enter one, get_available_actions to see what you can do, "
            "and perform_action to act. "
            "Every response includes pending_events — read them to stay aware of "
            "server-side changes (e.g. new obstacles). "
            "Call poll_events any time you want to drain buffered events explicitly."
        ),
    )

    client = _BufferingClient(server_uri)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ok(result: Any) -> str:
        return json.dumps({
            "ok": True,
            "result": result,
            "pending_events": client.drain_events(),
        })

    def _err(message: str) -> str:
        return json.dumps({
            "ok": False,
            "error": message,
            "pending_events": client.drain_events(),
        })

    async def _ensure_connected() -> None:
        if client._ws is None or client._ws.close_code is not None:
            await client.connect()
            # Start the receive loop as a background task if not already running
            if not hasattr(client, "_recv_task") or client._recv_task.done():
                client._recv_task = asyncio.create_task(client._receive_loop())

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    @mcp.tool()
    async def list_challenges() -> str:
        """List all challenges available on the server."""
        await _ensure_connected()
        try:
            challenges = await client.list_challenges()
            return _ok(challenges)
        except Exception as e:
            return _err(str(e))

    @mcp.tool()
    async def introspect_challenge(slug: str) -> str:
        """
        Return the full static action and event catalogue for a challenge.
        Use this before joining to understand what actions exist and their costs.

        Args:
            slug: Challenge identifier (e.g. "maze").
        """
        await _ensure_connected()
        try:
            info = await client.introspect(slug)
            return _ok(info)
        except Exception as e:
            return _err(str(e))

    @mcp.tool()
    async def join_challenge(slug: str, options: dict[str, Any] | None = None) -> str:
        """
        Join a challenge and start a session.
        Returns the initial world state and session id.

        Args:
            slug: Challenge identifier (e.g. "maze").
            options: Optional challenge-specific join options (e.g. {"seed": 42}).
        """
        await _ensure_connected()
        try:
            result = await client.join(slug, options or {})
            return _ok(result)
        except Exception as e:
            return _err(str(e))

    @mcp.tool()
    async def get_available_actions() -> str:
        """
        Return the actions currently available given the challenge's world state.
        Use this instead of introspect_challenge to know exactly what you can do
        right now (e.g. only unblocked move directions are listed for maze.move).
        """
        await _ensure_connected()
        try:
            actions = await client.available_actions()
            return _ok(actions)
        except Exception as e:
            return _err(str(e))

    @mcp.tool()
    async def get_objective() -> str:
        """
        Return the challenge's objective, hints, and success/failure conditions.
        Costs 1.0 server-side — call once and remember it.
        """
        await _ensure_connected()
        try:
            result = await client.get_objective()
            return _ok(result)
        except Exception as e:
            return _err(str(e))

    @mcp.tool()
    async def get_cost() -> str:
        """
        Return the current cumulative cost and a full breakdown by component
        (base actions, invalid action penalties, time elapsed, conversation length).
        Free to call — querying cost has no cost.
        """
        await _ensure_connected()
        try:
            result = await client.get_cost()
            return _ok(result)
        except Exception as e:
            return _err(str(e))

    @mcp.tool()
    async def perform_action(type: str, params: dict[str, Any] | None = None) -> str:
        """
        Perform a challenge-scoped action and get immediate feedback.
        The action cost (and any penalty for invalid actions) is included in the response.

        Use get_available_actions first to know valid type strings and their parameters.

        Args:
            type: Full action type string (e.g. "maze.move", "maze.get_map").
            params: Action parameters (e.g. {"direction": "right"} for maze.move).
        """
        await _ensure_connected()
        try:
            resp = await client.request(type, params or {})
            return _ok(resp["payload"])
        except Exception as e:
            return _err(str(e))

    @mcp.tool()
    async def poll_events() -> str:
        """
        Drain and return all push events buffered since the last tool call.
        Push events are also piggybacked on every other tool response —
        use this when you want to explicitly check for new events without
        performing any action.
        """
        await _ensure_connected()
        return json.dumps({
            "ok": True,
            "result": None,
            "pending_events": client.drain_events(),
        })

    @mcp.tool()
    async def leave_challenge() -> str:
        """
        Leave the current challenge without finalising the score.
        Returns the cost snapshot so far. You can join again after leaving.
        """
        await _ensure_connected()
        try:
            result = await client.leave()
            return _ok(result)
        except Exception as e:
            return _err(str(e))

    @mcp.tool()
    async def end_challenge() -> str:
        """
        Finalise the current challenge session and receive your score.
        Returns total score, cost breakdown, and a summary (moves taken, goal reached, etc.).
        You can join another challenge after ending.
        """
        await _ensure_connected()
        try:
            result = await client.end()
            return _ok(result)
        except Exception as e:
            return _err(str(e))

    return mcp


# ---------------------------------------------------------------------------
# Entry point (called from cli.py)
# ---------------------------------------------------------------------------

def run(server_uri: str) -> None:
    mcp_server = create_mcp_server(server_uri)
    logger.info("Starting aidle MCP server (stdio) — connecting to %s", server_uri)
    mcp_server.run(transport="stdio")
