"""core — PLATO-Native Agent Infrastructure

The deep connective layer. Every future Cocapn fleet agent stands on this.

Modules:
    pinna           — The Pinna Transform: fixed geometry provenance encoding
    tile_lifecycle  — Tile CRUD with mortality and disproof-only admission
    ender_protocol  — Simulation-first alignment through progressive abstraction
    swarm_router    — Topology-aware task routing and division of labor
    plato_retriever — Cold-start bootstrap and pinna-aware retrieval

Evidence: UNIFIED-FRAMEWORK.md (all 11 sections)
"""
# ── pinna.py ──────────────────────────────────────────────────────────────────
from .pinna import (
    AgentStage,
    ResidueClass,
    ScaffoldLevel,
    PinnaField,
    PinnaEncoder,
    PinnaReader,
    PinnaCalibrator,
    ConservationResult,
    check_conservation_law,
    ConservationLawChecker,       # legacy dict-based interface
)

# ── tile_lifecycle.py ─────────────────────────────────────────────────────────
from .tile_lifecycle import (
    Tile,
    TileStore,
    DisproofOnlyGate,
    MortalitySweep,
    TileCancerDetector,
)

# ── ender_protocol.py ─────────────────────────────────────────────────────────
from .ender_protocol import (
    CapabilityProfile,
    ContaminationSensor,
    Level0BoundaryMapping,
    Level1SelfScaffolding,
    Level2Composition,
    Level3Orchestration,
    GraduationMarkers,
)

# ── swarm_router.py ───────────────────────────────────────────────────────────
from .swarm_router import (
    Topology,
    TOPOLOGY_REGISTRY,
    ROUTING_TABLE,
    TaskDescriptor,
    classify_task,
    SwarmRouter,
)

# ── plato_retriever.py ────────────────────────────────────────────────────────
from .plato_retriever import (
    Bootstrap,
    ConservationLawProbe,
    ColdAgentSequence,
    make_seed_tiles,
)

# ── Legacy aliases (for code referencing old plato_retriever API) ─────────────
from .plato_retriever import ColdAgentSequence as ColdAgentBootstrapper

__all__ = [
    # pinna
    "AgentStage",
    "ResidueClass",
    "ScaffoldLevel",
    "PinnaField",
    "PinnaEncoder",
    "PinnaReader",
    "PinnaCalibrator",
    "ConservationResult",
    "check_conservation_law",
    "ConservationLawChecker",
    # tile lifecycle
    "Tile",
    "TileStore",
    "DisproofOnlyGate",
    "MortalitySweep",
    "TileCancerDetector",
    # ender protocol
    "CapabilityProfile",
    "ContaminationSensor",
    "Level0BoundaryMapping",
    "Level1SelfScaffolding",
    "Level2Composition",
    "Level3Orchestration",
    "GraduationMarkers",
    # swarm router
    "Topology",
    "TOPOLOGY_REGISTRY",
    "ROUTING_TABLE",
    "TaskDescriptor",
    "classify_task",
    "SwarmRouter",
    # plato retriever
    "Bootstrap",
    "ConservationLawProbe",
    "ColdAgentSequence",
    "ColdAgentBootstrapper",
    "make_seed_tiles",
]
