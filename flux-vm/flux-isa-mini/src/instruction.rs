//! Fixed-size FLUX instruction — exactly 24 bytes.

use crate::opcode::FluxOpcode;

/// A single FLUX ISA instruction.
///
/// Layout (24 bytes):
///   [0]    opcode
///   [1]    padding / flags low
///   [2..10]  operand 0 (f64, LE)
///   [10..18] operand 1 (f64, LE)
///   [18..22] reserved
///   [22..24] flags
#[repr(C, packed)]
#[derive(Debug, Clone, Copy)]
pub struct FluxInstruction {
    pub opcode: FluxOpcode,
    _pad: u8,
    pub operands: [f64; 2],
    _reserved: [u8; 4],
    pub flags: u16,
}

/// Exact byte size of one instruction.
pub const FLUX_INSTRUCTION_SIZE: usize = 24;

impl FluxInstruction {
    /// Create a new instruction with up to 2 operands.
    #[inline(always)]
    pub const fn new(opcode: FluxOpcode, op0: f64, op1: f64) -> Self {
        Self {
            opcode,
            _pad: 0,
            operands: [op0, op1],
            _reserved: [0; 4],
            flags: 0,
        }
    }

    /// Create with flags.
    #[inline(always)]
    pub const fn with_flags(opcode: FluxOpcode, op0: f64, op1: f64, flags: u16) -> Self {
        Self {
            opcode,
            _pad: 0,
            operands: [op0, op1],
            _reserved: [0; 4],
            flags,
        }
    }
}

// Safety: FluxInstruction is #[repr(C, packed)] with no padding issues for
// byte-casting. All field types are Copy and have no alignment requirements
// that would cause UB when cast from a byte array.
unsafe impl Send for FluxInstruction {}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn size_is_24() {
        assert_eq!(core::mem::size_of::<FluxInstruction>(), 24);
    }
}
