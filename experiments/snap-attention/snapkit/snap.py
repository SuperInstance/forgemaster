"""
snap.py — SnapFunction: Tolerance-Based Compression
====================================================

The snap function maps continuous values to discrete lattice points,
compressing "close enough to expected" into background and flagging
what exceeds tolerance as a delta demanding attention.

"Everything within tolerance is compressed away. Only the deltas survive."
— SNAPS-AS-ATTENTION.md
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from enum import Enum


class SnapTopologyType(Enum):
    """Supported snap topologies — each a different 'flavor of randomness'."""
    BINARY = "binary"          # Coin flip — 2 outcomes
    CATEGORICAL = "categorical" # Tetrahedral — 4 categories  
    HEXAGONAL = "hexagonal"    # A₂ Eisenstein — 6-fold, densest 2D
    CUBIC = "cubic"            # ℤⁿ — standard grid
    OCTAHEDRAL = "octahedral"  # 8 directions, ±axes
    UNIFORM = "uniform"        # dN — uniform spread
    BELL = "bell"              # 2d6 — peaked distribution
    GRADIENT = "gradient"      # d100 — near-continuous


@dataclass
class SnapResult:
    """Result of snapping a value to a lattice."""
    original: float
    snapped: float
    delta: float
    within_tolerance: bool
    tolerance: float
    topology: SnapTopologyType
    
    @property
    def is_delta(self) -> bool:
        """Whether this snap produced a detectable delta."""
        return not self.within_tolerance
    
    def __repr__(self):
        status = "SNAP" if self.within_tolerance else "DELTA"
        return f"S({self.original:.4f} → {self.snapped:.4f}, δ={self.delta:.4f}, {status})"


class SnapFunction:
    """
    Tolerance-based compression of information.
    
    Maps incoming values to their nearest expected point (lattice point).
    Values within tolerance are compressed ("snapped") to the expected point.
    Values exceeding tolerance are flagged as deltas demanding attention.
    
    The snap function IS the gatekeeper of attention. It determines what
    reaches consciousness and what is compressed away.
    
    Args:
        tolerance: Maximum distance within which values are snapped to expected.
        topology: The snap topology (determines the lattice shape).
        baseline: Initial expected value. Updated as system learns.
        adaptation_rate: How fast the baseline adapts to new data (0 = never, 1 = instant).
    
    Examples:
        >>> snap = SnapFunction(tolerance=0.1)
        >>> snap.observe(0.05)  # Within tolerance → snap to 0.0
        SnapResult(0.05 → 0.0, delta=0.05, SNAP)
        >>> snap.observe(0.3)   # Exceeds tolerance → delta detected
        SnapResult(0.3 → 0.0, delta=0.3, DELTA)
    """
    
    def __init__(
        self,
        tolerance: float = 0.1,
        topology: SnapTopologyType = SnapTopologyType.HEXAGONAL,
        baseline: float = 0.0,
        adaptation_rate: float = 0.01,
    ):
        self.tolerance = tolerance
        self.topology = topology
        self.baseline = baseline
        self.adaptation_rate = adaptation_rate
        self._history: List[SnapResult] = []
        self._snap_count = 0
        self._delta_count = 0
    
    def snap(self, value: float, expected: Optional[float] = None) -> SnapResult:
        """
        Snap a value to the nearest expected point.
        
        Args:
            value: The observed value to snap.
            expected: Override the baseline expected value.
        
        Returns:
            SnapResult with snapped value, delta, and tolerance check.
        """
        exp = expected if expected is not None else self.baseline
        
        # Compute distance from expected
        delta = abs(value - exp)
        
        # Check if within tolerance
        within = delta <= self.tolerance
        
        # Snap: if within tolerance, snap to expected; otherwise keep as-is
        snapped = exp if within else value
        
        result = SnapResult(
            original=value,
            snapped=snapped,
            delta=delta,
            within_tolerance=within,
            tolerance=self.tolerance,
            topology=self.topology,
        )
        
        # Update statistics
        self._history.append(result)
        if within:
            self._snap_count += 1
        else:
            self._delta_count += 1
        
        # Adapt baseline (for non-delta observations)
        if within and self.adaptation_rate > 0:
            self.baseline += self.adaptation_rate * (value - self.baseline)
        
        return result
    
    def observe(self, value: float) -> SnapResult:
        """Alias for snap()."""
        return self.snap(value)
    
    def snap_vector(self, values: np.ndarray, expected: Optional[np.ndarray] = None) -> List[SnapResult]:
        """Snap a vector of values."""
        if expected is None:
            expected = np.full_like(values, self.baseline)
        return [self.snap(v, e) for v, e in zip(values, expected)]
    
    def snap_complex(self, value: complex, tolerance: Optional[float] = None) -> SnapResult:
        """
        Snap a complex value using Eisenstein lattice (A₂ topology).
        
        The Eisenstein lattice ℤ[ω] where ω = e^(2πi/3) provides:
        - Densest packing in 2D
        - 6-fold symmetry (isotropic compression)
        - PID property → H¹ = 0 guarantee
        """
        tol = tolerance or self.tolerance
        sqrt3_2 = np.sqrt(3) / 2
        
        # Solve: value = a + b*ω where a,b ∈ ℤ
        # ω = -1/2 + i√3/2
        # So value.real = a - b/2, value.imag = b*√3/2
        b = value.imag / sqrt3_2
        a = value.real + b / 2
        
        a_int, b_int = round(a), round(b)
        snapped = complex(a_int - b_int / 2, b_int * sqrt3_2)
        
        delta = abs(value - snapped)
        within = delta <= tol
        
        return SnapResult(
            original=value.real,  # Store magnitude
            snapped=snapped.real,
            delta=delta,
            within_tolerance=within,
            tolerance=tol,
            topology=SnapTopologyType.HEXAGONAL,
        )
    
    @property
    def snap_rate(self) -> float:
        """Fraction of observations that snapped (within tolerance)."""
        total = self._snap_count + self._delta_count
        return self._snap_count / total if total > 0 else 0.0
    
    @property
    def delta_rate(self) -> float:
        """Fraction of observations that exceeded tolerance (deltas)."""
        return 1.0 - self.snap_rate
    
    @property
    def calibration(self) -> float:
        """
        How well-calibrated the snap tolerance is.
        
        0.0 = no snaps (tolerance too tight → anxiety)
        1.0 = all snaps (tolerance too loose → complacency)
        ~0.9 = well-calibrated (most things are expected, deltas are rare)
        """
        return self.snap_rate
    
    @property
    def statistics(self) -> dict:
        """Summary statistics of the snap function's history."""
        if not self._history:
            return {'total': 0}
        
        deltas = [r.delta for r in self._history]
        return {
            'total_observations': len(self._history),
            'snap_count': self._snap_count,
            'delta_count': self._delta_count,
            'snap_rate': self.snap_rate,
            'mean_delta': float(np.mean(deltas)),
            'max_delta': float(np.max(deltas)),
            'calibration': self.calibration,
            'current_baseline': self.baseline,
            'tolerance': self.tolerance,
        }
    
    def reset(self, baseline: Optional[float] = None):
        """Reset snap function state."""
        self.baseline = baseline if baseline is not None else self.baseline
        self._history.clear()
        self._snap_count = 0
        self._delta_count = 0
    
    def calibrate(self, values: List[float], target_snap_rate: float = 0.9):
        """
        Auto-calibrate tolerance to achieve target snap rate.
        
        This is the snap calibration that distinguishes expert from novice:
        the tolerance is adjusted so that exactly the right fraction of
        observations snap to "expected" and the rest demand attention.
        
        Args:
            values: Sample of typical values to calibrate on.
            target_snap_rate: Desired fraction of snaps (0.9 = 90% within tolerance).
        """
        if not values:
            return
        
        # Set baseline to mean
        self.baseline = float(np.mean(values))
        
        # Compute distances from baseline
        distances = sorted([abs(v - self.baseline) for v in values])
        
        # Set tolerance so target_snap_rate fraction are within it
        idx = int(len(distances) * target_snap_rate)
        idx = min(idx, len(distances) - 1)
        self.tolerance = distances[idx]
    
    def __repr__(self):
        return (f"SnapFunction(tolerance={self.tolerance:.4f}, "
                f"topology={self.topology.value}, "
                f"baseline={self.baseline:.4f}, "
                f"calibration={self.calibration:.2f})")
