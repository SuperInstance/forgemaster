use serde::{Deserialize, Serialize};
use std::fmt;

// ── Base 35 opcodes ──────────────────────────────────────────────

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[repr(u8)]
pub enum Opcode {
    // Stack / value
    Nop = 0x00,
    Push = 0x01,
    Pop = 0x02,
    Dup = 0x03,
    Swap = 0x04,
    Load = 0x05,
    Store = 0x06,

    // Arithmetic
    Add = 0x10,
    Sub = 0x11,
    Mul = 0x12,
    Div = 0x13,
    Mod = 0x14,
    Neg = 0x15,

    // Logic / comparison
    And = 0x20,
    Or = 0x21,
    Not = 0x22,
    Eq = 0x30,
    Ne = 0x31,
    Lt = 0x32,
    Le = 0x33,
    Gt = 0x34,
    Ge = 0x35,

    // Control flow
    Jmp = 0x40,
    Jz = 0x41,
    Jnz = 0x42,
    Call = 0x43,
    Ret = 0x44,
    Halt = 0x45,

    // CSP primitives
    Assert = 0x50,
    Constrain = 0x51,
    Propagate = 0x52,
    Solve = 0x53,
    Verify = 0x54,

    // I/O
    Print = 0x60,
    Debug = 0x61,
}

// ── Thor extended opcodes (0x80–0x87) ───────────────────────────

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[repr(u8)]
pub enum ThorOpcode {
    ParallelBranch = 0x80,
    Reduce = 0x81,
    GpuCompile = 0x82,
    BatchSolve = 0x83,
    SonarBatch = 0x84,
    TileCommit = 0x85,
    Pathfind = 0x86,
    ExtendedEnd = 0x87,
}

/// Unified opcode representation: base or Thor-extended.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Instruction {
    Base(Opcode),
    Thor(ThorOpcode),
}

impl Instruction {
    pub fn from_byte(b: u8) -> Option<Self> {
        match b {
            0x00..=0x06 => base_from_byte(b).map(Instruction::Base),
            0x10..=0x15 => base_from_byte(b).map(Instruction::Base),
            0x20..=0x22 => base_from_byte(b).map(Instruction::Base),
            0x30..=0x35 => base_from_byte(b).map(Instruction::Base),
            0x40..=0x45 => base_from_byte(b).map(Instruction::Base),
            0x50..=0x54 => base_from_byte(b).map(Instruction::Base),
            0x60..=0x61 => base_from_byte(b).map(Instruction::Base),
            0x80..=0x87 => thor_from_byte(b).map(Instruction::Thor),
            _ => None,
        }
    }

    pub fn to_byte(self) -> u8 {
        match self {
            Instruction::Base(op) => op as u8,
            Instruction::Thor(op) => op as u8,
        }
    }
}

impl fmt::Display for Instruction {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Instruction::Base(op) => write!(f, "{op:?}"),
            Instruction::Thor(op) => write!(f, "{op:?}"),
        }
    }
}

fn base_from_byte(b: u8) -> Option<Opcode> {
    match b {
        0x00 => Some(Opcode::Nop),
        0x01 => Some(Opcode::Push),
        0x02 => Some(Opcode::Pop),
        0x03 => Some(Opcode::Dup),
        0x04 => Some(Opcode::Swap),
        0x05 => Some(Opcode::Load),
        0x06 => Some(Opcode::Store),
        0x10 => Some(Opcode::Add),
        0x11 => Some(Opcode::Sub),
        0x12 => Some(Opcode::Mul),
        0x13 => Some(Opcode::Div),
        0x14 => Some(Opcode::Mod),
        0x15 => Some(Opcode::Neg),
        0x20 => Some(Opcode::And),
        0x21 => Some(Opcode::Or),
        0x22 => Some(Opcode::Not),
        0x30 => Some(Opcode::Eq),
        0x31 => Some(Opcode::Ne),
        0x32 => Some(Opcode::Lt),
        0x33 => Some(Opcode::Le),
        0x34 => Some(Opcode::Gt),
        0x35 => Some(Opcode::Ge),
        0x40 => Some(Opcode::Jmp),
        0x41 => Some(Opcode::Jz),
        0x42 => Some(Opcode::Jnz),
        0x43 => Some(Opcode::Call),
        0x44 => Some(Opcode::Ret),
        0x45 => Some(Opcode::Halt),
        0x50 => Some(Opcode::Assert),
        0x51 => Some(Opcode::Constrain),
        0x52 => Some(Opcode::Propagate),
        0x53 => Some(Opcode::Solve),
        0x54 => Some(Opcode::Verify),
        0x60 => Some(Opcode::Print),
        0x61 => Some(Opcode::Debug),
        _ => None,
    }
}

fn thor_from_byte(b: u8) -> Option<ThorOpcode> {
    match b {
        0x80 => Some(ThorOpcode::ParallelBranch),
        0x81 => Some(ThorOpcode::Reduce),
        0x82 => Some(ThorOpcode::GpuCompile),
        0x83 => Some(ThorOpcode::BatchSolve),
        0x84 => Some(ThorOpcode::SonarBatch),
        0x85 => Some(ThorOpcode::TileCommit),
        0x86 => Some(ThorOpcode::Pathfind),
        0x87 => Some(ThorOpcode::ExtendedEnd),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn round_trip_all_opcodes() {
        for b in 0x00u8..=0x87u8 {
            if let Some(inst) = Instruction::from_byte(b) {
                assert_eq!(inst.to_byte(), b);
            }
        }
    }

    #[test]
    fn base_count() {
        let base: Vec<u8> = (0x00u8..=0x61u8)
            .filter(|b| Instruction::from_byte(*b).is_some())
            .collect();
        assert_eq!(base.len(), 35);
    }

    #[test]
    fn thor_count() {
        let thor: Vec<u8> = (0x80u8..=0x87u8)
            .filter(|b| Instruction::from_byte(*b).is_some())
            .collect();
        assert_eq!(thor.len(), 8);
    }
}
