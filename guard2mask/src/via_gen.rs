//! Via pattern generator for GDSII output (stub)

use crate::types::Assignment;
use crate::types::GDSIIOutput;

/// Generate via patterns from a constraint assignment
pub fn generate_patterns(_assignment: &Assignment) -> GDSIIOutput {
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
