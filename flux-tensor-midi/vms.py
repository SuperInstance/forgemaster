#!/usr/bin/env python3
"""
vms — Video-as-Music-Score encoder/decoder.

Encodes video mockups as MIDI scores with FLUX metadata.
Time is first-class. Every cut is a beat. Every scene is a note.

Usage:
    # Create a video score
    python vms.py create demo --tempo 72 --lattice E12
    
    # Export to standard MIDI
    python vms.py export demo.vms demo.mid
    
    # Render score to JSON timeline
    python vms.py render demo.vms demo_timeline.json
    
    # Analyze temporal structure
    python vms.py analyze demo.vms
"""

import json
import math
import struct
import sys
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional, Tuple


# ── Constants ─────────────────────────────────────────────────────────────────

PPQN = 480  # Pulses per quarter note (standard MIDI)
SQRT3 = math.sqrt(3)

# Scene type → MIDI pitch mapping
class SceneType(IntEnum):
    PRODUCT_CLOSEUP = 60   # C4 — the "home" note
    USER_INTERACTION = 64  # E4
    RESULT_DISPLAY = 72    # C5
    WIDE_SHOT = 48         # C3
    DETAIL_SHOT = 84       # C6
    SPLIT_SCREEN = 66      # F#4
    ANIMATION = 69         # A4
    DATA_VIZ = 76          # E5
    TITLE_CARD = 78        # F#5
    CALL_TO_ACTION = 96    # C7 — highest priority
    BROLL = 55             # G3 — supporting
    TRANSITION = 42         # F#3 - between scenes

# Channel assignments
class Channel(IntEnum):
    VISUAL = 1
    TEXT = 2
    AUDIO = 3
    COLOR = 4
    MOTION = 5
    EFFECTS = 6
    DATA = 7
    SIDECHANNEL = 8
    META = 9

# Side-channel pitches
class SideChannel(IntEnum):
    NOD = 1      # Ready to hand off
    SMILE = 2    # Affirmation
    FROWN = 3    # Delta detected
    BREATH = 4   # About to act


# ── Core Types ────────────────────────────────────────────────────────────────

@dataclass
class FluxState:
    """FLUX 9-channel state for a scene/beat."""
    salience: List[float] = field(default_factory=lambda: [0.5] * 9)
    tolerance: List[float] = field(default_factory=lambda: [0.5] * 9)
    
    def to_dict(self) -> dict:
        return {"salience": self.salience, "tolerance": self.tolerance}
    
    @staticmethod
    def from_dict(d: dict) -> 'FluxState':
        return FluxState(
            salience=d.get("salience", [0.5] * 9),
            tolerance=d.get("tolerance", [0.5] * 9),
        )


@dataclass
class SceneEvent:
    """A scene/note in the video score."""
    beat: float                    # Position in beats (fractional OK)
    scene_type: SceneType          # What kind of scene
    duration_beats: float          # How many beats this scene lasts
    velocity: int = 80             # Intensity [1-127]
    channel: int = Channel.VISUAL  # Which production layer
    meta: Dict[str, Any] = field(default_factory=dict)
    flux: Optional[FluxState] = None
    
    # Text-specific
    text_content: str = ""
    text_position: str = "center"
    
    # Motion-specific
    motion_type: str = ""          # "push_in", "pan_left", "zoom", etc.
    motion_intensity: float = 0.5
    
    # Color-specific
    color_mood: str = ""           # "warm", "cool", "dramatic", "neutral"
    
    # Effect-specific
    effect_type: str = ""          # "fade", "dissolve", "wipe", "particle"
    
    def to_beat_ticks(self, ppqn: int = PPQN) -> int:
        return int(self.beat * ppqn)
    
    def duration_ticks(self, ppqn: int = PPQN) -> int:
        return int(self.duration_beats * ppqn)


@dataclass  
class EisensteinLattice:
    """Eisenstein snap lattice for rhythmic quantization."""
    divisions: int = 12  # E12 = 12 divisions per beat
    
    def snap(self, beat: float) -> float:
        """Snap a beat position to the nearest lattice point."""
        grid = 1.0 / self.divisions
        return round(beat / grid) * grid
    
    def snap_delta(self, beat: float) -> float:
        """How far off the beat is from its snap point."""
        return beat - self.snap(beat)
    
    def nearest_grid_points(self, beat: float, n: int = 3) -> List[float]:
        """Return the N nearest lattice points."""
        grid = 1.0 / self.divisions
        base = round(beat / grid)
        return [(base + i) * grid for i in range(-(n//2), n//2 + 1)]


@dataclass
class VideoScore:
    """A complete video encoded as a MIDI-like score."""
    name: str
    tempo_bpm: float = 72.0        # Default: upbeat modern
    lattice: EisensteinLattice = field(default_factory=lambda: EisensteinLattice(12))
    events: List[SceneEvent] = field(default_factory=list)
    
    def add_scene(self, event: SceneEvent, snap: bool = True) -> SceneEvent:
        """Add a scene, optionally snapping to the beat grid."""
        if snap:
            event.beat = self.lattice.snap(event.beat)
        self.events.append(event)
        return event
    
    def duration_seconds(self) -> float:
        """Total duration in seconds."""
        if not self.events:
            return 0.0
        last_end = max(e.beat + e.duration_beats for e in self.events)
        return last_end * (60.0 / self.tempo_bpm)
    
    def duration_beats(self) -> float:
        if not self.events:
            return 0.0
        return max(e.beat + e.duration_beats for e in self.events)
    
    def events_at_beat(self, beat: float, tolerance: float = 0.01) -> List[SceneEvent]:
        """Get all events at a given beat."""
        return [e for e in self.events if abs(e.beat - beat) < tolerance]
    
    def events_in_range(self, start: float, end: float) -> List[SceneEvent]:
        """Get all events overlapping [start, end) in beats."""
        return [e for e in self.events 
                if e.beat < end and (e.beat + e.duration_beats) > start]
    
    def channel_events(self, channel: int) -> List[SceneEvent]:
        return [e for e in self.events if e.channel == channel]
    
    def beat_map(self) -> Dict[float, List[SceneEvent]]:
        """Group events by beat position."""
        result: Dict[float, List[SceneEvent]] = {}
        for e in self.events:
            key = round(e.beat, 4)
            result.setdefault(key, []).append(e)
        return result
    
    def temporal_entropy(self) -> float:
        """Shannon entropy of inter-beat intervals."""
        if len(self.events) < 2:
            return 0.0
        beats = sorted(set(round(e.beat, 4) for e in self.events))
        intervals = [beats[i+1] - beats[i] for i in range(len(beats) - 1)]
        if not intervals:
            return 0.0
        median = sorted(intervals)[len(intervals) // 2]
        if median == 0:
            return 0.0
        normalized = [iv / median for iv in intervals]
        # Bin into 10 buckets
        bins = [0] * 10
        for n in normalized:
            idx = min(int(n * 2), 9)
            bins[idx] += 1
        total = sum(bins)
        if total == 0:
            return 0.0
        entropy = 0.0
        for b in bins:
            if b > 0:
                p = b / total
                entropy -= p * math.log2(p)
        return entropy
    
    def rhythm_quality(self) -> str:
        """Classify the temporal feel."""
        entropy = self.temporal_entropy()
        if entropy < 0.5:
            return "metronomic"
        elif entropy < 1.5:
            return "rhythmic"
        elif entropy < 2.5:
            return "groovy"
        else:
            return "free"


# ── MIDI File Writer ──────────────────────────────────────────────────────────

def write_variable_length(value: int) -> bytes:
    """Write a MIDI variable-length quantity."""
    if value < 0:
        value = 0
    result = []
    result.append(value & 0x7F)
    value >>= 7
    while value:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    return bytes(reversed(result))


def encode_midi_file(score: VideoScore) -> bytes:
    """Encode a VideoScore as a standard MIDI file (Format 1)."""
    ppqn = PPQN
    
    # Group events by channel into tracks
    channels = {}
    for event in score.events:
        ch = event.channel
        channels.setdefault(ch, []).append(event)
    
    num_tracks = len(channels) + 1  # +1 for tempo track
    microseconds_per_beat = int(60_000_000 / score.tempo_bpm)
    
    # Build tempo track
    tempo_track = bytearray()
    # Tempo meta event
    tempo_track += write_variable_length(0)  # delta=0
    tempo_track += bytes([0xFF, 0x51, 0x03])  # tempo meta
    tempo_track += struct.pack(">I", microseconds_per_beat)[1:]  # 3 bytes
    # End of track
    tempo_track += write_variable_length(1)  # delta=1
    tempo_track += bytes([0xFF, 0x2F, 0x00])
    
    tracks_data = [bytes(tempo_track)]
    
    # Build each channel track
    for ch, events in sorted(channels.items()):
        track = bytearray()
        
        # FLUX metadata as text meta events
        for event in sorted(events, key=lambda e: e.beat):
            delta = event.to_beat_ticks(ppqn)
            # Write delta (relative to previous event)
            # For simplicity, we sort and compute deltas
            pass
        
        # Sort events by beat
        sorted_events = sorted(events, key=lambda e: e.beat)
        
        prev_tick = 0
        for event in sorted_events:
            tick = event.to_beat_ticks(ppqn)
            delta = tick - prev_tick
            
            # Scene name as text meta event
            if event.meta:
                meta_text = json.dumps(event.meta)
                meta_bytes = meta_text.encode('utf-8')
                track += write_variable_length(delta)
                track += bytes([0xFF, 0x01, len(meta_bytes)])
                track += meta_bytes
                delta = 0  # Next event at same time
            
            # Note On
            track += write_variable_length(delta)
            track += bytes([0x90 | (ch - 1), event.scene_type, event.velocity])
            
            # Note Off after duration
            dur_ticks = event.duration_ticks(ppqn)
            track += write_variable_length(dur_ticks)
            track += bytes([0x80 | (ch - 1), event.scene_type, 0])
            
            prev_tick = tick + dur_ticks
        
        # End of track
        track += write_variable_length(1)
        track += bytes([0xFF, 0x2F, 0x00])
        
        tracks_data.append(bytes(track))
    
    # Assemble MIDI file
    midi = bytearray()
    
    # Header chunk: MThd
    midi += b'MThd'
    midi += struct.pack(">I", 6)  # header length
    midi += struct.pack(">H", 1)  # format 1
    midi += struct.pack(">H", num_tracks)
    midi += struct.pack(">H", ppqn)
    
    # Track chunks
    for track_data in tracks_data:
        midi += b'MTrk'
        midi += struct.pack(">I", len(track_data))
        midi += track_data
    
    return bytes(midi)


# ── VMS File Format ───────────────────────────────────────────────────────────

def save_vms(score: VideoScore, path: str):
    """Save as .vms (JSON + MIDI hybrid)."""
    data = {
        "format": "vms",
        "version": "0.1.0",
        "name": score.name,
        "tempo_bpm": score.tempo_bpm,
        "lattice_divisions": score.lattice.divisions,
        "events": []
    }
    for e in score.events:
        event_data = {
            "beat": e.beat,
            "scene_type": int(e.scene_type),
            "duration_beats": e.duration_beats,
            "velocity": e.velocity,
            "channel": e.channel,
            "text_content": e.text_content,
            "text_position": e.text_position,
            "motion_type": e.motion_type,
            "motion_intensity": e.motion_intensity,
            "color_mood": e.color_mood,
            "effect_type": e.effect_type,
        }
        if e.meta:
            event_data["meta"] = e.meta
        if e.flux:
            event_data["flux"] = e.flux.to_dict()
        data["events"].append(event_data)
    
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def load_vms(path: str) -> VideoScore:
    """Load a .vms file."""
    with open(path) as f:
        data = json.load(f)
    
    score = VideoScore(
        name=data["name"],
        tempo_bpm=data.get("tempo_bpm", 72.0),
        lattice=EisensteinLattice(data.get("lattice_divisions", 12)),
    )
    
    for ed in data.get("events", []):
        event = SceneEvent(
            beat=ed["beat"],
            scene_type=SceneType(ed["scene_type"]),
            duration_beats=ed["duration_beats"],
            velocity=ed.get("velocity", 80),
            channel=ed.get("channel", Channel.VISUAL),
            text_content=ed.get("text_content", ""),
            text_position=ed.get("text_position", "center"),
            motion_type=ed.get("motion_type", ""),
            motion_intensity=ed.get("motion_intensity", 0.5),
            color_mood=ed.get("color_mood", ""),
            effect_type=ed.get("effect_type", ""),
            meta=ed.get("meta", {}),
            flux=FluxState.from_dict(ed["flux"]) if "flux" in ed else None,
        )
        score.events.append(event)
    
    return score


def render_timeline(score: VideoScore) -> List[dict]:
    """Render score as a frame-by-frame timeline (JSON-friendly)."""
    seconds_per_beat = 60.0 / score.tempo_bpm
    total_beats = score.duration_beats()
    total_seconds = total_beats * seconds_per_beat
    
    # Sample at 30fps
    fps = 30
    frames = []
    for frame_idx in range(int(total_seconds * fps) + 1):
        t = frame_idx / fps
        beat = t / seconds_per_beat
        
        active = score.events_in_range(beat, beat + 1.0 / fps / seconds_per_beat)
        
        frame = {
            "frame": frame_idx,
            "time": round(t, 3),
            "beat": round(beat, 3),
            "beat_snapped": round(score.lattice.snap(beat), 3),
            "snap_delta": round(score.lattice.snap_delta(beat), 4),
            "active_layers": {},
        }
        
        for event in active:
            ch_name = Channel(event.channel).name.lower()
            frame["active_layers"][ch_name] = {
                "scene_type": SceneType(event.scene_type).name,
                "velocity": event.velocity,
                "text": event.text_content,
                "motion": event.motion_type,
                "mood": event.color_mood,
                "effect": event.effect_type,
                "progress": min(1.0, (beat - event.beat) / event.duration_beats) if event.duration_beats > 0 else 1.0,
            }
        
        frames.append(frame)
    
    return frames


def analyze_score(score: VideoScore) -> dict:
    """Analyze temporal structure of a video score."""
    visual = score.channel_events(Channel.VISUAL)
    text = score.channel_events(Channel.TEXT)
    audio = score.channel_events(Channel.AUDIO)
    
    entropy = score.temporal_entropy()
    
    # Inter-cut intervals
    beats = sorted(set(round(e.beat, 4) for e in visual))
    intervals = [beats[i+1] - beats[i] for i in range(len(beats) - 1)] if len(beats) > 1 else []
    
    # Velocity distribution (intensity profile)
    velocities = [e.velocity for e in visual]
    
    return {
        "name": score.name,
        "tempo_bpm": score.tempo_bpm,
        "lattice": f"E{score.lattice.divisions}",
        "duration_seconds": round(score.duration_seconds(), 2),
        "total_events": len(score.events),
        "visual_scenes": len(visual),
        "text_events": len(text),
        "audio_events": len(audio),
        "unique_beats": len(beats),
        "temporal_entropy": round(entropy, 3),
        "rhythm_quality": score.rhythm_quality(),
        "mean_cut_interval_beats": round(sum(intervals) / len(intervals), 2) if intervals else 0,
        "min_cut_interval_beats": round(min(intervals), 2) if intervals else 0,
        "max_cut_interval_beats": round(max(intervals), 2) if intervals else 0,
        "mean_velocity": round(sum(velocities) / len(velocities), 1) if velocities else 0,
        "peak_velocity": max(velocities) if velocities else 0,
        "dynamic_range": (max(velocities) - min(velocities)) if len(velocities) > 1 else 0,
    }


# ── Demo: Product Video ──────────────────────────────────────────────────────

def create_demo_score() -> VideoScore:
    """Create the FLUX-Tensor-MIDI product demo video score."""
    score = VideoScore(
        name="flux-tensor-midi-demo",
        tempo_bpm=72.0,
        lattice=EisensteinLattice(12),
    )
    
    # Beat 0: Hero product shot (intense opening)
    score.add_scene(SceneEvent(
        beat=0, scene_type=SceneType.PRODUCT_CLOSEUP, duration_beats=4,
        velocity=100, channel=Channel.VISUAL,
        meta={"name": "Hero product shot", "description": "FLUX-Tensor-MIDI logo reveal"},
    ))
    
    # Beat 0: Music bed starts
    score.add_scene(SceneEvent(
        beat=0, scene_type=SceneType.ANIMATION, duration_beats=16,
        velocity=30, channel=Channel.AUDIO,
        meta={"name": "Music bed", "type": "ambient_electronic"},
    ))
    
    # Beat 0.5: Title appears (off-beat — syncopated)
    score.add_scene(SceneEvent(
        beat=0.5, scene_type=SceneType.TITLE_CARD, duration_beats=3,
        velocity=70, channel=Channel.TEXT,
        text_content="FLUX-Tensor-MIDI",
        text_position="center",
    ))
    
    # Beat 4: Cut to user interaction
    score.add_scene(SceneEvent(
        beat=4, scene_type=SceneType.USER_INTERACTION, duration_beats=8,
        velocity=80, channel=Channel.VISUAL,
        meta={"name": "Room musician demo", "description": "Rooms snapping to each other"},
    ))
    # Beat 4: Camera push-in
    score.add_scene(SceneEvent(
        beat=4, scene_type=SceneType.ANIMATION, duration_beats=8,
        velocity=60, channel=Channel.MOTION,
        motion_type="push_in", motion_intensity=0.6,
    ))
    # Beat 5: Lower third
    score.add_scene(SceneEvent(
        beat=5, scene_type=SceneType.TITLE_CARD, duration_beats=6,
        velocity=40, channel=Channel.TEXT,
        text_content="Rooms snap to Eisenstein lattice",
        text_position="lower_third",
    ))
    
    # Beat 9: Side-channel nod
    score.add_scene(SceneEvent(
        beat=9, scene_type=SceneType.TRANSITION, duration_beats=0.5,
        velocity=10, channel=Channel.SIDECHANNEL,
        meta={"type": "nod", "from": "visual", "to": "text", "meaning": "ready_for_next"},
    ))
    
    # Beat 12: Result display (softer, building)
    score.add_scene(SceneEvent(
        beat=12, scene_type=SceneType.RESULT_DISPLAY, duration_beats=4,
        velocity=50, channel=Channel.VISUAL,
        meta={"name": "Harmony visualization", "description": "Temporal connectome rendering"},
    ))
    # Beat 12: Color mood shift to warm
    score.add_scene(SceneEvent(
        beat=12, scene_type=SceneType.ANIMATION, duration_beats=4,
        velocity=60, channel=Channel.COLOR,
        color_mood="warm_confident",
    ))
    # Beat 12: Lower third result
    score.add_scene(SceneEvent(
        beat=12, scene_type=SceneType.TITLE_CARD, duration_beats=3,
        velocity=40, channel=Channel.TEXT,
        text_content="33-37% fleet harmony",
        text_position="lower_third",
    ))
    
    # Beat 14: Music crescendo
    score.add_scene(SceneEvent(
        beat=14, scene_type=SceneType.ANIMATION, duration_beats=2,
        velocity=80, channel=Channel.AUDIO,
        meta={"name": "Crescendo", "volume_start": 30, "volume_end": 90},
    ))
    
    # Beat 16: CALL TO ACTION (highest velocity)
    score.add_scene(SceneEvent(
        beat=16, scene_type=SceneType.CALL_TO_ACTION, duration_beats=3,
        velocity=127, channel=Channel.VISUAL,
        meta={"name": "CTA", "description": "Get started with FLUX-Tensor-MIDI"},
    ))
    # Beat 16: CTA text
    score.add_scene(SceneEvent(
        beat=16, scene_type=SceneType.TITLE_CARD, duration_beats=3,
        velocity=100, channel=Channel.TEXT,
        text_content="github.com/SuperInstance/flux-tensor-midi",
        text_position="center",
    ))
    
    # Beat 19: Fermata (hold — silence IS content)
    score.add_scene(SceneEvent(
        beat=19, scene_type=SceneType.PRODUCT_CLOSEUP, duration_beats=2,
        velocity=30, channel=Channel.VISUAL,
        meta={"name": "Fermata", "description": "Hold. Let it breathe."},
    ))
    
    # Beat 20: Side-channel smile
    score.add_scene(SceneEvent(
        beat=20, scene_type=SceneType.TRANSITION, duration_beats=0.1,
        velocity=10, channel=Channel.SIDECHANNEL,
        meta={"type": "smile", "meaning": "good_take"},
    ))
    
    # Beat 21: ALL STOP
    score.add_scene(SceneEvent(
        beat=21, scene_type=SceneType.TRANSITION, duration_beats=0.5,
        velocity=1, channel=Channel.SIDECHANNEL,
        meta={"type": "breath", "meaning": "end"},
    ))
    
    return score


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    cmd = sys.argv[1]
    
    if cmd == "demo":
        # Create and save the demo score
        score = create_demo_score()
        vms_path = "flux-tensor-midi-demo.vms"
        save_vms(score, vms_path)
        print(f"✓ Demo score saved to {vms_path}")
        
        # Also export MIDI
        midi_path = "flux-tensor-midi-demo.mid"
        midi_data = encode_midi_file(score)
        with open(midi_path, 'wb') as f:
            f.write(midi_data)
        print(f"✓ MIDI export saved to {midi_path} ({len(midi_data)} bytes)")
        
        # Analyze
        analysis = analyze_score(score)
        print(f"\n{'='*50}")
        print(f"  {analysis['name']}")
        print(f"{'='*50}")
        print(f"  Tempo:     {analysis['tempo_bpm']} BPM")
        print(f"  Lattice:   {analysis['lattice']}")
        print(f"  Duration:  {analysis['duration_seconds']}s")
        print(f"  Events:    {analysis['total_events']}")
        print(f"  Scenes:    {analysis['visual_scenes']}")
        print(f"  Entropy:   {analysis['temporal_entropy']} bits")
        print(f"  Feel:      {analysis['rhythm_quality']}")
        print(f"  Cuts:      {analysis['visual_scenes']}, mean interval {analysis['mean_cut_interval_beats']} beats")
        print(f"  Velocity:  mean={analysis['mean_velocity']}, peak={analysis['peak_velocity']}, range={analysis['dynamic_range']}")
        print(f"{'='*50}")
        
        # Timeline
        timeline = render_timeline(score)
        tl_path = "flux-tensor-midi-demo-timeline.json"
        with open(tl_path, 'w') as f:
            json.dump(timeline, f, indent=2)
        print(f"✓ Timeline ({len(timeline)} frames at 30fps) saved to {tl_path}")
        
    elif cmd == "render":
        if len(sys.argv) < 4:
            print("Usage: vms.py render input.vms output.json")
            return
        score = load_vms(sys.argv[2])
        timeline = render_timeline(score)
        with open(sys.argv[3], 'w') as f:
            json.dump(timeline, f, indent=2)
        print(f"✓ Rendered {len(timeline)} frames to {sys.argv[3]}")
        
    elif cmd == "analyze":
        if len(sys.argv) < 3:
            print("Usage: vms.py analyze input.vms")
            return
        score = load_vms(sys.argv[2])
        analysis = analyze_score(score)
        print(json.dumps(analysis, indent=2))
        
    elif cmd == "export":
        if len(sys.argv) < 4:
            print("Usage: vms.py export input.vms output.mid")
            return
        score = load_vms(sys.argv[2])
        midi_data = encode_midi_file(score)
        with open(sys.argv[3], 'wb') as f:
            f.write(midi_data)
        print(f"✓ Exported {len(midi_data)} bytes to {sys.argv[3]}")
    
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
