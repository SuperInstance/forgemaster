#!/usr/bin/env python3
"""
vms-render — Render a .vms video score into an HTML5 visual player.

The output is a single HTML file that plays the video score visually:
- Timeline with beat grid
- Per-channel layers color-coded
- Side-channel signals (nods, smiles, frowns) as icons
- Velocity mapped to opacity/intensity
- Eisenstein snap grid shown as vertical lines
- Play/pause with real-time playback

Usage:
    python vms-render.py demo.vms demo-player.html
"""

import json
import math
import sys
from pathlib import Path

# Import from vms.py
sys.path.insert(0, str(Path(__file__).parent))
from vms import load_vms, Channel, SceneType, SideChannel


# Channel colors (Tailwind-inspired)
CHANNEL_COLORS = {
    Channel.VISUAL: "#3B82F6",      # Blue
    Channel.TEXT: "#10B981",         # Green
    Channel.AUDIO: "#F59E0B",        # Amber
    Channel.COLOR: "#EC4899",        # Pink
    Channel.MOTION: "#8B5CF6",      # Purple
    Channel.EFFECTS: "#6366F1",     # Indigo
    Channel.DATA: "#14B8A6",        # Teal
    Channel.SIDECHANNEL: "#EF4444", # Red
    Channel.META: "#6B7280",        # Gray
}

CHANNEL_NAMES = {
    Channel.VISUAL: "Visual",
    Channel.TEXT: "Text",
    Channel.AUDIO: "Audio",
    Channel.COLOR: "Color",
    Channel.MOTION: "Motion",
    Channel.EFFECTS: "Effects",
    Channel.DATA: "Data",
    Channel.SIDECHANNEL: "Side",
    Channel.META: "Meta",
}

SCENE_ICONS = {
    SceneType.PRODUCT_CLOSEUP: "🎬",
    SceneType.USER_INTERACTION: "👤",
    SceneType.RESULT_DISPLAY: "📊",
    SceneType.WIDE_SHOT: "🌄",
    SceneType.DETAIL_SHOT: "🔍",
    SceneType.SPLIT_SCREEN: "⊞",
    SceneType.ANIMATION: "✨",
    SceneType.DATA_VIZ: "📈",
    SceneType.TITLE_CARD: "📝",
    SceneType.CALL_TO_ACTION: "🎯",
    SceneType.BROLL: "🎞",
    SceneType.TRANSITION: "⚡",
}


def render_html(score, output_path: str):
    """Render a VideoScore as an interactive HTML player."""
    total_beats = score.duration_beats()
    total_seconds = score.duration_seconds()
    beats_per_second = score.tempo_bpm / 60.0
    
    # Group events by channel for the track view
    channels_used = sorted(set(e.channel for e in score.events))
    
    # Build timeline data as JSON
    timeline_events = []
    for e in score.events:
        evt = {
            "beat": e.beat,
            "time": round(e.beat / beats_per_second, 3),
            "channel": e.channel,
            "channelName": CHANNEL_NAMES.get(e.channel, f"Ch{e.channel}"),
            "color": CHANNEL_COLORS.get(e.channel, "#888"),
            "sceneType": SceneType(e.scene_type).name,
            "icon": SCENE_ICONS.get(e.scene_type, "•"),
            "velocity": e.velocity,
            "durationBeats": e.duration_beats,
            "durationSeconds": round(e.duration_beats / beats_per_second, 3),
            "text": e.text_content,
            "motion": e.motion_type,
            "mood": e.color_mood,
            "effect": e.effect_type,
        }
        if e.meta:
            evt["meta"] = e.meta
        timeline_events.append(evt)
    
    # Snap grid points
    grid_points = []
    for i in range(int(total_beats * score.lattice.divisions) + 1):
        beat = i / score.lattice.divisions
        if beat <= total_beats:
            is_major = (i % score.lattice.divisions == 0)
            grid_points.append({
                "beat": round(beat, 4),
                "time": round(beat / beats_per_second, 4),
                "major": is_major,
            })
    
    events_json = json.dumps(timeline_events)
    grid_json = json.dumps(grid_points)
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FLUX-Tensor-MIDI — {score.name}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ 
    background: #0f172a; color: #e2e8f0; 
    font-family: 'SF Mono', 'Fira Code', monospace;
    overflow-x: hidden;
  }}
  
  .header {{
    padding: 20px 30px;
    background: linear-gradient(135deg, #1e293b, #0f172a);
    border-bottom: 1px solid #334155;
  }}
  .header h1 {{ font-size: 1.4rem; color: #3B82F6; }}
  .header .meta {{ font-size: 0.8rem; color: #64748b; margin-top: 4px; }}
  
  .stats {{
    display: flex; gap: 20px; padding: 15px 30px;
    background: #1e293b; border-bottom: 1px solid #334155;
  }}
  .stat {{ text-align: center; }}
  .stat .value {{ font-size: 1.5rem; color: #3B82F6; font-weight: bold; }}
  .stat .label {{ font-size: 0.7rem; color: #64748b; text-transform: uppercase; }}
  
  .timeline-container {{
    position: relative;
    padding: 20px 30px;
    overflow-x: auto;
  }}
  
  .playback-bar {{
    position: sticky; top: 0; z-index: 100;
    background: #1e293b; padding: 10px 30px;
    border-bottom: 1px solid #334155;
    display: flex; align-items: center; gap: 15px;
  }}
  .play-btn {{
    background: #3B82F6; color: white; border: none;
    padding: 8px 20px; border-radius: 6px; cursor: pointer;
    font-family: inherit; font-size: 0.9rem;
  }}
  .play-btn:hover {{ background: #2563EB; }}
  .time-display {{ color: #94a3b8; font-size: 0.9rem; }}
  .tempo-badge {{ 
    background: #1e1b4b; color: #818cf8; padding: 2px 8px; 
    border-radius: 4px; font-size: 0.75rem; 
  }}
  
  .track-labels {{
    position: sticky; left: 0; z-index: 50;
    width: 80px; float: left;
  }}
  .track-label {{
    height: 48px; line-height: 48px;
    font-size: 0.7rem; color: #64748b;
    text-transform: uppercase;
  }}
  
  .tracks-scroll {{ margin-left: 80px; position: relative; }}
  
  .track-row {{
    height: 48px; position: relative;
    border-bottom: 1px solid #1e293b;
  }}
  
  .event-block {{
    position: absolute; top: 6px; bottom: 6px;
    border-radius: 6px; cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.2rem;
    transition: transform 0.1s, box-shadow 0.1s;
    overflow: hidden; white-space: nowrap;
  }}
  .event-block:hover {{
    transform: scaleY(1.1);
    box-shadow: 0 0 12px rgba(59, 130, 246, 0.4);
    z-index: 10;
  }}
  
  .grid-line {{
    position: absolute; top: 0; bottom: 0; width: 1px;
    background: #1e293b;
  }}
  .grid-line.major {{ background: #334155; }}
  
  .playhead {{
    position: absolute; top: 0; bottom: 0; width: 2px;
    background: #ef4444; z-index: 20;
    transition: left 0.05s linear;
  }}
  
  .side-channel-block {{
    border: 2px dashed;
    opacity: 0.8;
  }}
  
  .side-nod {{ border-color: #10B981; background: rgba(16, 185, 129, 0.1); }}
  .side-smile {{ border-color: #F59E0B; background: rgba(245, 158, 11, 0.1); }}
  .side-frown {{ border-color: #EF4444; background: rgba(239, 68, 68, 0.1); }}
  .side-breath {{ border-color: #8B5CF6; background: rgba(139, 92, 246, 0.1); }}
  
  .tooltip {{
    display: none; position: fixed; z-index: 1000;
    background: #1e293b; border: 1px solid #475569;
    border-radius: 8px; padding: 12px; max-width: 300px;
    font-size: 0.75rem; line-height: 1.5;
    box-shadow: 0 4px 20px rgba(0,0,0,0.5);
  }}
  .tooltip.visible {{ display: block; }}
  .tooltip .tt-title {{ color: #3B82F6; font-weight: bold; margin-bottom: 4px; }}
  .tooltip .tt-key {{ color: #64748b; }}
  .tooltip .tt-val {{ color: #e2e8f0; }}
  
  .legend {{
    padding: 15px 30px; display: flex; gap: 15px; flex-wrap: wrap;
    border-top: 1px solid #334155; margin-top: 20px;
  }}
  .legend-item {{ display: flex; align-items: center; gap: 6px; font-size: 0.75rem; }}
  .legend-dot {{ width: 10px; height: 10px; border-radius: 3px; }}
  
  .current-scene {{
    position: fixed; bottom: 20px; right: 20px;
    background: #1e293b; border: 1px solid #334155;
    border-radius: 12px; padding: 16px 20px;
    min-width: 200px; z-index: 100;
  }}
  .current-scene .cs-title {{ font-size: 0.7rem; color: #64748b; text-transform: uppercase; }}
  .current-scene .cs-value {{ font-size: 1rem; color: #e2e8f0; margin-top: 2px; }}
</style>
</head>
<body>

<div class="playback-bar">
  <button class="play-btn" id="playBtn">▶ Play</button>
  <span class="time-display" id="timeDisplay">0:00.000 / {total_seconds:.3f}s</span>
  <span class="tempo-badge">♩ {score.tempo_bpm} BPM</span>
  <span class="tempo-badge">E{score.lattice.divisions}</span>
  <span class="tempo-badge">Entropy: {score.temporal_entropy():.2f} bits</span>
  <span class="tempo-badge">{score.rhythm_quality()}</span>
</div>

<div class="header">
  <h1>🎵 {score.name}</h1>
  <div class="meta">
    {len(score.events)} events · {total_beats:.1f} beats · {total_seconds:.1f}s · 
    Eisenstein E{score.lattice.divisions} lattice · {len(channels_used)} channels
  </div>
</div>

<div class="stats">
  <div class="stat"><div class="value">{score.tempo_bpm}</div><div class="label">BPM</div></div>
  <div class="stat"><div class="value">{total_seconds:.1f}s</div><div class="label">Duration</div></div>
  <div class="stat"><div class="value">{len(score.events)}</div><div class="label">Events</div></div>
  <div class="stat"><div class="value">{len([e for e in score.events if e.channel == 1])}</div><div class="label">Scenes</div></div>
  <div class="stat"><div class="value">{score.temporal_entropy():.2f}</div><div class="label">Entropy</div></div>
  <div class="stat"><div class="value" style="color:#10B981">{score.rhythm_quality()}</div><div class="label">Feel</div></div>
</div>

<div class="timeline-container" id="timeline">
  <div class="track-labels" id="trackLabels"></div>
  <div class="tracks-scroll" id="tracksScroll">
    <div class="playhead" id="playhead"></div>
  </div>
</div>

<div class="legend">
  {"".join(f'<div class="legend-item"><div class="legend-dot" style="background:{CHANNEL_COLORS.get(ch, "#888")}"></div>{CHANNEL_NAMES.get(ch, f"Ch{ch}")}</div>' for ch in channels_used)}
</div>

<div class="tooltip" id="tooltip">
  <div class="tt-title" id="ttTitle"></div>
  <div id="ttBody"></div>
</div>

<div class="current-scene" id="currentScene">
  <div class="cs-title">Now Playing</div>
  <div class="cs-value" id="csValue">—</div>
</div>

<script>
const events = {events_json};
const grid = {grid_json};
const totalBeats = {total_beats};
const bps = {beats_per_second:.4f};
const pxPerBeat = 100;
const trackLabels = document.getElementById('trackLabels');
const tracksScroll = document.getElementById('tracksScroll');
const playhead = document.getElementById('playhead');
const playBtn = document.getElementById('playBtn');
const timeDisplay = document.getElementById('timeDisplay');
const tooltip = document.getElementById('tooltip');
const channelsUsed = {json.dumps(channels_used)};

// Build tracks
const channelColors = {json.dumps({str(k): v for k, v in CHANNEL_COLORS.items()})};
const channelNames = {json.dumps({str(k): v for k, v in CHANNEL_NAMES.items()})};

const sideTypes = {{'nod': 'side-nod', 'smile': 'side-smile', 'frown': 'side-frown', 'breath': 'side-breath'}};

channelsUsed.forEach(ch => {{
  const label = document.createElement('div');
  label.className = 'track-label';
  label.textContent = channelNames[ch] || 'Ch' + ch;
  label.style.color = channelColors[ch];
  trackLabels.appendChild(label);
  
  const row = document.createElement('div');
  row.className = 'track-row';
  row.dataset.channel = ch;
  
  // Add grid lines
  grid.forEach(g => {{
    const line = document.createElement('div');
    line.className = 'grid-line' + (g.major ? ' major' : '');
    line.style.left = (g.beat * pxPerBeat) + 'px';
    row.appendChild(line);
  }});
  
  // Add events
  events.filter(e => e.channel === ch).forEach(e => {{
    const block = document.createElement('div');
    block.className = 'event-block';
    const isSide = ch === 8;
    if (isSide && e.meta && e.meta.type) {{
      block.classList.add('side-channel-block', sideTypes[e.meta.type] || '');
    }}
    block.style.left = (e.beat * pxPerBeat) + 'px';
    block.style.width = Math.max(e.durationBeats * pxPerBeat, 8) + 'px';
    const alpha = Math.max(0.2, e.velocity / 127);
    const color = channelColors[ch] || '#888';
    block.style.background = isSide ? '' : color + Math.round(alpha * 255).toString(16).padStart(2, '0');
    block.style.borderLeft = '3px solid ' + color;
    block.textContent = e.icon;
    block.title = e.sceneType;
    
    // Tooltip
    block.addEventListener('mouseenter', ev => {{
      document.getElementById('ttTitle').textContent = e.icon + ' ' + e.sceneType;
      let body = '<div><span class="tt-key">Beat:</span> <span class="tt-val">' + e.beat.toFixed(2) + '</span></div>';
      body += '<div><span class="tt-key">Time:</span> <span class="tt-val">' + e.time.toFixed(3) + 's</span></div>';
      body += '<div><span class="tt-key">Velocity:</span> <span class="tt-val">' + e.velocity + '</span></div>';
      body += '<div><span class="tt-key">Duration:</span> <span class="tt-val">' + e.durationBeats.toFixed(1) + ' beats (' + e.durationSeconds.toFixed(2) + 's)</span></div>';
      if (e.text) body += '<div><span class="tt-key">Text:</span> <span class="tt-val">"' + e.text + '"</span></div>';
      if (e.motion) body += '<div><span class="tt-key">Motion:</span> <span class="tt-val">' + e.motion + '</span></div>';
      if (e.mood) body += '<div><span class="tt-key">Mood:</span> <span class="tt-val">' + e.mood + '</span></div>';
      if (e.effect) body += '<div><span class="tt-key">Effect:</span> <span class="tt-val">' + e.effect + '</span></div>';
      if (e.meta) body += '<div><span class="tt-key">Meta:</span> <span class="tt-val">' + JSON.stringify(e.meta) + '</span></div>';
      document.getElementById('ttBody').innerHTML = body;
      tooltip.style.left = (ev.clientX + 15) + 'px';
      tooltip.style.top = (ev.clientY - 10) + 'px';
      tooltip.classList.add('visible');
    }});
    block.addEventListener('mouseleave', () => tooltip.classList.remove('visible'));
    
    row.appendChild(block);
  }});
  
  tracksScroll.appendChild(row);
}});

// Set width
tracksScroll.style.width = (totalBeats * pxPerBeat + 100) + 'px';

// Playback
let playing = false;
let startTime = 0;
let elapsed = 0;

function updatePlayhead() {{
  if (!playing) return;
  const now = performance.now();
  elapsed = (now - startTime) / 1000;
  const beat = elapsed * bps;
  
  if (beat > totalBeats) {{
    playing = false;
    playBtn.textContent = '▶ Play';
    playhead.style.left = '0px';
    elapsed = 0;
    document.getElementById('csValue').textContent = '—';
    return;
  }}
  
  playhead.style.left = (beat * pxPerBeat) + 'px';
  timeDisplay.textContent = elapsed.toFixed(3) + 's / {total_seconds:.3f}s';
  
  // Find active visual scene
  const activeVisual = events.filter(e => 
    e.channel === 1 && e.beat <= beat && (e.beat + e.durationBeats) > beat
  );
  if (activeVisual.length > 0) {{
    const scene = activeVisual[activeVisual.length - 1];
    document.getElementById('csValue').textContent = scene.icon + ' ' + scene.sceneType + ' (vel ' + scene.velocity + ')';
  }}
  
  requestAnimationFrame(updatePlayhead);
}}

playBtn.addEventListener('click', () => {{
  if (playing) {{
    playing = false;
    playBtn.textContent = '▶ Play';
  }} else {{
    playing = true;
    startTime = performance.now() - (elapsed * 1000);
    playBtn.textContent = '⏸ Pause';
    requestAnimationFrame(updatePlayhead);
  }}
}});
</script>

</body>
</html>"""

    with open(output_path, 'w') as f:
        f.write(html)
    print(f"✓ Visual player rendered to {output_path} ({len(html)} bytes)")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: vms-render.py input.vms output.html")
        sys.exit(1)
    
    score = load_vms(sys.argv[1])
    render_html(score, sys.argv[2])
