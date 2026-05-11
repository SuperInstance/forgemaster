#!/usr/bin/env python3
"""
Animation Demo — Keyframes as MIDI Score

Shows how a motion graphics animation is encoded as a VMS score.
Each property (position, rotation, scale, opacity, color) is a MIDI channel.
The Eisenstein lattice IS the easing grid.

Output: an HTML animation player that renders the score in real-time.
"""

import json
import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'python'))

# ── Animation Primitives ─────────────────────────────────────────────────────

class AnimProperty:
    """An animated property = a MIDI channel."""
    def __init__(self, name, channel, value_type="float"):
        self.name = name
        self.channel = channel
        self.value_type = value_type
        self.keyframes = []  # (beat, value, velocity)
    
    def key(self, beat, value, velocity=80):
        """Set a keyframe = play a note."""
        self.keyframes.append({"beat": beat, "value": value, "velocity": velocity})
        return self
    
    def ease(self, t, easing="snap"):
        """Compute eased value at progress t ∈ [0, 1]."""
        if easing == "snap":
            return t  # Linear — the lattice handles the feel
        elif easing == "ease_in":
            return t * t
        elif easing == "ease_out":
            return 1 - (1 - t) ** 2
        elif easing == "ease_in_out":
            return 3 * t * t - 2 * t * t * t
        return t
    
    def value_at(self, beat, lattice_divisions=12):
        """Get interpolated value at a given beat (snapped to grid)."""
        # Snap to lattice
        grid = 1.0 / lattice_divisions
        beat = round(beat / grid) * grid
        
        # Find surrounding keyframes
        prev_kf = None
        next_kf = None
        for kf in self.keyframes:
            if kf["beat"] <= beat:
                prev_kf = kf
            if kf["beat"] >= beat and next_kf is None:
                next_kf = kf
        
        if prev_kf is None and next_kf is None:
            return 0
        if prev_kf is None:
            return next_kf["value"]
        if next_kf is None:
            return prev_kf["value"]
        if prev_kf["beat"] == next_kf["beat"]:
            return prev_kf["value"]
        
        # Interpolate
        t = (beat - prev_kf["beat"]) / (next_kf["beat"] - prev_kf["beat"])
        t = self.ease(t)
        return prev_kf["value"] + t * (next_kf["value"] - prev_kf["value"])


E12 = 12  # Standard animation lattice

class Animation:
    """A complete animation = a MIDI score with multiple channels."""
    def __init__(self, name, tempo_bpm=72, lattice=12):
        self.name = name
        self.tempo_bpm = tempo_bpm
        self.lattice = lattice
        self.bps = tempo_bpm / 60.0
        
        # 6 animated properties = 6 MIDI channels
        self.pos_x = AnimProperty("pos_x", 1)
        self.pos_y = AnimProperty("pos_y", 2)
        self.rotation = AnimProperty("rotation", 3)
        self.scale = AnimProperty("scale", 4)
        self.opacity = AnimProperty("opacity", 5)
        self.color_hue = AnimProperty("color_hue", 6)
        self.properties = [self.pos_x, self.pos_y, self.rotation, self.scale, self.opacity, self.color_hue]
    
    def duration_beats(self):
        """Total animation duration in beats."""
        max_beat = 0
        for prop in self.properties:
            for kf in prop.keyframes:
                max_beat = max(max_beat, kf["beat"])
        return max_beat
    
    def duration_seconds(self):
        return self.duration_beats() / self.bps
    
    def frame_at(self, beat):
        """Get all property values at a given beat."""
        return {prop.name: prop.value_at(beat, self.lattice) for prop in self.properties}
    
    def render_frames(self, fps=30):
        """Render all frames at given FPS."""
        frames = []
        total_seconds = self.duration_seconds()
        for i in range(int(total_seconds * fps) + 1):
            t = i / fps
            beat = t * self.bps
            frame = {
                "frame": i,
                "time": round(t, 4),
                "beat": round(beat, 4),
                **self.frame_at(beat),
            }
            frames.append(frame)
        return frames
    
    def to_vms(self):
        """Export as VMS format."""
        events = []
        for prop in self.properties:
            for kf in prop.keyframes:
                events.append({
                    "beat": kf["beat"],
                    "scene_type": 69,  # ANIMATION
                    "duration_beats": 0.1,
                    "velocity": kf["velocity"],
                    "channel": prop.channel,
                    "meta": {"property": prop.name, "value": kf["value"]},
                })
        return {
            "format": "vms",
            "version": "0.1.0",
            "name": self.name,
            "tempo_bpm": self.tempo_bpm,
            "lattice_divisions": self.lattice,
            "events": events,
        }
    
    def render_html_player(self, output_path):
        """Render an HTML animation player."""
        frames = self.render_frames()
        vms = self.to_vms()
        
        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>{self.name}</title>
<style>
  body {{ background: #0f172a; color: #e2e8f0; font-family: monospace; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }}
  .canvas {{ width: 400px; height: 400px; position: relative; background: #1e293b; border-radius: 12px; overflow: hidden; }}
  .element {{ position: absolute; width: 80px; height: 80px; border-radius: 12px; transition: none; }}
  .info {{ position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); text-align: center; font-size: 0.8rem; color: #64748b; }}
  .controls {{ position: fixed; top: 20px; left: 50%; transform: translateX(-50%); display: flex; gap: 10px; }}
  button {{ background: #3B82F6; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-family: inherit; }}
  .timeline {{ position: fixed; bottom: 60px; left: 50%; transform: translateX(-50%); width: 400px; height: 4px; background: #334155; border-radius: 2px; }}
  .progress {{ height: 100%; background: #3B82F6; border-radius: 2px; transition: width 0.03s; }}
  .beat-grid {{ position: absolute; top: 0; bottom: 0; width: 1px; background: rgba(59,130,246,0.15); }}
  .beat-grid.major {{ background: rgba(59,130,246,0.3); }}
</style></head><body>
<div class="controls"><button id="playBtn">▶ Play</button><span id="timeDisp" style="color:#94a3b8;padding:8px">0.00s</span></div>
<div class="canvas" id="canvas"><div class="element" id="el"></div></div>
<div class="timeline"><div class="progress" id="progress"></div></div>
<div class="info" id="info">Beat 0.00 · {self.tempo_bpm} BPM · E{self.lattice}</div>
<script>
const frames = {json.dumps(frames)};
const totalFrames = frames.length;
const totalSeconds = {self.duration_seconds():.2f};
let playing = false;
let frameIdx = 0;
let lastTime = 0;

function render(frame) {{
  const el = document.getElementById('el');
  const x = (frame.pos_x + 1) / 2 * 320;
  const y = (1 - frame.pos_y) / 2 * 320;
  const rot = frame.rotation * 180 / Math.PI;
  const scl = frame.scale;
  const opa = frame.opacity;
  const hue = frame.color_hue * 360;
  el.style.left = x + 'px';
  el.style.top = y + 'px';
  el.style.transform = 'rotate(' + rot + 'deg) scale(' + scl + ')';
  el.style.opacity = opa;
  el.style.background = 'hsl(' + hue + ', 70%, 60%)';
  el.style.boxShadow = '0 0 ' + (scl * 20) + 'px hsl(' + hue + ', 70%, 40%)';
  
  const beat = frame.beat;
  document.getElementById('info').textContent = 
    'Beat ' + beat.toFixed(2) + ' · {self.tempo_bpm} BPM · E{self.lattice} · ' +
    'x=' + frame.pos_x.toFixed(2) + ' y=' + frame.pos_y.toFixed(2) +
    ' rot=' + (rot).toFixed(0) + '° sc=' + scl.toFixed(2) +
    ' op=' + opa.toFixed(2) + ' hue=' + hue.toFixed(0) + '°';
  document.getElementById('progress').style.width = (frame.time / totalSeconds * 100) + '%';
  document.getElementById('timeDisp').textContent = frame.time.toFixed(2) + 's / ' + totalSeconds.toFixed(2) + 's';
}}

function animate(timestamp) {{
  if (!playing) return;
  if (!lastTime) lastTime = timestamp;
  const dt = (timestamp - lastTime) / 1000;
  lastTime = timestamp;
  
  frameIdx = Math.min(frameIdx + Math.round(dt * 30), totalFrames - 1);
  render(frames[frameIdx]);
  
  if (frameIdx >= totalFrames - 1) {{
    playing = false;
    document.getElementById('playBtn').textContent = '▶ Play';
    return;
  }}
  requestAnimationFrame(animate);
}}

document.getElementById('playBtn').addEventListener('click', function() {{
  if (playing) {{
    playing = false;
    this.textContent = '▶ Play';
  }} else {{
    if (frameIdx >= totalFrames - 1) frameIdx = 0;
    playing = true;
    lastTime = 0;
    this.textContent = '⏸ Pause';
    requestAnimationFrame(animate);
  }}
}});

render(frames[0]);
</script></body></html>"""
        
        with open(output_path, 'w') as f:
            f.write(html)
        print(f"✓ Animation player saved to {output_path} ({len(html)} bytes)")


def create_demo_animation():
    """Create a logo reveal animation as a MIDI score."""
    
    print("=" * 60)
    print("  ✨ ANIMATION AS MIDI SCORE — Logo Reveal Demo")
    print("=" * 60)
    print()
    
    anim = Animation("logo_reveal", tempo_bpm=72, lattice=E12)
    
    # The animation: a shape flies in, rotates, scales up, changes color, holds
    
    # Position: start off-screen left, fly to center
    anim.pos_x.key(0, -1.5, velocity=0)      # off-screen
    anim.pos_x.key(4, 0.0, velocity=100)      # center (the arrival = the note)
    anim.pos_x.key(16, 0.0, velocity=40)      # hold center
    anim.pos_x.key(18, 0.3, velocity=60)       # slight drift (breathing)
    
    anim.pos_y.key(0, 0.3, velocity=0)         # slightly above center
    anim.pos_y.key(4, 0.0, velocity=80)        # drop to center
    anim.pos_y.key(8, -0.1, velocity=40)       # overshoot (bounce)
    anim.pos_y.key(10, 0.0, velocity=60)       # settle
    anim.pos_y.key(16, 0.0, velocity=30)
    anim.pos_y.key(18, -0.05, velocity=50)     # gentle float
    
    # Rotation: spin in
    anim.rotation.key(0, -2 * math.pi, velocity=0)  # -360°
    anim.rotation.key(4, 0, velocity=100)            # settle at 0°
    anim.rotation.key(12, math.pi / 12, velocity=30) # slight tilt
    anim.rotation.key(16, 0, velocity=40)            # return
    anim.rotation.key(18, math.pi / 24, velocity=50) # gentle rock
    
    # Scale: grow from nothing
    anim.scale.key(0, 0.0, velocity=0)
    anim.scale.key(2, 0.3, velocity=60)       # start appearing
    anim.scale.key(4, 1.2, velocity=100)      # overshoot!
    anim.scale.key(6, 0.95, velocity=80)      # spring back
    anim.scale.key(8, 1.0, velocity=60)       # settle
    anim.scale.key(12, 1.05, velocity=30)     # subtle pulse
    anim.scale.key(16, 1.0, velocity=40)
    anim.scale.key(18, 1.02, velocity=50)     # breathing
    
    # Opacity: fade in
    anim.opacity.key(0, 0.0, velocity=0)
    anim.opacity.key(2, 0.3, velocity=60)
    anim.opacity.key(4, 1.0, velocity=100)    # full reveal at beat 4
    anim.opacity.key(16, 1.0, velocity=30)
    anim.opacity.key(18, 0.8, velocity=50)    # gentle fade
    
    # Color: hue shift
    anim.color_hue.key(0, 0.6, velocity=0)       # blue
    anim.color_hue.key(4, 0.55, velocity=80)      # blue-purple
    anim.color_hue.key(8, 0.45, velocity=60)      # purple
    anim.color_hue.key(12, 0.35, velocity=40)     # warm
    anim.color_hue.key(16, 0.6, velocity=50)      # back to blue
    anim.color_hue.key(18, 0.55, velocity=60)     # settle
    
    # Print score
    print(f"Animation: {anim.name}")
    print(f"Tempo: {anim.tempo_bpm} BPM ({anim.bps:.2f} beats/sec)")
    print(f"Lattice: E{anim.lattice} ({anim.lattice} divisions/beat)")
    print(f"Duration: {anim.duration_beats():.0f} beats = {anim.duration_seconds():.1f}s")
    print()
    
    print("Score (keyframes as MIDI notes):")
    for prop in anim.properties:
        print(f"\n  Channel {prop.channel} — {prop.name}:")
        for kf in sorted(prop.keyframes, key=lambda k: k["beat"]):
            bar = "█" * (kf["velocity"] // 8)
            print(f"    Beat {kf['beat']:5.1f} │ val={kf['value']:+6.2f} │ vel={kf['velocity']:3} {bar}")
    
    # Key insight: total keyframe count
    total_kfs = sum(len(p.keyframes) for p in anim.properties)
    total_frames = int(anim.duration_seconds() * 30)
    compression = total_frames / total_kfs if total_kfs > 0 else 0
    
    print()
    print(f"Compression: {total_kfs} keyframes → {total_frames} frames = {compression:.0f}x")
    print(f"Score size: ~{total_kfs * 20} bytes vs {total_frames * 100} bytes raw = {total_frames * 100 / (total_kfs * 20):.0f}x smaller")
    
    # Render
    output_dir = os.path.dirname(__file__)
    anim.render_html_player(os.path.join(output_dir, "animation_demo.html"))
    
    # Save VMS
    vms_path = os.path.join(output_dir, "animation_demo.vms")
    with open(vms_path, 'w') as f:
        json.dump(anim.to_vms(), f, indent=2)
    print(f"✓ VMS score saved to {vms_path}")
    
    return anim


if __name__ == "__main__":
    create_demo_animation()
