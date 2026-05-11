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

Based on: SNAP-ATTENTION-INTELLIGIBLE.md (Forgemaster & Digennaro, 2026)

Usage:
    from snapkit import SnapFunction, DeltaDetector, AttentionBudget
    
    snap = SnapFunction(tolerance=0.1, topology='hexagonal')
    detector = DeltaDetector(snap)
    budget = AttentionBudget(total=100.0)
    
    # Process information stream
    for value in data_stream:
        delta = detector.observe(value)
        if delta.exceeds_tolerance:
            budget.allocate(delta, actionability=0.8)
"""

from snapkit.snap import SnapFunction, SnapResult
from snapkit.delta import DeltaDetector, Delta, DeltaStream
from snapkit.attention import AttentionBudget, AttentionAllocation
from snapkit.scripts import ScriptLibrary, Script, ScriptMatch
from snapkit.topology import SnapTopology, ADEType
from snapkit.learning import LearningCycle, LearningPhase
from snapkit.cohomology import ConstraintSheaf, ConsistencyReport

__version__ = "0.1.0"
__author__ = "Forgemaster ⚒️ / Casey Digennaro"
