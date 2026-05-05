//! FLUX ISA opcodes — 21 essential operations stripped from the full 35.

/// Opcode representation — `#[repr(u8)]` for direct byte mapping.
#[repr(u8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FluxOpcode {
    // Arithmetic
    Add = 0x01,
    Sub = 0x02,
    Mul = 0x03,
    Div = 0x04,
    Mod = 0x05,
    // Comparison
    Eq  = 0x10,
    Lt  = 0x11,
    Gt  = 0x12,
    Lte = 0x13,
    Gte = 0x14,
    // Constraint
    Assert    = 0x20,
    Check     = 0x21,
    Validate  = 0x22,
    Reject    = 0x23,
    // Stack
    Load = 0x30,
    Push = 0x31,
    Pop  = 0x32,
    // Transform
    Snap      = 0x40,
    Quantize  = 0x41,
    // Control
    Halt = 0xF0,
    Nop  = 0xFF,
}

impl FluxOpcode {
    /// Convert raw byte to opcode. Returns `None` for unknown values.
    #[inline(always)]
    pub const fn from_u8(byte: u8) -> Option<Self> {
        match byte {
            0x01 => Some(Self::Add),
            0x02 => Some(Self::Sub),
            0x03 => Some(Self::Mul),
            0x04 => Some(Self::Div),
            0x05 => Some(Self::Mod),
            0x10 => Some(Self::Eq),
            0x11 => Some(Self::Lt),
            0x12 => Some(Self::Gt),
            0x13 => Some(Self::Lte),
            0x14 => Some(Self::Gte),
            0x20 => Some(Self::Assert),
            0x21 => Some(Self::Check),
            0x22 => Some(Self::Validate),
            0x23 => Some(Self::Reject),
            0x30 => Some(Self::Load),
            0x31 => Some(Self::Push),
            0x32 => Some(Self::Pop),
            0x40 => Some(Self::Snap),
            0x41 => Some(Self::Quantize),
            0xF0 => Some(Self::Halt),
            0xFF => Some(Self::Nop),
            _ => None,
        }
    }
}
