use super::{parser, ConstraintProblem};

/// Generic constraint parser.
/// Handles comparison operators, bounds, and simple numeric constraints.
pub fn parse(claim: &str) -> Result<ConstraintProblem, String> {
    let lower = claim.to_lowercase();
    let original = claim.to_string();

    // Try to parse as a comparison: "X is greater than Y", "X > Y", "X is at least Y"
    if let Some((left, op, right, _desc)) = parser::extract_comparison(&lower) {
        return Ok(ConstraintProblem {
            domain: "generic".into(),
            variables: vec![
                super::Variable {
                    name: "left".into(),
                    value: left,
                    desc: "left operand".into(),
                },
                super::Variable {
                    name: "right".into(),
                    value: right,
                    desc: "right operand".into(),
                },
            ],
            constraints: vec![super::Constraint::GenericCompare {
                left,
                operator: op.clone(),
                right,
                desc: original.clone(),
            }],
            assertion: super::Assertion {
                assertion_type: op,
                expected: right,
                actual_expr: original,
            },
        });
    }

    // Try to parse as a range check: "X is between Y and Z", "X is within [Y, Z]"
    if let Some((value, min, max, _desc)) = parser::extract_range_check(&lower) {
        return Ok(ConstraintProblem {
            domain: "generic".into(),
            variables: vec![
                super::Variable {
                    name: "value".into(),
                    value,
                    desc: "value".into(),
                },
                super::Variable {
                    name: "min".into(),
                    value: min,
                    desc: "minimum bound".into(),
                },
                super::Variable {
                    name: "max".into(),
                    value: max,
                    desc: "maximum bound".into(),
                },
            ],
            constraints: vec![super::Constraint::GenericRangeCheck {
                value,
                min,
                max,
                desc: original.clone(),
            }],
            assertion: super::Assertion {
                assertion_type: "in_range".into(),
                expected: 0.0,
                actual_expr: original,
            },
        });
    }

    // Try to parse as a simple bound: "X is within Y of Z"
    if let Some((value, min, max, _desc)) = parser::extract_bound(&lower) {
        return Ok(ConstraintProblem {
            domain: "generic".into(),
            variables: vec![
                super::Variable {
                    name: "value".into(),
                    value,
                    desc: "value".into(),
                },
                super::Variable {
                    name: "min".into(),
                    value: min,
                    desc: "minimum".into(),
                },
                super::Variable {
                    name: "max".into(),
                    value: max,
                    desc: "maximum".into(),
                },
            ],
            constraints: vec![super::Constraint::GenericBound {
                value,
                min,
                max,
                desc: original.clone(),
            }],
            assertion: super::Assertion {
                assertion_type: "in_range".into(),
                expected: 0.0,
                actual_expr: original,
            },
        });
    }

    Err("Could not parse claim as a generic constraint. Try: 'X is greater than Y', 'X is between Y and Z', or 'X > Y'".into())
}
