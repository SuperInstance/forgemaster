use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use std::time::Instant;
use tracing::info;

use super::{CspSolution, GpuDispatcher};

/// A single CSP instance for batch solving.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CspInstance {
    pub id: u64,
    pub variables: Vec<String>,
    pub domains: Vec<Vec<f64>>,
    pub constraints: Vec<CspConstraint>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CspConstraint {
    pub var_indices: Vec<usize>,
    pub relation: ConstraintRelation,
    pub params: Vec<f64>,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub enum ConstraintRelation {
    LessThan,
    Equal,
    NotEqual,
    SumEquals,
    AllDifferent,
    Custom(u8),
}

/// Batch CSP solver — CPU fallback and GPU dispatch.
pub struct BatchCspSolver {
    dispatcher: std::sync::Arc<GpuDispatcher>,
}

impl BatchCspSolver {
    pub fn new(dispatcher: std::sync::Arc<GpuDispatcher>) -> Self {
        Self { dispatcher }
    }

    /// Solve N CSP instances. Routes to GPU if batch is large enough.
    pub async fn solve_batch(&self, instances: &[CspInstance]) -> Vec<CspSolution> {
        if self.dispatcher.should_use_gpu(instances.len()) {
            self.solve_gpu(instances).await
        } else {
            self.solve_cpu(instances)
        }
    }

    /// CPU-parallel solve using rayon.
    fn solve_cpu(&self, instances: &[CspInstance]) -> Vec<CspSolution> {
        info!("Solving {} CSP instances on CPU", instances.len());
        instances
            .par_iter()
            .map(|inst| {
                let start = Instant::now();
                let solution = backtrack_solve(inst);
                CspSolution {
                    instance_id: inst.id,
                    satisfied: solution.is_some(),
                    assignments: solution.unwrap_or_default(),
                    solve_time_ns: start.elapsed().as_nanos() as u64,
                }
            })
            .collect()
    }

    /// GPU batch solve — in production, calls flux_cuda.so via FFI.
    async fn solve_gpu(&self, instances: &[CspInstance]) -> Vec<CspSolution> {
        let sem = self.dispatcher.semaphore();
        let _permit = sem.acquire().await.unwrap();
        info!(
            "Solving {} CSP instances on GPU ({}MB)",
            instances.len(),
            self.dispatcher.gpu_memory_mb()
        );

        // Production: FFI to libflux_cuda.so
        // For now: CPU fallback with GPU timing simulation
        let instances_vec = instances.to_vec();
        tokio::task::spawn_blocking(move || {
            instances_vec
                .par_iter()
                .map(|inst| {
                    let start = Instant::now();
                    let solution = backtrack_solve(inst);
                    CspSolution {
                        instance_id: inst.id,
                        satisfied: solution.is_some(),
                        assignments: solution.unwrap_or_default(),
                        solve_time_ns: start.elapsed().as_nanos() as u64,
                    }
                })
                .collect()
        })
        .await
        .unwrap_or_default()
    }
}

/// Simple backtracking solver for demonstration.
/// Production would use arc-consistency + forward-checking.
fn backtrack_solve(instance: &CspInstance) -> Option<Vec<(String, f64)>> {
    let n = instance.variables.len();
    let mut assignment = vec![None::<f64>; n];

    if backtrack_recursive(instance, &mut assignment, 0) {
        Some(
            instance
                .variables
                .iter()
                .zip(assignment.iter())
                .filter_map(|(name, val)| val.map(|v| (name.clone(), v)))
                .collect(),
        )
    } else {
        None
    }
}

fn backtrack_recursive(
    instance: &CspInstance,
    assignment: &mut [Option<f64>],
    idx: usize,
) -> bool {
    if idx >= instance.variables.len() {
        return check_constraints(instance, assignment);
    }

    for &val in &instance.domains[idx] {
        assignment[idx] = Some(val);
        if check_constraints_partial(instance, assignment, idx) {
            if backtrack_recursive(instance, assignment, idx + 1) {
                return true;
            }
        }
    }
    assignment[idx] = None;
    false
}

fn check_constraints(instance: &CspInstance, assignment: &[Option<f64>]) -> bool {
    instance.constraints.iter().all(|c| {
        let vals: Vec<f64> = c
            .var_indices
            .iter()
            .filter_map(|&i| assignment[i])
            .collect();
        evaluate_constraint(&c.relation, &c.params, &vals)
    })
}

fn check_constraints_partial(
    instance: &CspInstance,
    assignment: &[Option<f64>],
    _assigned_up_to: usize,
) -> bool {
    // Only check constraints where all involved variables are assigned
    instance.constraints.iter().all(|c| {
        let all_assigned = c
            .var_indices
            .iter()
            .all(|&i| assignment[i].is_some());
        if !all_assigned {
            return true; // Can't evaluate yet
        }
        let vals: Vec<f64> = c.var_indices.iter().map(|&i| assignment[i].unwrap()).collect();
        evaluate_constraint(&c.relation, &c.params, &vals)
    })
}

fn evaluate_constraint(rel: &ConstraintRelation, params: &[f64], vals: &[f64]) -> bool {
    if vals.is_empty() {
        return true;
    }
    match rel {
        ConstraintRelation::LessThan => vals[0] < params.first().copied().unwrap_or(f64::MAX),
        ConstraintRelation::Equal => {
            vals.windows(2).all(|w| (w[0] - w[1]).abs() < f64::EPSILON)
        }
        ConstraintRelation::NotEqual => vals
            .windows(2)
            .all(|w| (w[0] - w[1]).abs() >= f64::EPSILON),
        ConstraintRelation::SumEquals => {
            let sum: f64 = vals.iter().sum();
            let target = params.first().copied().unwrap_or(0.0);
            (sum - target).abs() < f64::EPSILON * vals.len() as f64
        }
        ConstraintRelation::AllDifferent => {
            let mut seen = std::collections::HashSet::new();
            vals.iter().all(|v| seen.insert(v.to_bits()))
        }
        ConstraintRelation::Custom(_code) => true, // User-defined
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_simple_instance() -> CspInstance {
        CspInstance {
            id: 1,
            variables: vec!["x".into(), "y".into()],
            domains: vec![vec![1.0, 2.0, 3.0], vec![1.0, 2.0, 3.0]],
            constraints: vec![CspConstraint {
                var_indices: vec![0, 1],
                relation: ConstraintRelation::NotEqual,
                params: vec![],
            }],
        }
    }

    #[test]
    fn solve_simple() {
        let inst = make_simple_instance();
        let result = backtrack_solve(&inst);
        assert!(result.is_some());
        let assign = result.unwrap();
        assert_eq!(assign.len(), 2);
        // x != y
        assert_ne!(assign[0].1, assign[1].1);
    }

    #[tokio::test]
    async fn batch_solve_cpu() {
        let dispatcher = std::sync::Arc::new(GpuDispatcher::new(false, 0, 4));
        let solver = BatchCspSolver::new(dispatcher);
        let instances: Vec<CspInstance> = (0..10)
            .map(|i| CspInstance {
                id: i,
                variables: vec!["a".into(), "b".into()],
                domains: vec![vec![1.0, 2.0], vec![1.0, 2.0]],
                constraints: vec![CspConstraint {
                    var_indices: vec![0, 1],
                    relation: ConstraintRelation::AllDifferent,
                    params: vec![],
                }],
            })
            .collect();
        let results = solver.solve_batch(&instances).await;
        assert_eq!(results.len(), 10);
        assert!(results.iter().all(|r| r.satisfied));
    }
}
