//! flux_wasm_vm — WebAssembly FLUX-C Bytecode Virtual Machine
//!
//! Executes FLUX-C 43-opcode bytecode inside a Wasm sandbox.
//! Targets wasm32-unknown-unknown with wasm-bindgen for JS interop.
//!
//! This file can also be compiled as a standard Rust library/test.
//! For Wasm: cargo build --target wasm32-unknown-unknown
//! For tests: cargo test

use std::fmt;

/// FLUX-C opcodes
#[repr(u8)]
#[derive(Clone, Copy, Debug, PartialEq)]
enum Op {
    Load  = 0x01, Store = 0x02, Const = 0x03,
    Add   = 0x04, Sub   = 0x05, Mul   = 0x06, Div = 0x07,
    And   = 0x08, Or    = 0x09, Not   = 0x0A,
    Lt    = 0x0B, Gt    = 0x0C, Eq    = 0x0D, Le  = 0x0E, Ge = 0x0F, Ne = 0x10,
    Jmp   = 0x11, Jz    = 0x12, Jnz   = 0x13,
    Pack8 = 0x14, Unpack = 0x15, Check = 0x16, Assert = 0x17, Halt = 0x18,
    Nop   = 0x19, Call  = 0x1A, Ret   = 0x1B,
}

impl Op {
    fn from_u8(v: u8) -> Option<Self> {
        match v {
            0x01 => Some(Op::Load), 0x02 => Some(Op::Store), 0x03 => Some(Op::Const),
            0x04 => Some(Op::Add), 0x05 => Some(Op::Sub), 0x06 => Some(Op::Mul), 0x07 => Some(Op::Div),
            0x08 => Some(Op::And), 0x09 => Some(Op::Or), 0x0A => Some(Op::Not),
            0x0B => Some(Op::Lt), 0x0C => Some(Op::Gt), 0x0D => Some(Op::Eq),
            0x0E => Some(Op::Le), 0x0F => Some(Op::Ge), 0x10 => Some(Op::Ne),
            0x11 => Some(Op::Jmp), 0x12 => Some(Op::Jz), 0x13 => Some(Op::Jnz),
            0x14 => Some(Op::Pack8), 0x15 => Some(Op::Unpack), 0x16 => Some(Op::Check),
            0x17 => Some(Op::Assert), 0x18 => Some(Op::Halt), 0x19 => Some(Op::Nop),
            0x1A => Some(Op::Call), 0x1B => Some(Op::Ret),
            _ => None,
        }
    }
}

#[derive(Clone, Copy, Debug)]
struct Instr {
    op: Op,
    arg0: u16,
    arg1: u16,
    imm: f64,
}

/// VM state
pub struct Vm {
    code: Vec<Instr>,
    pub stack: Vec<f64>,
    locals: Vec<f64>,
    pc: usize,
    pub checks: u64,
    pub violations: u64,
    pub halted: bool,
}

impl Vm {
    pub fn new() -> Self {
        Vm {
            code: Vec::new(), stack: Vec::with_capacity(64),
            locals: Vec::with_capacity(32), pc: 0,
            checks: 0, violations: 0, halted: false,
        }
    }

    /// Load raw FLUX-C bytecode. Format: opcode(1) + arg0(2) + arg1(2) + imm(8) = 13 bytes per instr.
    pub fn load_bytecode(&mut self, bytes: &[u8]) {
        self.code.clear();
        let mut i = 0usize;
        while i + 12 < bytes.len() {
            let op = Op::from_u8(bytes[i]).unwrap_or(Op::Nop);
            i += 1;
            let arg0 = u16::from_le_bytes([bytes[i], bytes[i+1]]);
            i += 2;
            let arg1 = u16::from_le_bytes([bytes[i], bytes[i+1]]);
            i += 2;
            let imm = f64::from_le_bytes([
                bytes[i], bytes[i+1], bytes[i+2], bytes[i+3],
                bytes[i+4], bytes[i+5], bytes[i+6], bytes[i+7],
            ]);
            i += 8;
            self.code.push(Instr { op, arg0, arg1, imm });
        }
    }

    fn push(&mut self, v: f64) { self.stack.push(v); }
    fn pop(&mut self) -> f64 { self.stack.pop().unwrap_or(0.0) }

    /// Run until HALT or cycle limit.
    pub fn step(&mut self, max_cycles: usize) {
        for _ in 0..max_cycles {
            if self.halted || self.pc >= self.code.len() { break; }
            let instr = self.code[self.pc];
            self.pc += 1;
            match instr.op {
                Op::Load => {
                    let v = self.locals.get(instr.arg0 as usize).copied().unwrap_or(0.0);
                    self.push(v);
                }
                Op::Store => {
                    let v = self.pop();
                    let idx = instr.arg0 as usize;
                    if idx >= self.locals.len() { self.locals.resize(idx + 1, 0.0); }
                    self.locals[idx] = v;
                }
                Op::Const => self.push(instr.imm),
                Op::Add => { let b = self.pop(); let a = self.pop(); self.push(a + b); }
                Op::Sub => { let b = self.pop(); let a = self.pop(); self.push(a - b); }
                Op::Mul => { let b = self.pop(); let a = self.pop(); self.push(a * b); }
                Op::Div => { let b = self.pop(); let a = self.pop(); self.push(a / b); }
                Op::And => { let b = self.pop(); let a = self.pop(); self.push(if a != 0.0 && b != 0.0 { 1.0 } else { 0.0 }); }
                Op::Or  => { let b = self.pop(); let a = self.pop(); self.push(if a != 0.0 || b != 0.0 { 1.0 } else { 0.0 }); }
                Op::Not => { let a = self.pop(); self.push(if a == 0.0 { 1.0 } else { 0.0 }); }
                Op::Lt  => { let b = self.pop(); let a = self.pop(); self.push(if a < b { 1.0 } else { 0.0 }); }
                Op::Gt  => { let b = self.pop(); let a = self.pop(); self.push(if a > b { 1.0 } else { 0.0 }); }
                Op::Eq  => { let b = self.pop(); let a = self.pop(); self.push(if a == b { 1.0 } else { 0.0 }); }
                Op::Le  => { let b = self.pop(); let a = self.pop(); self.push(if a <= b { 1.0 } else { 0.0 }); }
                Op::Ge  => { let b = self.pop(); let a = self.pop(); self.push(if a >= b { 1.0 } else { 0.0 }); }
                Op::Ne  => { let b = self.pop(); let a = self.pop(); self.push(if a != b { 1.0 } else { 0.0 }); }
                Op::Jmp => { self.pc = instr.arg0 as usize; }
                Op::Jz  => { let a = self.pop(); if a == 0.0 { self.pc = instr.arg0 as usize; } }
                Op::Jnz => { let a = self.pop(); if a != 0.0 { self.pc = instr.arg0 as usize; } }
                Op::Pack8 => {
                    let mut packed = 0u8;
                    for n in 0..8usize { let v = self.pop(); if v != 0.0 { packed |= 1 << n; } }
                    self.push(packed as f64);
                }
                Op::Unpack => {
                    let packed = self.pop() as u8;
                    for n in 0..8usize { self.push(if (packed >> n) & 1 == 1 { 1.0 } else { 0.0 }); }
                }
                Op::Check => { self.checks += 1; let v = self.pop(); if v == 0.0 { self.violations += 1; } }
                Op::Assert => { self.checks += 1; let v = self.pop(); if v == 0.0 { self.violations += 1; self.halted = true; } }
                Op::Halt => { self.halted = true; }
                Op::Nop => {}
                Op::Call => { self.push(self.pc as f64); self.pc = instr.arg0 as usize; }
                Op::Ret => { let ret_addr = self.pop() as usize; self.pc = ret_addr; }
            }
        }
    }

    /// Load inputs into local slots and run until HALT.
    pub fn run(&mut self, inputs: &[f64]) {
        self.locals.clear();
        self.locals.extend_from_slice(inputs);
        self.stack.clear();
        self.pc = 0;
        self.checks = 0;
        self.violations = 0;
        self.halted = false;
        self.step(100_000);
    }
}

fn encode(op: Op, arg0: u16, arg1: u16, imm: f64) -> Vec<u8> {
    let mut buf = vec![op as u8];
    buf.extend_from_slice(&arg0.to_le_bytes());
    buf.extend_from_slice(&arg1.to_le_bytes());
    buf.extend_from_slice(&imm.to_le_bytes());
    buf
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_const_add() {
        let mut vm = Vm::new();
        let mut bc = Vec::new();
        bc.extend(encode(Op::Const, 0, 0, 3.0));
        bc.extend(encode(Op::Const, 0, 0, 4.0));
        bc.extend(encode(Op::Add, 0, 0, 0.0));
        bc.extend(encode(Op::Halt, 0, 0, 0.0));
        vm.load_bytecode(&bc);
        vm.run(&[]);
        assert_eq!(vm.stack.len(), 1);
        assert!((vm.stack[0] - 7.0).abs() < 1e-9);
    }

    #[test]
    fn test_load_store_lt() {
        let mut vm = Vm::new();
        let mut bc = Vec::new();
        bc.extend(encode(Op::Load, 0, 0, 0.0));
        bc.extend(encode(Op::Const, 0, 0, 100.0));
        bc.extend(encode(Op::Lt, 0, 0, 0.0));
        bc.extend(encode(Op::Halt, 0, 0, 0.0));
        vm.load_bytecode(&bc);
        vm.run(&[50.0]);
        assert_eq!(vm.stack.len(), 1);
        assert_eq!(vm.stack[0], 1.0);
    }

    #[test]
    fn test_and_or() {
        let mut vm = Vm::new();
        let mut bc = Vec::new();
        bc.extend(encode(Op::Const, 0, 0, 1.0));
        bc.extend(encode(Op::Const, 0, 0, 0.0));
        bc.extend(encode(Op::And, 0, 0, 0.0));
        bc.extend(encode(Op::Const, 0, 0, 1.0));
        bc.extend(encode(Op::Or, 0, 0, 0.0));
        bc.extend(encode(Op::Halt, 0, 0, 0.0));
        vm.load_bytecode(&bc);
        vm.run(&[]);
        assert_eq!(vm.stack.len(), 2);
        assert_eq!(vm.stack[0], 0.0);
        assert_eq!(vm.stack[1], 1.0);
    }

    #[test]
    fn test_jmp_jz() {
        let mut vm = Vm::new();
        let mut bc = Vec::new();
        bc.extend(encode(Op::Const, 0, 0, 0.0));
        bc.extend(encode(Op::Jz, 3, 0, 0.0));
        bc.extend(encode(Op::Const, 0, 0, 99.0));
        bc.extend(encode(Op::Halt, 0, 0, 0.0));
        bc.extend(encode(Op::Const, 0, 0, 42.0));
        bc.extend(encode(Op::Halt, 0, 0, 0.0));
        vm.load_bytecode(&bc);
        vm.run(&[]);
        assert_eq!(vm.stack.len(), 1);
        assert_eq!(vm.stack[0], 42.0);
    }

    #[test]
    fn test_check_assert_violations() {
        let mut vm = Vm::new();
        let mut bc = Vec::new();
        bc.extend(encode(Op::Const, 0, 0, 0.0));
        bc.extend(encode(Op::Check, 0, 0, 0.0));
        bc.extend(encode(Op::Const, 0, 0, 0.0));
        bc.extend(encode(Op::Assert, 0, 0, 0.0));
        bc.extend(encode(Op::Halt, 0, 0, 0.0));
        vm.load_bytecode(&bc);
        vm.run(&[]);
        assert_eq!(vm.checks, 2);
        assert_eq!(vm.violations, 2);
        assert!(vm.halted);
    }

    #[test]
    fn test_pack8_unpack() {
        let mut vm = Vm::new();
        let mut bc = Vec::new();
        for _ in 0..8 { bc.extend(encode(Op::Const, 0, 0, 1.0)); }
        bc.extend(encode(Op::Pack8, 0, 0, 0.0));
        bc.extend(encode(Op::Unpack, 0, 0, 0.0));
        bc.extend(encode(Op::Halt, 0, 0, 0.0));
        vm.load_bytecode(&bc);
        vm.run(&[]);
        assert_eq!(vm.stack.len(), 9);
    }
}
