from __future__ import annotations

import asyncio
import logging
import random
from collections import deque
from typing import Any

from aidle.challenges.base import (
    ActionDescriptor,
    ActionResult,
    BaseChallenge,
    CostConfig,
    EventDescriptor,
)

logger = logging.getLogger(__name__)

# Cell types
OPEN = "."
WALL = "#"
GOAL = "G"
OBSTACLE = "O"

DIRECTIONS = {
    "up":    (-1,  0),
    "down":  ( 1,  0),
    "left":  ( 0, -1),
    "right": ( 0,  1),
}


class MazeChallenge(BaseChallenge):
    slug = "maze"
    name = "Labyrinth"
    description = "Navigate a maze from start to goal."
    version = "1.0"
    tags = ["navigation", "spatial"]
    difficulty = "medium"

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    @classmethod
    def actions(cls) -> list[ActionDescriptor]:
        return [
            ActionDescriptor(
                type="maze.get_map",
                description="Returns the current map, your position, and the goal position.",
                base_cost=1.0,
                params={},
                response_schema={
                    "map": "array<array<string>>",
                    "position": {"row": "int", "col": "int"},
                    "goal": {"row": "int", "col": "int"},
                    "legend": "object",
                },
            ),
            ActionDescriptor(
                type="maze.move",
                description="Move the agent one step in a cardinal direction.",
                base_cost=1.0,
                params={
                    "direction": {
                        "type": "string",
                        "enum": ["up", "down", "left", "right"],
                        "required": True,
                    }
                },
                response_schema={
                    "position": {"row": "int", "col": "int"},
                    "reached_goal": "bool",
                },
            ),
        ]

    @classmethod
    def events(cls) -> list[EventDescriptor]:
        return [
            EventDescriptor(
                type="maze.obstacle_created",
                description="Server added a dynamic obstacle to the maze.",
                payload_schema={"position": {"row": "int", "col": "int"}, "obstacle_id": "str"},
            ),
            EventDescriptor(
                type="maze.obstacle_moved",
                description="An existing dynamic obstacle moved.",
                payload_schema={
                    "obstacle_id": "str",
                    "from": {"row": "int", "col": "int"},
                    "to": {"row": "int", "col": "int"},
                },
            ),
            EventDescriptor(
                type="maze.goal_reached",
                description="Informational: you reached the goal.",
                payload_schema={"position": {"row": "int", "col": "int"}, "message": "str"},
            ),
        ]

    @classmethod
    def cost_config(cls) -> CostConfig:
        return CostConfig(
            invalid_action_multiplier=1.0,
            time_rate_per_second=0.01,
            length_rate_per_message=0.1,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def __init__(self, options: dict[str, Any]) -> None:
        super().__init__(options)
        seed = options.get("seed", None)
        size_opt = options.get("size", "medium")
        self._size = {"small": 5, "medium": 8, "large": 12}.get(size_opt, 8)
        self._grid: list[list[str]] = self._generate(seed)
        self._pos = (0, 0)
        self._goal = (self._size - 1, self._size - 1)
        self._grid[self._goal[0]][self._goal[1]] = GOAL
        self._obstacles: dict[str, tuple[int, int]] = {}
        self._obstacle_counter = 0
        self.reached_goal = False
        self.moves_taken = 0
        logger.info("[maze] New game created — size=%d, goal=(%d,%d)", self._size, *self._goal)

    def _generate(self, seed: int | None) -> list[list[str]]:
        rng = random.Random(seed)
        size = self._size
        start = (0, 0)
        goal = (size - 1, size - 1)
        # Regenerate until a path from start to goal exists
        while True:
            grid = [[OPEN] * size for _ in range(size)]
            # Scatter some walls (~20% of cells), never at start or goal
            for r in range(size):
                for c in range(size):
                    if (r, c) in (start, goal):
                        continue
                    if rng.random() < 0.20:
                        grid[r][c] = WALL
            if MazeChallenge._path_exists(grid, size, start, goal):
                return grid

    @staticmethod
    def _path_exists(
        grid: list[list[str]],
        size: int,
        start: tuple[int, int],
        goal: tuple[int, int],
        extra_blocked: tuple[int, int] | None = None,
    ) -> bool:
        """Return True if a passable path from start to goal exists in grid."""
        visited = {start}
        queue: deque[tuple[int, int]] = deque([start])
        while queue:
            r, c = queue.popleft()
            if (r, c) == goal:
                return True
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = r + dr, c + dc
                if (
                    0 <= nr < size
                    and 0 <= nc < size
                    and (nr, nc) not in visited
                    and (nr, nc) != extra_blocked
                    and grid[nr][nc] not in (WALL, OBSTACLE)
                ):
                    visited.add((nr, nc))
                    queue.append((nr, nc))
        return False

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "size": self._size,
            "grid": self._grid,
            "pos": list(self._pos),
            "goal": list(self._goal),
            "obstacles": {k: list(v) for k, v in self._obstacles.items()},
            "obstacle_counter": self._obstacle_counter,
            "reached_goal": self.reached_goal,
            "moves_taken": self.moves_taken,
            "options": self.options,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], options: dict[str, Any]) -> "MazeChallenge":
        instance = cls.__new__(cls)
        # Call BaseChallenge.__init__ manually to set up the push queue
        super(MazeChallenge, instance).__init__(options)
        instance.options = data.get("options", options)
        instance._size = data["size"]
        instance._grid = data["grid"]
        instance._pos = tuple(data["pos"])
        instance._goal = tuple(data["goal"])
        instance._obstacles = {k: tuple(v) for k, v in data["obstacles"].items()}
        instance._obstacle_counter = data["obstacle_counter"]
        instance.reached_goal = data["reached_goal"]
        instance.moves_taken = data["moves_taken"]
        logger.info("[maze] Session resumed — pos=(%d,%d), goal=(%d,%d), moves=%d",
                    *instance._pos, *instance._goal, instance.moves_taken)
        return instance

    def initial_state(self) -> dict[str, Any]:
        r, c = self._pos
        gr, gc = self._goal
        return {
            "position": {"row": r, "col": c},
            "goal": {"row": gr, "col": gc},
        }

    def objective(self) -> dict[str, Any]:
        gr, gc = self._goal
        return {
            "objective": (
                f"Navigate from your starting position (0, 0) to the goal at "
                f"({gr}, {gc}). Avoid walls and dynamic obstacles."
            ),
            "hints": [
                "Use maze.get_map to see the current layout.",
                "Dynamic obstacles can appear and move at any time.",
                "Each action costs points — reach the goal efficiently.",
            ],
            "success_condition": "reach_goal",
            "failure_condition": None,
        }

    def end_summary(self) -> dict[str, Any]:
        return {
            "moves_taken": self.moves_taken,
            "goal_reached": self.reached_goal,
        }

    # ------------------------------------------------------------------
    # Dynamic action availability
    # ------------------------------------------------------------------

    def available_actions(self) -> list[dict[str, Any]]:
        r, c = self._pos
        open_dirs = [
            d for d, (dr, dc) in DIRECTIONS.items()
            if self._passable(r + dr, c + dc)
        ]
        return [
            {
                "type": "maze.get_map",
                "base_cost": 1.0,
                "params": {},
                "available": True,
            },
            {
                "type": "maze.move",
                "base_cost": 1.0,
                "params": {
                    "direction": {"type": "string", "enum": open_dirs}
                },
                "available": bool(open_dirs),
                "note": (
                    None if open_dirs
                    else "All directions are blocked from current position."
                ),
            },
        ]

    # ------------------------------------------------------------------
    # Action handlers
    # ------------------------------------------------------------------

    async def handle(self, verb: str, payload: dict[str, Any]) -> ActionResult:
        if verb == "get_map":
            return self._get_map()
        if verb == "move":
            return self._move(payload)
        raise KeyError(verb)

    def _get_map(self) -> ActionResult:
        r, c = self._pos
        gr, gc = self._goal
        logger.info("[maze] get_map — player at (%d,%d), goal at (%d,%d)", r, c, gr, gc)
        # Overlay current position marker
        display = [row[:] for row in self._grid]
        if display[r][c] not in (GOAL,):
            display[r][c] = "@"
        return ActionResult(
            payload={
                "map": display,
                "position": {"row": r, "col": c},
                "goal": {"row": gr, "col": gc},
                "legend": {
                    ".": "open",
                    "#": "wall",
                    "G": "goal",
                    "O": "obstacle",
                    "@": "you",
                },
            },
            base_cost=1.0,
        )

    def _move(self, payload: dict[str, Any]) -> ActionResult:
        direction = payload.get("direction")
        logger.info("[maze] move %s — from (%d,%d)", direction, *self._pos)
        if direction not in DIRECTIONS:
            return ActionResult(
                payload={
                    "error": {
                        "code": "INVALID_PARAM",
                        "message": f"'direction' must be one of: {list(DIRECTIONS)}. Got: {direction!r}.",
                        "detail": {"param": "direction", "received": direction, "allowed": list(DIRECTIONS)},
                    }
                },
                base_cost=1.0,
                invalid=True,
                invalid_reason="invalid_param",
            )

        dr, dc = DIRECTIONS[direction]
        nr, nc = self._pos[0] + dr, self._pos[1] + dc

        if not self._passable(nr, nc):
            cell = self._cell(nr, nc)
            reason = "out_of_bounds" if cell is None else "wall" if cell == WALL else "obstacle"
            return ActionResult(
                payload={
                    "error": {
                        "code": "INVALID_ACTION",
                        "message": f"Cannot move {direction}: {reason}.",
                        "detail": {
                            "attempted_position": {"row": nr, "col": nc},
                            "reason": reason,
                        },
                    }
                },
                base_cost=1.0,
                invalid=True,
                invalid_reason="invalid_move",
            )

        self._pos = (nr, nc)
        self.moves_taken += 1
        reached = (nr, nc) == self._goal
        logger.info("[maze] moved to (%d,%d) — move #%d", nr, nc, self.moves_taken)
        if reached:
            self.reached_goal = True
            logger.info("[maze] ★ Goal reached in %d moves!", self.moves_taken)
            self._push(
                "maze.goal_reached",
                {"position": {"row": nr, "col": nc}, "message": "You reached the goal!"},
            )

        return ActionResult(
            payload={
                "position": {"row": nr, "col": nc},
                "reached_goal": reached,
            },
            base_cost=1.0,
            completed=reached,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _cell(self, r: int, c: int) -> str | None:
        if 0 <= r < self._size and 0 <= c < self._size:
            return self._grid[r][c]
        return None

    def _passable(self, r: int, c: int) -> bool:
        cell = self._cell(r, c)
        return cell is not None and cell not in (WALL, OBSTACLE)

    # ------------------------------------------------------------------
    # Background task — spawns moving obstacles periodically
    # ------------------------------------------------------------------

    async def run_background(self) -> None:
        await asyncio.sleep(10)
        while True:
            await asyncio.sleep(15)
            self._spawn_obstacle()
            await asyncio.sleep(10)
            self._move_obstacle()

    def _spawn_obstacle(self) -> None:
        # Find a free open cell that is not the player's position or goal,
        # and that does not make the goal unreachable from the player's position.
        candidates = [
            (r, c)
            for r in range(self._size)
            for c in range(self._size)
            if self._grid[r][c] == OPEN
            and (r, c) != self._pos
            and (r, c) != self._goal
            and MazeChallenge._path_exists(
                self._grid, self._size, self._pos, self._goal, extra_blocked=(r, c)
            )
        ]
        if not candidates:
            return
        r, c = random.choice(candidates)
        self._obstacle_counter += 1
        obs_id = f"obs-{self._obstacle_counter:03d}"
        self._obstacles[obs_id] = (r, c)
        self._grid[r][c] = OBSTACLE
        logger.info("[maze] obstacle %s spawned at (%d,%d)", obs_id, r, c)
        self._push("maze.obstacle_created", {"position": {"row": r, "col": c}, "obstacle_id": obs_id})

    def _move_obstacle(self) -> None:
        if not self._obstacles:
            return
        obs_id = random.choice(list(self._obstacles))
        old_r, old_c = self._obstacles[obs_id]
        candidates = [
            (old_r + dr, old_c + dc)
            for dr, dc in DIRECTIONS.values()
            if self._cell(old_r + dr, old_c + dc) == OPEN
            and (old_r + dr, old_c + dc) != self._pos
        ]
        if not candidates:
            return
        new_r, new_c = random.choice(candidates)
        self._grid[old_r][old_c] = OPEN
        self._grid[new_r][new_c] = OBSTACLE
        self._obstacles[obs_id] = (new_r, new_c)
        logger.info("[maze] obstacle %s moved (%d,%d) -> (%d,%d)", obs_id, old_r, old_c, new_r, new_c)
        self._push(
            "maze.obstacle_moved",
            {
                "obstacle_id": obs_id,
                "from": {"row": old_r, "col": old_c},
                "to": {"row": new_r, "col": new_c},
            },
        )
