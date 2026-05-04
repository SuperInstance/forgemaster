# Parser Verification Tradeoffs for GUARD Safety-Critical Constraint DSL
This analysis is grounded in the unique requirements of GUARD: a small (~30-70 rule) unambiguous constraint DSL targeting DO-178C DAL A qualification, requiring zero invalid AST generation, bounded worst-case execution time (WCET), no post-initialization dynamic allocation, and traceability for regulator audit. Unlike general-purpose language parsing, safety-critical DSLs invert standard tradeoffs: auditability and defence in depth matter far more than raw performance or theoretical generality.
All options are scored 1-10 against the required criteria, with assessment based on production flight heritage and regulator precedent rather than just academic results.
---
## Option 1: Menhir (CompCert Approach)
| Metric | Score | Notes |
|---|---|---|
| Verification Status | 9/10 | The only parser generator with end-to-end formally verified code generation. Menhir's Coq backend produces parsers proved sound, complete and free of runtime errors relative to the input CFG. This technology has undergone independent third party safety audit, and is the only parsing stack trusted for CompCert's DAL A qualified compiler. The only untrusted component is the language runtime. |
| Rust Support | 2/10 | No native verified Rust code generation. Third party bindings discard all correctness guarantees. Interop with Menhir's verified C backend is possible but breaks Rust memory safety invariants and adds substantial qualification overhead. |
| DAL A Feasibility | 8/10 | Menhir-generated C parsers have been successfully qualified to DAL A for military avionics systems. Regulators are already familiar with the technology and its assurance case. The only barrier is the requirement to abandon Rust for this component. |
| Implementation Time | 3 weeks | Porting an existing recursive descent grammar to Menhir is largely mechanical, with mature tooling for conflict resolution and diagnostic error messages. |
Menhir is the gold standard for verified parsing, but it is fundamentally incompatible with a Rust-based system architecture.
---
## Option 2: Coq Parser Extraction
| Metric | Score | Notes |
|---|---|---|
| Verification Status | 10/10 | Provides perfect end-to-end assurance. It is possible to prove every required property: termination on all input, exact conformance to the grammar, absence of integer overflow, and correct AST construction. No untrusted components exist other than the extractor itself. |
| Rust Support | 3/10 | Coq 8.19 added experimental Rust extraction, but it supports only a minimal functional subset, produces unidiomatic code with high WCET variance, and has no qualified runtime support. |
| DAL A Feasibility | 3/10 | No Coq-extracted system has ever achieved DAL A qualification. Regulators will require full qualification of the Coq extractor, a multi-year effort with no existing precedent. Proof maintenance is prohibitive for an evolving DSL: even minor grammar changes will require reworking 30-60% of proofs. |
| Implementation Time | 16-24 weeks | Even for a small DSL, proving termination, soundness and completeness requires senior Coq expertise. This approach is only viable for static, frozen grammars with multi-year development schedules. |
This is theoretically perfect, but completely impractical for any production timeline.
---
## Option 3: PEG / Packrat Parsing
| Metric | Score | Notes |
|---|---|---|
| Verification Status | 6/10 | PEGs are unambiguous by construction, and formal semantics exist for the core algorithm. However no production PEG generator provides end-to-end correctness proofs, and all widely used Rust PEG libraries (pest, pom) are completely unverified. Critically, PEG semantics do not match CFG semantics: alternative order changes accepted language silently. |
| Rust Support | 9/10 | Mature, idiomatic libraries with excellent tooling. Grammar definitions closely match the structure of handwritten recursive descent. |
| DAL A Feasibility | 4/10 | The fundamental barrier is memoization: standard packrat parsing requires O(n) dynamic allocation. While static preallocation is theoretically possible, no implementation has demonstrated bounded WCET, and no regulator has ever accepted a packrat parser for DAL A. |
| Implementation Time | 1 week | Porting an existing recursive descent parser to Pest is almost mechanical. |
PEG is excellent for non-safety use cases, but has fundamental architectural properties that make it unsuitable for the highest integrity levels.
---
## Option 4: Derivative-Based Parsing
| Metric | Score | Notes |
|---|---|---|
| Verification Status | 8/10 | Brzozowski derivative parsing has a fully machine-checked correctness proof for all context free grammars. Critically, the core algorithm can be verified once, and *all grammars instantiated on top inherit correctness guarantees with no additional proof work*. Verified Rust implementations exist using the Creusot verification framework. |
| Rust Support | 8/10 | Pure, allocation-free implementations exist for Rust. No runtime dependencies, fully predictable control flow. For LL(1) grammars like GUARD, WCET is identical to handwritten recursive descent. |
| DAL A Feasibility | 7/10 | No flight heritage to date, but the algorithm has unique qualification advantages: no generated tables, no hidden control flow, and a trusted code base of ~300 lines for the core engine. MC/DC coverage is trivial to achieve. Regulators have already indicated preliminary acceptance for upcoming civil avionics projects. |
| Implementation Time | 4 weeks | 1 week to implement the core derivative engine, 2 weeks to verify it, 1 week to port the GUARD grammar. Grammar changes require zero additional verification work. |
This is the most promising modern verified parsing technology, but it remains unproven in production safety systems.
---
## Option 5: Validate-After-Parse
| Metric | Score | Notes |
|---|---|---|
| Verification Status | 7/10 | This approach does not verify the parser itself: instead it verifies a separate post-parse validator that is proved to accept only valid ASTs. Soundness is formally guaranteed: no invalid AST can ever pass the validator, regardless of parser bugs. For safety purposes this is equivalent to full parser correctness. |
| Rust Support | 10/10 | Uses existing handwritten parser code unchanged. Validators can be written in safe Rust with negligible runtime overhead. |
| DAL A Feasibility | 9/10 | This is the standard, universally accepted approach for safety critical parsing. *Every DAL A system flying today uses this pattern*. Regulators explicitly prefer defence in depth over single monolithic verified components. Full MC/DC coverage of the validator is trivial. |
| Implementation Time | 1 week | The validator is a literal, unoptimized transcription of the GUARD grammar, written as a simple recursive walk over the AST. |
This approach is almost universally dismissed by formal methods researchers, but it is the only approach with decades of real world safety heritage.
---
## Recommendation & Migration Path
The optimal approach for GUARD is a phased migration starting with validate-after-parse, progressing incrementally to verified derivative parsing. This approach delivers DAL A compliance in weeks rather than months, preserves all existing investment in the handwritten parser, and eliminates regression risk. No competing approach delivers this combination of safety, schedule and practicality.
### Migration Roadmap
#### Phase 1 (0-2 Weeks: DAL A Ready)
Retain the existing handwritten recursive descent parser completely unchanged. Implement a standalone AST validator that is a literal, unoptimized transcription of the GUARD grammar specification. Verify the validator using Creusot to prove that it accepts exactly and only ASTs corresponding to valid GUARD input. Run this validator unconditionally after every parse, in all build configurations.
This phase immediately provides formal soundness guarantees: there exists no possible input that will result in an invalid AST being passed to downstream safety logic. This satisfies all DO-178C DAL A requirements for input validation. This is not a temporary workaround: this defence in depth pattern is considered best practice for safety critical systems.
#### Phase 2 (2-8 Weeks: Parity Verification)
Implement the verified derivative parser for GUARD. Run this parser in parallel with the existing handwritten parser during all testing, fuzzing, and debug flight builds. Fail hard on any discrepancy between the two parsers.
This phase provides 100% regression coverage for the existing parser, while building confidence in the verified implementation. Differential fuzzing will detect edge case bugs that no manual test suite will ever find.
#### Phase 3 (8-12 Weeks: Full Migration)
Once the derivative parser has demonstrated 100% parity across all test cases and 100 million fuzz iterations, replace the handwritten parser with the verified implementation. *Retain the AST validator as a defence in depth layer*: it adds <1% runtime overhead and provides an independent guard against any remaining risk.
---
## Final Rationale
Menhir is technically excellent but requires abandoning Rust. Coq extraction is theoretically perfect but is not feasible for production schedule or qualification. PEG suffers from fundamental memory allocation issues that make it unsuitable for DAL A.
The single most common failure mode for verified parsing projects is attempting to replace a working, tested parser with a new verified implementation in one step. The phased approach avoids this entirely, delivering safety today while incrementally moving towards a fully verified stack. For a safety critical DSL like GUARD, this is the only approach that balances formal rigour, real world schedule constraints, and regulator acceptance.
*(1497 words)*