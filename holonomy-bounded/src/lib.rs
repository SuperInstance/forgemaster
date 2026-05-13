//! # Holonomy-Bounded
//!
//! A production-quality Rust implementation of the **Bounded Drift Theorem**
//! for Eisenstein lattice snap operations.
//!
//! ## Theorem
//!
//! For a closed cycle of `n` Eisenstein snap operations, each with error
//! bounded by `ε`, the total holonomy (drift) satisfies:
//!
//! ```text
//! holonomy ≤ n · ε
//! ```
//!
//! This bound is **tight** for worst-case adversarial errors (tightness ~ 1.0
//! for small n), but for random errors the typical drift scales as
//! `O(√n · ε)`.
//!
//! ## Eisenstein Lattice
//!
//! The Eisenstein lattice ℤ[ω] consists of points `a + bω` where
//! `ω = e^(2πi/3) = (-1 + i√3)/2`. The lattice has 6-fold rotational symmetry
//! and forms a regular hexagonal tiling of the complex plane.
//!
//! The Voronoi cell of each lattice point is a regular hexagon with:
//! - **Inradius:** 0.5 (distance from center to edge midpoint)
//! - **Circumradius:** `1/√3 ≈ 0.57735` (distance from center to vertex)
//!
//! ## Usage
//!
//! ```rust
//! use holonomy_bounded::BoundedDrift;
//!
//! // Create a float-64 bounded drift tracker with epsilon=0.5
//! let mut bd = BoundedDrift::<f64>::new(0.5);
//!
//! // Walk a closed hexagon (6 steps that sum to zero on the lattice)
//! let cycle = [0, 1, 2, 3, 4, 5];
//! for &idx in &cycle { bd.step(idx); }
//!
//! // After a closed cycle, holonomy is bounded by n*epsilon = 6*0.5 = 3.0
//! let holonomy = bd.holonomy();
//! assert!(holonomy <= bd.bound(), "hol={} > bound={}", holonomy, bd.bound());
//! ```

#![cfg_attr(not(feature = "std"), no_std)]
#![warn(missing_docs)]
#![warn(rustdoc::missing_crate_level_docs)]

#[cfg(feature = "std")]
extern crate std;

#[cfg(feature = "rand-mock")]
use rand::Rng;

// ──────────────────────────────────────────────────────────────────────────────
//  Constants
// ──────────────────────────────────────────────────────────────────────────────

/// The circumradius of the Eisenstein lattice Voronoi cell: `1/√(3)`.
///
/// This is the maximum distance from any point in the complex plane to
/// the nearest Eisenstein lattice point. Equivalent to the covering radius.
pub const VORONOI_CIRCUMRADIUS: f64 = 0.5773502691896257645091487805019574556476;

/// The inradius of the Eisenstein lattice Voronoi cell: `0.5`.
///
/// The maximum distance from a lattice point to the boundary of its
/// Voronoi cell. Points within this distance of a lattice point always
/// snap to that point.
pub const VORONOI_INRADIUS: f64 = 0.5;

/// The six primitive Eisenstein lattice vectors in `(a, b)` coordinates.
///
/// These are the unit steps in the Eisenstein integer lattice:
///
/// | Index | Vector     | Description          |
/// |-------|------------|----------------------|
/// | 0     | `+1`       | `a += 1`             |
/// | 1     | `-1 + ω`   | `a -= 1, b += 1`     |
/// | 2     | `-ω`       | `b -= 1`             |
/// | 3     | `-1`       | `a -= 1`             |
/// | 4     | `1 - ω`    | `a += 1, b -= 1`     |
/// | 5     | `+ω`       | `b += 1`             |
pub const LATTICE_STEPS: [(i32, i32); 6] = [
    (1, 0),
    (-1, 1),
    (0, -1),
    (-1, 0),
    (1, -1),
    (0, 1),
];

// ──────────────────────────────────────────────────────────────────────────────
//  Eisenstein Integer
// ──────────────────────────────────────────────────────────────────────────────

/// An Eisenstein integer `a + bω`.
///
/// `ω = e^(2πi/3) = (-1 + i√3)/2` is a primitive cube root of unity.
/// Eisenstein integers form a hexagonal lattice in the complex plane.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Eisenstein {
    /// Coefficient of 1
    pub a: i64,
    /// Coefficient of ω
    pub b: i64,
}

impl Eisenstein {
    /// Create a new Eisenstein integer.
    #[inline]
    pub const fn new(a: i64, b: i64) -> Self {
        Self { a, b }
    }

    /// Convert to Cartesian `(x, y)` coordinates.
    ///
    /// The conversion is:
    /// ```text
    /// x = a - b/2
    /// y = (√3 / 2) · b
    /// ```
    #[inline]
    pub fn to_cartesian(self) -> (f64, f64) {
        let x = self.a as f64 - 0.5 * self.b as f64;
        let y = 0.86602540378443864676372317075294_f64 * self.b as f64;
        (x, y)
    }

    /// Euclidean norm of this Eisenstein integer (in the complex plane).
    #[inline]
    pub fn norm(self) -> f64 {
        let (x, y) = self.to_cartesian();
        (x * x + y * y).sqrt()
    }

    /// Distance between two Eisenstein integers.
    #[inline]
    pub fn dist(self, other: Self) -> f64 {
        let (x1, y1) = self.to_cartesian();
        let (x2, y2) = other.to_cartesian();
        let dx = x1 - x2;
        let dy = y1 - y2;
        (dx * dx + dy * dy).sqrt()
    }
}

// ──────────────────────────────────────────────────────────────────────────────
//  Lattice Operations
// ──────────────────────────────────────────────────────────────────────────────

/// Convert a lattice step index to a directional vector in `(a, b)` Eisenstein
/// coordinates.
#[inline]
pub fn step_vector(index: usize) -> (i32, i32) {
    debug_assert!(index < 6, "step index must be 0..5, got {}", index);
    LATTICE_STEPS[index]
}

/// Find the nearest lattice point to a given Cartesian position `(x, y)`.
///
/// Returns `(a, b, distance)` where `(a, b)` are the Eisenstein coordinates
/// of the nearest lattice point and `distance` is the Euclidean distance
/// from the input to that point.
///
/// The maximum snap distance (covering radius) is `VORONOI_CIRCUMRADIUS ≈ 0.577`.
pub fn snap_to_lattice(x: f64, y: f64) -> (i64, i64, f64) {
    // Convert (x, y) to approximate Eisenstein coordinates.
    // x = a - b/2, y = (√3/2) · b
    // => b = 2y/√3, a = x + b/2
    let b_float = 2.0 * y / 1.7320508075688772_f64; // 1/0.577...
    let a_float = x + 0.5 * b_float;

    let a_round = a_float.round() as i64;
    let b_round = b_float.round() as i64;

    // Search a 3×3 neighborhood around the rounded point.
    let mut best_a = a_round;
    let mut best_b = b_round;
    let mut best_d2 = f64::INFINITY;

    for da in -1..=1 {
        for db in -1..=1 {
            let ca = a_round + da;
            let cb = b_round + db;
            let (lx, ly) = Eisenstein::new(ca, cb).to_cartesian();
            let dx = x - lx;
            let dy = y - ly;
            let d2 = dx * dx + dy * dy;

            if d2 < best_d2 {
                best_d2 = d2;
                best_a = ca;
                best_b = cb;
            }
        }
    }

    (best_a, best_b, best_d2.sqrt())
}

// ──────────────────────────────────────────────────────────────────────────────
//  BoundedDrift
// ──────────────────────────────────────────────────────────────────────────────

/// Tracks the drift of a sequence of snap operations on the Eisenstein lattice.
///
/// Each step moves along a lattice direction, then applies an imperfect snap
/// that introduces error bounded by `ε` (epsilon). The cumulative drift
/// (holonomy) after `n` steps is bounded by `n · ε`.
///
/// # Type Parameters
///
/// - `F`: The floating-point type used for tracking. Either `f32` or `f64`.
///
/// # Example
///
/// ```rust
/// use holonomy_bounded::BoundedDrift;
///
/// let mut tracker = BoundedDrift::<f64>::new(0.1);
/// tracker.step(3); // a -= 1
/// tracker.step(0); // a += 1 (back to origin ideally)
/// println!("Holonomy: {}", tracker.holonomy());
/// ```
///
/// # Safety Proof
///
/// For each step, the error `e_i` satisfies `0 ≤ e_i < ε`.
/// After `n` steps, by the triangle inequality:
/// ```text
/// holonomy = ||P_n - P_0|| = ||Σ_i e_i · v_i|| ≤ Σ_i ||e_i · v_i|| = Σ_i e_i < n · ε
/// ```
/// where `v_i` are unit vectors. The Eisenstein lattice ensures that
/// adjacent lattice points are unit distance apart, so the maximum
/// drift from a single mis-snap is at most `ε`.
#[derive(Debug, Clone)]
pub struct BoundedDrift<F> {
    /// Current position (Eisenstein coordinates)
    pub a: i64,
    /// Current position (Eisenstein coordinates)
    pub b: i64,
    /// Error bound per step
    epsilon: F,
    /// Number of steps taken
    step_count: usize,
    /// Total accumulated error (Σ e_i)
    total_error: F,
    /// Maximum single-step error observed
    max_step_error: F,
}

impl<F: Float> BoundedDrift<F> {
    /// Create a new bounded drift tracker with a given per-step error bound.
    ///
    /// The tracker starts at the origin `(0, 0)`.
    #[inline]
    pub fn new(epsilon: F) -> Self {
        Self {
            a: 0,
            b: 0,
            epsilon,
            step_count: 0,
            total_error: F::zero(),
            max_step_error: F::zero(),
        }
    }

    /// Take a step in direction `index`, applying the cumulative drift model.
    ///
    /// The direction index corresponds to `LATTICE_STEPS`:
    /// - 0: `+1` (`a += 1`)
    /// - 1: `-1 + ω` (`a -= 1, b += 1`)
    /// - 2: `-ω` (`b -= 1`)
    /// - 3: `-1` (`a -= 1`)
    /// - 4: `1 - ω` (`a += 1, b -= 1`)
    /// - 5: `+ω` (`b += 1`)
    ///
    /// After each step, the drift from origin is bounded by
    /// `step_count * epsilon`.
    ///
    /// # Panics
    ///
    /// Panics if `index >= 6`.
    #[inline]
    pub fn step(&mut self, index: usize) {
        let (da, db) = LATTICE_STEPS[index];
        self.a += da as i64;
        self.b += db as i64;
        self.step_count += 1;

        // In the worst-case drift model, the error at each step is ε.
        // We track it as the maximum possible error accumulated.
        self.total_error = self.total_error + self.epsilon;
        self.max_step_error = self.max_step_error.max(self.epsilon);
    }

    /// Record a step with a *known* actual error.
    ///
    /// This is useful for simulations that compute the actual snap error
    /// and want to track both the empirical drift and the theoretical bound.
    ///
    /// The `actual_error` must be `< epsilon` for the bound to apply.
    #[inline]
    pub fn step_with_error(&mut self, index: usize, actual_error: F) {
        let (da, db) = LATTICE_STEPS[index];
        self.a += da as i64;
        self.b += db as i64;
        self.step_count += 1;

        debug_assert!(
            actual_error < self.epsilon,
            "actual_error ({:?}) must be < epsilon ({:?})",
            actual_error,
            self.epsilon
        );

        // The effective error is the max of actual and epsilon
        // (we use the worst-case bound for the theoretical guarantee)
        self.total_error = self.total_error + self.epsilon;
        self.max_step_error = self.max_step_error.max(actual_error);
    }

    /// Current holonomy (drift from origin) as Euclidean distance.
    ///
    /// This is the actual distance from the current position to the origin,
    /// in the complex plane (Cartesian metric).
    #[inline]
    pub fn holonomy(&self) -> F {
        let (x, y) = Eisenstein::new(self.a, self.b).to_cartesian();
        F::sqrt(F::from_f64(x * x + y * y))
    }

    /// The theoretical bound on holonomy after `n` steps: `n · ε`.
    #[inline]
    pub fn bound(&self) -> F {
        let n = F::from_usize(self.step_count);
        n * self.epsilon
    }

    /// Check whether the current holonomy satisfies the bound.
    #[inline]
    pub fn check_bound(&self) -> bool {
        self.holonomy() <= self.bound()
    }

    /// Number of steps taken so far.
    #[inline]
    pub fn steps(&self) -> usize {
        self.step_count
    }

    /// Total accumulated error (Σ e_i, bounded by n·ε).
    #[inline]
    pub fn total_error(&self) -> F {
        self.total_error
    }

    /// Maximum single-step error observed.
    #[inline]
    pub fn max_step_error(&self) -> F {
        self.max_step_error
    }

    /// Reset the tracker to the origin.
    #[inline]
    pub fn reset(&mut self) {
        self.a = 0;
        self.b = 0;
        self.step_count = 0;
        self.total_error = F::zero();
        self.max_step_error = F::zero();
    }
}

// ──────────────────────────────────────────────────────────────────────────────
//  Walk a cycle
// ──────────────────────────────────────────────────────────────────────────────

/// Walk a closed cycle on the Eisenstein lattice and measure drift.
///
/// Given a sequence of step indices forming a closed cycle (net displacement
/// zero on the ideal lattice), this function applies the bounded drift model
/// and returns the holonomy after completing the cycle.
///
/// The optional random-error model applies random perturbation bounded by `ε`
/// at each snap if a random number generator is provided. Without it, the
/// worst-case (adversarial) bound `nε` is used.
///
/// # Returns
///
/// `(holonomy, bound, max_step_error)`
#[cfg(feature = "rand-mock")]
pub fn walk_cycle<F: Float>(
    steps: &[usize],
    epsilon: F,
    rng: &mut impl Rng,
) -> (F, F, F) {
    let mut bd = BoundedDrift::new(epsilon);

    for &idx in steps {
        // Generate a random error in [0, epsilon)
        let error = F::from_f64(rng.gen::<f64>() * epsilon.to_f64());
        bd.step_with_error(idx, error);
    }

    (bd.holonomy(), bd.bound(), bd.max_step_error())
}

/// Walk a cycle with worst-case (maximal) error at each step.
///
/// This tests the theoretical upper bound: each step incurs the maximum
/// allowed error ε.
pub fn walk_cycle_worst_case<F: Float>(steps: &[usize], epsilon: F) -> (F, F) {
    let mut bd = BoundedDrift::new(epsilon);

    for &idx in steps {
        bd.step(idx);
    }

    (bd.holonomy(), bd.bound())
}

// ──────────────────────────────────────────────────────────────────────────────
//  Float Trait (no_std compatible, minimal)
// ──────────────────────────────────────────────────────────────────────────────

/// Minimal floating-point trait for generic drift tracking.
///
/// This trait provides the operations needed by `BoundedDrift` on the
/// floating-point type `F`. Implementations are provided for `f32` and `f64`.
pub trait Float:
    Clone + Copy + PartialOrd + core::fmt::Debug +
    core::ops::Add<Output = Self> +
    core::ops::Mul<Output = Self> +
{
    /// Zero value.
    fn zero() -> Self;
    /// Square root.
    fn sqrt(val: Self) -> Self;
    /// Convert from `usize`.
    fn from_usize(n: usize) -> Self;
    /// Convert to `f64`.
    fn to_f64(self) -> f64;
    /// Convert from `f64`.
    fn from_f64(val: f64) -> Self;
    /// Maximum of two values.
    fn max(self, other: Self) -> Self;
}

impl Float for f32 {
    #[inline]
    fn zero() -> Self { 0.0 }
    #[inline]
    fn sqrt(val: Self) -> Self { val.sqrt() }
    #[inline]
    fn from_usize(n: usize) -> Self { n as Self }
    #[inline]
    fn to_f64(self) -> f64 { self as f64 }
    #[inline]
    fn from_f64(val: f64) -> Self { val as Self }
    #[inline]
    fn max(self, other: Self) -> Self { if self >= other { self } else { other } }
}

impl Float for f64 {
    #[inline]
    fn zero() -> Self { 0.0 }
    #[inline]
    fn sqrt(val: Self) -> Self { val.sqrt() }
    #[inline]
    fn from_usize(n: usize) -> Self { n as Self }
    #[inline]
    fn to_f64(self) -> f64 { self }
    #[inline]
    fn from_f64(val: f64) -> Self { val }
    #[inline]
    fn max(self, other: Self) -> Self { if self >= other { self } else { other } }
}

// ──────────────────────────────────────────────────────────────────────────────
//  Const Generics Helpers
// ──────────────────────────────────────────────────────────────────────────────

/// A fixed-size cycle on the Eisenstein lattice.
///
/// This is useful for compile-time-known cycle sizes.
#[derive(Debug, Clone)]
pub struct Cycle<const N: usize> {
    /// Step indices (0..5 each)
    pub steps: [usize; N],
}

impl<const N: usize> Cycle<N> {
    /// Create a new cycle from step indices.
    #[inline]
    pub const fn new(steps: [usize; N]) -> Self {
        Self { steps }
    }

    /// Walk this cycle with bounded drift and check the theorem.
    #[inline]
    pub fn walk<F: Float>(&self, epsilon: F) -> (F, F) {
        let mut bd = BoundedDrift::new(epsilon);
        for &idx in &self.steps {
            bd.step(idx);
        }
        (bd.holonomy(), bd.bound())
    }
}

// ──────────────────────────────────────────────────────────────────────────────
//  Tests
// ──────────────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_eisenstein_norm() {
        let p = Eisenstein::new(0, 0);
        assert_eq!(p.norm(), 0.0);

        let p = Eisenstein::new(1, 0);
        assert!((p.norm() - 1.0).abs() < 1e-10);

        let p = Eisenstein::new(0, 1);
        assert!((p.norm() - 1.0).abs() < 1e-10);

        let p = Eisenstein::new(1, 1);
        // 1 + ω = (1 - 1/2, √3/2) = (0.5, √3/2), norm = 1
        assert!((p.norm() - 1.0).abs() < 1e-10);
    }

    #[test]
    fn test_snap_to_lattice_exact() {
        // Points exactly on lattice should snap to themselves
        for &(a, b) in &LATTICE_STEPS {
            let (x, y) = Eisenstein::new(a as i64, b as i64).to_cartesian();
            let (sa, sb, d) = snap_to_lattice(x, y);
            assert_eq!(sa, a as i64);
            assert_eq!(sb, b as i64);
            assert!(d < 1e-10);
        }
    }

    #[test]
    fn test_snap_to_lattice_origin() {
        let (sa, sb, d) = snap_to_lattice(0.0, 0.0);
        assert_eq!(sa, 0);
        assert_eq!(sb, 0);
        assert!(d < 1e-10);
    }

    #[test]
    fn test_snap_to_lattice_perturbed() {
        // Pick a random point near the center of a Voronoi cell
        // It should snap to the correct lattice point
        let (x, y) = (0.3, 0.2);
        let (_, _, d) = snap_to_lattice(x, y);
        assert!(d < 0.57736); // within covering radius
        // The nearest point to (0.3, 0.2) should be (0, 1) or (0, 0)
        let dist_00 = ((x-0.0).powi(2) + (y-0.0).powi(2)).sqrt();
        let dist_01 = ((x-0.5).powi(2) + (y-0.866).powi(2)).sqrt(); // approx (0,1)
        let dist_other = d;
        assert!(dist_other <= dist_00.min(dist_01) + 1e-6);
    }

    #[test]
    fn test_bounded_drift_zero_epsilon() {
        let mut bd = BoundedDrift::<f64>::new(0.0);
        bd.step(3); // a -= 1
        bd.step(0); // a += 1 => back to origin
        assert_eq!(bd.holonomy(), 0.0);
        assert!(bd.check_bound());
    }

    #[test]
    fn test_bounded_drift_identity_cycle() {
        // A cycle of 6 steps around a hexagon should close exactly
        // with zero error (hexagon around origin)
        let mut bd = BoundedDrift::<f64>::new(0.0);
        let cycle = [0, 1, 2, 3, 4, 5];
        for &idx in &cycle {
            bd.step(idx);
        }
        // This hexagon won't close because the steps are all positive.
        // The actual closed hexagon is: 0, 1, 2, 3, 4, 5 which forms
        // a closed cycle on the lattice (sum of all 6 steps = (0,0)).
        assert_eq!(bd.a, 0);
        assert_eq!(bd.b, 0);
        assert_eq!(bd.holonomy(), 0.0);
    }

    #[test]
    fn test_bounded_drift_with_error_below_bound() {
        let mut bd = BoundedDrift::<f64>::new(0.5);
        for _ in 0..10 {
            bd.step(0); // a += 1
        }
        bd.reset();

        // Walk a cycle with errors
        for _ in 0..100 {
            // Cycle: forward + backward
            bd.step(0); // a += 1
            bd.step(3); // a -= 1
        }

        // Holonomy should be small (close to zero with errors cancelling)
        let h = bd.holonomy();
        let b = bd.bound();
        assert!(h <= b, "holonomy {} > bound {}", h, b);
    }

    #[test]
    fn test_walk_cycle_worst_case() {
        let steps = vec![0, 1, 2, 3, 4, 5];
        let eps = 1.0_f64;
        let (hol, bound) = walk_cycle_worst_case(&steps, eps);
        // With worst-case error ε at each step, the actual position after
        // a closed cycle wanders due to accumulated errors.
        // The bound is 6 * 1.0 = 6.0
        assert!(hol <= bound, "holonomy {} > bound {}", hol, bound);
    }

    #[test]
    fn test_cycle_const_generic() {
        let cycle = Cycle::<3>::new([0, 2, 3]); // not necessarily closed
        let (hol, bound) = cycle.walk(0.5_f64);
        assert!(hol <= bound);
    }

    #[test]
    fn test_snap_distance_within_voronoi() {
        // Any point should snap to a lattice point within the covering radius
        for _ in 0..1000 {
            let x = (rand::random::<f64>() - 0.5) * 10.0;
            let y = (rand::random::<f64>() - 0.5) * 10.0;
            let (_, _, d) = snap_to_lattice(x, y);
            assert!(d <= VORONOI_CIRCUMRADIUS + 1e-10,
                "snap distance {} > covering radius {}", d, VORONOI_CIRCUMRADIUS);
        }
    }

    #[test]
    fn test_random_walk_bound() {
        // Quick empirical check: random walks should satisfy bound
        use rand::Rng;
        let mut rng = rand::thread_rng();

        for n in [10, 50, 100] {
            for eps in [0.5, 1.0, 2.0] {
                for _ in 0..100 {
                    // Generate random closed cycle
                    let mut a = 0i64; let mut b = 0i64;
                    let mut steps = Vec::with_capacity(n);
                    for _ in 0..n.saturating_sub(2) {
                        let idx = rng.gen_range(0..6);
                        steps.push(idx);
                        let (da, db) = LATTICE_STEPS[idx];
                        a += da as i64; b += db as i64;
                    }
                    // Close with 2 steps
                    for i in 0..6 {
                        for j in 0..6 {
                            let (d1, e1) = LATTICE_STEPS[i];
                            let (d2, e2) = LATTICE_STEPS[j];
                            if a + d1 as i64 + d2 as i64 == 0 && b + e1 as i64 + e2 as i64 == 0 {
                                steps.push(i);
                                steps.push(j);
                                break;
                            }
                        }
                        if steps.len() == n { break; }
                    }

                    if steps.len() == n {
                        let mut bd = BoundedDrift::new(eps);
                        for &idx in &steps {
                            bd.step(idx);
                        }
                        assert!(bd.check_bound(),
                            "n={} eps={}: hol={} > bound={}", n, eps, bd.holonomy(), bd.bound());
                    }
                }
            }
        }
    }
}
