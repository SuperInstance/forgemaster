# FLUX-Tensor-MIDI — C Implementation

High-performance C implementation of FLUX-Tensor-MIDI for embedded systems (ESP32, Jetson) and anywhere you need a lightweight, zero-dependency MIDI ensemble engine.

## Architecture

```
FLUX Vector (9-channel intent)
    ↓
T-Zero Clock (adaptive EWMA timing)
    ↓
Eisenstein Snap (rhythmic classification)
    ↓
RoomMusician (per-room state)
    ↓
Ensemble (full band management)
```

## Key Types

| Type | Purpose |
|------|---------|
| `FluxVector` | 9-channel (salience, tolerance) intent vector |
| `TZeroClock` | Adaptive interval clock with EWMA smoothing |
| `SnapResult` | Eisenstein lattice classification of rhythm pairs |
| `RoomMusician` | A PLATO room participating in the ensemble |
| `MidiEvent` | Unified MIDI + side-channel event |
| `SideSignal` | Nod, smile, frown — non-verbal ensemble signals |
| `HarmonyScore` | Multi-layer alignment between rooms |
| `Ensemble` | Full band of RoomMusicians |

## Building

```bash
mkdir build && cd build
cmake ..
make
ctest --output-on-failure
```

### Requirements
- C99 compiler (gcc, clang, arm-none-eabi-gcc)
- CMake 3.10+
- No external dependencies

### Cross-compilation (ESP32)

```bash
cmake -DCMAKE_TOOLCHAIN_FILE=toolchain-esp32.cmake ..
```

### ARM NEON

Key inner loops (flux_distance, flux_cosine, flux_blend) are candidates for NEON vectorization. The C99 reference implementation works everywhere; platform-specific intrinsics can be added via preprocessor guards.

## Use Cases

- **ESP32**: Real-time MIDI ensemble with <1ms timing jitter
- **Jetson Nano**: Multi-room simulation with NEON acceleration
- **Desktop**: Reference implementation and testing
- **Embedded Linux**: Headless ensemble coordination

## Eisenstein Snap

Interval pairs (a, b) are projected onto the Eisenstein integer lattice Z[w] where w = e^{2πi/3}. The rounded lattice point classifies rhythm into:

| Shape | Condition | Meaning |
|-------|-----------|---------|
| Burst | b/a ≥ 3.0 | Rapid-fire onset |
| Accel | 1.5 ≤ b/a < 3.0 | Gradual speedup |
| Steady | 0.7 ≤ b/a < 1.5 | Regular pulse |
| Decel | 0.3 ≤ b/a < 0.7 | Gradual slowdown |
| Collapse | b/a < 0.3 | Deceleration to stop |

## License

MIT
