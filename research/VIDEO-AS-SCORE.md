# VIDEO AS SCORE: Time-First Video Encoding via FLUX-Tensor-MIDI

**Date:** 2026-05-11  
**Status:** Theory + Architecture  
**Insight:** Casey — "encode video mock-ups with time as first class, more like music than a typical script"

---

## The Problem with Video Today

Traditional video is **spatial-first, temporal-uniform**:
- 24/30/60 fps — every frame is identical in importance
- Timeline is a ruler — seconds are centimeters
- Scripts describe WHAT happens, not WHEN it breathes
- Editing is manual placement on a flat track
- Layers (video, audio, text, effects) don't speak to each other temporally

Nobody watches this way. Your perception:
- Snaps to cuts (note-ons)
- Sustains through holds (fermatas)
- Drops attention during pauses (rests)
- Builds through sequences (crescendos)
- Releases at climaxes (cadences)

**Video IS music. We just encode it wrong.**

## The Solution: Video-as-Score

Instead of N frames at uniform intervals, encode video as a **MIDI score** where:

| Video Concept | MIDI/FLUX Concept | Encoding |
|--------------|-------------------|----------|
| Scene | Note (note-on to note-off) | Pitch=scene_type, velocity=intensity |
| Cut | Note boundary | Note-off + note-on, snap to beat |
| Hold/linger | Fermata | Extended duration, no note-off |
| Fade in | Crescendo | Increasing velocity over beats |
| Fade out | Decrescendo | Decreasing velocity over beats |
| Jump cut | Staccato | Short duration, high velocity |
| Long take | Legato | Tied notes across multiple beats |
| Montage | Tremolo | Rapid alternating notes |
| Static frame | Rest | No note — silence IS the content |
| Text overlay | Channel 2 | Different MIDI channel, same tempo |
| Music bed | Channel 3 | Audio layer on its own channel |
| Color grade | CC (control change) | Continuous parameter on its channel |
| Transition | Pitch bend | Sliding between scene pitches |
| B-roll | Comping | Supporting notes behind the solo |
| Title card | Solo | One element front and center |
| Lower third | Grace note | Quick decorative note before main |
| Speed ramp | Tempo change | MIDI tempo meta-event |
| Freeze frame | Fermata + sustain pedal | Hold + layer sustain |
| Split screen | Chord | Multiple notes simultaneously |
| Picture-in-picture | Channel layering | Two channels, different velocities |

## The Score Structure

A video mockup is a **MIDI file** with multiple channels, each representing a production layer:

```
Channel 1:  Primary visual (scenes, cuts, holds)
Channel 2:  Text/typography (titles, lower thirds, captions)
Channel 3:  Audio (music bed, VO, SFX)
Channel 4:  Color (grading changes, mood shifts)
Channel 5:  Motion (camera moves, animations)
Channel 6:  Effects (particles, transitions, overlays)
Channel 7:  Data (charts, numbers, live data feeds)
Channel 8:  Side-channel (nods, smiles, production cues)
```

### Channel 1: Primary Visual (the melody)

```python
# Scene: Hero shot of product, intense, 4 beats
MidiEvent(type="note_on", channel=1, pitch=60, velocity=100, timestamp=0.0)
MidiEvent(type="cc", channel=1, cc=1, value=80, timestamp=0.0)  # intensity=high
MidiEvent(type="note_off", channel=1, pitch=60, timestamp=4.0)

# Scene: User interaction, moderate, 8 beats
MidiEvent(type="note_on", channel=1, pitch=64, velocity=70, timestamp=4.0)
MidiEvent(type="note_off", channel=1, pitch=64, timestamp=12.0)

# Hold/linger on result, soft, 2 beats (fermata)
MidiEvent(type="note_on", channel=1, pitch=72, velocity=40, timestamp=12.0)
MidiEvent(type="cc", channel=1, cc=64, value=127, timestamp=12.0)  # sustain pedal ON
MidiEvent(type="cc", channel=1, cc=64, value=0, timestamp=14.0)    # sustain pedal OFF
MidiEvent(type="note_off", channel=1, pitch=72, timestamp=14.0)
```

### Channel 2: Text (the lyrics)

```python
# Title appears, aligned with scene 1
MidiEvent(type="note_on", channel=2, pitch=60, velocity=60, timestamp=0.5)
MidiEvent(type="note_off", channel=2, pitch=60, timestamp=3.5)

# Lower third for user interaction
MidiEvent(type="note_on", channel=2, pitch=48, velocity=40, timestamp=5.0)
MidiEvent(type="note_off", channel=2, pitch=48, timestamp=11.0)
```

### Channel 3: Audio (the rhythm section)

```python
# Music bed — continuous, background
MidiEvent(type="note_on", channel=3, pitch=36, velocity=30, timestamp=0.0)
MidiEvent(type="cc", channel=3, cc=7, value=60, timestamp=0.0)  # volume=60%
MidiEvent(type="cc", channel=3, cc=7, value=80, timestamp=12.0) # crescendo to 80%
MidiEvent(type="note_off", channel=3, pitch=36, timestamp=14.0)
```

### Channel 8: Side-Channel (production cues)

```python
# Nod: "ready for text layer"
MidiEvent(type="note_on", channel=8, pitch=1, velocity=1, timestamp=0.4)
# Smile: "text landed well"
MidiEvent(type="note_on", channel=8, pitch=2, velocity=1, timestamp=0.6)
# Frown: "audio needs adjustment"
MidiEvent(type="note_on", channel=8, pitch=3, velocity=1, timestamp=4.1)
```

## The Beat Grid (Eisenstein Snap)

Video doesn't breathe at uniform intervals. It snaps to a **beat grid** — the Eisenstein lattice determines where cuts LAND:

```
BPM: 60 (1 beat = 1 second — slow, cinematic)
Snap lattice: Eisenstein E₁₂ (12 divisions per beat)

Allowed cut points (in seconds):
0.000, 0.083, 0.167, 0.250, 0.333, 0.417, 0.500, 0.583, 0.667, 0.750, 0.833, 0.917,
1.000, 1.083, ...

But NOT every point is used. The snap determines the FEEL:

Snap to beat = clean cut (on the downbeat)
Snap to 0.500 = syncopated (off-beat, feels modern)
Snap to 0.333 = triplet feel (three-against-two, feels driving)
Snap to 0.250 = sixteenth note (rapid, feels urgent)
```

The producer doesn't place cuts at arbitrary times. They **snap to the nearest lattice point**. The lattice determines the feel:
- E₆ lattice → slow, spacious (documentary)
- E₁₂ lattice → standard (corporate, explainer)
- E₂₄ lattice → fast, detailed (product demo, social)

## Encoding Format: .vms (Video Music Score)

A `.vms` file IS a standard MIDI file with FLUX metadata:

```
Header:
  Format: 1 (multi-track)
  Division: 480 PPQN (24 PPQN × 20 subdivision)
  Tempo: mapped from desired pacing

Tracks:
  Track 1: Tempo map (MIDI tempo events)
  Track 2: Channel 1 — Primary visual
  Track 3: Channel 2 — Text
  Track 4: Channel 3 — Audio
  Track 5: Channel 4 — Color
  Track 6: Channel 5 — Motion
  Track 7: Channel 6 — Effects
  Track 8: Channel 7 — Data
  Track 9: Channel 8 — Side-channel cues

Meta Events:
  @scene:name "Hero product shot"
  @scene:type "product_closeup"
  @text:content "The fastest constraint solver"
  @text:position "center"
  @color:mood "warm_confident"
  @motion:type "slow_push_in"
  @effect:type "lens_flare"
  @data:source "benchmark_results.json"

FLUX Extensions (custom meta):
  @flux:channels [0.8, 0.2, 0.1, 0.0, 0.5, 0.0, 0.3, 0.0, 0.1]
  @flux:tolerance [0.1, 0.3, 0.5, 1.0, 0.2, 1.0, 0.4, 1.0, 0.6]
  @snap:lattice "E12"
  @snap:base_tempo 60
```

## The Rendering Pipeline

```
.vms (MIDI score) 
  → Parse (MIDI reader)
  → Eisenstein snap (quantize to beat grid)
  → FLUX analysis (what demands attention, when)
  → Per-channel rendering:
      Channel 1 → Visual renderer (scene generator)
      Channel 2 → Text renderer (typography engine)
      Channel 3 → Audio mixer (music + SFX)
      Channel 4 → Color engine (grading + mood)
      Channel 5 → Motion engine (camera + animation)
      Channel 6 → Effects engine (particles + transitions)
      Channel 7 → Data engine (charts + live feeds)
      Channel 8 → Production cues (side-channel processing)
  → Composite (all channels mixed by velocity)
  → Output (MP4, GIF, or interactive)
```

## The Producer Workflow

```
1. Open the score (.vms file) in any MIDI editor
   — Producers who know music understand it IMMEDIATELY
   — Piano roll = timeline, notes = scenes, velocity = intensity
   
2. Each channel is a "room" in the sound booth
   — Walk into the visual room → adjust scene timing
   — Walk into the text room → adjust title placement
   — Walk into the audio room → adjust music bed
   — They all snap to the same beat grid
   
3. Side-channels coordinate automatically
   — Text room nods to visual room: "title ready"
   — Visual room smiles: "looks good"
   — Audio room frowns: "beat doesn't align with cut"
   — FLUX adapts: tolerance tightens, snap adjusts
   
4. The assistant refactors the producer's vibe to the team
   — Producer adjusts one channel
   — FLUX propagates timing to related channels
   — The band snaps to the new groove
```

## Why This Works for Non-AI People

MIDI is 40 years old. Every musician, every producer, every sound engineer understands:
- Piano roll = timeline
- Notes = events
- Velocity = intensity
- Channels = layers
- Tempo = pacing
- Beat grid = rhythmic structure

They DON'T understand:
- Tensor operations
- Latent spaces
- Embedding dimensions
- Attention mechanisms

But they DO understand:
- "This scene hits on the downbeat"
- "The title comes in on the off-beat"
- "The music swells before the product reveal"
- "Hold that frame for two more beats"

**FLUX-Tensor-MIDI speaks their language.**

## The Information Savings

Traditional video encoding:
- 30 fps × 1920×1080 × 3 channels × 8 bits = ~186 MB/minute (raw)
- Even compressed: ~10-50 MB/minute

Video-as-Score encoding:
- MIDI events only at meaningful moments
- A 60-second video might have 200-500 MIDI events
- Each event: ~10-20 bytes
- Total: ~5-10 KB for the SCORE
- + assets (images, clips) referenced, not embedded

**The score is 0.001% the size of raw video.**
**The TIMING intelligence is in the score, not the pixels.**

This is exactly the snapkit philosophy:
- Don't store every point — store the snap
- Don't encode every frame — encode the beats
- The lattice determines the feel, not the pixel count

## Example: Product Demo in .vms

```
Tempo: 72 BPM (1 beat = 0.833s — upbeat, modern)
Lattice: E₁₂ (fine grid for snappy cuts)

Beat  0: [Ch1 NOTE_ON pitch=60 vel=100] Hero product shot
Beat  0: [Ch3 NOTE_ON pitch=36 vel=40]  Music bed starts
Beat  2: [Ch2 NOTE_ON pitch=60 vel=60]  Title: "FLUX-Tensor-MIDI"
Beat  3: [Ch1 NOTE_OFF pitch=60]        Cut!
Beat  3: [Ch1 NOTE_ON pitch=64 vel=80]  User interaction scene
Beat  3: [Ch2 NOTE_OFF pitch=60]        Title fades
Beat  5: [Ch5 CC cc=1 val=80]           Camera push-in starts
Beat  7: [Ch1 NOTE_OFF pitch=64]        Cut!
Beat  7: [Ch1 NOTE_ON pitch=72 vel=50]  Result display (softer)
Beat  7: [Ch2 NOTE_ON pitch=48 vel=40]  Lower third: "Zero drift"
Beat  9: [Ch3 CC cc=7 val=80]           Music crescendo
Beat 11: [Ch1 NOTE_OFF pitch=72]        Cut!
Beat 11: [Ch1 NOTE_ON pitch=84 vel=120] CALL TO ACTION (highest velocity)
Beat 11: [Ch2 NOTE_ON pitch=72 vel=100] Title: "Get Started"
Beat 13: [Ch1 CC cc=64 val=127]         Sustain (fermata — hold it)
Beat 15: [ALL NOTE_OFF]                 Everything stops
Beat 15: [Ch8 NOTE_ON pitch=2 vel=1]    Side-channel: smile (good take)

Total: 20 events across 8 channels for a 12.5-second video.
File size: ~400 bytes for the score.
```

## The Producer Can Riff

The producer doesn't script every frame. They:
1. Set the tempo (pacing feel)
2. Choose the lattice (rhythmic precision)
3. Place the key beats (scenes, cuts)
4. Let FLUX snap everything else
5. Walk into each room and fine-tune
6. The band plays

This is jazz, not classical.
The score is a lead sheet, not a full orchestration.
The rooms improvise within the chord changes.

---

*"Video production is jazz. The score is the lead sheet. The rooms are the musicians. The producer is the bandleader who doesn't conduct — they LISTEN and nod."*
