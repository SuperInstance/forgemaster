use serde::{Deserialize, Serialize};
use uuid::Uuid;
use crate::instruction::Instruction;

/// A compiled FLUX bytecode program.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Bytecode {
    pub id: Uuid,
    pub instructions: Vec<Instruction>,
    pub label: Option<String>,
}

impl Bytecode {
    pub fn new(instructions: Vec<Instruction>) -> Self {
        Bytecode {
            id: Uuid::new_v4(),
            instructions,
            label: None,
        }
    }

    pub fn with_label(mut self, label: impl Into<String>) -> Self {
        self.label = Some(label.into());
        self
    }

    /// Encode the entire program to bytes.
    pub fn encode(&self) -> Vec<u8> {
        let mut out = Vec::new();
        for instr in &self.instructions {
            out.extend(instr.encode());
        }
        out
    }

    /// Decode a program from bytes.
    pub fn decode(bytes: &[u8]) -> Option<Self> {
        let mut instructions = Vec::new();
        let mut pos = 0;
        while pos < bytes.len() {
            let (instr, consumed) = Instruction::decode(&bytes[pos..])?;
            instructions.push(instr);
            pos += consumed;
        }
        Some(Bytecode::new(instructions))
    }

    pub fn len(&self) -> usize {
        self.instructions.len()
    }

    pub fn is_empty(&self) -> bool {
        self.instructions.is_empty()
    }
}

/// Result of a bytecode execution.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionResult {
    pub bytecode_id: Uuid,
    pub success: bool,
    pub final_stack: Vec<f64>,
    pub steps_executed: u64,
    pub constraint_checks: u64,
    pub violations: u64,
    pub elapsed_ms: f64,
    pub instructions_per_sec: f64,
    pub error: Option<String>,
}
