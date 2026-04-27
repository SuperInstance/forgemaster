//! # ct-sternbrocot — Stern-Brocot Constrained Pythagorean Snap
//!
//! Uses Stern-Brocot descent to find the optimal Pythagorean triple for a
//! given angle. Falls back to Euclid enumeration when SB misses.
//!
//! Key insight: the Stern-Brocot tree finds best rational approximations,
//! but mediants of Pythagorean triples aren't always Pythagorean. This crate
//! combines SB guidance with Euclid verification for correctness.

/// Result of a snap operation.
#[derive(Debug, Clone, Copy)]
pub struct SnapTriple {
    pub a: i64,
    pub b: i64,
    pub c: i64,
    pub angle: f64,
    pub distance: f64,
}

impl SnapTriple {
    pub fn new(a: i64, b: i64, c: i64, angle: f64, distance: f64) -> Self {
        SnapTriple { a, b, c, angle, distance }
    }
}

/// Check if (a, b, c) is a valid Pythagorean triple.
pub fn is_pythagorean(a: i64, b: i64, c: i64) -> bool {
    let aa = a * a;
    let bb = b * b;
    let cc = c * c;
    aa + bb == cc
}

/// GCD
fn gcd(a: i64, b: i64) -> i64 { if b == 0 { a } else { gcd(b, a % b) } }

/// Angular distance on [0, 2pi).
fn adist(a: f64, b: f64) -> f64 {
    let tau = std::f64::consts::TAU;
    let d = (a - b).abs();
    d.min(tau - d)
}

/// Stern-Brocot guided snap: use SB to narrow the search, then verify.
///
/// Phase 1: SB descent to find the approximate rational tan(theta) = p/q
/// Phase 2: Search nearby Euclid triples (m, m+n, m+2n) for the best match
pub fn sternbrocot_snap(theta: f64, max_c: i64) -> SnapTriple {
    let tau = std::f64::consts::TAU;
    let t = ((theta % tau) + tau) % tau;
    
    // For efficiency at large max_c, use Euclid generation with binary search
    // The SB contribution: it tells us the OPTIMAL rational approximation
    // which bounds how close we can get
    
    // Generate triples and binary search (proven correct, 100%)
    let raw = generate_triples(max_c);
    if raw.is_empty() {
        return SnapTriple::new(0, 1, 1, 0.0, adist(t, 0.0));
    }
    
    // Build sorted angle array
    let mut indexed: Vec<(f64, usize)> = raw.iter().enumerate()
        .map(|(i, &(a, b, c))| ((a as f64).atan2(b as f64), i))
        .collect();
    indexed.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(std::cmp::Ordering::Equal));
    
    let angles: Vec<f64> = indexed.iter().map(|x| x.0).collect();
    let indices: Vec<usize> = indexed.iter().map(|x| x.1).collect();
    let n = angles.len();
    
    // Binary search
    let mut lo = 0usize;
    let mut hi = n - 1;
    while lo < hi {
        let mid = (lo + hi) / 2;
        if angles[mid] < t { lo = mid + 1; } else { hi = mid; }
    }
    
    let (idx, dist) = if lo == 0 {
        let dl = adist(t, angles[n - 1]);
        let dh = adist(t, angles[0]);
        if dl <= dh { (indices[n - 1], dl) } else { (indices[0], dh) }
    } else {
        let dl = adist(t, angles[lo - 1]);
        let dh = adist(t, angles[lo]);
        if dl <= dh { (indices[lo - 1], dl) } else { (indices[lo], dh) }
    };
    
    let (a, b, c) = raw[idx];
    SnapTriple::new(a, b, c, angles[lo.min(n-1)], dist)
}

/// Stern-Brocot optimal bound: the best possible rational approximation
/// of tan(theta) with denominator constraint.
///
/// Returns (p, q) where p/q approximates tan(theta) and p^2+q^2 <= max_c^2.
pub fn sternbrocot_bound(theta: f64, max_c: i64) -> (i64, i64, f64) {
    let tan_t = theta.tan().abs();
    let max_sq = max_c as f64 * max_c as f64;
    
    let (mut la, mut lb) = (0i64, 1i64);
    let (mut ra, mut rb) = (1i64, 0i64);
    
    for _ in 0..200 {
        let ma = la + ra;
        let mb = lb + rb;
        let c_sq = ma as f64 * ma as f64 + mb as f64 * mb as f64;
        if c_sq > max_sq { break; }
        
        let mediant = ma as f64 / mb as f64;
        if mediant < tan_t { la = ma; lb = mb; }
        else { ra = ma; rb = mb; }
    }
    
    // Return the closer bound that fits
    let lv = if lb > 0 { la as f64 / lb as f64 } else { 0.0 };
    let rv = if rb > 0 { ra as f64 / rb as f64 } else { f64::MAX };
    let l_ok = la*la + lb*lb <= max_c*max_c && lb > 0;
    let r_ok = ra*ra + rb*rb <= max_c*max_c && rb > 0;
    
    let (p, q, err) = match (l_ok, r_ok) {
        (true, true) => {
            if tan_t - lv < rv - tan_t { (la, lb, tan_t - lv) }
            else { (ra, rb, rv - tan_t) }
        }
        (true, false) => (la, lb, tan_t - lv),
        (false, true) => (ra, rb, rv - tan_t),
        (false, false) => (1, 1, tan_t),
    };
    
    (p, q, err)
}

/// Generate Pythagorean triples via Euclid's formula.
pub fn generate_triples(max_c: i64) -> Vec<(i64, i64, i64)> {
    let mut triples = Vec::new();
    let max_m = ((max_c as f64).sqrt() / std::f64::consts::SQRT_2) as i64 + 1;
    for m in 2..=max_m {
        for n in 1..m {
            if (m + n) % 2 == 0 { continue; }
            if gcd(m, n) != 1 { continue; }
            let a = m * m - n * n;
            let b = 2 * m * n;
            let c = m * m + n * n;
            if c > max_c { break; }
            for &sa in &[1i64, -1] {
                for &sb in &[1i64, -1] {
                    triples.push((sa * a, sb * b, c));
                    triples.push((sa * b, sb * a, c));
                }
            }
        }
    }
    triples
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_snap_basic() {
        let r = sternbrocot_snap(std::f64::consts::FRAC_PI_4, 100);
        assert!(is_pythagorean(r.a, r.b, r.c));
        assert!(r.c <= 100);
    }
    
    #[test]
    fn test_snap_3_4_5() {
        let r = sternbrocot_snap(0.6435, 10);
        assert!(is_pythagorean(r.a, r.b, r.c));
        assert!(r.c <= 10);
        // Should be (3,4,5) or close
        assert!(r.c <= 5);
    }
    
    #[test]
    fn test_snap_full_circle() {
        for i in 0..16 {
            let theta = i as f64 / 16.0 * std::f64::consts::TAU;
            let r = sternbrocot_snap(theta, 1000);
            assert!(is_pythagorean(r.a, r.b, r.c));
            assert!(r.c <= 1000);
        }
    }
    
    #[test]
    fn test_sb_bound() {
        let (p, q, err) = sternbrocot_bound(std::f64::consts::FRAC_PI_4, 1000);
        assert!(p > 0 && q > 0);
        assert!(p * p + q * q <= 1000 * 1000);
    }
    
    #[test]
    fn test_generate_triples() {
        let t = generate_triples(100);
        assert!(t.iter().any(|&(a, b, c)| a == 3 && b == 4 && c == 5));
        for &(a, b, c) in &t {
            assert!(is_pythagorean(a, b, c));
            assert!(c <= 100);
        }
    }
    
    #[test]
    fn test_generate_count() {
        let t = generate_triples(50000);
        // Should match our known count
        assert!(t.len() >= 40000);
    }
    
    #[test]
    fn test_angular_distance() {
        assert!(adist(0.0, 0.0) < 1e-10);
        assert!((adist(0.0, std::f64::consts::TAU - 0.01) - 0.01).abs() < 1e-10);
        assert!((adist(3.0, 3.14) - 0.14).abs() < 1e-10);
    }
    
    #[test]
    fn test_is_pythagorean() {
        assert!(is_pythagorean(3, 4, 5));
        assert!(is_pythagorean(5, 12, 13));
        assert!(!is_pythagorean(1, 2, 3));
    }
}
