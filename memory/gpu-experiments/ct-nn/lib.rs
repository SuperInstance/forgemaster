//! # Constraint Theory Nearest Neighbor
//!
//! Exact 1-nearest-neighbor lookup on the Pythagorean triple manifold.
//! Maps any query angle to the nearest triple using binary search in O(log n).

use std::f64::consts::TAU;

/// A Pythagorean triple (a, b, c) with its associated angle.
#[derive(Debug, Clone, Copy)]
pub struct Triple {
    pub a: i64,
    pub b: i64,
    pub c: u64,
    pub angle: f64,
}

/// Pre-computed index of Pythagorean triples sorted by angle.
pub struct TripleIndex {
    triples: Vec<Triple>,
}

impl TripleIndex {
    /// Build index from raw triples. Computes angles and sorts.
    pub fn new(raw: &[(i64, i64, u64)]) -> Self {
        let mut triples: Vec<Triple> = raw.iter().map(|&(a, b, c)| {
            Triple { a, b, c, angle: (a as f64).atan2(b as f64) }
        }).collect();
        triples.sort_by(|x, y| x.angle.partial_cmp(&y.angle).unwrap_or(std::cmp::Ordering::Equal));
        TripleIndex { triples }
    }

    /// Build from max_c using Euclid's formula (all 8 octants).
    pub fn from_max_c(max_c: u64) -> Self {
        let raw = generate_triples(max_c);
        Self::new(&raw)
    }

    /// Number of triples in the index.
    pub fn len(&self) -> usize { self.triples.len() }
    pub fn is_empty(&self) -> bool { self.triples.is_empty() }

    /// Exact 1-NN lookup via binary search. O(log n).
    /// Returns the index of the nearest triple.
    pub fn snap(&self, theta: f64) -> usize {
        if self.triples.is_empty() { return 0; }
        let a = ((theta % TAU) + TAU) % TAU;
        match self.triples.binary_search_by(|t| t.angle.partial_cmp(&a).unwrap_or(std::cmp::Ordering::Equal)) {
            Ok(i) => i,
            Err(0) => 0,
            Err(i) if i >= self.triples.len() => {
                // Wraparound: compare last with first
                let d_last = angular_dist(a, self.triples.last().unwrap().angle);
                let d_first = angular_dist(a, self.triples[0].angle);
                if d_last <= d_first { self.triples.len() - 1 } else { 0 }
            }
            Err(i) => {
                let d_lo = angular_dist(a, self.triples[i - 1].angle);
                let d_hi = angular_dist(a, self.triples[i].angle);
                if d_lo <= d_hi { i - 1 } else { i }
            }
        }
    }

    /// Get triple by index.
    pub fn get(&self, idx: usize) -> Option<&Triple> {
        self.triples.get(idx)
    }

    /// Snap and return the triple directly.
    pub fn snap_triple(&self, theta: f64) -> &Triple {
        let idx = self.snap(theta);
        &self.triples[idx]
    }

    /// Compute angular distance between query and snapped triple.
    pub fn snap_distance(&self, theta: f64) -> f64 {
        let a = ((theta % TAU) + TAU) % TAU;
        angular_dist(a, self.snap_triple(theta).angle)
    }

    /// Brute-force nearest neighbor. O(n). For correctness verification.
    pub fn snap_brute(&self, theta: f64) -> usize {
        let a = ((theta % TAU) + TAU) % TAU;
        let mut best_idx = 0;
        let mut best_dist = f64::MAX;
        for (i, t) in self.triples.iter().enumerate() {
            let d = angular_dist(a, t.angle);
            if d < best_dist {
                best_dist = d;
                best_idx = i;
            }
        }
        best_idx
    }

    /// Verify binary search against brute force for n random queries.
    pub fn verify(&self, n_queries: usize) -> VerificationResult {
        let mut agree = 0usize;
        let mut max_err = 0.0f64;
        let step = TAU / n_queries as f64;
        for i in 0..n_queries {
            let theta = i as f64 * step;
            let bs = self.snap(theta);
            let bf = self.snap_brute(theta);
            if bs == bf {
                agree += 1;
            } else {
                let err = angular_dist(self.triples[bs].angle, self.triples[bf].angle);
                max_err = max_err.max(err);
            }
        }
        VerificationResult {
            n_queries,
            n_agree: agree,
            n_disagree: n_queries - agree,
            agreement_rate: agree as f64 / n_queries as f64,
            max_angular_error: max_err,
        }
    }
}

/// Verification result comparing binary search to brute force.
#[derive(Debug, Clone)]
pub struct VerificationResult {
    pub n_queries: usize,
    pub n_agree: usize,
    pub n_disagree: usize,
    pub agreement_rate: f64,
    pub max_angular_error: f64,
}

/// Angular distance on [0, 2*pi) circle.
#[inline]
pub fn angular_dist(a: f64, b: f64) -> f64 {
    let d = (a - b).abs();
    d.min(TAU - d)
}

/// Generate all Pythagorean triples up to max_c (all 8 octants).
pub fn generate_triples(max_c: u64) -> Vec<(i64, i64, u64)> {
    let mut triples = Vec::new();
    let max_m = ((max_c as f64).sqrt() / std::f64::consts::SQRT_2) as u64 + 1;
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
                    triples.push((sa * a as i64, sb * b as i64, c));
                    triples.push((sa * b as i64, sb * a as i64, c));
                }
            }
        }
    }
    triples
}

fn gcd(a: u64, b: u64) -> u64 {
    if b == 0 { a } else { gcd(b, a % b) }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_angular_dist_zero() {
        assert!((angular_dist(1.0, 1.0) - 0.0).abs() < 1e-10);
    }

    #[test]
    fn test_angular_dist_pi() {
        assert!((angular_dist(0.0, std::f64::consts::PI) - std::f64::consts::PI).abs() < 1e-10);
    }

    #[test]
    fn test_angular_dist_wrap() {
        assert!((angular_dist(0.01, TAU - 0.01) - 0.02).abs() < 1e-10);
    }

    #[test]
    fn test_index_build() {
        let idx = TripleIndex::from_max_c(100);
        assert!(idx.len() > 0);
        // Should be sorted
        for i in 1..idx.len() {
            assert!(idx.triples[i].angle >= idx.triples[i-1].angle);
        }
    }

    #[test]
    fn test_snap_known() {
        let idx = TripleIndex::from_max_c(10);
        // (3,4,5) should be present
        let t = idx.snap_triple(0.6435); // arctan(3/4) ≈ 0.6435
        assert_eq!(t.c, 5);
    }

    #[test]
    fn test_verify_perfect() {
        let idx = TripleIndex::from_max_c(5000);
        let result = idx.verify(10000);
        assert_eq!(result.agreement_rate, 1.0);
        assert_eq!(result.n_disagree, 0);
    }

    #[test]
    fn test_snap_distance() {
        let idx = TripleIndex::from_max_c(100);
        let d = idx.snap_distance(0.5);
        assert!(d >= 0.0);
        assert!(d <= std::f64::consts::PI);
    }

    #[test]
    fn test_empty_index() {
        let raw: Vec<(i64, i64, u64)> = vec![];
        let idx = TripleIndex::new(&raw);
        assert!(idx.is_empty());
        assert_eq!(idx.snap(1.0), 0);
    }

    #[test]
    fn test_generate_triples() {
        let triples = generate_triples(10);
        assert!(triples.contains(&(3, 4, 5)));
        assert!(triples.contains(&(-3, 4, 5)));
        assert!(triples.contains(&(4, 3, 5)));
    }

    #[test]
    fn test_benchmark_runs() {
        let idx = TripleIndex::from_max_c(50000);
        let start = std::time::Instant::now();
        let mut sum = 0u64;
        for i in 0..100000 {
            let t = idx.snap(i as f64 / 100000.0 * TAU);
            sum = sum.wrapping_add(t as u64);
        }
        let elapsed = start.elapsed().as_secs_f64();
        std::hint::black_box(sum);
        let qps = 100000.0 / elapsed;
        assert!(qps > 100000.0, "Expected >100K qps, got {:.0}", qps);
    }
}
