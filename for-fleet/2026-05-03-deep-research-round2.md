# Deep Research Round 2: Multi-Model Multi-Angle Analysis

**Date:** 2026-05-03  
**Models used:** Seed-2.0-pro, Seed-2.0-code, GLM-5.1, Kimi, Nemotron-3-Super, Seed-2.0-mini  

---

## Models and Angles

| Model | Angle | Key Insight |
|-------|-------|-------------|
| **Seed-2.0-pro** | DO-254 certification expert (real Vivado numbers) | 1,717 LUTs, 120mW total. HALT IS NOT SAFE STATE. TMR on control only. 90-day build plan. |
| **Seed-2.0-code** | Mathematical physicist / category theorist | Bitmask functor is a logical morphism of topoi. BHCSP framework unifies classical + quantum CSP. |
| **GLM-5.1** | Verified compiler engineer | Complete IR design: CIR → LCIR → FLUX/HW fork. 6 proof obligations. 40-70K LoC in Coq. |
| **GLM-5.1** | Formal methods researcher | "The critics are right." P2 (invariant preservation on every transition) is the proof that changes everything. |
| **Kimi** | VC / technology strategist | This is a tool company, not a platform. $8M pre-seed. Exit: $50-150M to Siemens/Cadence. |
| **Kimi** | Red team lead | "Physically impossible" is provably false. 5 attack vectors. Compiler is the real weak link. |
| **Nemotron-3-Super** | Quantum computing researcher | CSP-quantum isomorphism is real but limited to diagonal projectors. Quantum advantage requires QCSP for quantum-native problems. |
| **Seed-2.0-mini** | Safety certification auditor | Unmitigated FPGA SEU in config memory is the #1 gap. Parity doesn't catch double-bit EMI glitches. |

---

## Cross-Model Convergence (All Agree)

1. **Halt is not a safe state** — Every model with safety expertise agrees. The FPGA must transition to a *defined hazard-free state*, not just stop.
2. **The compiler is the attack surface** — Formal verification of the bytecode generator is non-negotiable.
3. **Bitstream security matters** — Encrypt + authenticate the bitstream. JTAG must be disabled in production.
4. **SEU mitigation is critical** — FPGA configuration memory is volatile and vulnerable to radiation.
5. **This is a tool/IP company** — Not a chip company, not a platform. Position accordingly.

---

## Unique Breakthroughs Per Model

### Seed-2.0-pro: Real Hardware Numbers
- **1,717 LUTs, 1,807 FFs, 0 BRAM, 120mW** (1.7% of Artix-7 100T)
- Partial TMR is sufficient (DO-254 §6.3.2.2 Note 3)
- EDC on comparator lines is over-engineering (safe failures don't need mitigation)
- Separate power/clock domains is "cargo cult" — all DAL A Artix-7 designs use single global clock
- Safe-state: interlock pin → force comparators to safe value → NOP forever → fault code → 1Hz toggle
- Only power cycle clears fault latch

### Seed-2.0-code: Mathematical Framework (BHCSP)
- **Bitmask Functor Theorem**: Bit: E_U → H_64 is a logical morphism of topoi
- Speedup ratio = |D| (domain cardinality), exactly matching 12,324×
- Holonomy acts as automorphisms of the bitmask Boolean lattice
- Drift = Hamming distance between bitmask permutation and identity
- "Below C" = logical morphism to hardware topos; "close to physics" = full embedding in dagger compact categories
- Classical CSP ≅ commuting quantum CSP (diagonal projector sublattice)
- POPCOUNT = trace of projector (quantum observable)

### GLM-5.1: Compiler Pipeline (CIR → LCIR → FLUX/HW)
- **CIR** (Constraint IR): Relational, quantified, temporal modalities
- **LCIR** (Lowered CIR): ANF, explicit state, bounded quantifiers, basic blocks
- **Fork point**: LCIR branches to FLUX path (monitoring) or HW path (guarded transitions)
- **6 Proof Obligations**: P1 (type safety), P2 (invariant preservation), P3 (termination), P4 (refinement), P5 (monotonicity), P6 (equivariance)
- **P2 is the proof that changes everything** — proving invariant holds on every transition
- Estimated: 40-70K LoC in Coq, 2-3.5 years

### Kimi VC: Business Reality
- **Pre-seed $500K-$1.5M**, valuation $6-12M pre-money
- **Tool/IP company** — not chip, not platform
- TAM: $200-400M SOM (not $68B FPGA market)
- Top acquirers: Siemens EDA ($50-150M), Cadence ($30-100M), Synopsys ($25-80M)
- Failure mode #1: Certification chasm (2-4 years, $2-5M per product)
- Failure mode #2: EDA bundling (Cadence checks the box for free)
- What VC needs: revenue, cert roadmap, ecosystem partner, team with certified silicon experience

### Kimi Red Team: 5 Attack Vectors
1. **TMR tear-down via common-mode** — EM pulse hits all 3 replicas in same clock region
2. **Bitstream manipulation** — flip comparator safe-state constants
3. **Stack parity evasion** — metastable write with correct parity for wrong data
4. **Dead-man switch sabotage** — $2 555 timer replaces FPGA interlock
5. **u64 overflow** — arithmetic overflow truncates constraint domain

**Side channels**: Power analysis reveals opcode sequence AND constraint thresholds

**Kill chain**: Power recon → compiler supply chain attack → poisoned bytecode → fault injection backup

### Nemotron: Quantum Connection
- CSP-quantum isomorphism is rigorous but limited to diagonal projectors
- Classical bitmask CSP = commuting QCSP (Birkhoff-von Neumann)
- No quantum advantage for general CSPs (Grover is worse than CDCL)
- Quantum advantage requires: (a) constraint projectors forming quantum-expander graph, (b) classical propagation stuck due to symmetries, (c) quantum walks break symmetries
- "Where the isomorphism ends (non-diagonal projectors) is where quantum novelty begins"
- Quantum-native enforcement: constraints as quantum channels, propagation via Lüders rule

### Seed-2.0-mini: Auditor's Perspective
- **#1 gap: unmitigated SEU in FPGA configuration memory**
- A single cosmic ray can rewrite FLUX bytecode, bypassing all safety
- Parity fails on double-bit EMI glitches (preserve parity, corrupt value)
- Must scrub configuration memory or use radiation-hardened FPGA
- Need: independent sensor path (not through main CPU), cryptographic heartbeat, third-party proof review

---

## Actionable Takeaways

### Immediate (Before Any FPGA Work)
1. Design safe-state as defined hazard-free state, NOT halt
2. Add configuration memory scrubbing (SEU mitigation)
3. Encrypt + authenticate bitstream (Artix-7 supports AES)
4. Disable JTAG in production builds
5. Add overflow traps on all arithmetic before constraint checks

### Short-term (90 Days)
1. Implement FLUX mini on Artix-7 per Seed-Pro's 90-day plan
2. Write formal semantics for all 43 opcodes in Coq
3. Design constraint DSL with CIR → LCIR → FLUX pipeline
4. Prove P2 (invariant preservation) on abstract machine

### Strategic
1. Position as tool/IP company targeting formal verification acceleration
2. Target avionics Tier 2 suppliers (not prime OEMs)
3. Build partnership with Siemens EDA or Cadence
4. Focus on certification cost reduction, not performance
5. The "quantum FLUX" angle is for QCSP, not classical CSP — publish as research

---

*Generated by Forgemaster ⚒️ from 8 model analyses across 6 different perspectives*
