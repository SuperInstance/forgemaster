# SnapKit v2 Architecture: Composing the 10 Fixes

**Forgemaster ⚒️ | 2026-05-11 | Complete Architecture Document**

---

## 1. Module Dependency Graph (ASCII)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SnapKit v2 Architecture                      │
│                                                                      │
│  ┌───────────────┐     uses     ┌─────────────────┐                 │
│  │ Fix 1:        │──────────────►│ Fix 2:          │                 │
│  │ TensorTol     │              │ MultiScaleSnap  │                 │
│  └───────────────┘              └────────┬────────┘                 │
│        │                                 │                         │
│        │  provides PD                    │  provides K scales      │
│        │  constraint                     │  per observation        │
│        ▼                                 ▼                         │
│  ┌───────────────────────────────────────────────────────────┐     │
│  │                   Fix 6: LatticeMesh                       │     │
│  │  Core orchestration — regions, boundaries, topology dispatch│     │
│  │                                                             │     │
│  │  - owns: Dict[region_name, MeshRegion]                      │     │
│  │  - owns: List[MeshBoundary]                                 │     │
│  │  - method: snap(point) → dispatches to correct topology     │     │
│  │  - method: verify_h1_zero() → boundary completeness check   │     │
│  └─────────────────────────┬───────────────────────────────────┘     │
│                            │                                        │
│                  ┌─────────┼─────────┐                              │
│                  ▼                   ▼                              │
│  ┌────────────────────┐    ┌──────────────────┐                    │
│  │ Fix 3:             │    │ Fix 9:            │                    │
│  │ AttentionBudget    │    │ ChannelGrid       │                    │
│  └────────┬───────────┘    └────────┬─────────┘                    │
│           │                        │                               │
│           │  pools                  │  rank-derived channels        │
│           │  (safety/op/explore)    │  (A₂→2, A₃→3, etc.)          │
│           ▼                        ▼                               │
│  ┌───────────────────────────────────────────────────────────┐     │
│  │               Fix 7: DAG Pipeline                          │     │
│  │  Directed acyclic graph of pipeline nodes                  │     │
│  │                                                             │     │
│  │  Nodes: SNAP → MATCH → BRANCH → EXECUTE/LEARN → UPDATE     │     │
│  │         → TRANSFORM → ALLOCATE                              │     │
│  │  Edges: data flows, conditional, feedback (learning only)   │     │
│  └─────────────────────────┬───────────────────────────────────┘     │
│                            │                                        │
│                  ┌─────────┼─────────┐                              │
│                  ▼                   ▼                              │
│  ┌────────────────────┐    ┌──────────────────┐                    │
│  │ Fix 4:             │    │ Fix 5:            │                    │
│  │ LatticeMatching    │    │ TopologyTagged    │                    │
│  │ (Eisenstein dist)  │    │ Script (ADE tag)  │                    │
│  └────────────────────┘    └──────────────────┘                    │
│                            │                                        │
│                            ▼                                        │
│  ┌───────────────────────────────────────────────────────────┐     │
│  │           Fix 8: MultiResolutionOutput                     │     │
│  │  MINIMAL → STANDARD → FULL → RESEARCH                     │     │
│  │  Lazy evaluation, subscriber-based resolution escalation   │     │
│  └───────────────────────────────────────────────────────────┘     │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────┐     │
│  │           Fix 10: DistributedSnap                         │     │
│  │  Node-based distribution with H¹ boundary consistency     │     │
│  │  - broadcast on boundary-crossing events                  │     │
│  │  - consensus resolution for H¹ ≠ 0 conflicts             │     │
│  │  - each Node owns a LatticeMesh partition                 │     │
│  └───────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
```

### Dependency Order

The modules form a DAG (no cycles in inference):

```
TensorTol (1) ──────┐
MultiScaleSnap (2) ──┤
                     ├──► LatticeMesh (6) ──► DAG Pipeline (7) ──► Output (8)
AttentionBudget (3) ─┘         │
ChannelGrid (9) ───────────────┘
                                    │
    LatticeMatching (4) ◄───────────┘
    TopologyTagged (5) ◄────────────┘
    
    DistributedSnap (10) wraps everything, each node has its own LatticeMesh
```

---

## 2. Data Flow Diagram

```
### Standard Inference Flow (single observation)

point ∈ ℝⁿ
    │
    ▼
[LatticeMesh.snap(point)] ─────────── Fix 6
    │
    ├──→ Find region: which region contains this point?
    │       │
    │       ▼
    │   [MeshRegion] ─────────── region has topology τ, tolerance T
    │       │
    │       ├──→ Fix 1: Check TensorTolerance T(point - baseline)
    │       │       │  if T(u,v) ≤ 1.0: SNAP (within tolerance)
    │       │       │  if T(u,v) > 1.0:  DELTA (exceeded)
    │       │       │
    │       │       ▼
    │       │   Fix 2: MultiScaleSnap
    │       │       │  Snap at t₀, t₁, t₂, t₃
    │       │       │  → freed_cognition[0..3]
    │       │       │
    │       │       ▼
    │       │   SnapResult (is_delta, delta_magnitude, snapped_point)
    │       │
    │       └──────────────────────────────────┐
    │                                          │
    ▼                                          ▼
[ChannelGrid] ─── Fix 9         [AttentionBudget] ─── Fix 3
    │ Assigns channel by           │ Allocate attention from pools:
    │ topology + basis direction   │ safety (30%), op (50%), explore (20%)
    │                              │ Returns allocated_attention (0.0 if SNAP)
    ▼                              ▼
[MultiResolutionOutput] ─── Fix 8
    │ MINIMAL: (snapped_coords, is_delta)
    │ STANDARD: + (original, delta, within_tolerance)
    │ FULL: + (history, stats, tolerance_state)
    │ RESEARCH: + (boundary_conditions, holonomy, cohomology)
    │
    ▼
[Consumer subscribes at desired resolution]

### Script Matching Flow (when delta exceeds attention threshold)

delta + attention_allocated
    │
    ▼
[DAG Pipeline.execute] ─── Fix 7
    │
    ├──→ [MATCH node]
    │       ├──→ Fix 4: LatticeMatching.match(delta, tolerance_tensor)
    │       │       Uses Eisenstein distance (not cosine) for A₂
    │       │       Uses minimal embedding distance for cross-topology
    │       │
    │       └──→ Fix 5: TopologyTaggedScripts.find_candidates(delta)
    │               Filters by topology match (isometric embedding)
    │               Returns script(s) with highest lattice similarity
    │       │
    │       ▼
    ├──→ [BRANCH node]
    │       if match.found and match.confidence > threshold:
    │           → [EXECUTE node] — run matched script
    │       else:
    │           → [LEARN node] — build new script from delta pattern
    │                   │
    │                   ▼
    │               [UPDATE node] — update snap tolerance from learned pattern
    │                   │
    │                   └──→ Fix 1: adjust TensorTolerance
    │                       Fix 2: adjust scale ratios
    │
    ├──→ [TRANSFORM node] (if cross-topology matching)
    │       Embed query into script's topology space
    │       → retry MATCH with transformed query
    │
    └──→ [ALLOCATE node]
            If attention exhausted → drop delta (return SNAP)
            Else → proceed
    
    Results feed back to [SNAP node] for the next observation

### Distributed Flow (when point crosses region or node boundary)

Node A receives point ∈ R₁ (A₂ region)
    │
    ├──→ snap locally (same as single-node flow above)
    │
    └──→ is point near boundary R₁₂?
            │
            YES → Fix 10: Broadcast to neighbor Node B
                    │
                    Node B receives:
                        ├──→ snap independently using R₂ (D₄ topology)
                        └──→ compare results at gluing interface

                        if consistent (H¹ = 0):
                            → continue, no action needed
                        if inconsistent (H¹ ≠ 0):
                            → log obstruction
                            → resolve via consensus:
                                - If both deltas ≈ equally valid → use snapshot
                                - If one side is clearly superior → adopt that
                                - If systematic → adjust gluing (repartition)
```

---

## 3. API Surface: Key Classes and Methods

### Fix 1: TensorTolerance

```python
class TensorTolerance:
    def __init__(self, matrix: np.ndarray | float)
    def within(self, u: float, v: float) -> bool
    def scale(self, factor: float) -> TensorTolerance
    def compose(self, other: TensorTolerance) -> TensorTolerance
    def to_gram(self) -> np.ndarray
    @staticmethod
    def isotropic(t: float) -> TensorTolerance  # specialization
    @staticmethod
    def from_tolerances(t1: float, t2: float, t12: float = 0.0) -> TensorTolerance
    @property
    def eigenvalues(self) -> Tuple[float, float]
    @property
    def condition_number(self) -> float  # anisotropy measure
```

**Stream-level configuration:**
```python
# Per-stream tolerance tensors
tolerances = {
    'safety':    TensorTolerance.isotropic(0.01),       # tight, isotropic
    'timing':    TensorTolerance.isotropic(0.10),       # moderate
    'resources': TensorTolerance.from_tolerances(0.05, 0.20),  # anisotropic
    'knowledge': TensorTolerance.from_tolerances(0.10, 0.10, 0.05),  # coupled
}
```

### Fix 2: MultiScaleSnap

```python
class MultiScaleResult:
    scale_results: List[SnapResult]
    freed_cognition: List[float]      # N(z - Sₖ(z)) at each scale
    snap_mask: List[bool]              # which scales snapped
    delta_profile: List[float]         # delta magnitude at each scale

class MultiScaleSnap:
    def __init__(self, base_tolerance: float, scales: int = 4, ratio: float = 10.0)
    def observe(self, value: complex | float) -> MultiScaleResult
    def observe_vector(self, values: np.ndarray) -> List[MultiScaleResult]
    def set_scales(self, tolerances: List[float])
    def scale_contributions(self, result: MultiScaleResult) -> np.ndarray
```

### Fix 3: AttentionBudget

```python
class Pool:
    name: str
    share: float        # fraction of total budget (0.0 - 1.0)
    reserve: float      # minimum unallocated (0.0 - 1.0)
    ceiling: float      # max per delta (0.0 - 1.0)
    allocated: float    # running total allocated

class AttentionBudget:
    def __init__(self, total: float = 1.0)
    def allocate(self, channel: str, delta: float, source: str) -> float
    def release(self, channel: str, amount: float)
    def snapshot(self) -> Dict[str, Pool.Snapshot]
    def reset_cycle(self)
    @property
    def available(self) -> Dict[str, float]
    @property
    def utilization(self) -> float  # overall (0.0 - 1.0)
    
    # Pool configuration
    @staticmethod
    def default_pools() -> Dict[str, Pool]
    def custom_pool(self, name: str, share: float, reserve: float, ceiling: float)
```

### Fix 4: LatticeMatching

```python
class LatticeMatching:
    @staticmethod
    def eisenstein_distance(p1: np.ndarray, p2: np.ndarray) -> float
    
    @staticmethod
    def cross_topology_distance(p1: np.ndarray, topology1: SnapTopologyType,
                                 p2: np.ndarray, topology2: SnapTopologyType) -> float
    
    @staticmethod
    def match_rank(script: TopologyTaggedScript, query: np.ndarray) -> float
    
    def __init__(self, metric: str = 'lattice')
    def find_matches(self, query: np.ndarray, 
                     candidates: List[TopologyTaggedScript],
                     topology: SnapTopologyType,
                     k: int = 5) -> List[MatchResult]
    
    def similarity(self, query: np.ndarray, script: TopologyTaggedScript) -> float
```

### Fix 5: TopologyTaggedScript

```python
class TopologyTag:
    ade_type: ADEType
    rank: int
    coxeter_number: int
    metric: str
    tolerance_tensor: TensorTolerance
    lattice_basis: np.ndarray
    
    def is_isometric_to(self, other: TopologyTag) -> bool
    def embedding_distance(self, other: TopologyTag) -> float

class TopologyTaggedScript:
    def __init__(self, sequence: List, topology_tag: TopologyTag)
    def matches(self, context: TopologyTag) -> MatchDecision
    def embed_into(self, target_topology: TopologyTag) -> 'TopologyTaggedScript'
    @property
    def mobility_score(self) -> float  # how transferable is this script?
```

### Fix 6: LatticeMesh

```python
class MeshRegion:
    name: str
    topology: SnapTopologyType
    bounds: Callable[[np.ndarray], bool]
    tolerance: TensorTolerance
    channels: List[Channel]
    
    def contains(self, point: np.ndarray) -> bool
    
    def snap(self, point: np.ndarray) -> SnapResult
    def learn(self, point: np.ndarray, delta: float)
    def to_dict(self) -> dict

class MeshBoundary:
    region_a: str
    region_b: str
    gluing_map: Callable[[np.ndarray], np.ndarray]  # coordinate transform
    h1_obstruction: float  # computed, cached
    active: bool
    
    def check_consistency(self, point: np.ndarray) -> bool

class LatticeMesh:
    def __init__(self)
    def add_region(self, name: str, topology: SnapTopologyType, 
                   bounds: Callable, tolerance: TensorTolerance)
    def add_boundary(self, region_a: str, region_b: str, 
                     gluing_map: Callable)
    def snap(self, point: np.ndarray) -> SnapResult
    def region_for(self, point: np.ndarray) -> MeshRegion
    def verify_h1_zero(self) -> Dict[str, bool]
    def recompute_boundaries(self)
    def to_dict(self) -> dict
    @classmethod
    def from_dict(cls, data: dict) -> 'LatticeMesh'
```

### Fix 7: DAGPipeline

```python
class PipelineNodeType(Enum):
    SNAP = 'snap'
    MATCH = 'match'
    BRANCH = 'branch'
    EXECUTE = 'execute'
    LEARN = 'learn'
    TRANSFORM = 'transform'
    ALLOCATE = 'allocate'
    UPDATE = 'update'

class PipelineEdge:
    source: str
    target: str
    predicate: Optional[Callable]  # conditional edge
    feedback: bool                 # learning-only edge
    
    def active(self, context: Dict) -> bool

class DAGPipeline:
    def __init__(self)
    def add_node(self, name: str, node_type: PipelineNodeType, processor: Callable)
    def add_edge(self, source: str, target: str, 
                 conditional: Callable = None, feedback: bool = False)
    def execute(self, input_data: Any) -> PipelineResult
    def execute_batch(self, inputs: List) -> List[PipelineResult]
    def to_dot(self) -> str              # Graphviz export
    def validate(self) -> bool            # acyclic check, no dangling edges
    def visualize(self) -> str            # ASCII pipeline diagram
    
    # Pre-built pipelines
    @classmethod
    def standard_inference(cls) -> 'DAGPipeline'
    @classmethod
    def learning_pipeline(cls) -> 'DAGPipeline'
    @classmethod
    def research_pipeline(cls) -> 'DAGPipeline'
```

### Fix 8: MultiResolutionOutput

```python
class OutputLevel(Enum):
    MINIMAL = 0
    STANDARD = 1
    FULL = 2
    RESEARCH = 3

class SnapOutput:
    # MINIMAL (always present)
    snapped: complex
    is_delta: bool
    
    # STANDARD (lazy)
    _standard: Optional[StandardData]
    
    # FULL (lazy)
    _full: Optional[FullData]
    
    # RESEARCH (lazy)
    _research: Optional[ResearchData]
    
    def resolve(self, level: OutputLevel) -> 'SnapOutput'
    @property
    def standard(self) -> StandardData
    @property
    def full(self) -> FullData
    @property
    def research(self) -> ResearchData

class MultiResolutionOutput:
    def __init__(self)
    def publish(self, snap_result: SnapResult) -> SnapOutput
    def subscribe(self, consumer_id: str, level: OutputLevel)
    def unsubscribe(self, consumer_id: str)
    def broadcast(self, consumers: List[str]) -> List[SnapOutput]
```

### Fix 9: ChannelGrid

```python
class Channel:
    name: str
    topology: SnapTopologyType
    basis_direction: int        # 0 = α, 1 = β, etc.
    ade_rank: int
    
    def vector_component(self, v: np.ndarray) -> float
    def delta_severity(self, delta: float) -> float  # normalized 0-1

class ChannelGrid:
    def __init__(self, lattice_mesh: LatticeMesh)
    def channel_for(self, point: np.ndarray, delta: float) -> Channel
    def channels_for_topology(self, topology: SnapTopologyType) -> List[Channel]
    def to_json(self) -> list
    @property
    def count(self) -> int
    @property
    def active_channels(self) -> List[Channel]
```

### Fix 10: DistributedSnap

```python
class BoundaryCheck:
    point: np.ndarray
    neighbor_id: str
    consistent: bool
    local_delta: float
    neighbor_delta: float
    h1_value: float

class DistributedSnap:
    def __init__(self, node_id: str, neighbors: List[str], 
                 mesh: LatticeMesh, comm_backend: str = 'mpi' | 'grpc')
    def snap(self, point: np.ndarray, source: str = 'local') -> SnapResult
    def receive_broadcast(self, point: np.ndarray, 
                          neighbor_result: dict,
                          neighbor_id: str) -> BoundaryCheck
    def resolve_conflict(self, check: BoundaryCheck) -> SnapResult
    def verify_all_boundaries(self) -> Dict[str, bool]
    def partition(self) -> Dict[str, List[str]]  # region → node mapping
```

---

## 4. Comparison: v1 vs v2

| Feature | v1 | v2 | Improvement |
|---------|----|----|-------------|
| **Tolerance** | 1 float, isotropic | Tensor, anisotropic per direction × stream | Latent differentiation |
| **Scales** | 1 | K geometric (default 4) | Scale-space analysis |
| **Attention** | None (every delta equal) | 3 pools + budget + reserve | Prioritized allocation |
| **Matching** | Cosine similarity | Eisenstein distance + cross-topology embedding | Geometry-correct |
| **Scripts** | Untagged sequence | Topology-tagged with ADE metadata | Safe cross-domain transfer |
| **Topology** | Single global | LatticeMesh: per-region ADE + boundary glue | Specialized by need |
| **Pipeline** | Linear | DAG with branch/feedback/condition | Flexible, learnable |
| **Output** | Single SnapResult | 4 resolution levels | Consumer-appropriate |
| **Channels** | 9 hardcoded | Σ rank of active topologies | Derivation from first principles |
| **Distribution** | None | MPI/gRPC with H¹ boundary consensus | Scales to cluster |
| **Proofs** | None | H¹=0 boundary verification, Eisenstein norm multiplicativity | Formal guarantees |

### Quantitative Comparison

| Metric | v1 | v2 |
|--------|----|----|
| **Scalar tolerance → Tensor tolerance** | 1 parameter | 4+ parameters (PD matrix) |
| **Attention resolution** | None | 3 pools × K scales = 12 states |
| **Matching accuracy** | Cosine: O(d) float ops | Eisenstein: O(1) lattice ops |
| **Wrong topology cost** | Silent misapplication | Rejected (H¹ ≠ 0) |
| **Distribution overhead** | N/A | O(neighbors) broadcast on boundary-crossing |
| **Output cost** | Always full | Lazy: O(1) for MINIMAL |
| **Channel derivation** | Memorized | Dynamic from mesh |
| **Formal guarantees** | None | H¹=0 for boundary consistency |

---

## 5. Migration Path: v1 → v2

### Phase 1: Wrapper Compatibility (Same API, New Internals)

```python
# v1 → v2 seamless upgrade: same import, better implementation
from snapkit import SnapFunction

# Old code still works:
snap = SnapFunction(tolerance=0.1, topology=HEXAGONAL)
result = snap.observe(0.05)

# But internally, SnapFunction now uses TensorTolerance(Fix 1) + MultiScaleSnap(Fix 2)
# with isotropic tensor and single scale, 100% backward compatible
```

**Timeline:** Immediate — just swap the import.

### Phase 2: Gradual Adoption

```
Step 1: Replace tolerance=0.1 with TensorTolerance.isotropic(0.1)
        → Non-breaking, same behavior
        → Benefit: ready for anisotropy later

Step 2: Enable MultiScaleSnap on specific channels
        snap = SnapFunction(tolerance=0.1, multi_scale=True, num_scales=3)
        → New parameter, defaults to old behavior (1 scale)

Step 3: Define topologies for specific data regions
        mesh = LatticeMesh()
        mesh.add_region('safety', topology=A1, bounds=in_safety_region, ...)
        → New abstraction layer, doesn't replace old snap for simple use

Step 4: Replace string channels with ChannelGrid
        channels = ChannelGrid(mesh)
        → Dynamic from mesh configuration

Step 5: Add AttentionBudget
        budget = AttentionBudget()
        result = budget.allocate('safety', delta)
        → Only affects hot path if explicitly used

Step 6: Switch to DAGPipeline
        pipeline = DAGPipeline.standard_inference()
        pipeline.execute(point)
        → Replaces manual chaining

Step 7: Add LatticeMatching for scripts
        matcher = LatticeMatching(metric='eisenstein')
        matches = matcher.find_matches(query, tagged_scripts)
        → New script system, parallel to old

Step 8: Multi-resolution output
        output = MultiResolutionOutput()
        output.subscribe('dashboard', OutputLevel.FULL)
        output.subscribe('embedded_sensor', OutputLevel.MINIMAL)
        → Subscription-based, no breaking changes to SnapResult

Step 9: LatticeMesh topology tagging for existing scripts
        for script in existing_scripts:
            script.topology_tag = TopologyTag.from_data(script.source_data)
        → Batch migration

Step 10: Distributed deployment (if needed)
        dist = DistributedSnap(node_id='safety_node', neighbors=['control_node'])
        → New architecture, not a migration
```

### Phase 3: Deprecation of v1 APIs

```python
# Old way — works but warns
snap = SnapFunction(tolerance=0.1)
# DeprecationWarning: Use TensorTolerance instead of float tolerance

# New way — preferred
tolerance = TensorTolerance.isotropic(0.1)
snap = SnapFunction(tolerance=tolerance)
```

### Phase 4: Full v2 Native

```python
# v2 native — no backward compatibility, full LatticeMesh
mesh = LatticeMesh()
mesh.add_region('safety', topology=A1, 
                bounds=lambda p: is_safety_critical(p),
                tolerance=TensorTolerance.isotropic(0.01))
mesh.add_region('planning', topology=A3,
                bounds=lambda p: is_planning_state(p),
                tolerance=TensorTolerance.from_tolerances(0.1, 0.05))

channels = ChannelGrid(mesh)
budget = AttentionBudget()

pipeline = DAGPipeline.standard_inference()
output = MultiResolutionOutput()
pipeline >> output  # pipe into output

# Distributed
dist = DistributedSnap('node1', ['node2', 'node3'], mesh)
dist.snap(observation)
```

---

## 6. Architectural Principles

### A. PLATO-First Design

The LatticeMesh configuration is the **canonical state**. It lives in PLATO, not in ephemeral memory:

```
PLATO room: /fleet/snapkit/v2/lattice_mesh
- Region definitions with ADE types
- Boundary gluing maps
- Active tolerance tensors
- Attention pool configuration
```

### B. Composition over Conglomeration

Each fix is an independent module with a clear interface. The LatticeMesh composes them, but doesn't conflate them. You can use Fix 1 without Fix 2, Fix 3 without Fix 4, etc.

### C. Sheaf-Theoretic Correctness

The H¹=0 boundary condition (Fix 6, 10) provides a **mathematical guarantee** of path independence. This is the core insight that makes the whole system compose correctly — without it, region boundaries could produce contradictory results.

### D. Lazy Evaluation

Multi-resolution output (Fix 8) means: **compute what you need, nothing more**. An embedded device gets a single boolean. A research dashboard gets the full cohomology trace. Same source, different cost.

### E. Scale Invariance

The system's behavior at 1 node with 3 regions is isomorphic to its behavior at 100 nodes with 300 regions. The H¹ boundary protocol doesn't change. The LatticeMesh doesn't change. Only the partition changes.

---

## 7. Known Limitations

1. **H¹ verification is O(boundaries × dimensions).** For high-resolution meshes with many thin regions, this can be significant. Mitigate by caching verification results and only recomputing when mesh changes.

2. **Eisenstein distance is only optimal in 2D.** A₂ is the universal solvent, but cross-topology matching requires embedding that loses information. For topologies that don't embed isometrically (e.g., E₈ into anything lower-dimensional), matching degrades gracefully but not perfectly.

3. **Attention budget ceilings can cause starvation.** A single loud channel can max out a pool's ceiling, starving other channels. The reserve mechanism mitigates this but doesn't eliminate it.

4. **Distributed consensus is eventually consistent.** Under network partition, two nodes may disagree on boundary snap results until the partition heals. The system degrades to H¹ ≠ 0 warnings rather than crashes, but users must handle conflicts.

---

*"The snap doesn't tell you what's true. The snap tells you what you can ignore so you can think about what matters."* ⚒️
