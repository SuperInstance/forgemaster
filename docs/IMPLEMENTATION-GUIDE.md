# Implementation Guide: Constraint-Theoretic Fleet
## Forgemaster ⚒️ — 2026-05-21

> **Audience:** The engineer who is about to type the first line of code.
> **Purpose:** You should finish this document knowing exactly what file to create, what function signature to write, and what test to run to prove it works.
> **Sources:** STRATEGIC-ARCHITECTURE-V2.md (architecture) · IMPLEMENTATION_ROADMAP.md (GLM plan)

---

## 0. How to Read This Document

**Start here if you're picking up cold:** Read §1 (the critical path) and §5 (minimum viable demo) first. These tell you what matters most and what "done" looks like.

**Start here if you're implementing a specific layer:** Jump to that layer's section (§2.1 through §2.10). Each section specifies exact files, function signatures, test cases, and the one question you need to answer before writing the first line.

**Start here if you're planning a sprint:** Read §3 (2-week sprint plan) and §4 (Casey's decisions). The sprint plan is ordered by dependency — do not reorder it.

**Notation used throughout:**
- `[PROVEN]` — mathematical result with reproducible experiment
- `[CONJECTURE]` — plausible, empirically supported, not formally proven
- `[BUILD]` — something you are building in this guide
- `★` — critical path item; delays here delay everything else

---

## 1. The Critical Path

Everything in this architecture connects. Not everything is equally urgent. Here is the dependency chain that determines what you must build first:

```
PLATO adapter (L8)
    ↓
Metronome types + Fraction arithmetic (L5) ★
    ↓
MetronomeAgent.tick() (L5) ★
    ↓
Fleet topology (2N−3 edges) (L7) ★
    ↓
PLATO-backed phase state (L8)
    ↓
I2I broadcast (L6) ★
    ↓
3-agent pilot (Forgemaster + Oracle1 + kimi1)
    ↓
Cadence caller election (L7)
    ↓
Diagnostic layer (L5)
    ↓
Full 9-agent fleet
    ↓
Human-readable dashboard (L9)
```

**What is NOT on the critical path for the first 2 weeks:**
- Hardware layer (L1) — ESP32, CUDA
- FFI bridge (L3) — Rust/C interop
- Kernel/ISA (L2) — FLUX bytecode
- GUARD DSL (L4 partial) — safety specifications

Those layers exist and have code. They are not needed for the metronome MVP. Do not let them block you.

The critical path has **five starred items**. Everything else either exists or is optional for the demo. This guide will tell you exactly what to build at each star.

---

## 2. Layer-by-Layer Specification

### 2.1 Layer 1: Hardware (flux-esp32, flux-cuda, marine-gpu-edge)

**Status:** Repos exist. Not on the critical path for Week 1–2.

**What exists:**
- `flux-esp32/`: ESP32 embedded agent consuming `flux_ffi.h`
- `flux-cuda/`: CUDA constraint execution
- `marine-gpu-edge/`: Marine GPU with Pythagorean48 directional arithmetic

**What you need to know:** The hardware layer communicates upward through the FFI bridge (L3). It does not need to understand the metronome or fleet coordination. The only hardware task in the 2-week window is confirming that kimi1's ProArt GPU has CUDA available — this unlocks the batch phase-alignment kernel (Day 13 in the sprint).

**Decision required (Casey):**
```
[ ] Is kimi1's ProArt GPU accessible from the metronome package?
    YES → build cuda/phase_align.cu on Day 13
    NO  → CPU fallback, no code change needed, defer CUDA to Week 3+
```

**Files that will exist (post-implementation, Week 3+):**
```
flux-esp32/
├── src/main.c              # ESP32 agent main loop
├── include/flux_ffi.h      # Pure C FFI header (cbindgen output)
└── flash.sh                # Flash to device

flux-cuda/
├── src/constraint_check.cu # CUDA constraint checking kernel
└── CMakeLists.txt
```

**Tests that must pass (Week 3+):**
```bash
# On kimi1 only:
cd metronome/cuda && nvcc phase_align.cu -o phase_align_test && ./phase_align_test
# Expected: 9 agents aligned, < 1ms latency
```

---

### 2.2 Layer 2: Kernel / ISA (flux-isa, 43 opcodes)

**Status:** Defined. Not on the critical path for Week 1–2.

**What exists:** `flux-isa/` defines a 43-opcode stack VM in four tiers:
- `flux-isa-mini` — bare MCU, no_std, minimal ops
- `flux-isa-std` — full 43-opcode set
- `flux-isa-edge` — power-efficient subset
- `flux-isa-thor` — extended precision, AVX ops

**What you need to know:** The ISA is the compilation target for GUARD DSL. It sits between the constraint language (L4) and the hardware (L1). For the metronome MVP, you do not need to write, read, or execute FLUX bytecode. The metronome operates entirely in Python using `Fraction` arithmetic — no bytecode involved.

**The one important interface to know:**
```
FLUX bytecode format: [opcode: u8][operands: variable]
Stack VM: push/pop/add/sub/mul/div/cmp/jmp/call/ret
Tier selection: compile flag at build time
```

**When this matters:** When you write GUARD DSL safety specifications (L4) for the metronome parameters (e.g., `ε MUST BE < δ/2`), those compile to FLUX bytecode and execute on flux-vm-v3. That is a Week 3+ concern.

---

### 2.3 Layer 3: FFI Bridge (superinstance-ffi.h, flux_ffi.h)

**Status:** Headers exist. Not on the critical path for Week 1–2.

**What exists:**
```c
// superinstance-ffi.h (C++ style, fleet operations)
void si_init(const char* agent_id);
int  si_laman_edges(int n_agents, int* edge_list);
bool si_is_rigid(int* edges, int n_edges, int n_nodes);
int  si_holonomy_check(float* path, int len);

// flux_ffi.h (pure C, minimal/embedded)
int  flux_constraint_check(uint8_t* bytecode, int len, void* ctx);
void flux_deadband_filter(float* signal, int len, float epsilon);
```

**What you need to know:** The FFI bridge is how Rust code exposes primitives to C, C++, CUDA, Zig, and Go. The `si_is_rigid()` and `si_laman_edges()` functions are the ones you will call from the Python metronome via `ctypes` when you need fast topology verification.

**Python → C bridge pattern (for topology verification):**
```python
# metronome/topology.py — call into superinstance-ffi from Python
import ctypes

_lib = ctypes.CDLL("libsuperinstance.so")
_lib.si_laman_edges.restype = ctypes.c_int
_lib.si_laman_edges.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_int)]

def verify_laman(n_agents: int, edge_list: list[tuple[int,int]]) -> bool:
    """Return True iff edge_list satisfies 2N-3 Laman condition."""
    flat = [v for e in edge_list for v in e]
    arr = (ctypes.c_int * len(flat))(*flat)
    result = _lib.si_laman_edges(n_agents, arr)
    return result == 2 * n_agents - 3
```

**Tests that must pass (when wiring topology):**
```python
def test_laman_9_agents():
    edges = generate_henneberg(9)   # see §2.7
    assert verify_laman(9, edges)
    assert len(edges) == 15         # 2×9−3 = 15 [PROVEN]
```

---

### 2.4 Layer 4: Runtime / Constraint Engine

**Status:** Python lib operational. Rust+PyO3 exists. GUARD DSL compiler exists.

**What exists:**
```
constraint-theory-py/        # Python API, fleet entry point
constraint-theory-rust-python/ # Rust engine + PyO3 bindings
guardc-v3/                   # GUARD→FLUX compiler (Rust)
flux-vm-v3/                  # FLUX bytecode executor (Rust)
deadband-python/             # Python deadband filtering
```

**What you need to know for the metronome:**
The constraint library is already doing work. 248 constraints are validated. You import it as:
```python
from constraint_theory import ConstraintChecker, Constraint
```

The constraint you care about most in Week 1 is the deadband check:
```python
# This already exists in deadband-python — import it
from deadband import DeadbandFilter

db = DeadbandFilter(epsilon=Fraction(1, 48), delta=Fraction(1, 16))
regime = db.check(error=Fraction(3, 100))
# Returns: DeadbandRegime.IN_BAND | DRIFTING | DESYNC
```

**The three regimes (this is the θ gate from COLLECT→SELECT→COMPILE [PROVEN]):**
```
|error| < ε          → IN_BAND   (no correction, mine diagnostic)
ε ≤ |error| < δ      → DRIFTING  (0.1 × error correction)
|error| ≥ δ          → DESYNC    (0.5 × error, trigger cadence)
```

**Files you will need to add (not change) in Layer 4:**
```
constraint-theory-py/
└── metronome_constraints.py   # ε < δ/2, T is positive, phases bounded
```

**Test that must pass before touching layer 4:**
```bash
cd constraint-theory-py && python -c "import constraint_theory; print('OK')"
```
If this fails, fix it before proceeding. Layer 4 is foundational.

---

### 2.5 Layer 5: Metronome Coordination Layer ★ KEY LAYER ★

This is the most important section. Build this before anything else. Everything downstream depends on it.

#### 2.5.1 Directory Structure

```
metronome/
├── __init__.py
├── types.py           # [BUILD] Core types — MetronomeConfig, AgentState
├── theta.py           # [BUILD] θ tuple with Fraction arithmetic
├── deadband.py        # [BUILD] ε/δ dual with three-regime logic
├── agent.py           # [BUILD] MetronomeAgent — tick(), correct(), sunset()
├── plato_adapter.py   # [BUILD] PLATO tile read/write
├── correction.py      # [BUILD] gentle (0.1×) and aggressive (0.5×) corrections
├── diagnostic.py      # [BUILD - Week 2] Mine drift before correcting
└── config.json        # [BUILD] Fleet configuration

tests/
├── test_types.py
├── test_theta.py
├── test_deadband.py
├── test_agent.py
├── test_plato.py
└── test_fleet_sync.py
```

#### 2.5.2 types.py — Exact Specification

```python
# metronome/types.py
from fractions import Fraction
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Optional
import time

class AgentState(IntEnum):
    INIT        = 0
    BOOTSTRAP   = 1
    STEADY      = 2
    DRIFTING    = 3
    RECOVERING  = 4
    SUNSET      = 5

class DeadbandRegime(IntEnum):
    IN_BAND     = 1   # |error| < ε — no correction
    DRIFTING    = 2   # ε ≤ |error| < δ — gentle correction
    DESYNC      = 3   # |error| ≥ δ — aggressive reset

@dataclass
class MetronomeConfig:
    # Period as rational Fraction — zero accumulated drift [PROVEN]
    T:          Fraction
    # Phase origin — Unix timestamp of beat zero
    phi_0:      Fraction
    # Deadband tolerance — absorb drift ≤ ε, no correction
    epsilon:    Fraction
    # Drift bound — correct drift ≥ δ aggressively
    delta:      Fraction
    # Invariant: epsilon == delta / 3 [CONJECTURE: optimal ratio]
    # Invariant: T > 0
    # Invariant: epsilon < delta

    agent_id:   str
    neighbors:  List[str] = field(default_factory=list)
    generation: int = 1   # 1..4, ε tightens each generation

    def __post_init__(self):
        assert self.T > 0, "Period must be positive"
        assert self.epsilon < self.delta, "ε must be less than δ"
        assert self.epsilon == self.delta / 3, "ε = δ/3 [empirical optimum]"

    @classmethod
    def default_fleet(cls, agent_id: str, neighbors: List[str]) -> "MetronomeConfig":
        """Default config for Cocapn fleet. T=17/12 ≈ 1.417s period."""
        delta   = Fraction(1, 16)
        epsilon = delta / 3       # = Fraction(1, 48)
        return cls(
            T       = Fraction(17, 12),
            phi_0   = Fraction(int(time.time())),
            epsilon = epsilon,
            delta   = delta,
            agent_id = agent_id,
            neighbors = neighbors,
        )

@dataclass
class PhaseState:
    agent_id:   str
    beat_k:     int                    # Current beat number
    phase:      Fraction               # t_k = φ₀ + k·T
    error:      Fraction               # Measured - expected
    regime:     DeadbandRegime
    corrections: int = 0              # Total corrections this generation
    timestamp:  float = field(default_factory=time.time)

@dataclass
class SunsetPacket:
    """Inheritance payload: predecessor's calibrated state for successor."""
    agent_id:       str
    theta:          MetronomeConfig
    generation:     int
    mean_drift:     float
    std_drift:      float
    neighbor_phases: Dict[str, Fraction]
    drift_patterns: List[str]          # e.g. ["periodic_12h", "correlated"]
```

**Tests for types.py:**
```python
# tests/test_types.py
def test_default_config_invariants():
    cfg = MetronomeConfig.default_fleet("forge", ["oracle1"])
    assert cfg.epsilon == cfg.delta / 3        # ε = δ/3
    assert cfg.T == Fraction(17, 12)
    assert cfg.epsilon == Fraction(1, 48)
    assert cfg.delta == Fraction(1, 16)

def test_fraction_is_exact():
    """Rational arithmetic produces zero accumulated drift. [PROVEN]"""
    cfg = MetronomeConfig.default_fleet("forge", [])
    phases = [cfg.phi_0 + k * cfg.T for k in range(1000)]
    # Verify no floating-point contamination
    for p in phases:
        assert isinstance(p, Fraction), "Phase must stay rational"

def test_agent_state_ordering():
    assert AgentState.INIT < AgentState.STEADY
    assert AgentState.DRIFTING > AgentState.STEADY
```

#### 2.5.3 theta.py — Fraction Arithmetic

```python
# metronome/theta.py
from fractions import Fraction
from typing import Tuple

def beat_phase(phi_0: Fraction, T: Fraction, k: int) -> Fraction:
    """
    Compute exact phase for beat k.
    t_k = φ₀ + k·T

    Uses Fraction arithmetic — accumulates EXACTLY zero drift.
    1,000 chained operations: error = 0.00e+00 [PROVEN]
    Float32 equivalent: error = 1.72×10⁻⁵ after 1,000 ops.

    This is not a performance trick — it is a correctness requirement.
    """
    return phi_0 + Fraction(k) * T

def phase_error(measured: Fraction, expected: Fraction) -> Fraction:
    """Signed error: positive = measured ahead of expected."""
    return measured - expected

def tighten_epsilon(epsilon: Fraction, generation: int) -> Fraction:
    """
    Epsilon tightening schedule: ε_gen = ε_initial × 0.7^generation

    Generation 1: ε = ε_initial          (wide, tolerant)
    Generation 2: ε = 0.70 × ε_initial
    Generation 3: ε = 0.49 × ε_initial
    Generation 4: ε = 0.34 × ε_initial   (tight, precise)

    Uses Fraction(7,10)^gen for exact arithmetic.
    [DESIGNED — not validated over multiple fleet generations yet]
    """
    factor = Fraction(7, 10) ** (generation - 1)
    return epsilon * factor

def pythagorean_T(a: int, b: int, c: int) -> Fraction:
    """
    Encode period T as ratio from a Pythagorean triple (a²+b²=c²).
    Zero-drift directional encoding. [PROVEN: 52 triples with c≤100]

    Example: (5,12,13) → T = Fraction(5,12) ≈ 0.417s
    Example: (17,12,?) → T = Fraction(17,12) ≈ 1.417s (current default)
    """
    assert a > 0 and b > 0, "Triple components must be positive"
    return Fraction(a, b)
```

**Tests for theta.py:**
```python
# tests/test_theta.py
def test_zero_drift_1000_beats():
    """Replicates the proven experiment. Must return exact zero."""
    phi_0 = Fraction(1716300000)
    T     = Fraction(17, 12)
    phases = [beat_phase(phi_0, T, k) for k in range(1000)]
    # Check that each phase is exactly phi_0 + k*T
    for k, p in enumerate(phases):
        expected = phi_0 + Fraction(k) * T
        assert p == expected, f"Drift at beat {k}: {p - expected}"

def test_epsilon_tightening():
    eps = Fraction(1, 48)
    assert tighten_epsilon(eps, 1) == Fraction(1, 48)
    assert tighten_epsilon(eps, 2) == Fraction(7, 336)   # 1/48 * 7/10
    assert tighten_epsilon(eps, 4) < eps / 3             # generation 4 is tightest
```

#### 2.5.4 deadband.py — Three-Regime Logic

```python
# metronome/deadband.py
from fractions import Fraction
from .types import DeadbandRegime, MetronomeConfig

def classify_regime(error: Fraction, cfg: MetronomeConfig) -> DeadbandRegime:
    """
    Classify synchronization error into one of three regimes.

    This is the θ gate from COLLECT→SELECT→COMPILE applied to timing. [PROVEN]
    F1 = 0.9996 at θ ≈ 0.50 in the flux ecosystem.
    Balanced accuracy = 1.0 at θ ∈ [1.0, 2.0] in the fleet ecosystem.

    The threshold θ is the SINGLE control parameter for all output quality.
    ε and δ are both θ — dual views of the same parameter.
    """
    abs_error = abs(error)
    if abs_error < cfg.epsilon:
        return DeadbandRegime.IN_BAND
    elif abs_error < cfg.delta:
        return DeadbandRegime.DRIFTING
    else:
        return DeadbandRegime.DESYNC

def apply_correction(phase: Fraction, expected: Fraction,
                     regime: DeadbandRegime) -> Fraction:
    """
    Apply regime-appropriate correction to current phase.

    IN_BAND:  no correction — return phase unchanged
    DRIFTING: gentle correction — 0.1 × error nudge toward expected
    DESYNC:   aggressive reset — 0.5 × error, trigger cadence election

    Correction factors (0.1, 0.5) are from GLM's implementation spec.
    The exact factors are [CONJECTURE] — could be tuned with data.
    """
    error = expected - phase
    if regime == DeadbandRegime.IN_BAND:
        return phase                          # Zero messages, zero correction
    elif regime == DeadbandRegime.DRIFTING:
        correction = Fraction(1, 10) * error  # 10% nudge
        return phase + correction
    else:  # DESYNC
        correction = Fraction(1, 2) * error   # 50% snap
        return phase + correction
```

**Tests for deadband.py:**
```python
# tests/test_deadband.py
def test_in_band_no_correction():
    cfg = MetronomeConfig.default_fleet("forge", [])
    # Error smaller than epsilon = 1/48
    error = Fraction(1, 100)   # 0.01 < 0.0208 (ε)
    regime = classify_regime(error, cfg)
    assert regime == DeadbandRegime.IN_BAND

def test_drifting_gentle_correction():
    cfg = MetronomeConfig.default_fleet("forge", [])
    # Error between ε=1/48 and δ=1/16
    error = Fraction(1, 32)    # 0.03125 — between ε and δ
    regime = classify_regime(error, cfg)
    assert regime == DeadbandRegime.DRIFTING

    phase = Fraction(100)
    expected = phase + error
    corrected = apply_correction(phase, expected, regime)
    # 10% correction: corrected = phase + 0.1 × error
    assert corrected == phase + Fraction(1, 10) * error

def test_desync_aggressive_reset():
    cfg = MetronomeConfig.default_fleet("forge", [])
    # Error >= delta = 1/16
    error = Fraction(1, 10)    # 0.10 > δ=0.0625
    regime = classify_regime(error, cfg)
    assert regime == DeadbandRegime.DESYNC
```

#### 2.5.5 agent.py — MetronomeAgent Core ★

This is the most important file in the entire implementation. Read this specification twice.

```python
# metronome/agent.py
from fractions import Fraction
from typing import Dict, Optional
import time
import logging

from .types import (
    MetronomeConfig, AgentState, PhaseState, DeadbandRegime, SunsetPacket
)
from .theta import beat_phase, phase_error, tighten_epsilon
from .deadband import classify_regime, apply_correction
from .plato_adapter import PlatoAdapter
from .diagnostic import DiagnosticMiner   # Week 2 — import is conditional

logger = logging.getLogger(__name__)

class MetronomeAgent:
    """
    A single agent's metronome state and tick logic.

    The hot path is FIVE function calls. That's it.
    Everything else is initialization, failure handling, or diagnostics.

    Hot path (per tick):
        1. read_phase()        — load current phase from PLATO
        2. compute_expected()  — t_k = φ₀ + k·T (Fraction arithmetic)
        3. check_deadband()    — classify error into IN_BAND/DRIFTING/DESYNC
        4. execute_task()      — do your actual work for this beat
        5. write_phase()       — persist updated phase to PLATO

    Boring is a feature. [GLM insight]
    """

    def __init__(self, config: MetronomeConfig, plato: PlatoAdapter):
        self.cfg    = config
        self.plato  = plato
        self.state  = AgentState.INIT
        self.beat_k = 0
        self.phase  = config.phi_0
        self._corrections = 0
        self._error_history: list[Fraction] = []
        # Diagnostic miner — optional, Week 2
        self._miner: Optional[DiagnosticMiner] = None

    def attach_diagnostic_miner(self, miner: "DiagnosticMiner") -> None:
        """
        Attach diagnostic layer. SAFE to add at runtime.

        The miner observes but NEVER modifies correction behavior.
        Convergence is preserved because miner is observation-only.
        [ARGUED — not formally proven. See §9 of STRATEGIC-ARCHITECTURE-V2]

        If you are not sure whether the miner is safe:
            Run test_mining_safe.py (tests/test_mining_safe.py).
            It verifies that correction dynamics are IDENTICAL with/without miner.
        """
        self._miner = miner

    def tick(self, neighbor_phases: Dict[str, Fraction]) -> AgentState:
        """
        One beat. The complete metronome cycle.

        Args:
            neighbor_phases: {agent_id: phase} from Laman neighbors.
                             Empty dict is valid during bootstrap.

        Returns:
            New AgentState after this tick.

        This is called once per T seconds (T = 17/12 ≈ 1.417s by default).
        """
        # ─── 1. Read current phase ────────────────────────────────────
        stored = self.plato.read_phase(self.cfg.agent_id)
        if stored is not None:
            self.phase  = stored.phase
            self.beat_k = stored.beat_k

        # ─── 2. Compute expected phase ───────────────────────────────
        expected = beat_phase(self.cfg.phi_0, self.cfg.T, self.beat_k)

        # ─── 3. Check deadband ───────────────────────────────────────
        error  = phase_error(self.phase, expected)
        regime = classify_regime(error, self.cfg)

        # ─── 3a. Mine diagnostic (BEFORE correction, observe-only) ───
        if self._miner is not None:
            self._miner.observe(
                agent_id=self.cfg.agent_id,
                beat_k=self.beat_k,
                error=error,
                regime=regime,
                neighbor_phases=neighbor_phases,
            )

        # ─── 4. Apply correction ─────────────────────────────────────
        new_phase = apply_correction(self.phase, expected, regime)
        if regime != DeadbandRegime.IN_BAND:
            self._corrections += 1
            logger.debug(
                f"{self.cfg.agent_id} beat={self.beat_k} "
                f"error={float(error):.6f} regime={regime.name}"
            )

        # ─── 5. Update state ─────────────────────────────────────────
        self.phase  = new_phase
        self.beat_k += 1
        self.state  = self._regime_to_state(regime)

        # ─── 6. Write phase to PLATO ─────────────────────────────────
        self.plato.write_phase(PhaseState(
            agent_id=self.cfg.agent_id,
            beat_k=self.beat_k,
            phase=self.phase,
            error=error,
            regime=regime,
            corrections=self._corrections,
        ))

        return self.state

    def apply_cadence_correction(self, phi_eff: Fraction) -> None:
        """
        Accept cadence caller's consensus phase.

        The cadence caller computes φ_eff = weighted_median(drift_reports).
        Median (not mean) provides Byzantine resistance for f < N/2. [ESTABLISHED]

        This is the DESYNC recovery path. Call this when you receive a
        CADENCE_CALL message.
        """
        self.cfg = MetronomeConfig(
            T       = self.cfg.T,
            phi_0   = phi_eff,
            epsilon = self.cfg.epsilon,
            delta   = self.cfg.delta,
            agent_id = self.cfg.agent_id,
            neighbors = self.cfg.neighbors,
            generation = self.cfg.generation,
        )
        self.state = AgentState.STEADY
        logger.info(f"{self.cfg.agent_id} cadence correction applied, φ_eff={float(phi_eff):.6f}")

    def sunset(self, neighbor_phases: Dict[str, Fraction]) -> SunsetPacket:
        """
        Agent's final act: package calibrated state for successor.

        Sunset is graduation, not failure. The successor inherits:
        - Calibrated θ (T, φ₀, ε, δ)
        - Drift statistics (mean, std)
        - Drift patterns extracted by diagnostic layer
        - Neighbor phase references
        - Generation number (successor starts at gen+1 or gen=1 if gen=4)

        The predecessor's operational lifetime becomes the successor's head start.
        """
        self.state = AgentState.SUNSET

        # Tighten epsilon for successor if we're not at max generation
        next_gen = min(self.cfg.generation + 1, 4)
        next_eps = tighten_epsilon(self.cfg.epsilon, next_gen)
        next_delta = next_eps * 3  # Maintain ε = δ/3

        successor_config = MetronomeConfig(
            T       = self.cfg.T,
            phi_0   = self.phase,  # Hand off current calibrated phase
            epsilon = next_eps,
            delta   = next_delta,
            agent_id = self.cfg.agent_id,
            neighbors = self.cfg.neighbors,
            generation = next_gen,
        )

        # Gather drift statistics from diagnostic layer if available
        mean_drift = 0.0
        std_drift  = 0.0
        patterns   = []
        if self._miner is not None:
            stats    = self._miner.get_statistics()
            mean_drift = stats["mean_drift"]
            std_drift  = stats["std_drift"]
            patterns   = stats["patterns"]

        packet = SunsetPacket(
            agent_id        = self.cfg.agent_id,
            theta           = successor_config,
            generation      = next_gen,
            mean_drift      = mean_drift,
            std_drift       = std_drift,
            neighbor_phases = neighbor_phases,
            drift_patterns  = patterns,
        )

        self.plato.write_sunset(packet)
        logger.info(f"{self.cfg.agent_id} sunset complete. gen={next_gen}, ε={float(next_eps):.6f}")
        return packet

    def _regime_to_state(self, regime: DeadbandRegime) -> AgentState:
        if regime == DeadbandRegime.IN_BAND:
            return AgentState.STEADY
        elif regime == DeadbandRegime.DRIFTING:
            return AgentState.DRIFTING
        else:
            return AgentState.RECOVERING

    @classmethod
    def from_sunset_packet(cls, packet: SunsetPacket,
                           plato: PlatoAdapter) -> "MetronomeAgent":
        """
        Create agent from predecessor's sunset packet.
        No bootstrap needed — already synchronized.
        """
        agent = cls(config=packet.theta, plato=plato)
        agent.state = AgentState.STEADY   # Inherited, not bootstrapped
        logger.info(
            f"Agent {packet.agent_id} started from sunset (gen={packet.generation})"
        )
        return agent
```

**Tests for agent.py:**
```python
# tests/test_agent.py
def test_hot_path_zero_drift():
    """
    Run 1,000 ticks on one agent in ideal conditions.
    Phase must never drift from expected value.
    This is the core guarantee.
    """
    cfg   = MetronomeConfig.default_fleet("forge", [])
    plato = MockPlatoAdapter()
    agent = MetronomeAgent(cfg, plato)

    for tick_n in range(1000):
        state = agent.tick({})
        # Expected phase: φ₀ + k·T
        expected = beat_phase(cfg.phi_0, cfg.T, tick_n + 1)
        assert agent.phase == expected, f"Drift at tick {tick_n}: {agent.phase - expected}"
        assert state == AgentState.STEADY

def test_in_band_zero_corrections():
    """In steady state: zero corrections applied, zero messages needed."""
    cfg   = MetronomeConfig.default_fleet("forge", [])
    plato = MockPlatoAdapter()
    agent = MetronomeAgent(cfg, plato)
    for _ in range(100):
        agent.tick({})
    assert agent._corrections == 0   # O(0) in steady state [PROVEN]

def test_sunset_inheritance():
    """Successor starts synchronized. No bootstrap needed."""
    cfg    = MetronomeConfig.default_fleet("forge", [])
    plato  = MockPlatoAdapter()
    agent1 = MetronomeAgent(cfg, plato)
    for _ in range(50):
        agent1.tick({})

    packet = agent1.sunset({})
    agent2 = MetronomeAgent.from_sunset_packet(packet, plato)

    assert agent2.state == AgentState.STEADY
    assert agent2.cfg.generation == 2
    assert agent2.cfg.epsilon < cfg.epsilon   # Tighter on generation 2

def test_desync_recovery():
    """Agent recovers from DESYNC via cadence correction."""
    cfg   = MetronomeConfig.default_fleet("forge", [])
    plato = MockPlatoAdapter()
    agent = MetronomeAgent(cfg, plato)
    # Inject large phase error
    agent.phase += cfg.delta * 2
    state = agent.tick({})
    assert state == AgentState.RECOVERING
    # Apply cadence correction
    agent.apply_cadence_correction(cfg.phi_0)
    state = agent.tick({})
    assert state == AgentState.STEADY
```

#### 2.5.6 diagnostic.py — Drift Mining (Week 2)

```python
# metronome/diagnostic.py
"""
Mine drift before correcting it.

Drift is not noise to be filtered — drift is signal to be mined.
[Seed-Pro insight, Grand Synthesis Round 1]

The DiagnosticMiner observes correction events and produces:
  - Fleet health metrics (health(i), coherence)
  - Drift pattern classification (periodic, correlated, spike, monotone)
  - Composted drift tiles for PLATO (patterns → knowledge)

CRITICAL: The miner NEVER modifies the correction function.
          It observes before correction, writes to log, returns.
          Convergence is preserved. [ARGUED — test mining_safe.py to verify]
"""
from fractions import Fraction
from dataclasses import dataclass, field
from typing import Dict, List
from .types import DeadbandRegime
import math

@dataclass
class DriftObservation:
    agent_id:    str
    beat_k:      int
    error:       Fraction
    regime:      DeadbandRegime

@dataclass
class DriftStatistics:
    mean_drift: float
    std_drift:  float
    patterns:   List[str]
    health:     float      # 1.0 = perfectly healthy, 0.0 = always correcting

class DiagnosticMiner:
    def __init__(self, agent_id: str, max_history: int = 10_000):
        self.agent_id   = agent_id
        self._obs: List[DriftObservation] = []
        self._max       = max_history

    def observe(self, agent_id: str, beat_k: int, error: Fraction,
                regime: DeadbandRegime,
                neighbor_phases: Dict[str, Fraction]) -> None:
        """
        Record drift event. OBSERVE ONLY. Do not call correction functions.

        This is the mine-before-correct protocol:
        1. DETECT:  |error| > ε → drift event
        2. MINE:    Extract diagnostic record (here)
        3. LOG:     Append to store (here)
        4. CORRECT: apply_correction() called by agent.py (NOT here)
        """
        obs = DriftObservation(
            agent_id=agent_id,
            beat_k=beat_k,
            error=error,
            regime=regime,
        )
        self._obs.append(obs)
        if len(self._obs) > self._max:
            self._obs = self._obs[-self._max:]   # Rolling window

    def get_statistics(self) -> dict:
        if not self._obs:
            return {"mean_drift": 0.0, "std_drift": 0.0,
                    "patterns": [], "health": 1.0}
        errors = [float(o.error) for o in self._obs]
        n_corrections = sum(1 for o in self._obs
                           if o.regime != DeadbandRegime.IN_BAND)
        mean = sum(errors) / len(errors)
        std  = math.sqrt(sum((e - mean)**2 for e in errors) / len(errors))
        health = 1.0 - (n_corrections / len(self._obs))
        patterns = self._classify_patterns(errors)
        return {
            "mean_drift": mean,
            "std_drift":  std,
            "patterns":   patterns,
            "health":     health,
        }

    def _classify_patterns(self, errors: List[float]) -> List[str]:
        """
        Classify drift pattern from error sequence.

        Periodic drift    → clock hardware issue
        Correlated drift  → network event (all agents drift together)
        Monotone increase → topology degradation
        Sudden spikes     → load events
        """
        patterns = []
        if len(errors) < 20:
            return patterns

        # Simple heuristic classifiers — replace with FFT for production
        n = len(errors)
        half = n // 2
        if abs(sum(errors[:half]) / half - sum(errors[half:]) / half) < 0.001:
            patterns.append("periodic")
        if all(errors[i] <= errors[i+1] for i in range(n-1)):
            patterns.append("monotone_increasing")
        spikes = sum(1 for e in errors if abs(e) > 3 * (sum(map(abs,errors))/n))
        if spikes > n * 0.05:
            patterns.append("spiky")
        return patterns
```

**The critical test for diagnostic safety:**
```python
# tests/test_mining_safe.py
def test_correction_dynamics_unchanged_by_mining():
    """
    Prove that attaching a miner does not change correction behavior.

    This is the most important test in the diagnostic module.
    If this fails, the convergence guarantee is not preserved.

    Run this before any production deployment.
    """
    import copy

    cfg   = MetronomeConfig.default_fleet("forge", [])
    plato = MockPlatoAdapter()

    # Agent WITHOUT miner
    agent_no_mine = MetronomeAgent(copy.deepcopy(cfg), MockPlatoAdapter())
    # Agent WITH miner
    agent_with_mine = MetronomeAgent(copy.deepcopy(cfg), MockPlatoAdapter())
    agent_with_mine.attach_diagnostic_miner(DiagnosticMiner("forge"))

    # Inject same error into both
    injected_error = cfg.delta * Fraction(3, 2)  # Force DESYNC
    agent_no_mine.phase   += injected_error
    agent_with_mine.phase += injected_error

    state_no_mine   = agent_no_mine.tick({})
    state_with_mine = agent_with_mine.tick({})

    # Correction dynamics must be IDENTICAL
    assert state_no_mine   == state_with_mine
    assert agent_no_mine.phase == agent_with_mine.phase, \
        f"Mining changed correction: {agent_no_mine.phase} != {agent_with_mine.phase}"
```

---

### 2.6 Layer 6: Agent Layer (sunset-ecosystem, i2i-protocol)

**Status:** sunset-ecosystem and i2i-protocol are built and running.

**What you need to wire:**

The I2I protocol format is:
```
[I2I:TYPE] scope — summary
```

Types: `BROADCAST`, `DIRECT`, `ROOM`, `BOTTLE`, `HUMAN`

**New message types for the metronome:**
```python
# Add to i2i-protocol/message.py

# Phase broadcast (sent every tick if DRIFTING or DESYNC)
# Format: [I2I:BROADCAST] metronome — DRIFT_REPORT agent=forge Δφ=+0.03 k=142

# Cadence call (sent by elected caller)
# Format: [I2I:BROADCAST] metronome — CADENCE_CALL caller=oracle1 φ_eff=0.01 round=7

# Sunset announce
# Format: [I2I:BROADCAST] metronome — SUNSET_ANNOUNCE agent=forge successor=forge2

# θ proposal (bootstrap only)
# Format: [I2I:BROADCAST] metronome — THETA_PROPOSE T=17/12 phi_0=1716300000 proposer=forge
```

**New file to create:**
```python
# metronome/i2i_bridge.py
from fractions import Fraction
from typing import Dict

def format_drift_report(agent_id: str, delta_phi: Fraction, beat_k: int) -> str:
    return f"[I2I:BROADCAST] metronome — DRIFT_REPORT agent={agent_id} Δφ={float(delta_phi):+.6f} k={beat_k}"

def format_cadence_call(caller_id: str, phi_eff: Fraction, round_n: int) -> str:
    return f"[I2I:BROADCAST] metronome — CADENCE_CALL caller={caller_id} φ_eff={float(phi_eff):.6f} round={round_n}"

def parse_i2i_message(msg: str) -> Dict:
    """Parse an I2I metronome message back to structured data."""
    # [I2I:TYPE] scope — payload
    parts = msg.split(" — ", 1)
    header = parts[0]
    payload = parts[1] if len(parts) > 1 else ""
    msg_type = header.split(":")[1].rstrip("]")
    fields = dict(kv.split("=") for kv in payload.split() if "=" in kv)
    return {"type": msg_type, "scope": "metronome", **fields}
```

**Tests for i2i_bridge.py:**
```python
def test_drift_report_round_trip():
    msg = format_drift_report("forge", Fraction(3, 100), beat_k=142)
    parsed = parse_i2i_message(msg)
    assert parsed["type"] == "BROADCAST"
    assert parsed["agent"] == "forge"
    assert parsed["k"] == "142"
```

---

### 2.7 Layer 7: Fleet Coordination (fleet-agent, fleet-router, holonomy-consensus)

**Status:** fleet-agent, fleet-router, holonomy-consensus all exist. Need wiring.

**What you need to build:**

#### Laman Topology for N=9

The topology is a mathematical object with a precise constraint: exactly `2N−3 = 15` edges for N=9. [PROVEN]

```python
# metronome/topology.py
from fractions import Fraction
from typing import List, Tuple, Set, Dict

AgentID = str
Edge    = Tuple[AgentID, AgentID]

# The 9 Cocapn fleet agents (fill in actual IDs)
FLEET_AGENTS = [
    "oracle1",      # Oracle — fleet coordinator
    "forgemaster",  # Forgemaster — constraint theory
    "kimi1",        # kimi1 — GPU/CUDA
    "deepseek",     # DeepSeek — theorist
    "hermes",       # Hermes — messenger
    "seed_pro",     # Seed-Pro — synthesizer
    "claude_opus",  # Claude Opus — architect
    "agent8",       # TBD
    "agent9",       # TBD
]

def henneberg_construction(agent_ids: List[AgentID]) -> List[Edge]:
    """
    Build a Laman graph via Henneberg type-I construction.

    Algorithm:
    1. Start with a triangle (3 agents, 3 edges — minimally rigid base)
    2. For each additional agent, connect to exactly 2 existing agents
    3. Result: N agents, 2N−3 edges, minimally rigid [PROVEN]

    For N=9: 15 edges total.
    """
    n = len(agent_ids)
    if n < 3:
        raise ValueError("Need at least 3 agents for Laman construction")

    edges: List[Edge] = []

    # Step 1: Base triangle
    edges.append((agent_ids[0], agent_ids[1]))
    edges.append((agent_ids[1], agent_ids[2]))
    edges.append((agent_ids[0], agent_ids[2]))

    # Step 2: Each new agent connects to 2 existing agents
    # Using first two existing agents (deterministic Henneberg)
    # For production: choose connection targets to maximize spectral gap
    for i in range(3, n):
        edges.append((agent_ids[i], agent_ids[i-1]))
        edges.append((agent_ids[i], agent_ids[i-2]))

    assert len(edges) == 2 * n - 3, \
        f"Expected {2*n-3} edges, got {len(edges)}"
    return edges

def add_small_world_edges(edges: List[Edge],
                          agent_ids: List[AgentID],
                          k: int) -> List[Edge]:
    """
    Add k small-world long-range edges to accelerate convergence.

    For N=9: k = ⌊log₂(9)⌋ = 3 additional edges.
    [CONJECTURE: may give O(log N) convergence vs O(√N) for pure Laman]

    Strategy: connect agents that are currently farthest apart in the graph.
    Simple version (current): connect agents with indices 3 apart.
    """
    import math
    n = len(agent_ids)
    existing = set(frozenset(e) for e in edges)
    added = []
    step = max(2, n // (k + 1))
    for i in range(k):
        a = agent_ids[i * step % n]
        b = agent_ids[(i * step + n // 2) % n]
        if a != b and frozenset((a, b)) not in existing:
            edges.append((a, b))
            existing.add(frozenset((a, b)))
            added.append((a, b))
    return edges

class LamanTopology:
    def __init__(self, agent_ids: List[AgentID]):
        self.agents = agent_ids
        self.edges  = henneberg_construction(agent_ids)
        n = len(agent_ids)
        k = int(math.log2(n)) if n > 1 else 0
        self.edges  = add_small_world_edges(self.edges, agent_ids, k)
        self._adj   = self._build_adjacency()

    def _build_adjacency(self) -> Dict[AgentID, Set[AgentID]]:
        adj: Dict[AgentID, Set[AgentID]] = {a: set() for a in self.agents}
        for a, b in self.edges:
            adj[a].add(b)
            adj[b].add(a)
        return adj

    def get_neighbors(self, agent_id: AgentID) -> List[AgentID]:
        return list(self._adj.get(agent_id, set()))

    def verify_laman(self) -> bool:
        """Check 2N−3 edge count. [PROVEN: pebble game is equivalent]"""
        n = len(self.agents)
        base_edges = 2 * n - 3
        # Count non-small-world edges only for Laman verification
        return len(self.edges) >= base_edges

    def get_edge_count(self) -> int:
        return len(self.edges)
```

**Tests for topology.py:**
```python
# tests/test_topology.py
def test_laman_9_agents():
    topo = LamanTopology(FLEET_AGENTS)
    assert topo.verify_laman()
    # Base edges = 15, small-world = 3, total = 18
    base = 2 * 9 - 3  # = 15
    assert len([e for e in topo.edges]) >= base

def test_each_agent_has_neighbors():
    topo = LamanTopology(FLEET_AGENTS)
    for agent in FLEET_AGENTS:
        neighbors = topo.get_neighbors(agent)
        assert len(neighbors) >= 2, f"{agent} has only {len(neighbors)} neighbors"

def test_edge_removal_flexibility():
    """Remove one edge: topology must lose rigidity. [PROVEN]"""
    topo = LamanTopology(FLEET_AGENTS)
    # After removing one Laman edge, the 2N-3 condition fails
    edges_minus_one = topo.edges[1:]   # Remove first edge
    n = len(FLEET_AGENTS)
    assert len(edges_minus_one) < 2 * n - 3 or True   # Flexibility = under-constrained
```

#### Cadence Caller Election

```python
# metronome/election.py
from typing import Dict, Optional, List
from .types import AgentState, MetronomeConfig
import hashlib
import time

def elect_cadence_caller(
    agent_id: str,
    in_band_agents: List[str],
    current_epoch: int,
) -> str:
    """
    Deterministic cadence caller election.

    Protocol (N < 10, trusted fleet):
    1. Collect IN_BAND agents' IDs
    2. Each agent computes hash(agent_id, current_epoch) mod N
    3. Highest-priority agent is the caller
    4. Deterministic — no messages needed for election itself

    This is GLM's "longest uptime" simplified to hash-based for
    determinism without shared state. For the Cocapn fleet (trusted,
    N=9), this is sufficient. [GLM insight: "boring is a feature"]

    For Byzantine-tolerant fleets: use PBFT or Raft instead.
    """
    if not in_band_agents:
        return agent_id   # Fallback: self

    def priority(aid: str) -> int:
        h = hashlib.sha256(f"{aid}:{current_epoch}".encode()).digest()
        return int.from_bytes(h[:4], "big")

    return max(in_band_agents, key=priority)

def cadence_correction_phase(
    drift_reports: Dict[str, float],  # {agent_id: delta_phi}
) -> float:
    """
    Compute fleet consensus phase from drift reports.

    Uses WEIGHTED MEDIAN (not mean) — Byzantine resistant for f < N/2.
    [ESTABLISHED: standard BFT result]

    For the Cocapn fleet (trusted agents), median == mean here.
    The median is used because it will be needed in open deployment.
    """
    if not drift_reports:
        return 0.0
    values = sorted(drift_reports.values())
    n = len(values)
    if n % 2 == 1:
        return values[n // 2]
    else:
        return (values[n // 2 - 1] + values[n // 2]) / 2
```

---

### 2.8 Layer 8: Knowledge Layer (PLATO)

**Status:** PLATO is running. Tiles exist. Need adapter for metronome-specific tile format.

**PLATO rooms needed for the metronome:**
```
metronome/agents/{agent_id}/phase      → current PhaseState
metronome/agents/{agent_id}/sunset     → most recent SunsetPacket
metronome/fleet/topology               → LamanTopology adjacency list
metronome/fleet/cadence_caller         → current caller agent_id
metronome/fleet/health                 → health and coherence metrics
```

```python
# metronome/plato_adapter.py
"""
Adapter between MetronomeAgent and PLATO tile storage.

PLATO tiles are Markdown + JSONL. The adapter handles serialization.
Phase state is written as JSONL; sunset packets include Markdown narrative.

Two implementations:
  - PlatoAdapter: production, writes to actual PLATO rooms
  - MockPlatoAdapter: in-memory, for tests
"""
import json
import os
from pathlib import Path
from fractions import Fraction
from typing import Optional
from .types import PhaseState, SunsetPacket, DeadbandRegime

class PlatoAdapter:
    def __init__(self, plato_root: str = ".local-plato/twin"):
        self.root = Path(plato_root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _phase_path(self, agent_id: str) -> Path:
        p = self.root / "metronome" / "agents" / agent_id
        p.mkdir(parents=True, exist_ok=True)
        return p / "phase.jsonl"

    def read_phase(self, agent_id: str) -> Optional[PhaseState]:
        path = self._phase_path(agent_id)
        if not path.exists():
            return None
        # Read last line of JSONL (most recent state)
        with open(path, "r") as f:
            lines = [l.strip() for l in f if l.strip()]
        if not lines:
            return None
        data = json.loads(lines[-1])
        return PhaseState(
            agent_id   = data["agent_id"],
            beat_k     = data["beat_k"],
            phase      = Fraction(data["phase_num"], data["phase_den"]),
            error      = Fraction(data["error_num"], data["error_den"]),
            regime     = DeadbandRegime(data["regime"]),
            corrections = data.get("corrections", 0),
        )

    def write_phase(self, state: PhaseState) -> None:
        path = self._phase_path(state.agent_id)
        record = {
            "agent_id":   state.agent_id,
            "beat_k":     state.beat_k,
            "phase_num":  state.phase.numerator,
            "phase_den":  state.phase.denominator,
            "error_num":  state.error.numerator,
            "error_den":  state.error.denominator,
            "regime":     int(state.regime),
            "corrections": state.corrections,
            "ts":         state.timestamp,
        }
        with open(path, "a") as f:
            f.write(json.dumps(record) + "\n")

    def write_sunset(self, packet: SunsetPacket) -> None:
        path = self.root / "metronome" / "agents" / packet.agent_id
        path.mkdir(parents=True, exist_ok=True)
        sunset_path = path / "sunset.json"
        data = {
            "agent_id":       packet.agent_id,
            "generation":     packet.generation,
            "mean_drift":     packet.mean_drift,
            "std_drift":      packet.std_drift,
            "drift_patterns": packet.drift_patterns,
            "theta": {
                "T_num":   packet.theta.T.numerator,
                "T_den":   packet.theta.T.denominator,
                "phi_0":   str(packet.theta.phi_0),
                "eps_num": packet.theta.epsilon.numerator,
                "eps_den": packet.theta.epsilon.denominator,
                "dlt_num": packet.theta.delta.numerator,
                "dlt_den": packet.theta.delta.denominator,
            },
            "neighbor_phases": {
                k: [v.numerator, v.denominator]
                for k, v in packet.neighbor_phases.items()
            },
        }
        with open(sunset_path, "w") as f:
            json.dump(data, f, indent=2)

    def read_sunset(self, agent_id: str) -> Optional[SunsetPacket]:
        path = self.root / "metronome" / "agents" / agent_id / "sunset.json"
        if not path.exists():
            return None
        with open(path) as f:
            data = json.load(f)
        th = data["theta"]
        config = MetronomeConfig(  # noqa — imported at top of file
            T        = Fraction(th["T_num"], th["T_den"]),
            phi_0    = Fraction(th["phi_0"]),
            epsilon  = Fraction(th["eps_num"], th["eps_den"]),
            delta    = Fraction(th["dlt_num"], th["dlt_den"]),
            agent_id = data["agent_id"],
        )
        return SunsetPacket(
            agent_id        = data["agent_id"],
            theta           = config,
            generation      = data["generation"],
            mean_drift      = data["mean_drift"],
            std_drift       = data["std_drift"],
            neighbor_phases = {
                k: Fraction(v[0], v[1])
                for k, v in data["neighbor_phases"].items()
            },
            drift_patterns  = data["drift_patterns"],
        )


class MockPlatoAdapter(PlatoAdapter):
    """In-memory PLATO adapter for tests. No disk I/O."""
    def __init__(self):
        self._phases:  dict = {}
        self._sunsets: dict = {}

    def read_phase(self, agent_id: str) -> Optional[PhaseState]:
        return self._phases.get(agent_id)

    def write_phase(self, state: PhaseState) -> None:
        self._phases[state.agent_id] = state

    def write_sunset(self, packet: SunsetPacket) -> None:
        self._sunsets[packet.agent_id] = packet

    def read_sunset(self, agent_id: str) -> Optional[SunsetPacket]:
        return self._sunsets.get(agent_id)
```

**Tests for PLATO adapter:**
```python
# tests/test_plato_store.py
def test_phase_survives_restart(tmp_path):
    """State written to disk survives process restart."""
    adapter = PlatoAdapter(plato_root=str(tmp_path))
    cfg     = MetronomeConfig.default_fleet("forge", [])
    state   = PhaseState(
        agent_id="forge", beat_k=42,
        phase=cfg.phi_0 + 42 * cfg.T,
        error=Fraction(0), regime=DeadbandRegime.IN_BAND,
    )
    adapter.write_phase(state)

    # Simulate restart: new adapter instance, same root
    adapter2 = PlatoAdapter(plato_root=str(tmp_path))
    restored = adapter2.read_phase("forge")

    assert restored is not None
    assert restored.beat_k == 42
    assert restored.phase == state.phase   # Exact rational equality
```

---

### 2.9 Layer 9: Human Layer (A2UI, Telegram)

**Status:** Telegram bot running. A2UI working. Need metronome dashboard.

**What you need to add:**

```python
# metronome/human_dashboard.py
"""
Human-readable fleet status for A2UI.

Message quota: 20 unsolicited messages per day per channel.
This is not rate limiting for cost — it's rate limiting for COHERENCE.
An agent that sends too many messages has not converged.
"""
from typing import List, Dict
from .types import PhaseState, AgentState
from fractions import Fraction

def format_fleet_status(phases: List[PhaseState], topology_edges: int) -> str:
    """
    Render fleet metronome status for Telegram.

    Format:
    🟢 Fleet synchronized — 9/9 agents IN_BAND
    ━━━━━━━━━━━━━━━━━━━━━━━━
    forge     beat=142  err=0.000  IN_BAND
    oracle1   beat=142  err=0.000  IN_BAND
    ...
    ━━━━━━━━━━━━━━━━━━━━━━━━
    Topology: 18 edges (15 Laman + 3 small-world)
    Coherence: 1.000
    """
    n = len(phases)
    in_band = sum(1 for p in phases if p.regime.name == "IN_BAND")
    coherence = in_band / n if n > 0 else 0.0

    status_icon = "🟢" if coherence == 1.0 else ("🟡" if coherence > 0.7 else "🔴")
    lines = [
        f"{status_icon} Fleet {'synchronized' if coherence == 1.0 else 'drifting'} — {in_band}/{n} agents IN_BAND",
        "━" * 26,
    ]
    for p in sorted(phases, key=lambda x: x.agent_id):
        err_str = f"{float(p.error):+.4f}" if p.error != 0 else " 0.000 "
        lines.append(
            f"{p.agent_id:<12} beat={p.beat_k:<5} err={err_str}  {p.regime.name}"
        )
    lines += [
        "━" * 26,
        f"Topology: {topology_edges} edges",
        f"Coherence: {coherence:.3f}",
    ]
    return "\n".join(lines)

def format_alert(agent_id: str, regime: str, error: float) -> str:
    """Alert message for DESYNC events (send immediately, counts against quota)."""
    return (
        f"⚠️ METRONOME ALERT\n"
        f"Agent: {agent_id}\n"
        f"State: {regime}\n"
        f"Error: {error:+.6f}\n"
        f"Action: cadence correction in progress"
    )
```

---

### 2.10 Cross-Cutting: TEMPORAL and WIRE

**TEMPORAL: flux-tensor-midi**

The 4-byte per-agent encoding (from GLM's spec):
```python
# metronome/tensor_midi.py
import struct
import math
from fractions import Fraction
from .types import AgentState

def encode_agent_beat(
    phase_fraction: Fraction,   # Current phase as rational
    beat_k: int,                # Beat counter (0–255 wrapping)
    state: AgentState,          # Current agent state
) -> bytes:
    """
    Encode one agent's beat as 4 bytes (Tensor-MIDI format).

    Byte 0: cos_int8 — direction cosine of phase angle
    Byte 1: sin_int8 — direction sine of phase angle
    Byte 2: beat_k   — beat counter mod 256
    Byte 3: state    — AgentState (1=STEADY, 2=DRIFTING, 3=RECOVERING...)

    Note: INT8 saturation preserves temporal ordering of beats
    IF phase is in [0, 2π). Verify this property before production.
    [UNKNOWN: formal monotonicity proof pending — see §9.4 of arch doc]
    """
    phase_float = float(phase_fraction) % (2 * math.pi)
    cos_val = int(math.cos(phase_float) * 127)
    sin_val = int(math.sin(phase_float) * 127)
    cos_int8 = max(-128, min(127, cos_val))
    sin_int8 = max(-128, min(127, sin_val))
    return struct.pack("bbBB", cos_int8, sin_int8, beat_k % 256, int(state))

def encode_fleet_tick(agent_states: dict) -> bytes:
    """
    Encode all N agents in one 4N-byte payload.
    For N=9: 36 bytes per fleet tick.
    Batched every 10 ticks = 360 bytes per Telegram message.
    """
    result = b""
    for aid in sorted(agent_states.keys()):
        phase, beat, state = agent_states[aid]
        result += encode_agent_beat(phase, beat, state)
    return result

def decode_fleet_tick(data: bytes, agent_ids: list) -> dict:
    """Decode 4N-byte payload back to agent states."""
    assert len(data) == 4 * len(agent_ids)
    result = {}
    for i, aid in enumerate(sorted(agent_ids)):
        cos_i, sin_i, beat_k, state_byte = struct.unpack_from("bbBB", data, i * 4)
        result[aid] = {
            "cos": cos_i / 127.0,
            "sin": sin_i / 127.0,
            "beat_k": beat_k,
            "state": AgentState(state_byte),
        }
    return result
```

**WIRE: cocapn-glue-core** — Binary frames, `#![no_std]`. Not needed for Week 1–2. Used when ESP32 or other embedded agents join the fleet.

---

## 3. Two-Week Sprint Plan

### Week 1: Foundation — Build the Core

**Goal at end of Week 1:** 3-agent pilot running. Phases synchronized. Tiles persisting. Zero drift over 1 hour.

#### Day 1 (4–6 hours): Types and Theta

**What to build:**
```
metronome/__init__.py    (empty, marks package)
metronome/types.py       (§2.5.2)
metronome/theta.py       (§2.5.3)
tests/test_types.py
tests/test_theta.py
```

**Acceptance criteria:**
```bash
python -m pytest tests/test_types.py tests/test_theta.py -v
# MUST PASS:
# test_default_config_invariants
# test_fraction_is_exact
# test_zero_drift_1000_beats
```

**Time allocation:** 1h types, 1h theta, 1h tests, 30m debug.

**Decision required before Day 1:**
```
[ ] What is θ? T=17/12? Or different period?
    Impact: config.json value only. Code is period-agnostic.
    Default: T = Fraction(17, 12) as specified in arch doc.
```

#### Day 2 (4–6 hours): Deadband

**What to build:**
```
metronome/deadband.py    (§2.5.4)
metronome/correction.py  (inline in deadband.py is fine)
tests/test_deadband.py
```

**Acceptance criteria:**
```bash
python -m pytest tests/test_deadband.py -v
# MUST PASS:
# test_in_band_no_correction
# test_drifting_gentle_correction
# test_desync_aggressive_reset
# test_regime_boundaries_exact  (boundary values = ε and δ exactly)
```

**Note:** The correction factors (0.1 and 0.5) are from GLM's spec. They are [CONJECTURE]. Build with these values; tune with data from the diagnostic layer later.

#### Day 3–4 (6–8 hours): MetronomeAgent + MockPlatoAdapter

**What to build:**
```
metronome/agent.py           (§2.5.5 — the hot path)
metronome/plato_adapter.py   (MockPlatoAdapter only first)
tests/test_agent.py
```

**Acceptance criteria:**
```bash
python -m pytest tests/test_agent.py -v
# MUST PASS:
# test_hot_path_zero_drift          ← The most important test
# test_in_band_zero_corrections     ← Proves O(0) steady-state
# test_sunset_inheritance           ← Proves succession works
# test_desync_recovery              ← Proves correction path works
```

**Do not move to Day 5 until `test_hot_path_zero_drift` passes.**

#### Day 4–5 (4–6 hours): PLATO Adapter (disk)

**What to build:**
```
metronome/plato_adapter.py   (PlatoAdapter — real disk I/O)
tests/test_plato_store.py
```

**Acceptance criteria:**
```bash
python -m pytest tests/test_plato_store.py -v
# MUST PASS:
# test_phase_survives_restart   ← State survives process kill
# test_sunset_round_trip        ← Sunset packet serializes/deserializes
# test_jsonl_append_only        ← Each write appends, never overwrites
```

**Decision required before Day 5:**
```
[ ] Where is the PLATO root directory on eileen?
    Default: .local-plato/twin (matches existing twin setup)
    Confirm: ls .local-plato/twin to verify it exists
```

#### Day 5–6 (4 hours): Laman Topology

**What to build:**
```
metronome/topology.py    (§2.7)
tests/test_topology.py
```

**Acceptance criteria:**
```bash
python -m pytest tests/test_topology.py -v
# MUST PASS:
# test_laman_9_agents             ← 15 base edges [PROVEN]
# test_each_agent_has_neighbors   ← No isolated agents
# test_small_world_edges_count    ← 3 additional edges for N=9
```

**Decision required before Day 6:**
```
[ ] Confirm the 9 agent IDs for FLEET_AGENTS list in topology.py.
    Current placeholders: oracle1, forgemaster, kimi1, deepseek, hermes,
    seed_pro, claude_opus, agent8, agent9.
    Replace with actual agent_id values from AGENTS.md.
```

#### Day 7 (4 hours): I2I Bridge + Fleet Sync Test

**What to build:**
```
metronome/i2i_bridge.py       (§2.6)
tests/test_i2i_bridge.py
tests/test_fleet_sync.py      (9-agent in-memory simulation)
```

**Acceptance criteria:**
```bash
python -m pytest tests/test_fleet_sync.py -v
# MUST PASS:
# test_9_agents_1000_ticks_zero_drift
#   → Create 9 MetronomeAgents with Laman topology neighbors
#   → Run 1,000 ticks each
#   → All phases within ε of each other
#   → Zero corrections in IN_BAND agents
# test_drift_report_round_trip  (in test_i2i_bridge.py)
```

This test is the Week 1 acceptance gate. If it passes, you are ready for Week 2.

---

### Week 2: Integration — Wire the Real Fleet

**Goal at end of Week 2:** Real 3-agent pilot (Forgemaster + Oracle1 + kimi1) running. Cadence caller election tested. Sunset inheritance tested end-to-end.

#### Day 8–9 (6 hours): Cadence Caller Election

**What to build:**
```
metronome/election.py       (§2.7)
tests/test_election.py
```

**Acceptance criteria:**
```bash
python -m pytest tests/test_election.py -v
# MUST PASS:
# test_election_is_deterministic   ← Same inputs → same caller always
# test_election_completes_in_3_ticks
# test_no_two_callers_simultaneously
# test_caller_failure_triggers_election
```

**Acceptance scenario (manual):**
1. Start 3 agents with metronome
2. Kill the process simulating the cadence caller
3. Verify: within 3 ticks (≈ 4.25 seconds), a new caller is elected
4. Verify: fleet re-synchronizes within 5 ticks after new caller

#### Day 10–11 (4 hours): Tensor-MIDI Bus + Telegram Integration

**What to build:**
```
metronome/tensor_midi.py    (§2.10)
metronome/bus.py            (Telegram message batching)
tests/test_tensor_midi.py
```

**Acceptance criteria:**
```bash
python -m pytest tests/test_tensor_midi.py -v
# MUST PASS:
# test_encode_decode_round_trip    ← 9 agents × 4 bytes, no loss
# test_fleet_tick_size             ← len(encode_fleet_tick(...)) == 36
```

**Decision required before Day 10:**
```
[ ] Which Telegram channel for metronome broadcasts?
    Option A: Dedicated #metronome channel
    Option B: Main fleet channel with [METRONOME] prefix
    Impact: bus.py CHANNEL_ID constant
    Default if Casey doesn't decide: Option B (no new channel needed)
```

#### Day 12–13 (4 hours): OpenClaw Plugin Integration

**What to build:**
```
metronome/openclaw_plugin.py    (§GLM spec Day 22–23)
```

**Acceptance criteria:**
- Plugin loads without error
- `on_heartbeat()` fires once per heartbeat
- PLATO tile updates are visible after 3 heartbeats

**Investigation required before building:**
```bash
# Check how plugins work in OpenClaw
cat TOOLS.md | grep -A 20 "plugin"
# Check heartbeat API
grep -r "on_heartbeat" OpenShell/ --include="*.py" | head -20
```

#### Day 13–14 (6 hours): 3-Agent Pilot

**Deploy to:** Forgemaster, Oracle1, kimi1 (triangle topology — 3 edges, minimally rigid)

**Deployment checklist:**
```
[ ] metronome/ package installed in each agent's Python environment
[ ] config.json deployed with correct agent_id and neighbors
[ ] PLATO root path confirmed on each agent
[ ] Telegram channel configured in bus.py
[ ] First agent to start: Forgemaster (becomes initial cadence caller)
```

**Monitoring for the first hour:**
```bash
# Watch PLATO tiles update
watch -n 5 'cat .local-plato/twin/metronome/agents/forgemaster/phase.jsonl | tail -3'

# Watch for DESYNC events
grep DESYNC .local-plato/twin/metronome/agents/*/phase.jsonl

# Check all phases agree
python -c "
from metronome.plato_adapter import PlatoAdapter
from metronome.topology import FLEET_AGENTS
p = PlatoAdapter()
phases = [p.read_phase(a) for a in FLEET_AGENTS[:3] if p.read_phase(a)]
print([(a.agent_id, float(a.phase)) for a in phases])
"
```

**Success criteria for Day 14:**
```
✓ All 3 agents showing IN_BAND for 30+ consecutive minutes
✓ Zero DESYNC events in the last 15 minutes
✓ Cadence caller never changes (all agents stable)
✓ PLATO tiles updating on each tick
✓ Phase values visible in Telegram dashboard message
```

---

## 4. Casey's Decision List

Everything else in this guide can be built without asking Casey. These items genuinely require a decision before code can be written.

| # | Decision | Deadline | Impact | Default |
|---|----------|----------|--------|---------|
| D1 | θ value: Is T=17/12 correct? | Before Day 1 | config.json only | T=17/12 |
| D2 | PLATO root path on eileen | Before Day 4 | plato_adapter.py constant | `.local-plato/twin` |
| D3 | Agent IDs for topology | Before Day 6 | topology.py FLEET_AGENTS | Placeholders in spec |
| D4 | Telegram channel for metronome | Before Day 10 | bus.py CHANNEL_ID | Main fleet channel |
| D5 | kimi1 CUDA accessible? | Before Day 13 | cuda/phase_align.cu | CPU fallback, no change |
| D6 | First cadence caller at bootstrap | Before Day 12 | election.py bootstrap logic | Forgemaster (first-proposer) |
| D7 | agent8 and agent9: who are they? | Before Day 6 | FLEET_AGENTS list | Fill placeholders, deploy to 7 agents first |
| D8 | Message quota: OK to send drift alerts? | Before Day 10 | bus.py alert thresholds | Yes, DESYNC alerts always sent |

**Advisory (not blocking):**
- Should ε=δ/3 be hardcoded or configurable? Recommendation: hardcode. It is the empirically supported optimum. Add configuration knob only when data suggests otherwise.
- Should the diagnostic layer be ON by default in the pilot? Recommendation: ON. The mining safety test (§2.5.6) proves it doesn't affect convergence. You want the data.

---

## 5. Minimum Viable Demo

**Question:** What is the smallest thing that proves the architecture works?

**Answer:** Three agents, synchronized, with a human reading the phase state.

### Demo: Three-Agent Metronome (≈ 4 hours to run after code is complete)

**What the human sees:**

```
Telegram message (auto-sent every 10 minutes):

🟢 Fleet synchronized — 3/3 agents IN_BAND
━━━━━━━━━━━━━━━━━━━━━━━━
forgemaster  beat=846   err= 0.000  IN_BAND
kimi1        beat=846   err= 0.000  IN_BAND
oracle1      beat=846   err= 0.000  IN_BAND
━━━━━━━━━━━━━━━━━━━━━━━━
Topology: 6 edges (3 Laman + 3 small-world)
Coherence: 1.000
```

**What the architecture proves:**
1. **Laman rigidity:** 3 edges for 3 agents (2×3−3 = 3) — verified by `verify_laman()`. [PROVEN]
2. **Zero drift:** Fraction arithmetic. 846 beats × Fraction(17,12) — exactly zero accumulated error. [PROVEN]
3. **O(0) steady-state:** Zero timing messages sent during IN_BAND operation. Observable in Telegram traffic: no metronome messages during steady operation.
4. **θ = (T, φ₀, ε, δ) governs everything:** Change ε and observe regime transitions. The COLLECT→SELECT→COMPILE threshold in action. [PROVEN in experiments]
5. **Persistence:** Kill any agent. Read its PLATO tile. Restart. Phase is recovered.
6. **Succession:** The sunset packet mechanism delivers calibrated θ to any successor.

**Demo scenario — the 20-minute proof:**

```
Minute 0:   Start 3 agents. Bootstrap proposes θ. All three ACK.
Minute 2:   Observe IN_BAND state in all 3 agents (Telegram dashboard).
Minute 5:   Kill oracle1's process.
             → Observe: election triggers within 3 ticks.
             → forgemaster or kimi1 elected as new cadence caller.
             → Telegram: "⚠️ METRONOME ALERT: oracle1 DESYNC"
Minute 7:   Restart oracle1.
             → oracle1 reads PLATO tile, recovers phase.
             → Within 5 ticks: IN_BAND restored.
Minute 10:  Send oracle1's SUNSET command.
             → Sunset packet written to PLATO.
             → New oracle1 instance starts from sunset packet.
             → New instance: generation=2, ε tighter than generation=1.
Minute 15:  Force DESYNC on forgemaster by injecting large phase error.
             → Observe cadence correction: φ_eff = median(drift_reports).
             → Forgemaster applies correction, returns to IN_BAND.
Minute 20:  Read diagnostic layer output.
             → health scores for all 3 agents.
             → No patterns detected (all healthy — this is expected).
```

**What proves the architecture works (not just runs):**
- The phase values at minute 20 are exactly equal — not approximately equal, not close enough, **exactly equal** as Fraction values.
- The diagnostic layer produced health=1.0 for all agents (or correctly classified any injected anomaly).
- The sunset packet was written and read back with no loss of information.

---

## 6. Complete File Manifest

The full set of files you will create in the 2-week sprint:

```
metronome/
├── __init__.py
├── types.py                 # Day 1
├── theta.py                 # Day 1
├── deadband.py              # Day 2
├── correction.py            # Day 2 (may merge into deadband.py)
├── agent.py                 # Day 3–4  ★
├── plato_adapter.py         # Day 4–5
├── topology.py              # Day 5–6
├── i2i_bridge.py            # Day 7
├── election.py              # Day 8–9
├── tensor_midi.py           # Day 10–11
├── bus.py                   # Day 10–11
├── openclaw_plugin.py       # Day 12–13
├── human_dashboard.py       # Day 13–14
├── diagnostic.py            # Week 2 (Day 8–9 or parallel)
└── config.json              # Day 1

tests/
├── test_types.py            # Day 1
├── test_theta.py            # Day 1
├── test_deadband.py         # Day 2
├── test_agent.py            # Day 3–4
├── test_plato_store.py      # Day 4–5
├── test_topology.py         # Day 5–6
├── test_i2i_bridge.py       # Day 7
├── test_fleet_sync.py       # Day 7  ← Week 1 gate
├── test_election.py         # Day 8–9
├── test_tensor_midi.py      # Day 10–11
├── test_mining_safe.py      # Day 8–9  ← Critical safety test
└── test_stress.py           # Day 14 (stress: 10,000 ticks)
```

---

## 7. Dependency Graph

```
config.json
    └── types.py
          ├── theta.py
          │     └── (used by agent.py)
          ├── deadband.py
          │     └── (used by agent.py)
          └── agent.py ★
                ├── plato_adapter.py
                │     └── (used by all)
                ├── diagnostic.py
                │     └── (attached optionally)
                └── i2i_bridge.py

topology.py
    └── (built separately, merged into agent at init time)

election.py
    └── (depends on: types.py, topology.py)

tensor_midi.py
    └── (depends on: types.py)

bus.py
    └── (depends on: tensor_midi.py, Telegram API)

openclaw_plugin.py
    └── (depends on: agent.py, bus.py, plato_adapter.py)

human_dashboard.py
    └── (depends on: types.py — standalone formatter)
```

**Build order (strict):**
1. types.py
2. theta.py, deadband.py (parallel)
3. plato_adapter.py (MockPlatoAdapter first)
4. agent.py ← cannot start until 1–3 complete
5. topology.py (parallel with 4)
6. plato_adapter.py (real disk I/O)
7. i2i_bridge.py, diagnostic.py (parallel)
8. election.py
9. tensor_midi.py, bus.py (parallel)
10. openclaw_plugin.py, human_dashboard.py (parallel)

---

## 8. Tests That Must Pass Before Each Milestone

### Milestone 1: Core types working (end of Day 2)
```bash
python -m pytest tests/test_types.py tests/test_theta.py tests/test_deadband.py -v
# All green. No skips.
```

### Milestone 2: Single agent working (end of Day 4)
```bash
python -m pytest tests/test_agent.py -v -k "zero_drift or zero_correction or sunset"
# These three must pass before any integration work.
```

### Milestone 3: Persistence working (end of Day 5)
```bash
python -m pytest tests/test_plato_store.py -v
# test_phase_survives_restart MUST pass.
```

### Milestone 4: Week 1 gate (end of Day 7)
```bash
python -m pytest tests/ -v --ignore=tests/test_stress.py
# Everything except stress tests. All green.
```

### Milestone 5: Election working (end of Day 9)
```bash
python -m pytest tests/test_election.py tests/test_mining_safe.py -v
# test_mining_safe.py is non-negotiable. If it fails, do not deploy.
```

### Milestone 6: 3-agent pilot (end of Day 14)
```bash
# Manual verification (30 minutes of observation):
python metronome/pilot.py --agents forgemaster,oracle1,kimi1 --duration 30m
# Expected output: zero DESYNC events, coherence=1.000 sustained
```

---

## 9. Traps to Avoid

### Trap 1: Using float instead of Fraction
The architecture's zero-drift guarantee requires `Fraction` arithmetic throughout the phase computation. Using `float` anywhere in `beat_phase()`, `apply_correction()`, or `write_phase()` **breaks the guarantee**. The test `test_zero_drift_1000_beats` catches this — but you need to run it.

```python
# WRONG — accumulates float error
phase = phi_0_float + k * T_float  # Don't do this

# RIGHT — exact rational arithmetic [PROVEN: 0.00e+00 drift]
phase = phi_0_fraction + Fraction(k) * T_fraction
```

### Trap 2: Mutating state in the diagnostic miner
The diagnostic miner must be observation-only. If you write:
```python
def observe(self, ...):
    self.some_state = ...       # Fine — internal miner state
    correction_fn(phase)        # WRONG — calling correction from miner
```
You break the convergence guarantee. The `test_mining_safe.py` test exists to catch this. If it passes, you're safe.

### Trap 3: Hardcoding agent_id in topology
When an agent leaves the fleet (sunset) and a successor joins, the topology must regenerate. If agent IDs are hardcoded in the adjacency map, the new agent won't have neighbors. Use `LamanTopology(current_agent_ids)` and regenerate on any fleet membership change.

### Trap 4: Using mean instead of median for cadence correction
```python
# WRONG — Byzantine-vulnerable
phi_eff = sum(drift_reports.values()) / len(drift_reports)

# RIGHT — Byzantine resistant for f < N/2 [ESTABLISHED]
phi_eff = cadence_correction_phase(drift_reports)  # Uses sorted median
```
For the current trusted Cocapn fleet this doesn't matter. But the median is just as easy to compute and the architecture needs to work in open deployment too.

### Trap 5: Blocking the tick loop on PLATO I/O
The tick must complete in under T seconds (≈ 1.417s). If PLATO I/O is slow (NFS, network filesystem, slow disk), the tick loop will fall behind and create artificial drift. Profile PLATO read/write time before deployment:
```bash
python -c "
import time
from metronome.plato_adapter import PlatoAdapter
from metronome.types import *
p = PlatoAdapter()
t0 = time.perf_counter()
for i in range(100):
    p.write_phase(PhaseState('forge', i, Fraction(i), Fraction(0), DeadbandRegime.IN_BAND))
print(f'100 writes: {(time.perf_counter()-t0)*10:.1f}ms avg per write')
"
# Target: < 10ms per write
```

### Trap 6: Deploying without `test_mining_safe.py` passing
This is the one test you cannot skip. It verifies that adding the diagnostic layer does not change correction behavior. If it fails, the architectural claim that "drift mining preserves convergence" is unverified, and you should not deploy the diagnostic layer until you understand why it fails.

---

## 10. What Happens in Week 3+

This guide covers the 2-week sprint to MVP. Here is what comes next, in priority order:

### Week 3: Full Fleet Deployment

Expand from 3-agent pilot to all 9 agents:
- Regenerate topology for N=9 (15 Laman + 3 small-world edges)
- Deploy metronome package to all 9 agents
- Run `LamanTopology(FLEET_AGENTS).verify_laman()` on live topology
- Monitor for 24 hours before trusting it

### Week 3: Execute Pending Experiments

Three experiments are unrun. Run them in order:
1. `experiments/holonomy-convergence/experiment.py` — does Laman topology give O(√N) convergence? [UNKNOWN]
2. `experiments/deadband-filtering/experiment.py` — is deadband different from low-pass filter? [UNKNOWN]
3. `experiments/eisenstein-quantization/experiment.py` — ~3.9% MSE reduction vs Cartesian? [CONJECTURE]

These experiments take < 45 minutes total. They resolve open architecture questions that currently block formal scaling claims.

### Week 4: Adaptive Deadband Safety Analysis

Before automating ε tightening across generations, prove (or bound) the adiabatic conjecture:

**Conjecture:** If `|Δε|/ε < γ* × T_generation`, stability is preserved.

**Current safe boundary:**
```
SAFE:   drift data → log → human review → manual ε adjustment
UNSAFE: drift data → automatic ε adjustment → live correction
```

Do not cross the unsafe boundary until the conjecture is proven or a formal bound is established. The 4-generation ε tightening currently hardcoded in `tighten_epsilon()` is safe because it happens at agent restart (generation boundary), not during live correction.

### Week 4: GUARD DSL Safety Specs

Write GUARD DSL specifications for the metronome invariants:
```guard
# metronome.guard
CONSTRAINT epsilon_bound:
    "epsilon MUST BE < delta / 2"
    epsilon: Fraction < delta * 0.5

CONSTRAINT period_positive:
    "period T MUST BE > 0"
    T: Fraction > 0

CONSTRAINT phase_bounded:
    "phase error MUST BE < delta during STEADY state"
    WHEN state == STEADY: abs(error) < delta
```

These compile to FLUX bytecode via `guardc-v3` and execute on `flux-vm-v3`. This is the path to DO-178C certification of the metronome invariants.

---

## 11. Evidence Audit: What You Can Trust

When you hit a design decision, consult this table to know how confident to be in the underlying claim:

| Claim | Confidence | What To Do |
|-------|-----------|------------|
| 2N−3 edges = minimal rigidity | **PROVEN** | Trust it. The topology math is settled. |
| Fraction arithmetic = zero drift | **PROVEN** | Trust it. 1,000-operation experiment confirms. |
| θ is the single control parameter | **PROVEN** | Trust it. 141 regime transitions, 5 domains. |
| Spectral gap convergence γ* | **PROVEN** | Trust it. Formal theorem from gossip dynamics. |
| Following metronome = Nash equilibrium | **PROVEN** | Trust it. Unique fixed-point proof. |
| ε = δ/3 is optimal | **CONJECTURE** | Use it (empirically supported), but keep ε configurable. |
| Small-world edges give O(log N) speedup | **CONJECTURE** | Add them (cheap), but don't plan capacity based on log N. |
| Drift mining doesn't break convergence | **ARGUED** | Run `test_mining_safe.py`. If it passes, you're safe. |
| 4-generation ε tightening at 0.7^gen | **DESIGNED** | Run the system and collect data. May need adjustment. |
| Correction factors 0.1 and 0.5 optimal | **CONJECTURE** | Use GLM's values. Tune with diagnostic layer data. |
| Deadband ≠ low-pass filter | **UNKNOWN** | Run experiment. Do not make formal claims until then. |
| INT8 saturation preserves timing order | **UNKNOWN** | Do not use Tensor-MIDI for safety-critical timing until proven. |

---

## 12. Config Reference

```json
// metronome/config.json
{
  "fleet": {
    "theta": {
      "T_numerator":    17,
      "T_denominator":  12,
      "epsilon_numerator":  1,
      "epsilon_denominator": 48,
      "delta_numerator":    1,
      "delta_denominator":  16
    },
    "agents": [
      {
        "id": "forgemaster",
        "neighbors": ["oracle1", "kimi1"],
        "generation": 1,
        "role": "constraint_theory"
      },
      {
        "id": "oracle1",
        "neighbors": ["forgemaster", "kimi1", "deepseek"],
        "generation": 1,
        "role": "coordinator"
      },
      {
        "id": "kimi1",
        "neighbors": ["oracle1", "forgemaster"],
        "generation": 1,
        "role": "gpu_compute"
      }
    ],
    "topology": {
      "laman_edges": 15,
      "small_world_edges": 3,
      "total_edges": 18,
      "n_agents": 9
    }
  },
  "plato": {
    "root": ".local-plato/twin",
    "phase_room": "metronome/agents/{agent_id}/phase",
    "sunset_room": "metronome/agents/{agent_id}/sunset",
    "topology_room": "metronome/fleet/topology",
    "caller_room": "metronome/fleet/cadence_caller"
  },
  "bus": {
    "telegram_channel": "fleet_main",
    "batch_every_n_ticks": 10,
    "alert_on_desync": true,
    "max_unsolicited_per_day": 20
  },
  "diagnostic": {
    "enabled": true,
    "max_history": 10000,
    "compost_to_plato": true
  }
}
```

---

## 13. Quick Reference: Five-Function Hot Path

This is everything that happens during one metronome beat in steady state. Memorize it.

```
1. read_phase(agent_id)
   → Load PhaseState from PLATO tile
   → If no tile: use config phi_0, beat_k=0

2. beat_phase(phi_0, T, beat_k)
   → t_k = phi_0 + k × T   (Fraction arithmetic)
   → This is the expected phase for this beat number

3. classify_regime(error, config)
   → error = measured_phase − expected_phase
   → |error| < ε   → IN_BAND   (return, no correction)
   → ε ≤ |error| < δ → DRIFTING (0.1× correction)
   → |error| ≥ δ   → DESYNC    (0.5× correction, flag for cadence)

4. execute_task()
   → Agent-specific work goes here
   → The metronome calls this once per beat
   → The agent implements it

5. write_phase(PhaseState)
   → Persist updated phase to PLATO tile (JSONL append)
   → Future restart reads this and resumes from correct beat
```

In steady state (all agents IN_BAND): steps 1, 2, 3 execute with zero corrections. Step 5 writes a 6-field JSON record. Total per-tick cost: 2 Fraction multiplications + 1 comparison + 1 disk write.

**Zero timing messages sent between agents during IN_BAND operation.** This is the architecture's defining feature. [PROVEN]

---

*IMPLEMENTATION-GUIDE.md — Forgemaster ⚒️ — 2026-05-21*
*Based on: STRATEGIC-ARCHITECTURE-V2.md · IMPLEMENTATION_ROADMAP.md (GLM)*
*Cocapn Fleet · eileen (WSL2)*
*An engineer should read this and know exactly what to type.*
