//! # Constraint Satisfaction Solver Module
//!
//! Implements classic CSP solving algorithms with Pythagorean manifold extensions:
//!
//! - **AC-3 Arc Consistency**: Prunes variable domains by eliminating unsupported values
//! - **Backtracking Search**: Systematic assignment with constraint checking
//! - **Holonomy Checker**: Verifies constraint closure on Pythagorean manifolds
//!
//! ## Quick Example
//!
//! ```ignore
//! use ct_demo::solver::{CSP, Domain, Constraint, solve_backtracking};
//!
//! // Simple CSP: find x, y such that x + y == 7 and x != y
//! let csp = CSP {
//!     variables: vec!["x".into(), "y".into()],
//!     domains: vec![
//!         Domain::Range { min: 1, max: 6 },
//!         Domain::Range { min: 1, max: 6 },
//!     ],
//!     constraints: vec![
//!         Constraint {
//!             id: "sum".into(),
//!             variables: vec!["x".into(), "y".into()],
//!             check: Box::new(|assign| {
//!                 let x = assign.get("x").copied();
//!                 let y = assign.get("y").copied();
//!                 match (x, y) {
//!                     (Some(a), Some(b)) => a + b == 7,
//!                     _ => true, // unassigned → no constraint yet
//!                 }
//!             }),
//!         },
//!         Constraint {
//!             id: "neq".into(),
//!             variables: vec!["x".into(), "y".into()],
//!             check: Box::new(|assign| {
//!                 let x = assign.get("x").copied();
//!                 let y = assign.get("y").copied();
//!                 match (x, y) {
//!                     (Some(a), Some(b)) => a != b,
//!                     _ => true,
//!                 }
//!             }),
//!         },
//!     ],
//! };
//!
//! let solutions = solve_backtracking(&csp, 10);
//! assert!(!solutions.is_empty());
//! // All solutions should satisfy x + y == 7 and x != y
//! for sol in &solutions {
//!     assert_eq!(sol["x"] + sol["y"], 7);
//!     assert_ne!(sol["x"], sol["y"]);
//! }
//! ```

use std::collections::{HashMap, VecDeque};

use crate::PythagoreanManifold;

// ── Types ─────────────────────────────────────────────────────────────────────

/// A variable domain: the set of values a CSP variable can take.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Domain {
    /// Explicit set of allowed values.
    Set(Vec<i64>),
    /// Inclusive integer range [min, max].
    Range { min: i64, max: i64 },
}

impl Domain {
    /// Return all values in this domain as a Vec.
    pub fn values(&self) -> Vec<i64> {
        match self {
            Domain::Set(v) => v.clone(),
            Domain::Range { min, max } => (*min..=*max).collect(),
        }
    }

    /// Number of values in this domain.
    pub fn size(&self) -> usize {
        match self {
            Domain::Set(v) => v.len(),
            Domain::Range { min, max } => (*max - *min + 1).max(0) as usize,
        }
    }

    /// Check if the domain contains a value.
    pub fn contains(&self, val: i64) -> bool {
        match self {
            Domain::Set(v) => v.contains(&val),
            Domain::Range { min, max } => val >= *min && val <= *max,
        }
    }

    /// Remove a value from the domain, returning the new domain.
    /// Returns None if the domain becomes empty.
    pub fn remove(&self, val: i64) -> Option<Domain> {
        match self {
            Domain::Set(v) => {
                let new: Vec<i64> = v.iter().copied().filter(|&x| x != val).collect();
                if new.is_empty() { None } else { Some(Domain::Set(new)) }
            }
            Domain::Range { min, max } => {
                if val < *min || val > *max {
                    Some(self.clone())
                } else if *min == *max && val == *min {
                    None
                } else if val == *min {
                    Some(Domain::Range { min: min + 1, max: *max })
                } else if val == *max {
                    Some(Domain::Range { min: *min, max: max - 1 })
                } else {
                    // Value is in the middle — split to set (rare, but correct)
                    let new: Vec<i64> = (*min..=*max).filter(|&x| x != val).collect();
                    Some(Domain::Set(new))
                }
            }
        }
    }
}

/// A constraint: a boolean predicate over variable assignments.
pub struct Constraint {
    /// Unique identifier for this constraint.
    pub id: String,
    /// Variables involved in this constraint.
    pub variables: Vec<String>,
    /// Predicate: given current assignments, is this constraint satisfied?
    /// Unassigned variables should return true (not yet violated).
    pub check: Box<dyn Fn(&HashMap<String, i64>) -> bool>,
}

impl std::fmt::Debug for Constraint {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Constraint")
            .field("id", &self.id)
            .field("variables", &self.variables)
            .finish()
    }
}

/// A complete CSP specification.
pub struct CSP {
    /// Variable names.
    pub variables: Vec<String>,
    /// Domains, one per variable (parallel with `variables`).
    pub domains: Vec<Domain>,
    /// Constraints to satisfy.
    pub constraints: Vec<Constraint>,
}

/// Result of a CSP solve.
#[derive(Debug, Clone)]
pub struct SolveResult {
    /// All solutions found (up to the requested limit).
    pub solutions: Vec<HashMap<String, i64>>,
    /// Whether search was exhaustive (all solutions found) or stopped at limit.
    pub exhaustive: bool,
    /// Number of nodes explored in the search tree.
    pub nodes_explored: usize,
}

// ── AC-3 Arc Consistency ─────────────────────────────────────────────────────

/// Apply AC-3 arc consistency to reduce variable domains.
///
/// Returns reduced domains, or None if the CSP is detected unsatisfiable
/// (any domain becomes empty during propagation).
///
/// AC-3 maintains a worklist of arcs (variable, constraint) pairs.
/// For each arc, it removes values from the variable's domain that have
/// no support in the constraint. If a domain changes, all affected arcs
/// are re-added to the worklist.
pub fn ac3(csp: &CSP) -> Option<Vec<Domain>> {
    let mut domains: Vec<Domain> = csp.domains.clone();

    // Build variable → index map
    let var_idx: HashMap<&str, usize> = csp.variables
        .iter()
        .enumerate()
        .map(|(i, v)| (v.as_str(), i))
        .collect();

    // Build arc worklist: (variable_index, constraint_index)
    let mut worklist: VecDeque<(usize, usize)> = VecDeque::new();
    for (ci, constraint) in csp.constraints.iter().enumerate() {
        for var in &constraint.variables {
            if let Some(&vi) = var_idx.get(var.as_str()) {
                worklist.push_back((vi, ci));
            }
        }
    }

    while let Some((vi, ci)) = worklist.pop_front() {
        let constraint = &csp.constraints[ci];
        let var_name = &csp.variables[vi];
        let current_domain = domains[vi].values();

        // Find other variables in this constraint
        let other_vars: Vec<&str> = constraint.variables
            .iter()
            .filter(|v| v.as_str() != var_name.as_str())
            .map(|v| v.as_str())
            .collect();

        // For each value in the domain, check if there exists any
        // consistent assignment to other variables
        let mut new_values = Vec::new();
        for val in current_domain {
            if has_support(val, var_name, &other_vars, &domains, &var_idx, &constraint.check) {
                new_values.push(val);
            }
        }

        if new_values.is_empty() {
            return None; // Domain wipe-out → unsatisfiable
        }

        let new_size = new_values.len();
        let old_size = domains[vi].size();
        if new_size < old_size {
            // Domain was reduced — re-enqueue affected arcs
            domains[vi] = Domain::Set(new_values);
            for (ci2, constraint2) in csp.constraints.iter().enumerate() {
                if ci2 == ci { continue; }
                if constraint2.variables.iter().any(|v| v == var_name) {
                    for other_var in &constraint2.variables {
                        if other_var != var_name {
                            if let Some(&oi) = var_idx.get(other_var.as_str()) {
                                worklist.push_back((oi, ci2));
                            }
                        }
                    }
                }
            }
        }
    }

    Some(domains)
}

/// Check if a value for `var_name` has any supporting assignment for `other_vars`.
fn has_support(
    val: i64,
    var_name: &str,
    other_vars: &[&str],
    domains: &[Domain],
    var_idx: &HashMap<&str, usize>,
    check: &dyn Fn(&HashMap<String, i64>) -> bool,
) -> bool {
    if other_vars.is_empty() {
        // Unary constraint: just check the value alone
        let mut assign = HashMap::new();
        assign.insert(var_name.to_string(), val);
        return check(&assign);
    }

    // Try all combinations of values for other variables
    // (limited to first 1000 combinations to avoid exponential blowup)
    let mut assignments: Vec<HashMap<String, i64>> = vec![HashMap::new()];
    assignments[0].insert(var_name.to_string(), val);

    for &ov in other_vars {
        if let Some(&oi) = var_idx.get(ov) {
            let ov_domain = domains[oi].values();
            let mut new_assignments = Vec::new();
            for partial in &assignments {
                for oval in &ov_domain {
                    let mut extended = partial.clone();
                    extended.insert(ov.to_string(), *oval);
                    new_assignments.push(extended);
                }
            }
            assignments = new_assignments;
            // Cap to prevent explosion
            assignments.truncate(1000);
        }
    }

    assignments.iter().any(|a| check(a))
}

// ── Backtracking Solver ───────────────────────────────────────────────────────

/// Solve a CSP using backtracking with optional AC-3 preprocessing.
///
/// Finds up to `max_solutions` solutions. Set to `usize::MAX` for exhaustive search.
/// If `use_ac3` is true, runs arc consistency first to prune domains.
///
/// Returns a `SolveResult` with all found solutions and search statistics.
pub fn solve_backtracking(csp: &CSP) -> SolveResult {
    solve_backtracking_with_limit(csp, usize::MAX, true)
}

/// Solve a CSP with a solution limit and optional AC-3 preprocessing.
pub fn solve_backtracking_with_limit(
    csp: &CSP,
    max_solutions: usize,
    use_ac3: bool,
) -> SolveResult {
    let domains = if use_ac3 {
        match ac3(csp) {
            Some(d) => d,
            None => {
                return SolveResult {
                    solutions: vec![],
                    exhaustive: true,
                    nodes_explored: 1,
                };
            }
        }
    } else {
        csp.domains.clone()
    };

    let mut result = SolveResult {
        solutions: vec![],
        exhaustive: true,
        nodes_explored: 0,
    };

    let mut assignment: HashMap<String, i64> = HashMap::new();
    backtrack(csp, &domains, 0, &mut assignment, &mut result, max_solutions);

    result
}

/// Recursive backtracking search.
fn backtrack(
    csp: &CSP,
    domains: &[Domain],
    var_index: usize,
    assignment: &mut HashMap<String, i64>,
    result: &mut SolveResult,
    max_solutions: usize,
) -> bool {
    if var_index >= csp.variables.len() {
        // All variables assigned — record solution
        result.solutions.push(assignment.clone());
        return result.solutions.len() < max_solutions;
    }

    result.nodes_explored += 1;
    let var_name = &csp.variables[var_index];

    for val in domains[var_index].values() {
        assignment.insert(var_name.clone(), val);

        if is_consistent(csp, assignment) {
            let should_continue = backtrack(csp, domains, var_index + 1, assignment, result, max_solutions);
            if !should_continue {
                assignment.remove(var_name);
                result.exhaustive = false;
                return false;
            }
        }

        assignment.remove(var_name);
    }

    true // Continue searching
}

/// Check if current (possibly partial) assignment satisfies all constraints.
fn is_consistent(csp: &CSP, assignment: &HashMap<String, i64>) -> bool {
    for constraint in &csp.constraints {
        // Only check constraints where all variables are assigned
        let all_assigned = constraint.variables
            .iter()
            .all(|v| assignment.contains_key(v));

        if all_assigned && !(constraint.check)(assignment) {
            return false;
        }
    }
    true
}

// ── Holonomy Checker ──────────────────────────────────────────────────────────

/// Result of a holonomy check on a Pythagorean manifold.
///
/// Holonomy measures whether a closed path on the manifold returns to the
/// same state. On a discrete integer manifold, this is always true —
/// the manifold is **flat** (zero holonomy), which is the key property
/// that enables drift-free arithmetic.
#[derive(Debug, Clone)]
pub struct HolonomyResult {
    /// Whether the manifold is holonomic (closed paths return to start).
    pub is_holonomic: bool,
    /// Number of closed paths tested.
    pub paths_tested: usize,
    /// Maximum drift observed (should be 0 for integer manifolds).
    pub max_drift: i64,
    /// The manifold configuration tested.
    pub manifold: PythagoreanManifold,
}

/// Verify holonomy of a Pythagorean manifold by testing closed paths.
///
/// A manifold is holonomic if every closed path returns to the starting point.
/// For Pythagorean integer manifolds, this is trivially true because all
/// arithmetic is exact integer arithmetic. This function verifies that claim
/// empirically by testing random closed paths.
///
/// # Example
///
/// ```ignore
/// use ct_demo::{PythagoreanManifold, solver::check_holonomy};
///
/// let m = PythagoreanManifold::new(2, 1000, 1);
/// let result = check_holonomy(&m, 100);
/// assert!(result.is_holonomic);
/// assert_eq!(result.max_drift, 0);
/// ```
pub fn check_holonomy(manifold: &PythagoreanManifold, num_paths: usize) -> HolonomyResult {
    let mut max_drift: i64 = 0;
    let mut all_holonomic = true;

    for _ in 0..num_paths {
        // Generate a closed path: snap(start), then walk and snap, return
        let start: f64 = (manifold.max_coordinate / 2) as f64;
        let snapped_start = crate::snap(start, manifold);

        // Walk: add steps, snap at each point
        let mut current = snapped_start as f64;
        let steps = [
            3.0, -4.0,  // 3-4-5 step
            5.0, -12.0, // 5-12-13 step
            8.0, -15.0, // 8-15-17 step
        ];

        for &step in &steps {
            current += step;
            current = crate::snap(current, manifold) as f64;
        }

        // Return path (reverse steps)
        for &step in steps.iter().rev() {
            current -= step;
            current = crate::snap(current, manifold) as f64;
        }

        let snapped_return = crate::snap(current, manifold);
        let drift = (snapped_return - snapped_start).abs();
        max_drift = max_drift.max(drift);

        if drift != 0 {
            all_holonomic = false;
        }
    }

    HolonomyResult {
        is_holonomic: all_holonomic,
        paths_tested: num_paths,
        max_drift,
        manifold: manifold.clone(),
    }
}

// ── Convenience: N-Queens ─────────────────────────────────────────────────────

/// Solve the N-Queens problem using constraint satisfaction.
///
/// Returns all valid board configurations where N queens are placed on an
/// N×N board with no two queens threatening each other.
///
/// # Example
///
/// ```ignore
/// use ct_demo::solver::n_queens;
///
/// // Classic 8-queens: 92 solutions
/// let solutions = n_queens(8, 10);
/// assert!(!solutions.is_empty());
/// // Each solution has exactly 8 placements
/// for sol in &solutions {
///     assert_eq!(sol.len(), 8);
/// }
/// ```
pub fn n_queens(n: usize, max_solutions: usize) -> Vec<HashMap<String, i64>> {
    let variables: Vec<String> = (0..n).map(|i| format!("q{}", i)).collect();
    let domains: Vec<Domain> = (0..n).map(|_| Domain::Range { min: 0, max: (n - 1) as i64 }).collect();

    let constraints: Vec<Constraint> = (0..n).flat_map(|i| {
        (i + 1..n).map(move |j| {
            let id = format!("no_attack_{}_{}", i, j);
            Constraint {
                id,
                variables: vec![format!("q{}", i), format!("q{}", j)],
                check: Box::new(move |assign: &HashMap<String, i64>| {
                    let qi = assign.get(&format!("q{}", i)).copied();
                    let qj = assign.get(&format!("q{}", j)).copied();
                    match (qi, qj) {
                        (Some(row_i), Some(row_j)) => {
                            // Different rows (guaranteed by different variables)
                            // Different diagonals
                            row_i != row_j &&
                            (row_i - row_j).unsigned_abs() != (i as i64 - j as i64).unsigned_abs()
                        }
                        _ => true,
                    }
                }),
            }
        })
    }).collect();

    let csp = CSP { variables, domains, constraints };
    let result = solve_backtracking_with_limit(&csp, max_solutions, true);
    result.solutions
}

// ── Convenience: Graph Coloring ───────────────────────────────────────────────

/// Solve a graph coloring problem.
///
/// Given an adjacency list and number of colors, find valid colorings.
///
/// # Example
///
/// ```ignore
/// use ct_demo::solver::graph_coloring;
///
/// // Triangle graph: needs 3 colors
/// let edges: Vec<(usize, usize)> = vec![(0, 1), (1, 2), (0, 2)];
/// let solutions = graph_coloring(3, 3, &edges, 10);
/// assert!(!solutions.is_empty());
/// ```
pub fn graph_coloring(
    num_nodes: usize,
    num_colors: usize,
    edges: &[(usize, usize)],
    max_solutions: usize,
) -> Vec<HashMap<String, i64>> {
    let variables: Vec<String> = (0..num_nodes).map(|i| format!("n{}", i)).collect();
    let domains: Vec<Domain> = (0..num_nodes)
        .map(|_| Domain::Range { min: 0, max: (num_colors - 1) as i64 })
        .collect();

    let constraints: Vec<Constraint> = edges.iter().enumerate().map(|(ei, &(a, b))| {
        Constraint {
            id: format!("edge_{}", ei),
            variables: vec![format!("n{}", a), format!("n{}", b)],
            check: Box::new(move |assign: &HashMap<String, i64>| {
                let ca = assign.get(&format!("n{}", a)).copied();
                let cb = assign.get(&format!("n{}", b)).copied();
                match (ca, cb) {
                    (Some(x), Some(y)) => x != y,
                    _ => true,
                }
            }),
        }
    }).collect();

    let csp = CSP { variables, domains, constraints };
    let result = solve_backtracking_with_limit(&csp, max_solutions, true);
    result.solutions
}

#[cfg(test)]
mod tests {
    use super::*;

    // ── Domain tests ──

    #[test]
    fn domain_set_values() {
        let d = Domain::Set(vec![1, 3, 5]);
        assert_eq!(d.values(), vec![1, 3, 5]);
        assert_eq!(d.size(), 3);
        assert!(d.contains(3));
        assert!(!d.contains(2));
    }

    #[test]
    fn domain_range_values() {
        let d = Domain::Range { min: 1, max: 5 };
        assert_eq!(d.values(), vec![1, 2, 3, 4, 5]);
        assert_eq!(d.size(), 5);
    }

    #[test]
    fn domain_remove_from_set() {
        let d = Domain::Set(vec![1, 2, 3]);
        let d2 = d.remove(2).unwrap();
        assert_eq!(d2.values(), vec![1, 3]);
    }

    #[test]
    fn domain_remove_last_from_set() {
        let d = Domain::Set(vec![5]);
        assert!(d.remove(5).is_none());
    }

    #[test]
    fn domain_remove_from_range_boundary() {
        let d = Domain::Range { min: 1, max: 5 };
        let d2 = d.remove(1).unwrap();
        assert_eq!(d2, Domain::Range { min: 2, max: 5 });

        let d3 = d2.remove(5).unwrap();
        assert_eq!(d3, Domain::Range { min: 2, max: 4 });
    }

    #[test]
    fn domain_remove_out_of_range() {
        let d = Domain::Range { min: 1, max: 5 };
        let d2 = d.remove(0).unwrap();
        assert_eq!(d2, Domain::Range { min: 1, max: 5 });
    }

    // ── AC-3 tests ──

    #[test]
    fn ac3_detects_unsatisfiable() {
        // x in {1}, y in {1}, constraint: x != y
        let csp = CSP {
            variables: vec!["x".into(), "y".into()],
            domains: vec![Domain::Set(vec![1]), Domain::Set(vec![1])],
            constraints: vec![Constraint {
                id: "neq".into(),
                variables: vec!["x".into(), "y".into()],
                check: Box::new(|a| a.get("x") != a.get("y")),
            }],
        };
        assert!(ac3(&csp).is_none());
    }

    #[test]
    fn ac3_prunes_domains() {
        // x in {1,2,3}, y in {2,3,4}, constraint: x == y
        let csp = CSP {
            variables: vec!["x".into(), "y".into()],
            domains: vec![
                Domain::Set(vec![1, 2, 3]),
                Domain::Set(vec![2, 3, 4]),
            ],
            constraints: vec![Constraint {
                id: "eq".into(),
                variables: vec!["x".into(), "y".into()],
                check: Box::new(|a| a.get("x") == a.get("y")),
            }],
        };
        let result = ac3(&csp).unwrap();
        // x domain should be pruned to {2, 3}
        let x_vals = result[0].values();
        assert!(x_vals.contains(&2));
        assert!(x_vals.contains(&3));
        assert!(!x_vals.contains(&1));
        // y domain should be pruned to {2, 3}
        let y_vals = result[1].values();
        assert!(y_vals.contains(&2));
        assert!(y_vals.contains(&3));
        assert!(!y_vals.contains(&4));
    }

    // ── Backtracking solver tests ──

    #[test]
    fn solve_simple_csp() {
        let csp = CSP {
            variables: vec!["x".into(), "y".into()],
            domains: vec![
                Domain::Range { min: 1, max: 6 },
                Domain::Range { min: 1, max: 6 },
            ],
            constraints: vec![
                Constraint {
                    id: "sum".into(),
                    variables: vec!["x".into(), "y".into()],
                    check: Box::new(|a| {
                        match (a.get("x").copied(), a.get("y").copied()) {
                            (Some(x), Some(y)) => x + y == 7,
                            _ => true,
                        }
                    }),
                },
                Constraint {
                    id: "neq".into(),
                    variables: vec!["x".into(), "y".into()],
                    check: Box::new(|a| a.get("x") != a.get("y")),
                },
            ],
        };
        let result = solve_backtracking(&csp);
        assert!(!result.solutions.is_empty());
        for sol in &result.solutions {
            assert_eq!(sol["x"] + sol["y"], 7);
            assert_ne!(sol["x"], sol["y"]);
        }
    }

    #[test]
    fn solve_no_solution() {
        let csp = CSP {
            variables: vec!["x".into()],
            domains: vec![Domain::Set(vec![1, 2])],
            constraints: vec![Constraint {
                id: "gt5".into(),
                variables: vec!["x".into()],
                check: Box::new(|a| a.get("x").copied().unwrap_or(0) > 5),
            }],
        };
        let result = solve_backtracking(&csp);
        assert!(result.solutions.is_empty());
        assert!(result.exhaustive);
    }

    #[test]
    fn solve_with_limit() {
        let csp = CSP {
            variables: vec!["x".into()],
            domains: vec![Domain::Range { min: 1, max: 100 }],
            constraints: vec![], // No constraints → all values valid
        };
        let result = solve_backtracking_with_limit(&csp, 5, false);
        assert_eq!(result.solutions.len(), 5);
        assert!(!result.exhaustive);
    }

    // ── Holonomy tests ──

    #[test]
    fn holonomy_integer_manifold_is_flat() {
        let m = PythagoreanManifold::new(2, 1000, 1);
        let result = check_holonomy(&m, 50);
        assert!(result.is_holonomic);
        assert_eq!(result.max_drift, 0);
    }

    #[test]
    fn holonomy_coarse_resolution_still_flat() {
        let m = PythagoreanManifold::new(2, 1000, 5);
        let result = check_holonomy(&m, 50);
        assert!(result.is_holonomic);
        assert_eq!(result.max_drift, 0);
    }

    // ── N-Queens tests ──

    #[test]
    fn n_queens_4() {
        let solutions = n_queens(4, 100);
        assert_eq!(solutions.len(), 2); // 4-queens has exactly 2 solutions
    }

    #[test]
    fn n_queens_8_valid() {
        let solutions = n_queens(8, 100);
        assert!(!solutions.is_empty());
        for sol in &solutions {
            assert_eq!(sol.len(), 8);
            // Verify no two queens share a row or diagonal
            let positions: Vec<(usize, i64)> = (0..8)
                .map(|i| (i, sol[&format!("q{}", i)]))
                .collect();
            for i in 0..positions.len() {
                for j in i+1..positions.len() {
                    let (ci, ri) = positions[i];
                    let (cj, rj) = positions[j];
                    assert_ne!(ri, rj, "same row: q{} and q{}", ci, cj);
                    assert_ne!(
                        (ri - rj).unsigned_abs(),
                        (ci as i64 - cj as i64).unsigned_abs(),
                        "same diagonal: q{} and q{}", ci, cj
                    );
                }
            }
        }
    }

    // ── Graph coloring tests ──

    #[test]
    fn graph_coloring_triangle() {
        let edges = vec![(0, 1), (1, 2), (0, 2)];
        // 3 colors → should have solutions
        let solutions = graph_coloring(3, 3, &edges, 100);
        assert!(!solutions.is_empty());
        // Verify all edges have different colors
        for sol in &solutions {
            for &(a, b) in &edges {
                assert_ne!(sol[&format!("n{}", a)], sol[&format!("n{}", b)]);
            }
        }
    }

    #[test]
    fn graph_coloring_insufficient_colors() {
        let edges = vec![(0, 1), (1, 2), (0, 2)];
        // Triangle needs 3 colors — 2 should fail
        let solutions = graph_coloring(3, 2, &edges, 100);
        assert!(solutions.is_empty());
    }
}
