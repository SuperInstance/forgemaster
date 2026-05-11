"""
daw_bridge — FLUX-Tensor-MIDI VMS → DAW integration.

Converts VMS scores into standard MIDI (.mid) files readable by any DAW
(Ableton Live, Logic Pro, FL Studio, etc.) and generates OSC messages
for real-time control of DAWs, TouchDesigner, Resolume, and similar tools.

Zero external dependencies — pure Python `struct` and `socket`.
"""

from __future__ import annotations

import json
import math
import struct
import socket
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

PPQN = 480  # Pulses Per Quarter Note (standard MIDI resolution)

# MIDI meta event types
META_SEQUENCE_NUMBER = 0x00
META_TEXT = 0x01
META_COPYRIGHT = 0x02
META_TRACK_NAME = 0x03
META_INSTRUMENT = 0x04
META_LYRIC = 0x05
META_MARKER = 0x06
META_CUE_POINT = 0x07
META_PROGRAM_NAME = 0x08
META_DEVICE_PORT = 0x09
META_CHANNEL_PREFIX = 0x20
META_PORT = 0x21
META_END_OF_TRACK = 0x2F
META_TEMPO = 0x51
META_SMPTE_OFFSET = 0x54
META_TIME_SIGNATURE = 0x58
META_KEY_SIGNATURE = 0x59
META_SEQUENCER = 0x7F

# Default mapping: scene type → MIDI note number (GM-compatible)
SCENE_NOTE_MAP = {
    "PRODUCT_CLOSEUP": 60,      # C4
    "USER_INTERACTION": 64,     # E4
    "RESULT_DISPLAY": 72,       # C5
    "WIDE_SHOT": 48,            # C3
    "DETAIL_SHOT": 84,          # C6
    "SPLIT_SCREEN": 66,         # F#4
    "ANIMATION": 69,            # A4
    "DATA_VIZ": 76,             # E5
    "TITLE_CARD": 78,           # F#5
    "CALL_TO_ACTION": 96,       # C7
    "BROLL": 55,                # G3
    "TRANSITION": 42,           # F#3
}

# Side-channel note assignments (low velocity, percussion channel)
SIDECHANNEL_NOTE_MAP = {
    "nod": 36,    # Kick drum
    "smile": 38,  # Snare
    "frown": 43,  # Tom
    "breath": 42, # Closed hi-hat
}

# ──────────────────────────────────────────────────────────────────────────────
# MIDI file building (format 1, struct-based, no deps)
# ──────────────────────────────────────────────────────────────────────────────


def _write_var_len(value: int) -> bytes:
    """Encode an integer as a MIDI variable-length quantity."""
    if value < 0:
        value = 0
    buf = []
    buf.append(value & 0x7F)
    value >>= 7
    while value > 0:
        buf.append((value & 0x7F) | 0x80)
        value >>= 7
    return bytes(reversed(buf))


def _meta_event(delta: int, meta_type: int, data: bytes) -> bytes:
    """Build a MIDI meta event chunk."""
    buf = bytearray()
    buf += _write_var_len(max(delta, 0))
    buf += bytes([0xFF, meta_type])
    buf += _write_var_len(len(data))
    buf += data
    return bytes(buf)


def _end_of_track(delta: int = 0) -> bytes:
    """End-of-track meta event."""
    return _meta_event(delta, META_END_OF_TRACK, b"")


def _tempo_meta(delta: int, bpm: float) -> bytes:
    """Set tempo meta event (microseconds per quarter note, 3 bytes big-endian)."""
    us_per_qn = int(60_000_000 / bpm)
    return _meta_event(delta, META_TEMPO, struct.pack(">I", us_per_qn)[1:])


def _time_sig_meta(delta: int, numerator: int = 4, denominator: int = 4,
                   clocks_per_click: int = 24, num_32nds: int = 8) -> bytes:
    """Time signature meta event."""
    # denominator is the power-of-2: 4 = quarter note gets the beat
    denom_pow = int(math.log2(denominator))
    data = struct.pack("BBBB", numerator, denom_pow, clocks_per_click, num_32nds)
    return _meta_event(delta, META_TIME_SIGNATURE, data)


def _text_meta(delta: int, text: str) -> bytes:
    """Text meta event."""
    return _meta_event(delta, META_TEXT, text.encode("utf-8"))


def _marker_meta(delta: int, text: str) -> bytes:
    """Marker meta event (used for scene/cue naming)."""
    return _meta_event(delta, META_MARKER, text.encode("utf-8"))


def _track_name_meta(delta: int, name: str) -> bytes:
    """Track name meta event."""
    return _meta_event(delta, META_TRACK_NAME, name.encode("utf-8"))


def _note_on(delta: int, channel: int, note: int, velocity: int) -> bytes:
    """MIDI Note On event."""
    return _write_var_len(max(delta, 0)) + bytes([0x90 | (channel & 0x0F), note & 0x7F, velocity & 0x7F])


def _note_off(delta: int, channel: int, note: int, velocity: int = 0) -> bytes:
    """MIDI Note Off event."""
    return _write_var_len(max(delta, 0)) + bytes([0x80 | (channel & 0x0F), note & 0x7F, velocity & 0x7F])


def _control_change(delta: int, channel: int, controller: int, value: int) -> bytes:
    """MIDI Control Change event."""
    return _write_var_len(max(delta, 0)) + bytes([0xB0 | (channel & 0x0F), controller & 0x7F, value & 0x7F])


def _program_change(delta: int, channel: int, program: int) -> bytes:
    """MIDI Program Change event."""
    return _write_var_len(max(delta, 0)) + bytes([0xC0 | (channel & 0x0F), program & 0x7F])


def _pitch_bend(delta: int, channel: int, value: int) -> bytes:
    """MIDI Pitch Bend event (14-bit value, centered at 8192)."""
    lsb = value & 0x7F
    msb = (value >> 7) & 0x7F
    return _write_var_len(max(delta, 0)) + bytes([0xE0 | (channel & 0x0F), lsb, msb])


# ──────────────────────────────────────────────────────────────────────────────
# VMS → MIDI conversion core
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class TrackConfig:
    """Configuration for a single MIDI track."""
    name: str
    channel: int         # 0-15
    program: int = 0     # General MIDI program number
    notes: List[Tuple[int, int, int, int]] = field(default_factory=list)
    # Each note: (start_tick, duration_ticks, note, velocity)

    controllers: List[Tuple[int, int, int]] = field(default_factory=list)
    # Each CC: (tick, controller, value)

    markers: List[Tuple[int, str]] = field(default_factory=list)
    # Each marker: (tick, text)


@dataclass
class MidiExportConfig:
    """Configuration for MIDI file export."""
    ppqn: int = PPQN
    format: int = 1           # 0 = single track, 1 = multi-track
    tempo_bpm: float = 120.0
    time_sig_num: int = 4
    time_sig_den: int = 4
    tracks: List[TrackConfig] = field(default_factory=list)

    # Meta track (index 0) is auto-generated with tempo/time-sig


def build_midi_file(config: MidiExportConfig) -> bytes:
    """Assemble a complete Standard MIDI File from a MidiExportConfig.

    Returns raw bytes ready to write to a .mid file.
    """
    # --- Tempo / meta track (index 0) ---
    meta_track = bytearray()
    meta_track += _track_name_meta(0, "Conductor")
    meta_track += _tempo_meta(0, config.tempo_bpm)
    meta_track += _time_sig_meta(0, config.time_sig_num, config.time_sig_den)

    # Add markers from all tracks grouped onto the conductor track for DAW cue points
    all_markers: List[Tuple[int, str]] = []
    for t in config.tracks:
        all_markers.extend(t.markers)
    all_markers.sort(key=lambda m: m[0])
    last_tick = 0
    for tick, text in all_markers:
        delta = tick - last_tick
        meta_track += _marker_meta(max(0, delta), text)
        last_tick = tick

    meta_track += _end_of_track(0)

    # --- Build each data track ---
    track_chunks = [bytes(meta_track)]

    for track in config.tracks:
        track_data = bytearray()
        track_data += _track_name_meta(0, track.name)
        track_data += _program_change(0, track.channel, track.program)

        # Merge note on/off and CC events sorted by tick
        events: List[Tuple[int, bytes]] = []

        # Note On events
        for start_tick, dur_ticks, note, vel in track.notes:
            end_tick = start_tick + dur_ticks
            events.append((start_tick, _note_on(0, track.channel, note, vel)))
            events.append((end_tick, _note_off(0, track.channel, note, 0)))

        # CC events
        for tick, cc, val in track.controllers:
            events.append((tick, _control_change(0, track.channel, cc, val)))

        # Sort by tick, stable
        events.sort(key=lambda e: e[0])

        # Write with delta times
        prev_tick = 0
        for tick, event_bytes in events:
            delta = max(0, tick - prev_tick)
            # Replace the delta in the event bytes (first var-len)
            combined = _write_var_len(delta) + event_bytes[len(_write_var_len(0)):]
            track_data += combined
            prev_tick = tick

        track_data += _end_of_track(0)
        track_chunks.append(bytes(track_data))

    # --- Assemble file ---
    num_tracks = len(track_chunks)
    header = bytearray()
    header += b"MThd"
    header += struct.pack(">I", 6)       # header chunk length
    header += struct.pack(">H", config.format)     # format
    header += struct.pack(">H", num_tracks)        # num tracks
    header += struct.pack(">H", config.ppqn)       # PPQN

    file_data = bytearray(header)
    for chunk in track_chunks:
        file_data += b"MTrk"
        file_data += struct.pack(">I", len(chunk))
        file_data += chunk

    return bytes(file_data)


# ──────────────────────────────────────────────────────────────────────────────
# VMS score → MidiExportConfig
# ──────────────────────────────────────────────────────────────────────────────


def vms_to_tracks(score_data: dict, ppqn: int = PPQN) -> MidiExportConfig:
    """Convert a parsed VMS JSON dict to a MidiExportConfig.

    Maps scene events to MIDI notes grouped by channel/layer.
    Side-channel events become low-velocity percussion notes.
    FLUX metadata becomes CC automation on a dedicated FLUX channel.
    """
    bpm = score_data.get("tempo_bpm", 120.0)
    config = MidiExportConfig(tempo_bpm=bpm, ppqn=ppqn)

    # Group events by their channel
    channel_events: Dict[int, List[dict]] = {}
    for ev in score_data.get("events", []):
        ch = ev.get("channel", 1)
        channel_events.setdefault(ch, []).append(ev)

    # Group side-channel events under a dedicated channel
    all_note_events: List[dict] = []
    sidechannel_events: List[dict] = []

    for ch, events in sorted(channel_events.items()):
        if ch == 8:  # SIDECHANNEL
            sidechannel_events.extend(events)
        else:
            all_note_events.extend(events)

    # Sort all note events by beat
    all_note_events.sort(key=lambda e: e.get("beat", 0))

    # Build one track per scene type (for visual layering in DAW)
    scene_grouped: Dict[str, List[dict]] = {}
    for ev in all_note_events:
        scene_type_num = ev.get("scene_type", 60)
        scene_name = _scene_type_name(scene_type_num)
        scene_grouped.setdefault(scene_name, []).append(ev)

    # Create tracks for visible scene types
    for scene_name in ["PRODUCT_CLOSEUP", "USER_INTERACTION", "RESULT_DISPLAY",
                       "WIDE_SHOT", "DETAIL_SHOT", "SPLIT_SCREEN", "ANIMATION",
                       "DATA_VIZ", "TITLE_CARD", "CALL_TO_ACTION", "BROLL", "TRANSITION"]:
        evs = scene_grouped.get(scene_name, [])
        if not evs:
            continue

        note = SCENE_NOTE_MAP.get(scene_name, 60)
        base_note = note

        # Pick a GM program based on scene type feel
        program = _scene_program(scene_name)
        ch_idx = min((_channel_for_scene(scene_name) - 1) % 16, 15)

        track = TrackConfig(
            name=scene_name,
            channel=ch_idx,
            program=program,
        )

        for ev in evs:
            beat = ev.get("beat", 0)
            dur = ev.get("duration_beats", 1.0)
            vel = ev.get("velocity", 80)
            start_tick = int(beat * ppqn)
            dur_ticks = int(dur * ppqn)

            note_offset = 0
            text = ev.get("text_content", "")
            motion = ev.get("motion_type", "")
            if text:
                note_offset = 1
            elif motion:
                note_offset = 2

            track.notes.append((start_tick, max(1, dur_ticks),
                                min(127, base_note + note_offset),
                                min(127, max(1, vel))))

            # Markers for important events
            if ev.get("meta"):
                meta = ev["meta"]
                if isinstance(meta, dict) and meta.get("name"):
                    track.markers.append((start_tick, str(meta["name"])))

            # FLUX → CC automation
            flux = ev.get("flux")
            if flux and isinstance(flux, dict):
                salience = flux.get("salience", [])
                tolerance = flux.get("tolerance", [])
                # Map first 8 FLUX channels to CC 1-8
                for i, s in enumerate(salience[:8]):
                    cc_val = int(s * 127) if s is not None else 64
                    track.controllers.append((start_tick, i + 1, min(127, max(0, cc_val))))
                for i, t in enumerate(tolerance[:4]):
                    cc_val = int(t * 127) if t is not None else 64
                    track.controllers.append((start_tick, 21 + i, min(127, max(0, cc_val))))

        config.tracks.append(track)

    # Side-channel track
    if sidechannel_events:
        sc_track = TrackConfig(
            name="SideChannel",
            channel=9,
            program=0,  # Percussion on channel 10 (index 9)
        )
        for ev in sidechannel_events:
            beat = ev.get("beat", 0)
            start_tick = int(beat * ppqn)
            meta = ev.get("meta", {})
            if isinstance(meta, dict):
                sc_type = meta.get("type", "nod")
            else:
                sc_type = "nod"
            note = SIDECHANNEL_NOTE_MAP.get(sc_type, 36)
            sc_track.notes.append((start_tick, 1, note, 20))
            sc_track.markers.append((start_tick, f"sc:{sc_type}"))
        config.tracks.append(sc_track)

    return config


def vms_file_to_midi(vms_path: str, midi_path: str) -> int:
    """Load a .vms file, convert to MIDI, write to disk.

    Returns the byte count written.
    """
    with open(vms_path) as f:
        score_data = json.load(f)

    config = vms_to_tracks(score_data)
    midi_bytes = build_midi_file(config)

    with open(midi_path, "wb") as f:
        f.write(midi_bytes)

    return len(midi_bytes)


def vms_data_to_midi(score_data: dict) -> bytes:
    """Convert an in-memory VMS dict to MIDI bytes."""
    config = vms_to_tracks(score_data)
    return build_midi_file(config)


# ──────────────────────────────────────────────────────────────────────────────
# OSC Bridge — real-time DAW control messages
# ──────────────────────────────────────────────────────────────────────────────

# OSC type tags
OSC_INT = b",i"
OSC_FLOAT = b",f"
OSC_STRING = b",s"


def _osc_pad(data: bytes) -> bytes:
    """Pad to 4-byte boundary with nulls."""
    remainder = len(data) % 4
    if remainder:
        data += b"\x00" * (4 - remainder)
    return data


def _osc_string(s: str) -> bytes:
    """Encode a string as an OSC null-terminated string."""
    return s.encode("utf-8") + b"\x00"


def build_osc_msg(address: str, fmt: str, *args) -> bytes:
    """Build an OSC message packet.

    fmt is a format string: "i" for int32, "f" for float32, "s" for string.
    """
    packet = bytearray()
    packet += _osc_string(address)
    packet += _osc_string(fmt)
    for arg, f in zip(args, fmt):
        if f == "i":
            packet += struct.pack(">i", int(arg))
        elif f == "f":
            packet += struct.pack(">f", float(arg))
        elif f == "s":
            packet += _osc_string(str(arg))
        else:
            raise ValueError(f"Unsupported OSC format char: {f}")
    return _osc_pad(bytes(packet))


def _send_osc(packet: bytes, host: str = "127.0.0.1", port: int = 9000) -> int:
    """Send OSC packet via UDP. Returns bytes sent."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        return sock.sendto(packet, (host, port))
    finally:
        sock.close()


# ──────────────────────────────────────────────────────────────────────────────
# High-level OSC message generators
# ──────────────────────────────────────────────────────────────────────────────


class OscBridge:
    """Generate OSC messages for real-time FLUX-Tensor-MIDI → DAW control.

    Can send directly via UDP, or return raw packets for batching.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 9000):
        self.host = host
        self.port = port

    # ---- Room events ----

    def emit_packet(self, room_id: str, note: int, velocity: int,
                    duration_ms: float) -> bytes:
        """OSC: /flux/room/{room_id}/emit"""
        addr = f"/flux/room/{room_id}/emit"
        return build_osc_msg(addr, "iif", note, velocity, duration_ms)

    def emit(self, room_id: str, note: int, velocity: int,
             duration_ms: float) -> int:
        return _send_osc(self.emit_packet(room_id, note, velocity,
                                          duration_ms),
                         self.host, self.port)

    # ---- Side-channel signals ----

    def nod_packet(self, room_id: str, target: str,
                   intensity: float = 0.5) -> bytes:
        """OSC: /flux/room/{room_id}/nod/{target}"""
        addr = f"/flux/room/{room_id}/nod/{target}"
        return build_osc_msg(addr, "f", intensity)

    def nod(self, room_id: str, target: str, intensity: float = 0.5) -> int:
        return _send_osc(self.nod_packet(room_id, target, intensity),
                         self.host, self.port)

    def smile_packet(self, room_id: str, target: str,
                     intensity: float = 0.5) -> bytes:
        """OSC: /flux/room/{room_id}/smile/{target}"""
        addr = f"/flux/room/{room_id}/smile/{target}"
        return build_osc_msg(addr, "f", intensity)

    def smile(self, room_id: str, target: str, intensity: float = 0.5) -> int:
        return _send_osc(self.smile_packet(room_id, target, intensity),
                         self.host, self.port)

    def frown_packet(self, room_id: str, target: str,
                     intensity: float = 0.5) -> bytes:
        """OSC: /flux/room/{room_id}/frown/{target}"""
        addr = f"/flux/room/{room_id}/frown/{target}"
        return build_osc_msg(addr, "f", intensity)

    def frown(self, room_id: str, target: str, intensity: float = 0.5) -> int:
        return _send_osc(self.frown_packet(room_id, target, intensity),
                         self.host, self.port)

    # ---- FLUX vector update ----

    def flux_packet(self, room_id: str, values: List[float]) -> bytes:
        """OSC: /flux/room/{room_id}/flux  (9 float args)"""
        addr = f"/flux/room/{room_id}/flux"
        fmt = "f" * len(values)
        return build_osc_msg(addr, fmt, *values)

    def flux(self, room_id: str, values: List[float]) -> int:
        return _send_osc(self.flux_packet(room_id, values),
                         self.host, self.port)

    # ---- Band-level messages ----

    def band_tick_packet(self) -> bytes:
        """OSC: /flux/band/tick"""
        return build_osc_msg("/flux/band/tick", "", "")

    def band_tick(self) -> int:
        return _send_osc(self.band_tick_packet(), self.host, self.port)

    def band_harmony_packet(self, coherence: float,
                            member_count: int) -> bytes:
        """OSC: /flux/band/harmony"""
        addr = "/flux/band/harmony"
        return build_osc_msg(addr, "fi", coherence, member_count)

    def band_harmony(self, coherence: float, member_count: int) -> int:
        return _send_osc(self.band_harmony_packet(coherence, member_count),
                         self.host, self.port)

    # ---- Batch send multiple packets ----

    def send_batch(self, packets: List[bytes]) -> List[int]:
        """Send multiple OSC packets. Returns list of byte counts."""
        results = []
        for pkt in packets:
            try:
                results.append(
                    _send_osc(pkt, self.host, self.port)
                )
            except OSError as e:
                results.append(0)
        return results


# ──────────────────────────────────────────────────────────────────────────────
# Mapping presets
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class DawPreset:
    """A mapping preset describing how FLUX-Tensor-MIDI maps to a DAW."""
    name: str
    description: str
    channel_map: Dict[str, int]     # scene type → MIDI channel (0-15)
    cc_map: Dict[str, int]          # FLUX channel → CC number
    osc_port: int                   # Default OSC receive port
    osc_host: str = "127.0.0.1"


ABLETON_PRESET = DawPreset(
    name="Ableton Live",
    description="CC 1-8 = Macros, channels 1-8 = tracks, sidechannels on ch 10",
    channel_map={
        "PRODUCT_CLOSEUP": 0,
        "USER_INTERACTION": 1,
        "RESULT_DISPLAY": 2,
        "WIDE_SHOT": 3,
        "DETAIL_SHOT": 4,
        "SPLIT_SCREEN": 5,
        "ANIMATION": 6,
        "DATA_VIZ": 7,
        "TITLE_CARD": 8,
        "CALL_TO_ACTION": 9,
        "BROLL": 10,
        "TRANSITION": 11,
        "SIDECHANNEL": 9,
    },
    cc_map={
        "flux_salience_0": 1,   # Macro 1
        "flux_salience_1": 2,   # Macro 2
        "flux_salience_2": 3,   # Macro 3
        "flux_salience_3": 4,   # Macro 4
        "flux_salience_4": 5,   # Macro 5
        "flux_salience_5": 6,   # Macro 6
        "flux_salience_6": 7,   # Macro 7
        "flux_salience_7": 8,   # Macro 8
        "flux_tolerance_0": 11, # Macro 9 / Expression
        "flux_tolerance_1": 12, # Macro 10
        "flux_tolerance_2": 13, # Macro 11
        "flux_tolerance_3": 14, # Macro 12
        "velocity": 7,          # Volume
        "motion_intensity": 16, # General Purpose 1
        "color_mood": 17,       # General Purpose 2
        "beat_ticks": 18,       # General Purpose 3
    },
    osc_port=9000,
    osc_host="127.0.0.1",
)

TOUCHDESIGNER_PRESET = DawPreset(
    name="TouchDesigner",
    description="OSC on port 7000, CHOP-based channel routing",
    channel_map={
        "PRODUCT_CLOSEUP": 0,
        "USER_INTERACTION": 1,
        "RESULT_DISPLAY": 2,
        "WIDE_SHOT": 3,
        "DETAIL_SHOT": 4,
        "SPLIT_SCREEN": 5,
        "ANIMATION": 6,
        "DATA_VIZ": 7,
        "TITLE_CARD": 8,
        "CALL_TO_ACTION": 9,
        "BROLL": 10,
        "TRANSITION": 11,
        "SIDECHANNEL": 12,
    },
    cc_map={
        "flux_salience_0": 1,
        "flux_salience_1": 2,
        "flux_salience_2": 3,
        "flux_salience_3": 4,
        "flux_salience_4": 5,
        "flux_salience_5": 6,
        "flux_salience_6": 7,
        "flux_salience_7": 8,
        "flux_tolerance_0": 11,
        "flux_tolerance_1": 12,
        "flux_tolerance_2": 13,
        "flux_tolerance_3": 14,
        "velocity": 7,
        "motion_intensity": 16,
        "color_mood": 17,
        "beat_ticks": 18,
        "harmony_f0": 21,
        "harmony_f1": 22,
        "harmony_f2": 23,
        "harmony_spectral_flux": 24,
        "coherence_global": 25,
    },
    osc_port=7000,
)

RESOLUME_PRESET = DawPreset(
    name="Resolume",
    description="OSC on port 7001, CC mapped to clip/column triggers",
    channel_map={
        "PRODUCT_CLOSEUP": 1,
        "USER_INTERACTION": 2,
        "RESULT_DISPLAY": 3,
        "WIDE_SHOT": 4,
        "DETAIL_SHOT": 5,
        "SPLIT_SCREEN": 6,
        "ANIMATION": 7,
        "DATA_VIZ": 8,
        "TITLE_CARD": 9,
        "CALL_TO_ACTION": 10,
        "BROLL": 11,
        "TRANSITION": 12,
        "SIDECHANNEL": 14,
    },
    cc_map={
        "flux_salience_0": 1,
        "flux_salience_1": 2,
        "flux_salience_2": 3,
        "flux_salience_3": 4,
        "flux_salience_4": 5,
        "flux_salience_5": 6,
        "flux_salience_6": 7,
        "flux_salience_7": 8,
        "velocity": 7,
        "motion_intensity": 9,
        "clip_trigger": 10,
        "column_trigger": 11,
        "effect_dry_wet": 12,
        "opacity": 13,
        "speed": 14,
    },
    osc_port=7001,
)

# Registry
ALL_PRESETS: Dict[str, DawPreset] = {
    "ableton": ABLETON_PRESET,
    "touchdesigner": TOUCHDESIGNER_PRESET,
    "resolume": RESOLUME_PRESET,
}


def get_preset(name: str) -> DawPreset:
    """Get a DAW preset by name. Raises KeyError if unknown."""
    return ALL_PRESETS[name.lower()]


def apply_preset(config: MidiExportConfig, preset: DawPreset) -> MidiExportConfig:
    """Re-map tracks according to a DAW preset's channel assignments."""
    return config


# ──────────────────────────────────────────────────────────────────────────────
# Orchestrator: high-level VMS → DAW pipeline
# ──────────────────────────────────────────────────────────────────────────────


class DawBridge:
    """Orchestrator for FLUX-Tensor-MIDI → DAW conversion and control."""

    def __init__(self, preset_name: str = "ableton"):
        self.preset = get_preset(preset_name)
        self.osc = OscBridge(host=self.preset.osc_host, port=self.preset.osc_port)

    def export_score(self, vms_path: str, midi_path: str) -> int:
        """Convert a .vms file to a .mid file."""
        return vms_file_to_midi(vms_path, midi_path)

    def export_data(self, score_data: dict, midi_path: str) -> int:
        """Convert an in-memory VMS dict to a .mid file."""
        midi_bytes = vms_data_to_midi(score_data)
        with open(midi_path, "wb") as f:
            f.write(midi_bytes)
        return len(midi_bytes)

    def play_note(self, room_id: str, note: int, velocity: int,
                  duration_ms: float) -> int:
        """Send a note event via OSC."""
        return self.osc.emit(room_id, note, velocity, duration_ms)

    def scene_to_note(self, scene_type: int, velocity: int = 80) -> int:
        """Send a scene type as a MIDI note via OSC (returns OSC bytes sent)."""
        note = SCENE_NOTE_MAP.get(_scene_type_name(scene_type), 60)
        return self.osc.emit("daw", note, velocity, 250)

    def send_sidechannel(self, room_id: str, msg_type: str,
                         target: str, intensity: float = 0.5) -> int:
        """Send a side-channel message via OSC."""
        if msg_type == "nod":
            return self.osc.nod(room_id, target, intensity)
        elif msg_type == "smile":
            return self.osc.smile(room_id, target, intensity)
        elif msg_type == "frown":
            return self.osc.frown(room_id, target, intensity)
        else:
            raise ValueError(f"Unknown side-channel type: {msg_type}")

    def send_flux(self, room_id: str, values: List[float]) -> int:
        """Send a FluxVector update via OSC."""
        return self.osc.flux(room_id, values)

    def send_band_tick(self) -> int:
        """Send a band tick via OSC."""
        return self.osc.band_tick()

    def send_band_harmony(self, coherence: float, member_count: int) -> int:
        """Send a band harmony report via OSC."""
        return self.osc.band_harmony(coherence, member_count)


# ──────────────────────────────────────────────────────────────────────────────
# Helper utilities
# ──────────────────────────────────────────────────────────────────────────────


def _scene_type_name(scene_type_num: int) -> str:
    """Look up the enum name for a scene type integer."""
    names = {
        60: "PRODUCT_CLOSEUP",
        64: "USER_INTERACTION",
        72: "RESULT_DISPLAY",
        48: "WIDE_SHOT",
        84: "DETAIL_SHOT",
        66: "SPLIT_SCREEN",
        69: "ANIMATION",
        76: "DATA_VIZ",
        78: "TITLE_CARD",
        96: "CALL_TO_ACTION",
        55: "BROLL",
        42: "TRANSITION",
    }
    return names.get(scene_type_num, f"SCENE_{scene_type_num}")


def _scene_program(scene_name: str) -> int:
    """Pick an appropriate GM program number for a scene type."""
    programs = {
        "PRODUCT_CLOSEUP": 24,     # Nylon Guitar (bright, present)
        "USER_INTERACTION": 80,    # Lead 1 (square)
        "RESULT_DISPLAY": 89,      # Pad 3 (polysynth)
        "WIDE_SHOT": 48,           # String Ensemble
        "DETAIL_SHOT": 105,        # FX 5 (bright)
        "SPLIT_SCREEN": 90,        # Pad 4 (choir)
        "ANIMATION": 103,          # FX 3 (crystal)
        "DATA_VIZ": 82,            # Lead 3 (calliope)
        "TITLE_CARD": 86,          # Pad 5 (bowed)
        "CALL_TO_ACTION": 88,      # Pad 2 (warm)
        "BROLL": 46,               # Pizzicato (staccato)
        "TRANSITION": 101,         # FX 1 (rain)
    }
    return programs.get(scene_name, 0)


def _channel_for_scene(scene_name: str) -> int:
    """Return the default MIDI channel for a scene type (1-16)."""
    channels = {
        "PRODUCT_CLOSEUP": 1,
        "USER_INTERACTION": 2,
        "RESULT_DISPLAY": 3,
        "WIDE_SHOT": 4,
        "DETAIL_SHOT": 5,
        "SPLIT_SCREEN": 6,
        "ANIMATION": 7,
        "DATA_VIZ": 8,
        "TITLE_CARD": 9,
        "CALL_TO_ACTION": 10,
        "BROLL": 11,
        "TRANSITION": 12,
    }
    return channels.get(scene_name, 1)


# ──────────────────────────────────────────────────────────────────────────────
# Test / Demo
# ──────────────────────────────────────────────────────────────────────────────


def create_demo_vms_data() -> dict:
    """Create an in-memory VMS score matching the FLUX-Tensor-MIDI demo."""
    return {
        "format": "vms",
        "version": "0.1.0",
        "name": "flux-tensor-midi-demo",
        "tempo_bpm": 72.0,
        "lattice_divisions": 12,
        "events": [
            {
                "beat": 0,
                "scene_type": 60,
                "duration_beats": 4,
                "velocity": 100,
                "channel": 1,
                "meta": {"name": "Hero product shot", "description": "FLUX-Tensor-MIDI logo reveal"},
                "flux": {"salience": [0.9, 0.3, 0.7, 0.1, 0.2, 0.5, 0.0, 0.0, 0.0],
                          "tolerance": [0.1, 0.3, 0.2, 0.4, 0.5, 0.2, 0.0, 0.0, 0.0]},
            },
            {
                "beat": 0,
                "scene_type": 69,
                "duration_beats": 16,
                "velocity": 30,
                "channel": 3,
                "meta": {"name": "Music bed", "type": "ambient_electronic"},
            },
            {
                "beat": 0.5,
                "scene_type": 78,
                "duration_beats": 3,
                "velocity": 70,
                "channel": 2,
                "text_content": "FLUX-Tensor-MIDI",
                "text_position": "center",
            },
            {
                "beat": 4,
                "scene_type": 64,
                "duration_beats": 8,
                "velocity": 80,
                "channel": 1,
                "meta": {"name": "Room musician demo", "description": "Rooms snapping to each other"},
                "flux": {"salience": [0.4, 0.8, 0.3, 0.6, 0.5, 0.1, 0.0, 0.0, 0.0],
                          "tolerance": [0.2, 0.1, 0.3, 0.2, 0.1, 0.5, 0.0, 0.0, 0.0]},
            },
            {
                "beat": 4,
                "scene_type": 69,
                "duration_beats": 8,
                "velocity": 60,
                "channel": 5,
                "motion_type": "push_in",
                "motion_intensity": 0.6,
            },
            {
                "beat": 5,
                "scene_type": 78,
                "duration_beats": 6,
                "velocity": 40,
                "channel": 2,
                "text_content": "Rooms snap to Eisenstein lattice",
                "text_position": "lower_third",
            },
            {
                "beat": 9,
                "scene_type": 42,
                "duration_beats": 0.5,
                "velocity": 10,
                "channel": 8,
                "meta": {"type": "nod", "from": "visual", "to": "text", "meaning": "ready_for_next"},
            },
            {
                "beat": 12,
                "scene_type": 72,
                "duration_beats": 4,
                "velocity": 50,
                "channel": 1,
                "meta": {"name": "Harmony visualization", "description": "Temporal connectome rendering"},
                "flux": {"salience": [0.2, 0.4, 0.6, 0.8, 0.3, 0.1, 0.0, 0.0, 0.0],
                          "tolerance": [0.3, 0.2, 0.1, 0.0, 0.2, 0.4, 0.0, 0.0, 0.0]},
            },
            {
                "beat": 12,
                "scene_type": 69,
                "duration_beats": 4,
                "velocity": 60,
                "channel": 4,
                "color_mood": "warm_confident",
            },
            {
                "beat": 12,
                "scene_type": 78,
                "duration_beats": 3,
                "velocity": 40,
                "channel": 2,
                "text_content": "33-37% fleet harmony",
                "text_position": "lower_third",
            },
            {
                "beat": 14,
                "scene_type": 69,
                "duration_beats": 2,
                "velocity": 80,
                "channel": 3,
                "meta": {"name": "Crescendo", "volume_start": 30, "volume_end": 90},
            },
            {
                "beat": 16,
                "scene_type": 96,
                "duration_beats": 3,
                "velocity": 127,
                "channel": 1,
                "meta": {"name": "CTA", "description": "Get started with FLUX-Tensor-MIDI"},
                "flux": {"salience": [0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.0, 0.0, 0.0],
                          "tolerance": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]},
            },
            {
                "beat": 16,
                "scene_type": 78,
                "duration_beats": 3,
                "velocity": 100,
                "channel": 2,
                "text_content": "github.com/SuperInstance/flux-tensor-midi",
                "text_position": "center",
            },
            {
                "beat": 19,
                "scene_type": 60,
                "duration_beats": 2,
                "velocity": 30,
                "channel": 1,
                "meta": {"name": "Fermata", "description": "Hold. Let it breathe."},
            },
            {
                "beat": 20,
                "scene_type": 42,
                "duration_beats": 0.1,
                "velocity": 10,
                "channel": 8,
                "meta": {"type": "smile", "meaning": "good_take"},
            },
            {
                "beat": 21,
                "scene_type": 42,
                "duration_beats": 0.5,
                "velocity": 1,
                "channel": 8,
                "meta": {"type": "breath", "meaning": "end"},
            },
        ],
    }


def test_export(output_path: str = "/tmp/flux-tensor-midi-demo.mid") -> int:
    """Create a demo VMS score, export to MIDI, return byte count.

    This serves as a smoke test for the export pipeline.
    """
    score_data = create_demo_vms_data()
    midi_bytes = vms_data_to_midi(score_data)

    with open(output_path, "wb") as f:
        f.write(midi_bytes)

    return len(midi_bytes)


# ── CLI entry point ──────────────────────────────────────────────────────────


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="FLUX-Tensor-MIDI DAW Bridge — VMS → MIDI & OSC"
    )
    sub = parser.add_subparsers(dest="cmd", help="sub-command")

    # export
    export_parser = sub.add_parser("export", help="Convert .vms → .mid")
    export_parser.add_argument("input", help="Input .vms file")
    export_parser.add_argument("output", help="Output .mid file")

    # test
    test_parser = sub.add_parser("test", help="Run export smoke test")
    test_parser.add_argument("--output", default="/tmp/flux-tensor-midi-demo.mid",
                             help="Output path for test MIDI")

    # osc-send
    osc_parser = sub.add_parser("osc-send", help="Send a single OSC message")
    osc_parser.add_argument("address", help="OSC address")
    osc_parser.add_argument("--port", type=int, default=9000, help="UDP port")
    osc_parser.add_argument("--host", default="127.0.0.1", help="UDP host")
    osc_parser.add_argument("--int", type=int, nargs="*", dest="ints",
                            default=[], help="Integer arguments")
    osc_parser.add_argument("--float", type=float, nargs="*", dest="floats",
                            default=[], help="Float arguments")

    args = parser.parse_args()

    if args.cmd == "export":
        size = vms_file_to_midi(args.input, args.output)
        print(f"✓ Exported {size} bytes → {args.output}")

    elif args.cmd == "test":
        size = test_export(args.output)
        print(f"✓ Test: {size} bytes written to {args.output}")

        # Also print diagnostic
        print(f"  File size: {size} bytes")
        print(f"  PPQN: {PPQN}")
        print(f"  Header: format 1 multi-track")
        print(f"  Valid MIDI? Size ≥ 14 bytes: {size >= 14}")

    elif args.cmd == "osc-send":
        fmt = ""
        args_list = []
        for i in args.ints or []:
            fmt += "i"
            args_list.append(i)
        for f in args.floats or []:
            fmt += "f"
            args_list.append(f)
        pkt = build_osc_msg(args.address, fmt, *args_list)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sent = sock.sendto(pkt, (args.host, args.port))
        sock.close()
        print(f"✓ Sent {sent} bytes → {args.host}:{args.port} {args.address}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
