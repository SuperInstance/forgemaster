use serde::{Deserialize, Serialize};

use crate::opcode::FluxOpCode;

/// A single FLUX instruction with optional metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FluxInstruction {
    pub opcode: FluxOpCode,
    pub operands: Vec<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub label: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub source_location: Option<SourceLocation>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SourceLocation {
    pub line: usize,
    pub column: usize,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub file: Option<String>,
}

impl FluxInstruction {
    pub fn new(opcode: FluxOpCode) -> Self {
        Self {
            opcode,
            operands: Vec::new(),
            label: None,
            source_location: None,
        }
    }

    pub fn with_operand(mut self, value: f64) -> Self {
        self.operands.push(value);
        self
    }

    pub fn with_operands(mut self, values: &[f64]) -> Self {
        self.operands.extend_from_slice(values);
        self
    }

    pub fn with_label(mut self, label: impl Into<String>) -> Self {
        self.label = Some(label.into());
        self
    }

    pub fn with_source(mut self, line: usize, column: usize) -> Self {
        self.source_location = Some(SourceLocation {
            line,
            column,
            file: None,
        });
        self
    }

    /// Encode to bytes: [opcode_byte, operand_count, operand_bytes...]
    pub fn encode(&self) -> Vec<u8> {
        let mut buf = vec![self.opcode.to_byte(), self.operands.len() as u8];
        for &op in &self.operands {
            buf.extend_from_slice(&op.to_le_bytes());
        }
        buf
    }

    /// Decode from bytes starting at `offset`. Returns (instruction, bytes_consumed).
    pub fn decode(bytes: &[u8], offset: usize) -> Result<(Self, usize), String> {
        if offset >= bytes.len() {
            return Err("Unexpected end of bytecode".into());
        }
        let opcode = FluxOpCode::from_byte(bytes[offset])
            .ok_or_else(|| format!("Invalid opcode: 0x{:02X}", bytes[offset]))?;
        if offset + 1 >= bytes.len() {
            return Err("Missing operand count".into());
        }
        let count = bytes[offset + 1] as usize;
        let mut operands = Vec::with_capacity(count);
        let mut pos = offset + 2;
        for _ in 0..count {
            if pos + 8 > bytes.len() {
                return Err("Unexpected end of operands".into());
            }
            let bytes_arr: [u8; 8] = bytes[pos..pos + 8].try_into().unwrap();
            operands.push(f64::from_le_bytes(bytes_arr));
            pos += 8;
        }
        Ok((
            Self {
                opcode,
                operands,
                label: None,
                source_location: None,
            },
            pos - offset,
        ))
    }
}

impl std::fmt::Display for FluxInstruction {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        if let Some(ref label) = self.label {
            write!(f, "{}: ", label)?;
        }
        write!(f, "{}", self.opcode)?;
        for op in &self.operands {
            write!(f, " {}", op)?;
        }
        Ok(())
    }
}
