//! Constraint Engine module
//!
//! Implements Constraint-Theory's first-person perspective filtering.
//! No omniscience - entities see only what permissions allow.
//!
//! ## Assertive Markdown Constraints
//!
//! In the PLATO tradition ("Cave of Evals"), Markdown bullet points can be parsed
//! as hard runtime assertions. A bullet like:
//!   `- The user's name must be capitalized.`
//! becomes an `AssertiveConstraint` that a secondary `ConstraintAuditor` agent
//! enforces at output time — looping the primary agent back to a retry state if
//! the assertion fails, just like a PLATO lesson from the 1970s.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// A constraint that governs what an entity can see/do
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Constraint {
    pub id: String,
    pub description: String,
    pub enabled: bool,
    pub filter_type: FilterType,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum FilterType {
    /// This constraint allows the action
    Allow,
    /// This constraint denies the action
    Deny,
    /// This constraint requires approval from another entity
    RequestApproval,
}

/// Constraint matrix for an entity in a room
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConstraintMatrix {
    pub identity: String,
    pub room: String,
    pub constraints: Vec<Constraint>,
}

/// Result of checking constraints
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ConstraintResult {
    /// Action is allowed
    Allow,
    /// Action is denied (violation is computed, not an error)
    Deny(ConstraintViolation),
    /// Action requires approval from another entity
    RequestApproval(ApprovalRequest),
}

/// Details of a constraint violation
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ConstraintViolation {
    pub constraint: String,
    pub attempted_action: String,
    pub reason: String,
}

/// Details of an approval request
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ApprovalRequest {
    pub constraint: String,
    pub attempted_action: String,
    pub approvers: Vec<String>,
}

/// Command to check against constraints
#[derive(Debug, Clone)]
pub struct Command {
    pub verb: String,
    pub target: String,
    pub args: Vec<String>,
}

impl Command {
    pub fn new(verb: &str, target: &str, args: Vec<&str>) -> Self {
        Self {
            verb: verb.to_string(),
            target: target.to_string(),
            args: args.iter().map(|s| s.to_string()).collect(),
        }
    }

    pub fn from_string(input: &str) -> Self {
        let parts: Vec<&str> = input.split_whitespace().collect();
        if parts.is_empty() {
            return Self {
                verb: String::new(),
                target: String::new(),
                args: vec![],
            };
        }
        
        let verb = parts[0].to_string();
        let target = parts.get(1).map(|s| s.to_string()).unwrap_or_default();
        let args = parts[2..].iter().map(|s| s.to_string()).collect();
        
        Self { verb, target, args }
    }
}

/// Constraint Engine - checks commands against first-person permissions
pub struct ConstraintEngine {
    #[allow(dead_code)]
    matrices: HashMap<(String, String), ConstraintMatrix>, // (identity, room) -> matrix
}

impl ConstraintEngine {
    pub fn new() -> Self {
        Self {
            matrices: HashMap::new(),
        }
    }

    /// Load constraints for an identity in a room (from repo's .plato/CONSTRAINTS.yaml)
    pub fn load_constraints(&self, room_name: &str, identity: &str) -> Result<ConstraintMatrix, anyhow::Error> {
        // For now, return a default matrix
        // Real implementation would read from repo's .plato/CONSTRAINTS.yaml
        Ok(ConstraintMatrix {
            identity: identity.to_string(),
            room: room_name.to_string(),
            constraints: vec![
                Constraint {
                    id: "view_room".to_string(),
                    description: "Can view room description".to_string(),
                    enabled: true,
                    filter_type: FilterType::Allow,
                },
                Constraint {
                    id: "send_tell".to_string(),
                    description: "Can send tells to other entities".to_string(),
                    enabled: true,
                    filter_type: FilterType::Allow,
                },
                Constraint {
                    id: "admin_commands".to_string(),
                    description: "Can execute admin commands".to_string(),
                    enabled: false,
                    filter_type: FilterType::Deny,
                },
            ],
        })
    }

    /// Check a command against the constraint matrix
    pub fn check(&self, matrix: &ConstraintMatrix, command: &Command) -> ConstraintResult {
        // Find relevant constraints for this command
        for constraint in &matrix.constraints {
            if !constraint.enabled {
                continue;
            }

            // Match constraint to command type
            let matches = match constraint.id.as_str() {
                "view_room" => command.verb == "look" || command.verb == "examine",
                "send_tell" => command.verb == "tell" || command.verb == "page",
                "admin_commands" => command.verb.starts_with("@") || command.verb == "delete" || command.verb == "create",
                _ => false,
            };

            if matches {
                match constraint.filter_type {
                    FilterType::Allow => return ConstraintResult::Allow,
                    FilterType::Deny => {
                        return ConstraintResult::Deny(ConstraintViolation {
                            constraint: constraint.id.clone(),
                            attempted_action: format!("{} {}", command.verb, command.target),
                            reason: constraint.description.clone(),
                        });
                    }
                    FilterType::RequestApproval => {
                        return ConstraintResult::RequestApproval(ApprovalRequest {
                            constraint: constraint.id.clone(),
                            attempted_action: format!("{} {}", command.verb, command.target),
                            approvers: vec!["@admin".to_string()],
                        });
                    }
                }
            }
        }

        // Default: allow
        ConstraintResult::Allow
    }

    /// Add a constraint to a matrix
    pub fn add_constraint(&mut self, mut matrix: ConstraintMatrix, constraint: Constraint) -> ConstraintMatrix {
        matrix.constraints.push(constraint);
        matrix
    }
}

impl Default for ConstraintEngine {
    fn default() -> Self {
        Self::new()
    }
}

// ─── Assertive Markdown Constraints ─────────────────────────────────────────

/// An assertion extracted from a Markdown bullet point.
///
/// Bullets prefixed with `- ` or `* ` are treated as assertions the agent's
/// output must satisfy. Verbs like "must", "should", "cannot" drive the
/// `AssertionKind`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AssertiveConstraint {
    pub id: String,
    pub source_text: String,
    pub kind: AssertionKind,
    pub subject: Option<String>,
    pub predicate: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum AssertionKind {
    /// "must" / "shall" — hard requirement
    Must,
    /// "should" / "ought" — soft recommendation (auditor warns, doesn't retry)
    Should,
    /// "cannot" / "must not" — hard prohibition
    MustNot,
}

impl AssertiveConstraint {
    fn parse_kind(text: &str) -> AssertionKind {
        let lower = text.to_lowercase();
        if lower.contains("must not") || lower.contains("cannot") || lower.contains("never") {
            AssertionKind::MustNot
        } else if lower.contains("must") || lower.contains("shall") || lower.contains("always") {
            AssertionKind::Must
        } else {
            AssertionKind::Should
        }
    }
}

/// Parse Markdown content for assertive bullet constraints.
///
/// Bullets (`- ` or `* `) whose text contains modal verbs are extracted.
/// Non-modal bullets and headers are ignored — this is intentionally narrow
/// so that documentation prose doesn't accidentally become constraints.
pub fn parse_markdown_constraints(content: &str) -> Vec<AssertiveConstraint> {
    let modal_verbs = ["must", "shall", "cannot", "must not", "never", "always", "should"];

    content
        .lines()
        .enumerate()
        .filter_map(|(i, line)| {
            let trimmed = line.trim();
            let text = if let Some(rest) = trimmed.strip_prefix("- ") {
                rest
            } else if let Some(rest) = trimmed.strip_prefix("* ") {
                rest
            } else {
                return None;
            };

            let lower = text.to_lowercase();
            if !modal_verbs.iter().any(|v| lower.contains(v)) {
                return None;
            }

            let kind = AssertiveConstraint::parse_kind(text);
            Some(AssertiveConstraint {
                id: format!("md-assert-{}", i),
                source_text: text.trim_end_matches('.').to_string(),
                kind,
                subject: None,
                predicate: text.to_string(),
            })
        })
        .collect()
}

/// Outcome of auditing an agent output against assertive constraints.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AuditOutcome {
    /// All hard constraints passed; the output may proceed.
    Pass,
    /// One or more `Must`/`MustNot` constraints failed — loop agent to retry.
    RetryRequired(Vec<String>),
    /// Soft (`Should`) constraints were violated — emit warning but allow output.
    Warned(Vec<String>),
}

/// The ConstraintAuditor acts as the secondary "tutor" agent.
///
/// Given a set of `AssertiveConstraint`s and an agent's output text, it checks
/// each assertion and either passes, warns, or demands a retry — mirroring the
/// PLATO lesson loop where a student cannot advance without passing the current
/// block.
pub struct ConstraintAuditor {
    constraints: Vec<AssertiveConstraint>,
}

impl ConstraintAuditor {
    pub fn new(constraints: Vec<AssertiveConstraint>) -> Self {
        Self { constraints }
    }

    /// Load constraints by parsing a Markdown document.
    pub fn from_markdown(content: &str) -> Self {
        Self::new(parse_markdown_constraints(content))
    }

    /// Audit `agent_output` against all loaded constraints.
    ///
    /// This is a *lexical* audit: assertions are matched by checking whether the
    /// output contains (or avoids) keywords derived from the constraint text.
    /// A production implementation would use an LLM judge; this version is
    /// deterministic and testable.
    pub fn audit(&self, agent_output: &str) -> AuditOutcome {
        let mut hard_failures: Vec<String> = Vec::new();
        let mut soft_warnings: Vec<String> = Vec::new();

        for c in &self.constraints {
            let violated = self.check_violated(c, agent_output);
            if violated {
                match c.kind {
                    AssertionKind::Must | AssertionKind::MustNot => {
                        hard_failures.push(c.source_text.clone());
                    }
                    AssertionKind::Should => {
                        soft_warnings.push(c.source_text.clone());
                    }
                }
            }
        }

        if !hard_failures.is_empty() {
            AuditOutcome::RetryRequired(hard_failures)
        } else if !soft_warnings.is_empty() {
            AuditOutcome::Warned(soft_warnings)
        } else {
            AuditOutcome::Pass
        }
    }

    /// Heuristic violation check.
    /// For `Must` constraints: looks for key noun/verb phrases from the assertion.
    /// For `MustNot` constraints: checks that the prohibited token is absent.
    fn check_violated(&self, constraint: &AssertiveConstraint, output: &str) -> bool {
        // Extract the key noun phrase: words after "must be" / "must" / "cannot"
        let lower_pred = constraint.predicate.to_lowercase();
        let lower_out = output.to_lowercase();

        match constraint.kind {
            AssertionKind::MustNot => {
                // Find what is prohibited — words after "cannot" or "must not" or "never"
                for marker in ["must not ", "cannot ", "never "] {
                    if let Some(pos) = lower_pred.find(marker) {
                        let prohibited: String = lower_pred[pos + marker.len()..]
                            .split_whitespace()
                            .take(2)
                            .collect::<Vec<_>>()
                            .join(" ");
                        if lower_out.contains(&prohibited) {
                            return true;
                        }
                    }
                }
                false
            }
            AssertionKind::Must | AssertionKind::Should => {
                // Find what is required — words after "must be" / "must" / "should".
                // Try most-specific markers first; break after the first match so that
                // "must be" doesn't also get re-evaluated as "must" with a longer extract.
                for marker in ["must be ", "must ", "shall ", "should ", "always "] {
                    if let Some(pos) = lower_pred.find(marker) {
                        let required: String = lower_pred[pos + marker.len()..]
                            .split_whitespace()
                            .take(2)
                            .collect::<Vec<_>>()
                            .join(" ");
                        let violated = !required.is_empty() && !lower_out.contains(&required);
                        return violated; // First matching marker is authoritative
                    }
                }
                false
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_basic_constraint_check() {
        let engine = ConstraintEngine::new();
        
        let matrix = ConstraintMatrix {
            identity: "@test".to_string(),
            room: "test-room".to_string(),
            constraints: vec![
                Constraint {
                    id: "send_tell".to_string(),
                    description: "Can send tells".to_string(),
                    enabled: true,
                    filter_type: FilterType::Allow,
                },
            ],
        };
        
        let cmd = Command::new("tell", "@other", vec!["Hello"]);
        let result = engine.check(&matrix, &cmd);
        
        assert_eq!(result, ConstraintResult::Allow);
    }

    #[test]
    fn test_parse_markdown_constraints() {
        let md = "## Rules\n- The user's name must be capitalized.\n- Output cannot contain profanity.\n- Links should be https.\n";
        let constraints = parse_markdown_constraints(md);
        assert_eq!(constraints.len(), 3);
        assert_eq!(constraints[0].kind, AssertionKind::Must);
        assert_eq!(constraints[1].kind, AssertionKind::MustNot);
        assert_eq!(constraints[2].kind, AssertionKind::Should);
    }

    #[test]
    fn test_auditor_retry_on_hard_failure() {
        let md = "- Output must be capitalized.\n";
        let auditor = ConstraintAuditor::from_markdown(md);
        // Lowercase output → fails "must be capitalized" (heuristic: "capitalized" absent)
        let result = auditor.audit("hello world");
        assert_eq!(result, AuditOutcome::RetryRequired(vec!["Output must be capitalized".to_string()]));
    }

    #[test]
    fn test_auditor_pass() {
        let md = "- Output must be capitalized.\n";
        let auditor = ConstraintAuditor::from_markdown(md);
        let result = auditor.audit("Hello world — capitalized.");
        assert_eq!(result, AuditOutcome::Pass);
    }
}
