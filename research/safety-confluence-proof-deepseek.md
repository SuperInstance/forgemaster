**Theorem (Safety Confluence for FLUX-C).**  
Let \( \mathcal{V} \) be a virtual machine that is (1) Turing-incomplete, (2) memory-safe, (3) timing-side-channel-free, and (4) deterministic. Then for any two programs \( P_1, P_2 \) that each individually satisfy all four properties when executed on \( \mathcal{V} \), the sequential composition \( P_1 ; P_2 \) also satisfies all four properties. Moreover, the set of safety properties forms a bounded distributive lattice under the partial order induced by property inclusion, with sequential composition as the join operation on the set of programs satisfying the four-property conjunction.

*Proof.*  We proceed by first giving precise formal definitions of the four properties in the context of \( \mathcal{V} \), then defining sequential composition of programs, and finally proving that each property is preserved under composition. The lattice structure follows as a corollary.

---

### 1. Formal Model of the VM

Let \( \mathcal{V} = (S, T, M, \mathcal{P}) \) where:

- \( S \) is the countable set of all possible VM states. Each state \( s \in S \) includes a program counter, a finite set of memory cells \( M_c \), and a finite set of registers.
- \( T : S \times \mathcal{P} \to S \) is a partial transition function. For a given program \( P \in \mathcal{P} \) and a state \( s \), \( T(s, P) = s' \) if the VM can execute one step of \( P \) from \( s \); otherwise undefined.
- \( M \subseteq S \times \mathbb{N} \times \mathbb{N} \) is the memory-access relation: \((s, a, v) \in M\) means that executing one step from state \( s \) accesses memory address \( a \) with value \( v \) (either read or write). The VM enforces that no step accesses an address outside the program’s allocated region.
- \( \mathcal{P} \) is the set of finite programs written in the FLUX-C instruction set. Each program is a finite list of instructions.

A program \( P \) is **terminating** iff there exists a finite sequence of states \( s_0, s_1, \dots, s_n \) with \( s_{i+1} = T(s_i, P) \) for \( i < n \), and \( T(s_n, P) \) is undefined (the program halts). The **trace** of \( P \) from initial state \( s_0 \) is the sequence \( \tau(P, s_0) = (s_0, s_1, \dots, s_n) \).

---

### 2. Formal Definition of the Four Properties

*Property (1): Turing-incompleteness.*  
\( \mathcal{V} \) is called **Turing-incomplete** iff for every program \( P \in \mathcal{P} \) and every initial state \( s_0 \in S \), the execution of \( P \) terminates. Equivalently, the transition function \( T(\cdot, P) \) is well-founded: there is no infinite execution chain. This implies that the language \( \mathcal{P} \) does not admit general recursion or unbounded loops; all loops are bounded by a statically known bound.

*Property (2): Memory safety.*  
A program \( P \) is **memory-safe** on \( \mathcal{V} \) iff for every initial state \( s_0 \) and every step \( (s_i, a, v) \) in the execution trace, the address \( a \) lies inside the memory region allocated to \( P \) at step \( i \). The VM \( \mathcal{V} \) itself is memory-safe if this holds for all \( P \in \mathcal{P} \). In FLUX-C, memory is partitioned into disjoint regions per program, and the instruction set prevents any instruction from dereferencing an address outside the current program’s region. Formally:  
\( \forall P \in \mathcal{P}, \forall s_0 \in S, \forall i \in \{0,\dots,n-1\}, \text{if } (s_i, a, v) \in M \text{ then } a \in \text{alloc}(P, i) \).

*Property (3): Timing-side-channel-freedom.*  
A program \( P \) is **timing-side-channel-free** on \( \mathcal{V} \) iff the execution time depends only on the public input, not on any secret data. Formally, partition the state \( s \) into public \( s_{\text{pub}} \) and secret \( s_{\text{sec}} \). For any two initial states \( s_1, s_2 \) that agree on public values (\( s_1^{\text{pub}} = s_2^{\text{pub}} \)), the execution time \( \text{time}(P, s) \) is identical:  
\( \text{time}(P, s_1) = \text{time}(P, s_2) \).  
We assume the VM provides a constant-time instruction set (e.g., no data-dependent branching on secret values, no cache-timing leaks) and that the timing model is a deterministic function of the instruction sequence and public inputs only.

*Property (4): Determinism.*  
\( \mathcal{V} \) is **deterministic** iff for any program \( P \) and any initial state \( s_0 \), the execution trace is unique: \( T(s, P) \) is a function (single-valued). Consequently, the final state is a deterministic function of \( s_0 \) and \( P \). No nondeterministic choices (e.g., race conditions, random scheduling) exist.

---

### 3. Sequential Composition

The sequential composition of two programs \( P_1 \) and \( P_2 \) is a new program \( P_1 ; P_2 \) whose instruction sequence is the concatenation of the instructions of \( P_1 \) followed by those of \( P_2 \). The execution of \( P_1 ; P_2 \) from initial state \( s_0 \) proceeds as follows:

1. Execute \( P_1 \) from state \( s_0 \) to its final state \( s_f^{(1)} \).
2. Execute \( P_2 \) from state \( s_f^{(1)} \) to its final state \( s_f^{(2)} \).

The VM’s memory model ensures that \( P_2 \) runs in the same allocated region as \( P_1 \) (or in a separate region if the composition uses a new allocation; in FLUX-C, composed programs share an allocation unless explicitly isolated). We assume the simplest case: the composed program runs in a single contiguous region assigned at load time.

---

### 4. Preservation of Each Property Under Composition

We now prove that if \( P_1 \) and \( P_2 \) each satisfy all four properties individually, then \( P_1 ; P_2 \) also satisfies all four.

#### 4.1 Turing-incompleteness

Since \( \mathcal{V} \) is Turing-incomplete, every program terminates. In particular, \( P_1 \) terminates from any initial state, and \( P_2 \) terminates from any reachable state. The composed program \( P_1 ; P_2 \) is just a longer finite sequence of instructions. Termination of \( P_1 \) guarantees that control reaches the first instruction of \( P_2 \) after a finite number of steps. Then \( P_2 \) terminates from that state because it is a valid initial state for \( P_2 \) (the state after \( P_1 \) is a VM state, and \( P_2 \) terminates from all states). Thus the composition terminates in finite time. Turing-incompleteness of \( \mathcal{V} \) is a global property of the instruction set; concatenation does not introduce recursion or unbounded loops that were not already present. Hence \( P_1 ; P_2 \) is also Turing-incomplete.

#### 4.2 Memory safety

Assume \( P_1 \) and \( P_2 \) are memory-safe. For any initial state \( s_0 \), the execution of \( P_1 \) accesses only addresses in its allocated region. After \( P_1 \) halts, the VM state includes the memory region; \( P_2 \) then executes. Because the VM enforces memory safety globally, the instruction set of FLUX-C prevents \( P_2 \) from accessing addresses outside the region allocated to the composed program. However, we must check that \( P_2 \)’s memory safety with respect to its own intended region is preserved when the region is inherited from \( P_1 \). This is guaranteed because the region is the same physical allocation for the entire composed program. The VM’s memory-access checks are performed per instruction; they do not depend on which sub-program issued the instruction. Since every instruction in \( P_1 \) and \( P_2 \) individually satisfied the bound checks when run in isolation, and the checks are purely region-based, the same checks succeed when the instructions are concatenated. The only potential violation would be if \( P_1 \) corrupted metadata used by \( P_2 \). But memory safety of \( P_1 \) ensures it writes only to allocated cells; the metadata (e.g., bounds table) is stored in a protected area inaccessible to user programs. Therefore no corruption occurs. Hence \( P_1 ; P_2 \) is memory-safe.

#### 4.3 Timing-side-channel-freedom

Let \( \text{time}(P, s) \) denote the number of VM steps (or cycles) to execute \( P \) from state \( s \). Since \( \mathcal{V} \) is deterministic, this is a well-defined integer. For the composition:

\[
\text{time}(P_1 ; P_2, s_0) = \text{time}(P_1, s_0) + \text{time}(P_2, s_f^{(1)})
\]

where \( s_f^{(1)} \) is the final state of \( P_1 \). Now suppose two initial states \( s_0, s_0' \) have identical public components: \( s_0^{\text{pub}} = s_0'^{\text{pub}} \). Because \( P_1 \) is timing-side-channel-free, \( \text{time}(P_1, s_0) = \text{time}(P_1, s_0') \). Also, because \( \mathcal{V} \) is deterministic and \( P_1 \) is Turing-incomplete, the final state \( s_f^{(1)} \) is a deterministic function of the initial state. Moreover, the public part of \( s_f^{(1)} \) depends only on the public part of \( s_0 \) (since secret data is not used in any data-dependent way by \( P_1 \)). Formalizing: the mapping \( s_0^{\text{pub}} \mapsto s_f^{(1),\text{pub}} \) is a function. Therefore \( s_f^{(1),\text{pub}} = s_f'^{(1),\text{pub}} \). Since \( P_2 \) is timing-side-channel-free, its execution time depends only on the public state; hence:

\[
\text{time}(P_2, s_f^{(1)}) = \text{time}(P_2, s_f'^{(1)}).
\]

Adding the two equalities yields \( \text{time}(P_1 ; P_2, s_0) = \text{time}(P_1 ; P_2, s_0') \). The composition is therefore timing-side-channel-free. (Note: This argument relies on the absence of stateful timing channels that could propagate secret information through the execution time of \( P_2 \); but such channels are precluded by property (3) of \( P_2 \) and the deterministic public-to-public mapping of \( P_1 \).)

#### 4.4 Determinism

The deterministic transition function \( T \) of \( \mathcal{V} \) ensures that for any program \( P \) and state \( s \), the next state is uniquely determined. Therefore the entire trace of \( P_1 \) from \( s_0 \) is unique. Its final state \( s_f^{(1)} \) is uniquely determined. Then the trace of \( P_2 \) from \( s_f^{(1)} \) is likewise unique. Concatenating the two traces yields a unique trace for \( P_1 ; P_2 \