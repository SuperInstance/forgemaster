# Unified FLUX Intermediate Representation (FLUX-IR)
## Core Design Principles
FLUX-IR is a **two-tier, SSA-based, target-agnostic IR** inspired by Rustc's HIR→MIR→LLVM pipeline, GCC's tree-SSA/RTL, and Cranelift's CLIF. It unifies the work of all existing FLUX compilers, supports constraint-specific optimizations, carries formal proof obligations, and enables incremental compilation.

---

## 1. FLUX-IR Type System
Typed to support both primitive hardware types and first-class constraint predicates:
```rust
// Target-agnostic primitive types (map directly to hardware)
enum PrimitiveType {
    Int(u32, bool), // (width, signed): e.g. Int(32, true) = i32
    Float(u32),     // width: e.g. Float(64) = f64
    Bool,           // 1-bit predicate result
    Pointer(Box<FluxType>), // Memory pointer
    Opaque(String),  // User-defined custom type
}

// First-class constraint predicate types (high-level, target-agnostic)
enum ConstraintPredicateType {
    Range(Box<FluxType>),       // Value ∈ [min, max]
    Domain(Box<FluxType>, DomainSet), // Value ∈ discrete/continuous set
    Temporal(Box<FluxType>, TimeInterval), // Predicate holds over time window
    Security(Box<FluxType>, SecurityLabel), // Value flows within security domain
    And(Box<FluxType>, Box<FluxType>), // Logical AND of two predicates
    Or(Box<FluxType>, Box<FluxType>),  // Logical OR of two predicates
    Not(Box<FluxType>),               // Logical negation of a predicate
}

// Unified FLUX type enum
enum FluxType {
    Primitive(PrimitiveType),
    Constraint(ConstraintPredicateType),
    PredicateResult, // Low-level boolean result for lowered constraints
}

// Supporting types for constraints
enum DomainSet {
    Discrete(Vec<ConstantValue>), // e.g. {1, 3, 5}
    Interval(ConstantValue, ConstantValue), // e.g. [0, 100]
    AllExcept(Vec<ConstantValue>),
}
type TimeInterval = (Option<ConstantValue>, Option<ConstantValue>); // (start, end)
type SecurityLabel = String; // e.g. "public", "secret"
```

---

## 2. FLUX-IR Node Types
All nodes have a unique stable `NodeId` for incremental compilation, proof linking, and source mapping. We split nodes into two tiers for a clean separation of concerns:

### 2.1 High-Level Constraint IR (HL-CIR)
Directly represents user-written GUARD constraints, with no target-specific lowering. This is where constraint-specific optimizations run first.
```rust
#[derive(Clone, Copy, PartialEq, Eq, Hash)]
struct NodeId(u64);

struct SourceLocation {
    file: PathBuf,
    line: u32,
    col: u32,
}

// Base trait for all IR nodes
trait IrNode {
    fn id(&self) -> NodeId;
    fn ty(&self) -> FluxType;
    fn location(&self) -> SourceLocation;
}

// High-level range constraint: value ∈ [min, max]
struct RangeConstraint {
    id: NodeId,
    ty: FluxType,
    value: NodeId, // SSA value to validate
    min: ConstantValue,
    max: ConstantValue,
    proof: Option<NodeId>, // Link to formal correctness proof
}

// High-level domain constraint: value ∈ discrete/continuous set
struct DomainConstraint {
    id: NodeId,
    ty: FluxType,
    value: NodeId,
    domain: DomainSet,
    proof: Option<NodeId>,
}

// High-level temporal constraint: predicate holds over a time window
struct TemporalConstraint {
    id: NodeId,
    ty: FluxType,
    value: NodeId,
    time_var: NodeId, // Time tracking variable (e.g. f64 seconds)
    interval: TimeInterval,
    predicate: NodeId, // Sub-predicate on (value, time)
    proof: Option<NodeId>,
}

// High-level security constraint: value flows only within a security domain
struct SecurityConstraint {
    id: NodeId,
    ty: FluxType,
    value: NodeId,
    label: SecurityLabel,
    proof: Option<NodeId>,
}

// Logical combinators for combining constraints
struct AndConstraint {
    id: NodeId,
    ty: FluxType,
    left: NodeId,
    right: NodeId,
    proof: Option<NodeId>,
}

struct OrConstraint {
    id: NodeId,
    ty: FluxType,
    left: NodeId,
    right: NodeId,
    proof: Option<NodeId>,
}

struct NotConstraint {
    id: NodeId,
    ty: FluxType,
    operand: NodeId,
    proof: Option<NodeId>,
}
```

### 2.2 Low-Level Target-Agnostic IR (LL-CIR)
Lowered SSA representation of HL-CIR, identical in structure to LLVM IR for easy cross-compilation to all supported targets:
```rust
// Constant SSA value
struct Constant {
    id: NodeId,
    ty: FluxType,
    value: ConstantValue, // e.g. IntConst(42), FloatConst(99.5)
}

// Function argument
struct Argument {
    id: NodeId,
    ty: FluxType,
    name: String,
}

// Low-level SSA instructions
enum Instruction {
    // Arithmetic
    Add(NodeId, NodeId),
    Sub(NodeId, NodeId),
    Mul(NodeId, NodeId),
    // Comparisons (used to lower HL-CIR constraints)
    Eq(NodeId, NodeId),
    Ne(NodeId, NodeId),
    Lt(NodeId, NodeId, bool), // signed?
    Le(NodeId, NodeId, bool),
    Gt(NodeId, NodeId, bool),
    Ge(NodeId, NodeId, bool),
    // Logical
    And(NodeId, NodeId),
    Or(NodeId, NodeId),
    Not(NodeId),
    // Casts
    IntToPtr(NodeId, Box<FluxType>),
    PtrToInt(NodeId, Box<FluxType>),
    // Memory
    Load(NodeId),
    Store(NodeId, NodeId),
    // Control flow
    Phi(Vec<(NodeId, BasicBlockId)>),
}

// Basic block: sequence of instructions with a terminator
struct BasicBlock {
    id: BasicBlockId,
    name: String,
    instructions: Vec<Instruction>,
    terminator: Terminator,
}

// Terminator nodes: end of a basic block
enum Terminator {
    Ret(NodeId),
    Br(BasicBlockId),
    CondBr(NodeId, BasicBlockId, BasicBlockId),
    Unreachable,
}

// Top-level module container (unifies all FLUX-IR content)
struct FluxModule {
    module_id: Uuid, // Unique ID for incremental caching
    source_files: HashMap<PathBuf, SourceMap>, // Source location mappings
    types: HashMap<String, FluxType>, // Registered type registry
    global_constraints: Vec<NodeId>, // Top-level user constraints
    functions: Vec<FluxFunction>, // Validation helper functions
    proof_obligations: HashMap<NodeId, ProofLink>, // Node → formal proof link
    metadata: HashMap<String, String>, // Compilation metadata
}
```

---

## 3. Optimization Pass Ordering
Optimizations run in two phases: first on HL-CIR for constraint-specific improvements, then on LL-CIR for standard compiler optimizations:
1.  **Frontend Lowering**: Merge `guard2mask` and `guardc` into a single Rust parser that emits FLUX-IR directly, eliminating duplicated parsing logic.
2.  **High-Level Constraint Optimizations**:
    1.  **Constraint Normalization**: Convert all constraints to conjunctive/disjunctive normal form for easier analysis.
    2.  **Constraint Fusion**: Merge overlapping constraints (e.g. `temp ∈ [0,50] AND temp ∈ [25,100]` → `temp ∈ [25,50]`).
    3.  **Dead Constraint Elimination**: Remove unused or tautological constraints.
3.  **Proof Obligation Update**: Link optimized constraint nodes to their formal correctness proofs.
4.  **HL-CIR → LL-CIR Lowering**: Convert high-level constraint nodes to low-level SSA instructions.
5.  **Low-Level Target-Agnostic Optimizations**:
    1.  **Dead Instruction Elimination**
    2.  **Strength Reduction**: Replace expensive ops with cheaper equivalents (e.g. `x*2` → `x+x`).
    3.  **Vectorization**: Pack multiple constraint checks into vector AVX-512/WASM SIMD instructions.
    4.  **Common Subexpression Elimination**
6.  **Target-Specific Codegen**: Lower LL-CIR to x86-64, Wasm, eBPF, RISC-V, or CUDA using the unified backend.
7.  **Incremental Compilation Tracking**: Update node hashes to track changes for future compilations.

---

## 4. Serialization Format
FLUX-IR supports two serializable formats for different use cases:
### 4.1 Text Format (`.fluxir`)
Human-readable, identical to LLVM's `.ll` format, for debugging and manual inspection:
```fluxir
; FLUX-IR Text Format Example for: temp ∈ [0,100] AND pressure ∈ [900,1100]
source_files = ["/home/user/constraints.guard"]
source_map = {
  0: ("/home/user/constraints.guard", 1:1-1:20),
  1: ("/home/user/constraints.guard", 1:25-1:45)
}

; Type Registry
%i32 = Int(32, true)
%range_temp = RangePredicate(%i32)
%range_pressure = RangePredicate(%i32)
%combined_constraint = AndPredicate(%range_temp, %range_pressure)

; Top-level constraint function
define @validate_sensors() -> %combined_constraint {
entry:
  %temp = Argument(%i32, "temp")
  %pressure = Argument(%i32, "pressure")
  
  ; High-level range constraints
  %temp_ok = RangeConstraint %temp, 0, 100, !proof "coq:temp_range#123"
  %pressure_ok = RangeConstraint %pressure, 900, 1100, !proof "coq:press_range#456"
  
  ; Combined constraint
  %final = AndConstraint %temp_ok, %pressure_ok
  Ret %final
}

; Formal proof links
!proof "coq:temp_range#123" = CoqTheorem("sensor_constraints.v", "temp_valid")
!proof "coq:press_range#456" = CoqTheorem("sensor_constraints.v", "press_valid")
```

### 4.2 Binary Format (`.fluxirc`)
Compact, hashable format for incremental caching and production use, using Protocol Buffers for cross-language compatibility. It includes:
- Module header with unique `module_id`
- Serialized IR nodes with their hashes
- Source map entries
- Proof obligation links
- Compilation metadata

---

## 5. Example IR for the Sample Constraints
### 5.1 HL-CIR Version (Direct User Constraint Representation)
```rust
let temp_arg = Argument { id: NodeId(0), ty: FluxType::Primitive(PrimitiveType::Int(32, true)), name: "temp".into() };
let pressure_arg = Argument { id: NodeId(1), ty: FluxType::Primitive(PrimitiveType::Int(32, true)), name: "pressure".into() };

let temp_range = RangeConstraint {
    id: NodeId(2),
    ty: FluxType::Constraint(ConstraintPredicateType::Range(Box::new(FluxType::Primitive(PrimitiveType::Int(32, true))))),
    value: NodeId(0),
    min: ConstantValue::IntConst(0),
    max: ConstantValue::IntConst(100),
    proof: Some(NodeId(100)),
};

let pressure_range = RangeConstraint {
    id: NodeId(3),
    ty: FluxType::Constraint(ConstraintPredicateType::Range(Box::new(FluxType::Primitive(PrimitiveType::Int(32, true))))),
    value: NodeId(1),
    min: ConstantValue::IntConst(900),
    max: ConstantValue::IntConst(1100),
    proof: Some(NodeId(101)),
};

let combined = AndConstraint {
    id: NodeId(4),
    ty: FluxType::Constraint(ConstraintPredicateType::And(Box::new(temp_range.ty), Box::new(pressure_range.ty))),
    left: NodeId(2),
    right: NodeId(3),
    proof: Some(NodeId(102)),
};
```

### 5.2 LL-CIR Version (Lowered for Target Codegen)
```rust
// Lowered to low-level SSA instructions
let temp_ok = Instruction::And(
    Instruction::Ge(NodeId(0), NodeId(5), true), // temp >= 0
    Instruction::Le(NodeId(0), NodeId(6), true), // temp <= 100
);
let pressure_ok = Instruction::And(
    Instruction::Ge(NodeId(1), NodeId(7), true), // pressure >=900
    Instruction::Le(NodeId(1), NodeId(8), true), // pressure <=1100
);
let final_ok = Instruction::And(NodeId(9), NodeId(10));
```

---

## 6. Alignment with Research Questions
### Key Answers Tied to FLUX-IR:
1.  **Unified IR Design**: Covered above, with two-tier SSA structure, support for all constraint types, and target independence.
2.  **Merge `guard2mask` and `guardc`**: Yes! Merge them into a single Rust frontend that emits FLUX-IR directly, eliminating duplicated parsing logic.
3.  **Constraint-Specific Optimizations**: Covered in the pass ordering (normalization, fusion, dead elimination, vectorization).
4.  **Incremental Compilation**: Enabled by unique `NodeId`s, per-node hashes, and the modular `FluxModule` structure.
5.  **LSP Support**: FLUX-IR's source maps and node locations enable intellisense, error highlighting, and go-to-definition for GUARD files.
6.  **Proof-Carrying Code**: The `proof_obligations` HashMap links each IR node to its formal Coq/Isabelle proof, ensuring compiled code matches verified constraints.
7.  **Error Recovery**: Use panic-recover parsing to skip invalid constraints and continue compiling the rest of the file, with source maps pointing to exact error locations.
8.  **Differential Testing**: Use FLUX-IR as a single source of truth to test all backends, compare outputs across compilers, and fuzz test the constraint parser.
9.  **Bootstrapping**: Long-term goal: first build a stable Rust-based FLUX compiler, then rewrite the frontend in GUARD itself to bootstrap the compiler.
10. **Production Path**:
    1.  Phase 1: Merge frontends, add error recovery and source maps
    2.  Phase 2: Replace Python backends with Rust FLUX-IR consumers
    3.  Phase 3: Add formal proof integration and LSP support
    4.  Phase 4: Optimize for speed and vectorization
    5.  Phase 5: Bootstrap and release production-grade tooling