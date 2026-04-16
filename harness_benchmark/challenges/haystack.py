from __future__ import annotations

import logging
import random
from typing import Any

from harness_benchmark.challenges.base import (
    ActionDescriptor,
    ActionResult,
    BaseChallenge,
    CostConfig,
    EventDescriptor,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Word pool for generating bucket content
# ---------------------------------------------------------------------------

WORD_POOL = [
    "alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel",
    "india", "juliet", "kilo", "lima", "mike", "november", "oscar", "papa",
    "quebec", "romeo", "sierra", "tango", "uniform", "victor", "whiskey",
    "xray", "yankee", "zulu", "apple", "banana", "cherry", "date", "elder",
    "fig", "grape", "hazel", "iris", "juniper", "kiwi", "lemon", "mango",
    "nectar", "olive", "peach", "quince", "rose", "sage", "thyme", "umber",
    "violet", "willow", "yarrow", "zinc", "amber", "bronze", "coral", "dusk",
    "ember", "frost", "glow", "haze", "ivory", "jade", "knot", "lace",
    "moss", "night", "opal", "pearl", "quartz", "ridge", "stone", "tide",
    "unity", "vault", "wave", "xenon", "yield", "zenith", "arrow", "blade",
    "cliff", "drift", "flint", "grain", "heath", "ingot", "jewel", "marsh",
    "plume", "rapid", "shard", "torch", "crest", "depth", "forge", "gleam",
    "haven", "lunar", "noble", "orbit", "prism", "realm", "solar", "trail",
    "vivid", "wield", "bloom", "crane", "dwarf", "flame", "ghost", "hoist",
    "ivory", "joust", "kneel", "lance", "mirth", "nexus", "oxide", "pulse",
    "quest", "rover", "spire", "twist", "usher", "vigor", "wraith", "axiom",
]


class HaystackChallenge(BaseChallenge):
    slug = "haystack"
    name = "Needle in a Haystack"
    description = "Find all occurrences of a keyword across many buckets of text."
    version = "1.0"
    tags = ["search", "recall", "attention"]
    difficulty = "medium"

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    @classmethod
    def actions(cls) -> list[ActionDescriptor]:
        return [
            ActionDescriptor(
                type="haystack.list_buckets",
                description="List all bucket IDs.",
                base_cost=0.5,
                params={},
                response_schema={"bucket_ids": "array<int>", "total": "int"},
            ),
            ActionDescriptor(
                type="haystack.view_bucket",
                description="View the contents of a specific bucket by its ID. Returns lines of text.",
                base_cost=1.0,
                params={"bucket_id": {"type": "int", "required": True}},
                response_schema={
                    "bucket_id": "int",
                    "lines": "array<string>",
                    "line_count": "int",
                },
            ),
            ActionDescriptor(
                type="haystack.submit",
                description=(
                    "Submit all found positions of the keyword. Each position is "
                    "{bucket_id: int, line: int, col: int} where line and col are "
                    "1-indexed. The col is the character offset of the keyword start."
                ),
                base_cost=2.0,
                params={
                    "positions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "bucket_id": {"type": "int"},
                                "line": {"type": "int"},
                                "col": {"type": "int"},
                            },
                        },
                        "required": True,
                    }
                },
                response_schema={
                    "correct": "int",
                    "missed": "int",
                    "false_positives": "int",
                    "completed": "bool",
                },
            ),
        ]

    @classmethod
    def events(cls) -> list[EventDescriptor]:
        return [
            EventDescriptor(
                type="haystack.completed",
                description="All keyword positions were correctly identified.",
                payload_schema={"message": "string", "actions_taken": "int", "total_cost": "float"},
            ),
        ]

    @classmethod
    def cost_config(cls) -> CostConfig:
        return CostConfig(
            invalid_action_multiplier=2.0,
            time_rate_per_second=0.01,
            length_rate_per_message=0.1,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def __init__(self, options: dict[str, Any]) -> None:
        super().__init__(options)
        self._seed = options.get("seed", None)
        self._difficulty = options.get("difficulty", "medium")
        self._action_count = 0
        self._total_cost = 0.0
        self.completed = False

        self._buckets: list[list[str]] = []
        self._keyword: str = ""
        self._expected: list[dict[str, int]] = []

        self._generate(self._seed)
        logger.info(
            "[haystack] New game — difficulty=%s, buckets=%d, keyword=%r, occurrences=%d",
            self._difficulty, len(self._buckets), self._keyword, len(self._expected),
        )

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def _generate(self, seed: int | None) -> None:
        rng = random.Random(seed)

        cfg = {
            "easy":   {"num_buckets": 5,  "lines_min": 8,  "lines_max": 12, "words_min": 6,  "words_max": 10, "occurrences_min": 3,  "occurrences_max": 6},
            "medium": {"num_buckets": 15, "lines_min": 15, "lines_max": 25, "words_min": 8,  "words_max": 14, "occurrences_min": 8,  "occurrences_max": 15},
            "hard":   {"num_buckets": 40, "lines_min": 25, "lines_max": 40, "words_min": 10, "words_max": 18, "occurrences_min": 20, "occurrences_max": 40},
        }.get(self._difficulty, {
            "num_buckets": 15, "lines_min": 15, "lines_max": 25,
            "words_min": 8, "words_max": 14, "occurrences_min": 8, "occurrences_max": 15,
        })

        # Pick a keyword that is NOT in the word pool so it stands out clearly
        keyword_pool = [
            "needle", "target", "signal", "marker", "beacon",
            "cipher", "token", "anchor", "spark", "relic",
        ]
        self._keyword = rng.choice(keyword_pool)

        # Ensure keyword isn't accidentally in the word pool
        filler_words = [w for w in WORD_POOL if w != self._keyword]

        num_buckets = cfg["num_buckets"]
        num_occurrences = rng.randint(cfg["occurrences_min"], cfg["occurrences_max"])

        # Generate all buckets with random filler text
        buckets: list[list[list[str]]] = []
        for _ in range(num_buckets):
            num_lines = rng.randint(cfg["lines_min"], cfg["lines_max"])
            lines: list[list[str]] = []
            for _ in range(num_lines):
                num_words = rng.randint(cfg["words_min"], cfg["words_max"])
                line_words = [rng.choice(filler_words) for _ in range(num_words)]
                lines.append(line_words)
            buckets.append(lines)

        # Distribute keyword occurrences across random positions
        placements: list[tuple[int, int, int]] = []  # (bucket_idx, line_idx, word_idx)
        for _ in range(num_occurrences):
            bucket_idx = rng.randint(0, num_buckets - 1)
            line_idx = rng.randint(0, len(buckets[bucket_idx]) - 1)
            word_idx = rng.randint(0, len(buckets[bucket_idx][line_idx]) - 1)
            buckets[bucket_idx][line_idx][word_idx] = self._keyword
            placements.append((bucket_idx, line_idx, word_idx))

        # Convert word lists to strings and compute expected positions
        self._buckets = []
        self._expected = []

        for bucket_idx, bucket_lines in enumerate(buckets):
            string_lines: list[str] = []
            for line_idx, words in enumerate(bucket_lines):
                line_str = " ".join(words)
                string_lines.append(line_str)

                # Find all occurrences of keyword in this line
                start = 0
                while True:
                    pos = line_str.find(self._keyword, start)
                    if pos == -1:
                        break
                    self._expected.append({
                        "bucket_id": bucket_idx,
                        "line": line_idx + 1,  # 1-indexed
                        "col": pos + 1,         # 1-indexed
                    })
                    start = pos + 1

            self._buckets.append(string_lines)

        # Deduplicate expected (same position could be set multiple times)
        seen: set[tuple[int, int, int]] = set()
        deduped: list[dict[str, int]] = []
        for pos in self._expected:
            key = (pos["bucket_id"], pos["line"], pos["col"])
            if key not in seen:
                seen.add(key)
                deduped.append(pos)
        self._expected = deduped

    # ------------------------------------------------------------------
    # State / objective
    # ------------------------------------------------------------------

    def initial_state(self) -> dict[str, Any]:
        return {
            "difficulty": self._difficulty,
            "keyword": self._keyword,
            "num_buckets": len(self._buckets),
        }

    def objective(self) -> dict[str, Any]:
        return {
            "objective": (
                f"Find every occurrence of the keyword \"{self._keyword}\" across all "
                f"{len(self._buckets)} buckets. Use haystack.list_buckets to see bucket IDs, "
                "haystack.view_bucket to read each bucket, then haystack.submit with all "
                "positions found. Each position needs bucket_id, line, and col (all 1-indexed)."
            ),
            "keyword": self._keyword,
            "hints": [
                "Iterate through all buckets systematically.",
                "The keyword may appear multiple times in a single line.",
                "Line and col are 1-indexed.",
                "col is the character position where the keyword starts in the line.",
                "Submit all positions at once — missed positions incur a penalty.",
            ],
            "success_condition": "all_positions_found",
            "failure_condition": None,
        }

    def end_summary(self) -> dict[str, Any]:
        return {
            "actions_taken": self._action_count,
            "total_cost": self._total_cost,
            "completed": self.completed,
            "keyword": self._keyword,
            "total_occurrences": len(self._expected),
        }

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "buckets": self._buckets,
            "keyword": self._keyword,
            "expected": self._expected,
            "difficulty": self._difficulty,
            "seed": self._seed,
            "action_count": self._action_count,
            "total_cost": self._total_cost,
            "completed": self.completed,
            "options": self.options,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], options: dict[str, Any]) -> "HaystackChallenge":
        instance = cls.__new__(cls)
        super(HaystackChallenge, instance).__init__(options)
        instance.options = data.get("options", options)
        instance._buckets = data["buckets"]
        instance._keyword = data["keyword"]
        instance._expected = data["expected"]
        instance._difficulty = data["difficulty"]
        instance._seed = data["seed"]
        instance._action_count = data["action_count"]
        instance._total_cost = data["total_cost"]
        instance.completed = data["completed"]
        logger.info(
            "[haystack] Session resumed — difficulty=%s, buckets=%d, keyword=%r, actions=%d",
            instance._difficulty, len(instance._buckets), instance._keyword, instance._action_count,
        )
        return instance

    # ------------------------------------------------------------------
    # Dynamic action availability
    # ------------------------------------------------------------------

    def available_actions(self) -> list[dict[str, Any]]:
        bucket_ids = list(range(len(self._buckets)))
        return [
            {
                "type": "haystack.list_buckets",
                "base_cost": 0.5,
                "params": {},
                "available": True,
            },
            {
                "type": "haystack.view_bucket",
                "base_cost": 1.0,
                "params": {"bucket_id": {"type": "int", "enum": bucket_ids}},
                "available": True,
            },
            {
                "type": "haystack.submit",
                "base_cost": 2.0,
                "params": {
                    "positions": {
                        "type": "array",
                        "items": {"bucket_id": "int", "line": "int", "col": "int"},
                    }
                },
                "available": True,
            },
        ]

    # ------------------------------------------------------------------
    # Action dispatch
    # ------------------------------------------------------------------

    async def handle(self, verb: str, payload: dict[str, Any]) -> ActionResult:
        if verb == "list_buckets":
            return self._handle_list_buckets()
        if verb == "view_bucket":
            return self._handle_view_bucket(payload)
        if verb == "submit":
            return self._handle_submit(payload)
        raise KeyError(verb)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _handle_list_buckets(self) -> ActionResult:
        self._action_count += 1
        cost = 0.5
        self._total_cost += cost
        bucket_ids = list(range(len(self._buckets)))
        logger.info("[haystack] list_buckets — %d buckets", len(bucket_ids))
        return ActionResult(
            payload={"bucket_ids": bucket_ids, "total": len(bucket_ids)},
            base_cost=cost,
        )

    def _handle_view_bucket(self, payload: dict[str, Any]) -> ActionResult:
        self._action_count += 1
        cost = 1.0
        self._total_cost += cost
        bucket_id = payload.get("bucket_id")

        if not isinstance(bucket_id, int) or bucket_id < 0 or bucket_id >= len(self._buckets):
            logger.info("[haystack] view_bucket INVALID id=%s", bucket_id)
            return ActionResult(
                payload={
                    "error": {
                        "code": "INVALID_PARAM",
                        "message": f"bucket_id must be an integer in [0, {len(self._buckets) - 1}]. Got: {bucket_id!r}",
                        "detail": {"bucket_id": bucket_id, "valid_range": [0, len(self._buckets) - 1]},
                    }
                },
                base_cost=cost,
                invalid=True,
                invalid_reason="invalid_param",
            )

        lines = self._buckets[bucket_id]
        logger.info("[haystack] view_bucket %d — %d lines", bucket_id, len(lines))
        return ActionResult(
            payload={
                "bucket_id": bucket_id,
                "lines": lines,
                "line_count": len(lines),
            },
            base_cost=cost,
        )

    def _handle_submit(self, payload: dict[str, Any]) -> ActionResult:
        self._action_count += 1
        cost = 2.0
        self._total_cost += cost
        positions = payload.get("positions", [])

        if not isinstance(positions, list):
            logger.info("[haystack] submit INVALID — positions is not a list")
            return ActionResult(
                payload={
                    "error": {
                        "code": "INVALID_PARAM",
                        "message": "'positions' must be an array of {bucket_id, line, col}.",
                    }
                },
                base_cost=cost,
                invalid=True,
                invalid_reason="invalid_param",
            )

        # Normalize submitted positions to a set for comparison
        submitted: set[tuple[int, int, int]] = set()
        for pos in positions:
            if isinstance(pos, dict) and "bucket_id" in pos and "line" in pos and "col" in pos:
                submitted.add((pos["bucket_id"], pos["line"], pos["col"]))

        expected_set: set[tuple[int, int, int]] = {
            (p["bucket_id"], p["line"], p["col"]) for p in self._expected
        }

        correct = submitted & expected_set
        missed = expected_set - submitted
        false_positives = submitted - expected_set

        logger.info(
            "[haystack] submit — correct=%d, missed=%d, false_positives=%d (expected=%d)",
            len(correct), len(missed), len(false_positives), len(expected_set),
        )

        # Perfect match = completed
        is_perfect = len(missed) == 0 and len(false_positives) == 0

        if is_perfect:
            self.completed = True
            logger.info(
                "[haystack] ★ Challenge completed! actions=%d, total_cost=%.1f",
                self._action_count, self._total_cost,
            )
            self._push(
                "haystack.completed",
                {
                    "message": "All positions correctly identified!",
                    "actions_taken": self._action_count,
                    "total_cost": self._total_cost,
                },
            )
            return ActionResult(
                payload={
                    "correct": len(correct),
                    "missed": len(missed),
                    "false_positives": len(false_positives),
                    "completed": True,
                },
                base_cost=cost,
                completed=True,
            )

        # Not perfect — penalty for missed and false positives
        penalty_reason_parts = []
        if missed:
            penalty_reason_parts.append(f"{len(missed)} missed")
        if false_positives:
            penalty_reason_parts.append(f"{len(false_positives)} false positives")

        return ActionResult(
            payload={
                "correct": len(correct),
                "missed": len(missed),
                "false_positives": len(false_positives),
                "completed": False,
            },
            base_cost=cost,
            invalid=bool(missed or false_positives),
            invalid_reason=", ".join(penalty_reason_parts) if penalty_reason_parts else None,
        )
