//! T-0 temporal expectation clock with EWMA adaptation.
//!
//! Tracks when the next observation is expected (`t_zero`) and adapts the interval
//! using exponential weighted moving average (EWMA).

use core::fmt;

#[cfg(feature = "serde")]
use serde::{Deserialize, Serialize};

/// T-0 temporal expectation clock.
///
/// Learns the interval between observations and predicts the next one.
/// Uses EWMA to adapt to tempo changes.
#[derive(Clone, Debug)]
#[cfg_attr(feature = "serde", derive(Serialize, Deserialize))]
pub struct TZeroClock {
    /// Expected interval between observations (seconds).
    pub interval: f64,
    /// Timestamp of the last observation.
    pub t_last: f64,
    /// Predicted time of next observation.
    pub t_zero: f64,
    /// EWMA adaptation rate `[0, 1]`. Higher = faster adaptation.
    pub ewma_alpha: f64,
    /// Whether the clock has received at least one observation.
    pub adaptive: bool,
    /// Total observations received.
    pub observations: u64,
}

impl TZeroClock {
    /// Create a new clock with an initial interval estimate.
    ///
    /// `initial_interval` is in seconds (e.g., 0.5 for 120 BPM quarter notes).
    pub fn new(initial_interval: f64) -> Self {
        Self {
            interval: initial_interval,
            t_last: 0.0,
            t_zero: initial_interval,
            ewma_alpha: 0.3,
            adaptive: false,
            observations: 0,
        }
    }

    /// Create a clock from a BPM value.
    ///
    /// `subdivision` is the note value (4 = quarter note, 8 = eighth note).
    pub fn from_bpm(bpm: f64, subdivision: u32) -> Self {
        let interval = 60.0 / bpm / (subdivision as f64 / 4.0);
        Self::new(interval)
    }

    /// Observe an event at `t_now`. Updates interval via EWMA and predicts next.
    ///
    /// Returns the deviation (actual interval - expected interval).
    pub fn observe(&mut self, t_now: f64) -> f64 {
        if !self.adaptive {
            self.t_last = t_now;
            self.t_zero = t_now + self.interval;
            self.adaptive = true;
            self.observations = 1;
            return 0.0;
        }

        let observed_interval = t_now - self.t_last;
        let deviation = observed_interval - self.interval;

        // EWMA update
        self.interval = self.ewma_alpha * observed_interval + (1.0 - self.ewma_alpha) * self.interval;
        self.t_last = t_now;
        self.t_zero = t_now + self.interval;
        self.observations += 1;

        deviation
    }

    /// How far we are from the predicted T-0, in seconds.
    ///
    /// Negative = early, positive = late, 0 = right on time.
    #[inline]
    pub fn drift(&self, t_now: f64) -> f64 {
        if !self.adaptive {
            return 0.0;
        }
        t_now - self.t_zero
    }

    /// Normalized drift as a fraction of the expected interval.
    ///
    /// Returns 0.0 if no interval is set.
    pub fn drift_normalized(&self, t_now: f64) -> f64 {
        if !self.adaptive || self.interval == 0.0 {
            return 0.0;
        }
        self.drift(t_now) / self.interval
    }

    /// Whether `t_now` is within `tolerance` seconds of the expected T-0.
    #[inline]
    pub fn on_time(&self, t_now: f64, tolerance: f64) -> bool {
        self.drift(t_now).abs() <= tolerance
    }

    /// Reset the clock, keeping the learned interval.
    pub fn reset(&mut self) {
        self.t_last = 0.0;
        self.t_zero = self.interval;
        self.adaptive = false;
        self.observations = 0;
    }

    /// Set the EWMA alpha (adaptation rate).
    pub fn set_alpha(&mut self, alpha: f64) {
        self.ewma_alpha = alpha.clamp(0.0, 1.0);
    }

    /// Expected BPM based on current interval.
    pub fn bpm(&self) -> f64 {
        if self.interval > 0.0 { 60.0 / self.interval } else { 0.0 }
    }
}

impl fmt::Display for TZeroClock {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "TZero(interval={:.3}s, bpm={:.1}, obs={})",
            self.interval,
            self.bpm(),
            self.observations
        )
    }
}
