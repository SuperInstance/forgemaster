// FLUX ISA Standard Library — Embedded Linux constraint VM
// Raspberry Pi / BeagleBone / NanoPi / Jetson Nano edge nodes

pub mod opcode;
pub mod instruction;
pub mod bytecode;
pub mod vm;
pub mod gate;
pub mod sonar_physics;
pub mod pipeline;

pub use opcode::{FluxOpCode, OpCodeGroup};
pub use instruction::FluxInstruction;
pub use bytecode::{FluxBytecode, BytecodeError};
pub use vm::{FluxVM, VMError, VMConfig, ExecutionTrace};
pub use gate::{QualityGate, GateConfig, GateVerdict};
pub use sonar_physics::SonarPhysics;
pub use pipeline::{Pipeline, PipelineConfig, PipelineError};
