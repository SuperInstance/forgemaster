"""
cohomology.py — H¹ Computation via Sheaf-Theoretic Constraint Checking
=======================================================================

Constraint verification IS attention allocation. H¹ ≠ 0 means there's
an obstruction to gluing local data into a global picture — a delta
that demands attention.

"H¹ of the structure sheaf = 0 iff the ring of integers has class
number 1. ℤ[ω] (Eisenstein) has class number 1 → H¹ = 0 guarantee."
— ADE-VERIFICATION.md
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

from snapkit.topology import SnapTopology, ADEType


@dataclass
class ConsistencyReport:
    """Report on the consistency of a constraint sheaf."""
    num_constraints: int
    max_delta: float
    mean_delta: float
    h1_analog: int               # Number of constraints exceeding tolerance
    delta_detected: bool
    tolerance: float
    topology: str
    
    @property
    def globally_consistent(self) -> bool:
        """Whether all constraints are within tolerance (H¹ = 0 analog)."""
        return not self.delta_detected
    
    def __repr__(self):
        status = "CONSISTENT (H¹=0)" if self.globally_consistent else "DELTA DETECTED (H¹≠0)"
        return (f"ConsistencyReport({status}, "
                f"max_δ={self.max_delta:.4f}, "
                f"h1={self.h1_analog})")


class ConstraintSheaf:
    """
    A sheaf-theoretic model of a constraint system.
    
    Each constraint node has a value (stalk). Dependencies between
    constraints define the restriction maps. Consistency radius
    measures whether local constraints compose to global consistency.
    
    On the Eisenstein lattice (A₂), the PID property guarantees that
    local consistency → global consistency (H¹ = 0).
    
    Args:
        topology: The snap topology for the constraint lattice.
        tolerance: Maximum allowable drift before delta is detected.
    
    Usage:
        sheaf = ConstraintSheaf(topology=hexagonal_topology(), tolerance=0.1)
        
        sheaf.add_constraint('temp', 98.6)
        sheaf.add_constraint('bp_sys', 120.0)
        sheaf.add_constraint('bp_dia', 80.0)
        
        sheaf.add_dependency('bp_sys', 'bp_dia')  # Systolic affects diastolic
        
        report = sheaf.check_consistency()
        print(report)  # CONSISTENT (H¹=0) or DELTA DETECTED (H¹≠0)
    """
    
    def __init__(
        self,
        topology: Optional[SnapTopology] = None,
        tolerance: float = 0.1,
    ):
        self.topology = topology or SnapTopology.from_ade(ADEType.A2)
        self.tolerance = tolerance
        
        # Constraint graph
        self._constraints: Dict[str, float] = {}
        self._expected: Dict[str, float] = {}
        self._dependencies: List[Tuple[str, str]] = []
    
    def add_constraint(self, name: str, value: float, expected: Optional[float] = None):
        """
        Add a constraint node with its current value.
        
        Args:
            name: Unique identifier for this constraint.
            value: Current value of the constraint.
            expected: Expected value (baseline). If None, first value becomes baseline.
        """
        self._constraints[name] = value
        if expected is not None:
            self._expected[name] = expected
        elif name not in self._expected:
            self._expected[name] = value
    
    def add_dependency(self, source: str, target: str):
        """
        Add a dependency: source constraint affects target constraint.
        
        This defines the restriction map in the sheaf: how constraint
        values propagate through the dependency graph.
        """
        self._dependencies.append((source, target))
    
    def check_consistency(self) -> ConsistencyReport:
        """
        Check global consistency of the constraint sheaf.
        
        For each constraint:
        1. Compute delta from expected value
        2. Snap to lattice if within tolerance
        3. Flag as delta if exceeding tolerance
        
        For each dependency:
        1. Check if source and target constraints are compatible
        2. Compute compatibility delta
        
        Returns a ConsistencyReport with H¹ analog.
        """
        if not self._constraints:
            return ConsistencyReport(
                num_constraints=0, max_delta=0.0, mean_delta=0.0,
                h1_analog=0, delta_detected=False, tolerance=self.tolerance,
                topology=self.topology.name,
            )
        
        deltas = []
        
        # Check individual constraints
        for name, value in self._constraints.items():
            expected = self._expected.get(name, value)
            delta = abs(value - expected)
            deltas.append(delta)
        
        # Check dependencies (compatibility)
        for source, target in self._dependencies:
            if source in self._constraints and target in self._constraints:
                # Dependencies should maintain certain relationships
                # Simple version: check if delta between related constraints is within tolerance
                s_val = self._constraints[source]
                t_val = self._constraints[target]
                s_exp = self._expected.get(source, s_val)
                t_exp = self._expected.get(target, t_val)
                
                # If source has drifted, target should reflect it
                s_delta = s_val - s_exp
                t_delta = t_val - t_exp
                
                # Compatibility delta: how much the dependency is violated
                compat_delta = abs(s_delta - t_delta)
                deltas.append(compat_delta * 0.5)  # Weight dependencies
        
        max_delta = max(deltas) if deltas else 0.0
        mean_delta = float(np.mean(deltas)) if deltas else 0.0
        h1 = sum(1 for d in deltas if d > self.tolerance)
        
        return ConsistencyReport(
            num_constraints=len(self._constraints),
            max_delta=max_delta,
            mean_delta=mean_delta,
            h1_analog=h1,
            delta_detected=max_delta > self.tolerance,
            tolerance=self.tolerance,
            topology=self.topology.name,
        )
    
    def check_eisenstein(self, values: List[complex]) -> ConsistencyReport:
        """
        Check constraints on the Eisenstein lattice.
        
        Each value is snapped to the nearest Eisenstein integer.
        Deltas exceeding tolerance indicate H¹ ≠ 0 obstructions.
        """
        sqrt3_2 = np.sqrt(3) / 2
        deltas = []
        
        for v in values:
            b = v.imag / sqrt3_2
            a = v.real + b / 2
            snapped = complex(round(a) - round(b) / 2, round(b) * sqrt3_2)
            delta = abs(v - snapped)
            deltas.append(delta)
        
        max_delta = max(deltas) if deltas else 0.0
        mean_delta = float(np.mean(deltas)) if deltas else 0.0
        h1 = sum(1 for d in deltas if d > self.tolerance)
        
        return ConsistencyReport(
            num_constraints=len(values),
            max_delta=max_delta,
            mean_delta=mean_delta,
            h1_analog=h1,
            delta_detected=max_delta > self.tolerance,
            tolerance=self.tolerance,
            topology='A2_Eisenstein',
        )
    
    def update_expected(self, name: str, expected: float):
        """Update the expected value for a constraint."""
        self._expected[name] = expected
    
    def get_deltas(self) -> Dict[str, float]:
        """Get the current delta for each constraint."""
        result = {}
        for name, value in self._constraints.items():
            expected = self._expected.get(name, value)
            result[name] = abs(value - expected)
        return result
    
    def __repr__(self):
        return (f"ConstraintSheaf(nodes={len(self._constraints)}, "
                f"edges={len(self._dependencies)}, "
                f"topology={self.topology.name}, "
                f"tol={self.tolerance})")
