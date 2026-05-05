//! FLUX ISA — Instruction Set Architecture for Constraint Compilation
//!
//! The FLUX ISA defines the bytecode format and virtual machine for
//! executing compiled constraint satisfaction problems. The architecture
//! is stack-based with constraint checking at each execution step.

pub mod bytecode;
pub mod error;
pub mod instruction;
pub mod opcode;
pub mod vm;

pub use bytecode::FluxBytecode;
pub use error::FluxError;
pub use instruction::FluxInstruction;
pub use opcode::FluxOpcode;
pub use vm::{ConstraintVM, VMResult};
