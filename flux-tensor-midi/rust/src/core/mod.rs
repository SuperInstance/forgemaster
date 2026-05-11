/// Core types for FLUX-Tensor-MIDI.
///
/// # Flux Channels
///
/// A room has up to 9 FluxChannels, each representing a musician or voice
/// in the PLATO room. Each channel carries a signed intensity value and
/// an optional cluster assignment for harmonic grouping.

use crate::MidiEvent;
use core::cmp::Ordering;
use core::fmt;

/// 1/√3 — the Eisenstein lattice covering radius, computed at compile time.
pub(crate) const INV_SQRT_3: f64 = 0.5773502691896257645091487805019574556476;
