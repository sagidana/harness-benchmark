from __future__ import annotations

import asyncio
import time
import uuid
from enum import Enum, auto
from typing import Any

from aidle.challenges.base import BaseChallenge, CostConfig


class State(Enum):
    CONNECTED = auto()
    IN_CHALLENGE = auto()
    ENDED = auto()


class Session:
    """Per-connection session state and cost accounting."""

    def __init__(self) -> None:
        self.state = State.CONNECTED
        self.challenge: BaseChallenge | None = None
        self.session_id: str | None = None
        self._cost_config: CostConfig | None = None

        # Cost components
        self._base_actions: float = 0.0
        self._invalid_penalty: float = 0.0
        self._message_count: int = 0

        # Timing
        self._start_time: float | None = None
        self._end_time: float | None = None

        # Background task handle
        self._bg_task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def join(self, challenge: BaseChallenge) -> None:
        self.challenge = challenge
        self.session_id = str(uuid.uuid4())[:8]
        self._cost_config = challenge.cost_config()
        self._start_time = time.monotonic()
        self._end_time = None
        self._base_actions = 0.0
        self._invalid_penalty = 0.0
        self._message_count = 0
        self.state = State.IN_CHALLENGE

    def leave(self) -> None:
        self._finalise()
        self.state = State.CONNECTED

    def end(self) -> None:
        self._finalise()
        self.state = State.ENDED

    def _finalise(self) -> None:
        if self._end_time is None:
            self._end_time = time.monotonic()
        if self._bg_task and not self._bg_task.done():
            self._bg_task.cancel()

    # ------------------------------------------------------------------
    # Cost accounting
    # ------------------------------------------------------------------

    def record_message(self) -> None:
        """Call once per client message received (in-challenge)."""
        self._message_count += 1

    def record_action(self, base_cost: float, penalty: float = 0.0) -> None:
        self._base_actions += base_cost
        self._invalid_penalty += penalty

    @property
    def _elapsed(self) -> float:
        if self._start_time is None:
            return 0.0
        end = self._end_time if self._end_time is not None else time.monotonic()
        return end - self._start_time

    def _time_penalty(self) -> float:
        if self._cost_config is None:
            return 0.0
        return self._cost_config.time_rate_per_second * self._elapsed

    def _length_penalty(self) -> float:
        if self._cost_config is None:
            return 0.0
        return self._cost_config.length_rate_per_message * self._message_count

    def cumulative(self) -> float:
        return (
            self._base_actions
            + self._invalid_penalty
            + self._time_penalty()
            + self._length_penalty()
        )

    def cost_breakdown(self) -> dict[str, float]:
        return {
            "base_actions": round(self._base_actions, 4),
            "invalid_action_penalty": round(self._invalid_penalty, 4),
            "time_elapsed_penalty": round(self._time_penalty(), 4),
            "length_penalty": round(self._length_penalty(), 4),
        }

    def cost_block(self, action_cost: float = 0.0, penalty: float = 0.0, penalty_reason: str | None = None) -> dict[str, Any]:
        return {
            "action": round(action_cost + penalty, 4),
            "cumulative": round(self.cumulative(), 4),
            "penalty_applied": round(penalty, 4),
            "penalty_reason": penalty_reason,
        }

    def elapsed_seconds(self) -> int:
        return int(self._elapsed)
