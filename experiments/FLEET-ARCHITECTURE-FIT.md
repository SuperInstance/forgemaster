# Fleet Architecture Fit Analysis — FM + Oracle1 Alignment

## What Oracle1 Built (Structural Layer)

### fleet-math (v0.3.0)
- `CouplingAnalysis.build_coupling()` — spectral decomposition of agent coupling
- `CouplingTensor` — universal (n,n) adjacency matrix type
- `FleetHealthMetric` — z-scored health from spectral gap + entropy + timing
- `TypeAwareHealthMetric` — coupling-type-aware calibration (style/topology/mixed/directed)
- Conservation law baselines: γ+H = constant per coupling type
- `CouplingAnalysis.rmt_classification()` — Random Matrix Theory class detection

### fleet-types
- `AgentId` — canonical agent identifiers (oracle1, forgemaster, jc1, ccc)
- `CouplingTensor` — eigenvalues, spectral_gap, fiedler_value
- `StyleVector` — N-dim style fingerprints with cosine similarity
- `TaskStatus` — lifecycle enum (pending/active/resolved/superseded/retracted)

### federation-protocol
- Minimum viable: exchange coupling summaries (spectral_gap, agent_count, health)
- Falsification test: spectral gaps must agree within 0.1

### plato-midi-bridge
- `gauge_connection.py` — parallel transport of eigenvalues across PLATO rooms
- `format_bridge.py` — standardized eigenvalue tile format
- Holonomy computation: measures misalignment between two PLATO instances

## What FM Built (Behavioral Layer)

### Critical Angle System
- `core/critical_angle.py` — measures phase transitions per model × domain
- `core/fleet_router.py` — routes queries to cheapest safe model (3D: model × domain × temperature)
- `core/fleet_health.py` — periodic calibration, drift detection
- `core/tuna_tower.py` — multi-model observation, Fresnel zones, bottom topology

### Findings (F19-F25)
- Phase transitions are binary, universal, prompt-dependent
- Temperature is the mode switch (T=0.0 pump, T=0.7 strategist)
- 84% cost reduction via critical angle routing
- Models have non-overlapping infinite domains

### Room Protocol
- `core/room_protocol.py` — PLATO rooms as execution contexts
- 5 room templates: agentic loop, game, website, experiment, evolution
- ROOM = state + protocol + lifecycle

## THE FIT: Where They Interlock

### Complementary (No Overlap)
| Oracle1 (Structure) | FM (Behavior) | How They Connect |
|--------------------|----------------|------------------|
| Spectral gap (eigenvalue distance) | Critical angle (depth where accuracy breaks) | Spectral gap predicts WHERE to look for phase transitions |
| CouplingTensor (agent coupling matrix) | Fleet router (model routing) | Coupling tensor feeds into router: tightly coupled models need diverse routing |
| FleetHealthMetric (z-scored spectral health) | Fleet health calibration (drift detection) | Combine: structural health + behavioral health = complete picture |
| Conservation law (γ+H = const) | C(m,t) = T·A·K·M·E | Conservation law constrains the theoretical space; FM's formula measures it |
| Fiedler value (code coupling) | Critical angle map (model capability) | Low Fiedler = clean code boundaries = safe to route independently |
| Gauge connection (PLATO-PLATO alignment) | Room protocol (execution contexts) | Gauge measures whether two rooms agree; protocol enforces they stay aligned |

### Overlaps (Need Reconciliation)
1. **Both define "health" differently**
   - Oracle1: spectral health (coupling entropy, algebraic connectivity)
   - FM: behavioral health (critical angle drift, accuracy curves)
   - Resolution: `FleetHealth` should compute BOTH and return a composite score

2. **Both have "types" but different schemas**
   - Oracle1: `AgentId`, `CouplingTensor`, `StyleVector`, `TaskStatus`
   - FM: `ModelProfile`, `QueryAxis`, `AngleMeasurement`, `RoomProtocol`
   - Resolution: FM types extend Oracle1's fleet-types (add behavioral dimensions)

3. **Both define "routing" but at different layers**
   - Oracle1: federation routing (which fleet to send work to)
   - FM: model routing (which model within a fleet)
   - Resolution: Two-tier routing — Oracle1 routes between fleets, FM routes within fleet

4. **Both have PLATO integration but different APIs**
   - Oracle1: PLATO v3 with question/answer submit
   - FM: room_protocol.py with tile schemas and lifecycle
   - Resolution: Oracle1's PLATO server needs room lifecycle API (FM's protocol extends it)

## THE GAPS (What Neither Has Built Yet)

1. **No unified API gateway** — PLATO server is raw HTTP, no auth, no routing
2. **No real-time event bus** — tiles are polled, not pushed
3. **No model registry service** — critical angles are hardcoded in Python, not served from PLATO
4. **No billing/usage tracking** — no way to know what queries cost in aggregate
5. **No experiment reproducibility** — findings are markdown, not structured experiments
6. **No rendering layer** — room protocol has hints but no actual renderers
7. **No external API** — nobody outside the fleet can call into the system

## RECOMMENDATION: What to Build Next

### Week 1 Priority: Fleet Router as a Service (FM leads)
This is the revenue path. FM has the critical angle data. Ship it as an API.
Use Oracle1's fleet-types for shared types.

### Week 2 Priority: Unified Health Service (Joint)
Combine Oracle1's spectral health with FM's behavioral health.
One `/health` endpoint that returns both dimensions.

### Week 3 Priority: Room Runtime (FM leads, Oracle1 validates)
FM's room_protocol.py becomes the PLATO server extension.
Oracle1's gauge_connection.py validates cross-room alignment.

### Week 4 Priority: Federation (Oracle1 leads, FM provides routing)
Oracle1's federation-protocol goes live.
FM's fleet-router becomes the intra-fleet routing layer beneath federation.

## What NOT to Reconcile (Keep Separate)
- Oracle1's math stays in fleet-math (don't rewrite in FM's core/)
- FM's experiments stay in experiments/ (don't move to Oracle1's workspace)
- Both keep their own AI writings (different voices = different perspectives)
- No shared codebase — use fleet-types for shared types, everything else stays independent
