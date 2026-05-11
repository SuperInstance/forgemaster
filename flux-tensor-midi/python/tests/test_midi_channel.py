"""Tests for MIDI channel mapping."""

import pytest
from flux_tensor_midi.midi.channel import (
    MidiChannel,
    channel_for_role,
    program_for_role,
    ROLE_CHANNEL_MAP,
    ROLE_PROGRAM_MAP,
)
from flux_tensor_midi.core.snap import RhythmicRole


class TestMidiChannel:
    def test_channel_values(self):
        assert MidiChannel.CHANNEL_1 == 0
        assert MidiChannel.CHANNEL_10 == 9
        assert MidiChannel.CHANNEL_16 == 15

    def test_channel_for_role(self):
        ch = channel_for_role(RhythmicRole.ROOT)
        assert ch == MidiChannel.CHANNEL_1

    def test_channel_for_halftime(self):
        ch = channel_for_role(RhythmicRole.HALFTIME)
        assert ch == MidiChannel.CHANNEL_2

    def test_channel_for_unknown_role(self):
        ch = channel_for_role(RhythmicRole.OFFSET)
        assert ch == MidiChannel.CHANNEL_7

    def test_all_roles_have_channel(self):
        for role in RhythmicRole:
            assert role in ROLE_CHANNEL_MAP

    def test_all_roles_have_program(self):
        for role in RhythmicRole:
            assert role in ROLE_PROGRAM_MAP

    def test_program_for_role(self):
        pg = program_for_role(RhythmicRole.ROOT)
        assert pg == 0  # Acoustic Grand Piano

    def test_program_for_halftime(self):
        pg = program_for_role(RhythmicRole.HALFTIME)
        assert pg == 33  # Electric Bass
