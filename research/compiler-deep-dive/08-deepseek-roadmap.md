# FLUX Compiler Unification: Production Roadmap

## Executive Summary

This is a 8-week unification project with high technical risk. The core challenge isn't writing code—it's **architectural convergence** of four independently-designed systems. The Python compilers will be rewritten in Rust for performance. The formal verification pipeline is the hardest part and may slip.

**Critical insight**: The existing compilers have different *semantic models* of GUARD, not just different implementations. Unifying the parser is 30% engineering and 70% consensus-building on what GUARD actually means.

---

## Phase 0 (Week 1): Parser Unification

### What Changes
- **New module**: `flux_parser/` — single recursive descent parser with error recovery
- **Files removed**: `guard2mask/src/parser.rs`, `guardc/src/parser.rs`
- **Files modified**: Both existing compilers to use new parser crate
- **New file**: `flux_parser/src/error.rs` — error recovery strategy (panic on first error → collect up to 5 errors)
- **New file**: `flux_parser/src/syntax.rs` — unified AST types

### Tests Added
- **Parser fuzz test**: 10,000 randomly generated GUARD fragments
- **Error recovery test**: Malformed inputs that should produce 3-5 errors
- **Round-trip test**: Parse → pretty-print → parse → compare ASTs
- **Regression suite**: All 27 existing tests from both compilers

### Success Criterion
- Single parser passes all existing tests from both compilers
- Error recovery produces ≥3 errors before aborting on malformed input
- Parser is deterministic (same input → same AST every time)

### Risks
- **HIGH**: Semantic differences between the two parsers. guard2mask treats `constraint x = y` as a binding; guardc treats it as an equality constraint. These are *different semantics* that need resolution.
- **MEDIUM**: Error recovery for constraint DSLs is poorly studied. Expect 2-3 iterations to get right.
- **LOW**: Performance — Rust recursive descent is fast enough.

### Dependencies
- None (starting point)

---

## Phase 1 (Week 2): FLUX-IR Definition

### What Changes
- **New module**: `flux_ir/` — the unified intermediate representation
- **New file**: `flux_ir/src/ir.rs` — core IR types (inspired by MLIR's SSA + regions)
- **New file**: `flux_ir/src/verify.rs` — IR well-formedness checker
- **New file**: `flux_ir/src/print.rs` — IR printer (debug format)
- **Files removed**: `guardc/src/cir.rs`, `guardc/src/lcir.rs`
- **Files modified**: `guardc/src/codegen.rs` → now targets FLUX-IR instead of CIR

### FLUX-IR Design (Key Decisions)
- **SSA form** with basic blocks (like LLVM, not like CIR's expression trees)
- **Region-based** for constraint scopes (like MLIR)
- **Operations**: `constrain`, `assert`, `forall`, `exists`, `let`, `apply`
- **Types**: `Constraint`, `BoolExpr`, `IntExpr`, `Var`, `Domain`
- **No phi nodes** — use MLIR-style block arguments instead (simpler for constraints)

### Tests Added
- **IR well-formedness tests**: 50+ test IRs, some valid, some invalid
- **IR round-trip test**: Parse → lower to IR → print → parse → compare
- **Semantic preservation test**: 10 hand-written GUARD programs, verify IR semantics match

### Success Criterion
- All existing guardc tests pass through new IR
- IR well-formedness checker catches all invalid IRs in test suite
- IR can represent all constructs from both compilers

### Risks
- **HIGH**: IR design is the most consequential decision. Wrong abstraction level means rewriting backends later. The constraint DSL needs operations that don't exist in standard IRs (quantifiers, domain constraints).
- **MEDIUM**: Block arguments vs phi nodes is a religious debate. Pick one and commit.
- **LOW**: Performance of IR construction.

### Dependencies
- Phase 0 (parser must exist to produce ASTs that lower to IR)

---

## Phase 2 (Week 3): Optimization Passes

### What Changes
- **New module**: `flux_opt/` — optimization pass infrastructure
- **New file**: `flux_opt/src/passes/mod.rs` — pass manager
- **New files**: Individual passes:
  - `normalize.rs` — constraint normalization (conjunctive normal form)
  - `dead_elim.rs` — dead constraint elimination
  - `strength_reduce.rs` — strength reduction (replace expensive constraints with cheaper ones)
  - `fusion.rs` — constraint fusion (merge adjacent compatible constraints)
  - `vectorize.rs` — vectorization (SIMD-friendly constraint batches)
  - `inline.rs` — constraint inlining
- **New file**: `flux_opt/src/analysis.rs` — dataflow analysis framework

### Tests Added
- **Pass correctness tests**: For each pass, 10-20 test cases showing before/after IR
- **Pass composition test**: Run all passes in sequence, verify no crashes
- **Performance regression test**: Measure optimization time on 1000-constraint input
- **Semantic preservation test**: Optimized IR must produce same results as unoptimized

### Success Criterion
- All passes produce valid IR (passes well-formedness checker)
- Dead elimination removes at least 80% of trivially dead constraints
- No pass takes >2x the input IR size in memory
- Pass pipeline is deterministic

### Risks
- **HIGH**: Constraint fusion and vectorization are research-level problems. The "fusion" pass may need to be heuristic rather than optimal. Vectorization for constraint DSLs is unexplored territory.
- **MEDIUM**: Pass ordering matters. Expect to discover ordering constraints during testing.
- **LOW**: Dead elimination and normalization are well-understood.

### Dependencies
- Phase 1 (IR must exist to transform)

---

## Phase 3 (Week 4): Backend Implementation

### What Changes
- **New module**: `flux_backend/` — backend infrastructure
- **New files**: Individual backends:
  - `flux_backend/src/llvm.rs` — LLVM IR codegen (replaces `flux_llvm_backend.py`)
  - `flux_backend/src/ebpf.rs` — eBPF codegen (replaces `flux_ebpf_deploy.py`)
  - `flux_backend/src/c.rs` — C codegen (replaces `fluxc.py` C target)
  - `flux_backend/src/fortran.rs` — Fortran codegen (replaces `fluxc.py` Fortran target)
  - `flux_backend/src/asm.rs` — Assembly codegen (replaces `fluxc.py` assembly target)
  - `flux_backend/src/bytecode.rs` — FLUX bytecode (replaces `guard2mask`)
- **New file**: `flux_backend/src/register_alloc.rs` — register allocation for assembly backend
- **Files removed**: `fluxc.py`, `flux_llvm_backend.py`, `flux_ebpf_deploy.py`, `guard2mask/src/codegen.rs`

### Tests Added
- **Backend correctness tests**: For each backend, 20+ GUARD programs compiled and run
- **Cross-backend equivalence test**: Same GUARD program compiled to all backends, outputs compared
- **Performance benchmark**: Compilation time and output quality for each backend
- **Edge case tests**: Empty constraints, single constraint, deeply nested constraints

### Success Criterion
- All backends produce correct output for all existing test cases
- Rust backends are ≥50x faster than Python equivalents (target: 100x)
- LLVM backend produces valid LLVM IR that compiles with `llc`
- eBPF backend produces bytecode that passes kernel verifier

### Risks
- **HIGH**: Fortran backend is niche and may have low ROI. Consider deprecating.
- **MEDIUM**: Assembly backend requires register allocation, which is a significant engineering effort. Consider using LLVM as a middle-end for assembly targets.
- **MEDIUM**: eBPF verifier is extremely strict. Many valid GUARD programs may not compile to eBPF.
- **LOW**: LLVM and C backends are well-understood.

### Dependencies
- Phase 2 (optimized IR → better backend output)
- Phase 1 (IR must be stable)

---

## Phase 4 (Week 5): Proof-Carrying Code Integration

### What Changes
- **New module**: `flux_proof/` — proof infrastructure
- **New file**: `flux_proof/src/coq_bridge.rs` — Coq proof generation
- **New file**: `flux_proof/src/proof_ir.rs` — proof IR (annotations on FLUX-IR)
- **New file**: `flux_proof/src/verifier.rs` — proof checker (Rust implementation)
- **New file**: `flux_proof/src/pcc.rs` — proof-carrying code packaging
- **Files modified**: `flux_backend/src/*.rs` — each backend emits proof annotations
- **New file**: `proofs/` — Coq proof library for common constraint patterns

### Tests Added
- **Proof generation tests**: 10 GUARD programs with known properties, verify Coq proofs are valid
- **Proof verification tests**: 10 valid proofs, 10 invalid proofs, verify checker catches all
- **PCC round-trip test**: Compile → extract proof → verify → run
- **Performance test**: Proof verification time for 1000-constraint program

### Success Criterion
- Proof checker correctly validates all valid proofs and rejects all invalid ones
- Proof generation succeeds for at least 80% of test programs
- Proof verification adds ≤20% to compilation time
- Proof-carrying code packages are ≤2x the size of compiled code alone

### Risks
- **CRITICAL**: This is the hardest phase. Connecting Coq proofs to compiled code is an active research area. The "proof-carrying code" concept from the 1990s (Necula, Lee) has never been productionized.
- **HIGH**: Coq integration is fragile. Coq version changes can break proof generation.
- **HIGH**: Proof generation may fail for complex constraints. Need graceful fallback (emit warning, compile without proof).
- **MEDIUM**: Proof verification performance may be poor for large programs.

### Dependencies
- Phase 3 (backends must exist to annotate)
- External: Coq proof assistant (version 8.18+)

---

## Phase 5 (Week 6): LSP, Formatter, Linter

### What Changes
- **New module**: `flux_lsp/` — language server
- **New file**: `flux_lsp/src/server.rs` — LSP server implementation
- **New file**: `flux_lsp/src/completion.rs` — autocomplete
- **New file**: `flux_lsp/src/hover.rs` — hover information
- **New file**: `flux_lsp/src/diagnostics.rs` — real-time diagnostics
- **New module**: `flux_fmt/` — formatter
- **New file**: `flux_fmt/src/format.rs` — pretty-printer with configurable style
- **New module**: `flux_lint/` — linter
- **New file**: `flux_lint/src/rules/` — lint rules (naming conventions, dead constraints, etc.)

### Tests Added
- **LSP protocol tests**: 50+ LSP requests, verify responses
- **Formatter tests**: 100+ formatting examples (input → expected output)
- **Linter tests**: 50+ lint rule tests (each rule: valid + invalid examples)
- **Integration test**: LSP server running, editor sends requests, verify responses

### Success Criterion
- LSP provides completion, hover, go-to-definition, and real-time diagnostics
- Formatter produces deterministic output (idempotent: format twice = format once)
- Linter catches at least 10 common mistakes with actionable error messages
- LSP response time ≤100ms for typical files

### Risks
- **LOW**: LSP protocol is well-documented. Implementation is straightforward.
- **LOW**: Formatter is well-understood (prettier-style).
- **MEDIUM**: Linter rules for constraint DSLs are novel. May need user feedback to refine.

### Dependencies
- Phase 0 (parser must exist for syntax analysis)
- Phase 1 (IR must exist for semantic analysis in LSP)

---

## Phase 6 (Week 7): Incremental Compilation

### What Changes
- **New module**: `flux_incremental/` — incremental compilation engine
- **New file**: `flux_incremental/src/dependency.rs` — dependency tracking
- **New file**: `flux_incremental/src/cache.rs` — compilation cache
- **New file**: `flux_incremental/src/fingerprint.rs` — content fingerprinting
- **Files modified**: `flux_parser/`, `flux_ir/`, `flux_opt/`, `flux_backend/` — add incremental hooks

### Tests Added
- **Incremental correctness test**: Full compile → modify one line → incremental compile → compare outputs
- **Cache hit/miss test**: Verify cache is invalidated correctly
- **Performance benchmark**: Full compile vs incremental compile for 1-line change (target: 10x faster)
- **Edge case tests**: File deletion, file addition, circular dependencies

### Success Criterion
- Incremental compilation is ≥10x faster than full compilation for single-line changes
- Cache invalidation is correct (no stale results)
- Dependency tracking handles all constraint file constructs
- Incremental compilation produces identical output to full compilation

### Risks
- **HIGH**: Incremental compilation for constraint DSLs is novel. Dependency tracking for constraints (which can reference each other in complex ways) is harder than for imperative languages.
- **MEDIUM**: Cache invalidation bugs are subtle and hard to test.
- **LOW**: Fingerprinting is well-understood.

### Dependencies
- Phase 1-3 (all compilation stages must be stable)
- Phase 5 (LSP benefits from incremental compilation)

---

## Phase 7 (Week 8): Cross-Compiler Differential Testing

### What Changes
- **New module**: `flux_test/` — testing infrastructure
- **New file**: `flux_test/src/differential.rs` — differential testing harness
- **New file**: `flux_test/src/fuzz.rs` — fuzz testing
- **New file**: `flux_test/src/regression.rs` — regression test suite
- **New file**: `flux_test/src/compare.rs` — output comparison (structural equality for IRs)
- **New file**: `tests/` — shared test data directory

### Tests Added
- **Differential test suite**: 1000+ randomly generated GUARD programs, compiled by all backends, outputs compared
- **Fuzz test**: 100,000 randomly generated inputs, verify no crashes
- **Regression test**: All bugs found during development become regression tests
- **Cross-backend equivalence**: Same program compiled to LLVM, C, eBPF, bytecode — verify all produce same results

### Success Criterion
- Differential testing catches at least 90% of semantic bugs
- Fuzz testing runs for 24 hours without crash
- All regression tests pass on every commit
- Cross-backend equivalence holds for all test programs

### Risks
- **LOW**: Differential testing is well-understood (cargo-fuzz, libFuzzer).
- **MEDIUM**: Generating valid GUARD programs randomly is non-trivial. Need a grammar-based fuzzer.
- **MEDIUM**: Output comparison for different backends requires semantic equivalence, not syntactic. This is hard for assembly vs C output.

### Dependencies
- Phase 3 (all backends must exist)
- Phase 0 (parser must exist for fuzzing)

---

## Overall Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| Semantic divergence between existing parsers | High | Certain | Phase 0 must include design discussions; accept temporary breakage |
| IR design wrong | High | Likely | Prototype IR with 5 programs before committing; be willing to iterate |
| Proof-carrying code too hard | Critical | Likely | Make Phase 4 optional; ship without proofs if needed |
| Constraint fusion/vectorization research-level | High | Likely | Implement simple versions first; mark as experimental |
| Incremental compilation for constraints novel | High | Likely | Start with coarse-grained caching; refine later |
| Fortran backend low ROI | Medium | Likely | Deprecate Fortran; focus on LLVM, C, eBPF |
| eBPF verifier too strict | Medium | Likely | Document limitations; provide workarounds |

## What's Easy
- Parser unification (Phase 0) — straightforward engineering
- Formatter (Phase 5) — well-understood problem
- Differential testing (Phase 7) — existing tools available
- LLVM and C backends (Phase 3) — well-understood codegen

## What's Hard
- IR design (Phase 1) — wrong choice cascades to everything
- Proof-carrying code (Phase 4) — research-level problem
- Constraint optimization passes (Phase 2) — fusion and vectorization are novel
- Incremental compilation (Phase 6) — dependency tracking for constraints is novel

## Recommendation
Ship Phase 0-3 as v1.0. Make Phase 4 (proofs) v2.0 with explicit research timeline. Phase 5-7 can ship incrementally. The Python compilers should be deprecated immediately after Phase 3 ships.