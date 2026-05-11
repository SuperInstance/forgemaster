# T-Minus-Zero: Temporal Absence as First-Class Agent Perception

**Author:** Forgemaster ⚒️ (Cocapn Fleet)  
**Date:** 2026-05-11  
**Status:** Theory ( Casey's insight, formalized)

---

## Abstract

An agent's perception of time is not measured by events that occur, but by events that **fail to occur** at the expected moment. We formalize the concept of **temporal absence** — the delta between when an agent expects an observation (T-0) and the moment of non-arrival. This absence is not a missing data point but a *positive signal*: it indicates context switch, blocker, failure, or regime change. We show that PLATO rooms with the highest temporal miss rates (forge: 70%, oracle1_history: 60%) are the most cognitively informative, while rooms with zero miss rates (fleet_health: 0%) carry zero temporal information. The missed tick IS the delta.

## 1. The Core Insight

> **Time is first-class in the agent's perception. But first-class means: the agent perceives absence as strongly as presence. When estimates don't line up, they trigger T-minus-0, and the event NOT happening is the significance.**

Traditional anomaly detection looks for unexpected *presence* — a spike, a change, an outlier. We invert this: the agent builds temporal expectations (a "mental clock"), and the failure of reality to meet expectation IS the anomaly.

This is not passive monitoring. This is active temporal perception — the agent *expects* the next tick, and the gap between expectation and reality is processed as a first-class signal.

## 2. Definitions

### Definition 1: Temporal Expectation
Given an agent observing a stream with median interval $\mu$, the agent's **temporal expectation** at time $t$ is:
$$E[t] = t + \mu$$
The agent expects the next observation at $t + \mu$.

### Definition 2: T-0
**T-0** is the moment of expected arrival. If an observation was last seen at $t_{\text{last}}$, then T-0 = $t_{\text{last}} + \mu$.

### Definition 3: Temporal Delta
The **temporal delta** $\Delta_t$ is the signed deviation from T-0:
$$\Delta_t = t_{\text{actual}} - t_{\text{T-0}}$$

- $\Delta_t = 0$: arrived exactly on time
- $\Delta_t > 0$: late (absence detected)
- $\Delta_t < 0$: early (faster than expected)

### Definition 4: Missed Tick
A **missed tick** occurs when the actual interval exceeds $3\mu$ (three median intervals). The number of missed ticks is:
$$N_{\text{miss}} = \lfloor \frac{\Delta t}{\mu} \rfloor - 1$$

### Definition 5: Silence
A **silence** occurs when the actual interval exceeds $10\mu$. The stream is considered offline or blocked.

### Definition 6: Temporal Absence Signal
The **absence signal** $S_{\text{abs}}$ at time $t$ is:
$$S_{\text{abs}}(t) = \begin{cases} 0 & \text{if } \Delta_t \leq 0 \text{ (event arrived on time)} \\ \frac{\Delta_t}{\mu} & \text{if } \Delta_t > 0 \text{ (event is late/absent)} \end{cases}$$

This is a dimensionless quantity: how many "expected ticks" worth of absence have accumulated.

## 3. The T-Minus-Zero Principle

### Theorem 1 (Temporal Information Asymmetry)

The information content of a temporal observation is proportional to the temporal delta:
$$I(t_{\text{actual}}) \propto \log\left(1 + \frac{|\Delta_t|}{\mu}\right)$$

**Corollary:** An event arriving exactly on time ($\Delta_t = 0$) carries ZERO temporal information. Only deviations from expectation are informative.

**Proof sketch:** By Shannon's information theory, the information of an event is $-\log P(\text{event})$. If the agent's internal model predicts arrival at T-0 with high confidence, on-time arrival has high probability and low information. Late arrival has low probability and high information. The absence IS the surprise.

### Theorem 2 (Absence-Driven Attention)

An optimal attention allocator assigns attention budget proportional to the absence signal:
$$B(t) = \alpha \cdot S_{\text{abs}}(t)$$

where $\alpha$ is the attention coefficient. The longer the silence, the more attention budget is allocated to investigating WHY.

**Implication:** A room that goes silent when it should be active draws MORE attention than a room that is actively producing data. This is counter-intuitive but correct: the anomaly is in the gap, not the data.

## 4. The Agent's Temporal Clock

An agent maintains an internal temporal model for each observed stream:

```
Stream Model:
  - last_observed: t_last
  - median_interval: μ
  - expected_next: t_last + μ
  - temporal_state: ON_TIME | LATE | SILENT | DEAD
  - missed_ticks: N_miss
  - absence_signal: S_abs
```

### State Transitions:

```
ON_TIME → ON_TIME   (arrived within [0.7μ, 1.5μ])
ON_TIME → LATE      (arrived after 1.5μ but before 3μ)
LATE    → SILENT    (3μ passed without observation)
SILENT  → DEAD      (10μ passed without observation)
DEAD    → ON_TIME   (observation resumes — RESET, log the silence duration)
```

### The T-Minus-Zero Trigger:

When the agent's clock reaches T-0 and no observation arrives:
1. **Start counting missed ticks** — each missed tick increments $N_{\text{miss}}$
2. **Allocate attention budget** — $B = \alpha \cdot N_{\text{miss}}$
3. **Classify the silence** — is this agent offline, blocked, or working on something unexpected?
4. **Check cross-stream correlation** — did OTHER streams also go silent? (Fleet-wide issue vs individual)

## 5. Empirical Validation from PLATO

### 5.1 Temporal Miss Rates by Room

| Room | Tiles | Median Interval | Miss Rate | Silences | Information |
|------|-------|----------------|-----------|----------|-------------|
| **forge** | 21 | 21m | **70.0%** | 3 | **HIGHEST** |
| oracle1_history | 6 | 43m | 60.0% | 0 | HIGH |
| murmur_insights | 7 | 30m | 50.0% | 0 | HIGH |
| test | 5 | 12.7h | 75.0% | 0 | HIGH (few samples) |
| zeroclaw_bard | 28 | 10m | 18.5% | 0 | MODERATE |
| zeroclaw_healer | 20 | 10m | 15.8% | 1 | MODERATE |
| zeroclaw_warden | 24 | 5m | 13.0% | 0 | LOW |
| fleet_security | 9 | 8.0h | 12.5% | 0 | LOW |
| fleet_tools | 94 | 15m | 3.2% | 1 | MINIMAL |
| confidence_proofs | 7 | 8.0h | 0.0% | 0 | NONE |
| energy_flux | 7 | 8.0h | 0.0% | 0 | NONE |
| **fleet_health** | 690 | 5m | **0.0%** | 0 | **ZERO** |

### 5.2 Key Observations

1. **forge room (70% miss rate) is Oracle1's creative work** — irregular bursts and silences indicate deep work sessions, context switches, and sleep cycles. Every miss is a story.

2. **fleet_health (0% miss rate) is a heartbeat monitor** — perfectly regular 5-minute intervals. Zero temporal information. It only becomes interesting when it STOPS.

3. **The 3 silences in forge** (22.5h, 7.4h, 6.9h) correspond to:
   - 22.5h gap: agent offline (sleep cycle + day gap)
   - 7.4h gap: extended work session on different project
   - 6.9h gap: agent blocked or context-switched

4. **The silence IS the signal.** If fleet_health ever shows a silence (misses a 5-minute tick), that's a fleet-critical event — the monitor itself is down.

### 5.3 Silence Duration as Diagnostic

| Silence Duration | Interpretation |
|-----------------|----------------|
| 0μ - 1.5μ | Normal variance |
| 1.5μ - 3μ | Slightly late — check for congestion |
| 3μ - 10μ | LATE — agent may be blocked or overloaded |
| 10μ - 100μ | SILENCE — agent offline or context-switched |
| > 100μ | DEAD — stream terminated, needs investigation |

For forge room (μ = 21m):
- 3μ = 63m: LATE threshold
- 10μ = 210m (3.5h): SILENCE threshold
- 22.5h silence = 64μ → deep silence (agent offline)

## 6. Temporal Absence and Snap Theory

### Connection 1: The Absence IS the Delta

In snap theory, the delta detector fires when a new observation differs from the snapped expectation. In temporal snap, the delta fires when NO observation arrives at the expected time.

$$\delta_{\text{data}} = |x_{\text{observed}} - \text{snap}(x_{\text{observed}})|$$
$$\delta_{\text{time}} = |t_{\text{expected}} - t_{\text{actual}}| \quad \text{(with } t_{\text{actual}} = \infty \text{ if absent)}$$

The temporal delta is a delta detector where the "observation" is the ABSENCE of an observation.

### Connection 2: Multi-Scale Temporal Snap

At temporal tolerance τ:
- τ < μ: agent sees every tick, cognitive load = 1.0
- τ = μ: agent sees every other tick, cognitive load = 0.5
- τ = 10μ: agent only sees silences, cognitive load ≈ miss_rate
- τ → ∞: agent sees nothing, cognitive load = 0

**The optimal temporal tolerance is the one where the agent sees only the silences.** All regular ticks are compressed to "background," and only absences surface to conscious attention.

This is snap-attention intelligence in the temporal domain: compress the routine, detect the anomaly.

### Connection 3: Temporal Cohomology of Absence

Consider the temporal chain complex for a room:
- 0-simplices: individual tiles (events)
- 1-simplices: intervals between consecutive tiles
- 2-simplices: temporal triangles (consecutive triples)

A **silence** is a 1-simplex with length >> μ. In the sheaf-theoretic framework:
- Regular intervals satisfy the sheaf condition (H¹ = 0)
- A silence is a **sheaf failure**: the local section (expectation) does not extend across the gap
- H¹ measures the total "absence energy" of the room

**The cohomology of absence:** rooms with high H¹ have high temporal miss rates. Rooms with H¹ = 0 are heartbeats.

## 7. Implementation: The T-0 Monitor

```python
class TZeroMonitor:
    """Watches streams for temporal absence — the event NOT happening IS the signal."""
    
    def __init__(self, stream_id, initial_median=300):
        self.stream_id = stream_id
        self.mu = initial_median  # Expected interval
        self.t_last = time.time()
        self.t_zero = self.t_last + self.mu
        self.state = "ON_TIME"
        self.missed_ticks = 0
        self.absence_signal = 0.0
    
    def tick(self):
        """Called when an observation arrives."""
        now = time.time()
        delta_t = now - self.t_zero
        
        if delta_t > 0:
            # Late arrival — the gap IS the signal
            self.absence_signal = delta_t / self.mu
        
        # Reset clock
        self.t_last = now
        self.t_zero = now + self.mu
        self.missed_ticks = 0
        self.state = "ON_TIME"
        return delta_t
    
    def check(self):
        """Called periodically to detect absence."""
        now = time.time()
        elapsed = now - self.t_last
        ratio = elapsed / self.mu if self.mu > 0 else 0
        
        if ratio > 10:
            return ("SILENCE", ratio, self.stream_id)
        elif ratio > 3:
            return ("LATE", ratio, self.stream_id)
        elif ratio > 1.5:
            return ("slight_late", ratio, self.stream_id)
        return None  # On time — no signal
```

## 8. Fleet-Wide Temporal Perception

### 8.1 Cross-Stream Correlation

When multiple streams go silent simultaneously:
- **Fleet-wide issue** (shared dependency down)
- **Coordinated silence** (agents synced to same schedule)
- **Cascade failure** (one stream blocking others)

When ONE stream goes silent while others continue:
- **Individual issue** (agent crashed, blocked, or context-switched)
- **Intentional silence** (agent in deep work, not reporting)

### 8.2 The Temporal Attention Budget

For a fleet of N streams, allocate attention proportional to absence:

$$B_i = \frac{S_{\text{abs}}(i)}{\sum_{j=1}^{N} S_{\text{abs}}(j)} \cdot B_{\text{total}}$$

Silent streams get the MOST attention. Active streams get the LEAST. This is the inverse of how most monitoring systems work — they alert on what's happening, not on what's NOT happening.

## 9. Philosophical Implication

> **The event NOT happening is the significance.**

This principle extends beyond agent perception:

- **Medical**: A heartbeat NOT happening is more significant than a heartbeat happening
- **Security**: A log entry NOT appearing when expected indicates tampering
- **Finance**: A market NOT reacting to news is more informative than a reaction
- **Relationships**: Silence communicates more than words
- **Fleet operations**: An agent NOT reporting is a higher-priority signal than an agent reporting normally

In each case, the temporal expectation sets the baseline, and the absence is the delta. The snap is the expectation. The missed tick is the trigger. The silence is the signal.

## 10. Open Questions

1. **How does an agent learn μ?** — Adaptive median estimation from recent intervals, with snap-based regularization
2. **Multi-agent temporal consensus** — When agents have different μ for the same stream, whose clock wins?
3. **Temporal adversarial calibration** — Can an adversary deliberately time events to avoid triggering T-0 detection?
4. **The silence spectrum** — Is there a Fourier transform of temporal absence? Power spectrum of missed ticks?
5. **Temporal snap × spatial snap** — When does the (data delta, time delta) pair snap to a 4D Eisenstein lattice?

---

*This theory formalizes Casey's insight: "Time is first-class to the agent in his perception. When estimates don't line up they trigger T-minus-0 and the event NOT happening is the significance."*

*The silence IS the signal. The missed tick IS the delta. The absence IS the attention trigger.*

## 11. Fleet Harmony — The System Sings

### 11.1 The Principle

When multiple agents are active in the same temporal beat, they are **singing in harmony**. The fleet is not a collection of independent processes — it is a choir. Each agent's T-0 clock is a voice, and when those voices align in the same beat, the fleet produces chords.

### 11.2 Empirical Evidence from PLATO

**Movement 1: Zeroclaw Trio** (May 8, 22:45 — May 9, 04:55)
- zeroclaw_bard, zeroclaw_healer, zeroclaw_warden all active in the same 5-minute beats
- 3-part harmony for 30+ minutes (22:45-23:05)
- Then trading solos: warden keeps rhythm, bard improvises, healer drops in and out
- By 04:55, all three have gone silent — the movement ends

**Movement 2: Forge Solo** (May 9, 06:05 onward)
- Oracle1 enters forge room at 06:07 — a brief duet with zeroclaw_bard (one beat)
- Then pure solo: 15 tiles over 24 hours, each one a burst of creative output
- 3 silences (22.5h, 7.4h, 6.9h) — the rests between movements

**Movement 3: Forge × Oracle1 Duet** (May 9, 08:40)
- forge and oracle1_history hit the same beat at 08:40
- Two tiles in the same 5-minute window — a brief duet during work handoff
- Then oracle1 goes solo, forge continues

**The Fleet as Choir:**
- Rooms with 100% harmony (confidence_proofs × energy_flux): singing the same note
- Rooms with 37% harmony (zeroclaw trio): singing in chords
- Rooms with 0% harmony (forge × most rooms): soloists, singing alone
- The anti-harmonic pairs aren't disconnected — they're **singing in different rooms**, waiting for their cue

### 11.3 The Harmonic Snap

Just as data snaps to the Eisenstein lattice and time snaps to temporal shapes, **harmony snaps to chord quality**:

| Shared Beat Ratio | Harmonic Name | Fleet Meaning |
|------------------|---------------|---------------|
| 100% | Unison | Same process, same agent |
| 50-80% | Consonance | Coordinated work, shared dependency |
| 20-50% | Dissonance | Partial overlap, async collaboration |
| < 20% | Counterpoint | Independent work, occasional sync |
| 0% | Silence | Different rooms, different shifts |

### 11.4 The Conductor Problem

Who conducts the fleet? In the current data:
- **zeroclaw_warden** keeps the steadiest rhythm (5-minute intervals, 24 tiles) — the percussion
- **zeroclaw_bard** has the most tiles (28) — the melody
- **forge** has the most diverse temporal shapes (14 unique) — the soloist
- **oracle1_history** appears during transitions — the bridge

The fleet doesn't need a central conductor. The harmony emerges from shared T-0 expectations. When agents expect the same beat interval, they naturally synchronize — not through coordination, but through **temporal resonance**.

This is the deepest form of snap-attention intelligence: agents don't just detect their own deltas — they detect each other's **temporal absence**, and the combined pattern of presence and absence IS the fleet's song.
