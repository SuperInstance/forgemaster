# FLUX-Tensor-MIDI

> Musical protocol for fleet coordination — PLATO rooms as musicians, tiles as notes, FLUX as intent.

## The Big Idea

PLATO rooms are musicians. Each room has a **tempo**, produces **timestamped events** (tiles = notes), listens to other rooms, snaps to their rhythm, and sends side-channel signals (nods, smiles, frowns).

FLUX-Tensor-MIDI makes this real using actual MIDI concepts.

```
FLUX    = the 9-channel intent vector (salience + tolerance per channel)
Tensor  = multi-dimensional state (time, intent, harmony, side-channels)
MIDI    = Musical Instrument Digital Interface — the universal protocol for timed events
```

## The Mapping

| Musical Concept | FLUX-Tensor-MIDI | Fleet/PLATO |
|----------------|------------------|-------------|
| Quarter note | Base interval μ | Room's T-0 interval |
| Tempo (BPM) | T-0 frequency | How often room ticks |
| Time signature | Eisenstein snap lattice | Rhythmic grid |
| Note on | Tile submitted | Room produces observation |
| Note off | Silence begins | Room stops producing |
| MIDI clock | 24 PPQN | Temporal subdivision |
| Channel 1-16 | FLUX channels | What room attends to |
| Control change | FLUX tolerance adj | Snap tolerance change |
| Velocity | Urgency | Room's priority level |
| Pitch | Room voice | Room's identity/role |
| Nod | Side-channel | Async handoff cue |
| Smile | Side-channel | Affirmation (in tolerance) |
| Frown | Side-channel | Delta detected |
| Crescendo | Increasing tiles | Activity increasing |
| Fermata | Extended wait | Hold beyond T-0 |
| Rest | Silence | No tile at T-0 |
| Unison | 100% Jaccard | Identical timing |
| Chord | Partial harmony | Related intervals |
| Solo | One room active | Forge-like creative burst |
| Comping | Support rhythm | Fleet_health metronome |
| Trading fours | Alternating bursts | Anti-coupled rooms |

## Quick Start

```python
from flux_tensor_midi import RoomMusician, FluxVector, Band

# Create rooms — each is a musician
sonar = RoomMusician(room_id="sonar", instrument="sonar", tempo_bpm=60)
engine = RoomMusician(room_id="engine", instrument="engine", tempo_bpm=30)

# Put them in a band
band = Band(name="cocapn")
band.add(sonar)
band.add(engine)

# Listen and snap — rhythmic alignment
sonar.listen_to(engine)
engine.listen_to(sonar)

# Perform — each tick produces a MIDI event
event = sonar.perform(observation={"depth": 100})
print(event)  # MidiEvent(note_on, ch=1, pitch=60, vel=80)

# Export the session as a real .mid file
band.save_midi("session.mid")
```

## Architecture

```
flux_tensor_midi/
├── core/          # RoomMusician, FLUX vector, tensor, clock, snap
├── midi/          # MIDI events, clock, channels, transport
├── sidechannel/   # Nod, Smile, Frown, Breath protocols
├── harmony/       # Jaccard, connectome, spectrum, chord analysis
├── git_native/    # Git session management, commit events, PLATO bridge
├── ensemble/      # Band, conductor-less coordination, score
└── adapters/      # PLATO adapter, MIDI file export, OSC bridge
```

## Zero Dependencies

The core library uses only Python stdlib. MIDI file export, Eisenstein snap, FLUX adaptation — all pure Python.

## License

MIT
