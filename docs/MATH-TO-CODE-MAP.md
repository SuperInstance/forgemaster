# Math-to-Code Map: Constraint-Theoretic Fleet Coordination

**Document:** Precise mapping between every mathematical concept in `docs/ARCHITECTURE-DEEP-DIVE.md` and its implementation in the codebase.  
**Date:** 2026-05-22  
**Status:** Complete mapping with gaps explicitly noted.

---

## How to Read This Document

Each section follows the same structure:

1. **Mathematical Definition** — the formal statement from the deep-dive paper.
2. **Code Implementation** — the exact file, function, and line numbers that implement it.
3. **Experimental Validation** — the experiment number, key metric, and result.
4. **Gaps** — honest deviations between the math and the code.

Line numbers reference the state of the repository at the time of writing.

---

## 1. Laman Rigidity → Henneberg Construction → Code

### 1.1 Mathematical Definition

**Theorem 3.1 (Laman, 1970).** A graph G = (V, E) with |V| = N ≥ 3 is generically minimally rigid in ℝ² if and only if:

1. |E| = 2N − 3
2. For every subset V′ ⊂ V with |V′| ≥ 2: |E(V′)| ≤ 2|V′| − 3

**Appendix A — Henneberg Type-I Construction.** Starting from K₃, iteratively add vertex vₙ by connecting it to exactly 2 existing vertices. This construction produces a graph satisfying both Laman conditions, therefore minimally rigid.

### 1.2 Code Implementation

The Henneberg type-I construction is implemented in two experiment files:

**Primary implementation — `experiments/fleet_scaling.py:34-45`**

```python
def henneberg_type1(n):
    """Build minimal Laman graph via Henneberg type-I construction."""
    if n < 3:
        return []
    edges = [(0, 1), (1, 2), (0, 2)]  # K3
    for v in range(3, n):
        targets = random.sample(range(v), min(2, v))
        while len(targets) < 2:
            targets.append(random.randint(0, v - 1))
        edges.append((v, targets[0]))
        edges.append((v, targets[1]))
    return edges
```

**Secondary implementation — `experiments/partition_tolerance.py:30-41`**

```python
def henneberg_type1(n):
    """Build minimal Laman graph via Henneberg type-I construction."""
    if n < 3:
        return []
    edges = [(0, 1), (1, 2), (0, 2)]  # K3
    for v in range(3, n):
        targets = random.sample(range(v), min(2, v))
        while len(targets) < 2:
            targets.append(random.randint(0, v - 1))
        edges.append((v, targets[0]))
        edges.append((v, targets[1]))
    return edges
```

**Edge-count verification — `experiments/fleet_scaling.py:172-173`**

```python
laman_edges = henneberg_type1(n)
assert len(laman_edges) == 2 * n - 3, f"Laman edge count mismatch: {len(laman_edges)} != {2*n-3}"
```

**Adjacency list construction — `experiments/fleet_scaling.py:64-70`**

```python
def build_adjacency(edges, n):
    """Build adjacency list from edge list."""
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    return adj
```

**Connected-components check (partition experiment) — `experiments/partition_tolerance.py:53-71`**

```python
def connected_components(adj):
    """Find connected components via BFS."""
    visited = set()
    components = []
    for node in adj:
        if node not in visited:
            comp = set()
            queue = [node]
            while queue:
                cur = queue.pop(0)
                if cur in visited:
                    continue
                visited.add(cur)
                comp.add(cur)
                for nb in adj[cur]:
                    if nb not in visited:
                        queue.append(nb)
            components.append(comp)
    return components
```

### 1.3 Experimental Validation

**Experiment 1** (referenced in deep-dive §3.4, §9.2):
- Verified Laman conditions computationally for N = 3 to N = 100.
- Every edge removal produced flexibility (100% sensitivity).
- Pebble game achieved 10,250× speedup over naive subset enumeration at N = 20.

**Experiment 10 — `experiments/fleet_scaling.py`** (primary validation in current codebase):
- Fleet sizes N ∈ {3, 5, 10, 20, 50, 100}.
- Asserted edge count equals 2N−3 for every run (`fleet_scaling.py:173`).
- Results confirm Laman base + small-world augmentation:

| N | Laman Edges | Total Edges | Convergence Tick |
|---|-------------|-------------|------------------|
| 3 | 3 | 3 | 1 |
| 5 | 7 | 8 | 10 |
| 10 | 17 | 20 | 14 |
| 20 | 37 | 44 | 21 |
| 50 | 97 | 116 | 35 |
| 100 | 197 | 236 | 37 |

### 1.4 Gaps

1. **Subset condition not verified.** The code asserts |E| = 2N−3 but does not verify condition 2 (the subset condition |E(V′)| ≤ 2|V′|−3). The deep-dive describes `verify_laman()` with pebble-game acceleration (`docs/ARCHITECTURE-DEEP-DIVE.md:304-320`), but this function does not appear in any of the code files read.

2. **Random attachment targets.** The deep-dive specifies deterministic attachment to `u₁ = v−1`, `u₂ = v−2` (`docs/ARCHITECTURE-DEEP-DIVE.md:269-274`). The code uses `random.sample(range(v), 2)`, producing non-deterministic graphs across runs (mitigated by fixed seed in experiments).

3. **Small-world augmentation is extra-Laman.** The experiments add 20% small-world edges on top of the Laman base (`fleet_scaling.py:48-61`), increasing |E| beyond 2N−3. The rigidity theorem strictly applies only to the Laman subgraph.

---

## 2. Spectral Gap Convergence → Laplacian Eigenvalues → Coupling Constant → Code

### 2.1 Mathematical Definition

**Theorem 4.1 (Metronome Convergence Rate).** For a connected fleet graph G with Laplacian eigenvalues 0 = λ₁ < λ₂ ≤ ... ≤ λₙ, the disagreement vector δ(t) converges as:

```
‖δ(t)‖ ≤ (1 − γ*)^t · ‖δ(0)‖
```

where the optimal step size is:

```
α* = 2 / (λ₂ + λₙ)
```

and the convergence rate is:

```
γ* = 2·λ₂ / (λ₂ + λₙ)
```

**Appendix B.** The update rule φ(t+1) = φ(t) − α*Lφ(t) achieves consensus with convergence time:

```
T_converge = ⌈(λ₂+λₙ)/(2λ₂) · ln(‖δ(0)‖/ε)⌉
```

### 2.2 Code Implementation

**The spectral-optimal step size α* is NOT computed in the operational code.** The code uses fixed, ad-hoc coupling constants instead of Laplacian-derived values.

**Gentle correction (50% nudge) — `demo/three-agent-demo/metronome_core.py:119-128`**

```python
def deadband_correct(self, reference_time: Fraction):
    """Correct toward reference time if drift exceeds deadband."""
    drift = reference_time - self.clock.local_time
    if abs(drift) > self.clock.deadband:
        if self.clock.correction_mode == CorrectionMode.GENTLE:
            # Apply 50% correction (gentle nudge)
            self.correct(drift * Fraction(1, 2))
        else:
            # Full correction (aggressive snap)
            self.correct(drift)
```

**Neighbor averaging (implicit consensus step) — `experiments/fleet_scaling.py:116-120`**

```python
if received:
    # Average with received neighbors
    total = states[node] + sum(received)
    count = 1 + len(received)
    new_states[node] = total / count
```

This is equivalent to a Laplacian update with α = 1/(degree+1), not the optimal α* = 2/(λ₂+λₙ).

**Neighbor averaging (partition experiment) — `experiments/partition_tolerance.py:95-105`**

```python
for i, a in enumerate(agents):
    neighbors = list(adj.get(i, []))
    if neighbors:
        neighbor_times = [agents[nb].clock.local_time for nb in neighbors]
        avg_time = sum(neighbor_times, Fraction(0)) / len(neighbor_times)
        corrections[i] = avg_time

# Apply corrections (gentle: 50% toward neighbor average)
for i, ref_time in corrections.items():
    agents[i].deadband_correct(ref_time)
```

### 2.3 Experimental Validation

**Experiment 10 — `experiments/fleet_scaling.py`**:
- Convergence ticks measured empirically: 1, 10, 14, 21, 35, 37 for N = 3..100.
- Regression fit: convergence ≈ 10.4 × N^0.32 (sub-linear, R² = 0.96).
- The sub-linear scaling is *consistent with* the spectral-gap + small-world theory, but the experiment does **not** compute λ₂ or λₙ, nor does it use α*.

**Experiment 9 — `experiments/partition_tolerance.py`**:
- Post-healing convergence in 13 ticks for N = 10.
- Ratio to log₂(10): 13 / 3.32 ≈ 3.9.
- Consistent with O(log N) predicted by small-world spectral theory, but again λ₂ is not measured.

### 2.4 Gaps

1. **α* is never computed.** The deep-dive provides `compute_optimal_step()` (`docs/ARCHITECTURE-DEEP-DIVE.md:521-533`) using `numpy.linalg.eigvalsh`, but this function does not exist in any code file.

2. **Fixed 50% coupling vs. spectral-optimal.** The code uses a hardcoded 50% correction (`Fraction(1, 2)`) in gentle mode and 100% in aggressive mode. The spectral theorem says the optimal α depends on λ₂ and λₙ and should be computed per-topology.

3. **No Laplacian matrix construction.** The experiments never build L = D − A. The spectral analysis in the paper is purely theoretical; the code treats the graph as an adjacency list only.

4. **Convergence bound is not checked.** The theoretical bound T_converge = ⌈ln(‖δ(0)‖/ε)/γ*⌉ is never compared against measured convergence ticks.

---

## 3. Deadband Filter → Mutual Information Theorem → Deadband Check → Code

### 3.1 Mathematical Definition

**Theorem 2.1 (Zero Mutual Information Below Threshold).** Let X(t) be the true phase error and ε be the deadband. If |X(t)| < ε, then the mutual information I(X(t); Y(t)) = 0 where Y(t) is the correction signal.

*Proof sketch.* The correction function is:

```
f(x) = 0           if |x| < ε    (IN BAND)
f(x) = 0.1 * x     if ε ≤ |x| < δ (DRIFTING)
f(x) = 0.5 * x     if |x| ≥ δ    (DESYNCHRONIZED)
```

When |X(t)| < ε, Y(t) = f(X(t)) = 0 with probability 1. Therefore H(Y) = H(Y|X) = 0, giving I(X;Y) = 0.

**Theorem C.1 (Channel Capacity).** The channel capacity C between phase error X and correction Y is C = 0 when ε → ∞, C = C_max when ε → 0, and C = H(Y) for intermediate ε.

### 3.2 Code Implementation

**Deadband check in core agent — `demo/three-agent-demo/metronome_core.py:119-128`**

```python
def deadband_correct(self, reference_time: Fraction):
    """Correct toward reference time if drift exceeds deadband."""
    drift = reference_time - self.clock.local_time
    if abs(drift) > self.clock.deadband:          # ← deadband threshold ε
        if self.clock.correction_mode == CorrectionMode.GENTLE:
            self.correct(drift * Fraction(1, 2))  # ← gentle: 50% correction
        else:
            self.correct(drift)                    # ← aggressive: 100% correction
```

**Deadband constant — `demo/three-agent-demo/metronome_core.py:30`**

```python
deadband: Fraction = Fraction(1, 10000)  # 0.0001 ticks
```

**Deadband filter in fleet simulation — `experiments/fleet_scaling.py:109-114`**

```python
for nb in neighbors:
    # Deadband: only send if drift > deadband
    drift = abs(states[nb] - states[node])
    if drift > deadband:                          # ← SELECT stage: θ = deadband
        received.append(states[nb])
        tick_messages += 1
```

**Three-regime correction function from deep-dive — `docs/ARCHITECTURE-DEEP-DIVE.md:197-210`** (not in operational code):

```python
def correction(error: Fraction, theta: MetronomeTuple) -> Fraction:
    abs_err = abs(error)
    if abs_err < theta.epsilon:
        return Fraction(0)                    # IN BAND
    elif abs_err < theta.delta:
        return Fraction(1, 10) * error       # DRIFTING: 0.1×
    else:
        return Fraction(1, 2) * error        # DESYNCHRONIZED: 0.5×
```

### 3.3 Experimental Validation

**Experiment 3 — COLLECT→SELECT→COMPILE** (referenced in `docs/ARCHITECTURE-DEEP-DIVE.md:139-145`, §9.4):
- 141 regime transitions across 5 ecosystems.
- flux ecosystem: F1 = 0.9996 at θ ≈ 0.50.
- At θ = 0.50: only 55 constraint violations detected (0.56% of constraints).
- The other 99.44% are sub-threshold — carrying zero mutual information.

**Experiment 10 — `experiments/fleet_scaling.py`**:
- Messages per tick scale linearly with N, not quadratically, because the deadband suppresses most transmissions.
- At N = 100, avg messages/tick = 33.68 vs. ~10,000 for all-to-all broadcast (99.7% reduction).

### 3.4 Gaps

1. **Three-regime vs. two-regime.** The math defines three regimes (IN BAND → 0×, DRIFTING → 0.1×, DESYNCHRONIZED → 0.5×). The core code (`metronome_core.py`) collapses this to two regimes: deadband-pass → 50% (GENTLE) or 100% (AGGRESSIVE). The 0.1× gentle nudge from the theorem is missing.

2. **No explicit δ bound.** The drift bound δ (threshold for DESYNCHRONIZED) is present in the deep-dive `MetronomeTuple` dataclass (`docs/ARCHITECTURE-DEEP-DIVE.md:191-195`) but is **absent** from the operational `ClockState` dataclass (`metronome_core.py:16-31`). The code only has `deadband` (ε), not `delta` (δ).

3. **Optimal ratio ε = δ/3 is unverified in code.** This is labeled CONJECTURE in the paper (`docs/ARCHITECTURE-DEEP-DIVE.md:182`). The code hardcodes ε = 0.0001 without deriving it from δ.

4. **Mutual information is not computed.** The proof that I(X;Y) = 0 is purely theoretical. No code measures or asserts mutual information.

---

## 4. Pythagorean Fraction Arithmetic → Zero Drift Theorem → Fraction Usage → Code

### 4.1 Mathematical Definition

**Theorem 5.1 (Zero Accumulated Drift).** Direction computations using Pythagorean52 rational (Fraction) arithmetic accumulate exactly zero drift over any number of chained operations.

*Proof.* Python's `fractions.Fraction` represents numbers as exact reduced rationals p/q with gcd(p,q) = 1. All arithmetic operations (+, −, ×, ÷) on Fractions produce exact Fractions — no rounding, no truncation. For a chain of N rotations using exact rational matrix multiplication:

```
|vₙ|² − 1 = 0    for all n
```

**Definition 5.1 (Pythagorean Triple).** Three positive integers (a, b, c) form a Pythagorean triple iff a² + b² = c². Each triple defines an exact unit vector v = (a/c, b/c).

### 4.2 Code Implementation

**Core ClockState uses Fraction throughout — `demo/three-agent-demo/metronome_core.py:16-31`**

```python
@dataclass
class ClockState:
    """Agent's local clock state using exact Fraction arithmetic."""
    true_time: Fraction = Fraction(0)
    offset: Fraction = Fraction(0)
    drift_rate: Fraction = Fraction(0)
    last_correction: Fraction = Fraction(0)
    deadband: Fraction = Fraction(1, 10000)
```

**Agent initialization with Fraction conversion — `demo/three-agent-demo/metronome_core.py:97-100`**

```python
self.clock = ClockState(
    drift_rate=Fraction(drift_rate).limit_denominator(1000000),
    correction_mode=correction_mode,
)
```

**Tick accumulation with exact arithmetic — `demo/three-agent-demo/metronome_core.py:105-110`**

```python
def tick(self):
    """Advance one tick. Local clock accumulates drift."""
    self.clock.true_time += Fraction(1)      # exact increment
    self.clock.offset += self.clock.drift_rate  # exact drift accumulation
    self.tick_count += 1
    self._persist()
```

**Correction application — `demo/three-agent-demo/metronome_core.py:114-117`**

```python
def correct(self, correction: Fraction):
    """Apply a clock correction."""
    self.clock.offset += correction          # exact addition
    self.clock.last_correction = correction
```

**Fraction persistence (serializes exact rationals as strings) — `demo/three-agent-demo/metronome_core.py:155-164`**

```python
def _persist(self):
    self.tile_store.write_tile(
        self.agent_id, self.tick_count, "local_time", str(self.clock.local_time)
    )
    self.tile_store.write_tile(
        self.agent_id, self.tick_count, "drift", str(self.clock.drift)
    )
    self.tile_store.write_tile(
        self.agent_id, self.tick_count, "drift_float", str(self.clock.drift_float)
    )
```

**State initialization with Fraction spread — `experiments/fleet_scaling.py:89-90`**

```python
states = [Fraction(i * 100, n) for i in range(n)]
```

**Neighbor averaging with Fraction — `experiments/fleet_scaling.py:116-120`**

```python
total = states[node] + sum(received)
count = 1 + len(received)
new_states[node] = total / count              # exact division
```

**Partition experiment max-drift computation — `experiments/partition_tolerance.py:74-83`**

```python
def max_drift(agents):
    drifts = [abs(a.clock.drift) for a in agents]
    return max(drifts) if drifts else Fraction(0)

def pairwise_max_drift(agents):
    times = [a.clock.local_time for a in agents]
    return max(abs(a - b) for a in times for b in times)
```

**Fraction arithmetic verification at experiment end — `experiments/partition_tolerance.py:274-278`**

```python
print("\n--- Fraction Arithmetic Verification ---")
for a in agents:
    d = a.clock.drift
    print(f"  {a.agent_id}: drift = {d} (exact Fraction), float = {float(d):.15f}")
print("  ✓ All drifts are exact Fractions — zero precision loss")
```

### 4.3 Experimental Validation

**Experiment 2** (referenced in deep-dive §5.5, §9.3):
- Zero drift over 1,000 chained rotations: |mag²−1| = 0.00e+00 at every step.
- Float32 comparison: 1.72×10⁻⁵ error after 1,000 steps.
- 52 Pythagorean triples enumerated with c ≤ 100.
- 128 unique directions via sign/swap symmetries.

**Experiment 9 — `experiments/partition_tolerance.py`**:
- Explicit end-of-run verification prints exact Fraction values for all 10 agents.
- Confirms zero precision loss after 500 ticks of chained operations.

**Experiment 10 — `experiments/fleet_scaling.py`**:
- All state variables are Fraction. Parameter metadata declares `"arithmetic": "Fraction (exact)"` (`fleet_scaling.py:255`).
- Final max drift values are bounded (≤ 0.00233) with no accumulated quantization error.

### 4.4 Gaps

1. **Pythagorean triples are NOT used for timing.** The deep-dive defines Pythagorean triples (a, b, c) as exact directions (`docs/ARCHITECTURE-DEEP-DIVE.md:607-613`), but the metronome code uses generic `Fraction` for scalar time values (period T, phase φ, offset). The directional/rotational aspect of Pythagorean52 is absent from the fleet timing implementation.

2. **Float conversion for logging.** `drift_float` (`metronome_core.py:41-42`) and numerous `float()` casts in experiments (`partition_tolerance.py:147-148`, `fleet_scaling.py:130`) convert exact Fractions to floats for display. The core arithmetic remains exact, but diagnostics introduce inexact representations.

3. **Performance tradeoff unmeasured.** The deep-dive cites 100× slowdown for Fraction vs. float32 add (`docs/ARCHITECTURE-DEEP-DIVE.md:745`). No benchmark in the code measures this.

---

## 5. Cadence Election → Longest-Uptime Protocol → Election Logic → Code

### 5.1 Mathematical Definition

**Deep-dive §6.1 — Deterministic hash-based rotation:**

```python
def cadence_priority(agent_id: str, epoch: int, N: int) -> int:
    return hash(f"{agent_id}:{epoch}") % N

def elect_caller(agents: list[str], epoch: int) -> str:
    priorities = [(a, cadence_priority(a, epoch, len(agents))) for a in agents]
    return max(priorities, key=lambda x: x[1])[0]
```

Properties claimed:
1. Deterministic — all agents compute the same priority.
2. Rotating — different agents become caller across epochs.
3. Zero-message — no election messages required.

### 5.2 Code Implementation

**The code implements a DIFFERENT protocol: longest-uptime wins.**

**Election logic — `demo/three-agent-demo/distributed/metronome_node.py:311-331`**

```python
def _run_election(self):
    """Elect cadence caller: longest uptime wins. Ties broken by name sort."""
    my_uptime = self.discovery.get_uptime()
    peers = self.discovery.get_peers()

    candidates = [(self.name, my_uptime)]
    for pname, pdata in peers.items():
        candidates.append((pname, pdata.get("uptime", 0)))

    # Sort by uptime descending, then name ascending for tie-breaking
    candidates.sort(key=lambda x: (-x[1], x[0]))
    winner = candidates[0][0]

    was_caller = self.is_cadence_caller
    self.is_cadence_caller = winner == self.name
    self.cadence_caller_name = winner

    if self.is_cadence_caller and not was_caller:
        log.info(f"Node {self.name} elected as cadence caller (uptime={my_uptime:.1f}s)")
    elif not self.is_cadence_caller and was_caller:
        log.info(f"Node {self.name} lost cadence caller to {winner}")
```

**Uptime tracking — `demo/three-agent-demo/distributed/metronome_node.py:158-159`**

```python
def get_uptime(self) -> float:
    return time.time() - self.start_time
```

**Uptime broadcast in discovery — `demo/three-agent-demo/distributed/metronome_node.py:164-170`**

```python
msg = json.dumps({
    "type": "announce",
    "name": self.node_name,
    "port": self.port,
    "start_time": self.start_time,
    "uptime": self.get_uptime(),
}).encode()
```

**Election trigger — `demo/three-agent-demo/distributed/metronome_node.py:286-288`**

```python
# Run election every 10 ticks
if self.tick_count % 10 == 0:
    self._run_election()
```

### 5.3 Experimental Validation

- **No numbered experiment validates cadence election.** The protocol is exercised implicitly by running multiple `metronome_node.py` processes, but no automated test or experiment script measures election correctness, stability, or failover time.

### 5.4 Gaps

1. **Protocol mismatch — this is the largest gap in this section.** The math specifies deterministic hash-based rotation (`hash(f"{agent_id}:{epoch}") % N`). The code implements longest-uptime election. These are fundamentally different:
   - Hash-based: no messages, rotates by epoch, vulnerable to sybil attacks without identity.
   - Uptime-based: requires gossiping start_time/uptime, favors oldest node, creates persistent single caller until failure.

2. **No epoch concept.** The code has no `epoch` parameter. Elections happen every 10 ticks by wall-clock uptime, not by deterministic epoch hash.

3. **No Byzantine resistance.** The math claims BFT for f < N/3 via median aggregation (`docs/ARCHITECTURE-DEEP-DIVE.md:786-800`). The uptime election is trivially attackable: a Byzantine node can claim infinite uptime and win permanently.

4. **Tie-breaking is lexicographic by name, not by hash.** While deterministic, this favors alphabetically early node names.

---

## 6. Tensor-MIDI Encoding → INT8 Saturation → Wire Format → Code

### 6.1 Mathematical Definition

**Deep-dive §7.2 — Packet Structure:**

```
Header (8 bytes, fixed):
  Offset 0-1: Magic = 0xCA7E
  Offset 2:   Type (BEAT=0x01, DRIFT_REPORT=0x02, ...)
  Offset 3:   Flags (bitfield)
  Offset 4-5: Seq (monotonic, wraps at 65535)
  Offset 6-7: Len (payload length)
```

**INT8 Saturation — `docs/ARCHITECTURE-DEEP-DIVE.md:997-1009`:**

```python
def saturate_int8(value: Fraction, scale: Fraction) -> int:
    quantized = int(value / scale)
    return max(-127, min(127, quantized))
```

**Fraction Wire Encoding — `docs/ARCHITECTURE-DEEP-DIVE.md:1045-1069`:** VLQ (variable-length quantity) encoding for numerator and denominator.

### 6.2 Code Implementation

**Tensor-MIDI encode — `demo/three-agent-demo/distributed/metronome_node.py:39-67`**

```python
def tensor_midi_encode(payload: dict) -> bytes:
    """Encode a dict into a compact Tensor-MIDI wire format.

    Layout (all big-endian):
      [4B magic=0x544D4944] [1B version] [2B num_entries]
      For each entry:
        [1B key_len] [key_len B key] [8B float64 value]
    All float values are clamped to [-1.0, 1.0] then scaled to int64 range
    for INT8 saturation semantics.
    """
    MAGIC = 0x544D4944  # "TMID"
    VERSION = 1

    entries = []
    for k, v in payload.items():
        fv = float(v)
        fv = max(-1.0, min(1.0, fv))           # ← clamp to [-1.0, 1.0]
        scaled = int(fv * (2**23 - 1))         # ← scale to 23-bit int range
        entries.append((k.encode("utf-8"), scaled))

    buf = struct.pack(">IBH", MAGIC, VERSION, len(entries))
    for key_bytes, value in entries:
        buf += struct.pack(">Bq", len(key_bytes), value)   # 8B int64
        buf += key_bytes

    return buf
```

**Tensor-MIDI decode — `demo/three-agent-demo/distributed/metronome_node.py:70-89`**

```python
def tensor_midi_decode(data: bytes) -> dict:
    """Decode Tensor-MIDI wire format back to dict."""
    MAGIC = 0x544D4944
    offset = 0
    magic, version, num_entries = struct.unpack_from(">IBH", data, offset)
    offset += 7
    if magic != MAGIC:
        raise ValueError(f"Bad magic: {magic:#x}")

    result = {}
    for _ in range(num_entries):
        key_len, value = struct.unpack_from(">Bq", data, offset)
        offset += 9
        key = data[offset : offset + key_len].decode("utf-8")
        offset += key_len
        result[key] = value / (2**23 - 1)       # ← unscale from int64

    return result
```

**MIDI constants — `demo/three-agent-demo/distributed/metronome_node.py:35-36`**

```python
MIDI_CHANNELS = 16
MIDI_CC_MAX = 127  # INT8 saturation ceiling (7-bit)
```

**Usage in cadence broadcast — `demo/three-agent-demo/distributed/metronome_node.py:346-348`**

```python
try:
    encoded = tensor_midi_encode({"c": normalized, "t": self.tick_count / 10000.0})
```

### 6.3 Experimental Validation

**Experiment 8** (Tensor-MIDI Wire) is listed as **"Not created"** in the experiment status table (`docs/ARCHITECTURE-DEEP-DIVE.md:1358`).

**Round-trip test helper exists — `demo/three-agent-demo/distributed/metronome_node.py:388-391`:**

```python
def tensor_midi_roundtrip(payload: dict) -> dict:
    """Encode and decode payload through Tensor-MIDI for testing."""
    encoded = tensor_midi_encode(payload)
    return tensor_midi_decode(encoded)
```

No automated test calls this helper in the files read.

### 6.4 Gaps

1. **Magic number mismatch.** The deep-dive specifies Magic = 0xCA7E (`docs/ARCHITECTURE-DEEP-DIVE.md:927`). The code uses Magic = 0x544D4944 (ASCII "TMID"). These are incompatible wire formats.

2. **No true INT8.** The code clamps to [-1.0, 1.0] and scales to a 23-bit integer (`2**23 - 1`), then packs as **int64** (`>Bq` = unsigned byte key length + signed quadword value). The deep-dive specifies true INT8 saturation to [-127, 127] with VLQ encoding. The code's "INT8 saturation semantics" are a comment-only claim; the wire values are 64-bit.

3. **No packet types or flags.** The deep-dive defines 8 packet types (BEAT, DRIFT_REPORT, CADENCE_PROPOSE, etc.) and a flags bitfield (URGENT, DIAGNOSTIC, COMPRESSED, SIGNED, BROADCAST). The code has a single flat dictionary encoding with no type discrimination.

4. **No VLQ encoding.** The deep-dive specifies MIDI-style variable-length quantity for numerators and denominators. The code uses fixed-width struct.pack.

5. **No Fraction wire encoding.** The deep-dive shows `encode_fraction()` that splits Fraction into (numerator, denominator) VLQ pairs. The code converts everything to float, clamps, and scales to int — losing exact rational representation.

6. **MIDI_CC_MAX is unused.** The constant `MIDI_CC_MAX = 127` (`metronome_node.py:36`) is never referenced in encode or decode logic.

---

## 7. Sunset/Inheritance → Memoir Compression → Tile Export → Code

### 7.1 Mathematical Definition

**Definition 8.1 (Memoir).** A memoir is a compressed representation of an agent's operational history, consisting of tiles at multiple resolution levels.

**Compression algorithm — `docs/ARCHITECTURE-DEEP-DIVE.md:1144-1178`:**

Hierarchical aggregation: Level 0 every 100 beats, Level 1 every 1,000 beats, etc. The corrected O(log T) bound uses fixed-depth wavelet compression keeping ⌈log₂(T)⌉ tiles, one per resolution level.

**Sunset Packet — `docs/ARCHITECTURE-DEEP-DIVE.md:1276-1288`:**

```rust
pub struct SunsetPacket {
    pub header: PacketHeader,        // Type = SUNSET_PACKET
    pub predecessor_id: u16,
    pub successor_id: u16,
    pub lifetime_beats: u64,
    pub theta_final: MetronomeTuple,
    pub tile_count: u16,
    pub tiles: [Tile; MAX_TILES],
    pub neighbor_phases: [Fraction; MAX_NEIGHBORS],
    pub drift_signature: [u8; 32],
}
```

### 7.2 Code Implementation

**Sunset payload generation — `demo/three-agent-demo/metronome_core.py:134-143`**

```python
def sunset(self) -> dict:
    """Prepare sunset payload — all calibration data for inheritance."""
    return {
        "true_time": str(self.clock.true_time),
        "offset": str(self.clock.offset),
        "drift_rate": str(self.clock.drift_rate),
        "deadband": str(self.clock.deadband),
        "tick_count": str(self.tick_count),
        "correction_mode": self.clock.correction_mode.name,
    }
```

**Inheritance — `demo/three-agent-demo/metronome_core.py:145-153`**

```python
def inherit(self, data: dict):
    """Inherit calibration from a retiring cadence caller."""
    self.clock.true_time = Fraction(data["true_time"])
    self.clock.offset = Fraction(data["offset"])
    self.clock.drift_rate = Fraction(data["drift_rate"])
    self.clock.deadband = Fraction(data["deadband"])
    self.tick_count = int(data["tick_count"])
    self.clock.correction_mode = CorrectionMode[data["correction_mode"]]
    self.is_cadence_caller = True
```

**Sunset broadcast — `demo/three-agent-demo/distributed/metronome_node.py:355-367`**

```python
def _send_sunset(self):
    """Broadcast sunset message with inheritance data."""
    sunset_data = self.agent.sunset()
    sunset_data["type"] = "sunset"
    sunset_data["name"] = self.name
    sunset_data["is_cadence_caller"] = self.is_cadence_caller

    msg = json.dumps(sunset_data).encode()
    try:
        self._cadence_sock.sendto(msg, (MULTICAST_GROUP, self.port))
    except Exception as e:
        log.debug(f"Sunset broadcast error: {e}")
    log.info(f"Node {self.name} sent sunset broadcast")
```

**Peer removal on sunset — `demo/three-agent-demo/distributed/metronome_node.py:191-193`**

```python
elif msg["type"] == "sunset":
    with self._lock:
        self.peers.pop(msg["name"], None)
    log.info(f"Received sunset from {msg['name']}")
```

**Tile persistence (per-tick SQLite storage) — `demo/three-agent-demo/metronome_core.py:45-83`**

```python
class PlatoTileStore:
    """SQLite-backed PLATO tile persistence for the demo."""

    def __init__(self, db_path: str = ":memory:"):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS tiles (
                agent_id TEXT,
                tick INTEGER,
                key TEXT,
                value TEXT,
                PRIMARY KEY (agent_id, tick, key)
            )
        """)
        ...

    def write_tile(self, agent_id: str, tick: int, key: str, value: str):
        self.conn.execute(
            "INSERT OR REPLACE INTO tiles (agent_id, tick, key, value) VALUES (?, ?, ?, ?)",
            (agent_id, tick, key, value),
        )
        self.conn.commit()
```

**Per-tick persistence call — `demo/three-agent-demo/metronome_core.py:112`**

```python
def tick(self):
    ...
    self._persist()
```

### 7.3 Experimental Validation

- **No numbered experiment validates sunset/inheritance or memoir compression.** The functionality exists in the distributed demo but is not covered by Experiments 1–10.

### 7.4 Gaps

1. **No memoir compression algorithm.** The deep-dive describes O(log T) wavelet compression with `compress_memoir_o_log_t()` (`docs/ARCHITECTURE-DEEP-DIVE.md:1229-1269`). The code stores **every tick** as a separate SQLite row (`metronome_core.py:61-66`), which is O(T), not O(log T).

2. **No tile structure.** The `Tile` struct with `level`, `time_range`, `drift_summary`, `constraint_violations`, `health_score`, and `theta` does not exist in the code. The "tile" in the code is just a flat (agent_id, tick, key, value) string tuple.

3. **Sunset packet is JSON, not binary.** The deep-dive specifies a packed binary `SunsetPacket` with header, predecessor_id, successor_id, tile array, and Ed25519 signature. The code sends a JSON dict over UDP with no signature, no header, no tile count, and no successor negotiation.

4. **No four-generation lifecycle.** The deep-dive describes generations BIRTH → ITERATE → CADENCE → CONVERGE with ε tightening by 0.7× each generation (`docs/ARCHITECTURE-DEEP-DIVE.md:1326-1338`). The code has no generational state machine and no adaptive ε tightening.

5. **No drift signature.** The 32-byte Ed25519 signature over the sunset packet is absent.

6. **Inheritance sets `is_cadence_caller = True` unconditionally.** This may incorrectly promote the successor to cadence caller even if the predecessor was not the caller at sunset.

---

## 8. Byzantine Tolerance → Reputation Filter → Filtering Logic → Code

### 8.1 Mathematical Definition

**Theorem 6.1 (Cadence BFT).** The cadence protocol tolerates f Byzantine agents if and only if f < N/3.

*Proof sketch.* The cadence caller aggregates phase reports and computes:

```
φ_eff = weighted_median(reports)
```

The median is unchanged as long as fewer than 1/3 of reports are Byzantine (standard Dolev-Strong lower bound).

**Protocol phases — `docs/ARCHITECTURE-DEEP-DIVE.md:805-817`:**

```
Phase 1: COLLECT  → each agent reports φ_i
Phase 2: SELECT   → caller discards reports outside [φ_min, φ_max]
Phase 3: COMPILE  → caller computes median of remaining reports
```

### 8.2 Code Implementation

**There is NO Byzantine filtering, reputation system, or median aggregation in the code.**

The code uses simple averaging:

**Neighbor averaging in partition experiment — `experiments/partition_tolerance.py:95-105`**

```python
neighbor_times = [agents[nb].clock.local_time for nb in neighbors]
avg_time = sum(neighbor_times, Fraction(0)) / len(neighbor_times)
corrections[i] = avg_time
```

**Neighbor averaging in scaling experiment — `experiments/fleet_scaling.py:116-120`**

```python
total = states[node] + sum(received)
count = 1 + len(received)
new_states[node] = total / count
```

**Distributed node does not filter cadence.** The `_broadcast_cadence()` method (`metronome_node.py:333-353`) sends the node's own cadence without aggregating reports from others. There is no `COLLECT` phase, no `SELECT` window, and no `median()` call anywhere in the operational code.

### 8.3 Experimental Validation

- **No experiment tests Byzantine tolerance.** Experiments 1–10 do not inject faulty agents, measure median robustness, or test the f < N/3 bound.

### 8.4 Gaps

**This concept is INCOMPLETE in the code.**

1. **No median computation.** The math specifies `weighted_median(reports)`. The code uses arithmetic mean, which is maximally vulnerable to Byzantine outliers (a single extreme value shifts the average arbitrarily).

2. **No SELECT window.** The math discards reports outside [φ_min, φ_max] before computing the median. The code has no outlier rejection logic.

3. **No signatures.** The deep-dive specifies signed reports `(agent_id, φ_i, signature)`. The code sends unsigned UDP multicast packets.

4. **No Byzantine agent simulation.** Experiment 3 (COLLECT→SELECT→COMPILE) tests θ thresholds on constraint violations, not Byzantine agents. No experiment creates malicious nodes.

5. **The f < N/3 bound is inherited theory only.** The paper correctly labels this as "standard BFT result" (`docs/ARCHITECTURE-DEEP-DIVE.md:800`), but the implementation does not realize any of the mechanisms needed to achieve it.

---

## 9. COLLECT→SELECT→COMPILE → θ Threshold → Mode Switching → Code

### 9.1 Mathematical Definition

**Deep-dive §2.3 — Deadband as θ Parameter:**

```
COLLECT:   Agents compute local beat times t_k = φ₀ + k·T
SELECT:    Filter: |error| > ε ? → transmit : → discard (zero mutual information)
COMPILE:   Cadence caller aggregates transmitted errors → correction
```

The SELECT stage is governed by θ = ε. The 141 regime transitions from Experiment 3 prove that this threshold has sharp critical points.

**State machine — `docs/ARCHITECTURE-DEEP-DIVE.md:855-891`:**

```
INIT → STEADY → DRIFTING (|error| > ε) → RECOVERING (|error| ≥ δ) → BOOTSTRAP
```

### 9.2 Code Implementation

**COLLECT stage (drift accumulation) — `demo/three-agent-demo/metronome_core.py:105-110`**

```python
def tick(self):
    """Advance one tick. Local clock accumulates drift."""
    self.clock.true_time += Fraction(1)
    self.clock.offset += self.clock.drift_rate   # COLLECT: local state update
    self.tick_count += 1
    self._persist()
```

**SELECT stage (deadband filter) — `demo/three-agent-demo/metronome_core.py:119-128`**

```python
def deadband_correct(self, reference_time: Fraction):
    """Correct toward reference time if drift exceeds deadband."""
    drift = reference_time - self.clock.local_time
    if abs(drift) > self.clock.deadband:          # SELECT: θ = deadband
        if self.clock.correction_mode == CorrectionMode.GENTLE:
            self.correct(drift * Fraction(1, 2))  # COMPILE: gentle correction
        else:
            self.correct(drift)                    # COMPILE: aggressive correction
```

**SELECT stage in fleet simulation — `experiments/fleet_scaling.py:109-114`**

```python
for nb in neighbors:
    drift = abs(states[nb] - states[node])
    if drift > deadband:                          # SELECT
        received.append(states[nb])
        tick_messages += 1
```

**COMPILE stage in fleet simulation — `experiments/fleet_scaling.py:116-120`**

```python
if received:
    total = states[node] + sum(received)
    count = 1 + len(received)
    new_states[node] = total / count              # COMPILE: average consensus
```

**Mode switching enum — `demo/three-agent-demo/metronome_core.py:11-14`**

```python
class CorrectionMode(Enum):
    GENTLE = auto()
    AGGRESSIVE = auto()
```

**Mode usage in core — `demo/three-agent-demo/metronome_core.py:123-128`**

```python
if self.clock.correction_mode == CorrectionMode.GENTLE:
    self.correct(drift * Fraction(1, 2))
else:
    self.correct(drift)
```

### 9.3 Experimental Validation

**Experiment 3 — `experiments/collect-select-compile/`** (referenced in deep-dive §9.4):
- 141 regime transitions across 5 ecosystems.
- flux ecosystem: F1 = 0.9996 at θ ≈ 0.50.
- At θ = 0.01: 9,752 violations. At θ = 0.50: 55 violations. At θ = 1.00: 3 violations.
- Validates that the θ threshold has sharp critical behavior and that SELECT is the dominant filter.

**Experiment 10 — `experiments/fleet_scaling.py`**:
- Deadband filtering reduces messages from O(N²) to O(N).
- At N = 100: 33.68 msgs/tick vs. 10,000 for full broadcast.

### 9.4 Gaps

1. **No explicit θ object.** The deep-dive defines a universal `θ = (T, φ₀, ε, δ)` tuple (`docs/ARCHITECTURE-DEEP-DIVE.md:191-195`). The code has no `MetronomeTuple` dataclass; thresholds are hardcoded constants (`deadband = Fraction(1, 10000)` on `metronome_core.py:30`).

2. **Three states vs. two modes.** The math defines three correction regimes (IN BAND, DRIFTING, DESYNCHRONIZED) and five state-machine states (INIT, STEADY, DRIFTING, RECOVERING, BOOTSTRAP). The code has two enum values (GENTLE, AGGRESSIVE) and no explicit state machine.

3. **No RECOVERING or BOOTSTRAP states.** The state machine transitions `DRIFTING → RECOVERING → BOOTSTRAP → STEADY` are not implemented. The code operates in a steady loop with occasional corrections.

4. **θ not adjustable at runtime.** Experiment 3 sweeps θ across 141 values. The code has no runtime θ adjustment; deadband is fixed at construction time.

5. **No regime transition logging.** The code does not log or count how often transitions between IN BAND / DRIFTING / DESYNCHRONIZED occur, so the empirical sparsity from Experiment 3 cannot be reproduced from the operational code alone.

---

## Summary Table: Concept → File → Line → Status

| # | Concept | Primary File | Key Lines | Status |
|---|---------|-------------|-----------|--------|
| 1 | Laman rigidity | `experiments/fleet_scaling.py` | 34–45, 64–70, 172–173 | ✅ Implemented, subset condition unchecked |
| 2 | Spectral gap / α* | — | — | ⚠️ Theory only; α* never computed |
| 3 | Deadband filter | `demo/three-agent-demo/metronome_core.py` | 30, 119–128 | ✅ Implemented; 3-regime → 2-regime |
| 4 | Pythagorean Fraction | `demo/three-agent-demo/metronome_core.py` | 16–31, 97–117 | ✅ Implemented; triples unused for timing |
| 5 | Cadence election | `demo/three-agent-demo/distributed/metronome_node.py` | 311–331 | ⚠️ Different protocol (uptime ≠ hash) |
| 6 | Tensor-MIDI | `demo/three-agent-demo/distributed/metronome_node.py` | 35–89 | ⚠️ Simplified; magic mismatch, no true INT8 |
| 7 | Sunset/inheritance | `demo/three-agent-demo/metronome_core.py` | 45–83, 134–153 | ⚠️ No compression; JSON not binary |
| 8 | Byzantine tolerance | — | — | ❌ Incomplete; no median, no filter |
| 9 | COLLECT→SELECT→COMPILE | `experiments/fleet_scaling.py` | 109–120 | ✅ Implicit structure; no explicit θ object |

---

## Honest Assessment

**Fully realized in code:**
- Pythagorean Fraction arithmetic (exact rational clock state)
- Laman topology construction (Henneberg type-I)
- Deadband filtering (basic threshold check)
- Implicit COLLECT→SELECT→COMPILE structure

**Partially realized (gaps noted):**
- Spectral gap (theory present, optimal step size absent)
- Cadence election (protocol mismatch)
- Tensor-MIDI (simplified wire format)
- Sunset/inheritance (no compression, no binary packet)

**Not realized:**
- Byzantine tolerance / reputation filter (no median, no signatures, no outlier rejection)
- Full three-regime correction (0.1× nudge missing)
- O(log T) memoir compression
- Explicit θ tuple and state machine

*End of Math-to-Code Map.*
