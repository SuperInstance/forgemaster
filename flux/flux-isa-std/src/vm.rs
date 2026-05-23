use serde::{Deserialize, Serialize};
use thiserror::Error;

use crate::bytecode::FluxBytecode;
use crate::instruction::FluxInstruction;
use crate::opcode::FluxOpCode;

#[derive(Debug, Error)]
pub enum VMError {
    #[error("Stack underflow: {operation} needs {needed} items, have {have}")]
    StackUnderflow {
        operation: String,
        needed: usize,
        have: usize,
    },
    #[error("Division by zero")]
    DivisionByZero,
    #[error("Assertion failed at instruction {ip}: {message}")]
    AssertionFailed { ip: usize, message: String },
    #[error("Constraint check failed at instruction {ip}: {message}")]
    ConstraintFailed { ip: usize, message: String },
    #[error("Invalid jump target: {target}")]
    InvalidJump { target: usize },
    #[error("Call stack overflow (depth > {max})")]
    CallStackOverflow { max: usize },
    #[error("Memory access out of bounds: index {index}, size {size}")]
    MemoryOutOfBounds { index: usize, size: usize },
    #[error("Bytecode error: {0}")]
    Bytecode(#[from] crate::bytecode::BytecodeError),
    #[error("Halted at instruction {0}")]
    Halted(usize),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VMConfig {
    pub max_stack_size: usize,
    pub max_call_depth: usize,
    pub memory_size: usize,
    pub trace_enabled: bool,
    pub max_instructions: usize,
}

impl Default for VMConfig {
    fn default() -> Self {
        Self {
            max_stack_size: 4096,
            max_call_depth: 256,
            memory_size: 65536,
            trace_enabled: false,
            max_instructions: 1_000_000,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionTrace {
    pub instruction_index: usize,
    pub opcode: String,
    pub stack_before: Vec<f64>,
    pub stack_after: Vec<f64>,
}

pub struct FluxVM {
    stack: Vec<f64>,
    call_stack: Vec<usize>,
    memory: Vec<f64>,
    ip: usize,
    config: VMConfig,
    instructions: Vec<FluxInstruction>,
    trace: Vec<ExecutionTrace>,
    output: Vec<String>,
    halted: bool,
    instruction_count: usize,
}

impl FluxVM {
    pub fn new(config: VMConfig) -> Self {
        Self {
            stack: Vec::with_capacity(256),
            call_stack: Vec::new(),
            memory: vec![0.0; config.memory_size],
            ip: 0,
            config,
            instructions: Vec::new(),
            trace: Vec::new(),
            output: Vec::new(),
            halted: false,
            instruction_count: 0,
        }
    }

    pub fn with_default_config() -> Self {
        Self::new(VMConfig::default())
    }

    pub fn reset(&mut self) {
        self.stack.clear();
        self.call_stack.clear();
        self.memory.fill(0.0);
        self.ip = 0;
        self.trace.clear();
        self.output.clear();
        self.halted = false;
        self.instruction_count = 0;
    }

    pub fn stack(&self) -> &[f64] {
        &self.stack
    }

    pub fn output(&self) -> &[String] {
        &self.output
    }

    pub fn trace(&self) -> &[ExecutionTrace] {
        &self.trace
    }

    pub fn memory(&self) -> &[f64] {
        &self.memory
    }

    /// Load and execute bytecode
    pub fn execute_bytecode(&mut self, bytecode: &FluxBytecode) -> Result<(), VMError> {
        self.instructions = bytecode.instructions.clone();
        self.reset();
        self.run()
    }

    /// Load and execute instruction list
    pub fn execute_instructions(&mut self, instructions: Vec<FluxInstruction>) -> Result<(), VMError> {
        self.instructions = instructions;
        self.reset();
        self.run()
    }

    pub fn instructions(&self) -> &[FluxInstruction] {
        &self.instructions
    }

    /// Load instructions for step-by-step execution (call step() after)
    pub fn load_instructions(&mut self, instructions: Vec<FluxInstruction>) {
        self.instructions = instructions;
    }

    /// Execute a single step. Returns Ok(true) if more steps available.
    pub fn step(&mut self) -> Result<bool, VMError> {
        if self.halted || self.ip >= self.instructions.len() {
            return Ok(false);
        }
        self.exec_one()?;
        Ok(!self.halted && self.ip < self.instructions.len())
    }

    fn run(&mut self) -> Result<(), VMError> {
        while !self.halted && self.ip < self.instructions.len() {
            if self.instruction_count >= self.config.max_instructions {
                return Err(VMError::Halted(self.ip));
            }
            self.exec_one()?;
        }
        Ok(())
    }

    fn exec_one(&mut self) -> Result<(), VMError> {
        let instr = self.instructions[self.ip].clone();
        let stack_before = if self.config.trace_enabled {
            self.stack.clone()
        } else {
            Vec::new()
        };

        self.instruction_count += 1;

        match instr.opcode {
            FluxOpCode::Push => {
                let v = instr.operands.first().copied().unwrap_or(0.0);
                self.push(v)?;
            }
            FluxOpCode::Pop => {
                self.pop("POP")?;
            }
            FluxOpCode::Dup => {
                let v = self.peek(0, "DUP")?;
                self.push(v)?;
            }
            FluxOpCode::Swap => {
                let len = self.stack.len();
                if len < 2 {
                    return Err(VMError::StackUnderflow {
                        operation: "SWAP".into(),
                        needed: 2,
                        have: len,
                    });
                }
                self.stack.swap(len - 1, len - 2);
            }
            FluxOpCode::Over => {
                let v = self.peek(1, "OVER")?;
                self.push(v)?;
            }
            FluxOpCode::Rot => {
                let len = self.stack.len();
                if len < 3 {
                    return Err(VMError::StackUnderflow {
                        operation: "ROT".into(),
                        needed: 3,
                        have: len,
                    });
                }
                let c = self.stack[len - 3];
                self.stack[len - 3] = self.stack[len - 2];
                self.stack[len - 2] = self.stack[len - 1];
                self.stack[len - 1] = c;
            }
            FluxOpCode::Depth => {
                self.push(self.stack.len() as f64)?;
            }
            FluxOpCode::Add => {
                let b = self.pop("ADD")?;
                let a = self.pop("ADD")?;
                self.push(a + b)?;
            }
            FluxOpCode::Sub => {
                let b = self.pop("SUB")?;
                let a = self.pop("SUB")?;
                self.push(a - b)?;
            }
            FluxOpCode::Mul => {
                let b = self.pop("MUL")?;
                let a = self.pop("MUL")?;
                self.push(a * b)?;
            }
            FluxOpCode::Div => {
                let b = self.pop("DIV")?;
                if b == 0.0 {
                    return Err(VMError::DivisionByZero);
                }
                let a = self.pop("DIV")?;
                self.push(a / b)?;
            }
            FluxOpCode::Mod => {
                let b = self.pop("MOD")?;
                if b == 0.0 {
                    return Err(VMError::DivisionByZero);
                }
                let a = self.pop("MOD")?;
                self.push(a % b)?;
            }
            FluxOpCode::Negate => {
                let a = self.pop("NEGATE")?;
                self.push(-a)?;
            }
            FluxOpCode::Abs => {
                let a = self.pop("ABS")?;
                self.push(a.abs())?;
            }
            FluxOpCode::And => {
                let b = self.pop("AND")?;
                let a = self.pop("AND")?;
                self.push(if a != 0.0 && b != 0.0 { 1.0 } else { 0.0 })?;
            }
            FluxOpCode::Or => {
                let b = self.pop("OR")?;
                let a = self.pop("OR")?;
                self.push(if a != 0.0 || b != 0.0 { 1.0 } else { 0.0 })?;
            }
            FluxOpCode::Not => {
                let a = self.pop("NOT")?;
                self.push(if a == 0.0 { 1.0 } else { 0.0 })?;
            }
            FluxOpCode::Xor => {
                let b = self.pop("XOR")?;
                let a = self.pop("XOR")?;
                self.push(if (a != 0.0) ^ (b != 0.0) { 1.0 } else { 0.0 })?;
            }
            FluxOpCode::Shl => {
                let b = self.pop("SHL")?;
                let a = self.pop("SHL")?;
                self.push((a as u64).wrapping_shl(b as u32) as f64)?;
            }
            FluxOpCode::Eq => {
                let b = self.pop("EQ")?;
                let a = self.pop("EQ")?;
                self.push(if a == b { 1.0 } else { 0.0 })?;
            }
            FluxOpCode::Ne => {
                let b = self.pop("NE")?;
                let a = self.pop("NE")?;
                self.push(if a != b { 1.0 } else { 0.0 })?;
            }
            FluxOpCode::Lt => {
                let b = self.pop("LT")?;
                let a = self.pop("LT")?;
                self.push(if a < b { 1.0 } else { 0.0 })?;
            }
            FluxOpCode::Gt => {
                let b = self.pop("GT")?;
                let a = self.pop("GT")?;
                self.push(if a > b { 1.0 } else { 0.0 })?;
            }
            FluxOpCode::Le => {
                let b = self.pop("LE")?;
                let a = self.pop("LE")?;
                self.push(if a <= b { 1.0 } else { 0.0 })?;
            }
            FluxOpCode::Ge => {
                let b = self.pop("GE")?;
                let a = self.pop("GE")?;
                self.push(if a >= b { 1.0 } else { 0.0 })?;
            }
            FluxOpCode::Jmp => {
                let target = instr.operands.first().copied().unwrap_or(0.0) as usize;
                if target >= self.instructions.len() {
                    return Err(VMError::InvalidJump { target });
                }
                self.ip = target;
                return Ok(());
            }
            FluxOpCode::Call => {
                let target = instr.operands.first().copied().unwrap_or(0.0) as usize;
                if target >= self.instructions.len() {
                    return Err(VMError::InvalidJump { target });
                }
                if self.call_stack.len() >= self.config.max_call_depth {
                    return Err(VMError::CallStackOverflow {
                        max: self.config.max_call_depth,
                    });
                }
                self.call_stack.push(self.ip + 1);
                self.ip = target;
                return Ok(());
            }
            FluxOpCode::Ret => {
                if let Some(ret_ip) = self.call_stack.pop() {
                    self.ip = ret_ip;
                    return Ok(());
                }
                // No call stack — treat as halt
                self.halted = true;
                return Ok(());
            }
            FluxOpCode::Halt => {
                self.halted = true;
                return Ok(());
            }
            FluxOpCode::Nop => {}
            FluxOpCode::Load => {
                let addr = self.pop("LOAD")? as usize;
                if addr >= self.memory.len() {
                    return Err(VMError::MemoryOutOfBounds {
                        index: addr,
                        size: self.memory.len(),
                    });
                }
                self.push(self.memory[addr])?;
            }
            FluxOpCode::Store => {
                let addr = instr.operands.first().copied().unwrap_or(0.0) as usize;
                if addr >= self.memory.len() {
                    return Err(VMError::MemoryOutOfBounds {
                        index: addr,
                        size: self.memory.len(),
                    });
                }
                let val = self.pop("STORE")?;
                self.memory[addr] = val;
            }
            FluxOpCode::LoadConst => {
                let v = instr.operands.first().copied().unwrap_or(0.0);
                self.push(v)?;
            }
            FluxOpCode::Assert => {
                let cond = self.pop("ASSERT")?;
                if cond == 0.0 {
                    let msg = instr.operands.first().map(|_| "assertion value was zero")
                        .unwrap_or("assertion value was zero")
                        .to_string();
                    return Err(VMError::AssertionFailed { ip: self.ip, message: msg });
                }
            }
            FluxOpCode::Check => {
                let cond = self.pop("CHECK")?;
                if cond == 0.0 {
                    let msg = "constraint check failed".to_string();
                    return Err(VMError::ConstraintFailed { ip: self.ip, message: msg });
                }
            }
            FluxOpCode::Print => {
                let v = self.pop("PRINT")?;
                self.output.push(format!("{}", v));
            }
            FluxOpCode::Emit => {
                let v = self.pop("EMIT")?;
                self.output.push(format!("{}", v));
            }
        }

        if self.config.trace_enabled {
            self.trace.push(ExecutionTrace {
                instruction_index: self.ip,
                opcode: instr.opcode.to_string(),
                stack_before,
                stack_after: self.stack.clone(),
            });
        }

        self.ip += 1;
        Ok(())
    }

    fn push(&mut self, value: f64) -> Result<(), VMError> {
        if self.stack.len() >= self.config.max_stack_size {
            return Err(VMError::StackUnderflow {
                operation: "PUSH".into(),
                needed: 1,
                have: self.config.max_stack_size,
            });
        }
        self.stack.push(value);
        Ok(())
    }

    fn pop(&mut self, op: &str) -> Result<f64, VMError> {
        self.stack.pop().ok_or_else(|| VMError::StackUnderflow {
            operation: op.into(),
            needed: 1,
            have: 0,
        })
    }

    fn peek(&self, depth: usize, op: &str) -> Result<f64, VMError> {
        let len = self.stack.len();
        if len <= depth {
            Err(VMError::StackUnderflow {
                operation: op.into(),
                needed: depth + 1,
                have: len,
            })
        } else {
            Ok(self.stack[len - 1 - depth])
        }
    }
}
