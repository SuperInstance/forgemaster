# CAM/CNC Demo: G-code as MIDI Score

Converts G-code tool paths to a Video Music Score (VMS) format. Each G-code operation becomes a musical event with velocity mapped to feed rate, duration to travel distance, and special articulations for rapid moves, dwell, and spindle events.

## Concept

```
G-code Operation     Musical Mapping
──────────────────────────────────────────────────
G0 (rapid)           → High velocity, short duration (staccato)
G1 (feed)            → Moderate velocity, legato (duration = distance/feed_rate)
G2/G3 (arc)          → Portamento (smooth transition)
G4 (dwell)           → Fermata (long held note)
M3 (spindle on)      → Percussion strike (loud)
M5 (spindle off)     → Percussion release
M6 (tool change)     → Program change (new instrument)
Low feed + deep cut  → Chatter warning (dissonant side-channel)
```

## Features

- **Full G-code parser**: Handles G0-G4, M3-M6, M8-M9, M30, comments, arcs, and tool changes
- **VMS score export**: 123+ events with scene types, velocities, durations, and metadata
- **Feed rate profile**: Each event's velocity = feed rate / 10 (clamped to 0-127)
- **Motion channel**: Feed rate mapped as motion intensity
- **Chatter detection**: Low feed rate + deep Z while spindle on → side-channel warning
- **HTML visualization**: Interactive score with:
  - XY toolpath trace (color-coded by move type)
  - MIDI-style note bars
  - Feed rate profile chart
  - Chatter detection table
  - Raw event data
- **GCodeRoom band**: RoomMusician-based axis processors with 5 musicians (axis X, Y, Z, spindle, chatter monitor)

## Sample G-code

`sample_pocket.nc` — 50mm × 30mm pocket roughing operation, 5mm deep with 4 depth passes + finish pass (74 parsed lines).

## Run

```bash
cd demos/cam/
python3 demo_cam.py
```

## Output

- `pocket_operation.vms` — VMS score of the full tool path
- `gcode_midi_score.html` — Interactive HTML visualization
- Console output showing parsed G-code stats, harmony analysis, and chatter detection

## Harmony Analysis

The demo computes CAM "harmony" based on velocity and feed rate consistency:
- **Stable cutting**: Harmony score near 1.0 (consistent feed rates)
- **Chatter risk**: Harmony drops below 0.5 (feed rate drops or velocity spikes)
- **Mean band coherence**: ~0.20 (axes move independently, as expected for independent motions)

## Technical Notes

- G-code positions are normalized into 9-channel FluxVectors
- The chatter monitor is a dedicated RoomMusician that emits dissonant vectors and sends high-intensity nods to the spindle when it detects low-feed deep cuts
- HTML visualization uses inline SVG for toolpath and feed rate chart
