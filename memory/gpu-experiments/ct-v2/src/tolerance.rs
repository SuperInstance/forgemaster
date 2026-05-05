pub trait TolerancePolicy: Send + Sync {
    fn epsilon(&self, context: f64) -> f64;
}

pub struct AdaptiveTolerance {
    pub k: f64,
}

impl AdaptiveTolerance {
    pub fn new(k: f64) -> Self {
        Self { k }
    }
}

impl TolerancePolicy for AdaptiveTolerance {
    fn epsilon(&self, context: f64) -> f64 {
        if context == 0.0 {
            self.k
        } else {
            self.k / context.abs()
        }
    }
}

pub struct FixedTolerance {
    pub epsilon: f64,
}

impl FixedTolerance {
    pub fn new(epsilon: f64) -> Self {
        Self { epsilon }
    }
}

impl TolerancePolicy for FixedTolerance {
    fn epsilon(&self, _context: f64) -> f64 {
        self.epsilon
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_fixed_tolerance_constant() {
        let tol = FixedTolerance::new(0.5);
        assert_eq!(tol.epsilon(1.0), 0.5);
        assert_eq!(tol.epsilon(10.0), 0.5);
        assert_eq!(tol.epsilon(100.0), 0.5);
    }

    #[test]
    fn test_adaptive_tolerance() {
        let tol = AdaptiveTolerance::new(10.0);
        assert_eq!(tol.epsilon(2.0), 5.0);
        assert_eq!(tol.epsilon(5.0), 2.0);
        assert_eq!(tol.epsilon(10.0), 1.0);
    }

    #[test]
    fn test_adaptive_tolerance_zero_context() {
        let tol = AdaptiveTolerance::new(5.0);
        assert_eq!(tol.epsilon(0.0), 5.0);
    }

    #[test]
    fn test_tolerance_send_sync() {
        fn assert_send_sync<T: Send + Sync>() {}
        assert_send_sync::<FixedTolerance>();
        assert_send_sync::<AdaptiveTolerance>();
    }
}
