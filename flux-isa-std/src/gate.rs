use serde::{Deserialize, Serialize};

/// Verdict from quality gate
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum GateVerdict {
    Accept,
    Reject(String),
}

/// Configuration for quality gate rules
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GateConfig {
    /// Minimum content length (characters)
    pub min_length: usize,
    /// Reject claims containing these keywords (absolute certainty language)
    pub absolute_keywords: Vec<String>,
    /// Required fields that must be present in structured data
    pub required_fields: Vec<String>,
    /// Maximum numeric value (sanity check)
    pub max_value: Option<f64>,
    /// Minimum numeric value (sanity check)
    pub min_value: Option<f64>,
}

impl Default for GateConfig {
    fn default() -> Self {
        Self {
            min_length: 10,
            absolute_keywords: vec![
                "prove".into(),
                "proof".into(),
                "definitely".into(),
                "certainly".into(),
                "absolutely".into(),
                "guaranteed".into(),
                "impossible".into(),
                "never".into(),
                "always".into(),
                "undeniable".into(),
                "infallible".into(),
            ],
            required_fields: vec![],
            max_value: None,
            min_value: None,
        }
    }
}

/// Local quality gate — validates data before forwarding to PLATO
pub struct QualityGate {
    config: GateConfig,
}

impl QualityGate {
    pub fn new(config: GateConfig) -> Self {
        Self { config }
    }

    pub fn with_default_config() -> Self {
        Self::new(GateConfig::default())
    }

    /// Check a text value through the gate
    pub fn check(&self, value: &str) -> GateVerdict {
        // Reject too short
        if let Some(v) = self.reject_too_short(value) {
            return v;
        }
        // Reject absolute claims
        if let Some(v) = self.reject_absolute_claims(value) {
            return v;
        }
        // Check required fields
        if let Some(v) = self.reject_missing_fields(value) {
            return v;
        }
        // Numeric bounds check
        if let Ok(num) = value.trim().parse::<f64>() {
            if let Some(min) = self.config.min_value {
                if num < min {
                    return GateVerdict::Reject(format!("Value {} below minimum {}", num, min));
                }
            }
            if let Some(max) = self.config.max_value {
                if num > max {
                    return GateVerdict::Reject(format!("Value {} above maximum {}", num, max));
                }
            }
        }
        GateVerdict::Accept
    }

    /// Batch check — returns verdicts for each item
    pub fn check_batch(&self, values: &[&str]) -> Vec<GateVerdict> {
        values.iter().map(|v| self.check(v)).collect()
    }

    fn reject_too_short(&self, value: &str) -> Option<GateVerdict> {
        if value.trim().len() < self.config.min_length {
            Some(GateVerdict::Reject(format!(
                "Content too short: {} chars (minimum {})",
                value.trim().len(),
                self.config.min_length
            )))
        } else {
            None
        }
    }

    fn reject_absolute_claims(&self, value: &str) -> Option<GateVerdict> {
        let lower = value.to_lowercase();
        for keyword in &self.config.absolute_keywords {
            // Simple keyword boundary check — word must appear as a whole word
            if Self::contains_word(&lower, &keyword.to_lowercase()) {
                return Some(GateVerdict::Reject(format!(
                    "Absolute claim detected: keyword '{}'",
                    keyword
                )));
            }
        }
        None
    }

    fn reject_missing_fields(&self, value: &str) -> Option<GateVerdict> {
        if self.config.required_fields.is_empty() {
            return None;
        }
        let lower = value.to_lowercase();
        for field in &self.config.required_fields {
            if !lower.contains(&field.to_lowercase()) {
                return Some(GateVerdict::Reject(format!(
                    "Missing required field: '{}'",
                    field
                )));
            }
        }
        None
    }

    /// Simple whole-word keyword match (regex-free)
    fn contains_word(haystack: &str, needle: &str) -> bool {
        let haystack_lower = haystack.to_lowercase();
        let needle_lower = needle.to_lowercase();
        let mut start = 0;
        while let Some(pos) = haystack_lower[start..].find(&needle_lower) {
            let abs_pos = start + pos;
            let before_ok = abs_pos == 0
                || !haystack_lower.as_bytes()[abs_pos - 1].is_ascii_alphabetic();
            let after_pos = abs_pos + needle_lower.len();
            let after_ok = after_pos >= haystack_lower.len()
                || !haystack_lower.as_bytes()[after_pos].is_ascii_alphabetic();
            if before_ok && after_ok {
                return true;
            }
            start = abs_pos + 1;
        }
        false
    }
}
