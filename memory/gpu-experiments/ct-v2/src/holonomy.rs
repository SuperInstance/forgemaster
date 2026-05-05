use rand::Rng;

use crate::manifold::PythagoreanManifold;

pub struct HolonomyMeter<'a> {
    manifold: &'a PythagoreanManifold,
}

impl<'a> HolonomyMeter<'a> {
    pub fn new(manifold: &'a PythagoreanManifold) -> Self {
        Self { manifold }
    }

    pub fn holonomy_loop(&self, start: (i64, i64, i64), steps: usize) -> f64 {
        if self.manifold.triples.is_empty() || steps == 0 {
            return 0.0;
        }

        let mut rng = rand::thread_rng();
        let mut current = (start.0 as f64, start.1 as f64, start.2 as f64);
        let mut total_error = 0.0;

        for _ in 0..steps {
            let idx = rng.gen_range(0..self.manifold.triples.len());
            let target = self.manifold.triples[idx];
            let target_f = (target.0 as f64, target.1 as f64, target.2 as f64);

            // Move halfway toward a random triple on the manifold
            current = (
                (current.0 + target_f.0) / 2.0,
                (current.1 + target_f.1) / 2.0,
                (current.2 + target_f.2) / 2.0,
            );

            // Snap back to the manifold
            match self.manifold.snap(current) {
                Ok(report) => {
                    total_error += report.error;
                    current = (
                        report.snapped.0 as f64,
                        report.snapped.1 as f64,
                        report.snapped.2 as f64,
                    );
                }
                Err(_) => break,
            }
        }

        total_error
    }

    pub fn survey(&self, samples: usize) -> f64 {
        if self.manifold.triples.is_empty() || samples == 0 {
            return 0.0;
        }

        let mut rng = rand::thread_rng();
        let mut total_error = 0.0;
        let mut valid = 0usize;

        for _ in 0..samples {
            let idx = rng.gen_range(0..self.manifold.triples.len());
            let (a, b, c) = self.manifold.triples[idx];
            let point = (
                a as f64 + rng.gen_range(-0.5..0.5),
                b as f64 + rng.gen_range(-0.5..0.5),
                c as f64 + rng.gen_range(-0.5..0.5),
            );

            match self.manifold.snap(point) {
                Ok(report) => {
                    total_error += report.error;
                    valid += 1;
                }
                Err(_) => {}
            }
        }

        if valid > 0 {
            total_error / valid as f64
        } else {
            0.0
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::resolution::ResolutionConfig;
    use crate::tolerance::FixedTolerance;

    fn make_manifold() -> PythagoreanManifold {
        PythagoreanManifold::new(Box::new(FixedTolerance::new(2.0)), ResolutionConfig::low())
    }

    #[test]
    fn test_holonomy_loop_zero_steps() {
        let m = make_manifold();
        let meter = HolonomyMeter::new(&m);
        assert_eq!(meter.holonomy_loop((3, 4, 5), 0), 0.0);
    }

    #[test]
    fn test_holonomy_loop_non_negative() {
        let m = make_manifold();
        let meter = HolonomyMeter::new(&m);
        let err = meter.holonomy_loop((3, 4, 5), 10);
        assert!(err >= 0.0);
    }

    #[test]
    fn test_survey_zero_samples() {
        let m = make_manifold();
        let meter = HolonomyMeter::new(&m);
        assert_eq!(meter.survey(0), 0.0);
    }

    #[test]
    fn test_survey_non_negative() {
        let m = make_manifold();
        let meter = HolonomyMeter::new(&m);
        let avg = meter.survey(20);
        assert!(avg >= 0.0);
    }

    #[test]
    fn test_survey_on_exact_triples_is_small() {
        // Use a very large tolerance so all perturbed points snap successfully
        let m = PythagoreanManifold::new(Box::new(FixedTolerance::new(10.0)), ResolutionConfig::low());
        let meter = HolonomyMeter::new(&m);
        let avg = meter.survey(50);
        assert!(avg >= 0.0);
        // With perturbation of +/-0.5 and a dense set of triples up to c=100,
        // the average snap error should be reasonably small (< 5.0).
        assert!(avg < 5.0);
    }
}
