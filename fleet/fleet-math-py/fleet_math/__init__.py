"""fleet-math: Cyclotomic field, Eisenstein, and Penrose tiling operations.

Exports:
- CyclotomicField / Q15 — cyclotomic field Q(ζ₁₅)
- eisenstein_project, penrose_project — unified 6D cut-and-project
- unified_snap, eisenstein_snap — lattice snapping
- dodecet_encode — 12-bit dodecet encoding
- constraint_check / constraint_db — 3-tier constraint checking
- BoundedDrift — drift verification for open/closed walks
- generate_eisenstein_lattice, generate_penrose_vertices
"""

from fleet_math.cyclotomic import (
    CyclotomicField,
    Q15,
    eisenstein_project,
    penrose_project,
    unified_snap,
    eisenstein_snap_to_lattice,
    dodecet_encode,
    generate_eisenstein_lattice,
    generate_penrose_vertices,
    BoundedDrift,
    drift_bound_open,
    drift_bound_closed,
)

from fleet_math.eisenstein import (
    eins_round,
    eins_distance,
    constraint_check,
)

__all__ = [
    # Cyclotomic field
    "CyclotomicField",
    "Q15",
    "eisenstein_project",
    "penrose_project",
    "unified_snap",
    "eisenstein_snap_to_lattice",
    "dodecet_encode",
    # Lattice generation
    "generate_eisenstein_lattice",
    "generate_penrose_vertices",
    # Drift verification
    "BoundedDrift",
    "drift_bound_open",
    "drift_bound_closed",
    # Eisenstein operations
    "eins_round",
    "eins_distance",
    "constraint_check",
]

__version__ = "0.1.0"
