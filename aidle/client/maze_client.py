from __future__ import annotations

import logging
from collections import deque
from typing import Any

from aidle.client.base import WCGPClient

logger = logging.getLogger(__name__)

PASSABLE = {".", "G", "@"}  # cell values the client can walk through

DIRECTION_DELTA: dict[str, tuple[int, int]] = {
    "up":    (-1,  0),
    "down":  ( 1,  0),
    "left":  ( 0, -1),
    "right": ( 0,  1),
}


class MazeClient(WCGPClient):
    """
    Plays the maze challenge using BFS pathfinding.

    Strategy:
      1. Fetch the map after joining to get the full grid.
      2. Run BFS to compute the shortest path to the goal.
      3. Execute the path step by step.
      4. Replan automatically when a push event reports a new obstacle,
         or when a move is rejected (obstacle appeared between plan and execute).
    """

    def __init__(self, uri: str, seed: int | None = None) -> None:
        super().__init__(uri)
        self._seed = seed
        self._pos: tuple[int, int] = (0, 0)
        self._goal: tuple[int, int] = (0, 0)
        self._grid: list[list[str]] = []
        self._replan = False  # set by on_event when an obstacle changes the map

    # ------------------------------------------------------------------
    # Push event handler
    # ------------------------------------------------------------------

    async def on_event(self, event: dict[str, Any]) -> None:
        etype = event.get("type", "")
        payload = event.get("payload", {})

        if etype == "maze.obstacle_created":
            pos = payload["position"]
            logger.info("[EVENT] Obstacle created at (%d, %d)", pos["row"], pos["col"])
            self._apply_obstacle(pos["row"], pos["col"], "O")
            self._replan = True

        elif etype == "maze.obstacle_moved":
            frm, to = payload["from"], payload["to"]
            logger.info("[EVENT] Obstacle %s moved (%d,%d) → (%d,%d)",
                        payload["obstacle_id"], frm["row"], frm["col"], to["row"], to["col"])
            self._apply_obstacle(frm["row"], frm["col"], ".")
            self._apply_obstacle(to["row"], to["col"], "O")
            self._replan = True

        elif etype == "maze.goal_reached":
            logger.info("[EVENT] %s", payload.get("message", "Goal reached!"))

        else:
            logger.debug("[EVENT] %s: %s", etype, payload)

    def _apply_obstacle(self, row: int, col: int, value: str) -> None:
        if self._grid and 0 <= row < len(self._grid) and 0 <= col < len(self._grid[0]):
            self._grid[row][col] = value

    # ------------------------------------------------------------------
    # Main play loop
    # ------------------------------------------------------------------

    async def play(self) -> None:
        # 1. List & introspect
        challenges = await self.list_challenges()
        logger.info("Available challenges: %s", [c["slug"] for c in challenges])

        spec = await self.introspect("maze")
        logger.info("Maze actions: %s", [a["type"] for a in spec["actions"]])

        # 2. Join
        join_resp = await self.join("maze", options={"seed": self._seed})
        init = join_resp["initial_state"]
        self._pos = (init["position"]["row"], init["position"]["col"])
        self._goal = (init["goal"]["row"], init["goal"]["col"])
        logger.info("Joined maze. Start: %s  Goal: %s", self._pos, self._goal)

        # 3. Objective (once)
        obj = await self.get_objective()
        logger.info("Objective: %s", obj["objective"])

        # 4. Fetch map and display
        self._grid = await self._fetch_grid()
        logger.info("Map fetched (%dx%d)", len(self._grid), len(self._grid[0]))
        self._print_map(self._grid)

        # 5. Navigate
        steps = 0
        max_steps = 500
        while steps < max_steps:
            # (Re)plan
            path = self._bfs(self._grid, self._pos, self._goal)
            if path is None:
                logger.warning("No path found — re-fetching map and retrying.")
                self._grid = await self._fetch_grid()
                path = self._bfs(self._grid, self._pos, self._goal)
                if path is None:
                    logger.error("Maze is unsolvable from current position.")
                    break

            logger.info("Path planned: %d steps remaining.", len(path))
            self._replan = False

            # Execute planned path
            for direction in path:
                if self._replan:
                    logger.info("Obstacle event received — replanning.")
                    break

                steps += 1
                result = await self._move(direction)

                if "error" in result:
                    # Move rejected (obstacle appeared); re-fetch and replan
                    logger.info("Move blocked (%s) — re-fetching map and replanning.",
                                result["error"].get("message", ""))
                    self._grid = await self._fetch_grid()
                    self._replan = True
                    break

                cost = result.get("cost", {})
                logger.info(
                    "Step %d: moved %s → (%d,%d)  action_cost=%.2f  cumulative=%.2f",
                    steps,
                    direction,
                    result["position"]["row"],
                    result["position"]["col"],
                    cost.get("action", 0),
                    cost.get("cumulative", 0),
                )
                self._pos = (result["position"]["row"], result["position"]["col"])

                if result.get("reached_goal"):
                    logger.info("Reached the goal in %d steps!", steps)
                    await self._finish(steps)
                    return

            if steps >= max_steps:
                logger.warning("Reached step limit (%d) without solving.", max_steps)

        await self._finish(steps)

    # ------------------------------------------------------------------
    # BFS
    # ------------------------------------------------------------------

    @staticmethod
    def _bfs(
        grid: list[list[str]],
        start: tuple[int, int],
        goal: tuple[int, int],
    ) -> list[str] | None:
        """Return shortest list of direction strings from start to goal, or None."""
        rows, cols = len(grid), len(grid[0])
        queue: deque[tuple[tuple[int, int], list[str]]] = deque()
        queue.append((start, []))
        visited: set[tuple[int, int]] = {start}

        while queue:
            pos, path = queue.popleft()
            if pos == goal:
                return path
            for direction, (dr, dc) in DIRECTION_DELTA.items():
                nr, nc = pos[0] + dr, pos[1] + dc
                if (nr, nc) in visited:
                    continue
                if not (0 <= nr < rows and 0 <= nc < cols):
                    continue
                if grid[nr][nc] not in PASSABLE:
                    continue
                visited.add((nr, nc))
                queue.append(((nr, nc), path + [direction]))

        return None  # no path found

    # ------------------------------------------------------------------
    # Challenge actions
    # ------------------------------------------------------------------

    async def _fetch_grid(self) -> list[list[str]]:
        resp = await self.request("maze.get_map")
        return resp["payload"]["map"]

    async def _move(self, direction: str) -> dict[str, Any]:
        resp = await self.request("maze.move", {"direction": direction})
        return resp["payload"]

    async def _finish(self, steps: int) -> None:
        score_resp = await self.end()
        score = score_resp.get("score", {})
        summary = score_resp.get("summary", {})
        logger.info(
            "Session ended. Total score: %.4f  moves: %d  elapsed: %ds",
            score.get("total", 0),
            summary.get("moves_taken", steps),
            summary.get("elapsed_seconds", 0),
        )
        logger.info("Cost breakdown: %s", score.get("breakdown", {}))

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def _print_map(self, grid: list[list[str]]) -> None:
        lines = ["Map:"]
        for row in grid:
            lines.append("  " + " ".join(row))
        logger.info("\n".join(lines))
