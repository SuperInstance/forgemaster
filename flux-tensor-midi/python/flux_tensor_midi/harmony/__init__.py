"""
Harmony modules for FLUX-Tensor-MIDI.
"""

from flux_tensor_midi.harmony.jaccard import (
    jaccard_index,
    weighted_jaccard,
    jaccard_distance,
)
from flux_tensor_midi.harmony.spectrum import (
    spectral_centroid,
    spectral_flux,
    salience_weighted_flux,
    dominant_channel,
    autocorrelation,
)
from flux_tensor_midi.harmony.chord import (
    HarmonyState,
    ChordQuality,
    INTERVAL_CONSONANCE,
)

__all__ = [
    "jaccard_index",
    "weighted_jaccard",
    "jaccard_distance",
    "spectral_centroid",
    "spectral_flux",
    "salience_weighted_flux",
    "dominant_channel",
    "autocorrelation",
    "HarmonyState",
    "ChordQuality",
    "INTERVAL_CONSONANCE",
]
