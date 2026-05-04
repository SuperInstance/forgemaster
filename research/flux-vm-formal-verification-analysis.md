## Security Analysis of Safety-Critical Stack VM (DAL A)

### (1) Attack Surface Analysis

**Memory Safety Vulnerabilities:**
- **Stack overflow/underflow**: 43 opcodes create 43×42=1806 possible stack state transitions. Each opcode must specify exact stack depth change (Δ). Attack vector: malformed bytecode sequences causing stack imbalance.
- **CHECKPOINT/REVERT sandbox escape**: If checkpoint boundaries are not cryptographically enforced (e.g., Merkle tree), rollback could corrupt adjacent memory regions. Proof: require `∀c: checkpoint_id, memory_range(c) ∩ memory_range(c+1) = ∅`.
- **DEADLINE opcode bypass**: If deadline check occurs after state mutation, attacker can execute infinite loops. Must enforce `DEADLINE` as first opcode in basic block.

**Control Flow Attacks:**
- **Indirect jump targets**: If VM supports computed GOTO, attacker can redirect to arbitrary opcode handler. Mitigation: require jump targets to be aligned to opcode boundaries (4-byte alignment).
- **Recursive CHECKPOINT nesting**: Unbounded nesting could exhaust stack. Limit to `MAX_NESTING = 8` (DO-178C §6.3.3 robustness).

**Determinism Violations:**
- **Timing side channels**: Even without timing ops, memory access patterns (cache timing) could leak data. For DAL A, require constant-time memory access (e.g., single-cycle SRAM).
- **Floating-point non-determinism**: If VM uses IEEE 754, different rounding modes break Galois connection. Must use fixed-point arithmetic only.

**Bytecode Validation Gaps:**
- **Dead code with side effects**: Opcodes that modify state but are unreachable must be rejected (DO-178C §6.4.2.2 structural coverage).
- **Type confusion**: Stack elements must have static type tags (e.g., `int32`, `bool`, `reference`). Attack: push `int32` then pop as `reference`.

### (2) Proof Obligations for DO-178C Level A Tool Qualification

**DO-178C §12.2 Tool Qualification Levels:**
- **TQL-1** (development tool): VM must be qualified as TQL-1 since it generates executable code from DSL.
- **TQL-4** (verification tool): If VM is used only for simulation, TQL-4 applies.

**Proof Obligations (per DO-178C Table 12-1):**

| Obligation | DO-178C Ref | Formal Requirement |
|------------|-------------|-------------------|
| **Soundness of Galois Connection** | §12.2.2a | `∀dsl: DSL, ⟦compile(dsl)⟧_VM = α(⟦dsl⟧_DSL)` where α is abstraction function |
| **Memory Isolation** | §6.3.3b | `∀c1≠c2: memory(c1) ∩ memory(c2) = ∅` with formal separation logic |
| **Bounded Execution** | §6.4.2.1 | `∀p: program, steps(p) ≤ DEADLINE_value` proven via ranking function |
| **Stack Safety** | §6.4.2.3 | `∀op: opcode, stack_depth_before(op) ≥ required_pop(op)` and `stack_depth_after(op) ≤ MAX_STACK` |
| **Determinism** | §6.3.1c | `∀p: program, ∀t1,t2: traces, t1 = t2` (same input → same output) |
| **No Undefined Behavior** | §6.3.3a | `∀op: opcode, all possible operand values produce defined behavior` (proven via type system) |
| **Checkpoint Revert Correctness** | §6.4.2.4 | `∀c: checkpoint, revert(c) ⇒ state = state_at_checkpoint(c)` |

**Proof Methodology:**
- Use Coq or Isabelle/HOL for machine-checked proofs (DO-178C §12.2.2c recommends formal methods for TQL-1).
- Each opcode must have formal semantics in HOL:
  ```
  ⊢ OP_ADD : (int32 # int32) stack → int32 stack
  precondition: stack_depth ≥ 2 ∧ top_type = int32 ∧ next_type = int32
  postcondition: stack_depth' = stack_depth - 1
  ```

### (3) Comparison to Java Card VM and WebAssembly Validation

| Aspect | This VM (DAL A) | Java Card VM | WebAssembly |
|--------|-----------------|--------------|-------------|
| **Validation Phase** | Static + dynamic (DEADLINE) | Static only (CAP file verification) | Static only (module validation) |
| **Memory Model** | Sandboxed regions (CHECKPOINT) | Applet firewall (JCRE) | Linear memory with bounds checks |
| **Type Safety** | Stack type tags (runtime) | Bytecode verifier (static) | Structured control flow (static) |
| **Termination Guarantee** | DEADLINE opcode (dynamic) | None (applet can loop) | None (but no infinite loops in practice) |
| **Formal Methods** | Required (TQL-1) | Optional (Global Platform) | Optional (W3C spec is informal) |
| **Certification Standard** | DO-178C Level A | Common Criteria EAL4+ | None (but FIPS 140-3 for crypto) |
| **Attack Surface** | 43 opcodes (small) | ~200 opcodes (larger) | ~150 opcodes (medium) |
| **Determinism** | Enforced (no timing ops) | Not guaranteed (GC timing) | Not guaranteed (host environment) |

**Key Differences:**
1. **WebAssembly validation** uses structured control flow (blocks/loops) which is easier to verify than arbitrary jumps. Our VM must enforce structured control flow via `CHECKPOINT` boundaries.
2. **Java Card** uses static bytecode verification (CAP file verifier) but allows dynamic class loading. Our VM has no dynamic loading (DO-178C §6.3.3 prohibits dynamic memory allocation).
3. **Both Java Card and WASM** allow non-terminating programs. Our DEADLINE opcode is unique to safety-critical systems.

### (4) Minimum Test Coverage Requirements (DO-178C Level A)

**DO-178C §6.4.2 Structural Coverage Analysis:**

| Coverage Type | Requirement | Target | Measurement Method |
|---------------|-------------|--------|-------------------|
| **Statement Coverage** | §6.4.2.2a | 100% of opcode handlers | Line coverage of VM interpreter |
| **Decision Coverage (DC)** | §6.4.2.2b | 100% of branches in opcode handlers | MC/DC for safety-critical paths |
| **Modified Condition/Decision Coverage (MC/DC)** | §6.4.2.2c | 100% for all conditions affecting safety | Each condition independently toggles outcome |
| **Data Coupling** | §6.4.2.3 | All opcode operand combinations | Pairwise testing of stack types |
| **Control Coupling** | §6.4.2.3 | All possible opcode sequences | Path coverage through basic blocks |

**Minimum Test Cases (43 opcodes):**

1. **Stack Safety Tests** (86 cases):
   - Each opcode: valid stack depth (43 cases)
   - Each opcode: invalid stack depth (underflow/overflow) (43 cases)

2. **Type Safety Tests** (43 × 42 = 1806 cases):
   - Each opcode with correct operand types
   - Each opcode with incorrect operand types (e.g., ADD with boolean)

3. **Checkpoint Tests** (2^8 = 256 cases for nesting):
   - Single checkpoint/revert
   - Nested checkpoints (up to 8 levels)
   - Revert after checkpoint boundary violation

4. **DEADLINE Tests** (3 cases):
   - Normal termination before deadline
   - Deadline exceeded (must halt)
   - Deadline = 0 (immediate halt)

5. **Determinism Tests** (43 × 2 = 86 cases):
   - Each opcode: same input → same output (run twice)
   - Each opcode: different execution order → same result (commutativity)

6. **Boundary Value Tests** (43 × 4 = 172 cases):
   - Min/max operand values
   - Min/max stack depths
   - Min/max checkpoint sizes

**Total Minimum Tests: 86 + 1806 + 256 + 3 + 86 + 172 = 2409 test cases**

**Additional DO-178C Requirements:**
- **§6.4.3 Robustness Testing**: 100% of error handling code (e.g., stack overflow handler)
- **§6.4.4 Requirements-Based Testing**: Each DSL construct maps to at least one test case
- **§6.4.5 Integration Testing**: VM running on target hardware (endianness, word size)

**Test Automation:**
- Use property-based testing (QuickCheck) to generate random bytecode sequences
- Formal verification of test oracle: `∀bytecode: valid_bytecode, run(bytecode) = spec(bytecode)`
- Coverage measurement via LLVM SanitizerCoverage or custom instrumentation

**Certification Artifacts:**
- Test plan (DO-178C §11.4)
- Test procedures (DO-178C §11.5)
- Test results (DO-178C §11.6)
- Structural coverage analysis (DO-178C §11.7)
- Formal proof documents (DO-178C §12.2.2)
