# Beta Test: openshell-signal-chain

**Tester:** Forgemaster ⚒️  
**Date:** 2026-05-19  
**Crate version:** 0.1.0  
**Verdict:** Clean architecture, needs polish before production

---

## Test 1: Build ✅

```
cargo check -p openshell-signal-chain  → COMPILES (1 warning: unused variable `name` in room.rs:121)
cargo test -p openshell-signal-chain   → 14/14 PASS
  - 8 unit tests
  - 5 integration tests
  - 1 doc test
```

**Build time:** ~8s (clean). Zero dependency surprises.

The one warning is cosmetic — `name` in the cascade loop isn't used. Trivial fix: `_name`.

---

## Test 2: API Discoverability — 7/10

**Can you understand what this crate does in 30 seconds?** Yes. The lib.rs doc header nails it:

> Every intelligent system needs a dial between hard-snapped algorithms and soft-inferenced models.

The four primitives are clear: `Dial`, `Snap`, `Inference`, `Room`. The example in lib.rs compiles and shows the workflow.

**Main types:**
1. `Dial` — position on the hard↔soft spectrum
2. `Snap` — hard-locked fact with confidence
3. `Inference` — soft extrapolation with confidence
4. `Room` — fact-space containing snaps, inferences, children
5. `SignalChain` — collection of rooms with global dial

**First function you'd call:** `SignalChain::new("name")` → `.room("name")` → `.add_snap(...)` / `.add_inference(...)`. Obvious.

**What's missing:**
- No type alias or explainer for what `serde_json::Value` represents in context. Newcomers see JSON blobs without schema guidance.
- `Dial` field is called `position` but `Room` field is called `dialect` — confusing naming inconsistency. Why isn't it `dial_position` everywhere?

---

## Test 3: README — 4/10

**Crate-level README:** ❌ NONE. This is a real gap. There's no `crates/openshell-signal-chain/README.md`.

**OpenShell main README:** Does explain signal-chain well. Has the dial diagram, snap/inference explanation, and a code example. Good overview.

**But:** A Rust developer doing `cargo add openshell-signal-chain` lands on docs.rs, which renders lib.rs docs only. No README means the landing page is bare. The main OpenShell README won't be there.

**Finding:** Add a crate README. Even a minimal one with the dial diagram and a 10-line example would close this gap.

---

## Test 4: Documentation — 6/10

**Module-level docs:** ✅ Every module has `//!` header docs. Good.

**Public types:** All have doc comments. `Dial`, `Snap`, `Inference`, `Room`, `SignalChain` — all documented.

**Public methods:** Mostly documented, but inconsistently:
- ✅ `Dial::new()` — documented
- ✅ `Room::query()` — documented ("Returns snaps always + inferences that pass threshold")
- ❌ `Room::cascade()` — NO doc comment. What does `depth` mean? What gets cascaded?
- ❌ `Room::query_snaps()` — NO doc comment
- ❌ `Room::query_inferences()` — NO doc comment
- ❌ `Room::add_absolute()` — NO doc comment
- ❌ `Snap::absolute()` — NO doc comment
- ❌ `Inference::likely()` — NO doc comment
- ❌ `Inference::speculative()` — NO doc comment
- ❌ `SignalChain::traverse()` — NO doc comment. What order? What if a name doesn't exist?
- ❌ `SignalChain::cascade_from()` — NO doc comment

**Preset constants:** DIAL_FORMAL, DIAL_BATHY, etc. — all have doc comments. ✅

**Doc tests:** Only 1 (the lib.rs example). The type-level examples in Dial are just tests, not doc examples.

**Finding:** ~10 public methods lack doc comments. For a crate with 5 types and ~25 methods, that's a 40% gap.

---

## Test 5: Examples — 2/10

**Runnable examples directory:** ❌ NONE. `examples/` does not exist.

The lib.rs has one inline doc example that compiles. That's it.

**The integration tests serve as de facto examples** — they show real workflows. But they're in `tests/`, not `examples/`.

**Finding:** Add an `examples/` directory with at least:
1. `basic.rs` — create chain, add room, add snap + inference, query at two dials
2. `cascade.rs` — parent→child cascade demo
3. `fleet.rs` — realistic multi-room fleet operations

---

## Test 6: The Dial Concept — 8/10

The hard/soft spectrum is immediately intuitive. The preset constants are excellent:

```rust
DIAL_FORMAL    = 0.0  // theorem provers
DIAL_BATHY     = 0.1  // sonar data
DIAL_COMMIT    = 0.05 // build logs
DIAL_ANALYSIS  = 0.4  // reasoning with anchors
DIAL_REVIEW    = 0.5  // equal weight
DIAL_EXTRAPOLATE = 0.7 // hypothesis gen
DIAL_CREATIVE  = 0.9  // story gen
DIAL_EXPLORATORY = 1.0 // pure inference
```

The `accepts_inference()` method makes threshold logic transparent. `snap_weight()` / `inference_weight()` give clear weight functions.

**Can you use this without reading source?** Yes, from the lib.rs example alone. The API is:

```rust
let room = chain.room("name");
room.add_snap(json!({...}), 1.0);
room.add_inference(json!({...}), 0.7);
let results = room.query(Dial::new(0.5));
```

**Nit:** `Room.dialect` is a `Dial`, but the word "dialect" doesn't map to "dial position". Why not `room.dial` or `room.dial_position`? This is a naming consistency issue.

---

## Test 7: Edge Cases — 5/10

### dial = 0.0 (hard)
`Dial::new(0.0)` → `position: 0.0`. `inference_threshold() = 1.0`. Only confidence=1.0 inferences pass. Snaps always returned. ✅ Correct.

### dial = 1.0 (soft)
`Dial::new(1.0)` → `position: 1.0`. `inference_threshold() = 0.0`. All inferences pass. ✅ Correct.

### dial = -0.5
`Dial::new(-0.5)` → **clamped to 0.0**. ✅ Correct, but SILENT. No error, no log. A user passing -0.5 won't know it was clamped. **Finding:** At minimum, log a warning when clamping occurs.

### dial = 1.5
Same as above — clamped to 1.0, silently. **Finding:** Same.

### Empty room
`Room::new("empty").query(Dial::new(0.5))` → returns `vec![]`. ✅ Correct, no panic.

### Room with 1000 snaps
No pagination, no limits. `query()` returns all snaps + filtered inferences as one Vec. For 1000 snaps this is fine. For 1M snaps, it's a problem. But that's a v2 concern.

### Cascade with circular references
`cascade()` doesn't detect cycles. If room A has child B, and B has child A, it'll stack overflow at `child.cascade(depth - 1)`. The `depth` parameter provides some protection, but:
- `cascade(usize::MAX)` = stack overflow guaranteed if there's any cycle
- No cycle detection, no max depth guard

**Finding:** Add a cycle guard or document that callers must ensure DAG structure.

### confidence = 0.0
`Snap::new(json!({...}), 0.0, 0.5)` → confidence clamped to 0.0. The snap exists but is meaningless. Room.query() returns it regardless of confidence — snaps are always included. **Is this correct?** A snap with confidence 0.0 is still returned as a "fact"? This is a design question, not a bug.

**Finding:** Should `query()` filter snaps by confidence too? At minimum, document that snaps are ALWAYS returned regardless of confidence.

---

## Test 8: Integration Test

I wrote and ran a real workflow test:

```rust
use openshell_signal_chain::{Dial, Room, SignalChain, DIAL_FORMAL, DIAL_ANALYSIS};

#[test]
fn test_fleet_workflow() {
    // Create chain for fleet ops
    let mut chain = SignalChain::new("cocapn-fleet");
    
    // Room: constraint checking (hard)
    let constraint_room = chain.room_with_dial("constraints", DIAL_FORMAL);
    constraint_room.add_absolute(serde_json::json!({
        "rule": "no_drift_beyond_0.01",
        "type": "flux_constraint"
    }));
    
    // Room: sensor data
    let sensor_room = chain.room("sensors");
    sensor_room.add_snap(serde_json::json!({
        "sensor": "bathy-1",
        "depth": 87.2,
        "lat": 45.3
    }), 1.0);
    sensor_room.add_inference(serde_json::json!({
        "hypothesis": "anomaly at depth 90m"
    }), 0.6);
    
    // Room: analysis (soft-ish)
    let analysis_room = chain.room_with_dial("analysis", DIAL_ANALYSIS);
    analysis_room.add_inference(serde_json::json!({
        "pattern": "drift_detected",
        "magnitude": 0.003
    }), 0.75);
    
    // Query at formal level — only snaps + high-confidence inferences
    let formal = chain.query_all(DIAL_FORMAL);
    assert_eq!(formal.len(), 3); // 3 rooms
    let constraint_results = &formal["constraints"];
    assert_eq!(constraint_results.len(), 1); // 1 snap, 0 inferences pass threshold 1.0
    
    // Query at analysis level — snaps + inferences >= 0.6
    let analysis = chain.query_all(DIAL_ANALYSIS);
    let sensor_results = &analysis["sensors"];
    assert!(sensor_results.len() >= 2); // snap + inference at 0.6 passes threshold 0.6
    
    // Read dial positions
    assert_eq!(chain.get_room("constraints").unwrap().dialect.position, 0.0);
    assert_eq!(chain.get_room("analysis").unwrap().dialect.position, 0.4);
}
```

**Result:** This compiles and passes. The API is workable for real workflows.

**Friction points:**
1. `query_all` returns `HashMap<String, Vec<Value>>` — you lose type information immediately. Everything is JSON.
2. No way to distinguish snaps from inferences in query results (they're all `serde_json::Value`). You can't tell which items are facts vs hypotheses.
3. No filtering, no pagination, no ordering by confidence. Just a flat Vec.

---

## Test 9: Scores

| Category | Score | Notes |
|----------|:-----:|-------|
| README clarity | **4/10** | No crate README. Main repo README is good. |
| API discoverability | **7/10** | Clean API, intuitive flow. Naming inconsistency (dialect vs dial). |
| Documentation quality | **6/10** | Module docs good. ~40% of public methods undocumented. |
| Code quality | **8/10** | Clean, readable, well-structured. 1 warning. Unused `tokio` dep. |
| Would use in production | **5/10** | Not yet. Missing: error handling (no Error type, no Result), no validation, no persistence. |
| Trust level | **7/10** | Solid foundation. No unsafe, no unwrap in non-test code. Clamping is safe. |
| Integration with OpenShell | **6/10** | Standalone crate. No actual integration with sandbox or policy enforcement yet. |

**Overall: 6.1/10**

---

## Test 10: The ONE Fix

**Add a `SignalChainError` enum and make fallible methods return `Result`.**

Right now everything silently succeeds or clamps. `cascade()` can stack overflow. `room()` creates rooms silently on access (HashMap entry pattern). There's no way to distinguish "room not found" from "room is empty" because `room()` auto-creates.

```rust
// Current: silently creates room if missing
pub fn room(&mut self, name: &str) -> &mut Room

// Better: explicit creation vs access
pub fn create_room(&mut self, name: &str) -> &mut Room
pub fn get_room(&self, name: &str) -> Option<&Room>  // already exists
pub fn get_room_mut(&mut self, name: &str) -> Option<&mut Room>  // missing!
```

The crate is a solid foundation. The dial concept is genuinely elegant — the spectrum from formal to exploratory with threshold-gated inference is a real contribution. But for production use, it needs error handling, documentation gaps closed, a crate README, and examples.

---

## Bonus Findings

1. **Unused dependency:** `tokio` (with `full` features) is declared but never used. No async code anywhere. Remove it — it's pulling in unnecessary compile time and binary size.

2. **Unused dependency:** `tracing` is declared but no tracing calls exist. Either add instrumentation or remove the dep.

3. **Unused dependency:** `thiserror` is declared but no error types exist. Remove until error handling is added.

4. **Cascade test is misleading:** The integration test `test_cascade` passes because the child already has a snap (`child_snaps.len() >= 1` is true from the pre-existing snap), NOT because cascade actually worked. The cascade operates on `Room.children` (the nested HashMap), but the test adds "child" as a sibling room in the chain, not as a child of "parent". The cascade does nothing, test passes anyway. This is a **false positive**.

5. **`query()` returns mixed types:** Snaps and inferences both become `serde_json::Value`. There's no way to tell which is which in the result. Consider returning a tagged enum or separate vecs.

6. **No `Serialize`/`Deserialize` round-trip tests:** All types derive Serialize/Deserialize but there are no tests for JSON round-tripping.

7. **`dialect` naming:** Inconsistent — `Dial` type has `position`, `Room` has `dialect` (a `Dial`). Should be consistent: either both `dial` or both `position`.
