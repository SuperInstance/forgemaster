//! 9-candidate Voronoï snap with covering radius guarantee.
//!
//! The A₂ lattice Voronoï cell contains at most 9 Eisenstein integers.
//! By testing all 9 candidates we guarantee the nearest neighbor is found,
//! and the maximum snap distance (covering radius) is ≤ 1/√3.

use crate::eisenstein::{fabs, hypot, round, EisensteinInt, HALF_SQRT3, INV_SQRT3};

/// Snap (x, y) to the true nearest Eisenstein integer using 9-candidate Voronoï search.
///
/// Guarantees covering radius ≤ 1/√3. Uses squared-distance comparison
/// (no sqrt in the inner loop) for performance.
pub fn eisenstein_round_voronoi(x: f64, y: f64) -> EisensteinInt {
    let b0 = round(y * 2.0 * INV_SQRT3) as i64;
    let a0 = round(x + b0 as f64 * 0.5) as i64;

    let mut best_dist_sq = f64::MAX;
    let mut best_a = a0;
    let mut best_b = b0;

    for da in -1..=1i64 {
        for db in -1..=1i64 {
            let a = a0 + da;
            let b = b0 + db;
            let dx = x - (a as f64 - b as f64 * 0.5);
            let dy = y - (b as f64 * HALF_SQRT3);
            let d_sq = dx * dx + dy * dy;
            if d_sq < best_dist_sq - 1e-24 {
                best_dist_sq = d_sq;
                best_a = a;
                best_b = b;
            } else if fabs(d_sq - best_dist_sq) < 1e-24 {
                // Tie-break: prefer smaller (|a|, |b|)
                if (a.abs(), b.abs()) < (best_a.abs(), best_b.abs()) {
                    best_a = a;
                    best_b = b;
                }
            }
        }
    }

    EisensteinInt::new(best_a, best_b)
}

/// Snap with distance and tolerance check using Voronoï method.
///
/// Returns `(nearest, distance, is_snap)`.
pub fn eisenstein_snap_voronoi(x: f64, y: f64, tolerance: f64) -> (EisensteinInt, f64, bool) {
    let nearest = eisenstein_round_voronoi(x, y);
    let (cx, cy) = nearest.to_cartesian();
    let dist = hypot(x - cx, y - cy);
    let is_snap = dist <= tolerance;
    (nearest, dist, is_snap)
}

/// Batch Voronoï snap for multiple points.
pub fn eisenstein_snap_voronoi_batch(points: &[(f64, f64)]) -> alloc::vec::Vec<EisensteinInt> {
    points
        .iter()
        .map(|&(x, y)| eisenstein_round_voronoi(x, y))
        .collect()
}

/// Batch Voronoï snap with distance and tolerance check.
pub fn eisenstein_snap_voronoi_batch_with_tolerance(
    points: &[(f64, f64)],
    tolerance: f64,
) -> alloc::vec::Vec<(EisensteinInt, f64, bool)> {
    points
        .iter()
        .map(|&(x, y)| eisenstein_snap_voronoi(x, y, tolerance))
        .collect()
}

/// Verify the covering radius guarantee: maximum snap distance ≤ 1/√3.
///
/// Tests a dense grid of points and returns the maximum observed snap distance.
pub fn verify_covering_radius(grid_resolution: usize) -> f64 {
    let mut max_dist = 0.0_f64;
    let step = 1.0 / grid_resolution as f64;
    // Test points in [0, 1]² — one Voronoï cell
    let n = grid_resolution;
    for i in 0..=n {
        for j in 0..=n {
            let x = i as f64 * step;
            let y = j as f64 * step;
            let nearest = eisenstein_round_voronoi(x, y);
            let (cx, cy) = nearest.to_cartesian();
            let dist = hypot(x - cx, y - cy);
            if dist > max_dist {
                max_dist = dist;
            }
        }
    }
    max_dist
}

extern crate alloc;
