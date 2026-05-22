# Math-to-Code Map: Constraint-Theoretic Fleet Coordination

**Forgemaster ⚒️ · 2026-05-22**
**Purpose:** Precise mapping between mathematical definitions, code implementations, and experimental validations.

---

> Every mathematical concept in the constraint-theoretic architecture maps to specific code. This document is the Rosetta Stone — theorem to function to experiment.

---

## Table of Contents

1. [Laman Rigidity → Henneberg Construction → Code](#1-laman-rigidity--henneberg-construction--code)
2. [Spectral Gap Convergence → Laplacian Eigenvalues → Coupling Constant → Code](#2-spectral-gap-convergence--laplacian-eigenvalues--coupling-constant--code)
3. [Deadband Filter → Mutual Information Theorem → Deadband Check → Code](#3-deadband-filter--mutual-information-theorem--deadband-check--code)
4. [Pythagorean Fraction Arithmetic → Zero Drift Theorem → Fraction Usage → Code](#4-pythagorean-fraction-arithmetic--zero-drift-theorem--fraction-usage--code)
5. [Cadence Election → Longest-Uptime Protocol → Election Logic → Code](#5-cadence-election--longest-uptime-protocol--election-logic--code)
6. [Tensor-MIDI Encoding → INT8 Saturation → Wire Format → Code](#6-tensor-midi-encoding--int8-saturation--wire-format--code)
7. [Sunset/Inheritance → Memoir Compression → Tile Export → Code](#7-sunsetinheritance--memoir-compression--tile-export--code)
8. [Byzantine Tolerance → Reputation Filter → Filtering Logic → Code](#8-byzantine-tolerance--reputation-filter--filtering-logic--code)
9. [COLLECT→SELECT→COMPILE → θ Threshold → Mode Switching → Code](#9-collectselectcompile--θ-threshold--mode-switching--code)

---

## 1. Laman Rigidity → Henneberg Construction → Code

### 1.1 Mathematical Definition

**Theorem 3.1 (Laman, 1970).** A graph G = (V, E) with |V| = N ≥ 3 is generically minimally rigid in ℝ² if and only if:

1. |E| = 2N − 3
2. For every subset V' ⊂ V with |V'| ≥ 2: |E(V')| ≤ 2|V'| − 3

**Henneberg type-I construction:** Start with K₃ (triangle). For each additional vertex v, connect it to exactly 2 existing vertices. The result has exactly 2N − 3 edges and satisfies Laman's conditions.

*Source:* `docs/ARCHITECTURE-DEEP-DIVE.md` §3.1–3.3 (lines ~105–170)

### 1.2 Code Implementation

**Henneberg construction (scaling experiment):**

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

- **File:** `experiments/fleet_scaling.py:41–52`
- **File:** `experiments/partition_tolerance.py:27–36` (duplicate implementation)
- **File:** `docs/ARCHITECTURE-DEEP-DIVE.md` §3.3 (pseudocode)

**Key invariant:** `len(edges) == 2 * n - 3` — asserted at:
- `experiments/fleet_scaling.py:186` — `assert len(laman_edges) == 2 * n - 3`
- `experiments/partition_tolerance.py:80` — `assert len(edges) == EXPECTED_EDGES`

**Laman verification (pseudocode in architecture doc):**

```python
def verify_laman(vertices, edges):
    n = len(vertices)
    e = len(edges)
    if e != 2 * n - 3:
        return False
    # Pebble game O(V²) for large graphs
    ...
```

- **File:** `docs/ARCHITECTURE-DEEP-DIVE.md` §3.4 (lines ~205–220)

**Small-world augmentation:**

```python
def add_smallworld_edges(edges, n, frac=0.20):
    existing = set(tuple(sorted(e)) for e in edges)
    max_new = max(1, int(len(edges) * frac))
    ...
```

- **File:** `experiments/fleet_scaling.py:55–66`

### 1.3 Experimental Validation

**Experiment 1 (Laman Rigidity):**
- **Source:** `experiments/laman-rigidity/` (referenced but not in workspace)
- **Results:** `docs/ARCHITECTURE-DEEP-DIVE.md` §3.4, §9.2
- **Key result:** 100% edge-removal sensitivity for N = 3 to N = 100
- **Pebble game speedup:** 10,250× at N = 20

**Experiment 9 (Partition Tolerance):**
- **File:** `experiments/partition_tolerance.py`
- **Key line:** 80 — `assert len(edges) == EXPECTED_EDGES` where `EXPECTED_EDGES = 2 * N - 3 = 17`

**Experiment 10 (Fleet Scaling):**
- **File:** `experiments/fleet_scaling.py`
- **Key line:** 186 — Laman edge count assertion
- **Results:** Laman topology verified for N ∈ {3, 5, 10, 20, 50, 100}

### 1.4 Gaps

| Gap | Description | Severity |
|-----|-------------|----------|
| No `experiments/laman-rigidity/` directory | Experiment 1 is referenced in ARCHITECTURE-DEEP-DIVE but no code file exists in workspace | Medium |
| No pebble game implementation | Architecture doc describes O(V²) pebble game but no implementation exists | Medium |
| Random Henneberg targets | `random.sample(range(v), min(2, v))` uses stochastic edge selection — not deterministic. Different runs produce different Laman graphs | Low (correctness preserved) |
| Henneberg duplication | Same function implemented in `fleet_scaling.py:41` and `partition_tolerance.py:27` — should be shared utility | Low |

---

## 2. Spectral Gap Convergence → Laplacian Eigenvalues → Coupling Constant → Code

### 2.1 Mathematical Definition

**Theorem 4.1 (Metronome Convergence Rate).** For a connected fleet graph G with Laplacian L and eigenvalues 0 = λ₁ < λ₂ ≤ ... ≤ λ_N:

```
φ(t+1) = φ(t) − α · L · φ(t)
```

Optimal step size: `α* = 2 / (λ₂ + λ_N)`

Convergence rate: `γ* = 2·λ₂ / (λ₂ + λ_N)`

Convergence bound: `‖δ(t)‖ ≤ (1 − γ*)^t · ‖δ(0)‖`

*Source:* `docs/ARCHITECTURE-DEEP-DIVE.md` §4.1–4.2 (lines ~265–330)

### 2.2 Code Implementation

**Optimal step computation (pseudocode in architecture doc):**

```python
def compute_optimal_step(laplacian):
    eigenvalues = np.linalg.eigvalsh(laplacian)
    eigenvalues.sort()
    lambda_2 = eigenvalues[1]
    lambda_N = eigenvalues[-1]
    alpha_star = 2.0 / (lambda_2 + lambda_N)
    gamma_star = 2.0 * lambda_2 / (lambda_2 + lambda_N)
    return alpha_star, gamma_star, lambda_2, lambda_N
```

- **File:** `docs/ARCHITECTURE-DEEP-DIVE.md` §4.5 (lines ~355–380) — pseudocode only, not a runnable file

**Consensus simulation (implicit in scaling experiment):**

The `simulate()` function in `experiments/fleet_scaling.py:77–119` implements the consensus update without explicitly computing the Laplacian or optimal step size:

```python
for node in range(n):
    neighbors = adj[node]
    if not neighbors:
        continue
    received = []
    for nb in neighbors:
        drift = abs(states[nb] - states[node])
        if drift > deadband:
            received.append(states[nb])
            tick_messages += 1
    if received:
        total = states[node] + sum(received)
        count = 1 + len(received)
        new_states[node] = total / count
```

- **File:** `experiments/fleet_scaling.py:84–115`
- **Gap:** Uses simple averaging (α = 1/count) instead of optimal α* = 2/(λ₂+λ_N). The deadband filter modifies the effective step size.

**Laplacian construction (pseudocode in architecture doc):**

```python
L = np.zeros((N, N))
for u, v in edges:
    L[u, v] -= 1; L[v, u] -= 1
    L[u, u] += 1; L[v, v] += 1
```

- **File:** `docs/ARCHITECTURE-DEEP-DIVE.md` §4.5 — pseudocode only

### 2.3 Experimental Validation

**Experiment 10 (Fleet Scaling):**
- **File:** `experiments/fleet_scaling.py:77–119` (`simulate` function)
- **Results:** Convergence ticks grow sub-linearly: `≈ 10.4 × N^{0.32}` (R² = 0.96)
- **Key data:** N=100 converges in 37 ticks, consistent with O(log²N) prediction from small-world spectral gap theory

**Experiment 9 (Partition Tolerance):**
- **File:** `experiments/partition_tolerance.py:99–123` (`run_simulation` function)
- **Results:** 13-tick convergence after partition healing, ratio 4.3× log₂(10)

### 2.4 Gaps

| Gap | Description | Severity |
|-----|-------------|----------|
| No Laplacian eigenvalue computation | `compute_optimal_step` exists only as pseudocode in the architecture doc. Neither experiment computes λ₂ or λ_N | High |
| Simulation uses ad-hoc step size | `fleet_scaling.py:112` uses `new_states[node] = total / count` (simple average), not `α* = 2/(λ₂+λ_N)` | Medium |
| Spectral gap conjecture untested | §4.3 conjectures `λ₂ ≈ Θ(1/√N)` for Laman graphs but no experiment verifies this numerically | Medium |
| No convergence rate measurement | Experiments measure convergence *ticks* but not the convergence *rate* γ* | Low |

---

## 3. Deadband Filter → Mutual Information Theorem → Deadband Check → Code

### 3.1 Mathematical Definition

**Theorem 2.1 (Zero Mutual Information Below Threshold).** If |X(t)| < ε, then I(X(t); Y(t)) = 0 where Y(t) is the correction signal.

Three-regime correction function:
- **IN BAND:** f(x) = 0 if |x| < ε (zero correction, zero information)
- **DRIFTING:** f(x) = 0.1·x if ε ≤ |x| < δ (gentle nudge)
- **DESYNCHRONIZED:** f(x) = 0.5·x if |x| ≥ δ (aggressive reset)

**Theorem 2.2 (Optimal Deadband Ratio).** Empirically, ε = δ/3 balances over-correction and under-correction costs.

*Source:* `docs/ARCHITECTURE-DEEP-DIVE.md` §2.1–2.5 (lines ~55–105)

### 3.2 Code Implementation

**Deadband correction (core agent):**

```python
def deadband_correct(self, reference_time: Fraction):
    """Correct toward reference time if drift exceeds deadband."""
    drift = reference_time - self.clock.local_time
    if abs(drift) > self.clock.deadband:
        if self.clock.correction_mode == CorrectionMode.GENTLE:
            self.correct(drift * Fraction(1, 2))
        else:
            self.correct(drift)
```

- **File:** `demo/three-agent-demo/metronome_core.py:76–83`
- **Note:** Implements two-regime logic (gentle 50% vs aggressive 100%), not three-regime. The IN BAND regime (zero correction) is the `if abs(drift) > self.clock.deadband` gate.

**Deadband default:**

```python
deadband: Fraction = Fraction(1, 10000)  # 0.0001 ticks
```

- **File:** `demo/three-agent-demo/metronome_core.py:31`

**Three-regime correction (architecture doc pseudocode):**

```python
def correction(error: Fraction, theta: MetronomeTuple) -> Fraction:
    abs_err = abs(error)
    if abs_err < theta.epsilon:
        return Fraction(0)
    elif abs_err < theta.delta:
        return Fraction(1, 10) * error  # 0.1 * error
    else:
        return Fraction(1, 2) * error   # 0.5 * error
```

- **File:** `docs/ARCHITECTURE-DEEP-DIVE.md` §2.5 — pseudocode only, not in runnable code

**Deadband in scaling experiment:**

```python
def simulate(n, edges, max_ticks=500, convergence_threshold=Fraction(1, 100), deadband=Fraction(1, 1000)):
    ...
    for nb in neighbors:
        drift = abs(states[nb] - states[node])
        if drift > deadband:
            received.append(states[nb])
```

- **File:** `experiments/fleet_scaling.py:79, 97–100`
- **Note:** Uses `deadband=Fraction(1, 1000)` (0.001), different from core agent's `Fraction(1, 10000)` (0.0001)

### 3.3 Experimental Validation

**Experiment 3 (COLLECT→SELECT→COMPILE):**
- **Source:** `experiments/collect-select-compile/` (referenced, not in workspace)
- **Results:** 141 regime transitions, 99.44% of constraints below θ=0.50 threshold
- **Sparsity data:** `docs/ARCHITECTURE-DEEP-DIVE.md` §2.2 — at θ=0.50, only 55/9812 constraints violated

**Experiment 10 (Fleet Scaling):**
- **File:** `experiments/fleet_scaling.py:97–100`
- **Deadband effect:** Average messages/tick ≈ 0.34·N, confirming most state exchanges are filtered by deadband

### 3.4 Gaps

| Gap | Description | Severity |
|-----|-------------|----------|
| Three-regime vs two-regime | Architecture doc defines 3 regimes (IN BAND / DRIFTING / DESYNCHRONIZED). Core code implements only 2 (gentle 50% / aggressive 100%). Missing: the 0.1× gentle DRIFTING regime | High |
| No ε = δ/3 enforcement | Theorem 2.2 recommends ε = δ/3 but no code enforces or validates this ratio | Medium |
| Deadband inconsistency | Core agent uses `Fraction(1, 10000)`, scaling experiment uses `Fraction(1, 1000)`, node uses `delta` parameter (default 0.0001) | Medium |
| No mutual information computation | Theorem 2.1 proves I(X;Y) = 0 below deadband but no code computes or verifies this | Low |

---

## 4. Pythagorean Fraction Arithmetic → Zero Drift Theorem → Fraction Usage → Code

### 4.1 Mathematical Definition

**Theorem 5.1 (Zero Accumulated Drift).** Direction computations using Pythagorean52 rational (Fraction) arithmetic accumulate exactly zero drift over any number of chained operations.

**Pythagorean triples:** Integer triples (a, b, c) with a² + b² = c². With c ≤ 100, there are 52 unique triples yielding 128 unique directions via sign/swap symmetries.

**Beat computation:** t_k = φ₀ + k·T where φ₀ and T are Fractions and k is an integer. All arithmetic is exact.

*Source:* `docs/ARCHITECTURE-DEEP-DIVE.md` §5.1–5.6 (lines ~395–500)

### 4.2 Code Implementation

**Fraction-based clock state:**

```python
@dataclass
class ClockState:
    true_time: Fraction = Fraction(0)
    offset: Fraction = Fraction(0)
    drift_rate: Fraction = Fraction(0)
    last_correction: Fraction = Fraction(0)
    deadband: Fraction = Fraction(1, 10000)
```

- **File:** `demo/three-agent-demo/metronome_core.py:18–32`

**Tick accumulation (exact drift):**

```python
def tick(self):
    self.clock.true_time += Fraction(1)
    self.clock.offset += self.clock.drift_rate
    self.tick_count += 1
```

- **File:** `demo/three-agent-demo/metronome_core.py:50–54`
- **Key:** `Fraction(1)` + `self.clock.drift_rate` is exact. No floating-point error.

**Drift rate initialization (Fraction conversion):**

```python
self.clock = ClockState(
    drift_rate=Fraction(drift_rate).limit_denominator(1000000),
    ...
)
```

- **File:** `demo/three-agent-demo/metronome_core.py:42`
- **Note:** `limit_denominator(1000000)` bounds denominator size for performance while maintaining precision to ~10⁻⁶

**Beat computation (architecture doc):**

```python
def compute_beat(phi_0: Fraction, T: Fraction, k: int) -> Fraction:
    return phi_0 + k * T  # Fraction arithmetic: exact
```

- **File:** `docs/ARCHITECTURE-DEEP-DIVE.md` §1.3 — pseudocode

**Scaling experiment Fraction usage:**

```python
from fractions import Fraction
states = [Fraction(i * 100, n) for i in range(n)]
```

- **File:** `experiments/fleet_scaling.py:8, 85`

**Partition experiment Fraction verification:**

```python
# All drifts are exact Fractions — zero precision loss
for a in agents:
    d = a.clock.drift
    print(f"  {a.agent_id}: drift = {d} (exact Fraction)")
```

- **File:** `experiments/partition_tolerance.py:158–161`

### 4.3 Experimental Validation

**Experiment 2 (Pythagorean48 Encoding):**
- **Source:** `experiments/pythagorean48-encoding/` (referenced, not in workspace)
- **Results:** `docs/ARCHITECTURE-DEEP-DIVE.md` §9.3
- **Key data:** Zero drift (0.00e+00) over 1,000 chained rotations vs Float32's 1.72×10⁻⁵

**Experiment 9 (Partition Tolerance):**
- **File:** `experiments/partition_tolerance.py:155–162`
- **Validation:** Prints exact Fraction drift for every agent — confirms zero precision loss

### 4.4 Gaps

| Gap | Description | Severity |
|-----|-------------|----------|
| No Pythagorean triple code | Architecture doc enumerates 52 triples but no implementation file exists in workspace | Medium |
| No direction encoding code | The 128-direction expansion from 52 triples is described mathematically but not implemented | Medium |
| `limit_denominator` introduces approximation | `Fraction(drift_rate).limit_denominator(1000000)` may not exactly represent the input float. True zero drift requires rational inputs from the start | Low |
| No beat computation function | `compute_beat()` exists only as pseudocode. The tick loop in `metronome_core.py:50` accumulates incrementally rather than computing t_k = φ₀ + k·T directly | Low |

---

## 5. Cadence Election → Longest-Uptime Protocol → Election Logic → Code

### 5.1 Mathematical Definition

**Cadence election:** The cadence caller is a transient role, not a fixed node. The highest-priority agent becomes caller, where priority is deterministic and rotatable.

Two election protocols described:
1. **Hash-based priority:** `priority = hash(f"{agent_id}:{epoch}") % N` — deterministic, rotating
2. **Longest-uptime:** Agent with longest uptime wins, ties broken by name sort

**Theorem 6.1 (Cadence BFT).** The cadence protocol tolerates f Byzantine agents iff f < N/3.

*Source:* `docs/ARCHITECTURE-DEEP-DIVE.md` §6.1–6.2 (lines ~510–570)

### 5.2 Code Implementation

**Hash-based election (architecture doc pseudocode):**

```python
def cadence_priority(agent_id: str, epoch: int, N: int) -> int:
    return hash(f"{agent_id}:{epoch}") % N

def elect_caller(agents: list[str], epoch: int) -> str:
    priorities = [(a, cadence_priority(a, epoch, len(agents))) for a in agents]
    return max(priorities, key=lambda x: x[1])[0]
```

- **File:** `docs/ARCHITECTURE-DEEP-DIVE.md` §6.1 — pseudocode only

**Longest-uptime election (distributed node):**

```python
def _run_election(self):
    """Elect cadence caller: longest uptime wins. Ties broken by name sort."""
    my_uptime = self.discovery.get_uptime()
    peers = self.discovery.get_peers()

    candidates = [(self.name, my_uptime)]
    for pname, pdata in peers.items():
        candidates.append((pname, pdata.get("uptime", 0)))

    candidates.sort(key=lambda x: (-x[1], x[0]))
    winner = candidates[0][0]

    was_caller = self.is_cadence_caller
    self.is_cadence_caller = winner == self.name
    self.cadence_caller_name = winner
```

- **File:** `demo/three-agent-demo/distributed/metronome_node.py:216–231`
- **Key:** Sort by `(-uptime, name)` — longest uptime first, name for tie-breaking. Runs every 10 ticks.

**Election scheduling:**

```python
if self.tick_count % 10 == 0:
    self._run_election()
```

- **File:** `demo/three-agent-demo/distributed/metronome_node.py:204`

### 5.3 Experimental Validation

**Experiment 9 (Partition Tolerance):**
- **File:** `experiments/partition_tolerance.py`
- **Election implied:** The partition experiment uses neighbor-based correction (each agent corrects toward neighbor average), which is the distributed analog of cadence calling

**Experiment 10 (Fleet Scaling):**
- **File:** `experiments/fleet_scaling.py`
- **Election not tested:** The scaling experiment uses centralized averaging, not distributed election

### 5.4 Gaps

| Gap | Description | Severity |
|-----|-------------|----------|
| Two election protocols | Architecture doc describes hash-based priority election; distributed node implements longest-uptime. These are different algorithms with different properties | High |
| No BFT median aggregation | Theorem 6.1 requires `weighted_median(reports)` but no code implements median-based aggregation | High |
| Election only in distributed node | `_run_election()` exists only in `metronome_node.py`, not in the core or experiments | Medium |
| No COLLECT→SELECT→COMPILE integration | The cadence caller should run the 3-phase protocol (§6.2) but no code implements this | Medium |

---

## 6. Tensor-MIDI Encoding → INT8 Saturation → Wire Format → Code

### 6.1 Mathematical Definition

The Tensor-MIDI wire format encodes fleet data into compact binary packets:
- **Header:** 8 bytes (magic 0xCA7E, type, flags, sequence, length)
- **Payload:** Variable length, values clamped to [-1.0, 1.0] then scaled to int64 for INT8 saturation semantics
- **Diagnostic:** 0–64 bytes optional

**INT8 saturation:** Values scaled to [-127, 127] with guaranteed clamping. Drift encoding: resolution = δ/127 per LSB.

**Packet types:** BEAT (0x01), DRIFT_REPORT (0x02), CADENCE_PROPOSE (0x03), CADENCE_ACK (0x04), THETA_COMMIT (0x05), SUNSET_PACKET (0x06), DIAGNOSTIC (0x07), CONSTRAINT (0x10).

*Source:* `docs/ARCHITECTURE-DEEP-DIVE.md` §7.1–7.6 (lines ~615–700)

### 6.2 Code Implementation

**Tensor-MIDI encode:**

```python
def tensor_midi_encode(payload: dict) -> bytes:
    MAGIC = 0x544D4944  # "TMID"
    VERSION = 1
    entries = []
    for k, v in payload.items():
        fv = float(v)
        fv = max(-1.0, min(1.0, fv))  # Clamp for INT8 saturation
        scaled = int(fv * (2**23 - 1))  # Scale to int64 range
        entries.append((k.encode("utf-8"), scaled))

    buf = struct.pack(">IBH", MAGIC, VERSION, len(entries))
    for key_bytes, value in entries:
        buf += struct.pack(">Bq", len(key_bytes), value)
        buf += key_bytes
    return buf
```

- **File:** `demo/three-agent-demo/distributed/metronome_node.py:38–56`

**Tensor-MIDI decode:**

```python
def tensor_midi_decode(data: bytes) -> dict:
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
        result[key] = value / (2**23 - 1)
    return result
```

- **File:** `demo/three-agent-demo/distributed/metronome_node.py:59–75`

**INT8 saturation (architecture doc pseudocode):**

```python
def saturate_int8(value: Fraction, scale: Fraction) -> int:
    quantized = int(value / scale)
    return max(-127, min(127, quantized))
```

- **File:** `docs/ARCHITECTURE-DEEP-DIVE.md` §7.4 — pseudocode only

**Round-trip test helper:**

```python
def tensor_midi_roundtrip(payload: dict) -> dict:
    encoded = tensor_midi_encode(payload)
    return tensor_midi_decode(encoded)
```

- **File:** `demo/three-agent-demo/distributed/metronome_node.py:317–320`

### 6.3 Experimental Validation

**Experiment 8 (Tensor-MIDI Wire):**
- **Status:** ❌ Not created (per `docs/ARCHITECTURE-DEEP-DIVE.md` §9.1)
- **No experimental validation of the wire format exists**

### 6.4 Gaps

| Gap | Description | Severity |
|-----|-------------|----------|
| Magic number mismatch | Architecture doc specifies `0xCA7E`; code uses `0x544D4944` ("TMID"). These are different protocols | High |
| No header structure | Architecture doc defines 8-byte header with type/flags/seq/len. Code uses 7-byte header (magic+version+entries count) — different packet format entirely | High |
| No packet types | Architecture doc defines 8 packet types (BEAT, DRIFT_REPORT, etc.). Code has a single generic encode/decode with no type discrimination | High |
| No Fraction wire encoding | Architecture doc specifies VLQ encoding for Fractions. Code encodes values as float→int64, losing exactness | Medium |
| No experiment | Experiment 8 was never created. Wire format is unvalidated | Medium |
| INT8 vs int64 | Architecture doc emphasizes INT8 (±127) saturation. Code scales to `int(fv * (2**23 - 1))` — that's 24-bit, not 8-bit | Medium |

---

## 7. Sunset/Inheritance → Memoir Compression → Tile Export → Code

### 7.1 Mathematical Definition

**Sunset protocol:** When an agent leaves the fleet, its operational history is compressed to O(log T) tiles via wavelet decomposition. The successor inherits:
1. Final calibrated θ (no BOOTSTRAP needed)
2. O(log T) tiles covering predecessor's lifetime
3. Final neighbor phases

**Memoir compression:** Fixed-depth wavelet: keep exactly ⌈log₂(T)⌉ tiles, one per resolution level. The successor can reconstruct behavior at any desired resolution.

**Four-generation lifecycle:** ε tightens by 0.7× per generation: ε₁ = δ/3, ε₂ = 0.7·δ/3, ε₃ = 0.7²·δ/3, ε₄ = 0.7³·δ/3.

*Source:* `docs/ARCHITECTURE-DEEP-DIVE.md` §8.1–8.6 (lines ~700–810)

### 7.2 Code Implementation

**Sunset payload preparation:**

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

- **File:** `demo/three-agent-demo/metronome_core.py:86–95`

**Inheritance:**

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

- **File:** `demo/three-agent-demo/metronome_core.py:97–106`

**Sunset broadcast (distributed node):**

```python
def _send_sunset(self):
    """Broadcast sunset message with inheritance data."""
    sunset_data = self.agent.sunset()
    sunset_data["type"] = "sunset"
    sunset_data["name"] = self.name
    sunset_data["is_cadence_caller"] = self.is_cadence_caller
    msg = json.dumps(sunset_data).encode()
    self._cadence_sock.sendto(msg, (MULTICAST_GROUP, self.port))
```

- **File:** `demo/three-agent-demo/distributed/metronome_node.py:250–259`

**Sunset on shutdown:**

```python
def stop(self, sunset: bool = True):
    self._running = False
    if sunset:
        self._send_sunset()
    ...
```

- **File:** `demo/three-agent-demo/distributed/metronome_node.py:167–173`

**Memoir compression (architecture doc pseudocode):**

```python
def compress_memoir_o_log_t(drift_log, max_levels=10):
    n = len(drift_log)
    coarse_tiles = []
    for level in range(min(max_levels, n.bit_length())):
        window_size = n // (2 ** level)
        start = n // 2
        window = drift_log[max(0, start - window_size//2):start + window_size//2]
        coarse_tiles.append(Tile(level=level, ...))
    return coarse_tiles  # O(log T) tiles
```

- **File:** `docs/ARCHITECTURE-DEEP-DIVE.md` §8.3 — pseudocode only

**Tile persistence (PLATO store):**

```python
class PlatoTileStore:
    def write_tile(self, agent_id, tick, key, value):
        self.conn.execute("INSERT OR REPLACE INTO tiles ...")
    def read_tile(self, agent_id, tick, key): ...
    def read_latest(self, agent_id, key): ...
```

- **File:** `demo/three-agent-demo/metronome_core.py:35–60`

### 7.3 Experimental Validation

**No dedicated experiment for sunset/inheritance.**

The sunset protocol is validated implicitly by:
- **Experiment 9 (Partition):** Uses `run_simulation` with neighbor correction — analogous to inheritance without explicit sunset
- **Core demo:** `sunset()` and `inherit()` methods are testable but no automated test validates the full lifecycle

### 7.4 Gaps

| Gap | Description | Severity |
|-----|-------------|----------|
| No memoir compression implementation | `compress_memoir_o_log_t()` exists only as pseudocode. No runnable code compresses drift logs into O(log T) tiles | High |
| No four-generation lifecycle | Architecture doc describes 4 generations with ε tightening (0.7× per generation). No code implements this | High |
| Sunset is full state dump | `sunset()` sends all clock state as dict, not O(log T) tiles. For long-lived agents, this is O(1) but not historically compressed | Medium |
| No Tile struct | Architecture doc defines `Tile` with `DriftSummary`, `regime_counts`, `health_score`. Code has no such structures — just raw key/value in SQLite | Medium |
| No wavelet decomposition | The O(log T) compression algorithm is unimplemented | Medium |

---

## 8. Byzantine Tolerance → Reputation Filter → Filtering Logic → Code

### 8.1 Mathematical Definition

**Theorem 6.1 (Cadence BFT).** The cadence protocol tolerates f Byzantine agents iff f < N/3. Uses weighted median aggregation: `φ_eff = weighted_median(reports)`.

**COLLECT→SELECT→COMPILE for Byzantine filtering:**
1. **COLLECT:** Each agent reports φ_i to cadence caller
2. **SELECT:** Discard reports outside [φ_min, φ_max] window — rejects grossly Byzantine values
3. **COMPILE:** Compute median of remaining reports

**Byzantine resistance (without full BFT):**
- Crash failure: N−1 tolerated
- Clock drift: δ bounded by three-regime correction
- Network partition: each component converges independently
- Byzantine (1 agent): requires ~3-connectivity (provided by small-world augmentation)

*Source:* `docs/ARCHITECTURE-DEEP-DIVE.md` §6.2–6.3 (lines ~540–590)

### 8.2 Code Implementation

**No explicit Byzantine filtering code exists.** The closest implementations are:

**Neighbor filtering in scaling experiment:**

```python
for nb in neighbors:
    drift = abs(states[nb] - states[node])
    if drift > deadband:
        received.append(states[nb])
```

- **File:** `experiments/fleet_scaling.py:97–100`
- **This is deadband filtering, not Byzantine filtering.** It filters by drift magnitude, not by reputation or outlier detection.

**Cadence caller state machine (architecture doc):**

```
STEADY → DRIFTING → RECOVERING → BOOTSTRAP
```

- **File:** `docs/ARCHITECTURE-DEEP-DIVE.md` §6.5 — diagram only

**Peer expiry in discovery:**

```python
def get_peers(self) -> dict:
    now = time.time()
    expired = [n for n, p in self.peers.items() if now - p["last_seen"] > 5.0]
    for n in expired:
        del self.peers[n]
```

- **File:** `demo/three-agent-demo/distributed/metronome_node.py:128–132`
- **This is liveness filtering** (remove peers not seen in 5s), not Byzantine filtering

### 8.3 Experimental Validation

**No experiment validates Byzantine tolerance.**

- Experiment 9 tests partition tolerance (network split), not Byzantine behavior (malicious agents)
- The BFT theorem (f < N/3) is cited from standard literature (Dolev-Strong, 1982) but never experimentally verified in this codebase

### 8.4 Gaps

| Gap | Description | Severity |
|-----|-------------|----------|
| **No Byzantine filtering code** | The architecture describes COLLECT→SELECT→COMPILE with outlier rejection. No code implements reputation filtering, median aggregation, or Byzantine detection | Critical |
| No weighted median | `weighted_median(reports)` is specified in §6.2 but not implemented anywhere | High |
| No reputation system | No agent tracks reputation scores or filters based on historical behavior | High |
| No Byzantine experiment | No experiment simulates faulty/malicious agents | High |
| Architecture explicitly marks this as incomplete | `docs/ARCHITECTURE-DEEP-DIVE.md` §6.3 notes "Not supported for N=9" for 3-agent Byzantine | Medium |

---

## 9. COLLECT→SELECT→COMPILE → θ Threshold → Mode Switching → Code

### 9.1 Mathematical Definition

**COLLECT→SELECT→COMPILE framework:** A universal decomposition for constraint processing:

1. **COLLECT:** Gather raw data from all agents (phase reports, drift measurements, constraint values)
2. **SELECT:** Filter by threshold θ — discard sub-threshold values (zero mutual information)
3. **COMPILE:** Aggregate remaining values into fleet decision (median for BFT, average for trusted fleet)

**θ parameter:** The universal threshold controlling the SELECT stage. Different θ values produce qualitatively different fleet behaviors (regime transitions).

**141 regime transitions** across 5 ecosystems, with F1 = 0.9996 at θ ≈ 0.50 in the flux ecosystem.

*Source:* `docs/ARCHITECTURE-DEEP-DIVE.md` §2.2–2.3 (lines ~80–95)

### 9.2 Code Implementation

**SELECT (deadband filter in scaling experiment):**

```python
# COLLECT: Gather neighbor values
for nb in neighbors:
    drift = abs(states[nb] - states[node])
    # SELECT: Filter by deadband (θ = deadband)
    if drift > deadband:
        received.append(states[nb])

# COMPILE: Average with received neighbors
if received:
    total = states[node] + sum(received)
    count = 1 + len(received)
    new_states[node] = total / count
```

- **File:** `experiments/fleet_scaling.py:91–115`
- **θ parameter:** `deadband = Fraction(1, 1000)` (line 79)

**SELECT (deadband filter in core agent):**

```python
def deadband_correct(self, reference_time: Fraction):
    drift = reference_time - self.clock.local_time
    if abs(drift) > self.clock.deadband:  # SELECT: θ = deadband
        if self.clock.correction_mode == CorrectionMode.GENTLE:
            self.correct(drift * Fraction(1, 2))  # COMPILE: gentle
        else:
            self.correct(drift)                     # COMPILE: aggressive
```

- **File:** `demo/three-agent-demo/metronome_core.py:76–83`

**Three-regime mode switching (architecture doc):**

```python
def correction(error: Fraction, theta: MetronomeTuple) -> Fraction:
    abs_err = abs(error)
    if abs_err < theta.epsilon:     # IN BAND
        return Fraction(0)
    elif abs_err < theta.delta:     # DRIFTING
        return Fraction(1, 10) * error
    else:                           # DESYNCHRONIZED
        return Fraction(1, 2) * error
```

- **File:** `docs/ARCHITECTURE-DEEP-DIVE.md` §2.5 — pseudocode only

**State machine transitions (architecture doc):**

| Transition | Condition | Code Location |
|-----------|-----------|---------------|
| STEADY → DRIFTING | \|error\| > ε | `metronome_core.py:79` — `if abs(drift) > self.clock.deadband` |
| DRIFTING → STEADY | \|error\| < ε | Implicit — no correction applied |
| DRIFTING → RECOVERING | \|error\| ≥ δ | Not implemented |
| RECOVERING → BOOTSTRAP | Timeout 4T | Not implemented |

### 9.3 Experimental Validation

**Experiment 3 (COLLECT→SELECT→COMPILE):**
- **Source:** `experiments/collect-select-compile/` (referenced, not in workspace)
- **Results:** `docs/ARCHITECTURE-DEEP-DIVE.md` §2.2, §9.4
- **Key data:**

```
θ = 0.01:  9,752 violations
θ = 0.10:  1,241 violations
θ = 0.50:  55 violations (F1 = 0.9996)
θ = 1.00:  3 violations
```

**Experiment 10 (implicit COLLECT→SELECT→COMPILE):**
- **File:** `experiments/fleet_scaling.py:91–115`
- The simulation loop is a COLLECT→SELECT→COMPILE pipeline with θ = deadband

### 9.4 Gaps

| Gap | Description | Severity |
|-----|-------------|----------|
| No dedicated COLLECT→SELECT→COMPILE implementation | The framework is described as universal but no single code module implements it as a reusable pattern | Medium |
| No θ sweep in experiments | Experiment 3 sweeps θ but the experiment code is not in the workspace. Experiments 9/10 use fixed deadband values | Medium |
| No regime transition detection | The 141 regime transitions are measured in Experiment 3 but no code detects or logs regime transitions in real-time | Low |
| Three-regime incomplete in code | Architecture doc has 3 regimes; code has 2. The DRIFTING gentle regime (0.1× correction) is missing | High |

---

## Appendix A: Summary Table

| # | Concept | Math Source | Code File | Experiment | Completeness |
|---|---------|-------------|-----------|------------|-------------|
| 1 | Laman rigidity | ARCH-DEEP-DIVE §3 | `fleet_scaling.py:41`, `partition_tolerance.py:27` | Exp 1, 9, 10 | ⚠️ 80% — Henneberg works, no pebble game |
| 2 | Spectral gap | ARCH-DEEP-DIVE §4 | None (pseudocode only) | Exp 9, 10 (implicit) | ⚠️ 40% — no eigenvalue computation |
| 3 | Deadband filter | ARCH-DEEP-DIVE §2 | `metronome_core.py:76`, `fleet_scaling.py:97` | Exp 3, 10 | ⚠️ 70% — two-regime, not three |
| 4 | Fraction arithmetic | ARCH-DEEP-DIVE §5 | `metronome_core.py:18–54`, `fleet_scaling.py:85` | Exp 2, 9 | ✅ 90% — zero drift proven and tested |
| 5 | Cadence election | ARCH-DEEP-DIVE §6 | `metronome_node.py:216` | Exp 9 (implicit) | ⚠️ 50% — uptime election only, no BFT |
| 6 | Tensor-MIDI | ARCH-DEEP-DIVE §7 | `metronome_node.py:38–75` | None (Exp 8 not created) | ⚠️ 40% — different format than spec |
| 7 | Sunset/inheritance | ARCH-DEEP-DIVE §8 | `metronome_core.py:86–106`, `metronome_node.py:250` | None | ⚠️ 50% — basic transfer, no memoir |
| 8 | Byzantine tolerance | ARCH-DEEP-DIVE §6.2 | None | None | ❌ 10% — spec only |
| 9 | COLLECT→SELECT→COMPILE | ARCH-DEEP-DIVE §2.2 | `fleet_scaling.py:91–115` (implicit) | Exp 3 (external) | ⚠️ 50% — implicit in experiments |

---

## Appendix B: File Reference Index

| File | Concepts Covered | Lines of Code |
|------|-----------------|---------------|
| `docs/ARCHITECTURE-DEEP-DIVE.md` | All 9 concepts (definitions + pseudocode) | ~1,744 lines |
| `demo/three-agent-demo/metronome_core.py` | Fraction arithmetic, deadband, sunset/inheritance | ~100 lines |
| `demo/three-agent-demo/distributed/metronome_node.py` | Tensor-MIDI, cadence election, sunset broadcast, peer discovery | ~335 lines |
| `experiments/fleet_scaling.py` | Laman construction, COLLECT→SELECT→COMPILE (implicit), spectral convergence (implicit) | ~230 lines |
| `experiments/partition_tolerance.py` | Laman construction, Fraction validation, partition recovery | ~170 lines |

---

*End of Math-to-Code Map. 9 concepts mapped, 4 gaps at high/critical severity, 1 concept (Byzantine tolerance) essentially unimplemented.*

*Forgemaster ⚒️ · 2026-05-22*
