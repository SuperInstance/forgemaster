# Fleet-Math Conservation Law Report

> Deep research into SuperInstance/fleet-math and the surrounding ecosystem.
> Forgemaster ⚒️, 2026-05-15

---

## 1. The Conservation Law: γ + H = 1.283 − 0.159·log(V)

### What It Means

In the fleet's coupling analysis, two fundamental quantities are computed for any coupling matrix C (n×n symmetric, real):

- **γ (gamma)** = `algebraic_normalized(C)` — the normalized algebraic connectivity. Computed as `(λ₁ − λ₀) / (λₙ − λ₀)` of the graph Laplacian L = D − C. Measures how *tightly connected* the system is.
- **H** = `coupling_entropy(C)` — spectral entropy of the coupling matrix. Computed from eigenvalue distribution `pᵢ = |λᵢ| / Σ|λⱼ|`, normalized by log(n). Measures how *diverse* the coupling is.

The empirical discovery: **their sum is conserved** for a fixed number of agents V, regardless of coupling matrix structure:

```
γ + H ≈ 1.283 − 0.159 · ln(V)
```

### Physical Analogy

This is the mass-energy conservation of the fleet's coupling space. Just as E = mc² constrains the total energy of a physical system, this law constrains the total "coupling budget" of a fleet. More connectivity (γ) means less diversity (H), and vice versa. You can't increase both simultaneously for a fixed fleet size.

### How It Was Discovered

1. **Monte Carlo sweep**: Random coupling matrices generated for V ∈ {5, 10, 20, 30, 50, 100, 200}, with 5000 samples per V.
2. **Linear regression** of γ+H vs ln(V): fit `γ+H = a + b·ln(V)`.
3. **Result**: a = 1.283, b = −0.159, **R² = 0.9602**.
4. Original derivation lives in `plato-ng experiments/coupling_conversation/proof.py`.

### Why R² = 0.9602 (Not 1.0)

The remaining 3.98% variance comes from:
- **Coupling type differences** — "style" vs "topology" vs "directed" coupling matrices have slightly different intercepts (see §3).
- **Matrix structure noise** — random matrices don't perfectly satisfy the law; real fleet coupling matrices are expected to be tighter.
- **Finite-size effects** — the law is asymptotic; small V shows more scatter.

### What Violations Mean

The code uses a ±2σ tolerance window (95% CI). If γ+H deviates by more than `2 × sigma(V)`:

| Deviation | Diagnosis |
|-----------|-----------|
| > 2σ positive | One agent dominates (preferential attachment) |
| > 2σ negative | Measurement noise or anomalous coupling regime |
| > 4σ | Something is structurally wrong — investigate immediately |

### Sigma Table (Empirical)

| V  | σ     | ±2σ range width |
|----|-------|-----------------|
| 5  | 0.070 | 0.280 |
| 10 | 0.065 | 0.260 |
| 20 | 0.058 | 0.232 |
| 30 | 0.050 | 0.200 |
| 50 | 0.048 | 0.192 |
| 100| 0.042 | 0.168 |
| 200| 0.038 | 0.152 |

Values for intermediate V are linearly interpolated.

---

## 2. The Health Metric System

### FleetHealthMetric (health.py)

A z-score combining three orthogonal health signals:

```python
z = z_gamma + z_H + z_timing
```

Where each component is `(value − baseline_μ) / baseline_σ` against a Monte Carlo baseline (500 random n×109 matrices, n=30 agents).

| Signal | What it measures | Healthy range |
|--------|-----------------|---------------|
| `algebraic_normalized` (γ) | Connectivity of the coupling graph | ~0.05–0.15 |
| `coupling_entropy` (H) | Diversity of coupling patterns | ~0.90–1.00 |
| `timing_stability` | Log-variance of agent response times | Depends on timing distribution |

**Diagnosis levels:**
- |z| < 1.0 → "healthy"
- |z| < 2.0 → "watch" with specific clues (low_connectivity, low_diversity, consensus_herd, chaotic_diverse)
- |z| ≥ 2.0 → "anomaly: investigate"

### Spectral Entropy (H)

Computed from eigenvalue probability distribution:
```python
e = eigvalsh(C) sorted descending
p = |e| / sum(|e|)
H = -sum(p · log(p)) / log(n)  # normalized to [0, 1]
```

High H (→ 1.0) = uniform eigenvalue distribution = diverse coupling.
Low H (→ 0) = single dominant eigenvalue = one agent/pattern dominates.

### Algebraic Connectivity (γ)

Normalized gap between the first two Laplacian eigenvalues:
```python
L = diag(sum(C)) - C
λ = sort(eigvalsh(L))
γ = (λ[1] - λ[0]) / (λ[-1] - λ[0])
```

High γ = well-connected graph (agents are tightly coupled).
Low γ = disconnected/fragmented fleet.

### Timing Stability

```python
log_t = log(timings)
stability = 1 / (1 + var(log_t))
```

Measures how consistent agent response times are. High variance = some agents are lagging.

---

## 3. Coupling Types and the Conservation Law

### Four Coupling Types (types.py)

| Type | Characteristics | Conservation offset |
|------|----------------|-------------------|
| **style** | All off-diagonal non-zero, entries in [0,1] | Universal law: 0.870 − 0.232/ln(V) |
| **topology** | Many zeros (sparse), some positive values | Constant: 1.232 |
| **mixed** | Intermediate between style and topology | 0.742 + 0.349·α (α = mixing parameter) |
| **directed** | Asymmetric matrix (triu ≠ tril) | Constant: 0.995 |

### Auto-Detection (estimate_type)

The system automatically classifies coupling matrices:
1. **Directed**: asymmetry > 0.1 (upper/lower triangle differ significantly)
2. **Topology**: sparsity > 50% (most entries near zero)
3. **Style**: off-diagonal mean < 0.3 (dense, low-weight connections)
4. **Mixed**: everything else

### TypeAwareHealthMetric

Combines auto-detection with type-specific baselines:
```python
baseline = BASELINES[coupling_type]["form"](V)
z = (γ + H - baseline) / 0.15  # approximate sigma
```

Uses a fixed σ ≈ 0.15 as an approximation (less precise than the full interpolation table, but simpler).

### Key Insight

The conservation law holds across all coupling types (CV < 0.2), but the intercept shifts. Topology coupling has the highest baseline (1.232), meaning topological coupling "costs" more of the γ+H budget.

---

## 4. The Calibrator (fleet-calibrator)

### What It Does

Periodically tests fleet models against standardized probe suites to:
1. **Measure accuracy** per domain (arithmetic, reasoning, code, etc.)
2. **Detect phase transitions** — the critical angle where accuracy drops 100% → 0%
3. **Track drift** over time
4. **Emit results to PLATO** for fleet-wide visibility

### Probe Suites

| Suite | Probes | What it tests |
|-------|--------|--------------|
| `addition_depth_probes` | 25 | Addition chains of increasing length (depth 1–25) |
| `multiplication_depth_probes` | 7 | Multiplication chains (depth 1–7) |
| `coefficient_probes` | 8 | Pattern familiarity (Eisenstein norm vs unfamiliar) |
| `syllogism_probes` | 5 | Logical reasoning (simple → transitive) |
| `magnitude_probes` | 5 | Number size (tiny → huge) |

### Status Tiers

| Status | Accuracy | Meaning |
|--------|----------|---------|
| CHAMPION | ≥ 85% | Fleet primary for this domain |
| CONTENDER | ≥ 70% | Backup, good enough for most tasks |
| BACKUP | ≥ 50% | Emergency fallback |
| UNRELIABLE | < 50% | Don't route here |

### Integration with Fleet-Math

The calibrator provides the empirical data that feeds into the router's critical angle table. When a calibrator run detects a phase transition shift (e.g., seed-mini's addition CA drops from ∞ to 25), the router updates its routing table accordingly.

---

## 5. The Router (fleet-router)

### How It Picks Models

```
Prompt → classify_domain() → route(domain) → provider.complete()
```

1. **Domain classification**: keyword matching against 6 domains (arithmetic, reasoning, code, design, analysis, general). Hardcoded table — beats LLM classification in accuracy AND cost.

2. **Critical angle lookup**: each model has measured phase transition depths per domain. The "critical angle" is the depth at which accuracy drops from 100% to 0%. Phase transitions are **binary** (Finding F19) — not a gradual slope, but a wall.

3. **Cheapest safe model**: among models with ∞ or high critical angle for the detected domain, pick the one with lowest cost.

4. **Temperature selection**: T=0.0 for structured tasks ("pump" mode), T=0.7 for creative/strategy ("strategist" mode).

### Current Routing Table

| Domain | Model | Temperature | Cost/1K | Critical Angle |
|--------|-------|-------------|---------|----------------|
| Arithmetic | seed-2.0-mini | 0.0 | $0.05 | ∞ |
| Reasoning | gemini-flash-lite | 0.0 | $0.002 | ∞ (syllogism) |
| Code | glm-5-turbo | 0.3 | $0.08 | ∞ (estimated) |
| Design | seed-2.0-mini | 0.7 | $0.05 | N/A (creative) |
| Analysis | gemini-flash-lite | 0.0 | $0.002 | — |
| General | seed-2.0-mini | 0.0 | $0.05 | ∞ (addition) |

### API

Full FastAPI service with:
- `POST /v1/completions` — route and execute
- `POST /v1/route` — preview routing (no execution)
- `GET /v1/models` — list models with capabilities
- `POST /v1/chat/completions` — OpenAI-compatible drop-in replacement
- `GET /v1/savings` — cost savings vs GPT-4

---

## 6. Fleet-Types (fleet-types)

### Canonical Data Structures

| Type | Purpose | Used by |
|------|---------|---------|
| `AgentId` | Unified agent identifier with name/host/role | All agents |
| `CouplingTensor` | n×n weighted adjacency matrix with spectral properties | Fleet-math, health metrics |
| `StyleVector` | N-dim fingerprint (109-dim or 5-dim) | Style analysis, Penrose encoding |
| `Task` | Lifecycle-tracked work item (PENDING→RESOLVED) | Task coordination |

`CouplingTensor` is the bridge between fleet-types and fleet-math — it's the universal data structure that both packages operate on.

---

## 7. Integration with the Hebbian Layer

No `hebbian_layer.py` exists yet in the fleet-math ecosystem. Here's how it would integrate:

### What a Hebbian Layer Needs

A Hebbian learning rule strengthens connections between co-active units: Δw ∝ x·y. In the fleet context, this means strengthening coupling between agents that produce correlated outputs.

### Integration Points

1. **Coupling matrix as Hebbian weights**: `CouplingTensor.matrix` IS the weight matrix. A Hebbian layer would update C based on co-activation of agents:
   ```python
   C[i][j] += η · output[i] · output[j]  # Hebbian update
   C = project_to_positive_semidefinite(C)  # maintain validity
   ```

2. **Conservation law as a constraint**: After each Hebbian update, the conservation law γ+H = f(V) must still hold. If updating C pushes γ+H outside the ±2σ window, the update violates the coupling budget. This provides a **natural regularization** — the Hebbian layer can't strengthen connections without weakening diversity (or vice versa).

3. **Spectral entropy as a stability signal**: If H drops too low during Hebbian training, the system is collapsing to a single dominant pattern. The health metric system already detects this ("low_diversity" diagnostic). The Hebbian layer should monitor H and apply diversity-preserving updates when H < threshold.

4. **Coupling types affect learning rate**: Different coupling types (style, topology, mixed, directed) have different conservation law baselines. The Hebbian learning rate η should be calibrated per type so that updates stay within the conservation envelope.

5. **Critical angles inform routing**: The router's critical angle table tells the Hebbian layer which models are reliable for which domains. If a model's CA drops (detected by the calibrator), the Hebbian layer should reduce its coupling weight in that domain — the model is no longer trustworthy.

### Proposed Architecture

```python
class HebbianCouplingLayer:
    def __init__(self, n_agents, coupling_type="style"):
        self.C = initialize_coupling(n_agents)  # uniform
        self.coupling_type = coupling_type
        self.eta = 0.01  # learning rate
        self.conservation_law = fleet_conservation_law(n_agents, coupling_type)
    
    def update(self, agent_outputs):
        # Hebbian update
        delta = self.eta * np.outer(agent_outputs, agent_outputs)
        self.C += delta
        self.C = project_to_psd(self.C)
        
        # Check conservation law
        gamma = algebraic_normalized(self.C)
        H = coupling_entropy(self.C)
        if not self.conservation_law["is_conserved"](gamma, H):
            # Scale back update to stay within budget
            self.C -= delta * 0.5  # conservative rollback
    
    def health(self):
        return FleetHealthMetric.compute(self.C)
```

---

## 8. Stability Assessment

### Stable (Production-Ready)

| Component | Status | Evidence |
|-----------|--------|----------|
| Conservation law formula | ✅ Stable | R²=0.9602, 35,000 Monte Carlo samples, 15 tests passing |
| `coupling_entropy` | ✅ Stable | Pure linear algebra, well-tested |
| `algebraic_normalized` | ✅ Stable | Standard graph theory |
| `FleetHealthMetric` | ✅ Stable | Monte Carlo baseline, z-score diagnostics |
| `CouplingAnalysis` (spectral) | ✅ Stable | Standard RMT methods |
| `EisensteinLattice` | ✅ Stable | 12-chamber hexagonal encoding |
| `PenroseEncoder` | ✅ Stable | 5th roots of unity projection |
| `vicreg_loss` | ✅ Stable | Standard VICReg implementation |
| Fleet-types | ✅ Stable | Canonical data structures |
| Router domain classification | ✅ Stable | Keyword matching |
| Router API (FastAPI) | ✅ Stable | OpenAI-compatible endpoint |

### Experimental / Needs Work

| Component | Status | Issue |
|-----------|--------|-------|
| Coupling-type baselines | ⚠️ Partial | Only "style" has multi-V data; topology/mixed/directed have single-V placeholders |
| TypeAwareHealthMetric σ | ⚠️ Approximate | Uses fixed σ=0.15 instead of interpolated sigma table |
| Topology conservation form | ⚠️ Placeholder | `form: lambda V: 1.232` — no V-scaling |
| Mixed conservation form | ⚠️ Partial | Depends on mixing parameter α that isn't auto-detected |
| Calibrator → Router pipeline | ⚠️ Manual | Calibrator emits to PLATO, but router table isn't auto-updated |
| `Pythagorean48` | 🚧 Stub | `pythagorean48_snap()` is trivial rounding; not the full 6-bit encoding |
| Hebbian layer integration | 🚧 Not started | No code exists yet |

### Missing / TODO

- **Real fleet data validation**: The conservation law was derived from random matrices. Needs validation against actual fleet coupling matrices.
- **Streaming updates**: Conservation law only works for fixed V. Dynamic agent joining/leaving isn't handled.
- **Multi-layer coupling**: Current system is flat (one coupling matrix). Nested/hierarchical coupling (agent → team → fleet) isn't modeled.
- **Calibrator scheduling**: `run_calibrate.py` is manual. Should run on cron every 6 hours.

---

## 9. Repository Summary

| Repo | Version | Tests | Dependencies |
|------|---------|-------|-------------|
| **fleet-math** | 0.3.1 | 15 in test_conservation.py | numpy |
| **fleet-calibrator** | 0.1.0 | (probe suites, no test file) | httpx |
| **fleet-router** | 0.1.0 | (API endpoints, no test file) | fastapi, uvicorn, httpx, pydantic |
| **fleet-types** | (no version) | 10 (from CI badge) | numpy |

### Dependency Graph

```
fleet-types (CouplingTensor, StyleVector)
    ↑
fleet-math (health metrics, conservation law, spectral analysis)
    ↑
fleet-calibrator (probe suites → calibration results)
    ↓
fleet-router (critical angles → routing decisions)
```

---

*End of report. Built from source analysis of all four repos on 2026-05-15.*
