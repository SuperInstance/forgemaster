//! # ct — Constraint Theory Umbrella
//!
//! Unified API for the constraint theory ecosystem: snap, holonomy,
//! nearest-neighbor search, and manifold operations.
//!
//! ```
//! use ct::{snap, Triple, DEFAULT_MAX_C};
//!
//! let result = snap(std::f64::consts::FRAC_PI_4, DEFAULT_MAX_C);
//! assert!(result.triple.is_pythagorean());
//! ```

use std::cmp::Ordering;

/// 2π — full circle in radians.
pub const TAU: f64 = 6.283185307179586;
/// Default max hypotenuse for triple generation.
pub const DEFAULT_MAX_C: i64 = 50000;

/// A Pythagorean triple (a, b, c) where a² + b² = c².
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Triple {
    pub a: i64,
    pub b: i64,
    pub c: i64,
}

impl Triple {
    pub fn new(a: i64, b: i64, c: i64) -> Self { Triple { a, b, c } }

    /// Verify a² + b² = c².
    pub fn is_pythagorean(&self) -> bool {
        self.a * self.a + self.b * self.b == self.c * self.c
    }

    /// Angle of this triple: atan2(a, b).
    pub fn angle(&self) -> f64 {
        (self.a as f64).atan2(self.b as f64)
    }

    /// Hypotenuse magnitude.
    pub fn hypotenuse(&self) -> f64 {
        (self.c as f64)
    }

    /// Squared norm.
    pub fn norm_sq(&self) -> i64 {
        self.a * self.a + self.b * self.b
    }
}

impl std::fmt::Display for Triple {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        write!(f, "({}, {}, {})", self.a, self.b, self.c)
    }
}

/// Result of a snap operation.
#[derive(Debug, Clone)]
pub struct SnapResult {
    pub triple: Triple,
    pub distance: f64,
    pub index: usize,
}

/// A point on the Pythagorean manifold.
#[derive(Debug, Clone)]
pub struct ManifoldPoint {
    pub angle: f64,
    pub triple: Triple,
}

impl ManifoldPoint {
    pub fn new(angle: f64, triple: Triple) -> Self { ManifoldPoint { angle, triple } }
}

// === Core Functions ===

/// Angular distance on [0, 2π).
pub fn angular_distance(a: f64, b: f64) -> f64 {
    let d = (a - b).abs();
    d.min(TAU - d)
}

/// Snap an angle to the nearest Pythagorean triple.
/// Uses Euclid's formula + binary search on all 8 octants.
pub fn snap(theta: f64, max_c: i64) -> SnapResult {
    let t = ((theta % TAU) + TAU) % TAU;
    let triples = generate_triples(max_c);
    let n = triples.len();
    if n == 0 {
        return SnapResult { triple: Triple::new(0, 1, 1), distance: angular_distance(t, 0.0), index: 0 };
    }

    // Build sorted angle array
    let mut indexed: Vec<(f64, usize)> = triples.iter().enumerate()
        .map(|(i, tr)| (tr.angle(), i))
        .collect();
    indexed.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(Ordering::Equal));
    let angles: Vec<f64> = indexed.iter().map(|x| x.0).collect();
    let indices: Vec<usize> = indexed.iter().map(|x| x.1).collect();

    // Binary search
    let (mut lo, mut hi) = (0usize, n - 1);
    while lo < hi {
        let mid = (lo + hi) / 2;
        if angles[mid] < t { lo = mid + 1; } else { hi = mid; }
    }

    let (idx, dist) = if lo == 0 {
        let dl = angular_distance(t, angles[n - 1]);
        let dh = angular_distance(t, angles[0]);
        if dl <= dh { (indices[n - 1], dl) } else { (indices[0], dh) }
    } else {
        let dl = angular_distance(t, angles[lo - 1]);
        let dh = angular_distance(t, angles[lo]);
        if dl <= dh { (indices[lo - 1], dl) } else { (indices[lo], dh) }
    };

    SnapResult { triple: triples[idx], distance: dist, index: idx }
}

/// Generate all Pythagorean triples with c ≤ max_c, all 8 octants.
pub fn generate_triples(max_c: i64) -> Vec<Triple> {
    let mut triples = Vec::new();
    let max_m = ((max_c as f64) / 1.41421356) as i64 + 1;

    for m in 2..=max_m {
        for n in 1..m {
            if (m + n) % 2 == 0 { continue; }
            if gcd(m, n) != 1 { continue; }
            let a = m * m - n * n;
            let b = 2 * m * n;
            let c = m * m + n * n;
            if c > max_c { break; }
            // All 8 sign/reflection octants × 2 swaps
            for &sa in &[1i64, -1] {
                for &sb in &[1i64, -1] {
                    triples.push(Triple::new(sa * a, sb * b, c));
                    triples.push(Triple::new(sa * b, sb * a, c));
                }
            }
        }
    }
    triples
}

/// Measure holonomy: angular deficit after a random walk on the manifold.
pub fn holonomy(start: f64, steps: usize) -> f64 {
    let mut angle = ((start % TAU) + TAU) % TAU;
    let mut deficit = 0.0;
    let mut rng = (start.to_bits() as u64).wrapping_mul(6364136223846793005);

    for _ in 0..steps {
        let result = snap(angle, DEFAULT_MAX_C);
        let snapped = result.triple.angle();
        deficit += result.distance;
        angle = snapped;
        // LCG perturbation
        rng = rng.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        let perturbation = (rng >> 33) as f64 / (1u64 << 31) as f64 - 0.5;
        angle += perturbation * 0.1;
    }
    deficit
}

/// GCD via Euclidean algorithm.
fn gcd(a: i64, b: i64) -> i64 {
    if b == 0 { a.abs() } else { gcd(b, a % b) }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_triple_is_pythagorean_345() {
        let t = Triple::new(3, 4, 5);
        assert!(t.is_pythagorean());
    }

    #[test]
    fn test_triple_is_pythagorean_5_12_13() {
        let t = Triple::new(5, 12, 13);
        assert!(t.is_pythagorean());
    }

    #[test]
    fn test_triple_not_pythagorean() {
        let t = Triple::new(1, 2, 3);
        assert!(!t.is_pythagorean());
    }

    #[test]
    fn test_triple_angle() {
        let t = Triple::new(3, 4, 5);
        let ang = t.angle();
        // atan2(3, 4) ≈ 0.6435 rad
        assert!((ang - 0.6435).abs() < 0.01);
    }

    #[test]
    fn test_snap_45_degrees() {
        let result = snap(std::f64::consts::FRAC_PI_4, 1000);
        assert!(result.triple.is_pythagorean());
        assert!(result.triple.c <= 1000);
        // 45° = arctan(1) — should snap close to (3,4,5) or similar
        assert!(result.distance < 0.1);
    }

    #[test]
    fn test_snap_16_compass() {
        for i in 0..16 {
            let theta = i as f64 / 16.0 * TAU;
            let result = snap(theta, 1000);
            assert!(result.triple.is_pythagorean(), "Failed at i={}", i);
            assert!(result.triple.c <= 1000);
        }
    }

    #[test]
    fn test_snap_returns_valid_triple() {
        for angle in [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0] {
            let result = snap(angle, 50000);
            assert!(result.triple.is_pythagorean(), "Failed at angle={}", angle);
        }
    }

    #[test]
    fn test_angular_distance_wraparound() {
        let d = angular_distance(0.0, TAU - 0.01);
        assert!((d - 0.01).abs() < 1e-10);
    }

    #[test]
    fn test_angular_distance_zero() {
        assert!(angular_distance(1.0, 1.0) < 1e-10);
    }

    #[test]
    fn test_generate_triples_count() {
        let triples = generate_triples(50000);
        // 16 copies per primitive triple (8 octants × 2 swaps), ~3980 primitives
        assert!(triples.len() > 60000, "Got {}", triples.len());
        assert!(triples.len() < 70000, "Got {}", triples.len());
    }

    #[test]
    fn test_generate_triples_all_valid() {
        let triples = generate_triples(1000);
        for t in &triples {
            assert!(t.is_pythagorean());
            assert!(t.c <= 1000);
        }
    }

    #[test]
    fn test_holonomy_nonzero() {
        let h = holonomy(1.0, 1000);
        assert!(h > 0.0, "Holonomy should be nonzero, got {}", h);
    }

    #[test]
    fn test_holonomy_bounded() {
        let h = holonomy(1.0, 10000);
        assert!(h < TAU * 10.0, "Holonomy should be bounded, got {}", h);
    }

    #[test]
    fn test_snap_edge_angle_zero() {
        let result = snap(0.0, 50000);
        assert!(result.triple.is_pythagorean());
        assert!(result.distance < 0.01);
    }

    #[test]
    fn test_snap_edge_angle_pi() {
        let result = snap(std::f64::consts::PI, 100);
        assert!(result.triple.is_pythagorean());
    }

    #[test]
    fn test_snap_negative_angle() {
        let result = snap(-1.0, 100);
        assert!(result.triple.is_pythagorean());
    }

    #[test]
    fn test_triple_display() {
        let t = Triple::new(3, 4, 5);
        assert_eq!(format!("{}", t), "(3, 4, 5)");
    }
}
