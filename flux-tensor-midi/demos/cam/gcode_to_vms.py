#!/usr/bin/env python3
"""
G-code to VMS converter — CNC machining operations as MIDI scores.

Feed rate = tempo. Rapid moves = staccato. Dwell = fermata.
Tool changes = program changes. The cutter doesn't care about geometry —
it cares about WHEN it arrives at each point.

Usage:
    python3 gcode_to_vms.py input.nc output.vms [--render output.html]
"""

import math
import re
import sys
import json
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'python'))


# ── G-code Parser ─────────────────────────────────────────────────────────────

class GCodeLine:
    """A parsed G-code line."""
    def __init__(self, raw="", line_num=0):
        self.raw = raw.strip()
        self.line_num = line_num
        self.code = None        # G0, G1, G2, G3, G4, M3, M5, M6, etc.
        self.params = {}        # X, Y, Z, F, S, T, etc.
        self.comment = ""
        self._parse()
    
    def _parse(self):
        if not self.raw or self.raw.startswith('%') or self.raw.startswith('('):
            if self.raw.startswith('('):
                self.comment = self.raw.strip('()')
            return
        
        # Remove inline comments
        line = re.sub(r'\(.*?\)', '', self.raw).strip()
        if not line:
            return
        
        # Extract G/M code
        match = re.match(r'([GM]\d+\.?\d*)', line, re.IGNORECASE)
        if match:
            self.code = match.group(1).upper()
        
        # Extract parameters
        for param_match in re.finditer(r'([XYZIJFSTNPRH])(-?\d+\.?\d*)', line, re.IGNORECASE):
            key = param_match.group(1).upper()
            value = float(param_match.group(2))
            self.params[key] = value


class ToolPath:
    """A segment of the tool path."""
    def __init__(self, gcode, start, end, feed_rate, spindle_speed, tool):
        self.gcode = gcode          # G0, G1, etc.
        self.start = start          # (x, y, z)
        self.end = end              # (x, y, z)
        self.feed_rate = feed_rate  # mm/min
        self.spindle_speed = spindle_speed
        self.tool = tool
    
    def distance(self):
        """Euclidean distance in 3D."""
        dx = self.end[0] - self.start[0]
        dy = self.end[1] - self.start[1]
        dz = self.end[2] - self.start[2]
        return math.sqrt(dx*dx + dy*dy + dz*dz)
    
    def duration_seconds(self):
        """Time to execute this segment."""
        if self.gcode == 'G0':
            # Rapid: assume 10 m/min = 10000 mm/min
            return self.distance() / 10000.0 * 60.0
        elif self.feed_rate > 0:
            return self.distance() / self.feed_rate * 60.0
        return 0.0


def parse_gcode(text):
    """Parse G-code text into structured lines."""
    lines = []
    for i, line in enumerate(text.strip().split('\n')):
        parsed = GCodeLine(line, i + 1)
        if parsed.code:
            lines.append(parsed)
    return lines


def gcode_to_toolpath(lines):
    """Convert parsed G-code lines into tool path segments."""
    segments = []
    x, y, z = 0.0, 0.0, 0.0
    feed_rate = 100.0  # mm/min default
    spindle_speed = 0
    tool = 1
    
    for line in lines:
        if line.code in ('G0', 'G1', 'G2', 'G3'):
            new_x = line.params.get('X', x)
            new_y = line.params.get('Y', y)
            new_z = line.params.get('Z', z)
            new_f = line.params.get('F', feed_rate)
            
            feed_rate = new_f
            start = (x, y, z)
            end = (new_x, new_y, new_z)
            
            if start != end:
                segments.append(ToolPath(
                    gcode=line.code,
                    start=start,
                    end=end,
                    feed_rate=feed_rate,
                    spindle_speed=spindle_speed,
                    tool=tool,
                ))
            
            x, y, z = new_x, new_y, new_z
        
        elif line.code == 'G4':
            # Dwell
            dwell_p = line.params.get('P', 1.0)  # seconds
            segments.append(ToolPath(
                gcode='G4',
                start=(x, y, z),
                end=(x, y, z),
                feed_rate=0,
                spindle_speed=spindle_speed,
                tool=tool,
            ))
        
        elif line.code == 'M3':
            spindle_speed = line.params.get('S', 3000)
        
        elif line.code == 'M5':
            spindle_speed = 0
        
        elif line.code == 'M6':
            tool = int(line.params.get('T', tool))
    
    return segments


# ── G-code to VMS ─────────────────────────────────────────────────────────────

def toolpath_to_vms(segments, name="cnc_operation"):
    """Convert tool path segments to VMS events."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from vms import VideoScore, SceneEvent, SceneType, Channel, EisensteinLattice
    
    score = VideoScore(
        name=name,
        tempo_bpm=60,  # 1 beat = 1 second
        lattice=EisensteinLattice(24),  # Fine grid for CNC
    )
    
    current_beat = 0.0
    
    # Spindle start
    score.add_scene(SceneEvent(
        beat=0, scene_type=SceneType.ANIMATION, duration_beats=0.5,
        velocity=100, channel=Channel.AUDIO,
        meta={"name": "Spindle start", "type": "percussion"},
    ), snap=False)
    current_beat = 0.5
    
    for seg in segments:
        if seg.gcode == 'G4':
            # Dwell = fermata
            score.add_scene(SceneEvent(
                beat=current_beat, scene_type=SceneType.PRODUCT_CLOSEUP, duration_beats=1.0,
                velocity=20, channel=Channel.VISUAL,
                meta={"name": "Dwell (fermata)"},
            ), snap=False)
            current_beat += 1.0
            continue
        
        duration = seg.duration_seconds()
        if duration < 0.001:
            continue
        
        # Map feed rate to velocity
        if seg.gcode == 'G0':
            velocity = 120  # Rapid = high velocity (staccato)
            event_name = "Rapid traverse (staccato)"
        else:
            # Feed rate mapped to velocity: 100 mm/min → 40, 1000 → 100
            velocity = min(127, max(30, int(40 + seg.feed_rate / 20)))
            event_name = "Feed cut (legato)"
        
        # Map position to pitch (just Z depth for now)
        pitch = min(127, max(0, int(60 + (seg.end[2] + 10) * 3)))
        
        score.add_scene(SceneEvent(
            beat=current_beat,
            scene_type=SceneType.ANIMATION if seg.gcode == 'G0' else SceneType.USER_INTERACTION,
            duration_beats=duration,
            velocity=velocity,
            channel=Channel.VISUAL,
            meta={
                "name": event_name,
                "gcode": seg.gcode,
                "from": f"({seg.start[0]:.1f}, {seg.start[1]:.1f}, {seg.start[2]:.1f})",
                "to": f"({seg.end[0]:.1f}, {seg.end[1]:.1f}, {seg.end[2]:.1f})",
                "distance_mm": round(seg.distance(), 2),
                "feed_rate": seg.feed_rate,
                "tool": seg.tool,
                "duration_s": round(duration, 3),
            },
        ), snap=False)
        
        # Motion channel: camera move
        score.add_scene(SceneEvent(
            beat=current_beat,
            scene_type=SceneType.ANIMATION,
            duration_beats=duration,
            velocity=int(seg.feed_rate / 20),
            channel=Channel.MOTION,
            motion_type="linear",
            motion_intensity=min(1.0, seg.feed_rate / 1000),
        ), snap=False)
        
        current_beat += duration
    
    # Spindle stop
    score.add_scene(SceneEvent(
        beat=current_beat, scene_type=SceneType.ANIMATION, duration_beats=0.5,
        velocity=0, channel=Channel.AUDIO,
        meta={"name": "Spindle stop"},
    ), snap=False)
    
    # Return to home
    score.add_scene(SceneEvent(
        beat=current_beat + 0.5, scene_type=SceneType.PRODUCT_CLOSEUP, duration_beats=1.0,
        velocity=80, channel=Channel.VISUAL,
        meta={"name": "G28 Home (resolve to tonic)"},
    ), snap=False)
    
    return score


# ── Sample G-code ─────────────────────────────────────────────────────────────

SAMPLE_POCKET = """%
(Pocket Operation - 50x50mm, 10mm deep)
(Tool: T1 6mm flat endmill)
(Spindle: S8000)
(Feed: F600 plunge, F1200 XY)
G20 G90 G17
T1 M6
S8000 M3
G0 X0 Y0
G0 Z5.0
(--- First pass Z=-2 ---)
G1 Z-2.0 F600
G1 X50.0 F1200
G1 Y12.0
G1 X0.0
G1 Y24.0
G1 X50.0
G1 Y36.0
G1 X0.0
G1 Y48.0
G1 X50.0
G0 Z5.0
(--- Second pass Z=-4 ---)
G1 Z-4.0 F600
G1 X0.0 F1200
G1 Y36.0
G1 X50.0
G1 Y24.0
G1 X0.0
G1 Y12.0
G1 X50.0
G1 Y0.0
G0 Z5.0
(--- Third pass Z=-6 ---)
G1 Z-6.0 F600
G1 X50.0 F1200
G1 Y12.0
G1 X0.0
G1 Y24.0
G1 X50.0
G1 Y36.0
G1 X0.0
G1 Y48.0
G1 X50.0
G0 Z5.0
(--- Finish pass Z=-7 ---)
G1 Z-7.0 F400
G1 X0.0 F800
G1 Y48.0
G1 X50.0
G1 Y0.0
G0 Z5.0
G4 P1.0
M5
G28 X0 Y0 Z0
M30
%"""


def main():
    if len(sys.argv) < 2 or sys.argv[1] == '--sample':
        # Run sample
        print("=" * 60)
        print("  🏭 G-CODE → VMS CONVERSION")
        print("=" * 60)
        print()
        
        print("Parsing sample pocket operation (50x50mm, 10mm deep, 4 passes)...")
        lines = parse_gcode(SAMPLE_POCKET)
        print(f"  Parsed {len(lines)} G-code lines")
        
        print("Converting to tool path...")
        segments = gcode_to_toolpath(lines)
        print(f"  Generated {len(segments)} tool path segments")
        
        total_distance = sum(s.distance() for s in segments)
        total_time = sum(s.duration_seconds() for s in segments)
        print(f"  Total distance: {total_distance:.1f} mm")
        print(f"  Estimated time: {total_time:.1f} seconds")
        
        print("Converting to VMS score...")
        score = toolpath_to_vms(segments, "pocket_50x50")
        print(f"  Score: {len(score.events)} events, {score.duration_seconds():.1f}s")
        print(f"  Temporal entropy: {score.temporal_entropy():.2f} bits")
        print(f"  Rhythm quality: {score.rhythm_quality()}")
        
        # Print the score
        print()
        print("─" * 60)
        print("  SCORE (G-code as MIDI)")
        print("─" * 60)
        for e in sorted(score.events, key=lambda e: e.beat):
            meta = e.meta.get("name", "") if e.meta else ""
            gcode = e.meta.get("gcode", "") if e.meta else ""
            dist = e.meta.get("distance_mm", "") if e.meta else ""
            feed = e.meta.get("feed_rate", "") if e.meta else ""
            to_pos = e.meta.get("to", "") if e.meta else ""
            
            bar = "█" * (e.velocity // 8)
            info = f"{gcode:3} {to_pos:25} dist={dist}" if gcode else meta
            print(f"  Beat {e.beat:5.2f} │ vel={e.velocity:3} {bar} │ {info}")
        
        # Save
        out_dir = os.path.dirname(__file__)
        
        from vms import save_vms, encode_midi_file
        
        vms_path = os.path.join(out_dir, "pocket_50x50.vms")
        save_vms(score, vms_path)
        print(f"\n✓ VMS saved to {vms_path}")
        
        mid_path = os.path.join(out_dir, "pocket_50x50.mid")
        midi_data = encode_midi_file(score)
        with open(mid_path, 'wb') as f:
            f.write(midi_data)
        print(f"✓ MIDI saved to {mid_path} ({len(midi_data)} bytes)")
        
        # Render HTML if requested
        if '--render' in sys.argv:
            idx = sys.argv.index('--render')
            html_path = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else os.path.join(out_dir, "pocket_50x50.html")
            
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
            from vms_render import render_html
            render_html(score, html_path)
        
        return score


if __name__ == "__main__":
    main()
