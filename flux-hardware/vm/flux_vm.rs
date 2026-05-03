use core::result::Result;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Fault {
    StackUnderflow,
    StackOverflow,
    GasExhausted,
    AssertFailed,
    GuardTrap,
    CallStackOverflow,
    CallStackUnderflow,
    InvalidMemoryAccess,
}

const STACK_SIZE: usize = 256;
const MEMORY_SIZE: usize = 65536;
const CALL_STACK_SIZE: usize = 32;

pub struct FluxVM {
    stack: [u8; STACK_SIZE],
    sp: usize,
    pc: usize,
    gas: u32,
    halted: bool,
    yielded: bool,
    memory: [u8; MEMORY_SIZE],
    call_stack: [usize; CALL_STACK_SIZE],
    csp: usize,
    guard_reg: u8,
    last_check_passed: bool,
}

impl FluxVM {
    pub fn new(gas: u32) -> Self {
        Self {
            stack: [0u8; STACK_SIZE],
            sp: 0,
            pc: 0,
            gas,
            halted: false,
            yielded: false,
            memory: [0u8; MEMORY_SIZE],
            call_stack: [0usize; CALL_STACK_SIZE],
            csp: 0,
            guard_reg: 0,
            last_check_passed: true,
        }
    }

    fn push(&mut self, value: u8) -> Result<(), Fault> {
        if self.sp >= STACK_SIZE { return Err(Fault::StackOverflow); }
        self.stack[self.sp] = value;
        self.sp += 1;
        Ok(())
    }

    fn pop(&mut self) -> Result<u8, Fault> {
        if self.sp == 0 { return Err(Fault::StackUnderflow); }
        self.sp -= 1;
        Ok(self.stack[self.sp])
    }

    fn peek(&self) -> Result<u8, Fault> {
        if self.sp == 0 { return Err(Fault::StackUnderflow); }
        Ok(self.stack[self.sp - 1])
    }

    fn read_byte(&self, bytecode: &[u8]) -> Result<u8, Fault> {
        bytecode.get(self.pc).copied().ok_or(Fault::InvalidMemoryAccess)
    }

    fn binop<F: FnOnce(u8, u8) -> u8>(&mut self, f: F) -> Result<(), Fault> {
        let b = self.pop()?;
        let a = self.pop()?;
        self.push(f(a, b))
    }

    fn cmpop<F: FnOnce(u8, u8) -> bool>(&mut self, f: F) -> Result<(), Fault> {
        let b = self.pop()?;
        let a = self.pop()?;
        self.push(if f(a, b) { 1 } else { 0 })
    }

    pub fn step(&mut self, bytecode: &[u8]) -> Result<bool, Fault> {
        if self.halted { return Ok(true); }
        if self.yielded { self.yielded = false; }
        if self.gas == 0 { return Err(Fault::GasExhausted); }
        if self.pc >= bytecode.len() { return Ok(true); }

        let op = bytecode[self.pc];
        self.pc += 1;
        self.gas -= 1;

        match op {
            // === Stack Operations ===
            0x00 => { // PUSH val
                let v = self.read_byte(bytecode)?;
                self.pc += 1;
                self.push(v)?;
            }
            0x01 => { self.pop()?; } // POP
            0x02 => { // DUP
                let v = self.peek()?;
                self.push(v)?;
            }
            0x03 => { // SWAP
                let b = self.pop()?;
                let a = self.pop()?;
                self.push(b)?;
                self.push(a)?;
            }

            // === Memory ===
            0x04 => { // LOAD addr
                let addr = self.read_byte(bytecode)? as usize;
                self.pc += 1;
                let v = *self.memory.get(addr).ok_or(Fault::InvalidMemoryAccess)?;
                self.push(v)?;
            }
            0x05 => { // STORE addr
                let addr = self.read_byte(bytecode)? as usize;
                self.pc += 1;
                let v = self.pop()?;
                *self.memory.get_mut(addr).ok_or(Fault::InvalidMemoryAccess)? = v;
            }

            // === Arithmetic ===
            0x06 => self.binop(|a, b| a.wrapping_add(b))?, // ADD
            0x07 => self.binop(|a, b| a.wrapping_sub(b))?, // SUB
            0x08 => self.binop(|a, b| a.wrapping_mul(b))?, // MUL

            // === Bitwise ===
            0x09 => self.binop(|a, b| a & b)?, // AND
            0x0A => self.binop(|a, b| a | b)?, // OR
            0x0B => self.binop(|a, b| a ^ b)?, // XOR
            0x0C => { let a = self.pop()?; self.push(!a)?; } // NOT
            0x0D => { let a = self.pop()?; self.push(a << 1)?; } // SHL
            0x0E => { let a = self.pop()?; self.push(a >> 1)?; } // SHR

            // === Comparison ===
            0x0F => self.cmpop(|a, b| a == b)?, // EQ
            0x10 => self.cmpop(|a, b| a != b)?, // NEQ
            0x11 => self.cmpop(|a, b| a < b)?,  // LT
            0x12 => self.cmpop(|a, b| a > b)?,  // GT
            0x13 => self.cmpop(|a, b| a <= b)?, // LTE
            0x14 => self.cmpop(|a, b| a >= b)?, // GTE

            // === Control Flow ===
            0x15 => { // JUMP addr
                let addr = self.read_byte(bytecode)? as usize;
                self.pc = addr;
            }
            0x16 => { // JZ addr
                let addr = self.read_byte(bytecode)? as usize;
                self.pc += 1; // consume operand even if we jump
                let v = self.pop()?;
                if v == 0 { self.pc = addr; }
            }
            0x17 => { // JNZ addr
                let addr = self.read_byte(bytecode)? as usize;
                self.pc += 1;
                let v = self.pop()?;
                if v != 0 { self.pc = addr; }
            }
            0x18 => { // CALL addr
                let addr = self.read_byte(bytecode)? as usize;
                self.pc += 1;
                if self.csp >= CALL_STACK_SIZE { return Err(Fault::CallStackOverflow); }
                self.call_stack[self.csp] = self.pc;
                self.csp += 1;
                self.pc = addr;
            }
            0x19 => { // RET
                if self.csp == 0 { return Err(Fault::CallStackUnderflow); }
                self.csp -= 1;
                self.pc = self.call_stack[self.csp];
            }

            // === Execution Control ===
            0x1A => { self.halted = true; } // HALT
            0x1B => { // ASSERT
                let v = self.pop()?;
                self.last_check_passed = v != 0;
                if v == 0 { return Err(Fault::AssertFailed); }
            }

            // === Constraint Checking ===
            0x1C => { // CHECK_DOMAIN mask
                let mask = self.read_byte(bytecode)?;
                self.pc += 1;
                let v = self.pop()?;
                let result = v & mask;
                self.last_check_passed = result != 0;
                self.push(result)?;
            }
            0x1D => { // BITMASK_RANGE lo hi
                let lo = self.read_byte(bytecode)?;
                self.pc += 1;
                let hi = self.read_byte(bytecode)?;
                self.pc += 1;
                let v = self.pop()?;
                let in_range = v >= lo && v <= hi;
                self.last_check_passed = in_range;
                self.push(if in_range { 1 } else { 0 })?;
            }
            0x1E => { // LOAD_GUARD
                self.push(self.guard_reg)?;
            }
            0x1F => { // MERKLE_VERIFY (simplified: pop 4 bytes, compare to stored)
                let _b3 = self.pop()?;
                let _b2 = self.pop()?;
                let _b1 = self.pop()?;
                let _b0 = self.pop()?;
                // Simplified: always pass for now
                self.last_check_passed = true;
                self.push(1)?;
            }
            0x20 => { return Err(Fault::GuardTrap); } // GUARD_TRAP

            // === Hash/Crypto ===
            0x21 => { // CRC32 (simplified: XOR-fold stack)
                let mut acc: u8 = 0;
                for i in 0..self.sp {
                    acc ^= self.stack[i];
                }
                self.push(acc)?;
            }
            0x22 => { // PUSH_HASH hi lo
                let hi = self.read_byte(bytecode)?;
                let lo = self.read_byte(bytecode)?;
                self.pc += 2;
                self.push(hi)?;
                self.push(lo)?;
            }
            0x23 => { // XNOR_POPCOUNT
                let b = self.pop()?;
                let a = self.pop()?;
                let xnor = !(a ^ b);
                let count = xnor.count_ones() as u8;
                self.push(count)?;
            }

            // === Extended Comparison ===
            0x24 => self.cmpop(|a, b| a >= b)?, // CMP_GE (same as GTE)
            0x25 => { // CARRY_LT: pop a,b, push 1 if a < b (unsigned)
                let b = self.pop()?;
                let a = self.pop()?;
                self.push(if a < b { 1 } else { 0 })?;
            }
            0x26 => { // JFAIL addr
                let addr = self.read_byte(bytecode)? as usize;
                self.pc += 1;
                if !self.last_check_passed { self.pc = addr; }
            }

            // === Misc ===
            0x27 => {} // NOP
            0x28 => { self.sp = 0; } // FLUSH
            0x29 => { self.yielded = true; } // YIELD

            _ => {} // Unknown opcodes are NOP
        }

        Ok(self.halted)
    }

    pub fn execute(&mut self, bytecode: &[u8], max_steps: usize) -> Result<(), Vec<Fault>> {
        for _ in 0..max_steps {
            match self.step(bytecode) {
                Ok(true) => return Ok(()),
                Ok(false) => continue,
                Err(f) => return Err(vec![f]),
            }
        }
        Ok(())
    }

    // === Public Accessors ===
    pub fn is_halted(&self) -> bool { self.halted }
    pub fn is_yielded(&self) -> bool { self.yielded }
    pub fn stack_top(&self) -> Option<u8> {
        if self.sp > 0 { Some(self.stack[self.sp - 1]) } else { None }
    }
    pub fn stack_len(&self) -> usize { self.sp }
    pub fn gas_remaining(&self) -> u32 { self.gas }
    pub fn pc(&self) -> usize { self.pc }
    pub fn get_memory(&self, addr: usize) -> Option<u8> { self.memory.get(addr).copied() }
    pub fn set_memory(&mut self, addr: usize, val: u8) { if addr < MEMORY_SIZE { self.memory[addr] = val; } }
    pub fn set_guard(&mut self, val: u8) { self.guard_reg = val; }
    pub fn last_check_passed(&self) -> bool { self.last_check_passed }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_push_add_halt() {
        let mut vm = FluxVM::new(100);
        vm.execute(&[0x00, 3, 0x00, 4, 0x06, 0x1A], 100).unwrap();
        assert!(vm.halted);
        assert_eq!(vm.stack[0], 7);
    }

    #[test]
    fn test_assert_fail() {
        let mut vm = FluxVM::new(100);
        let result = vm.execute(&[0x00, 0, 0x1B], 100);
        assert!(result.is_err());
    }

    #[test]
    fn test_guard_trap() {
        let mut vm = FluxVM::new(100);
        let result = vm.execute(&[0x20], 100);
        assert!(matches!(result, Err(f) if f[0] == Fault::GuardTrap));
    }

    #[test]
    fn test_gas_exhaustion() {
        let mut vm = FluxVM::new(2);
        let result = vm.execute(&[0x00, 1, 0x00, 2, 0x00, 3], 100);
        assert!(matches!(result, Err(f) if f[0] == Fault::GasExhausted));
    }

    #[test]
    fn test_jump_control_flow() {
        let mut vm = FluxVM::new(100);
        vm.execute(&[0x00, 0, 0x16, 7, 0x00, 99, 0x1A, 0x00, 42, 0x1A], 100).unwrap();
        assert_eq!(vm.stack[0], 42);
    }

    // === New opcode tests ===

    #[test]
    fn test_dup() {
        let mut vm = FluxVM::new(100);
        // PUSH 7, DUP, HALT → stack has [7, 7]
        vm.execute(&[0x00, 7, 0x02, 0x1A], 100).unwrap();
        assert_eq!(vm.stack_len(), 2);
        assert_eq!(vm.stack_top(), Some(7));
    }

    #[test]
    fn test_swap() {
        let mut vm = FluxVM::new(100);
        // PUSH 3, PUSH 5, SWAP → [5, 3]
        vm.execute(&[0x00, 3, 0x00, 5, 0x03, 0x1A], 100).unwrap();
        assert_eq!(vm.stack_top(), Some(3)); // top is 3 (was bottom)
    }

    #[test]
    fn test_memory_load_store() {
        let mut vm = FluxVM::new(100);
        // PUSH 42, STORE 100, LOAD 100, HALT
        vm.execute(&[0x00, 42, 0x05, 100, 0x04, 100, 0x1A], 100).unwrap();
        assert_eq!(vm.stack_top(), Some(42));
    }

    #[test]
    fn test_shl_shr() {
        let mut vm = FluxVM::new(100);
        // PUSH 1, SHL → 2, SHL → 4, SHR → 2
        vm.execute(&[0x00, 1, 0x0D, 0x0D, 0x0E, 0x1A], 100).unwrap();
        assert_eq!(vm.stack_top(), Some(2));
    }

    #[test]
    fn test_lte_gte() {
        let mut vm = FluxVM::new(100);
        // 5 <= 5 → 1
        vm.execute(&[0x00, 5, 0x00, 5, 0x13, 0x1A], 100).unwrap();
        assert_eq!(vm.stack_top(), Some(1));
    }

    #[test]
    fn test_jnz() {
        let mut vm = FluxVM::new(100);
        // PUSH 1, JNZ 7, PUSH 99, HALT, PUSH 42, HALT
        vm.execute(&[0x00, 1, 0x17, 7, 0x00, 99, 0x1A, 0x00, 42, 0x1A], 100).unwrap();
        assert_eq!(vm.stack_top(), Some(42)); // took the jump
    }

    #[test]
    fn test_call_ret() {
        let mut vm = FluxVM::new(100);
        // CALL 5, HALT, PUSH 42, RET
        vm.execute(&[0x18, 5, 0x1A, 0x00, 42, 0x19, 0x1A], 100).unwrap();
        // After CALL 5, runs PUSH 42, RET, continues to... 
        // Actually CALL pushes return addr (2), jumps to 5
        // addr 5: RET → returns to addr 2 (the HALT)
        assert!(vm.is_halted());
    }

    #[test]
    fn test_check_domain() {
        let mut vm = FluxVM::new(100);
        // PUSH 0x42, CHECK_DOMAIN 0x0F → 0x42 & 0x0F = 0x02
        vm.execute(&[0x00, 0x42, 0x1C, 0x0F, 0x1A], 100).unwrap();
        assert_eq!(vm.stack_top(), Some(0x02));
        assert!(vm.last_check_passed());
    }

    #[test]
    fn test_bitmask_range() {
        let mut vm = FluxVM::new(100);
        // PUSH 50, BITMASK_RANGE 0 100 → in range, push 1
        vm.execute(&[0x00, 50, 0x1D, 0, 100, 0x1A], 100).unwrap();
        assert_eq!(vm.stack_top(), Some(1));
        assert!(vm.last_check_passed());
    }

    #[test]
    fn test_bitmask_range_fail() {
        let mut vm = FluxVM::new(100);
        // PUSH 200, BITMASK_RANGE 0 100 → out of range, push 0
        vm.execute(&[0x00, 200, 0x1D, 0, 100, 0x1A], 100).unwrap();
        assert_eq!(vm.stack_top(), Some(0));
        assert!(!vm.last_check_passed());
    }

    #[test]
    fn test_xnor_popcount() {
        let mut vm = FluxVM::new(100);
        // PUSH 0xFF, PUSH 0xFF, XNOR_POPCOUNT → 8 bits match
        vm.execute(&[0x00, 0xFF, 0x00, 0xFF, 0x23, 0x1A], 100).unwrap();
        assert_eq!(vm.stack_top(), Some(8));
    }

    #[test]
    fn test_carry_lt() {
        let mut vm = FluxVM::new(100);
        // PUSH 3, PUSH 5, CARRY_LT → 3 < 5 = true → 1
        vm.execute(&[0x00, 3, 0x00, 5, 0x25, 0x1A], 100).unwrap();
        assert_eq!(vm.stack_top(), Some(1));
    }

    #[test]
    fn test_jfail() {
        let mut vm = FluxVM::new(100);
        // PUSH 50, BITMASK_RANGE 0 100 → pass, JFAIL should NOT jump
        vm.execute(&[0x00, 50, 0x1D, 0, 100, 0x26, 10, 0x00, 77, 0x1A, 0x20], 100).unwrap();
        assert_eq!(vm.stack_top(), Some(77)); // didn't jump to GUARD_TRAP
    }

    #[test]
    fn test_flush() {
        let mut vm = FluxVM::new(100);
        // PUSH 1, PUSH 2, PUSH 3, FLUSH, PUSH 42, HALT
        vm.execute(&[0x00, 1, 0x00, 2, 0x00, 3, 0x28, 0x00, 42, 0x1A], 100).unwrap();
        assert_eq!(vm.stack_len(), 1);
        assert_eq!(vm.stack_top(), Some(42));
    }

    #[test]
    fn test_yield() {
        let mut vm = FluxVM::new(100);
        vm.step(&[0x29]).unwrap(); // YIELD
        assert!(vm.is_yielded());
        assert!(!vm.is_halted());
    }

    #[test]
    fn test_load_guard() {
        let mut vm = FluxVM::new(100);
        vm.set_guard(0xAB);
        vm.execute(&[0x1E, 0x1A], 100).unwrap(); // LOAD_GUARD, HALT
        assert_eq!(vm.stack_top(), Some(0xAB));
    }

    // === Certification test vectors (15 programs) ===

    #[test]
    fn cert_identity() {
        let mut vm = FluxVM::new(100);
        vm.execute(&[0x00, 42, 0x1A], 100).unwrap();
        assert_eq!(vm.stack[0], 42);
    }

    #[test]
    fn cert_add() {
        let mut vm = FluxVM::new(100);
        vm.execute(&[0x00, 3, 0x00, 4, 0x06, 0x1A], 100).unwrap();
        assert_eq!(vm.stack[0], 7);
    }

    #[test]
    fn cert_mul() {
        let mut vm = FluxVM::new(100);
        vm.execute(&[0x00, 6, 0x00, 7, 0x08, 0x1A], 100).unwrap();
        assert_eq!(vm.stack[0], 42);
    }

    #[test]
    fn cert_sub() {
        let mut vm = FluxVM::new(100);
        vm.execute(&[0x00, 10, 0x00, 3, 0x07, 0x1A], 100).unwrap();
        assert_eq!(vm.stack[0], 7);
    }

    #[test]
    fn cert_and_mask() {
        let mut vm = FluxVM::new(100);
        vm.execute(&[0x00, 0xFF, 0x00, 0x0F, 0x09, 0x1A], 100).unwrap();
        assert_eq!(vm.stack[0], 0x0F);
    }

    #[test]
    fn cert_or() {
        let mut vm = FluxVM::new(100);
        vm.execute(&[0x00, 0xF0, 0x00, 0x0F, 0x0A, 0x1A], 100).unwrap();
        assert_eq!(vm.stack[0], 0xFF);
    }

    #[test]
    fn cert_xor() {
        let mut vm = FluxVM::new(100);
        vm.execute(&[0x00, 0xAA, 0x00, 0x55, 0x0B, 0x1A], 100).unwrap();
        assert_eq!(vm.stack[0], 0xFF);
    }

    #[test]
    fn cert_not() {
        let mut vm = FluxVM::new(100);
        vm.execute(&[0x00, 0x00, 0x0C, 0x1A], 100).unwrap();
        assert_eq!(vm.stack[0], 0xFF);
    }

    #[test]
    fn cert_eq() {
        let mut vm = FluxVM::new(100);
        vm.execute(&[0x00, 7, 0x00, 7, 0x0F, 0x1A], 100).unwrap();
        assert_eq!(vm.stack[0], 1);
    }

    #[test]
    fn cert_neq() {
        let mut vm = FluxVM::new(100);
        vm.execute(&[0x00, 3, 0x00, 5, 0x10, 0x1A], 100).unwrap();
        assert_eq!(vm.stack[0], 1);
    }

    #[test]
    fn cert_lt() {
        let mut vm = FluxVM::new(100);
        vm.execute(&[0x00, 3, 0x00, 5, 0x11, 0x1A], 100).unwrap();
        assert_eq!(vm.stack[0], 1);
    }

    #[test]
    fn cert_gt() {
        let mut vm = FluxVM::new(100);
        vm.execute(&[0x00, 5, 0x00, 3, 0x12, 0x1A], 100).unwrap();
        assert_eq!(vm.stack[0], 1);
    }

    #[test]
    fn cert_jz_skip() {
        let mut vm = FluxVM::new(100);
        vm.execute(&[0x00, 0, 0x16, 7, 0x00, 99, 0x1A, 0x00, 42, 0x1A], 100).unwrap();
        assert_eq!(vm.stack[0], 42);
    }

    #[test]
    fn cert_assert_pass() {
        let mut vm = FluxVM::new(100);
        vm.execute(&[0x00, 1, 0x1B, 0x00, 77, 0x1A], 100).unwrap();
        assert_eq!(vm.stack[0], 77);
    }

    #[test]
    fn cert_nops() {
        let mut vm = FluxVM::new(100);
        vm.execute(&[0x27, 0x27, 0x00, 13, 0x1A], 100).unwrap();
        assert_eq!(vm.stack[0], 13);
    }

    // === Extended tests ===

    #[test]
    fn test_bitwise_and_mask() {
        let mut vm = FluxVM::new(100);
        vm.execute(&[0x00, 0xFF, 0x00, 0x0F, 0x09, 0x1A], 100).unwrap();
        assert_eq!(vm.stack[0], 0x0F);
    }

    #[test]
    fn test_domain_check_pass() {
        let mut vm = FluxVM::new(100);
        vm.execute(&[0x00, 0x42, 0x00, 0x0F, 0x09, 0x00, 0, 0x0F, 0x0C, 0x1B, 0x1A], 100).unwrap();
        assert!(vm.is_halted());
    }

    #[test]
    fn test_xor_swap() {
        let mut vm = FluxVM::new(100);
        vm.execute(&[0x00, 0xAA, 0x00, 0x55, 0x0B, 0x1A], 100).unwrap();
        assert_eq!(vm.stack[0], 0xFF);
    }

    #[test]
    fn test_comparison_gt() {
        let mut vm = FluxVM::new(100);
        vm.execute(&[0x00, 10, 0x00, 5, 0x12, 0x1B, 0x1A], 100).unwrap();
        assert!(vm.is_halted());
    }

    #[test]
    fn test_nested_if_else() {
        let mut vm = FluxVM::new(100);
        vm.execute(&[0x00, 5, 0x00, 3, 0x12, 0x16, 10, 0x00, 42, 0x1A, 0x00, 99, 0x1A], 100).unwrap();
        assert_eq!(vm.stack[0], 42);
    }

    #[test]
    fn test_sub_and_assert() {
        let mut vm = FluxVM::new(100);
        vm.execute(&[0x00, 10, 0x00, 3, 0x07, 0x00, 7, 0x0F, 0x1B, 0x1A], 100).unwrap();
        assert!(vm.is_halted());
    }
}
