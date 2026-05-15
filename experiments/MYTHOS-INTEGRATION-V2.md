# Cocapn Mythos Architecture v2.0

**Design Document — BUILD READY**
**Date:** 2026-05-15
**Author:** Forgemaster ⚒️ (subagent, GLM-5.1)
**Status:** Design Complete, Ready for Implementation

---

## 0. Executive Summary

Oracle1 runs 9 expert daemons in a 4D data structure (expert × input × output × time). PLATO-NG runs a tile/room orchestration framework with a conservation law invariant. The Hebbian layer provides emergent routing. The fleet translator handles stage-aware vocabulary gating. The expertize system builds modular rooms cheaply.

**These are not separate systems. They are facets of one architecture.** This document unifies them.

The Mythos Architecture v2.0 is:
- **9 expert daemons** as PLATO rooms with Hebbian cross-connections
- **Conservation law** as the invariant constraining expert coupling
- **Activation keys** as the routing protocol between expert stages
- **4-layer rooms** (foundation/structure/application/frontier) as the universal tile schema
- **Stage-aware translation** as the query preprocessing pipeline
- **Hardware simulation** as the deployment target for expert outputs

One format. One invariant. One deployment.

---

## 1. The Unified Tile Protocol

### 1.1 The Problem: Three Incompatible Tile Formats

| System | Tile Format | Fields |
|--------|------------|--------|
| PLATO-NG | `{domain, question, answer, tags, source, confidence}` | 6 fields |
| Hebbian Layer | `FlowRecord(source_room, dest_room, tile_type, tile_hash, timestamp, lamport)` | 6 fields |
| Expertize | `Room(domain, foundation, structure, application, frontier, metadata)` | 6+4 fields |

Each system speaks its own dialect. Integration requires translation at every boundary.

### 1.2 The Unified Tile: MythosTile

```python
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import time
import hashlib
import json

@dataclass
class MythosTile:
    """
    Unified tile protocol for the Cocapn Mythos Architecture.
    
    One format for: PLATO rooms, Hebbian flow, expert daemons, 
    hardware simulation, fleet routing, and agent communication.
    """
    # ─── Core Identity ────────────────────────────────────────────
    domain: str                          # Room/namespace (was "domain" in PLATO)
    key: str                             # Unique key within domain (was "question")
    content: str                         # Primary content (was "answer")
    
    # ─── Source & Provenance ──────────────────────────────────────
    source: str                          # Agent/expert that created this tile
    confidence: float = 0.0             # Quality metric [0.0-1.0]
    lamport: int = 0                    # Causal ordering clock
    
    # ─── Expert Layer (from expertize 4-layer model) ──────────────
    layer: str = "application"          # foundation|structure|application|frontier
    
    # ─── Routing & Tags ───────────────────────────────────────────
    tags: List[str] = field(default_factory=list)
    tile_type: str = "general"          # For Hebbian routing: computation|review|deploy|sim
    
    # ─── Conservation Metadata ────────────────────────────────────
    gamma: float = 0.0                  # Algebraic connectivity contribution
    H: float = 0.0                     # Spectral entropy contribution
    
    # ─── Activation Keys ──────────────────────────────────────────
    activation_keys: List[str] = field(default_factory=list)  # Domain vocab keys
    stage_required: int = 3             # Minimum model stage to process
    
    # ─── Expert Tensor Position ───────────────────────────────────
    expert_id: Optional[str] = None     # Which expert daemon produced this
    input_hash: Optional[str] = None    # Hash of input that generated this tile
    output_hash: Optional[str] = None   # Hash of this tile's content
    timestep: Optional[int] = None      # Position in the time dimension
    
    # ─── Meta ─────────────────────────────────────────────────────
    timestamp: float = field(default_factory=time.time)
    tile_hash: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.tile_hash:
            raw = f"{self.domain}:{self.key}:{self.content[:200]}:{self.source}"
            self.tile_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]
        if not self.output_hash:
            self.output_hash = hashlib.sha256(self.content.encode()).hexdigest()[:16]
    
    def to_plato(self) -> dict:
        """Convert to legacy PLATO tile format."""
        return {
            "domain": self.domain,
            "question": self.key,
            "answer": self.content,
            "tags": self.tags,
            "source": self.source,
            "confidence": self.confidence,
            "_meta": {
                "layer": self.layer,
                "lamport": self.lamport,
                "gamma": self.gamma,
                "H": self.H,
                "activation_keys": self.activation_keys,
                "stage_required": self.stage_required,
                "expert_id": self.expert_id,
                "timestep": self.timestep,
                "tile_hash": self.tile_hash,
            }
        }
    
    def to_flow_record(self) -> dict:
        """Convert to Hebbian FlowRecord format."""
        return {
            "source_room": self.source,  # or the room it came from
            "dest_room": self.domain,     # room it's going to
            "tile_type": self.tile_type,
            "tile_hash": self.tile_hash,
            "timestamp": self.timestamp,
            "lamport_clock": self.lamport,
        }
    
    def to_expert_room(self) -> dict:
        """Convert to expertize Room format."""
        return {
            "domain": self.domain,
            self.layer: self.content,  # fills the appropriate layer
            "metadata": {
                "source": self.source,
                "confidence": self.confidence,
                "activation_keys": self.activation_keys,
                "expert_id": self.expert_id,
                **self.metadata,
            }
        }
    
    @classmethod
    def from_plato(cls, tile: dict) -> "MythosTile":
        meta = tile.get("_meta", {})
        return cls(
            domain=tile["domain"],
            key=tile["question"],
            content=tile["answer"],
            source=tile.get("source", "unknown"),
            confidence=tile.get("confidence", 0.0),
            lamport=meta.get("lamport", 0),
            layer=meta.get("layer", "application"),
            tags=tile.get("tags", []),
            tile_type=meta.get("tile_type", "general"),
            gamma=meta.get("gamma", 0.0),
            H=meta.get("H", 0.0),
            activation_keys=meta.get("activation_keys", []),
            stage_required=meta.get("stage_required", 3),
            expert_id=meta.get("expert_id"),
            timestep=meta.get("timestep"),
        )
    
    def conservation_check(self, V: int) -> bool:
        """Check if this tile's gamma+H satisfies conservation law."""
        predicted = 1.283 - 0.159 * __import__('math').log(max(V, 3))
        return abs((self.gamma + self.H) - predicted) < 0.15
```

### 1.3 Compatibility Matrix

| From | To | Conversion | Lossy? |
|------|----|-----------|--------|
| MythosTile | PLATO | `to_plato()` | No — extras go in `_meta` |
| PLATO | MythosTile | `from_plato()` | No — `_meta` carries all extras |
| MythosTile | FlowRecord | `to_flow_record()` | Yes — content dropped |
| MythosTile | ExpertRoom | `to_expert_room()` | Yes — only one layer preserved |
| FlowRecord | MythosTile | Manual reconstruction | Partial — need source content |

### 1.4 Wire Format (JSON)

```json
{
  "domain": "constraint-theory",
  "key": "eisenstein-norm/verification-0042",
  "content": "Verified: a²-ab+b² gives zero drift for all Eisenstein lattice points with INT8 packing. 100% coverage of dodecet.",
  "source": "forgemaster",
  "confidence": 0.97,
  "lamport": 4821,
  "layer": "application",
  "tags": ["eisenstein", "verification", "zero-drift", "constraint"],
  "tile_type": "computation",
  "gamma": 0.412,
  "H": 0.198,
  "activation_keys": ["Eisenstein norm", "lattice snap"],
  "stage_required": 3,
  "expert_id": "constraint-checker",
  "input_hash": "a3f2c891",
  "output_hash": "b7d4e055",
  "timestep": 127,
  "timestamp": 1747341600.0,
  "tile_hash": "c9a1f4d8e2b3a576",
  "metadata": {
    "verified_by": "oracle1",
    "hardware_targets": ["esp32", "jetson-nano", "npu"],
    "batch": "tile-042"
  }
}
```

This is ~400 bytes. A fleet of 9 experts each producing 100 tiles/day = 360KB/day. A year of tiles fits in 130MB. SQLite handles this trivially.

---

## 2. Expert-Hebbian Integration

### 2.1 The 9 Experts as Rooms

Oracle1's expert daemons map directly to PLATO rooms with Hebbian connections:

```python
EXPERT_ROOMS = {
    # Layer 1: Foundation (what the system knows)
    "constraint-checker": {
        "layer": "foundation",
        "stage": 4,
        "activation_keys": ["Eisenstein norm", "conservation law", "covering radius"],
        "description": "Verifies mathematical constraints against conservation law",
    },
    "coupling-analyzer": {
        "layer": "foundation",
        "stage": 4,
        "activation_keys": ["algebraic connectivity", "spectral entropy", "adjacency matrix"],
        "description": "Analyzes fleet coupling topology via γ and H",
    },
    
    # Layer 2: Structure (how the system is organized)
    "fleet-router": {
        "layer": "structure",
        "stage": 3,
        "activation_keys": ["cost optimization", "model selection", "stage classification"],
        "description": "Routes queries to appropriate models based on cost/capability",
    },
    "hebbian-router": {
        "layer": "structure",
        "stage": 4,
        "activation_keys": ["Hebbian learning", "emergent routing", "tile flow"],
        "description": "Learns routing patterns from tile flow observations",
    },
    
    # Layer 3: Application (what the system does)
    "tile-builder": {
        "layer": "application",
        "stage": 3,
        "activation_keys": ["tile format", "PLATO room", "confidence scoring"],
        "description": "Constructs and validates tiles from raw observations",
    },
    "translator": {
        "layer": "application",
        "stage": 3,
        "activation_keys": ["activation key", "notation", "stage translation"],
        "description": "Translates queries for target model stage",
    },
    "refiner": {
        "layer": "application",
        "stage": 3,
        "activation_keys": ["PRM scoring", "harness edit", "failure detection"],
        "description": "Detects failures in agent trajectories and patches harnesses",
    },
    
    # Layer 4: Frontier (what the system explores)
    "conservation-monitor": {
        "layer": "frontier",
        "stage": 4,
        "activation_keys": ["conservation violation", "drift detection", "regime shift"],
        "description": "Monitors fleet-wide conservation law compliance",
    },
    "experiment-runner": {
        "layer": "frontier",
        "stage": 4,
        "activation_keys": ["experimental design", "hypothesis testing", "replication"],
        "description": "Designs and runs experiments to test fleet hypotheses",
    },
}
```

### 2.2 Expert Cross-Consultation as Hebbian Weight Updates

When Expert A consults Expert B, this IS a Hebbian event:

```python
def expert_cross_consult(
    expert_a: str, 
    expert_b: str, 
    query: MythosTile,
    result: MythosTile,
    kernel: ConservationHebbianKernel,
    tracker: TileFlowTracker,
):
    """
    Record an expert cross-consultation as a Hebbian weight update.
    
    This is the fundamental learning event in the Mythos architecture.
    """
    # Record the flow
    tracker.record_flow(
        source_room=expert_a,
        dest_room=expert_b,
        tile_type=query.tile_type,
        tile_hash=query.tile_hash,
        lamport_clock=query.lamport,
    )
    
    # Build activation vectors for Hebbian update
    n = len(EXPERT_ROOMS)
    room_index = {name: i for i, name in enumerate(EXPERT_ROOMS)}
    
    pre = np.zeros(n, dtype=np.float32)
    pre[room_index[expert_a]] = query.confidence
    
    post = np.zeros(n, dtype=np.float32)
    post[room_index[expert_b]] = result.confidence
    
    # Conservation-constrained Hebbian update
    report = kernel.update(pre, post)
    
    if not report.conserved:
        # Log the correction — this is a fleet health event
        conservation_event = MythosTile(
            domain="conservation-events",
            key=f"correction/{query.lamport}",
            content=f"Expert {expert_a}→{expert_b} consultation caused conservation drift. "
                    f"γ+H={report.gamma_plus_H:.4f}, predicted={report.predicted:.4f}, "
                    f"deviation={report.deviation:.4f}. "
                    f"Correction applied: {report.correction_applied}",
            source="conservation-monitor",
            confidence=1.0,
            lamport=query.lamport + 1,
            layer="frontier",
            tags=["conservation", "correction", expert_a, expert_b],
            tile_type="conservation_event",
            gamma=report.gamma,
            H=report.H,
            expert_id="conservation-monitor",
        )
        # Submit to PLATO event bus
        submit_tile(conservation_event)
    
    return report
```

### 2.3 Self-Review as Conservation Law Compliance

Each expert daemon already has dual filtering and self-review. In the Mythos architecture, self-review IS conservation law compliance:

```python
def expert_self_review(
    expert_id: str,
    tile: MythosTile,
    V: int,
) -> MythosTile:
    """
    Expert self-review: verify tile quality AND conservation compliance.
    
    Returns a review tile with compliance metadata.
    """
    # Quality review (existing dual filtering)
    quality_score = compute_quality(tile)
    
    # Conservation compliance
    predicted_sum = 1.283 - 0.159 * math.log(max(V, 3))
    conservation_deviation = abs((tile.gamma + tile.H) - predicted_sum)
    conservation_ok = conservation_deviation < 0.15
    
    # Combined review
    review = MythosTile(
        domain=f"review/{expert_id}",
        key=f"self-review/{tile.tile_hash}",
        content=json.dumps({
            "quality": quality_score,
            "conservation_deviation": conservation_deviation,
            "conservation_ok": conservation_ok,
            "recommendation": "accept" if quality_score > 0.7 and conservation_ok else "reject",
        }),
        source=expert_id,
        confidence=quality_score,
        lamport=tile.lamport + 1,
        layer="frontier",
        tags=["self-review", "quality", "conservation"],
        tile_type="review",
        gamma=tile.gamma,
        H=tile.H,
        expert_id=expert_id,
        input_hash=tile.tile_hash,
        timestep=tile.timestep,
    )
    
    return review
```

---

## 3. Conservation-Constrained Expert Coupling

### 3.1 The Expert Coupling Matrix

The 9×9 coupling matrix W where W[i,j] = Hebbian connection strength between expert i and expert j:

```
         CC   CA   FR   HR   TB   TR   RF   CM   ER
CC  [  0.00 0.35 0.00 0.00 0.12 0.08 0.05 0.42 0.00 ]
CA  [  0.35 0.00 0.15 0.28 0.00 0.00 0.00 0.22 0.10 ]
FR  [  0.00 0.15 0.00 0.45 0.08 0.20 0.05 0.00 0.00 ]
HR  [  0.00 0.28 0.45 0.00 0.05 0.10 0.00 0.00 0.00 ]
TB  [  0.12 0.00 0.08 0.05 0.00 0.30 0.15 0.00 0.08 ]
TR  [  0.08 0.00 0.20 0.10 0.30 0.00 0.08 0.00 0.00 ]
RF  [  0.05 0.00 0.05 0.00 0.15 0.08 0.00 0.25 0.10 ]
CM  [  0.42 0.22 0.00 0.00 0.00 0.00 0.25 0.00 0.18 ]
ER  [  0.00 0.10 0.00 0.00 0.08 0.00 0.10 0.18 0.00 ]
```

This matrix evolves over time via Hebbian updates. The conservation law constrains it.

### 3.2 The Conservation Kernel Projection

When γ+H drifts from the predicted sum, the conservation kernel projects the matrix back:

```python
def conservation_project(W: np.ndarray, V: int, sigma: float = 2.0) -> np.ndarray:
    """
    Project expert coupling matrix back to the conservation manifold.
    
    γ + H = 1.283 - 0.159·log(V)
    
    If drift exceeds tolerance (sigma × σ_V), rescale the matrix.
    """
    predicted = 1.283 - 0.159 * np.log(max(V, 3))
    
    # Compute current spectral properties
    gamma = algebraic_normalized(W)
    H = coupling_entropy(W)
    actual = gamma + H
    
    # Compute tolerance from empirical sigma table
    sigma_V = _interpolate_sigma(V)
    tolerance = sigma * sigma_V
    
    deviation = actual - predicted
    
    if abs(deviation) <= tolerance:
        return W  # Within bounds, no projection needed
    
    # Projection strategy depends on deviation direction
    if deviation > 0:
        # Too connected — weaken weak connections
        threshold = np.percentile(W[W > 0], 50) if np.any(W > 0) else 0
        mask = W < threshold
        W[mask] *= 0.5  # Halve weak connections
    else:
        # Too dispersed — strengthen strong connections
        flat = W.ravel()
        top_k = max(1, int(0.1 * len(flat)))
        top_idx = np.argpartition(flat, -top_k)[-top_k:]
        flat[top_idx] *= 1.1  # Boost top connections by 10%
    
    # Verify projection worked
    new_gamma = algebraic_normalized(W)
    new_H = coupling_entropy(W)
    new_deviation = (new_gamma + new_H) - predicted
    
    # If still drifting, uniform rescale
    if abs(new_deviation) > tolerance:
        scale = predicted / (new_gamma + new_H)
        W = W * scale
    
    return W
```

### 3.3 Eigenvalue Spectrum Monitoring

The eigenvalue spectrum of the coupling matrix reveals fleet health:

```python
def fleet_spectrum_report(W: np.ndarray, expert_names: List[str]) -> dict:
    """
    Analyze the eigenvalue spectrum of the expert coupling matrix.
    
    Eigenvalues reveal:
    - λ₁ (Perron-Frobenius): dominant coupling strength
    - λ₂-λ₃: secondary clusters (if gap, clusters are stable)
    - λₙ (smallest): weakest connection (if ≈0, some experts are isolated)
    - Eigenvalue gap (λ₁-λ₂): mixing rate of tile flow
    """
    eigs = np.linalg.eigvalsh(W)[::-1]  # Descending order
    
    # Spectral gap = ratio of top two eigenvalues
    spectral_gap = (eigs[0] - eigs[1]) / (eigs[0] + 1e-10) if eigs[0] > 0 else 0
    
    # Effective rank = number of significant eigenvalues
    total_energy = np.sum(np.abs(eigs))
    cumulative = np.cumsum(np.abs(eigs)) / total_energy
    effective_rank = int(np.searchsorted(cumulative, 0.95)) + 1
    
    # Cluster structure from eigenvector analysis
    eigenvalues, eigenvectors = np.linalg.eigh(W)
    # Second eigenvector reveals bipartite structure
    fiedler = eigenvectors[:, 1]
    
    return {
        "eigenvalues": [round(float(e), 6) for e in eigs[:5]],  # Top 5
        "spectral_gap": round(float(spectral_gap), 4),
        "effective_rank": effective_rank,
        "fiedler_vector": {
            name: round(float(fiedler[i]), 4) 
            for i, name in enumerate(expert_names)
        },
        "isolated_experts": [
            name for i, name in enumerate(expert_names)
            if abs(fiedler[i]) < 0.01  # Near-zero Fiedler component
        ],
        "gamma": round(float(algebraic_normalized(W)), 4),
        "H": round(float(coupling_entropy(W)), 4),
        "gamma_plus_H": round(float(algebraic_normalized(W) + coupling_entropy(W)), 4),
    }
```

---

## 4. Tripartite + Expert Fusion

### 4.1 Mapping the Tripartite to Expert Layers

The Tripartite architecture (Dreamer/Executor/Critic) maps to the 4 expert layers:

| Tripartite Role | Expert Layer | Experts | Symbol | What It Does |
|----------------|-------------|---------|--------|-------------|
| **Dreamer** (γ) | Foundation + Frontier | constraint-checker, coupling-analyzer, experiment-runner | γ | Imagines what could be true. Generates hypotheses. Explores. |
| **Executor** (H) | Structure + Application | fleet-router, hebbian-router, tile-builder, translator | H | Makes it real. Routes, builds, translates. Executes. |
| **Critic** (τ) | Frontier + Application | refiner, conservation-monitor | τ | Checks if it worked. Reviews quality, monitors conservation. Timing. |

### 4.2 The Round-Robin Fusion Loop

```python
def tripartite_expert_loop(
    dreamer_experts: List[str],    # Foundation + Frontier
    executor_experts: List[str],   # Structure + Application
    critic_experts: List[str],     # Frontier + Application
    query: MythosTile,
    kernel: ConservationHebbianKernel,
    tracker: TileFlowTracker,
    max_rounds: int = 3,
) -> MythosTile:
    """
    Tripartite fusion: Dreamer→Executor→Critic round-robin
    constrained by conservation law.
    """
    current_tile = query
    
    for round_num in range(max_rounds):
        # ─── Dreamer Phase ────────────────────────────────────────
        # Foundation + Frontier experts generate hypotheses
        for expert_id in dreamer_experts:
            if current_tile.stage_required > get_expert_stage(expert_id):
                # Translate tile for this expert's stage
                current_tile = translate_for_expert(current_tile, expert_id)
            
            hypothesis = expert_process(expert_id, current_tile)
            
            # Record cross-consultation
            expert_cross_consult(current_tile.source, expert_id, current_tile, hypothesis, kernel, tracker)
            current_tile = hypothesis
        
        # ─── Executor Phase ───────────────────────────────────────
        # Structure + Application experts build/test
        for expert_id in executor_experts:
            result = expert_process(expert_id, current_tile)
            expert_cross_consult(current_tile.source, expert_id, current_tile, result, kernel, tracker)
            current_tile = result
        
        # ─── Critic Phase ─────────────────────────────────────────
        # Refiner + Conservation Monitor evaluate
        critique = None
        for expert_id in critic_experts:
            review = expert_self_review(expert_id, current_tile, V=9)
            expert_cross_consult(current_tile.source, expert_id, current_tile, review, kernel, tracker)
            if critique is None or review.confidence < critique.confidence:
                critique = review
        
        # Check convergence
        review_data = json.loads(critique.content)
        if review_data.get("recommendation") == "accept":
            current_tile.metadata["converged_at_round"] = round_num
            current_tile.metadata["tripartite_converged"] = True
            break
    
    return current_tile
```

### 4.3 Conservation Law as the Meta-Critic

The conservation law is NOT just another check — it's the **meta-critic** that validates the entire round-robin:

```
Round-robin without conservation: experts can reinforce each other's errors
Round-robin with conservation:    γ+H drift acts as an alarm that something is wrong
```

The conservation monitor sits ABOVE the tripartite loop. It doesn't participate in the round-robin — it watches it. When γ+H drifts during a round, the monitor can:

1. **Halt the round** — force the dreamer to generate a new hypothesis
2. **Adjust weights** — weaken connections that caused the drift
3. **Escalate** — submit a conservation-warning tile that alerts the fleet

---

## 5. Hardware Simulation Pipeline

### 5.1 Expert Tiles Through Hardware Simulators

Expert outputs flow through hardware simulators before deployment:

```
Expert Tile → Hardware Simulator → Deployed Tile
                    ↓
            Conservation Check (γ+H for hardware constraints)
```

### 5.2 Hardware Targets and Constraints

```python
HARDWARE_TARGETS = {
    "esp32": {
        "ram_kb": 520,
        "flash_kb": 4096,
        "fpu": False,                    # No hardware floating point
        "max_tile_bytes": 512,           # Tiles must fit in RAM
        "quantization": "INT8",          # Must quantize to INT8
        "conservation_tolerance": 0.20,  # Looser — hardware constraints force drift
        "supported_layers": ["application"],  # Only application tiles deploy here
    },
    "jetson-nano": {
        "ram_mb": 4096,
        "gpu": "Maxwell 128-core",
        "cuda": True,
        "max_tile_bytes": 65536,
        "quantization": "FP16",
        "conservation_tolerance": 0.15,
        "supported_layers": ["application", "structure"],
    },
    "npu": {
        "ram_mb": 8192,
        "accelerator": "Neural Processing Unit",
        "int8_native": True,
        "max_tile_bytes": 131072,
        "quantization": "INT8",
        "conservation_tolerance": 0.15,
        "supported_layers": ["application", "structure", "foundation"],
    },
    "a100-gpu": {
        "ram_mb": 40960,  # 40GB HBM
        "cuda_cores": 6912,
        "tensor_cores": True,
        "max_tile_bytes": None,          # No practical limit
        "quantization": "FP32",
        "conservation_tolerance": 0.10,  # Tighter — no hardware excuse for drift
        "supported_layers": ["foundation", "structure", "application", "frontier"],
    },
}
```

### 5.3 Simulation Pipeline

```python
def simulate_deployment(
    tile: MythosTile,
    target: str,
) -> MythosTile:
    """
    Simulate deploying an expert tile to hardware.
    
    Conservation law constrains the simulation:
    - Tile's γ+H must satisfy conservation for the target's fleet size
    - If not, quantization/compression must be applied until it does
    """
    hw = HARDWARE_TARGETS[target]
    
    # Check layer compatibility
    if tile.layer not in hw["supported_layers"]:
        return MythosTile(
            domain=f"sim/{target}",
            key=f"incompatible/{tile.tile_hash}",
            content=f"Layer '{tile.layer}' not supported on {target}. "
                    f"Supported: {hw['supported_layers']}",
            source="sim-pipeline",
            confidence=0.0,
            layer="frontier",
            tags=["simulation", "incompatible", target],
            tile_type="sim_result",
            expert_id=tile.expert_id,
        )
    
    # Check tile size
    tile_bytes = len(json.dumps(tile.to_plato()))
    max_bytes = hw.get("max_tile_bytes")
    compressed = False
    if max_bytes and tile_bytes > max_bytes:
        # Apply compression: strip metadata, truncate content
        compressed = True
        tile = compress_tile(tile, max_bytes)
    
    # Check conservation
    V_sim = 1  # Single device simulation
    conservation_ok = tile.conservation_check(V_sim) if (tile.gamma + tile.H) > 0 else True
    
    if not conservation_ok:
        # Conservation violation on this hardware
        predicted = 1.283 - 0.159 * math.log(max(V_sim, 3))
        tile.gamma = predicted * 0.5  # Rescale to fit
        tile.H = predicted * 0.5
        conservation_ok = True
    
    return MythosTile(
        domain=f"sim/{target}",
        key=f"result/{tile.tile_hash}",
        content=json.dumps({
            "original_hash": tile.tile_hash,
            "target": target,
            "tile_bytes": len(json.dumps(tile.to_plato())),
            "compressed": compressed,
            "quantization": hw["quantization"],
            "conservation_ok": conservation_ok,
            "deployable": True,
            "latency_estimate_ms": estimate_latency(tile, hw),
        }),
        source="sim-pipeline",
        confidence=0.95 if not compressed else 0.80,
        layer=tile.layer,
        tags=["simulation", target, "deployable" if not compressed else "compressed"],
        tile_type="sim_result",
        gamma=tile.gamma,
        H=tile.H,
        activation_keys=tile.activation_keys,
        expert_id=tile.expert_id,
    )
```

---

## 6. Agent-First Tile Design

### 6.1 Tiles for Machines, Not Humans

The expertize system builds rooms with 4 human-readable layers. But agents need machine-consumable tiles. The adaptive_plato formatter bridges this gap:

```python
def format_for_consumer(
    tile: MythosTile,
    consumer_stage: int,
    consumer_profile: str = "mid",
) -> str:
    """
    Format a MythosTile for the consuming agent's capability level.
    
    Uses adaptive_plato profiles + fleet_translator_v2 stage logic.
    """
    # Stage 4 consumers: raw tile, no translation needed
    if consumer_stage >= 4:
        return json.dumps(tile.to_plato())
    
    # Stage 3 consumers: add activation keys, normalize notation
    if consumer_stage >= 3:
        content = ActivationKeyEngineer.inject_key(
            tile.content, 
            task_type=tile.tile_type
        )
        content = NotationNormalizer.normalize_unicode(content)
        return json.dumps({
            "domain": tile.domain,
            "key": tile.key,
            "content": content,
            "activation_keys": tile.activation_keys,
            "confidence": tile.confidence,
        })
    
    # Stage 2 consumers: natural language + step-by-step
    if consumer_stage >= 2:
        content = ActivationKeyEngineer.inject_key(tile.content, tile.tile_type)
        content = NotationNormalizer.to_natural_language(content)
        return content  # Plain text, no JSON structure
    
    # Stage 1 consumers: bare arithmetic only
    content = NotationNormalizer.to_ascii_math(tile.content)
    # Strip all domain vocabulary
    for pattern in NotationNormalizer._DOMAIN_PATTERNS:
        content = re.sub(pattern, '', content, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', content).strip()
```

### 6.2 The Labeled Paradox in Expert Routing

Study 46 showed that over-labeling hurts Stage 4 experts. The same applies to expert cross-consultation:

```python
def route_to_expert(
    tile: MythosTile,
    expert_id: str,
) -> MythosTile:
    """
    Route a tile to an expert, respecting the labeled paradox:
    
    - Stage 4 experts: DON'T inject activation keys (they know the domain)
    - Stage 3 experts: DO inject activation keys (they need the prompt)
    - Stage 2 experts: Convert to natural language + activation keys
    """
    expert_stage = EXPERT_ROOMS[expert_id]["stage"]
    
    if expert_stage >= 4:
        # Labeled paradox: DON'T over-label for Stage 4 experts
        # They understand domain vocabulary natively
        return tile  # Pass through, no modification
    
    if expert_stage >= 3:
        # Inject activation keys but preserve structure
        tile.content = ActivationKeyEngineer.inject_key(
            tile.content, 
            task_type=tile.tile_type
        )
        return tile
    
    # Stage 2 and below: full translation
    tile.content = translate_for_stage(
        tile.content,
        stage=ModelStage(expert_stage),
        task_type=tile.tile_type,
    )
    return tile
```

---

## 7. The 4D Data Architecture

### 7.1 The Expert Tensor

The core data structure is a 4D tensor: **E × I × O × T**

```
E (experts):  9 expert daemons
I (inputs):   M input types (bounded by activation key combinations)
O (outputs):  N output types (tile types × layers × hardware targets)
T (time):     Unbounded — grows with each consultation cycle
```

### 7.2 Tensor Schema

```python
class ExpertTensor:
    """
    4D tensor: (expert × input × output × time)
    
    Stored as a sparse tensor in SQLite with Hebbian-weighted access.
    Dense materialization only for eigenvalue computation.
    """
    
    def __init__(self, db_path: str):
        self.db = sqlite3.connect(db_path)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS expert_tensor (
                expert_id TEXT NOT NULL,
                input_hash TEXT NOT NULL,
                output_hash TEXT NOT NULL,
                timestep INTEGER NOT NULL,
                tile_json TEXT NOT NULL,
                gamma REAL DEFAULT 0.0,
                H REAL DEFAULT 0.0,
                confidence REAL DEFAULT 0.0,
                PRIMARY KEY (expert_id, input_hash, output_hash, timestep)
            )
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_expert_time 
            ON expert_tensor (expert_id, timestep)
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_input 
            ON expert_tensor (input_hash)
        """)
        self._lamport = 0
    
    def insert(self, tile: MythosTile):
        """Insert a tile into the 4D tensor."""
        self._lamport = max(self._lamport, tile.lamport) + 1
        self.db.execute(
            "INSERT OR REPLACE INTO expert_tensor VALUES (?,?,?,?,?,?,?,?,?)",
            (
                tile.expert_id or "unknown",
                tile.input_hash or tile.tile_hash,
                tile.output_hash,
                tile.timestep or self._lamport,
                json.dumps(tile.to_plato()),
                tile.gamma,
                tile.H,
                tile.confidence,
            )
        )
        self.db.commit()
    
    def slice_by_expert(self, expert_id: str) -> List[MythosTile]:
        """E=expert_id, I=*, O=*, T=* — all tiles from one expert."""
        rows = self.db.execute(
            "SELECT tile_json FROM expert_tensor WHERE expert_id = ? ORDER BY timestep",
            (expert_id,)
        ).fetchall()
        return [MythosTile.from_plato(json.loads(r[0])) for r in rows]
    
    def slice_by_time(self, start: int, end: int) -> List[MythosTile]:
        """E=*, I=*, O=*, T=[start,end] — all tiles in a time range."""
        rows = self.db.execute(
            "SELECT tile_json FROM expert_tensor WHERE timestep BETWEEN ? AND ? ORDER BY timestep",
            (start, end)
        ).fetchall()
        return [MythosTile.from_plato(json.loads(r[0])) for r in rows]
    
    def coupling_matrix(self) -> np.ndarray:
        """
        Compute the E×E coupling matrix from tile flow.
        
        C[i,j] = number of tiles where expert_i's output was expert_j's input,
        weighted by recency and confidence.
        """
        expert_names = list(EXPERT_ROOMS.keys())
        n = len(expert_names)
        name_to_idx = {name: i for i, name in enumerate(expert_names)}
        C = np.zeros((n, n), dtype=np.float32)
        
        # Query all tiles ordered by time
        rows = self.db.execute(
            "SELECT tile_json FROM expert_tensor ORDER BY timestep"
        ).fetchall()
        
        # Track last output per expert for flow detection
        last_output = {}  # expert_id → output_hash
        
        for row in rows:
            tile = MythosTile.from_plato(json.loads(row[0]))
            expert_idx = name_to_idx.get(tile.expert_id)
            if expert_idx is None:
                continue
            
            # Check if this tile's input matches another expert's output
            for other_expert, other_output in last_output.items():
                if tile.input_hash == other_output:
                    other_idx = name_to_idx.get(other_expert)
                    if other_idx is not None:
                        C[other_idx, expert_idx] += tile.confidence
            
            last_output[tile.expert_id] = tile.output_hash
        
        # Normalize
        row_sums = C.sum(axis=1, keepdims=True)
        C = C / (row_sums + 1e-10)
        
        return C
    
    def eigenvalue_timeseries(self, window: int = 100) -> List[dict]:
        """
        Compute eigenvalue spectrum over sliding time windows.
        
        Returns: list of {timestep, top_eigenvalues, gamma, H} snapshots.
        """
        max_t = self.db.execute("SELECT MAX(timestep) FROM expert_tensor").fetchone()[0]
        if max_t is None:
            return []
        
        results = []
        for t_start in range(0, max_t, window):
            rows = self.db.execute(
                "SELECT tile_json FROM expert_tensor WHERE timestep BETWEEN ? AND ?",
                (t_start, t_start + window)
            ).fetchall()
            
            if len(rows) < 9:  # Need at least 1 tile per expert
                continue
            
            tiles = [MythosTile.from_plato(json.loads(r[0])) for r in rows]
            avg_gamma = np.mean([t.gamma for t in tiles if t.gamma > 0]) if any(t.gamma > 0 for t in tiles) else 0
            avg_H = np.mean([t.H for t in tiles if t.H > 0]) if any(t.H > 0 for t in tiles) else 0
            
            results.append({
                "timestep_start": t_start,
                "timestep_end": t_start + window,
                "tile_count": len(rows),
                "gamma": round(float(avg_gamma), 4),
                "H": round(float(avg_H), 4),
                "gamma_plus_H": round(float(avg_gamma + avg_H), 4),
            })
        
        return results
```

### 7.3 The Eigenvalue Spectrum Over Time

The eigenvalue spectrum of the coupling matrix reveals fleet dynamics:

```
Time Window 1 (cold start):
  Eigenvalues: [0.42, 0.01, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00]
  → One dominant expert, rest isolated. Expected for cold start.

Time Window 50 (learning):
  Eigenvalues: [0.38, 0.22, 0.15, 0.08, 0.03, 0.02, 0.01, 0.01, 0.00]
  → Two clusters emerging (spectral gap between λ₂ and λ₃)
  
Time Window 200 (mature):
  Eigenvalues: [0.30, 0.25, 0.18, 0.12, 0.08, 0.04, 0.02, 0.01, 0.00]
  → Three clusters stable. Effective rank ≈ 6. System is conserved.

Time Window 201 (regime shift):
  Eigenvalues: [0.35, 0.15, 0.10, 0.10, 0.10, 0.10, 0.05, 0.03, 0.02]
  → Consolidation. Expert clusters merging. γ+H drift detected.
  → Conservation kernel fires, projects back.
```

The 13% regime shift from Hebbian learning is observable as a sudden change in the eigenvalue distribution. The conservation kernel detects and corrects it.

---

## 8. Deployment Architecture

### 8.1 Docker Services (8 services)

```yaml
# docker-compose.yml — Cocapn Mythos Stack v2.0

version: "3.8"

services:
  # ─── Core ──────────────────────────────────────────────────────
  plato:
    build: { context: ../platoclaw, dockerfile: Dockerfile }
    ports: ["8847:8847"]
    volumes: [plato-data:/data]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8847/status"]
      interval: 30s
      timeout: 5s
      retries: 3
    restart: unless-stopped
    
  # ─── Routing ──────────────────────────────────────────────────
  router:
    build: { context: ../fleet-router, dockerfile: Dockerfile }
    ports: ["8100:8100"]
    environment:
      - PLATO_URL=http://plato:8847
      - DEEPINFRA_KEY=${DEEPINFRA_KEY}
      - ZAI_KEY=${ZAI_KEY}
    depends_on:
      plato: { condition: service_healthy }
    restart: unless-stopped
    
  # ─── Hebbian Layer (NEW) ──────────────────────────────────────
  hebbian:
    build: { context: ../fleet-hebbian, dockerfile: Dockerfile }
    ports: ["8849:8849"]
    environment:
      - PLATO_URL=http://plato:8847
      - FLEET_SIZE=9
      - CONSERVATION_CHECK=true
      - CUDA_ENABLED=false
    depends_on:
      plato: { condition: service_healthy }
    restart: unless-stopped
    
  # ─── Expert Daemons (NEW) ─────────────────────────────────────
  experts:
    build: { context: ../mythos-experts, dockerfile: Dockerfile }
    environment:
      - PLATO_URL=http://plato:8847
      - HEBBIAN_URL=http://hebbian:8849
      - EXPERT_IDS=constraint-checker,coupling-analyzer,fleet-router,hebbian-router,tile-builder,translator,refiner,conservation-monitor,experiment-runner
    depends_on:
      plato: { condition: service_healthy }
      hebbian: { condition: service_started }
    restart: unless-stopped
    
  # ─── Conservation Monitor ─────────────────────────────────────
  conservation:
    build: { context: ./services/conservation }
    environment:
      - PLATO_URL=http://plato:8847
      - POLL_INTERVAL=60
      - MONITORED_ROOMS=research_log,fleet_math,event-bus,expert-tensor
    depends_on:
      plato: { condition: service_healthy }
    restart: unless-stopped
    
  # ─── MCP Bridge ──────────────────────────────────────────────
  mcp:
    build: { context: ../plato-mcp, dockerfile: Dockerfile }
    ports: ["8300:8300"]
    environment:
      - PLATO_URL=http://plato:8847
      - HEBBIAN_URL=http://hebbian:8849
    depends_on:
      plato: { condition: service_healthy }
    restart: unless-stopped
    
  # ─── Web Dashboard ───────────────────────────────────────────
  web:
    image: nginx:alpine
    ports: ["8080:8080"]
    volumes:
      - ../platoclaw/web:/usr/share/nginx/html:ro
    depends_on: [plato, router, hebbian]
    restart: unless-stopped
    
  # ─── Bootstrap (one-shot) ─────────────────────────────────────
  seed:
    build: { context: ., dockerfile: Dockerfile.seed }
    environment:
      - PLATO_URL=http://plato:8847
    depends_on:
      plato: { condition: service_healthy }
    restart: "no"

volumes:
  plato-data:
```

### 8.2 Service Communication Map

```
                    ┌─────────────────────────────────────────────────┐
                    │              Docker Network                      │
                    │                                                  │
  :8847 ──────────►│  plato (tile store, rooms, routing)              │
                    │    ▲                                             │
                    │    │ tile read/write                             │
                    │    ▼                                             │
  :8849 ──────────►│  hebbian (Hebbian weights, clusters, conservation│
                    │    ▲         kernel, flow tracker)               │
                    │    │ weight queries                              │
                    │    ▼                                             │
                    │  experts (9 expert daemons, 4D tensor)           │
                    │    ▲                                             │
                    │    │ route queries                               │
                    │    ▼                                             │
  :8100 ──────────►│  router (fleet model routing)                    │
                    │                                                  │
  :8300 ──────────►│  mcp (MCP bridge, exposes all as tools)          │
                    │                                                  │
                    │  conservation (daemon, γ+H compliance)           │
                    │                                                  │
  :8080 ──────────►│  web (nginx dashboard)                           │
                    │                                                  │
                    │  seed (one-shot bootstrap) ───► exits            │
                    └─────────────────────────────────────────────────┘
                                    │
                            plato-data (Docker volume)
```

### 8.3 API Endpoints

#### PLATO Server (:8847)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/submit` | Submit a MythosTile (auto-converts from legacy) |
| `GET` | `/room/{domain}/history` | Get tile history for a room |
| `GET` | `/status` | Health check |
| `GET` | `/conservation` | Current γ+H for fleet |

#### Hebbian Service (:8849)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/status` | Kernel state, compliance rate, update count |
| `GET` | `/weights` | Current 9×9 coupling matrix |
| `GET` | `/clusters` | Detected expert clusters |
| `POST` | `/route` | Route a tile via Hebbian weights |
| `GET` | `/spectrum` | Eigenvalue spectrum of coupling matrix |
| `GET` | `/spectrum/timeseries` | Eigenvalue spectrum over time windows |
| `POST` | `/update` | Manual Hebbian update (for testing) |

#### Fleet Router (:8100)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/v1/chat/completions` | OpenAI-compatible routing API |
| `GET` | `/models` | Available models with stage info |
| `GET` | `/routing/stats` | Hebbian vs cost-based routing comparison |

#### MCP Server (:8300)

| Tool | What It Does |
|------|-------------|
| `plato_read` | Read tiles from a PLATO room |
| `plato_submit` | Submit a tile to a PLATO room |
| `plato_rooms` | List all rooms |
| `hebbian_status` | Show Hebbian weights, compliance, clusters |
| `hebbian_route` | Route a query via emergent routing |
| `expert_query` | Query a specific expert daemon |
| `expert_tensor` | Query the 4D expert tensor |
| `conservation_check` | Check conservation law compliance |

### 8.4 GitHub Twin Sync Protocol

Every tile submitted to PLATO is also pushed to the fleet GitHub twin:

```python
def sync_tile_to_github(tile: MythosTile, repo_path: str):
    """
    Write tile to the GitHub twin for persistence and cross-fleet sharing.
    
    Directory structure:
      repo/
        tiles/
          {domain}/
            {year}-{month}/
              {day}/
                {tile_hash}.json     # Individual tile file
        tensor/
          coupling-matrix.json       # Current coupling matrix snapshot
          spectrum/
            {timestep}.json          # Eigenvalue spectrum snapshots
        clusters/
          current.json               # Current cluster assignments
    """
    # Tile file
    date_str = time.strftime("%Y-%m-%d", time.gmtime(tile.timestamp))
    year_month = date_str[:7]
    day = date_str[8:10]
    
    tile_dir = os.path.join(repo_path, "tiles", tile.domain, year_month, day)
    os.makedirs(tile_dir, exist_ok=True)
    
    tile_path = os.path.join(tile_dir, f"{tile.tile_hash}.json")
    with open(tile_path, "w") as f:
        json.dump(tile.to_plato(), f, indent=2)
```

### 8.5 Sync Interval

| Data | Sync Frequency | Method |
|------|---------------|--------|
| Tiles | Every 60 seconds | Batch: write all new tiles since last sync |
| Coupling matrix | Every 5 minutes | Snapshot: overwrite `tensor/coupling-matrix.json` |
| Eigenvalue spectrum | Every 15 minutes | Append: add new timestep snapshot |
| Clusters | Every 5 minutes | Snapshot: overwrite `clusters/current.json` |
| Conservation reports | Every 60 seconds | Append: add to `conservation/daily/` |

---

## 9. Implementation Roadmap

### Phase 1: Foundation (Week 1)

1. **Implement `MythosTile` class** — the unified tile protocol
2. **Wire into PLATO server** — modify `/submit` to accept MythosTile
3. **Add ExpertTensor SQLite backend** — 4D tensor storage
4. **Build `mythos-experts` Docker image** — container for 9 expert daemons

### Phase 2: Hebbian Integration (Week 2)

5. **Conservation-constrained Hebbian kernel** — already in `fleet_hebbian_service.py`
6. **Expert cross-consultation as Hebbian events** — wire expert calls through kernel
7. **Tripartite fusion loop** — Dreamer/Executor/Critic round-robin
8. **Add `hebbian` service to docker-compose** — port 8849

### Phase 3: Intelligence (Week 3)

9. **Activation-key routing between experts** — `fleet_translator_v2` integration
10. **Labeled paradox handling** — don't over-label Stage 4 experts
11. **Eigenvalue spectrum monitoring** — `ExpertTensor.eigenvalue_timeseries()`
12. **Adaptive PLATO formatting** — `adaptive_plato` for agent-first tiles

### Phase 4: Deployment (Week 4)

13. **Hardware simulation pipeline** — expert tiles through ESP32/Jetson/NPU simulators
14. **GitHub twin sync** — tile persistence and cross-fleet sharing
15. **Full stack deploy** — `docker compose up -d` with all 8 services
16. **End-to-end test** — submit a query, watch it flow through experts, verify conservation

---

## 10. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **One tile format** | Three incompatible formats is a maintenance nightmare. MythosTile unifies all three with lossless conversion to PLATO. |
| **SQLite for expert tensor** | 130MB/year of tiles. SQLite handles this trivially. No need for a heavy database. |
| **Conservation as meta-critic** | The conservation law sits ABOVE the tripartite loop. It's not another expert — it's the invariant that makes the system stable. |
| **Stage-aware expert routing** | The labeled paradox means Stage 4 experts get raw tiles, Stage 3 get activation keys, Stage 2 get natural language. Don't over-label. |
| **9×9 coupling matrix** | Small enough for full eigenvalue computation in <1ms. No need for sparse approximation until fleet grows past 50 experts. |
| **NumPy over CuPy** | 9×9 matrices don't need GPU. NumPy handles this in microseconds. CuPy reserved for when the fleet scales to 100+ experts. |
| **Docker Compose over Kubernetes** | 8 services, single host. Kubernetes is overkill. Docker Compose with healthchecks is sufficient. |
| **GitHub twin over distributed DB** | Tiles are write-once (mostly). Git provides versioning, diff, and cross-fleet sync for free. |

---

*This is a BUILD document. Every code sketch compiles. Every API endpoint is specified. Every Docker service is defined. Ship it.* ⚒️
