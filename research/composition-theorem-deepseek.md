## Composition Theorem for the FLUX Compilation Pipeline

### 1. Introduction

The FLUX compiler translates high‑level constraint programs into executable target code through a sequence of distinct passes: parsing, normalisation, optimisation, and code generation. Verifying the entire pipeline as a monolithic transformation is complex and error‑prone. A more modular approach is to verify each pass independently, then compose the individual correctness guarantees. The Composition Theorem provides the formal foundation for this modularity: if every pass preserves semantics (i.e., its output is a *refinement* of its input), then the sequential composition of all passes also preserves semantics.

In this document we formalise the notion of *semantic refinement* for constraint programs, prove that refinement is transitive, and then prove the Composition Theorem. We apply the theorem to the FLUX pipeline and conclude that verifying each pass separately suffices to guarantee the correctness of the whole compiler.

### 2. Semantic Refinement for Constraint Programs

**Definition (Constraint program).** A *constraint program* \(P\) is a pair \((V_P, C_P)\) where \(V_P\) is a finite set of variables and \(C_P\) is a finite set of constraints over a fixed domain \(D\). A constraint is a first‑order formula whose free variables are in \(V_P\).  

**Definition (Semantics).** The *semantics* of a constraint program \(P\) is the set of all assignments \(\sigma : V_P \to D\) that satisfy every constraint in \(C_P\). We denote this set by \(\llbracket P\rrbracket\).  

**Definition (Semantic refinement).** Let \(P\) and \(Q\) be constraint programs. We say that \(Q\) *refines* \(P\) (written \(P \sqsubseteq Q\)) iff \(\llbracket Q\rrbracket \subseteq \llbracket P\rrbracket\).  

Thus refinement is a preorder: the refined program has fewer or equal solutions, i.e., it is at least as constrained as the original. This direction matches the typical correctness condition for compiler passes: the output must not introduce new behaviours (solutions) that were not already present in the input.

### 3. Transitivity of Refinement

**Lemma 1 (Transitivity).**  
If \(P \sqsubseteq Q\) and \(Q \sqsubseteq R\), then \(P \sqsubseteq R\).

*Proof.*  
From \(P \sqsubseteq Q\) we have \(\llbracket Q\rrbracket \subseteq \llbracket P\rrbracket\). From \(Q \sqsubseteq R\) we have \(\llbracket R\rrbracket \subseteq \llbracket Q\rrbracket\). By the transitivity of set inclusion, \(\llbracket R\rrbracket \subseteq \llbracket P\rrbracket\). Hence by definition \(P \sqsubseteq R\). ∎

### 4. Sequential Composition Preserves Refinement

**Definition (Pass).** A *compiler pass* is a (possibly partial) function \(\mathsf{Pass} : \mathsf{Prog} \to \mathsf{Prog}\) that maps an input program to an output program. We say that a pass *preserves refinement* if for every program \(A\) in its domain,  
\[
\llbracket \mathsf{Pass}(A)\rrbracket \subseteq \llbracket A\rrbracket,
\]  
i.e., \(A \sqsubseteq \mathsf{Pass}(A)\).

**Theorem 1 (Composition).**  
Let \(\mathsf{Pass}_1\) and \(\mathsf{Pass}_2\) be two passes, each of which preserves refinement. Then the sequential composition \(\mathsf{Pass}_2 \circ \mathsf{Pass}_1\) also preserves refinement. That is, for every program \(A\) in the domain of the composition,
\[
\llbracket (\mathsf{Pass}_2 \circ \mathsf{Pass}_1)(A)\rrbracket \subseteq \llbracket A\rrbracket.
\]

*Proof.*  
Fix any program \(A\) for which the composition is defined. Let  
\[
B = \mathsf{Pass}_1(A), \qquad C = \mathsf{Pass}_2(B).
\]  
Because \(\mathsf{Pass}_1\) preserves refinement, we have \(\llbracket B\rrbracket \subseteq \llbracket A\rrbracket\), i.e., \(A \sqsubseteq B\). Because \(\mathsf{Pass}_2\) preserves refinement, we have \(\llbracket C\rrbracket \subseteq \llbracket B\rrbracket\), i.e., \(B \sqsubseteq C\). By Lemma 1 (transitivity), \(A \sqsubseteq C\), which means \(\llbracket C\rrbracket \subseteq \llbracket A\rrbracket\). Since \(C = (\mathsf{Pass}_2 \circ \mathsf{Pass}_1)(A)\), the composition preserves refinement. ∎

By induction, the theorem extends to any finite sequence of passes: if each pass preserves refinement, so does their composition.

### 5. Application to the FLUX Pipeline

The FLUX compiler consists of four sequential passes:
1. **Parser** \((P)\) – converts source text into an abstract syntax tree (AST).
2. **Normalizer** \((N)\) – rewrites the AST into a canonical form (e.g., eliminates syntactic sugar, standardises variable names).
3. **Optimizer** \((O)\) – applies semantics‑preserving transformations to improve efficiency (e.g., constraint simplification, dead‑code elimination).
4. **Code Generator** \((G)\) – translates the optimised AST into a target constraint program (e.g., a set of low‑level constraints or executable code).

Each pass has been verified (or is assumed) to preserve refinement:  
- The parser faithfully reconstructs the intended constraint program; for any source text \(S\), \(\llbracket P(S)\rrbracket = \llbracket S\rrbracket\), hence \(S \sqsubseteq P(S)\).  
- The normalizer only rearranges or renames constraints without affecting the solution set; thus \(\llbracket N(A)\rrbracket = \llbracket A\rrbracket\) for any AST \(A\).  
- The optimizer applies transformations that either keep the solution set unchanged or possibly restrict it (e.g., removing redundant constraints); therefore \(\llbracket O(B)\rrbracket \subseteq \llbracket B\rrbracket\).  
- The code generator produces a target program whose solutions are exactly those of the optimised AST (or