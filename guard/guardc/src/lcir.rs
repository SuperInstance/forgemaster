//! Lowered CIR (LCIR) — a flat, A-normal form IR with no quantifiers or
//! temporal operators.
//!
//! LCIR is the input to code generation.  Every sub-expression is bound to a
//! named variable, and control flow is explicit (basic blocks with
//! conditional branches).

use crate::cir::{CirType, ConstValue, VarId, VarKind};
use crate::error::{GuardError, Result, Span};
use indexmap::IndexMap;

// ---------------------------------------------------------------------------
// LCIR Program
// ---------------------------------------------------------------------------

/// An LCIR program is a collection of basic blocks with a single entry point.
#[derive(Debug, Clone, PartialEq)]
pub struct LcirProgram {
    pub name: String,
    pub version: String,
    pub blocks: Vec<BasicBlock>,
    pub entry: BlockId,
    /// Memory slot allocation map: VarId → FLUX memory slot (0–255)
    pub slot_map: IndexMap<VarId, u8>,
    /// Total number of slots used.
    pub slot_count: u8,
    /// Per-invariant metadata for bytecode emission.
    pub invariant_metadata: Vec<InvariantMeta>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct InvariantMeta {
    pub name: String,
    pub priority: crate::cir::Priority,
    pub on_violation: crate::cir::ViolationAction,
    pub assert_slot: u8, // slot holding the boolean result
    pub source_span: Span,
}

// ---------------------------------------------------------------------------
// Basic Blocks
// ---------------------------------------------------------------------------

/// A basic block identifier.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct BlockId(pub u32);

/// A basic block: a sequence of atomic statements ending in a terminator.
#[derive(Debug, Clone, PartialEq)]
pub struct BasicBlock {
    pub id: BlockId,
    pub label: String,
    pub stmts: Vec<Stmt>,
    pub terminator: Terminator,
}

// ---------------------------------------------------------------------------
// Statements (A-normal form)
// ---------------------------------------------------------------------------

/// An atomic statement with a clear evaluation order.
#[derive(Debug, Clone, PartialEq)]
pub enum Stmt {
    /// Assign the result of an atomic expression to a variable.
    Assign { dest: VarId, op: AtomicOp, span: Span },
    /// Load a state variable from its memory slot.
    LoadState { dest: VarId, slot: u8, ty: CirType, span: Span },
    /// Store a local variable to a memory slot.
    Store { src: VarId, slot: u8, span: Span },
    /// Push a constant onto the evaluation stack.
    PushConst { value: ConstValue, span: Span },
    /// Pop the top of stack into a variable.
    Pop { dest: VarId, ty: CirType, span: Span },
    /// Assert that a boolean variable is true.
    Assert { cond: VarId, invariant_name: String, span: Span },
    /// Trace / mark a source location.
    Trace { label: String, span: Span },
}

/// Atomic operations that can appear on the right-hand side of `Assign`.
/// Every operand is either a variable or a constant — no nested expressions.
#[derive(Debug, Clone, PartialEq)]
pub enum AtomicOp {
    // Nullary
    Const(ConstValue),

    // Unary
    Neg(VarId),
    Abs(VarId),
    Not(VarId),

    // Binary arithmetic
    Add(VarId, VarId),
    Sub(VarId, VarId),
    Mul(VarId, VarId),
    Div(VarId, VarId),
    Mod(VarId, VarId),

    // Comparison
    Eq(VarId, VarId),
    Neq(VarId, VarId),
    Lt(VarId, VarId),
    Gt(VarId, VarId),
    Lte(VarId, VarId),
    Gte(VarId, VarId),

    // Logic
    And(VarId, VarId),
    Or(VarId, VarId),
    Implies(VarId, VarId),

    // Memory
    LoadSlot(u8),

    // History buffer access (temporal lowering)
    Old { buffer: u8, depth: usize },
    RateOf { buffer: u8, dt: f64 },
    Delta { buffer: u8 },
}

// ---------------------------------------------------------------------------
// Terminators
// ---------------------------------------------------------------------------

/// Control-flow terminator for a basic block.
#[derive(Debug, Clone, PartialEq)]
pub enum Terminator {
    /// Unconditional jump to another block.
    Jump(BlockId),
    /// Conditional branch.
    Branch { cond: VarId, then_target: BlockId, else_target: BlockId },
    /// Halt the VM.
    Halt { reason: HaltReason },
    /// Return from a subroutine (used for loop bodies).
    Return,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum HaltReason {
    ConstraintViolation { invariant: String },
    Normal,
}

// ---------------------------------------------------------------------------
// Builder helpers
// ---------------------------------------------------------------------------

/// A builder for constructing LCIR programs incrementally.
pub struct LcirBuilder {
    program: LcirProgram,
    pub current_block: BlockId,
    next_var: u32,
    next_block: u32,
}

impl LcirBuilder {
    pub fn new(name: impl Into<String>, version: impl Into<String>) -> Self {
        let entry = BlockId(0);
        let mut builder = Self {
            program: LcirProgram {
                name: name.into(),
                version: version.into(),
                blocks: vec![BasicBlock {
                    id: entry,
                    label: "entry".to_string(),
                    stmts: vec![],
                    terminator: Terminator::Halt {
                        reason: HaltReason::Normal,
                    },
                }],
                entry,
                slot_map: IndexMap::new(),
                slot_count: 0,
                invariant_metadata: vec![],
            },
            current_block: entry,
            next_var: 1000, // Reserve 0–999 for CIR vars
            next_block: 1,
        };
        builder
    }

    pub fn fresh_var(&mut self, ty: CirType, kind: VarKind, _name_hint: &str) -> VarId {
        let id = VarId(self.next_var);
        self.next_var += 1;
        id
    }

    pub fn fresh_block(&mut self, label: impl Into<String>) -> BlockId {
        let id = BlockId(self.next_block);
        self.next_block += 1;
        self.program.blocks.push(BasicBlock {
            id,
            label: label.into(),
            stmts: vec![],
            terminator: Terminator::Halt {
                reason: HaltReason::Normal,
            },
        });
        id
    }

    pub fn switch_block(&mut self, id: BlockId) {
        self.current_block = id;
    }

    pub fn current(&mut self) -> &mut BasicBlock {
        let idx = self.current_block.0 as usize;
        &mut self.program.blocks[idx]
    }

    pub fn emit(&mut self, stmt: Stmt) {
        self.current().stmts.push(stmt);
    }

    pub fn set_terminator(&mut self, term: Terminator) {
        self.current().terminator = term;
    }

    pub fn allocate_slot(&mut self, var: VarId) -> u8 {
        if let Some(&slot) = self.program.slot_map.get(&var) {
            return slot;
        }
        let slot = self.program.slot_count;
        assert!(slot < 224, "FLUX memory exhausted (max 224 user slots)");
        self.program.slot_count += 1;
        self.program.slot_map.insert(var, slot);
        slot
    }

    pub fn build(self) -> LcirProgram {
        self.program
    }
}

impl LcirProgram {
    /// Validate basic block integrity (all targets exist, entry is valid).
    pub fn validate(&self) -> Result<()> {
        let block_count = self.blocks.len();
        for block in &self.blocks {
            match &block.terminator {
                Terminator::Jump(target) | Terminator::Branch { then_target: target, .. } => {
                    if target.0 as usize >= block_count {
                        return Err(GuardError::Validation(format!(
                            "block {} jumps to non-existent block {}",
                            block.id.0, target.0
                        )));
                    }
                }
                Terminator::Branch { else_target: target, .. } => {
                    if target.0 as usize >= block_count {
                        return Err(GuardError::Validation(format!(
                            "block {} branches to non-existent block {}",
                            block.id.0, target.0
                        )));
                    }
                }
                _ => {}
            }
        }
        Ok(())
    }
}
