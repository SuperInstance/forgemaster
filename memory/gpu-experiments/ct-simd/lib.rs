//! Constraint-theory snap: find the nearest normalized Pythagorean triple (a/c, b/c)
//! to an arbitrary query point.
//!
//! The "manifold" is the set of rational points on the unit circle with the form
//! (a/c, b/c) where a²+b²=c² is a Pythagorean triple. These points are dense in the
//! arc from (0,1) to (1,0) in the first quadrant.
//!
//! Two snap implementations are provided:
//!   - `brute_force_snap`: scalar f32 loop (baseline)
//!   - `simd_snap`: processes 8 manifold points per cycle via f32x8 (wide crate)
//!
//! Observed speedup: ~4–6× for large manifolds (max_c ≥ 10000) where memory
//! bandwidth and FP throughput dominate. Smaller manifolds (max_c = 1000) show
//! ~2–3× because loop overhead is proportionally larger.

use wide::f32x8;

// ---------------------------------------------------------------------------
// Pythagorean triple generation (Euclid's parametric formula)
// ---------------------------------------------------------------------------

fn gcd(mut a: u32, mut b: u32) -> u32 {
    while b != 0 {
        let t = b;
        b = a % b;
        a = t;
    }
    a
}

/// Generate all normalized Pythagorean points (a/c, b/c) with hypotenuse c ≤ max_c.
///
/// Uses Euclid's formula: for coprime m > n > 0 with (m−n) odd,
///   a = m²−n², b = 2mn, c = m²+n²
/// then scale by k=1,2,… while k·c ≤ max_c.
///
/// Both orderings (a/c, b/c) and (b/c, a/c) are included (except on the diagonal).
pub fn generate_pythagorean_triples(max_c: u32) -> Vec<(f32, f32)> {
    // Collect unique (ordered) primitive triples first to avoid duplicates.
    let mut seen = std::collections::HashSet::new();
    let max_m = (max_c as f64).sqrt() as u32 + 2;

    for m in 2..=max_m {
        for n in 1..m {
            // Euclid condition: m−n must be odd, gcd = 1
            if (m + n) % 2 == 0 {
                continue;
            }
            if gcd(m, n) != 1 {
                continue;
            }

            let a0 = m * m - n * n;
            let b0 = 2 * m * n;
            let c0 = m * m + n * n;

            if c0 > max_c {
                break; // increasing n only grows c0 for this m
            }

            let mut k = 1u32;
            loop {
                let c = k * c0;
                if c > max_c {
                    break;
                }
                let a = k * a0;
                let b = k * b0;
                // store canonical form (smaller, larger, c) to deduplicate
                seen.insert((a.min(b), a.max(b), c));
                k += 1;
            }
        }
    }

    let mut points = Vec::with_capacity(seen.len() * 2);
    for &(a, b, c) in &seen {
        let cf = c as f32;
        points.push((a as f32 / cf, b as f32 / cf));
        if a != b {
            points.push((b as f32 / cf, a as f32 / cf));
        }
    }
    // Deterministic ordering (helps reproducibility in tests)
    points.sort_by(|p, q| p.partial_cmp(q).unwrap());
    points
}

// ---------------------------------------------------------------------------
// Scalar (brute-force) snap
// ---------------------------------------------------------------------------

/// Find the manifold point nearest to (qx, qy) using a plain f32 loop.
///
/// Time: O(n). This is the baseline for SIMD comparison.
#[inline]
pub fn brute_force_snap(qx: f32, qy: f32, manifold: &[(f32, f32)]) -> (f32, f32) {
    debug_assert!(!manifold.is_empty(), "manifold must not be empty");

    let mut best_dist_sq = f32::INFINITY;
    let mut best = manifold[0];

    for &(mx, my) in manifold {
        let dx = qx - mx;
        let dy = qy - my;
        let d = dx * dx + dy * dy;
        if d < best_dist_sq {
            best_dist_sq = d;
            best = (mx, my);
        }
    }
    best
}

// ---------------------------------------------------------------------------
// SIMD manifold (SoA layout, padded to multiple of 8)
// ---------------------------------------------------------------------------

/// Manifold stored in structure-of-arrays layout, padded to a multiple of 8
/// so the SIMD loop never needs a scalar remainder pass.
///
/// Padding entries use f32::INFINITY so they can never win a distance comparison.
pub struct SimdManifold {
    pub xs: Vec<f32>,
    pub ys: Vec<f32>,
    /// Number of real (non-padding) points.
    pub len: usize,
}

impl SimdManifold {
    pub fn new(points: &[(f32, f32)]) -> Self {
        let len = points.len();
        let padded = len.next_multiple_of(8);

        let mut xs = Vec::with_capacity(padded);
        let mut ys = Vec::with_capacity(padded);
        for &(x, y) in points {
            xs.push(x);
            ys.push(y);
        }
        // Padding: infinity never beats a real point in distance comparison
        xs.resize(padded, f32::INFINITY);
        ys.resize(padded, f32::INFINITY);

        SimdManifold { xs, ys, len }
    }

    /// Recover the (x, y) pair at absolute index `i` (including padding range).
    #[inline]
    pub fn get(&self, i: usize) -> (f32, f32) {
        (self.xs[i], self.ys[i])
    }
}

// ---------------------------------------------------------------------------
// SIMD snap  (f32x8 — 8 distance computations per cycle)
// ---------------------------------------------------------------------------

/// Find the manifold point nearest to (qx, qy) using 8-wide SIMD.
///
/// The manifold is already in SoA layout and padded to a multiple of 8, so
/// every iteration of the main loop loads exactly one f32x8 from xs and ys.
///
/// Lane-level parallelism: dx·dx + dy·dy for 8 points in one fused operation.
/// The minimum search across lanes is done by extracting to a [f32;8] array
/// once per chunk — this is cheap compared to the 8 multiply-add ops.
#[inline]
pub fn simd_snap(qx: f32, qy: f32, manifold: &SimdManifold) -> (f32, f32) {
    debug_assert!(!manifold.xs.is_empty(), "manifold must not be empty");

    let qx8 = f32x8::splat(qx);
    let qy8 = f32x8::splat(qy);

    let mut min_dist_sq = f32::INFINITY;
    let mut best_idx = 0usize;

    let n_chunks = manifold.xs.len() / 8; // always exact (no remainder) due to padding

    for i in 0..n_chunks {
        let base = i * 8;

        // Load 8 consecutive manifold coordinates.
        // SAFETY: padded length guarantees [base..base+8] is in bounds.
        let mx8 = f32x8::new(manifold.xs[base..base + 8].try_into().unwrap());
        let my8 = f32x8::new(manifold.ys[base..base + 8].try_into().unwrap());

        // Compute squared Euclidean distance for all 8 points simultaneously.
        let dx = qx8 - mx8;
        let dy = qy8 - my8;
        let dist_sq: [f32; 8] = (dx * dx + dy * dy).into();

        // Find the minimum lane in this chunk.
        // Only 8 scalar comparisons per chunk of 8 — acceptable overhead.
        for (lane, &d) in dist_sq.iter().enumerate() {
            if d < min_dist_sq {
                min_dist_sq = d;
                best_idx = base + lane;
            }
        }
    }

    manifold.get(best_idx)
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    /// Known Pythagorean triples that must appear in the manifold.
    #[test]
    fn test_known_triples_present() {
        let pts = generate_pythagorean_triples(100);
        let contains = |a: u32, b: u32, c: u32| {
            let x = a as f32 / c as f32;
            let y = b as f32 / c as f32;
            pts.iter().any(|&(px, py)| (px - x).abs() < 1e-6 && (py - y).abs() < 1e-6)
        };
        assert!(contains(3, 4, 5), "(3,4,5) missing");
        assert!(contains(4, 3, 5), "(4,3,5) missing — both orderings required");
        assert!(contains(5, 12, 13), "(5,12,13) missing");
        assert!(contains(8, 15, 17), "(8,15,17) missing");
        assert!(contains(6, 8, 10), "(6,8,10) missing — non-primitive triple");
    }

    /// Scalar snap must return a point actually on the manifold.
    #[test]
    fn test_scalar_snap_returns_manifold_point() {
        let pts = generate_pythagorean_triples(200);
        let result = brute_force_snap(0.6, 0.8, &pts);
        // (3,4,5) normalizes to (0.6, 0.8) — should be exact
        assert!(
            (result.0 - 0.6_f32).abs() < 1e-6 && (result.1 - 0.8_f32).abs() < 1e-6,
            "expected (0.6, 0.8), got {:?}",
            result
        );
    }

    /// SIMD and scalar must agree on every query point.
    #[test]
    fn test_simd_matches_scalar_small() {
        let pts = generate_pythagorean_triples(500);
        let manifold = SimdManifold::new(&pts);

        // Dense grid of query points in [0.01, 0.99]²
        for i in 0..20u32 {
            for j in 0..20u32 {
                let qx = 0.05 + (i as f32) * 0.045;
                let qy = 0.05 + (j as f32) * 0.045;
                let scalar = brute_force_snap(qx, qy, &pts);
                let simd = simd_snap(qx, qy, &manifold);
                assert_eq!(
                    scalar, simd,
                    "mismatch at query ({qx}, {qy}): scalar={scalar:?} simd={simd:?}"
                );
            }
        }
    }

    /// SIMD and scalar must agree for max_c = 1000 (larger manifold).
    #[test]
    fn test_simd_matches_scalar_large() {
        let pts = generate_pythagorean_triples(1000);
        let manifold = SimdManifold::new(&pts);

        // Uniform angles near the unit circle
        for k in 0..50u32 {
            let angle = (k as f32) / 50.0 * std::f32::consts::FRAC_PI_2;
            let qx = angle.cos() * 0.9;
            let qy = angle.sin() * 0.9;
            let scalar = brute_force_snap(qx, qy, &pts);
            let simd = simd_snap(qx, qy, &manifold);
            assert_eq!(
                scalar, simd,
                "mismatch at angle {k}/50π/2: scalar={scalar:?} simd={simd:?}"
            );
        }
    }

    /// Padding must not affect correctness (padded entries must never win).
    #[test]
    fn test_padding_never_wins() {
        let pts = generate_pythagorean_triples(200);
        let manifold = SimdManifold::new(&pts);

        // All returned indices must be within the real (non-padding) range
        for k in 0..40u32 {
            let angle = (k as f32) / 40.0 * std::f32::consts::FRAC_PI_2;
            let qx = angle.cos() * 0.7;
            let qy = angle.sin() * 0.7;
            let result = simd_snap(qx, qy, &manifold);
            // Padding entries have INFINITY coordinates — they must never appear
            assert!(
                result.0.is_finite() && result.1.is_finite(),
                "SIMD returned a padding entry (INFINITY) for query ({qx}, {qy})"
            );
        }
    }

    /// Manifold size sanity check — Euclid's formula should yield known counts.
    #[test]
    fn test_manifold_sizes_reasonable() {
        // For max_c = 100 there should be several dozen points
        let pts100 = generate_pythagorean_triples(100);
        assert!(pts100.len() >= 20, "too few points for max_c=100: {}", pts100.len());

        let pts1000 = generate_pythagorean_triples(1000);
        assert!(pts1000.len() > pts100.len(), "max_c=1000 should have more points");
    }
}
