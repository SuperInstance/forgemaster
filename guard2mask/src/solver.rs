//! CSP solver for constraint satisfaction

use crate::types::*;
use crate::parser::{Constraint, Check};

/// Solve constraints and produce a variable assignment (stub)
pub fn solve(constraints: &[Constraint]) -> Result<Assignment, String> {
    let mut assignment = Assignment::new();
    for c in constraints {
        for check in &c.checks {
            match check {
                Check::Range { start, end } => {
                    if *start <= 0.0 && *end >= 0.0 {
                        assignment.values.insert(format!("range_{}", c.name), TernaryWeight::Zero);
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
    use crate::parser::Priority;

    #[test]
    fn solve_empty() {
        let result = solve(&[]);
        assert!(result.is_ok());
    }

    #[test]
    fn solve_range() {
        let constraints = vec![Constraint {
            name: "altitude".to_string(),
            priority: Priority::Hard,
            checks: vec![Check::Range { start: 0.0, end: 15000.0 }],
        }];
        let result = solve(&constraints).unwrap();
        assert!(result.values.contains_key("range_altitude"));
    }
}
