use crate::error::{FluxError, Result};
use crate::instruction::{FluxInstruction, InstructionMetadata};
use crate::opcode::FluxOpcode;

/// A collection of FLUX instructions representing a complete program or module.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct FluxBytecode {
    /// The instruction sequence.
    pub instructions: Vec<FluxInstruction>,
}

impl FluxBytecode {
    /// Create an empty bytecode object.
    pub fn new() -> Self {
        Self::default()
    }

    /// Create bytecode from a vector of instructions.
    pub fn from_instructions(instructions: Vec<FluxInstruction>) -> Self {
        Self { instructions }
    }

    /// Append an instruction.
    pub fn push(&mut self, instruction: FluxInstruction) {
        self.instructions.push(instruction);
    }

    /// Encode the full instruction sequence into a compact binary representation.
    ///
    /// Binary layout per instruction:
    /// ```text
    /// +--------+--------+--------+--------+
    /// | opcode |  argc  | flags  | reserved|
    /// +--------+--------+--------+--------+
    /// |          operand[0] (8 bytes)       |
    /// +-------------------------------------+
    /// |          operand[1] (8 bytes)       |
    /// +-------------------------------------+
    /// ```
    pub fn encode(&self) -> Vec<u8> {
        let mut buf = Vec::with_capacity(
            self.instructions.iter().map(|i| i.encoded_size()).sum(),
        );

        for inst in &self.instructions {
            buf.push(inst.opcode as u8);
            let argc = inst.operands.len();
            assert!(argc <= u8::MAX as usize, "too many operands for encoding");
            buf.push(argc as u8);
            buf.push(0x00); // flags (reserved)
            buf.push(0x00); // reserved
            for &op in &inst.operands {
                buf.extend_from_slice(&op.to_le_bytes());
            }
        }

        buf
    }

    /// Decode a byte slice back into a `FluxBytecode`.
    pub fn decode(bytes: &[u8]) -> Result<Self> {
        let mut instructions = Vec::new();
        let mut offset = 0usize;

        while offset < bytes.len() {
            if offset + 4 > bytes.len() {
                return Err(FluxError::MalformedBytecode(format!(
                    "incomplete instruction header at offset {}",
                    offset
                )));
            }

            let opcode_byte = bytes[offset];
            let argc = bytes[offset + 1] as usize;
            // bytes[offset + 2] and bytes[offset + 3] are reserved/flags

            let opcode = FluxOpcode::from_u8(opcode_byte)
                .ok_or(FluxError::InvalidOpcode(opcode_byte))?;

            let payload_start = offset + 4;
            let payload_end = payload_start + argc * 8;

            if payload_end > bytes.len() {
                return Err(FluxError::MalformedBytecode(format!(
                    "instruction at offset {} needs {} operand bytes but only {} remain",
                    offset,
                    argc * 8,
                    bytes.len().saturating_sub(payload_start)
                )));
            }

            let mut operands = Vec::with_capacity(argc);
            for i in 0..argc {
                let start = payload_start + i * 8;
                let chunk = &bytes[start..start + 8];
                let mut le_bytes = [0u8; 8];
                le_bytes.copy_from_slice(chunk);
                operands.push(f64::from_le_bytes(le_bytes));
            }

            instructions.push(FluxInstruction::with_operands(opcode, operands));
            offset = payload_end;
        }

        Ok(Self { instructions })
    }

    /// Validate the instruction sequence for basic correctness.
    ///
    /// Checks performed:
    /// - Every jump target operand points to a valid instruction index.
    /// - The program does not fall off the end (last instruction should be Halt or Return).
    /// - Stack effect is non-negative for the whole program (basic static check).
    pub fn validate(&self) -> Result<()> {
        let len = self.instructions.len();
        if len == 0 {
            return Err(FluxError::ValidationError(
                "bytecode contains no instructions".to_string(),
            ));
        }

        let last = &self.instructions[len - 1];
        if last.opcode != FluxOpcode::Halt && last.opcode != FluxOpcode::Return {
            return Err(FluxError::ValidationError(
                "program must end with Halt or Return".to_string(),
            ));
        }

        // Check jump targets and basic stack effect.
        let mut min_stack: isize = 0;
        let mut stack: isize = 0;

        for (idx, inst) in self.instructions.iter().enumerate() {
            // Validate jump targets for flow-control opcodes that take an address operand.
            match inst.opcode {
                FluxOpcode::Jump | FluxOpcode::Branch | FluxOpcode::Call => {
                    if let Some(&target) = inst.operands.first() {
                        let t = target as usize;
                        if t >= len {
                            return Err(FluxError::ValidationError(format!(
                                "instruction {} ({:?}) jumps to invalid target {}",
                                idx, inst.opcode, t
                            )));
                        }
                    } else {
                        return Err(FluxError::ValidationError(format!(
                            "instruction {} ({:?}) missing jump target operand",
                            idx, inst.opcode
                        )));
                    }
                }
                _ => {}
            }

            let inputs = inst.opcode.stack_inputs() as isize;
            let outputs = inst.opcode.stack_outputs() as isize;

            stack -= inputs;
            if stack < min_stack {
                min_stack = stack;
            }
            stack += outputs;
        }

        if min_stack < 0 {
            return Err(FluxError::ValidationError(format!(
                "stack underflow detected (minimum stack depth: {})",
                min_stack
            )));
        }

        Ok(())
    }

    /// Produce a human-readable disassembly of the bytecode.
    pub fn disassemble(&self) -> String {
        let mut out = String::new();
        out.push_str("; FLUX Bytecode Disassembly\n");
        out.push_str("; -------------------------\n");

        for (idx, inst) in self.instructions.iter().enumerate() {
            let label_prefix = if let Some(label) = &inst.metadata.label {
                format!("{}:\n", label)
            } else {
                String::new()
            };

            let loc_comment = if let Some(loc) = &inst.metadata.source_location {
                format!(" ; src: {}", loc)
            } else {
                String::new()
            };

            let op_str = format!("{:?}", inst.opcode);
            let operand_str = if inst.operands.is_empty() {
                String::new()
            } else {
                let parts: Vec<String> = inst
                    .operands
                    .iter()
                    .map(|v| {
                        if v.fract() == 0.0 {
                            format!("{:.0}", v)
                        } else {
                            format!("{}", v)
                        }
                    })
                    .collect();
                format!(" {}", parts.join(", "))
            };

            out.push_str(&format!(
                "{:04X}  {:8} {}{}\n",
                idx,
                op_str.to_uppercase(),
                operand_str,
                loc_comment
            ));

            if !label_prefix.is_empty() {
                out.insert_str(out.len() - operand_str.len() - op_str.len() - 10, &label_prefix);
            }
        }

        out
    }

    /// Build a map from label name to instruction index.
    pub fn label_map(&self) -> std::collections::HashMap<String, usize> {
        let mut map = std::collections::HashMap::new();
        for (idx, inst) in self.instructions.iter().enumerate() {
            if let Some(label) = &inst.metadata.label {
                map.insert(label.clone(), idx);
            }
        }
        map
    }
}

impl From<Vec<FluxInstruction>> for FluxBytecode {
    fn from(instructions: Vec<FluxInstruction>) -> Self {
        Self::from_instructions(instructions)
    }
}

impl IntoIterator for FluxBytecode {
    type Item = FluxInstruction;
    type IntoIter = std::vec::IntoIter<FluxInstruction>;

    fn into_iter(self) -> Self::IntoIter {
        self.instructions.into_iter()
    }
}
