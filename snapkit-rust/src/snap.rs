//! SnapFunction — tolerance-based attention compression.
//!
//! The snap function maps continuous values to their nearest expected point
//! (lattice point). Values within tolerance are compressed ("snapped") to the
//! expected point. Values exceeding tolerance are flagged as deltas demanding
//! attention.
//!
//! EVERYTHING within tolerance is compressed away. ONLY the deltas survive.
//! The snap function IS the gatekeeper of attention.

use crate::topology::SnapTopology;
use num_traits::Float;

/// The result of snapping a value to its nearest expected point.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct SnapResult<T: Float + Default> {
    /// The original observed value.
    pub original: T,
    /// The snapped (compressed) value.
    pub snapped: T,
    /// Absolute distance from expected value.
    pub delta: T,
    /// Whether the value was within tolerance.
    pub within_tolerance: bool,
    /// Current tolerance threshold.
    pub tolerance: T,
    /// Topology used for this snap.
    pub topology: SnapTopology,
}

impl<T: Float + Default> SnapResult<T> {
    /// Returns true if this was detected as a delta (outside tolerance).
    #[inline]
    pub fn is_delta(&self) -> bool {
        !self.within_tolerance
    }
}

/// A tolerance-compressed attention gatekeeper.
///
/// The snap function determines what reaches consciousness (deltas) and
/// what is compressed away (snaps). Every value within tolerance of
/// the expected baseline is "snapped" to the baseline and ignored.
/// Only values exceeding tolerance demand attention.
///
/// # Generics
///
/// Generic over `T: Float`, works with `f32` and `f64`.
///
/// # Builder Pattern
///
/// Use `SnapFunction::builder()` for ergonomic construction.
///
/// ```
/// use snapkit::{SnapFunction, SnapTopology};
///
/// let snap = SnapFunction::builder()
///     .tolerance(0.1)
///     .topology(SnapTopology::Hexagonal)
///     .build();
///
/// let result = snap.observe(0.05);
/// assert!(result.within_tolerance); // within 0.1 tolerance
///
/// let result = snap.observe(0.3);
/// assert!(!result.within_tolerance); // delta!
/// ```
#[derive(Debug, Clone)]
pub struct SnapFunction<T: Float + Default> {
    tolerance: T,
    topology: SnapTopology,
    baseline: T,
    adaptation_rate: T,
    snap_count: u64,
    delta_count: u64,
}

impl<T: Float + Default> SnapFunction<T> {
    /// Create a new `SnapFunction` with default values.
    ///
    /// Default tolerance is 0.1, topology is Hexagonal, baseline is 0.0,
    /// adaptation rate is 0.01.
    pub fn new() -> Self {
        Self {
            tolerance: T::from(0.1).unwrap(),
            topology: SnapTopology::Hexagonal,
            baseline: T::zero(),
            adaptation_rate: T::from(0.01).unwrap(),
            snap_count: 0,
            delta_count: 0,
        }
    }

    /// Create a builder for ergonomic construction.
    pub fn builder() -> SnapFunctionBuilder<T> {
        SnapFunctionBuilder::new()
    }

    /// Set the tolerance threshold.
    #[inline]
    pub fn set_tolerance(&mut self, tolerance: T) {
        self.tolerance = tolerance;
    }

    /// Get the current tolerance.
    #[inline]
    pub fn tolerance(&self) -> T {
        self.tolerance
    }

    /// Set the topology type.
    #[inline]
    pub fn set_topology(&mut self, topology: SnapTopology) {
        self.topology = topology;
    }

    /// Get the current topology.
    #[inline]
    pub fn topology(&self) -> SnapTopology {
        self.topology
    }

    /// Get the current baseline (expected value).
    #[inline]
    pub fn baseline(&self) -> T {
        self.baseline
    }

    /// Set the baseline (expected value).
    #[inline]
    pub fn set_baseline(&mut self, baseline: T) {
        self.baseline = baseline;
    }

    /// Set the adaptation rate (0 = never adapt, 1 = instant).
    #[inline]
    pub fn set_adaptation_rate(&mut self, rate: T) {
        self.adaptation_rate = rate;
    }

    /// Snap a value to its nearest expected point.
    ///
    /// Returns a `SnapResult` with the snapped value, delta, and tolerance check.
    ///
    /// # Examples
    ///
    /// ```
    /// use snapkit::SnapFunction;
    ///
    /// let mut snap = SnapFunction::<f64>::new();
    ///
    /// // Within tolerance → snap to baseline (0.0)
    /// let result = snap.observe(0.05);
    /// assert!(result.within_tolerance);
    /// assert!((result.snapped - 0.0).abs() < 1e-10);
    ///
    /// // Exceeds tolerance → delta detected, value preserved
    /// let result = snap.observe(0.3);
    /// assert!(result.is_delta());
    /// assert!((result.snapped - 0.3).abs() < 1e-10);
    /// ```
    pub fn observe(&mut self, value: T) -> SnapResult<T>
    where
        T: Float,
    {
        let delta = (value - self.baseline).abs();
        let within = delta <= self.tolerance;
        let snapped = if within { self.baseline } else { value };

        if within {
            self.snap_count += 1;
            // Adapt baseline toward observed value
            if self.adaptation_rate > T::zero() {
                self.baseline = self.baseline + self.adaptation_rate * (value - self.baseline);
            }
        } else {
            self.delta_count += 1;
        }

        SnapResult {
            original: value,
            snapped,
            delta,
            within_tolerance: within,
            tolerance: self.tolerance,
            topology: self.topology,
        }
    }

    /// Snap a value with an explicit expected value override.
    ///
    /// This does NOT update the baseline or affect statistics.
    pub fn snap_with_expected(&self, value: T, expected: T) -> SnapResult<T> {
        let delta = (value - expected).abs();
        let within = delta <= self.tolerance;
        let snapped = if within { expected } else { value };
        SnapResult {
            original: value,
            snapped,
            delta,
            within_tolerance: within,
            tolerance: self.tolerance,
            topology: self.topology,
        }
    }

    /// Snap a slice of values in one pass.
    ///
    /// Returns a `Vec<SnapResult<T>>` with results for each value.
    /// Uses the current baseline for all values.
    pub fn snap_batch(&mut self, values: &[T]) -> Vec<SnapResult<T>>
    where
        T: Float + Default,
    {
        values.iter().map(|&v| self.observe(v)).collect()
    }

    /// Snap a slice with expected values per observation.
    ///
    /// This variant does NOT update the baseline. It uses the provided
    /// expected values for each observation independently.
    pub fn snap_with_expected_batch(&self, values: &[T], expected: &[T]) -> Vec<SnapResult<T>> {
        values
            .iter()
            .zip(expected.iter())
            .map(|(&v, &e)| self.snap_with_expected(v, e))
            .collect()
    }

    /// Fraction of observations that snapped (within tolerance).
    pub fn snap_rate(&self) -> f64 {
        let total = self.snap_count + self.delta_count;
        if total == 0 {
            return 1.0; // default: no data, assume everything snaps
        }
        self.snap_count as f64 / total as f64
    }

    /// Fraction of observations that exceeded tolerance (deltas).
    pub fn delta_rate(&self) -> f64 {
        1.0 - self.snap_rate()
    }

    /// Calibration score [0..1].
    ///
    /// - 0.0 = no snaps (tolerance too tight → anxiety)
    /// - 1.0 = all snaps (tolerance too loose → complacency)
    /// - ~0.9 = well-calibrated (most things are expected, deltas are rare)
    pub fn calibration(&self) -> f64 {
        self.snap_rate()
    }

    /// Total observations processed.
    pub fn total_observations(&self) -> u64 {
        self.snap_count + self.delta_count
    }

    /// Reset all state (counts and baseline).
    pub fn reset(&mut self) {
        self.baseline = T::zero();
        self.snap_count = 0;
        self.delta_count = 0;
    }

    /// Reset with a specific baseline value.
    pub fn reset_with_baseline(&mut self, baseline: T) {
        self.baseline = baseline;
        self.snap_count = 0;
        self.delta_count = 0;
    }
}

impl<T: Float + Default> Default for SnapFunction<T> {
    fn default() -> Self {
        Self::new()
    }
}

/// Builder for ergonomic `SnapFunction` construction.
///
/// # Examples
///
/// ```
/// use snapkit::{SnapFunction, SnapTopology};
///
/// let snap = SnapFunction::<f64>::builder()
///     .tolerance(0.05)
///     .topology(SnapTopology::Cubic)
///     .baseline(1.0)
///     .adaptation_rate(0.02)
///     .build();
/// ```
#[derive(Debug, Clone)]
pub struct SnapFunctionBuilder<T: Float + Default> {
    tolerance: T,
    topology: SnapTopology,
    baseline: T,
    adaptation_rate: T,
}

impl<T: Float + Default> SnapFunctionBuilder<T> {
    fn new() -> Self {
        Self {
            tolerance: T::from(0.1).unwrap(),
            topology: SnapTopology::Hexagonal,
            baseline: T::zero(),
            adaptation_rate: T::from(0.01).unwrap(),
        }
    }

    /// Set the snap tolerance.
    pub fn tolerance(mut self, tol: T) -> Self {
        self.tolerance = tol;
        self
    }

    /// Set the snap topology.
    pub fn topology(mut self, topo: SnapTopology) -> Self {
        self.topology = topo;
        self
    }

    /// Set the baseline expected value.
    pub fn baseline(mut self, bl: T) -> Self {
        self.baseline = bl;
        self
    }

    /// Set the adaptation rate.
    pub fn adaptation_rate(mut self, rate: T) -> Self {
        self.adaptation_rate = rate;
        self
    }

    /// Build the `SnapFunction`.
    pub fn build(self) -> SnapFunction<T> {
        SnapFunction {
            tolerance: self.tolerance,
            topology: self.topology,
            baseline: self.baseline,
            adaptation_rate: self.adaptation_rate,
            snap_count: 0,
            delta_count: 0,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_snap_within_tolerance() {
        let mut snap = SnapFunction::<f64>::new();
        let result = snap.observe(0.05);
        assert!(result.within_tolerance);
        assert!((result.snapped - 0.0).abs() < 1e-10, "snapped={}", result.snapped);
    }

    #[test]
    fn test_snap_delta() {
        let mut snap = SnapFunction::<f64>::new();
        let result = snap.observe(0.3);
        assert!(result.is_delta());
        assert!((result.snapped - 0.3).abs() < 1e-10);
    }

    #[test]
    fn test_baseline_adaptation() {
        let mut snap = SnapFunction::<f64>::builder()
            .adaptation_rate(0.5)
            .build();
        // After snapping 0.05 with rate 0.5, baseline becomes 0 + 0.5*0.05 = 0.025
        snap.observe(0.05);
        assert!((snap.baseline() - 0.025).abs() < 1e-10);
    }

    #[test]
    fn test_snap_rate() {
        let mut snap = SnapFunction::<f64>::new();
        assert!((1.0 - snap.snap_rate()).abs() < 1e-10); // default: no data
        snap.observe(0.05);
        snap.observe(0.08);
        snap.observe(0.3);
        assert!((snap.snap_rate() - 2.0 / 3.0).abs() < 1e-10);
    }

    #[test]
    fn test_delta_rate() {
        let mut snap = SnapFunction::<f64>::new();
        snap.observe(0.05);
        snap.observe(0.3);
        assert!((snap.delta_rate() - 0.5).abs() < 1e-10);
    }

    #[test]
    fn test_calibration() {
        let mut snap = SnapFunction::<f64>::new();
        for _ in 0..9 {
            snap.observe(0.05);
        }
        snap.observe(0.3);
        assert!((snap.calibration() - 0.9).abs() < 1e-10);
    }

    #[test]
    fn test_snap_with_expected() {
        let snap = SnapFunction::<f64>::new();
        let result = snap.snap_with_expected(0.05, 0.0);
        assert!(result.within_tolerance);
        // Baseline should NOT have been updated
        assert!(snap.baseline().abs() < 1e-10);
    }

    #[test]
    fn test_snap_batch() {
        let mut snap = SnapFunction::<f64>::new();
        let values = vec![0.05, 0.08, 0.3, 0.02];
        let results = snap.snap_batch(&values);
        assert_eq!(results.len(), 4);
        assert!(results[0].within_tolerance);
        assert!(!results[2].within_tolerance);
    }

    #[test]
    fn test_snap_with_expected_batch() {
        let snap = SnapFunction::<f64>::new();
        let values = vec![0.05, 0.3, 0.08];
        let expected = vec![0.0, 0.0, 0.0];
        let results = snap.snap_with_expected_batch(&values, &expected);
        assert_eq!(results.len(), 3);
        assert!(results[0].within_tolerance);
        assert!(!results[1].within_tolerance);
    }

    #[test]
    fn test_builder() {
        let snap = SnapFunction::<f64>::builder()
            .tolerance(0.5)
            .topology(SnapTopology::Cubic)
            .baseline(10.0)
            .adaptation_rate(0.1)
            .build();
        assert!((snap.tolerance() - 0.5).abs() < 1e-10);
        assert_eq!(snap.topology(), SnapTopology::Cubic);
        assert!((snap.baseline() - 10.0).abs() < 1e-10);
    }

    #[test]
    fn test_reset() {
        let mut snap = SnapFunction::<f64>::new();
        snap.observe(0.3);
        assert_eq!(snap.total_observations(), 1);
        snap.reset();
        assert_eq!(snap.total_observations(), 0);
    }

    #[test]
    fn test_f32_support() {
        let mut snap = SnapFunction::<f32>::new();
        let result = snap.observe(0.05_f32);
        assert!(result.within_tolerance);
        let result = snap.observe(0.3_f32);
        assert!(result.is_delta());
    }

    #[test]
    fn test_default() {
        let snap = SnapFunction::<f64>::default();
        assert!((snap.tolerance() - 0.1).abs() < 1e-10);
        assert_eq!(snap.topology(), SnapTopology::Hexagonal);
    }
}
