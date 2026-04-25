use crate::resolution::ResolutionConfig;
use crate::snap::{SnapError, SnapReport};
use crate::tolerance::TolerancePolicy;

pub struct PythagoreanManifold {
    pub triples: Vec<(i64, i64, i64)>,
    pub tolerance: Box<dyn TolerancePolicy>,
}

impl PythagoreanManifold {
    pub fn new(tolerance: Box<dyn TolerancePolicy>, config: ResolutionConfig) -> Self {
        let mut m = Self {
            triples: Vec::new(),
            tolerance,
        };
        m.generate_triples(config);
        m
    }

    pub fn generate_triples(&mut self, config: ResolutionConfig) {
        self.triples.clear();
        let max_c = config.max_c;
        let step = config.step_size.max(1);

        for a in (1..=max_c).step_by(step as usize) {
            for b in (a..=max_c).step_by(step as usize) {
                let c_sq = a * a + b * b;
                let c = (c_sq as f64).sqrt().round() as i64;
                if c <= max_c && c > 0 && a * a + b * b == c * c {
                    self.triples.push((a, b, c));
                }
            }
        }

        self.triples.sort_by_key(|t| t.2);
    }

    pub fn snap(&self, point: (f64, f64, f64)) -> Result<SnapReport, SnapError> {
        if self.triples.is_empty() {
            return Err(SnapError::NoTripleFound);
        }

        let (x, y, z) = point;
        if x < 0.0 || y < 0.0 || z < 0.0 {
            return Err(SnapError::OutOfBounds);
        }

        let mut best: Option<(i64, i64, i64)> = None;
        let mut min_error = f64::INFINITY;

        for &(a, b, c) in &self.triples {
            let err = ((x - a as f64).powi(2)
                + (y - b as f64).powi(2)
                + (z - c as f64).powi(2))
            .sqrt();
            if err < min_error {
                min_error = err;
                best = Some((a, b, c));
            }
        }

        if let Some((a, b, c)) = best {
            let tol = self.tolerance.epsilon(c as f64);
            if min_error <= tol {
                Ok(SnapReport {
                    original: point,
                    snapped: (a, b, c),
                    error: min_error,
                    is_exact: min_error < 1e-12,
                })
            } else {
                Err(SnapError::NoTripleFound)
            }
        } else {
            Err(SnapError::NoTripleFound)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::tolerance::{AdaptiveTolerance, FixedTolerance};

    #[test]
    fn test_generate_triples_sorted_by_c() {
        let tol = Box::new(FixedTolerance::new(1.0));
        let m = PythagoreanManifold::new(tol, ResolutionConfig::low());
        assert!(!m.triples.is_empty());

        for i in 1..m.triples.len() {
            assert!(m.triples[i - 1].2 <= m.triples[i].2);
        }
    }

    #[test]
    fn test_generate_triples_contains_345() {
        let tol = Box::new(FixedTolerance::new(1.0));
        let m = PythagoreanManifold::new(tol, ResolutionConfig::low());
        assert!(m.triples.contains(&(3, 4, 5)));
    }

    #[test]
    fn test_generate_triples_contains_51213() {
        let tol = Box::new(FixedTolerance::new(1.0));
        let m = PythagoreanManifold::new(tol, ResolutionConfig::low());
        assert!(m.triples.contains(&(5, 12, 13)));
    }

    #[test]
    fn test_snap_exact_match() {
        let tol = Box::new(FixedTolerance::new(0.01));
        let m = PythagoreanManifold::new(tol, ResolutionConfig::low());
        let report = m.snap((3.0, 4.0, 5.0)).unwrap();
        assert_eq!(report.snapped, (3, 4, 5));
        assert!(report.is_exact);
        assert!(report.error < 1e-12);
    }

    #[test]
    fn test_snap_nearest_within_tolerance() {
        let tol = Box::new(FixedTolerance::new(1.0));
        let m = PythagoreanManifold::new(tol, ResolutionConfig::low());
        let report = m.snap((3.1, 4.1, 5.1)).unwrap();
        assert_eq!(report.snapped, (3, 4, 5));
        assert!(!report.is_exact);
    }

    #[test]
    fn test_snap_outside_tolerance() {
        let tol = Box::new(FixedTolerance::new(0.001));
        let m = PythagoreanManifold::new(tol, ResolutionConfig::low());
        assert!(matches!(m.snap((50.0, 60.0, 70.0)), Err(SnapError::NoTripleFound)));
    }

    #[test]
    fn test_snap_out_of_bounds() {
        let tol = Box::new(FixedTolerance::new(100.0));
        let m = PythagoreanManifold::new(tol, ResolutionConfig::low());
        assert!(matches!(m.snap((-1.0, 4.0, 5.0)), Err(SnapError::OutOfBounds)));
        assert!(matches!(m.snap((3.0, -4.0, 5.0)), Err(SnapError::OutOfBounds)));
        assert!(matches!(m.snap((3.0, 4.0, -5.0)), Err(SnapError::OutOfBounds)));
    }

    #[test]
    fn test_snap_empty_manifold() {
        let tol = Box::new(FixedTolerance::new(1.0));
        let m = PythagoreanManifold::new(tol, ResolutionConfig { max_c: 0, step_size: 1 });
        assert!(matches!(m.snap((1.0, 1.0, 1.0)), Err(SnapError::NoTripleFound)));
    }

    #[test]
    fn test_adaptive_tolerance_snap() {
        let tol = Box::new(AdaptiveTolerance::new(10.0));
        let m = PythagoreanManifold::new(tol, ResolutionConfig::low());
        // At c=5, epsilon = 10/5 = 2.0
        let report = m.snap((3.5, 4.5, 5.5)).unwrap();
        assert_eq!(report.snapped, (3, 4, 5));
    }

    #[test]
    fn test_manifold_send_sync() {
        fn assert_send_sync<T: Send + Sync>() {}
        assert_send_sync::<PythagoreanManifold>();
    }
}
