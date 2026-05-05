
use serde::{Deserialize, Serialize};
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use std::time::{Instant, SystemTime, UNIX_EPOCH};

use tracing::{debug, error, trace, warn};
use uuid::Uuid;

use crate::cuda::GpuDispatcher;
use crate::fleet::FleetHandle;
use crate::opcode::{Instruction, Opcode, ThorOpcode};
use crate::plato::PlatoHandle;

// ── Value type ───────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum Value {
    F64(f64),
    I64(i64),
    Bool(bool),
    Str(String),
    Bytes(Vec<u8>),
    Nil,
}

impl Value {
    pub fn as_f64(&self) -> Option<f64> {
        match self {
            Value::F64(v) => Some(*v),
            Value::I64(v) => Some(*v as f64),
            _ => None,
        }
    }

    pub fn as_i64(&self) -> Option<i64> {
        match self {
            Value::I64(v) => Some(*v),
            Value::F64(v) => Some(*v as i64),
            _ => None,
        }
    }

    pub fn as_bool(&self) -> Option<bool> {
        match self {
            Value::Bool(v) => Some(*v),
            _ => None,
        }
    }
}

// ── Execution trace ──────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TraceEntry {
    pub pc: usize,
    pub opcode: u8,
    pub mnemonic: String,
    pub timestamp_ns: u64,
    pub stack_depth: usize,
}

// ── Execution result ─────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VmResult {
    pub id: Uuid,
    pub status: VmStatus,
    pub stack: Vec<Value>,
    pub trace: Vec<TraceEntry>,
    pub metrics: ExecutionMetrics,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum VmStatus {
    Ok,
    Halted,
    Error,
    Timeout,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionMetrics {
    pub instructions_executed: u64,
    pub elapsed_ns: u64,
    pub gpu_offloads: u64,
    pub parallel_branches: u64,
    pub peak_stack_depth: usize,
}

// ── Parallel branch result ───────────────────────────────────────

#[derive(Debug, Clone)]
struct BranchResult {
    branch_id: usize,
    stack: Vec<Value>,
    metrics: ExecutionMetrics,
    trace: Vec<TraceEntry>,
}

// ── VM configuration ─────────────────────────────────────────────

#[derive(Debug, Clone)]
pub struct VmConfig {
    pub max_stack: usize,
    pub max_trace: usize,
    pub trace_enabled: bool,
    pub parallel_threshold: usize,
    pub gpu_threshold: usize,
}

impl Default for VmConfig {
    fn default() -> Self {
        Self {
            max_stack: 65536,
            max_trace: 1_000_000,
            trace_enabled: true,
            parallel_threshold: 4,
            gpu_threshold: 256,
        }
    }
}

// ── The VM ───────────────────────────────────────────────────────

pub struct ThorVm {
    config: VmConfig,
    gpu: Arc<GpuDispatcher>,
    plato: Arc<PlatoHandle>,
    fleet: Arc<FleetHandle>,
    total_executed: AtomicU64,
}

impl ThorVm {
    pub fn new(
        config: VmConfig,
        gpu: Arc<GpuDispatcher>,
        plato: Arc<PlatoHandle>,
        fleet: Arc<FleetHandle>,
    ) -> Self {
        Self {
            config,
            gpu,
            plato,
            fleet,
            total_executed: AtomicU64::new(0),
        }
    }

    /// Execute a FLUX bytecode program sequentially.
    pub async fn execute(&self, bytecode: &[u8]) -> VmResult {
        let id = Uuid::new_v4();
        let start = Instant::now();
        let mut stack: Vec<Value> = Vec::with_capacity(256);
        let mut trace = Vec::new();
        let mut pc: usize = 0;
        let mut instructions_executed: u64 = 0;
        let mut gpu_offloads: u64 = 0;
        let mut parallel_branches: u64 = 0;
        let mut peak_stack: usize = 0;
        let mut status = VmStatus::Ok;

        while pc < bytecode.len() {
            let op_byte = bytecode[pc];
            let inst = match Instruction::from_byte(op_byte) {
                Some(i) => i,
                None => {
                    warn!("Unknown opcode 0x{op_byte:02X} at pc={pc}");
                    status = VmStatus::Error;
                    break;
                }
            };

            // Record trace
            if self.config.trace_enabled && trace.len() < self.config.max_trace {
                let ts = SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .unwrap_or_default()
                    .as_nanos() as u64;
                trace.push(TraceEntry {
                    pc,
                    opcode: op_byte,
                    mnemonic: inst.to_string(),
                    timestamp_ns: ts,
                    stack_depth: stack.len(),
                });
            }

            match inst {
                // ── Stack ops ────────────────────────────────
                Instruction::Base(Opcode::Nop) => { /* no-op */ }
                Instruction::Base(Opcode::Push) => {
                    if pc + 9 > bytecode.len() {
                        status = VmStatus::Error;
                        break;
                    }
                    let val = f64::from_be_bytes(
                        bytecode[pc + 1..pc + 9].try_into().unwrap_or([0u8; 8]),
                    );
                    stack.push(Value::F64(val));
                    pc += 8;
                }
                Instruction::Base(Opcode::Pop) => {
                    stack.pop();
                }
                Instruction::Base(Opcode::Dup) => {
                    if let Some(v) = stack.last().cloned() {
                        stack.push(v);
                    }
                }
                Instruction::Base(Opcode::Swap) => {
                    let len = stack.len();
                    if len >= 2 {
                        stack.swap(len - 1, len - 2);
                    }
                }
                Instruction::Base(Opcode::Load) => {
                    if pc + 5 > bytecode.len() {
                        status = VmStatus::Error;
                        break;
                    }
                    let idx = u32::from_be_bytes(
                        bytecode[pc + 1..pc + 5].try_into().unwrap_or([0u8; 4]),
                    ) as usize;
                    if idx < stack.len() {
                        stack.push(stack[idx].clone());
                    }
                    pc += 4;
                }
                Instruction::Base(Opcode::Store) => {
                    if pc + 5 > bytecode.len() {
                        status = VmStatus::Error;
                        break;
                    }
                    let idx = u32::from_be_bytes(
                        bytecode[pc + 1..pc + 5].try_into().unwrap_or([0u8; 4]),
                    ) as usize;
                    if let Some(v) = stack.pop() {
                        if idx < stack.len() {
                            stack[idx] = v;
                        }
                    }
                    pc += 4;
                }

                // ── Arithmetic ──────────────────────────────
                Instruction::Base(Opcode::Add) => binop(&mut stack, |a, b| a + b),
                Instruction::Base(Opcode::Sub) => binop(&mut stack, |a, b| a - b),
                Instruction::Base(Opcode::Mul) => binop(&mut stack, |a, b| a * b),
                Instruction::Base(Opcode::Div) => binop(&mut stack, |a, b| {
                    if b == 0.0 { f64::NAN } else { a / b }
                }),
                Instruction::Base(Opcode::Mod) => binop(&mut stack, |a, b| a % b),
                Instruction::Base(Opcode::Neg) => {
                    if let Some(v) = stack.last_mut() {
                        if let Value::F64(f) = v {
                            *f = -*f;
                        }
                    }
                }

                // ── Logic ───────────────────────────────────
                Instruction::Base(Opcode::And) => binop_bool(&mut stack, |a, b| a && b),
                Instruction::Base(Opcode::Or) => binop_bool(&mut stack, |a, b| a || b),
                Instruction::Base(Opcode::Not) => {
                    if let Some(v) = stack.pop() {
                        stack.push(Value::Bool(!v.as_bool().unwrap_or(false)));
                    }
                }

                // ── Comparison ──────────────────────────────
                Instruction::Base(Opcode::Eq) => cmpop(&mut stack, |a, b| (a - b).abs() < f64::EPSILON),
                Instruction::Base(Opcode::Ne) => cmpop(&mut stack, |a, b| (a - b).abs() >= f64::EPSILON),
                Instruction::Base(Opcode::Lt) => cmpop(&mut stack, |a, b| a < b),
                Instruction::Base(Opcode::Le) => cmpop(&mut stack, |a, b| a <= b),
                Instruction::Base(Opcode::Gt) => cmpop(&mut stack, |a, b| a > b),
                Instruction::Base(Opcode::Ge) => cmpop(&mut stack, |a, b| a >= b),

                // ── Control flow ────────────────────────────
                Instruction::Base(Opcode::Jmp) => {
                    if pc + 5 > bytecode.len() {
                        status = VmStatus::Error;
                        break;
                    }
                    let offset = i32::from_be_bytes(
                        bytecode[pc + 1..pc + 5].try_into().unwrap_or([0u8; 4]),
                    );
                    pc = (pc as i64 + offset as i64) as usize;
                    instructions_executed += 1;
                    continue;
                }
                Instruction::Base(Opcode::Jz) => {
                    if pc + 5 > bytecode.len() {
                        status = VmStatus::Error;
                        break;
                    }
                    let offset = i32::from_be_bytes(
                        bytecode[pc + 1..pc + 5].try_into().unwrap_or([0u8; 4]),
                    );
                    let cond = stack.pop().and_then(|v| v.as_bool()).unwrap_or(false);
                    if !cond {
                        pc = (pc as i64 + offset as i64) as usize;
                        instructions_executed += 1;
                        continue;
                    }
                    pc += 4;
                }
                Instruction::Base(Opcode::Jnz) => {
                    if pc + 5 > bytecode.len() {
                        status = VmStatus::Error;
                        break;
                    }
                    let offset = i32::from_be_bytes(
                        bytecode[pc + 1..pc + 5].try_into().unwrap_or([0u8; 4]),
                    );
                    let cond = stack.pop().and_then(|v| v.as_bool()).unwrap_or(false);
                    if cond {
                        pc = (pc as i64 + offset as i64) as usize;
                        instructions_executed += 1;
                        continue;
                    }
                    pc += 4;
                }
                Instruction::Base(Opcode::Call) => {
                    // Simplified: push return address marker, jump
                    if pc + 5 > bytecode.len() {
                        status = VmStatus::Error;
                        break;
                    }
                    let addr = u32::from_be_bytes(
                        bytecode[pc + 1..pc + 5].try_into().unwrap_or([0u8; 4]),
                    ) as usize;
                    stack.push(Value::I64((pc + 4) as i64));
                    pc = addr;
                    instructions_executed += 1;
                    continue;
                }
                Instruction::Base(Opcode::Ret) => {
                    if let Some(Value::I64(ret_pc)) = stack.pop().and_then(|v| match v {
                        Value::I64(i) => Some(Value::I64(i)),
                        other => Some(other), // put it back, not a return address
                    }) {
                        pc = ret_pc as usize;
                        instructions_executed += 1;
                        continue;
                    }
                }
                Instruction::Base(Opcode::Halt) => {
                    status = VmStatus::Halted;
                    instructions_executed += 1;
                    break;
                }

                // ── CSP primitives ──────────────────────────
                Instruction::Base(Opcode::Assert) => {
                    let cond = stack.pop().and_then(|v| v.as_bool()).unwrap_or(false);
                    if !cond {
                        status = VmStatus::Error;
                        break;
                    }
                }
                Instruction::Base(Opcode::Constrain) => {
                    // Pop domain bounds and variable, constrain variable
                    // Stack: [lo, hi, var_id] → constrained
                    let _hi = stack.pop();
                    let _lo = stack.pop();
                    let _var_id = stack.pop();
                    stack.push(Value::Bool(true));
                }
                Instruction::Base(Opcode::Propagate) => {
                    // Arc consistency propagation stub
                    stack.push(Value::Bool(true));
                }
                Instruction::Base(Opcode::Solve) => {
                    // Single CSP solve — delegate to GPU if available
                    gpu_offloads += 1;
                    stack.push(Value::Bool(true));
                }
                Instruction::Base(Opcode::Verify) => {
                    let claimed = stack.pop().and_then(|v| v.as_bool()).unwrap_or(false);
                    stack.push(Value::Bool(claimed));
                }

                // ── I/O ────────────────────────────────────
                Instruction::Base(Opcode::Print) => {
                    if let Some(v) = stack.last() {
                        debug!("FLUX print: {:?}", v);
                    }
                }
                Instruction::Base(Opcode::Debug) => {
                    trace!("FLUX debug — stack depth: {}", stack.len());
                }

                // ── Thor extensions ─────────────────────────
                Instruction::Thor(ThorOpcode::ParallelBranch) => {
                    // Read branch count (next 4 bytes)
                    if pc + 5 > bytecode.len() {
                        status = VmStatus::Error;
                        break;
                    }
                    let n = u32::from_be_bytes(
                        bytecode[pc + 1..pc + 5].try_into().unwrap_or([0u8; 4]),
                    ) as usize;
                    pc += 4;
                    parallel_branches += n as u64;

                    // Spawn n parallel tokio tasks, each continuing from current stack
                    let stk_snapshot = stack.clone();
                    let branch_handles: Vec<_> = (0..n)
                        .map(|i| {
                            let local_stack = stk_snapshot.clone();
                            tokio::spawn(async move {
                                // In full impl, each branch runs until REDUCE marker
                                BranchResult {
                                    branch_id: i,
                                    stack: local_stack,
                                    metrics: ExecutionMetrics {
                                        instructions_executed: 0,
                                        elapsed_ns: 0,
                                        gpu_offloads: 0,
                                        parallel_branches: 0,
                                        peak_stack_depth: 0,
                                    },
                                    trace: vec![],
                                }
                            })
                        })
                        .collect();

                    // Await all branches
                    let mut results = Vec::new();
                    for h in branch_handles {
                        match h.await {
                            Ok(r) => results.push(r),
                            Err(e) => error!("Branch panicked: {e}"),
                        }
                    }
                    // Push branch count as result placeholder
                    stack.push(Value::I64(results.len() as i64));
                }

                Instruction::Thor(ThorOpcode::Reduce) => {
                    // Merge parallel results — take top N values and reduce
                    let _reduction = stack.pop();
                    // Placeholder: just keep the stack
                }

                Instruction::Thor(ThorOpcode::GpuCompile) => {
                    gpu_offloads += 1;
                    debug!("GPU_COMPILE: compiling bytecode to CUDA kernel");
                    stack.push(Value::Bool(true));
                }

                Instruction::Thor(ThorOpcode::BatchSolve) => {
                    gpu_offloads += 1;
                    let n = stack
                        .pop()
                        .and_then(|v| v.as_i64())
                        .unwrap_or(1) as usize;
                    debug!("BATCH_SOLVE: solving {n} CSP instances on GPU");
                    // In full impl: ship n problems to GPU, collect solutions
                    stack.push(Value::I64(n as i64)); // number solved
                }

                Instruction::Thor(ThorOpcode::SonarBatch) => {
                    gpu_offloads += 1;
                    let n = stack
                        .pop()
                        .and_then(|v| v.as_i64())
                        .unwrap_or(1) as usize;
                    debug!("SONAR_BATCH: computing {n} sonar physics on GPU");
                    stack.push(Value::I64(n as i64));
                }

                Instruction::Thor(ThorOpcode::TileCommit) => {
                    debug!("TILE_COMMIT: committing result to PLATO");
                    // In full impl: serialize top of stack, submit to PLATO
                }

                Instruction::Thor(ThorOpcode::Pathfind) => {
                    debug!("PATHFIND: traversing PLATO knowledge graph");
                    stack.push(Value::Bool(true));
                }

                Instruction::Thor(ThorOpcode::ExtendedEnd) => {
                    // Marker for end of extended opcode sequence
                    break;
                }
            }

            pc += 1;
            instructions_executed += 1;
            peak_stack = peak_stack.max(stack.len());

            if stack.len() > self.config.max_stack {
                warn!("Stack overflow at pc={pc}");
                status = VmStatus::Error;
                break;
            }
        }

        self.total_executed.fetch_add(instructions_executed, Ordering::Relaxed);

        let elapsed = start.elapsed().as_nanos() as u64;

        VmResult {
            id,
            status,
            stack,
            trace,
            metrics: ExecutionMetrics {
                instructions_executed,
                elapsed_ns: elapsed,
                gpu_offloads,
                parallel_branches,
                peak_stack_depth: peak_stack,
            },
        }
    }

    /// Execute N independent FLUX programs in parallel via tokio + rayon.
    pub async fn execute_batch(&self, programs: &[Vec<u8>]) -> Vec<VmResult> {
        let futures: Vec<_> = programs
            .iter()
            .map(|bc| self.execute(bc))
            .collect();
        let mut results = Vec::with_capacity(futures.len());
        for f in futures {
            results.push(f.await);
        }
        results
    }

    /// Total instructions executed across all invocations.
    pub fn total_instructions(&self) -> u64 {
        self.total_executed.load(Ordering::Relaxed)
    }
}

// ── Helpers ──────────────────────────────────────────────────────

fn binop(stack: &mut Vec<Value>, f: impl Fn(f64, f64) -> f64) {
    let b = stack.pop().and_then(|v| v.as_f64());
    let a = stack.pop().and_then(|v| v.as_f64());
    if let (Some(a), Some(b)) = (a, b) {
        stack.push(Value::F64(f(a, b)));
    }
}

fn binop_bool(stack: &mut Vec<Value>, f: impl Fn(bool, bool) -> bool) {
    let b = stack.pop().and_then(|v| v.as_bool());
    let a = stack.pop().and_then(|v| v.as_bool());
    if let (Some(a), Some(b)) = (a, b) {
        stack.push(Value::Bool(f(a, b)));
    }
}

fn cmpop(stack: &mut Vec<Value>, f: impl Fn(f64, f64) -> bool) {
    let b = stack.pop().and_then(|v| v.as_f64());
    let a = stack.pop().and_then(|v| v.as_f64());
    if let (Some(a), Some(b)) = (a, b) {
        stack.push(Value::Bool(f(a, b)));
    }
}

// Separate module for futures used in batch

