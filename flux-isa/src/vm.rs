//! Constraint VM — Stack-based virtual machine for FLUX bytecode execution

use crate::bytecode::FluxBytecode;
use crate::error::FluxError;
use crate::opcode::FluxOpcode;

/// Result of constraint VM execution
#[derive(Debug, Clone)]
pub struct VMResult {
    /// Output values from execution
    pub outputs: Vec<f64>,
    /// Whether all constraint checks passed
    pub constraints_satisfied: bool,
    /// Step-by-step execution trace for provenance
    pub execution_trace: Vec<TraceEntry>,
}

/// Single step in the execution trace
#[derive(Debug, Clone)]
pub struct TraceEntry {
    pub step: usize,
    pub opcode: FluxOpcode,
    pub stack_before: Vec<f64>,
    pub stack_after: Vec<f64>,
    pub constraint_result: Option<bool>,
}

/// Stack-based constraint virtual machine
pub struct ConstraintVM {
    stack: Vec<f64>,
    call_stack: Vec<usize>,
    trace: Vec<TraceEntry>,
    constraint_results: Vec<bool>,
}

impl ConstraintVM {
    pub fn new() -> Self {
        Self {
            stack: Vec::with_capacity(256),
            call_stack: Vec::new(),
            trace: Vec::new(),
            constraint_results: Vec::new(),
        }
    }

    /// Execute a FLUX bytecode program
    pub fn execute(&mut self, bytecode: &FluxBytecode) -> Result<VMResult, FluxError> {
        self.stack.clear();
        self.call_stack.clear();
        self.trace.clear();
        self.constraint_results.clear();

        let instructions = &bytecode.instructions;
        let mut ip: usize = 0;

        while ip < instructions.len() {
            let instr = &instructions[ip];
            let stack_before = self.stack.clone();

            match instr.opcode {
                // Arithmetic
                FluxOpcode::Add => self.binop(|a, b| a + b)?,
                FluxOpcode::Sub => self.binop(|a, b| a - b)?,
                FluxOpcode::Mul => self.binop(|a, b| a * b)?,
                FluxOpcode::Div => {
                    let b = self.stack.last().copied().ok_or(FluxError::StackUnderflow)?;
                    if b == 0.0 {
                        return Err(FluxError::ArithmeticError("division by zero".into()));
                    }
                    self.binop(|a, b| a / b)?;
                }
                FluxOpcode::Mod => self.binop(|a, b| a % b)?,

                // Constraint operations
                FluxOpcode::Assert => {
                    let val = self.pop()?;
                    let ok = val != 0.0;
                    self.constraint_results.push(ok);
                    if !ok {
                        let label = instr.metadata.label.clone().unwrap_or_default();
                        return Err(FluxError::ConstraintViolation(
                            format!("step {}: {}", ip, label),
                        ));
                    }
                }
                FluxOpcode::Check => {
                    let val = self.pop()?;
                    let ok = val != 0.0;
                    self.constraint_results.push(ok);
                    self.stack.push(if ok { 1.0 } else { 0.0 });
                }
                FluxOpcode::Validate => {
                    let val = self.pop()?;
                    let min = instr.operands.get(0).copied().unwrap_or(f64::NEG_INFINITY);
                    let max = instr.operands.get(1).copied().unwrap_or(f64::INFINITY);
                    let ok = val >= min && val <= max;
                    self.constraint_results.push(ok);
                    self.stack.push(if ok { 1.0 } else { 0.0 });
                }
                FluxOpcode::Reject => {
                    let label = instr.metadata.label.clone().unwrap_or_else(|| "Explicit reject".into());
                    return Err(FluxError::ConstraintViolation(
                        format!("step {}: {}", ip, label),
                    ));
                }

                // Flow control
                FluxOpcode::Jump => {
                    let target = instr.operands.get(0).copied().unwrap_or(0.0) as usize;
                    ip = target;
                    continue;
                }
                FluxOpcode::Branch => {
                    let cond = self.pop()?;
                    let target = instr.operands.get(0).copied().unwrap_or(0.0) as usize;
                    if cond != 0.0 {
                        ip = target;
                        continue;
                    }
                }
                FluxOpcode::Call => {
                    let target = instr.operands.get(0).copied().unwrap_or(0.0) as usize;
                    self.call_stack.push(ip + 1);
                    ip = target;
                    continue;
                }
                FluxOpcode::Return => {
                    match self.call_stack.pop() {
                        Some(ret_addr) => ip = ret_addr,
                        None => break,
                    }
                    continue;
                }
                FluxOpcode::Halt => break,

                // Memory / Stack
                FluxOpcode::Load => {
                    let val = instr.operands.get(0).copied().unwrap_or(0.0);
                    self.stack.push(val);
                }
                FluxOpcode::Store => { let _ = self.pop()?; }
                FluxOpcode::Push => {
                    for &v in &instr.operands {
                        self.stack.push(v);
                    }
                }
                FluxOpcode::Pop => { self.pop()?; }
                FluxOpcode::Swap => {
                    let len = self.stack.len();
                    if len >= 2 {
                        self.stack.swap(len - 1, len - 2);
                    }
                }

                // Convert
                FluxOpcode::Snap => {
                    let val = self.pop()?;
                    self.stack.push(val.round());
                }
                FluxOpcode::Quantize => {
                    let val = self.pop()?;
                    let step = instr.operands.get(0).copied().unwrap_or(1.0);
                    self.stack.push((val / step).round() * step);
                }
                FluxOpcode::Cast | FluxOpcode::Promote => {}

                // Logic
                FluxOpcode::And => self.binop(|a, b| if a != 0.0 && b != 0.0 { 1.0 } else { 0.0 })?,
                FluxOpcode::Or => self.binop(|a, b| if a != 0.0 || b != 0.0 { 1.0 } else { 0.0 })?,
                FluxOpcode::Not => {
                    let val = self.pop()?;
                    self.stack.push(if val == 0.0 { 1.0 } else { 0.0 });
                }
                FluxOpcode::Xor => self.binop(|a, b| if (a != 0.0) != (b != 0.0) { 1.0 } else { 0.0 })?,

                // Compare
                FluxOpcode::Eq => self.binop(|a, b| if (a - b).abs() < f64::EPSILON { 1.0 } else { 0.0 })?,
                FluxOpcode::Neq => self.binop(|a, b| if (a - b).abs() >= f64::EPSILON { 1.0 } else { 0.0 })?,
                FluxOpcode::Lt => self.binop(|a, b| if a < b { 1.0 } else { 0.0 })?,
                FluxOpcode::Gt => self.binop(|a, b| if a > b { 1.0 } else { 0.0 })?,
                FluxOpcode::Lte => self.binop(|a, b| if a <= b { 1.0 } else { 0.0 })?,
                FluxOpcode::Gte => self.binop(|a, b| if a >= b { 1.0 } else { 0.0 })?,

                // INT8 Saturation (FLUX-X extended)
                FluxOpcode::SatAdd => self.binop(|a, b| {
                    let r = a + b;
                    r.max(-128.0).min(127.0)
                })?,
                FluxOpcode::SatSub => self.binop(|a, b| {
                    let r = a - b;
                    r.max(-128.0).min(127.0)
                })?,
                FluxOpcode::Clip => {
                    let upper = instr.operands.get(1).copied().unwrap_or(127.0);
                    let lower = instr.operands.get(0).copied().unwrap_or(-128.0);
                    let val = self.pop()?;
                    self.stack.push(val.max(lower).min(upper));
                }
                FluxOpcode::Mad => {
                    let c = self.pop()?;
                    let b = self.pop()?;
                    let a = self.pop()?;
                    self.stack.push(a * b + c);
                }
                FluxOpcode::Popcnt => {
                    let val = self.pop()?;
                    let bits = val as i64;
                    self.stack.push(bits.count_ones() as f64);
                }
                FluxOpcode::Ctz => {
                    let val = self.pop()?;
                    let bits = val as i64;
                    self.stack.push(bits.trailing_zeros() as f64);
                }
                FluxOpcode::Pabs => {
                    let val = self.pop()?;
                    self.stack.push(val.abs());
                }
                FluxOpcode::Pmin => self.binop(f64::min)?,

                // Special
                FluxOpcode::Nop | FluxOpcode::Debug | FluxOpcode::Trace | FluxOpcode::Dump => {}
            }

            self.trace.push(TraceEntry {
                step: ip,
                opcode: instr.opcode,
                stack_before,
                stack_after: self.stack.clone(),
                constraint_result: self.constraint_results.last().copied(),
            });

            ip += 1;
        }

        let all_satisfied = !self.constraint_results.is_empty()
            && self.constraint_results.iter().all(|&r| r);

        Ok(VMResult {
            outputs: self.stack.clone(),
            constraints_satisfied: all_satisfied,
            execution_trace: self.trace.clone(),
        })
    }

    fn pop(&mut self) -> Result<f64, FluxError> {
        self.stack.pop().ok_or(FluxError::StackUnderflow)
    }

    fn binop<F: Fn(f64, f64) -> f64>(&mut self, op: F) -> Result<(), FluxError> {
        let b = self.pop()?;
        let a = self.pop()?;
        self.stack.push(op(a, b));
        Ok(())
    }
}

impl Default for ConstraintVM {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::instruction::FluxInstruction;

    fn make_bc(instrs: Vec<FluxInstruction>) -> FluxBytecode {
        FluxBytecode { instructions: instrs }
    }

    #[test]
    fn test_add() {
        let bc = make_bc(vec![
            FluxInstruction::with_operands(FluxOpcode::Load, vec![3.0]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![4.0]),
            FluxInstruction::new(FluxOpcode::Add),
            FluxInstruction::new(FluxOpcode::Halt),
        ]);
        let mut vm = ConstraintVM::new();
        let result = vm.execute(&bc).unwrap();
        assert_eq!(result.outputs, vec![7.0]);
    }

    #[test]
    fn test_constraint_violation() {
        let bc = make_bc(vec![
            FluxInstruction::with_operands(FluxOpcode::Load, vec![0.0]),
            FluxInstruction::new(FluxOpcode::Assert),
        ]);
        let mut vm = ConstraintVM::new();
        let result = vm.execute(&bc);
        assert!(result.is_err());
    }

    #[test]
    fn test_validate_bounds() {
        let bc = make_bc(vec![
            FluxInstruction::with_operands(FluxOpcode::Load, vec![5.0]),
            FluxInstruction::with_operands(FluxOpcode::Validate, vec![0.0, 10.0]),
            FluxInstruction::new(FluxOpcode::Halt),
        ]);
        let mut vm = ConstraintVM::new();
        let result = vm.execute(&bc).unwrap();
        assert_eq!(result.outputs[0], 1.0);
    }

    #[test]
    fn test_snap() {
        let bc = make_bc(vec![
            FluxInstruction::with_operands(FluxOpcode::Load, vec![3.7]),
            FluxInstruction::new(FluxOpcode::Snap),
            FluxInstruction::new(FluxOpcode::Halt),
        ]);
        let mut vm = ConstraintVM::new();
        let result = vm.execute(&bc).unwrap();
        assert_eq!(result.outputs, vec![4.0]);
    }

    #[test]
    fn test_saturation_clamp_positive() {
        let bc = make_bc(vec![
            FluxInstruction::with_operands(FluxOpcode::Load, vec![200.0]),
            FluxInstruction::with_operands(FluxOpcode::Validate, vec![0.0, 127.0]),
            FluxInstruction::new(FluxOpcode::Halt),
        ]);
        let mut vm = ConstraintVM::new();
        let result = vm.execute(&bc);
        // 200 > 127 → should violate
        assert!(result.is_ok());
        assert!(!result.unwrap().constraints_satisfied);
    }

    #[test]
    fn test_saturation_boundary_127() {
        let bc = make_bc(vec![
            FluxInstruction::with_operands(FluxOpcode::Load, vec![127.0]),
            FluxInstruction::with_operands(FluxOpcode::Validate, vec![-127.0, 127.0]),
            FluxInstruction::new(FluxOpcode::Halt),
        ]);
        let mut vm = ConstraintVM::new();
        let result = vm.execute(&bc).unwrap();
        assert!(result.constraints_satisfied);
        assert_eq!(result.outputs[0], 1.0);
    }

    #[test]
    fn test_saturation_boundary_neg127() {
        let bc = make_bc(vec![
            FluxInstruction::with_operands(FluxOpcode::Load, vec![-127.0]),
            FluxInstruction::with_operands(FluxOpcode::Validate, vec![-127.0, 127.0]),
            FluxInstruction::new(FluxOpcode::Halt),
        ]);
        let mut vm = ConstraintVM::new();
        let result = vm.execute(&bc).unwrap();
        assert!(result.constraints_satisfied);
        assert_eq!(result.outputs[0], 1.0);
    }

    #[test]
    fn test_subtraction() {
        let bc = make_bc(vec![
            FluxInstruction::with_operands(FluxOpcode::Load, vec![10.0]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![3.0]),
            FluxInstruction::new(FluxOpcode::Sub),
            FluxInstruction::new(FluxOpcode::Halt),
        ]);
        let mut vm = ConstraintVM::new();
        let result = vm.execute(&bc).unwrap();
        assert_eq!(result.outputs, vec![7.0]);
    }

    #[test]
    fn test_multiplication() {
        let bc = make_bc(vec![
            FluxInstruction::with_operands(FluxOpcode::Load, vec![6.0]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![7.0]),
            FluxInstruction::new(FluxOpcode::Mul),
            FluxInstruction::new(FluxOpcode::Halt),
        ]);
        let mut vm = ConstraintVM::new();
        let result = vm.execute(&bc).unwrap();
        assert_eq!(result.outputs, vec![42.0]);
    }

    #[test]
    fn test_comparison_lt() {
        let bc = make_bc(vec![
            FluxInstruction::with_operands(FluxOpcode::Load, vec![3.0]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![5.0]),
            FluxInstruction::new(FluxOpcode::Lt),
            FluxInstruction::new(FluxOpcode::Halt),
        ]);
        let mut vm = ConstraintVM::new();
        let result = vm.execute(&bc).unwrap();
        // 3 < 5 → 1.0
        assert_eq!(result.outputs, vec![1.0]);
    }

    #[test]
    fn test_stack_underflow() {
        let bc = make_bc(vec![
            FluxInstruction::new(FluxOpcode::Add), // empty stack → error
        ]);
        let mut vm = ConstraintVM::new();
        let result = vm.execute(&bc);
        assert!(result.is_err());
    }

    #[test]
    fn test_execution_trace() {
        let bc = make_bc(vec![
            FluxInstruction::with_operands(FluxOpcode::Load, vec![5.0]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![3.0]),
            FluxInstruction::new(FluxOpcode::Add),
            FluxInstruction::new(FluxOpcode::Halt),
        ]);
        let mut vm = ConstraintVM::new();
        let result = vm.execute(&bc).unwrap();
        // Should have 3+ trace entries (Load, Load, Add, [Halt optional])
        assert!(result.execution_trace.len() >= 3);
    }

    #[test]
    fn test_multiple_constraints_all_pass() {
        let bc = make_bc(vec![
            FluxInstruction::with_operands(FluxOpcode::Load, vec![50.0]),
            FluxInstruction::with_operands(FluxOpcode::Validate, vec![0.0, 100.0]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![-50.0]),
            FluxInstruction::with_operands(FluxOpcode::Validate, vec![-127.0, 0.0]),
            FluxInstruction::new(FluxOpcode::Halt),
        ]);
        let mut vm = ConstraintVM::new();
        let result = vm.execute(&bc).unwrap();
        assert!(result.constraints_satisfied);
    }
}
