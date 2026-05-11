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
/// let e = EisensteinInt::new(3, 2);  // 3 + 2ω
/// assert_eq!(e.norm(), 7);  // 3² - 3·2 + 2² = 7
/// ```
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct EisensteinInt {
    /// Coefficient of 1 (real part coefficient).
    pub a: i64,
    /// Coefficient of ω (imaginary part coefficient).
    pub b: i64,
}

impl EisensteinInt {
    /// Create a new Eisenstein integer a + b·ω.
    #[inline]
    pub const fn new(a: i64, b: i64) -> Self {
        Self { a, b }
    }

    /// The Eisenstein norm: a² - ab + b².
    ///
    /// This is multiplicative: N(α·β) = N(α)·N(β), making it an
    /// Euclidean domain — the guarantee that H¹ = 0.
    #[inline]
    pub fn norm(self) -> i64 {
        self.a * self.a - self.a * self.b + self.b * self.b
    }

    /// Check if this is a unit (norm = 1).
    ///
    /// The six units of ℤ[ω] are: ±1, ±ω, ±(1+ω).
    #[inline]
    pub fn is_unit(self) -> bool {
        self.norm() == 1
    }

    /// The complex conjugate in ℤ[ω].
    ///
    /// Since ω̄ = ω² = -1 - ω:
    ///   conj(a + b·ω) = a + b·ω̄ = a + b(-1 - ω) = (a - b) - b·ω
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
        Self {
            a: self.a * other.a - self.b * other.b,
            b: self.a * other.b + self.b * other.a - self.b * other.b,
        }
    }
}

impl fmt::Display for EisensteinInt {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match (self.a, self.b) {
            (0, 0) => write!(f, "0"),
            (a, 0) => write!(f, "{}", a),
            (0, 1) => write!(f, "ω"),
            (0, -1) => write!(f, "-ω"),
            (0, b) => write!(f, "{}ω", b),
            (a, 1) => write!(f, "{}+ω", a),
            (a, -1) => write!(f, "{}-ω", a),
            (a, b) if b > 0 => write!(f, "{}+{}ω", a, b),
            (a, b) => write!(f, "{}{}ω", a, b),
        }
    }
}

/// Snap a 2D point to the nearest Eisenstein integer (ℤ[ω] lattice).
///
/// The hexagonal lattice has the densest packing in 2D. Uses O(1)
/// direct computation with neighbor checking for correctness.
///
/// Algorithm: convert to the Eisenstein basis (a,b), then check all 7
/// candidates (initial point + 6 hexagonal neighbors) and pick the
/// truly nearest one. This handles Voronoi cell boundary cases.
///
/// # Examples
///
/// ```
/// use snapkit::{eisenstein_snap, EisensteinInt};
///
/// // At the origin
/// let at_origin = eisenstein_snap((0.0, 0.0));
/// assert_eq!(at_origin, EisensteinInt::new(0, 0));
///
/// // Near (1.2, 0.7) — nearest lattice point is (2, 1)
/// let near = eisenstein_snap((1.2, 0.7));
/// assert_eq!(near, EisensteinInt::new(2, 1));
/// ```
pub fn eisenstein_snap(point: (f64, f64)) -> EisensteinInt {
    let (x, y) = point;
    // ω = -1/2 + i√3/2
    // So: x = a - b/2, y = b·√3/2
    // => b = 2y/√3, a = x + b/2
    let sqrt3_2 = 0.866_025_403_784_438_6_f64;
    let b_init = (y / sqrt3_2).round() as i64;
    let a_init = (x + b_init as f64 / 2.0).round() as i64;

    // The initial guess can be off by one. Check all 7 candidates.
    let candidates = [
        EisensteinInt { a: a_init, b: b_init },
        EisensteinInt { a: a_init + 1, b: b_init },
        EisensteinInt { a: a_init - 1, b: b_init },
        EisensteinInt { a: a_init, b: b_init + 1 },
        EisensteinInt { a: a_init, b: b_init - 1 },
        EisensteinInt { a: a_init + 1, b: b_init - 1 },
        EisensteinInt { a: a_init - 1, b: b_init + 1 },
    ];

    let mut best = candidates[0];
    let mut best_dist = f64::MAX;

    for &c in &candidates {
        let (cx, cy) = c.to_complex();
        let dx = x - cx;
        let dy = y - cy;
        let dist = dx * dx + dy * dy;
        if dist < best_dist {
            best_dist = dist;
            best = c;
        }
    }

    best
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
    for i in 0..len {
        result.push(eisenstein_snap((xs[i], ys[i])));
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
/// // All neighbors should be at unit distance
/// for n in &neighbors {
///     assert_eq!(n.norm(), 1, "{:?} has norm {}", n, n.norm());
/// }
/// ```
pub fn eisenstein_neighbors(e: EisensteinInt) -> Vec<EisensteinInt> {
    vec![
        e + EisensteinInt::new(1, 0),   // +1
        e + EisensteinInt::new(-1, 0),  // -1
        e + EisensteinInt::new(0, 1),   // +ω
        e + EisensteinInt::new(0, -1),  // -ω
        e + EisensteinInt::new(1, 1),   // +1+ω
        e + EisensteinInt::new(-1, -1), // -1-ω
    ]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_eisenstein_snap_origin() {
        let snapped = eisenstein_snap((0.0, 0.0));
        assert_eq!(snapped, EisensteinInt::new(0, 0));
    }

    #[test]
    fn test_eisenstein_snap_simple() {
        // (1.2, 0.7): in Cartesian coordinates, the nearest lattice point
        // is (a=2, b=1) which maps to complex (1.5, 0.866)
        let snapped = eisenstein_snap((1.2, 0.7));
        assert_eq!(snapped, EisensteinInt::new(2, 1));
    }

    #[test]
    fn test_eisenstein_snap_negative() {
        let snapped = eisenstein_snap((-0.8, -1.3));
        assert_eq!(snapped, EisensteinInt::new(-2, -2));
    }

    #[test]
    fn test_eisenstein_distance_origin() {
        let d = eisenstein_distance((0.0, 0.0));
        assert!(d.abs() < 1e-10);
    }

    #[test]
    fn test_eisenstein_distance_positive() {
        // The covering radius of A₂ is 1/√3 ≈ 0.57735
        // So distance must always be less than that
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
        let xs = &[1.2, 0.0, -0.8];
        let ys = &[0.7, 0.0, 1.3];
        let result = eisenstein_snap_batch(xs, ys);
        assert_eq!(result.len(), 3);
        // First point snaps to (2,1) now
        assert_eq!(result[0], EisensteinInt::new(2, 1));
    }

    #[test]
    fn test_eisenstein_display() {
        assert_eq!(format!("{}", EisensteinInt::new(3, 2)), "3+2ω");
        assert_eq!(format!("{}", EisensteinInt::new(3, -2)), "3-2ω");
        assert_eq!(format!("{}", EisensteinInt::new(0, 1)), "ω");
        assert_eq!(format!("{}", EisensteinInt::new(0, -1)), "-ω");
        assert_eq!(format!("{}", EisensteinInt::new(5, 0)), "5");
    }

    #[test]
    fn test_eisenstein_add() {
        let a = EisensteinInt::new(3, 2);
        let b = EisensteinInt::new(1, 4);
        let sum = a + b;
        assert_eq!(sum, EisensteinInt::new(4, 6));
    }

    #[test]
    fn test_eisenstein_sub() {
        let a = EisensteinInt::new(3, 2);
        let b = EisensteinInt::new(1, 4);
        let diff = a - b;
        assert_eq!(diff, EisensteinInt::new(2, -2));
    }

    #[test]
    fn test_eisenstein_mul() {
        let a = EisensteinInt::new(3, 2);
        let b = EisensteinInt::new(1, 4);
        // (3+2ω)(1+4ω) = 3 + 12ω + 2ω + 8ω²
        // = 3 + 14ω + 8(-1-ω) = 3 + 14ω - 8 - 8ω = -5 + 6ω
        let product = a * b;
        assert_eq!(product, EisensteinInt::new(-5, 6));
    }

    #[test]
    fn test_eisenstein_norm_multiplicative() {
        let a = EisensteinInt::new(3, 2);
        let b = EisensteinInt::new(1, 4);
        assert_eq!((a * b).norm(), a.norm() * b.norm());
    }

    #[test]
    fn test_eisenstein_units() {
        // The six units of ℤ[ω]: ±1, ±ω, ±(1+ω)
        // In (a,b) representation:
        let units = vec![
            EisensteinInt::new(1, 0),   // 1
            EisensteinInt::new(-1, 0),  // -1
            EisensteinInt::new(0, 1),   // ω
            EisensteinInt::new(0, -1),  // -ω
            EisensteinInt::new(1, 1),   // 1+ω = -ω²
            EisensteinInt::new(-1, -1), // -1-ω = ω²
        ];
        for u in &units {
            assert!(u.is_unit(), "expected {:?} to be a unit (norm={})", u, u.norm());
            assert_eq!(u.norm(), 1);
        }
    }
}
