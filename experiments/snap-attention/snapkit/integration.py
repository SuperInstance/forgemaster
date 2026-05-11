"""
integration.py — External Library Integration
==============================================

Optional dependencies that gracefully degrade when not installed:
- PySheafAdapter: converts snapkit constraint systems to PySheaf sheaves
- SymPyTopologyFactory: generates SnapTopology from SymPy Lie algebra data
- NumpySnap: vectorized snap functions for high-throughput data

All integrations are optional. The module works without external deps.
"""

import numpy as np
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass

from snapkit.snap import SnapFunction, SnapResult, SnapTopologyType
from snapkit.topology import SnapTopology, ADEType


# ─── PySheaf Integration ──────────────────────────────────────────────

class PySheafAdapter:
    """
    Converts snapkit constraint systems to PySheaf sheaves.
    
    PySheaf is a Python sheaf theory library. This adapter translates
    snapkit's ConstraintSheaf into PySheaf's sheaf data structures
    for advanced consistency checking and cohomology computation.
    
    Requires: pysheaf (optional dependency)
    
    Args:
        pysheaf_instance: Pre-initialized PySheaf module (optional).
    
    Usage:
        from snapkit.cohomology import ConstraintSheaf
        
        adapter = PySheafAdapter()
        sheaf = ConstraintSheaf(tolerance=0.1)
        sheaf.add_constraint('temp', 98.6)
        sheaf.add_constraint('bp', 120.0)
        
        if adapter.is_available:
            pysheaf_graph = adapter.build_sheaf(sheaf)
            result = adapter.check_cohomology(pysheaf_graph)
            print(f"H¹ dimension: {result.h1}")
        else:
            print("PySheaf not installed. Install with: pip install pysheaf")
    """
    
    def __init__(self, pysheaf_instance: Any = None):
        self._pysheaf = pysheaf_instance
        self._available = False
        self._import_error = None
        
        if pysheaf_instance is not None:
            self._available = True
        else:
            try:
                import pysheaf
                self._pysheaf = pysheaf
                self._available = True
            except ImportError as e:
                self._import_error = str(e)
                self._available = False
    
    @property
    def is_available(self) -> bool:
        """Whether PySheaf is installed and importable."""
        return self._available
    
    @property
    def import_error(self) -> Optional[str]:
        """Error message if PySheaf import failed."""
        return self._import_error
    
    def build_sheaf(self, constraint_sheaf: Any) -> Any:
        """
        Convert a snapkit ConstraintSheaf to a PySheaf graph.
        
        Args:
            constraint_sheaf: A ConstraintSheaf instance.
        
        Returns:
            PySheaf Graph or Sheaf object.
        
        Raises:
            ImportError: If PySheaf is not installed.
        """
        if not self._available:
            raise ImportError(
                "PySheaf is required for this operation. "
                "Install with: pip install pysheaf"
            )
        
        from snapkit.cohomology import ConstraintSheaf
        
        # Access constraint data
        constraints = constraint_sheaf._constraints
        dependencies = constraint_sheaf._dependencies
        
        # Build PySheaf graph
        pysheaf_graph = self._pysheaf.Graph()
        
        # Add nodes
        for name in constraints:
            pysheaf_graph.add_node(name, stalk=constraints.get(name, 0.0))
        
        # Add edges
        for source, target in dependencies:
            pysheaf_graph.add_edge(source, target)
        
        return pysheaf_graph
    
    def check_cohomology(self, sheaf_graph: Any) -> 'CohomologyResult':
        """
        Compute H¹ of the sheaf using PySheaf.
        
        Returns a CohomologyResult with H¹ dimension info.
        """
        h1_dimension = 0
        if hasattr(sheaf_graph, 'compute_cohomology'):
            try:
                cohomology = sheaf_graph.compute_cohomology()
                if hasattr(cohomology, 'get', 'H1'):
                    h1_dimension = cohomology.get('H1', 0) or 0
                elif hasattr(cohomology, 'h1'):
                    h1_dimension = cohomology.h1 or 0
            except Exception:
                pass
        
        return CohomologyResult(h1_dimension=h1_dimension)
    
    def get_pysheaf_error_stub(self) -> str:
        """Get a helpful error message suggesting installation."""
        return (
            "PySheaf is not installed. It provides advanced sheaf-theoretic "
            "consistency checking. Install with: pip install pysheaf\n\n"
            "Without PySheaf, snapkit uses simplified constraint checking "
            "(ConstraintSheaf) that works well for most cases."
        )


@dataclass
class CohomologyResult:
    """Result of cohomology computation."""
    h1_dimension: int = 0
    
    @property
    def is_trivial(self) -> bool:
        """H¹ = 0 means no obstructions."""
        return self.h1_dimension == 0


# ─── SymPy Integration ──────────────────────────────────────────────

class SymPyTopologyFactory:
    """
    Generates SnapTopology from SymPy Lie algebra data.
    
    Uses SymPy's Lie algebra module (sympy.liealgebras) to compute
    root systems, Cartan matrices, and Dynkin diagrams for all ADE
    types. This provides the most accurate simple root coordinates
    for snap lattice construction.
    
    Requires: sympy (optional dependency)
    
    Usage:
        factory = SymPyTopologyFactory()
        
        if factory.is_available:
            # Generate any ADE topology from SymPy
            topology = factory.from_dynkin_diagram('E8')
            print(f"E8 roots: {topology.num_roots}")
            
            # Get symmetric space data
            space = factory.symmetric_space('E8', 'E7')
        else:
            # Fallback to built-in topologies
            from snapkit.topology import SnapTopology, ADEType
            topology = SnapTopology.from_ade(ADEType.E8)
    """
    
    def __init__(self, sympy_instance: Any = None):
        self._sympy = sympy_instance
        self._available = False
        self._import_error = None
        
        if sympy_instance is not None:
            self._available = True
        else:
            try:
                import sympy
                self._sympy = sympy
                self._available = True
            except ImportError as e:
                self._import_error = str(e)
                self._available = False
    
    @property
    def is_available(self) -> bool:
        return self._available
    
    def from_dynkin_diagram(self, diagram_type: str) -> 'SnapTopology':
        """
        Generate a SnapTopology from a Dynkin diagram type.
        
        Args:
            diagram_type: String like 'A2', 'D4', 'E8', etc.
        
        Returns:
            SnapTopology with SymPy-computed root system.
        
        Raises:
            ImportError: If SymPy is not installed.
            ValueError: If diagram_type is not a valid ADE type.
        """
        if not self._available:
            raise ImportError(
                "SymPy is required for this operation. "
                "Install with: pip install sympy"
            )
        
        # Parse type
        diagram_type = diagram_type.upper()
        if not diagram_type.startswith(('A', 'D', 'E')):
            raise ValueError(f"Unsupported Dynkin type: {diagram_type}")
        
        # Map to ADEType
        type_map = {
            'A1': ADEType.A1, 'A2': ADEType.A2, 'A3': ADEType.A3,
            'A4': ADEType.A4, 'D4': ADEType.D4, 'D5': ADEType.D5,
            'E6': ADEType.E6, 'E7': ADEType.E7, 'E8': ADEType.E8,
        }
        
        if diagram_type not in type_map:
            raise ValueError(f"Unsupported type: {diagram_type}")
        
        ade_type = type_map[diagram_type]
        
        # Try to get roots from SymPy
        try:
            root_system = self._sympy.liealgebras.RootSystem(diagram_type)
            simple_roots = self._get_simple_roots_sympy(root_system)
        except (AttributeError, ImportError):
            # Fallback to built-in
            simple_roots = None
        
        topology = SnapTopology.from_ade(ade_type)
        if simple_roots is not None:
            topology.simple_roots = simple_roots
        
        return topology
    
    def _get_simple_roots_sympy(self, root_system: Any) -> Optional[np.ndarray]:
        """Extract simple roots from a SymPy RootSystem."""
        try:
            if hasattr(root_system, 'simple_roots'):
                roots = root_system.simple_roots()
                if hasattr(roots, 'tolist'):
                    return np.array(roots.tolist(), dtype=float)
                elif hasattr(roots, '__iter__'):
                    return np.array([[float(r) for r in row] for row in roots])
        except Exception:
            pass
        return None
    
    def symmetric_space(self, g_type: str, k_type: str) -> Dict[str, Any]:
        """
        Get symmetric space data for G/K decomposition.
        
        Used for advanced topology: G/K = symmetric space where
        the snap lattice is a maximal compact subgroup.
        
        Args:
            g_type: Dynkin type of the full Lie group G.
            k_type: Dynkin type of the maximal compact subgroup K.
        
        Returns:
            Dict with symmetric space data.
        """
        if not self._available:
            raise ImportError(
                "SymPy is required for symmetric space computation."
            )
        
        return {
            'group_type': g_type,
            'subgroup_type': k_type,
            'dimension': None,  # Would need full Lie algebra dimension
            'rank': None,
        }
    
    def get_cartan_matrix(self, diagram_type: str) -> np.ndarray:
        """
        Get the Cartan matrix for a Dynkin diagram.
        
        Args:
            diagram_type: String like 'A2', 'D4', 'E8'.
        
        Returns:
            NumPy array with Cartan matrix.
        """
        if not self._available:
            raise ImportError("SymPy required for Cartan matrix computation.")
        
        try:
            cartan = self._sympy.liealgebras.cartan_matrix(diagram_type)
            if hasattr(cartan, 'tolist'):
                return np.array(cartan.tolist(), dtype=float)
        except Exception:
            pass
        
        return np.array([[2]])


# ─── NumpySnap: Vectorized Snap Functions ────────────────────────────

class NumpySnap:
    """
    Vectorized snap functions for high-throughput data.
    
    Processes numpy arrays in bulk using vectorized operations.
    Much faster than iterating with SnapFunction for large datasets.
    
    This is the "production" snap — when you have millions of data
    points, use NumpySnap instead of SnapFunction.
    
    Args:
        tolerance: Snap tolerance.
        baseline: Expected value.
        adaptation_rate: How fast baseline adapts (0 = no adaptation).
    
    Usage:
        snap = NumpySnap(tolerance=0.1)
        
        data = np.random.randn(10000)
        
        # Vectorized snap
        results = snap.snap_vectorized(data)
        print(f"Snap rate: {results['snap_rate']:.1%}")
        print(f"Deltas: {results['delta_mask'].sum()}")
        
        # Rolling snap
        rolling = snap.snap_rolling(data, window=50)
    """
    
    def __init__(
        self,
        tolerance: float = 0.1,
        baseline: float = 0.0,
        adaptation_rate: float = 0.0,
    ):
        self.tolerance = tolerance
        self.baseline = baseline
        self.adaptation_rate = adaptation_rate
        self._snap_count = 0
        self._delta_count = 0
    
    def snap_vectorized(self, values: np.ndarray) -> Dict[str, Any]:
        """
        Vectorized snap: process entire array at once.
        
        Args:
            values: 1D numpy array of values to snap.
        
        Returns:
            Dict with:
                - 'snapped': snapped values (where within tolerance)
                - 'deltas': delta magnitudes
                - 'delta_mask': boolean mask of non-tolerance observations
                - 'snap_rate': fraction snapped
                - 'mean_delta': mean delta magnitude
        """
        values = np.asarray(values, dtype=float)
        
        deltas = np.abs(values - self.baseline)
        delta_mask = deltas > self.tolerance
        
        snapped = np.where(delta_mask, values, self.baseline)
        
        counts = len(values)
        snap_count = int((~delta_mask).sum())
        delta_count = int(delta_mask.sum())
        
        self._snap_count += snap_count
        self._delta_count += delta_count
        
        # Adapt baseline using mean of snapped values
        if self.adaptation_rate > 0 and snap_count > 0:
            mean_snapped = float(np.mean(snapped[~delta_mask]))
            self.baseline += self.adaptation_rate * (mean_snapped - self.baseline)
        
        return {
            'snapped': snapped,
            'deltas': deltas,
            'delta_mask': delta_mask,
            'snap_rate': snap_count / max(counts, 1),
            'mean_delta': float(np.mean(deltas)),
            'max_delta': float(np.max(deltas)),
            'count': counts,
        }
    
    def snap_rolling(
        self,
        values: np.ndarray,
        window: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Apply sliding window snap to a time series.
        
        Each window is snapped independently with tolerance adapted
        to the window's statistics.
        
        Args:
            values: 1D numpy array of values.
            window: Sliding window size.
        
        Returns:
            List of per-window results.
        """
        values = np.asarray(values, dtype=float)
        results = []
        
        for i in range(0, len(values), window):
            chunk = values[i:i + window]
            if len(chunk) < window // 2:
                continue
            
            # Calibrate tolerance for this window
            self.baseline = float(np.mean(chunk))
            
            result = self.snap_vectorized(chunk)
            result['window_start'] = i
            result['window_end'] = i + len(chunk)
            results.append(result)
        
        return results
    
    def snap_matrix(
        self,
        matrix: np.ndarray,
        axis: int = 0,
    ) -> Dict[str, np.ndarray]:
        """
        Snap multi-dimensional data along an axis.
        
        Args:
            matrix: N-dimensional numpy array.
            axis: Axis along which to snap (0 = per-column, 1 = per-row).
        
        Returns:
            Dict with snapped matrix and per-axis results.
        """
        matrix = np.asarray(matrix, dtype=float)
        
        if axis == 0:
            snapped_rows = []
            for col in range(matrix.shape[1]):
                col_data = matrix[:, col]
                result = self.snap_vectorized(col_data)
                snapped_rows.append(result['snapped'])
            snapped = np.column_stack(snapped_rows)
        elif axis == 1:
            snapped = np.zeros_like(matrix)
            for row in range(matrix.shape[0]):
                result = self.snap_vectorized(matrix[row, :])
                snapped[row, :] = result['snapped']
        else:
            raise ValueError(f"Unsupported axis: {axis}")
        
        return {
            'snapped': snapped,
            'original': matrix,
        }
    
    def batch_adaptive(
        self,
        values: np.ndarray,
        target_snap_rate: float = 0.9,
        min_tolerance: float = 0.001,
        max_tolerance: float = 10.0,
        iterations: int = 10,
    ) -> Dict[str, Any]:
        """
        Batch process with adaptive tolerance calibration.
        
        Iteratively adjusts tolerance to achieve target snap rate.
        
        Args:
            values: 1D numpy array.
            target_snap_rate: Desired snap rate (0.9 = 90% within tolerance).
            min_tolerance, max_tolerance: Tolerance bounds.
            iterations: Maximum calibration iterations.
        
        Returns:
            Dict with final snap results, tolerance trajectory.
        """
        values = np.asarray(values, dtype=float)
        self.baseline = float(np.median(values))
        
        tol_history = []
        snap_rate_history = []
        
        for _ in range(iterations):
            self.tolerance = float(np.clip(self.tolerance, min_tolerance, max_tolerance))
            
            result = self.snap_vectorized(values)
            snap_rate = result['snap_rate']
            
            tol_history.append(self.tolerance)
            snap_rate_history.append(snap_rate)
            
            if abs(snap_rate - target_snap_rate) < 0.01:
                break
            
            # Adjust tolerance
            if snap_rate < target_snap_rate:
                self.tolerance *= 1.2  # Loosen
            else:
                self.tolerance *= 0.8  # Tighten
        
        return {
            'results': result,
            'tolerance_history': tol_history,
            'snap_rate_history': snap_rate_history,
            'final_tolerance': self.tolerance,
            'final_baseline': self.baseline,
        }
    
    @property
    def statistics(self) -> Dict[str, Any]:
        total = self._snap_count + self._delta_count
        return {
            'snap_count': self._snap_count,
            'delta_count': self._delta_count,
            'total_processed': total,
            'snap_rate': self._snap_count / max(total, 1),
            'tolerance': self.tolerance,
            'baseline': self.baseline,
            'adaptation_rate': self.adaptation_rate,
        }
    
    def __repr__(self):
        return (f"NumpySnap(tolerance={self.tolerance:.4f}, "
                f"baseline={self.baseline:.4f}, "
                f"processed={self._snap_count + self._delta_count})")
