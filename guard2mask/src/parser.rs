//! GUARD DSL parser (stub — full nom-based parser in development)

use crate::types::*;

/// Parse a GUARD DSL source string into constraints
pub fn parse_guard(source: &str) -> Result<Vec<Constraint>, String> {
    let mut constraints = Vec::new();
    for line in source.lines() {
        let line = line.trim();
        if line.is_empty() || line.starts_with("//") {
            continue;
        }
        // TODO: full nom-based parser
        constraints.push(Constraint {
            name: line.to_string(),
            priority: Priority::Default,
            checks: vec![],
        });
    }
    Ok(constraints)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_empty() {
        assert_eq!(parse_guard("").unwrap(), vec![]);
    }

    #[test]
    fn parse_comments() {
        assert_eq!(parse_guard("// comment\n").unwrap(), vec![]);
    }
}
