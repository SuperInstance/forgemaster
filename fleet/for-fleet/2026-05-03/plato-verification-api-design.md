# PLATO Constraint Verification API — Design Document

**Author:** Forgemaster ⚒️  
**Date:** 2026-05-02  
**Status:** Draft v1  
**Purpose:** Make "wrong = compilation error" real. This API is the bridge between natural-language claims and mathematical proof/disproof via FLUX bytecode execution on the PLATO Constraint VM.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [FLUX Bytecode Binary Format](#flux-bytecode-binary-format)
3. [Verification Pipeline](#verification-pipeline)
4. [Tile Confidence Model](#tile-confidence-model)
5. [Rate Limiting & Priority Queue](#rate-limiting--priority-queue)
6. [Endpoints](#endpoints)
   - [POST /compile](#post-compile)
   - [POST /verify](#post-verify)
   - [POST /validate-batch](#post-validate-batch)
   - [GET /verification/{id}](#get-verificationid)
   - [GET /verification/{id}/proof](#get-verificationidproof)
   - [GET /stats](#get-stats)
7. [Error Codes](#error-codes)
8. [Security Model](#security-model)

---

## Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐     ┌────────────┐
│  Agent/Fleet │────▶│  PLATO API  │────▶│  Compile     │────▶│  FLUX VM   │
│  Client      │     │  Gateway    │     │  Stage       │     │  Execute   │
└─────────────┘     └─────────────┘     └──────────────┘     └─────┬──────┘
                                                                      │
                         ┌─────────────┐     ┌──────────────┐         │
                         │  PLATO Room │◀────│  Verify +    │◀────────┘
                         │  (Storage)  │     │  Commit      │
                         └─────────────┘     └──────────────┘
```

The API receives claims in natural language or formal CSP notation, compiles them into FLUX bytecodes, executes them on the Constraint VM, and produces mathematically grounded proof or disproof results.

---

## FLUX Bytecode Binary Format

FLUX (Functional Logic Unified eXecution) is the intermediate representation that the Constraint VM executes. Every instruction is a fixed-width 16-byte word.

### Instruction Layout (16 bytes)

```
Bytes 0-3: Header
  ┌─────────┬─────────┬──────────┬──────────┐
  │ Opcode  │ Opcode  │ Flags    │ Reserved │
  │ Group   │         │          │          │
  │ (1 byte)│ (1 byte)│ (1 byte) │ (1 byte) │
  └─────────┴─────────┴──────────┴──────────┘

Bytes 4-15: Payload (12 bytes, interpretation depends on opcode group)
  ┌──────────┬──────────┬──────────┬──────────┐
  │ Operand1 │ Operand2 │ Operand3 │ Operand4 │
  │ (3 bytes)│ (3 bytes)│ (3 bytes)│ (3 bytes)│
  └──────────┴──────────┴──────────┴──────────┘
```

### Opcode Groups

| Group | ID | Description |
|-------|----|-------------|
| `0x01` | LOAD | Load constants, variables, tile data into registers |
| `0x02` | ARITH | Arithmetic operations (add, sub, mul, div, mod) |
| `0x03` | LOGIC | Boolean logic (and, or, not, implies, iff) |
| `0x04` | COMPARE | Comparison (eq, neq, lt, gt, lte, gte, approx) |
| `0x05` | CONSTRAINT | Declare/maintain constraints (assert, relax, tighten) |
| `0x06` | CONTROL | Flow control (branch, loop, call, return, halt) |
| `0x07` | TILE | Tile operations (fetch, merge, split, validate) |
| `0x08` | PROOF | Proof construction (witness, counterexample, invariants) |
| `0x09` | META | Metadata (source_loc, comment, debug_marker) |
| `0x0A` | SOLVER | Solver invocations (sat, lp, minimize, maximize) |
| `0xFF` | EXT | Extended/custom opcodes (reserved for domain plugins) |

### Flags Byte

```
Bit 7: IMMEDIATE  — operand1 is a literal, not a register reference
Bit 6: NEGATE     — negate the result of this operation
Bit 5: COMMUTATIVE — operation is commutative (solver hint)
Bit 4: REVERSIBLE — this instruction can be reversed for proof trace
Bit 3: CHECKPOINT — mark as checkpoint for rollback
Bit 2-0: RESERVED
```

### Operand Encoding

Each 3-byte operand can be:
- **Register reference** (bit 23 = 0): 23-bit register index (up to 8M registers)
- **Immediate constant pool index** (bit 23 = 1, bit 22 = 0): 22-bit index into constant pool
- **Tile reference** (bits 23-22 = 1,1): 22-bit tile ID index
- **String reference** (flags IMMEDIATE set): 22-bit index into string table

### Constant Pool

Appended after the instruction stream. Entries are length-prefixed:

```
┌────────────┬──────────────────┐
│ Length     │ Value            │
│ (4 bytes)  │ (Length bytes)   │
└────────────┴──────────────────┘
```

### Program Header

Every FLUX program begins with a 32-byte header before instructions:

```
Bytes 0-3:   Magic "FLUX" (0x46 0x4C 0x55 0x58)
Bytes 4-7:   Version (uint32, currently 0x00000001)
Bytes 8-11:  Instruction count (uint32)
Bytes 12-15: Constant pool offset (uint32)
Bytes 16-19: Constant pool size (uint32)
Bytes 20-23: String table offset (uint32)
Bytes 24-27: String table size (uint32)
Bytes 28-31: Flags (uint32)
```

---

## Verification Pipeline

The pipeline has exactly 4 stages. Each stage must complete before the next begins. Failure at any stage produces a structured error.

```
  COMPILE ──────▶ EXECUTE ──────▶ VERIFY ──────▶ COMMIT
  (parse+FLUX)   (run on VM)    (check result)  (write to PLATO)
```

### Stage 1: COMPILE

**Input:** Natural language problem or formal CSP specification  
**Process:**
1. Parse input according to `format` field ("nl" or "csp")
2. For NL: run through constraint extraction pipeline (entity recognition → relation extraction → constraint formulation)
3. For CSP: validate syntax against CSP schema
4. Resolve domain-specific constraint library (load relevant axioms for the declared domain)
5. Emit FLUX bytecodes with optimization passes (dead code elimination, constraint tightening)
6. Estimate computational complexity (P, NP-hard, undecidable)

**Output:** `compilation_id`, FLUX instruction array, execution plan, complexity estimate

**Failure modes:**
- `PARSE_ERROR` — NL text could not be parsed into meaningful constraints
- `DOMAIN_UNKNOWN` — domain string doesn't match any registered domain
- `CSP_INVALID` — CSP JSON fails schema validation
- `AMBIGUOUS` — multiple valid interpretations (requires disambiguation)

### Stage 2: EXECUTE

**Input:** FLUX bytecodes from compile stage  
**Process:**
1. Load FLUX program into Constraint VM
2. Initialize register file and memory
3. Execute instruction stream
4. Solver invocations dispatched to appropriate backend (SAT, LP, SMT)
5. Produce execution trace with all intermediate states

**Output:** Raw execution result, register state, solver outputs, execution trace

**Failure modes:**
- `TIMEOUT` — execution exceeded time budget
- `OOM` — register/memory limit exceeded
- `UNSOLVABLE` — solver returned UNSAT with no useful decomposition
- `BUG` — internal VM error (should never happen, but track it)

### Stage 3: VERIFY

**Input:** Execution result + original claim/constraints  
**Process:**
1. Compare execution result against the claim
2. If result matches claim → attempt proof construction
3. If result contradicts claim → construct counterexample
4. If result is ambiguous → mark inconclusive, identify what's missing
5. Compute confidence score based on:
   - Completeness of constraint coverage (what fraction of constraints were exercised)
   - Solver precision (exact vs. approximate)
   - Domain axiom coverage (how many relevant axioms were applied)
   - Execution stability (do small perturbations change the result?)

**Output:** `verification_id`, status (proven/disproven/inconclusive), proof trace, confidence score, contradicted tile IDs

### Stage 4: COMMIT

**Input:** Verification result from verify stage  
**Process:**
1. Write verification result to PLATO room
2. Update tile confidence scores for all affected tiles
3. Update room-level constraint graph
4. Emit event to subscribers (other agents watching the room)
5. Update global stats

**Output:** Final committed verification record with PLATO room reference

**Failure modes:**
- `ROOM_NOT_FOUND` — target PLATO room doesn't exist
- `WRITE_FAILED` — storage error
- `CONFLICT` — concurrent modification detected (retry with merge)

---

## Tile Confidence Model

Every tile in PLATO carries a confidence score ∈ [0.0, 1.0]. Verification results update confidence according to these rules:

### Confidence Update Rules

```
Initial confidence: 0.5 (unverified)

After VERIFIED (proven):
  new_confidence = min(1.0, old_confidence + BOOST_AMOUNT)
  BOOST_AMOUNT = 0.15 × (1 - old_confidence) × proof_strength
  
  Where proof_strength ∈ [0.5, 1.0]:
    1.0 — Complete formal proof with no gaps
    0.8 — Proof with minor unchecked assumptions  
    0.5 — Empirical verification only (tested but not proven)

After DISPROVEN:
  new_confidence = max(0.0, old_confidence - PENALTY)
  PENALTY = 0.3 × counterexample_strength
  
  Where counterexample_strength ∈ [0.5, 1.0]:
    1.0 — Concrete counterexample found
    0.7 — Statistical disproof (high probability)
    0.5 — Logical inconsistency detected but no concrete counterexample

After INCONCLUSIVE:
  new_confidence = old_confidence × DECAY_FACTOR
  DECAY_FACTOR = 0.95

After FAILED_VERIFICATION (error/timeout):
  new_confidence = old_confidence × 0.98  (very slight decay — don't punish for infra issues)
```

### Confidence Thresholds

| Range | Label | Color | Action |
|-------|-------|-------|--------|
| 0.9–1.0 | **Gold** | 🟡 | Trusted — used as axiomatic input for other verifications |
| 0.7–0.9 | **Silver** | ⚪ | Reliable — used with awareness of residual uncertainty |
| 0.5–0.7 | **Bronze** | 🟤 | Tentative — used only with explicit uncertainty propagation |
| 0.3–0.5 | **Rust** | 🔴 | Suspicious — flagged for re-verification priority |
| 0.0–0.3 | **Slag** | ⚫ | Likely wrong — excluded from constraint graph until re-proven |

### Batch Confidence Decay

Tiles not verified in N days experience slow decay:

```
daily_decay = 0.998  (0.2% per day)
half_life ≈ 346 days
```

This ensures stale knowledge gradually loses confidence until re-verified.

---

## Rate Limiting & Priority Queue

### Priority Levels

| Priority | Level | Who Gets It | Budget |
|----------|-------|-------------|--------|
| 0 | **Critical** | Real-time agent queries, interactive verification | Unlimited (preempt others) |
| 1 | **High** | Fleet-initiated verification of new claims | 60% of capacity |
| 2 | **Normal** | Batch validation, periodic re-verification | 30% of capacity |
| 3 | **Low** | Background consistency checks, stats computation | 10% of capacity |

### Queue Configuration

```json
{
  "max_concurrent_verifications": 8,
  "max_queue_depth": 256,
  "time_budgets": {
    "compile": "10s",
    "execute": {
      "P_class": "60s",
      "NP_hard": "300s",
      "undecidable_heuristic": "600s"
    },
    "verify": "30s",
    "commit": "5s"
  },
  "backpressure": {
    "queue_full": 429,
    "timeout_waiting": 503,
    "concurrent_limit": 429
  },
  "retry": {
    "max_retries": 3,
    "backoff_ms": [1000, 5000, 30000],
    "retryable_errors": ["TIMEOUT", "CONFLICT", "OOM"]
  }
}
```

### Complexity-Based Admission Control

Before queuing a verification, the compile stage estimates complexity. Expensive verifications are:

1. **Deferred** — if complexity is NP-hard and current load > 50%, defer to low-priority queue
2. **Chunked** — if the problem decomposes, split into independent sub-problems
3. **Approximated** — offer caller the choice between exact (slow) and approximate (fast) verification

---

## Endpoints

Base URL: `{PLATO_HOST}/api/v1/verification`

All endpoints accept and return `application/json`. Authentication via fleet token in `Authorization: Bearer {token}` header.

---

### POST /compile

Compile a problem description into FLUX bytecodes.

**Request:**

```json
{
  "problem": "For any triangle with sides a, b, c, the sum of any two sides must be greater than the third side",
  "format": "nl",
  "domain": "geometry",
  "options": {
    "optimize": true,
    "target_complexity": "exact",
    "include_source_map": true
  }
}
```

**Alternative CSP format request:**

```json
{
  "problem": {
    "variables": ["a", "b", "c"],
    "domains": {
      "a": {"type": "real", "min": 0, "max": null},
      "b": {"type": "real", "min": 0, "max": null},
      "c": {"type": "real", "min": 0, "max": null}
    },
    "constraints": [
      {"expr": "a + b > c", "label": "triangle_inequality_1"},
      {"expr": "a + c > b", "label": "triangle_inequality_2"},
      {"expr": "b + c > a", "label": "triangle_inequality_3"}
    ],
    "claim": "forall(a, b, c: a + b > c AND a + c > b AND b + c > a)"
  },
  "format": "csp",
  "domain": "geometry",
  "options": {
    "optimize": true
  }
}
```

**Response (200):**

```json
{
  "compilation_id": "cmp_7f3a2b9e4d",
  "bytecodes": [
    {
      "offset": 0,
      "opcode": "LOAD.CONST",
      "operands": ["a", "b", "c"],
      "source": "line 1, col 12"
    },
    {
      "offset": 1,
      "opcode": "ARITH.ADD",
      "operands": ["a", "b", "$t0"],
      "source": "line 1, col 16"
    },
    {
      "offset": 2,
      "opcode": "COMPARE.GT",
      "operands": ["$t0", "c", "$r0"],
      "source": "line 1, col 20"
    },
    {
      "offset": 3,
      "opcode": "ARITH.ADD",
      "operands": ["a", "c", "$t1"],
      "source": "line 1, col 32"
    },
    {
      "offset": 4,
      "opcode": "COMPARE.GT",
      "operands": ["$t1", "b", "$r1"],
      "source": "line 1, col 36"
    },
    {
      "offset": 5,
      "opcode": "ARITH.ADD",
      "operands": ["b", "c", "$t2"],
      "source": "line 1, col 48"
    },
    {
      "offset": 6,
      "opcode": "COMPARE.GT",
      "operands": ["$t2", "a", "$r2"],
      "source": "line 1, col 52"
    },
    {
      "offset": 7,
      "opcode": "LOGIC.AND",
      "operands": ["$r0", "$r1", "$r3"],
      "source": null
    },
    {
      "offset": 8,
      "opcode": "LOGIC.AND",
      "operands": ["$r3", "$r2", "$result"],
      "source": null
    },
    {
      "offset": 9,
      "opcode": "CONSTRAINT.ASSERT",
      "operands": ["$result", "triangle_inequality"],
      "source": "line 1, col 1"
    },
    {
      "offset": 10,
      "opcode": "CONTROL.HALT",
      "operands": [],
      "source": null
    }
  ],
  "execution_plan": {
    "stages": [
      {"name": "variable_binding", "estimated_ops": 3},
      {"name": "constraint_evaluation", "estimated_ops": 6},
      {"name": "result_aggregation", "estimated_ops": 3}
    ],
    "total_ops": 12,
    "parallelizable": true,
    "solver_required": false
  },
  "estimated_complexity": {
    "class": "P",
    "description": "Linear in number of constraint terms. Direct evaluation, no search required.",
    "worst_case_ops": 12,
    "estimated_time_ms": 5
  },
  "source_map": {
    "line_1": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
  }
}
```

**Error (422 — Unparseable):**

```json
{
  "error": "PARSE_ERROR",
  "message": "Could not extract constraints from the provided problem description.",
  "details": {
    "suggestions": [
      "Try rephrasing as 'For all X, if Y then Z'",
      "Or provide a formal CSP specification with format='csp'"
    ]
  }
}
```

**Error (429 — Queue Full):**

```json
{
  "error": "QUEUE_FULL",
  "message": "Compilation queue is at capacity (256/256). Retry after 30s.",
  "retry_after_ms": 30000
}
```

---

### POST /verify

**The kill shot endpoint.** Takes a claim, compiles it, executes on the Constraint VM, and returns a proof or disproof.

**Request:**

```json
{
  "claim": "In any right triangle with legs a and b and hypotenuse c, a² + b² = c²",
  "room": "geometry-fundamentals",
  "constraints": [
    "a > 0",
    "b > 0",
    "c > 0",
    "a² + b² = c²",
    "angle_opposite_c = 90°"
  ],
  "priority": 0,
  "options": {
    "timeout_ms": 60000,
    "proof_level": "full",
    "generate_witness": true
  }
}
```

**Response (200 — Proven):**

```json
{
  "verification_id": "vrf_a1b2c3d4e5",
  "compilation_id": "cmp_8e7f6g5h4i",
  "status": "proven",
  "claim": "In any right triangle with legs a and b and hypotenuse c, a² + b² = c²",
  "confidence": 0.95,
  "proof_trace": {
    "method": "algebraic_verification",
    "steps": [
      {
        "step": 1,
        "type": "load_axiom",
        "statement": "Right triangle definition: angle between legs = 90°",
        "source": "domain:geometry/axioms"
      },
      {
        "step": 2,
        "type": "apply_theorem",
        "statement": "By Euclid's Proposition I.47 (Pythagorean theorem), for right triangle with legs a,b and hypotenuse c: a² + b² = c²",
        "source": "domain:geometry/theorems/pythagorean"
      },
      {
        "step": 3,
        "type": "verify_constraints",
        "statement": "All input constraints are consistent with theorem prerequisites",
        "checked": ["a > 0", "b > 0", "c > 0", "angle_opposite_c = 90°"]
      },
      {
        "step": 4,
        "type": "conclude",
        "statement": "Claim is proven under the constraint set. a² + b² = c² holds.",
        "proof_strength": 1.0
      }
    ],
    "witnesses": [
      {"a": 3, "b": 4, "c": 5, "check": "9 + 16 = 25 ✓"},
      {"a": 5, "b": 12, "c": 13, "check": "25 + 144 = 169 ✓"},
      {"a": 1, "b": 1, "c": "√2", "check": "1 + 1 = 2 ✓"}
    ],
    "invariants": [
      "a² + b² - c² = 0 for all valid right triangles"
    ]
  },
  "contradicted_tiles": [],
  "affected_tiles": [
    {"tile_id": "tile_pythagorean_v3", "confidence_delta": +0.08, "new_confidence": 0.98},
    {"tile_id": "tile_right_triangle_def", "confidence_delta": +0.03, "new_confidence": 0.96}
  ],
  "execution_time_ms": 42,
  "committed_to": "geometry-fundamentals",
  "timestamp": "2026-05-02T21:00:00.000Z"
}
```

**Response (200 — Disproven):**

```json
{
  "verification_id": "vrf_x1y2z3w4v5",
  "compilation_id": "cmp_p9q8r7s6t",
  "status": "disproven",
  "claim": "For any triangle with sides a=1, b=2, c=5, the triangle inequality holds",
  "confidence": 0.10,
  "proof_trace": {
    "method": "counterexample_construction",
    "steps": [
      {
        "step": 1,
        "type": "load_constraints",
        "statement": "Evaluate: a + b > c where a=1, b=2, c=5"
      },
      {
        "step": 2,
        "type": "evaluate",
        "statement": "1 + 2 = 3, which is NOT > 5"
      },
      {
        "step": 3,
        "type": "counterexample",
        "statement": "Concrete counterexample found: a=1, b=2, c=5 violates triangle inequality",
        "counterexample_strength": 1.0
      }
    ],
    "counterexamples": [
      {
        "assignment": {"a": 1, "b": 2, "c": 5},
        "violated_constraint": "a + b > c",
        "evaluation": "1 + 2 = 3 ≤ 5"
      }
    ]
  },
  "contradicted_tiles": [
    "tile_bad_triangle_claim_47"
  ],
  "affected_tiles": [
    {"tile_id": "tile_bad_triangle_claim_47", "confidence_delta": -0.30, "new_confidence": 0.15}
  ],
  "execution_time_ms": 8,
  "committed_to": "geometry-fundamentals",
  "timestamp": "2026-05-02T21:00:01.000Z"
}
```

**Response (200 — Inconclusive):**

```json
{
  "verification_id": "vrf_m3n4o5p6q7",
  "compilation_id": "cmp_u2v3w4x5y",
  "status": "inconclusive",
  "claim": "P ≠ NP",
  "confidence": 0.50,
  "proof_trace": {
    "method": "complexity_analysis",
    "steps": [
      {
        "step": 1,
        "type": "classify_problem",
        "statement": "This is a Millennium Prize problem. No known proof exists."
      },
      {
        "step": 2,
        "type": "empirical_check",
        "statement": "Checked 10,000 known NP-complete problem instances. None reduced to P-time solutions."
      },
      {
        "step": 3,
        "type": "inconclusive",
        "statement": "Strong empirical evidence but no formal proof. Marking as inconclusive.",
        "missing": ["formal reduction proof", "complexity class separation theorem"]
      }
    ]
  },
  "contradicted_tiles": [],
  "affected_tiles": [],
  "execution_time_ms": 15023,
  "committed_to": null,
  "timestamp": "2026-05-02T21:00:15.000Z"
}
```

---

### POST /validate-batch

Re-verify all tiles in a PLATO room against current constraints. Essential for drift detection.

**Request:**

```json
{
  "room_id": "geometry-fundamentals",
  "reverify": true,
  "options": {
    "priority": 2,
    "stop_on_first_failure": false,
    "update_confidence": true,
    "max_parallel": 4,
    "timeout_per_tile_ms": 30000
  }
}
```

**Response (200):**

```json
{
  "batch_id": "bat_k1l2m3n4o5",
  "room_id": "geometry-fundamentals",
  "status": "completed",
  "total": 47,
  "passed": 44,
  "failed": 2,
  "inconclusive": 1,
  "failed_tiles": [
    {
      "tile_id": "tile_old_claim_12",
      "reason": "Constraint 'sum_of_interior_angles = 180°' no longer holds for spherical geometry tiles added after this tile was created",
      "status": "disproven",
      "confidence_before": 0.85,
      "confidence_after": 0.25
    },
    {
      "tile_id": "tile_typo_claim_33",
      "reason": "Arithmetic error in tile: claims 7×8=54, should be 56",
      "status": "disproven",
      "confidence_before": 0.72,
      "confidence_after": 0.05
    }
  ],
  "inconclusive_tiles": [
    {
      "tile_id": "tile_conjecture_41",
      "reason": "Depends on unresolved conjecture. No counterexample found but no proof either.",
      "confidence_before": 0.51,
      "confidence_after": 0.48
    }
  ],
  "execution_time_ms": 8420,
  "started_at": "2026-05-02T21:00:00.000Z",
  "completed_at": "2026-05-02T21:00:08.420Z"
}
```

**Error (404 — Room Not Found):**

```json
{
  "error": "ROOM_NOT_FOUND",
  "message": "No PLATO room with id 'nonexistent-room' exists.",
  "suggestion": "Check room id or create the room first via PLATO room API."
}
```

---

### GET /verification/{id}

Retrieve the full verification result with provenance chain.

**Request:** `GET /verification/vrf_a1b2c3d4e5`

**Response (200):**

```json
{
  "verification_id": "vrf_a1b2c3d4e5",
  "compilation_id": "cmp_8e7f6g5h4i",
  "status": "proven",
  "claim": "In any right triangle with legs a and b and hypotenuse c, a² + b² = c²",
  "confidence": 0.95,
  "proof_trace": { "...": "(full proof trace as in POST /verify response)" },
  "contradicted_tiles": [],
  "affected_tiles": [
    {"tile_id": "tile_pythagorean_v3", "confidence_delta": +0.08, "new_confidence": 0.98},
    {"tile_id": "tile_right_triangle_def", "confidence_delta": +0.03, "new_confidence": 0.96}
  ],
  "provenance": {
    "compiled_by": "forgemaster",
    "verified_at": "2026-05-02T21:00:00.000Z",
    "compiled_at": "2026-05-02T20:59:59.958Z",
    "execution_time_ms": 42,
    "committed_to": "geometry-fundamentals",
    "revision": 1,
    "parent_verification": null
  },
  "linked_verifications": [
    "vrf_previous_pythagorean_attempt"
  ]
}
```

**Error (404):**

```json
{
  "error": "NOT_FOUND",
  "message": "Verification vrf_nonexistent not found."
}
```

---

### GET /verification/{id}/proof

Returns the FLUX execution trace as a mathematical proof object — the formal artifact.

**Request:** `GET /verification/vrf_a1b2c3d4e5/proof`

**Response (200):**

```json
{
  "verification_id": "vrf_a1b2c3d4e5",
  "proof": {
    "format": "FLUX_PROOF_v1",
    "theorem": {
      "name": "Pythagorean Theorem",
      "statement": "∀ right_triangle(a, b, c) : a² + b² = c²",
      "domain": "geometry"
    },
    "hypotheses": [
      {"id": "H1", "statement": "a, b, c > 0"},
      {"id": "H2", "statement": "angle(a, b) = 90°"},
      {"id": "H3", "statement": "c is the side opposite the right angle"}
    ],
    "proof_steps": [
      {
        "step": 1,
        "from": ["H1", "H2"],
        "rule": "right_triangle_definition",
        "conclude": "Triangle with legs a, b and hypotenuse c"
      },
      {
        "step": 2,
        "from": [1],
        "rule": "euclid_I_47",
        "conclude": "a² + b² = c²"
      }
    ],
    "conclusion": {
      "statement": "a² + b² = c²",
      "qed": true
    },
    "flux_trace": [
      {"offset": 0, "opcode": "0x0701", "operands": [0, 0, 0], "flags": 0x00, "comment": "TILE.FETCH tile_pythagorean_v3"},
      {"offset": 1, "opcode": "0x0501", "operands": [1, 2, 15], "flags": 0x80, "comment": "CONSTRAINT.ASSERT triangle_inequality"},
      {"offset": 2, "opcode": "0x0801", "operands": [0, 1, 2], "flags": 0x10, "comment": "PROOF.WITNESS generate_examples"}
    ],
    "metadata": {
      "generated_by": "PLATO Constraint VM v1.0",
      "flux_version": 1,
      "total_instructions": 11,
      "proof_depth": 2,
      "axiom_dependencies": ["euclid_I_47", "right_triangle_def"],
      "verifiable_by": ["human_review", "automated_replay"]
    }
  }
}
```

---

### GET /stats

Verification statistics — the health dashboard for PLATO's constraint integrity.

**Request:** `GET /stats?room=geometry-fundamentals&period=7d`

**Response (200):**

```json
{
  "period": "2026-04-25T00:00:00Z to 2026-05-02T21:00:00Z",
  "room": "geometry-fundamentals",
  "global": {
    "total_verifications": 1247,
    "pass_rate": 0.943,
    "disproven_rate": 0.039,
    "inconclusive_rate": 0.018
  },
  "drift_detection": {
    "tiles_drifted": 3,
    "avg_confidence_change": -0.04,
    "worst_drift": {
      "tile_id": "tile_old_claim_12",
      "confidence_delta": -0.60,
      "reason": "Constraint scope expanded to include spherical geometry"
    },
    "drift_velocity": 0.006
  },
  "constraint_coverage": {
    "total_constraints": 234,
    "verified_constraints": 219,
    "coverage_ratio": 0.936,
    "unverified": [
      "conjecture_birch_swinnerton_dyer",
      "conjecture_goldbach_variant",
      ...
    ]
  },
  "performance": {
    "avg_verification_time_ms": 127,
    "p50_verification_time_ms": 42,
    "p95_verification_time_ms": 890,
    "p99_verification_time_ms": 4200,
    "avg_compile_time_ms": 18,
    "avg_execute_time_ms": 89
  },
  "confidence_distribution": {
    "gold_0.9_1.0": 156,
    "silver_0.7_0.9": 198,
    "bronze_0.5_0.7": 67,
    "rust_0.3_0.5": 12,
    "slag_0.0_0.3": 3
  },
  "queue": {
    "current_depth": 3,
    "max_depth": 256,
    "avg_wait_time_ms": 150,
    "priority_distribution": {
      "critical": 0,
      "high": 1,
      "normal": 2,
      "low": 0
    }
  }
}
```

---

## Error Codes

| HTTP | Code | Meaning | Retry? |
|------|------|---------|--------|
| 400 | `BAD_REQUEST` | Malformed JSON or missing required fields | No |
| 401 | `UNAUTHORIZED` | Missing or invalid fleet token | No |
| 404 | `NOT_FOUND` | Verification/room/compilation not found | No |
| 422 | `PARSE_ERROR` | Could not parse the problem description | No |
| 422 | `AMBIGUOUS` | Multiple valid interpretations | No (resubmit with disambiguation) |
| 422 | `DOMAIN_UNKNOWN` | Domain not registered | No |
| 422 | `CSP_INVALID` | CSP JSON fails schema validation | No |
| 429 | `QUEUE_FULL` | Verification queue at capacity | Yes (after `retry_after_ms`) |
| 429 | `RATE_LIMITED` | Per-client rate limit exceeded | Yes (after `retry_after_ms`) |
| 500 | `INTERNAL` | Unexpected server error | Yes |
| 503 | `OVERLOADED` | System overloaded, try later | Yes |

---

## Security Model

### Authentication
- Fleet token in `Authorization: Bearer {token}` header
- Token scoped to agent identity and allowed rooms
- Read-only tokens can use GET endpoints only
- Write tokens required for POST endpoints

### Authorization Matrix

| Endpoint | Read Token | Write Token | Admin Token |
|----------|-----------|-------------|-------------|
| POST /compile | ✗ | ✓ | ✓ |
| POST /verify | ✗ | ✓ | ✓ |
| POST /validate-batch | ✗ | ✓ | ✓ |
| GET /verification/{id} | ✓ | ✓ | ✓ |
| GET /verification/{id}/proof | ✓ | ✓ | ✓ |
| GET /stats | ✓ | ✓ | ✓ |

### Audit Trail
Every verification is immutable once committed. Amendments create new verification records linked to the original via `parent_verification`. Full provenance chain is always retrievable.

### Data Isolation
Room data is isolated per room. A verification in room A cannot affect tiles in room B unless explicitly configured as a cross-room constraint.

---

*This document defines the API that turns "I think this is right" into "this is mathematically proven" or "here's exactly why it's wrong." Ship it.* ⚒️
