use std::fmt;

/// Errors that can occur in the FLUX ISA.
#[derive(Debug, Clone, PartialEq)]
pub enum FluxError {
    /// An invalid opcode byte was encountered during decoding.
    InvalidOpcode(u8),
    /// The bytecode buffer is too short or malformed.
    MalformedBytecode(String),
    /// A validation error in the instruction sequence.
    ValidationError(String),
    /// A runtime VM error during execution.
    ExecutionError(String),
    /// An arithmetic error (e.g., division by zero).
    ArithmeticError(String),
    /// A stack underflow occurred.
    StackUnderflow,
    /// A stack overflow occurred.
    StackOverflow,
    /// An invalid jump target was specified.
    InvalidJumpTarget(usize),
    /// A constraint was violated during execution.
    ConstraintViolation(String),
}

impl fmt::Display for FluxError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            FluxError::InvalidOpcode(op) => write!(f, "invalid opcode: 0x{:02X}", op),
            FluxError::MalformedBytecode(msg) => write!(f, "malformed bytecode: {}", msg),
            FluxError::ValidationError(msg) => write!(f, "validation error: {}", msg),
            FluxError::ExecutionError(msg) => write!(f, "execution error: {}", msg),
            FluxError::ArithmeticError(msg) => write!(f, "arithmetic error: {}", msg),
            FluxError::StackUnderflow => write!(f, "stack underflow"),
            FluxError::StackOverflow => write!(f, "stack overflow"),
            FluxError::InvalidJumpTarget(target) => write!(f, "invalid jump target: {}", target),
            FluxError::ConstraintViolation(msg) => write!(f, "constraint violation: {}", msg),
        }
    }
}

impl std::error::Error for FluxError {}

/// Shorthand result type used throughout the crate.
pub type Result<T> = std::result::Result<T, FluxError>;
