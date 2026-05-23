//! Minimal FLUX ISA constraint VM for bare-metal microcontrollers.
//!
//! Runs on ARM Cortex-M0+/M3/M4 — 8KB SRAM. No allocator. No std.
//! Sensor nodes validate sonar constraint checks before forwarding upstream.

#![no_std]

pub mod encode;
pub mod instruction;
pub mod opcode;
pub mod sonar_check;
pub mod vm;

pub use opcode::FluxOpcode;
pub use instruction::FluxInstruction;
pub use vm::{FluxVm, FluxResult, FluxError};
