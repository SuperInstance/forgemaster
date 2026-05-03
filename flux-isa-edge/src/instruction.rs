use serde::{Deserialize, Serialize};
use crate::opcode::OpCode;

/// A single FLUX instruction.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Instruction {
    pub opcode: OpCode,
    /// Optional immediate operand.
    pub operand: Option<f64>,
}

impl Instruction {
    pub fn new(opcode: OpCode) -> Self {
        Instruction { opcode, operand: None }
    }

    pub fn with_operand(opcode: OpCode, operand: f64) -> Self {
        Instruction { opcode, operand: Some(operand) }
    }

    /// Encode to bytes: [opcode, operand_flag, optional 8-byte f64].
    pub fn encode(&self) -> Vec<u8> {
        let mut out = vec![self.opcode.byte()];
        if let Some(v) = self.operand {
            out.push(1);
            out.extend_from_slice(&v.to_le_bytes());
        } else {
            out.push(0);
        }
        out
    }

    /// Decode one instruction from a byte slice, returning (instruction, bytes_consumed).
    pub fn decode(bytes: &[u8]) -> Option<(Self, usize)> {
        if bytes.is_empty() {
            return None;
        }
        let opcode = OpCode::from_byte(bytes[0])?;
        if bytes.len() < 2 {
            return None;
        }
        let has_operand = bytes[1] != 0;
        if has_operand {
            if bytes.len() < 10 {
                return None;
            }
            let v = f64::from_le_bytes(bytes[2..10].try_into().ok()?);
            Some((Instruction::with_operand(opcode, v), 10))
        } else {
            Some((Instruction::new(opcode), 2))
        }
    }
}

impl std::fmt::Display for Instruction {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self.operand {
            Some(v) => write!(f, "{} {}", self.opcode, v),
            None => write!(f, "{}", self.opcode),
        }
    }
}
