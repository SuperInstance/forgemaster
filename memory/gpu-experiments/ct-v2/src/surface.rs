use crate::manifold::PythagoreanManifold;
use crate::snap::{SnapError, SnapReport};

pub trait ConstraintSurface: Send + Sync {
    fn snap(&self, point: (f64, f64, f64)) -> Result<SnapReport, SnapError>;
    fn contains(&self, point: (i64, i64, i64)) -> bool;
    fn count(&self) -> usize;
}

pub struct PythagoreanSurface {
    manifold: PythagoreanManifold,
}

impl PythagoreanSurface {
    pub fn new(manifold: PythagoreanManifold) -> Self {
        Self { manifold }
    }
}

impl ConstraintSurface for PythagoreanSurface {
    fn snap(&self, point: (f64, f64, f64)) -> Result<SnapReport, SnapError> {
        self.manifold.snap(point)
    }

    fn contains(&self, point: (i64, i64, i64)) -> bool {
        self.manifold.triples.contains(&point)
    }

    fn count(&self) -> usize {
        self.manifold.triples.len()
    }
}

#[derive(Debug, Clone, PartialEq)]
pub enum ConflictStrategy {
    Nearest,
    Priority(usize),
    All,
}

pub struct MultiManifold {
    surfaces: Vec<Box<dyn ConstraintSurface>>,
    strategy: ConflictStrategy,
}

impl MultiManifold {
    pub fn new(strategy: ConflictStrategy) -> Self {
        Self {
            surfaces: Vec::new(),
            strategy,
        }
    }

    pub fn add_surface(&mut self, surface: Box<dyn ConstraintSurface>) {
        self.surfaces.push(surface);
    }

    pub fn snap(&self, point: (f64, f64, f64)) -> Result<Vec<SnapReport>, SnapError> {
        if self.surfaces.is_empty() {
            return Err(SnapError::NoTripleFound);
        }

        match self.strategy {
            ConflictStrategy::Nearest => {
                let mut best: Option<SnapReport> = None;
                for surface in &self.surfaces {
                    if let Ok(report) = surface.snap(point) {
                        best = match best {
                            Some(ref b) if report.error < b.error => Some(report),
                            None => Some(report),
                            _ => best,
                        };
                    }
                }
                best.map(|r| vec![r]).ok_or(SnapError::NoTripleFound)
            }
            ConflictStrategy::Priority(p) => {
                if p < self.surfaces.len() {
                    match self.surfaces[p].snap(point) {
                        Ok(report) => Ok(vec![report]),
                        Err(_) => {
                            // Fallback to first successful surface
                            for surface in &self.surfaces {
                                if let Ok(report) = surface.snap(point) {
                                    return Ok(vec![report]);
                                }
                            }
                            Err(SnapError::NoTripleFound)
                        }
                    }
                } else {
                    Err(SnapError::OutOfBounds)
                }
            }
            ConflictStrategy::All => {
                let mut results = Vec::new();
                for surface in &self.surfaces {
                    if let Ok(report) = surface.snap(point) {
                        results.push(report);
                    }
                }
                if results.is_empty() {
                    Err(SnapError::NoTripleFound)
                } else {
                    Ok(results)
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::resolution::ResolutionConfig;
    use crate::tolerance::FixedTolerance;

    #[test]
    fn test_surface_contains() {
        let s = PythagoreanSurface::new(PythagoreanManifold::new(
            Box::new(FixedTolerance::new(1.0)),
            ResolutionConfig::low(),
        ));
        assert!(s.contains((3, 4, 5)));
        assert!(!s.contains((1, 1, 1)));
    }

    #[test]
    fn test_surface_count() {
        let s = PythagoreanSurface::new(PythagoreanManifold::new(
            Box::new(FixedTolerance::new(1.0)),
            ResolutionConfig::low(),
        ));
        assert!(s.count() > 0);
    }

    #[test]
    fn test_surface_snap() {
        let s = PythagoreanSurface::new(PythagoreanManifold::new(
            Box::new(FixedTolerance::new(1.0)),
            ResolutionConfig::low(),
        ));
        let report = s.snap((3.0, 4.0, 5.0)).unwrap();
        assert_eq!(report.snapped, (3, 4, 5));
    }

    #[test]
    fn test_multi_nearest() {
        let mut multi = MultiManifold::new(ConflictStrategy::Nearest);
        multi.add_surface(Box::new(PythagoreanSurface::new(PythagoreanManifold::new(
            Box::new(FixedTolerance::new(1.0)),
            ResolutionConfig::low(),
        ))));
        multi.add_surface(Box::new(PythagoreanSurface::new(PythagoreanManifold::new(
            Box::new(FixedTolerance::new(1.0)),
            ResolutionConfig { max_c: 20, step_size: 1 },
        ))));

        let results = multi.snap((3.0, 4.0, 5.0)).unwrap();
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].snapped, (3, 4, 5));
    }

    #[test]
    fn test_multi_all() {
        let mut multi = MultiManifold::new(ConflictStrategy::All);
        multi.add_surface(Box::new(PythagoreanSurface::new(PythagoreanManifold::new(
            Box::new(FixedTolerance::new(1.0)),
            ResolutionConfig::low(),
        ))));
        multi.add_surface(Box::new(PythagoreanSurface::new(PythagoreanManifold::new(
            Box::new(FixedTolerance::new(1.0)),
            ResolutionConfig { max_c: 20, step_size: 1 },
        ))));

        let results = multi.snap((3.0, 4.0, 5.0)).unwrap();
        // Both surfaces contain (3,4,5), so we should get at least one result
        assert!(!results.is_empty());
    }

    #[test]
    fn test_multi_priority() {
        let mut multi = MultiManifold::new(ConflictStrategy::Priority(1));
        multi.add_surface(Box::new(PythagoreanSurface::new(PythagoreanManifold::new(
            Box::new(FixedTolerance::new(1.0)),
            ResolutionConfig::low(),
        ))));
        multi.add_surface(Box::new(PythagoreanSurface::new(PythagoreanManifold::new(
            Box::new(FixedTolerance::new(1.0)),
            ResolutionConfig { max_c: 20, step_size: 1 },
        ))));

        let results = multi.snap((3.0, 4.0, 5.0)).unwrap();
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].snapped, (3, 4, 5));
    }

    #[test]
    fn test_multi_priority_fallback() {
        let mut multi = MultiManifold::new(ConflictStrategy::Priority(0));
        // m1 is empty (max_c=2 produces no Pythagorean triple)
        multi.add_surface(Box::new(PythagoreanSurface::new(PythagoreanManifold::new(
            Box::new(FixedTolerance::new(0.001)),
            ResolutionConfig { max_c: 2, step_size: 1 },
        ))));
        multi.add_surface(Box::new(PythagoreanSurface::new(PythagoreanManifold::new(
            Box::new(FixedTolerance::new(1.0)),
            ResolutionConfig::low(),
        ))));

        // priority(0) fails and falls back to second surface
        let results = multi.snap((3.0, 4.0, 5.0)).unwrap();
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].snapped, (3, 4, 5));
    }

    #[test]
    fn test_multi_empty_error() {
        let multi = MultiManifold::new(ConflictStrategy::All);
        assert!(matches!(multi.snap((1.0, 1.0, 1.0)), Err(SnapError::NoTripleFound)));
    }

    #[test]
    fn test_multi_priority_out_of_bounds() {
        let mut multi = MultiManifold::new(ConflictStrategy::Priority(5));
        multi.add_surface(Box::new(PythagoreanSurface::new(PythagoreanManifold::new(
            Box::new(FixedTolerance::new(1.0)),
            ResolutionConfig::low(),
        ))));
        assert!(matches!(multi.snap((1.0, 1.0, 1.0)), Err(SnapError::OutOfBounds)));
    }

    #[test]
    fn test_constraint_surface_object_safe() {
        fn _assert_object_safe(_: &dyn ConstraintSurface) {}
    }
}
