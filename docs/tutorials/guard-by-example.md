# GUARD by Example

A hands-on tutorial that teaches the GUARD constraint language through 10 progressively complex examples. Each example presents a problem, the GUARD solution, a line-by-line explanation, and the compiled output for a sample target.

---

## Prerequisites

- Familiarity with constraint systems (helpful but not required)
- GUARD compiler (`fluxc`) installed
- Basic understanding of domains, ranges, and boolean logic

---

## Example 1: Single Range Constraint

**Problem:** A temperature sensor must report values between 0°C and 100°C. Anything outside this range is invalid.

```guard
temperature IN 0.0..100.0
```

**Explanation:**
- `temperature` is the target field we're constraining.
- `IN` asserts membership in a range.
- `0.0..100.0` defines a half-open interval [0.0, 100.0).

Wait — actually GUARD uses closed ranges by default. So this means temperature ∈ [0, 100].

**Compiled output (target: `temperature`):**

```json
{
  "constraint": {
    "type": "range",
    "field": "temperature",
    "min": 0.0,
    "max": 100.0,
    "inclusive": true
  },
  "hash": "a3f1c8e2"
}
```

The compiler emits a JSON constraint object and a content hash for caching. Simple, fast, deterministic.

---

## Example 2: Multiple Range Constraints

**Problem:** A pressure vessel has both a minimum safe pressure (1.0 atm) and an operating ceiling (5.0 atm), plus a temperature window of -20°C to 80°C.

```guard
pressure IN 1.0..5.0
temperature IN -20.0..80.0
```

**Explanation:**
- Each line is an independent constraint. GUARD treats newlines as implicit conjunctions at the top level (see Example 4 for explicit AND).
- The compiler generates separate constraint entries for each field.
- Order doesn't matter — the solver handles them in parallel.

**Compiled output (target: `pressure`):**

```json
{
  "constraint": {
    "type": "all",
    "constraints": [
      {
        "type": "range",
        "field": "pressure",
        "min": 1.0,
        "max": 5.0,
        "inclusive": true
      },
      {
        "type": "range",
        "field": "temperature",
        "min": -20.0,
        "max": 80.0,
        "inclusive": true
      }
    ]
  },
  "hash": "b7d2e9f4"
}
```

Both constraints are wrapped in an `all` node (everything must pass).

---

## Example 3: Domain Constraint

**Problem:** A vehicle classification system must only accept values from a fixed set: "sedan", "suv", "truck", "van".

```guard
vehicle_class IN ["sedan", "suv", "truck", "van"]
```

**Explanation:**
- `IN` works with both ranges and explicit sets.
- Sets are written as JSON-style arrays of strings.
- At compile time, the set is deduplicated and sorted for consistent hashing.
- The compiled constraint uses a hash set for O(1) membership checks at runtime.

**Compiled output (target: `vehicle_class`):**

```json
{
  "constraint": {
    "type": "domain",
    "field": "vehicle_class",
    "values": ["sedan", "suv", "truck", "van"],
    "mode": "whitelist"
  },
  "hash": "c4a3f1b6"
}
```

---

## Example 4: Exact Match

**Problem:** A firmware version field must be exactly "2.4.1-stable". No ranges, no sets — just one value.

```guard
firmware_version IS "2.4.1-stable"
```

**Explanation:**
- `IS` is the exact match operator. It's sugar for a domain constraint with one element.
- Useful for pinning versions, modes, or states.
- The compiler optimizes this into a direct string comparison (no hash set overhead).

**Compiled output (target: `firmware_version`):**

```json
{
  "constraint": {
    "type": "exact",
    "field": "firmware_version",
    "value": "2.4.1-stable"
  },
  "hash": "d5b4c2a8"
}
```

---

## Example 5: AND Combinator

**Problem:** An engine RPM must be between 800 and 6500, AND the coolant temperature must be below 105°C. Both conditions must hold simultaneously.

```guard
rpm IN 800..6500 AND coolant_temp < 105.0
```

**Explanation:**
- `AND` is an explicit combinator. Use it when constraints are logically coupled and should be grouped.
- `<` is a comparison operator — shorthand for a one-sided range.
- Available comparison operators: `<`, `<=`, `>`, `>=`, `==`, `!=`.
- When you want both sides, use `IN` (it's cleaner). When you need one side, use comparison operators.

**Compiled output (target: `rpm`):**

```json
{
  "constraint": {
    "type": "all",
    "constraints": [
      {
        "type": "range",
        "field": "rpm",
        "min": 800.0,
        "max": 6500.0,
        "inclusive": true
      },
      {
        "type": "range",
        "field": "coolant_temp",
        "max": 105.0,
        "min": null,
        "inclusive": false
      }
    ]
  },
  "hash": "e6c5d3b9"
}
```

Note the `null` min — the compiler emits a half-bounded range rather than -∞.

---

## Example 6: OR Combinator

**Problem:** A sensor reading is valid if it comes from EITHER the primary sensor (range 0–100) OR the backup sensor (range 0–50). The two sensors have different operating envelopes.

```guard
(sensor_a IN 0.0..100.0) OR (sensor_b IN 0.0..50.0)
```

**Explanation:**
- `OR` is the disjunction combinator. At least one branch must pass.
- Parentheses group sub-expressions. Always use them with OR to avoid ambiguity.
- The compiled output is an `any` node — if any child constraint passes, the whole thing passes.
- This is useful for redundant systems, fallback paths, and multi-mode configurations.

**Compiled output (target: `sensor_a`):**

```json
{
  "constraint": {
    "type": "any",
    "constraints": [
      {
        "type": "range",
        "field": "sensor_a",
        "min": 0.0,
        "max": 100.0,
        "inclusive": true
      },
      {
        "type": "range",
        "field": "sensor_b",
        "min": 0.0,
        "max": 50.0,
        "inclusive": true
      }
    ]
  },
  "hash": "f7d6e4c1"
}
```

---

## Example 7: NOT Combinator

**Problem:** A status field must NOT be "faulted" or "unknown". Everything else is acceptable.

```guard
NOT status IN ["faulted", "unknown"]
```

**Explanation:**
- `NOT` negates any constraint. The compiled form wraps the inner constraint in a `not` node.
- At runtime, the engine evaluates the inner constraint, then flips the result.
- `NOT` is especially useful for blacklists (block known-bad values) when a whitelist would be impractical.
- Combine with AND/OR for complex logic: `NOT (x IN ["a", "b"]) AND y > 0`.

**Compiled output (target: `status`):**

```json
{
  "constraint": {
    "type": "not",
    "inner": {
      "type": "domain",
      "field": "status",
      "values": ["faulted", "unknown"],
      "mode": "whitelist"
    }
  },
  "hash": "a8e7f5d2"
}
```

---

## Example 8: Temporal Constraints

**Problem:** A battery voltage must stay above 3.0V for at least 30 continuous seconds. Brief dips below 3.0V are tolerated if they don't last more than 500ms, but the sustained minimum is 3.0V over a 30-second window.

```guard
battery_voltage >= 3.0
  FOR duration >= 30s
  WITH tolerance < 500ms
```

**Explanation:**
- `FOR` introduces a temporal window. `duration >= 30s` means the constraint must hold over a 30-second sliding window.
- `WITH tolerance < 500ms` allows brief violations within that window — up to 500ms of dip is acceptable.
- Temporal units: `ms`, `s`, `m`, `h` (milliseconds, seconds, minutes, hours).
- The compiler generates a temporal constraint node that tracks state over time using a ring buffer.
- Temporal constraints are stateful — the engine must maintain history per field.

**Compiled output (target: `battery_voltage`):**

```json
{
  "constraint": {
    "type": "temporal",
    "field": "battery_voltage",
    "inner": {
      "type": "range",
      "field": "battery_voltage",
      "min": 3.0,
      "min_inclusive": true,
      "max": null
    },
    "window": {
      "duration_ms": 30000,
      "tolerance_ms": 500
    }
  },
  "hash": "b9f8a6e3"
}
```

---

## Example 9: Security Constraints

**Problem:** A command is only valid if it's signed by an authorized key, comes from a trusted network, and the issuer has "admin" or "operator" clearance level.

```guard
command.signature TRUSTED
command.source IN ["internal", "vpn", "lan"]
command.issuer.role IN ["admin", "operator"]
SECURITY clearance >= "admin"
```

**Explanation:**
- `TRUSTED` checks cryptographic signature validity against a configured key store.
- `command.source` constrains the network origin to a whitelist.
- `command.issuer.role` constrains the role to authorized levels.
- `SECURITY clearance >= "admin"` is a security-level assertion. It's evaluated against the runtime security context (not the data payload).
- Security constraints are evaluated **before** data constraints — fail fast on unauthorized access.
- The compiler tags security constraints with a `priority: "security"` flag so the runtime can order evaluation.

**Compiled output (target: `command`):**

```json
{
  "constraint": {
    "type": "all",
    "constraints": [
      {
        "type": "security",
        "priority": "critical",
        "check": "signature_trusted",
        "field": "command.signature"
      },
      {
        "type": "domain",
        "field": "command.source",
        "values": ["internal", "vpn", "lan"],
        "mode": "whitelist"
      },
      {
        "type": "domain",
        "field": "command.issuer.role",
        "values": ["admin", "operator"],
        "mode": "whitelist"
      },
      {
        "type": "security",
        "priority": "critical",
        "check": "clearance",
        "field": "command",
        "minimum_level": "admin"
      }
    ]
  },
  "hash": "c0a9b7f4"
}
```

---

## Example 10: Full Flight Envelope

**Problem:** Define the complete flight envelope constraint for an autonomous drone. This includes:

- Altitude: 0–400ft (regulatory ceiling)
- Airspeed: 0–60 knots, with a temporal requirement that speed stays below 50 knots for sustained flight
- Geographic boundary: must be within one of the approved geofence zones
- Security: only authorized operators with "pilot" clearance can command the drone
- Metadata: tag this constraint set for audit and version tracking
- Exclusions: drone must NOT be in "faulted" or "maintenance" mode

```guard
# Flight Envelope Constraint — v2.1
# Audit: OPS-2024-0315
# Generated: 2024-03-15T10:00:00Z

@version "2.1.0"
@audit_id "OPS-2024-0315"
@authorized_by "chief_pilot:casey.d"

altitude IN 0..400
airspeed IN 0..60

airspeed <= 50
  FOR duration >= 60s
  WITH tolerance < 2000ms

geo_zone IN ["alpha", "bravo", "charlie", "delta"]

NOT flight_mode IN ["faulted", "maintenance"]

SECURITY clearance >= "pilot"
command.signature TRUSTED

@expires "2025-03-15T00:00:00Z"
```

**Explanation:**

This is a production-grade constraint file. Let's break it down section by section.

**Comments:** Lines starting with `#` are comments. They're ignored by the compiler but preserved in the AST for documentation tooling.

**Metadata annotations:** Lines starting with `@` are metadata. They don't generate runtime constraints but are attached to the compiled output for:
- `@version` — Semantic version for change tracking.
- `@audit_id` — Links to an external audit record.
- `@authorized_by` — Who approved this constraint set.
- `@expires` — The constraint set auto-invalidates after this timestamp.

**Core constraints:** The altitude, airspeed, and geo_zone constraints are straightforward range and domain constraints as covered in earlier examples.

**Temporal constraint:** The sustained speed limit (≤50 knots for 60s with 2s tolerance) ensures the drone doesn't cruise at high speed continuously. Brief bursts to 60 knots are allowed.

**NOT constraint:** Excludes faulted and maintenance modes. The drone must be in an operational state.

**Security constraints:** Both signature trust and clearance level are checked. These are evaluated first at runtime.

**Compiled output (target: `flight_envelope`):**

```json
{
  "constraint": {
    "type": "all",
    "constraints": [
      {
        "type": "security",
        "priority": "critical",
        "check": "clearance",
        "minimum_level": "pilot"
      },
      {
        "type": "security",
        "priority": "critical",
        "check": "signature_trusted",
        "field": "command.signature"
      },
      {
        "type": "range",
        "field": "altitude",
        "min": 0.0,
        "max": 400.0,
        "inclusive": true
      },
      {
        "type": "range",
        "field": "airspeed",
        "min": 0.0,
        "max": 60.0,
        "inclusive": true
      },
      {
        "type": "temporal",
        "field": "airspeed",
        "inner": {
          "type": "range",
          "field": "airspeed",
          "max": 50.0,
          "max_inclusive": true,
          "min": null
        },
        "window": {
          "duration_ms": 60000,
          "tolerance_ms": 2000
        }
      },
      {
        "type": "domain",
        "field": "geo_zone",
        "values": ["alpha", "bravo", "charlie", "delta"],
        "mode": "whitelist"
      },
      {
        "type": "not",
        "inner": {
          "type": "domain",
          "field": "flight_mode",
          "values": ["faulted", "maintenance"],
          "mode": "whitelist"
        }
      }
    ]
  },
  "metadata": {
    "version": "2.1.0",
    "audit_id": "OPS-2024-0315",
    "authorized_by": "chief_pilot:casey.d",
    "expires": "2025-03-15T00:00:00Z",
    "source_hash": "e1b0c8d3"
  },
  "hash": "d2c1a9b5"
}
```

Notice the compilation order: security constraints are promoted to the front, followed by data constraints, then temporal constraints. This ordering ensures fail-fast behavior — unauthorized requests are rejected before any expensive temporal or domain checks run.

---

## Recap

| Example | Concept | Key Syntax |
|---------|---------|------------|
| 1 | Range | `field IN min..max` |
| 2 | Multiple ranges | One per line (implicit AND) |
| 3 | Domain (set) | `field IN ["a", "b"]` |
| 4 | Exact match | `field IS "value"` |
| 5 | AND | `... AND ...` |
| 6 | OR | `(...) OR (...)` |
| 7 | NOT | `NOT ...` |
| 8 | Temporal | `FOR duration >= 30s WITH tolerance < 500ms` |
| 9 | Security | `SECURITY`, `TRUSTED` |
| 10 | Full envelope | All of the above + metadata + comments |

---

## Next Steps

- **GUARD Language Reference** — Complete syntax specification
- **fluxc Compiler Guide** — Compilation flags, targets, and optimization
- **Runtime Integration** — How to embed GUARD constraints in your application
- **Temporal Constraint Deep Dive** — Ring buffers, sliding windows, and state management
- **Security Model** — Key stores, clearance levels, and audit trails

---

*Written for the Flux compiler workspace. GUARD is a work in progress — syntax may evolve.*
