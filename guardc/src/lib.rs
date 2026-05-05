//! # guardc — GUARD → FLUX Verified Compiler
//!
//! A constraint-specification compiler that targets the FLUX 43-opcode
//! stack VM and emits independently-checkable proof certificates.
//!
//! ## Pipeline
//!
//! ```text
//! GUARD Source → AST → CIR → LCIR → FLUX Bytecode + Proof Certificate
//! ```
//!
//! ## Key Modules
//!
//! | Module | Purpose |
//! |--------|---------|
//! | `ast` | Raw syntax tree from the parser |
//! | `cir` | Constraint IR — relational, quantified, temporal |
//! | `lcir`| Lowered CIR — flat, ANF, explicit CFG |
//! | `lower` | Lowering passes (quantifier elimination, temporal expansion) |
//! | `codegen` | LCIR → FLUX bytecode emitter |
//! | `proof` | SMT-LIB VC generation + certificate construction |
//! | `compiler` | Orchestration pipeline |

pub mod ast;
pub mod cir;
pub mod codegen;
pub mod compiler;
pub mod error;
pub mod lcir;
pub mod lower;
pub mod proof;

pub use compiler::{compile, CompileOutput};
pub use error::{GuardError, Result, Span};
