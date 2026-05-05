/// Every operation supported by the FLUX virtual machine.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
#[repr(u8)]
pub enum FluxOpcode {
    // ARITHMETIC
    Add = 0x01,
    Sub = 0x02,
    Mul = 0x03,
    Div = 0x04,
    Mod = 0x05,

    // CONSTRAINT
    Assert = 0x10,
    Check = 0x11,
    Validate = 0x12,
    Reject = 0x13,

    // FLOW
    Jump = 0x20,
    Branch = 0x21,
    Call = 0x22,
    Return = 0x23,
    Halt = 0x24,

    // MEMORY
    Load = 0x30,
    Store = 0x31,
    Push = 0x32,
    Pop = 0x33,
    Swap = 0x34,

    // CONVERT
    Snap = 0x40,
    Quantize = 0x41,
    Cast = 0x42,
    Promote = 0x43,

    // LOGIC
    And = 0x50,
    Or = 0x51,
    Not = 0x52,
    Xor = 0x53,

    // COMPARE
    Eq = 0x60,
    Neq = 0x61,
    Lt = 0x62,
    Gt = 0x63,
    Lte = 0x64,
    Gte = 0x65,

    // INT8 SATURATION (FLUX-X extended, not in FLUX-C certified subset)
    SatAdd = 0x28,
    SatSub = 0x29,
    Clip = 0x2A,
    Mad = 0x2B,
    Popcnt = 0x2C,
    Ctz = 0x2D,
    Pabs = 0x2E,
    Pmin = 0x2F,

    // SPECIAL
    Nop = 0x70,
    Debug = 0x71,
    Trace = 0x72,
    Dump = 0x73,
}

impl FluxOpcode {
    /// Convert a raw `u8` into an opcode.
    pub fn from_u8(value: u8) -> Option<Self> {
        match value {
            0x01 => Some(FluxOpcode::Add),
            0x02 => Some(FluxOpcode::Sub),
            0x03 => Some(FluxOpcode::Mul),
            0x04 => Some(FluxOpcode::Div),
            0x05 => Some(FluxOpcode::Mod),

            0x10 => Some(FluxOpcode::Assert),
            0x11 => Some(FluxOpcode::Check),
            0x12 => Some(FluxOpcode::Validate),
            0x13 => Some(FluxOpcode::Reject),

            0x20 => Some(FluxOpcode::Jump),
            0x21 => Some(FluxOpcode::Branch),
            0x22 => Some(FluxOpcode::Call),
            0x23 => Some(FluxOpcode::Return),
            0x24 => Some(FluxOpcode::Halt),

            0x30 => Some(FluxOpcode::Load),
            0x31 => Some(FluxOpcode::Store),
            0x32 => Some(FluxOpcode::Push),
            0x33 => Some(FluxOpcode::Pop),
            0x34 => Some(FluxOpcode::Swap),

            0x40 => Some(FluxOpcode::Snap),
            0x41 => Some(FluxOpcode::Quantize),
            0x42 => Some(FluxOpcode::Cast),
            0x43 => Some(FluxOpcode::Promote),

            0x50 => Some(FluxOpcode::And),
            0x51 => Some(FluxOpcode::Or),
            0x52 => Some(FluxOpcode::Not),
            0x53 => Some(FluxOpcode::Xor),

            0x60 => Some(FluxOpcode::Eq),
            0x61 => Some(FluxOpcode::Neq),
            0x62 => Some(FluxOpcode::Lt),
            0x63 => Some(FluxOpcode::Gt),
            0x64 => Some(FluxOpcode::Lte),
            0x65 => Some(FluxOpcode::Gte),

            0x28 => Some(FluxOpcode::SatAdd),
            0x29 => Some(FluxOpcode::SatSub),
            0x2A => Some(FluxOpcode::Clip),
            0x2B => Some(FluxOpcode::Mad),
            0x2C => Some(FluxOpcode::Popcnt),
            0x2D => Some(FluxOpcode::Ctz),
            0x2E => Some(FluxOpcode::Pabs),
            0x2F => Some(FluxOpcode::Pmin),

            0x70 => Some(FluxOpcode::Nop),
            0x71 => Some(FluxOpcode::Debug),
            0x72 => Some(FluxOpcode::Trace),
            0x73 => Some(FluxOpcode::Dump),

            _ => None,
        }
    }

    /// Returns the opcode group as a human-readable string.
    pub fn group(&self) -> &'static str {
        match self {
            FluxOpcode::Add | FluxOpcode::Sub | FluxOpcode::Mul | FluxOpcode::Div | FluxOpcode::Mod => "ARITHMETIC",
            FluxOpcode::Assert | FluxOpcode::Check | FluxOpcode::Validate | FluxOpcode::Reject => "CONSTRAINT",
            FluxOpcode::Jump | FluxOpcode::Branch | FluxOpcode::Call | FluxOpcode::Return | FluxOpcode::Halt => "FLOW",
            FluxOpcode::Load | FluxOpcode::Store | FluxOpcode::Push | FluxOpcode::Pop | FluxOpcode::Swap => "MEMORY",
            FluxOpcode::Snap | FluxOpcode::Quantize | FluxOpcode::Cast | FluxOpcode::Promote => "CONVERT",
            FluxOpcode::And | FluxOpcode::Or | FluxOpcode::Not | FluxOpcode::Xor => "LOGIC",
            FluxOpcode::Eq | FluxOpcode::Neq | FluxOpcode::Lt | FluxOpcode::Gt | FluxOpcode::Lte | FluxOpcode::Gte => "COMPARE",
            FluxOpcode::SatAdd | FluxOpcode::SatSub | FluxOpcode::Clip
            | FluxOpcode::Mad | FluxOpcode::Popcnt | FluxOpcode::Ctz
            | FluxOpcode::Pabs | FluxOpcode::Pmin => "INT8_SATURATION",

            FluxOpcode::Nop | FluxOpcode::Debug | FluxOpcode::Trace | FluxOpcode::Dump => "SPECIAL",
        }
    }

    /// Returns the number of stack operands this opcode consumes, if known statically.
    pub fn stack_inputs(&self) -> usize {
        match self {
            FluxOpcode::Add | FluxOpcode::Sub | FluxOpcode::Mul | FluxOpcode::Div | FluxOpcode::Mod => 2,
            FluxOpcode::And | FluxOpcode::Or | FluxOpcode::Xor => 2,
            FluxOpcode::Eq | FluxOpcode::Neq | FluxOpcode::Lt | FluxOpcode::Gt | FluxOpcode::Lte | FluxOpcode::Gte => 2,
            FluxOpcode::Not => 1,
            FluxOpcode::Push => 0,
            FluxOpcode::Pop => 1,
            FluxOpcode::Swap => 2,
            FluxOpcode::Assert | FluxOpcode::Check | FluxOpcode::Validate => 1,
            FluxOpcode::SatAdd | FluxOpcode::SatSub => 2,
            FluxOpcode::Clip => 3,  // value, lower, upper
            FluxOpcode::Mad => 3,    // a, b, c
            FluxOpcode::Popcnt | FluxOpcode::Ctz => 1,
            FluxOpcode::Pabs => 1,
            FluxOpcode::Pmin => 2,
            _ => 0,
        }
    }

    /// Returns the number of values this opcode pushes onto the stack.
    pub fn stack_outputs(&self) -> usize {
        match self {
            FluxOpcode::Add | FluxOpcode::Sub | FluxOpcode::Mul | FluxOpcode::Div | FluxOpcode::Mod => 1,
            FluxOpcode::And | FluxOpcode::Or | FluxOpcode::Not | FluxOpcode::Xor => 1,
            FluxOpcode::Eq | FluxOpcode::Neq | FluxOpcode::Lt | FluxOpcode::Gt | FluxOpcode::Lte | FluxOpcode::Gte => 1,
            FluxOpcode::Push => 1,
            FluxOpcode::Pop => 0,
            FluxOpcode::Swap => 2,
            FluxOpcode::Snap | FluxOpcode::Quantize | FluxOpcode::Cast | FluxOpcode::Promote => 1,
            FluxOpcode::SatAdd | FluxOpcode::SatSub => 1,
            FluxOpcode::Clip => 1,
            FluxOpcode::Mad => 1,
            FluxOpcode::Popcnt | FluxOpcode::Ctz => 1,
            FluxOpcode::Pabs => 1,
            FluxOpcode::Pmin => 1,
            _ => 0,
        }
    }
}
