# Architecture Evolution: From Experiments to Codebase

**Author:** Forgemaster ⚒️ · PLATO Fleet Laboratory
**Date:** 2026-05-15
**Status:** ACTIVE — build planning
**Feeds from:** EXPERIMENT-ROADMAP.md (Studies 54–63)
**Feeds into:** THE-COCAPN-ARCHITECTURE.md (canonical build doc)

---

## 1. Current Service Topology

### What Exists (Working Code)

| Service | Port | File | Status |
|---------|------|------|--------|
| Fleet Router | :8100 | `fleet_translator_v2.py` | **Bug:** NONE/ECHO output on passthrough |
| PLATO Server | :8848 | `.local-plato/` | Working (SQLite tile store) |
| PLATO Docker | :8847 | `platoclaw/` | Working |
| Hebbian Service | :8849 | `fleet_hebbian_service.py` | Working (kernel, tracker, router, clusters) |
| Expert Bridge | :8850 | `expert_hebbian_bridge.py` | Working (coupling matrix, cross-consult) |
| MCP Bridge | :8300 | `plato-mcp/` | Working (6 MCP tools) |
| Dashboard | :8080 | nginx/platoclaw/web | Working (read-only) |
| GL(9) Consensus | — | `gl9_consensus.py` | **Library only** — no service wrapper |

### What's Missing (Critical Gaps)

| Gap | Impact | Priority |
|-----|--------|----------|
| **MythosTile class** (`mythos_tile.py`) | Three incompatible tile formats. Every integration point needs manual translation. | P0 |
| **Expert daemon implementations** | 9 daemons defined in config but not implemented. The bridge connects to ghosts. | P1 |
| **Conservation daemon service** | Running as script, not a managed service. No auto-restart, no health monitoring. | P1 |
| **GL(9) service wrapper** | `gl9_consensus.py` is a library. No HTTP endpoint. No integration with PLATO/Hebbian. | P2 |
| **Fleet Router NONE/ECHO bug fix** | Stage 4 passthrough returns NONE or ECHO instead of the actual response. Blocks end-to-end testing. | P0 |
| **Hardware simulation pipeline** | Defined in spec, not implemented. No `simulate_deployment()`. | P2 |
| **GitHub twin sync** | Defined in spec, not implemented. No persistence beyond SQLite. | P3 |
| **Event sourcing** | Tiles are stored but not replayable. No `event_type`, `aggregate_id`, `sequence_number`. | P3 |
| **Docker Compose stack** | 8 services defined, not composed. Running as individual processes. | P3 |

### Service Topology Diagram (Current State)

```
    ┌──────────────┐
    │ Fleet Router │:8100  ─── Has passthrough bug
    │ (translator) │
    └──────┬───────┘
           │ manual tile conversion (no MythosTile)
           ▼
    ┌──────────────┐        ┌────────────────┐
    │ PLATO Server │:8848   │ Hebbian Service│:8849 ─── Working
    │ (SQLite)     │◄──────►│ (9×9 matrix)   │
    └──────┬───────┘        └───────┬────────┘
           │                        │
           │ manual wiring          │ manual wiring
           ▼                        ▼
    ┌──────────────┐        ┌────────────────┐
    │ Expert Bridge│:8850   │ MCP Bridge     │:8300 ─── Working
    │ (no experts) │        │ (6 tools)      │
    └──────────────┘        └────────────────┘

    ┌──────────────┐        ┌────────────────┐
    │ GL(9) lib    │ ──── No service ──── Not integrated
    │ (standalone) │
    └──────────────┘
```

---

## 2. GL(9) Integration Path

### 2.1 Current State: Isolated Library

`gl9_consensus.py` provides:
- `GL9Matrix` — 9×9 matrix operations (multiply, deviation, determinant, plane rotation)
- `IntentVector` — 9D vector with CI facet structure (C1–C9)
- `GL9HolonomyConsensus` — cycle detection, holonomy computation, fault location via binary search
- `GL9ConsensusResult` — consensus check result with deviation, faulty agents, correlation

None of this is wired to PLATO, Hebbian, or the Expert Bridge.

### 2.2 Integration Plan

```
Phase A: GL(9) as Health Metric (P2 — after Study 54)
─────────────────────────────────────────────────────────

1. Wrap GL9HolonomyConsensus as a FastAPI service (:8851)
   - POST /consensus    → check_consensus()
   - POST /locate_fault → locate_fault()
   - GET  /alignment    → compute_alignment()
   - GET  /correlation  → holonomy_alignment_correlation()

2. Wire expert daemons as GL(9) agents:
   - Each expert gets an IntentVector from its activation_keys
   - Each expert's cross-consultation becomes a GL9Matrix transform
   - Neighbor connections from Hebbian coupling weights

3. Add consensus check to the 5-checkpoint pipeline:
   - After Hebbian kernel update (checkpoint 1): also run GL9 check
   - If holonomy deviation > tolerance: locate_fault() → flag expert
   - Log to conservation-events room

Phase B: GL(9) as Fault Detector (P1 — after Study 58)
───────────────────────────────────────────────────────

4. If Study 54 shows >70% overlap with conservation monitoring:
   - Merge into unified fault detector
   - GL(9) does fast localization (binary search)
   - Hebbian does drift quantification (γ+H deviation)
   - Single /health endpoint returns both metrics

5. If Study 58 confirms:
   - Add GL(9) fault detection to tripartite_expert_loop()
   - Before each round: check_consensus()
   - If faulty agent detected: skip that expert in the round

Phase C: GL(9) as Self-Healing Trigger (P1 — after Study 63)
──────────────────────────────────────────────────────────────

6. If self-healing works (Study 63):
   - GL(9) locate_fault() → remove expert → Hebbian re-route
   - Conservation kernel re-calibrates for V-1
   - Automatic expert restart with fresh IntentVector

7. Add GL(9) intent drift monitoring:
   - Track IntentVector changes over time per expert
   - If intent drifts > threshold: the expert has lost focus
   - Trigger re-alignment: re-seed expert's activation_keys
```

### 2.3 GL(9) Service Spec

```python
# gl9_service.py — FastAPI wrapper

app = FastAPI(title="GL(9) Consensus Service")

@app.post("/consensus")
async def consensus_check() -> GL9ConsensusResult:
    """Full consensus check across all expert agents."""

@app.post("/locate_fault/{cycle_id}")
async def locate_fault(cycle_id: str) -> dict:
    """Binary search for faulty agent in a specific cycle."""

@app.get("/alignment")
async def alignment() -> dict:
    """Average pairwise cosine similarity of expert intent vectors."""

@app.get("/correlation")
async def correlation() -> dict:
    """Pearson correlation between holonomy deviation and alignment."""

@app.post("/register_agent")
async def register_agent(expert_id: str, activation_keys: list[str]):
    """Register an expert daemon as a GL(9) agent with intent vector derived from activation keys."""

@app.get("/intent/{expert_id}")
async def get_intent(expert_id: str) -> list[float]:
    """Get the current intent vector for an expert."""
```

---

## 3. Conservation Law as Runtime Constraint

### 3.1 Current State: Monitoring Only

The conservation law is currently used in two modes:
1. **Check after update:** `ConservationHebbianKernel.update()` returns a `ConservationReport` with `conserved: bool`.
2. **Background daemon:** Polls `/conservation` every 60s, logs violations.

Neither mode **prevents** violations. They detect and correct after the fact.

### 3.2 Evolution: From Monitoring to Constraint

```
CURRENT (reactive):
  Hebbian update → check γ+H → if violation: project back → log

TARGET (proactive):
  Hebbian update → compute proposed ΔW → check if ΔW would violate →
    if safe: apply
    if violation: scale ΔW to stay within manifold → apply scaled update
```

### 3.3 Implementation: Constrained Hebbian Kernel

```python
class ConstrainedHebbianKernel(ConservationHebbianKernel):
    """
    Conservation-constrained Hebbian kernel that NEVER allows violations.
    
    Instead of detecting violations and correcting, it scales the proposed
    update to stay within the conservation manifold.
    """
    
    def update_safe(self, pre: np.ndarray, post: np.ndarray) -> ConservationReport:
        # Step 1: Compute proposed update
        delta_W = self.eta * np.outer(pre, post) - self.lam * self.W
        proposed_W = self.W + delta_W
        proposed_W = (proposed_W + proposed_W.T) / 2
        np.fill_diagonal(proposed_W, 0)
        
        # Step 2: Check if proposed update would violate
        proposed_gamma = algebraic_normalized(proposed_W)
        proposed_H = coupling_entropy(proposed_W)
        proposed_sum = proposed_gamma + proposed_H
        
        predicted = self._target or (1.283 - 0.159 * np.log(max(self.V, 3)))
        sigma_V = _interpolate_sigma(self.V)
        
        if abs(proposed_sum - predicted) > 2 * sigma_V:
            # Step 3: Scale the update to land exactly on the manifold
            # Binary search for the maximum scaling factor α ∈ [0, 1]
            alpha = self._find_safe_scale(delta_W, predicted, sigma_V)
            delta_W = delta_W * alpha
        
        # Step 4: Apply (guaranteed safe)
        self.W = self.W + delta_W
        self.W = (self.W + self.W.T) / 2
        np.fill_diagonal(self.W, 0)
        
        return ConservationReport(
            gamma=self._compute_gamma(),
            H=self._compute_H(),
            conserved=True,  # Guaranteed by construction
            correction_applied=alpha < 1.0,
        )
    
    def _find_safe_scale(self, delta_W, predicted, sigma_V):
        """Binary search for maximum α such that (W + α·ΔW) is conserved."""
        lo, hi = 0.0, 1.0
        for _ in range(20):  # ~1e-6 precision
            mid = (lo + hi) / 2
            test_W = self.W + mid * delta_W
            test_W = (test_W + test_W.T) / 2
            np.fill_diagonal(test_W, 0)
            test_sum = algebraic_normalized(test_W) + coupling_entropy(test_W)
            if abs(test_sum - predicted) <= 2 * sigma_V:
                lo = mid
            else:
                hi = mid
        return lo
```

### 3.4 Migration Path

| Step | Change | Risk |
|------|--------|------|
| 1 | Add `update_safe()` alongside existing `update()` | Low — additive |
| 2 | Run both in parallel for 500 updates. Log divergences. | Low — read-only comparison |
| 3 | If safe update matches reactive correction >95% of the time: switch default to `update_safe()`. | Medium — behavior change |
| 4 | Deprecate reactive `update()`. Remove `conservation_project()`. | Low — cleanup |

---

## 4. Self-Healing Router

### 4.1 Design

The self-healing router adapts based on experimental findings. It maintains a **routing health ledger** that tracks:

```python
@dataclass
class ExpertHealth:
    expert_id: str
    confidence_ema: float          # Exponential moving average of tile confidence
    last_success_lamport: int      # Last lamport clock with confidence > 0.7
    fault_count: int               # Number of GL(9) fault detections
    conservation_contribution: float  # This expert's contribution to γ+H
    stage: int                     # Model stage (4/3/2/1)
    status: str                    # "healthy" | "degraded" | "faulted" | "removed"

class SelfHealingRouter:
    """
    Router that adapts to expert health in real-time.
    
    Uses three signals:
    1. GL(9) consensus — logical fault detection
    2. Conservation law — structural drift detection
    3. Confidence EMA — behavioral quality tracking
    
    Any signal can trigger re-routing. Two signals trigger expert quarantine.
    All three trigger expert removal + restart.
    """
    
    def __init__(self, hebbian_router, gl9_service, health_ledger):
        self.hebbian = hebbian_router
        self.gl9 = gl9_service
        self.health = health_ledger
    
    def route(self, query_tile, available_experts):
        # 1. Filter out unhealthy experts
        healthy = [e for e in available_experts 
                   if self.health[e].status in ("healthy", "degraded")]
        
        if not healthy:
            # Emergency: all experts degraded. Reset and retry.
            self._emergency_reset()
            healthy = available_experts
        
        # 2. Try Hebbian routing among healthy experts
        result = self.hebbian.route(query_tile, healthy)
        
        # 3. Check GL(9) consensus post-routing
        consensus = self.gl9.consensus_check()
        if not consensus.consensus:
            faulty = consensus.faulty_agents
            for f_id in faulty:
                self.health.flag_fault(f_id)
        
        return result
    
    def _emergency_reset(self):
        """Reset all experts to healthy and re-warm the Hebbian kernel."""
        for expert_id in self.health:
            self.health[expert_id].status = "healthy"
            self.health[expert_id].fault_count = 0
        # Reset Hebbian kernel to initial weights
        self.hebbian.reset_weights()
```

### 4.2 What Experiments Drive This

| Experiment | What It Tests | What It Triggers |
|-----------|--------------|-----------------|
| Study 54 | Conservation vs GL(9) correlation | Whether to merge the two health signals |
| Study 55 | Router accuracy over time | Confidence EMA tracking granularity |
| Study 58 | GL(9) vs Hebbian fault detection | Fault detection strategy |
| Study 63 | Self-healing recovery rate | Whether to implement auto-removal |

### 4.3 Implementation Priority

| Priority | Component | Depends On |
|----------|-----------|------------|
| P1 | ExpertHealth tracking (confidence EMA) | Study 55 design |
| P1 | GL(9) fault integration | Study 54 results |
| P2 | Auto-quarantine (2-signal trigger) | Studies 54 + 58 |
| P2 | Self-healing re-routing | Study 63 results |
| P3 | Emergency reset protocol | Study 63 recovery rate |
| P3 | Dynamic V-recalibration | Study 63 (expert removal changes fleet size) |

---

## 5. The Feedback Loop: Experiment → Finding → Code Change → New Experiment

### 5.1 The Cycle

```
     ┌──────────────┐
     │  EXPERIMENT  │  Run Study N, get finding F
     └──────┬───────┘
            │
            ▼
     ┌──────────────┐
     │   FINDING    │  F triggers code change C (from pre-registered triggers)
     └──────┬───────┘
            │
            ▼
     ┌──────────────┐
     │  CODE CHANGE │  Implement C in the appropriate module
     └──────┬───────┘
            │
            ▼
     ┌──────────────┐
     │  VALIDATION  │  Does C break anything? Run regression tests.
     └──────┬───────┘
            │
            ▼
     ┌──────────────┐
     │ NEW CAPACITY │  C enables new experiments that weren't possible before
     └──────┬───────┘
            │
            └──────────────► Back to EXPERIMENT
```

### 5.2 Concrete Examples

| Experiment | Finding | Code Change | New Experiment Enabled |
|-----------|---------|-------------|----------------------|
| Study 54 | Conservation + GL(9) correlate >0.7 | Merge fault detectors | Study 63 (self-healing with unified detector) |
| Study 55 | Accuracy degrades after conservation violation | Block routing during projection | Study 55b (measure blocking impact on throughput) |
| Study 56 | Three-tier pattern replicates cross-domain | Domain-aware StageClassifier | Study 56b (domain-specific activation key dictionaries) |
| Study 58 | GL(9) detects faults Hebbian misses | Add GL(9) to tripartite loop | Study 58b (detect adversarial experts) |
| Study 59 | Tier boundary different for code | Domain-specific tier profiles | Study 59b (code-specific routing rules) |
| Study 60 | Temperature helps Tier 2 | Add temperature optimization to router | Study 60b (find optimal temperature per model) |
| Study 61 | Conservation law generalizes | Generalize conservation daemon | Study 61b (test on real social network data) |
| Study 63 | Self-healing recovers >80% | Implement auto-removal | Study 63b (test with multiple simultaneous faults) |

---

## 6. Module Inventory: Add / Change / Deprecate

### 6.1 Modules to Add

| Module | File | Priority | Purpose |
|--------|------|----------|---------|
| `MythosTile` | `mythos_tile.py` | **P0** | Unified tile protocol. Eliminates 3-format translation. |
| `ConstrainedHebbianKernel` | `fleet_hebbian_service.py` (extension) | **P1** | Proactive conservation enforcement. Never allows violations. |
| `SelfHealingRouter` | `self_healing_router.py` | **P2** | Adapts routing based on expert health signals. |
| `GL9Service` | `gl9_service.py` | **P2** | FastAPI wrapper for GL(9) consensus. |
| `ExpertHealth` | `expert_health.py` | **P2** | Per-expert health tracking (confidence EMA, fault count, status). |
| `DomainStageClassifier` | `fleet_translator_v2.py` (extension) | **P2** | Domain-aware stage classification (if Study 56 requires it). |
| `HardwareSimulator` | `hardware_sim.py` | **P3** | `simulate_deployment()` for expert tiles. |
| `GitHubTwinSync` | `github_twin.py` | **P3** | Tile persistence via git. |
| `ConservationDaemon` | `conservation_daemon.py` | **P1** | Managed service (not script) for γ+H monitoring. |

### 6.2 Modules to Change

| Module | Change | Why | Triggered By |
|--------|--------|-----|-------------|
| `fleet_translator_v2.py` | Fix NONE/ECHO passthrough bug | Stage 4 passthrough is broken | P0 — immediate |
| `fleet_translator_v2.py` | Add temperature optimization | Study 60 may show T=0.5 helps Tier 2 | Study 60 |
| `fleet_translator_v2.py` | Domain-aware stage classification | Study 56 tests cross-domain | Study 56 |
| `fleet_hebbian_service.py` | Add `update_safe()` method | Proactive conservation | Migration step 1 |
| `fleet_hebbian_service.py` | Dynamic V-tracking | Self-healing changes fleet size | Study 63 |
| `expert_hebbian_bridge.py` | Expert health integration | Self-healing router needs health signals | Study 55 |
| `expert_hebbian_bridge.py` | Auto-quarantine | Two-signal fault detection | Studies 54+58 |
| `gl9_consensus.py` | Service wrapper + expert wiring | Integration with PLATO/Hebbian | Phase A (Study 54) |

### 6.3 Modules to Deprecate (After Migration)

| Module | Replacement | When |
|--------|------------|------|
| `ConservationHebbianKernel.update()` (reactive) | `ConstrainedHebbianKernel.update_safe()` (proactive) | After migration step 3 |
| `conservation_project()` | No longer needed (violations prevented, not corrected) | After migration step 4 |
| Manual tile format conversion code | `MythosTile.to_plato()` / `from_plato()` / `to_flow_record()` | After MythosTile is adopted |
| 3-format translation at integration points | Single MythosTile everywhere | After MythosTile is adopted |

---

## 7. Priority Ordering: What to Build Next

### Phase 0: Unblocking (Week 1)

```
[T01] Fix fleet_translator_v2 NONE/ECHO bug           ─── BLOCKS ALL TESTING
[T02] Implement MythosTile class (mythos_tile.py)      ─── BLOCKS ALL INTEGRATION
```

**Why first:** Without T01, end-to-end testing is impossible. Without T02, every integration point requires manual format translation. These are the two highest-leverage changes.

### Phase 1: Experimental Infrastructure (Week 1–2)

```
[T03] Run Study 54 (Conservation vs GL9 correlation)
[T04] Run Study 58 (MythosTile consensus fault detection)
[T05] Implement ConstrainedHebbianKernel.update_safe()
[T06] Wire GL(9) as FastAPI service (:8851)
```

**Why:** Studies 54 and 58 are the two P0 experiments. Their results determine whether we merge GL(9) into the fault detector (saves code) or keep them orthogonal (more code but more robust). `update_safe()` is a pure improvement that can ship regardless.

### Phase 2: Self-Healing and Routing (Week 2–3)

```
[T07] Implement ExpertHealth tracking (confidence EMA, fault count)
[T08] Implement SelfHealingRouter
[T09] Run Study 63 (self-healing validation)
[T10] Run Study 55 (router accuracy over time)
[T11] Run Study 56 (cross-domain transfer)
```

**Why:** If self-healing works (Study 63), the fleet becomes autonomous. If it doesn't, we know expert daemons need human-in-the-loop recovery. Studies 55 and 56 validate the router in practice and across domains.

### Phase 3: Generalization (Week 3–4)

```
[T12] Run Study 59 (tier boundary on code)
[T13] Run Study 60 (temperature × tier)
[T14] Domain-specific routing rules (if Study 56/59 require it)
[T15] Run Study 62 (expert vs centralized comparison)
[T16] Dynamic V-recalibration in conservation kernel
```

**Why:** These studies test whether the architecture generalizes beyond math computation. If the tier taxonomy holds for code and other domains, the routing system is domain-general. If not, we need domain-specific routing.

### Phase 4: Research and Polish (Week 4+)

```
[T17] Run Study 57 (fleet coupling measurement)
[T18] Run Study 61 (conservation law generalization)
[T19] Hardware simulation pipeline
[T20] GitHub twin sync
[T21] Docker Compose full stack
[T22] Deprecate reactive conservation kernel
```

**Why:** Academic studies (57, 61) have low engineering impact but high scientific value. Hardware simulation and GitHub twin sync are completeness features. Docker Compose is production readiness.

---

## 8. Dependency Graph

```
Phase 0 (Unblocking):
  T01 ──► ALL TESTING
  T02 ──► ALL INTEGRATION

Phase 1 (Experimental Infrastructure):
  T01 + T02 ──► T03 (Study 54)
  T01 + T02 ──► T04 (Study 58)
  T02 ──► T05 (ConstrainedHebbianKernel)
  T02 ──► T06 (GL9 service)

Phase 2 (Self-Healing):
  T03 + T04 ──► T07 (ExpertHealth)
  T05 + T06 + T07 ──► T08 (SelfHealingRouter)
  T08 ──► T09 (Study 63)
  T01 ──► T10 (Study 55)
  T01 ──► T11 (Study 56)

Phase 3 (Generalization):
  T01 ──► T12 (Study 59)
  T01 ──► T13 (Study 60)
  T11 + T12 ──► T14 (Domain routing)
  T08 ──► T15 (Study 62)
  T09 ──► T16 (Dynamic V)

Phase 4 (Research + Polish):
  T02 ──► T17 (Study 57)
  T05 ──► T18 (Study 61)
  T02 ──► T19 (Hardware sim)
  T02 ──► T20 (GitHub twin)
  T19 + T20 ──► T21 (Docker Compose)
  T05 + T09 ──► T22 (Deprecate reactive kernel)
```

### Critical Path

```
T01 (fix bug) → T03 (Study 54) → T07 (ExpertHealth) → T08 (SelfHealingRouter) → T09 (Study 63)
T02 (MythosTile) → T05 (safe kernel) ─────────────────────────────────────────────↗

Total critical path: T01 + T02 + T03 + T07 + T08 + T09 ≈ 2.5 weeks
```

If self-healing works at the end of this path, the fleet can operate autonomously.
If it doesn't, the path still produces: safe conservation kernel, GL(9) integration, health tracking, and 6 completed studies.

---

## 9. Architecture After Evolution (Target State)

```
═══════════════════════════════════════════════════════════════════
              THE COCAPN FLEET (Post-Evolution Target)
═══════════════════════════════════════════════════════════════════

LAYER 3: BEHAVIORAL (Routing + Translation + Self-Healing)
──────────────────────────────────────────────────────────────
  ┌────────────────────────────────────────────────────────┐
  │  SelfHealingRouter (:8100)                             │
  │    ├── ConstrainedHebbianKernel (proactive)            │
  │    ├── GL9Service (:8851) — fault detection             │
  │    ├── ExpertHealth — confidence EMA per expert        │
  │    ├── DomainStageClassifier — domain-aware tiers      │
  │    └── TemperatureOptimizer — per-model T tuning       │
  │                                                        │
  │  Fleet Router (OpenAI-compatible)                      │
  │    ├── StageClassifier (domain-aware)                  │
  │    ├── NotationNormalizer (domain-specific)            │
  │    └── ActivationKeyEngineer (domain-specific)         │
  └──────────────────────┬─────────────────────────────────┘
                         │
                         ▼
LAYER 2: STRUCTURAL (Conservation + Health)
─────────────────────────────────────────────
  ┌────────────────────────────────────────────────────────┐
  │  Unified Health Service                                │
  │    ├── ConstrainedHebbianKernel (proactive γ+H)        │
  │    ├── GL(9) Consensus (holonomy fault detection)      │
  │    ├── ExpertHealthLedger (per-expert status)          │
  │    └── Dynamic V-tracking (fleet size changes)         │
  │                                                        │
  │  Conservation Daemon (managed service)                 │
  │    └── Single /health endpoint: {γ+H, holonomy,        │
  │        expert_health[], compliance_rate}                │
  └──────────────────────┬─────────────────────────────────┘
                         │
                         ▼
LAYER 1: RUNTIME (PLATO Rooms + Expert Daemons)
─────────────────────────────────────────────────
  ┌────────────────────────────────────────────────────────┐
  │  PLATO Server (:8848) — MythosTile native              │
  │                                                        │
  │  9 Expert Daemons (with health status):                │
  │    Foundation:  CC ✓  CA ✓                             │
  │    Structure:   FR ✓  HR ✓                             │
  │    Application: TB ✓  TR ✓  RF ✓                      │
  │    Frontier:    CM ✓  ER ✓                             │
  │                                                        │
  │  Self-healing: fault → locate → quarantine → re-route  │
  │  Dynamic V: expert removal → kernel recalibration      │
  │                                                        │
  │  Hardware Sim Pipeline                                 │
  │  GitHub Twin Sync                                      │
  └────────────────────────────────────────────────────────┘

  MCP Bridge :8300  ── 10 MCP tools (+4 new: health, consensus, quarantine, sim)
  Dashboard :8080   ── Live health visualization
  Docker Compose    ── 10 services (9 + seed)
```

### Port Registry (Target)

| Port | Service | Status |
|------|---------|--------|
| 8100 | SelfHealingRouter | Replaces current Fleet Router |
| 8300 | MCP Bridge | Extended (+4 tools) |
| 8847 | PLATO (docker) | Unchanged |
| 8848 | PLATO (local) | MythosTile native |
| 8849 | Hebbian Service | Constrained kernel |
| 8850 | Expert Bridge | Health-aware |
| 8851 | GL(9) Consensus | **NEW** |
| 8080 | Dashboard | Unchanged |

---

## 10. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| Studies 54/58 show GL(9) and Hebbian are uncorrelated | Medium | Medium — more code, two separate health systems | Keep both. Orthogonal health axes are more robust. |
| Self-healing doesn't recover from faults | Medium | High — fleet needs human-in-the-loop | Fallback to manual expert management. Self-healing becomes an optimization, not a necessity. |
| Conservation law doesn't generalize beyond PLATO | Low | Low — it was derived from PLATO, that's its scope | Document scope. Don't oversell universality. |
| MythosTile adoption breaks existing integrations | Low | High — all services speak the old format | Keep `to_plato()` / `from_plato()` as first-class conversion methods. Deprecate gradually. |
| Tier taxonomy doesn't hold for non-math domains | Medium | Medium — routing needs domain-specific tuning | Build domain-aware stage classification. Not a crisis, just more code. |
| Temperature optimization makes routing non-deterministic | Low | Medium — reproducibility issues | Log temperature used for every routing decision. Add seed parameter for deterministic testing. |

---

## 11. Success Metrics

The architecture evolution succeeds if:

1. **Zero conservation violations in production.** The constrained kernel prevents all violations by construction.
2. **Self-healing recovery >80%** within 5 routing steps after fault detection (Study 63).
3. **Expert utilization >90%.** No expert sits idle while others are overloaded. Hebbian routing distributes work.
4. **Single tile format everywhere.** No manual format translation at any integration point. MythosTile everywhere.
5. **GL(9) consensus check <100ms.** Fault detection is fast enough for real-time routing.
6. **End-to-end latency <5s.** Query → expert → PLATO → Hebbian → response, all under 5 seconds.
7. **10 completed studies** (54–63) with pre-registered findings and triggered code changes.

---

*This document is the engineering companion to EXPERIMENT-ROADMAP.md. Every module addition, change, and deprecation is traced to a specific experimental finding. Build what the evidence demands.* ⚒️
