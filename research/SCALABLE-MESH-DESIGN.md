# Scalable Mesh Design: 10 Clunky Fixes to SnapKit v2

**Forgemaster ⚒️ | 2026-05-11 | v1 → v2 Architecture Gap Analysis**

---

## Overview

SnapKit v1 works but it's _clunky_. Every clunkiness reduces to one root cause: **the v1 codebase treats the snap function as a single scalar operation on flat data**. Real attention allocation needs tensors, hierarchies, topologies, and distributed consistency. These 10 fixes compose into a mesh that scales.

---

## Fix 1: Scalar Tolerance → Tensor Tolerance

### What's Clunky

```python
snap = SnapFunction(tolerance=0.1, topology=HEXAGONAL)
```

One float for everything. The same tolerance applies in every lattice direction, every stream, every channel. A tolerance of `0.1` along `a`-axis is also `0.1` along `bω`-axis, even though the lattice has 60° rhombus geometry where distances are anisotropic relative to the basis.

### The Math Fix

Replace scalar `t ∈ ℝ⁺` with a **positive-definite tensor `T ∈ Sym⁺₂(ℤ[ω])`**, represented as a 2×2 Gram matrix in the Eisenstein basis:

```
T = [ t₁₁  t₁₂ ]
    [ t₂₁  t₂₂ ]
```

where `t₁₁ > 0`, `t₂₂ > 0`, and `det(T) > 0`. The condition `N(u,v) ≤ T(u,v)` becomes:

```
u² - uv + v² ≤ t₁₁·u² + 2·t₁₂·uv + t₂₂·v²
```

For a lattice with 6-fold symmetry, `T` must respect the dihedral group D₆: the only tensors that are D₆-invariant are scalar multiples of the identity. But we don't want full invariance — **we want directional tuning**.

**The fix:** Parameterize tolerance by stream type × lattice direction:

```python
T = {              # Tolerance tensor per stream
    'safety':    [[0.01, 0.00], [0.00, 0.01]],   # isotropic, tight
    'timing':    [[0.10, 0.05], [0.05, 0.10]],   # coupled
    'resources': [[0.05, 0.00], [0.00, 0.20]],   # anisotropic: b-axis looser
}
```

A stream like `resources` tolerates more drift in the imaginary (resource-level) direction than in the real (resource-type) direction.

### API

```python
class TensorTolerance:
    """Tolerance as a positive-definite Gram matrix."""
    
    def __init__(self, matrix: np.ndarray):
        assert np.all(np.linalg.eigvalsh(matrix) > 0), "Must be PD"
        self._T = matrix
    
    def within(self, u: float, v: float) -> bool:
        """Check if lattice vector (u,v) is within tensor tolerance."""
        uv = np.array([u, v])
        return uv @ self._T @ uv <= 1.0  # ellipsoid constraint
    
    def scale(self, factor: float):
        self._T *= factor
```

### Why It Scales

- Tensor tolerance generalizes scalar: scalar is `T = t · I`.
- Directional tuning per stream means **streams don't compete for tolerance budget** the way they do with a shared scalar.
- Tensor adapts to lattice geometry automatically: the Eisenstein norm `N(u,v) = u²−uv+v²` defines the natural metric, and `T` is a deformation of that metric.

---

## Fix 2: Single-Scale Snap → Multi-Scale Snap

### What's Clunky

```python
snap = SnapFunction(tolerance=0.1)
snap.observe(value)  # one tolerance, one result
```

Everything snaps at one resolution. Nanosecond-scale jitter competes with minute-scale trends for the same snap gate.

### The Math Fix

Snap simultaneously at K geometrically-spaced tolerance scales:

```
t_k = t₀ · rᵏ    for k = 0, 1, ..., K-1
```

where `t₀` is base tolerance and `r > 1` sets scale spacing (e.g., `r = 10` for order-of-magnitude spacing).

For the Eisenstein lattice, each scale k defines an **arithmetic progression of lattice snap points**: `Sₖ(z) = nearest lattice point at scale tₖ`.

The **freed cognition** at scale k is:

```
Fₖ(z) = N(z − Sₖ(z))  (how much was snapped away)
```

**Higher scales = more freed cognition.** A value that triggers delta at scale 0 (tight) but snaps at scale 3 (loose) has structure at intermediate scales — it's not noise, it's a pattern emerging.

### API

```python
class MultiScaleSnap:
    """Snap at geometrically spaced tolerances simultaneously."""
    
    def __init__(self, base_tolerance: float = 0.001, scales: int = 4, ratio: float = 10.0):
        self._scales = [base_tolerance * (ratio ** k) for k in range(scales)]
        self._snap = SnapFunction()  # single topology, multiple passes
    
    def observe(self, value: complex) -> MultiScaleResult:
        """Snap at all scales. Returns a profile, not a single result."""
        results = [self._snap(value, tolerance=t) for t in self._scales]
        # Freed cognition per scale
        freed = [N(value - r.snapped) for r in results]
        return MultiScaleResult(
            scale_results=results,
            freed_cognition=freed,
            # Which scales snapped, which delta'd
            snap_mask=[r.within_tolerance for r in results],
        )
```

### Why It Scales

- Nanosecond tolerance catches micro-fluctuations; minute tolerance catches trends.
- The freed cognition profile tells you **what the system can safely ignore at each temporal layer**.
- Multi-scale composition is the same math as wavelet decomposition — scale-space theory transfers directly.

---

## Fix 3: Flat Attention → Hierarchical Attention

### What's Clunky

```python
snap.observe(value)  # no concept of attention budget
```

The v1 snap treats all deltas equally. But a system has finite cognition — it can't attend to everything. Deltas must compete.

### The Math Fix

Allocate attention as proportions of a total budget `A = 1.0`:

| Pool | Share | Role |
|------|-------|------|
| **Safety** | 30% | Non-negotiable reserve |
| **Operational** | 50% | Active problem-solving |
| **Exploration** | 20% | Novelty-seeking, learning |

Each pool has:
- A **reserve** (unallocated within pool) — the safety pool has a minimum unallocated amount `r_s = 0.10 · A` that can't be touched.
- An **allocation function** `a(c, s, p)` — how much attention delta `d` at channel `c` and severity `s` gets from pool `p`.
- A **budget ceiling** — no single delta can consume more than `m_p` of pool `p`.

The snap now returns an **attention-weighted delta**:

```python
def snap_with_attention(self, value, channel: str) -> AttendedSnap:
    result = self.snap(value)
    if result.is_delta:
        pool = self._channel_pool(channel)  # map channel to pool
        attention = self._allocate(pool, result.delta, channel)
    else:
        attention = 0.0
    return AttendedSnap(result=result, attention_allocated=attention)
```

### API

```python
class AttentionBudget:
    def __init__(self, total: float = 1.0):
        self._pools = {
            'safety':     Pool(share=0.30, reserve=0.10),
            'operational': Pool(share=0.50, reserve=0.05),
            'exploration': Pool(share=0.20, reserve=0.02),
        }
    
    def allocate(self, channel: str, delta_magnitude: float, source: str) -> float:
        """Return allocated attention, tracking budget consumption."""
        pool = self._pool_for(channel)
        return pool.consume(min(delta_magnitude, pool.ceiling))
```

### Why It Scales

- The safety pool is the "fire alarm" — it doesn't compete with operational budget. A safety-critical delta always gets attention because the reserve guarantees minimum allocation.
- Exploration pool enables learning without starving operations.
- Budget ceilings prevent one loud delta from consuming all cognition.

---

## Fix 4: Cosine Script Matching → Lattice-Aware Matching

### What's Clunky

```python
# Current approach: cosine similarity on embedded vectors
similarity = cosine(query_embedding, script_embedding)
```

Cosine similarity treats the embedding space as isotropic and orthogonal. But if scripts live on a lattice (which they should — the ADE topology defines the natural geometry), cosine similarity is geometrically wrong.

### The Math Fix

Replace cosine similarity with **Eisenstein distance** between lattice points:

```
d_lattice(s₁, s₂) = N(α₁ − α₂, β₁ − β₂) = (α₁−α₂)² − (α₁−α₂)(β₁−β₂) + (β₁−β₂)²
```

where `(αⱼ, βⱼ)` are the Eisenstein integer coordinates of script `j`'s snap point.

The Eisenstein distance:
- Respects the hexagonal lattice geometry (60° basis)
- Is positive-definite (it's a norm)
- Satisfies triangle inequality
- Is invariant under the D₆ symmetry of the lattice

For cross-topology matching (e.g., matching an A₂-snapped query to an A₃-snapped script), use the **minimal embedding distance**:

```
d_cross(τ₁, τ₂) = min_{φ ∈ Hom(τ₁, τ₂)} d₂(φ(z₁), z₂)
```

where `Hom(τ₁, τ₂)` is the set of lattice homomorphisms embedding topology τ₁ into τ₂'s ambient space. For A₂ → A₃, this is the inclusion of the hexagonal plane into 3D.

### API

```python
def lattice_distance(p1: np.ndarray, p2: np.ndarray, topology: SnapTopologyType) -> float:
    """Distance in the natural lattice metric, not Euclidean."""
    if topology == HEXAGONAL:
        # Eisenstein distance
        da, db = p1[0] - p2[0], p1[1] - p2[1]
        return da*da - da*db + db*db
    elif topology == CUBIC:
        return np.sum((p1 - p2)**2)
    # ... per-topology distance functions
```

### Why It Scales

- Lattice distance is the **natural** metric of the snap topology — it measures what the snap function actually cares about.
- Cosine similarity assumes a spherical geometry that doesn't match any ADE lattice. Using it is geometrically inconsistent.
- Cross-topology matching via minimal embedding gives a principled way to match scripts learned on different topologies.

---

## Fix 5: Topology-Blind Learning → Topology-Tagged Scripts

### What's Clunky

```python
# Current: scripts are just sequences — no topology metadata
class Script:
    def __init__(self, sequence: List[Move]):
        self.sequence = sequence
```

A script learned on the Eisenstein lattice is applied as-is to cubic lattice data. The geometry is wrong.

### The Math Fix

Every script carries its **SnapTopology signature**:

```python
@dataclass
class TopologyTag:
    """Metadata about the topology a script was learned on."""
    ade_type: ADEType
    rank: int
    coxeter_number: int
    # The lattice metric used during learning
    metric: str  # 'eisenstein', 'euclidean', 'manhattan', etc.
    # Calibration: the tolerance settings when this script was built
    calibration: Dict[str, float]
```

When matching a script to current context:

1. **Same topology → direct match** using lattice distance
2. **Different topology → check isometry** — if the script's topology embeds isometrically into current topology (e.g., A₂ ⊂ A₃ as a maximal subgroup), transform the script
3. **No isometry → check cohomology obstruction** — the H¹ obstruction in `H¹(X, ℤ)` between the two topologies determines if approximate matching is possible

### API

```python
class TopologyTaggedScript:
    def __init__(self, sequence, topology: SnapTopologyType, tolerance_tensor: np.ndarray):
        self.sequence = sequence
        self.topology_tag = TopologyTag(
            ade_type=ade_for(topology),
            topology_type=topology,
            tolerance_tensor=tolerance_tensor,
        )
    
    def matches(self, context_topology: SnapTopologyType) -> bool:
        """Check if this script can be safely applied in the current topology."""
        return isometric_embedding(self.topology_tag.topology_type, context_topology)
```

### Why It Scales

- Topology tags let the system **reject false matches** — a script built for D₄ triality doesn't get applied to A₁ binary data.
- The lattice metric ensures that "close" in topology space means "close in behavior."
- Isometry checking prevents geometric misapplication without requiring full recomputation.

---

## Fix 6: One Topology Everywhere → LatticeMesh

### What's Clunky

```python
# Current: global topology, global tolerance
snap = SnapFunction(tolerance=0.1, topology=HEXAGONAL)
```

The same lattice everywhere. But different regions of state-space have different geometric requirements. Safety-critical regions need A₁ (binary): "is this safe or not?". Creative regions need E₈: "rich combinatorial structure with maximum symmetry."

### The Math Fix: LatticeMesh

Partition state-space into regions `R₁, R₂, ..., Rₙ`, each with its own ADE topology `τᵢ`. The regions are glued together via **sheaf cohomology**:

- Each region boundary `∂Rᵢⱼ = Rᵢ ∩ Rⱼ` is a transition zone
- On the boundary, both topologies are valid snap functions
- The **gluing condition** is `H¹(∂Rᵢⱼ, ℤ) = 0` — no obstruction to composing snaps across the boundary

This means: snapping a point on the boundary using either topology gives the same delta classification (snap/delta is consistent).

### API

```python
class LatticeMesh:
    """State-space partitioned by ADE topology."""
    
    def __init__(self):
        self._regions: Dict[str, MeshRegion] = {}
        self._boundaries: List[MeshBoundary] = []
    
    def add_region(self, name: str, topology: SnapTopologyType, 
                   bounds: Callable[[np.ndarray], bool], 
                   tolerance: TensorTolerance):
        """Add a region with its topology and tolerance."""
        self._regions[name] = MeshRegion(topology, bounds, tolerance)
    
    def snap(self, point: np.ndarray) -> RegionSnapResult:
        """Snap point using the correct region's topology."""
        region = self._region_for(point)
        if region is None:
            # Boundary zone — snap with both topologies, verify consistency
            return self._boundary_snap(point)
        return region.snap(point)
    
    def verify_h1_zero(self) -> bool:
        """Verify all boundaries have H¹=0 (no gluing obstructions)."""
        for b in self._boundaries:
            if self._h1_obstruction(b) != 0:
                return False
        return True
```

### Why It Scales

- **Efficient by design:** deep-reasoning regions (E₈) are local — they don't force the whole mesh to be high-dimensional.
- **Sheaf consistency:** `H¹=0` at boundaries means distributed computation works. A point's snap classification is path-independent.
- **Region specialization:** safety regions use A₁ (cheap, binary), creative regions use E₈ (expensive, rich) — the right topology for each job.

---

## Fix 7: Linear Pipeline → DAG Pipeline

### What's Clunky

```python
# Current: sequential processing chain
value → snap.channel1 → snap.channel2 → ... → decision
```

Linear pipelines hide feedback loops. They can't branch on condition, can't learn from output effects, can't pause for attention allocation.

### The Math Fix: DAG Pipeline

Model the pipeline as a **directed acyclic graph** `G = (V, E)` where:
- **Vertices** `v ∈ V` are processing nodes (snap, transform, learn, decide)
- **Edges** `e ∈ E` are data flows (streams of deltas)
- **Conditional edges** carry a predicate `p_e`: data flows only if predicate is true
- **Feedback edges** are allowed in the LEARN phase but removed in the EXECUTE phase (to prevent cycles during inference)

Each node has:
- **Inputs:** one or more delta streams
- **State:** the node's snap function, possibly with accumulated holonomy
- **Outputs:** processed delta stream(s)

### Pipeline Types

```python
class PipelineNode:
    INPUT → SNAP         # Snap incoming data
    SNAP → MATCH         # Match delta to known scripts
    MATCH → BRANCH       # Conditional: known script → execute, unknown → learn
    BRANCH → EXECUTE     # Run the matched script
    BRANCH → LEARN       # Build new script from delta pattern
    MATCH → TRANSFORM    # Transform data for cross-topology matching
    EXECUTE → SNAP       # Feedback: execution results feed back into snap
    LEARN → UPDATE       # Update snap function with learned tolerance
    TRANSFORM → MATCH    # Transformed data goes to matching
    SNAP → ALLOCATE      # Send delta to attention budget allocator
    ALLOCATE → BRANCH    # Only if attention is available
```

### Why It Scales

- DAGs compose naturally across distributed nodes (see Fix 10).
- Conditional edges prevent unnecessary computation — if a delta isn't interesting, it doesn't propagate.
- Feedback from EXECUTE to SNAP enables **closing the loop**: the system sees the results of its own actions.
- No cycles in inference mode → bounded latency.

---

## Fix 8: Single Output Format → Multi-Resolution Output

### What's Clunky

```python
# Current: one SnapResult per observation
result = snap.observe(value)
print(result)  # S(0.05 → 0.0, δ=0.05, SNAP)
```

One result, one resolution. But different consumers need different fidelity:
- An embedded sensor needs the minimum viable delta
- An analytics dashboard needs full statistics
- Research mode needs the complete cohomological trace

### The Math Fix

Define 4 output resolutions with progressively more data:

| Level | Name | Contents | Cost |
|-------|------|----------|------|
| **MINIMAL** | Embedded | `(snapped_coords, is_delta)` | 1 float + 1 bit |
| **STANDARD** | Application | `(original, snapped, delta, within_tolerance)` | 3 floats + 1 bool |
| **FULL** | Analytics | `(history, statistics, tolerance_state)` | Full state |
| **RESEARCH** | Trace | `(lattice point, fractional parts, boundary conditions, holonomy, cohomology map)` | Full cohomology |

Each consumer subscribes to the level they need. The snap function computes once, broadcasts to all subscribers at their requested resolution.

### API

```python
@dataclass
class SnapOutput:
    """Multi-resolution snap output."""
    
    # Always available
    snapped: complex       # Lattice point
    is_delta: bool         # Whether this exceeded tolerance
    
    # STANDARD level
    original: Optional[complex] = None
    delta: Optional[float] = None
    
    # FULL level
    history: Optional[List[SnapResult]] = None
    statistics: Optional[Dict[str, float]] = None
    
    # RESEARCH level
    boundary_conditions: Optional[Dict[str, bool]] = None
    holonomy: Optional[float] = None
    cohomology_map: Optional[Dict[str, Any]] = None
```

### Why It Scales

- Embedded devices don't carry full state — MINIMAL is a single float and a bit.
- Research mode is expensive but only turned on when debugging or training.
- The output resolution is not computed speculatively; it's populated lazily as subscribers request it.

---

## Fix 9: 9 Arbitrary Channels → Math-Derived Channels

### What's Clunky

```python
# Current: 9 channels chosen by intuition
CHANNELS = ['safety', 'timing', 'resources', 'knowledge', 'social',
            'deep_structure', 'instrument', 'paradigm', 'urgency']
```

These 9 channels came from Casey's phenomenological model. They work, but they're not derived from first principles. There could be 7, or 11, or 42.

### The Math Fix

Channel count = **rank of the ADE root system** used for the system's primary topology.

```
A₂  →  2 channels   (binary pair)
A₃  →  3 channels   (triple)
D₄  →  4 channels   (quadruple)
E₆  →  6 channels
E₇  →  7 channels
E₈  →  8 channels
```

For a multi-topology LatticeMesh (Fix 6), the total channel count is the sum of ranks across active regions, but attention is allocated per the hierarchical pool model (Fix 3).

For example, a LatticeMesh with regions [A₂ (safety), A₃ (operational), E₈ (exploration)] has:

```
n_channels = 2 + 3 + 8 = 13
```

**But wait — the original model has 9 channels.** Where does 9 come from?

9 = 2(A₂) + 3(A₃) + 4(D₄) — the channels decompose across three active topologies:

| Channel | Topology | Basis |
|---------|----------|-------|
| Safety, Timing | A₂ (rank 2) | Eisenstein lattice directions |
| Resources, Knowledge, Social | A₃ (rank 3) | Tetrahedron vertices |
| Deep structure, Instrument, Paradigm, Urgency | D₄ (rank 4) | Triality symmetry |

So 9 isn't arbitrary — it's the **sum of ranks** of a composite topology A₂ ⊕ A₃ ⊕ D₄. But it should be **derived from the lattice configuration**, not hardcoded.

### API

```python
class ChannelGrid:
    """Channels derived from active topologies."""
    
    def __init__(self, lattice_mesh: LatticeMesh):
        # Channel count = sum of ranks of active regions
        self._channels = []
        for name, region in lattice_mesh.regions().items():
            rank = region.topology.rank
            for r in range(rank):
                self._channels.append(Channel(
                    name=f"{name}_{r}",
                    topology=region.topology,
                    basis_direction=r,
                ))
    
    @property
    def count(self) -> int:
        return len(self._channels)
```

### Why It Scales

- **No magic numbers.** If the lattice mesh changes, channels change automatically.
- Each channel has a well-defined geometric meaning: it's a direction in the ADE root space.
- Channel interaction is determined by the ADE Dynkin diagram, not intuition.

---

## Fix 10: No Distributed Snap → Distributed with H¹ Boundary Consistency

### What's Clunky

```python
# Current: single-process snap
snap.observe(value)
```

No distribution. Not even threaded. If the system runs across a GPU cluster, each node makes independent snap decisions that may conflict at partition boundaries.

### The Math Fix

Snap on a distributed LatticeMesh where each node handles a region `Rᵢ`. The partition boundaries are **sheaf gluing interfaces**:

1. Each node owns its region and the boundaries with neighbors
2. A point on boundary `∂Rᵢⱼ` is snapped by **both** nodes independently
3. The results must satisfy `H¹(∂, ℤ) = 0` — the cohomology obstruction at the boundary is zero

This means:
- Snapping the same point from either side gives the same delta classification
- The gluing is **consistent**: path from A to B through R₁ matches path through R₂

**Implementation:**

```
┌──────────┐     gluing interface     ┌──────────┐
│ Node A   │ ◄──────────────────────► │ Node B   │
│ R₁: A₂   │    H¹(∂R₁₂, ℤ) = 0      │ R₂: D₄   │
│ channels:│                          │ channels:│
│ [0..1]   │                          │ [2..5]   │
└──────────┘                          └──────────┘
```

When a crossing delta occurs (an event that starts in R₁ and propagates into R₂):
1. Node A snaps it → sends snapped classification + delta to Node B
2. Node B snaps independently → compares at boundary
3. If classification matches → boundary is consistent (H¹ = 0)
4. If classification differs → boundary obstruction found (H¹ ≠ 0) → record and resolve via consensus

### Consensus Protocol

```python
class DistributedSnap:
    """Distributed snap with boundary consistency verification."""
    
    def __init__(self, node_id: str, neighbors: List[str], 
                 lattice_mesh: LatticeMesh):
        self.node_id = node_id
        self.neighbors = neighbors
        self.mesh = lattice_mesh
        self._boundary_cache = {}  # (neighbor_id, point_hash) → classification
    
    def snap(self, point: np.ndarray, source: str) -> SnapResult:
        result = self.mesh.snap(point)
        
        # If near boundary, broadcast to neighbors for verification
        if self._near_boundary(point):
            for neighbor_id in self.neighbors:
                if neighbor_id != source:
                    self._broadcast(point, result, neighbor_id)
        
        return result
    
    def receive_broadcast(self, point: np.ndarray, 
                          neighbor_result: SnapResult,
                          neighbor_id: str) -> BoundaryCheck:
        """Check consistency with neighbor's snap."""
        local_result = self.mesh.snap(point)
        
        consistent = (local_result.within_tolerance == 
                     neighbor_result.within_tolerance)
        
        return BoundaryCheck(
            point=point,
            neighbor=neighbor_id,
            consistent=consistent,
            local_delta=local_result.delta,
            neighbor_delta=neighbor_result.delta,
        )
```

### Why It Scales

- H¹ consistency is **checkable at runtime**: if obstructions appear, the system knows its partition is wrong.
- The broadcast is sparsely activated — only near boundaries.
- Consensus resolves conflicts without centralized coordination.
- Scales to any number of nodes: each node only talks to its topological neighbors.

---

## Composition: How All 10 Fixes Mesh

```
┌─────────────────────────────────────────────────────────────────┐
│                      Distributed SnapKit v2                      │
│                                                                  │
│  Fix 10: Distributed LatticeMesh                                │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Node A (A₂ region)          Node B (D₄ region)         │    │
│  │  ┌─────────────────┐         ┌─────────────────┐        │    │
│  │  │ Fix 1: Tensor    │  gluing │ Fix 1: Tensor    │        │    │
│  │  │ Tolerance        │◄──────►│ Tolerance        │        │    │
│  │  │                  │  H¹=0  │                  │        │    │
│  │  │ Fix 2: Multi-    │         │ Fix 2: Multi-    │        │    │
│  │  │ Scale Snap       │         │ Scale Snap       │        │    │
│  │  │                  │         │                  │        │    │
│  │  │ Fix 3: Attention │         │ Fix 3: Attention │        │    │
│  │  │ Budget           │         │ Budget           │        │    │
│  │  └────────┬─────────┘         └────────┬─────────┘        │    │
│  │           │                   │                           │    │
│  └───────────┼───────────────────┼───────────────────────────┘    │
│              │                   │                                │
│  Fix 8: Multi-Resolution Output + Fix 9: Math-Derived Channels   │
│              │                   │                                │
│              ▼                   ▼                                │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Fix 6: LatticeMesh (global orchestration)               │    │
│  │  Fix 4: Lattice-Aware Matching (scripts crossed w/        │    │
│  │          Eisenstein distance)                             │    │
│  │  Fix 5: Topology-Tagged Scripts (prevent misapplication)  │    │
│  │  Fix 7: DAG Pipeline (branch, feedback, conditional)      │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Summary: v1 → v2 Migration Map

| Fix | v1 | v2 | Math |
|-----|----|----|------|
| 1 | `tolerance: float` | `T: Sym⁺₂(ℤ[ω])` | Positive-definite tensor |
| 2 | One scale | K geometric scales | Scale-space theory |
| 3 | Flat attention | 3-pool budget | Constrained optimization |
| 4 | Cosine similarity | Eisenstein distance | Lattice norm |
| 5 | Untagged scripts | Topology-tagged | ADE classification |
| 6 | One topology | LatticeMesh | Sheaf cohomology |
| 7 | Linear pipeline | DAG pipeline | Directed graphs |
| 8 | Single output | 4-resolution | Lazy evaluation |
| 9 | 9 arbitrary channels | Σ rank(topologies) | ADE rank theory |
| 10 | Single process | Distributed | H¹ boundary consistency |

**The v2 scaling regime:** v1 is O(1) per observation — constant time regardless of scale. v2 is O(N × K × R) where N = nodes, K = scales, R = regions, but each factor is independently tunable and the boundary consistency check (Fix 10) ensures the mesh behaves correctly regardless of how many nodes you add.

---

*"The snap is the handoff. The script is the offload. The freed mind is the intelligence."* ⚒️
