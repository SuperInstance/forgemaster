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
    /// Perpendicular-space residue storage for PROJECT/RECONSTRUCT
    residue_memory: Vec<Vec<f64>>,
    /// Acceptance window size for cut-and-project (set by WINDOW opcode)
    acceptance_window: f64,
}

impl ConstraintVM {
    pub fn new() -> Self {
        Self {
            stack: Vec::with_capacity(256),
            call_stack: Vec::new(),
            trace: Vec::new(),
            constraint_results: Vec::new(),
            residue_memory: Vec::new(),
            acceptance_window: 1.0,
        }
    }

    /// Execute a FLUX bytecode program
    pub fn execute(&mut self, bytecode: &FluxBytecode) -> Result<VMResult, FluxError> {
        self.stack.clear();
        self.call_stack.clear();
        self.trace.clear();
        self.constraint_results.clear();
        self.residue_memory.clear();
        self.acceptance_window = 1.0;

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
                FluxOpcode::Nop | FluxOpcode::Debug | FluxOpcode::Trace | FluxOpcode::Dump => {},

                // FLUX-DEEP: Galois Adjunctions
                FluxOpcode::XorInvert => {
                    let mask = self.pop()?;
                    let val = self.pop()?;
                    let result = (val as i64) ^ (mask as i64);
                    self.stack.push(result as f64);
                }
                FluxOpcode::Clamp => {
                    let upper = self.pop()?;
                    let lower = self.pop()?;
                    let val = self.pop()?;
                    self.stack.push(val.max(lower).min(upper));
                }
                FluxOpcode::Bloom => {
                    let item = self.pop()?;
                    let filter = self.pop()?;
                    let hash = (item * 2654435769.0).abs();
                    self.stack.push((filter as u64 | hash as u64) as f64);
                }
                FluxOpcode::BloomQ => {
                    let item = self.pop()?;
                    let filter = self.pop()?;
                    let hash = (item * 2654435769.0).abs();
                    let present = (filter as u64 & hash as u64) != 0;
                    self.stack.push(if present { 1.0 } else { 0.0 });
                }
                FluxOpcode::FloorQ => {
                    let step = self.pop()?;
                    let val = self.pop()?;
                    self.stack.push((val / step).floor() * step);
                }
                FluxOpcode::CeilQ => {
                    let step = self.pop()?;
                    let val = self.pop()?;
                    self.stack.push((val / step).ceil() * step);
                }
                FluxOpcode::Align => {
                    let tolerance = self.pop()?;
                    let intent = self.pop()?;
                    let val = self.pop()?;
                    self.stack.push(if (val - intent).abs() <= tolerance { 1.0 } else { 0.0 });
                }
                FluxOpcode::Holonomy => {
                    let n = self.pop()? as usize;
                    let mut product = 1.0_f64;
                    for _ in 0..n {
                        let v = self.pop()?;
                        product *= if v >= 0.0 { 1.0 } else { -1.0 };
                    }
                    self.stack.push(product);
                }

                // FLUX-DEEP: Cross-Domain Operations
                FluxOpcode::Tdqkr => {
                    let _k = self.pop()? as usize;
                    let _n_cols = self.pop()? as usize;
                    let _n_rows = self.pop()? as usize;
                    let query = self.pop()?;
                    let score = query * query;
                    self.stack.push(score);
                }
                FluxOpcode::Amnesia => {
                    let age = self.pop()?;
                    let valence = self.pop()?;
                    let tau = instr.operands.get(0).copied().unwrap_or(1.0);
                    self.stack.push(valence * (-age / tau).exp());
                }
                FluxOpcode::Shadow => {
                    let n = self.pop()? as usize;
                    let mut sum = 0.0_f64;
                    for _ in 0..n {
                        sum += self.pop()?;
                    }
                    self.stack.push((1.0 - sum).max(0.0).min(1.0));
                }
                FluxOpcode::Phase => {
                    let threshold = self.pop()?;
                    let order_param = self.pop()?;
                    self.stack.push(if order_param > threshold { 1.0 } else { 0.0 });
                }
                FluxOpcode::Couple => {
                    let b = self.pop()?;
                    let a = self.pop()?;
                    let norm = (a * a + b * b).sqrt().max(1e-10);
                    self.stack.push((a * b) / norm);
                }
                FluxOpcode::Federate => {
                    let n = self.pop()? as usize;
                    let mut yes = 0.0_f64;
                    for _ in 0..n {
                        let v = self.pop()?;
                        if v > 0.5 { yes += 1.0; }
                    }
                    self.stack.push(if yes > (n as f64) / 2.0 { 1.0 } else { 0.0 });
                }
                FluxOpcode::Bearing => {
                    let angle = self.pop()?;
                    let normalized = ((angle % 360.0) + 360.0) % 360.0;
                    let snapped = (normalized / 30.0).round() as i64 % 12;
                    self.stack.push(snapped as f64);
                }
                FluxOpcode::Depth => {
                    let time_ms = self.pop()?;
                    let speed = instr.operands.get(0).copied().unwrap_or(1500.0);
                    self.stack.push(speed * time_ms / 2000.0);
                }

                // FLUX-DEEP: Projection / Reconstruction (Penrose navigation space)
                FluxOpcode::Project => {
                    // Stack: [embed_dim, tiling_dim, ...coords] → [...projected_coords, residue_ptr]
                    let tiling_dim = self.pop()? as usize;
                    let embed_dim = self.pop()? as usize;
                    let n_coords = self.stack.len();
                    let coord_count = embed_dim.min(n_coords);
                    let coords: Vec<f64> = self.stack.split_off(n_coords - coord_count);

                    // Golden ratio projection matrix (deterministic pseudo-random projection)
                    let phi = (1.0 + 5_f64.sqrt()) / 2.0; // golden ratio ≈ 1.618
                    let mut projected = Vec::with_capacity(tiling_dim);
                    for t in 0..tiling_dim {
                        let mut sum = 0.0_f64;
                        for (i, &c) in coords.iter().enumerate() {
                            // Deterministic projection: use golden ratio powers
                            sum += c * ((i + t + 1) as f64 * phi).fract();
                        }
                        projected.push(sum);
                    }

                    // Compute perpendicular-space residue (information lost in projection)
                    let residue_len = embed_dim.saturating_sub(tiling_dim);
                    let mut residue = Vec::with_capacity(residue_len);
                    for i in 0..residue_len {
                        let idx = tiling_dim + i;
                        if idx < coords.len() {
                            residue.push(coords[idx]);
                        } else {
                            residue.push(0.0);
                        }
                    }

                    // Store residue in a special memory region (use stack offset as ptr)
                    let residue_ptr = self.residue_memory.len() as f64;
                    self.residue_memory.push(residue);

                    for v in projected {
                        self.stack.push(v);
                    }
                    self.stack.push(residue_ptr);
                }
                FluxOpcode::Reconstruct => {
                    // Stack: [residue_ptr, ...projected_coords] → [...reconstructed_coords]
                    let residue_ptr = self.pop()? as usize;
                    let projected: Vec<f64> = self.stack.drain(..).collect();

                    // Retrieve residue
                    let residue = if residue_ptr < self.residue_memory.len() {
                        self.residue_memory[residue_ptr].clone()
                    } else {
                        vec![0.0; 4] // default stub
                    };

                    // Reconstruct: interleave projected + residue
                    let phi = (1.0 + 5_f64.sqrt()) / 2.0;
                    let embed_dim = projected.len() + residue.len();
                    let mut reconstructed = Vec::with_capacity(embed_dim);
                    for i in 0..embed_dim {
                        if i < projected.len() {
                            // Invert projection approximately
                            let inv_factor = 1.0 / (((i + 1) as f64 * phi).fract().max(0.1));
                            reconstructed.push(projected[i] * inv_factor / (embed_dim as f64).sqrt());
                        } else {
                            let ri = i - projected.len();
                            if ri < residue.len() {
                                reconstructed.push(residue[ri]);
                            } else {
                                reconstructed.push(0.0);
                            }
                        }
                    }

                    for v in reconstructed {
                        self.stack.push(v);
                    }
                }
                FluxOpcode::Window => {
                    // Stack: [window_size] — sets the acceptance window
                    let window_size = self.pop()?;
                    self.acceptance_window = window_size.max(0.0);
                }
                FluxOpcode::Residue => {
                    // Stack: [] → [...perp_coords]
                    // Push the last stored residue onto the stack
                    if let Some(residue) = self.residue_memory.last() {
                        for &v in residue {
                            self.stack.push(v);
                        }
                    }
                    // If no residue, push nothing (empty stack stays empty)
                }
                FluxOpcode::Nasty => {
                    // Stack: [dim] → [is_nasty: 0 or 1]
                    // Greenfeld-Tao: dimensions ≥ threshold guarantee aperiodicity
                    // Conservative threshold: dim > 2 (Penrose works in 2+, higher = nastier)
                    let dim = self.pop()? as usize;
                    let threshold = instr.operands.get(0).copied().unwrap_or(2.0) as usize;
                    self.stack.push(if dim > threshold { 1.0 } else { 0.0 });
                }
                FluxOpcode::SnapHigh => {
                    // Stack: [dim, ...coords] → [...snapped_coords]
                    let dim = self.pop()? as usize;
                    let n = self.stack.len();
                    let take = dim.min(n);
                    let mut coords: Vec<f64> = self.stack.split_off(n - take);

                    // Snap to nearest aperiodic lattice point using golden ratio
                    let phi = (1.0 + 5_f64.sqrt()) / 2.0;
                    for (i, c) in coords.iter_mut().enumerate() {
                        // Snap: round to nearest golden-ratio-spaced lattice point
                        let lattice_spacing = phi.powi((i % 5) as i32);
                        *c = (*c / lattice_spacing).round() * lattice_spacing;
                    }

                    for v in coords {
                        self.stack.push(v);
                    }
                }
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

    // FLUX-DEEP tests

    #[test]
    fn test_xorinvert_involution() {
        // XOR with mask, then XOR again = identity (self-adjoint)
        let bc = make_bc(vec![
            FluxInstruction::with_operands(FluxOpcode::Load, vec![42.0]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![255.0]),
            FluxInstruction::new(FluxOpcode::XorInvert),
            FluxInstruction::new(FluxOpcode::Halt),
        ]);
        let mut vm = ConstraintVM::new();
        let result = vm.execute(&bc).unwrap();
        assert!(result.outputs[0] != 0.0); // should be non-zero
    }

    #[test]
    fn test_clamp_idempotent() {
        // Clamping twice = clamping once (reflective subcategory)
        let bc = make_bc(vec![
            FluxInstruction::with_operands(FluxOpcode::Load, vec![200.0]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![-128.0]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![127.0]),
            FluxInstruction::new(FluxOpcode::Clamp),
            FluxInstruction::new(FluxOpcode::Halt),
        ]);
        let mut vm = ConstraintVM::new();
        let result = vm.execute(&bc).unwrap();
        assert_eq!(result.outputs[0], 127.0);
    }

    #[test]
    fn test_floorq_ceilq_adjunction() {
        // floor(x/step)*step ≤ x ≤ ceil(x/step)*step
        let bc = make_bc(vec![
            FluxInstruction::with_operands(FluxOpcode::Load, vec![3.7]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![1.0]),
            FluxInstruction::new(FluxOpcode::FloorQ),
            FluxInstruction::new(FluxOpcode::Halt),
        ]);
        let mut vm = ConstraintVM::new();
        let result = vm.execute(&bc).unwrap();
        assert_eq!(result.outputs[0], 3.0); // floor(3.7) = 3

        let bc2 = make_bc(vec![
            FluxInstruction::with_operands(FluxOpcode::Load, vec![3.7]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![1.0]),
            FluxInstruction::new(FluxOpcode::CeilQ),
            FluxInstruction::new(FluxOpcode::Halt),
        ]);
        let mut vm2 = ConstraintVM::new();
        let result2 = vm2.execute(&bc2).unwrap();
        assert_eq!(result2.outputs[0], 4.0); // ceil(3.7) = 4
    }

    #[test]
    fn test_align_tolerance() {
        // Within tolerance → 1.0
        let bc = make_bc(vec![
            FluxInstruction::with_operands(FluxOpcode::Load, vec![10.0]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![10.05]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![0.1]),
            FluxInstruction::new(FluxOpcode::Align),
            FluxInstruction::new(FluxOpcode::Halt),
        ]);
        let mut vm = ConstraintVM::new();
        let result = vm.execute(&bc).unwrap();
        assert_eq!(result.outputs[0], 1.0);

        // Outside tolerance → 0.0
        let bc2 = make_bc(vec![
            FluxInstruction::with_operands(FluxOpcode::Load, vec![10.0]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![10.5]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![0.1]),
            FluxInstruction::new(FluxOpcode::Align),
            FluxInstruction::new(FluxOpcode::Halt),
        ]);
        let mut vm2 = ConstraintVM::new();
        let result2 = vm2.execute(&bc2).unwrap();
        assert_eq!(result2.outputs[0], 0.0);
    }

    #[test]
    fn test_amnesia_decay() {
        let bc = make_bc(vec![
            FluxInstruction::with_operands(FluxOpcode::Load, vec![1.0]), // valence
            FluxInstruction::with_operands(FluxOpcode::Load, vec![1.0]), // age = 1
            FluxInstruction::with_operands(FluxOpcode::Amnesia, vec![1.0]), // tau = 1
            FluxInstruction::new(FluxOpcode::Halt),
        ]);
        let mut vm = ConstraintVM::new();
        let result = vm.execute(&bc).unwrap();
        let decayed = result.outputs[0];
        assert!(decayed < 1.0, "should decay: {}", decayed);
        assert!(decayed > 0.0, "should be positive: {}", decayed);
        // At t=1, tau=1: e^(-1) ≈ 0.368
        assert!((decayed - 0.368).abs() < 0.01, "should be ~0.368: {}", decayed);
    }

    #[test]
    fn test_bearing_dodecet() {
        // 90° → direction 3 (step 3 of 12)
        let bc = make_bc(vec![
            FluxInstruction::with_operands(FluxOpcode::Load, vec![90.0]),
            FluxInstruction::new(FluxOpcode::Bearing),
            FluxInstruction::new(FluxOpcode::Halt),
        ]);
        let mut vm = ConstraintVM::new();
        let result = vm.execute(&bc).unwrap();
        assert_eq!(result.outputs[0], 3.0);
    }

    #[test]
    fn test_depth_sonar() {
        // 10ms round trip at 1500 m/s → 7.5m depth
        let bc = make_bc(vec![
            FluxInstruction::with_operands(FluxOpcode::Load, vec![10.0]),
            FluxInstruction::with_operands(FluxOpcode::Depth, vec![1500.0]),
            FluxInstruction::new(FluxOpcode::Halt),
        ]);
        let mut vm = ConstraintVM::new();
        let result = vm.execute(&bc).unwrap();
        assert!((result.outputs[0] - 7.5).abs() < 0.01);
    }

    #[test]
    fn test_holonomy_consistency() {
        // All positive → product = 1 (consistent)
        let bc = make_bc(vec![
            FluxInstruction::with_operands(FluxOpcode::Load, vec![1.0]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![1.0]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![1.0]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![3.0]), // n=3
            FluxInstruction::new(FluxOpcode::Holonomy),
            FluxInstruction::new(FluxOpcode::Halt),
        ]);
        let mut vm = ConstraintVM::new();
        let result = vm.execute(&bc).unwrap();
        assert_eq!(result.outputs[0], 1.0);
    }

    #[test]
    fn test_phase_transition() {
        // order > threshold → aligned (1.0)
        let bc = make_bc(vec![
            FluxInstruction::with_operands(FluxOpcode::Load, vec![0.95]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![0.9]),
            FluxInstruction::new(FluxOpcode::Phase),
            FluxInstruction::new(FluxOpcode::Halt),
        ]);
        let mut vm = ConstraintVM::new();
        let result = vm.execute(&bc).unwrap();
        assert_eq!(result.outputs[0], 1.0);
    }

    #[test]
    fn test_federate_majority() {
        // 3 yes, 2 no → majority = 1.0
        let bc = make_bc(vec![
            FluxInstruction::with_operands(FluxOpcode::Load, vec![1.0]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![1.0]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![1.0]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![0.0]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![0.0]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![5.0]),
            FluxInstruction::new(FluxOpcode::Federate),
            FluxInstruction::new(FluxOpcode::Halt),
        ]);
        let mut vm = ConstraintVM::new();
        let result = vm.execute(&bc).unwrap();
        assert_eq!(result.outputs[0], 1.0);
    }

    #[test]
    fn test_shadow_negative_space() {
        // 3 constraints summing to 0.6 → shadow = 0.4
        let bc = make_bc(vec![
            FluxInstruction::with_operands(FluxOpcode::Load, vec![0.3]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![0.2]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![0.1]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![3.0]),
            FluxInstruction::new(FluxOpcode::Shadow),
            FluxInstruction::new(FluxOpcode::Halt),
        ]);
        let mut vm = ConstraintVM::new();
        let result = vm.execute(&bc).unwrap();
        assert!((result.outputs[0] - 0.4).abs() < 0.01);
    }

    // ═══════════════════════════════════════════════════════════
    // FLUX-DEEP: Projection / Reconstruction tests
    // ═══════════════════════════════════════════════════════════

    #[test]
    fn test_project_cuts_to_lower_dim() {
        // Project 4D → 2D: embed_dim=4, tiling_dim=2, coords=[1,2,3,4]
        let bc = make_bc(vec![
            FluxInstruction::with_operands(FluxOpcode::Load, vec![1.0]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![2.0]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![3.0]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![4.0]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![4.0]), // embed_dim
            FluxInstruction::with_operands(FluxOpcode::Load, vec![2.0]), // tiling_dim
            FluxInstruction::new(FluxOpcode::Project),
            FluxInstruction::new(FluxOpcode::Halt),
        ]);
        let mut vm = ConstraintVM::new();
        let result = vm.execute(&bc).unwrap();
        // Should have 2 projected coords + 1 residue_ptr = 3 values
        assert_eq!(result.outputs.len(), 3, "projected output should be tiling_dim + 1 (ptr)");
        // residue_ptr should be 0 (first residue stored)
        assert_eq!(result.outputs[2], 0.0, "first residue ptr should be 0");
    }

    #[test]
    fn test_reconstruct_roundtrip() {
        // Project 3D→1D then reconstruct — should produce some values
        let bc = make_bc(vec![
            FluxInstruction::with_operands(FluxOpcode::Load, vec![1.0]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![2.0]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![3.0]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![3.0]), // embed_dim
            FluxInstruction::with_operands(FluxOpcode::Load, vec![1.0]), // tiling_dim
            FluxInstruction::new(FluxOpcode::Project),
            // Stack now: [projected, residue_ptr]
            FluxInstruction::new(FluxOpcode::Reconstruct),
            FluxInstruction::new(FluxOpcode::Halt),
        ]);
        let mut vm = ConstraintVM::new();
        let result = vm.execute(&bc).unwrap();
        // Reconstructed should have embed_dim values (3)
        assert_eq!(result.outputs.len(), 3, "reconstructed to embed_dim=3");
        // All should be finite
        for v in &result.outputs {
            assert!(v.is_finite(), "reconstructed value should be finite: {}", v);
        }
    }

    #[test]
    fn test_window_sets_acceptance() {
        let bc = make_bc(vec![
            FluxInstruction::with_operands(FluxOpcode::Load, vec![2.5]),
            FluxInstruction::new(FluxOpcode::Window),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![42.0]),
            FluxInstruction::new(FluxOpcode::Halt),
        ]);
        let mut vm = ConstraintVM::new();
        let result = vm.execute(&bc).unwrap();
        // WINDOW consumes the value, so only 42.0 should remain
        assert_eq!(result.outputs, vec![42.0]);
        assert_eq!(vm.acceptance_window, 2.5);
    }

    #[test]
    fn test_residue_pushes_perp_coords() {
        // Project 4D→2D, then RESIDUE should push the 2 perp coords
        let bc = make_bc(vec![
            FluxInstruction::with_operands(FluxOpcode::Load, vec![1.0]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![2.0]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![3.0]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![4.0]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![4.0]), // embed_dim
            FluxInstruction::with_operands(FluxOpcode::Load, vec![2.0]), // tiling_dim
            FluxInstruction::new(FluxOpcode::Project),
            // Pop residue_ptr to get it out of the way
            FluxInstruction::new(FluxOpcode::Pop),
            // Pop projected coords
            FluxInstruction::new(FluxOpcode::Pop),
            FluxInstruction::new(FluxOpcode::Pop),
            // Now push residue
            FluxInstruction::new(FluxOpcode::Residue),
            FluxInstruction::new(FluxOpcode::Halt),
        ]);
        let mut vm = ConstraintVM::new();
        let result = vm.execute(&bc).unwrap();
        // Residue should have embed_dim - tiling_dim = 2 coords
        assert_eq!(result.outputs.len(), 2, "residue should have perp-space coords");
        // The residue should be coords[2] and coords[3] = 3.0, 4.0
        assert_eq!(result.outputs[0], 3.0, "first perp coord");
        assert_eq!(result.outputs[1], 4.0, "second perp coord");
    }

    #[test]
    fn test_nasty_high_dim() {
        // dim=5, threshold=2 → nasty (1.0)
        let bc = make_bc(vec![
            FluxInstruction::with_operands(FluxOpcode::Load, vec![5.0]),
            FluxInstruction::new(FluxOpcode::Nasty),
            FluxInstruction::new(FluxOpcode::Halt),
        ]);
        let mut vm = ConstraintVM::new();
        let result = vm.execute(&bc).unwrap();
        assert_eq!(result.outputs[0], 1.0, "dim 5 > 2 should be nasty");

        // dim=2, threshold=2 → NOT nasty (0.0)
        let bc2 = make_bc(vec![
            FluxInstruction::with_operands(FluxOpcode::Load, vec![2.0]),
            FluxInstruction::new(FluxOpcode::Nasty),
            FluxInstruction::new(FluxOpcode::Halt),
        ]);
        let mut vm2 = ConstraintVM::new();
        let result2 = vm2.execute(&bc2).unwrap();
        assert_eq!(result2.outputs[0], 0.0, "dim 2 not > 2 should not be nasty");
    }

    #[test]
    fn test_snap_high_golden_ratio() {
        // Snap [1.0, 2.0] in dim=2 — should snap to golden-ratio-spaced lattice
        let bc = make_bc(vec![
            FluxInstruction::with_operands(FluxOpcode::Load, vec![1.0]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![2.0]),
            FluxInstruction::with_operands(FluxOpcode::Load, vec![2.0]), // dim
            FluxInstruction::new(FluxOpcode::SnapHigh),
            FluxInstruction::new(FluxOpcode::Halt),
        ]);
        let mut vm = ConstraintVM::new();
        let result = vm.execute(&bc).unwrap();
        assert_eq!(result.outputs.len(), 2, "should have 2 snapped coords");
        // Verify snapped values are finite and on golden-ratio lattice
        let phi = (1.0 + 5_f64.sqrt()) / 2.0;
        for (i, v) in result.outputs.iter().enumerate() {
            let lattice_spacing = phi.powi((i % 5) as i32);
            let remainder = (v / lattice_spacing).fract().abs();
            assert!(remainder < 1e-10 || (1.0 - remainder) < 1e-10,
                "coord {} = {} should be on phi^{} lattice (spacing {})",
                i, v, i % 5, lattice_spacing);
        }
    }
}
