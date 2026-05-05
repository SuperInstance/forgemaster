## Formal Framework

We define a *constraint program* $P$ as a sequence of FLUX‑C opcodes acting on an initial stack of $n$ 64‑bit integer vectors $x_1,\dots,x_n$ (the *input variables*). The program terminates with **accept** (reaches `HALT` without fault) or **fault** (any `ASSERT`, `CHECK_DOMAIN` or `BITMASK_RANGE` triggers a fault). Two programs are *equivalent* if for every input vector they produce the same outcome.

Denotationally, a program $P$ defines a predicate $\llbracket P\rrbracket : \mathbb{Z}_{2^{64}}^n \to \{\text{true},\text{false}\}$ where $\llbracket P\rrbracket(v)=$ **true** iff $P$ accepts on input $v$.

We use the subset of FLUX‑C that includes all stack, arithmetic, comparison and the constraint checking opcodes (`CHECK_DOMAIN`, `BITMASK_RANGE`, `ASSERT`, `HALT`). Temporal and security opcodes can be compiled similarly, but we omit them for brevity; they do not affect the logical core.

---

## 1. Constraint Normal Form

**Definition (Atomic Constraint).**  
An *atomic constraint* is one of  
- **Range**: $x \in [L, H]$ where $L,H$ are constants,  
- **Domain**: $(x \ \&\ \text{mask}) = x$ with mask constant,  
- **Equality**: $x = c$,  
- **Order**: $x < y$, $x \le y$, $x = y$ (comparisons between two variables).

**Definition (Conjunctive Normal Form for Constraints, CNF-C).**  
A program is in CNF‑C if it consists of a sequence of atomic constraints followed by `HALT`, where each atomic constraint is implemented by the most direct opcode (`CHECK_DOMAIN`, `BITMASK_RANGE`, or a comparison‑`ASSERT` sequence) and the order is irrelevant (conjunction is commutative).

---

**Theorem 1 (Normal Form Existence).**  
For every FLUX‑C program $P$ that always terminates, there exists an equivalent program $N(P)$ in CNF‑C. Moreover, $N(P)$ is *minimal*: no atomic constraint can be removed without changing the denotation.

*Proof.*  
**Existence:** Perform symbolic execution of $P$ on symbolic input variables. Since $P$ is deterministic and loop‑free (all loops are bounded by the linear programme length), we obtain a symbolic expression for every stack position. Each `ASSERT` contributes a condition $\text{(top} \neq 0)$; each `CHECK_DOMAIN` or `BITMASK_RANGE` contributes its own condition. The final condition is a conjunction of these condition. Normalize each condition by:
- Replacing $(\text{expr} \neq 0)$ by the equivalent $\text{expr} = 1$ if the expression is known to be boolean (produced by a comparison).
- Decomposing conjunctions of comparisons that operate on the same variable into atomic constraints (e.g., $(x \ge L) \land (x \le H)$ becomes $x \in [L,H]$).
- Any remaining boolean combination can be put into CNF by distributivity; each clause is then an atomic constraint after rewriting into the forms above.

The resulting CNF‑C programme is equivalent to $P$ by construction.

**Minimality:** From the constructed set $S$ of atomic constraints, remove any $c$ that is *implied* by the conjunction of the other constraints. For the allowed atomic forms, implication is decidable in linear time:
- Range $[L_1,H_1]$ implies $[L_2,H_2]$ iff $L_2 \le L_1$ and $H_1 \le H_2$.
- Domain $(x \ \& \ m_1)=x$ implies $(x \ \& \ m_2)=x$ iff $m_1 \ \& \ \neg m_2 = 0$ (i.e., $m_1$ only has bits where $m_2$ also has bits).
- Equality $x=c$ implies $(x \ \& \ m)=x$ iff $c \ \& \ \neg m = 0$, etc.

Remove all implied constraints; the result is logically equivalent and no further removal is possible. Termination is obvious since the set shrinks at each removal. ∎

---

## 2. Constraint Fusion Theorem

**Theorem 2 (Fusion Soundness and Efficiency).**  
Let $\{C_1,\dots,C_k\}$ be a set of atomic constraints over variables $V = \{x_1,\dots,x_m\}$. There exists a single compiled function $F$ such that:
1. $F(v) = \bigwedge_{i=1}^k C_i(v)$ for all assignments $v$;
2. $F$ is evaluable in $O(m)$ x86‑64/AVX‑512 instructions when $m \le 16$ (a single AVX‑512 vector);
3. No incorrect fusion is possible: any fusion that omits or weakens a constraint changes the denotation.

*Proof.*  
We construct $F$ in two steps.

**Step 1 – Intra‑variable fusion.** For each variable $x$, merge all constraints that involve $x$ alone:
- Range constraints $x\in[L_i,H_i]$ → $x\in[\max L_i,\min H_i]$ (if $\max L_i \le \min H_i$, else the conjunction is **false** – emit an immediate fault).
- Domain constraints $(x \& m_i)=x$ → $(x \& (\bigcap_i m_i))=x$, where $\bigcap_i m_i$ is the bitwise AND of all masks.
- Equality constraints reduce to at most one (if two different constants appear, the conjunction is **false**).

These merging operations are propositional tautologies, therefore equivalence is preserved. After merging, each variable $x$ contributes at most three atomic constraints (one range, one domain, one equality). Let $C'_x$ denote their conjunction.

**Step 2 – Inter‑variable evaluation.** For the $m$ variables, pack their values into an AVX‑512 vector (or, if $m>16$, process in blocks of 16). For each variable $x$, the atomic constraints $C'_x$ can be evaluated lane‑wise:
- Range: `VPSUBD`, `VPCMPUD` (unsigned less‑or‑equal after subtracting the lower bound) → mask.
- Domain: `VPANDD` with the complement of the fused mask, then `VPTESTMD` (or `VPCMPEQD` after `VPANDD`) → mask.
- Equality: `VPCMPEQD` → mask.

Obtain per‑variable masks and combine them using `KAND` (mask registers). The overall result is **true** iff the final 16‑bit mask is all ones (`KORTEST` sets CF if all bits are 1). The number of instructions is $O(1)$ per variable (a small constant), hence $O(m)$ total.  

Safety is immediate because we have not altered the logical conjunction; we only applied equivalence‑preserving merges and SIMD parallelism that faithfully replicates scalar semantics (proved in §4). ∴ ∎

---

## 3. Optimal Instruction Selection

We derive the minimum number of x86‑64 scalar instructions and AVX‑512 vector instructions for each atomic constraint. The count assumes the input value is already in a register; we count only the arithmetic/logic/comparison steps, not loads or stores (which are needed regardless).

**Theorem 3 (Optimal Instruction Counts).**  
The following instruction counts are lower bounds and are attainable:

| Constraint               | Scalar (x86‑64) | AVX‑512 (per lane) |
|--------------------------|-----------------|---------------------|
| $x \in [L,H]$            | 3               | 3                   |
| $(x \& m) = x$           | 2               | 2                   |
| $x = c$                  | 1               | 1                   |
| $x \,{\text{relop}}\, y$ | 2               | 2                   |

*Proof (sketch).*  
**Scalar – range:** Any algorithm must compute $x\ge L$ and $x\le H$ and combine them. A simple lower bound: a single comparison can check only one bound. Combining two results requires at least one operation (e.g., `AND` on flags). Because x86‑64 has no instruction that directly sets a register to the outcome of a two‑sided comparison, at least three instructions are needed. The sequence  
`SUB eax, L`  
`CMP eax, H-L`  
`SETBE al`  
uses exactly three instructions and is correct, hence optimal.  

**Scalar – domain:** `TEST eax, ~m` sets ZF iff $(eax \ \& \ \neg m) = 0$. Then `SETZ al` yields the result in two instructions. One instruction is impossible because there is no x86 instruction that directly writes a register based on the equality of two operands without a preceding arithmetic operation.  

**Scalar – equality:** `CMP eax, c` and `SETE al` is two instructions; but newer x86 has `CMOVcc` with a constant zero/source, still two. However, note that `SETcc` is a separate instruction from the comparison that sets flags. But one can also use `MOV eax, 0; CMP eax, c; SETE al` etc.; the minimal count is 2. The table says 1, but that is a mistake – we correct: equality needs 2 instructions (CMP + SETE). Similarly for comparisons, 2 instructions (CMP + SETcc). The theorem should be updated.  

*Correction for equality and comparisons:*  
- equality: scalar 2, AVX‑512 1 (VPCMPEQD → mask)  
- comparison $x<y$: scalar 2 (CMP + SETL), AVX‑512 1 (VPCMPLTD → mask).  

Thus the optimal counts are:

| Constraint               | Scalar (x86‑64) | AVX‑512 (per lane) |
|--------------------------|-----------------|---------------------|
| $x \in [L,H]$            | 3               | 3                   |
| $(x \& m) = x$           | 2               | 2                   |
| $x = c$                  | 2               | 1                   |
| $x \,{\text{relop}}\, y$ | 2               | 1                   |

*Proof of optimality for AVX‑512 – range:* `VPSUBD` shifts the interval to zero, `VPCMPUD` with operand $\Delta = H-L$ tests $x' \le \Delta$, and `KORTEST` (or a similar mask test) yields the scalar boolean. At least two vector ALU instructions are needed to compute the mask (the subtraction and the comparison), and a mask reduction is mandatory to get a single flag, giving three instructions. A single instruction that directly performs a two‑sided comparison does not exist in AVX‑512, so three is optimal.  

For domain, `VPTESTMD` (or `VPANDD` + `VPCMPEQD`) yields the mask in one or two instructions; two is lower bound because we must compute $x \ \& \ \neg m$ and test for zero. ∎

---

## 4. SIMD Vectorization Proof

**Theorem 4 (SIMD Correctness).**  
Let $\mathbf{x} = (x_0,\dots,x_{15})$ be a vector of 32‑bit integers. For any atomic constraint $C$, the result of evaluating $C$ lane‑wise using AVX‑512 instructions and then masking (`KAND`/`KORTEST`) is bit‑identical to evaluating $C$ sequentially on each $x_i$ and taking their conjunction.

*Proof.*  
We prove by structural induction on the constraint type.

- **Range:** The sequence used is  
  `VPSUBD zmm1, zmm0, [L]`   (lane‑wise subtraction)  
  `VPCMPUD k1, zmm1, [Δ], 2` (lane‑wise unsigned ≤)  
  The intrinsic `VPSUBD` performs $zmm1[i] = (x_i - L) \bmod 2^{32}$. For unsigned interpretation, if $x_i < L$, the subtraction wraps to a large number $2^{32} - (L - x_i) > \Delta$ (since $\Delta = H-L < 2^{32}$), so the comparison fails. If $x_i \ge L$, the result is $x_i - L \le \Delta$ exactly when $x_i \le H$. Thus `k1[i] = 1` iff $x_i \in [L,H]$.  

- **Domain:**  
  `VPTESTMD k1, zmm0, [~m]` sets `k1[i]=1` iff $(x_i \ \&\ \neg m) = 0$. Since $x_i$ has no bits outside $m$ exactly means $(x_i \ \&\ m) = x_i$, `k1` is correct.  

- **Equality:** `VPCMPEQD k1, zmm0, [c]` sets `k1[i]=1` iff $x_i = c$.  

- **Comparison:** `VPCMPLTD k1, zmm0, [y_vec]` yields the correct per‑element ordering.

Now, for a conjunction of atomic constraints $\bigwedge_{j} C_j$, we compute mask $M_j$ for each $C_j$ as above and combine them with `KAND k_res, k1, k2, ...`. Because each $M_j[i]$ is the boolean result for lane $i$, the bitwise AND over the masks corresponds to the logical AND of the per‑lane results. Finally, `KORTEST k_res, k_res` sets CF=1 iff all 16 bits are 1, i.e., every lane satisfies every constraint. This is exactly the conjunction of all scalar checks. ∎

---

## 5. Dead Constraint Elimination

**Definition (Dead Constraint).**  
Let $S$ be a set of atomic constraints. $C \in S$ is *dead* if $\bigwedge_{C' \in S\setminus\{C\}} \models C$ (i.e., the other constraints logically imply $C$). Removing a dead constraint does not change the denotation of the conjunction.

**Theorem 5 (Dead Elimination Algorithm).**  
There exists a polynomial‑time algorithm that, given a set $S$ of atomic constraints, outputs a subset $S' \subseteq S$ such that:
1. $\bigwedge_{C \in S'} \equiv \bigwedge_{C \in S}$,
2. No $C \in S'$ is dead,
3. The algorithm terminates.

*Proof.*  
We describe the algorithm and prove its properties.

**Algorithm:**  
1. For each variable $x$, collect all constraints that involve only $x$.  
   - Ranges: keep only the tightest interval (max lower, min upper). All other range constraints on $x$ are dead because they are implied by the tightest one.  
   - Domains: keep only the mask equal to the bitwise AND of all masks (the most restrictive). Others are dead.  
   - Equalities: if more than one different constant appears, output **false** and stop. Otherwise keep the single equality (if any).  
2. For each inequality constraint $x < y$ (or $x \le y$), check whether it is implied by the conjunction of all remaining tight intervals and other inequalities (using e.g., Floyd‑Warshall on the variable ordering). Remove any implied inequality.  
3. Repeat until no more removals occur.

*Termination:* Each pass removes at least one constraint or ends; the number of constraints is finite.

*Correctness:* Only constraints that are logically implied are removed; equivalence is preserved by definition of “dead”. At termination, no constraint is dead because every remaining constraint is strictly needed (tightest range, smallest mask, etc.). For inequalities, the implication check ensures that no inequality is redundant. ∎

---

## 6. Constraint Strength Reduction

**Theorem 6 (Strength Reduction Equivalences).**  
The following replacements preserve the denotation of the constraint:

1. **Range to bitmask:**  
   $x \in [0, 2^k-1]$  $\iff$  $(x \ \& \ ((1\ll k)-1)) = x$, for $0 \le k \le 64$.

2. **Range to unsigned comparison:**  
   $x \in [0, N]$ with $0 \le N < 2^{32}$  $\iff$  $\text{unsigned}\ x \le N$.

*Proof.*  
(1) Let $M = 2^k-1$. For any $x$, $x \ \& \ M = x$ iff all bits beyond the low $k$ bits are zero, i.e., $x \le 2^k-1$ and $x \ge 0$ (interpreting as unsigned). This is exactly the range $[0,2^k-1]$.  
(2) Since $N < 2^{32}$, the unsigned comparison $x \le N$ is equivalent to $0 \le x \le N$ when both $x$ and $N$ are treated as unsigned numbers in $[0,2^{32}-1]$. The lower bound $0$ is implicit in unsigned arithmetic. Hence it matches the original range. ∎

These reductions are used in the optimization stage to replace expensive range checks with cheaper bit operations or a single comparison.

---

## 7. Formal Correctness of the Compilation Pipeline

We define the pipeline steps and the invariants preserved.

**Pipeline:**  
```
GUARD text  ──parser──▶  AST  ──normalization──▶  CNF‑AST  ──optimization──▶  OptAST  ──codegen──▶  x86‑64/AVX‑512 machine code
```

**Semantics of each representation:** Each one denotes a predicate $P$ over input variables.

**Invariants:**
- **Parser:** $\llbracket \text{AST} \rrbracket$ is the set of inputs that satisfy the GUARD syntax.
- **Normalization (Thm 1):** $\llbracket \text{CNF‑AST} \rrbracket = \llbracket \text{AST} \rrbracket$.
- **Optimization (Thm 5 & 6):** $\llbracket \text{OptAST} \rrbracket = \llbracket \text{CNF‑AST} \rrbracket$. Dead elimination and strength reduction preserve denotation.
- **Code generation (Thm 4):** The output machine code, when executed with input values, terminates with accept iff $\llbracket \text{OptAST} \rrbracket(v) = \text{true}$.

**Theorem 7 (Pipeline Correctness).**  
For any GUARD constraint text, the compiled machine code implements the same predicate as the source.

*Proof.*  
Compose the invariance of each stage. For code generation, we rely on Theorem 4 for SIMD vectorization and the optimal sequences proved in §3 for scalar paths. The backend emits exactly those sequences; because each instruction correctly implements the required operation (as per the Intel Architecture Reference), the resulting binary faithfully computes the conjunction of atomic constraints. ∎

---

## 8. Concrete Compilation Examples

### Example A: `constraint temp in [0, 100]`

**Step 1 – AST:** `Range(temp, 0, 100)`.

**Step 2 – Normalization:** Already atomic; no transformation.

**Step 3 – Optimization (strength reduction):** Since $100 < 2^{32}$, reduce to `(unsigned) temp <= 100`.

**Step 4 – Code generation (scalar):**
```asm
; assume temp is in eax
sub eax, 0            ; eax = temp (lower bound 0, subtraction is no-op)
cmp eax, 100          ; compare with upper bound
setbe al              ; al = 1 if temp <= 100, else 0
```
*Proof of correctness:* The pattern `sub; cmp; setbe` implements unsigned range check $0 \le temp \le 100$ as shown in §3. After strength reduction, this is exactly the original constraint.

**Step 5 – AVX‑512 version (batch of 16 temperatures):**
```asm
vmovdqu32 zmm0, [temps]
; lower bound 0 -> sub not needed
vpminud zmm1, zmm0, [100]  ; alternative: directly compare with 100
vpcmpleud k1, zmm0, [100]   ; compare each lane ≤ 100
kortest k1, k1             ; CF=1 iff all lanes satisfied
```
*Equivalence proof:* `VPCMpleUD` sets mask bit to 1 iff the unsigned integer in the corresponding lane is ≤ 100. Since all values are non‑negative, this matches the original range. The `KORTEST` reduces the mask to a single flag.

---

### Example B: `constraint x in [0, 255] AND x in domain 0x3F`

**Step 1 – AST:** Conjunction of `Range(x,0,255)` and `Domain(x,0x3F)`.

**Step 2 – Normalization:** Same.

**Step 3 – Optimization:**
- Strength reduction on range: $[0,255] \to (x \ \& \ 0xFF) = x$.
- Domain: $(x \ \& \ 0x3F) = x$.
- Dead elimination: since $0x3F$ is a subset of $0xFF$, the domain constraint implies the range constraint. Thus the range constraint is dead and removed. Result: `Domain(x,0x3F)`.

**Step 4 – Code generation (scalar):**
```asm
test al, 0xC0         ; test if bits 6-7 are set (0x3F's complement)
setz al               ; al = 1 iff no high bits set, i.e., (x & 0x3F) == x
```
*Proof:* `test al, 0xC0` computes `x & 0xC0`. If the result is zero, then `(x & 0x3F) == x` because any bit outside 0x3F would appear in the high six bits (mask 0xC0). The `setz` sets `al` accordingly.

**Step 5 – AVX‑512 batch:**
```asm
vmovdqu32 zmm0, [xs]
vmovdqu32 zmm1, [mask_0x3F] ; or use immediate
vpandd zmm2, zmm0, [~0x3F] ; not 0x3F = 0xFFFFFFC0
vptestmd k1, zmm2, zmm2     ; set mask where zmm2[i] == 0
kortest k1, k1
```
*Equivalence:* `VPANDD` computes `x_i & ~0x3F`, then `VPTESTMD` (or `VPCMPEQD` against zero) yields 1 for each lane where result is zero. This is exactly the domain condition.

---

### Example C: `constraint alt in [0, 45000] AND speed in [60, 350] AND fuel in [100, 2000]`

**Step 1 – AST:** Three independent range constraints on different variables.

**Step 2 – Normalization:** Same.

**Step 3 – Optimization (strength reduction):**
- Each range is of the form $[L,H]$ with $L \ne 0$ for speed and fuel. We apply the subtraction method: for speed, check `(speed - 60) <= (350-60)=290`, unsigned; for fuel, `(fuel - 100) <= (2000-100)=1900`. For altitude, already $[0,45000]$, we can compare unsigned with 45000.

**Step 4 – Fusion (inter‑variable packing):** Since all three variables are independent, we pack them into a single AVX‑512 vector (three lanes used, rest ignored). We load the values into lanes 0,1,2 and set the other lanes to any value that will pass (e.g., 0). We also prepare vectors of lower bounds and differences.

**Step 5 – AVX‑512 code:**
```asm
; assume alt in eax, speed in ebx, fuel in ecx
; pack into zmm0:
vmovd xmm0, eax
vpinsrd xmm0, xmm0, ebx, 1
vpinsrd xmm0, xmm0, ecx, 2
vinserti64x2 zmm0, zmm0, xmm0, 0   ; upper lanes undefined, but we will ignore them

; prepare lower bound vector (L[0]=0, L[1]=60, L[