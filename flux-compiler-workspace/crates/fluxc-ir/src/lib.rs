//! fluxc-ir — FLUX intermediate representation.

use thiserror::Error;

/// IR error type.
#[derive(Error, Debug)]
pub enum IrError {
    #[error("invalid IR: {msg}")]
    Invalid { msg: String },

    #[error("verification failed: {msg}")]
    VerificationFailed { msg: String },
}

/// Reason for a halt instruction.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum HaltReason {
    /// Constraint satisfied, normal termination.
    Pass,
    /// Constraint violated.
    Violation { slot: u8 },
    /// Unreachable code reached.
    Unreachable,
}

/// A FLUX intermediate representation instruction.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum FluxIR {
    /// Check that slot value is in `[lo, hi]`.
    CheckRange { slot: u8, lo: i64, hi: i64 },
    /// Check that slot bits match `mask`.
    CheckDomain { slot: u8, mask: u64 },
    /// Check that slot equals `value`.
    CheckExact { slot: u8, value: i64 },
    /// Logical AND of the two preceding results.
    And,
    /// Logical OR of the two preceding results.
    Or,
    /// Negate the preceding result.
    Not,
    /// Halt execution with a reason.
    Halt { reason: HaltReason },
    /// No-op / placeholder.
    Nop,
}

/// A basic block of IR instructions.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BasicBlock {
    pub label: String,
    pub instructions: Vec<FluxIR>,
}

impl BasicBlock {
    pub fn new(label: &str) -> Self {
        Self {
            label: label.to_string(),
            instructions: Vec::new(),
        }
    }
}

/// A complete IR module.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IrModule {
    pub name: String,
    pub blocks: Vec<BasicBlock>,
}

impl IrModule {
    pub fn new(name: &str) -> Self {
        Self {
            name: name.to_string(),
            blocks: Vec::new(),
        }
    }
}
