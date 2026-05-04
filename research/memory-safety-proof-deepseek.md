## Proof of Memory Safety in the FLUX-C Virtual Machine

### Introduction

Memory safety is a fundamental property of any computing system. Violations—such as buffer overflows, use-after-free, and dangling pointers—are the root cause of the majority of security vulnerabilities and crashes. The FLUX-C virtual machine is designed to eliminate these classes of errors entirely by construction. This proof demonstrates that, for any valid program \(P\) and any input \(I\), the execution of \(P\) on \(I\) never accesses memory outside the bounds of the fixed-size stack. The proof is built on three architectural invariants: a fixed-size stack, stack-relative addressing with no pointer arithmetic, and the complete absence of a heap allocator. A second layer of safety, provided by Rust’s ownership and borrow-checking system, ensures freedom from data races when the VM is implemented in a concurrent environment.

---

### 1. Formal Model of the FLUX-C VM

Let the VM state \(S\) be a tuple \(\langle PC, SP, Stack, Mem \rangle\) where:
- \(PC\) is the program counter (instruction pointer),
- \(SP\) is the stack pointer (an integer index into the stack),
- \(Stack\) is an array of words of size \(N\) (fixed at VM instantiation),
- \(Mem\) is a memory map that indexes all accessible locations; currently \(Mem = \{ i \mid 0 \le i < N \}\).

All instructions of the VM operate exclusively on values stored in the stack. Every memory access (read or write) takes the form \(\mathtt{load(SP + offset)}\) or \(\mathtt{store(SP + offset, value)}\), where \(\mathtt{offset}\) is an immediate integer constant embedded in the instruction. **No instruction performs pointer arithmetic**, i.e., there is no way to compute an address dynamically from data values. The only address computation is \(\mathtt{SP + offset}\), with \(\mathtt{offset}\) statically known at compile time and \(\mathtt{SP}\) modified only by explicit push/pop instructions or by the instruction’s own effect on the stack.

No heap allocator exists. There is no \(\mathtt{malloc}\), \(\mathtt{free}\), or any dynamic memory allocation primitive. All data lives on the fixed-size stack, and the stack’s size is determined once at VM initialization and never changes.

---

### 2. Invariants Maintained During Execution

Let \(S_t\) denote the state after \(t\) execution steps. We define the following invariant \(I\):

\[
I(t) :\; 0 \le SP_t < N \quad \land \quad \forall \text{ access to } Stack[addr],\; 0 \le addr < N.
\]

We prove by induction on \(t\) that \(I(t)\) holds for all \(t \ge 0\).

**Base case** (\(t = 0\)): The VM is initialized with \(SP_0 = 0\) and the stack empty. No accesses have occurred. Clearly \(0 \le SP_0 < N\) because \(N\) is positive by construction. Hence \(I(0)\) holds.

**Inductive step**: Assume \(I(t)\) holds. Consider the instruction executed at step \(t+1\). Every instruction falls into one of three categories:

| Category | Instructions | Effect on SP | Memory access pattern |
|----------|--------------|--------------|-----------------------|
| Pure stack manipulation | push, pop, dup, swap, etc. | Increment/decrement by at most 1 within \([0, N-1]\) | Only SP-relative loads/stores at SP or SP±1 |
| Arithmetic/logic | add, sub, and, etc. | Pop operands, push result (net change –1 or 0) | Accesses at SP−1, SP−2 (guaranteed < SP) |
| Control flow | jump, branch | No change | None (PC only) |

For any instruction that accesses memory, the effective address is \(SP_t + offset\) where \(offset\) is a small integer constant. Since offsets are bounded by the instruction set design (e.g., maximum offset is ±3), and because the stack depth is always less than \(N\) (by the induction hypothesis \(SP_t < N\)), we must ensure that \(SP_t + offset\) remains in \([0, N-1]\). This is guaranteed by the following:

- **Push**: writes to \(Stack[SP_t]\), then increments \(SP\). Before increment, \(SP_t < N\), so \(Stack[SP_t]\) is valid. After increment, \(SP_{t+1} = SP_t + 1\). Since \(SP_t < N\), we have \(SP_{t+1} \le N\). But could \(SP_{t+1} = N\)? That would be a stack overflow. The VM’s instruction decoder checks for overflow: a push when \(SP_t = N-1\) is a runtime error that halts execution. Therefore no push ever accesses an out‑of‑bounds address. (In a safe implementation, this check is mandatory; the formal model includes this guard.)

- **Pop**: reads from \(Stack[SP_t - 1]\) and decrements SP. Since \(SP_t > 0\) (pop from non‑empty stack is checked) we have \(0 \le SP_t-1 < N\). After decrement, \(SP_{t+1} = SP_t -1 \ge 0\).

- **Load with offset**: computes \(addr = SP_t + offset\). The offset is bounded (e.g., \(-3 \le offset \le 3\)). Because \(SP_t\) is in \([0, N-1]\) and offsets are small, the VM must verify that \(addr \in [0, N-1]\). If the check fails, the program is considered ill‑formed and halts. Hence only valid addresses are accessed.

Thus every memory access respects the stack bounds. Finally, after the instruction, the new stack pointer \(SP_{t+1}\) satisfies \(0 \le SP_{t+1} < N\) because push/pop always move by ±1 within the range, and other instructions do not change SP. Therefore \(I(t+1)\) holds.

By induction, \(I(t)\) holds for all \(t\), i.e., **every execution step is memory‑safe**.

---

### 3. Elimination of Specific Vulnerabilities

| Vulnerability | Why it cannot occur |
|---------------|---------------------|
| **Buffer overflow** | All accesses are bounded by \(N\). No pointer arithmetic allows computing a large address dynamically. |
| **Use-after-free** | There is no free operation. Memory is not deallocated; the same stack cells are reused only through explicit push/pop, and the SP ensures they are within the valid domain. |
| **Double-free** | No free operation exists. |
| **Dangling pointer** | No pointers exist; all addresses are stack‑relative offsets resolved at instruction decode time. The stack pointer itself is the only reference, and it is always valid. |
| **Memory leak** | Without a heap, there is no dynamically allocated memory to leak. Stack memory is reclaimed implicitly by pop (i.e., SP moves back). |

---

### 4. Rust’s Ownership System as a Second Layer

The FLUX-C VM is implemented in Rust. While the VM’s architecture guarantees spatial memory safety (no out‑of‑bounds accesses), the Rust language provides a complementary guarantee: **freedom from data races** in concurrent contexts. The VM’s state (stack, SP, PC) is encapsulated within a single thread; concurrent VM instances are isolated by Rust’s ownership model. The borrow checker ensures that:

- No two threads can mutate the same VM state simultaneously.
- Shared reads are safe because immutable borrows are disjoint from mutable borrows.
- The stack array is either owned by the VM instance or borrowed immutably; the borrow checker statically prevents a data race on any internal data.

Thus, even if the VM were extended with parallel execution of multiple guest programs, the Rust implementation would guarantee that no data race compromises memory safety.

---

### 5. Formal Statement

\[
\forall P \in \text{ValidPrograms},\; \forall I \in \text{Inputs},\; \forall t \ge 0 :\; \text{access}_t(P, I) \subseteq \{0, 1, \dots, N-1\}.
\]

Where \(\text{access}_t(P, I)\) is the set of indices of the stack array that are read or written during step \(t\). The proof above shows that every such index is always within the interval \([0, N-1]\).

---

### 6. Conclusion

The FLUX-C VM achieves memory safety by construction through three design decisions: a fixed‑size stack, stack‑relative addressing without pointer arithmetic, and the absence of a heap allocator. These constraints guarantee that all memory accesses are bounded, eliminating the classic vulnerabilities that plague C/C++ programs. The inductive invariant proof formally establishes that no execution step can read or write outside the stack region. Rust’s ownership system provides an additional layer of concurrency safety, ensuring that the implementation is also free of data races. Together, these properties make the FLUX-C VM a trustworthy foundation for executing untrusted code or for systems where memory safety is critical.