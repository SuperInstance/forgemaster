use crate::types::*;
use hashbrown::{HashMap, HashSet};
use itertools::Itertools;
use rand::prelude::*;

// ------------------------------
// Optimization Objective
// ------------------------------
#[derive(Clone, Debug)]
pub enum Objective {
    MinimizeNonZeros,
    MaximizeSum,
    None,
}

// ------------------------------
// GAC-3 Constraint Propagation
// ------------------------------
fn gac_propagate(
    cs: &ConstraintSystem,
    domains: &mut HashMap<VarId, BitmaskDomain>,
    assignment: &PartialAssignment,
) -> Result<(), Guard2MaskError> {
    let mut worklist: Vec<&Constraint> = cs.constraints.iter().collect();
    let var_indices: HashMap<VarId, usize> = cs.variables.keys().enumerate().map(|(i, &v)| (v, i)).collect();

    while let Some(constraint) = worklist.pop() {
        // Get all variables affected by this constraint
        let vars = get_constraint_vars(constraint, cs.width, cs.height);
        
        for &var in &vars {
            if assignment.0.contains_key(&var) { continue; }
            let old_domain = domains[&var];
            let mut new_domain = 0;

            // Test each possible value for var to see if it's consistent with the constraint
            for val in old_domain.values() {
                let mut temp_assignment = assignment.clone();
                temp_assignment.0.insert(var, val);
                
                // Check if there exists a valid assignment to other vars that satisfies the constraint
                if is_consistent(constraint, &temp_assignment, domains, &vars) {
                    new_domain |= val.mask();
                }
            }

            if new_domain.is_empty() {
                return Err(Guard2MaskError::NoSolutionError(
                    format!("Domain empty for variable {:?}", var)
                ));
            }

            if new_domain != old_domain {
                domains.insert(var, new_domain);
                // Add all constraints involving this var back to the worklist
                for c in &cs.constraints {
                    if get_constraint_vars(c, cs.width, cs.height).contains(&var) {
                        worklist.push(c);
                    }
                }
            }
        }
    }
    Ok(())
}

// ------------------------------
// Backtracking Search with MRV Heuristic
// ------------------------------
pub fn solve_csp(
    cs: &ConstraintSystem,
    objective: Objective,
) -> Result<Assignment, Guard2MaskError> {
    let mut domains: HashMap<VarId, BitmaskDomain> = cs.variables.iter().map(|(&k, v)| (k, v.domain)).collect();
    let mut best_assignment: Option<Assignment> = None;
    let mut rng = SmallRng::seed_from_u64(42); // Deterministic for reproducibility

    fn backtrack(
        cs: &ConstraintSystem,
        mut assignment: PartialAssignment,
        mut domains: HashMap<VarId, BitmaskDomain>,
        objective: &Objective,
        best: &mut Option<Assignment>,
        rng: &mut SmallRng,
    ) -> Result<(), Guard2MaskError> {
        // Propagate constraints first
        if gac_propagate(cs, &mut domains, &assignment).is_err() {
            return Ok(());
        }

        // Check if assignment is complete
        if assignment.0.len() == cs.variables.len() {
            let full_assignment = Assignment(assignment.0.iter().map(|(&k, &v)| (k, v)).collect());
            if is_better(&full_assignment, best.as_ref(), objective) {
                *best = Some(full_assignment);
            }
            return Ok(());
        }

        // Select unassigned variable with MRV heuristic
        let var = *domains
            .iter()
            .filter(|(v, _)| !assignment.0.contains_key(v))
            .min_by_key(|(_, d)| d.len())
            .ok_or_else(|| Guard2MaskError::NoSolutionError("No variables left".to_string()))?
            .0;

        // Try values in random order (for optimization)
        let mut values: Vec<TernaryWeight> = domains[&var].values();
        values.shuffle(rng);

        for val in values {
            assignment.0.insert(var, val);
            backtrack(cs, assignment.clone(), domains.clone(), objective, best, rng)?;
            assignment.0.remove(&var);
        }

        Ok(())
    }

    backtrack(cs, PartialAssignment(HashMap::new()), domains, &objective, &mut best_assignment, &mut rng)?;

    best_assignment.ok_or_else(|| Guard2MaskError::NoSolutionError("No valid assignment found".to_string()))
}

// ------------------------------
// Helper Functions (Simplified)
// ------------------------------
type PartialAssignment = HashMap<VarId, TernaryWeight>;

fn get_constraint_vars(constraint: &Constraint, width: u32, height: u32) -> Vec<VarId> {
    match constraint {
        Constraint::Range { scope, .. } | Constraint::Thermal { scope, .. } | Constraint::Sparsity { scope, .. } | Constraint::Custom { scope, .. } => {
            match scope {
                Scope::Global => (0..height).cartesian_product(0..width).map(|(y, x)| (x, y)).collect(),
                Scope::Row(y) => (0..width).map(|x| (x, *y)).collect(),
                Scope::Column(x) => (0..height).map(|y| (*x, y)).collect(),
                Scope::Region { x0, x1, y0, y1 } => (*y0..*y1).cartesian_product(*x0..*x1).map(|(y, x)| (x, y)).collect(),
                _ => vec![], // Expanded earlier in constraint system creation
            }
        }
    }
}

fn is_consistent(
    constraint: &Constraint,
    assignment: &PartialAssignment,
    _domains: &HashMap<VarId, BitmaskDomain>,
    _vars: &[VarId],
) -> bool {
    // Simplified: check if partial assignment doesn't violate the constraint
    match constraint {
        Constraint::Sparsity { max_non_zero_ratio, .. } => {
            let total = assignment.len();
            let non_zero = assignment.values().filter(|&&v| v != TernaryWeight::Zero).count();
            total == 0 || (non_zero as f32 / total as f32) <= *max_non_zero_ratio + 0.001 // Epsilon for floating point
        }
        Constraint::Range { min_sum, max_sum, .. } => {
            let sum: i32 = assignment.values().map(|&v| v.to_i32()).sum();
            sum >= *min_sum && sum <= *max_sum
        }
        // Add other constraint checks
        _ => true,
    }
}

fn is_better(new: &Assignment, best: Option<&Assignment>, objective: &Objective) -> bool {
    match objective {
        Objective::MinimizeNonZeros => {
            let new_nonzeros = new.0.values().filter(|&&v| v != TernaryWeight::Zero).count();
            best.map_or(true, |b| {
                let b_nonzeros = b.0.values().filter(|&&v| v != TernaryWeight::Zero).count();
                new_nonzeros < b_nonzeros
            })
        }
        Objective::MaximizeSum => {
            let new_sum: i32 = new.0.values().map(|&v| v.to_i32()).sum();
            best.map_or(true, |b| {
                let b_sum: i32 = b.0.values().map(|&v| v.to_i32()).sum();
                new_sum > b_sum
            })
        }
        Objective::None => true,
    }
}
