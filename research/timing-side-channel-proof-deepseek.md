## Proof: The FLUX-C VM is Free from Timing Side-Channels

### 1. Introduction  
Timing side-channels exploit variations in execution time to infer secret data (e.g., cryptographic keys, classified constraint values). This proof demonstrates that the FLUX-C Virtual Machine (VM) is provably immune to such attacks under its stated design principles. The VM is assumed to execute programs that operate on secret data (e.g., altitude limits) while preventing any leakage through observable timing. The argument relies on four core properties and a formalization of execution time independence.

---

### 2. System Model  
We model the FLUX-C VM as a deterministic state machine executing a sequence of opcodes.  
- **State** \( S \) consists of a program counter \( PC \), a stack \( Stk \), a memory \( Mem \), and a set of registers \( Reg \).  
- **Input** \( I \) consists of two parts: public non-secret data \( P \) and secret data \( C \) (e.g., constraint values).  
- **Execution** proceeds in discrete steps. At each step, the opcode \( op = Mem[PC] \) is fetched, executed, and the state is updated.  
- **Execution time** \( \mathcal{T}(P, I) \) is the total wall-clock time from start to termination.

---

### 3. Assumptions (Design Properties of FLUX-C VM)

1. **Constant-time opcodes**: Every opcode \( op \) has a fixed execution time \( \tau(op) \) that does **not** depend on the operand values, the current state, or any secret data.  
2. **Deterministic memory access pattern**: The only memory accesses are to the top of the stack (\( Stk.top \)). There is no data‑dependent addressing (e.g., no `load from address register + secret`).  
3. **No secret‑dependent control flow**: The VM has **no conditional jumps** or branches whose outcome depends on secret data. All jumps are unconditional or based solely on public program constants. Consequently, the program counter updates are deterministic and independent of \( C \).  
4. **Single‑threaded, no interrupts**: No external events can perturb execution time (e.g., no context switches, no variable‑latency hardware caches – or the effect is constant).

These assumptions align with the “arguments” listed in the problem statement.

---

### 4. Lemma: Program Path is Independent of Secret Data  

Define the **program path** \( \mathcal{P}(P, I) \) as the sequence of opcodes executed during the run:  
\[
\mathcal{P}(P, I) = \langle op_1, op_2, \dots, op_n \rangle,
\]
where \( n \) is the number of steps (including termination).

**Lemma.** For any fixed public data \( P \) and any two secret inputs \( C_1, C_2 \), the program paths are identical:  
\[
\mathcal{P}(P, (P, C_1)) = \mathcal{P}(P, (P, C_2)).
\]

*Proof.*  
The next opcode at step \( i \) is solely determined by the current program counter \( PC_i \). The update of \( PC \) from step \( i \) to \( i+1 \) is given by:

- If \( op_i \) is an **unconditional jump**, then \( PC_{i+1} \) = target address (a constant in the program).  
- Otherwise, \( PC_{i+1} = PC_i + 1 \).  

Because no conditional jump exists, the evolution of \( PC \) depends only on the program code and not on any secret data stored in registers, stack, or memory. By induction on \( i \), the sequence of opcodes is therefore a deterministic function of the program binary alone, not of the input secret \( C \). Hence the path is the same for \( C_1 \) and \( C_2 \). ∎

*Remarks.*  
- The lemma holds even if the program contains data‑independent loops (e.g., a `for i = 1 to 10` loop) because the number of iterations is public.  
- If the VM had conditional jumps, the path could diverge for different secret values; the lemma relies crucially on the absence of such jumps.

---

### 5. Theorem: Constant Execution Time  

**Theorem.** For any program \( P \) and any two inputs \( I_1 = (P, C_1) \), \( I_2 = (P, C_2) \) that differ only in secret data, the execution times are equal:  
\[
\mathcal{T}(P, I_1) = \mathcal{T}(P, I_2).
\]

*Proof.*  
Let the common program path be \( \mathcal{P} = \langle op_1, \dots, op_n \rangle \) (by Lemma). The total execution time is the sum of the times of each step:  
\[
\mathcal{T}(P, I) = \sum_{i=1}^{n} \tau_i,
\]
where \( \tau_i \) is the time taken by opcode \( op_i \).

By Assumption 1 (constant‑time opcodes), each \( \tau_i \) depends only on \( op_i \), not on the data being processed. In particular, it is independent of the secret \( C \). Consequently,  
\[
\mathcal{T}(P, I_1) = \sum_{i=1}^n \tau(op_i) = \mathcal{T}(P, I_2).
\]

The sum is identical for both inputs because the path and the per‑opcode timings are the same. Note that Assumption 2 (deterministic memory access) guarantees that memory operations do not introduce variable latency (e.g., no cache misses that depend on secret addresses). Assumption 3 ensures the path is fixed, and Assumption 4 removes external timing noise. Thus the theorem holds. ∎

---

### 6. Security Implications  

In many cyber‑physical security contexts, **constraint values** (e.g., the maximum altitude of a drone, the pressure threshold of a pipeline) are classified. An attacker who can measure execution time might otherwise infer these values by observing timing differences caused by:

- data‑dependent branches (e.g., `if altitude > LIMIT then ...`);  
- variable‑time arithmetic (e.g., multiplication by large vs. small numbers);  
- memory‑lookup patterns (e.g., accessing a table indexed by a secret).  

The FLUX‑C VM eliminates all such leakage **by design**:  
- No secret‑dependent branches ⇒ program path is constant across secret inputs.  
- Constant‑time opcodes ⇒ each operation’s duration is fixed.  
- Deterministic stack‑only memory ⇒ no secret‑dependent cache timing.  

Therefore, an adversarial observer cannot distinguish between different secret values by measuring the time of one execution. This provides a **provable guarantee** that timing side‑channels do not exist in the VM, assuming the model and assumptions are faithfully implemented.

---

### 7. Conclusion  

We have formally proved that the FLUX‑C VM is free from timing side‑channels. The proof rests on three pillars: constant‑time opcodes, deterministic memory access, and the absence of secret‑dependent control flow. Under these properties, the execution time depends solely on the program’s code and public inputs, not on secret data. This result holds for any program executing on the VM, making it suitable for environments where timing leakage must be eliminated at the architecture level, such as in safety‑critical systems with classified constraint values.

The proof also highlights the importance of verifying the underlying assumptions (e.g., that all opcodes are indeed constant‑time on the target hardware) – any violation would break the guarantee. Nevertheless, within the stated model, the security property is mathematically ensured.