//! flux_grpc_service — gRPC Remote Constraint Verification Service (simplified standalone)
//!
//! This is a standalone version that doesn't require tonic/protobuf build infrastructure.
//! The VM logic is self-contained and testable.

/// Simplified FLUX-C VM for the gRPC service
pub struct BytecodeVm {
    code: Vec<u8>,
    pub stack: Vec<f64>,
    locals: Vec<f64>,
}

impl BytecodeVm {
    pub fn new() -> Self {
        BytecodeVm { code: Vec::new(), stack: Vec::with_capacity(32), locals: Vec::with_capacity(16) }
    }

    pub fn load(&mut self, bytecode: &[u8]) {
        self.code = bytecode.to_vec();
    }

    pub fn run(&mut self, inputs: &[f64]) -> (u64, u64, bool) {
        self.locals.clear();
        self.locals.extend_from_slice(inputs);
        self.stack.clear();
        let mut pc = 0usize;
        let mut checks = 0u64;
        let mut violations = 0u64;
        let mut halted = false;

        while pc < self.code.len() && !halted {
            let op = self.code[pc];
            pc += 1;
            match op {
                0x03 => {
                    if pc + 7 < self.code.len() {
                        let v = f64::from_le_bytes([
                            self.code[pc], self.code[pc+1], self.code[pc+2], self.code[pc+3],
                            self.code[pc+4], self.code[pc+5], self.code[pc+6], self.code[pc+7],
                        ]);
                        self.stack.push(v);
                        pc += 8;
                    }
                }
                0x01 => {
                    let idx = self.code.get(pc).copied().unwrap_or(0) as usize;
                    pc += 1;
                    self.stack.push(*self.locals.get(idx).unwrap_or(&0.0));
                }
                0x02 => {
                    let idx = self.code.get(pc).copied().unwrap_or(0) as usize;
                    pc += 1;
                    let v = self.stack.pop().unwrap_or(0.0);
                    if idx >= self.locals.len() { self.locals.resize(idx + 1, 0.0); }
                    self.locals[idx] = v;
                }
                0x04 => { let b = self.pop(); let a = self.pop(); self.stack.push(a + b); }
                0x05 => { let b = self.pop(); let a = self.pop(); self.stack.push(a - b); }
                0x06 => { let b = self.pop(); let a = self.pop(); self.stack.push(a * b); }
                0x07 => { let b = self.pop(); let a = self.pop(); self.stack.push(a / b); }
                0x08 => { let b = self.pop(); let a = self.pop(); self.stack.push(if a != 0.0 && b != 0.0 { 1.0 } else { 0.0 }); }
                0x09 => { let b = self.pop(); let a = self.pop(); self.stack.push(if a != 0.0 || b != 0.0 { 1.0 } else { 0.0 }); }
                0x0A => { let a = self.pop(); self.stack.push(if a == 0.0 { 1.0 } else { 0.0 }); }
                0x0B => { let b = self.pop(); let a = self.pop(); self.stack.push(if a < b { 1.0 } else { 0.0 }); }
                0x0C => { let b = self.pop(); let a = self.pop(); self.stack.push(if a > b { 1.0 } else { 0.0 }); }
                0x0D => { let b = self.pop(); let a = self.pop(); self.stack.push(if a == b { 1.0 } else { 0.0 }); }
                0x0E => { let b = self.pop(); let a = self.pop(); self.stack.push(if a <= b { 1.0 } else { 0.0 }); }
                0x0F => { let b = self.pop(); let a = self.pop(); self.stack.push(if a >= b { 1.0 } else { 0.0 }); }
                0x10 => { let b = self.pop(); let a = self.pop(); self.stack.push(if a != b { 1.0 } else { 0.0 }); }
                0x16 => { checks += 1; let v = self.pop(); if v == 0.0 { violations += 1; } }
                0x17 => { checks += 1; let v = self.pop(); if v == 0.0 { violations += 1; halted = true; } }
                0x18 => halted = true,
                _ => {}
            }
        }
        (checks, violations, halted)
    }

    fn pop(&mut self) -> f64 { self.stack.pop().unwrap_or(0.0) }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_vm_const_add() {
        let mut vm = BytecodeVm::new();
        vm.load(&[
            0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x40, 0x08, 0x00, 0x00,
            0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x40, 0x10, 0x00, 0x00,
            0x04, 0x18,
        ]);
        vm.run(&[]);
        assert_eq!(vm.stack.len(), 1);
        assert!((vm.stack[0] - 7.0).abs() < 1e-9);
    }

    #[test]
    fn test_vm_lt() {
        let mut vm = BytecodeVm::new();
        vm.load(&[
            0x01, 0x00,
            0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x40, 0x5E, 0x00, 0x00,
            0x0B, 0x18,
        ]);
        let (checks, violations, _) = vm.run(&[50.0]);
        assert_eq!(vm.stack[0], 1.0);
        assert_eq!(checks, 0);
        assert_eq!(violations, 0);
    }

    #[test]
    fn test_vm_check_violation() {
        let mut vm = BytecodeVm::new();
        vm.load(&[
            0x01, 0x00,
            0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x40, 0x5E, 0x00, 0x00,
            0x0B, 0x16, 0x18,
        ]);
        let (checks, violations, halted) = vm.run(&[150.0]);
        assert_eq!(checks, 1);
        assert_eq!(violations, 1);
        assert!(!halted);
    }

    #[test]
    fn test_vm_and() {
        let mut vm = BytecodeVm::new();
        vm.load(&[
            0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x3F, 0xF0, 0x00, 0x00,
            0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x08, 0x18,
        ]);
        vm.run(&[]);
        assert_eq!(vm.stack.len(), 1);
        assert_eq!(vm.stack[0], 0.0);
    }
}
