//! Lowering passes: CIR → LCIR.
//!
//! This module implements the core transformation pipeline:
//!   1. **Quantifier Elimination** — Expand `forall`/`exists` over finite domains.
//!   2. **Temporal Expansion** — Replace `always`, `next`, `old`, `rate_of`, etc.
//!      with explicit history-buffer loads.
//!   3. **Relation Flattening** — Break nested comparisons into simple atoms.
//!   4. **A-normalization** — Ensure every sub-expression is bound to a variable.
//!   5. **Basic-block Generation** — Emit explicit CFG with jumps and branches.

use crate::cir::{
    BinOp, BufferId, CirDerived, CirInvariant, CirModule, CirType, ConstValue, Expr, TypeKind,
    Unit, VarId, VarInfo, VarKind,
};
use crate::error::{GuardError, Result, Span};
use crate::lcir::{
    AtomicOp, BasicBlock, BlockId, HaltReason, LcirBuilder, LcirProgram, Stmt, Terminator,
};
use indexmap::IndexMap;

// ---------------------------------------------------------------------------
// Lowering Context
// ---------------------------------------------------------------------------

/// Mutable state carried through the lowering pipeline.
pub struct LowerCtx<'a> {
    pub module: &'a CirModule,
    pub builder: LcirBuilder,
    /// Map from CIR VarId to LCIR VarId (for renamed temporals).
    pub var_map: IndexMap<VarId, VarId>,
    /// Map from temporal buffer ID to FLUX slot base.
    pub buffer_slots: IndexMap<BufferId, u8>,
    /// Counter for generating unique temporaries.
    pub tmp_counter: u32,
}

impl<'a> LowerCtx<'a> {
    pub fn new(module: &'a CirModule) -> Self {
        Self {
            module,
            builder: LcirBuilder::new(&module.name, &module.version),
            var_map: IndexMap::new(),
            buffer_slots: IndexMap::new(),
            tmp_counter: 0,
        }
    }

    /// Generate a fresh temporary variable name.
    pub fn fresh_tmp(&mut self, ty: CirType, name_hint: &str) -> VarId {
        let name = format!("{}_t{}", name_hint, self.tmp_counter);
        self.tmp_counter += 1;
        self.builder.fresh_var(ty, VarKind::Local, &name)
    }

    /// Look up the FLUX memory slot for a CIR variable.
    pub fn slot_for(&mut self, var: VarId) -> u8 {
        let lcir_var = self.var_map.get(&var).copied().unwrap_or(var);
        self.builder.allocate_slot(lcir_var)
    }

    /// Ensure a CIR variable is mapped into LCIR and has a slot.
    pub fn map_var(&mut self, var: VarId) -> VarId {
        *self.var_map.entry(var).or_insert_with(|| {
            let info = self.module.symbol_table.var_info(var);
            let ty = info.map(|i| i.ty.clone()).unwrap_or_else(|| CirType {
                kind: TypeKind::Real,
                unit: Unit::Dimensionless,
            });
            self.builder.fresh_var(ty, VarKind::Local, "v")
        })
    }
}

// ---------------------------------------------------------------------------
// Entry Point
// ---------------------------------------------------------------------------

/// Lower a complete CIR module to LCIR.
pub fn lower_module(module: &CirModule) -> Result<LcirProgram> {
    let mut ctx = LowerCtx::new(module);

    // Allocate slots for all state variables and constants.
    for (id, info) in &module.symbol_table.vars {
        let lcir_id = ctx.map_var(*id);
        ctx.builder.allocate_slot(lcir_id);
    }

    // Allocate history buffer slots for temporal variables.
    for (buf_id, buf_info) in &module.symbol_table.buffers {
        let slot = ctx.builder.allocate_slot(buf_info.var);
        ctx.buffer_slots.insert(*buf_id, slot);
    }

    // Emit initialization block that loads constants and state defaults.
    let init_block = ctx.builder.current_block;
    emit_init(&mut ctx)?;

    // Create the main constraint-check loop body.
    let loop_head = ctx.builder.fresh_block("loop_head");
    let loop_body = ctx.builder.fresh_block("loop_body");
    let loop_exit = ctx.builder.fresh_block("loop_exit");

    // Init → loop_head
    ctx.builder.switch_block(init_block);
    ctx.builder.set_terminator(Terminator::Jump(loop_head));

    // Loop head: trace marker, then fall through to body
    ctx.builder.switch_block(loop_head);
    ctx.builder.emit(Stmt::Trace {
        label: "constraint_loop".to_string(),
        span: Span::new("<lower>", 0, 0),
    });
    ctx.builder.set_terminator(Terminator::Jump(loop_body));

    // Loop body: emit all invariant checks.
    ctx.builder.switch_block(loop_body);
    for inv in &module.invariants {
        lower_invariant(&mut ctx, inv)?;
    }

    // Loop body → loop_head (unconditional jump back)
    ctx.builder.set_terminator(Terminator::Jump(loop_head));

    // Loop exit: halt (unreachable in normal operation, but required).
    ctx.builder.switch_block(loop_exit);
    ctx.builder.set_terminator(Terminator::Halt {
        reason: HaltReason::Normal,
    });

    let prog = ctx.builder.build();
    prog.validate()?;
    Ok(prog)
}

// ---------------------------------------------------------------------------
// Per-Invariant Lowering
// ---------------------------------------------------------------------------

fn lower_invariant(ctx: &mut LowerCtx, inv: &CirInvariant) -> Result<()> {
    let span = inv.source_span.clone();

    // If there is a `when` guard, emit a conditional branch.
    let guard_var = if let Some(when) = &inv.when {
        let guard = lower_expr_to_var(ctx, when)?;
        Some(guard)
    } else {
        None
    };

    let check_block = ctx.builder.fresh_block(&format!("inv_{}", inv.name));
    let next_block = ctx.builder.fresh_block(&format!("inv_{}_done", inv.name));

    if let Some(gv) = guard_var {
        let current = ctx.builder.current_block;
        ctx.builder.switch_block(current);
        ctx.builder.set_terminator(Terminator::Branch {
            cond: gv,
            then_target: check_block,
            else_target: next_block,
        });
    }

    ctx.builder.switch_block(check_block);

    // Lower the ensure expression.
    let result = lower_expr_to_var(ctx, &inv.ensure)?;

    // Emit assert.
    ctx.builder.emit(Stmt::Assert {
        cond: result,
        invariant_name: inv.name.clone(),
        span: span.clone(),
    });

    ctx.builder.set_terminator(Terminator::Jump(next_block));
    ctx.builder.switch_block(next_block);

    Ok(())
}

// ---------------------------------------------------------------------------
// Expression Lowering
// ---------------------------------------------------------------------------

/// Lower a CIR expression into a fresh LCIR variable (ANF).
/// This is the heart of the lowering pass.
pub fn lower_expr_to_var(ctx: &mut LowerCtx, expr: &Expr) -> Result<VarId> {
    let span = Span::new("<lower>", 0, 0);
    let ty = expr.ty().clone();

    match expr {
        Expr::Const(c) => {
            let dest = ctx.fresh_tmp(ty, "c");
            ctx.builder.emit(Stmt::Assign {
                dest,
                op: AtomicOp::Const(c.clone()),
                span,
            });
            Ok(dest)
        }

        Expr::Var(v) => {
            let dest = ctx.map_var(*v);
            Ok(dest)
        }

        Expr::Unary { op, operand, .. } => {
            let src = lower_expr_to_var(ctx, operand)?;
            let dest = ctx.fresh_tmp(ty, "u");
            let atomic = match op {
                crate::cir::UnOp::Neg => AtomicOp::Neg(src),
                crate::cir::UnOp::Abs => AtomicOp::Abs(src),
                crate::cir::UnOp::Not => AtomicOp::Not(src),
            };
            ctx.builder.emit(Stmt::Assign { dest, op: atomic, span });
            Ok(dest)
        }

        Expr::Binary { op, left, right, .. } => {
            let l = lower_expr_to_var(ctx, left)?;
            let r = lower_expr_to_var(ctx, right)?;
            let dest = ctx.fresh_tmp(ty, "b");
            let atomic = match op {
                BinOp::Add => AtomicOp::Add(l, r),
                BinOp::Sub => AtomicOp::Sub(l, r),
                BinOp::Mul => AtomicOp::Mul(l, r),
                BinOp::Div => AtomicOp::Div(l, r),
                BinOp::Mod => AtomicOp::Mod(l, r),
                BinOp::Eq => AtomicOp::Eq(l, r),
                BinOp::Neq => AtomicOp::Neq(l, r),
                BinOp::Lt => AtomicOp::Lt(l, r),
                BinOp::Gt => AtomicOp::Gt(l, r),
                BinOp::Lte => AtomicOp::Lte(l, r),
                BinOp::Gte => AtomicOp::Gte(l, r),
                BinOp::And => AtomicOp::And(l, r),
                BinOp::Or => AtomicOp::Or(l, r),
                BinOp::Implies => AtomicOp::Implies(l, r),
            };
            ctx.builder.emit(Stmt::Assign { dest, op: atomic, span });
            Ok(dest)
        }

        Expr::If { cond, then_branch, else_branch, .. } => {
            let cond_var = lower_expr_to_var(ctx, cond)?;
            let then_block = ctx.builder.fresh_block("if_then");
            let else_block = ctx.builder.fresh_block("if_else");
            let merge_block = ctx.builder.fresh_block("if_merge");

            let current = ctx.builder.current_block;
            ctx.builder.switch_block(current);
            ctx.builder.set_terminator(Terminator::Branch {
                cond: cond_var,
                then_target: then_block,
                else_target: else_block,
            });

            // Then branch
            ctx.builder.switch_block(then_block);
            let then_val = lower_expr_to_var(ctx, then_branch)?;
            let then_out = ctx.fresh_tmp(ty.clone(), "t");
            ctx.builder.emit(Stmt::Assign {
                dest: then_out,
                op: AtomicOp::Const(ConstValue::Bool(true)), // placeholder: copy via load/store
                span: span.clone(),
            });
            // Actually copy the value: store then_val to a temp slot, then load in merge
            let tmp_slot = ctx.builder.allocate_slot(then_out);
            ctx.builder.emit(Stmt::Store {
                src: then_val,
                slot: tmp_slot,
                span: span.clone(),
            });
            ctx.builder.set_terminator(Terminator::Jump(merge_block));

            // Else branch
            ctx.builder.switch_block(else_block);
            let else_val = lower_expr_to_var(ctx, else_branch)?;
            ctx.builder.emit(Stmt::Store {
                src: else_val,
                slot: tmp_slot,
                span: span.clone(),
            });
            ctx.builder.set_terminator(Terminator::Jump(merge_block));

            // Merge block: load the unified slot
            ctx.builder.switch_block(merge_block);
            let dest = ctx.fresh_tmp(ty, "phi");
            ctx.builder.emit(Stmt::Assign {
                dest,
                op: AtomicOp::LoadSlot(tmp_slot),
                span,
            });
            Ok(dest)
        }

        // Temporal operators — expanded to history buffer accesses
        Expr::Old(var, _) => {
            let dest = ctx.fresh_tmp(ty, "old");
            // Find buffer for this variable
            let buf_slot = ctx
                .buffer_slots
                .iter()
                .find(|(buf_id, &_slot)| {
                    ctx.module.symbol_table.buffers.get(*buf_id).map(|b| b.var == *var).unwrap_or(false)
                })
                .map(|(_, slot)| *slot)
                .unwrap_or_else(|| ctx.slot_for(*var));
            ctx.builder.emit(Stmt::Assign {
                dest,
                op: AtomicOp::Old {
                    buffer: buf_slot,
                    depth: 1,
                },
                span,
            });
            Ok(dest)
        }

        Expr::RateOf(var, _) => {
            let dest = ctx.fresh_tmp(ty, "rate");
            let buf_slot = ctx
                .buffer_slots
                .iter()
                .find(|(buf_id, &_slot)| {
                    ctx.module.symbol_table.buffers.get(*buf_id).map(|b| b.var == *var).unwrap_or(false)
                })
                .map(|(_, slot)| *slot)
                .unwrap_or_else(|| ctx.slot_for(*var));
            let dt = ctx.module.sample_period_ms / 1000.0;
            ctx.builder.emit(Stmt::Assign {
                dest,
                op: AtomicOp::RateOf { buffer: buf_slot, dt },
                span,
            });
            Ok(dest)
        }

        Expr::Delta(var, _) => {
            let dest = ctx.fresh_tmp(ty, "delta");
            let buf_slot = ctx
                .buffer_slots
                .iter()
                .find(|(buf_id, &_slot)| {
                    ctx.module.symbol_table.buffers.get(*buf_id).map(|b| b.var == *var).unwrap_or(false)
                })
                .map(|(_, slot)| *slot)
                .unwrap_or_else(|| ctx.slot_for(*var));
            ctx.builder.emit(Stmt::Assign {
                dest,
                op: AtomicOp::Delta { buffer: buf_slot },
                span,
            });
            Ok(dest)
        }

        // Quantifiers — eliminate by expansion over finite domains
        Expr::Forall { var, domain, body, .. } => {
            lower_forall(ctx, *var, domain, body)
        }
        Expr::Exists { var, domain, body, .. } => {
            lower_exists(ctx, *var, domain, body)
        }

        // Simple temporal: always P → P ∧ old(always P) unrolled
        Expr::Always(inner, _) => {
            // For finite-horizon checking, unroll k times.
            // Here we simplify to just the inner expression (single-step).
            lower_expr_to_var(ctx, inner)
        }
        Expr::Next(inner, _) => {
            lower_expr_to_var(ctx, inner)
        }
        Expr::Eventually(inner, _) => {
            lower_expr_to_var(ctx, inner)
        }
        Expr::Until { left, right, .. } => {
            // Simplified: emit (left or right) for single-step
            let l = lower_expr_to_var(ctx, left)?;
            let r = lower_expr_to_var(ctx, right)?;
            let dest = ctx.fresh_tmp(ty, "until");
            ctx.builder.emit(Stmt::Assign {
                dest,
                op: AtomicOp::Or(l, r),
                span,
            });
            Ok(dest)
        }
        Expr::Since { left, right, .. } => {
            let l = lower_expr_to_var(ctx, left)?;
            let r = lower_expr_to_var(ctx, right)?;
            let dest = ctx.fresh_tmp(ty, "since");
            ctx.builder.emit(Stmt::Assign {
                dest,
                op: AtomicOp::And(l, r),
                span,
            });
            Ok(dest)
        }
        Expr::For { duration, body, .. } => {
            // Expand to a conjunction over the last N samples.
            // For now, simplify to just the current sample.
            let _ = duration;
            lower_expr_to_var(ctx, body)
        }
        Expr::After { duration, body, .. } => {
            let _ = duration;
            lower_expr_to_var(ctx, body)
        }

        Expr::Index { .. } => {
            Err(GuardError::Lowering("array index lowering not yet implemented".into()))
        }
        Expr::Field { .. } => {
            Err(GuardError::Lowering("field access lowering not yet implemented".into()))
        }
    }
}

// ---------------------------------------------------------------------------
// Quantifier Elimination
// ---------------------------------------------------------------------------

fn lower_forall(
    ctx: &mut LowerCtx,
    _var: VarId,
    domain: &crate::cir::Domain,
    body: &Expr,
) -> Result<VarId> {
    let span = Span::new("<lower>", 0, 0);
    let bool_ty = CirType {
        kind: TypeKind::Boolean,
        unit: Unit::Dimensionless,
    };

    match domain {
        crate::cir::Domain::Enum(variants) => {
            let mut acc: Option<VarId> = None;
            for _variant in variants {
                // In a real implementation, substitute the variant for the bound
                // variable in the body, then lower.
                let lowered = lower_expr_to_var(ctx, body)?;
                acc = match acc {
                    None => Some(lowered),
                    Some(prev) => {
                        let dest = ctx.fresh_tmp(bool_ty.clone(), "forall");
                        ctx.builder.emit(Stmt::Assign {
                            dest,
                            op: AtomicOp::And(prev, lowered),
                            span: span.clone(),
                        });
                        Some(dest)
                    }
                };
            }
            Ok(acc.unwrap_or_else(|| {
                let t = ctx.fresh_tmp(bool_ty, "true");
                ctx.builder.emit(Stmt::Assign {
                    dest: t,
                    op: AtomicOp::Const(ConstValue::Bool(true)),
                    span: span.clone(),
                });
                t
            }))
        }
        crate::cir::Domain::Interval { low, high } => {
            let mut acc: Option<VarId> = None;
            for _i in *low..=*high {
                let lowered = lower_expr_to_var(ctx, body)?;
                acc = match acc {
                    None => Some(lowered),
                    Some(prev) => {
                        let dest = ctx.fresh_tmp(bool_ty.clone(), "forall");
                        ctx.builder.emit(Stmt::Assign {
                            dest,
                            op: AtomicOp::And(prev, lowered),
                            span: span.clone(),
                        });
                        Some(dest)
                    }
                };
            }
            Ok(acc.unwrap_or_else(|| {
                let t = ctx.fresh_tmp(bool_ty, "true");
                ctx.builder.emit(Stmt::Assign {
                    dest: t,
                    op: AtomicOp::Const(ConstValue::Bool(true)),
                    span,
                });
                t
            }))
        }
        crate::cir::Domain::Array { size } => {
            let mut acc: Option<VarId> = None;
            for _i in 0..*size {
                let lowered = lower_expr_to_var(ctx, body)?;
                acc = match acc {
                    None => Some(lowered),
                    Some(prev) => {
                        let dest = ctx.fresh_tmp(bool_ty.clone(), "forall");
                        ctx.builder.emit(Stmt::Assign {
                            dest,
                            op: AtomicOp::And(prev, lowered),
                            span: span.clone(),
                        });
                        Some(dest)
                    }
                };
            }
            Ok(acc.unwrap_or_else(|| {
                let t = ctx.fresh_tmp(bool_ty, "true");
                ctx.builder.emit(Stmt::Assign {
                    dest: t,
                    op: AtomicOp::Const(ConstValue::Bool(true)),
                    span,
                });
                t
            }))
        }
    }
}

fn lower_exists(
    ctx: &mut LowerCtx,
    _var: VarId,
    domain: &crate::cir::Domain,
    body: &Expr,
) -> Result<VarId> {
    let span = Span::new("<lower>", 0, 0);
    let bool_ty = CirType {
        kind: TypeKind::Boolean,
        unit: Unit::Dimensionless,
    };

    match domain {
        crate::cir::Domain::Enum(variants) => {
            let mut acc: Option<VarId> = None;
            for _variant in variants {
                let lowered = lower_expr_to_var(ctx, body)?;
                acc = match acc {
                    None => Some(lowered),
                    Some(prev) => {
                        let dest = ctx.fresh_tmp(bool_ty.clone(), "exists");
                        ctx.builder.emit(Stmt::Assign {
                            dest,
                            op: AtomicOp::Or(prev, lowered),
                            span: span.clone(),
                        });
                        Some(dest)
                    }
                };
            }
            Ok(acc.unwrap_or_else(|| {
                let f = ctx.fresh_tmp(bool_ty, "false");
                ctx.builder.emit(Stmt::Assign {
                    dest: f,
                    op: AtomicOp::Const(ConstValue::Bool(false)),
                    span,
                });
                f
            }))
        }
        crate::cir::Domain::Interval { low, high } => {
            let mut acc: Option<VarId> = None;
            for _i in *low..=*high {
                let lowered = lower_expr_to_var(ctx, body)?;
                acc = match acc {
                    None => Some(lowered),
                    Some(prev) => {
                        let dest = ctx.fresh_tmp(bool_ty.clone(), "exists");
                        ctx.builder.emit(Stmt::Assign {
                            dest,
                            op: AtomicOp::Or(prev, lowered),
                            span: span.clone(),
                        });
                        Some(dest)
                    }
                };
            }
            Ok(acc.unwrap_or_else(|| {
                let f = ctx.fresh_tmp(bool_ty, "false");
                ctx.builder.emit(Stmt::Assign {
                    dest: f,
                    op: AtomicOp::Const(ConstValue::Bool(false)),
                    span,
                });
                f
            }))
        }
        crate::cir::Domain::Array { size } => {
            let mut acc: Option<VarId> = None;
            for _i in 0..*size {
                let lowered = lower_expr_to_var(ctx, body)?;
                acc = match acc {
                    None => Some(lowered),
                    Some(prev) => {
                        let dest = ctx.fresh_tmp(bool_ty.clone(), "exists");
                        ctx.builder.emit(Stmt::Assign {
                            dest,
                            op: AtomicOp::Or(prev, lowered),
                            span: span.clone(),
                        });
                        Some(dest)
                    }
                };
            }
            Ok(acc.unwrap_or_else(|| {
                let f = ctx.fresh_tmp(bool_ty, "false");
                ctx.builder.emit(Stmt::Assign {
                    dest: f,
                    op: AtomicOp::Const(ConstValue::Bool(false)),
                    span,
                });
                f
            }))
        }
    }
}

// ---------------------------------------------------------------------------
// Initialization
// ---------------------------------------------------------------------------

fn emit_init(ctx: &mut LowerCtx) -> Result<()> {
    let span = Span::new("<init>", 0, 0);
    // Load constants into their slots.
    for (id, info) in &ctx.module.symbol_table.vars {
        if matches!(info.kind, VarKind::Constant) {
            let lcir_id = ctx.map_var(*id);
            let slot = ctx.builder.allocate_slot(lcir_id);
            // In a full implementation, we'd emit PushConst + Store here.
            ctx.builder.emit(Stmt::Store { src: lcir_id, slot, span: span.clone() });
        }
    }
    Ok(())
}
