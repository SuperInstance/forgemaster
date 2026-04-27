//! # CT Core Extensions
//!
//! Extended constraint theory primitives: adaptive deadband,
//! multi-constraint intersection, and snap diagnostics.

/// Adaptive deadband with epsilon(c) = k/c scaling.
#[derive(Debug, Clone)]
pub struct AdaptiveDeadband {
    k: f64,
    floor: f64,
    ceiling: f64,
}

impl AdaptiveDeadband {
    pub fn new(k: f64, floor: f64, ceiling: f64) -> Self {
        AdaptiveDeadband { k, floor: f64::max(floor, 0.0), ceiling: f64::max(ceiling, floor) }
    }

    pub fn epsilon(&self, c: f64) -> f64 {
        if c <= 0.0 { return self.ceiling; }
        let eps = self.k / c;
        eps.max(self.floor).min(self.ceiling)
    }

    pub fn within(&self, distance: f64, c: f64) -> bool {
        distance <= self.epsilon(c)
    }

    pub fn classify(&self, distance: f64, c: f64) -> SnapClass {
        if distance == 0.0 { return SnapClass::Exact; }
        if self.within(distance, c) { return SnapClass::WithinDeadband; }
        SnapClass::OutsideDeadband
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SnapClass { Exact, WithinDeadband, OutsideDeadband }

/// A single constraint with a check function.
pub trait Constraint: Send + Sync {
    fn name(&self) -> &str;
    fn satisfied(&self, distance: f64) -> bool;
    fn weight(&self) -> f64 { 1.0 }
}

/// Multi-constraint manager.
pub struct MultiConstraint {
    constraints: Vec<Box<dyn Constraint>>,
}

impl MultiConstraint {
    pub fn new() -> Self { MultiConstraint { constraints: vec![] } }

    pub fn add<C: Constraint + 'static>(&mut self, c: C) {
        self.constraints.push(Box::new(c));
    }

    pub fn all_satisfied(&self, distances: &[f64]) -> bool {
        self.constraints.iter().zip(distances.iter()).all(|(c, &d)| c.satisfied(d))
    }

    pub fn violations(&self, distances: &[f64]) -> Vec<&str> {
        self.constraints.iter().zip(distances.iter())
            .filter(|(c, &d)| !c.satisfied(d))
            .map(|(c, _)| c.name())
            .collect()
    }

    pub fn weighted_score(&self, distances: &[f64]) -> f64 {
        self.constraints.iter().zip(distances.iter())
            .map(|(c, &d)| { let w = c.weight(); if c.satisfied(d) { w } else { -w } })
            .sum()
    }

    pub fn len(&self) -> usize { self.constraints.len() }
    pub fn is_empty(&self) -> bool { self.constraints.is_empty() }
}

/// Simple threshold constraint.
pub struct ThresholdConstraint {
    name: String,
    threshold: f64,
    weight: f64,
}

impl ThresholdConstraint {
    pub fn new(name: &str, threshold: f64) -> Self {
        ThresholdConstraint { name: name.into(), threshold, weight: 1.0 }
    }
}

impl Constraint for ThresholdConstraint {
    fn name(&self) -> &str { &self.name }
    fn satisfied(&self, distance: f64) -> bool { distance <= self.threshold }
    fn weight(&self) -> f64 { self.weight }
}

/// Result of a snap operation with diagnostics.
#[derive(Debug, Clone)]
pub struct SnapResult {
    pub index: usize,
    pub distance: f64,
    pub triple_a: i64,
    pub triple_b: i64,
    pub triple_c: u64,
    pub time_ns: u64,
    pub snap_class: SnapClass,
}

impl SnapResult {
    pub fn new(index: usize, distance: f64, a: i64, b: i64, c: u64, time_ns: u64, cls: SnapClass) -> Self {
        SnapResult { index, distance, triple_a: a, triple_b: b, triple_c: c, time_ns, snap_class: cls }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_adaptive_deadband_scaling() {
        let db = AdaptiveDeadband::new(1.0, 1e-10, 1.0);
        assert!((db.epsilon(100.0) - 0.01).abs() < 1e-12);
        assert!((db.epsilon(1000.0) - 0.001).abs() < 1e-12);
    }

    #[test]
    fn test_deadband_floor_ceiling() {
        let db = AdaptiveDeadband::new(1.0, 0.01, 0.5);
        assert!((db.epsilon(10000.0) - 0.01).abs() < 1e-12); // hits floor
        assert!((db.epsilon(1.0) - 0.5).abs() < 1e-12);     // hits ceiling
    }

    #[test]
    fn test_deadband_within() {
        let db = AdaptiveDeadband::new(1.0, 1e-10, 1.0);
        assert!(db.within(0.005, 100.0));
        assert!(!db.within(0.02, 100.0));
    }

    #[test]
    fn test_deadband_classify() {
        let db = AdaptiveDeadband::new(1.0, 1e-10, 1.0);
        assert_eq!(db.classify(0.0, 100.0), SnapClass::Exact);
        assert_eq!(db.classify(0.005, 100.0), SnapClass::WithinDeadband);
        assert_eq!(db.classify(0.02, 100.0), SnapClass::OutsideDeadband);
    }

    #[test]
    fn test_multi_constraint_all_satisfied() {
        let mut mc = MultiConstraint::new();
        mc.add(ThresholdConstraint::new("tight", 0.1));
        mc.add(ThresholdConstraint::new("loose", 1.0));
        assert!(mc.all_satisfied(&[0.05, 0.5]));
    }

    #[test]
    fn test_multi_constraint_violations() {
        let mut mc = MultiConstraint::new();
        mc.add(ThresholdConstraint::new("tight", 0.1));
        mc.add(ThresholdConstraint::new("loose", 1.0));
        let v = mc.violations(&[0.5, 0.5]);
        assert_eq!(v, vec!["tight"]);
    }

    #[test]
    fn test_multi_constraint_weighted_score() {
        let mut mc = MultiConstraint::new();
        mc.add(ThresholdConstraint::new("a", 0.1));
        mc.add(ThresholdConstraint::new("b", 1.0));
        let s = mc.weighted_score(&[0.05, 2.0]);
        assert!((s - 0.0).abs() < 1e-10); // 1 + (-1) = 0
    }

    #[test]
    fn test_multi_constraint_empty() {
        let mc = MultiConstraint::new();
        assert!(mc.is_empty());
        assert!(mc.all_satisfied(&[]));
    }

    #[test]
    fn test_snap_result_creation() {
        let sr = SnapResult::new(42, 0.001, 3, 4, 5, 1234, SnapClass::WithinDeadband);
        assert_eq!(sr.index, 42);
        assert_eq!(sr.triple_c, 5);
        assert_eq!(sr.snap_class, SnapClass::WithinDeadband);
    }

    #[test]
    fn test_deadband_zero_c() {
        let db = AdaptiveDeadband::new(1.0, 0.01, 1.0);
        assert_eq!(db.epsilon(0.0), 1.0); // ceiling
    }

    #[test]
    fn test_deadband_negative_c() {
        let db = AdaptiveDeadband::new(1.0, 0.01, 1.0);
        assert_eq!(db.epsilon(-5.0), 1.0); // ceiling
    }
}
