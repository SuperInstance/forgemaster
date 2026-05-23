/// FLUX ISA Thor — Heavyweight runtime for GPU-class edge.
///
/// Jetson Thor / AGX Orin / data-center GPU with CUDA acceleration,
/// batch CSP solving, fleet coordination, and full PLATO integration.

pub mod config;
pub mod cuda;
pub mod fleet;
pub mod opcode;
pub mod pipeline;
pub mod plato;
pub mod server;
pub mod vm;

pub use config::ThorConfig;
pub use opcode::{Opcode, ThorOpcode};
pub use vm::ThorVm;
