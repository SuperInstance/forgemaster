"""
SnapKit v2 — Eisenstein lattice snap, temporal analysis, and connectome detection.

Zero external dependencies. stdlib only.
"""

from snapkit.eisenstein import EisensteinInteger, eisenstein_snap, eisenstein_distance, eisenstein_round, eisenstein_round_naive
from snapkit.eisenstein_voronoi import eisenstein_snap_voronoi, eisenstein_snap_naive as eisenstein_snap_naive_voronoi
from snapkit.temporal import TemporalSnap, TemporalResult, BeatGrid
from snapkit.spectral import entropy, hurst_exponent, autocorrelation, spectral_summary
from snapkit.midi import FluxTensorMIDI, Room, TempoMap, MIDIEvent
from snapkit.connectome import (
    TemporalConnectome,
    CouplingType,
    RoomPair,
    ConnectomeResult,
)

__version__ = "2.0.0"
__all__ = [
    "EisensteinInteger",
    "eisenstein_snap",
    "eisenstein_distance",
    "eisenstein_round",
    "eisenstein_round_naive",
    "eisenstein_snap_voronoi",
    "TemporalSnap",
    "TemporalResult",
    "BeatGrid",
    "entropy",
    "hurst_exponent",
    "autocorrelation",
    "spectral_summary",
    "FluxTensorMIDI",
    "Room",
    "TempoMap",
    "MIDIEvent",
    "TemporalConnectome",
    "CouplingType",
    "RoomPair",
    "ConnectomeResult",
]
