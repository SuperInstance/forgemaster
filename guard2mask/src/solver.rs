//! CSP solver for constraint satisfaction (stub — full AC-3 solver in development)

use crate::types::*;

/// Solve constraints and produce a variable assignment
pub fn solve(constraints: &[Constraint]) -> Result<Assignment, String> {
    // TODO: AC-3 + backtracking with BitmaskDomain
    let mut assignment = Assignment::new();
    for c in constraints {
        for check in &c.checks {
            match check {
                Check::Range { var, min, max } => {
                    // Assign positive weight for variables in range
                    if *min <= 0 && *max >= 0 {
                        assignment.values.insert(var.clone(), TernaryWeight::Zero);
                    }
                }
                _ => {}
            }
        }
    }
    Ok(assignment)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn solve_empty() {
        let result = solve(&[]);
        assert!(result.is_ok());
    }
}
