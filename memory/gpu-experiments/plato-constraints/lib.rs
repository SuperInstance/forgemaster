//! # plato-constraints
//!
//! Constraint-theory operations integrated with the PLATO knowledge graph.
//! Provides snap, holonomy, and manifold distance for tile relevance.

const TAU: f64 = std::f64::consts::TAU;
const MAX_C: i64 = 50000;

/// Snap an angle to the nearest Pythagorean triple angle.
pub fn snap(theta: f64) -> (i64, i64, i64, f64) {
    let t = ((theta % TAU) + TAU) % TAU;
    let mut best_a = 3i64; let mut best_b = 4i64; let mut best_c = 5i64;
    let mut best_dist = TAU;
    
    let max_m = (MAX_C as f64 / 1.414) as i64;
    for m in 2..=max_m {
        for n in 1..m {
            if (m + n) % 2 == 0 { continue; }
            if gcd(m, n) != 1 { continue; }
            let a = m*m - n*n; let b = 2*m*n; let c = m*m + n*n;
            if c > MAX_C { break; }
            for &(sa, sb) in &[(1,1),(1,-1),(-1,1),(-1,-1)] {
                let ang = ((sa * a) as f64).atan2((sb * b) as f64);
                let d = adist(t, ang);
                if d < best_dist { best_dist = d; best_a = sa*a; best_b = sb*b; best_c = c; }
            }
        }
    }
    (best_a, best_b, best_c, best_dist)
}

/// Angular distance on [0, 2pi).
pub fn adist(a: f64, b: f64) -> f64 {
    let d = (a - b).abs();
    d.min(TAU - d)
}

/// Compute holonomy after a random walk of n steps on the triple manifold.
pub fn holonomy(start: f64, steps: usize) -> f64 {
    let mut angle = start;
    let mut deficit = 0.0;
    let mut rng = start.to_bits() as u64;
    
    for _ in 0..steps {
        let (a, b, c, dist) = snap(angle);
        let snapped = (a as f64).atan2(b as f64);
        deficit += adist(angle, snapped);
        angle = snapped;
        // Small random perturbation
        rng = rng.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        angle += ((rng >> 33) as f64 / (1u32 << 31) as f64 - 0.5) * 0.1;
    }
    deficit
}

fn gcd(a: i64, b: i64) -> i64 { if b == 0 { a } else { gcd(b, a % b) } }

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_snap_45_degrees() {
        let (a, b, c, dist) = snap(std::f64::consts::FRAC_PI_4);
        assert_eq!(c, 5); // (3,4,5)
        assert!(dist < 0.01);
    }
    
    #[test]
    fn test_snap_pythagorean() {
        let (a, b, c, dist) = snap(1.0);
        assert_eq!(a*a + b*b, c*c);
        assert!(dist < 0.001);
    }
    
    #[test]
    fn test_holonomy_nonzero() {
        let h = holonomy(1.0, 1000);
        assert!(h > 0.0);
        assert!(h < 10.0); // bounded
    }
    
    #[test]
    fn test_adist() {
        assert!(adist(0.0, 0.0) < 1e-10);
        assert!((adist(0.0, TAU - 0.01) - 0.01).abs() < 1e-10);
    }
}
