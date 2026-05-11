#!/usr/bin/env python3
"""
CAM/CNC Demo: G-code as MIDI Score

Converts G-code tool paths to VMS (Video Music Score) format.
Each G-code operation becomes a musical event with velocity mapped
to feed rate, duration mapped to travel distance, and special
articulations for rapid moves, dwell, and spindle events.

Usage:
    python3 demo_cam.py
"""

import sys
import os
import math
import json
import re

from flux_tensor_midi import RoomMusician, FluxVector, EisensteinSnap
from flux_tensor_midi.core.snap import RhythmicRole
from flux_tensor_midi.ensemble.band import Band
from flux_tensor_midi.ensemble.score import Score
from flux_tensor_midi.harmony.jaccard import jaccard_index
from flux_tensor_midi.harmony.chord import HarmonyState

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from vms import (
    VideoScore, SceneEvent, SceneType, Channel,
    EisensteinLattice, save_vms,
)


# -- G-code Parser --------------------------------------------------------------

class GCodeLine:
    """A single parsed G-code line."""

    def __init__(self, line: str, line_num: int):
        self.raw = line.strip()
        self.line_num = line_num
        self.is_comment = line.strip().startswith("(") or line.strip().startswith(";")
        self.comment = ""

        # Initialize all attributes early to avoid AttributeError on early return
        self.words: dict[str, float | str] = {}
        self.g_code: int | None = None
        self.m_code: int | None = None
        self.x: float | None = None
        self.y: float | None = None
        self.z: float | None = None
        self.f: float | None = None
        self.i: float | None = None
        self.j: float | None = None
        self.r: float | None = None

        if self.is_comment:
            m = re.search(r"\((.*?)\)", line)
            if m:
                self.comment = m.group(1)
            return
        for token in line.split():
            if token.startswith("(") or token.startswith(";"):
                break
            m = re.match(r"([A-Za-z])(-?\d+\.?\d*)", token)
            if m:
                key = m.group(1).upper()
                val = float(m.group(2))
                self.words[key] = val
            else:
                self.comment = token

        if "G" in self.words:
            self.g_code = int(self.words["G"])
        if "M" in self.words:
            self.m_code = int(self.words["M"])
        self.x = self.words.get("X")
        self.y = self.words.get("Y")
        self.z = self.words.get("Z")
        self.f = self.words.get("F")
        self.i = self.words.get("I")
        self.j = self.words.get("J")
        self.r = self.words.get("R")

    def __repr__(self) -> str:
        return f"GCodeLine({self.raw[:40]})"


def parse_gcode(path: str) -> list[GCodeLine]:
    """Parse a G-code file into a list of GCodeLine objects."""
    lines: list[GCodeLine] = []
    with open(path) as f:
        for i, line in enumerate(f):
            stripped = line.strip()
            if not stripped or stripped.startswith("%"):
                continue
            lines.append(GCodeLine(stripped, i))
    return lines


# -- G-code to VMS Converter ----------------------------------------------------

TOOLPATH_CHANNELS: dict[str, int] = {
    "rapid": 0,
    "feed": 1,
    "plunge": 2,
    "retract": 3,
    "spindle": 9,
    "arc": 4,
    "dwell": 5,
    "toolchange": 6,
    "chatter": 7,
}


def gcode_to_vms(gcode_path: str, output_vms_path: str | None = None) -> VideoScore:
    """Convert G-code to a VMS (Video Music Score) format.

    Mapping:
        G0 rapid      -> high velocity, short duration (staccato)
        G1 feed       -> moderate velocity, duration = distance/feed_rate
        G2/G3 arc     -> portamento (pitch bend)
        G4 dwell      -> fermata (long held note)
        M3 spindle on -> percussion strike
        M5 spindle off-> percussion release
        M6 tool change-> program change (new channel)
    """
    lines = parse_gcode(gcode_path)
    score = VideoScore(
        name=os.path.splitext(os.path.basename(gcode_path))[0],
        tempo_bpm=60,
        lattice=EisensteinLattice(24),
    )

    current_x = current_y = 0.0
    current_z = 5.0
    current_f = 600.0
    spindle_on = False
    beat = 0.0
    toolpath_points: list[dict] = []

    for line in lines:
        if line.is_comment:
            if line.comment:
                score.add_scene(SceneEvent(
                    beat=beat,
                    scene_type=SceneType.TITLE_CARD,
                    duration_beats=0.5, velocity=30,
                    channel=Channel.TEXT,
                    text_content=line.comment,
                    text_position="lower_third",
                    meta={"type": "comment", "line": line.line_num},
                ), snap=True)
            continue

        g = line.g_code
        m = line.m_code
        if line.f is not None:
            current_f = line.f

        if m == 6:
            score.add_scene(SceneEvent(
                beat=beat, scene_type=SceneType.ANIMATION,
                duration_beats=2.0, velocity=80,
                channel=Channel.EFFECTS, effect_type="tool_change",
                meta={"type": "toolchange", "tool": int(line.words.get("T", 1)),
                      "line": line.line_num},
            ), snap=True)
            beat += 2.0
            continue
        if m == 3:
            spindle_on = True
            score.add_scene(SceneEvent(
                beat=beat, scene_type=SceneType.ANIMATION,
                duration_beats=1.0, velocity=100, channel=Channel.AUDIO,
                meta={"type": "spindle_on", "rpm": int(line.words.get("S", 8000)),
                      "line": line.line_num},
            ), snap=True)
            continue
        if m == 5:
            spindle_on = False
            score.add_scene(SceneEvent(
                beat=beat, scene_type=SceneType.ANIMATION,
                duration_beats=0.5, velocity=40, channel=Channel.AUDIO,
                meta={"type": "spindle_off", "line": line.line_num},
            ), snap=True)
            continue
        if m in (8, 9):
            continue
        if m == 30:
            score.add_scene(SceneEvent(
                beat=beat, scene_type=SceneType.CALL_TO_ACTION,
                duration_beats=2.0, velocity=20, channel=Channel.SIDECHANNEL,
                meta={"type": "program_end", "line": line.line_num},
            ), snap=True)
            continue

        new_x = line.x if line.x is not None else current_x
        new_y = line.y if line.y is not None else current_y
        new_z = line.z if line.z is not None else current_z
        dx, dy, dz = new_x - current_x, new_y - current_y, new_z - current_z
        distance = math.sqrt(dx * dx + dy * dy + dz * dz)

        is_rapid = g == 0
        is_feed = g == 1
        is_arc = g in (2, 3)
        is_dwell = g == 4

        if distance == 0 and not is_dwell:
            current_x, current_y, current_z = new_x, new_y, new_z
            if line.f is not None:
                current_f = line.f
            continue

        if is_rapid:
            duration_beats = max(0.25, distance * 2.0)
            velocity = min(127, max(40, int(distance * 80 + 30)))
            move_type = "rapid"
            scene_subtype = SceneType.TRANSITION
        elif is_arc:
            duration_beats = max(0.5, distance * 4.0)
            velocity = min(127, max(40, int(distance * 60 + 20)))
            move_type = "arc"
            scene_subtype = SceneType.SPLIT_SCREEN
        elif is_dwell:
            duration_beats = max(2.0, line.words.get("P", 1.0))
            velocity = 20
            move_type = "dwell"
            scene_subtype = SceneType.CALL_TO_ACTION
        elif dz < 0:
            duration_beats = max(0.5, abs(dz) * 3.0)
            velocity = min(127, max(60, int(abs(dz) * 90)))
            move_type = "plunge"
            scene_subtype = SceneType.USER_INTERACTION
        elif dz > 0 and abs(dz) > 0.1:
            duration_beats = max(0.25, abs(dz) * 2.0)
            velocity = min(127, max(30, int(abs(dz) * 50)))
            move_type = "retract"
            scene_subtype = SceneType.USER_INTERACTION
        else:
            feed_mm_per_min = max(current_f, 1.0)
            time_seconds = (distance / feed_mm_per_min) * 60.0
            duration_beats = max(0.25, time_seconds * 2.0)
            velocity = min(127, max(40, int(current_f / 10)))
            move_type = "feed_xy"
            scene_subtype = SceneType.USER_INTERACTION

        move_meta = {
            "type": move_type, "g_code": g,
            "x": round(new_x, 3), "y": round(new_y, 3),
            "z": round(new_z, 3), "feed": current_f,
            "distance": round(distance, 3), "line": line.line_num,
        }

        score.add_scene(SceneEvent(
            beat=beat, scene_type=scene_subtype,
            duration_beats=round(duration_beats, 3),
            velocity=velocity, channel=Channel.VISUAL, meta=move_meta,
        ), snap=True)

        toolpath_points.append({
            "x": new_x, "y": new_y, "z": new_z,
            "type": move_type, "velocity": velocity,
            "beat": beat, "duration": duration_beats, "feed": current_f,
        })

        score.add_scene(SceneEvent(
            beat=beat, scene_type=SceneType.WIDE_SHOT,
            duration_beats=round(duration_beats, 3),
            velocity=max(1, min(127, int(current_f / 10))),
            channel=Channel.MOTION, motion_type=move_type,
            motion_intensity=min(1.0, current_f / 8000.0),
            meta={"feed_rate": current_f},
        ), snap=True)

        next_beat = round(beat + duration_beats, 3)
        beat = next_beat
        current_x, current_y, current_z = new_x, new_y, new_z

        if spindle_on and current_f < 200 and distance > 0:
            score.add_scene(SceneEvent(
                beat=beat - duration_beats / 2,
                scene_type=SceneType.CALL_TO_ACTION,
                duration_beats=duration_beats / 2, velocity=90,
                channel=Channel.SIDECHANNEL,
                meta={
                    "type": "chatter_warning",
                    "feed_rate": current_f,
                    "description": "Low feed rate at depth - potential chatter",
                    "line": line.line_num,
                },
            ), snap=True)

    score._toolpath = toolpath_points
    if output_vms_path:
        save_vms(score, output_vms_path)
        print(f"  VMS score saved to: {output_vms_path}")
    return score


# -- HTML Visualization ---------------------------------------------------------

def render_html_timeline(vms_score: VideoScore, gcode_path: str, output_html: str):
    """Render an HTML visualization of the G-code as a MIDI score."""
    toolpath = getattr(vms_score, "_toolpath", [])
    events = vms_score.events

    move_types = sorted(set(
        e.meta.get("type", "feed_xy") for e in events if e.meta
    ))
    colors = [
        "#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6",
        "#1abc9c", "#e67e22", "#34495e", "#7f8c8d", "#c0392b",
    ]
    type_colors = {t: colors[i % len(colors)] for i, t in enumerate(move_types)}

    max_vel = max((e.velocity for e in events), default=1)
    min_vel = min((e.velocity for e in events), default=0)
    vel_range = max(max_vel - min_vel, 1)

    bars_html = ""
    for e in events:
        if e.channel == Channel.VISUAL:
            mt = e.meta.get("type", "feed_xy")
            feed = e.meta.get("feed", 600)
            color = type_colors.get(mt, "#7f8c8d")
            width_pct = max(1.0, e.duration_beats * 2.5)
            opacity = 0.3 + 0.7 * (e.velocity - min_vel) / vel_range
            top_pos = 60 + (10 - move_types.index(mt)) * 28 if mt in move_types else 60
            bars_html += (
                f'<div class="midi-note" style="'
                f'left:{e.beat * 25}px;width:{width_pct}px;'
                f'top:{top_pos}px;height:22px;'
                f'background:{color};opacity:{opacity:.2f};'
                f'border-radius:3px;position:absolute;" '
                f'title="{mt} vel={e.velocity} feed={feed}mm/min"></div>\n'
            )

    if toolpath:
        xs = [p["x"] for p in toolpath]
        ys = [p["y"] for p in toolpath]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        x_range = max(max_x - min_x, 1)
        y_range = max(max_y - min_y, 1)
        svg_w, svg_h = 520, 440

        seg_svg = ""
        for i in range(1, len(toolpath)):
            p0, p1 = toolpath[i-1], toolpath[i]
            sx0 = 50 + (p0["x"] - min_x) / x_range * (svg_w - 80)
            sy0 = svg_h - 30 - (p0["y"] - min_y) / y_range * (svg_h - 60)
            sx1 = 50 + (p1["x"] - min_x) / x_range * (svg_w - 80)
            sy1 = svg_h - 30 - (p1["y"] - min_y) / y_range * (svg_h - 60)
            c = type_colors.get(p1["type"], "#7f8c8d")
            seg_svg += (
                f'<line x1="{sx0:.1f}" y1="{sy0:.1f}" '
                f'x2="{sx1:.1f}" y2="{sy1:.1f}" '
                f'stroke="{c}" stroke-width="2" opacity="0.8" />\n'
            )

        grid_svg = ""
        for gx in range(0, int(max_x) + 11, 10):
            sx = 50 + (gx - min_x) / x_range * (svg_w - 80)
            grid_svg += (
                f'<line x1="{sx:.1f}" y1="15" '
                f'x2="{sx:.1f}" y2="{svg_h-20}" '
                f'stroke="#333" stroke-width="0.5" />\n'
            )
            grid_svg += (
                f'<text x="{sx:.1f}" y="{svg_h-8}" '
                f'font-size="8" fill="#777" '
                f'text-anchor="middle">{gx}</text>\n'
            )
        for gy in range(0, int(max_y) + 11, 10):
            sy = svg_h - 30 - (gy - min_y) / y_range * (svg_h - 60)
            grid_svg += (
                f'<line x1="30" y1="{sy:.1f}" '
                f'x2="{svg_w-10}" y2="{sy:.1f}" '
                f'stroke="#333" stroke-width="0.5" />\n'
            )
            grid_svg += (
                f'<text x="25" y="{sy + 3:.1f}" '
                f'font-size="8" fill="#777" '
                f'text-anchor="end">{gy}</text>\n'
            )
    else:
        seg_svg = ""
        grid_svg = ""
        svg_w, svg_h = 520, 440

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>G-code as MIDI Score: {os.path.basename(gcode_path)}</title>
<style>
  body {{ font-family: 'Segoe UI', sans-serif; margin: 20px; background: #1a1a2e; color: #eee; }}
  h1, h2, h3 {{ color: #e94560; }}
  .container {{ max-width: 1200px; margin: 0 auto; }}
  .score-container {{ background: #16213e; border-radius: 8px; padding: 20px; margin: 20px 0; overflow-x: auto; min-height: 400px; position: relative; }}
  .midi-note {{ transition: opacity 0.2s; }}
  .midi-note:hover {{ opacity: 0.8 !important; transform: scaleY(1.3); }}
  .legend {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0; }}
  .legend-item {{ padding: 4px 10px; border-radius: 4px; font-size: 12px; color: white; }}
  .stats {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; margin: 20px 0; }}
  .stat-card {{ background: #0f3460; border-radius: 8px; padding: 15px; }}
  .stat-value {{ font-size: 24px; font-weight: bold; color: #e94560; }}
  .stat-label {{ font-size: 11px; color: #888; margin-top: 4px; }}
</style>
</head>
<body>
<div class="container">

<h1>G-code as MIDI Score</h1>
<p>File: <strong>{os.path.basename(gcode_path)}</strong></p>

<div class="stats">
  <div class="stat-card">
    <div class="stat-value">{len(vms_score.events)}</div>
    <div class="stat-label">Total Events</div>
  </div>
  <div class="stat-card">
    <div class="stat-value">{len(toolpath)}</div>
    <div class="stat-label">Toolpath Points</div>
  </div>
  <div class="stat-card">
    <div class="stat-value">{max(e.velocity for e in events) if events else 0}</div>
    <div class="stat-label">Peak Velocity</div>
  </div>
  <div class="stat-card">
    <div class="stat-value">{len(move_types)}</div>
    <div class="stat-label">Move Types</div>
  </div>
</div>

<h2>Tool Path (XY plane)</h2>
<div style="background: #0f3460; border-radius: 8px; padding: 15px;">
<svg width="{svg_w}" height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}">
{grid_svg}
{seg_svg}
</svg>
</div>

<h2>MIDI Score Visualization</h2>
<div class="legend">"""
    for t, c in type_colors.items():
        html += f'\n  <div class="legend-item" style="background:{c}">{t}</div>'
    html += """
</div>
<div class="score-container">
  <div style="position: relative; height: 350px;">
"""
    html += bars_html
    html += """
  </div>
  <div style="margin-top:10px;font-size:10px;color:#666;text-align:center;">
    Beat grid (1 tick = 1 beat at 60 BPM)
  </div>
</div>

<h3>Feed Rate Profile</h3>
<div style="background: #0f3460; border-radius: 8px; padding: 15px; margin: 20px 0;">
"""
    if toolpath:
        feeds = [p["feed"] for p in toolpath]
        max_feed = max(feeds) if feeds else 1
        fr_w, fr_h = 800, 150
        pts = " ".join(
            f"{i / len(feeds) * fr_w},{fr_h - 20 - (f / max_feed) * (fr_h - 40):.1f}"
            for i, f in enumerate(feeds)
        )
        html += f"""
<svg width="100%" height="{fr_h}" viewBox="0 0 {fr_w} {fr_h}">
  <polyline points="{pts}" fill="none" stroke="#e94560" stroke-width="2" />
  <text x="5" y="15" fill="#999" font-size="10">Feed Rate (mm/min)</text>
  <text x="5" y="{fr_h-5}" fill="#999" font-size="9">0</text>
  <text x="{fr_w-30}" y="{fr_h-5}" fill="#999" font-size="9">{max_feed}</text>
</svg>"""

    html += """
</div>

<h3>Chatter Detection</h3>
"""
    warnings = [e for e in events if e.meta.get("type") == "chatter_warning"]
    if warnings:
        rows = "".join(
            f"<tr><td>{w.beat:.1f}</td><td>{w.meta.get('feed_rate','?')}</td>"
            f"<td>{w.meta.get('description','?')}</td>"
            f"<td>Line {w.meta.get('line','?')}</td></tr>"
            for w in warnings
        )
        html += f"""
<table style="width:100%;border-collapse:collapse;font-size:12px;">
<tr style="background:#e94560;color:white;">
  <th style="padding:6px;text-align:left;">Beat</th>
  <th style="padding:6px;text-align:left;">Feed Rate</th>
  <th style="padding:6px;text-align:left;">Description</th>
  <th style="padding:6px;text-align:left;">Line</th>
</tr>
{rows}
</table>"""
    else:
        html += "<p>No chatter detected - harmony maintained.</p>"

    html += """
<h3>Raw Data (first 20 events)</h3>
<pre style="background:#0f3460;padding:15px;border-radius:8px;font-size:11px;overflow-x:auto;max-height:400px;">
"""
    for e in events[:20]:
        html += (
            f"beat={e.beat:6.1f}  dur={e.duration_beats:6.2f}  "
            f"vel={e.velocity:3d}  "
            f"type={e.meta.get('type','?'):<12}  "
            f"x={e.meta.get('x','?'):>7}  "
            f"y={e.meta.get('y','?'):>7}  "
            f"z={e.meta.get('z','?'):>7}  "
            f"feed={e.meta.get('feed','?'):>5}\n"
        )

    html += """
</pre>

</div>
</body>
</html>"""

    with open(output_html, "w") as f:
        f.write(html)
    print(f"  HTML visualization saved to: {output_html}")


# -- Harmony Analysis ----------------------------------------------------------

def analyze_cam_harmony(vms_score: VideoScore) -> dict:
    """Analyze the CAM score for harmony and chatter detection."""
    events = vms_score.events
    harmony_buckets: list[dict] = []
    if not events:
        return {"buckets": [], "harmony_quality": "silent", "chatter_events": 0}

    max_beat = max(e.beat + e.duration_beats for e in events)
    window = 2.0

    beat = 0.0
    while beat < max_beat:
        window_events = [e for e in events if beat <= e.beat < beat + window]
        if window_events:
            velocities = [e.velocity for e in window_events if e.channel == Channel.VISUAL]
            feed_rates = [e.meta.get("feed", 600) for e in window_events if e.meta]
            mean_vel = sum(velocities) / len(velocities) if velocities else 0
            vel_spread = max(velocities) - min(velocities) if len(velocities) > 1 else 0
            feed_spread = max(feed_rates) - min(feed_rates) if len(feed_rates) > 1 else 0
            harmony_score = max(0.0, 1.0 - (vel_spread / 127.0) - (feed_spread / 8000.0))
            harmony_buckets.append({
                "beat": beat, "events": len(window_events),
                "mean_velocity": round(mean_vel, 1),
                "harmony_score": round(harmony_score, 3),
                "chatter_risk": harmony_score < 0.5,
            })
        beat += window

    chatter_count = sum(1 for b in harmony_buckets if b["chatter_risk"])
    overall_harmony = (
        "stable"
        if harmony_buckets
        and sum(b["harmony_score"] for b in harmony_buckets) / len(harmony_buckets) > 0.6
        else "unstable"
    ) if harmony_buckets else "silent"

    return {
        "buckets": harmony_buckets,
        "harmony_quality": overall_harmony,
        "chatter_events": chatter_count,
        "total_windows": len(harmony_buckets),
    }


# -- FLUX-Tensor-MIDI RoomMusician Processor ------------------------------------

class GCodeRoom:
    """A RoomMusician-based G-code processor treating axis moves as notes.

    Each axis becomes a musician. The chatter monitor listens for low-feed
    deep cuts and sends a dissonant nod (frown) to the spindle.
    """

    def __init__(self, gcode_path: str):
        self.lines = parse_gcode(gcode_path)
        self.band = Band("cnc_operation", bpm=60)

        self.axis_x = RoomMusician("axis_x", role=RhythmicRole.ROOT)
        self.axis_y = RoomMusician("axis_y", role=RhythmicRole.COMPOUND)
        self.axis_z = RoomMusician("axis_z", role=RhythmicRole.HALFTIME)
        self.spindle = RoomMusician("spindle", role=RhythmicRole.WALTZ)
        self.chatter_monitor = RoomMusician("chatter_monitor", role=RhythmicRole.TRIPLET)

        for m in [self.axis_x, self.axis_y, self.axis_z, self.spindle, self.chatter_monitor]:
            self.band.add_musician(m)
        self.band.everyone_listens_to_everyone()

    def process(self) -> Score:
        """Process G-code through the band, return a Score."""
        score = Score("cnc_gcode_processing")
        current_x = current_y = 0.0
        current_z = 5.0
        feed_rate = 600.0
        spindle_on = False
        beat_count = 0

        for line in self.lines:
            if line.is_comment or line.g_code is None:
                continue

            m = line.m_code
            if m == 3:
                spindle_on = True
                self.spindle.state = FluxVector([1.0, 0, 0, 0, 0, 0, 0, 0, 0])
                self.spindle.emit(self.spindle.state)
                continue
            if m == 5:
                spindle_on = False
                self.spindle.state = FluxVector([0.0, 0, 0, 0, 0, 0, 0, 0, 0])
                self.spindle.emit(self.spindle.state)
                continue

            new_x = line.x if line.x is not None else current_x
            new_y = line.y if line.y is not None else current_y
            new_z = line.z if line.z is not None else current_z
            if line.f is not None:
                feed_rate = line.f

            vec_x = FluxVector([new_x / 50.0, dx := new_x - current_x,
                                feed_rate / 8000.0, 0, 0, 0, 0, 0, 0])
            self.axis_x.state = vec_x
            self.axis_x.emit(vec_x)

            vec_y = FluxVector([new_y / 30.0, dy := new_y - current_y,
                                feed_rate / 8000.0, 0, 0, 0, 0, 0, 0])
            self.axis_y.state = vec_y
            self.axis_y.emit(vec_y)

            vec_z = FluxVector([new_z / 10.0, dz := new_z - current_z,
                                feed_rate / 8000.0, 0, 0, 0, 0, 0, 0])
            self.axis_z.state = vec_z
            self.axis_z.emit(vec_z)

            # Chatter monitor: low feed + deep Z = dissonance
            if spindle_on and feed_rate < 200 and abs(new_z) > 3:
                vec_chatter = FluxVector([0.9, 0.8, 0.7, 0, 0, 0, 0, 0, 0])
                self.chatter_monitor.state = vec_chatter
                ts, _ = self.chatter_monitor.emit(vec_chatter)
                self.chatter_monitor.send_nod(self.spindle, intensity=0.9)
                score.record_side_channel("chatter_monitor", "chatter_warning", int(ts))
            else:
                vec_quiet = FluxVector([0.1, 0, 0, 0, 0, 0, 0, 0, 0])
                self.chatter_monitor.state = vec_quiet
                self.chatter_monitor.emit(vec_quiet)

            ts_x = self.axis_x.event_history[-1][0]
            score.record_event("axis_x", ts_x, vec_x)

            current_x, current_y, current_z = new_x, new_y, new_z
            beat_count += 1

        return score

    def print_summary(self):
        """Print a summary of the processing."""
        h = self.band.harmony()
        print(f"  GCodeRoom processed {len(self.lines)} lines")
        print(f"  Band: {self.band.name} with {self.band.member_count} musicians")
        print(f"  Mean coherence:   {self.band.mean_coherence():.4f}")
        print(f"  Final harmony:    {h.quality()} (consonance={h.consonance():.3f})")


# -- Main -----------------------------------------------------------------------

def main():
    out_dir = os.path.dirname(os.path.abspath(__file__))
    gcode_path = os.path.join(out_dir, "sample_pocket.nc")
    vms_path = os.path.join(out_dir, "pocket_operation.vms")
    html_path = os.path.join(out_dir, "gcode_midi_score.html")

    print("=" * 72)
    print("  CAM/CNC Demo: G-code as MIDI Score")
    print("=" * 72)
    print(f"\nG-code file: {gcode_path}")

    # 1. Parse and inspect
    lines = parse_gcode(gcode_path)
    g0_count = sum(1 for l in lines if l.g_code == 0)
    g1_count = sum(1 for l in lines if l.g_code == 1)
    comment_count = sum(1 for l in lines if l.is_comment)
    toolchanges = [l for l in lines if l.m_code == 6]
    spindle_events = [l for l in lines if l.m_code in (3, 5)]

    print(f"\n  Parsed G-code stats:")
    print(f"    Total lines:       {len(lines)}")
    print(f"    Comments:          {comment_count}")
    print(f"    G0 (rapid):        {g0_count}")
    print(f"    G1 (feed):         {g1_count}")
    print(f"    Tool changes:      {len(toolchanges)}")
    print(f"    Spindle on/off:    {len(spindle_events)}")

    # 2. Convert to VMS score
    print(f"\n  Converting to VMS score...")
    vms_score = gcode_to_vms(gcode_path, vms_path)
    print(f"    Events generated:  {len(vms_score.events)}")
    print(f"    Tempo:             {vms_score.tempo_bpm} BPM")
    print(f"    Lattice divisions: {vms_score.lattice.divisions}")

    # 3. Compute harmony
    print(f"\n  Analyzing CAM harmony...")
    harmony = analyze_cam_harmony(vms_score)
    print(f"    Harmony quality:     {harmony['harmony_quality']}")
    print(f"    Chatter risk windows: {harmony['chatter_events']} / {harmony['total_windows']}")

    if harmony["buckets"]:
        avg_h = sum(b["harmony_score"] for b in harmony["buckets"]) / len(harmony["buckets"])
        print(f"    Mean harmony score:  {avg_h:.3f}")

    bad_buckets = [b for b in harmony["buckets"] if b["chatter_risk"]]
    if bad_buckets:
        print(f"    Chatter detected at beats: {[b['beat'] for b in bad_buckets]}")

    # 4. GCodeRoom processing
    print(f"\n  Processing through GCodeRoom (band)...")
    gcode_room = GCodeRoom(gcode_path)
    band_score = gcode_room.process()
    gcode_room.print_summary()

    # 5. Render HTML
    print(f"\n  Rendering HTML visualization...")
    render_html_timeline(vms_score, gcode_path, html_path)

    # 6. Harmony summary
    print(f"\n{'='*72}")
    print(f"  CAM HARMONY SUMMARY")
    print(f"{'='*72}")
    for b in harmony["buckets"]:
        status = "CHATTER RISK" if b["chatter_risk"] else "stable"
        print(f"  beat={b['beat']:4.0f}  events={b['events']:2d}  "
              f"harmony={b['harmony_score']:.3f}  status={status}")

    print(f"\n{'='*72}")
    print(f"  DEMO COMPLETE +")
    print(f"{'='*72}")


if __name__ == "__main__":
    main()
