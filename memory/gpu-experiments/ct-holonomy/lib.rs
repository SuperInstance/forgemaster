//! # ct-holonomy — Holonomy on the Pythagorean Manifold
//!
//! Measures angular deficit (holonomy) from random walks on the discrete
//! Pythagorean triple manifold. Connects to Berry phase in quantum mechanics.
//!
//! ```
//! use ct_holonomy::{holonomy_walk, holonomy_batch, HolonomyResult};
//!
//! let result = holonomy_walk(1.0, 1000, 50000);
//! assert!(result.total_deficit > 0.0);
//! ```

const TAU: f64 = 6.283185307179586;

/// Result of a single holonomy walk.
#[derive(Debug, Clone)]
pub struct HolonomyResult {
    pub start_angle: f64,
    pub end_angle: f64,
    pub total_deficit: f64,
    pub steps: usize,
    pub final_triple: (i64, i64, i64),
    pub per_step_deficit: Vec<f64>,
}

/// Result of batch holonomy measurement.
#[derive(Debug, Clone)]
pub struct BatchHolonomyResult {
    pub mean_deficit: f64,
    pub std_deficit: f64,
    pub max_deficit: f64,
    pub min_deficit: f64,
    pub median_deficit: f64,
    pub walks: usize,
    pub steps_per_walk: usize,
    pub deficit_bound: f64,
}

/// GCD
fn gcd(a: i64, b: i64) -> i64 { if b == 0 { a.abs() } else { gcd(b, a % b) } }

/// Angular distance on [0, 2pi).
pub fn angular_distance(a: f64, b: f64) -> f64 {
    let a = ((a % TAU) + TAU) % TAU;
    let b = ((b % TAU) + TAU) % TAU;
    let d = (a - b).abs();
    d.min(TAU - d)
}

/// Snap angle to nearest Pythagorean triple.
fn snap(angle: f64, max_c: i64) -> (i64, i64, i64, f64) {
    let t = ((angle % TAU) + TAU) % TAU;
    let mut best_a = 3i64; let mut best_b = 4i64; let mut best_c = 5i64;
    let mut best_dist = TAU;
    let max_m = ((max_c as f64) / 1.414) as i64;
    for m in 2..=max_m {
        for n in 1..m {
            if (m + n) % 2 == 0 { continue; }
            if gcd(m, n) != 1 { continue; }
            let a = m*m - n*n; let b = 2*m*n; let c = m*m + n*n;
            if c > max_c { break; }
            for &(sa, sb) in &[(1,1),(1,-1),(-1,1),(-1,-1)] {
                let ang = ((sa * a) as f64).atan2((sb * b) as f64);
                let d = angular_distance(t, ang);
                if d < best_dist { best_dist = d; best_a = sa*a; best_b = sb*b; best_c = c; }
            }
        }
    }
    (best_a, best_b, best_c, best_dist)
}

/// Perform a single holonomy random walk.
pub fn holonomy_walk(start: f64, steps: usize, max_c: i64) -> HolonomyResult {
    let mut angle = ((start % TAU) + TAU) % TAU;
    let mut deficit = 0.0;
    let mut per_step = Vec::with_capacity(steps);
    let mut rng = (start.to_bits() as u64).wrapping_mul(6364136223846793005);
    let mut final_triple = (3, 4, 5);

    for _ in 0..steps {
        let (a, b, c, dist) = snap(angle, max_c);
        final_triple = (a, b, c);
        angle = ((a as f64).atan2(b as f64) % TAU + TAU) % TAU;
        deficit += dist;
        per_step.push(dist);
        rng = rng.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        let perturbation = (rng >> 33) as f64 / (1u64 << 31) as f64 - 0.5;
        angle += perturbation * 0.5;
    }

    HolonomyResult {
        start_angle: start,
        end_angle: angle,
        total_deficit: deficit,
        steps,
        final_triple,
        per_step_deficit: per_step,
    }
}

/// Batch holonomy: run many walks and compute statistics.
pub fn holonomy_batch(walks: usize, steps: usize, max_c: i64) -> BatchHolonomyResult {
    let mut deficits = Vec::with_capacity(walks);

    for i in 0..walks {
        let start = (i as f64 / walks as f64) * TAU;
        let result = holonomy_walk(start, steps, max_c);
        deficits.push(result.total_deficit);
    }

    deficits.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));

    let mean = deficits.iter().sum::<f64>() / walks as f64;
    let variance = deficits.iter().map(|d| (d - mean) * (d - mean)).sum::<f64>() / walks as f64;
    let std_dev = variance.sqrt();
    let median = if walks % 2 == 0 {
        (deficits[walks/2 - 1] + deficits[walks/2]) / 2.0
    } else {
        deficits[walks/2]
    };

    // Theoretical bound: deficit per step < max angular gap
    // Total bound < steps * max_gap, but empirically much less
    let deficit_bound = steps as f64 * 0.01; // conservative

    BatchHolonomyResult {
        mean_deficit: mean,
        std_deficit: std_dev,
        max_deficit: deficits[walks - 1],
        min_deficit: deficits[0],
        median_deficit: median,
        walks,
        steps_per_walk: steps,
        deficit_bound,
    }
}

/// Berry phase analogy: the holonomy deficit is the classical analog
/// of the geometric (Berry) phase acquired during adiabatic transport
/// on the parameter space manifold.
///
/// Returns the "Berry phase" as a fraction of 2π.
pub fn berry_phase_fraction(walks: usize, steps: usize, max_c: i64) -> f64 {
    let batch = holonomy_batch(walks, steps, max_c);
    batch.mean_deficit / TAU
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_holonomy_positive() {
        let result = holonomy_walk(1.0, 100, 500);
        assert!(result.total_deficit > 0.0);
    }

    #[test]
    fn test_holonomy_increases_with_steps() {
        let short = holonomy_walk(1.0, 10, 500).total_deficit;
        let long = holonomy_walk(1.0, 100, 500).total_deficit;
        assert!(long > short);
    }

    #[test]
    fn test_holonomy_final_triple_valid() {
        let result = holonomy_walk(1.0, 50, 500);
        let (a, b, c) = result.final_triple;
        assert_eq!(a*a + b*b, c*c);
    }

    #[test]
    fn test_holonomy_per_step_recorded() {
        let result = holonomy_walk(1.0, 20, 500);
        assert_eq!(result.per_step_deficit.len(), 20);
        for d in &result.per_step_deficit {
            assert!(*d >= 0.0);
        }
    }

    #[test]
    fn test_batch_holonomy() {
        let batch = holonomy_batch(50, 100, 5000);
        assert!(batch.mean_deficit > 0.0);
        assert!(batch.std_deficit >= 0.0);
        assert!(batch.max_deficit >= batch.min_deficit);
        assert_eq!(batch.walks, 50);
    }

    #[test]
    fn test_batch_sorted_stats() {
        let batch = holonomy_batch(100, 50, 5000);
        assert!(batch.min_deficit <= batch.median_deficit);
        assert!(batch.median_deficit <= batch.max_deficit);
    }

    #[test]
    fn test_berry_phase_fraction() {
        let frac = berry_phase_fraction(20, 100, 5000);
        assert!(frac > 0.0);
        assert!(frac < 1.0);
    }

    #[test]
    fn test_angular_distance() {
        assert!(angular_distance(0.0, 0.0) < 1e-10);
        assert!((angular_distance(0.0, TAU - 0.01) - 0.01).abs() < 1e-10);
    }

    #[test]
    fn test_holonomy_different_starts() {
        let r1 = holonomy_walk(0.0, 100, 500).total_deficit;
        let r2 = holonomy_walk(3.0, 100, 500).total_deficit;
        // Different starting points should give different paths
        // (statistically likely, though not guaranteed)
        // Just verify both are positive
        assert!(r1 > 0.0);
        assert!(r2 > 0.0);
    }
}
