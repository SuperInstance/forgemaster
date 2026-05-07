//! flux-ast — Universal Constraint AST
//!
//! Single source of truth for constraint semantics. Every downstream representation
//! (GUARD, FLUX-C, TLA+, Coq, SystemVerilog, Python) is GENERATED from this AST,
//! never hand-written and then "translated."

use std::fmt;

/// Signal reference — what we're constraining
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct SignalRef {
    pub name: String,
    pub index: Option<usize>,  // for tensor elements
    pub agent: Option<String>, // for multi-agent constraints
}

impl SignalRef {
    pub fn local(name: &str) -> Self {
        SignalRef { name: name.to_string(), index: None, agent: None }
    }
    pub fn indexed(name: &str, idx: usize) -> Self {
        SignalRef { name: name.to_string(), index: Some(idx), agent: None }
    }
    pub fn remote(name: &str, agent: &str) -> Self {
        SignalRef { name: name.to_string(), index: None, agent: Some(agent.to_string()) }
    }
}

impl fmt::Display for SignalRef {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match (&self.agent, &self.index) {
            (Some(a), Some(i)) => write!(f, "{}.{}[{}]", a, self.name, i),
            (Some(a), None) => write!(f, "{}.{}", a, self.name),
            (None, Some(i)) => write!(f, "{}[{}]", self.name, i),
            (None, None) => write!(f, "{}", self.name),
        }
    }
}

/// Value type for constraint parameters
#[derive(Debug, Clone, PartialEq)]
pub enum Value {
    Integer(i64),
    Float(f64),
    Bool(bool),
    Symbol(String),
}

impl fmt::Display for Value {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            Value::Integer(i) => write!(f, "{}", i),
            Value::Float(fl) => write!(f, "{}", fl),
            Value::Bool(b) => write!(f, "{}", b),
            Value::Symbol(s) => write!(f, "{}", s),
        }
    }
}

/// Severity level for constraints
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Severity {
    Hard,    // Never relax, always enforced
    Soft,    // May weaken under conflict
    Default, // Relax first under resource pressure
}

impl fmt::Display for Severity {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            Severity::Hard => write!(f, "HARD"),
            Severity::Soft => write!(f, "SOFT"),
            Severity::Default => write!(f, "DEFAULT"),
        }
    }
}

/// Temporal window for rate-of-change constraints
#[derive(Debug, Clone, PartialEq)]
pub enum Window {
    PerFrame,
    Sliding(usize),
    Cumulative,
}

/// Inter-signal relation type
#[derive(Debug, Clone, PartialEq)]
pub enum Relation {
    MutuallyExclusive,
    IncreasesWith,
    DecreasesWith,
    Proportional(f64),
}

/// Delegation protocol
#[derive(Debug, Clone, PartialEq)]
pub enum DelegateProtocol {
    Sync,       // Block until result
    Async,      // Fire and check later
    CoIterate,  // Collaborative solving
}

/// Convergence criteria for co-iteration
#[derive(Debug, Clone, PartialEq)]
pub enum ConvergenceCriteria {
    MaxIterations(usize),
    Tolerance(f64),
    TimeoutMs(u64),
}

/// Conflict resolution policy
#[derive(Debug, Clone, PartialEq)]
pub enum ResolutionPolicy {
    Priority,   // Higher severity wins
    Voting,     // Majority rules
    Arbiter(String),  // Named arbiter agent
}

/// Core AST node types
#[derive(Debug, Clone, PartialEq)]
pub enum ConstraintNode {
    // Primitive constraints
    Bound(BoundNode),
    Delta(DeltaNode),
    Relation(RelationNode),
    Confidence(ConfidenceNode),
    Semantic(SemanticNode),

    // Multi-agent constraints
    Delegate(DelegateNode),
    CoIterate(CoIterateNode),

    // Logical combinators
    And(Vec<ConstraintNode>),
    Or(Vec<ConstraintNode>),
    Not(Box<ConstraintNode>),
    Implies(Box<ConstraintNode>, Box<ConstraintNode>),
}

/// Output range constraint: lower ≤ signal ≤ upper
#[derive(Debug, Clone, PartialEq)]
pub struct BoundNode {
    pub signal: SignalRef,
    pub lower: Value,
    pub upper: Value,
    pub severity: Severity,
}

/// Temporal rate-of-change constraint: |signal[t] - signal[t-w]| ≤ max_delta
#[derive(Debug, Clone, PartialEq)]
pub struct DeltaNode {
    pub signal: SignalRef,
    pub max_delta: Value,
    pub window: Window,
    pub severity: Severity,
}

/// Inter-signal dependency constraint
#[derive(Debug, Clone, PartialEq)]
pub struct RelationNode {
    pub signal_a: SignalRef,
    pub signal_b: SignalRef,
    pub relation: Relation,
    pub severity: Severity,
}

/// Minimum confidence requirement
#[derive(Debug, Clone, PartialEq)]
pub struct ConfidenceNode {
    pub signal: SignalRef,
    pub threshold: f64,
    pub severity: Severity,
}

/// Class-membership constraint
#[derive(Debug, Clone, PartialEq)]
pub struct SemanticNode {
    pub signal: SignalRef,
    pub allowed_classes: Vec<String>,
    pub mask: Option<u64>,
    pub severity: Severity,
}

/// Cross-agent constraint delegation
#[derive(Debug, Clone, PartialEq)]
pub struct DelegateNode {
    pub source_agent: String,
    pub target_agent: String,
    pub constraint: Box<ConstraintNode>,
    pub protocol: DelegateProtocol,
}

/// Collaborative constraint solving
#[derive(Debug, Clone, PartialEq)]
pub struct CoIterateNode {
    pub agents: Vec<String>,
    pub constraints: Vec<ConstraintNode>,
    pub convergence: ConvergenceCriteria,
    pub conflict_resolution: ResolutionPolicy,
}

impl ConstraintNode {
    /// Count leaf constraints (non-combinator nodes)
    pub fn leaf_count(&self) -> usize {
        match self {
            ConstraintNode::And(cs) | ConstraintNode::Or(cs) => cs.iter().map(|c| c.leaf_count()).sum(),
            ConstraintNode::Not(c) => c.leaf_count(),
            ConstraintNode::Implies(a, b) => a.leaf_count() + b.leaf_count(),
            ConstraintNode::CoIterate { .. } => 0, // meta-node
            _ => 1,
        }
    }

    /// Get maximum severity of any node in the tree
    pub fn max_severity(&self) -> Severity {
        match self {
            ConstraintNode::Bound(b) => b.severity,
            ConstraintNode::Delta(d) => d.severity,
            ConstraintNode::Relation(r) => r.severity,
            ConstraintNode::Confidence(c) => c.severity,
            ConstraintNode::Semantic(s) => s.severity,
            ConstraintNode::And(cs) | ConstraintNode::Or(cs) => {
                cs.iter().map(|c| c.max_severity()).max_by_key(|s| match s {
                    Severity::Hard => 2,
                    Severity::Soft => 1,
                    Severity::Default => 0,
                }).unwrap_or(Severity::Default)
            }
            ConstraintNode::Not(c) => c.max_severity(),
            ConstraintNode::Implies(a, b) => {
                let sa = a.max_severity();
                let sb = b.max_severity();
                match (sa, sb) {
                    (Severity::Hard, _) | (_, Severity::Hard) => Severity::Hard,
                    (Severity::Soft, _) | (_, Severity::Soft) => Severity::Soft,
                    _ => Severity::Default,
                }
            }
            _ => Severity::Default,
        }
    }

    /// Check if this node involves remote agents (multi-agent constraint)
    pub fn is_distributed(&self) -> bool {
        match self {
            ConstraintNode::Delegate(_) | ConstraintNode::CoIterate(_) => true,
            ConstraintNode::And(cs) | ConstraintNode::Or(cs) => cs.iter().any(|c| c.is_distributed()),
            ConstraintNode::Not(c) => c.is_distributed(),
            ConstraintNode::Implies(a, b) => a.is_distributed() || b.is_distributed(),
            ConstraintNode::Relation(r) => r.signal_a.agent.is_some() || r.signal_b.agent.is_some(),
            _ => false,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bound_node() {
        let node = ConstraintNode::Bound(BoundNode {
            signal: SignalRef::local("velocity"),
            lower: Value::Integer(0),
            upper: Value::Integer(300),
            severity: Severity::Hard,
        });
        assert_eq!(node.leaf_count(), 1);
        assert_eq!(node.max_severity(), Severity::Hard);
        assert!(!node.is_distributed());
    }

    #[test]
    fn delta_node() {
        let node = ConstraintNode::Delta(DeltaNode {
            signal: SignalRef::local("heading"),
            max_delta: Value::Integer(15),
            window: Window::PerFrame,
            severity: Severity::Hard,
        });
        assert_eq!(node.leaf_count(), 1);
    }

    #[test]
    fn and_combinator() {
        let node = ConstraintNode::And(vec![
            ConstraintNode::Bound(BoundNode {
                signal: SignalRef::local("alt"),
                lower: Value::Integer(0),
                upper: Value::Integer(15000),
                severity: Severity::Hard,
            }),
            ConstraintNode::Confidence(ConfidenceNode {
                signal: SignalRef::local("detect"),
                threshold: 0.7,
                severity: Severity::Soft,
            }),
        ]);
        assert_eq!(node.leaf_count(), 2);
        assert_eq!(node.max_severity(), Severity::Hard);
    }

    #[test]
    fn delegate_node() {
        let node = ConstraintNode::Delegate(DelegateNode {
            source_agent: "forgemaster".to_string(),
            target_agent: "oracle1".to_string(),
            constraint: Box::new(ConstraintNode::Bound(BoundNode {
                signal: SignalRef::remote("altitude", "navigator"),
                lower: Value::Integer(0),
                upper: Value::Integer(15000),
                severity: Severity::Hard,
            })),
            protocol: DelegateProtocol::Sync,
        });
        assert!(node.is_distributed());
    }

    #[test]
    fn co_iterate_node() {
        let node = ConstraintNode::CoIterate(CoIterateNode {
            agents: vec!["agent_a".to_string(), "agent_b".to_string()],
            constraints: vec![
                ConstraintNode::Bound(BoundNode {
                    signal: SignalRef::local("x"),
                    lower: Value::Integer(0),
                    upper: Value::Integer(100),
                    severity: Severity::Hard,
                }),
            ],
            convergence: ConvergenceCriteria::MaxIterations(100),
            conflict_resolution: ResolutionPolicy::Priority,
        });
        assert!(node.is_distributed());
    }

    #[test]
    fn signal_ref_display() {
        assert_eq!(SignalRef::local("velocity").to_string(), "velocity");
        assert_eq!(SignalRef::indexed("tensor", 3).to_string(), "tensor[3]");
        assert_eq!(SignalRef::remote("altitude", "navigator").to_string(), "navigator.altitude");
    }

    #[test]
    fn semantic_node_with_mask() {
        let node = ConstraintNode::Semantic(SemanticNode {
            signal: SignalRef::local("object_class"),
            allowed_classes: vec!["VEHICLE".into(), "PEDESTRIAN".into(), "CYCLIST".into()],
            mask: Some(0x07),
            severity: Severity::Hard,
        });
        assert_eq!(node.leaf_count(), 1);
        assert_eq!(node.max_severity(), Severity::Hard);
    }
}

// === Temporal Extensions (v3.0) ===

/// Temporal failure mode — not every failure is a catastrophe
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum TemporalFault {
    Timeout,         // Deadline exceeded
    WatchExpired,    // Watched signal didn't change in time
    StaleValue,      // Value received but too old
    DriftExceeded,   // Signal drifting beyond threshold
}

/// Checkpoint for state reversion
#[derive(Debug, Clone, PartialEq)]
pub struct Checkpoint {
    pub id: u8,
    pub cycle_created: u32,
    pub description: String,
}

/// Temporal constraint: enforce with deadline and fallback
#[derive(Debug, Clone, PartialEq)]
pub struct TemporalBoundNode {
    pub inner: BoundNode,
    pub deadline_cycles: u32,
    pub on_timeout: Box<ConstraintNode>,  // fallback constraint
}

/// Temporal delegate: delegate with timeout and revert semantics
#[derive(Debug, Clone, PartialEq)]
pub struct TemporalDelegateNode {
    pub source_agent: String,
    pub target_agent: String,
    pub constraint: Box<ConstraintNode>,
    pub protocol: DelegateProtocol,
    pub deadline_cycles: u32,
    pub on_timeout: Box<ConstraintNode>,  // degraded mode
}

/// Drift monitor: detect constraint violations BEFORE they happen
#[derive(Debug, Clone, PartialEq)]
pub struct DriftMonitorNode {
    pub signal: SignalRef,
    pub checkpoint: String,          // named checkpoint reference
    pub warning_threshold: Value,     // switch to degraded mode
    pub violation_threshold: Value,   // hard fault
    pub severity: Severity,
}

impl ConstraintNode {
    /// Check if this node has temporal semantics (deadlines, checkpoints, watches)
    pub fn has_temporal(&self) -> bool {
        match self {
            ConstraintNode::Delegate(d) => matches!(d.protocol, DelegateProtocol::Async | DelegateProtocol::CoIterate),
            ConstraintNode::And(cs) | ConstraintNode::Or(cs) => cs.iter().any(|c| c.has_temporal()),
            ConstraintNode::Not(c) => c.has_temporal(),
            ConstraintNode::Implies(a, b) => a.has_temporal() || b.has_temporal(),
            _ => false,
        }
    }
}
