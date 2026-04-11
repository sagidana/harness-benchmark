# WCGP v1.0 — WebSocket Challenge/Game Protocol

## Overview

WCGP (WebSocket Challenge/Game Protocol) is a JSON-based protocol for a challenge system where clients connect to a server, browse challenges, and attempt to solve them. The protocol is generic: new challenges plug in without any protocol changes.

All communication happens over a single persistent WebSocket connection per client.

---

## 1. Transport & Encoding

- **Protocol**: WebSocket (RFC 6455)
- **Encoding**: UTF-8 JSON text frames exclusively
- **Endpoint**: `ws://host:port/` (single endpoint; challenge selection happens at protocol level)
- **Subprotocol header** (optional): `Sec-WebSocket-Protocol: wcgp-1.0`

---

## 2. Message Envelope

Every message in both directions uses this envelope:

```json
{
  "wcgp": "1.0",
  "id": "<string | null>",
  "type": "<string>",
  "payload": {}
}
```

| Field | Description |
|-------|-------------|
| `wcgp` | Protocol version. Must be `"1.0"`. |
| `id` | Correlation ID. Client sets a unique string on every request; server echoes it on the corresponding response. Server-push events set `id` to `null`. |
| `type` | Dot-namespaced discriminator. See naming convention below. |
| `payload` | Message-specific data. Always an object; use `{}` for empty payloads. |

### Type Naming Convention

```
<scope>.<verb>           # client → server  (request)
<scope>.<verb>.ok        # server → client  (success response)
<scope>.<verb>.error     # server → client  (error response)
<scope>.<event_name>     # server → client  (push event, id = null)
```

`scope` is either `session` (cross-challenge) or the challenge slug (e.g. `maze`).

---

## 3. Session State Machine

```
CONNECTED ──session.join──► IN_CHALLENGE ──session.leave──► CONNECTED
                                  │
                             session.end
                                  ▼
                              ENDED (may rejoin)
```

- Challenge actions are only valid in `IN_CHALLENGE`.
- WebSocket disconnect silently finalises any active session server-side.
- After `ENDED`, the client remains connected and may join again.

---

## 4. Generic (Cross-Challenge) Messages

| Type | Dir | Cost | State Required |
|------|-----|------|----------------|
| `session.list` | C→S | 0 | Any |
| `session.introspect` | C→S | 0 | Any |
| `session.join` | C→S | 0 | CONNECTED or ENDED |
| `session.actions` | C→S | 0 | IN_CHALLENGE |
| `session.cost` | C→S | 0 | IN_CHALLENGE |
| `session.objective` | C→S | 1.0 | IN_CHALLENGE |
| `session.leave` | C→S | 0 | IN_CHALLENGE |
| `session.end` | C→S | 0 | IN_CHALLENGE |

---

### `session.list` — Browse available challenges

**Request**
```json
{ "wcgp": "1.0", "id": "1", "type": "session.list", "payload": {} }
```

**Response**
```json
{
  "wcgp": "1.0", "id": "1", "type": "session.list.ok",
  "payload": {
    "challenges": [
      {
        "slug": "maze",
        "name": "Labyrinth",
        "description": "Navigate a maze from start to goal.",
        "version": "1.0",
        "tags": ["navigation", "spatial"],
        "difficulty": "medium"
      }
    ]
  }
}
```

---

### `session.introspect` — Discover a challenge's full action & event catalogue

Returns the static, state-independent catalogue. Use `session.actions` for context-sensitive availability.

**Request**
```json
{
  "wcgp": "1.0", "id": "2", "type": "session.introspect",
  "payload": { "challenge_slug": "maze" }
}
```

**Response**
```json
{
  "wcgp": "1.0", "id": "2", "type": "session.introspect.ok",
  "payload": {
    "challenge_slug": "maze",
    "version": "1.0",
    "actions": [
      {
        "type": "maze.get_map",
        "description": "Returns the current map, your position, and the goal.",
        "base_cost": 1.0,
        "params": {},
        "response_schema": {
          "map": "array<array<string>>",
          "position": {"row": "int", "col": "int"},
          "goal": {"row": "int", "col": "int"}
        }
      },
      {
        "type": "maze.move",
        "description": "Move one step in a cardinal direction.",
        "base_cost": 1.0,
        "params": {
          "direction": {"type": "string", "enum": ["up", "down", "left", "right"], "required": true}
        },
        "response_schema": {
          "position": {"row": "int", "col": "int"},
          "reached_goal": "bool"
        }
      }
    ],
    "events": [
      {
        "type": "maze.obstacle_created",
        "description": "Server added an obstacle to the maze.",
        "payload_schema": {"position": {"row": "int", "col": "int"}}
      },
      {
        "type": "maze.obstacle_moved",
        "description": "An existing obstacle moved.",
        "payload_schema": {
          "from": {"row": "int", "col": "int"},
          "to": {"row": "int", "col": "int"}
        }
      }
    ],
    "cost_config": {
      "invalid_action_multiplier": 1.0,
      "time_rate_per_second": 0.01,
      "length_rate_per_message": 0.1
    }
  }
}
```

---

### `session.join` — Join a challenge

**Request**
```json
{
  "wcgp": "1.0", "id": "3", "type": "session.join",
  "payload": { "challenge_slug": "maze", "options": { "seed": 42 } }
}
```

`options` is challenge-specific and optional.

**Response**
```json
{
  "wcgp": "1.0", "id": "3", "type": "session.join.ok",
  "payload": {
    "challenge_slug": "maze",
    "session_id": "sess-7f3a2b",
    "initial_state": {
      "position": {"row": 0, "col": 0},
      "goal": {"row": 7, "col": 7}
    },
    "cost": { "action": 0.0, "cumulative": 0.0 }
  }
}
```

---

### `session.actions` — Query currently available actions (context-sensitive)

Unlike `session.introspect`, this asks the active challenge *"what can I do right now?"* given the current world state. The challenge evaluates its state and returns only the actions that are currently valid, potentially narrowing parameter enums (e.g. only listing non-blocked directions for `maze.move`).

- **Cost: 0** — querying available actions must be free.
- Reflects state at the moment of request. A push event arriving immediately after may invalidate it; treat as a hint, not a guarantee.
- Push events are never included — they are not client-initiated.

**Request**
```json
{ "wcgp": "1.0", "id": "4", "type": "session.actions", "payload": {} }
```

**Response**
```json
{
  "wcgp": "1.0", "id": "4", "type": "session.actions.ok",
  "payload": {
    "actions": [
      {
        "type": "maze.get_map",
        "base_cost": 1.0,
        "params": {},
        "available": true
      },
      {
        "type": "maze.move",
        "base_cost": 1.0,
        "params": {
          "direction": {"type": "string", "enum": ["down", "right"]}
        },
        "available": true,
        "note": "up and left are blocked by walls from current position"
      }
    ]
  }
}
```

---

### `session.cost` — Query cumulative cost

**Request**
```json
{ "wcgp": "1.0", "id": "5", "type": "session.cost", "payload": {} }
```

**Response**
```json
{
  "wcgp": "1.0", "id": "5", "type": "session.cost.ok",
  "payload": {
    "cost": {
      "cumulative": 14.5,
      "breakdown": {
        "base_actions": 10.0,
        "invalid_action_penalty": 2.0,
        "time_elapsed_penalty": 1.5,
        "length_penalty": 1.0
      }
    }
  }
}
```

Cost: 0 (querying cost is free).

---

### `session.objective` — Get the challenge's goal description

Cost: 1.0 (to discourage repeated reads).

**Request**
```json
{ "wcgp": "1.0", "id": "6", "type": "session.objective", "payload": {} }
```

**Response**
```json
{
  "wcgp": "1.0", "id": "6", "type": "session.objective.ok",
  "payload": {
    "objective": "Navigate from (0,0) to the goal. Reach it in as few moves as possible.",
    "hints": ["Dynamic obstacles can appear at any time."],
    "success_condition": "reach_goal",
    "failure_condition": null,
    "cost": { "action": 1.0, "cumulative": 1.0, "penalty_applied": 0.0, "penalty_reason": null }
  }
}
```

---

### `session.leave` — Leave current challenge (without ending)

Returns a cost snapshot; state returns to `CONNECTED`.

**Response**
```json
{
  "wcgp": "1.0", "id": "7", "type": "session.leave.ok",
  "payload": {
    "session_id": "sess-7f3a2b",
    "completed": false,
    "final_cost": {
      "cumulative": 22.5,
      "breakdown": { "base_actions": 18.0, "invalid_action_penalty": 2.0, "time_elapsed_penalty": 1.5, "length_penalty": 1.0 }
    }
  }
}
```

---

### `session.end` — Finalise and score the session

**Response**
```json
{
  "wcgp": "1.0", "id": "8", "type": "session.end.ok",
  "payload": {
    "session_id": "sess-7f3a2b",
    "challenge_slug": "maze",
    "completed": true,
    "score": {
      "total": 22.5,
      "breakdown": { "base_actions": 18.0, "invalid_action_penalty": 2.0, "time_elapsed_penalty": 1.5, "length_penalty": 1.0 },
      "rating": "B",
      "percentile": 73
    },
    "summary": { "moves_taken": 18, "goal_reached": true, "elapsed_seconds": 45 }
  }
}
```

---

## 5. Challenge-Scoped Messages (Maze Example)

### `maze.get_map` (cost: 1.0)

**Response payload**
```json
{
  "map": [[".", ".", "#"], [".", "G", "."]],
  "position": {"row": 0, "col": 0},
  "goal": {"row": 1, "col": 1},
  "legend": {".": "open", "#": "wall", "G": "goal", "O": "obstacle"},
  "cost": { "action": 1.0, "cumulative": 1.0, "penalty_applied": 0.0, "penalty_reason": null }
}
```

### `maze.move` (cost: 1.0; +1.0 penalty on invalid move)

**Request payload**: `{ "direction": "right" }`

**Success response payload**
```json
{
  "position": {"row": 0, "col": 1},
  "reached_goal": false,
  "cost": { "action": 1.0, "cumulative": 2.0, "penalty_applied": 0.0, "penalty_reason": null }
}
```

**Error response payload** (moving into wall)
```json
{
  "error": {
    "code": "INVALID_ACTION",
    "message": "Cannot move up: wall at that position.",
    "detail": { "attempted_position": {"row": -1, "col": 0}, "reason": "wall" }
  },
  "cost": { "action": 2.0, "cumulative": 4.0, "penalty_applied": 1.0, "penalty_reason": "invalid_move" }
}
```

### Push Events

```json
{ "wcgp": "1.0", "id": null, "type": "maze.obstacle_created",
  "payload": { "position": {"row": 3, "col": 4}, "obstacle_id": "obs-001" } }

{ "wcgp": "1.0", "id": null, "type": "maze.obstacle_moved",
  "payload": { "obstacle_id": "obs-001", "from": {"row": 3, "col": 4}, "to": {"row": 4, "col": 4} } }

{ "wcgp": "1.0", "id": null, "type": "maze.goal_reached",
  "payload": { "position": {"row": 7, "col": 7}, "message": "You reached the goal!" } }
```

`maze.goal_reached` is informational only; `session.end.ok` is the authoritative record.

---

## 6. Cost Accounting

### Components

```
total_cost = base_action_cost
           + invalid_action_penalty   (multiplier × base_cost, per invalid attempt)
           + time_elapsed_penalty     (time_rate × elapsed_seconds, accrues continuously)
           + conversation_length_penalty (length_rate × total_messages_sent)
```

All rates are declared per-challenge in `session.introspect.ok` under `cost_config`.

### Cost Block

Every challenge action response (success **or** error) includes a `cost` block:

```json
{
  "cost": {
    "action": 1.0,
    "cumulative": 14.5,
    "penalty_applied": 0.0,
    "penalty_reason": null
  }
}
```

Full `breakdown` is only included in `session.cost.ok`, `session.leave.ok`, and `session.end.ok`.

`cumulative` always reflects state **after** the current action's cost is applied.

---

## 7. Error Handling

All error responses use a `.error` type suffix:

```json
{
  "wcgp": "1.0",
  "id": "<echoed>",
  "type": "<original_type>.error",
  "payload": {
    "error": { "code": "ERROR_CODE", "message": "Human-readable.", "detail": {} },
    "cost": { "action": 0.0, "cumulative": 0.0, "penalty_applied": 0.0, "penalty_reason": null }
  }
}
```

The `cost` block is present on all in-challenge errors (so the client's model stays in sync). It is omitted for protocol-level errors before a session is established.

### Error Codes

| Code | Description |
|------|-------------|
| `MALFORMED_MESSAGE` | Not valid JSON or missing required envelope fields. |
| `UNKNOWN_TYPE` | Unrecognised `type` field. |
| `UNKNOWN_CHALLENGE` | `challenge_slug` does not exist. |
| `WRONG_STATE` | Action not valid in current state. |
| `ALREADY_IN_CHALLENGE` | `session.join` while already in a challenge. |
| `NOT_IN_CHALLENGE` | Challenge action sent without joining first. |
| `INVALID_ACTION` | Structurally valid but semantically invalid (e.g. move into wall). Penalty applies. |
| `MISSING_PARAM` | Required payload parameter absent. |
| `INVALID_PARAM` | Parameter present but invalid value. |
| `CHALLENGE_ENDED` | Session already ended; no further actions accepted. |
| `RATE_LIMITED` | Too many messages. |
| `INTERNAL_ERROR` | Unexpected server error. Detail is minimal. |
| `UNSUPPORTED_VERSION` | `wcgp` version not supported by this server. |

---

## 8. Challenge Extensibility

A challenge declares:
1. **Slug** — lowercase, hyphen-separated identifier
2. **Actions** — each maps to a `<slug>.<action>` type with `base_cost`, params schema, response schema
3. **Events** — each maps to a `<slug>.<event>` type with payload schema
4. **Join options schema** — optional
5. **Initial state** — returned in `session.join.ok`
6. **Objective** — text, hints, conditions
7. **Cost config** — rates for time/length penalties
8. **`available_actions(state)`** — called by the protocol layer when handling `session.actions`; returns the filtered/annotated action list for the current world state

**Routing**: the server splits `type` on the first `.` to get the scope. If the scope matches a registered challenge slug, the message is routed to that challenge handler. `session.*` messages are handled by the protocol layer directly.

New challenges never require protocol changes.

---

## 9. Protocol-Level Push Events

| Type | Description |
|------|-------------|
| `session.server_notice` | Maintenance or info messages. Payload: `{ level, message, code }`. |
| `session.rate_limit_warning` | Client is sending too fast. Payload: `{ message, retry_after_ms }`. |

---

## 10. Forward Compatibility

- Clients **MUST** ignore unknown fields in any message.
- Clients **MUST NOT** fail on unknown push event types — log and discard.
- Unknown `wcgp` version returns `UNSUPPORTED_VERSION` error.
- Challenge versions are independent of the protocol version.

---

## 11. Security

- **Authentication**: out of scope for this spec; handled at WebSocket upgrade (e.g. `Authorization` header or `?token=` query param).
- **Message size**: recommended limit 64 KB; exceed → `MALFORMED_MESSAGE`.
- **Rate limiting**: warn with `session.rate_limit_warning` before hard `RATE_LIMITED` error.
- **`INTERNAL_ERROR`**: MUST NOT expose stack traces or internal state.
