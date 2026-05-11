# FLUX-Tensor-MIDI Publish Log

## Published

| Registry | Package | Version | Status | URL |
|----------|---------|---------|--------|-----|
| **crates.io** | `flux-tensor-midi` | 0.1.0 | ✅ LIVE | https://crates.io/crates/flux-tensor-midi |
| **PyPI** | `flux-tensor-midi` | 0.1.0 | ✅ LIVE | https://pypi.org/project/flux-tensor-midi/0.1.0/ |
| **npm** | `@superinstance/flux-tensor-midi` | 0.1.0 | 🔴 BLOCKED | npm token expired (401) |

## Blocked — Needs Casey's Keys

| Registry | Package | Version | Blocker | What's Ready |
|----------|---------|---------|---------|-------------|
| **npm** | `@superinstance/flux-tensor-midi` | 0.1.0 | Token expired, need OTP to refresh | `js/index.js` (10.8KB ESM, zero deps, full API) + `js/package.json` |
| **Fortran Package Manager** | N/A | N/A | No registry for Fortran | `fortran/` compiled, 32/32 tests, static library |
| **C/C++ Package** | N/A | N/A | No standard registry (vcpkg/conan possible later) | `c/` compiled, 4/4 tests, CMake + static lib |
| **CUDA** | N/A | N/A | No registry, GPU-specific | `cuda/` compiled, batch kernels |

## What's In Each Package

### crates.io (Rust) — 23 files, 96.3 KiB
- `FluxVector` (9-channel intent), `TZeroClock` (EWMA adaptive)
- `RoomMusician`, `MidiEvent`, `Band`, `Score`
- `Nod`/`Smile`/`Frown` side-channels
- `HarmonyState` with chord quality (11 types)
- DCT spectral analysis on flux profiles
- Optional serde feature for serialization
- 109 tests

### PyPI (Python) — 37.3 KiB wheel
- Same API as Rust, pure Python (3.10+)
- Zero external dependencies
- 219 tests across 12 test files
- `pyproject.toml` ready for `pip install flux-tensor-midi`

### npm (JS) — Ready but blocked
- ESM module, zero dependencies, Node.js >= 18
- `FluxVector`, `TZeroClock`, `RoomMusician`, `Band`, `Score`
- Eisenstein snap, rhythmic ratio classification
- Side-channels (Nod, Smile, Frown)
- VMS score encoder/decoder

## Publish Commands (for when keys arrive)

```bash
# npm — needs fresh token
cd flux-tensor-midi/js
npm login  # Casey does this with OTP
npm publish --access public

# Fortran — no registry, but can distribute via GitHub Releases
# C/C++ — vcpkg or conan recipe possible
```

## Cumulative Published (all time)

| Registry | Count | Packages |
|----------|-------|----------|
| crates.io | 18 | constraint-theory-core, ct-demo, flux-lucid (5 versions), holonomy-consensus, fleet-coordinate, polyformalism-a2a, eisenstein-*, **flux-tensor-midi** |
| PyPI | 5 | constraint-theory, polyformalism-a2a, eisenstein-snap, snapkit, **flux-tensor-midi** |
| npm | 0 | @superinstance/flux-tensor-midi (READY, blocked by token) |

## Session Publish Stats
- **2 packages published** this session (crates.io + PyPI)
- **1 package ready** (npm, blocked by token)
- **2 additional implementations** (C+CUDA, Fortran — no registries)
