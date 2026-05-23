use regex::Regex;
use serde::{Deserialize, Serialize};
use std::sync::LazyLock;

use crate::tile::Tile;

/// Gate decision after evaluating a tile.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum GateDecision {
    Accept,
    Reject(String),
}

/// Configuration for the quality gate.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GateConfig {
    /// Reject absolute claims ("always", "never", etc.)
    pub reject_absolute_claims: bool,
    /// Reject duplicate tiles (checked externally via room hash lookup)
    pub reject_duplicates: bool,
    /// Minimum answer length
    pub min_answer_length: usize,
    /// Minimum question length
    pub min_question_length: usize,
    /// Reject if required fields are missing
    pub reject_missing_fields: bool,
    /// Custom absolute claim patterns (in addition to defaults)
    pub extra_absolute_patterns: Vec<String>,
}

impl Default for GateConfig {
    fn default() -> Self {
        Self {
            reject_absolute_claims: true,
            reject_duplicates: true,
            min_answer_length: 10,
            min_question_length: 3,
            reject_missing_fields: true,
            extra_absolute_patterns: Vec::new(),
        }
    }
}

/// Absolute claim patterns to detect.
static ABSOLUTE_PATTERNS: LazyLock<Vec<Regex>> = LazyLock::new(|| {
    let patterns = [
        r"\balways\b",
        r"\bnever\b",
        r"\bimpossible\b",
        r"\bguaranteed\b",
        r"\b100%\b",
        r"\beveryone\b",
        r"\bno one\b",
        r"\ball\s+\w+\s+(are|is|will|can|should|must)\b",
        r"\bnone\s+(of|are|is|will)\b",
    ];
    patterns
        .iter()
        .map(|p| Regex::new(p).expect("invalid absolute claim regex"))
        .collect()
});

/// Check if text is inside quotes (heuristic: odd number of quotes before position).
fn is_in_quotes(text: &str, position: usize) -> bool {
    let before = &text[..position];
    let quote_count = before.matches('"').count() + before.matches('\'').count();
    quote_count % 2 == 1
}

/// Detect absolute claims in text, respecting quoted context.
fn detect_absolute_claims(text: &str) -> Vec<String> {
    let mut found = Vec::new();
    let lower = text.to_lowercase();

    for re in ABSOLUTE_PATTERNS.iter() {
        for mat in re.find_iter(&lower) {
            if !is_in_quotes(&lower, mat.start()) {
                found.push(mat.as_str().to_string());
            }
        }
    }

    found.sort();
    found.dedup();
    found
}

/// The quality gate — evaluates tiles before acceptance.
#[derive(Debug, Clone)]
pub struct Gate {
    pub config: GateConfig,
}

impl Gate {
    pub fn new(config: GateConfig) -> Self {
        Self { config }
    }

    pub fn with_defaults() -> Self {
        Self::new(GateConfig::default())
    }

    /// Evaluate a tile through all gate rules.
    /// Returns Accept if all rules pass, or the first Reject with reason.
    pub fn evaluate(&self, tile: &Tile) -> GateDecision {
        // Rule: reject missing fields
        if self.config.reject_missing_fields {
            if let Err(e) = tile.validate() {
                return GateDecision::Reject(format!("missing/invalid fields: {}", e));
            }
        }

        // Rule: reject too-short questions
        if tile.question.trim().len() < self.config.min_question_length {
            return GateDecision::Reject(format!(
                "question too short ({} < {})",
                tile.question.trim().len(),
                self.config.min_question_length
            ));
        }

        // Rule: reject too-short answers
        if tile.answer.trim().len() < self.config.min_answer_length {
            return GateDecision::Reject(format!(
                "answer too short ({} < {})",
                tile.answer.trim().len(),
                self.config.min_answer_length
            ));
        }

        // Rule: reject absolute claims
        if self.config.reject_absolute_claims {
            let claims = detect_absolute_claims(&tile.answer);
            if !claims.is_empty() {
                return GateDecision::Reject(format!(
                    "absolute claims detected: {}",
                    claims.join(", ")
                ));
            }
        }

        GateDecision::Accept
    }

    /// Evaluate a tile, also checking for duplicates against existing hashes.
    pub fn evaluate_with_hashes(&self, tile: &Tile, existing_hashes: &[impl AsRef<str>]) -> GateDecision {
        // Run base rules first
        let decision = self.evaluate(tile);
        if let GateDecision::Reject(_) = decision {
            return decision;
        }

        // Check duplicate
        if self.config.reject_duplicates {
            let tile_hash = tile.content_hash();
            for h in existing_hashes {
                if h.as_ref() == tile_hash {
                    return GateDecision::Reject("duplicate tile (matching content hash)".into());
                }
            }
        }

        GateDecision::Accept
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::tile::{Provenance, TileBuilder};

    fn make_tile(answer: &str, question: &str) -> Tile {
        TileBuilder::new()
            .domain("test")
            .question(question)
            .answer(answer)
            .source("test-source")
            .confidence(0.8)
            .provenance(Provenance {
                agent_id: "test-agent".into(),
                session_id: "test-session".into(),
                chain_hash: "abc".into(),
                signature: "sig".into(),
            })
            .build()
            .unwrap()
    }

    #[test]
    fn test_accept_good_tile() {
        let gate = Gate::with_defaults();
        let tile = make_tile("This is a well-qualified answer about something.", "What is it?");
        assert!(matches!(gate.evaluate(&tile), GateDecision::Accept));
    }

    #[test]
    fn test_reject_absolute_always() {
        let gate = Gate::with_defaults();
        let tile = make_tile("This will always work perfectly.", "Does it work?");
        match gate.evaluate(&tile) {
            GateDecision::Reject(reason) => assert!(reason.contains("absolute claims")),
            GateDecision::Accept => panic!("should reject absolute claims"),
        }
    }

    #[test]
    fn test_reject_absolute_never() {
        let gate = Gate::with_defaults();
        let tile = make_tile("This never fails under any condition.", "Is it reliable?");
        match gate.evaluate(&tile) {
            GateDecision::Reject(reason) => assert!(reason.contains("absolute claims")),
            GateDecision::Accept => panic!("should reject"),
        }
    }

    #[test]
    fn test_allow_quoted_absolute() {
        // "always" inside quotes should be allowed
        let gate = Gate::with_defaults();
        let tile = make_tile(
            r#"'Always' is a word people use too often."#,
            "What about that word?",
        );
        assert!(matches!(gate.evaluate(&tile), GateDecision::Accept));
    }

    #[test]
    fn test_reject_too_short_answer() {
        let gate = Gate::with_defaults();
        let tile = make_tile("Short", "What is the answer?");
        match gate.evaluate(&tile) {
            GateDecision::Reject(reason) => assert!(reason.contains("too short")),
            GateDecision::Accept => panic!("should reject short answer"),
        }
    }

    #[test]
    fn test_reject_too_short_question() {
        let gate = Gate::with_defaults();
        let tile = make_tile(
            "This is a detailed answer to the question.",
            "W",
        );
        match gate.evaluate(&tile) {
            GateDecision::Reject(reason) => assert!(reason.contains("too short")),
            GateDecision::Accept => panic!("should reject short question"),
        }
    }

    #[test]
    fn test_duplicate_detection() {
        let gate = Gate::with_defaults();
        let tile = make_tile("A unique answer to the question.", "What?");
        let hash = tile.content_hash();
        let decision = gate.evaluate_with_hashes(&tile, &[hash.as_str()]);
        assert!(matches!(decision, GateDecision::Reject(_)));
    }
}
