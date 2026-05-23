//! Stack-based FLUX VM — no heap, no std, runs in 256 bytes of stack.

use crate::instruction::FluxInstruction;
use crate::opcode::FluxOpcode;

/// Maximum stack depth — 32 × 8 bytes = 256 bytes SRAM.
const STACK_SIZE: usize = 32;
/// Maximum outputs captured from the stack.
const MAX_OUTPUTS: usize = 8;

/// VM execution result.
#[derive(Debug)]
pub struct FluxResult {
    /// Values remaining on stack after execution.
    pub outputs: [f64; MAX_OUTPUTS],
    /// How many output slots are populated.
    pub output_count: usize,
    /// Did all ASSERT/CHECK/VALIDATE pass?
    pub constraints_satisfied: bool,
    /// Total instructions executed (including NOP).
    pub steps_executed: usize,
}

/// VM execution error.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FluxError {
    StackOverflow,
    StackUnderflow,
    DivisionByZero,
    ConstraintViolation,
    InvalidInstruction(u8),
}

/// The FLUX virtual machine.
pub struct FluxVm {
    stack: [f64; STACK_SIZE],
    sp: usize,  // stack pointer (next free slot)
}

impl FluxVm {
    /// Create a new VM with an empty stack.
    #[inline(always)]
    pub const fn new() -> Self {
        Self {
            stack: [0.0; STACK_SIZE],
            sp: 0,
        }
    }

    /// Reset VM state for reuse without reallocation.
    #[inline(always)]
    pub fn reset(&mut self) {
        self.sp = 0;
        self.stack = [0.0; STACK_SIZE];
    }

    #[inline(always)]
    fn push(&mut self, val: f64) -> Result<(), FluxError> {
        if self.sp >= STACK_SIZE {
            return Err(FluxError::StackOverflow);
        }
        self.stack[self.sp] = val;
        self.sp += 1;
        Ok(())
    }

    #[inline(always)]
    fn pop(&mut self) -> Result<f64, FluxError> {
        if self.sp == 0 {
            return Err(FluxError::StackUnderflow);
        }
        self.sp -= 1;
        Ok(self.stack[self.sp])
    }

    #[inline(always)]
    fn peek(&self, offset: usize) -> Result<f64, FluxError> {
        if offset >= self.sp {
            return Err(FluxError::StackUnderflow);
        }
        Ok(self.stack[self.sp - 1 - offset])
    }

    /// Execute a slice of instructions. Returns result or first error.
    pub fn execute(&mut self, instructions: &[FluxInstruction]) -> Result<FluxResult, FluxError> {
        let mut steps = 0usize;
        let mut constraints_ok = true;

        for instr in instructions {
            steps += 1;
            match instr.opcode {
                // -- Arithmetic --
                FluxOpcode::Add => {
                    let b = self.pop()?;
                    let a = self.pop()?;
                    self.push(a + b)?;
                }
                FluxOpcode::Sub => {
                    let b = self.pop()?;
                    let a = self.pop()?;
                    self.push(a - b)?;
                }
                FluxOpcode::Mul => {
                    let b = self.pop()?;
                    let a = self.pop()?;
                    self.push(a * b)?;
                }
                FluxOpcode::Div => {
                    let b = self.pop()?;
                    if b == 0.0 { return Err(FluxError::DivisionByZero); }
                    let a = self.pop()?;
                    self.push(a / b)?;
                }
                FluxOpcode::Mod => {
                    let b = self.pop()?;
                    if b == 0.0 { return Err(FluxError::DivisionByZero); }
                    let a = self.pop()?;
                    self.push(a % b)?;
                }

                // -- Comparison (push 1.0 true / 0.0 false) --
                FluxOpcode::Eq => {
                    let b = self.pop()?;
                    let a = self.pop()?;
                    self.push(if a == b { 1.0 } else { 0.0 })?;
                }
                FluxOpcode::Lt => {
                    let b = self.pop()?;
                    let a = self.pop()?;
                    self.push(if a < b { 1.0 } else { 0.0 })?;
                }
                FluxOpcode::Gt => {
                    let b = self.pop()?;
                    let a = self.pop()?;
                    self.push(if a > b { 1.0 } else { 0.0 })?;
                }
                FluxOpcode::Lte => {
                    let b = self.pop()?;
                    let a = self.pop()?;
                    self.push(if a <= b { 1.0 } else { 0.0 })?;
                }
                FluxOpcode::Gte => {
                    let b = self.pop()?;
                    let a = self.pop()?;
                    self.push(if a >= b { 1.0 } else { 0.0 })?;
                }

                // -- Constraints --
                FluxOpcode::Assert => {
                    let val = self.pop()?;
                    if val == 0.0 {
                        constraints_ok = false;
                        return Err(FluxError::ConstraintViolation);
                    }
                }
                FluxOpcode::Check => {
                    let val = self.peek(0)?;
                    if val == 0.0 { constraints_ok = false; }
                    // Don't pop — CHECK is non-consuming
                }
                FluxOpcode::Validate => {
                    let upper = self.pop()?;
                    let lower = self.pop()?;
                    let val = self.pop()?;
                    let ok = val >= lower && val <= upper;
                    self.push(if ok { 1.0 } else { 0.0 })?;
                    if !ok { constraints_ok = false; }
                }
                FluxOpcode::Reject => {
                    constraints_ok = false;
                    // Don't halt — let program continue to capture rejection reason
                }

                // -- Stack --
                FluxOpcode::Load => {
                    // LOAD operand0 — push literal
                    self.push(instr.operands[0])?;
                }
                FluxOpcode::Push => {
                    self.push(instr.operands[0])?;
                }
                FluxOpcode::Pop => {
                    self.pop()?;
                }

                // -- Transform --
                FluxOpcode::Snap => {
                    // Round to nearest (quantize snap)
                    let val = self.pop()?;
                    self.push(libm::round(val))?;
                }
                FluxOpcode::Quantize => {
                    // Quantize val to step size: round(val / step) * step
                    let step = self.pop()?;
                    let val = self.pop()?;
                    if step == 0.0 { return Err(FluxError::DivisionByZero); }
                    self.push(libm::round(val / step) * step)?;
                }

                // -- Control --
                FluxOpcode::Halt => break,
                FluxOpcode::Nop => { /* no-op */ }
            }
        }

        // Collect outputs
        let count = if self.sp < MAX_OUTPUTS { self.sp } else { MAX_OUTPUTS };
        let mut outputs = [0.0f64; MAX_OUTPUTS];
        let base = self.sp.saturating_sub(count);
        for i in 0..count {
            outputs[i] = self.stack[base + i];
        }

        Ok(FluxResult {
            outputs,
            output_count: count,
            constraints_satisfied: constraints_ok,
            steps_executed: steps,
        })
    }
}
