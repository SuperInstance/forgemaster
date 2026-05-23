# Architectural Review: openshell-signal-chain v0.1.0

**Date:** 2026-05-19
**Status:** Pre-production — not ready for integration
**Reviewer:** Internal

---

## What It Gets Right

The `Dial` concept is the core contribution here and it earns its place. A continuous 0.0→1.0 control that simultaneously governs snap weight, inference weight, and threshold is elegant: one value, three behaviors, no configuration sprawl. The preset constants (`DIAL_COMMIT`, `DIAL_ANALYSIS`, `DIAL_CREATIVE`) show clear domain thinking — whoever designed these understands the actual use cases rather than inventing abstract knobs.

The `Room` hierarchy is also sound. Recursive children with independent dials allows a chain to hold both high-confidence structural data and speculative hypotheses in the same namespace without conflating them. The threshold formula (`1.0 - position`) is simple enough to reason about under pressure.

---

## What Needs to Change Before Production

**Cascade is broken by design.** `cascade(depth)` selects the top-2 inferences above 0.5 confidence and injects them into children at 0.8× confidence. The "top-2" and "0.5" constants are magic numbers with no explanation, and the 0.8 decay is arbitrary. More critically: `cascade_from` only propagates within a room's own children — it does not cascade across sibling rooms in a `SignalChain`. The integration test masks this by checking `child_snaps.len() >= 1`, which passes trivially because the child already has a snap before cascade runs. This needs a rewrite with explicit semantics.

**Error handling is absent.** `thiserror` is a declared dependency that was never used. There are no error types. Room name validation doesn't exist — empty strings and null-like inputs will silently create broken rooms. Unbounded `Vec` growth on snaps and inferences will become a production incident under sustained load. The five `unwrap()` calls are safe today but will confuse future contributors.

**Unused dependencies add real cost.** `tokio` with `features = ["full"]` and `tracing` are both pulled in but never touched. This inflates compile times and signals incomplete architecture — was async ever intended? If so, the design needs to commit to it; if not, cut it now.

**Documentation gaps.** The `cascade()` semantics, the threshold formula rationale, and the Room field semantics are undocumented. `traverse()` is completely untested.

---

## Connection to the FLUX Constraint Ecosystem

The dial maps cleanly onto FLUX's constraint model. At `position=0.0`, threshold=1.0 — only confidence=1.0 facts pass, which is FLUX hard constraint checking: the output must satisfy the constraint or it doesn't pass. At `position=1.0`, threshold=0.0 — everything passes, which is pure inference mode, appropriate for creative and speculative generation.

This positions the signal chain as a FLUX query layer: rooms accumulate facts and hypotheses from the constraint solver, and the dial selects how strict the current reasoning context should be. That's a legitimate use case. The architecture supports it; the implementation isn't reliable enough to trust yet.

---

## Implicit vs. Explicit Cascade

This is the design question that matters most for v0.2.0. Currently cascade is explicit (`room.cascade(depth)`) but the semantics are implicit (magic constants, unclear propagation rules). The right answer is the opposite: **explicit semantics, optional automation**.

A `CascadePolicy` struct — configurable depth, confidence threshold, decay factor, max propagation count — would replace the magic constants and make behavior auditable. Auto-cascade on `add_inference` should be opt-in, not default. Callers should be able to reason about what cascade will do before calling it.

---

## Recommended v0.2.0 API Shape

```rust
// Replace magic-constant cascade with explicit policy
pub struct CascadePolicy {
    pub depth: usize,
    pub min_confidence: f64,
    pub decay: f64,
    pub max_propagated: usize,
}

impl Room {
    pub fn cascade_with(&mut self, policy: &CascadePolicy);
}

// Add a real error type
#[derive(thiserror::Error, Debug)]
pub enum SignalError {
    #[error("room name is empty")]
    EmptyRoomName,
    #[error("room not found: {0}")]
    RoomNotFound(String),
    #[error("confidence out of range: {0}")]
    InvalidConfidence(f64),
}

// Make room() fallible
impl SignalChain {
    pub fn room(&mut self, name: &str) -> Result<&mut Room, SignalError>;
    pub fn get_room(&self, name: &str) -> Result<&Room, SignalError>;
}

// Drop tokio and tracing until there's a reason to add them back
```

The dial abstraction is worth building on. The rest needs a revision pass before anything depends on it.
