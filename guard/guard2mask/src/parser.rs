//! GUARD DSL parser
//!
//! Parses constraint definitions like:
//! ```guard
//! constraint eVTOL_altitude @priority(HARD) {
//!     range(0, 15000)
//!     whitelist(HOVER, ASCEND, DESCEND)
//!     bitmask(0x3F)
//!     thermal(2.5)
//!     sparsity(128)
//! }
//! ```

use std::fmt;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Priority {
    Hard,
    Soft,
    Default,
}

#[derive(Debug, Clone, PartialEq)]
pub enum Check {
    Range { start: f64, end: f64 },
    Whitelist(Vec<String>),
    Bitmask(u64),
    Thermal(f64),
    Sparsity(u32),
}

#[derive(Debug, Clone, PartialEq)]
pub struct Constraint {
    pub name: String,
    pub priority: Priority,
    pub checks: Vec<Check>,
}

#[derive(Debug, Clone, PartialEq)]
pub enum GuardItem {
    Constraint(Constraint),
    Comment(String),
}

#[derive(Debug, Clone)]
pub struct ParseError {
    pub line: usize,
    pub message: String,
}

impl fmt::Display for ParseError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "Line {}: {}", self.line, self.message)
    }
}

/// Parse a GUARD DSL source string into items.
pub fn parse_guard(source: &str) -> Result<Vec<GuardItem>, ParseError> {
    let mut items = Vec::new();
    let mut current_name = String::new();
    let mut current_priority = Priority::Default;
    let mut current_checks: Vec<Check> = Vec::new();
    let mut in_constraint = false;

    for (line_num, raw_line) in source.lines().enumerate() {
        let line = raw_line.split("//").next().unwrap_or("").trim();

        if line.is_empty() {
            continue;
        }

        if line.starts_with("constraint ") {
            if in_constraint {
                // Close previous constraint
                items.push(GuardItem::Constraint(Constraint {
                    name: std::mem::take(&mut current_name),
                    priority: current_priority,
                    checks: std::mem::take(&mut current_checks),
                }));
            }
            in_constraint = true;
            current_name = parse_constraint_header(line, line_num)?;
            current_priority = Priority::Default;
            current_checks.clear();

            // Check for @priority on same line
            if let Some(p) = parse_priority_tag(line) {
                current_priority = p;
            }

            // Handle inline content after '{' on the same line
            if let Some(after_brace) = line.split('{').nth(1) {
                let inline = after_brace.replace('}', "").trim().to_string();
                if !inline.is_empty() {
                    if let Some(p) = parse_priority_tag(&inline) {
                        current_priority = p;
                    } else if let Some(check) = parse_check(&inline, line_num)? {
                        current_checks.push(check);
                    }
                    // Check if '}' closes it on same line
                    if after_brace.contains('}') {
                        items.push(GuardItem::Constraint(Constraint {
                            name: std::mem::take(&mut current_name),
                            priority: current_priority,
                            checks: std::mem::take(&mut current_checks),
                        }));
                        in_constraint = false;
                    }
                } else if after_brace.trim() == "}" || after_brace.trim().is_empty() {
                    // '{' followed by '}' on same line = empty constraint
                    // stay in_constraint, will be closed by '}' on its own line
                }
            }
        } else if line == "}" && in_constraint {
            items.push(GuardItem::Constraint(Constraint {
                name: std::mem::take(&mut current_name),
                priority: current_priority,
                checks: std::mem::take(&mut current_checks),
            }));
            in_constraint = false;
        } else if in_constraint {
            // Parse @priority annotation
            if let Some(p) = parse_priority_tag(line) {
                current_priority = p;
                continue;
            }
            // Parse check
            if let Some(check) = parse_check(line, line_num)? {
                current_checks.push(check);
            }
        } else {
            // Top-level comment or unknown
            items.push(GuardItem::Comment(line.to_string()));
        }
    }

    // Handle unclosed constraint
    if in_constraint {
        items.push(GuardItem::Constraint(Constraint {
            name: current_name,
            priority: current_priority,
            checks: current_checks,
        }));
    }

    Ok(items)
}

fn parse_constraint_header(line: &str, line_num: usize) -> Result<String, ParseError> {
    // "constraint name @priority(HARD) {" or "constraint name {"
    let line = line.trim_end_matches('{').trim();
    let parts: Vec<&str> = line.splitn(3, ' ').collect();
    if parts.len() < 2 {
        return Err(ParseError {
            line: line_num,
            message: "Expected: constraint name {".to_string(),
        });
    }
    Ok(parts[1].to_string())
}

fn parse_priority_tag(line: &str) -> Option<Priority> {
    if line.contains("@priority(HARD)") {
        Some(Priority::Hard)
    } else if line.contains("@priority(SOFT)") {
        Some(Priority::Soft)
    } else if line.contains("@priority(DEFAULT)") {
        Some(Priority::Default)
    } else {
        None
    }
}

fn parse_check(line: &str, line_num: usize) -> Result<Option<Check>, ParseError> {
    let line = line.trim().trim_end_matches(',');

    if line.starts_with("range(") {
        let inner = extract_parens(line, "range", line_num)?;
        let nums = parse_two_numbers(&inner, line_num)?;
        Ok(Some(Check::Range { start: nums.0, end: nums.1 }))
    } else if line.starts_with("whitelist(") {
        let inner = extract_parens(line, "whitelist", line_num)?;
        let values: Vec<String> = inner.split(',')
            .map(|s| s.trim().trim_matches('"').to_string())
            .filter(|s| !s.is_empty())
            .collect();
        Ok(Some(Check::Whitelist(values)))
    } else if line.starts_with("bitmask(") {
        let inner = extract_parens(line, "bitmask", line_num)?;
        let val = parse_number(&inner, line_num)?;
        Ok(Some(Check::Bitmask(val as u64)))
    } else if line.starts_with("thermal(") {
        let inner = extract_parens(line, "thermal", line_num)?;
        let val = parse_number(&inner, line_num)?;
        Ok(Some(Check::Thermal(val)))
    } else if line.starts_with("sparsity(") {
        let inner = extract_parens(line, "sparsity", line_num)?;
        let val = parse_number(&inner, line_num)?;
        Ok(Some(Check::Sparsity(val as u32)))
    } else if line.starts_with('@') || line.is_empty() {
        Ok(None) // annotation or empty, skip
    } else {
        Ok(None) // unknown check, skip gracefully
    }
}

fn extract_parens(line: &str, func: &str, line_num: usize) -> Result<String, ParseError> {
    let start = func.len() + 1; // "func("
    let end = line.rfind(')').ok_or(ParseError {
        line: line_num,
        message: format!("Missing closing ')' in {}", func),
    })?;
    Ok(line[start..end].to_string())
}

fn parse_number(s: &str, line_num: usize) -> Result<f64, ParseError> {
    let s = s.trim();
    if s.starts_with("0x") || s.starts_with("0X") {
        u64::from_str_radix(s.trim_start_matches("0x").trim_start_matches("0X"), 16)
            .map(|v| v as f64)
            .map_err(|_| ParseError { line: line_num, message: format!("Invalid hex: {}", s) })
    } else {
        s.parse::<f64>()
            .map_err(|_| ParseError { line: line_num, message: format!("Invalid number: {}", s) })
    }
}

fn parse_two_numbers(s: &str, line_num: usize) -> Result<(f64, f64), ParseError> {
    let parts: Vec<&str> = s.split(',').collect();
    if parts.len() != 2 {
        return Err(ParseError { line: line_num, message: format!("Expected two numbers, got: {}", s) });
    }
    let a = parse_number(parts[0], line_num)?;
    let b = parse_number(parts[1], line_num)?;
    Ok((a, b))
}

/// Extract only Constraint items from parse results.
pub fn extract_constraints(items: &[GuardItem]) -> Vec<&Constraint> {
    items.iter().filter_map(|item| match item {
        GuardItem::Constraint(c) => Some(c),
        _ => None,
    }).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_empty() {
        let items = parse_guard("").unwrap();
        assert!(items.is_empty());
    }

    #[test]
    fn parse_comments() {
        let items = parse_guard("// just a comment\n").unwrap();
        assert!(items.is_empty());
    }

    #[test]
    fn parse_range_constraint() {
        let src = r#"
            constraint altitude @priority(HARD) {
                range(0, 15000)
            }
        "#;
        let items = parse_guard(src).unwrap();
        let constraints = extract_constraints(&items);
        assert_eq!(constraints.len(), 1);
        assert_eq!(constraints[0].name, "altitude");
        assert_eq!(constraints[0].priority, Priority::Hard);
        assert_eq!(constraints[0].checks.len(), 1);
        assert!(matches!(&constraints[0].checks[0], Check::Range { start, end } if *start == 0.0 && *end == 15000.0));
    }

    #[test]
    fn parse_whitelist() {
        let src = r#"
            constraint flight_commands @priority(HARD) {
                whitelist(HOVER, ASCEND, DESCEND, LAND, EMERGENCY)
            }
        "#;
        let items = parse_guard(src).unwrap();
        let constraints = extract_constraints(&items);
        assert_eq!(constraints[0].checks.len(), 1);
        assert!(matches!(&constraints[0].checks[0], Check::Whitelist(v) if v.len() == 5));
    }

    #[test]
    fn parse_bitmask_thermal() {
        let src = r#"
            constraint sensor_check {
                bitmask(0x3F)
                thermal(2.5)
                sparsity(128)
            }
        "#;
        let items = parse_guard(src).unwrap();
        let constraints = extract_constraints(&items);
        assert_eq!(constraints[0].checks.len(), 3);
        assert_eq!(constraints[0].priority, Priority::Default);
    }

    #[test]
    fn parse_multiple_constraints() {
        let src = r#"
            constraint altitude @priority(HARD) {
                range(0, 15000)
            }
            constraint steering @priority(SOFT) {
                range(-12, 12)
            }
        "#;
        let items = parse_guard(src).unwrap();
        let constraints = extract_constraints(&items);
        assert_eq!(constraints.len(), 2);
        assert_eq!(constraints[0].name, "altitude");
        assert_eq!(constraints[1].name, "steering");
    }
}
