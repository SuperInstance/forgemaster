"""tensor-penrose — Constraint tensors on Penrose tilings."""

from tensor_penrose._tensor_penrose import (
    Tile,
    Tiling,
    EisensteinBackend,
    PenroseBackend,
    ThresholdOp,
    L1NormOp,
    apply_threshold,
    from_coordinates,
)

__version__ = "0.1.0"

__all__ = [
    "Tile",
    "Tiling",
    "EisensteinBackend",
    "PenroseBackend",
    "ThresholdOp",
    "L1NormOp",
    "apply_threshold",
    "from_coordinates",
]
