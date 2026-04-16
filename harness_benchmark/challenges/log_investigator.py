from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
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
# Constants
# ---------------------------------------------------------------------------

SERVICE_NAMES = [
    "api-gateway", "auth-service", "user-db", "payment-service",
    "notification-service", "cache-layer", "order-service", "inventory-service",
    "search-service", "analytics-service", "config-service", "rate-limiter",
    "session-store", "file-storage", "email-worker", "scheduler-service",
]

DIFFICULTY_CONFIGS = {
    "easy": {
        "num_services": 5,
        "lines_min": 150,
        "lines_max": 250,
        "time_window_minutes": 60,
        "num_red_herrings": 0,
        "cascade_depth": 2,
    },
    "medium": {
        "num_services": 8,
        "lines_min": 400,
        "lines_max": 600,
        "time_window_minutes": 90,
        "num_red_herrings": 2,
        "cascade_depth": 3,
    },
    "hard": {
        "num_services": 12,
        "lines_min": 1200,
        "lines_max": 1800,
        "time_window_minutes": 120,
        "num_red_herrings": 4,
        "cascade_depth": 5,
    },
}

# ---------------------------------------------------------------------------
# Log message templates
# ---------------------------------------------------------------------------

INFO_TEMPLATES = [
    "Processed request {method} {endpoint} in {duration}ms (status={status})",
    "Health check passed: cpu={cpu}%, memory={mem}MB",
    "Cache hit for key={key} (ttl={ttl}s remaining)",
    "Connection pool stats: active={active}/{max}, idle={idle}",
    "Request {request_id} routed to {target}",
    "Metrics flush: {count} data points sent",
    "TLS handshake completed with {peer}",
    "Session {session_id} validated successfully",
    "Incoming request from {client_ip} to {endpoint}",
    "Response serialized in {duration}ms ({size} bytes)",
    "Worker {worker_id} picked up job {job_id}",
    "Rate limit check passed for client {client_id} ({remaining}/{limit} remaining)",
    "Database query completed in {duration}ms (rows={rows})",
    "Background job {job_id} completed successfully",
    "Config reload completed, {count} keys updated",
]

DEBUG_TEMPLATES = [
    "Entering {function}() with args={args}",
    "Query plan: {plan_type} on table={table} (estimated_rows={rows})",
    "Serializing response payload ({size} bytes)",
    "Middleware chain: [{chain}]",
    "Cache lookup for key={key}: {result}",
    "Token validation: issuer={issuer}, exp={exp}",
    "Routing decision: {path} -> {handler}",
    "Connection acquired from pool in {duration}ms",
    "Request body parsed: content_type={content_type}, size={size}",
    "Retry policy: attempt={attempt}, backoff={backoff}ms",
]

WARN_TEMPLATES = [
    "Slow query detected: {query} took {duration}ms (threshold={threshold}ms)",
    "Deprecated API endpoint called: {endpoint} by client {client_id}",
    "Retry attempt {attempt}/{max_retries} for {operation}",
    "Connection pool nearing capacity: {active}/{max}",
    "Response time above SLA: {duration}ms for {endpoint} (sla={sla}ms)",
    "Disk usage at {usage}% on volume {volume}",
    "Certificate expiring in {days} days for {domain}",
    "Memory usage elevated: {mem}MB / {max_mem}MB",
]

BENIGN_ERROR_TEMPLATES = [
    "Transient DNS resolution failure for {host} (resolved on retry)",
    "Client disconnected before response sent: {client_ip}",
    "Malformed request from {client_ip}: missing header {header}",
    "Rate limit exceeded for client {client_id} (window resets in {reset}s)",
    "Request timeout for {endpoint}: client did not send body within {timeout}s",
]

# ---------------------------------------------------------------------------
# Incident scenario templates
# ---------------------------------------------------------------------------

INCIDENT_SCENARIOS = {
    "connection_refused": {
        "root_cause": [
            "FATAL: Connection pool exhausted — all {max} connections in use, {queued} requests queued",
            "Database connection refused on {host}:{port} — max connections reached",
            "FATAL: Unable to acquire database connection after {timeout}ms — pool depleted",
        ],
        "downstream": [
            "Request to {target} failed: connection refused after {retries} retries",
            "Circuit breaker OPEN for {target} (failures={count}/{threshold})",
            "Upstream {target} unavailable — returning 503 to client",
            "Health check failed for dependency {target}: connection refused",
        ],
        "keywords": ["connection", "refused", "pool", "exhausted", "unavailable"],
        "resolution_keywords": ["increase", "pool", "connection", "limit", "scale", "restart", "max_connections"],
        "resolution": "Increase database connection pool size or scale horizontally to handle load.",
    },
    "timeout": {
        "root_cause": [
            "FATAL: Query execution exceeded {timeout}ms — possible table lock contention",
            "Request processing timed out after {timeout}ms — deadlocked thread detected",
            "FATAL: Upstream response not received within {timeout}ms — circuit breaker triggered",
        ],
        "downstream": [
            "Request to {target} timed out after {timeout}ms",
            "Dependency {target} response time degraded: {duration}ms (expected <{sla}ms)",
            "Circuit breaker OPEN for {target} — consecutive timeouts: {count}",
            "Fallback activated for {target}: returning cached/default response",
        ],
        "keywords": ["timeout", "timed out", "slow", "latency", "deadlock"],
        "resolution_keywords": ["optimize", "query", "index", "timeout", "cache", "scale"],
        "resolution": "Optimize slow queries, add missing indexes, or increase timeout thresholds.",
    },
    "oom": {
        "root_cause": [
            "FATAL: OutOfMemoryError — heap space exhausted (used={used}MB, max={max}MB)",
            "FATAL: Memory allocation failed — system OOM killer invoked on pid {pid}",
            "FATAL: GC overhead limit exceeded — 98% of time spent in garbage collection",
        ],
        "downstream": [
            "Request to {target} failed: connection reset by peer",
            "Health check failed for {target}: no response (service may have crashed)",
            "Upstream {target} returned 502 Bad Gateway",
            "Reconnection attempt {attempt} to {target} failed — service unresponsive",
        ],
        "keywords": ["memory", "oom", "heap", "allocation", "crash", "killed"],
        "resolution_keywords": ["memory", "leak", "heap", "limit", "restart", "gc", "scale"],
        "resolution": "Identify and fix memory leak, increase heap size, or add memory limits.",
    },
    "null_pointer": {
        "root_cause": [
            "FATAL: NullPointerException in {function}() at line {line} — unexpected null value for {field}",
            "FATAL: TypeError: Cannot read property '{field}' of null in {function}()",
            "FATAL: Unhandled exception: AttributeError: 'NoneType' has no attribute '{field}'",
        ],
        "downstream": [
            "Request to {target} returned 500 Internal Server Error",
            "Dependency {target} returning errors — {count} failures in last {window}s",
            "Circuit breaker OPEN for {target} — error rate {rate}% exceeds threshold",
            "Upstream {target} error: received malformed response (null body)",
        ],
        "keywords": ["null", "none", "error", "exception", "unhandled", "crash"],
        "resolution_keywords": ["null", "check", "validate", "handle", "fix", "config", "deploy"],
        "resolution": "Add null checks for the affected field or fix the configuration that produces null values.",
    },
    "deadlock": {
        "root_cause": [
            "FATAL: Deadlock detected — transaction {tx_id} waiting on lock held by {other_tx}",
            "FATAL: Lock wait timeout exceeded for transaction {tx_id} — probable deadlock",
            "FATAL: Database reported deadlock on table {table} — two transactions in circular wait",
        ],
        "downstream": [
            "Request to {target} failed: transaction aborted due to upstream deadlock",
            "Write operation to {target} rejected — service returned 409 Conflict",
            "Timeout waiting for {target} to process write — queue backing up",
            "Upstream {target} experiencing high error rate — {count} failures in {window}s",
        ],
        "keywords": ["deadlock", "lock", "transaction", "conflict", "contention"],
        "resolution_keywords": ["lock", "order", "transaction", "retry", "isolation", "deadlock"],
        "resolution": "Fix lock acquisition order to prevent circular waits, or implement retry logic with backoff.",
    },
    "config_error": {
        "root_cause": [
            "FATAL: Invalid configuration — key '{key}' has value '{value}' (expected {expected})",
            "FATAL: Config parse error in {file}: malformed JSON at line {line}",
            "FATAL: Required config key '{key}' missing after reload — using stale value",
        ],
        "downstream": [
            "Request to {target} failed: received malformed response (could not parse payload)",
            "Dependency {target} returning invalid data — schema validation failed",
            "Upstream {target} response format changed unexpectedly — {count} parse failures",
            "Integration with {target} broken — unexpected field values in response",
        ],
        "keywords": ["config", "configuration", "parse", "invalid", "malformed", "schema"],
        "resolution_keywords": ["config", "fix", "revert", "correct", "validate", "rollback"],
        "resolution": "Revert the bad configuration change or fix the malformed config file.",
    },
}

# Template fill helpers
ENDPOINTS = ["/api/v1/users", "/api/v1/orders", "/api/v1/payments", "/api/v1/search", "/api/v1/auth/token", "/api/v1/inventory", "/health", "/metrics"]
METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH"]
FUNCTIONS = ["processRequest", "handleAuth", "executeQuery", "serializeResponse", "validateInput", "routeRequest", "fetchConfig", "checkRateLimit"]
TABLES = ["users", "orders", "payments", "sessions", "inventory", "audit_log", "configs"]
FIELDS = ["user_id", "order_id", "session_token", "payment_ref", "config_key", "auth_header"]


def _fill_template(rng: random.Random, template: str, services: list[str], target: str | None = None) -> str:
    """Fill a log message template with random plausible values."""
    replacements = {
        "method": rng.choice(METHODS),
        "endpoint": rng.choice(ENDPOINTS),
        "duration": str(rng.randint(1, 500)),
        "status": str(rng.choice([200, 200, 200, 201, 204, 301, 400, 404])),
        "cpu": str(rng.randint(5, 85)),
        "mem": str(rng.randint(128, 2048)),
        "max_mem": str(rng.randint(2048, 4096)),
        "key": f"cache:{rng.choice(['user', 'session', 'config', 'rate'])}:{rng.randint(1000, 9999)}",
        "ttl": str(rng.randint(10, 3600)),
        "active": str(rng.randint(5, 45)),
        "max": str(rng.choice([50, 100, 200])),
        "idle": str(rng.randint(1, 20)),
        "request_id": f"req-{rng.randint(10000, 99999):05x}",
        "target": target or rng.choice(services),
        "peer": f"{rng.randint(10, 200)}.{rng.randint(0, 255)}.{rng.randint(0, 255)}.{rng.randint(1, 254)}",
        "session_id": f"sess-{rng.randint(10000, 99999):05x}",
        "client_ip": f"{rng.randint(10, 200)}.{rng.randint(0, 255)}.{rng.randint(0, 255)}.{rng.randint(1, 254)}",
        "size": str(rng.randint(64, 65536)),
        "worker_id": f"w-{rng.randint(1, 16)}",
        "job_id": f"job-{rng.randint(10000, 99999):05x}",
        "client_id": f"client-{rng.randint(1000, 9999)}",
        "remaining": str(rng.randint(0, 100)),
        "limit": str(rng.choice([100, 500, 1000])),
        "rows": str(rng.randint(1, 10000)),
        "count": str(rng.randint(1, 50)),
        "function": rng.choice(FUNCTIONS),
        "args": f"{{{rng.choice(FIELDS)}: ...}}",
        "plan_type": rng.choice(["SeqScan", "IndexScan", "HashJoin", "NestedLoop"]),
        "table": rng.choice(TABLES),
        "result": rng.choice(["HIT", "MISS"]),
        "issuer": rng.choice(["auth.internal", "sso.corp", "oauth.provider"]),
        "exp": str(rng.randint(1700000000, 1800000000)),
        "path": rng.choice(ENDPOINTS),
        "handler": rng.choice(FUNCTIONS),
        "content_type": rng.choice(["application/json", "text/plain", "multipart/form-data"]),
        "attempt": str(rng.randint(1, 5)),
        "max_retries": str(rng.choice([3, 5])),
        "backoff": str(rng.choice([100, 200, 500, 1000])),
        "operation": rng.choice(["db_write", "cache_set", "rpc_call", "queue_publish"]),
        "query": f"SELECT * FROM {rng.choice(TABLES)} WHERE id = ?",
        "threshold": str(rng.choice([100, 200, 500])),
        "sla": str(rng.choice([100, 200, 500])),
        "usage": str(rng.randint(60, 95)),
        "volume": rng.choice(["/data", "/logs", "/tmp"]),
        "days": str(rng.randint(1, 30)),
        "domain": rng.choice(["api.internal", "auth.internal", "db.internal"]),
        "host": rng.choice(["db-primary.internal", "db-replica.internal", "cache.internal"]),
        "port": str(rng.choice([5432, 6379, 3306, 27017])),
        "header": rng.choice(["Authorization", "Content-Type", "X-Request-Id"]),
        "reset": str(rng.randint(5, 60)),
        "timeout": str(rng.choice([5000, 10000, 30000])),
        "queued": str(rng.randint(10, 200)),
        "retries": str(rng.choice([3, 5, 10])),
        "rate": str(rng.randint(50, 100)),
        "window": str(rng.choice([30, 60, 120])),
        "line": str(rng.randint(42, 500)),
        "field": rng.choice(FIELDS),
        "tx_id": f"tx-{rng.randint(10000, 99999):05x}",
        "other_tx": f"tx-{rng.randint(10000, 99999):05x}",
        "value": rng.choice(["null", "", "undefined", "NaN"]),
        "expected": rng.choice(["string", "int > 0", "valid URL", "non-empty"]),
        "file": rng.choice(["config.json", "settings.yaml", "app.conf"]),
        "pid": str(rng.randint(1000, 65000)),
        "used": str(rng.randint(3500, 4096)),
    }
    try:
        return template.format(**replacements)
    except KeyError:
        return template


def _make_timestamp(base: datetime, offset_seconds: float) -> str:
    dt = base + timedelta(seconds=offset_seconds)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def _parse_timestamp(ts: str) -> float:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return dt.timestamp()


# ---------------------------------------------------------------------------
# Log generation
# ---------------------------------------------------------------------------

@dataclass
class _IncidentDef:
    root_cause_service: str
    error_category: str
    first_error_timestamp: str
    affected_services: list[str]
    resolution: str
    keywords: list[str]
    resolution_keywords: list[str]


def _generate(seed: int | None, difficulty: str) -> tuple[dict[str, list[dict[str, Any]]], _IncidentDef]:
    """Generate logs and incident definition. Returns (logs_by_source, incident)."""
    rng = random.Random(seed)
    cfg = DIFFICULTY_CONFIGS.get(difficulty, DIFFICULTY_CONFIGS["medium"])

    # Pick services
    all_services = list(SERVICE_NAMES)
    rng.shuffle(all_services)
    services = sorted(all_services[: cfg["num_services"]])

    # Build a simple dependency chain for the cascade
    # Root cause is the first in a shuffled copy; cascade follows
    cascade_order = list(services)
    rng.shuffle(cascade_order)
    root_cause = cascade_order[0]
    cascade_depth = min(cfg["cascade_depth"], len(cascade_order) - 1)
    affected = cascade_order[1 : 1 + cascade_depth]

    # Pick scenario
    scenario_key = rng.choice(list(INCIDENT_SCENARIOS.keys()))
    scenario = INCIDENT_SCENARIOS[scenario_key]

    # Time window
    base_time = datetime(2025, 3, 15, 12, 0, 0, tzinfo=timezone.utc)
    window_seconds = cfg["time_window_minutes"] * 60

    # Incident starts in the middle 40-60% of the window
    incident_offset = rng.uniform(window_seconds * 0.4, window_seconds * 0.6)
    incident_ts = _make_timestamp(base_time, incident_offset)

    incident = _IncidentDef(
        root_cause_service=root_cause,
        error_category=scenario_key,
        first_error_timestamp=incident_ts,
        affected_services=affected,
        resolution=scenario["resolution"],
        keywords=scenario["keywords"],
        resolution_keywords=scenario["resolution_keywords"],
    )

    # Generate logs per service
    logs_by_source: dict[str, list[dict[str, Any]]] = {}

    for svc in services:
        num_lines = rng.randint(cfg["lines_min"], cfg["lines_max"])
        entries: list[dict[str, Any]] = []

        # Generate background noise
        for _ in range(num_lines):
            offset = rng.uniform(0, window_seconds)
            ts = _make_timestamp(base_time, offset)

            # Level distribution: DEBUG 30%, INFO 60%, WARN 8%, benign ERROR 2%
            roll = rng.random()
            if roll < 0.30:
                level = "DEBUG"
                msg = _fill_template(rng, rng.choice(DEBUG_TEMPLATES), services)
            elif roll < 0.90:
                level = "INFO"
                msg = _fill_template(rng, rng.choice(INFO_TEMPLATES), services)
            elif roll < 0.98:
                level = "WARN"
                msg = _fill_template(rng, rng.choice(WARN_TEMPLATES), services)
            else:
                level = "ERROR"
                msg = _fill_template(rng, rng.choice(BENIGN_ERROR_TEMPLATES), services)

            trace_id = f"trace-{rng.randint(100000, 999999):06x}" if rng.random() < 0.3 else None
            request_id = f"req-{rng.randint(10000, 99999):05x}" if rng.random() < 0.5 else None

            entries.append({
                "timestamp": ts,
                "level": level,
                "message": msg,
                "trace_id": trace_id,
                "request_id": request_id,
            })

        logs_by_source[svc] = entries

    # Inject incident: root cause errors
    incident_trace = f"trace-incident-{rng.randint(1000, 9999)}"
    num_root_errors = rng.randint(3, 6)
    for i in range(num_root_errors):
        offset = incident_offset + i * rng.uniform(0.5, 3.0)
        ts = _make_timestamp(base_time, offset)
        level = "FATAL" if i == 0 else "ERROR"
        msg = _fill_template(rng, rng.choice(scenario["root_cause"]), services)
        logs_by_source[root_cause].append({
            "timestamp": ts,
            "level": level,
            "message": msg,
            "trace_id": incident_trace,
            "request_id": f"req-{rng.randint(10000, 99999):05x}",
        })

    # Inject cascade: downstream errors with increasing delays
    for depth_idx, downstream_svc in enumerate(affected):
        cascade_delay = (depth_idx + 1) * rng.uniform(5.0, 15.0)
        num_downstream_errors = rng.randint(2, 5)
        for i in range(num_downstream_errors):
            offset = incident_offset + cascade_delay + i * rng.uniform(1.0, 5.0)
            ts = _make_timestamp(base_time, offset)
            level = "ERROR" if i > 0 else "WARN"
            msg = _fill_template(rng, rng.choice(scenario["downstream"]), services, target=root_cause)
            logs_by_source[downstream_svc].append({
                "timestamp": ts,
                "level": level,
                "message": msg,
                "trace_id": incident_trace if rng.random() < 0.7 else f"trace-{rng.randint(100000, 999999):06x}",
                "request_id": f"req-{rng.randint(10000, 99999):05x}",
            })

    # Inject red herrings
    non_affected = [s for s in services if s != root_cause and s not in affected]
    num_red_herrings = min(cfg["num_red_herrings"], len(non_affected))
    for i in range(num_red_herrings):
        svc = non_affected[i % len(non_affected)] if non_affected else rng.choice(services)
        # Place red herring at a different time from the incident
        rh_offset = rng.uniform(0, window_seconds * 0.35)  # early in the window
        ts = _make_timestamp(base_time, rh_offset)
        msg = _fill_template(rng, rng.choice(BENIGN_ERROR_TEMPLATES), services)
        logs_by_source[svc].append({
            "timestamp": ts,
            "level": "ERROR",
            "message": msg,
            "trace_id": f"trace-{rng.randint(100000, 999999):06x}",
            "request_id": f"req-{rng.randint(10000, 99999):05x}",
        })

    # Sort logs by timestamp and assign IDs
    for svc in services:
        logs_by_source[svc].sort(key=lambda e: e["timestamp"])
        for idx, entry in enumerate(logs_by_source[svc]):
            entry["id"] = f"{svc}-{idx:05d}"
            entry["source"] = svc

    return logs_by_source, incident


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def _keywords_match(text: str, keyword_list: list[str]) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in keyword_list)


def _score_submission(payload: dict[str, Any], incident: _IncidentDef) -> dict[str, Any]:
    score: dict[str, Any] = {}

    # Root cause service (30 pts)
    if payload.get("root_cause_service") == incident.root_cause_service:
        score["root_cause_service"] = 30
    elif payload.get("root_cause_service") in incident.affected_services:
        score["root_cause_service"] = 5
    else:
        score["root_cause_service"] = 0

    # Error category (15 pts)
    score["error_category"] = 15 if payload.get("error_category") == incident.error_category else 0

    # First error timestamp (20 pts)
    try:
        delta = abs(_parse_timestamp(payload.get("first_error_timestamp", "")) - _parse_timestamp(incident.first_error_timestamp))
    except (ValueError, TypeError):
        delta = float("inf")

    if delta <= 1:
        score["first_error_timestamp"] = 20
    elif delta <= 5:
        score["first_error_timestamp"] = 15
    elif delta <= 30:
        score["first_error_timestamp"] = 10
    elif delta <= 120:
        score["first_error_timestamp"] = 5
    else:
        score["first_error_timestamp"] = 0

    # Affected services (25 pts) — Jaccard similarity
    submitted_set = set(payload.get("affected_services", []))
    expected_set = set(incident.affected_services)
    if submitted_set or expected_set:
        jaccard = len(submitted_set & expected_set) / len(submitted_set | expected_set)
    else:
        jaccard = 1.0
    score["affected_services"] = round(jaccard * 25, 1)

    # Root cause description (5 pts) — keyword match
    desc = payload.get("root_cause_description", "")
    score["root_cause_description"] = 5 if _keywords_match(desc, incident.keywords) else 0

    # Resolution (5 pts) — keyword match
    resolution = payload.get("resolution", "")
    score["resolution"] = 5 if _keywords_match(resolution, incident.resolution_keywords) else 0

    score["total"] = sum(v for v in score.values() if isinstance(v, (int, float)))
    score["max"] = 100
    return score


# ---------------------------------------------------------------------------
# Challenge class
# ---------------------------------------------------------------------------

class LogInvestigatorChallenge(BaseChallenge):
    slug = "log_investigator"
    name = "Log Investigation"
    description = "Investigate a distributed system incident by analyzing logs from multiple services."
    version = "1.0"
    tags = ["investigation", "context_management", "search", "reasoning"]
    difficulty = "medium"

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    @classmethod
    def actions(cls) -> list[ActionDescriptor]:
        return [
            ActionDescriptor(
                type="log_investigator.list_sources",
                description="List all log sources (services) with their total line counts and time ranges.",
                base_cost=0.5,
                params={},
                response_schema={
                    "sources": "array<{name: string, total_lines: int, earliest: string, latest: string}>",
                },
            ),
            ActionDescriptor(
                type="log_investigator.read_logs",
                description=(
                    "Read logs from a source with optional filters. "
                    "Using any filter (level, time_from, time_to, pattern) reduces cost from 2.0 to 0.5. "
                    "Paginated via page (1-indexed) and page_size (default 50, max 200)."
                ),
                base_cost=2.0,
                params={
                    "source": {"type": "string", "required": True, "description": "Service name"},
                    "page": {"type": "int", "required": False, "default": 1},
                    "page_size": {"type": "int", "required": False, "default": 50, "max": 200},
                    "level": {"type": "string", "required": False, "enum": ["DEBUG", "INFO", "WARN", "ERROR", "FATAL"]},
                    "time_from": {"type": "string", "required": False, "description": "ISO timestamp lower bound (inclusive)"},
                    "time_to": {"type": "string", "required": False, "description": "ISO timestamp upper bound (inclusive)"},
                    "pattern": {"type": "string", "required": False, "description": "Substring search in message field"},
                },
                response_schema={
                    "source": "string",
                    "entries": "array<LogEntry>",
                    "page": "int",
                    "page_size": "int",
                    "total_matching": "int",
                    "total_pages": "int",
                    "filters_applied": "array<string>",
                },
            ),
            ActionDescriptor(
                type="log_investigator.get_entry",
                description="Get a single log entry by its ID. Useful for cross-referencing trace/request IDs.",
                base_cost=0.2,
                params={
                    "entry_id": {"type": "string", "required": True},
                },
                response_schema={"entry": "LogEntry"},
            ),
            ActionDescriptor(
                type="log_investigator.submit_report",
                description=(
                    "Submit investigation findings. Scored on correctness of root cause, "
                    "timeline, affected services, and error category. "
                    "The challenge ends after submission regardless of score."
                ),
                base_cost=3.0,
                params={
                    "root_cause_service": {"type": "string", "required": True, "description": "Service that caused the incident"},
                    "root_cause_description": {"type": "string", "required": True, "description": "What went wrong"},
                    "error_category": {
                        "type": "string", "required": True,
                        "enum": ["timeout", "null_pointer", "connection_refused", "oom", "deadlock", "config_error"],
                    },
                    "first_error_timestamp": {"type": "string", "required": True, "description": "ISO timestamp of the first error"},
                    "affected_services": {
                        "type": "array", "items": {"type": "string"}, "required": True,
                        "description": "List of services affected by the cascade (excluding root cause)",
                    },
                    "resolution": {"type": "string", "required": True, "description": "Suggested fix"},
                },
                response_schema={
                    "score": "object",
                    "total_points": "float",
                    "max_points": "float",
                    "completed": "bool",
                },
            ),
        ]

    @classmethod
    def events(cls) -> list[EventDescriptor]:
        return [
            EventDescriptor(
                type="log_investigator.completed",
                description="Investigation report submitted.",
                payload_schema={"message": "string", "score": "object", "actions_taken": "int", "total_cost": "float"},
            ),
        ]

    @classmethod
    def cost_config(cls) -> CostConfig:
        return CostConfig(
            invalid_action_multiplier=2.0,
            time_rate_per_second=0.02,
            length_rate_per_message=0.15,
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
        self._submission: dict[str, Any] | None = None
        self._score: dict[str, Any] | None = None

        self._logs: dict[str, list[dict[str, Any]]] = {}
        self._incident: _IncidentDef | None = None

        logs, incident = _generate(self._seed, self._difficulty)
        self._logs = logs
        self._incident = incident

        total_lines = sum(len(v) for v in self._logs.values())
        logger.info(
            "[log_investigator] New game — difficulty=%s, services=%d, total_lines=%d, "
            "root_cause=%s, category=%s",
            self._difficulty, len(self._logs), total_lines,
            incident.root_cause_service, incident.error_category,
        )

    # ------------------------------------------------------------------
    # State / objective
    # ------------------------------------------------------------------

    def initial_state(self) -> dict[str, Any]:
        return {
            "difficulty": self._difficulty,
            "num_services": len(self._logs),
            "services": sorted(self._logs.keys()),
            "total_log_lines": sum(len(entries) for entries in self._logs.values()),
        }

    def objective(self) -> dict[str, Any]:
        return {
            "objective": (
                "Investigate a distributed system incident. Determine the root cause service, "
                "error category, first error timestamp, and all affected services. "
                "Use filtered log reads to minimize cost — filters reduce read cost from 2.0 to 0.5. "
                "Submit your findings via submit_report."
            ),
            "hints": [
                "Start with list_sources to see available services and log volumes.",
                "Use level='ERROR' or level='FATAL' filters to find errors efficiently (cost 0.5 vs 2.0 unfiltered).",
                "Use time_from/time_to to narrow down the incident window once you find initial errors.",
                "Look for trace_id values in error entries to follow the cascade across services.",
                "The root cause service is the one where the FIRST error in the incident appears.",
                "Use get_entry (cost 0.2) to inspect individual entries by ID for cross-referencing.",
            ],
            "success_condition": "submit_report with correct findings",
            "failure_condition": None,
            "scoring": {
                "root_cause_service": "30 points (exact match)",
                "error_category": "15 points (exact match)",
                "first_error_timestamp": "20 points (tolerance tiers: <=1s=20, <=5s=15, <=30s=10, <=2min=5)",
                "affected_services": "25 points (Jaccard similarity)",
                "root_cause_description": "5 points (keyword match)",
                "resolution": "5 points (keyword match)",
            },
        }

    def end_summary(self) -> dict[str, Any]:
        summary: dict[str, Any] = {
            "actions_taken": self._action_count,
            "total_cost": self._total_cost,
            "completed": self.completed,
            "difficulty": self._difficulty,
            "num_services": len(self._logs),
        }
        if self._score:
            summary["score"] = self._score
        return summary

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "logs": self._logs,
            "incident": {
                "root_cause_service": self._incident.root_cause_service,
                "error_category": self._incident.error_category,
                "first_error_timestamp": self._incident.first_error_timestamp,
                "affected_services": self._incident.affected_services,
                "resolution": self._incident.resolution,
                "keywords": self._incident.keywords,
                "resolution_keywords": self._incident.resolution_keywords,
            } if self._incident else None,
            "difficulty": self._difficulty,
            "seed": self._seed,
            "action_count": self._action_count,
            "total_cost": self._total_cost,
            "completed": self.completed,
            "submission": self._submission,
            "score": self._score,
            "options": self.options,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], options: dict[str, Any]) -> "LogInvestigatorChallenge":
        instance = cls.__new__(cls)
        super(LogInvestigatorChallenge, instance).__init__(options)
        instance.options = data.get("options", options)
        instance._logs = data["logs"]
        inc = data["incident"]
        instance._incident = _IncidentDef(
            root_cause_service=inc["root_cause_service"],
            error_category=inc["error_category"],
            first_error_timestamp=inc["first_error_timestamp"],
            affected_services=inc["affected_services"],
            resolution=inc["resolution"],
            keywords=inc["keywords"],
            resolution_keywords=inc["resolution_keywords"],
        ) if inc else None
        instance._difficulty = data["difficulty"]
        instance._seed = data["seed"]
        instance._action_count = data["action_count"]
        instance._total_cost = data["total_cost"]
        instance.completed = data["completed"]
        instance._submission = data.get("submission")
        instance._score = data.get("score")
        logger.info(
            "[log_investigator] Session resumed — difficulty=%s, services=%d, actions=%d",
            instance._difficulty, len(instance._logs), instance._action_count,
        )
        return instance

    # ------------------------------------------------------------------
    # Dynamic action availability
    # ------------------------------------------------------------------

    def available_actions(self) -> list[dict[str, Any]]:
        source_names = sorted(self._logs.keys())
        return [
            {
                "type": "log_investigator.list_sources",
                "base_cost": 0.5,
                "params": {},
                "available": True,
            },
            {
                "type": "log_investigator.read_logs",
                "base_cost": 2.0,
                "params": {
                    "source": {"type": "string", "enum": source_names},
                    "page": {"type": "int", "default": 1},
                    "page_size": {"type": "int", "default": 50, "max": 200},
                    "level": {"type": "string", "enum": ["DEBUG", "INFO", "WARN", "ERROR", "FATAL"]},
                    "time_from": {"type": "string"},
                    "time_to": {"type": "string"},
                    "pattern": {"type": "string"},
                },
                "available": True,
                "note": "Cost is 0.5 when any filter (level, time_from, time_to, pattern) is applied, 2.0 otherwise.",
            },
            {
                "type": "log_investigator.get_entry",
                "base_cost": 0.2,
                "params": {"entry_id": {"type": "string"}},
                "available": True,
            },
            {
                "type": "log_investigator.submit_report",
                "base_cost": 3.0,
                "params": {
                    "root_cause_service": {"type": "string", "enum": source_names},
                    "root_cause_description": {"type": "string"},
                    "error_category": {"type": "string", "enum": ["timeout", "null_pointer", "connection_refused", "oom", "deadlock", "config_error"]},
                    "first_error_timestamp": {"type": "string"},
                    "affected_services": {"type": "array", "items": {"type": "string"}},
                    "resolution": {"type": "string"},
                },
                "available": not self.completed,
                "note": "Challenge ends after submission." if not self.completed else "Already submitted.",
            },
        ]

    # ------------------------------------------------------------------
    # Action dispatch
    # ------------------------------------------------------------------

    async def handle(self, verb: str, payload: dict[str, Any]) -> ActionResult:
        if verb == "list_sources":
            return self._handle_list_sources()
        if verb == "read_logs":
            return self._handle_read_logs(payload)
        if verb == "get_entry":
            return self._handle_get_entry(payload)
        if verb == "submit_report":
            return self._handle_submit_report(payload)
        raise KeyError(verb)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _handle_list_sources(self) -> ActionResult:
        self._action_count += 1
        cost = 0.5
        self._total_cost += cost
        sources = []
        for name in sorted(self._logs.keys()):
            entries = self._logs[name]
            sources.append({
                "name": name,
                "total_lines": len(entries),
                "earliest": entries[0]["timestamp"] if entries else None,
                "latest": entries[-1]["timestamp"] if entries else None,
            })
        logger.info("[log_investigator] list_sources — %d services", len(sources))
        return ActionResult(payload={"sources": sources}, base_cost=cost)

    def _handle_read_logs(self, payload: dict[str, Any]) -> ActionResult:
        self._action_count += 1
        source = payload.get("source")

        if source not in self._logs:
            cost = 2.0
            self._total_cost += cost
            return ActionResult(
                payload={
                    "error": {
                        "code": "UNKNOWN_SOURCE",
                        "message": f"Unknown source: {source!r}. Use list_sources to see available services.",
                        "detail": {"available": sorted(self._logs.keys())},
                    }
                },
                base_cost=cost,
                invalid=True,
                invalid_reason="unknown_source",
            )

        page = max(1, payload.get("page", 1))
        page_size = min(200, max(1, payload.get("page_size", 50)))
        level = payload.get("level")
        time_from = payload.get("time_from")
        time_to = payload.get("time_to")
        pattern = payload.get("pattern")

        filters_applied: list[str] = []
        entries = self._logs[source]

        if level:
            entries = [e for e in entries if e["level"] == level]
            filters_applied.append("level")
        if time_from:
            entries = [e for e in entries if e["timestamp"] >= time_from]
            filters_applied.append("time_from")
        if time_to:
            entries = [e for e in entries if e["timestamp"] <= time_to]
            filters_applied.append("time_to")
        if pattern:
            pattern_lower = pattern.lower()
            entries = [e for e in entries if pattern_lower in e["message"].lower()]
            filters_applied.append("pattern")

        is_filtered = len(filters_applied) > 0
        cost = 0.5 if is_filtered else 2.0
        self._total_cost += cost

        total_matching = len(entries)
        total_pages = max(1, (total_matching + page_size - 1) // page_size)
        start = (page - 1) * page_size
        page_entries = entries[start : start + page_size]

        logger.info(
            "[log_investigator] read_logs source=%s filters=%s page=%d/%d matching=%d cost=%.1f",
            source, filters_applied, page, total_pages, total_matching, cost,
        )

        return ActionResult(
            payload={
                "source": source,
                "entries": page_entries,
                "page": page,
                "page_size": page_size,
                "total_matching": total_matching,
                "total_pages": total_pages,
                "filters_applied": filters_applied,
            },
            base_cost=cost,
        )

    def _handle_get_entry(self, payload: dict[str, Any]) -> ActionResult:
        self._action_count += 1
        cost = 0.2
        self._total_cost += cost
        entry_id = payload.get("entry_id", "")

        # Parse entry_id: format is "{service-name}-{index:05d}"
        # Service names can contain hyphens, so we split on the last hyphen-followed-by-digits
        parts = entry_id.rsplit("-", 1)
        if len(parts) == 2 and parts[1].isdigit():
            svc_name = parts[0]
            idx = int(parts[1])
        else:
            return ActionResult(
                payload={
                    "error": {
                        "code": "INVALID_ENTRY_ID",
                        "message": f"Invalid entry ID format: {entry_id!r}. Expected format: 'service-name-00042'.",
                    }
                },
                base_cost=cost,
                invalid=True,
                invalid_reason="invalid_entry_id",
            )

        if svc_name not in self._logs:
            return ActionResult(
                payload={
                    "error": {
                        "code": "UNKNOWN_SOURCE",
                        "message": f"No service named {svc_name!r} found.",
                    }
                },
                base_cost=cost,
                invalid=True,
                invalid_reason="unknown_source",
            )

        entries = self._logs[svc_name]
        if idx < 0 or idx >= len(entries):
            return ActionResult(
                payload={
                    "error": {
                        "code": "ENTRY_NOT_FOUND",
                        "message": f"Entry index {idx} out of range for {svc_name} (0-{len(entries) - 1}).",
                    }
                },
                base_cost=cost,
                invalid=True,
                invalid_reason="entry_not_found",
            )

        logger.info("[log_investigator] get_entry %s", entry_id)
        return ActionResult(payload={"entry": entries[idx]}, base_cost=cost)

    def _handle_submit_report(self, payload: dict[str, Any]) -> ActionResult:
        self._action_count += 1
        cost = 3.0
        self._total_cost += cost

        if self.completed:
            return ActionResult(
                payload={
                    "error": {
                        "code": "ALREADY_SUBMITTED",
                        "message": "A report has already been submitted. The challenge is over.",
                    }
                },
                base_cost=cost,
                invalid=True,
                invalid_reason="already_submitted",
            )

        # Validate required fields
        required = ["root_cause_service", "root_cause_description", "error_category",
                     "first_error_timestamp", "affected_services", "resolution"]
        missing = [f for f in required if f not in payload or payload[f] is None]
        if missing:
            return ActionResult(
                payload={
                    "error": {
                        "code": "MISSING_FIELDS",
                        "message": f"Missing required fields: {missing}",
                    }
                },
                base_cost=cost,
                invalid=True,
                invalid_reason="missing_fields",
            )

        self._submission = payload
        self._score = _score_submission(payload, self._incident)
        self.completed = True

        logger.info(
            "[log_investigator] Report submitted — score=%d/%d, actions=%d, cost=%.1f",
            self._score["total"], self._score["max"],
            self._action_count, self._total_cost,
        )

        self._push(
            "log_investigator.completed",
            {
                "message": "Investigation report submitted.",
                "score": self._score,
                "actions_taken": self._action_count,
                "total_cost": self._total_cost,
            },
        )

        return ActionResult(
            payload={
                "score": self._score,
                "total_points": self._score["total"],
                "max_points": self._score["max"],
                "completed": True,
            },
            base_cost=cost,
            completed=True,
        )
