//! Via pattern generator for GDSII output (stub)

use crate::types::*;

/// Generate via patterns from a constraint assignment
pub fn generate_patterns(_assignment: &Assignment) -> GDSIIOutput {
    // TODO: full pattern generation with metal layer routing
    GDSIIOutput::new()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn generate_empty() {
        let result = generate_patterns(&Assignment::new());
        assert!(result.patterns.is_empty());
    }
}
