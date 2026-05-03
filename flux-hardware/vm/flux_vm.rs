#![no_std]

use core::result::Result;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Fault {
    StackUnderflow,
    StackOverflow,
    GasExhausted,
    AssertFailed,
    GuardTrap,
}

pub struct FluxVM {
    stack: [u8; 256],
    sp: usize,
    pc: usize,
    gas: u32,
    halted: bool,
}

impl FluxVM {
    pub fn new(gas: u32) -> Self {
        Self {
            stack: [0u8; 256],
            sp: 0,
            pc: 0,
            gas,
            halted: false,
        }
    }

    fn push(&mut self, value: u8) -> Result<(), Fault> {
        if self.sp >= 256 {
            return Err(Fault::StackOverflow);
        }
        self.stack[self.sp] = value;
        self.sp += 1;
        Ok(())
    }

    fn pop(&mut self) -> Result<u8, Fault> {
        if self.sp == 0 {
            return Err(Fault::StackUnderflow);
        }
        self.sp -= 1;
        Ok(self.stack[self.sp])
    }

    fn binop<F>(&mut self, f: F) -> Result<(), Fault>
    where
        F: FnOnce(u8, u8) -> u8,
    {
        let b = self.pop()?;
        let a = self.pop()?;
        self.push(f(a, b))
    }

    fn cmpop<F>(&mut self, f: F) -> Result<(), Fault>
    where
        F: FnOnce(u8, u8) -> bool,
    {
        let b = self.pop()?;
        let a = self.pop()?;
        self.push(if f(a, b) { 1 } else { 0 })
    }

    pub fn step(&mut self, bytecode: &[u8]) -> Result<bool, Fault> {
        if self.halted {
            return Ok(true);
        }
        if self.gas == 0 {
            return Err(Fault::GasExhausted);
        }
        self.gas -= 1;

        if self.pc >= bytecode.len() {
            return Ok(true);
        }

        let op = bytecode[self.pc];
        self.pc += 1;

        match op {
            0x00 => {
                // PUSH
                if self.pc >= bytecode.len() {
                    return Err(Fault::StackUnderflow);
                }
                let val = bytecode[self.pc];
                self.pc += 1;
                self.push(val)?;
            }
            0x01 => {
                // POP
                self.pop()?;
            }
            0x02 => {
                // DUP
                if self.sp == 0 {
                    return Err(Fault::StackUnderflow);
                }
                let val = self.stack[self.sp - 1];
                self.push(val)?;
            }
            0x03 => {
                // SWAP
                if self.sp < 2 {
                    return Err(Fault::StackUnderflow);
                }
                self.stack.swap(self.sp - 1, self.sp - 2);
            }
            0x06 => {
                // ADD
                self.binop(u8::wrapping_add)?;
            }
            0x07 => {
                // SUB
                self.binop(u8::wrapping_sub)?;
            }
            0x08 => {
                // MUL
                self.binop(u8::wrapping_mul)?;
            }
            0x09 => {
                // AND
                self.binop(|a, b| a & b)?;
            }
            0x0A => {
                // OR
                self.binop(|a, b| a | b)?;
            }
            0x0B => {
                // XOR
                self.binop(|a, b| a ^ b)?;
            }
            0x0C => {
                // NOT
                let a = self.pop()?;
                self.push(!a)?;
            }
            0x0F => {
                // EQ
                self.cmpop(|a, b| a == b)?;
            }
            0x10 => {
                // NEQ
                self.cmpop(|a, b| a != b)?;
            }
            0x11 => {
                // LT
                self.cmpop(|a, b| a < b)?;
            }
            0x12 => {
                // GT
                self.cmpop(|a, b| a > b)?;
            }
            0x15 => {
                // JUMP
                if self.pc >= bytecode.len() {
                    return Err(Fault::StackUnderflow);
                }
                let addr = bytecode[self.pc] as usize;
                self.pc = addr;
            }
            0x16 => {
                // JZ
                if self.pc >= bytecode.len() {
                    return Err(Fault::StackUnderflow);
                }
                let addr = bytecode[self.pc] as usize;
                self.pc += 1;
                let val = self.pop()?;
                if val == 0 {
                    self.pc = addr;
                }
            }
            0x1A => {
                // HALT
                self.halted = true;
            }
            0x1B => {
                // ASSERT
                let val = self.pop()?;
                if val == 0 {
                    return Err(Fault::AssertFailed);
                }
            }
            0x20 => {
                // GUARD_TRAP
                return Err(Fault::GuardTrap);
            }
            0x27 => {
                // NOP
            }
            _ => {}
        }

        Ok(self.halted)
    }

    pub fn execute(&mut self, bytecode: &[u8], max: usize) -> Result<(), Vec<Fault>> {
        let mut faults = Vec::new();
        for _ in 0..max {
            match self.step(bytecode) {
                Ok(true) => return Ok(()),
                Ok(false) => continue,
                Err(fault) => {
                    faults.push(fault);
                    return Err(faults);
                }
            }
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_push_add_halt() {
        let mut vm = FluxVM::new(100);
        let bytecode = [0x00, 10, 0x00, 20, 0x06, 0x1A];
        vm.execute(&bytecode, 100).unwrap();
        assert!(vm.halted);
        assert_eq!(vm.sp, 1);
        assert_eq!(vm.stack[0], 30);
    }

    #[test]
    fn test_assert_fails_on_zero() {
        let mut vm = FluxVM::new(100);
        let bytecode = [0x00, 0x00, 0x1B];
        let res = vm.execute(&bytecode, 100);
        assert!(res.is_err());
        assert_eq!(res.unwrap_err()[0], Fault::AssertFailed);
    }

    #[test]
    fn test_guard_trap_immediate() {
        let mut vm = FluxVM::new(100);
        let bytecode = [0x20];
        let res = vm.execute(&bytecode, 100);
        assert!(res.is_err());
        assert_eq!(res.unwrap_err()[0], Fault::GuardTrap);
    }

    #[test]
    fn test_gas_exhaustion() {
        let mut vm = FluxVM::new(2);
        let bytecode = [0x00, 0x01, 0x00, 0x02, 0x06, 0x1A];
        let res = vm.execute(&bytecode, 100);
        assert!(res.is_err());
        assert_eq!(res.unwrap_err()[0], Fault::GasExhausted);
    }

    #[test]
    fn test_jump_and_jz_control_flow() {
        let mut vm = FluxVM::new(100);
        // 0: PUSH 1, 2: PUSH 0, 4: EQ -> 0, 5: JZ 10, 7: PUSH 99, 9: HALT
        // 10: PUSH 42, 12: HALT
        let bytecode = [0x00, 0x01, 0x00, 0x00, 0x0F, 0x16, 0x0A, 0x00, 0x63, 0x1A, 0x00, 0x2A, 0x1A];
        vm.execute(&bytecode, 100).unwrap();
        assert!(vm.halted);
        assert_eq!(vm.sp, 1);
        assert_eq!(vm.stack[0], 42);
    }
}