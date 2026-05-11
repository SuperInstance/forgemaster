"""
snapkit — Tolerance-Compressed Attention Allocation Library
============================================================

A reusable library implementing snap-attention theory:
the tolerance compression of context so cognition can focus
on where thinking matters.

Core concepts:
  - SnapFunction: compresses information to "close enough to expected"
  - DeltaDetector: tracks what exceeds snap tolerance
  - AttentionBudget: finite cognition allocation to actionable deltas
  - ScriptLibrary: learned patterns that free cognition
  - SnapTopology: Platonic/ADE classification of snap shapes
  - LearningCycle: experience → pattern → script → automation

Advanced modules:
  - adversarial: Adversarial snap calibration (real vs fake deltas)
  - crossdomain: Cross-domain feel transfer
  - streaming: Real-time stream processing
  - visualization: Terminal + HTML visualization
  - integration: External library integration (PySheaf, SymPy, Numpy)
  - serial: Serialization & persistence
  - pipeline: Composable processing pipelines

Based on: SNAPS-AS-ATTENTION.md (Forgemaster & Digennaro, 2026)

"The snap doesn't tell you what's true. The snap tells you what you can
SAFELY IGNORE so you can think about what matters."
"""

from snapkit.snap import SnapFunction, SnapResult, SnapTopologyType
from snapkit.delta import DeltaDetector, Delta, DeltaStream, DeltaSeverity
from snapkit.attention import AttentionBudget, AttentionAllocation
from snapkit.scripts import ScriptLibrary, Script, ScriptMatch, ScriptStatus
from snapkit.topology import (
    SnapTopology, ADEType, ADE_DATA,
    binary_topology, hexagonal_topology, tetrahedral_topology,
    triality_topology, exceptional_e6, exceptional_e7, exceptional_e8,
    all_topologies, recommend_topology,
)
from snapkit.learning import LearningCycle, LearningPhase, LearningState
from snapkit.cohomology import ConstraintSheaf, ConsistencyReport

# Optional advanced modules (always importable)
try:
    from snapkit import adversarial
except ImportError:
    adversarial = None  # type: ignore

try:
    from snapkit import crossdomain
except ImportError:
    crossdomain = None  # type: ignore

try:
    from snapkit import streaming
except ImportError:
    streaming = None  # type: ignore

try:
    from snapkit import visualization
except ImportError:
    visualization = None  # type: ignore

try:
    from snapkit import integration
except ImportError:
    integration = None  # type: ignore

try:
    from snapkit import serial
except ImportError:
    serial = None  # type: ignore

try:
    from snapkit import pipeline
except ImportError:
    pipeline = None  # type: ignore

try:
    from snapkit import cli
except ImportError:
    cli = None  # type: ignore


__version__ = "0.2.0"
__author__ = "Forgemaster ⚒️ / Casey Digennaro"
__all__ = [
    # Core
    "SnapFunction", "SnapResult", "SnapTopologyType",
    "DeltaDetector", "Delta", "DeltaStream", "DeltaSeverity",
    "AttentionBudget", "AttentionAllocation",
    "ScriptLibrary", "Script", "ScriptMatch", "ScriptStatus",
    "SnapTopology", "ADEType", "ADE_DATA",
    "binary_topology", "hexagonal_topology", "tetrahedral_topology",
    "triality_topology", "exceptional_e6", "exceptional_e7", "exceptional_e8",
    "all_topologies", "recommend_topology",
    "LearningCycle", "LearningPhase", "LearningState",
    "ConstraintSheaf", "ConsistencyReport",
    # Advanced modules
    "adversarial", "crossdomain", "streaming", "visualization",
    "integration", "serial", "pipeline", "cli",
]
