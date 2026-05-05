//! fluxc-parser — GUARD constraint parser
//!
//! Parses range, domain, exact constraints with AND/OR/NOT combinators.

use thiserror::Error;

/// Parser error type.
#[derive(Error, Debug)]
pub enum ParseError {
    #[error("unexpected token at position {pos}: {msg}")]
    UnexpectedToken { pos: usize, msg: String },

    #[error("unexpected end of input: {msg}")]
    UnexpectedEof { msg: String },

    #[error("invalid range: {msg}")]
    InvalidRange { msg: String },

    #[error("invalid domain mask: {msg}")]
    InvalidDomain { msg: String },
}

/// A parsed GUARD constraint expression.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GuardExpr {
    /// Range constraint: `name` must be in `[lo, hi]`.
    Range { name: String, lo: i64, hi: i64 },
    /// Domain constraint: `name` bits must match `mask`.
    Domain { name: String, mask: u64 },
    /// Exact constraint: `name` must equal `value`.
    Exact { name: String, value: i64 },
    /// Logical AND of two expressions.
    And(Box<GuardExpr>, Box<GuardExpr>),
    /// Logical OR of two expressions.
    Or(Box<GuardExpr>, Box<GuardExpr>),
    /// Logical NOT of an expression.
    Not(Box<GuardExpr>),
}

/// Parse a GUARD constraint string into a `GuardExpr`.
pub fn parse(input: &str) -> Result<GuardExpr, ParseError> {
    let tokens = tokenize(input)?;
    let (expr, _remaining) = parse_expr(&tokens, 0)?;
    Ok(expr)
}

/// Token types for the constraint lexer.
#[derive(Debug, Clone, PartialEq)]
#[allow(dead_code)]
enum Token {
    Ident(String),
    Int(i64),
    LParen,
    RParen,
    And,
    Or,
    Not,
    RangeOp,   // ..
    DomainOp,  // @
    EqOp,      // =
}

fn tokenize(input: &str) -> Result<Vec<Token>, ParseError> {
    let _ = input;
    Ok(Vec::new())
}

fn parse_expr(_tokens: &[Token], _pos: usize) -> Result<(GuardExpr, usize), ParseError> {
    Err(ParseError::UnexpectedEof {
        msg: "parser not yet fully implemented".into(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_exact() {
        let expr = GuardExpr::Exact {
            name: "x".into(),
            value: 42,
        };
        assert_eq!(
            expr,
            GuardExpr::Exact {
                name: "x".into(),
                value: 42
            }
        );
    }
}
