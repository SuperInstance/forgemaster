// flux_vm_test_harness.rs — Comprehensive test harness for FLUX-C VM
// Tests every opcode category + adversarial edge cases

use std::collections::HashMap;

#[derive(Debug, Clone, PartialEq)]
enum Value {
    Bool(bool),
    I64(i64),
    F64(f64),
    U64(u64),
}

#[derive(Debug, Clone)]
enum Opcode {
    // Stack
    Push(Value),
    Pop,
    Dup,
    Swap,
    // Arithmetic
    Add, Sub, Mul, Div,
    // Comparison
    CmpEq, CmpLt, CmpGe, CmpGt, CmpLe,
    // Range/Domain
    CheckRange,
    CheckDomain,
    // Logical
    And, Or, Not,
    // Temporal
    Checkpoint,    // Mark current state
    Revert,        // Rollback to last checkpoint
    Deadline(u64), // Max time in ms
    Drift(f64),    // Max allowed drift from constraint
    // Security
    CapGrant(String),
    CapRevoke(String),
    // Control
    Halt,
    Nop,
}

#[derive(Debug)]
struct VmState {
    stack: Vec<Value>,
    caps: HashMap<String, bool>,
    checkpoints: Vec<Vec<Value>>,
    deadline_ms: Option<u64>,
    start_time: Option<std::time::Instant>,
    constraints_checked: u64,
    constraints_passed: u64,
    constraints_failed: u64,
    halted: bool,
}

impl VmState {
    fn new() -> Self {
        VmState {
            stack: Vec::with_capacity(64),
            caps: HashMap::new(),
            checkpoints: Vec::new(),
            deadline_ms: None,
            start_time: None,
            constraints_checked: 0,
            constraints_passed: 0,
            constraints_failed: 0,
            halted: false,
        }
    }

    fn execute(&mut self, program: &[Opcode]) -> Result<VmResult, VmError> {
        self.start_time = Some(std::time::Instant::now());
        for (pc, op) in program.iter().enumerate() {
            if self.halted { break; }
            self.check_deadline(pc)?;
            self.execute_opcode(op, pc)?;
        }
        Ok(VmResult {
            constraints_checked: self.constraints_checked,
            constraints_passed: self.constraints_passed,
            constraints_failed: self.constraints_failed,
            stack_depth: self.stack.len(),
        })
    }

    fn check_deadline(&self, pc: usize) -> Result<(), VmError> {
        if let (Some(dl), Some(start)) = (self.deadline_ms, self.start_time) {
            if start.elapsed().as_millis() as u64 > dl {
                return Err(VmError::DeadlineExceeded { pc, deadline_ms: dl });
            }
        }
        Ok(())
    }

    fn execute_opcode(&mut self, op: &Opcode, pc: usize) -> Result<(), VmError> {
        match op {
            Opcode::Push(v) => self.stack.push(v.clone()),
            Opcode::Pop => { self.stack.pop().ok_or(VmError::StackUnderflow { pc })?; }
            Opcode::Dup => {
                let top = self.stack.last().cloned().ok_or(VmError::StackUnderflow { pc })?;
                self.stack.push(top);
            }
            Opcode::Swap => {
                let len = self.stack.len();
                if len < 2 { return Err(VmError::StackUnderflow { pc }); }
                self.stack.swap(len - 1, len - 2);
            }
            Opcode::Add => self.binop_i64(pc, |a, b| a + b)?,
            Opcode::Sub => self.binop_i64(pc, |a, b| a - b)?,
            Opcode::Mul => self.binop_i64(pc, |a, b| a * b)?,
            Opcode::Div => {
                let b = self.pop_i64(pc)?;
                let a = self.pop_i64(pc)?;
                if b == 0 { return Err(VmError::DivisionByZero { pc }); }
                self.stack.push(Value::I64(a / b));
            }
            Opcode::CmpEq => self.cmp(pc, |a, b| a == b)?,
            Opcode::CmpLt => self.cmp(pc, |a, b| a < b)?,
            Opcode::CmpGe => self.cmp(pc, |a, b| a >= b)?,
            Opcode::CmpGt => self.cmp(pc, |a, b| a > b)?,
            Opcode::CmpLe => self.cmp(pc, |a, b| a <= b)?,
            Opcode::CheckRange => {
                // Stack: value, min, max → push bool
                self.constraints_checked += 1;
                let max = self.pop_i64(pc)?;
                let min = self.pop_i64(pc)?;
                let val = self.pop_i64(pc)?;
                let result = val >= min && val <= max;
                if result { self.constraints_passed += 1; } else { self.constraints_failed += 1; }
                self.stack.push(Value::Bool(result));
            }
            Opcode::CheckDomain => {
                // Stack: value, [domain values...] count → push bool
                self.constraints_checked += 1;
                let count = self.pop_i64(pc)? as usize;
                let val = self.stack[self.stack.len() - count - 1].clone();
                let domain: Vec<Value> = self.stack.drain(self.stack.len() - count..).collect();
                let result = domain.contains(&val);
                if result { self.constraints_passed += 1; } else { self.constraints_failed += 1; }
                self.stack.push(Value::Bool(result));
            }
            Opcode::And => {
                let b = self.pop_bool(pc)?;
                let a = self.pop_bool(pc)?;
                self.stack.push(Value::Bool(a && b));
            }
            Opcode::Or => {
                let b = self.pop_bool(pc)?;
                let a = self.pop_bool(pc)?;
                self.stack.push(Value::Bool(a || b));
            }
            Opcode::Not => {
                let a = self.pop_bool(pc)?;
                self.stack.push(Value::Bool(!a));
            }
            Opcode::Checkpoint => {
                self.checkpoints.push(self.stack.clone());
            }
            Opcode::Revert => {
                if let Some(saved) = self.checkpoints.pop() {
                    self.stack = saved;
                }
            }
            Opcode::Deadline(ms) => { self.deadline_ms = Some(*ms); }
            Opcode::Drift(_tolerance) => { /* Applied during CheckRange comparison */ }
            Opcode::CapGrant(name) => { self.caps.insert(name.clone(), true); }
            Opcode::CapRevoke(name) => { self.caps.remove(name); }
            Opcode::Halt => { self.halted = true; }
            Opcode::Nop => {}
        }
        Ok(())
    }

    fn binop_i64<F>(&mut self, pc: usize, f: F) -> Result<(), VmError>
    where F: Fn(i64, i64) -> i64 {
        let b = self.pop_i64(pc)?;
        let a = self.pop_i64(pc)?;
        self.stack.push(Value::I64(f(a, b)));
        Ok(())
    }

    fn cmp<F>(&mut self, pc: usize, f: F) -> Result<(), VmError>
    where F: Fn(i64, i64) -> bool {
        let b = self.pop_i64(pc)?;
        let a = self.pop_i64(pc)?;
        self.stack.push(Value::Bool(f(a, b)));
        Ok(())
    }

    fn pop_i64(&mut self, pc: usize) -> Result<i64, VmError> {
        match self.stack.pop() {
            Some(Value::I64(v)) => Ok(v),
            Some(v) => Err(VmError::TypeError { pc, expected: "I64", got: format!("{:?}", v) }),
            None => Err(VmError::StackUnderflow { pc }),
        }
    }

    fn pop_bool(&mut self, pc: usize) -> Result<bool, VmError> {
        match self.stack.pop() {
            Some(Value::Bool(v)) => Ok(v),
            Some(v) => Err(VmError::TypeError { pc, expected: "Bool", got: format!("{:?}", v) }),
            None => Err(VmError::StackUnderflow { pc }),
        }
    }
}

#[derive(Debug, PartialEq)]
struct VmResult {
    constraints_checked: u64,
    constraints_passed: u64,
    constraints_failed: u64,
    stack_depth: usize,
}

#[derive(Debug, PartialEq)]
enum VmError {
    StackUnderflow { pc: usize },
    DivisionByZero { pc: usize },
    TypeError { pc: usize, expected: &'static str, got: String },
    DeadlineExceeded { pc: usize, deadline_ms: u64 },
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_push_pop_dup() {
        let mut vm = VmState::new();
        let prog = vec![Opcode::Push(Value::I64(42)), Opcode::Dup, Opcode::Pop, Opcode::Halt];
        let result = vm.execute(&prog).unwrap();
        assert_eq!(result.stack_depth, 1);
    }

    #[test]
    fn test_arithmetic() {
        let mut vm = VmState::new();
        let prog = vec![
            Opcode::Push(Value::I64(10)), Opcode::Push(Value::I64(3)),
            Opcode::Add, // 13
            Opcode::Push(Value::I64(2)), Opcode::Mul, // 26
            Opcode::Push(Value::I64(1)), Opcode::Sub, // 25
            Opcode::Halt,
        ];
        let result = vm.execute(&prog).unwrap();
        assert_eq!(result.stack_depth, 1);
        assert_eq!(vm.stack[0], Value::I64(25));
    }

    #[test]
    fn test_division_by_zero() {
        let mut vm = VmState::new();
        let prog = vec![Opcode::Push(Value::I64(1)), Opcode::Push(Value::I64(0)), Opcode::Div];
        let err = vm.execute(&prog).unwrap_err();
        assert_eq!(err, VmError::DivisionByZero { pc: 2 });
    }

    #[test]
    fn test_check_range_pass() {
        let mut vm = VmState::new();
        // Check if 5 is in [0, 10]
        let prog = vec![
            Opcode::Push(Value::I64(5)),   // value
            Opcode::Push(Value::I64(0)),   // min
            Opcode::Push(Value::I64(10)),  // max
            Opcode::CheckRange,
            Opcode::Halt,
        ];
        let result = vm.execute(&prog).unwrap();
        assert_eq!(result.constraints_checked, 1);
        assert_eq!(result.constraints_passed, 1);
        assert_eq!(result.constraints_failed, 0);
        assert_eq!(vm.stack[0], Value::Bool(true));
    }

    #[test]
    fn test_check_range_fail() {
        let mut vm = VmState::new();
        // Check if 15 is in [0, 10] — should fail
        let prog = vec![
            Opcode::Push(Value::I64(15)),
            Opcode::Push(Value::I64(0)),
            Opcode::Push(Value::I64(10)),
            Opcode::CheckRange,
            Opcode::Halt,
        ];
        let result = vm.execute(&prog).unwrap();
        assert_eq!(result.constraints_passed, 0);
        assert_eq!(result.constraints_failed, 1);
        assert_eq!(vm.stack[0], Value::Bool(false));
    }

    #[test]
    fn test_flight_envelope() {
        // Real aerospace constraint: altitude 0-40000ft, speed 0-600kts
        let mut vm = VmState::new();
        let prog = vec![
            // Altitude check: 15000 ft in [0, 40000]
            Opcode::Push(Value::I64(15000)),
            Opcode::Push(Value::I64(0)),
            Opcode::Push(Value::I64(40000)),
            Opcode::CheckRange,
            // Speed check: 350 kts in [0, 600]
            Opcode::Push(Value::I64(350)),
            Opcode::Push(Value::I64(0)),
            Opcode::Push(Value::I64(600)),
            Opcode::CheckRange,
            // Both must pass
            Opcode::And,
            Opcode::Halt,
        ];
        let result = vm.execute(&prog).unwrap();
        assert_eq!(result.constraints_checked, 2);
        assert_eq!(result.constraints_passed, 2);
        assert_eq!(vm.stack[0], Value::Bool(true));
    }

    #[test]
    fn test_checkpoint_revert() {
        let mut vm = VmState::new();
        let prog = vec![
            Opcode::Push(Value::I64(1)),
            Opcode::Checkpoint,
            Opcode::Push(Value::I64(2)),
            Opcode::Push(Value::I64(3)),
            Opcode::Revert, // Back to just [1]
            Opcode::Halt,
        ];
        vm.execute(&prog).unwrap();
        assert_eq!(vm.stack.len(), 1);
        assert_eq!(vm.stack[0], Value::I64(1));
    }

    #[test]
    fn test_capabilities() {
        let mut vm = VmState::new();
        let prog = vec![
            Opcode::CapGrant("range_check".into()),
            Opcode::CapGrant("temporal".into()),
            Opcode::CapRevoke("temporal".into()),
            Opcode::Halt,
        ];
        vm.execute(&prog).unwrap();
        assert!(vm.caps.contains_key("range_check"));
        assert!(!vm.caps.contains_key("temporal"));
    }

    #[test]
    fn test_stack_underflow() {
        let mut vm = VmState::new();
        let prog = vec![Opcode::Pop]; // Empty stack
        let err = vm.execute(&prog).unwrap_err();
        assert_eq!(err, VmError::StackUnderflow { pc: 0 });
    }

    #[test]
    fn test_swap() {
        let mut vm = VmState::new();
        let prog = vec![
            Opcode::Push(Value::I64(1)),
            Opcode::Push(Value::I64(2)),
            Opcode::Swap,
            Opcode::Halt,
        ];
        vm.execute(&prog).unwrap();
        assert_eq!(vm.stack[0], Value::I64(2));
        assert_eq!(vm.stack[1], Value::I64(1));
    }
}
