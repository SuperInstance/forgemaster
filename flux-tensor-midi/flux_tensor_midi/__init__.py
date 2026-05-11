"""FLUX-Tensor-MIDI: Musical protocol for fleet coordination."""

from flux_tensor_midi.core.flux import FluxChannel, FluxVector, Alignment
from flux_tensor_midi.core.room import RoomMusician
from flux_tensor_midi.core.clock import TZeroClock
from flux_tensor_midi.core.snap import EisensteinSnap, SnapResult
from flux_tensor_midi.midi.events import MidiEvent
from flux_tensor_midi.ensemble.band import Band

__version__ = "0.1.0"
__all__ = [
    "FluxChannel",
    "FluxVector",
    "Alignment",
    "RoomMusician",
    "TZeroClock",
    "EisensteinSnap",
    "SnapResult",
    "MidiEvent",
    "Band",
]
