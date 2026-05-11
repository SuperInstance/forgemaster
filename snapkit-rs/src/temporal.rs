//! Temporal snap — beat grid alignment and T-minus-0 detection.
//!
//! `BeatGrid` defines a periodic grid of time points.
//! `TemporalSnap` adds T-minus-0 (inflection point) detection using a circular buffer.

use crate::types::TemporalResult;
use crate::eisenstein::fabs;

/// A periodic grid of time points.
///
/// ```
/// # use snapkit::temporal::BeatGrid;
/// let grid = BeatGrid::new(1.0, 0.0, 0.0);
/// let result = grid.snap(1.37, 0.1);
/// assert!(result.is_on_beat == false); // 0.37 > tolerance
/// ```
#[derive(Debug, Clone)]
pub struct BeatGrid {
    /// Period between beats.
    pub period: f64,
    /// Phase offset.
    pub phase: f64,
    /// Start time.
    pub t_start: f64,
    inv_period: f64,
}

impl BeatGrid {
    /// Create a new beat grid. Panics if period ≤ 0.
    pub fn new(period: f64, phase: f64, t_start: f64) -> Self {
        assert!(period > 0.0, "period must be positive");
        Self {
            period,
            phase,
            t_start,
            inv_period: 1.0 / period,
        }
    }

    /// Find the nearest beat time and its index.
    pub fn nearest_beat(&self, t: f64) -> (f64, i64) {
        let adjusted = t - self.t_start - self.phase;
        let index = round_i64(adjusted * self.inv_period);
        let beat_time = self.t_start + self.phase + index as f64 * self.period;
        (beat_time, index)
    }

    /// Snap a timestamp to the nearest beat.
    pub fn snap(&self, t: f64, tolerance: f64) -> TemporalResult {
        let (beat_time, beat_index) = self.nearest_beat(t);
        let offset = t - beat_time;
        let is_on_beat = fabs(offset) <= tolerance;
        let phase = frac_part((t - self.t_start - self.phase) * self.inv_period);
        TemporalResult {
            original_time: t,
            snapped_time: beat_time,
            offset,
            is_on_beat,
            is_t_minus_0: false,
            beat_index,
            beat_phase: phase,
        }
    }

    /// Snap multiple timestamps.
    pub fn snap_batch(&self, timestamps: &[f64], tolerance: f64) -> alloc::vec::Vec<TemporalResult> {
        timestamps.iter().map(|&t| self.snap(t, tolerance)).collect()
    }

    /// List all beat times in [t_start, t_end].
    pub fn beats_in_range(&self, t_start: f64, t_end: f64) -> alloc::vec::Vec<f64> {
        if t_end <= t_start {
            return alloc::vec::Vec::new();
        }
        let first_idx = ceil_i64((t_start - self.t_start - self.phase) * self.inv_period);
        let last_idx = floor_i64((t_end - self.t_start - self.phase) * self.inv_period);
        let mut result = alloc::vec::Vec::new();
        let mut i = first_idx;
        while i <= last_idx {
            result.push(self.t_start + self.phase + i as f64 * self.period);
            i += 1;
        }
        result
    }
}

/// Temporal snap with T-minus-0 (inflection point) detection.
///
/// Uses a circular buffer to track recent observations and detects sign changes
/// in the derivative (inflection points) as potential T-minus-0 events.
pub struct TemporalSnap {
    /// The underlying beat grid.
    pub grid: BeatGrid,
    /// Tolerance for on-beat detection.
    pub tolerance: f64,
    /// Threshold for T-minus-0 value (must be small).
    pub t0_threshold: f64,
    /// Window size for derivative estimation.
    pub t0_window: usize,
    history: alloc::vec::Vec<Option<(f64, f64)>>,
    hist_idx: usize,
    hist_len: usize,
    hist_cap: usize,
}

impl TemporalSnap {
    /// Create a new temporal snap detector.
    pub fn new(grid: BeatGrid, tolerance: f64, t0_threshold: f64, t0_window: usize) -> Self {
        let window = if t0_window < 2 { 2 } else { t0_window };
        let cap = window * 2;
        let mut history = alloc::vec::Vec::with_capacity(cap);
        history.resize_with(cap, || None);
        Self {
            grid,
            tolerance,
            t0_threshold,
            t0_window: window,
            history,
            hist_idx: 0,
            hist_len: 0,
            hist_cap: cap,
        }
    }

    /// Observe a timestamp and value, returning a temporal result with T-minus-0 flag.
    pub fn observe(&mut self, t: f64, value: f64) -> TemporalResult {
        self.history[self.hist_idx] = Some((t, value));
        self.hist_idx = (self.hist_idx + 1) % self.hist_cap;
        if self.hist_len < self.hist_cap {
            self.hist_len += 1;
        }

        let is_t0 = self.detect_t0();

        let mut result = self.grid.snap(t, self.tolerance);
        result.is_t_minus_0 = is_t0;
        result
    }

    /// Reset the observation history.
    pub fn reset(&mut self) {
        self.hist_idx = 0;
        self.hist_len = 0;
    }

    /// Get the current history as a flat list.
    pub fn history(&self) -> alloc::vec::Vec<(f64, f64)> {
        let mut result = alloc::vec::Vec::new();
        for i in 0..self.hist_len {
            let idx = (self.hist_idx + self.hist_cap - self.hist_len + i) % self.hist_cap;
            if let Some(val) = self.history[idx] {
                result.push(val);
            }
        }
        result
    }

    fn detect_t0(&self) -> bool {
        if self.hist_len < 3 {
            return false;
        }
        let cap = self.hist_cap;
        let idx = self.hist_idx;

        let (curr_t, curr_val) = match self.history[(idx + cap - 1) % cap] {
            Some(v) => v,
            None => return false,
        };
        let (mid_t, mid_val) = match self.history[(idx + cap - 2) % cap] {
            Some(v) => v,
            None => return false,
        };
        let (prev_t, prev_val) = match self.history[(idx + cap - 3) % cap] {
            Some(v) => v,
            None => return false,
        };

        if fabs(curr_val) > self.t0_threshold {
            return false;
        }

        let dt1 = mid_t - prev_t;
        let dt2 = curr_t - mid_t;
        if dt1 == 0.0 || dt2 == 0.0 {
            return false;
        }

        let d1 = (mid_val - prev_val) / dt1;
        let d2 = (curr_val - mid_val) / dt2;

        d1 * d2 < 0.0
    }
}

// ── helpers ──────────────────────────────────────────────────────────

fn round_i64(x: f64) -> i64 {
    floor(x + 0.5) as i64
}

fn floor_i64(x: f64) -> i64 {
    floor(x) as i64
}

fn ceil_i64(x: f64) -> i64 {
    let f = floor(x);
    if x == f { f as i64 } else { f as i64 + 1 }
}

/// Fractional part, always in [0, 1).
fn frac_part(x: f64) -> f64 {
    let f = floor(x);
    let frac = x - f;
    if frac < 0.0 { frac + 1.0 } else { frac }
}

fn floor(x: f64) -> f64 {
    crate::eisenstein::floor(x)
}

extern crate alloc;
