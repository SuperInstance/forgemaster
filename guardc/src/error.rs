//! Error types for the GUARD compiler.

use std::fmt;
use thiserror::Error;

/// A source span for error reporting.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct Span {
    pub file: String,
    pub start_line: u32,
    pub start_col: u32,
    pub end_line: u32,
    pub end_col: u32,
}

impl Span {
    pub fn new(file: impl Into<String>, line: u32, col: u32) -> Self {
        let file = file.into();
        Self {
            file,
            start_line: line,
            start_col: col,
            end_line: line,
            end_col: col,
        }
    }

    pub fn merge(&self, other: &Span) -> Span {
        Span {
            file: self.file.clone(),
            start_line: self.start_line.min(other.start_line),
            start_col: self.start_col.min(other.start_col),
            end_line: self.end_line.max(other.end_line),
            end_col: self.end_col.max(other.end_col),
        }
    }
}

impl fmt::Display for Span {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "{}:{}:{}-{}:{}",
            self.file, self.start_line, self.start_col, self.end_line, self.end_col
        )
    }
}

/// The main error type for `guardc`.
#[derive(Error, Debug, Clone)]
pub enum GuardError {
    #[error("parse error at {span}: {message}")]
    Parse { span: Span, message: String },

    #[error("type error at {span}: {message}")]
    Type { span: Span, message: String },

    #[error("unit mismatch at {span}: expected {expected}, got {got}")]
    UnitMismatch {
        span: Span,
        expected: String,
        got: String,
    },

    #[error("lowering error: {0}")]
    Lowering(String),

    #[error("codegen error: {0}")]
    Codegen(String),

    #[error("proof generation failed for '{obligation}': {reason}")]
    ProofFailed { obligation: String, reason: String },

    #[error("validation error: {0}")]
    Validation(String),
}

/// Result alias used throughout the compiler.
pub type Result<T> = std::result::Result<T, GuardError>;
