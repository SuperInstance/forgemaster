use std::time::{Duration, Instant};
use serde::{Deserialize, Serialize};
use crate::bytecode::{Bytecode, ExecutionResult};
use crate::instruction::Instruction;
use crate::opcode::OpCode;

/// Execution limits to prevent runaway programs.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionLimits {
    pub max_steps: u64,
    pub max_time: Duration,
    pub max_stack_depth: usize,
}

impl Default for ExecutionLimits {
    fn default() -> Self {
        ExecutionLimits {
            max_steps: 1_000_000,
            max_time: Duration::from_secs(30),
            max_stack_depth: 1024,
        }
    }
}

/// Live execution metrics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VmMetrics {
    pub steps_executed: u64,
    pub constraint_checks: u64,
    pub violations: u64,
    pub stack_depth: usize,
    pub memory_slots_used: usize,
    pub elapsed_ms: f64,
    pub instructions_per_sec: f64,
}

/// Reason the VM halted.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum HaltReason {
    Normal,
    MaxStepsExceeded,
    Timeout,
    StackOverflow,
    StackUnderflow,
    DivisionByZero,
    ConstraintViolation(String),
    InvalidInstruction(String),
}

/// The async-aware FLUX virtual machine.
pub struct Vm {
    stack: Vec<f64>,
    memory: Vec<f64>,
    call_stack: Vec<usize>,
    limits: ExecutionLimits,
    steps: u64,
    constraint_checks: u64,
    violations: u64,
    start: Instant,
    /// Yield to the tokio runtime every N instructions for cooperative scheduling.
    pub yield_every: u64,
}

impl Vm {
    pub fn new(limits: ExecutionLimits) -> Self {
        Vm {
            stack: Vec::with_capacity(256),
            memory: vec![0.0; 256],
            call_stack: Vec::new(),
            limits,
            steps: 0,
            constraint_checks: 0,
            violations: 0,
            start: Instant::now(),
            yield_every: 1024,
        }
    }

    pub fn with_defaults() -> Self {
        Vm::new(ExecutionLimits::default())
    }

    /// Current metrics snapshot.
    pub fn metrics(&self) -> VmMetrics {
        let elapsed = self.start.elapsed().as_secs_f64();
        let elapsed_ms = elapsed * 1000.0;
        VmMetrics {
            steps_executed: self.steps,
            constraint_checks: self.constraint_checks,
            violations: self.violations,
            stack_depth: self.stack.len(),
            memory_slots_used: self.memory.iter().filter(|v| **v != 0.0).count(),
            elapsed_ms,
            instructions_per_sec: if elapsed > 0.0 { self.steps as f64 / elapsed } else { 0.0 },
        }
    }

    /// Reset VM state for a new execution.
    pub fn reset(&mut self) {
        self.stack.clear();
        self.memory.iter_mut().for_each(|m| *m = 0.0);
        self.call_stack.clear();
        self.steps = 0;
        self.constraint_checks = 0;
        self.violations = 0;
        self.start = Instant::now();
    }

    /// Execute a bytecode program asynchronously, yielding to the runtime periodically.
    pub async fn execute(&mut self, bytecode: &Bytecode) -> ExecutionResult {
        self.reset();
        let id = bytecode.id;
        let deadline = self.start + self.limits.max_time;

        let mut pc: usize = 0;
        let halt_reason = loop {
            if pc >= bytecode.instructions.len() {
                break HaltReason::Normal;
            }
            if self.steps >= self.limits.max_steps {
                break HaltReason::MaxStepsExceeded;
            }
            if Instant::now() > deadline {
                break HaltReason::Timeout;
            }

            // Cooperative yield every N steps.
            if self.steps > 0 && self.steps % self.yield_every == 0 {
                tokio::task::yield_now().await;
            }

            let instr = &bytecode.instructions[pc];
            match self.exec_instruction(instr, &mut pc, bytecode.instructions.len()) {
                Ok(should_continue) => {
                    if !should_continue {
                        break HaltReason::Normal;
                    }
                }
                Err(reason) => break reason,
            }
            self.steps += 1;
        };

        let elapsed_ms = self.start.elapsed().as_secs_f64() * 1000.0;
        let ips = if elapsed_ms > 0.0 {
            self.steps as f64 / (elapsed_ms / 1000.0)
        } else {
            0.0
        };

        let success = matches!(halt_reason, HaltReason::Normal);
        ExecutionResult {
            bytecode_id: id,
            success,
            final_stack: self.stack.clone(),
            steps_executed: self.steps,
            constraint_checks: self.constraint_checks,
            violations: self.violations,
            elapsed_ms,
            instructions_per_sec: ips,
            error: if success { None } else { Some(format!("{:?}", halt_reason)) },
        }
    }

    /// Execute a single instruction. Returns Ok(true) to continue, Ok(false) for halt.
    fn exec_instruction(
        &mut self,
        instr: &Instruction,
        pc: &mut usize,
        len: usize,
    ) -> Result<bool, HaltReason> {
        match instr.opcode {
            // ── Stack ────────────────────────────
            OpCode::Push => {
                let v = instr.operand.unwrap_or(0.0);
                if self.stack.len() >= self.limits.max_stack_depth {
                    return Err(HaltReason::StackOverflow);
                }
                self.stack.push(v);
            }
            OpCode::Pop => {
                if self.stack.pop().is_none() {
                    return Err(HaltReason::StackUnderflow);
                }
            }
            OpCode::Dup => {
                if self.stack.is_empty() {
                    return Err(HaltReason::StackUnderflow);
                }
                let v = *self.stack.last().unwrap();
                if self.stack.len() >= self.limits.max_stack_depth {
                    return Err(HaltReason::StackOverflow);
                }
                self.stack.push(v);
            }
            OpCode::Swap => {
                let n = self.stack.len();
                if n < 2 {
                    return Err(HaltReason::StackUnderflow);
                }
                self.stack.swap(n - 1, n - 2);
            }
            OpCode::Load => {
                let idx = instr.operand.unwrap_or(0.0) as usize;
                if idx >= self.memory.len() {
                    return Err(HaltReason::InvalidInstruction(format!("LOAD: index {} out of range", idx)));
                }
                self.stack.push(self.memory[idx]);
            }
            OpCode::Store => {
                let idx = self.stack.pop().ok_or(HaltReason::StackUnderflow)? as usize;
                let v = self.stack.pop().ok_or(HaltReason::StackUnderflow)?;
                if idx < self.memory.len() {
                    self.memory[idx] = v;
                }
            }

            // ── Arithmetic ──────────────────────
            OpCode::Add => self.binary_op(|a, b| a + b)?,
            OpCode::Sub => self.binary_op(|a, b| a - b)?,
            OpCode::Mul => self.binary_op(|a, b| a * b)?,
            OpCode::Div => {
                let b = self.stack.pop().ok_or(HaltReason::StackUnderflow)?;
                let a = self.stack.pop().ok_or(HaltReason::StackUnderflow)?;
                if b == 0.0 {
                    return Err(HaltReason::DivisionByZero);
                }
                self.stack.push(a / b);
            }
            OpCode::Mod => self.binary_op(|a, b| a % b)?,
            OpCode::Neg => {
                let v = self.stack.pop().ok_or(HaltReason::StackUnderflow)?;
                self.stack.push(-v);
            }

            // ── Comparison ──────────────────────
            OpCode::Eq  => self.binary_op(|a, b| if a == b { 1.0 } else { 0.0 })?,
            OpCode::Ne  => self.binary_op(|a, b| if a != b { 1.0 } else { 0.0 })?,
            OpCode::Lt  => self.binary_op(|a, b| if a < b  { 1.0 } else { 0.0 })?,
            OpCode::Le  => self.binary_op(|a, b| if a <= b { 1.0 } else { 0.0 })?,
            OpCode::Gt  => self.binary_op(|a, b| if a > b  { 1.0 } else { 0.0 })?,
            OpCode::Ge  => self.binary_op(|a, b| if a >= b { 1.0 } else { 0.0 })?,

            // ── Logic ───────────────────────────
            OpCode::And => self.binary_op(|a, b| if a != 0.0 && b != 0.0 { 1.0 } else { 0.0 })?,
            OpCode::Or  => self.binary_op(|a, b| if a != 0.0 || b != 0.0 { 1.0 } else { 0.0 })?,
            OpCode::Not => {
                let v = self.stack.pop().ok_or(HaltReason::StackUnderflow)?;
                self.stack.push(if v == 0.0 { 1.0 } else { 0.0 });
            }

            // ── Constraint ──────────────────────
            OpCode::Validate => {
                self.constraint_checks += 1;
                // Stack: [value, min, max] → push 1 if valid, 0 if not
                let max  = self.stack.pop().ok_or(HaltReason::StackUnderflow)?;
                let min  = self.stack.pop().ok_or(HaltReason::StackUnderflow)?;
                let val  = self.stack.pop().ok_or(HaltReason::StackUnderflow)?;
                let valid = val >= min && val <= max;
                if !valid { self.violations += 1; }
                self.stack.push(if valid { 1.0 } else { 0.0 });
            }
            OpCode::Assert => {
                self.constraint_checks += 1;
                let cond = self.stack.pop().ok_or(HaltReason::StackUnderflow)?;
                if cond == 0.0 {
                    self.violations += 1;
                    return Err(HaltReason::ConstraintViolation("assertion failed".into()));
                }
            }
            OpCode::Tolerance => {
                self.constraint_checks += 1;
                // Stack: [value, expected, tolerance] → push 1 if within tol
                let tol   = self.stack.pop().ok_or(HaltReason::StackUnderflow)?;
                let exp   = self.stack.pop().ok_or(HaltReason::StackUnderflow)?;
                let val   = self.stack.pop().ok_or(HaltReason::StackUnderflow)?;
                let ok = (val - exp).abs() <= tol;
                if !ok { self.violations += 1; }
                self.stack.push(if ok { 1.0 } else { 0.0 });
            }
            OpCode::Clamp => {
                // Stack: [value, min, max] → push clamped value
                let max = self.stack.pop().ok_or(HaltReason::StackUnderflow)?;
                let min = self.stack.pop().ok_or(HaltReason::StackUnderflow)?;
                let val = self.stack.pop().ok_or(HaltReason::StackUnderflow)?;
                self.stack.push(val.clamp(min, max));
            }

            // ── Control flow ────────────────────
            OpCode::Jump => {
                let target = instr.operand.unwrap_or(0.0) as usize;
                if target < len {
                    *pc = target;
                    return Ok(true);
                }
            }
            OpCode::JumpIf => {
                let cond = self.stack.pop().ok_or(HaltReason::StackUnderflow)?;
                if cond != 0.0 {
                    let target = instr.operand.unwrap_or(0.0) as usize;
                    if target < len {
                        *pc = target;
                        return Ok(true);
                    }
                }
            }
            OpCode::Call => {
                let target = instr.operand.unwrap_or(0.0) as usize;
                if target >= len {
                    return Err(HaltReason::InvalidInstruction(format!("CALL: target {} out of range", target)));
                }
                self.call_stack.push(*pc + 1);
                *pc = target;
                return Ok(true);
            }
            OpCode::Ret => {
                match self.call_stack.pop() {
                    Some(ret_pc) => { *pc = ret_pc; return Ok(true); }
                    None => return Ok(false), // top-level return = halt
                }
            }
            OpCode::Halt => return Ok(false),

            // ── I/O (no-op in edge VM — handled at pipeline level) ──
            OpCode::Input  => {
                // Push a placeholder zero; real input comes from sensor pipeline.
                self.stack.push(instr.operand.unwrap_or(0.0));
            }
            OpCode::Output => {
                // Pop and discard; output is captured via result stack.
                let _ = self.stack.pop();
            }

            // ── Extended ────────────────────────
            OpCode::Sync => {
                // No-op marker for sync points in the pipeline.
            }
            OpCode::Nop => {}
        }

        *pc += 1;
        Ok(true)
    }

    fn binary_op<F: Fn(f64, f64) -> f64>(&mut self, op: F) -> Result<(), HaltReason> {
        let b = self.stack.pop().ok_or(HaltReason::StackUnderflow)?;
        let a = self.stack.pop().ok_or(HaltReason::StackUnderflow)?;
        self.stack.push(op(a, b));
        Ok(())
    }

    /// Push values onto the stack (for injecting sensor data).
    pub fn push_inputs(&mut self, values: &[f64]) {
        for &v in values {
            self.stack.push(v);
        }
    }

    /// Drain the stack.
    pub fn drain_stack(&mut self) -> Vec<f64> {
        self.stack.drain(..).collect()
    }
}
