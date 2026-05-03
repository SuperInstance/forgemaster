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
        Self { stack: [0u8; 256], sp: 0, pc: 0, gas, halted: false }
    }
    
    fn push(&mut self, value: u8) -> Result<(), Fault> {
        if self.sp >= 256 { return Err(Fault::StackOverflow); }
        self.stack[self.sp] = value;
        self.sp += 1;
        Ok(())
    }
    
    fn pop(&mut self) -> Result<u8, Fault> {
        if self.sp == 0 { return Err(Fault::StackUnderflow); }
        self.sp -= 1;
        Ok(self.stack[self.sp])
    }
    
    pub fn step(&mut self, bytecode: &[u8]) -> Result<bool, Fault> {
        if self.halted { return Ok(true); }
        if self.gas == 0 { return Err(Fault::GasExhausted); }
        if self.pc >= bytecode.len() { return Ok(true); }
        
        let op = bytecode[self.pc];
        self.pc += 1;
        self.gas -= 1;
        
        match op {
            0x00 => { // PUSH
                let v = bytecode.get(self.pc).copied().ok_or(Fault::StackOverflow)?;
                self.pc += 1;
                self.push(v)?;
            }
            0x01 => { self.pop()?; }
            0x06 => { let b = self.pop()?; let a = self.pop()?; self.push(a.wrapping_add(b))?; }
            0x07 => { let b = self.pop()?; let a = self.pop()?; self.push(a.wrapping_sub(b))?; }
            0x08 => { let b = self.pop()?; let a = self.pop()?; self.push(a.wrapping_mul(b))?; }
            0x09 => { let b = self.pop()?; let a = self.pop()?; self.push(a & b)?; }
            0x0A => { let b = self.pop()?; let a = self.pop()?; self.push(a | b)?; }
            0x0B => { let b = self.pop()?; let a = self.pop()?; self.push(a ^ b)?; }
            0x0C => { let a = self.pop()?; self.push(!a)?; }
            0x0F => { let b = self.pop()?; let a = self.pop()?; self.push(if a == b { 1 } else { 0 })?; }
            0x10 => { let b = self.pop()?; let a = self.pop()?; self.push(if a != b { 1 } else { 0 })?; }
            0x11 => { let b = self.pop()?; let a = self.pop()?; self.push(if a < b { 1 } else { 0 })?; }
            0x12 => { let b = self.pop()?; let a = self.pop()?; self.push(if a > b { 1 } else { 0 })?; }
            0x15 => { self.pc = bytecode.get(self.pc).copied().ok_or(Fault::StackOverflow)? as usize; }
            0x16 => {
                let addr = bytecode.get(self.pc).copied().ok_or(Fault::StackOverflow)? as usize;
                self.pc += 1;
                let v = self.pop()?;
                if v == 0 { self.pc = addr; }
            }
            0x1A => { self.halted = true; }
            0x1B => { let v = self.pop()?; if v == 0 { return Err(Fault::AssertFailed); } }
            0x20 => { return Err(Fault::GuardTrap); }
            0x27 => {} // NOP
            _ => {}
        }
        Ok(self.halted)
    }
    
    pub fn execute(&mut self, bytecode: &[u8], max: usize) -> Result<(), Vec<Fault>> {
        for _ in 0..max {
            match self.step(bytecode) {
                Ok(true) => return Ok(()),
                Ok(false) => continue,
                Err(f) => return Err(vec![f]),
            }
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn push_add_halt() {
        let mut vm = FluxVM::new(100);
        // PUSH 3, PUSH 4, ADD, HALT
        vm.execute(&[0x00, 3, 0x00, 4, 0x06, 0x1A], 100).unwrap();
        assert!(vm.halted);
        assert_eq!(vm.sp, 1);
        assert_eq!(vm.stack[0], 7);
    }
    
    #[test]
    fn assert_fail() {
        let mut vm = FluxVM::new(100);
        // PUSH 0, ASSERT
        let result = vm.execute(&[0x00, 0, 0x1B], 100);
        assert!(result.is_err());
    }
    
    #[test]
    fn guard_trap() {
        let mut vm = FluxVM::new(100);
        let result = vm.execute(&[0x20], 100);
        assert!(matches!(result, Err(f) if f[0] == Fault::GuardTrap));
    }
    
    #[test]
    fn gas_exhaustion() {
        let mut vm = FluxVM::new(2);
        // PUSH 1, PUSH 2, PUSH 3 — 3 instructions but only 2 gas
        let result = vm.execute(&[0x00, 1, 0x00, 2, 0x00, 3], 100);
        assert!(matches!(result, Err(f) if f[0] == Fault::GasExhausted));
    }
    
    #[test]
    fn jump_control_flow() {
        let mut vm = FluxVM::new(100);
        // PUSH 0, JZ 6, PUSH 99, HALT, (addr 6:) PUSH 42, HALT
        vm.execute(&[0x00, 0, 0x16, 7, 0x00, 99, 0x1A, 0x00, 42, 0x1A], 100).unwrap();
        assert_eq!(vm.stack[0], 42);
    }
}

    #[test]
    fn bitwise_and_mask() {
        let mut vm = FluxVM::new(100);
        // PUSH 0xFF, PUSH 0x0F, AND, HALT
        vm.execute(&[0x00, 0xFF, 0x00, 0x0F, 0x09, 0x1A], 100).unwrap();
        assert_eq!(vm.stack[0], 0x0F);
    }

    #[test]
    fn domain_check_pass() {
        let mut vm = FluxVM::new(100);
        // PUSH 0x42, PUSH 0x0F, AND (result 0x02), PUSH 0, EQ (0x02 != 0 → false → 0), NOT → 1, ASSERT
        vm.execute(&[0x00, 0x42, 0x00, 0x0F, 0x09, 0x00, 0, 0x0F, 0x0C, 0x1B, 0x1A], 100).unwrap();
        assert!(vm.halted);
    }

    #[test]
    fn xor_swap() {
        let mut vm = FluxVM::new(100);
        // XOR swap of a=5, b=3:
        // PUSH 5, PUSH 3, XOR → a^b on stack, now need actual swap...
        // Simpler: just verify XOR properties
        // PUSH 0xAA, PUSH 0x55, XOR → 0xFF
        vm.execute(&[0x00, 0xAA, 0x00, 0x55, 0x0B, 0x1A], 100).unwrap();
        assert_eq!(vm.stack[0], 0xFF);
    }

    #[test]
    fn comparison_gt() {
        let mut vm = FluxVM::new(100);
        // PUSH 10, PUSH 5, GT → 1, ASSERT, HALT
        vm.execute(&[0x00, 10, 0x00, 5, 0x12, 0x1B, 0x1A], 100).unwrap();
        assert!(vm.halted);
    }

    #[test]
    fn nested_if_else() {
        let mut vm = FluxVM::new(100);
        // if 5 > 3 then push 42 else push 99
        // PUSH 5, PUSH 3, GT → 1, JZ to else-branch, PUSH 42, HALT, (else:) PUSH 99, HALT
        // Bytes: [PUSH 5, PUSH 3, GT, JZ 10, PUSH 42, HALT, PUSH 99, HALT]
        //         0x00,5  0x00,3  0x12 0x16,10 0x00,42 0x1A  0x00,99  0x1A
        vm.execute(&[0x00, 5, 0x00, 3, 0x12, 0x16, 10, 0x00, 42, 0x1A, 0x00, 99, 0x1A], 100).unwrap();
        assert_eq!(vm.stack[0], 42); // Took the "then" branch
    }

    #[test]
    fn sub_and_assert() {
        let mut vm = FluxVM::new(100);
        // PUSH 10, PUSH 3, SUB → 7, PUSH 7, EQ → 1, ASSERT, HALT
        vm.execute(&[0x00, 10, 0x00, 3, 0x07, 0x00, 7, 0x0F, 0x1B, 0x1A], 100).unwrap();
        assert!(vm.halted);
    }
