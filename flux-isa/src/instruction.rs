use crate::opcode::FluxOpcode;

/// Additional metadata attached to an instruction for debugging and labelling.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct InstructionMetadata {
    /// An optional human-readable label (e.g., a branch target).
    pub label: Option<String>,
    /// An optional source location string (e.g., "file.flux:42:5").
    pub source_location: Option<String>,
}

impl InstructionMetadata {
    /// Create new empty metadata.
    pub fn new() -> Self {
        Self::default()
    }

    /// Set the label.
    pub fn with_label(mut self, label: impl Into<String>) -> Self {
        self.label = Some(label.into());
        self
    }

    /// Set the source location.
    pub fn with_source_location(mut self, loc: impl Into<String>) -> Self {
        self.source_location = Some(loc.into());
        self
    }
}

/// A single FLUX instruction.
#[derive(Debug, Clone, PartialEq)]
pub struct FluxInstruction {
    /// The operation to perform.
    pub opcode: FluxOpcode,
    /// Immediate operands encoded as `f64` values.
    pub operands: Vec<f64>,
    /// Metadata for debugging and flow-control resolution.
    pub metadata: InstructionMetadata,
}

impl FluxInstruction {
    /// Create a new instruction with the given opcode.
    pub fn new(opcode: FluxOpcode) -> Self {
        Self {
            opcode,
            operands: Vec::new(),
            metadata: InstructionMetadata::default(),
        }
    }

    /// Create a new instruction with operands.
    pub fn with_operands(opcode: FluxOpcode, operands: Vec<f64>) -> Self {
        Self {
            opcode,
            operands,
            metadata: InstructionMetadata::default(),
        }
    }

    /// Create a new instruction with operands and metadata.
    pub fn with_metadata(
        opcode: FluxOpcode,
        operands: Vec<f64>,
        metadata: InstructionMetadata,
    ) -> Self {
        Self {
            opcode,
            operands,
            metadata,
        }
    }

    /// Push an operand onto this instruction's operand list.
    pub fn operand(mut self, value: f64) -> Self {
        self.operands.push(value);
        self
    }

    /// Returns the total size of this instruction when encoded, in bytes.
    ///
    /// Format per instruction:
    ///   1 byte  – opcode
    ///   1 byte  – operand count (max 255)
    ///   2 bytes – reserved / flags (currently zero)
    ///   N×8 bytes – operand f64 values
    pub fn encoded_size(&self) -> usize {
        4 + self.operands.len() * 8
    }
}
