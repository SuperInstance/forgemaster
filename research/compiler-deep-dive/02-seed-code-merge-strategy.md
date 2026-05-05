# Unified `fluxc` Compiler Design: Rust Implementation
This design merges `guard2mask` and `guardc` into a single, production-grade compiler with a layered IR, proof tracking, composable optimizations, and support for all required features (LSP, incremental compilation, differential testing).

---

## Core Design Principles
1. **Layered IR** (inspired by Rustc/LLVM/Cranelift):
   - Surface AST → HIR → **CIR (Unified Constraint IR)** → L-CIR → Target IR
2. **Parser Choice**: Adopt `guard2mask`'s hand-written recursive descent parser (better error recovery, LSP support, span tracking).
3. **Unified IR**: Extend `guardc`'s **CIR** to absorb `guard2mask`'s types/IR—CIR becomes the single source of truth for middle-end optimizations and proof tracking.
4. **Proof-Carrying Code**: Track formal proof obligations through *every* pipeline step (leveraging `guardc`'s proof module).
5. **Composable Passes/Backends**: Use traits for optimization passes and codegen backends (like LLVM/Cranelift).

---

## Workspace & Module Structure
We use a workspace architecture (like Rustc) for modularity:
```toml
# Cargo.toml (workspace root)
[workspace]
members = [
    "fluxc_ast",      # Parser, surface AST, diagnostics, spans
    "fluxc_hir",      # High-level IR, semantic analysis (name/type/borrow check)
    "fluxc_middle",   # Unified CIR, proof tracking, optimizations, incremental queries
    "fluxc_lcir",     # Lowered CIR (target-independent, codegen-ready)
    "fluxc_codegen",  # Backends: FLUX bytecode, Cranelift, LLVM, RISC-V, eBPF, WAT
    "fluxc_driver",   # Compiler driver (orchestrates pipeline, config, sessions)
    "fluxc_lsp",      # LSP server (incremental parsing, diagnostics)
    "fluxc_test",     # Test utilities (differential testing, property-based testing)
]
```

---

## Key Module Outlines & Type Signatures

### 1. `fluxc_ast`: Frontend (Parser, Surface AST, Diagnostics)
Adopts `guard2mask`'s hand-written recursive descent parser for error recovery and LSP support.
```rust
// fluxc_ast/src/lib.rs
pub mod parser;      // Hand-written RD parser (from guard2mask, with error recovery)
pub mod lexer;       // Lexer with span tracking
pub mod ast;         // Unified surface AST (merges guard2mask/guardc ASTs)
pub mod diagnostic;  // Diagnostics (errors/warnings with spans for LSP/source maps)
pub mod span;        // Source location tracking

use std::hash::Hash;

// ------------------------------
// Core Types for Frontend
// ------------------------------
/// Unique identifier for source files (used in spans)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct FileId(pub u64);

/// Source span (byte offset + file ID) for diagnostics/LSP/source maps
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct Span {
    pub lo: usize,
    pub hi: usize,
    pub file_id: FileId,
}

/// Diagnostic severity (matches LSP protocol)
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Level { Error, Warning, Note, Help }

/// Diagnostic message with span and context (for error recovery/LSP)
#[derive(Debug, Clone)]
pub struct Diagnostic {
    pub level: Level,
    pub message: String,
    pub primary_span: Option<Span>,
    pub secondary_spans: Vec<(String, Option<Span>)>,
}

/// AST node wrapper: attaches span to every AST node (critical for diagnostics)
#[derive(Debug, Clone)]
pub struct AstNode<T> {
    pub kind: T,
    pub span: Span,
}

/// Unified identifier (for variables/functions/types)
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct Ident(pub String, pub Span);

/// Unified type system (merges guard2mask's types.rs and guardc's type system)
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum Ty {
    Bool,
    Int { width: usize, signed: bool },  // e.g., Int { width:32, signed:true } = i32
    BitVec(usize),
    Array(Box<Ty>, usize),                // Element type, length
    Function(Vec<Ty>, Box<Ty>),           // Params, return type
}

// ------------------------------
// Surface AST Kinds (Unified)
// ------------------------------
#[derive(Debug, Clone)]
pub enum ExprKind {
    // Literals
    LitBool(bool),
    LitInt(u64),
    LitBitVec(Vec<bool>),
    // Variables
    Var(Ident),
    // Arithmetic
    Add(Box<AstNode<ExprKind>>, Box<AstNode<ExprKind>>),
    Sub(Box<AstNode<ExprKind>>, Box<AstNode<ExprKind>>),
    Mul(Box<AstNode<ExprKind>>, Box<AstNode<ExprKind>>),
    // Comparisons
    Eq(Box<AstNode<ExprKind>>, Box<AstNode<ExprKind>>),
    Lt(Box<AstNode<ExprKind>>, Box<AstNode<ExprKind>>),
    // Constraints (core to FLUX)
    And(Box<AstNode<ExprKind>>, Box<AstNode<ExprKind>>),
    Or(Box<AstNode<ExprKind>>, Box<AstNode<ExprKind>>),
    Not(Box<AstNode<ExprKind>>),
    Implies(Box<AstNode<ExprKind>>, Box<AstNode<ExprKind>>),
    // Quantifiers (from guardc's proof module)
    ForAll(Ident, Ty, Box<AstNode<ExprKind>>),
    Exists(Ident, Ty, Box<AstNode<ExprKind>>),
    // Arrays
    ArrayIndex(Box<AstNode<ExprKind>>, Box<AstNode<ExprKind>>),
}

#[derive(Debug, Clone)]
pub enum ItemKind {
    Constraint(Ident, AstNode<ExprKind>),
    Function(Ident, Vec<(Ident, Ty)>, Ty, AstNode<ExprKind>),
    TypeAlias(Ident, Ty),
}
```

---

### 2. `fluxc_hir`: High-Level IR (Semantic Analysis)
Desugared AST with name resolution, type checking, and explicit constructs. Output of semantic analysis.
```rust
// fluxc_hir/src/lib.rs
pub mod hir;          // HIR definition
pub mod resolver;     // Name resolution (Ident → DefId)
pub mod typeck;       // Type checking
pub mod borrowck;     // Borrow checking (if applicable for FLUX)
pub mod lower;        // HIR → CIR lowering

use fluxc_ast::{Span, Ty, Ident};
use fluxc_middle::proof::ProofObligation;

// ------------------------------
// Core HIR Types
// ------------------------------
/// Unique identifier for *all* definitions (variables, functions, constraints)
/// Like Rustc's `DefId`—used for name resolution and SSA.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct DefId(pub u64);

/// HIR node wrapper: attaches type, proof obligation, and DefId
#[derive(Debug, Clone)]
pub struct HirNode<T> {
    pub kind: T,
    pub def_id: DefId,
    pub ty: Ty,
    pub proof: ProofObligation,  // Tracks formal proof for this node
    pub span: Span,
}

// ------------------------------
// HIR Kinds (Desugared)
// ------------------------------
/// HIR removes implicit constructs: e.g., `Implies(a,b)` → `Or(Not(a), b)`
#[derive(Debug, Clone)]
pub enum HirExprKind {
    LitBool(bool),
    LitInt(u64),
    LitBitVec(Vec<bool>),
    Var(DefId),  // Resolved to DefId (no more raw Ident)
    // Arithmetic (no overloading)
    Add(Box<HirNode<HirExprKind>>, Box<HirNode<HirExprKind>>),
    Sub(Box<HirNode<HirExprKind>>, Box<HirNode<HirExprKind>>),
    Mul(Box<HirNode<HirExprKind>>, Box<HirNode<HirExprKind>>),
    // Comparisons
    Eq(Box<HirNode<HirExprKind>>, Box<HirNode<HirExprKind>>),
    Lt(Box<HirNode<HirExprKind>>, Box<HirNode<HirExprKind>>),
    // Constraints (desugared)
    And(Box<HirNode<HirExprKind>>, Box<HirNode<HirExprKind>>),
    Or(Box<HirNode<HirExprKind>>, Box<HirNode<HirExprKind>>),
    Not(Box<HirNode<HirExprKind>>),
    // Quantifiers (from guardc)
    ForAll(DefId, Box<HirNode<HirExprKind>>),
    Exists(DefId, Box<HirNode<HirExprKind>>),
    // Arrays (explicit bounds checks inserted during typeck)
    ArrayIndex(Box<HirNode<HirExprKind>>, Box<HirNode<HirExprKind>>),
    ArrayUpdate(Box<HirNode<HirExprKind>>, Box<HirNode<HirExprKind>>, Box<HirNode<HirExprKind>>),
}

#[derive(Debug, Clone)]
pub enum HirItemKind {
    Constraint(DefId, HirNode<HirExprKind>),
    Function(DefId, Vec<DefId>, Ty, HirNode<HirExprKind>),
    TypeAlias(DefId, Ty),
}
```

---

### 3. `fluxc_middle`: Unified CIR (Middle-End, Proof Tracking, Optimizations)
The **core of the compiler**: merges `guardc`'s CIR and `guard2mask`'s internal IR. This is where all constraint-specific optimizations and proof tracking live.

Uses **Salsa** (Rustc's incremental query engine) for incremental compilation.
```rust
// fluxc_middle/src/lib.rs
pub mod cir;           // Unified Constraint IR (SSA form, like LLVM/MIR/CLIF)
pub mod proof;         // Proof tracking (from guardc's proof.rs)
pub mod optim;         // Constraint-specific optimization passes
pub mod query;         // Salsa query system (incremental compilation)
pub mod ty;            // Re-export of fluxc_ast::Ty (unified type system)

use fluxc_ast::{Span, Ty};
use fluxc_hir::DefId;

// ------------------------------
// Proof Tracking (Proof-Carrying Code)
// ------------------------------
/// A formal proof obligation that an IR node/transformation is correct.
/// Merges guardc's proof module with Coq integration.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ProofObligation {
    /// The node is correct by construction (e.g., literals, resolved variables)
    Axiom,
    /// The node is derived from other obligations (e.g., `AndIntro` for logical and)
    Derived {
        rule: String,  // Name of the proof rule (for Coq)
        premises: Vec<ProofObligation>,
    },
    /// A serialized Coq proof term (for formal verification of transformations)
    CoqProof(Vec<u8>),
}

/// A certificate proving the compiled output is equivalent to the source.
/// Exported with compiled binaries for proof-carrying code.
#[derive(Debug, Clone)]
pub struct ProofCertificate {
    pub source_hash: [u8; 32],  // Blake3 hash of source GUARD code
    pub transformation_proofs: Vec<ProofObligation>,  // Chain of proof for each pass
    pub final_proof: ProofObligation,  // Proof output ≡ source
}

// ------------------------------
// Unified CIR (Constraint IR)
// SSA form for optimizations, with proof tracking.
// Replaces guardc's CIR and guard2mask's internal IR.
// ------------------------------
/// Unique SSA index for CIR nodes (like LLVM's `Value*`)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct CirId(pub u64);

/// CIR node: SSA value with type, proof obligation, and source span
#[derive(Debug, Clone)]
pub struct CirNode {
    pub id: CirId,
    pub kind: CirKind,
    pub ty: Ty,
    pub proof: ProofObligation,  // Proof this node is correct
    pub span: Span,
}

/// CIR is in SSA form, with constructs specialized for constraint problems.
#[derive(Debug, Clone)]
pub enum CirKind {
    // ------------------------------
    // Constants
    // ------------------------------
    ConstBool(bool),
    ConstInt(u64),
    ConstBitVec(Vec<bool>),

    // ------------------------------
    // SSA Uses (references to other CIR nodes)
    // ------------------------------
    Use(CirId),

    // ------------------------------
    // Arithmetic/Logical (for constraints)
    // ------------------------------
    Add(CirId, CirId),
    Sub(CirId, CirId),
    Mul(CirId, CirId),
    BitAnd(CirId, CirId),
    BitOr(CirId, CirId),
    BitXor(CirId, CirId),
    BitNot(CirId),
    Shl(CirId, CirId),
    Shr(CirId, CirId),

    // ------------------------------
    // Comparisons (core to constraints)
    // ------------------------------
    Eq(CirId, CirId),
    Ne(CirId, CirId),
    Lt(CirId, CirId),
    Le(CirId, CirId),
    Gt(CirId, CirId),
    Ge(CirId, CirId),

    // ------------------------------
    // Constraint-Specific Constructs
    // ------------------------------
    And(CirId, CirId),  // Logical AND (for constraints)
    Or(CirId, CirId),   // Logical OR
    Not(CirId),          // Logical NOT
    Ite(CirId, CirId, CirId),  // If-then-else (for constraint solving)

    // ------------------------------
    // Quantifiers (for formal proofs)
    // ------------------------------
    ForAll(DefId, CirId),  // ∀ var: body
    Exists(DefId, CirId),  // ∃ var: body

    // ------------------------------
    // Arrays (for bounded constraints)
    // ------------------------------
    ArrayIndex(CirId, CirId),
    ArrayUpdate(CirId, CirId, CirId),

    // ------------------------------
    // Control Flow (for codegen)
    // ------------------------------
    Phi(Vec<(CirId, CirBlockId)>),  // SSA phi node (value, predecessor block)
    Call(CirId, Vec<CirId>),         // Function call
    Return(CirId),                    // Return value
}

/// Unique ID for CIR basic blocks
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct CirBlockId(pub u64);

/// CIR Basic Block (for control flow)
#[derive(Debug, Clone)]
pub struct CirBlock {
    pub id: CirBlockId,
    pub insts: Vec<CirNode>,
    pub terminator: CirNode,  // Must be a control flow instruction (Br, BrCond, Return)
}

/// CIR Function (top-level container for code/constraints)
#[derive(Debug, Clone)]
pub struct CirFunction {
    pub def_id: DefId,
    pub params: Vec<(DefId, Ty)>,
    pub return_ty: Ty,
    pub blocks: Vec<CirBlock>,
    pub proof: ProofObligation,  // Proof the function is correct
}

/// CIR Module (top-level container for the entire program)
#[derive(Debug, Clone)]
pub struct CirModule {
    pub functions: Vec<CirFunction>,
    pub constraints: Vec<(DefId, CirFunction)>,  // Constraints are lowered to functions
}

// ------------------------------
// Optimization Pass Trait (Composable)
// ------------------------------
/// A trait for constraint-specific optimization passes.
/// Every pass returns a *semantics-preserving proof* for the transformation.
pub trait CirPass {
    fn name(&self) -> &'static str;
    /// Run the pass on `input`, returning the transformed module and a proof
    /// that the transformation is semantics-preserving.
    fn run(&self, input: &CirModule) -> (CirModule, ProofObligation);
}

// ------------------------------
// Example Constraint-Specific Optimizations
// ------------------------------
pub struct DeadConstraintElimination;  // Remove unused constraints
pub struct ConstraintNormalization;     // Convert to canonical form (e.g., CNF)
pub struct StrengthReduction;            // Replace expensive ops with cheap ones (e.g., *2 → <<1)
pub struct ConstraintFusion;             // Merge related constraints (e.g., two bounds checks → one)
pub struct ConstantPropagation;          // Evaluate constants at compile time
pub struct CSE;                          // Common Subexpression Elimination

impl CirPass for DeadConstraintElimination {
    fn name(&self) -> &'static str { "dead-constraint-elim" }
    fn run(&self, input: &CirModule) -> (CirModule, ProofObligation) {
        // 1. Find unused constraints (no side effects, not used in output)
        // 2. Remove them
        // 3. Generate proof that removing unused constraints preserves semantics
        let transformed = input.clone();  // Placeholder
        let proof = ProofObligation::Derived {
            rule: "dead_constraint_elimination".to_string(),
            premises: vec![ProofObligation::Axiom],
        };
        (transformed, proof)
    }
}
```

---

### 4. `fluxc_lcir`: Lowered CIR (Codegen-Ready)
Target-independent but low-level IR (like LLVM's Machine IR or Cranelift's CLIF). No high-level constraint constructs—ready for code generation.
```rust
// fluxc_lcir/src/lib.rs
pub mod lcir;          // Lowered CIR definition
pub mod lower;         // CIR → L-CIR lowering
pub mod optim;         // Machine-independent optimizations (e.g., instruction selection prep)

use fluxc_ast::{Span, Ty};
use fluxc_hir::DefId;
use fluxc_middle::{CirId, ProofObligation};

// ------------------------------
// L-CIR Core Types
// ------------------------------
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct LCirId(pub u64);  // SSA index for L-CIR
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct LCirBlockId(pub u64);

/// L-CIR node: low-level, no high-level constraint constructs
#[derive(Debug, Clone)]
pub struct LCirNode {
    pub id: LCirId,
    pub kind: LCirKind,
    pub ty: Ty,
    pub proof: ProofObligation,
    pub span: Span,
}

/// L-CIR Kinds (low-level, close to machine code)
#[derive(Debug, Clone)]
pub enum LCirKind {
    // Constants
    ConstBool(bool),
    ConstInt(u64),
    ConstBitVec(Vec<bool>),
    // SSA Uses
    Use(LCirId),
    // Arithmetic/Logical (no overloading)
    Add(LCirId, LCirId),
    Sub(LCirId, LCirId),
    Mul(LCirId, LCirId),
    BitAnd(LCirId, LCirId),
    BitOr(LCirId, LCirId),
    BitXor(LCirId, LCirId),
    BitNot(LCirId),
    Shl(LCirId, LCirId),
    Shr(LCirId, LCirId),
    // Comparisons
    Eq(LCirId, LCirId),
    Ne(LCirId, LCirId),
    Lt(LCirId, LCirId),
    Le(LCirId, LCirId),
    Gt(LCirId, LCirId),
    Ge(LCirId, LCirId),
    // Logical (no quantifiers, no Ite unless needed)
    And(LCirId, LCirId),
    Or(LCirId, LCirId),
    Not(LCirId),
    // Arrays (lowered to pointer ops for native targets)
    ArrayIndex(LCirId, LCirId),
    ArrayUpdate(LCirId, LCirId, LCirId),
    // Control Flow (explicit blocks)
    Phi(Vec<(LCirId, LCirBlockId)>),
    Call(LCirId, Vec<LCirId>),
    Return(LCirId),
    Br(LCirBlockId),  // Unconditional branch
    BrCond(LCirId, LCirBlockId, LCirBlockId),  // Conditional branch
}

/// L-CIR Basic Block
#[derive(Debug, Clone)]
pub struct LCirBlock {
    pub id: LCirBlockId,
    pub insts: Vec<LCirNode>,
    pub terminator: LCirNode,
}

/// L-CIR Function
#[derive(Debug, Clone)]
pub struct LCirFunction {
    pub def_id: DefId,
    pub params: Vec<(DefId, Ty)>,
    pub return_ty: Ty,
    pub blocks: Vec<LCirBlock>,
    pub proof: ProofObligation,
}

/// L-CIR Module
#[derive(Debug, Clone)]
pub struct LCirModule {
    pub functions: Vec<LCirFunction>,
    pub constraints: Vec<(DefId, LCirFunction)>,
}
```

---

### 5. `fluxc_codegen`: Composable Backends
Replaces *all* existing backends (guard2mask's bytecode, guardc's native, Python's LLVM/eBPF/WAT). Uses a trait for composability.
```rust
// fluxc_codegen/src/lib.rs
pub mod backend;       // Backend trait
pub mod flux_bytecode; // FLUX VM bytecode (from guard2mask's compiler.rs)
pub mod cranelift;     // Fast native code (from guardc's codegen.rs, using Cranelift)
pub mod llvm;          // LLVM IR (from flux_llvm_backend.py, using `inkwell` crate)
pub mod riscv;         // RISC-V assembly
pub mod ebpf;          // eBPF C (from flux_llvm_backend.py)
pub mod wat;           // WebAssembly Text (WAT)

use fluxc_lcir::LCirModule;
use fluxc_middle::ProofCertificate;

// ------------------------------
// Backend Trait (Composable)
// ------------------------------
pub trait Backend {
    /// Name of the backend (for debugging)
    fn name(&self) -> &'static str;
    /// Target triple (e.g., "x86_64-unknown-linux-gnu", "bpf")
    fn target_triple(&self) -> &'static str;
    /// Compile L-CIR to target output, returning the binary and proof certificate.
    fn compile(&self, module: &LCirModule) -> Result<(Vec<u8>, ProofCertificate), CodegenError>;
}

#[derive(Debug, Clone)]
pub enum CodegenError {
    UnsupportedOperation(String),
    TypeMismatch(String),
    TargetSpecific(String),
}

// ------------------------------
// Example: FLUX Bytecode Backend (from guard2mask)
// ------------------------------
pub struct FluxBytecodeBackend;

impl Backend for FluxBytecodeBackend {
    fn name(&self) -> &'static str { "flux-bytecode" }
    fn target_triple(&self) -> &'static str { "flux-vm" }

    fn compile(&self, module: &LCirModule) -> Result<(Vec<u8>, ProofCertificate), CodegenError> {
        // 1. Lower L-CIR to FLUX bytecode instructions (from guard2mask's compiler.rs)
        // 2. Serialize bytecode to Vec<u8>
        // 3. Generate proof certificate (proves bytecode ≡ L-CIR)
        let bytecode = vec![]; // Placeholder
        let cert = ProofCertificate {
            source_hash: [0u8; 32],
            transformation_proofs: vec![],
            final_proof: fluxc_middle::ProofObligation::Axiom,
        };
        Ok((bytecode, cert))
    }
}
```

---

### 6. `fluxc_driver`: Compiler Pipeline Orchestrator
Ties all modules together, handles configuration, incremental compilation, and session state.
```rust
// fluxc_driver/src/lib.rs
pub mod driver;        // Main pipeline
pub mod config;        // Compiler config (opt level, target, etc.)
pub mod session;       // Session state (diagnostics, query context)

use fluxc_ast::{parser::Parser, Diagnostic, Span};
use fluxc_hir::{resolver::Resolver, typeck::TypeChecker, lower