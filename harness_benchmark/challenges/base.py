from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator


@dataclass
class ActionDescriptor:
    type: str
    description: str
    base_cost: float
    params: dict[str, Any] = field(default_factory=dict)
    response_schema: dict[str, Any] = field(default_factory=dict)


@dataclass
class EventDescriptor:
    type: str
    description: str
    payload_schema: dict[str, Any] = field(default_factory=dict)


@dataclass
class CostConfig:
    invalid_action_multiplier: float = 1.0
    time_rate_per_second: float = 0.01
    length_rate_per_message: float = 0.1


@dataclass
class ActionResult:
    """Returned by challenge action handlers."""
    payload: dict[str, Any]
    base_cost: float
    # Set to True if the action was semantically invalid (penalty applies).
    invalid: bool = False
    invalid_reason: str | None = None
    # Set to True when the challenge objective is complete.
    completed: bool = False


class BaseChallenge(ABC):
    slug: str
    name: str
    description: str
    version: str = "1.0"
    tags: list[str] = []
    difficulty: str = "medium"

    def __init__(self, options: dict[str, Any]) -> None:
        self.options = options
        self._push_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    # ------------------------------------------------------------------
    # Metadata (static — returned by session.introspect)
    # ------------------------------------------------------------------

    @classmethod
    @abstractmethod
    def actions(cls) -> list[ActionDescriptor]:
        """Full static catalogue of actions this challenge exposes."""

    @classmethod
    @abstractmethod
    def events(cls) -> list[EventDescriptor]:
        """All push event types this challenge may emit."""

    @classmethod
    def cost_config(cls) -> CostConfig:
        return CostConfig()

    @classmethod
    def introspect(cls) -> dict[str, Any]:
        cfg = cls.cost_config()
        return {
            "challenge_slug": cls.slug,
            "version": cls.version,
            "actions": [
                {
                    "type": a.type,
                    "description": a.description,
                    "base_cost": a.base_cost,
                    "params": a.params,
                    "response_schema": a.response_schema,
                }
                for a in cls.actions()
            ],
            "events": [
                {
                    "type": e.type,
                    "description": e.description,
                    "payload_schema": e.payload_schema,
                }
                for e in cls.events()
            ],
            "cost_config": {
                "invalid_action_multiplier": cfg.invalid_action_multiplier,
                "time_rate_per_second": cfg.time_rate_per_second,
                "length_rate_per_message": cfg.length_rate_per_message,
            },
        }

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @abstractmethod
    def initial_state(self) -> dict[str, Any]:
        """State returned inside session.join.ok."""

    @abstractmethod
    def objective(self) -> dict[str, Any]:
        """Payload for session.objective.ok (minus cost block)."""

    @abstractmethod
    def end_summary(self) -> dict[str, Any]:
        """Extra fields merged into session.end.ok summary."""

    # ------------------------------------------------------------------
    # Serialization (for persistent sessions)
    # ------------------------------------------------------------------

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Serialize all challenge-specific state to a JSON-safe dict."""

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict[str, Any], options: dict[str, Any]) -> "BaseChallenge":
        """Restore a challenge instance from a previously serialized dict."""

    # ------------------------------------------------------------------
    # Dynamic action availability (session.actions)
    # ------------------------------------------------------------------

    @abstractmethod
    def available_actions(self) -> list[dict[str, Any]]:
        """
        Return the currently available actions given world state.
        Each entry mirrors ActionDescriptor fields plus 'available' bool
        and optional 'note' string.
        """

    # ------------------------------------------------------------------
    # Action dispatch
    # ------------------------------------------------------------------

    @abstractmethod
    async def handle(self, verb: str, payload: dict[str, Any]) -> ActionResult:
        """
        Handle a challenge-scoped action.
        verb = the part after the slug dot (e.g. "move" from "maze.move").
        Raise KeyError for unknown verbs.
        """

    # ------------------------------------------------------------------
    # Background tasks & push events
    # ------------------------------------------------------------------

    async def run_background(self) -> None:
        """
        Override to run background tasks (e.g. spawning obstacles).
        Use self._push(event_type, payload) to enqueue push events.
        This coroutine is cancelled when the session ends.
        """

    def _push(self, event_type: str, payload: dict[str, Any]) -> None:
        self._push_queue.put_nowait({"type": event_type, "payload": payload})

    async def push_events(self) -> AsyncIterator[dict[str, Any]]:
        """Async generator yielding queued push events."""
        while True:
            event = await self._push_queue.get()
            yield event
