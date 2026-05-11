//! AttentionBudget — finite cognition allocation.
//!
//! Cognition is finite. The snap functions serve as gatekeepers of a
//! finite attention budget. Attention is allocated proportionally to
//! the magnitude of the felt delta AND the actionability of that delta.
//!
//! "The snap function does not merely detect deltas — it allocates
//! attention to deltas where cognition can affect outcomes."

use crate::delta::{Delta, DeltaSeverity};

/// The result of allocating attention to a delta.
#[derive(Debug, Clone)]
pub struct AttentionAllocation {
    /// The delta that was allocated attention.
    pub delta: Delta,
    /// Amount of attention allocated.
    pub allocated: f64,
    /// Priority rank (1 = highest).
    pub priority: usize,
    /// Reason for this allocation.
    pub reason: String,
}

/// Strategy for allocating attention across deltas.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum AllocationStrategy {
    /// Actionability-weighted: proportional to magnitude × actionability × urgency.
    /// This is THE expert strategy — focus on what you can change.
    Actionability,
    /// Reactive: attend to biggest deltas regardless of actionability.
    Reactive,
    /// Uniform: equal attention to all nontrivial deltas.
    Uniform,
}

#[allow(dead_code)]
impl AllocationStrategy {
    fn name(&self) -> &'static str {
        match self {
            AllocationStrategy::Actionability => "actionability",
            AllocationStrategy::Reactive => "reactive",
            AllocationStrategy::Uniform => "uniform",
        }
    }
}

/// Finite cognitive resource allocator.
///
/// Models the attention budget constraint:
///     Σ A_i ≤ A_max
/// where A_i is attention allocated to delta i, and A_max is total
/// available cognitive bandwidth.
///
/// Attention is allocated based on:
/// 1. Delta magnitude — how far from expected
/// 2. Actionability — can thinking change this?
/// 3. Urgency — does this need attention NOW?
///
/// # Examples
///
/// ```
/// use snapkit::{AttentionBudget, AllocationStrategy, SnapFunction, DeltaDetector};
///
/// let mut budget = AttentionBudget::new(100.0, AllocationStrategy::Actionability);
///
/// let mut detector = DeltaDetector::new();
/// detector.add_stream("test", SnapFunction::<f64>::new());
/// detector.observe("test", 0.5); // major delta
///
/// let deltas = detector.prioritize(10);
/// let allocations = budget.allocate(&deltas);
/// assert!(!allocations.is_empty());
/// ```
#[derive(Debug, Clone)]
pub struct AttentionBudget {
    /// Maximum attention available per allocation cycle.
    total_budget: f64,
    /// Remaining attention after allocation.
    remaining: f64,
    /// Allocation strategy.
    strategy: AllocationStrategy,
    /// History of all allocations made.
    history: Vec<Vec<AttentionAllocation>>,
    /// How many times the budget was exhausted.
    exhaustion_count: u64,
}

impl AttentionBudget {
    /// Create a new attention budget.
    pub fn new(total_budget: f64, strategy: AllocationStrategy) -> Self {
        Self {
            total_budget,
            remaining: total_budget,
            strategy,
            history: Vec::new(),
            exhaustion_count: 0,
        }
    }

    /// Set the allocation strategy.
    pub fn set_strategy(&mut self, strategy: AllocationStrategy) {
        self.strategy = strategy;
    }

    /// Get the current strategy.
    pub fn strategy(&self) -> AllocationStrategy {
        self.strategy
    }

    /// Allocate attention budget to a prioritized list of deltas.
    ///
    /// Returns a list of `AttentionAllocation` objects showing what was allocated
    /// and why.
    pub fn allocate(&mut self, deltas: &[&Delta]) -> Vec<AttentionAllocation> {
        self.remaining = self.total_budget;

        let allocations = match self.strategy {
            AllocationStrategy::Actionability => self.allocate_actionability(deltas),
            AllocationStrategy::Reactive => self.allocate_reactive(deltas),
            AllocationStrategy::Uniform => self.allocate_uniform(deltas),
        };

        self.history.push(allocations.clone());

        if self.remaining <= 0.0 {
            self.exhaustion_count += 1;
        }

        allocations
    }

    /// Actionability-weighted allocation (THE expert strategy).
    ///
    /// Weight = delta.magnitude × delta.attention_weight.
    /// Allocate budget proportionally to weight.
    fn allocate_actionability(&self, deltas: &[&Delta]) -> Vec<AttentionAllocation> {
        if deltas.is_empty() {
            return Vec::new();
        }

        // Filter to nontrivial deltas and compute weights
        let nontrivial: Vec<(usize, &Delta)> = deltas
            .iter()
            .enumerate()
            .filter(|(_, d)| d.exceeds_tolerance())
            .map(|(i, d)| (i, *d))
            .collect();

        if nontrivial.is_empty() {
            return Vec::new();
        }

        let total_weight: f64 = nontrivial.iter().map(|(_, d)| d.attention_weight).sum();
        if total_weight <= 0.0 {
            return Vec::new();
        }

        let mut budget_remaining = self.total_budget;
        let mut allocations = Vec::with_capacity(nontrivial.len());

        // Sort by attention weight descending for priority ranking
        let mut sorted: Vec<&Delta> = nontrivial.iter().map(|(_, d)| *d).collect();
        sorted.sort_by(|a, b| {
            b.attention_weight
                .partial_cmp(&a.attention_weight)
                .unwrap_or(std::cmp::Ordering::Equal)
        });

        for (priority, delta) in sorted.iter().enumerate() {
            let proportional = (delta.attention_weight / total_weight) * self.total_budget;
            let allocated = proportional.min(budget_remaining);

            let reason = explain_allocation(delta);

            if allocated <= 0.0 {
                allocations.push(AttentionAllocation {
                    delta: (*delta).clone(),
                    allocated: 0.0,
                    priority: priority + 1,
                    reason: "BUDGET_EXHAUSTED".to_string(),
                });
                continue;
            }

            budget_remaining -= allocated;
            allocations.push(AttentionAllocation {
                delta: (*delta).clone(),
                allocated,
                priority: priority + 1,
                reason,
            });
        }

        allocations
    }

    /// Reactive: attend to biggest deltas regardless of actionability.
    fn allocate_reactive(&self, deltas: &[&Delta]) -> Vec<AttentionAllocation> {
        let mut nontrivial: Vec<&Delta> = deltas
            .iter()
            .filter(|d| d.exceeds_tolerance())
            .copied()
            .collect();

        nontrivial.sort_by(|a, b| {
            b.magnitude
                .partial_cmp(&a.magnitude)
                .unwrap_or(std::cmp::Ordering::Equal)
        });

        let mut budget_remaining = self.total_budget;
        let mut allocations = Vec::new();

        for (priority, delta) in nontrivial.iter().enumerate() {
            let allocated = delta.magnitude.min(budget_remaining);
            budget_remaining -= allocated;
            allocations.push(AttentionAllocation {
                delta: (*delta).clone(),
                allocated,
                priority: priority + 1,
                reason: "REACTIVE_LARGEST_FIRST".to_string(),
            });
            if budget_remaining <= 0.0 {
                break;
            }
        }

        allocations
    }

    /// Uniform: equal attention to all nontrivial deltas.
    fn allocate_uniform(&self, deltas: &[&Delta]) -> Vec<AttentionAllocation> {
        let nontrivial: Vec<&Delta> = deltas
            .iter()
            .filter(|d| d.exceeds_tolerance())
            .copied()
            .collect();

        if nontrivial.is_empty() {
            return Vec::new();
        }

        let per_delta = self.total_budget / nontrivial.len() as f64;
        nontrivial
            .iter()
            .enumerate()
            .map(|(priority, delta)| AttentionAllocation {
                delta: (*delta).clone(),
                allocated: per_delta,
                priority: priority + 1,
                reason: "UNIFORM_EQUAL".to_string(),
            })
            .collect()
    }

    /// Fraction of budget currently used.
    pub fn utilization(&self) -> f64 {
        let used = self.total_budget - self.remaining;
        if self.total_budget <= 0.0 {
            return 0.0;
        }
        used / self.total_budget
    }

    /// How often the budget has been exhausted.
    pub fn exhaustion_rate(&self) -> f64 {
        if self.history.is_empty() {
            return 0.0;
        }
        self.exhaustion_count as f64 / self.history.len() as f64
    }

    /// Remaining attention budget.
    pub fn remaining(&self) -> f64 {
        self.remaining
    }

    /// Total budget per cycle.
    pub fn total_budget(&self) -> f64 {
        self.total_budget
    }

    /// Total allocation cycles.
    pub fn cycles(&self) -> usize {
        self.history.len()
    }

    /// Reset the budget (clear history, reset counters).
    pub fn reset(&mut self) {
        self.remaining = self.total_budget;
        self.history.clear();
        self.exhaustion_count = 0;
    }
}

/// Generate a human-readable reason for an allocation.
fn explain_allocation(delta: &Delta) -> String {
    match delta.severity {
        DeltaSeverity::None => "within tolerance".to_string(),
        DeltaSeverity::Low => "minor variation".to_string(),
        DeltaSeverity::Medium => "notable delta".to_string(),
        DeltaSeverity::High => "significant delta".to_string(),
        DeltaSeverity::Critical => "CRITICAL: system-level concern".to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_detector_and_deltas() -> (Vec<Delta>, Vec<Delta>) {
        // Create two deltas: one small, one large
        let small = Delta {
            value: 0.2,
            expected: 0.0,
            magnitude: 0.2,
            tolerance: 0.1,
            severity: DeltaSeverity::Medium,
            timestamp: 1,
            stream_id: "small".to_string(),
            attention_weight: 2.0,
        };
        let large = Delta {
            value: 0.8,
            expected: 0.0,
            magnitude: 0.8,
            tolerance: 0.1,
            severity: DeltaSeverity::High,
            timestamp: 2,
            stream_id: "large".to_string(),
            attention_weight: 8.0,
        };
        (vec![small], vec![large])
    }

    #[test]
    fn test_actionability_allocation() {
        let (small_deltas, large_deltas) = make_detector_and_deltas();
        let all_deltas: Vec<&Delta> = vec![&small_deltas[0], &large_deltas[0]];

        let mut budget = AttentionBudget::new(100.0, AllocationStrategy::Actionability);
        let allocations = budget.allocate(&all_deltas);

        // The large delta should get more attention
        assert_eq!(allocations.len(), 2);
        assert!(allocations[0].allocated > allocations[1].allocated);
    }

    #[test]
    fn test_reactive_allocation() {
        let (small_deltas, large_deltas) = make_detector_and_deltas();
        let all_deltas: Vec<&Delta> = vec![&small_deltas[0], &large_deltas[0]];

        let mut budget = AttentionBudget::new(100.0, AllocationStrategy::Reactive);
        let allocations = budget.allocate(&all_deltas);

        assert_eq!(allocations.len(), 2);
        assert!(allocations[0].allocated > allocations[1].allocated);
    }

    #[test]
    fn test_uniform_allocation() {
        let (small_deltas, large_deltas) = make_detector_and_deltas();
        let all_deltas: Vec<&Delta> = vec![&small_deltas[0], &large_deltas[0]];

        let mut budget = AttentionBudget::new(100.0, AllocationStrategy::Uniform);
        let allocations = budget.allocate(&all_deltas);

        assert_eq!(allocations.len(), 2);
        assert!((allocations[0].allocated - allocations[1].allocated).abs() < 1e-10);
    }

    #[test]
    fn test_budget_exhaustion() {
        let delta = Delta {
            value: 10.0,
            expected: 0.0,
            magnitude: 10.0,
            tolerance: 0.1,
            severity: DeltaSeverity::Critical,
            timestamp: 1,
            stream_id: "big".to_string(),
            attention_weight: 10.0,
        };

        let mut budget = AttentionBudget::new(5.0, AllocationStrategy::Reactive);
        let allocations = budget.allocate(&[&delta]);

        // Allocation should be capped at remaining budget
        assert_eq!(allocations.len(), 1);
        assert!((allocations[0].allocated - 5.0).abs() < 1e-10);
    }

    #[test]
    fn test_empty_deltas() {
        let mut budget = AttentionBudget::new(100.0, AllocationStrategy::Actionability);
        let allocations = budget.allocate(&[]);
        assert!(allocations.is_empty());
    }

    #[test]
    fn test_utilization() {
        let delta = Delta {
            value: 1.0,
            expected: 0.0,
            magnitude: 1.0,
            tolerance: 0.1,
            severity: DeltaSeverity::High,
            timestamp: 1,
            stream_id: "test".to_string(),
            attention_weight: 1.0,
        };

        let mut budget = AttentionBudget::new(10.0, AllocationStrategy::Uniform);
        let _ = budget.allocate(&[&delta]);
        assert!((budget.utilization() - 1.0).abs() < 1e-10);
    }

    #[test]
    fn test_strategy_switching() {
        let mut budget = AttentionBudget::new(100.0, AllocationStrategy::Reactive);
        assert_eq!(budget.strategy(), AllocationStrategy::Reactive);
        budget.set_strategy(AllocationStrategy::Actionability);
        assert_eq!(budget.strategy(), AllocationStrategy::Actionability);
    }

    #[test]
    fn test_cycles_count() {
        let mut budget = AttentionBudget::new(100.0, AllocationStrategy::Actionability);
        assert_eq!(budget.cycles(), 0);

        let d = Delta {
            value: 1.0,
            expected: 0.0,
            magnitude: 1.0,
            tolerance: 0.1,
            severity: DeltaSeverity::High,
            timestamp: 1,
            stream_id: "test".to_string(),
            attention_weight: 1.0,
        };

        budget.allocate(&[&d]);
        assert_eq!(budget.cycles(), 1);
    }

    #[test]
    fn test_budget_reset() {
        let mut budget = AttentionBudget::new(100.0, AllocationStrategy::Actionability);
        assert_eq!(budget.cycles(), 0);

        let d = Delta {
            value: 1.0,
            expected: 0.0,
            magnitude: 1.0,
            tolerance: 0.1,
            severity: DeltaSeverity::High,
            timestamp: 1,
            stream_id: "test".to_string(),
            attention_weight: 1.0,
        };

        budget.allocate(&[&d]);
        assert_eq!(budget.cycles(), 1);

        budget.reset();
        assert_eq!(budget.cycles(), 0);
        assert!((budget.remaining() - budget.total_budget()).abs() < 1e-10);
    }
}
