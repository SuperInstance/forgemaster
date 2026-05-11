"""
MIDI modules.
"""

from flux_tensor_midi.midi.events import MidiEvent, NoteName
from flux_tensor_midi.midi.clock import MidiClock
from flux_tensor_midi.midi.channel import (
    MidiChannel,
    ROLE_CHANNEL_MAP,
    ROLE_PROGRAM_MAP,
    channel_for_role,
    program_for_role,
)

__all__ = [
    "MidiEvent",
    "NoteName",
    "MidiClock",
    "MidiChannel",
    "ROLE_CHANNEL_MAP",
    "ROLE_PROGRAM_MAP",
    "channel_for_role",
    "program_for_role",
]
