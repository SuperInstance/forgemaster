"""core — PLATO-Native Agent Infrastructure

The deep connective layer. Every future agent stands on this.

Six modules, one harness:

  pinna             Fixed geometry provenance encoding.
                    AgentStage, ResidueClass, ScaffoldLevel enums.
                    PinnaField, PinnaEncoder, PinnaReader, PinnaCalibrator.
                    check_conservation_law() — the most important falsifiable test.

  tile_lifecycle    Tile CRUD with disproof-only admission and mortality sweep.
                    Tile, TileStore, DisproofOnlyGate, MortalitySweep,
                    TileCancerDetector.

  ender_protocol    Simulation-first alignment through progressive abstraction.
                    CapabilityProfile, ContaminationSensor,
                    Level0BoundaryMapping, Level1SelfScaffolding,
                    Level2Composition, Level3Orchestration, GraduationMarkers.

  swarm_router      Topology-aware task routing with jam session mode.
                    Topology, TaskDescriptor, SwarmRouter,
                    ROUTING_TABLE, TOPOLOGY_REGISTRY.

  plato_retriever   Cold-start bootstrap (11-step) and pinna-aware retrieval.
                    Bootstrap, ColdAgentSequence, ConservationLawProbe,
                    make_seed_tiles().

  harness           The conductor's baton — wires all six modules together.
                    Harness, FleetState, FleetAgent, TaskResult.

Usage:
    from core import Harness, TaskDescriptor

    harness = Harness("my-agent", query_fn)
    harness.seed()
    result = harness.bootstrap()
    task = TaskDescriptor.from_description("compute Eisenstein norm")
    task_result = harness.execute(task)

Evidence:
    UNIFIED-FRAMEWORK.md, PINNA-PRINCIPLE.md, SWARM-TOPOLOGY.md,
    JAM-SESSION-ANALYSIS.md, PLATO-LOOPS.md, MULTI-MODEL-SYNTHESIS.md

Findings:
    R1-R32 (3 confidence tiers: BEDROCK, SOLID, SUGGESTIVE)

Tests:
    tests/test_core.py — 35 tests, all passing, provenance-traced
"""

# ─── Enums (canonical definitions live in pinna.py) ────────────────────────────
from .pinna import AgentStage, ResidueClass, ScaffoldLevel

# ─── Pinna (provenance encoding) ───────────────────────────────────────────────
from .pinna import (
    PinnaField,
    PinnaEncoder,
    PinnaReader,
    PinnaCalibrator,
    ConservationLawChecker,
    ConservationResult,
    check_conservation_law,
)

# ─── Tile Lifecycle (CRUD + mortality) ─────────────────────────────────────────
from .tile_lifecycle import (
    Tile,
    TileStore,
    DisproofOnlyGate,
    MortalitySweep,
    TileCancerDetector,
)

# ─── Ender Protocol (alignment + capability) ───────────────────────────────────
from .ender_protocol import (
    CapabilityProfile,
    ContaminationSensor,
    Level0BoundaryMapping,
    Level1SelfScaffolding,
    Level2Composition,
    Level3Orchestration,
    GraduationMarkers,
)

# ─── Swarm Router (topology + routing) ─────────────────────────────────────────
from .swarm_router import (
    Topology,
    TaskDescriptor,
    SwarmRouter,
    ROUTING_TABLE,
    TOPOLOGY_REGISTRY,
    classify_task,
)

# ─── PLATO Retriever (cold start + retrieval) ──────────────────────────────────
from .plato_retriever import (
    make_seed_tiles,
    Bootstrap,
    ColdAgentSequence,
    ConservationLawProbe,
)

# ─── Harness (the conductor) ───────────────────────────────────────────────────
from .harness import (
    Harness,
    FleetState,
    FleetAgent,
    TaskResult,
)

__all__ = [
    # Enums
    "AgentStage", "ResidueClass", "ScaffoldLevel",
    # Pinna
    "PinnaField", "PinnaEncoder", "PinnaReader", "PinnaCalibrator",
    "ConservationLawChecker", "ConservationResult", "check_conservation_law",
    # Tile Lifecycle
    "Tile", "TileStore", "DisproofOnlyGate", "MortalitySweep", "TileCancerDetector",
    # Ender Protocol
    "CapabilityProfile", "ContaminationSensor",
    "Level0BoundaryMapping", "Level1SelfScaffolding",
    "Level2Composition", "Level3Orchestration", "GraduationMarkers",
    # Swarm Router
    "Topology", "TaskDescriptor", "SwarmRouter",
    "ROUTING_TABLE", "TOPOLOGY_REGISTRY", "classify_task",
    # PLATO Retriever
    "make_seed_tiles", "Bootstrap", "ColdAgentSequence", "ConservationLawProbe",
    # Harness
    "Harness", "FleetState", "FleetAgent", "TaskResult",
]
