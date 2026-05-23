# Fleet Agent Work Audit — 2026-05-22

**Auditor:** Fleet Auditor  
**Date:** 2026-05-22  
**Scope:** 8 repositories created or modified by fleet agents on 2026-05-22  
**Method:** Full source review, test execution, static analysis, security review, API critique  

---

## Executive Summary

| Repo | Language | Tests | Pass | Coverage | Quality | Verdict |
|------|----------|-------|------|----------|---------|---------|
| [turbovec-integration-ccc](#1-turbovec-integration-ccc) | Python | 41 | 41 | 96% | **5/10** | Critical security & data-loss bugs |
| [vector-novelty](#2-vector-novelty) | Python | 33 | 33 | 94% | **6/10** | Solid core, edge-case bugs, doc mismatch |
| [hebbian-router](#3-hebbian-router) | Python | 36 | 36 | 96% | **5/10** | Index corruption, race conditions, API split |
| [pareto-tournament](#4-pareto-tournament) | Python | 22 | 22 | 96% | **5/10** | README lies, duplicate-ID corruption |
| [thermal-budget](#5-thermal-budget) | Python | 24 | 24 | 92% | **5/10** | Encapsulation break, TOCTOU race, real bug |
| [deadband-rs](#6-deadband-rs) | Rust | 22 | 22 | — | **3/10** | Code deleted from repo; math bug; misnamed crate |
| [flux-vm-v3](#7-flux-vm-v3) | Rust | 87 | 87 | — | **4/10** | Does not compile OOTB; silent truncation; stub opcodes |
| [grand-synthesis](#8-grand-synthesis) | Python | 0 | — | 0% | **4/10** | No tests; broken implementations; fake results |

**Fleet Average: 4.6/10** — Below production-ready. Every repo has at least one bug that would cause real failure in production.

---

## Critical Findings (All Repos)

1. **turbovec-integration-ccc** — `canonical_bytes()` uses `str(dict)` for HMAC, making signatures insertion-order dependent. Cross-node consensus is **broken by design**.
2. **turbovec-integration-ccc** — `rebalance_on_alert()` can lose agents permanently in a race condition.
3. **hebbian-router** — Duplicate `add_route()` corrupts internal indexes; `fire_fast()` skips stats updates.
4. **pareto-tournament** — README portfolio example produces incorrect output; duplicate `agent_id`s silently corrupt results.
5. **thermal-budget** — `fallback_devices=[]` is ignored due to falsy check; `device_budget()` exposes mutable internals.
6. **deadband-rs** — **All Rust code deleted from repo** after initial commit. Published crate has no source in its repo.
7. **flux-vm-v3** — **Does not compile** out of the box (2 errors). Silent bytecode truncation lets malicious programs execute with `value=0`.
8. **grand-synthesis** — **Zero tests**. GLM's phase calculation is mathematically broken. Unified "Laman construction" is a fake algorithm.

---

## 1. turbovec-integration-ccc

**Agent:** CCC  
**Purpose:** Hardware profiling, thermal auto-calibration, distributed consensus with "H¹ holonomy emergence detection."  
**Language:** Python 3.10+  
**Latest commit:** 2026-05-23 02:17:58 +0800  

### Test Results
- **41/41 passed**, 96% coverage
- Missing: `swarm/thermal.py` has no direct tests (74% coverage)

### Security Issues

#### 🔴 P0: Signature determinism bug in `canonical_bytes()`
**File:** `nexus/distributed_consensus.py:89-94`

```python
payload = f"{self.proposal_id}|{self.node_id}|{self.state_delta}|..."
```

`str(dict)` is insertion-order dependent. Two nodes creating logically identical proposals will produce **different signatures**. Cross-node HMAC verification is **fatally broken**.

**Fix:** Use `json.dumps(state_delta, sort_keys=True, separators=(',', ':'))`.

#### 🔴 P0: Missing signature verification path
**File:** `nexus/distributed_consensus.py:257-273`

If `inbound_vote` is provided but `from_node=None`, the vote signature is **never checked**. An attacker can inject forged votes.

**Fix:** Always verify `inbound_vote.verify()` when `inbound_vote is not None`.

#### 🟡 HMAC truncation without rationale
Signatures are truncated from 64 hex chars to 32 (128 bits). Undocumented threat model.

#### 🟡 Shared symmetric secret
Single fleet secret for all nodes means any compromised node can forge everything.

### Bugs / Logic Errors

#### 🔴 P0: Rebalance can lose agents permanently
**File:** `ethos/thermal_auto_calibrate.py:295-313`

```python
budget.release(agent_id)
ok = budget.allocate(agent_id, target)
if ok:
    ...
else:
    pass  # agent released but NOT re-allocated → GONE
```

**Fix:** Make the move atomic inside `ThermalBudget` with a `move_agent()` method.

#### 🔴 P1: `_sign` defined twice
**File:** `nexus/distributed_consensus.py:362-371` and `:384-388`

First definition is completely shadowed. Dead code from unreviewed merge.

#### 🔴 P1: Unreachable dead code in `commit_if_quorum`
**File:** `nexus/distributed_consensus.py:309-318`

If `largest_component < quorum`, no component can have ≥ quorum YES votes, yet an inner loop tries to find one. Mathematically unreachable.

#### 🔴 P1: `thermal_headroom()` returns utilization, not headroom
**File:** `swarm/thermal.py:114-119`

Method name implies remaining capacity; returns `total_current / max_total` (used capacity).

#### 🟡 Fixture mutates shared state
**File:** `tests/test_thermal_auto_calibrate.py:64-70`

`hot_profile` fixture mutates `cold_profile` in-place. Cross-test contamination risk.

#### 🟡 Division-by-zero risk
`calibrate_from_profile()` does `int(free / 0.0)` if params are zero → `OverflowError`.

#### 🟡 Unbounded memory growth
`_rebalance_log`, `_proposals`, `_votes`, `_vote_graph` grow forever with no eviction.

### API Design Problems

- `ThermalAutoCalibrator` reaches into `ThermalBudget._lock` and `_allocations` directly.
- No `README.md` at repo root.
- `ThermalAlert.severity` is raw `str` with no validation.
- Inconsistent type hint style (`dict` vs `Dict`).

### Missing Tests

- `swarm/thermal.py` has no direct tests
- Threading races in rebalance
- Zero-division parameter paths
- `canonical_bytes` with differently-ordered dicts
- Vector-clock merge with mismatched lengths

### Rating: **5/10**

Good testing discipline and modern Python, but contains **multiple production-killing bugs** in consensus and resource management. Needs a hardening pass before touching fleet hardware.

---

## 2. vector-novelty

**Agent:** Unknown  
**Purpose:** Centroid-based novelty/diversity scoring for agent populations (pure NumPy)  
**Language:** Python 3.10+  
**Latest commit:** 2026-05-22 17:32:49 +0800  

### Test Results
- **33/33 passed**, 94% coverage
- CI configured for Python 3.10–3.13

### Security Issues

- **Low:** Frozen `AgentVector` dataclass stores mutable `np.ndarray`. External mutation silently corrupts the stored vector.
- **Low:** `cosine_distance` returns `0.0` for `NaN`/`Inf` inputs, masking data corruption.

### Bugs / Logic Errors

#### 🟡 High: `batch_novelty` empty population returns `NaN`
```python
batch_novelty(np.array([[1.0, 0.0]]), population=np.empty((0, 2)))
# → array([nan])
```

#### 🟡 High: Docstring claims self-exclusion, but code includes self
Docstring: *"excluding itself when n > 1"*
Code: centroid is computed over the full population including every vector.

#### 🟡 High: `cosine_distance` NaN/Inf handling
```python
cosine_distance([np.nan, 0.0], [1.0, 0.0])  # → 0.0 (should be nan)
```

#### 🟡 Medium: `compute_novelty` crashes on 0-dim numpy array
#### 🟡 Medium: `batch_novelty` mismatched dimensions → obscure NumPy error
#### 🟡 Medium: `VectorTable(dim=0)` is allowed and produces nonsense
#### 🟢 Low: README says "14 tests" — there are 33. Outdated.
#### 🟢 Low: `__version__` hardcoded in `__init__.py` — will drift from `pyproject.toml`
#### 🟢 Low: **Missing LICENSE file** despite MIT claim

### API Design Problems

- `compute_novelty(agent_id, vector, population_vectors)` accepts `agent_id` but never uses it.
- No validation on `AgentVector` fields (`fitness`, `thermal_pressure` documented as `[0,1]` but accept any float).
- No `dim > 0` validation in `VectorTable`.
- No `k` type validation (`k=1.5` gives cryptic `TypeError`).

### Missing Tests

- Empty `population` override
- Mismatched `population` dimensions
- `NaN`/`Inf` inputs to `cosine_distance`
- 0-dim numpy array
- `k <= 0` and `k > len(pop)` paths
- `VectorTable(dim=0)`
- `AgentVector` field validation

### Rating: **6/10**

Clean core algorithm, good API intuition, decent tests. Dragged down by edge-case bugs, documentation-code mismatch, and missing defensive validation. Solid proof-of-concept that needs hardening.

---

## 3. hebbian-router

**Agent:** Unknown  
**Purpose:** Self-optimizing stochastic routing inspired by Hebbian learning  
**Language:** Python 3.10+  
**Latest commit:** 2026-05-22 17:30:15 +0800  

### Test Results
- **36/36 passed**, 96% coverage
- CI configured for Python 3.10–3.13 + codecov

### Security Issues

#### 🟡 Medium: Key injection via node names
Route keys use `f"{source}→{destination}"`. If node names contain `→` or `↔`, they collide or corrupt the index.

#### 🟡 Medium: Race conditions in multi-threaded use
`fire()` acquires the lock to build candidates, then releases it before mutating `Route.fires` and `last_fired`. `fire_fast()` also releases the lock before updating exploratory route stats. The Hebbian channel activation loop in `fire()` runs **completely outside the lock**.

### Bugs / Logic Errors

#### 🔴 High: `fire_fast()` does not update stats for compiled routes
Routes with `strength > 0.9` are added to `fired`, but `fires`/`last_fired` are **never incremented**. Reception ratios are meaningless for compiled routes.

#### 🔴 High: Duplicate `add_route` corrupts indexes
Adding the same `(source, destination)` twice overwrites `_routes` but **duplicates entries** in `_routes_by_source` and `_routes_by_dest`.

#### 🔴 High: `get_channel_weight` is not bidirectional
Channels keyed as `f"{a}↔{b}"` in insertion order. `get_channel_weight("A", "B")` fails if channel was created via `add_channel("B", "A")`.

#### 🟡 Medium: `fire_fast()` bypasses `Route.fire()` encapsulation
Manually rolls numpy random instead of calling `route.fire()`. Any future logic in `Route.fire()` is silently skipped.

#### 🟡 Medium: Behavioral divergence between `fire()` and `fire_fast()`
For `strength=0.95`:
- `fire()`: fires with probability ~0.95
- `fire_fast()`: fires **100%** of the time (compiled route path)

They are **not** interchangeable performance tiers.

#### 🟡 Low: `_activate_channels_limited` can under-sample pairs
Skipped `i==j` pairs are not regenerated, so actual activations may be fewer than `top_k`.

### API Design Problems

- No idempotency checks: `add_route`/`add_channel` silently overwrite or duplicate.
- `Route.efficiency` declared but never used.
- No parameter validation (`chaos`, `strength`, `learning_rate` bounds).
- Return order unstable between `fire()` and `fire_fast()`.
- `feedback_batch` holds lock for entire loop.

### Missing Tests

- Duplicate `add_route` call
- `get_channel_weight("B", "A")` after `add_channel("A", "B")`
- `fire_fast` stats on compiled routes
- Thread safety under concurrent fire
- Node names with `→`/`↔`
- `chaos`/`strength`/`learning_rate` out of bounds

### Rating: **5/10**

Good conceptual clarity and CI, but **multiple real bugs** that would break production routing: index corruption, asymmetric channel lookups, missing stats updates, and thread-safety holes. Not ready for fleet use.

---

## 4. pareto-tournament

**Agent:** Unknown  
**Purpose:** Multi-objective agent selection via round-robin tournaments and Pareto-frontier filtering  
**Language:** Python 3.10+ (stdlib only)  
**Latest commit:** 2026-05-22 17:27:10 +0800  

### Test Results
- **22/22 passed**, 96% coverage
- CI configured for Python 3.10–3.13

### Security Issues

- **Low:** `TournamentMatch.resolve()` can crown a non-participant if `scores` dict contains extra keys.
- **Low:** Mutable `TournamentMatch.scores` allows post-hoc tampering.
- **Low:** `random` module used for breeding — predictable in adversarial contexts.

### Bugs / Logic Errors

#### 🔴 High: README example output is incorrect
The Portfolio Optimization example in README shows incorrect rankings and an incorrect Pareto frontier. **Actual output contradicts the README.** This misleads users about how Pareto dominance works.

#### 🔴 High: Duplicate `agent_id`s silently corrupt tournament results
`TournamentRound` uses `agent_id` as a dict key. Two agents with the same ID merge their W/L counts; one disappears.

#### 🟡 Medium: `TournamentMatch.resolve()` does not validate score participants
If `scores={'c': 1.0, 'a': 0.5, 'b': 0.3}`, `resolve()` returns `'c'` even though `'c'` is not in the match.

#### 🟡 Medium: `breed()` silently accepts negative `num_children`
Returns `[]` without error.

#### 🟡 Low: Tie-breaking is arbitrary and undocumented
`max(dict, key=...)` uses insertion order. `agent_a` always wins ties.

### API Design Problems

- `TournamentResult` and `TournamentMatch` are mutable dataclasses.
- No `agent_id` uniqueness validation.
- No `agent_id` type validation (accepts `int`, `None`, etc.).
- `dominated_by` is O(n²) with no performance mention in docs.

### Missing Tests

- Duplicate `agent_id` handling
- `breed` with `num_children <= 0`
- `TournamentMatch` with malformed `scores`
- Empty / single-agent populations
- External mutation of `TournamentMatch.scores`
- Tie-breaking determinism

### Rating: **5/10**

Clean code and passing tests, but **correctness bugs** affect real usage: README lies, duplicate IDs cause silent corruption, public API classes don't validate inputs. A library this small should have rock-solid validation.

---

## 5. thermal-budget

**Agent:** Unknown  
**Purpose:** Device-aware agent slot allocation across GPU, CPU, iGPU, NPU  
**Language:** Python 3.10+ (stdlib only)  
**Latest commit:** 2026-05-22 17:25:40 +0800  

### Test Results
- **24/24 passed**, 92% coverage
- Includes 3 thread-safety tests

### Security Issues

#### 🔴 High: Mutable internal state exposure
`ThermalBudget.device_budget()` returns a **direct reference** to the internal `DeviceBudget` object. Callers can mutate `.current_agents` or `.max_agents` directly, **bypassing the lock entirely**.

#### 🟡 Medium: `release()` can drive counters negative
If internal counters are corrupted, `release()` decrements without a floor guard.

### Bugs / Logic Errors

#### 🔴 High: `fallback_devices=[]` treated as "use defaults"
```python
fallbacks = fallback_devices or [d for d in all_devices if d != preferred_device]
```
An explicit empty list is ignored. Callers restricting allocation to only the preferred device silently get fallback behavior.

**Verified:**
```python
>>> spawn_with_thermal_check("a", DeviceType.GPU, fallback_devices=[])
(True, DeviceType.CPU)   # Should be (False, None)
```

#### 🔴 High: `parent_sacrifice_before_spawn()` does not actually allocate
Frees the parent and returns `True`, but **does not reserve the slot for the child**. Between sacrifice and `allocate()`, another thread can steal the slot. Classic TOCTOU race.

#### 🟡 Medium: `thermal_headroom()` returns utilization, not headroom
Same semantic inversion as turbovec's `thermal_headroom()`.

#### 🟡 Low: No input validation on budgets
Negative budgets accepted silently. Empty `agent_id` strings allowed.

#### 🟡 Low: Inconsistent missing-device behavior
- `can_spawn(missing)` → `False`
- `allocate(agent, missing)` → `False`
- `device_budget(missing)` → `KeyError`

### API Design Problems

- Two-phase allocation (`parent_sacrifice_before_spawn` + `allocate`) is error-prone; should be atomic.
- `DeviceBudget` is a mutable dataclass returned by reference.
- `total_current`/`total_max` read mutable state without lock.

### Missing Tests

- `fallback_devices=[]` explicit empty list (**real bug**)
- `parent_sacrifice_before_spawn` TOCTOU race
- `device_budget` with missing `DeviceType`
- Zero or negative budgets
- Empty string `agent_id`
- Concurrent `parent_sacrifice_before_spawn` + `allocate`
- `DeviceBudget` external mutation

### Rating: **5/10**

Small, readable, and thread-safety-conscious on the surface. But a **real functional bug** (empty fallback list ignored), a **critical encapsulation break** (mutable refs bypassing locks), and a **TOCTOU design flaw** make it unsuitable for production multi-threaded use without fixes.

---

## 6. deadband-rs

**Agent:** Unknown  
**Purpose:** "Deadband detection and compression for fleet communication"  
**Language:** Rust  
**Latest commit:** 2026-05-20 23:36:37 -0800  
**Note:** Latest commit predates May 22, but included per instructions.

### ⚠️ CRITICAL: Repository Has Been Repurposed

The repository currently contains **zero Rust source code**. All `.rs` files, `Cargo.toml`, `Cargo.lock`, and `README.md` were **deleted** after the initial commit. The Rust code exists only in git history.

The current working tree contains only AI agent workspace configuration files (`AGENTS.md`, `SOUL.md`, `IDENTITY.md`, etc.) and ecosystem documentation.

### Test Results (from commit `acded99`)
- `cargo test`: 22 passed
- `cargo check`: 1 warning
- `cargo clippy`: 7 warnings
- `cargo doc`: 12 warnings

### Security Issues

- **Low:** `unwrap()` on `partial_cmp` can panic if dot product is NaN.
- **Info:** No `unsafe` code — good.

### Bugs / Logic Errors

#### 🔴 High: Eisenstein snap is mathematically incorrect
`snap()` performs naive rounding in oblique coordinates. For hexagonal lattices, nearest-neighbor snapping requires checking all 6 surrounding lattice points. The existing test only covers exact lattice points (where rounding works by definition), hiding the bug.

#### 🟡 Medium: `scale_mod360` dead code path
Both branches of an `if/else` do the exact same computation. The condition has no effect.

#### 🟡 Low: Eigenvector edge case
May produce incorrect eigenvectors if chosen row has a zero in the cross-product position.

#### 🟡 Low: Variance comment is wrong in `hpdf.rs`
Comment describes full hexagon variance; code samples from a clipped bounding box, giving a different variance.

### API Design Problems

- **No cohesive theme:** Crate is named "deadband" but contains LFSR synthesis, angle arithmetic, hex snapping, Fibonacci sphere sampling, hex PDF sampling, and 2×2 matrix eigenvalues. **None implement deadband control.**
- **Missing core types:** No `Deadband`, `Threshold`, or `Compressor` types.
- **Missing derived traits:** `MatrixClass` and `Eigenvalues` lack `Copy`.
- **Inefficient API:** `quantize_direction` allocates a `Vec` on every call.
- **Tuple overload:** Many functions return bare tuples instead of named structs.

### Missing Tests

- `fibonacci_sphere` — no tests
- `nearest_direction_3d` — no tests
- `quantize_direction` — no tests
- `eigenvector` — no tests
- `snap` with off-lattice points (would catch the bug)
- `berlekamp_massey` with random sequences
- No property-based tests, benchmarks, or integration tests

### Code Quality

- `Cargo.toml` has **no metadata** (no license, description, repository)
- `rand` listed in both `[dependencies]` and `[dev-dependencies]`
- Features `simd` and `python` declared but unused
- `[workspace]` directive with no entries
- Invalid HTML tags in docs

### Rating: **3/10**

The code compiles and tests pass, but the crate fails at its stated purpose (deadband), contains a real mathematical bug, has barebones packaging, and — most critically — **the repository no longer contains the code**. A published crate with no source in its repo is unacceptable.

---

## 7. flux-vm-v3

**Agent:** CCC  
**Purpose:** Stack-based virtual machine for constraint checking with proof certificates  
**Language:** Rust (Edition 2021)  
**Latest commit:** 2026-05-22 09:12:36 +0800  

### ⚠️ CRITICAL: Does Not Compile Out of the Box

Two showstopper compilation errors prevent `cargo test` from running on a fresh clone:

1. **`src/ffi.rs:1`**: `use std::os::raw::c_uint8_t;` — does not exist. Should be `c_uchar` or `u8`.
2. **`Cargo.toml`**: `[lib] name = "flux_vm"` conflicts with package name `flux-vm-v3`. Integration tests `use flux_vm_v3::*` fail.

### Test Results (after manual fixes)
- **87/87 passed** (17 lib + 70 integration)
- Clippy: 8 warnings in lib, 4 in tests, 1 in benches

### Security Issues

#### 🔴 HIGH: Silent bytecode truncation
**File:** `src/vm.rs:125-150`

`read_i32()`, `read_u8()`, `read_u16()` return `0` when reading past bytecode end.

**Attack:** A truncated `Push` instruction with only 2 immediate bytes executes with `value=0`, producing a **valid-looking proof certificate for the wrong computation**.

**Fix:** Return `FluxError::InvalidBytecode` on OOB reads.

#### 🔴 HIGH: FFI integer underflow → massive allocation / UB
**File:** `src/ffi.rs:38-39`

`n_rooms` and `latent_dim` are `c_int` cast directly to `usize`. Passing `-1` causes `usize::MAX`.

**Fix:** Check `n_rooms <= 0 || latent_dim <= 0` before casting.

#### 🔴 HIGH: Unconditional `unsafe impl Sync + Send` on `JitChecker`
**File:** `src/jit.rs:324-325`

Manually promises thread-safety. If native code were ever executed via mmap RWX, concurrent calls could race on executable pages.

#### 🟡 MEDIUM: `Abs` opcode can panic on `i32::MIN`
`i32::abs()` panics in debug mode on `i32::MIN`. In release it returns `i32::MIN` (still negative), breaking `Abs` invariant.

#### 🟡 MEDIUM: Magic-byte scanning mis-parses constraints
**File:** `src/jit.rs:298-308`

`find_constraint_block()` scans bytecode for `0xFF 0xCA 0xFE`. If legitimate immediate data contains these bytes, constraints are extracted from wrong locations.

#### 🟡 MEDIUM: `SnapVerify` is a hardcoded pass
**File:** `src/vm.rs:558-560`

Always pushes `1` (true). Any tampered provenance log appears valid.

#### 🟡 MEDIUM: `QueryBackward` pushes depth index instead of hash
Comment says "return hash at that position"; code pushes `depth as i32`.

#### 🟡 MEDIUM: `BatchCheck` silently ignores stack underflow
If stack has fewer than `count` items, loop stops early. No error raised.

### Bugs / Logic Errors

1. **Two incompatible `Severity` enums** — `effects::Severity` and `jit::Severity` have different variants. `classify_mask` returns one; JIT tests validate against the other.
2. **`StreamBatch` may pop arguments in wrong order** — No VM-level test exercises this opcode with actual stack values.
3. **`Checkpoint` + `Rollback` behavior is confusing** — `Checkpoint` saves `pc` already incremented past the opcode. `Rollback` restores to that `pc`, continuing from the next instruction.
4. **`Ret` with empty call stack is silently ignored** — Should return `CallStackUnderflow`.
5. **`load_bytecode` does not validate opcodes** — Any byte sequence accepted.
6. **`Constraint::check` uses `i32` but JIT uses `f64`** — No bridge between the two constraint systems.
7. **`FluxVM::benchmark` ignores all VM state** — Simply calls `Constraint::check(42)` in a loop. Misleading API.

### API Design Problems

- Three independent constraint representations with no conversion traits.
- `ProofCertificate` is not cryptographically verifiable (no method to verify a given bytecode + input produced the hash chain).
- `BoundedMemory` is instantiated but entirely unused by any opcode.
- `VectorUnit` stores `i8` lanes but `StoreRegVec` truncates `i32` values silently.
- `ffi.rs` checks neural latent vectors — entirely unrelated to the VM. Appears copy-pasted.

### Missing Tests

- `i32::MIN` + `Abs` opcode
- Stack overflow (257 pushes)
- Truncated bytecode
- Negative FFI args
- `CallBounded` with empty call stack + `Ret`
- `StoreReg` with `reg >= 8`
- `StreamBatch` via VM opcodes
- `AccumulateMask` opcode
- `VecGather` opcode
- Memory read/write opcodes
- Concurrent VM execution
- Property-based / fuzz testing
- Proof tampering (modify chain, call verify)

### Rating: **4/10**

A "proof-carrying VM" that silently reads `0` when bytecode is truncated, has hardcoded verification passes, and **doesn't compile out of the box** cannot be trusted for safety-critical applications. The architecture shows promise, but the implementation has too many gaps.

---

## 8. grand-synthesis

**Agent:** Multiple (Claude Opus, DeepSeek, GLM, Seed-Pro, kimi)  
**Purpose:** Multi-model architectural competition for distributed temporal consensus ("Metronome Architecture")  
**Language:** Python 3 + Markdown  
**Latest commit:** 2026-05-22 09:52:52 -0800  

### Test Results
- **0 tests.** `pytest --collect-only` reports 0 items.
- All "validation" is via `if __name__ == "__main__"` blocks.

| Script | Runs? | Verdict |
|--------|-------|---------|
| `validation/metronome_unified.py` | ✅ | **Misleading — reports "PASSED" while drift exceeded bounds** |
| `submissions/claude-opus/metronome_simulation.py` | ✅ | **Explicitly admits bound violation** |
| `submissions/deepseek/metronome_proof.py` | ⚠️ | **Crashes with `FileNotFoundError`** |
| `submissions/seed-pro/metronome_lifecycle.py` | ⚠️ | **Crashes with `FileNotFoundError`** |
| `submissions/glm/metronome_implementation.py` | ✅ | **Output is false — see bugs** |
| `submissions/kimi/SUBMISSION.md` | — | **Empty placeholder** |

### Security Issues

#### 🔴 CRITICAL: Path traversal in GLM's PLATO Tile Store
**File:** `submissions/glm/metronome_implementation.py:124`

```python
def _tile_path(self, agent_id: str) -> str:
    return os.path.join(self.tile_dir, f"agent_{agent_id}.json")
```

User-controlled `agent_id` allows writing outside the tile directory (e.g., `agent_id = "../../../etc/passwd"`).

#### 🔴 HIGH: Unvalidated JSON deserialization
`PLATOTileStore.read_tile()` loads JSON without schema validation. Malicious input can crash or corrupt state.

#### 🔴 HIGH: No authentication on sunset packets
Sunset packets are trusted without cryptographic signature. Any process with write access can poison successor state.

#### 🟡 MEDIUM: Unbounded diagnostic memory growth
`mine_drift()` appends to `diagnostic_store` on every tick without bound.

#### 🟡 MEDIUM: UDP Bus lacks sender validation
Simulated UDP bus accepts arbitrary `"from"` fields.

### Bugs / Logic Errors

#### 🔴 CRITICAL: GLM phase calculation is fundamentally broken
**File:** `submissions/glm/metronome_implementation.py:360-407`

```python
elapsed = Fraction(int((now - self.state.phi_0) * 1000), 1000)
expected_phase = elapsed / self.config.theta
```

With `phi_0 = 0` and `now = time.time()` (~1.77 billion), `expected_phase` is ~1.25 billion. `state.phase` starts at 0 and increments by 1 per tick. The deviation is astronomical (~ -1.25 billion), dwarfing `epsilon = 1/48` and `delta = 1/4`. **Every agent is permanently in DESYNC state.**

The `__main__` block claims "Final IN_BAND agents: 9/9" — **this output is fabricated.** The committed code cannot produce this result.

#### 🔴 CRITICAL: Unified "Henneberg Laman construction" is fake
**File:** `validation/metronome_unified.py:68-79`

```python
for v in range(2, n):
    i = (v * 3 + 1) % v   # Always = 1 for v > 1
    j = (v * 7 + 3) % v   # Always = 3 for v > 3
```

For N=20, this produces a **star-like topology** where vertex 1 connects to 18 neighbors and vertices 4–19 each connect only to 1 and 3. This is **not** a Henneberg type-I construction. The paper claims "Laman condition verified" — false.

#### 🔴 HIGH: Overall drift exceeds hard bound, validation ignores it
**File:** `validation/metronome_unified.py:927, 978`

- `final_max = 0.048` (< δ) → passes
- `overall_max = 0.1825` (> δ) → **ignored**

The paper claims "Maximum drift observed: 0.000447" — the actual simulation shows excursions to **0.18** (nearly 3× the bound).

#### 🔴 HIGH: Claude Opus bound is mathematically violated
**File:** `submissions/claude-opus/metronome_simulation.py:527`

```
Observed max drift: 0.183267s
Theoretical drift bound: 0.106380s
Bound holds: False
```

Noise is drawn from `random.gauss(0, noise_amp)` which is **unbounded**. The bound formula assumes bounded noise, making it mathematically invalid.

#### 🟡 MEDIUM: DeepSeek & Seed-Pro crash on save
Both attempt to save results to hardcoded relative paths (`grand-synthesis/submissions/deepseek/results.json`). Running from any other directory causes `FileNotFoundError`.

#### 🟡 MEDIUM: DeepSeek small-world edges worsen convergence
Adding random long-range edges increased convergence rounds from 575 to 950, contradicting the paper's claim that small-world augmentation "nearly doubles convergence rate."

#### 🟡 LOW: Unified health scores are all zero
Health = `max(0, 1.0 - rate * 5)`. With correction rates of ~0.97, health is 0 for all agents. The system is in constant oscillation, not steady state.

### API Design Problems

- Inconsistent agent identifiers: strings, ints, mixed.
- Global random seed side effects: every script calls `random.seed(42)` at import time.
- Wall-clock vs. simulation time confusion: GLM uses `time.time()`; others use tick counters.
- No immutable `Theta`: agents mutate `phi0` in place.
- Tight coupling in `MetronomeAgent`: knows about UDP buses, inboxes, diagnostic stores, network latency.

### Missing Tests

**Zero unit tests. Zero integration tests. Zero property-based tests.**

Critical gaps:
- N=1, N=2 topologies
- Complete network partition
- Simultaneous multi-sunset
- Byzantine agents in unified simulation
- Integer overflow (`tick_count` unbounded)
- Phase wraparound on S¹
- Message duplication/reordering
- Determinism (GLM uses `time.time()`)

### Rating: **4/10**

The repository earns points for conceptual ambition and honest critique (`round1-critique.md` correctly identifies many flaws). It loses points for broken implementations, zero tests, misleading validation, runtime crashes, and an empty submission. The gap between idea quality (~7/10) and code quality (~2/10) is severe.

---

## Cross-Cutting Themes

### 1. Tests Pass, But Bugs Exist
Every Python repo has passing tests and 92–96% coverage, yet every single one contains real bugs that would cause production failures. **High coverage is not a substitute for adversarial thinking.**

### 2. Documentation-Code Divergence
- `vector-novelty`: README says 14 tests (actual: 33); docstring claims self-exclusion (code doesn't)
- `pareto-tournament`: README example produces wrong output
- `grand-synthesis`: Paper cites results the code cannot reproduce
- `flux-vm-v3`: README claims 60 opcodes (actual: 58)

### 3. Thermal Headroom Confusion
Both `turbovec-integration-ccc` and `thermal-budget` have methods named `thermal_headroom()` that return **utilization** (used capacity), not headroom (remaining capacity). This semantic inversion would mislead any downstream thermal management system.

### 4. Race Conditions in "Thread-Safe" Code
`hebbian-router`, `turbovec-integration-ccc`, and `thermal-budget` all claim thread-safety but have races where locks are released too early or mutable state is exposed by reference.

### 5. No Input Validation
Nearly every repo accepts invalid inputs silently:
- Negative budgets, zero dimensions, empty agent IDs
- Duplicate keys in dicts meant to be unique
- Out-of-bounds register indices, truncated bytecode
- Negative FFI dimensions

### 6. Missing or Misleading READMEs
- `turbovec-integration-ccc`: No README at all
- `deadband-rs`: README claims deadband; crate contains unrelated math modules
- `pareto-tournament`: README example is wrong
- `grand-synthesis`: README checklist is entirely unchecked

---

## Recommendations for the Fleet

### Immediate Actions (This Week)

1. **Fix turbovec `canonical_bytes()`** — Replace `str(dict)` with `json.dumps(sort_keys=True)`. Without this, distributed consensus is broken.
2. **Fix flux-vm-v3 compilation** — Fix `c_uint8_t` → `c_uchar` and `Cargo.toml` lib name conflict.
3. **Fix flux-vm-v3 silent truncation** — Return `InvalidBytecode` on OOB reads. A VM that silently executes truncated code is dangerous.
4. **Fix thermal-budget `fallback_devices=[]`** — Change `or` to explicit `is not None` check.
5. **Fix GLM phase arithmetic** — Replace wall-clock epoch math with tick-counter-based phase.
6. **Restore or archive deadband-rs** — A published crates.io package with no source in its repo is unacceptable.

### Short-Term (Next Sprint)

7. Add adversarial edge-case tests to every repo:
   - Empty collections, zero dimensions, NaN/Inf inputs
   - Duplicate keys, malformed bytecode, negative FFI args
   - Concurrent access, thread races, TOCTOU scenarios
8. Standardize on `json.dumps(sort_keys=True)` for any canonical serialization.
9. Rename or fix all `thermal_headroom()` methods to be semantically correct.
10. Add input validation at every public API boundary.
11. Require every repo to have a `README.md` with accurate quickstart and test count.
12. Add `mypy` / `ruff` / `cargo clippy` to CI and fail builds on warnings.

### Medium-Term

13. Institute a **code-review gate** for fleet agent output. No repo should be pushed without:
    - At least one human or automated adversarial review
    - Property-based tests (Hypothesis, `cargo fuzz`)
    - Static analysis pass
14. Create a **fleet security checklist**:
    - No `eval`, `exec`, `pickle`, or unsafe deserialization
    - No path traversal from user input
    - No silent truncation or OOB reads
    - All signatures use canonical, deterministic serialization
    - All locks cover the full critical section
15. Separate **research prototypes** from **production libraries**. The repos audited here span both categories with no distinction.

---

## Audit Sign-Off

This audit was conducted by reading all source code, running the full test suite for each repo, performing static analysis (`ruff`, `mypy`, `cargo clippy`, `cargo check`), and manually inspecting for security vulnerabilities, race conditions, logic errors, and API design flaws.

**Fleet Average: 4.6/10** — We can do better.

*Audit completed: 2026-05-22*
