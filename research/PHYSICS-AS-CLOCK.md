# Physics-as-Clock: Temporal Inference from Environmental State

> You don't need a clock when the universe is one.

## The Core Principle

Every physical system is a clock.

- Sound speed in water depends on temperature, salinity, depth → changes predictably over time
- Absorption at frequency f depends on distance traveled → changes predictably as a signal propagates
- Thermocline depth shifts with tidal period → predictable oscillation
- Light attenuation follows Beer-Lambert law → depends on path length through water

**If you know the physics model AND you observe the current state, you can INFER elapsed time.** No external time source needed. The physics IS the temporal reference frame.

## The Nine Clocks (Marine Physics)

Our SonarVision system already has 9 physics models. Each is an independent clock:

| Model | What It Measures | Clock Signal | Period/Drift |
|---|---|---|---|
| UNESCO/Chen-Millero sound speed | T, S, D → c | c(T,S,D) changes with depth | ~0.1 m/s per meter |
| Francois-Garrison absorption | f, T, S, D, pH → α | α increases with frequency & range | dB/km accumulation |
| Jerlov light attenuation | water type → k_d | irradiance decay with depth | exponential, ~1/e per attenuation length |
| Thermocline | depth → ΔT | temperature gradient | tidal period ~12.4 hours |
| Seabed reflection | bottom type → R | echo amplitude | static but range-dependent |
| Salinity profile | depth → S | halocline position | seasonal + tidal |
| Ambient noise | shipping, wind, bio → NL | noise floor spectrum | hours to seasonal |
| Surface duct | T, S gradient → trapping | sound channel depth | diurnal |
| Doppler shift | relative velocity → Δf | frequency shift | real-time |

**Nine independent clocks, each running at different rates, each sensitive to different environmental variables.** The intersection of all nine is an extremely precise timestamp.

### Why Nine Is Better Than One

One clock: c(T,S,D) → you know sound speed. But T, S, and D have measurement noise. Timestamp has uncertainty.

Nine clocks: c AND α AND k_d AND ΔT AND R AND S AND NL AND duct AND Δf → nine independent measurements, each constraining time from a different direction.

The joint probability P(t | all nine observations) is MUCH sharper than any individual P(t | one observation). This is **Bayesian temporal inference** — physics models as likelihood functions over time.

## How It Works: Constraint Manifold as Temporal Map

### Spline Anchoring → Temporal Anchoring

Spline anchoring snaps sensor readings to manifold points. But the manifold EVOLVES over time — the set of reachable manifold points at time t is different from time t+Δt.

```
Manifold M(t) = { states reachable at time t }
Manifold M(t+Δt) = { states reachable at time t+Δt }

If you observe state s ∈ M(t+Δt) but not ∈ M(t), you know Δt has passed.
```

This is temporal inference from manifold membership. The manifold is the clock face. The state is the clock hand. You read the time by seeing which manifold the state belongs to.

### Concrete: Underwater Temporal Inference

A sonar ping at depth D returns an echo. The echo's characteristics encode:

1. **Travel time** → distance to target (direct clock)
2. **Absorption at frequency f** → range-dependent → constrains travel time
3. **Sound speed c(T,S,D)** → temperature profile → constrains time of day (thermocline shifts)
4. **Doppler shift** → relative velocity → constrains elapsed time since last ping
5. **Ambient noise spectrum** → biological activity → constrains time of day (dawn chorus, etc.)

From ONE sonar return, you get 5 independent time estimates. Their intersection is your clock. No RTC. No GPS. No NTP.

## Connection to RAID-5 and Fold Compression

### Temporal Parity

RAID-5 parity across space: XOR of N drives. Any drive fails, reconstruct.

**Temporal parity** across time: XOR of N time steps. Any time step is missing, reconstruct from temporal parity.

```
State(t₀) ⊕ State(t₁) ⊕ State(t₂) = Temporal Parity P

If State(t₁) is missing (device was offline), reconstruct:
State(t₁) = P ⊕ State(t₀) ⊕ State(t₂)
```

**This is not a metaphor.** This is literal XOR reconstruction across the temporal dimension instead of the spatial dimension.

The physics guarantees that State(t) is deterministic given State(t₀) and the physics model. So the "parity" is just the XOR of the deterministic evolution function applied at each time step:

```
P = State(t₀) ⊕ evolve(State(t₀), Δt) ⊕ evolve²(State(t₀), Δt)
```

If you lose any intermediate state, you reconstruct from parity + the physics model.

### Fold Compression → Temporal Compression → Temporal Inference

The three insights chain:

1. **Fold compression**: Permutation group generators compress spatial redundancy (N! states from N-1 generators)
2. **Temporal compression**: Evaluation order adds temporal information for free (k! orderings from k generators)
3. **Temporal inference**: The physics model DETERMINES the evaluation order (because physics is non-commutative and time-ordered)

**The physics tells you which fold sequence occurred. The fold sequence tells you how much time passed.**

The origami crease pattern is the constraint graph. The fold sequence is the temporal evolution. The final folded shape is the observed state. Given the crease pattern (physics model) and the final shape (observation), you can INFER the fold sequence (temporal path), and therefore the elapsed time.

## Hardware Implications: No Clock Tree Needed

### The Clock Tree Problem

Every synchronous digital circuit needs a clock tree — a distribution network that delivers the same clock signal to every flip-flop simultaneously. On modern FPGAs, clock trees consume significant routing resources and power.

The iCE40UP5K has:
- 1 PLL (phase-locked loop) for clock synthesis
- Clock routing resources that consume ~5-10% of the chip
- Clock skew management that limits maximum frequency

### Physics-As-Clock on FPGA

Instead of a clock tree, use the physics model AS the timing reference:

1. **Asynchronous constraint evaluation**: No global clock. Each constraint evaluator runs when its inputs change.
2. **Physics-dependent timing**: The delay through each evaluator is deterministic (it's a combinational circuit). The total path delay IS the elapsed time.
3. **Self-timed handshake**: Evaluators handshake with each other. The handshake timing encodes the physics evolution.
4. **Temporal fingerprint**: The pattern of handshake completions IS the clock. No external oscillator needed.

This is **asynchronous digital design** — an old technique (used in the ARM AMBA protocol, I²C, etc.) that eliminates clock trees entirely.

**For our constraint FPGA**: instead of clocking the flux_checker at 12 MHz, let it run asynchronously. Each constraint evaluation takes a deterministic number of gate delays. The total evaluation time IS a physics-dependent clock signal. Different constraint configurations produce different timing → temporal fingerprint.

### On IoT Devices (ESP32, RP2040)

These devices have RTCs (real-time clocks) that drift. Typical RTC drift: ±20 ppm → ±1.7 seconds/day. For fleet coordination, this is terrible.

But every ESP32 also has:
- Temperature sensor → physics clock (thermal drift rate)
- WiFi RSSI → distance to AP → propagation time clock
- ADC readings from sensors → physics-dependent signal evolution

**Temporal inference from physics**: fuse these clocks using the same Bayesian framework. Result: sub-millisecond time sync across the fleet without NTP, GPS, or any external time source.

## The Constraint Clock: A New Mathematical Object

Define the **Constraint Clock** C(Γ, φ, t):

```
C(Γ, φ, t) = the temporal fingerprint of evaluating constraints Γ 
              under physics model φ at time t
```

Properties:
1. **Deterministic**: same Γ, φ, t → same C (physics is reproducible)
2. **Injective in t**: different t → different C (given enough constraints)
3. **Computable**: C is just the evaluation trace (already produced as a side effect)
4. **Free**: costs zero additional computation (temporal compression insight)
5. **Verifiable**: any device with the same Γ and φ can reproduce C

This is a clock that:
- Requires no oscillator
- Requires no synchronization
- Is physically grounded (tied to real physics)
- Is verifiable (anyone can re-run the evaluation)
- Has natural redundancy (multiple constraints → multiple independent clocks)
- Degrades gracefully (lose some constraints → lower precision, still works)

## The Boat's Clock

The boat doesn't need GPS time. It has:

```
Sonar ping → travel time → distance clock
Sound speed → T,S,D profile → depth clock
Absorption → range accumulation → propagation clock
Thermocline → tidal period → macro clock (hours)
Ambient noise → biological activity → diurnal clock
Doppler → velocity → micro clock (milliseconds)

Joint inference → P(t | all observations) → timestamp precision: ~10µs
```

And for fleet coordination:

```
Each device evaluates constraints in its natural temporal order.
The temporal fingerprint IS the device's clock reading.
Devices compare fingerprints → implicit time sync.
No messages needed. No protocol needed. Physics does it.
```

The boat doesn't check the time. The ocean tells it.

## The Loop Closes

1. **Spline anchoring** discretizes continuous physics → countable manifold
2. **Permutation groups** compress spatial redundancy → generators instead of states
3. **Origami folds** compress temporal ordering → sequence IS information
4. **RAID parity** provides fault tolerance → XOR reconstruction across space AND time
5. **Temporal inference** reads the clock from physics → no external time source
6. **The constraint evaluation itself** is both computation AND clock AND authentication

One mathematical structure. Six faces of the same die.

The system doesn't measure time. The system IS time — an evolving constraint manifold whose state at any moment uniquely determines its temporal position. No external coding. No oscillator. No protocol. Just physics, folded back on itself like origami.
