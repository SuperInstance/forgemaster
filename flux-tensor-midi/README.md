# FLUX-Tensor-MIDI ⚒️🎵

**PLATO rooms as musicians. MIDI as the universal timing protocol. Side-channels as nods, smiles, and frowns.**

[![crates.io](https://img.shields.io/crates/v/flux-tensor-midi.svg)](https://crates.io/crates/flux-tensor-midi)
[![PyPI](https://img.shields.io/pypi/v/flux-tensor-midi.svg)](https://pypi.org/project/flux-tensor-midi/)

## Install

```bash
# Python
pip install flux-tensor-midi

# Rust
cargo add flux-tensor-midi

# JavaScript (coming soon — npm token renewal pending)
npm install @superinstance/flux-tensor-midi
```

## What Is It?

FLUX-Tensor-MIDI is a coordination protocol where each agent, sensor, robot joint, or animated element is a **musician** in a **band**:

- Each has its own **T-0 clock** (temporal expectation)
- They **listen** to each other's events
- They **snap** to shared rhythm via the Eisenstein lattice
- They send **side-channel signals** (nods = "your turn", smiles = "looks good", frowns = "something's off")
- No central conductor. No shared clock. Just the band playing.

The protocol works for:
- 🤖 **Robotics** — 6-DOF arm joints as musicians, pick-and-place as a chord
- 🏭 **CNC/CAM** — G-code as MIDI scores, feed rate = velocity, rapid = staccato
- 🎮 **Game NPCs** — Dialogue as trading fours, reaction time = snap delta
- ✨ **Animation** — Keyframes as notes, 66x compression over raw frames
- 📡 **IoT Sensors** — Different sample rates as different tempos, anomaly = groove change
- 🎬 **Video Production** — Scenes as notes, cuts as beats, Eisenstein grid = the feel

## Quick Start

```python
from flux_tensor_midi.core.room import RoomMusician
from flux_tensor_midi.core.clock import TZeroClock
from flux_tensor_midi.core.flux import FluxVector
from flux_tensor_midi.ensemble.band import Band

# Create a band
band = Band(name="my_robot", bpm=72.0)

# Create musicians (robot joints)
base = RoomMusician(name="base_rotation", clock=TZeroClock(bpm=30))
elbow = RoomMusician(name="elbow", clock=TZeroClock(bpm=60))
gripper = RoomMusician(name="gripper", clock=TZeroClock(bpm=120))

band.add_musician(base)
band.add_musician(elbow)
band.add_musician(gripper)

# Everyone listens
band.everyone_listens_to_everyone()

# Base completes rotation, nods to gripper
base.send_nod(gripper, intensity=0.9)  # "I'm done, your turn"

# Tick the whole band
events = band.tick_all()
```

## Video-as-Score (VMS)

Encode video mockups as MIDI scores — time is first-class:

```python
from vms import VideoScore, SceneEvent, SceneType, Channel

score = VideoScore("product_demo", tempo_bpm=72)

# Hero shot at beat 0, 4 beats long
score.add_scene(SceneEvent(
    beat=0, scene_type=SceneType.PRODUCT_CLOSEUP, 
    duration_beats=4, velocity=100, channel=Channel.VISUAL
))

# Title appears at beat 2 (off-beat = syncopated)
score.add_scene(SceneEvent(
    beat=2, scene_type=SceneType.TITLE_CARD,
    duration_beats=3, velocity=70, channel=Channel.TEXT,
    text_content="FLUX-Tensor-MIDI"
))

# Export to standard MIDI (opens in any DAW)
from flux_tensor_midi.adapters.daw_bridge import DawBridge
bridge = DawBridge()
bridge.export_midi(score, "demo.mid")  # 920 bytes for a 17.9s video
```

## The Ether Principle

The best timing system is one nobody notices. The Eisenstein snap is **ether** — it attracts to the nearest lattice point so gently that the correction is below perception. Like gravity: you don't feel the pull, everything just orbits.

- **Bad:** "Wait for the click... NOW."
- **Good:** "Here's the grid, snap to it."
- **Invisible:** "What grid? We were just playing."

## Poly-Language

| Language | Tests | Package |
|----------|-------|---------|
| Python 3.10+ | 219 | `pip install flux-tensor-midi` |
| Rust | 109 | `cargo add flux-tensor-midi` |
| C99 + CUDA | 4 | Static library + GPU kernels |
| Fortran 2008 | 32 | Batch spectral analysis |
| JavaScript | — | ESM module (npm pending) |

## Side-Channel Protocol

Musicians don't coordinate through notes alone. They use glances, nods, smiles:

| Signal | Meaning | When |
|--------|---------|------|
| **Nod** | "Your turn" / "Ready" | Handoff between rooms |
| **Smile** | "Looks good" / "In tolerance" | Affirmation |
| **Frown** | "Something's off" | Delta detected |
| **Breath** | "About to act" | Pre-action signal |

## Pre-Render Forward Buffer

Rooms plan ahead like a Rubik's cube speed-solver:

- **Committed zone** (1-2 beats): Locked, executing now
- **Tentative zone** (2-4 beats): Planned, can adjust
- **Sketch zone** (2-8 beats): Rough, can scrap entirely

Planning IS a form of listening. The future is a cache. Pre-render it.

## Key Numbers

- **Eisenstein vs Z²:** 18.4% better worst-case, 8.1% better mean
- **Video compression:** 34 keyframes → 450 frames = 66x
- **CNC encoding:** 45 G-code lines → 78 MIDI events
- **IoT data reduction:** 20x by using native sensor tempos
- **Covering radius:** 1/√3 ≈ 0.577 (proven optimal for A₂)

## License

MIT

## Fleet

Part of the Cocapn fleet. Built by Forgemaster ⚒️.
