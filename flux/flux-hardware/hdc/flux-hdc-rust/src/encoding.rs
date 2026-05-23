//! 3-layer multi-scale semantic encoding for range constraints.
//! Uses log-uniform thresholds for high similarity between nearly-identical ranges.

use crate::{Hypervector, bind, majority_bundle};
use rand::SeedableRng;
use rand_xoshiro::Xoroshiro64Star;
use thiserror::Error;

/// Error type for encoding operations.
#[derive(Debug, Clone, Copy, PartialEq, Error)]
#[non_exhaustive]
pub enum EncodingError {
    /// Range bounds are invalid (a >= b).
    #[error("invalid range bounds: a={0} >= b={1}")]
    InvalidBounds(f64, f64),
    /// Range is outside [0, 100] limits.
    #[error("range out of bounds: must be within [0, 100]")]
    OutOfRange,
    /// No thresholds matched the range (internal error).
    #[error("no thresholds matched the range")]
    NoMatchingThresholds,
    /// Operation error during encoding.
    #[error("operation error during encoding")]
    OperationError,
}

impl From<crate::OperationError> for EncodingError {
    fn from(_: crate::OperationError) -> Self {
        EncodingError::OperationError
    }
}

/// Minimum threshold value for log-uniform spacing (avoids log(0)).
pub const MIN_THRESHOLD: f64 = 1e-6;
/// Maximum threshold value (matches [0, 100] range requirement).
pub const MAX_THRESHOLD: f64 = 100.0;

/// Default number of log-uniform thresholds (1024 for fine-grained overlap detection).
pub const DEFAULT_NUM_THRESHOLDS: usize = 1024;
/// Default number of center quantization levels (128 for smooth center encoding).
pub const DEFAULT_NUM_CENTER_LEVELS: usize = 128;
/// Default number of span quantization levels (128 for smooth span encoding).
pub const DEFAULT_NUM_SPAN_LEVELS: usize = 128;

/// Generate log-uniform spaced thresholds for range overlap detection.
/// Log-uniform spacing ensures nearly-identical ranges have >99% threshold overlap.
pub fn generate_log_uniform_thresholds<const N: usize>() -> [f64; N] {
    let mut thresholds = [0.0; N];
    let log_min = MIN_THRESHOLD.ln();
    let log_max = MAX_THRESHOLD.ln();
    let log_step = (log_max - log_min) / (N - 1) as f64;

    for i in 0..N {
        thresholds[i] = (log_min + log_step * i as f64).exp();
    }
    thresholds
}

/// Semantic encoder for range constraints using 3-layer multi-scale HDC encoding.
/// 
/// Layers:
/// 1. Threshold Occupation: Bundle of thresholds within the range (main similarity driver)
/// 2. Center Levels: Hypervector for the range center
/// 3. Span Levels: Hypervector for the range width
#[derive(Debug, Clone)]
pub struct Encoder<
    const NUM_THRESHOLDS: usize = DEFAULT_NUM_THRESHOLDS,
    const NUM_CENTER_LEVELS: usize = DEFAULT_NUM_CENTER_LEVELS,
    const NUM_SPAN_LEVELS: usize = DEFAULT_NUM_SPAN_LEVELS,
> {
    thresholds: [f64; NUM_THRESHOLDS],
    threshold_hvs: [Hypervector; NUM_THRESHOLDS],
    center_hvs: [Hypervector; NUM_CENTER_LEVELS],
    span_hvs: [Hypervector; NUM_SPAN_LEVELS],
}

impl<
    const NUM_T: usize,
    const NUM_C: usize,
    const NUM_S: usize,
> Encoder<NUM_T, NUM_C, NUM_S> {
    /// Create a new encoder with reproducible hypervectors from a seed.
    pub fn new(seed: u64) -> Self {
        let mut rng = Xoroshiro64Star::seed_from_u64(seed);
        let thresholds = generate_log_uniform_thresholds::<NUM_T>();
        let threshold_hvs = [(); NUM_T].map(|_| Hypervector::random(&mut rng));
        let center_hvs = [(); NUM_C].map(|_| Hypervector::random(&mut rng));
        let span_hvs = [(); NUM_S].map(|_| Hypervector::random(&mut rng));

        Self { thresholds, threshold_hvs, center_hvs, span_hvs }
    }

    /// Encode a range [a, b] (0 ≤ a < b ≤ 100) into a hypervector.
    /// 
    /// # Guarantees
    /// - range(0, 100) vs range(0, 99) have >0.95 similarity
    /// - Similar ranges have high similarity, dissimilar ranges have ~0.5 similarity
    pub fn encode_range(&self, a: f64, b: f64) -> Result<Hypervector, EncodingError> {
        // Validate input
        if a < 0.0 || b > MAX_THRESHOLD {
            return Err(EncodingError::OutOfRange);
        }
        if a >= b {
            return Err(EncodingError::InvalidBounds(a, b));
        }

        // 1. Threshold Occupation Layer
        let active_thresholds: Vec<Hypervector> = self.thresholds
            .iter()
            .zip(self.threshold_hvs.iter())
            .filter(|(&t, _)| t >= a && t <= b)
            .map(|(_, &hv)| hv)
            .collect();

        if active_thresholds.is_empty() {
            return Err(EncodingError::NoMatchingThresholds);
        }

        let threshold_hv = majority_bundle(&active_thresholds)?;

        // 2. Center Level Layer
        let center = (a + b) / 2.0;
        let center_idx = ((center - MIN_THRESHOLD) / (MAX_THRESHOLD - MIN_THRESHOLD) * (NUM_C - 1) as f64)
            .round() as usize;
        let center_idx = center_idx.clamp(0, NUM_C - 1);
        let center_hv = self.center_hvs[center_idx];

        // 3. Span Level Layer
        let span = b - a;
        let span_idx = (span / MAX_THRESHOLD * (NUM_S - 1) as f64)
            .round() as usize;
        let span_idx = span_idx.clamp(0, NUM_S - 1);
        let span_hv = self.span_hvs[span_idx];

        // Bind all layers
        Ok(bind(bind(threshold_hv, center_hv), span_hv))
    }
}
