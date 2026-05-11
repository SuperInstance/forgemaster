//! Temporal connectome — coupled and anti-coupled signal detection.
//!
//! Cross-correlation based coupling detection between pairs of temporal signals.

use crate::types::{ConnectomeResult, CouplingType, RoomPair};
use crate::eisenstein::fabs;

/// Builder for temporal connectome analysis.
///
/// ```
/// # use snapkit::connectome::TemporalConnectome;
/// let mut tc = TemporalConnectome::new(0.3, 5, 10);
/// tc.add_room(&[1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0]);
/// tc.add_room(&[2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0]);
/// let result = tc.analyze();
/// assert!(result.pairs.len() == 1);
/// assert!(result.pairs[0].coupling == CouplingType::Coupled);
/// ```
pub struct TemporalConnectome {
    /// Correlation threshold for coupling detection.
    pub threshold: f64,
    /// Maximum lag for cross-correlation.
    pub max_lag: usize,
    /// Minimum number of samples required.
    pub min_samples: usize,
    traces: alloc::vec::Vec<alloc::vec::Vec<f64>>,
}

impl TemporalConnectome {
    /// Create a new connectome analyzer.
    pub fn new(threshold: f64, max_lag: usize, min_samples: usize) -> Self {
        Self {
            threshold,
            max_lag,
            min_samples,
            traces: alloc::vec::Vec::new(),
        }
    }

    /// Add a room's activity trace. The index is used as the room identifier.
    pub fn add_room(&mut self, activity: &[f64]) {
        self.traces.push(activity.to_vec());
    }

    /// Analyze all pairs and return the connectome result.
    pub fn analyze(&self) -> ConnectomeResult {
        let n = self.traces.len();
        let mut pairs = alloc::vec::Vec::new();

        for i in 0..n {
            for j in (i + 1)..n {
                pairs.push(self.analyze_pair(i, j));
            }
        }

        ConnectomeResult {
            pairs,
            num_rooms: n,
        }
    }

    fn analyze_pair(&self, room_a: usize, room_b: usize) -> RoomPair {
        let trace_a = &self.traces[room_a];
        let trace_b = &self.traces[room_b];

        let n = trace_a.len().min(trace_b.len());
        if n < self.min_samples {
            return RoomPair {
                room_a,
                room_b,
                coupling: CouplingType::Uncoupled,
                correlation: 0.0,
                lag: 0,
                confidence: 0.0,
            };
        }

        let a = &trace_a[..n];
        let b = &trace_b[..n];

        let xcorrs = cross_correlation(a, b, self.max_lag);
        let mut best_lag = 0i32;
        let mut best_corr = 0.0f64;
        for (lag, corr) in &xcorrs {
            if fabs(*corr) > fabs(best_corr) {
                best_corr = *corr;
                best_lag = *lag;
            }
        }

        let coupling = if best_corr > self.threshold {
            CouplingType::Coupled
        } else if best_corr < -self.threshold {
            CouplingType::AntiCoupled
        } else {
            CouplingType::Uncoupled
        };

        let sample_factor = (n as f64 / 50.0).min(1.0);
        let confidence = sample_factor * fabs(best_corr);

        // Round to 6 decimal places like Python
        let correlation = crate::eisenstein::round(best_corr * 1_000_000.0) / 1_000_000.0;
        let confidence = crate::eisenstein::round(confidence * 10_000.0) / 10_000.0;

        RoomPair {
            room_a,
            room_b,
            coupling,
            correlation,
            lag: best_lag,
            confidence,
        }
    }
}

/// Compute Pearson correlation between two slices.
fn pearson_correlation(x: &[f64], y: &[f64]) -> f64 {
    let n = x.len().min(y.len());
    if n < 2 {
        return 0.0;
    }

    let inv_n = 1.0 / n as f64;
    let mean_x: f64 = x[..n].iter().sum::<f64>() * inv_n;
    let mean_y: f64 = y[..n].iter().sum::<f64>() * inv_n;

    let mut cov = 0.0;
    let mut var_x = 0.0;
    let mut var_y = 0.0;
    for i in 0..n {
        let dx = x[i] - mean_x;
        let dy = y[i] - mean_y;
        cov += dx * dy;
        var_x += dx * dx;
        var_y += dy * dy;
    }

    let denom = crate::eisenstein::sqrt(var_x * var_y);
    if denom < 1e-15 {
        0.0
    } else {
        cov / denom
    }
}

/// Compute cross-correlation at lags -max_lag..=max_lag.
fn cross_correlation(x: &[f64], y: &[f64], max_lag: usize) -> alloc::vec::Vec<(i32, f64)> {
    let n = x.len().min(y.len());
    let mut results = alloc::vec::Vec::with_capacity(2 * max_lag + 1);

    for lag in 0..=max_lag as i32 {
        for sign in &[1i32, -1i32] {
            let l = lag * sign;
            let (xx, yy) = if l >= 0 {
                let l = l as usize;
                if l >= n { continue; }
                (&x[..n - l], &y[l..n])
            } else {
                let l = (-l) as usize;
                if l >= n { continue; }
                (&x[l..n], &y[..n - l])
            };

            let corr = if xx.len() < 3 {
                0.0
            } else {
                pearson_correlation(xx, yy)
            };
            results.push((l, corr));
        }
    }

    // Deduplicate lag=0 (visited twice: sign=1 and sign=-1)
    results.sort_by_key(|(lag, _)| *lag);
    results.dedup_by_key(|(lag, _)| *lag);
    results
}

extern crate alloc;
