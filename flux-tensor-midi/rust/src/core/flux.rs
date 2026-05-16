//! 9-channel intent vector (FLUX).
//!
//! Each channel carries a **salience** (what I'm paying attention to) and a **tolerance**
//! (how much deviation I accept), both in `[0, 1]`.

use core::fmt;

#[cfg(feature = "serde")]
use serde::{Deserialize, Serialize};

/// Number of channels in a FLUX vector.
pub const FLUX_CHANNELS: usize = 9;

/// A single channel in the FLUX intent vector.
#[derive(Clone, Copy, Debug, PartialEq)]
#[cfg_attr(feature = "serde", derive(Serialize, Deserialize))]
pub struct FluxChannel {
    /// What I'm paying attention to `[0, 1]`.
    pub salience: f64,
    /// How much deviation I accept `[0, 1]`.
    pub tolerance: f64,
}

impl FluxChannel {
    /// Create a new channel with the given salience and tolerance.
    ///
    /// Values are clamped to `[0, 1]`.
    #[inline]
    pub fn new(salience: f64, tolerance: f64) -> Self {
        Self {
            salience: salience.clamp(0.0, 1.0),
            tolerance: tolerance.clamp(0.0, 1.0),
        }
    }

    /// Channel with zero salience and full tolerance (idle/ignoring).
    #[inline]
    pub fn idle() -> Self {
        Self { salience: 0.0, tolerance: 1.0 }
    }

    /// Channel with full salience and zero tolerance (locked focus).
    #[inline]
    pub fn locked() -> Self {
        Self { salience: 1.0, tolerance: 0.0 }
    }

    /// Effective weight: salience × (1 - tolerance). Higher means more rigid focus.
    #[inline]
    pub fn effective_weight(&self) -> f64 {
        self.salience * (1.0 - self.tolerance)
    }
}

impl Default for FluxChannel {
    fn default() -> Self {
        Self::idle()
    }
}

impl fmt::Display for FluxChannel {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "S:{:.2} T:{:.2}", self.salience, self.tolerance)
    }
}

/// 9-channel intent vector representing a room's current attentional state.
#[derive(Clone, Debug, PartialEq)]
#[cfg_attr(feature = "serde", derive(Serialize, Deserialize))]
pub struct FluxVector {
    channels: [FluxChannel; FLUX_CHANNELS],
}

impl FluxVector {
    /// Create a new FLUX vector with all channels set to idle.
    #[inline]
    pub fn new() -> Self {
        Self { channels: [FluxChannel::idle(); FLUX_CHANNELS] }
    }

    /// Create a FLUX vector from an array of channels.
    #[inline]
    pub fn from_channels(channels: [FluxChannel; FLUX_CHANNELS]) -> Self {
        Self { channels }
    }

    /// Create a FLUX vector where every channel is locked.
    pub fn all_locked() -> Self {
        Self { channels: [FluxChannel::locked(); FLUX_CHANNELS] }
    }

    /// Get a reference to a channel by index (0–8).
    ///
    /// Returns `None` if out of range.
    #[inline]
    pub fn channel(&self, idx: usize) -> Option<&FluxChannel> {
        self.channels.get(idx)
    }

    /// Get a mutable reference to a channel by index (0–8).
    #[inline]
    pub fn channel_mut(&mut self, idx: usize) -> Option<&mut FluxChannel> {
        self.channels.get_mut(idx)
    }

    /// Set a channel by index. No-op if out of range.
    #[inline]
    pub fn set_channel(&mut self, idx: usize, ch: FluxChannel) {
        if let Some(slot) = self.channels.get_mut(idx) {
            *slot = ch;
        }
    }

    /// Iterate over all channels.
    #[inline]
    pub fn iter(&self) -> impl Iterator<Item = &FluxChannel> {
        self.channels.iter()
    }

    /// Total salience across all channels.
    pub fn total_salience(&self) -> f64 {
        self.channels.iter().map(|c| c.salience).sum()
    }

    /// Average tolerance across all channels.
    pub fn avg_tolerance(&self) -> f64 {
        self.channels.iter().map(|c| c.tolerance).sum::<f64>() / FLUX_CHANNELS as f64
    }

    /// Euclidean distance to another FLUX vector.
    ///
    /// Measures how different two intent states are in salience space.
    pub fn distance(&self, other: &FluxVector) -> f64 {
        self.channels
            .iter()
            .zip(other.channels.iter())
            .map(|(a, b)| {
                let ds = a.salience - b.salience;
                let dt = a.tolerance - b.tolerance;
                ds * ds + dt * dt
            })
            .sum::<f64>()
            .sqrt()
    }

    /// Blend this vector toward `other` by factor `alpha` ∈ [0, 1].
    ///
    /// `alpha = 0` leaves self unchanged; `alpha = 1` replaces with other.
    pub fn blend(&mut self, other: &FluxVector, alpha: f64) {
        let a = alpha.clamp(0.0, 1.0);
        for (mine, theirs) in self.channels.iter_mut().zip(other.channels.iter()) {
            mine.salience = mine.salience * (1.0 - a) + theirs.salience * a;
            mine.tolerance = mine.tolerance * (1.0 - a) + theirs.tolerance * a;
        }
    }
}

impl Default for FluxVector {
    fn default() -> Self {
        Self::new()
    }
}

impl fmt::Display for FluxVector {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "Flux[")?;
        for (i, ch) in self.channels.iter().enumerate() {
            if i > 0 { write!(f, " | ")?; }
            write!(f, "{}", ch)?;
        }
        write!(f, "]")
    }
}
