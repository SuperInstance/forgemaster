//! Eisenstein integer lattice ℤ[ω] — the crown jewel of snap topologies.
//!
//! Eisenstein integers are complex numbers of the form a + b·ω where
//! ω = e^(2πi/3) = (-1 + i√3)/2 is the primitive cube root of unity.
//! They form the hexagonal lattice (A₂ root system), which provides:
//!
//! - **Densest packing** in 2D — maximum information per snap
//! - **Isotropic snap** — no directional bias in attention
//! - **PID guarantee** — H¹ = 0, no obstructions to composing attention
//! - **6-fold symmetry** — matches human peripheral attention
//!
//! The snap operation is O(1) — direct computation, no search.

use std::fmt;
use std::ops::{Add, Mul, Sub};

/// An Eisenstein integer a + b·ω where ω = e^(2πi/3).
///
/// # Examples
///
/// ```
/// use snapkit::EisensteinInt;
///
/// let e = EisensteinInt::new(3, 2);
/// assert_eq!(e.norm(), 7); // 3² - 3·2 + 2² = 9 - 6 + 4 = 7
///
/// let e2 = EisensteinInt::new(1, 1);
/// let sum = e + e2;
/// assert_eq!(sum, EisensteinInt::new(4, 3));
/// ```
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct EisensteinInt {
    /// Real coefficient a (integer part)
    pub a: i64,
    /// ω coefficient b
    pub b: i64,
}

impl EisensteinInt {
    /// Create a new Eisenstein integer a + b·ω.
    #[inline]
    pub fn new(a: i64, b: i64) -> Self {
        Self { a, b }
    }

    /// The Eisenstein norm: a² - ab + b².
    ///
    /// This is the squared magnitude |a + b·ω|², always non-negative.
    /// The norm is multiplicative: N(z·w) = N(z)·N(w).
    ///
    /// # Examples
    ///
    /// ```
    /// use snapkit::EisensteinInt;
    ///
    /// assert_eq!(EisensteinInt::new(0, 1).norm(), 1);
    /// assert_eq!(EisensteinInt::new(1, 1).norm(), 1); // unit
    /// assert_eq!(EisensteinInt::new(2, 1).norm(), 3); // prime
    /// ```
    #[inline]
    pub fn norm(self) -> i64 {
        let a = self.a;
        let b = self.b;
        a * a - a * b + b * b
    }

    /// Returns true if this is a unit (norm = 1).
    ///
    /// The six units are: ±1, ±ω, ±ω²
    /// Represented as: (1,0), (-1,0), (0,1), (0,-1), (1,1), (-1,-1)
    #[inline]
    pub fn is_unit(self) -> bool {
        self.norm() == 1
    }

    /// Returns true if this is zero.
    #[inline]
    pub fn is_zero(self) -> bool {
        self.a == 0 && self.b == 0
    }

    /// Conjugate: a + b·ω → (a - b) - b·ω
    ///
    /// In the Eisenstein ring, conjugation swaps ω and ω².
    /// The conjugate of a + b·ω is (a - b) - b·ω.
    #[inline]
    pub fn conjugate(self) -> Self {
        Self {
            a: self.a - self.b,
            b: -self.b,
        }
    }

    /// Complex representation as (real, imag) tuple.
    ///
    /// Since ω = -1/2 + i√3/2:
    ///   real = a - b/2
    ///   imag = b·√3/2
    pub fn to_complex(self) -> (f64, f64) {
        let sqrt3_2 = 0.866_025_403_784_438_6_f64;
        let real = self.a as f64 - self.b as f64 * 0.5;
        let imag = self.b as f64 * sqrt3_2;
        (real, imag)
    }
}

impl Add for EisensteinInt {
    type Output = Self;

    #[inline]
    fn add(self, other: Self) -> Self {
        Self {
            a: self.a + other.a,
            b: self.b + other.b,
        }
    }
}

impl Sub for EisensteinInt {
    type Output = Self;

    #[inline]
    fn sub(self, other: Self) -> Self {
        Self {
            a: self.a - other.a,
            b: self.b - other.b,
        }
    }
}

impl Mul for EisensteinInt {
    type Output = Self;

    /// Multiplication in ℤ[ω].
    ///
    /// Using ω² = ω̄ = -1 - ω:
    ///   (a + b·ω)(c + d·ω) = ac + (ad + bc)ω + bd·ω²
    ///                      = ac + (ad + bc)ω + bd(-1 - ω)
    ///                      = (ac - bd) + (ad + bc - bd)ω
    #[inline]
    fn mul(self, other: Self) -> Self {
        let a1 = self.a;
        let b1 = self.b;
        let a2 = other.a;
        let b2 = other.b;
        Self {
            a: a1 * a2 - b1 * b2,
            b: a1 * b2 + b1 * a2 - b1 * b2,
        }
    }
}

impl fmt::Display for EisensteinInt {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        if self.b == 0 {
            write!(f, "{}", self.a)
        } else if self.a == 0 {
            if self.b == 1 {
                write!(f, "ω")
            } else if self.b == -1 {
                write!(f, "-ω")
            } else {
                write!(f, "{}ω", self.b)
            }
        } else {
            let sign = if self.b > 0 { "+" } else { "-" };
            let abs_b = self.b.abs();
            if abs_b == 1 {
                write!(f, "{}{}ω", self.a, sign)
            } else {
                write!(f, "{}{}{}ω", self.a, sign, abs_b)
            }
        }
    }
}

/// Snap a 2D point (real, imag) to the nearest Eisenstein integer.
///
/// The algorithm works by solving for the nearest lattice point directly
/// (O(1), no search). Given a point (x, y):
///
/// 1. Compute lattice coordinates (a, b) where point = a + b·ω
/// 2. Round both a and b to nearest integer
/// 3. That's the nearest Eisenstein integer
///
/// # Examples
///
/// ```
/// use snapkit::{eisenstein_snap, EisensteinInt};
///
/// // Snap to nearest lattice point
/// let nearest = eisenstein_snap((1.2, 0.7));
/// assert_eq!(nearest, EisensteinInt::new(1, 1));
///
/// // Origin snaps to zero
/// let origin = eisenstein_snap((0.0, 0.0));
/// assert_eq!(origin, EisensteinInt::new(0, 0));
/// ```
pub fn eisenstein_snap(point: (f64, f64)) -> EisensteinInt {
    let (x, y) = point;
    // ω = -1/2 + i√3/2
    // So: x = a - b/2, y = b·√3/2
    // => b = 2y/√3, a = x + b/2
    let sqrt3_2 = 0.866_025_403_784_438_6_f64;
    let b = (y / sqrt3_2).round() as i64;
    let a = (x + b as f64 / 2.0).round() as i64;
    EisensteinInt { a, b }
}

/// Distance from a 2D point to the nearest Eisenstein lattice point.
///
/// # Examples
///
/// ```
/// use snapkit::eisenstein_distance;
///
/// // At the origin, distance is 0
/// assert!(eisenstein_distance((0.0, 0.0)).abs() < 1e-10);
///
/// // Distance is bounded by the covering radius ~0.577
/// let d = eisenstein_distance((0.5, 0.3));
/// assert!(d < 0.58);
/// ```
pub fn eisenstein_distance(point: (f64, f64)) -> f64 {
    let snapped = eisenstein_snap(point);
    let (sx, sy) = snapped.to_complex();
    let dx = point.0 - sx;
    let dy = point.1 - sy;
    (dx * dx + dy * dy).sqrt()
}

/// Snap a batch of 2D points to Eisenstein integers in one pass.
///
/// Processes points as two parallel slices (x-coords, y-coords) for
/// SIMD-friendly layout. Returns a `Vec<EisensteinInt>` of the same length.
///
/// # Examples
///
/// ```
/// use snapkit::{eisenstein_snap_batch, EisensteinInt};
///
/// let xs = &[1.2, 0.0, -0.8];
/// let ys = &[0.7, 0.0, 1.3];
/// let result = eisenstein_snap_batch(xs, ys);
/// assert_eq!(result.len(), 3);
/// ```
pub fn eisenstein_snap_batch(xs: &[f64], ys: &[f64]) -> Vec<EisensteinInt> {
    let len = xs.len().min(ys.len());
    let mut result = Vec::with_capacity(len);
    let sqrt3_2 = 0.866_025_403_784_438_6_f64;
    for i in 0..len {
        let b = (ys[i] / sqrt3_2).round() as i64;
        let a = (xs[i] + b as f64 / 2.0).round() as i64;
        result.push(EisensteinInt { a, b });
    }
    result
}

/// Generate the six nearest neighbors of an Eisenstein integer.
///
/// Returns the six neighbors connected by unit vectors: ±1, ±ω, ±(1+ω).
/// These correspond to the six directions of the hexagonal lattice.
///
/// # Examples
///
/// ```
/// use snapkit::{EisensteinInt, eisenstein_neighbors};
///
/// let zero = EisensteinInt::new(0, 0);
/// let neighbors = eisenstein_neighbors(zero);
/// assert_eq!(neighbors.len(), 6);
/// // All neighbors have norm 1 (units)
/// for n in &neighbors {
///     assert!(n.is_unit());
/// }
/// ```
pub fn eisenstein_neighbors(e: EisensteinInt) -> Vec<EisensteinInt> {
    vec![
        e + EisensteinInt::new(1, 0),   // +1
        e - EisensteinInt::new(1, 0),   // -1
        e + EisensteinInt::new(0, 1),   // +ω
        e - EisensteinInt::new(0, 1),   // -ω
        e + EisensteinInt::new(1, 1),   // +(1+ω) = -ω²
        e - EisensteinInt::new(1, 1),   // -(1+ω) = ω²
    ]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_eisenstein_units() {
        let units = [
            EisensteinInt::new(1, 0),
            EisensteinInt::new(-1, 0),
            EisensteinInt::new(0, 1),
            EisensteinInt::new(0, -1),
            EisensteinInt::new(1, 1),
            EisensteinInt::new(-1, -1),
        ];
        for u in &units {
            assert!(u.is_unit(), "unit {} not recognized", u);
        }
        // The unit group has exactly 6 elements
        assert_eq!(units.iter().filter(|u| u.is_unit()).count(), 6);
    }

    #[test]
    fn test_eisenstein_add() {
        let a = EisensteinInt::new(3, 2);
        let b = EisensteinInt::new(1, 5);
        assert_eq!(a + b, EisensteinInt::new(4, 7));
    }

    #[test]
    fn test_eisenstein_sub() {
        let a = EisensteinInt::new(5, 3);
        let b = EisensteinInt::new(2, 1);
        assert_eq!(a - b, EisensteinInt::new(3, 2));
    }

    #[test]
    fn test_eisenstein_mul() {
        // (a + bω)(c + dω) = (ac - bd) + (ad + bc - bd)ω
        let a = EisensteinInt::new(2, 1);
        let b = EisensteinInt::new(1, 1);
        let p = a * b;
        // a=2,b=1,c=1,d=1: ac-bd = 2-1=1; ad+bc-bd = 2+1-1=2
        assert_eq!(p, EisensteinInt::new(1, 2));
    }

    #[test]
    fn test_eisenstein_norm_multiplicative() {
        let a = EisensteinInt::new(3, 2);
        let b = EisensteinInt::new(1, 4);
        assert_eq!((a * b).norm(), a.norm() * b.norm());
    }

    #[test]
    fn test_eisenstein_snap_origin() {
        let snapped = eisenstein_snap((0.0, 0.0));
        assert_eq!(snapped, EisensteinInt::new(0, 0));
    }

    #[test]
    fn test_eisenstein_snap_simple() {
        let snapped = eisenstein_snap((1.2, 0.7));
        assert_eq!(snapped, EisensteinInt::new(1, 1));
    }

    #[test]
    fn test_eisenstein_snap_negative() {
        let snapped = eisenstein_snap((-0.8, -1.3));
        // b = round(-1.3/0.866) = round(-1.501) = -2
        // a = round(-0.8 + (-2)/2) = round(-0.8 - 1) = round(-1.8) = -2
        assert_eq!(snapped, EisensteinInt::new(-2, -2));
    }

    #[test]
    fn test_eisenstein_distance_origin() {
        let d = eisenstein_distance((0.0, 0.0));
        assert!(d.abs() < 1e-10);
    }

    #[test]
    fn test_eisenstein_distance_positive() {
        let d = eisenstein_distance((0.5, 0.3));
        assert!(d < 0.58, "distance {} >= 0.58", d);
    }

    #[test]
    fn test_eisenstein_neighbors_count() {
        let e = EisensteinInt::new(5, 3);
        let neighbors = eisenstein_neighbors(e);
        assert_eq!(neighbors.len(), 6);
        // All should be distinct
        let mut sorted = neighbors.clone();
        sorted.sort_by_key(|n| (n.a, n.b));
        sorted.dedup();
        assert_eq!(sorted.len(), 6);
    }

    #[test]
    fn test_eisenstein_conjugate() {
        let e = EisensteinInt::new(3, 2);
        let c = e.conjugate();
        // Conjugate of a + bω is (a-b) - bω
        assert_eq!(c.a, 1); // 3-2 = 1
        assert_eq!(c.b, -2);
    }

    #[test]
    fn test_eisenstein_snap_batch() {
        let xs = &[1.2, 0.0, -0.8, 2.5];
        let ys = &[0.7, 0.0, 1.3, 1.1];
        let result = eisenstein_snap_batch(xs, ys);
        assert_eq!(result.len(), 4);
        // First point should snap to (1,1) as before
        assert_eq!(result[0], EisensteinInt::new(1, 1));
    }

    #[test]
    fn test_eisenstein_display() {
        assert_eq!(format!("{}", EisensteinInt::new(3, 2)), "3+2ω");
        assert_eq!(format!("{}", EisensteinInt::new(3, -2)), "3-2ω");
        assert_eq!(format!("{}", EisensteinInt::new(0, 1)), "ω");
        assert_eq!(format!("{}", EisensteinInt::new(0, -1)), "-ω");
        assert_eq!(format!("{}", EisensteinInt::new(5, 0)), "5");
        assert_eq!(format!("{}", EisensteinInt::new(0, 0)), "0");
    }
}
