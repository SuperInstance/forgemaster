//! Spectral analysis — entropy, Hurst exponent, autocorrelation.
//!
//! All algorithms are libm-free (pure Rust) and `no_std` compatible.

use crate::eisenstein::{fabs, ln, sqrt, LN2};
use crate::types::SpectralSummary;

/// Compute Shannon entropy (in bits) via histogram binning.
///
/// ```
/// # use snapkit::spectral::entropy;
/// let data = vec![1.0, 2.0, 3.0, 4.0, 5.0];
/// let h = entropy(&data, 5);
/// assert!(h > 0.0);
/// ```
pub fn entropy(data: &[f64], bins: usize) -> f64 {
    let n = data.len();
    if n < 2 || bins == 0 {
        return 0.0;
    }

    // Inline min/max
    let mut min_val = data[0];
    let mut max_val = data[0];
    for &x in data {
        if x < min_val {
            min_val = x;
        } else if x > max_val {
            max_val = x;
        }
    }

    if max_val == min_val {
        return 0.0;
    }

    let inv_range = bins as f64 / (max_val - min_val);
    let mut counts = alloc::vec![0usize; bins];

    for &x in data {
        let mut idx = ((x - min_val) * inv_range) as usize;
        if idx >= bins {
            idx = bins - 1;
        }
        counts[idx] += 1;
    }

    let inv_n = 1.0 / n as f64;
    let inv_ln2 = 1.0 / LN2;
    let mut h = 0.0;
    for &c in &counts {
        if c > 0 {
            let p = c as f64 * inv_n;
            h -= p * ln(p) * inv_ln2;
        }
    }
    h
}

/// Compute normalized autocorrelation up to `max_lag`.
///
/// Returns a vector of length `max_lag + 1` where `result[0] = 1.0`.
/// If `max_lag` is `None`, uses `n / 2`.
pub fn autocorrelation(data: &[f64], max_lag: Option<usize>) -> alloc::vec::Vec<f64> {
    let n = data.len();
    if n < 2 {
        return alloc::vec![1.0];
    }

    let max_lag = max_lag.unwrap_or(n / 2).min(n - 1);
    let inv_n = 1.0 / n as f64;

    // Center
    let mean = data.iter().sum::<f64>() * inv_n;
    let centered: alloc::vec::Vec<f64> = data.iter().map(|x| x - mean).collect();

    // Variance
    let r0: f64 = centered.iter().map(|x| x * x).sum::<f64>() * inv_n;
    if r0 == 0.0 {
        let mut result = alloc::vec![1.0];
        result.extend(alloc::vec![0.0; max_lag]);
        return result;
    }

    let inv_r0 = 1.0 / r0;
    let mut result = alloc::vec![0.0; max_lag + 1];

    for lag in 0..=max_lag {
        let mut rk = 0.0;
        for t in 0..(n - lag) {
            rk += centered[t] * centered[t + lag];
        }
        result[lag] = rk * inv_n * inv_r0;
    }
    result
}

/// Estimate Hurst exponent via R/S analysis.
///
/// Returns 0.5 for insufficient data (< 20 points).
/// Result is clamped to [0, 1].
pub fn hurst_exponent(data: &[f64]) -> f64 {
    let n = data.len();
    if n < 20 {
        return 0.5;
    }

    let inv_n = 1.0 / n as f64;
    let mean_val = data.iter().sum::<f64>() * inv_n;
    let centered: alloc::vec::Vec<f64> = data.iter().map(|x| x - mean_val).collect();

    // Geometric progression of test sizes
    let mut test_sizes = alloc::vec![];
    let mut s = 16usize;
    while s <= n / 2 {
        test_sizes.push(s);
        let next2 = s * 2;
        if next2 <= n / 2 {
            s = next2;
        } else {
            let next15 = (s as f64 * 1.5) as usize;
            if next15 == s || next15 > n / 2 {
                break;
            }
            s = next15;
        }
    }

    if test_sizes.is_empty() {
        if n >= 8 {
            test_sizes.push(n / 4);
        } else {
            test_sizes.push(n);
        }
        test_sizes.retain(|&s| s >= 4);
    }

    let mut sizes = alloc::vec![];
    let mut rs_values = alloc::vec![];

    for &size in &test_sizes {
        if size < 4 || size > n {
            continue;
        }
        let num_sub = n / size;
        if num_sub < 1 {
            continue;
        }
        let inv_size = 1.0 / size as f64;
        let mut rs_sum = 0.0_f64;
        let mut rs_count = 0usize;

        for i in 0..num_sub {
            let start = i * size;
            let sub = &centered[start..start + size];
            let sub_mean = sub.iter().sum::<f64>() * inv_size;

            // Cumulative deviations with min/max tracking
            let mut running = 0.0;
            let mut cum_min = 0.0;
            let mut cum_max = 0.0;
            for &x in sub {
                running += x - sub_mean;
                if running < cum_min {
                    cum_min = running;
                } else if running > cum_max {
                    cum_max = running;
                }
            }
            let r = cum_max - cum_min;

            let var: f64 = sub
                .iter()
                .map(|x| {
                    let d = x - sub_mean;
                    d * d
                })
                .sum::<f64>()
                * inv_size;
            if var > 1e-20 {
                rs_sum += r / sqrt(var);
                rs_count += 1;
            }
        }

        if rs_count > 0 {
            let avg_rs = rs_sum / rs_count as f64;
            if avg_rs > 0.0 {
                sizes.push(size as f64);
                rs_values.push(avg_rs);
            }
        }
    }

    if sizes.len() < 2 {
        return 0.5;
    }

    // Linear regression on log-log
    let n_pts = sizes.len() as f64;
    let log_n: alloc::vec::Vec<f64> = sizes.iter().map(|s| ln(*s)).collect();
    let log_rs: alloc::vec::Vec<f64> = rs_values.iter().map(|r| ln(*r)).collect();

    let sum_x: f64 = log_n.iter().sum();
    let sum_y: f64 = log_rs.iter().sum();
    let sum_xy: f64 = log_n.iter().zip(log_rs.iter()).map(|(x, y)| x * y).sum();
    let sum_x2: f64 = log_n.iter().map(|x| x * x).sum();

    let denom = n_pts * sum_x2 - sum_x * sum_x;
    if denom == 0.0 {
        return 0.5;
    }

    let h = (n_pts * sum_xy - sum_x * sum_y) / denom;
    if h < 0.0 {
        0.0
    } else if h > 1.0 {
        1.0
    } else {
        h
    }
}

/// Compute a complete spectral summary of a signal.
///
/// ```
/// # use snapkit::spectral::spectral_summary;
/// // White noise should have H ≈ 0.5
/// let data: Vec<f64> = (0..100).map(|i| ((i as f64 * 7.3).sin() * 10.0 + 5.0)).collect();
/// let summary = spectral_summary(&data, 10, None);
/// assert!(summary.entropy_bits > 0.0);
/// ```
pub fn spectral_summary(data: &[f64], bins: usize, max_lag: Option<usize>) -> SpectralSummary {
    let h = entropy(data, bins);
    let hurst_val = hurst_exponent(data);
    let acf = autocorrelation(data, max_lag);

    let acf_lag1 = if acf.len() > 1 { acf[1] } else { 0.0 };

    // Decay lag: first lag where |acf| < 1/e
    let inv_e = 0.36787944117144233;
    let mut decay_lag = acf.len() as f64;
    for i in 1..acf.len() {
        if fabs(acf[i]) < inv_e {
            decay_lag = i as f64;
            break;
        }
    }

    let is_stationary = (0.4..=0.6).contains(&hurst_val) && fabs(acf_lag1) < 0.3;

    SpectralSummary {
        entropy_bits: h,
        hurst: hurst_val,
        autocorr_lag1: acf_lag1,
        autocorr_decay: decay_lag,
        is_stationary,
    }
}

/// Batch spectral summary for multiple time series.
pub fn spectral_batch(
    series_list: &[&[f64]],
    bins: usize,
    max_lag: Option<usize>,
) -> alloc::vec::Vec<SpectralSummary> {
    series_list
        .iter()
        .map(|data| spectral_summary(data, bins, max_lag))
        .collect()
}

extern crate alloc;
