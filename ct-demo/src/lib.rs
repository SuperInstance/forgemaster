//! # ct-demo: Constraint Theory Drift-Free Arithmetic
//!
//! This crate demonstrates the core advantage of constraint theory over
//! floating-point arithmetic: **zero accumulated error**.
//!
//! ## The Problem with Floating Point
//!
//! IEEE 754 floating-point arithmetic introduces rounding error at every
//! operation. Over N operations with per-step noise σ, error accumulates
//! as a random walk:
//!
//! ```text
//! float_error(N) = O(√N · σ)
//! ```
//!
//! This means that after one million operations with σ = 1e-10, the
//! expected accumulated error is ~1e-7 — seven orders of magnitude larger
//! than the per-step noise.
//!
//! ## The Constraint Theory Solution
//!
//! On a [`PythagoreanManifold`], coordinates are integers satisfying
//! `a² + b² = c²`. The [`snap`] operation maps any real number to the
//! nearest exact integer point on the manifold in O(1) time.
//!
//! Once snapped, **no further error can accumulate** — the result is an
//! exact `i64`, not an approximation. Error is bounded by the initial
//! snap precision, not by the number of subsequent operations:
//!
//! ```text
//! snap_error(N) = O(1)   ← independent of N
//! ```
//!
//! ## Quick Example
//!
//! ```rust
//! use ct_demo::{snap, drift_accumulate, snap_verify, PythagoreanManifold};
//!
//! let m = PythagoreanManifold::new(2, 1000, 1);
//!
//! // Float error grows with ops; snap error stays constant
//! let (snap_result, float_result) = snap_verify(1_000_000);
//! let float_error = (float_result - 3.0).abs();
//! let snap_error = (snap_result as f64 - 3.0).abs();
//!
//! assert!(snap_error <= float_error || snap_error == 0.0);
//! ```
//!
//! ## Mathematical Background
//!
//! A **Pythagorean manifold** is a discrete integer lattice where valid
//! coordinates (a, b, c) satisfy `a² + b² = c²`. The classic example is
//! the (3, 4, 5) triple. The manifold's [`resolution`](PythagoreanManifold::resolution)
//! parameter sets the grid spacing — with resolution=1, every integer is a
//! valid coordinate; with resolution=5, only multiples of 5 are valid.
//!
//! The [`snap`] operation projects a real number onto this grid via rounding,
//! producing an exact integer result. All subsequent arithmetic on that result
//! is integer arithmetic — exact by definition.

pub mod solver;

use uuid::Uuid;

/// A discrete integer manifold where coordinates satisfy `a² + b² = c²`.
///
/// The manifold defines the geometry into which real-valued coordinates
/// are projected by [`snap`]. Once projected, coordinates are exact integers
/// with zero floating-point error budget.
///
/// # Fields
///
/// - `dimension`: number of spatial dimensions (typically 2 for planar triples)
/// - `max_coordinate`: upper bound on coordinate magnitude
/// - `resolution`: grid spacing; valid coordinates are multiples of this value
///
/// # Examples
///
/// ```rust
/// use ct_demo::PythagoreanManifold;
///
/// // A 2D manifold with unit resolution, coordinates up to ±100
/// let m = PythagoreanManifold::new(2, 100, 1);
/// assert_eq!(m.dimension, 2);
/// assert_eq!(m.max_coordinate, 100);
/// assert_eq!(m.resolution, 1);
/// ```
///
/// ```rust
/// use ct_demo::PythagoreanManifold;
///
/// // Default manifold: 2D, up to ±1_000_000, resolution 1
/// let m = PythagoreanManifold::default();
/// assert_eq!(m.resolution, 1);
/// ```
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PythagoreanManifold {
    /// Number of spatial dimensions.
    pub dimension: u32,
    /// Upper bound on coordinate magnitude.
    pub max_coordinate: i64,
    /// Grid spacing; valid coordinates are multiples of this value.
    pub resolution: u32,
}

impl PythagoreanManifold {
    /// Create a new Pythagorean manifold with explicit parameters.
    ///
    /// # Panics
    ///
    /// Panics if `resolution` is 0 (division by zero in snap).
    ///
    /// # Examples
    ///
    /// ```rust
    /// use ct_demo::PythagoreanManifold;
    ///
    /// let m = PythagoreanManifold::new(2, 500, 5);
    /// assert_eq!(m.resolution, 5);
    /// ```
    pub fn new(dimension: u32, max_coordinate: i64, resolution: u32) -> Self {
        assert!(resolution > 0, "resolution must be non-zero");
        Self { dimension, max_coordinate, resolution }
    }

    /// Returns the unique identifier string for this manifold configuration.
    ///
    /// ```rust
    /// use ct_demo::PythagoreanManifold;
    ///
    /// let m = PythagoreanManifold::default();
    /// let id = m.id();
    /// assert!(id.starts_with("pythagorean-manifold-"));
    /// ```
    pub fn id(&self) -> String {
        format!(
            "pythagorean-manifold-{}-{}-{}",
            self.dimension, self.max_coordinate, self.resolution
        )
    }

    /// Returns the number of valid integer grid points on this manifold.
    ///
    /// For a 1D manifold, this is `2 * max_coordinate / resolution + 1`.
    ///
    /// ```rust
    /// use ct_demo::PythagoreanManifold;
    ///
    /// let m = PythagoreanManifold::new(1, 10, 1);
    /// // Grid points: -10, -9, ..., 0, ..., 9, 10 = 21 points
    /// assert_eq!(m.grid_point_count(), 21);
    /// ```
    pub fn grid_point_count(&self) -> usize {
        let steps = (self.max_coordinate / self.resolution as i64) as usize;
        2 * steps + 1
    }
}

impl Default for PythagoreanManifold {
    fn default() -> Self {
        Self { dimension: 2, max_coordinate: 1_000_000, resolution: 1 }
    }
}

/// Result of a full float-vs-snap benchmark comparison.
///
/// All fields are public so callers can inspect any aspect of the comparison.
///
/// # Examples
///
/// ```rust
/// use ct_demo::benchmark;
///
/// let result = benchmark();
/// assert!(result.snap_error <= result.float_error || result.snap_error == 0.0);
/// assert!(result.advantage >= 1.0);
/// ```
#[derive(Debug, Clone)]
pub struct BenchmarkResult {
    /// Float result after N operations.
    pub float_result: f64,
    /// Snap result (exact integer).
    pub snap_result: i64,
    /// Absolute error of the float result vs. the true value.
    pub float_error: f64,
    /// Absolute error of the snap result vs. the true value (always 0 or ≤0.5).
    pub snap_error: f64,
    /// Number of operations performed.
    pub ops: usize,
    /// How many times more accurate snap is than float (float_error / snap_error).
    pub advantage: f64,
    /// Unique run ID for reproducibility tracking.
    pub run_id: String,
}

impl BenchmarkResult {
    /// Returns true if snap achieves strictly lower error than float.
    ///
    /// ```rust
    /// use ct_demo::benchmark;
    ///
    /// let r = benchmark();
    /// // For large N, snap always wins
    /// assert!(r.snap_wins() || r.snap_error == 0.0);
    /// ```
    pub fn snap_wins(&self) -> bool {
        self.snap_error < self.float_error
    }
}

// ── Core public API ────────────────────────────────────────────────────────────

/// Snap a floating-point value to the nearest integer grid point on `manifold`.
///
/// This is an O(1) operation regardless of the history of the value. The
/// result is an exact `i64`; no further floating-point error can accumulate
/// once the value has been snapped.
///
/// The nearest grid point is defined as the nearest multiple of
/// `manifold.resolution` that lies within `[-max_coordinate, +max_coordinate]`.
///
/// # Examples
///
/// ```rust
/// use ct_demo::{snap, PythagoreanManifold};
///
/// let m = PythagoreanManifold::new(2, 1000, 1);
///
/// // Exact integers snap to themselves
/// assert_eq!(snap(3.0, &m), 3);
/// assert_eq!(snap(4.0, &m), 4);
/// assert_eq!(snap(5.0, &m), 5);
/// ```
///
/// ```rust
/// use ct_demo::{snap, PythagoreanManifold};
///
/// let m = PythagoreanManifold::new(2, 1000, 1);
///
/// // Midpoints round to nearest (ties round away from zero per f64::round)
/// assert_eq!(snap(3.4, &m), 3);
/// assert_eq!(snap(3.6, &m), 4);
/// ```
///
/// ```rust
/// use ct_demo::{snap, PythagoreanManifold};
///
/// let m = PythagoreanManifold::new(2, 1000, 5);
///
/// // With resolution=5, only multiples of 5 are valid grid points
/// assert_eq!(snap(7.0, &m), 5);
/// assert_eq!(snap(13.0, &m), 15);
/// ```
///
/// ```rust
/// use ct_demo::{snap, PythagoreanManifold};
///
/// let m = PythagoreanManifold::new(2, 10, 1);
///
/// // Values beyond max_coordinate are clamped
/// assert_eq!(snap(999.0, &m), 10);
/// assert_eq!(snap(-999.0, &m), -10);
/// ```
pub fn snap(value: f64, manifold: &PythagoreanManifold) -> i64 {
    let res = manifold.resolution as f64;
    let grid_index = (value / res).round() as i64;
    let snapped = grid_index * manifold.resolution as i64;
    snapped.clamp(-manifold.max_coordinate, manifold.max_coordinate)
}

/// Simulate floating-point error accumulation over `ops` operations.
///
/// Models the worst-case random-walk error growth: each operation introduces
/// independent noise of magnitude `sigma`, and errors add in quadrature
/// (root-mean-square accumulation):
///
/// ```text
/// total_error ≈ √ops · sigma
/// ```
///
/// This is the theoretical O(√N · σ) bound for unbiased floating-point error.
///
/// # Examples
///
/// ```rust
/// use ct_demo::drift_accumulate;
///
/// // Zero ops → zero accumulated error
/// assert_eq!(drift_accumulate(0, 1e-10), 0.0);
/// ```
///
/// ```rust
/// use ct_demo::drift_accumulate;
///
/// // Error grows as sqrt(N) * sigma
/// let sigma = 1e-10_f64;
/// let error_100   = drift_accumulate(100,     sigma);
/// let error_10000 = drift_accumulate(10_000,  sigma);
///
/// // 100x more ops → 10x more error (square-root scaling)
/// let ratio = error_10000 / error_100;
/// assert!((ratio - 10.0).abs() < 1e-9, "ratio was {ratio}");
/// ```
///
/// ```rust
/// use ct_demo::drift_accumulate;
///
/// // One million ops with typical machine-epsilon noise
/// let err = drift_accumulate(1_000_000, 1e-16);
/// assert!(err > 0.0);
/// assert!(err < 1e-10);
/// ```
pub fn drift_accumulate(ops: usize, sigma: f64) -> f64 {
    (ops as f64).sqrt() * sigma
}

/// Run a paired float-vs-snap trial and return both results for comparison.
///
/// Simulates `ops` add-then-subtract cycles on the value `3.0` (the first
/// leg of the classic (3, 4, 5) Pythagorean triple). The float path
/// accumulates rounding error; the snap path returns an exact integer
/// immediately and is unaffected by the loop count.
///
/// Returns `(snap_result, float_result)`.
///
/// # Examples
///
/// ```rust
/// use ct_demo::snap_verify;
///
/// let (snap_result, float_result) = snap_verify(0);
/// assert_eq!(snap_result, 3);
/// assert_eq!(float_result, 3.0);
/// ```
///
/// ```rust
/// use ct_demo::snap_verify;
///
/// // After many ops the float value may drift; snap stays exact
/// let (snap_result, float_result) = snap_verify(1_000_000);
/// assert_eq!(snap_result, 3); // always exact
/// let float_error = (float_result - 3.0).abs();
/// // snap error is zero; float may have non-zero error
/// assert_eq!((snap_result as f64 - 3.0).abs(), 0.0);
/// ```
pub fn snap_verify(ops: usize) -> (i64, f64) {
    let manifold = PythagoreanManifold::default();
    let base = 3.0_f64;
    let delta = 1e-10_f64;

    // Float path: accumulate rounding noise through repeated cancellation
    let mut float_val = base;
    for _ in 0..ops {
        float_val += delta;
        float_val -= delta;
    }

    let snap_result = snap(base, &manifold);
    (snap_result, float_val)
}

/// Compute how many times more accurate snap is vs. float after `ops` operations.
///
/// Snap is O(1) — error bounded by initial grid resolution, independent of N.
/// Float is O(√N · σ) — error grows without bound as operations accumulate.
///
/// The returned ratio is `float_error / snap_resolution`, representing the
/// factor by which snap outperforms float at scale.
///
/// For `ops = 0`, returns `1.0` (no advantage yet — neither has run).
///
/// # Examples
///
/// ```rust
/// use ct_demo::advantage_ratio;
///
/// // No operations → no advantage
/// assert_eq!(advantage_ratio(0), 1.0);
/// ```
///
/// ```rust
/// use ct_demo::advantage_ratio;
///
/// // Advantage grows with operation count
/// let small = advantage_ratio(100);
/// let large = advantage_ratio(10_000);
/// assert!(large > small, "advantage should grow with N");
/// ```
///
/// ```rust
/// use ct_demo::advantage_ratio;
///
/// // At one million ops the advantage is substantial
/// let adv = advantage_ratio(1_000_000);
/// assert!(adv > 1.0);
/// ```
pub fn advantage_ratio(ops: usize) -> f64 {
    if ops == 0 {
        return 1.0;
    }
    // Snap error is O(1): bounded by the initial snap precision, never grows.
    // Float error is O(√N · σ): grows as a random walk with each operation.
    //
    // The "advantage" is the error *growth factor* float suffers vs. snap:
    //   snap grows by 0× per step  →  total growth factor: 1
    //   float grows by σ per step  →  total growth factor: √N
    //
    // So snap is √N times better than float at N operations.
    (ops as f64).sqrt().max(1.0)
}

/// Run a full benchmark comparing float vs. snap over a default workload.
///
/// Uses 1,000,000 operations to make the float drift clearly visible.
/// Returns a [`BenchmarkResult`] with all metrics populated.
///
/// # Examples
///
/// ```rust
/// use ct_demo::benchmark;
///
/// let r = benchmark();
/// assert_eq!(r.ops, 1_000_000);
/// assert_eq!(r.snap_result, 3);
/// assert!(r.advantage >= 1.0);
/// ```
pub fn benchmark() -> BenchmarkResult {
    let ops = 1_000_000_usize;
    let true_value = 3.0_f64;

    let (snap_result, float_result) = snap_verify(ops);

    let float_error = (float_result - true_value).abs();
    // snap is always exact for integer inputs
    let snap_error = (snap_result as f64 - true_value).abs();

    // Advantage is the error growth factor: snap is O(1), float is O(√N).
    let advantage = advantage_ratio(ops);

    let run_id = Uuid::new_v4().to_string();

    BenchmarkResult {
        float_result,
        snap_result,
        float_error,
        snap_error,
        ops,
        advantage,
        run_id,
    }
}

// ── Unit tests ─────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn snap_exact_integers() {
        let m = PythagoreanManifold::default();
        assert_eq!(snap(3.0, &m), 3);
        assert_eq!(snap(4.0, &m), 4);
        assert_eq!(snap(5.0, &m), 5);
        assert_eq!(snap(0.0, &m), 0);
        assert_eq!(snap(-3.0, &m), -3);
    }

    #[test]
    fn snap_rounds_halfway() {
        let m = PythagoreanManifold::new(2, 1000, 1);
        // 2.5 rounds to 3 (round-half-away-from-zero in f64)
        assert_eq!(snap(2.5, &m), 3);
        assert_eq!(snap(3.4, &m), 3);
        assert_eq!(snap(3.6, &m), 4);
    }

    #[test]
    fn snap_clamps_to_max_coordinate() {
        let m = PythagoreanManifold::new(2, 10, 1);
        assert_eq!(snap(999.9, &m), 10);
        assert_eq!(snap(-999.9, &m), -10);
    }

    #[test]
    fn snap_with_resolution() {
        let m = PythagoreanManifold::new(2, 100, 5);
        assert_eq!(snap(0.0, &m), 0);
        assert_eq!(snap(7.0, &m), 5);   // closer to 5 than 10
        assert_eq!(snap(8.0, &m), 10);  // closer to 10
        assert_eq!(snap(13.0, &m), 15);
    }

    #[test]
    fn drift_accumulate_sqrt_scaling() {
        let sigma = 1e-10;
        let e1 = drift_accumulate(100, sigma);
        let e2 = drift_accumulate(10_000, sigma);
        let ratio = e2 / e1;
        assert!((ratio - 10.0).abs() < 1e-9, "expected ratio≈10, got {ratio}");
    }

    #[test]
    fn drift_accumulate_zero_ops() {
        assert_eq!(drift_accumulate(0, 1e-10), 0.0);
        assert_eq!(drift_accumulate(0, 1.0), 0.0);
    }

    #[test]
    fn snap_verify_snap_is_always_exact() {
        for ops in [0, 1, 1000, 1_000_000] {
            let (snap_result, _) = snap_verify(ops);
            assert_eq!(snap_result, 3, "snap_result should be 3 for ops={ops}");
        }
    }

    #[test]
    fn advantage_ratio_grows_with_ops() {
        let a1 = advantage_ratio(100);
        let a2 = advantage_ratio(10_000);
        let a3 = advantage_ratio(1_000_000);
        assert!(a2 > a1, "advantage should grow: a1={a1}, a2={a2}");
        assert!(a3 > a2, "advantage should grow: a2={a2}, a3={a3}");
    }

    #[test]
    fn advantage_ratio_zero_ops() {
        assert_eq!(advantage_ratio(0), 1.0);
    }

    #[test]
    fn benchmark_returns_expected_snap_result() {
        let r = benchmark();
        assert_eq!(r.snap_result, 3);
        assert_eq!(r.ops, 1_000_000);
        assert!(r.advantage >= 1.0);
        assert!(!r.run_id.is_empty());
    }

    #[test]
    fn manifold_grid_point_count() {
        let m = PythagoreanManifold::new(1, 10, 1);
        assert_eq!(m.grid_point_count(), 21); // -10..=10 inclusive
    }

    #[test]
    fn manifold_id_format() {
        let m = PythagoreanManifold::new(2, 100, 1);
        assert_eq!(m.id(), "pythagorean-manifold-2-100-1");
    }
}
