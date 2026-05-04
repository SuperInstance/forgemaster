## Proof of Determinism of the FLUX Constraint Compiler

A compiler is **deterministic** if its output is a function of its inputs: given the same source program and same target specification, every invocation produces identical output. We prove that the FLUX constraint compiler satisfies this property by showing that each stage of its pipeline is a deterministic function and that their composition is therefore also deterministic. This proof covers the parser, normalizer, optimizer, and code generator, and addresses why this matters for DO-254 certification.

---

### 1. Parser Determinism

Let \( \text{parse}: \text{SourceText} \to \text{AST} \) be the lexical and syntactic analysis phase.

**Lemma 1.** parse is a deterministic function.

*Proof.* FLUX uses a deterministic finite automaton for lexing and an LALR(1) parser with a fixed parse table. Both employ only the source text as input; no random seeds, system clocks, or file system metadata are consulted. The lexer maps each character to a token using a state machine whose transitions depend only on the current state and input character. The parser reduces tokens to an abstract syntax tree (AST) using the fixed LR table and a deterministic stack. No backtracking or speculative parsing occurs. Hence, for the same source text, the token stream and AST are identical across runs. \(\square\)

---

### 2. Normalization Determinism

Let \( \text{norm}: \text{AST} \to \text{NormalizedAST} \) transform the AST into a canonical normal form.

**Lemma 2.** norm is a deterministic function that yields a unique normal form.

*Proof.* Normalization applies a fixed sequence of rewrite rules in a fixed order. All commutative operators (e.g., conjunction, disjunction) are sorted using a total order on subterms (lexicographic term ordering). Variables are renamed using de Bruijn indices, so bindings are canonical. Constant folding evaluates constant subexpressions using exact integer arithmetic. The order of reductions is predetermined (leftmost-innermost). Because the term rewriting system is confluent and terminating, and because the algorithm never branches on external state or random choices, the normal form is uniquely determined by the input AST. \(\square\)

---

### 3. Optimization Pass Determinism

Optimization passes are applied sequentially: \( \text{opt}_i : \text{IR} \to \text{IR} \) for \( i = 1,\dots,n \). The full optimizer is \( \text{opt} = \text{opt}_n \circ \cdots \circ \text{opt}_1 \).

**Lemma 3.** Each \( \text{opt}_i \) is a deterministic function.

*Proof.* Each pass performs a fixed set of transformations:
- Constant propagation: replaces uses of a variable with its statically known value. The algorithm uses a worklist that processes nodes in a deterministic order (e.g., reverse postorder).
- Dead code elimination: marks live instructions via a deterministic fixed-point iteration that starts from a canonical set of entry points.
- Loop unrolling: unrolls loops by a fixed factor (supplied as a compile-time constant). The factor does not depend on run-time or random values.
- Inlining: uses a fixed threshold and a deterministic heuristic (e.g., call count order).

All internal data structures use sorted containers or arrays instead of hash tables with unpredictable iteration order. No multi-threading, random numbers, or timestamps are employed. Consequently, for the same input IR, each pass produces exactly the same output IR across runs. \(\square\)

**Corollary.** The composition opt is deterministic, as the composition of deterministic functions is deterministic.

---

### 4. Code Generation Determinism

Let \( \text{codegen}_T : \text{NormalizedIR} \to \text{TargetCode} \) map the normalized intermediate representation to target-specific assembly or object code.

**Lemma 4.** codegen\(_T\) is a deterministic function for each target \( T \).

*Proof.* Code generation consists of:
- **Instruction selection**: pattern matching maps IR operations to target instructions in a fixed, greedy manner (no backtracking).
- **Register allocation**: uses linear scan with a fixed precomputed order of live intervals, or graph coloring with a predetermined node ordering (e.g., sorted by spill cost). Tie-breaking is resolved by a total order on virtual registers (their IDs). No random perturbations are introduced.
- **Instruction scheduling**: if performed, uses a deterministic list scheduler with a fixed priority function (e.g., critical path length). No heuristic depends on random seeds.
- **Output emission**: text or binary is produced in a fixed format (e.g., little-endian byte ordering, fixed symbol naming). External factors (directory listing, system time) do not influence the emitted code.

Thus, the same normalized IR yields identical target code on every invocation for a given target. \(\square\)

---

### 5. Full Pipeline Determinism by Composition

The complete compilation function is:

\[
\text{compile}(S, T) = \text{codegen}_T( \text{opt}( \text{norm}( \text{parse}(S) ) ) )
\]

**Theorem.** compile is deterministic: for any fixed source program \( S \) and target \( T \), \( \text{compile}(S,T) \) is the same on every invocation.

*Proof.* By Lemma 1, parse is a deterministic function of \( S \). By Lemma 2, norm is deterministic, so \( \text{norm}(\text{parse}(S)) \) is deterministic. By Lemma 3, opt is deterministic, so \( \text{opt}(\text{norm}(\text{parse}(S))) \) is deterministic. By Lemma 4, codegen\(_T\) is deterministic, and the composition of deterministic functions is deterministic. Therefore, for the same \( S \) and \( T \), the output is fixed across runs. \(\square\)

---

### Why Determinism Matters for DO‑254

DO‑254 (Design Assurance for Airborne Electronic Hardware) mandates that the development tool chain produce reproducible builds. The regulatory logic is:

- **Verification by testing**: The binary artifact that is tested during qualification must be exactly the one that is deployed in the aircraft field. If the compiler is nondeterministic, the binary produced for testing may differ from the binary compiled later for production, even from the same source. This invalidates any safety case that relies on test results.
- **Traceability**: DO‑254 requires a clear chain from requirements to source code to object code. A nondeterministic compiler breaks this chain because a single source requirement could map to multiple possible object-code outputs, none of which can be independently verified.
- **Tool Qualification**: The compiler itself must be qualified as a development tool. A qualification artifact is a deterministic specification of the compiler’s behavior. Nondeterministic behavior makes it impossible to create such a specification and to reproduce verification results.

The FLUX constraint compiler’s deterministic design eliminates these risks. By proving that the parser, normalizer, optimizer, and code generator are each deterministic, we guarantee that the same source always yields the same binary. This property enables:
- **Repeatable verification**: The binary tested in the lab is identical to the binary installed in the aircraft.
- **Regression consistency**: Fixing a bug in the source leads to a predictable change in the binary; no spurious differences arise from compiler nondeterminism.
- **Certification confidence**: Auditors can inspect the compiler’s deterministic algorithms and verify that the build process is fully reproducible.

---

### Conclusion

We have proved that the FLUX constraint compiler is deterministic by showing that each stage of its pipeline is a deterministic function. The parser depends only on source text; normalization yields a unique canonical form; optimization passes are order‑deterministic and free from randomness; code generation produces fixed target code per given target. By composition, the entire compilation process is a pure function of its inputs. This determinism satisfies the reproducibility requirements of DO‑254, ensuring that safety‑critical avionics systems can be confidently tested and deployed.