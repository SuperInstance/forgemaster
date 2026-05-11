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
from typing import Optional, List, Tuple, Dict, Any, Union
from enum import Enum
import json


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
    
    Supports:
    - Multi-dimensional snap (vectors, matrices)
    - Adaptive tolerance (auto-adjusts based on recent delta rate)
    - Hierarchical snap (multiple tolerance levels simultaneously)
    - Batch processing
    - Rolling window for time series
    - Serialization
    
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
        
        # Adaptive tolerance state
        self._adaptive_enabled = False
        self._recent_delta_rates: List[float] = []
        self._base_tolerance = tolerance
        
        # Hierarchical snap state
        self._hierarchical_levels: List[float] = []
    
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
        
        # Adaptive tolerance adjustment
        if self._adaptive_enabled:
            self._update_adaptive_tolerance()
        
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
        
        The Eisenstein lattice ℝ[ω] where ω = e^(2πi/3) provides:
        - Densest packing in 2D
        - 6-fold symmetry (isotropic compression)
        - PID property → H¹ = 0 guarantee
        """
        tol = tolerance or self.tolerance
        sqrt3_2 = np.sqrt(3) / 2
        
        # Solve: value = a + b*ω where a,b ∈ ℤ
        # ω = -1/2 + i√3/2
        b = value.imag / sqrt3_2
        a = value.real + b / 2
        
        a_int, b_int = round(a), round(b)
        snapped = complex(a_int - b_int / 2, b_int * sqrt3_2)
        
        delta = abs(value - snapped)
        within = delta <= tol
        
        return SnapResult(
            original=value.real,
            snapped=snapped.real,
            delta=delta,
            within_tolerance=within,
            tolerance=tol,
            topology=SnapTopologyType.HEXAGONAL,
        )
    
    # ─── Multi-Dimensional Snap ────────────────────────────────────
    
    def snap_nd(self, values: np.ndarray) -> List[SnapResult]:
        """
        Snap a multi-dimensional array element-wise.
        
        Args:
            values: N-dimensional numpy array.
        
        Returns:
            Flattened list of SnapResults for each element.
        """
        flat = np.asarray(values).flatten()
        return [self.snap(float(v)) for v in flat]
    
    def snap_matrix(self, matrix: np.ndarray, axis: int = 1) -> np.ndarray:
        """
        Snap a 2D matrix along an axis, preserving shape.
        
        Args:
            matrix: 2D numpy array.
            axis: 0 = per-column, 1 = per-row.
        
        Returns:
            Matrix with snapped values, same shape as input.
        """
        matrix = np.asarray(matrix, dtype=float)
        result = np.zeros_like(matrix)
        
        if axis == 0:
            for col in range(matrix.shape[1]):
                for row in range(matrix.shape[0]):
                    sr = self.snap(float(matrix[row, col]))
                    result[row, col] = sr.snapped
        elif axis == 1:
            for row in range(matrix.shape[0]):
                for col in range(matrix.shape[1]):
                    sr = self.snap(float(matrix[row, col]))
                    result[row, col] = sr.snapped
        else:
            raise ValueError(f"Unsupported axis: {axis}")
        
        return result
    
    # ─── Adaptive Tolerance ────────────────────────────────────────
    
    def enable_adaptive_tolerance(self, window: int = 50):
        """
        Enable adaptive tolerance that adjusts based on recent delta rate.
        
        When delta rate spikes, tolerance tightens (more attention).
        When delta rate drops, tolerance loosens (less attention).
        
        Args:
            window: Number of recent observations to track.
        """
        self._adaptive_enabled = True
        self._adaptive_window = window
        self._base_tolerance = self.tolerance
    
    def disable_adaptive_tolerance(self):
        """Disable adaptive tolerance and restore base tolerance."""
        self._adaptive_enabled = False
        self.tolerance = self._base_tolerance
    
    def _update_adaptive_tolerance(self):
        """Update tolerance based on recent delta rate."""
        if len(self._history) < 5:
            return
        
        recent = self._history[-min(len(self._history), self._adaptive_window):]
        delta_count = sum(1 for r in recent if r.is_delta)
        rate = delta_count / len(recent)
        
        self._recent_delta_rates.append(rate)
        if len(self._recent_delta_rates) > 20:
            self._recent_delta_rates.pop(0)
        
        # Adjust: high rate -> tighten; low rate -> loosen
        if rate > 0.4:
            self.tolerance = max(0.001, self._base_tolerance * (1.0 - min(rate, 0.8)))
        elif rate < 0.05 and len(self._history) > 20:
            self.tolerance = min(self._base_tolerance * 2.0, self.tolerance * 1.05)
        else:
            # Slight smoothing toward base
            self.tolerance += 0.05 * (self._base_tolerance - self.tolerance)
    
    # ─── Hierarchical Snap ──────────────────────────────────────────
    
    def snap_hierarchical(
        self, value: float, levels: Optional[List[float]] = None
    ) -> List[SnapResult]:
        """
        Snap a value at multiple tolerance levels simultaneously.
        
        Each level has a different tolerance, producing a hierarchy of
        snap results from tight (few snaps) to loose (many snaps).
        
        This models attention at different resolutions: tight tolerance
        catches micro-deltas, loose tolerance catches major shifts.
        
        Args:
            value: Value to snap.
            levels: Tolerance levels. Default: [0.01, 0.05, 0.1, 0.2, 0.5].
        
        Returns:
            List of SnapResults, one per level.
        """
        if levels is None:
            levels = [0.01, 0.05, 0.1, 0.2, 0.5]
        
        results = []
        original_tolerance = self.tolerance
        
        for level_tol in levels:
            self.tolerance = level_tol
            results.append(self.snap(value))
        
        self.tolerance = original_tolerance
        self._hierarchical_levels = levels
        
        return results
    
    def hierarchical_profile(self, value: float) -> Dict[str, Any]:
        """
        Get a hierarchical snap profile showing at which tolerance
        levels the value is a snap vs delta.
        
        Useful for understanding the "depth" of a delta — how tightly
        calibrated does your snap need to be to catch this?
        
        Returns:
            Dict with 'levels' and 'transition_tolerance'.
        """
        results = self.snap_hierarchical(value)
        
        transition = None
        for r in results:
            if r.is_delta and transition is None:
                transition = r.tolerance
        
        return {
            'levels': [
                {'tolerance': r.tolerance, 'is_delta': r.is_delta, 'delta': r.delta}
                for r in results
            ],
            'transition_tolerance': transition,
            'value': value,
            'baseline': self.baseline,
        }
    
    # ─── Batch Processing ───────────────────────────────────────────
    
    def snap_batch(self, values: List[float]) -> Dict[str, Any]:
        """
        Vectorized batch processing of multiple values.
        
        Processes all values without changing internal state
        (no baseline adaptation during batch).
        
        Args:
            values: List of values to snap.
        
        Returns:
            Dict with snap_results, snap_rate, mean_delta.
        """
        original_rate = self.adaptation_rate
        self.adaptation_rate = 0.0  # Pause adaptation
        
        results = [self.snap(v) for v in values]
        
        self.adaptation_rate = original_rate
        
        deltas = [r.delta for r in results]
        snap_count = sum(1 for r in results if r.within_tolerance)
        
        return {
            'results': results,
            'snap_rate': snap_count / max(len(results), 1),
            'mean_delta': float(np.mean(deltas)) if deltas else 0.0,
            'max_delta': float(np.max(deltas)) if deltas else 0.0,
            'count': len(results),
        }
    
    def snap_rolling(
        self, values: List[float], window: int = 50, stride: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Rolling window snap for time series.
        
        Each window is snapped independently. The snap function's
        baseline is updated per window.
        
        Args:
            values: Time series values.
            window: Window size.
            stride: Steps between windows.
        
        Returns:
            List of per-window analysis dicts.
        """
        results = []
        
        for i in range(0, len(values) - window + 1, stride):
            chunk = values[i:i + window]
            
            # Calibrate for this window
            old_baseline = self.baseline
            old_tolerance = self.tolerance
            
            self.calibrate(chunk)
            
            # Process window
            window_results = [self.snap(v) for v in chunk]
            
            results.append({
                'window_start': i,
                'window_end': i + window,
                'tolerance': self.tolerance,
                'baseline': self.baseline,
                'snap_rate': sum(1 for r in window_results if r.within_tolerance) / window,
                'mean_delta': float(np.mean([r.delta for r in window_results])),
            })
            
            # Restore state
            self.baseline = old_baseline
            self.tolerance = old_tolerance
        
        return results
    
    # ─── Serialization Support ───────────────────────────────────────
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize snap function state to a dict."""
        return {
            'tolerance': self.tolerance,
            'topology': self.topology.value,
            'baseline': self.baseline,
            'adaptation_rate': self.adaptation_rate,
            'snap_count': self._snap_count,
            'delta_count': self._delta_count,
            'history': [
                {
                    'original': r.original,
                    'snapped': r.snapped,
                    'delta': r.delta,
                    'within_tolerance': r.within_tolerance,
                    'tolerance': r.tolerance,
                }
                for r in self._history
            ],
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SnapFunction':
        """Restore snap function from a dict."""
        import numpy as np
        
        topology = SnapTopologyType(data.get('topology', SnapTopologyType.HEXAGONAL.value))
        snap = cls(
            tolerance=data.get('tolerance', 0.1),
            topology=topology,
            baseline=data.get('baseline', 0.0),
            adaptation_rate=data.get('adaptation_rate', 0.01),
        )
        
        # Restore history if present
        history_data = data.get('history', [])
        for h in history_data:
            snap._history.append(SnapResult(
                original=h['original'],
                snapped=h['snapped'],
                delta=h['delta'],
                within_tolerance=h['within_tolerance'],
                tolerance=h.get('tolerance', snap.tolerance),
                topology=topology,
            ))
        
        snap._snap_count = data.get('snap_count', 0)
        snap._delta_count = data.get('delta_count', 0)
        
        return snap
    
    # ─── Existing Properties ─────────────────────────────────────────
    
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
            'delta_rate': self.delta_rate,
            'mean_delta': float(np.mean(deltas)),
            'max_delta': float(np.max(deltas)),
            'calibration': self.calibration,
            'current_baseline': self.baseline,
            'tolerance': self.tolerance,
            'topology': self.topology.value,
            'adaptive_enabled': self._adaptive_enabled,
            'adaptation_rate': self.adaptation_rate,
        }
    
    def reset(self, baseline: Optional[float] = None):
        """Reset snap function state."""
        self.baseline = baseline if baseline is not None else self.baseline
        self._history.clear()
        self._snap_count = 0
        self._delta_count = 0
        self._recent_delta_rates.clear()
    
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
        self._base_tolerance = self.tolerance
    
    def __repr__(self):
        return (f"SnapFunction(tolerance={self.tolerance:.4f}, "
                f"topology={self.topology.value}, "
                f"baseline={self.baseline:.4f}, "
                f"calibration={self.calibration:.2f})")
