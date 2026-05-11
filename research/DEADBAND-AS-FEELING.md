# Deadband as the Feeling of Precision

**Origin:** Casey Digennaro, 2026-05-11

> "The snaps in time let a reading be known when it should be perfect and the geometry is t-minus to that perfect theoretical perfect snapping point on their simulated spline where the deadband reading can be lowest for feeling the precision."

---

## The Core Insight

The deadband is not a static tolerance band. It has a **shape** — a dynamic width that varies as the agent moves through its predicted trajectory (spline).

At the **snap point**, the deadband reaches its **minimum width**. That minimum is the *feeling* of precision. T-minus is the geometric distance to that minimum.

```
Deadband width
    ^
    |  ╲              ╱
    |   ╲            ╱
    |    ╲          ╱
    |     ╲        ╱
    |      ╲      ╱
    |       ╲    ╱
    |        ╲  ╱  ← deadband narrows toward snap
    |         ╲╱
    |          V ← SNAP POINT: deadband = minimum = feeling of precision
    |
    +──────────────────────> Time / Agent trajectory
         T-3  T-2  T-1  T=0
```

## Formal Definition

### The Deadband Funnel

For an agent A following predicted spline S(t), define:

**Deadband width at time t:**
```
δ(t) = max acceptable deviation from S(t) before constraint violation
```

**Snap point t\*:**
```
t* = argmin_t δ(t)
```

The point where the deadband is narrowest — where precision matters most.

**T-minus:**
```
T-minus(t) = |t - t*|
```

The geometric distance to maximum precision.

**Precision feeling:**
```
Φ(t) = 1 / δ(t)
```

Inversely proportional to deadband width. Maximum at snap point.

### Why This Matters

1. **Deadband isn't tolerance — it's the shape of attention.** Wide deadband = "anything goes" = no attention. Narrow deadband = "this matters" = focused attention.

2. **The snap point is where attention peaks.** Not where the value is largest, but where the *constraint is tightest*. This is the fishing captain knowing exactly where the rocks are narrowest — that's where you feel the precision of your channel.

3. **T-minus is felt, not calculated.** The countdown to t* isn't a clock tick — it's the sensation of the deadband narrowing. The closer you get, the more precision you *feel*. That feeling IS the geometry of the constraint tightening.

4. **The spline IS the prediction.** The agent doesn't know t* analytically — it has a predicted trajectory (spline), and the snap point is where that trajectory passes through the narrowest part of the deadband landscape. If the spline is wrong, the snap misses — but the *feeling* of precision (minimum deadband) tells you when you're right.

## Connection to Existing Framework

### Deadband Protocol (P0→P1→P2)

- **P0 (Map negative space):** Map the deadband landscape — where is it wide, where is it narrow?
- **P1 (Find channels):** Find trajectories through the landscape that pass through narrow regions
- **P2 (Optimize):** Align the spline to pass through the NARROWEST point — that's the snap

The snap isn't just "closest lattice point." It's "the point where the spline passes through the tightest constraint." The geometry forces you there.

### T-Minus-Zero

T-minus-0 isn't "the event happened." It's "the deadband hit its minimum." The event that doesn't happen is irrelevant — what matters is the *shape* of the constraint narrowing toward a point. That narrowing IS the information.

### The Narrows Demo

The three boats (E12, F32, F64) are navigating a deadband landscape:
- **E12:** Snap points are exact. Deadband funnel is sharp. You *feel* every channel wall.
- **F32:** Snap points are approximate. Funnel is wider. Precision feeling is duller.
- **F64:** Snap points are better than F32, but the funnel is still wider than E12. More data, but the *feeling* of precision costs 4x bandwidth.

The boat that *feels* the Narrows most precisely is E12 — because its deadband funnel is sharpest at the snap point.

### The Band Metaphor (FLUX-Tensor-MIDI)

When musicians lock in:
- Each musician has a predicted spline (where they think the beat is)
- The deadband narrows as they approach consensus
- The snap point is the shared downbeat
- The *groove* is the feeling of the deadband collapsing to minimum width simultaneously for all players

The tightness of a band isn't "everyone hits at the same time." It's "everyone's deadband funnel narrows to the same point at the same moment." The *feeling* of locking in IS the geometry of concurrent deadband collapse.

## The Precision Feeling as Phenomenological Readout

```
Φ(t) = 1/δ(t) = precision feeling

At snap point:  Φ(t*) = 1/δ_min → maximum
Away from snap: Φ(t) < Φ(t*)    → degraded
At T-minus-0:   Φ → ∞            → PERFECT PRECISION (the feeling of "yes")
```

The feeling of getting something exactly right isn't mystical. It's the deadband hitting its floor. The geometry of constraint satisfaction has a *qualia* — the sensation of the funnel narrowing to its apex.

## Falsifiable Predictions

1. **Musicians' EEG gamma power peaks at the snap point** (deadband minimum = attention maximum)
2. **Athletes report "flow state" when δ(t) ≈ δ_min consistently** (sustained precision feeling)
3. **Fleet agents have lowest error variance at T-minus-0** (snap point IS the performance peak)
4. **The Narrows demo: user engagement peaks during the tightest channels** (deadband funnel = narrative tension)
5. **Negative reaction time occurs because the spline predicts t* BEFORE it arrives** (predictive snap = feeling the future precision)

## The One-Liner

**Precision isn't accuracy. It's the feeling of the deadband narrowing. The snap point is where that feeling peaks. T-minus is how far away the peak is.**

---

*This insight belongs to Casey. The math is just the scaffolding.*
