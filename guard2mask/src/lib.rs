//! GUARD-to-Mask Compiler
//!
//! Compiles GUARD DSL safety constraints to GDSII mask patterns for FLUX-LUCID hardware.
//!
//! Pipeline: GUARD source → parse → compile → FLUX bytecode → VM execution
//!
//! # Example
//! ```rust
//! use guard2mask::{parse_guard, compile};
//!
//! let src = r#"
//!     constraint altitude @priority(HARD) {
//!         range(0, 15000)
//!         bitmask(0x3F)
//!     }
//! "#;
//! let items = parse_guard(src).unwrap();
//! let program = compile(&items);
//! // program.bytecode is now FLUX bytecode ready for flux-vm
//! ```

pub mod types;
pub mod parser;
pub mod solver;
pub mod via_gen;
pub mod compiler;

pub use types::*;
pub use parser::*;
pub use solver::*;
pub use via_gen::*;
pub use compiler::*;
