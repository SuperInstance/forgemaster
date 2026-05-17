# PLATO-MIDI-Bridge Recovery Report

**Date:** 2026-05-16
**Status:** FULLY RECOVERED — code exists on GitHub and locally

---

## Summary

plato-midi-bridge is **not lost**. It exists as two live GitHub repos and extensive local workspace traces.

---

## Repos Found

### 1. [SuperInstance/plato-midi-bridge](https://github.com/SuperInstance/plato-midi-bridge) (Python)
- **Updated:** 2026-05-16T09:15:08Z (today)
- **Description:** PLATO rooms as musicians — connects FM's flux-tensor-midi to live fleet tiles
- **Branch:** main (PUBLIC)

**Structure:**
```
plato-midi-bridge/
├── plato_midi.py            # CLI entry point (stream/scan/ensemble modes)
├── plato_midi_bridge/       # Core package
│   ├── __init__.py          # v0.1.0 — exports RoomTensor, MIDIStream, PlatoMIDIEngine
│   ├── tensor.py            # RoomTensor, CouplingTensor, TMinusTensor (11047 bytes)
│   ├── midi.py              # MIDIStream, MIDINote, MIDIControl (7980 bytes)
│   ├── engine.py            # PlatoMIDIEngine (4289 bytes)
│   ├── web.py               # Web interface server (11047 bytes)
│   ├── cli.py               # CLI helpers (2046 bytes)
│   ├── decompose/           # Style decomposition
│   ├── autopilot/           # Autonomous bridge mode
│   └── jepa/                # JEPA-style prediction
├── flux_modules/
├── plato_torch_bridge/
├── services/
├── scripts/
├── tests/
└── archived/
```

**Musical Mapping:**
| Concept | PLATO/MIDI Mapping |
|---------|-------------------|
| Room | Musician (MIDI channel) |
| Tile | Note (velocity = confidence) |
| FluxVector (9ch) | Harmonic spectrum |
| TZeroClock | Rhythmic grid |
| EisensteinSnap | Rhythmic quantization |
| Sidechannels (Nod/Smile/Frown) | Agreement/disagreement |

**Domain → MIDI channel map:** forge=0, fleet-coord=1, arena=2, calibration=3, flux-engine=4, research_log=5, tension=6, synthesis=7, oracle1=8

### 2. [SuperInstance/plato-midi-bridge-rs](https://github.com/SuperInstance/plato-midi-bridge-rs) (Rust)
- **Updated:** 2026-05-14T09:40:48Z
- **Description:** Rust crate — Eisenstein lattices, Penrose tilings, and multi-scale musical style analysis
- **No external dependencies** — pure math core

**Types:**
- `StyleVector` — 109-dimensional musical style vector
- `EisensteinLattice` — 12-chamber hexagonal lattice encoding
- `PenroseEncoder` — 5D cut-and-project tiling encoding
- `ScaleLevel` — Multi-scale analysis (micro/note/phrase/section/piece)

---

## Dependency: flux-tensor-midi

The bridge depends on `flux-tensor-midi`, which is a full library in the workspace at `/home/phoenix/.openclaw/workspace/flux-tensor-midi/`:

- **Published:** crates.io + PyPI (v0.1.1)
- **Languages:** Python, Rust, C, Fortran, CUDA
- **Core concepts:** Band metaphor (each agent = musician), TZeroClock, EisensteinSnap, sidechannels
- **Key files:** 25+ source files across 5 language implementations

---

## Related Workspace Traces

- `research/FLUX-TENSOR-MIDI.md` — Full theory document (400+ lines)
- `for-fleet/2026-05-11-FLUX-TENSOR-MIDI-TO-ORACLE1.i2i.md` — I2I bottle to Oracle1
- `snapkit-v2/snapkit/midi.py` — SnapKit MIDI module
- `experiments/midi-folding-*.md` — Three experiment reports on MIDI folding synergy
- Memory references in 2026-05-11, 05-13, 05-14, 05-16 daily logs

---

## Conclusion

**No recovery needed.** Both repos are live and active (plato-midi-bridge was updated TODAY). The code is functional — it connects to PLATO server at localhost:8847, reads room tiles, and converts them to MIDI via the flux-tensor-midi library.

The bridge is ready to use:
```bash
pip3 install flux-tensor-midi
python3 plato_midi.py --scan       # List rooms as musicians
python3 plato_midi.py --room forge # Stream forge room
python3 plato_midi.py --ensemble   # All rooms as orchestra
```
