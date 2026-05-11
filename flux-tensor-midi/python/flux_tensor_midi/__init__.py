"""
FLUX-Tensor-MIDI: PLATO rooms as musicians.

Each room has a T-0 clock, produces timestamped events (tiles=notes),
listens to others, snaps to rhythm via Eisenstein lattice, and sends
side-channels (nods/smiles/frowns) for ensemble coordination.

Zero external dependencies. Pure Python 3.10+.
"""

from flux_tensor_midi.core.flux import FluxVector
from flux_tensor_midi.core.clock import TZeroClock
from flux_tensor_midi.core.room import RoomMusician
from flux_tensor_midi.core.snap import EisensteinSnap

__all__ = [
    "FluxVector",
    "TZeroClock",
    "RoomMusician",
    "EisensteinSnap",
]
