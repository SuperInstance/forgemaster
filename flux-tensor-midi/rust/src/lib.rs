//! # FLUX-Tensor-MIDI
//!
//! PLATO rooms as musicians with T-0 clocks, Eisenstein rhythmic snap,
//! and side-channel communication (nods, smiles, frowns).
//!
//! ## Architecture
//!
//! - **`core`** — FluxVector, FluxChannel, TZeroClock, RoomMusician, SnapRatio
//! - **`midi`** — MidiEvent, MidiClock, MidiChannelConfig/MidiChannelMap
//! - **`sidechannel`** — Nod, Smile, Frown (non-verbal room signals)
//! - **`harmony`** — Jaccard similarity, DCT spectral analysis, ChordQuality
//! - **`ensemble`** — Band (musician collective), Score (musical score)

pub mod core;
pub mod ensemble;
pub mod harmony;
pub mod midi;
pub mod sidechannel;

// Optional serde support
#[cfg(feature = "serde")]
pub mod serde_impl;

// Re-exports for convenient top-level use
pub use core::{
    best_snap, within_covering_radius, FluxChannel, FluxVector, RoomMusician, SnapClass,
    SnapRatio, TZeroClock,
};
pub use ensemble::{band::Band, score::Score};
pub use harmony::{
    chord::{ChordQuality, HarmonyState},
    jaccard::{harmonic_distance, jaccard_active, weighted_jaccard},
    spectrum::{dominant_bin, flux_dct, spectral_centroid, spectral_flatness, total_spectral_energy},
};
pub use midi::{
    channel::{midi_to_flux_channel, MidiChannelConfig, MidiChannelMap},
    clock::MidiClock,
    events::MidiEvent,
};
pub use sidechannel::{frown::Frown, nod::Nod, smile::Smile};

// ---------------------------------------------------------------------------
// Library-level constants
// ---------------------------------------------------------------------------

/// Number of flux channels in a room.
pub const FLUX_CHANNEL_COUNT: usize = 9;

/// Version string for the library.
pub const VERSION: &str = env!("CARGO_PKG_VERSION");
