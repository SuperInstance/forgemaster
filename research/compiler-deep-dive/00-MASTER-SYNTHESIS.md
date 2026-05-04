## 1. Executive Summary (3 sentences)
The `flux-compiler` will become a unified, Rust-based production-grade constraint compiler that merges `guard2mask` and `guardc` into a single pipeline, centered on a tiered SSA-based Intermediate Representation (FLUX-IR) that natively encodes constraint predicates and formal proof obligations. It will prioritize safety via proof-carrying code that tracks constraint check sites through every compilation stage, developer experience via a first-class LSP server and tooling, and speed via constraint-specific optimizations and fine-grained incremental compilation with hot-reload for constraint logic. It will not be self-hosted (bootstrapped) due to the limited expressiveness of FLUX’s GUARD precondition construct, instead targeting backends including eBPF, RISC-V, WASM, and LLVM for embedded, high-assurance, and cloud use cases.

---

## 2. Unified IR Design (The Consensus)
All reports align on a 4-tier, SSA-based FLUX-IR with strict separation of concerns, designed to unify `guard2mask` and `guardc`’s competing IRs:
1. **Tier Structure (Aligned Across All Reports)**:
   - `HL-CIR/HL-AST`: Retains exact source syntax/spans, directly encodes unlowered user GUARD constraints, for LSP diagnostics and early optimizations.
   - `Unified ML-IR/CIR`: Single source of truth for middle-end logic, SSA-based, with cross-constraint dependency tracking and proof links.
   - `Optimized ML-IR`: Post-optimization IR, cached per pass version for incremental builds.
   - `LL-IR/L-CIR`: Target-agnostic lowered IR, codegen-ready, compatible with LLVM/Cranelift backends.
2. **Core Type System**: Unified `FluxType` with two native categories:
   - Primitive hardware types (int, float, bool, pointer, opaque) mapping directly to target ISAs.
   - First-class constraint predicate types (range, domain, temporal, security, logical combinators) as IR citizens, not annotations.
3. **Shared Metadata**: All nodes have a stable unique `NodeId` (for incremental/proof/source tracking), source span, optional proof link, and SHA-256 content hash cache key (for change detection).

---

## 3. Merge Strategy (The Decision)
The merge path prioritizes reusing the strongest existing components while eliminating duplication:
1. **Workspace Architecture**: Adopt the 9-crate Rust workspace from the merge report: `fluxc_parser`, `fluxc_ast`, `fluxc_hir`, `fluxc_middle` (unified CIR/proof tracking), `fluxc_lcir`, `fluxc_codegen` (backends), `fluxc_driver`, `fluxc_lsp`, `fluxc_test`.
2. **Frontend Unification**: Retire both existing parsers, adopt `guard2mask`’s hand-written recursive descent parser for superior error recovery, LSP span tracking, and error collection; resolve semantic mismatches (e.g., `constraint x = y` as binding vs equality) via a unified AST in `fluxc_ast`.
3. **IR Unification**: Retire `guardc`’s legacy `cir.rs`/`lcir.rs`, replacing them with the unified FLUX-IR; `fluxc_middle`’s CIR becomes the single source of truth for all middle-end logic.
4. **Pass/Backend Unification**: Use trait-based interfaces for optimizations and backends to unify `guard2mask`’s mask generation and `guardc`’s codegen, supporting all original targets (eBPF, RISC-V, WASM, LLVM).

---

## 4. Optimization Pipeline (Ordered)
Passes are ordered to run early on high-level constraint IR (to prune redundancy first) before general middle-end passes, per the constraint optimization report:
1. **Early Constraint-Specific Passes (Unoptimized ML-IR, Target-Agnostic)**:
   1. Interval Arithmetic Simplification (4-step: AC-3 interval consistency, interval merging, expression folding, conditional pruning)
   2. Domain Set Simplification
   3. Temporal Constraint Fusing
   4. Security Constraint Lifting
   5. Logical Constraint Normalization
   6. Redundant Constraint Elimination
2. **Standard Middle-End Passes (Optimized ML-IR, Target-Agnostic)**:
   1. Normal Form Conversion
   2. Constraint Fusion
   3. Optimal Check Selection
   4. Dead Constraint Elimination
   5. Strength Reduction
   6. SIMD Vectorization
   7. Pipeline Correctness Validation
3. **Late Target-Specific Passes (LL-IR, Target-Aware)**:
   1. Target Intrinsic Lowering
   2. Check Scheduling

---

## 5. Proof-Carrying Code (The Architecture)
Proofs thread through every pipeline stage per the PCC report, with correctness defined as: *every source constraint maps to a verified check site in the binary calling a certified runtime function*:
1. **Obligation Flow**:
   - **Frontend**: Assign unique `ConstraintId` (tied to IR `NodeId`) to every GUARD constraint; defer proof generation (trusted frontend).
   - **ML-IR Generation**: Generate high-level proof obligations `Op(c)` (e.g., `RangeCheck(var, lo, hi)`) linked to each constraint’s `NodeId`.
   - **Optimizations**: Update the obligation mapping for all transformations: track check site movement for scheduling, map fused constraints to a single check site, and attach static dominance justifications for any removed checks.
   - **Lowering/Codegen**: Translate `Op(c)` to target-specific check sites; adjust addresses during linking to reflect final binary offsets.
2. **Proof Certificate**: Compact binary format with a magic header, target ID, and entries per constraint: truncated SHA-256 hash of the canonical constraint string, final binary check site address, target pattern ID, and check arguments.
3. **Trusted Base**: Target-specific pattern tables (<100 entries per target) and certified runtime checks, verified separately from the compiler.

---

## 6. Developer Experience (What to Build, Prioritized)
DX tooling is prioritized by user impact per the LSP report:
1. **Highest Priority: LSP Server (`fluxc_lsp`)**: Core features first: real-time parse/type/constraint diagnostics, semantic highlighting, go-to-definition, find-references, and hover tooltips showing constraint semantics and proof status.
2. **Second Priority: Formatter (`guardfmt`)**: Integrated with the LSP, supporting standardize formatting, format-on-save, and range formatting.
3. **Third Priority: Linter (`guardlint`)**: Built on the unified CIR, with rule-based checks for common constraint anti-patterns (redundant bounds, unprovable constraints) integrated with LSP diagnostics.
4. **Lowest Priority: Advanced LSP Features**: Inlay hints, auto-completion for struct fields/constraint predicates, deferred to post-alpha releases.

---

## 7. Incremental Compilation (The Design)
Constraint hot-reload is built on a dependency DAG and content-hashed caching per the incremental compilation report:
1. **Dependency Tracking**: Directed acyclic graph (DAG) of all compilation artifacts, with nodes for: GUARD source files (roots), HL-CIR, ML-IR, Optimized ML-IR, LL-IR, and target artifacts; each node tracks transitive dependencies.
2. **Change Detection**: Classify edits to minimize recompilation:
   - Trivial edits (whitespace/comments): No IR regeneration, only update source spans.
   - Non-semantic syntactic edits (local variable renames): Only regenerate local IR nodes.
   - Semantic edits (constraint bound modifications): Mark all dependent DAG nodes as dirty.
3. **Caching**: Every DAG node has a SHA-256 cache key (content hash + dependent layer keys) for fast reuse of clean artifacts.
4. **Hot-Reload Workflow**: Detect edits, recompile only dirty nodes, update the proof certificate, and apply in-place memory updates (for eBPF/ targets supporting dynamic linking) without restarting the running application.

---

## 8. Bootstrapping (The Verdict)
**Do NOT bootstrap the FLUX compiler**. The bootstrapping report’s definitive conclusion is based on three unassailable points:
1. **GUARD’s Limited Expressiveness**: FLUX’s GUARD construct is restricted to static first-order precondition checks, and cannot support dynamic state transitions (e.g., stack-based parsing) or iterative fixed-point computation (e.g., constant folding) required to build a compiler.
2. **No Practical Benefit**: FLUX’s core value is constraint validation for high-assurance/embedded use cases, not general-purpose programming; self-hosting adds unnecessary complexity without improving its target use cases.
3. **Meta-Constraint Checker Alternative**: A meta-checker (verifying FLUX constraint validity) can be implemented in Rust, avoiding bootstrapping while retaining a closed verification loop for constraints.

---

## 9. Production Roadmap (8 Weeks)
Aligned with the DeepSeek roadmap, updated to reflect synthesis decisions:
### Week 1: Parser Unification
- Deliverables: Unified `fluxc_parser` (hand-written RD parser, error recovery ≥3 errors), retire legacy parsers, merged test suite (27 regression tests + fuzz/round-trip tests).
- Success Criterion: Parser passes all tests, deterministic, error recovery meets requirements.

### Week 2: FLUX-IR Definition
- Deliverables: `fluxc_ir` crate with 4-tier SSA IR, stable `NodeId`, proof links, content hashing; retire `guardc`’s legacy CIR/LCIR; 50+ IR well-formedness tests.
- Success Criterion: IR encodes all existing `guard2mask`/`guardc` constraint types.

### Week 3: Workspace & Merge Completion
- Deliverables: Full 9-crate workspace, unified pipeline (AST→HIR→ML-IR→LL-IR→Target), trait-based passes/backends, differential test suite comparing new pipeline to legacy compilers.
- Success Criterion: Unified pipeline produces functionally equivalent output to both legacy compilers.

### Week 4: Constraint Optimization Passes
- Deliverables: 6 constraint-specific + 7 standard passes, pass version tracking for caching, correctness/performance benchmarks.
- Success Criterion: All passes are correctness-preserving, ≥20% binary size reduction for constraint-heavy tests.

### Week 5: Proof-Carrying Code Pipeline
- Deliverables: Obligation tracking through all stages, proof certificate serialization, trusted checker for x86/WASM/eBPF, end-to-end proof tests.
- Success Criterion: All test binaries have valid certificates, checker rejects tampered binaries.

### Week 6: LSP & DX Tooling
- Deliverables: `fluxc_lsp` (core features), `guardfmt`, `guardlint` (10+ core rules), VS Code integration tests.
- Success Criterion: LSP works with VS Code, formatter is idempotent, linter detects common anti-patterns.

### Week 7: Incremental Compilation & Hot-Reload
- Deliverables: Dependency DAG, change detection, caching, eBPF hot-swap support, incremental build tests.
- Success Criterion: Incremental builds ≥5x faster than full builds, hot-reload works for eBPF targets.

### Week 8: Hardening & Alpha Release
- Deliverables: Fuzz testing of all core components, user/developer documentation, alpha release of `fluxc` + tooling.
- Success Criterion: No critical bugs found in 24h of fuzzing, documentation covers all core use cases.

---

## 10. The Forgemaster's Verdict
### What’s Easy (Low Risk, High Predictability):
Parser unification, workspace setup, and LSP/DX tooling are straightforward: Rust’s LSP ecosystem is mature, `guard2mask`’s parser is proven, and trait-based pass/backend interfaces are a standard Rust pattern. Merging test suites and retiring duplicate code reduces, rather than adds, complexity.

### What’s Hard (High Risk, Uncertainty):
1. **GUARD Semantic Alignment**: `guard2mask` and `guardc` have competing semantic models (e.g., `constraint x = y` as binding vs equality) that require consensus on GUARD’s formal rules, not just engineering work.
2. **PCC for Optimizations**: Tracking proof obligations through check fusion, removal, and scheduling is non-trivial; justifying every check removal (required for high-assurance use cases) adds significant complexity, and verifying the PCC checker itself is a high-effort task.
3. **Embedded Hot-Reload**: eBPF hot-swap is mature, but hot-reload for RISC-V embedded targets requires custom runtime support and carries safety risk if untested.

### What’s Most Valuable (Highest ROI):
1. **Unified FLUX-IR**: The single source of truth enabling all other features, eliminating the maintenance cost of two separate IRs.
2. **Constraint-Specific Optimizations**: Immediate value for FLUX’s core use cases, reducing binary size and improving performance for embedded/high-assurance systems.
3. **Proof-Carrying Code**: FLUX’s unique differentiator, enabling use in regulated domains (DO-254 aerospace, medical devices) where formal verification is a hard requirement.

### Final Call:
The unification is feasible in 8 weeks, with semantic alignment and PCC implementation as the highest-risk gating items. Prioritize FLUX-IR, constraint optimizations, and PCC first (the irreplaceable core of `flux-compiler`), deferring low-priority DX features to post-alpha releases.