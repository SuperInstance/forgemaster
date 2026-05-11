"""
MIDI channel mapping for FLUX-Tensor-MIDI.

Maps musician roles to MIDI channels for ensemble coordination.
"""

from __future__ import annotations
from enum import IntEnum
from flux_tensor_midi.core.snap import RhythmicRole


class MidiChannel(IntEnum):
    """Standard MIDI channels (0–15)."""
    CHANNEL_1 = 0
    CHANNEL_2 = 1
    CHANNEL_3 = 2
    CHANNEL_4 = 3
    CHANNEL_5 = 4
    CHANNEL_6 = 5
    CHANNEL_7 = 6
    CHANNEL_8 = 7
    CHANNEL_9 = 8
    CHANNEL_10 = 9   # GM percussion
    CHANNEL_11 = 10
    CHANNEL_12 = 11
    CHANNEL_13 = 12
    CHANNEL_14 = 13
    CHANNEL_15 = 14
    CHANNEL_16 = 15


# Default channel assignment by rhythmic role
ROLE_CHANNEL_MAP: dict[RhythmicRole, MidiChannel] = {
    RhythmicRole.ROOT: MidiChannel.CHANNEL_1,
    RhythmicRole.HALFTIME: MidiChannel.CHANNEL_2,
    RhythmicRole.TRIPLET: MidiChannel.CHANNEL_3,
    RhythmicRole.WALTZ: MidiChannel.CHANNEL_4,
    RhythmicRole.COMPOUND: MidiChannel.CHANNEL_5,
    RhythmicRole.DOUBLETIME: MidiChannel.CHANNEL_6,
    RhythmicRole.OFFSET: MidiChannel.CHANNEL_7,
    RhythmicRole.QUINTUPLE: MidiChannel.CHANNEL_8,
    RhythmicRole.SEPTUPLE: MidiChannel.CHANNEL_9,
}


# GM program numbers for channel voices (0=Acoustic Grand Piano)
ROLE_PROGRAM_MAP: dict[RhythmicRole, int] = {
    RhythmicRole.ROOT: 0,       # Acoustic Grand Piano
    RhythmicRole.HALFTIME: 33,  # Electric Bass (finger)
    RhythmicRole.TRIPLET: 9,    # Glockenspiel
    RhythmicRole.WALTZ: 41,     # Violin
    RhythmicRole.COMPOUND: 49,  # String Ensemble 1
    RhythmicRole.DOUBLETIME: 25,  # Acoustic Guitar (nylon)
    RhythmicRole.OFFSET: 57,    # Trumpet
    RhythmicRole.QUINTUPLE: 74,  # Flute
    RhythmicRole.SEPTUPLE: 90,   # Pad 3 (polysynth)
}


def channel_for_role(role: RhythmicRole) -> MidiChannel:
    """Get the MIDI channel for a rhythmic role."""
    return ROLE_CHANNEL_MAP.get(role, MidiChannel.CHANNEL_1)


def program_for_role(role: RhythmicRole) -> int:
    """Get the GM program number for a rhythmic role."""
    return ROLE_PROGRAM_MAP.get(role, 0)
