use serde::{Deserialize, Serialize};
use std::fmt;

/// Opcode groups — 8 functional categories for the FLUX ISA
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum OpCodeGroup {
    Stack,      // 0x00–0x0F: Push, pop, dup, swap
    Arithmetic, // 0x10–0x1F: Add, sub, mul, div, mod
    Logic,      // 0x20–0x2F: And, or, not, xor
    Comparison, // 0x30–0x3F: Eq, ne, lt, gt, le, ge
    Control,    // 0x40–0x4F: Jmp, call, ret, halt
    Memory,     // 0x50–0x5F: Load, store, alloc, free
    Constraint, // 0x60–0x6F: Assert, check, solve, bind
    IO,         // 0x70–0x7F: Read, write, flush, sync
}

/// All 35 FLUX ISA opcodes
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum FluxOpCode {
    // Stack (7)
    Push,       // 0x01
    Pop,        // 0x02
    Dup,        // 0x03
    Swap,       // 0x04
    Over,       // 0x05
    Rot,        // 0x06
    Depth,      // 0x07

    // Arithmetic (7)
    Add,        // 0x10
    Sub,        // 0x11
    Mul,        // 0x12
    Div,        // 0x13
    Mod,        // 0x14
    Negate,     // 0x15
    Abs,        // 0x16

    // Logic (5)
    And,        // 0x20
    Or,         // 0x21
    Not,        // 0x22
    Xor,        // 0x23
    Shl,        // 0x24

    // Comparison (6)
    Eq,         // 0x30
    Ne,         // 0x31
    Lt,         // 0x32
    Gt,         // 0x33
    Le,         // 0x34
    Ge,         // 0x35

    // Control (5)
    Jmp,        // 0x40
    Call,       // 0x41
    Ret,        // 0x42
    Halt,       // 0x43
    Nop,        // 0x44

    // Memory (3)
    Load,       // 0x50
    Store,      // 0x51
    LoadConst,  // 0x52

    // Constraint (2)
    Assert,     // 0x60
    Check,      // 0x61

    // IO (2)
    Print,      // 0x70
    Emit,       // 0x71
}

impl FluxOpCode {
    pub fn from_byte(byte: u8) -> Option<Self> {
        match byte {
            0x01 => Some(Self::Push),
            0x02 => Some(Self::Pop),
            0x03 => Some(Self::Dup),
            0x04 => Some(Self::Swap),
            0x05 => Some(Self::Over),
            0x06 => Some(Self::Rot),
            0x07 => Some(Self::Depth),
            0x10 => Some(Self::Add),
            0x11 => Some(Self::Sub),
            0x12 => Some(Self::Mul),
            0x13 => Some(Self::Div),
            0x14 => Some(Self::Mod),
            0x15 => Some(Self::Negate),
            0x16 => Some(Self::Abs),
            0x20 => Some(Self::And),
            0x21 => Some(Self::Or),
            0x22 => Some(Self::Not),
            0x23 => Some(Self::Xor),
            0x24 => Some(Self::Shl),
            0x30 => Some(Self::Eq),
            0x31 => Some(Self::Ne),
            0x32 => Some(Self::Lt),
            0x33 => Some(Self::Gt),
            0x34 => Some(Self::Le),
            0x35 => Some(Self::Ge),
            0x40 => Some(Self::Jmp),
            0x41 => Some(Self::Call),
            0x42 => Some(Self::Ret),
            0x43 => Some(Self::Halt),
            0x44 => Some(Self::Nop),
            0x50 => Some(Self::Load),
            0x51 => Some(Self::Store),
            0x52 => Some(Self::LoadConst),
            0x60 => Some(Self::Assert),
            0x61 => Some(Self::Check),
            0x70 => Some(Self::Print),
            0x71 => Some(Self::Emit),
            _ => None,
        }
    }

    pub fn to_byte(self) -> u8 {
        match self {
            Self::Push => 0x01,
            Self::Pop => 0x02,
            Self::Dup => 0x03,
            Self::Swap => 0x04,
            Self::Over => 0x05,
            Self::Rot => 0x06,
            Self::Depth => 0x07,
            Self::Add => 0x10,
            Self::Sub => 0x11,
            Self::Mul => 0x12,
            Self::Div => 0x13,
            Self::Mod => 0x14,
            Self::Negate => 0x15,
            Self::Abs => 0x16,
            Self::And => 0x20,
            Self::Or => 0x21,
            Self::Not => 0x22,
            Self::Xor => 0x23,
            Self::Shl => 0x24,
            Self::Eq => 0x30,
            Self::Ne => 0x31,
            Self::Lt => 0x32,
            Self::Gt => 0x33,
            Self::Le => 0x34,
            Self::Ge => 0x35,
            Self::Jmp => 0x40,
            Self::Call => 0x41,
            Self::Ret => 0x42,
            Self::Halt => 0x43,
            Self::Nop => 0x44,
            Self::Load => 0x50,
            Self::Store => 0x51,
            Self::LoadConst => 0x52,
            Self::Assert => 0x60,
            Self::Check => 0x61,
            Self::Print => 0x70,
            Self::Emit => 0x71,
        }
    }

    pub fn group(self) -> OpCodeGroup {
        match self {
            Self::Push | Self::Pop | Self::Dup | Self::Swap | Self::Over | Self::Rot | Self::Depth => OpCodeGroup::Stack,
            Self::Add | Self::Sub | Self::Mul | Self::Div | Self::Mod | Self::Negate | Self::Abs => OpCodeGroup::Arithmetic,
            Self::And | Self::Or | Self::Not | Self::Xor | Self::Shl => OpCodeGroup::Logic,
            Self::Eq | Self::Ne | Self::Lt | Self::Gt | Self::Le | Self::Ge => OpCodeGroup::Comparison,
            Self::Jmp | Self::Call | Self::Ret | Self::Halt | Self::Nop => OpCodeGroup::Control,
            Self::Load | Self::Store | Self::LoadConst => OpCodeGroup::Memory,
            Self::Assert | Self::Check => OpCodeGroup::Constraint,
            Self::Print | Self::Emit => OpCodeGroup::IO,
        }
    }

    /// Expected operand count
    pub fn operand_count(self) -> usize {
        match self {
            Self::Push => 1,
            Self::LoadConst => 1,
            Self::Jmp | Self::Call => 1,
            Self::Assert | Self::Check => 1,
            Self::Store => 1,
            _ => 0,
        }
    }
}

impl fmt::Display for FluxOpCode {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Push => write!(f, "PUSH"),
            Self::Pop => write!(f, "POP"),
            Self::Dup => write!(f, "DUP"),
            Self::Swap => write!(f, "SWAP"),
            Self::Over => write!(f, "OVER"),
            Self::Rot => write!(f, "ROT"),
            Self::Depth => write!(f, "DEPTH"),
            Self::Add => write!(f, "ADD"),
            Self::Sub => write!(f, "SUB"),
            Self::Mul => write!(f, "MUL"),
            Self::Div => write!(f, "DIV"),
            Self::Mod => write!(f, "MOD"),
            Self::Negate => write!(f, "NEGATE"),
            Self::Abs => write!(f, "ABS"),
            Self::And => write!(f, "AND"),
            Self::Or => write!(f, "OR"),
            Self::Not => write!(f, "NOT"),
            Self::Xor => write!(f, "XOR"),
            Self::Shl => write!(f, "SHL"),
            Self::Eq => write!(f, "EQ"),
            Self::Ne => write!(f, "NE"),
            Self::Lt => write!(f, "LT"),
            Self::Gt => write!(f, "GT"),
            Self::Le => write!(f, "LE"),
            Self::Ge => write!(f, "GE"),
            Self::Jmp => write!(f, "JMP"),
            Self::Call => write!(f, "CALL"),
            Self::Ret => write!(f, "RET"),
            Self::Halt => write!(f, "HALT"),
            Self::Nop => write!(f, "NOP"),
            Self::Load => write!(f, "LOAD"),
            Self::Store => write!(f, "STORE"),
            Self::LoadConst => write!(f, "LOADCONST"),
            Self::Assert => write!(f, "ASSERT"),
            Self::Check => write!(f, "CHECK"),
            Self::Print => write!(f, "PRINT"),
            Self::Emit => write!(f, "EMIT"),
        }
    }
}
