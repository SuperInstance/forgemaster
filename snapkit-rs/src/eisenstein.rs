//! Eisenstein integer type and naive snap operations.
//!
//! An Eisenstein integer is a + bω where ω = e^{2πi/3} = (-1 + i√3)/2.
//! The six units of Z[ω] are ±1, ±ω, ±ω², all with norm 1.

use core::ops::{Add, Mul, Sub};
use core::fmt;

/// Precomputed √3.
pub const SQRT3: f64 = 1.7320508075688772;
/// Precomputed √3 / 2.
pub const HALF_SQRT3: f64 = 0.8660254037844386;
/// Precomputed 2 / √3.
pub const TWO_OVER_SQRT3: f64 = 1.1547005383792515;
/// Precomputed 1 / √3.
pub const INV_SQRT3: f64 = 0.5773502691896257;
/// Covering radius of the A₂ lattice: 1/√3.
pub const COVERING_RADIUS: f64 = INV_SQRT3;

/// An Eisenstein integer a + bω where a, b ∈ Z.
#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
pub struct EisensteinInt {
    pub a: i64,
    pub b: i64,
}

impl EisensteinInt {
    /// Create a new Eisenstein integer.
    #[inline]
    pub const fn new(a: i64, b: i64) -> Self {
        Self { a, b }
    }

    /// Convert to Cartesian coordinates (x, y).
    /// x = a - b/2, y = b·√3/2
    #[inline]
    pub fn to_cartesian(self) -> (f64, f64) {
        let x = self.a as f64 - 0.5 * self.b as f64;
        let y = self.b as f64 * HALF_SQRT3;
        (x, y)
    }

    /// Eisenstein norm squared: a² - ab + b². Always ≥ 0.
    #[inline]
    pub fn norm_squared(self) -> i64 {
        self.a * self.a - self.a * self.b + self.b * self.b
    }

    /// Euclidean distance from origin.
    #[inline]
    pub fn abs_f64(self) -> f64 {
        sqrt(self.norm_squared() as f64)
    }

    /// Galois conjugate: (a - b) - b·ω.
    #[inline]
    pub const fn conjugate(self) -> Self {
        Self::new(self.a - self.b, -self.b)
    }

    /// Convert Cartesian (x, y) to Eisenstein coordinates (a_float, b_float).
    #[inline]
    pub fn from_cartesian_coords(x: f64, y: f64) -> (f64, f64) {
        let b_float = y * TWO_OVER_SQRT3;
        let a_float = x + b_float * 0.5;
        (a_float, b_float)
    }

    /// The six units of Z[ω]: ±1, ±ω, ±ω².
    /// These all have Eisenstein norm a²-ab+b² = 1.
    pub const UNITS: [EisensteinInt; 6] = [
        EisensteinInt::new(1, 0),    // 1
        EisensteinInt::new(0, 1),    // ω
        EisensteinInt::new(1, 1),    // -ω² = 1+ω
        EisensteinInt::new(-1, 0),   // -1
        EisensteinInt::new(0, -1),   // -ω
        EisensteinInt::new(-1, -1),  // ω² = -1-ω
    ];
}

impl Add for EisensteinInt {
    type Output = Self;
    #[inline]
    fn add(self, rhs: Self) -> Self {
        Self::new(self.a + rhs.a, self.b + rhs.b)
    }
}

impl Sub for EisensteinInt {
    type Output = Self;
    #[inline]
    fn sub(self, rhs: Self) -> Self {
        Self::new(self.a - rhs.a, self.b - rhs.b)
    }
}

impl Mul for EisensteinInt {
    type Output = Self;
    /// (a + bω)(c + dω) = (ac - bd) + (ad + bc - bd)ω
    #[inline]
    fn mul(self, rhs: Self) -> Self {
        let (a, b) = (self.a, self.b);
        let (c, d) = (rhs.a, rhs.b);
        Self::new(a * c - b * d, a * d + b * c - b * d)
    }
}

impl fmt::Display for EisensteinInt {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}+{}ω", self.a, self.b)
    }
}

/// Naive rounding: test 4 candidates (floor, floor+1) × (floor, floor+1).
/// Tie-break by smallest (|a|, |b|).
pub fn eisenstein_round_naive(x: f64, y: f64) -> EisensteinInt {
    let (a_float, b_float) = EisensteinInt::from_cartesian_coords(x, y);
    let a_floor = floor(a_float) as i64;
    let b_floor = floor(b_float) as i64;

    let mut best = EisensteinInt::new(a_floor, b_floor);
    let mut best_dist = f64::MAX;
    let mut best_key = (i64::MAX, i64::MAX);

    for da in 0..=1i64 {
        for db in 0..=1i64 {
            let a = a_floor + da;
            let b = b_floor + db;
            let (cx, cy) = EisensteinInt::new(a, b).to_cartesian();
            let dist = hypot(x - cx, y - cy);
            let key = (a.abs(), b.abs());
            if dist < best_dist - 1e-9 || (fabs(dist - best_dist) < 1e-9 && key < best_key) {
                best_dist = dist;
                best_key = key;
                best = EisensteinInt::new(a, b);
            }
        }
    }
    best
}

/// Snap a Cartesian point to the nearest Eisenstein integer (naive 4-candidate).
///
/// Returns `(nearest, distance, is_snap)` where `is_snap` indicates distance ≤ tolerance.
pub fn eisenstein_snap(x: f64, y: f64, tolerance: f64) -> (EisensteinInt, f64, bool) {
    let nearest = eisenstein_round_naive(x, y);
    let (cx, cy) = nearest.to_cartesian();
    let dist = hypot(x - cx, y - cy);
    let is_snap = dist <= tolerance;
    (nearest, dist, is_snap)
}

/// Batch snap: apply [`eisenstein_snap`] to a slice of `(x, y)` points.
pub fn eisenstein_snap_batch(
    points: &[(f64, f64)],
    tolerance: f64,
) -> alloc::vec::Vec<(EisensteinInt, f64, bool)> {
    points.iter().map(|&(x, y)| eisenstein_snap(x, y, tolerance)).collect()
}

/// Eisenstein lattice distance between two Cartesian points.
pub fn eisenstein_distance(x1: f64, y1: f64, x2: f64, y2: f64) -> f64 {
    let dx = x1 - x2;
    let dy = y1 - y2;
    let nearest = crate::voronoi::eisenstein_round_voronoi(dx, dy);
    let (cx, cy) = nearest.to_cartesian();
    let residual = hypot(dx - cx, dy - cy);
    sqrt(nearest.norm_squared() as f64) + residual
}

// ── libm-free float helpers ──────────────────────────────────────────

/// Floor without libm.
pub(crate) fn floor(x: f64) -> f64 {
    if x >= 0.0 {
        x as u64 as f64
    } else {
        let i = x as i64 as f64;
        if i == x { i } else { i - 1.0 }
    }
}

/// Round to nearest integer (ties away from zero).
pub(crate) fn round(x: f64) -> f64 {
    floor(x + 0.5)
}

/// Absolute value.
#[inline]
pub(crate) fn fabs(x: f64) -> f64 {
    if x < 0.0 { -x } else { x }
}

/// √x via Newton's method (no libm).
pub(crate) fn sqrt(x: f64) -> f64 {
    if x <= 0.0 {
        return 0.0;
    }
    // Initial guess via bit trick (Quake-style inverse sqrt)
    let half = 0.5 * x;
    let mut i = x.to_bits();
    i = 0x5fe6eb50c7b537a9_u64.wrapping_sub(i >> 1);
    let mut z = f64::from_bits(i); // ≈ 1/√x
    z = z * (1.5 - half * z * z);  // 1st Newton refinement
    z = z * (1.5 - half * z * z);  // 2nd
    z = z * (1.5 - half * z * z);  // 3rd
    // z is now ≈ 1/√x with high accuracy; multiply by x to get √x
    // But: x * (1/√x) = √x only if exact. Do a final Newton on √x directly:
    let mut s = x * z;
    for _ in 0..3 {
        s = 0.5 * (s + x / s);
    }
    s
}

/// hypot: √(x² + y²) without libm.
pub(crate) fn hypot(x: f64, y: f64) -> f64 {
    sqrt(x * x + y * y)
}

/// Natural log via Newton's method (for entropy computation).
pub(crate) fn ln(x: f64) -> f64 {
    if x <= 0.0 {
        return f64::NEG_INFINITY;
    }
    if x == 1.0 {
        return 0.0;
    }
    // Use log₂(x) = log₂ frexp approach, then convert
    // Simpler: iterative method
    // ln(x) = 2 * atanh((x-1)/(x+1)) using series
    // For decent range, use: ln(x) = 2 * sum_{k=0}^{N} (1/(2k+1)) * ((x-1)/(x+1))^{2k+1}
    let t = (x - 1.0) / (x + 1.0);
    let mut result = 0.0;
    let mut t_pow = t;
    let mut k = 0;
    while k < 30 {
        result += t_pow / (2.0_f64 * k as f64 + 1.0);
        t_pow *= t * t;
        k += 1;
        if fabs(t_pow) < 1e-16 {
            break;
        }
    }
    2.0 * result
}

/// log base 2.
pub(crate) fn log2(x: f64) -> f64 {
    ln(x) / LN2
}

/// ln(2) precomputed.
pub const LN2: f64 = 0.6931471805599453;

/// π precomputed.
pub const PI: f64 = 3.1415926535897932;

/// Ceiling without libm.
pub(crate) fn ceil(x: f64) -> f64 {
    let f = floor(x);
    if x == f { f } else { f + 1.0 }
}

extern crate alloc;
