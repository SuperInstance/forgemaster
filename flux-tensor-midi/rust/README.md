# FLUX-Tensor-MIDI ⚒️

**PLATO rooms as musicians with T-0 clocks, Eisenstein rhythmic snap, and side-channel communication.**

A zero-dependency Rust crate for modeling musical rooms where flux vectors express musician intensity, thermodynamic-zero clocks track timing without thermal noise, and Eisenstein lattice snap ratios classify rhythm.

## 🏗 Architecture

```
flux-tensor-midi/
├── core/        # FluxVector (9 channels), TZeroClock, RoomMusician, SnapRatio
├── midi/        # MidiEvent, MidiClock, MidiChannelConfig/Map
├── sidechannel/ # Nod, Smile, Frown — non-verbal room signals
├── harmony/     # Jaccard similarity, DCT spectrum, ChordQuality
└── ensemble/    # Band (collective), Score (musical score)
```

## 🧠 Key Concepts

### FluxVector
A 9-channel signed intensity vector representing all musicians in a room. Each channel carries `i8` intensity in [-128, 127] with optional cluster assignments.

```rust
use flux_tensor_midi::*;

let room = FluxVector::uniform(64);
println!("Energy: {}", room.energy());         // 9 * 64² = 36,864
println!("L2 distance: {}", room.l2_distance(&FluxVector::uniform(0))); // ~192.0
```

### TZeroClock
A Thermodynamic-Zero clock using Exponential Weighted Moving Average (EWMA) for temporal smoothing at absolute zero — no thermal noise. The half-life parameter configures the smoothing rate.

```rust
use flux_tensor_midi::TZeroClock;

let mut clock = TZeroClock::with_half_life(4.0);
clock.record(10.0);
clock.record(20.0);
clock.record(15.0);
println!("EWMA: {:.4}", clock.ema);
println!("Deviation: {:.4}", clock.deviation());
```

### Eisenstein Snap
Rhythmic classification using the Eisenstein integer lattice with a covering radius of `1/√3`. Interval ratios snap to standard rhythmic classes when the lattice distance is ≤ 1.

```rust
use flux_tensor_midi::*;

let ratio = SnapRatio::new(1, 2);      // eighth note
println!("Class: {}", ratio.classify()); // "Half"
println!("Snaps to beat? {}", ratio.snaps_to(SnapRatio::new(1, 1))); // false

let best = best_snap(0.48, 16).unwrap();
println!("Best snap: {}/{}", best.p, best.q); // 1/2
```

### Side Channels
Non-verbal communication between musicians in a PLATO room. Nods (approval), Smiles (delight), Frowns (disapproval) — carried alongside MIDI data without interrupting the primary stream.

```rust
use flux_tensor_midi::*;

let nod = Nod::new(60, 100);
let smile = Smile::from_cc(7, 127);
let frown = Frown::from_midi_note_off(64, 30);

println!("{}", nod);   // "Nod(note=60 intensity=100)"
println!("{}", smile); // "Smile(source=7 warmth=127 😊)"
println!("{}", frown); // "Frown(note=64 displeasure=30)"
```

### Harmony Analysis
Jaccard similarity for comparing active channel sets, DCT-II spectral analysis for spatial frequency, and chord quality detection (Major, Minor, Dim, Aug, Dom7, etc.).

```rust
use flux_tensor_midi::*;

let a = FluxVector::uniform(100);
let b = FluxVector::uniform(64);
println!("Jaccard: {:.4}", jaccard_active(&a, &b));

let spectrum = flux_dct(&[127, 0, 0, 0, 0, 0, 0, 0, 0]);
println!("Centroid: {:.4}", spectral_centroid(&spectrum));

let quality = ChordQuality::from_active_channels(&[0, 4, 7]);
println!("Quality: {quality}"); // "Major"
```

### Band & Score
A `Band` manages up to 9 musicians. A `Score` captures a sequence of events with rhythmically-snapped timing.

```rust
use flux_tensor_midi::*;

let mut band = Band::with_musicians("Jazz Trio", &["Piano", "Bass", "Drums"]);

// Send MIDI events
band.play_midi(&MidiEvent::note_on(60, 100), 1.0);
band.play_midi(&MidiEvent::note_on(64, 80), 2.0);
band.play_midi(&MidiEvent::note_on(67, 90), 3.0);

println!("{}", band); // "Band 'Jazz Trio' (3 musicians, energy=...)"
println!("Harmony: {}", band.harmony.quality);

// Build a score
let score = Score::from_events(
    "Contrafact",
    "Jazz Trio",
    &[MidiEvent::note_on(60, 100)],
    &[0.0],
    None,
    120.0,
);
println!("{score}");
```

## 🎯 Features

- **Zero external deps** (core) — `no_std` compatible
- **Optional serde** — enable with `features = ["serde"]`
- **DCT-II spectral analysis** — 9-bin harmonic spectrum
- **Eisenstein lattice snap** — covering radius `1/√(3)` rhythmic classification
- **9-channel flux vectors** — with cluster assignments
- **EWMA T-0 clocks** — with half-life configuration
- **Chord quality detection** — 11 chord types including extensions
- **Side-channel signals** — Nod, Smile, Frown with confidence metrics
- **MIDI mapping** — 16 MIDI channels → 9 flux channels

## 📦 Installation

```toml
[dependencies]
flux-tensor-midi = "0.1.0"

# With serde support:
flux-tensor-midi = { version = "0.1.0", features = ["serde"] }
```

## 🧪 Testing

```bash
cargo test
cargo test --features serde
```

## 📄 License

MIT
