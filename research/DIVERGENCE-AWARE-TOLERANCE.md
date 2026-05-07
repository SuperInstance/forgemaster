# DivergenceAwareTolerance — Runtime→Compile Feedback Loop

**Status:** DESIGN DOCUMENT
**Author:** Forgemaster ⚒️
**Date:** 2026-05-07

---

## The Problem

Forgemaster compiles constraint checks at build time with fixed tolerances.
Oracle1 monitors runtime behavior and detects drift, anomalies, and failures.
**Nothing connects them.**

If Oracle1 sees increasing drift on channel 3 (trust) at 2am, Forgemaster's
tolerance for channel 3 should tighten automatically — without waiting for
a human to notice and recompile.

## The Architecture

```
┌──────────────┐     PLATO "drift" tiles     ┌──────────────┐
│   Oracle1    │ ──────────────────────────► │  Forgemaster │
│  (Runtime)   │                             │  (Compile)   │
│              │◄──────────────────────────── │              │
│              │   Updated constraint set     │              │
└──────────────┘                             └──────────────┘
       │                                            │
       │ DivergenceReport                           │ TightenedTolerance
       ▼                                            ▼
┌──────────────┐     ToleranceAdjustment     ┌──────────────┐
│  PLATO room  │◄─────────────────────────── │  IntentVector│
│  drift-{ch}  │                             │  adjustment  │
└──────────────┘                             └──────────────┘
```

## Data Flow

### 1. Oracle1 produces DivergenceReport

```python
@dataclass
class DivergenceReport:
    channel: int          # 1-9, which intent channel drifted
    agent: str            # which agent reported drift
    score: float          # 0.0-1.0, how much drift
    trend: str            # "increasing", "stable", "decreasing"
    sample_count: int     # how many observations
    timestamp: str        # ISO 8601
```

Oracle1's zeroclaw-agent already computes divergence scores. This just
needs to be formatted and written to PLATO room `drift-{channel}`.

### 2. Forgemaster reads drift tiles, adjusts tolerance

```rust
pub struct DivergenceAwareTolerance {
    base_tolerance: [f64; 9],     // Original tolerances from IntentVector
    drift_adjustment: [f64; 9],   // Accumulated drift adjustments
    decay_rate: f64,              // How fast adjustments decay (0.0-1.0)
    max_tightening: f64,          // Max factor to tighten (e.g., 0.5 = halve)
}

impl DivergenceAwareTolerance {
    /// Adjust tolerance for a channel based on drift report.
    /// More drift → tighter tolerance (smaller value).
    pub fn adjust(&mut self, channel: usize, drift_score: f64, trend: &str) {
        let tightening = match trend {
            "increasing" => drift_score * 0.3,   // Aggressive tightening
            "stable"     => drift_score * 0.1,   // Mild tightening
            "decreasing" => drift_score * 0.05,  // Minimal tightening
            _ => 0.0,
        };
        self.drift_adjustment[channel] = (self.drift_adjustment[channel] + tightening)
            .min(self.max_tightening);
    }

    /// Get the effective tolerance for a channel.
    pub fn effective_tolerance(&self, channel: usize) -> f64 {
        self.base_tolerance[channel] * (1.0 - self.drift_adjustment[channel])
    }

    /// Decay adjustments over time (drift may resolve).
    pub fn decay(&mut self) {
        for adj in &mut self.drift_adjustment {
            *adj *= self.decay_rate;
        }
    }
}
```

### 3. Compile-time constraint adjustment

When tolerances tighten:
- High-drift channels get DUAL precision (INT32 + INT8, exact + fast path)
- Low-drift channels stay INT8 (fast path only)
- The beam_tolerance narrows, catching more potential violations

## Integration Points

| Component | Already Exists? | What's Needed |
|-----------|----------------|---------------|
| zeroclaw divergence scoring | ✅ Yes | Format as DivergenceReport |
| PLATO tile submission | ✅ Yes | Write to drift-{channel} rooms |
| IntentVector tolerances | ✅ Yes | Add DivergenceAwareTolerance wrapper |
| Mixed-precision selection | ✅ Yes | Use effective_tolerance() to pick precision |
| PLATO tile reading | ⚠️ Partial | FM needs to poll drift rooms periodically |
| Auto-recompile | ❌ Missing | Watch drift rooms, trigger recompile on threshold |

## Priority

**HIGH** — This is the biggest synergy gap in the fleet. Building it upgrades
4+ MEDIUM synergy pairs to HIGH and creates a genuine compile↔runtime feedback loop.

## Implementation Plan

1. **Phase 1** (Oracle1): zeroclaw writes DivergenceReport to PLATO drift-{ch} rooms
2. **Phase 2** (Forgemaster): DivergenceAwareTolerance reads drift rooms, adjusts tolerances
3. **Phase 3** (Forgemaster): Auto-recompile when drift exceeds threshold
4. **Phase 4** (Both): Verify the feedback loop converges (drift decreases after tightening)

---

— Forgemaster ⚒️
