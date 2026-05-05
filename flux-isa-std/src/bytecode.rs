use serde::{Deserialize, Serialize};
use thiserror::Error;

use crate::instruction::FluxInstruction;
use crate::opcode::FluxOpCode;

pub const FLUX_MAGIC: [u8; 4] = [0x46, 0x4C, 0x55, 0x58]; // "FLUX"
pub const FLUX_VERSION: u16 = 1;

#[derive(Debug, Error)]
pub enum BytecodeError {
    #[error("Invalid magic bytes: expected 0xFLUX")]
    InvalidMagic,
    #[error("Unsupported version: {0}")]
    UnsupportedVersion(u16),
    #[error("Decode error at offset {offset}: {reason}")]
    DecodeError { offset: usize, reason: String },
    #[error("Validation error: {0}")]
    ValidationError(String),
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
}

/// FLUX bytecode container
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FluxBytecode {
    pub version: u16,
    pub instructions: Vec<FluxInstruction>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub metadata: Option<BytecodeMetadata>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BytecodeMetadata {
    pub created: String,
    pub source: Option<String>,
    pub author: Option<String>,
}

impl FluxBytecode {
    pub fn new(instructions: Vec<FluxInstruction>) -> Self {
        Self {
            version: FLUX_VERSION,
            instructions,
            metadata: None,
        }
    }

    pub fn with_metadata(mut self, meta: BytecodeMetadata) -> Self {
        self.metadata = Some(meta);
        self
    }

    /// Encode to binary format: magic(4) + version(2 LE) + instr_count(4 LE) + instructions
    pub fn encode(&self) -> Vec<u8> {
        let mut buf = Vec::new();
        buf.extend_from_slice(&FLUX_MAGIC);
        buf.extend_from_slice(&self.version.to_le_bytes());
        buf.extend_from_slice(&(self.instructions.len() as u32).to_le_bytes());
        for instr in &self.instructions {
            buf.extend(instr.encode());
        }
        buf
    }

    /// Decode binary format
    pub fn decode(bytes: &[u8]) -> Result<Self, BytecodeError> {
        if bytes.len() < 10 {
            return Err(BytecodeError::DecodeError {
                offset: 0,
                reason: "Bytecode too short".into(),
            });
        }
        if &bytes[0..4] != &FLUX_MAGIC {
            return Err(BytecodeError::InvalidMagic);
        }
        let version = u16::from_le_bytes([bytes[4], bytes[5]]);
        if version > FLUX_VERSION {
            return Err(BytecodeError::UnsupportedVersion(version));
        }
        let count = u32::from_le_bytes([bytes[6], bytes[7], bytes[8], bytes[9]]) as usize;
        let mut instructions = Vec::with_capacity(count);
        let mut offset = 10;
        for _ in 0..count {
            let (instr, consumed) = FluxInstruction::decode(bytes, offset).map_err(|e| {
                BytecodeError::DecodeError {
                    offset,
                    reason: e,
                }
            })?;
            instructions.push(instr);
            offset += consumed;
        }
        Ok(Self {
            version,
            instructions,
            metadata: None,
        })
    }

    /// Validate instruction sequence
    pub fn validate(&self) -> Result<(), BytecodeError> {
        for (i, instr) in self.instructions.iter().enumerate() {
            // Check operand count
            let expected = instr.opcode.operand_count();
            if instr.operands.len() < expected {
                return Err(BytecodeError::ValidationError(format!(
                    "Instruction {} ({}): expected at least {} operands, got {}",
                    i, instr.opcode, expected, instr.operands.len()
                )));
            }
            // Check jump targets
            if instr.opcode == FluxOpCode::Jmp || instr.opcode == FluxOpCode::Call {
                if let Some(&target) = instr.operands.first() {
                    let t = target as usize;
                    if t >= self.instructions.len() {
                        return Err(BytecodeError::ValidationError(format!(
                            "Instruction {} ({}): jump target {} out of range (max {})",
                            i, instr.opcode, t, self.instructions.len() - 1
                        )));
                    }
                }
            }
            // Division by zero guard
            if instr.opcode == FluxOpCode::Div || instr.opcode == FluxOpCode::Mod {
                if let Some(&v) = instr.operands.first() {
                    if v == 0.0 {
                        return Err(BytecodeError::ValidationError(format!(
                            "Instruction {} ({}): literal division by zero",
                            i, instr.opcode
                        )));
                    }
                }
            }
        }
        Ok(())
    }

    /// Human-readable disassembly
    pub fn disassemble(&self) -> String {
        let mut out = String::new();
        out.push_str(&format!("FLUX bytecode v{}\n", self.version));
        out.push_str(&format!("{} instructions\n\n", self.instructions.len()));
        for (i, instr) in self.instructions.iter().enumerate() {
            out.push_str(&format!("{:04}  {}\n", i, instr));
        }
        out
    }

    /// Save to file
    pub fn save_to_file(&self, path: &str) -> Result<(), BytecodeError> {
        let bytes = self.encode();
        std::fs::write(path, bytes)?;
        Ok(())
    }

    /// Load from file
    pub fn load_from_file(path: &str) -> Result<Self, BytecodeError> {
        let bytes = std::fs::read(path)?;
        Self::decode(&bytes)
    }

    /// Serialize to JSON string
    pub fn to_json(&self) -> Result<String, BytecodeError> {
        Ok(serde_json::to_string_pretty(self)?)
    }

    /// Deserialize from JSON string
    pub fn from_json(json: &str) -> Result<Self, BytecodeError> {
        Ok(serde_json::from_str(json)?)
    }
}
