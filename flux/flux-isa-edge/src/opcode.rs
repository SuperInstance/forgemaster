use std::fmt;
use std::str::FromStr;
use serde::{Deserialize, Serialize};

/// All 35 FLUX ISA opcodes.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[repr(u8)]
pub enum OpCode {
    // ── Stack / value ──────────────────────────────
    Push      = 0x01,
    Pop       = 0x02,
    Dup       = 0x03,
    Swap      = 0x04,
    Load      = 0x05,
    Store     = 0x06,

    // ── Arithmetic ─────────────────────────────────
    Add       = 0x10,
    Sub       = 0x11,
    Mul       = 0x12,
    Div       = 0x13,
    Mod       = 0x14,
    Neg       = 0x15,

    // ── Comparison ─────────────────────────────────
    Eq        = 0x20,
    Ne        = 0x21,
    Lt        = 0x22,
    Le        = 0x23,
    Gt        = 0x24,
    Ge        = 0x25,

    // ── Logic ──────────────────────────────────────
    And       = 0x30,
    Or        = 0x31,
    Not       = 0x32,

    // ── Constraint ─────────────────────────────────
    Validate  = 0x40,
    Assert    = 0x41,
    Tolerance = 0x42,
    Clamp     = 0x43,

    // ── Control flow ───────────────────────────────
    Jump      = 0x50,
    JumpIf    = 0x51,
    Call      = 0x52,
    Ret       = 0x53,
    Halt      = 0x54,

    // ── I/O ────────────────────────────────────────
    Input     = 0x60,
    Output    = 0x61,

    // ── Extended ───────────────────────────────────
    Sync      = 0x70,
    Nop       = 0x00,
}

impl OpCode {
    /// All opcodes in definition order.
    pub fn all() -> &'static [OpCode] {
        &[
            OpCode::Push, OpCode::Pop, OpCode::Dup, OpCode::Swap,
            OpCode::Load, OpCode::Store,
            OpCode::Add, OpCode::Sub, OpCode::Mul, OpCode::Div,
            OpCode::Mod, OpCode::Neg,
            OpCode::Eq, OpCode::Ne, OpCode::Lt, OpCode::Le,
            OpCode::Gt, OpCode::Ge,
            OpCode::And, OpCode::Or, OpCode::Not,
            OpCode::Validate, OpCode::Assert, OpCode::Tolerance, OpCode::Clamp,
            OpCode::Jump, OpCode::JumpIf, OpCode::Call, OpCode::Ret, OpCode::Halt,
            OpCode::Input, OpCode::Output,
            OpCode::Sync, OpCode::Nop,
        ]
    }

    pub fn from_byte(byte: u8) -> Option<Self> {
        match byte {
            0x01 => Some(OpCode::Push),
            0x02 => Some(OpCode::Pop),
            0x03 => Some(OpCode::Dup),
            0x04 => Some(OpCode::Swap),
            0x05 => Some(OpCode::Load),
            0x06 => Some(OpCode::Store),
            0x10 => Some(OpCode::Add),
            0x11 => Some(OpCode::Sub),
            0x12 => Some(OpCode::Mul),
            0x13 => Some(OpCode::Div),
            0x14 => Some(OpCode::Mod),
            0x15 => Some(OpCode::Neg),
            0x20 => Some(OpCode::Eq),
            0x21 => Some(OpCode::Ne),
            0x22 => Some(OpCode::Lt),
            0x23 => Some(OpCode::Le),
            0x24 => Some(OpCode::Gt),
            0x25 => Some(OpCode::Ge),
            0x30 => Some(OpCode::And),
            0x31 => Some(OpCode::Or),
            0x32 => Some(OpCode::Not),
            0x40 => Some(OpCode::Validate),
            0x41 => Some(OpCode::Assert),
            0x42 => Some(OpCode::Tolerance),
            0x43 => Some(OpCode::Clamp),
            0x50 => Some(OpCode::Jump),
            0x51 => Some(OpCode::JumpIf),
            0x52 => Some(OpCode::Call),
            0x53 => Some(OpCode::Ret),
            0x54 => Some(OpCode::Halt),
            0x60 => Some(OpCode::Input),
            0x61 => Some(OpCode::Output),
            0x70 => Some(OpCode::Sync),
            0x00 => Some(OpCode::Nop),
            _ => None,
        }
    }

    pub fn byte(self) -> u8 {
        self as u8
    }

    pub fn group(self) -> &'static str {
        match self {
            OpCode::Push | OpCode::Pop | OpCode::Dup | OpCode::Swap
            | OpCode::Load | OpCode::Store => "stack",
            OpCode::Add | OpCode::Sub | OpCode::Mul | OpCode::Div
            | OpCode::Mod | OpCode::Neg => "arithmetic",
            OpCode::Eq | OpCode::Ne | OpCode::Lt | OpCode::Le
            | OpCode::Gt | OpCode::Ge => "comparison",
            OpCode::And | OpCode::Or | OpCode::Not => "logic",
            OpCode::Validate | OpCode::Assert | OpCode::Tolerance
            | OpCode::Clamp => "constraint",
            OpCode::Jump | OpCode::JumpIf | OpCode::Call
            | OpCode::Ret | OpCode::Halt => "control",
            OpCode::Input | OpCode::Output => "io",
            OpCode::Sync | OpCode::Nop => "extended",
        }
    }
}

impl fmt::Display for OpCode {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let s = match self {
            OpCode::Push      => "PUSH",
            OpCode::Pop       => "POP",
            OpCode::Dup       => "DUP",
            OpCode::Swap      => "SWAP",
            OpCode::Load      => "LOAD",
            OpCode::Store     => "STORE",
            OpCode::Add       => "ADD",
            OpCode::Sub       => "SUB",
            OpCode::Mul       => "MUL",
            OpCode::Div       => "DIV",
            OpCode::Mod       => "MOD",
            OpCode::Neg       => "NEG",
            OpCode::Eq        => "EQ",
            OpCode::Ne        => "NE",
            OpCode::Lt        => "LT",
            OpCode::Le        => "LE",
            OpCode::Gt        => "GT",
            OpCode::Ge        => "GE",
            OpCode::And       => "AND",
            OpCode::Or        => "OR",
            OpCode::Not       => "NOT",
            OpCode::Validate  => "VALIDATE",
            OpCode::Assert    => "ASSERT",
            OpCode::Tolerance => "TOLERANCE",
            OpCode::Clamp     => "CLAMP",
            OpCode::Jump      => "JUMP",
            OpCode::JumpIf    => "JUMP_IF",
            OpCode::Call      => "CALL",
            OpCode::Ret       => "RET",
            OpCode::Halt      => "HALT",
            OpCode::Input     => "INPUT",
            OpCode::Output    => "OUTPUT",
            OpCode::Sync      => "SYNC",
            OpCode::Nop       => "NOP",
        };
        f.write_str(s)
    }
}

impl FromStr for OpCode {
    type Err = String;
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_uppercase().as_str() {
            "PUSH"      => Ok(OpCode::Push),
            "POP"       => Ok(OpCode::Pop),
            "DUP"       => Ok(OpCode::Dup),
            "SWAP"      => Ok(OpCode::Swap),
            "LOAD"      => Ok(OpCode::Load),
            "STORE"     => Ok(OpCode::Store),
            "ADD"       => Ok(OpCode::Add),
            "SUB"       => Ok(OpCode::Sub),
            "MUL"       => Ok(OpCode::Mul),
            "DIV"       => Ok(OpCode::Div),
            "MOD"       => Ok(OpCode::Mod),
            "NEG"       => Ok(OpCode::Neg),
            "EQ"        => Ok(OpCode::Eq),
            "NE"        => Ok(OpCode::Ne),
            "LT"        => Ok(OpCode::Lt),
            "LE"        => Ok(OpCode::Le),
            "GT"        => Ok(OpCode::Gt),
            "GE"        => Ok(OpCode::Ge),
            "AND"       => Ok(OpCode::And),
            "OR"        => Ok(OpCode::Or),
            "NOT"       => Ok(OpCode::Not),
            "VALIDATE"  => Ok(OpCode::Validate),
            "ASSERT"    => Ok(OpCode::Assert),
            "TOLERANCE" => Ok(OpCode::Tolerance),
            "CLAMP"     => Ok(OpCode::Clamp),
            "JUMP"      => Ok(OpCode::Jump),
            "JUMP_IF"   => Ok(OpCode::JumpIf),
            "CALL"      => Ok(OpCode::Call),
            "RET"       => Ok(OpCode::Ret),
            "HALT"      => Ok(OpCode::Halt),
            "INPUT"     => Ok(OpCode::Input),
            "OUTPUT"    => Ok(OpCode::Output),
            "SYNC"      => Ok(OpCode::Sync),
            "NOP"       => Ok(OpCode::Nop),
            other       => Err(format!("unknown opcode: {other}")),
        }
    }
}
