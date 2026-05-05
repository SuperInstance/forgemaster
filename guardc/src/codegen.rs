//! LCIR → FLUX bytecode emitter.
//!
//! Translates the flat A-normal form into the 43-opcode FLUX stack VM.
//! Memory layout:
//!   0–31   : constants
//!   32–127 : state variables
//!   128–223: temporal history buffers
//!   224–255: scratch / locals

use crate::cir::{ConstValue, TypeKind, VarKind};
use crate::error::{GuardError, Result, Span};
use crate::lcir::{
    AtomicOp, BasicBlock, BlockId, HaltReason, LcirProgram, Stmt, Terminator,
};
use flux_isa::bytecode::FluxBytecode;
use flux_isa::instruction::{FluxInstruction, InstructionMetadata};
use flux_isa::opcode::FluxOpcode;
use indexmap::IndexMap;

/// Code generation context.
pub struct CodegenCtx {
    pub bytecode: FluxBytecode,
    /// Map from LCIR BlockId to instruction offset.
    pub block_offsets: IndexMap<BlockId, usize>,
    /// Patch list for forward jumps: (instruction_index, target_block).
    pub jump_patches: Vec<(usize, BlockId)>,
    /// Current source span for metadata.
    pub current_span: Span,
}

impl CodegenCtx {
    pub fn new() -> Self {
        Self {
            bytecode: FluxBytecode::new(),
            block_offsets: IndexMap::new(),
            jump_patches: vec![],
            current_span: Span::new("<codegen>", 0, 0),
        }
    }

    pub fn emit(&mut self, inst: FluxInstruction) {
        self.bytecode.push(inst);
    }

    pub fn emit_op(&mut self, op: FluxOpcode) {
        self.bytecode.push(FluxInstruction::new(op));
    }

    pub fn emit_op_slot(&mut self, op: FluxOpcode, slot: u8) {
        self.bytecode.push(FluxInstruction::with_operands(
            op,
            vec![slot as f64],
        ));
    }

    pub fn emit_push(&mut self, value: f64) {
        self.bytecode.push(FluxInstruction::with_operands(
            FluxOpcode::Push,
            vec![value],
        ));
    }

    pub fn here(&self) -> usize {
        self.bytecode.instructions.len()
    }
}

/// Compile an LCIR program to FLUX bytecode.
pub fn codegen(program: &LcirProgram) -> Result<FluxBytecode> {
    let mut ctx = CodegenCtx::new();

    // First pass: record block offsets.
    for block in &program.blocks {
        ctx.block_offsets.insert(block.id, ctx.here());
        gen_block(&mut ctx, block)?;
    }

    // Second pass: patch forward jumps.
    for (inst_idx, target) in &ctx.jump_patches {
        let target_offset = ctx
            .block_offsets
            .get(target)
            .ok_or_else(|| GuardError::Codegen(format!("unknown block {:?}", target)))?;
        let inst = &mut ctx.bytecode.instructions[*inst_idx];
        // The first operand is the jump target.
        if inst.operands.is_empty() {
            inst.operands.push(*target_offset as f64);
        } else {
            inst.operands[0] = *target_offset as f64;
        }
    }

    // Ensure program ends with Halt.
    if ctx.bytecode.instructions.last().map(|i| i.opcode) != Some(FluxOpcode::Halt) {
        ctx.emit_op(FluxOpcode::Halt);
    }

    ctx.bytecode.validate().map_err(|e| {
        GuardError::Validation(format!("bytecode validation failed: {}", e))
    })?;

    Ok(ctx.bytecode)
}

fn gen_block(ctx: &mut CodegenCtx, block: &BasicBlock) -> Result<()> {
    // Label as metadata
    let _label = &block.label;

    for stmt in &block.stmts {
        gen_stmt(ctx, stmt)?;
    }

    gen_terminator(ctx, &block.terminator)?;
    Ok(())
}

fn gen_stmt(ctx: &mut CodegenCtx, stmt: &Stmt) -> Result<()> {
    match stmt {
        Stmt::Assign { dest: _, op, span } => {
            ctx.current_span = span.clone();
            gen_atomic_op(ctx, op)?;
        }
        Stmt::LoadState { dest: _, slot, ty, span } => {
            ctx.current_span = span.clone();
            // Load state from its slot, optionally converting type.
            ctx.emit_op_slot(FluxOpcode::Load, *slot);
            if matches!(ty.kind, TypeKind::Integer) {
                // Cast real (f64 on stack) to integer representation
                ctx.emit_op(FluxOpcode::Cast);
            }
        }
        Stmt::Store { src: _, slot, span } => {
            ctx.current_span = span.clone();
            ctx.emit_op_slot(FluxOpcode::Store, *slot);
        }
        Stmt::PushConst { value, span } => {
            ctx.current_span = span.clone();
            match value {
                ConstValue::Real(v) => ctx.emit_push(*v),
                ConstValue::Integer(v) => ctx.emit_push(*v as f64),
                ConstValue::Bool(b) => ctx.emit_push(if *b { 1.0 } else { 0.0 }),
            }
        }
        Stmt::Pop { dest: _, ty: _, span } => {
            ctx.current_span = span.clone();
            // Pop top of stack into a local slot.
            // In the current design, Pop is handled via Store after an operation.
            ctx.emit_op(FluxOpcode::Pop);
        }
        Stmt::Assert { cond: _, invariant_name, span } => {
            ctx.current_span = span.clone();
            // The boolean result is already on the stack from the preceding comparison.
            // Assert consumes it.
            let meta = InstructionMetadata::new()
                .with_source_location(format!("{}", span))
                .with_label(invariant_name.clone());
            ctx.emit(FluxInstruction::with_metadata(
                FluxOpcode::Assert,
                vec![], // Assert uses the stack top; constraint ID from metadata
                meta,
            ));
        }
        Stmt::Trace { label, span } => {
            ctx.current_span = span.clone();
            let meta = InstructionMetadata::new()
                .with_source_location(format!("{}", span))
                .with_label(label.clone());
            ctx.emit(FluxInstruction::with_metadata(
                FluxOpcode::Trace,
                vec![],
                meta,
            ));
        }
    }
    Ok(())
}

fn gen_atomic_op(ctx: &mut CodegenCtx, op: &AtomicOp) -> Result<()> {
    match op {
        AtomicOp::Const(c) => match c {
            ConstValue::Real(v) => ctx.emit_push(*v),
            ConstValue::Integer(v) => ctx.emit_push(*v as f64),
            ConstValue::Bool(b) => ctx.emit_push(if *b { 1.0 } else { 0.0 }),
        },
        AtomicOp::Neg(a) => {
            ctx.emit_op_slot(FluxOpcode::Load, a.0 as u8); // simplified: vars map to slots
            ctx.emit_op(FluxOpcode::Push);
            ctx.emit_push(-1.0);
            ctx.emit_op(FluxOpcode::Mul);
        }
        AtomicOp::Abs(a) => {
            ctx.emit_op_slot(FluxOpcode::Load, a.0 as u8);
            // abs(x) = sqrt(x*x) or conditional; FLUX has no native abs.
            // Emit: dup, neg, max
            ctx.emit_op(FluxOpcode::Push);
            ctx.emit_push(0.0);
            ctx.emit_op(FluxOpcode::Gte); // x >= 0 ?
            // Simplified: just push the value (placeholder for full abs)
        }
        AtomicOp::Not(a) => {
            ctx.emit_op_slot(FluxOpcode::Load, a.0 as u8);
            ctx.emit_op(FluxOpcode::Not);
        }
        AtomicOp::Add(a, b) => {
            ctx.emit_op_slot(FluxOpcode::Load, a.0 as u8);
            ctx.emit_op_slot(FluxOpcode::Load, b.0 as u8);
            ctx.emit_op(FluxOpcode::Add);
        }
        AtomicOp::Sub(a, b) => {
            ctx.emit_op_slot(FluxOpcode::Load, a.0 as u8);
            ctx.emit_op_slot(FluxOpcode::Load, b.0 as u8);
            ctx.emit_op(FluxOpcode::Sub);
        }
        AtomicOp::Mul(a, b) => {
            ctx.emit_op_slot(FluxOpcode::Load, a.0 as u8);
            ctx.emit_op_slot(FluxOpcode::Load, b.0 as u8);
            ctx.emit_op(FluxOpcode::Mul);
        }
        AtomicOp::Div(a, b) => {
            ctx.emit_op_slot(FluxOpcode::Load, a.0 as u8);
            ctx.emit_op_slot(FluxOpcode::Load, b.0 as u8);
            ctx.emit_op(FluxOpcode::Div);
        }
        AtomicOp::Mod(a, b) => {
            ctx.emit_op_slot(FluxOpcode::Load, a.0 as u8);
            ctx.emit_op_slot(FluxOpcode::Load, b.0 as u8);
            ctx.emit_op(FluxOpcode::Mod);
        }
        AtomicOp::Eq(a, b) => {
            ctx.emit_op_slot(FluxOpcode::Load, a.0 as u8);
            ctx.emit_op_slot(FluxOpcode::Load, b.0 as u8);
            ctx.emit_op(FluxOpcode::Eq);
        }
        AtomicOp::Neq(a, b) => {
            ctx.emit_op_slot(FluxOpcode::Load, a.0 as u8);
            ctx.emit_op_slot(FluxOpcode::Load, b.0 as u8);
            ctx.emit_op(FluxOpcode::Neq);
        }
        AtomicOp::Lt(a, b) => {
            ctx.emit_op_slot(FluxOpcode::Load, a.0 as u8);
            ctx.emit_op_slot(FluxOpcode::Load, b.0 as u8);
            ctx.emit_op(FluxOpcode::Lt);
        }
        AtomicOp::Gt(a, b) => {
            ctx.emit_op_slot(FluxOpcode::Load, a.0 as u8);
            ctx.emit_op_slot(FluxOpcode::Load, b.0 as u8);
            ctx.emit_op(FluxOpcode::Gt);
        }
        AtomicOp::Lte(a, b) => {
            ctx.emit_op_slot(FluxOpcode::Load, a.0 as u8);
            ctx.emit_op_slot(FluxOpcode::Load, b.0 as u8);
            ctx.emit_op(FluxOpcode::Lte);
        }
        AtomicOp::Gte(a, b) => {
            ctx.emit_op_slot(FluxOpcode::Load, a.0 as u8);
            ctx.emit_op_slot(FluxOpcode::Load, b.0 as u8);
            ctx.emit_op(FluxOpcode::Gte);
        }
        AtomicOp::And(a, b) => {
            ctx.emit_op_slot(FluxOpcode::Load, a.0 as u8);
            ctx.emit_op_slot(FluxOpcode::Load, b.0 as u8);
            ctx.emit_op(FluxOpcode::And);
        }
        AtomicOp::Or(a, b) => {
            ctx.emit_op_slot(FluxOpcode::Load, a.0 as u8);
            ctx.emit_op_slot(FluxOpcode::Load, b.0 as u8);
            ctx.emit_op(FluxOpcode::Or);
        }
        AtomicOp::Implies(a, b) => {
            // a → b  ≡  ¬a ∨ b
            ctx.emit_op_slot(FluxOpcode::Load, a.0 as u8);
            ctx.emit_op(FluxOpcode::Not);
            ctx.emit_op_slot(FluxOpcode::Load, b.0 as u8);
            ctx.emit_op(FluxOpcode::Or);
        }
        AtomicOp::LoadSlot(slot) => {
            ctx.emit_op_slot(FluxOpcode::Load, *slot);
        }
        AtomicOp::Old { buffer, depth } => {
            // Load from history buffer: buffer slot + depth offset
            let slot = buffer + *depth as u8;
            ctx.emit_op_slot(FluxOpcode::Load, slot);
        }
        AtomicOp::RateOf { buffer, dt } => {
            // (current - old) / dt
            ctx.emit_op_slot(FluxOpcode::Load, *buffer);
            let old_slot = buffer + 1;
            ctx.emit_op_slot(FluxOpcode::Load, old_slot);
            ctx.emit_op(FluxOpcode::Sub);
            ctx.emit_push(*dt);
            ctx.emit_op(FluxOpcode::Div);
        }
        AtomicOp::Delta { buffer } => {
            ctx.emit_op_slot(FluxOpcode::Load, *buffer);
            let old_slot = buffer + 1;
            ctx.emit_op_slot(FluxOpcode::Load, old_slot);
            ctx.emit_op(FluxOpcode::Sub);
        }
    }
    Ok(())
}

fn gen_terminator(ctx: &mut CodegenCtx, term: &Terminator) -> Result<()> {
    match term {
        Terminator::Jump(target) => {
            let here = ctx.here();
            ctx.jump_patches.push((here, *target));
            ctx.emit(FluxInstruction::with_operands(
                FluxOpcode::Jump,
                vec![0.0], // patched later
            ));
        }
        Terminator::Branch {
            cond,
            then_target,
            else_target,
        } => {
            // Load condition, branch if false (0) to else_target.
            ctx.emit_op_slot(FluxOpcode::Load, cond.0 as u8);
            let here = ctx.here();
            ctx.jump_patches.push((here, *else_target));
            ctx.emit(FluxInstruction::with_operands(
                FluxOpcode::Branch,
                vec![0.0], // patched later
            ));
            // Fall through to then_target.
            let here = ctx.here();
            ctx.jump_patches.push((here, *then_target));
            ctx.emit(FluxInstruction::with_operands(
                FluxOpcode::Jump,
                vec![0.0], // patched later
            ));
        }
        Terminator::Halt { reason } => {
            match reason {
                HaltReason::ConstraintViolation { invariant } => {
                    let meta = InstructionMetadata::new()
                        .with_label(format!("violation:{}", invariant));
                    ctx.emit(FluxInstruction::with_metadata(
                        FluxOpcode::Halt,
                        vec![],
                        meta,
                    ));
                }
                HaltReason::Normal => {
                    ctx.emit_op(FluxOpcode::Halt);
                }
            }
        }
        Terminator::Return => {
            ctx.emit_op(FluxOpcode::Return);
        }
    }
    Ok(())
}
