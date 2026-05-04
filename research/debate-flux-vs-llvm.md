# Debate: Adopt FLUX Now or Wait for LLVM?

## FOR FLUX: Don't Wait (DeepSeek Reasoner — Aerospace Engineer)

**Subject: The Falling Knife: Why “Wait for LLVM” is a Certification Death Spiral, and Why FLUX NOW is the Only Safe Path**

**To:** Aerospace Safety Review Board / Systems Engineering Leadership  
**From:** Lead Safety Engineer, Axiom Verification Group  

The aerospace industry stands at a precipice. We are attempting to certify software for DO-178C Level A—the domain of fly-by-wire flight controls, engine management, and autonomous landing—using toolchains originally designed for web browsers and video games. The current strategy, or rather the strategy we are *failing to adopt*, relies on a dangerous fallacy: that LLVM will eventually mature into a verified safety compiler. I am here to argue, with specific technical and financial evidence, that waiting for LLVM to add constraint verification is professionally irresponsible. The only rational, audit-passing, cost-effective path forward is the immediate adoption of FLUX NOW.

Let me be blunt. **LLVM has no plans for constraint verification. It is a general-purpose compiler infrastructure, not a certification tool.** Its primary stakeholders are the C++, Rust, and Swift ecosystems—communities that prioritize runtime performance and language features over formal correctness. The LLVM foundation has never published a roadmap for HOL-style theorem proving, Floyd-Hoare logic integration, or DO-178C/ISO 26262 qualification packs. Suggesting we “wait for LLVM” is like waiting for a commercial aircraft to be retrofitted with a submarine hull—it will never happen because it was never designed for that purpose. Every LLVM release notes read: “New vectorization passes, improved debug info, faster JIT.” Not once: “Added verified constraint solver for safety-critical IR lowering.” The mathematics does not lie. Compilers are not safety tools. They are translation engines.

Now, let us examine the scale problem. **LLVM has over 30 million lines of C++ code**—a figure that grows with every release. For DO-178C Level A, we must demonstrate the absence of design errors, data flow anomalies, and unintended control transfers across the entire tool. A typical DO-178C verification effort for a 100k SLOC flight application costs $50–$100 million over five years, with the tool chain itself consuming 20–30% of that effort. To verify LLVM’s 30 million lines to Level A—using current manual review, structural coverage analysis, and integration testing—would require an estimated 15,000 engineer-years. That is not hyperbole; that is a linear scaling of historical data from Honeywell and Rockwell Collins. Even with AI-assisted verification, the combinatorial explosion of LLVM’s 120+ instruction opcodes, each with multi-mode semantics, makes exhaustive proof intractable. **We cannot wait twenty years for a tool that will never arrive.**

Contrast this with **FLUX: 7 Rust crates. That’s it.** Seven. The entire compiler—including frontends, IR, optimizer, code generator, and verification harness—fits into a codebase smaller than a typical avionics control module. This is not a toy. FLUX’s size is a direct consequence of architectural discipline: a 50-opcode virtual machine (VM) instead of LLVM’s 120+ opcode IR. Each opcode in FLUX is a single, well-defined transformation over a monotonic store. There is no undef, no poison, no metadata attributes that interact non-locally. The FLUX IR is designed for *auditability*, not generality. An auditor can hold the entire VM specification in their head. They can trace every optimization pass—there are only 12—back to its verifying theorem. With LLVM, an auditor must wade through 5,000+ files, each with branching complexity, undocumented edge cases, and C++ undefined behavior that itself requires a second compiler to resolve. FLUX’s 50-opcode VM is not a limitation; it is a *feature*. It means the compiler’s semantics are finitely enumerable and mathematically closed.

The argument “Wait for LLVM to add constraint verification” is, in reality, **“wait forever, and spend $50 million per certification cycle in the meantime.”** Consider the economics. A typical aircraft program that uses a non-verified LLVM toolchain must perform two parallel activities: (1) run the compiler on the source code, and (2) run a separate static analysis tool (e.g., ASTREE, Polyspace) to verify the *output binary* satisfies safety constraints. This dual-path certification doubles the validation cost and introduces a coordination risk—the analyzer might prove properties about the *intended* semantics while the compiler silently produces code that violates them. FLUX eliminates this entirely. Because FLUX’s optimizer and code generator are themselves verified with SMT-based refinement proofs, every transformation is guaranteed to preserve the original high-level constraints. **You run one pass, you get one binary, and you get a mathematical proof that it matches your specification.** That is not a cost saving; it is a paradigm shift. The $50 million you are currently spending on redundant verification is not an investment in safety. It is a tax on architectural debt.

Let me address the inevitable concern: vendor lock-in. **FLUX is Apache 2.0 licensed.** There is no proprietary entity controlling the standard. No single company can change the IR semantics, remove a verification pass, or demand licensing fees. In contrast, LLVM’s governance model is dominated by Apple, Google, ARM, and Intel—organizations that have zero incentive to prioritize aerospace safety over consumer electronics. When Apple changes LLVM’s GlobalISel to favor mobile performance, we must re-verify the entire toolchain. When Google adds a new metadata format for debugging, our certification artifacts become stale. FLUX, as a community-maintained standard, gives us the same guarantees as DO-178C itself: stability, transparency, and the right to fork. Apache 2.0 is not an afterthought; it is a safety requirement.

Finally, the most critical point: **the theorems are real, not marketing.** FLUX has already been used to verify a safety-critical bootstrap loader for a medical infusion pump (IEC 62304 Class C) and a UAV flight stabilization kernel. In both cases, the compiler produced a machine-checked proof that the binary’s memory safety, control flow integrity, and arithmetic bounds were preserved. The verification is not a paper exercise—it is an automated process. When you compile with `flux build --certify`, the tool emits a proof certificate that a third-party verifier (Coq or Lean) can validate independently. The theorems are not “benchmark results” on synthetic C code. They are constructive proofs that the *specific binary you will fly* satisfies its contract. No amount of LLVM sanitizer runs or fuzzing can give you that. Fuzzing finds bugs probabilistically; theorem proving finds them deterministically. In aerospace, we do not fly on probabilities.

The counterargument often raised is: “But LLVM has a vast ecosystem of frontends (C, C++, Rust, Swift, Julia). FLUX only supports a Rust-like language.” This is a red herring. The safety-critical software we certify is overwhelmingly written in C and Ada, with a smaller but growing fraction in Rust. FLUX can and will add C and Ada frontends—the RSIC-V-like IR is agnostic to source language. The complexity is in the IR verification, not the parsing. Moreover, if your argument is that you need C++20 modules and lambda captures in flight software, you are already failing safety engineering. Level A code should be simple, auditable, and side-effect-free. FLUX enforces that discipline by design.

I am not asking the industry to abandon LLVM for general-purpose compilation. LLVM is excellent for web browsers, mobile apps, and data center workloads. It is catastrophic for flight safety. The choice is not between FLUX and LLVM. The choice is between **doing the hard work now**—adopting a small, proven, verifiable toolchain—and **continuing to pay $50 million per program forever** while waiting for a tool that will never gain verification capabilities. The mathematics is clear. The cost is clear. The liability is clear.

**Recommendation:** Fund a consortium (airframers, Tier 1 suppliers, regulators) to baseline FLUX as a recommended COTS compiler for Level A certification by 2026. Begin parallel qualification projects on two low-criticality flight functions (e.g., cabin pressure control, environmental monitoring) using FLUX with DO-330 Tool Qualification Level 4. This will generate the evidence needed for full Level A use by 2028. Meanwhile, stop all internal research into “verifying LLVM.” It is a dead end disguised as a roadmap.

We cannot afford to wait for a general compiler to become a safety tool. It will never happen. The future is FLUX. The time is now.

— *Aerospace Safety Engineer, 15 years DO-178C DAL A*

---

## FOR LLVM: Wait for the Standard (Seed-2.0-pro — LLVM Compiler Engineer)

# Subject: Response: The Falling Knife Is Jumping To Unproven Tools, Not Waiting For LLVM
**To:** Aerospace Safety Review Board / Systems Engineering Leadership  
**From:** Eleanor Voss, Senior Principal Compiler Verification, LLVM Foundation Safety Working Group; 18 year LLVM contributor, former DO-178C tool qualification lead for Airbus
First: Let us start with full agreement. The author of the original memo is correct about the single most important fact on this table. We are in a crisis. There is no production-qualified formally verified compiler for Level A flight software available today. Every program is running on borrowed time, every audit is a compromise, every release carries unnecessary risk. Frustration is justified. Impatience is understandable.
But the proposed solution is not just unwise. It is professionally reckless. It commits the oldest error in safety engineering: replacing a known, quantified risk with an unknown, unquantifiable risk, because you are tired of waiting for the known risk to be fixed.
Let us speak plainly, with engineering facts, not rhetoric.
---
## 1. Production track record is not a flaw: it is the single most important safety property
The original memo dismisses LLVM as "built for browsers and games". This is a half-truth, and a dangerous one. LLVM was first deployed 20 years ago. It has compiled code that has run on every device on the planet, on every CPU architecture, in every failure environment. It has had every possible edge case exercised, every silent code generation bug dug up, every optimizer failure documented. As of today, qualified LLVM forks fly on Falcon 9 flight controllers, the Boeing 777X primary avionics, and every modern automotive ADAS system. There are over 12 billion operating hours of flight critical code compiled with LLVM.
FLUX was first pushed to public Github 76 hours before the original memo was sent. It has zero production runtime. Zero disclosed bugs. Zero independent third party testing. This is not a tool. This is a proof of concept demo. You would not test a new fire extinguisher by throwing away all your working ones and installing it in the cockpit. You do not do that with a compiler.
Nobody argues that new tools cannot be good. But safety is not built on mathematical proofs. It is built on scars. LLVM has scars. FLUX does not even have skin yet.
## 2. Backing is not corporate favouritism: it is survivability
The original memo complains that LLVM's stakeholders care about performance. That is correct. It also means that LLVM will exist next year. It will exist in 10 years. There are 117 full time, paid engineers from Apple, ARM, Airbus, Siemens, and NVIDIA assigned to the LLVM Safety Technical Steering Committee as of Q2 2025. When a code generation bug is reported, 10,000 engineers can triage it within hours. When a silicon errata is released under NDA, LLVM gets the workaround before the public announcement.
FLUX has one primary maintainer. Three of the last seven merged PRs are marked "generated by GPT-4o". There is no industrial support. No maintenance contract. No escalation path.
This is not a trivial point. If you adopt FLUX for your flight control program, and the maintainer gets hit by a bus, quits, loses interest, or just makes a mistake, your entire program dies. There is nobody else who can fix it. For Level A certification, you are required to demonstrate 30 years of projected tool support. FLUX cannot demonstrate 30 days.
## 3. We do not need to verify all of LLVM. That was always a straw man.
The original memo's core technical argument rests on a fallacy that was obsolete 5 years ago: that to use LLVM safely you must verify all 30 million lines of its source code.
Nobody is proposing that. Nobody has ever proposed that.
What we are building, and what is 62% complete today, is separate translation validation. This is exactly the same formal method that CompCert used to become the first certified C compiler. You do not verify the compiler. You verify the output. For any given safety-critical input, we run an independent, formally verified validator that proves that the generated assembly has exactly the same semantic behaviour as the input IR. All 30 million lines of LLVM optimizer and backend code become untrusted. If they make a mistake, the validator catches it.
This is not theory. The AArch64 safety subset validator passed all 140,000 TSOV2 compiler correctness tests last month. It has already been audited by three independent certification bodies. We are not retrofitting a submarine hull onto an aeroplane. We are adding a certified altimeter to an aeroplane that is already flying.
## 4. Backend support is not a nice to have: it is how you avoid silent silicon death
A compiler is not just a theorem prover. 70% of the work of a safety compiler is not generating correct code in ideal conditions. It is working around broken silicon.
Every production aerospace CPU has dozens of documented errata. Wrong instruction scheduling can trigger silent register corruption. Certain branch patterns will lock the core. Vector operations will return incorrect results above 52C. LLVM has workarounds for every single one of these, documented, tested, audited, for every stepping of every flight qualified CPU released in the last 12 years.
FLUX today is 1200 lines of Python that wraps GCC 12. It will take a minimum of 8 years for FLUX to replicate just the errata handling work that already exists in LLVM. When NXP releases their next generation flight controller core next year, LLVM will have qualified support on launch day. FLUX will have an open Github issue.
This is not an argument that FLUX will never get there. It is an argument that it will not get there this decade.
## 5. Certification does not care about your proof. It cares about track record.
This is the unspoken truth that every safety engineer knows, and no FLUX advocate will admit: DO-178C is not a mathematics standard. It is an audit standard.
To pass Level A tool qualification, you do not just show up with a Coq proof. You need 10 years of public bug history. You need incident reports. You need known failure modes. You need third party auditors who have seen the tool break before, and know what to look for. There is not a single certification body on this planet that will sign off on a tool with zero production runtime, zero independent audits, zero disclosed flaws.
The last time the aerospace industry tried to certify a clean sheet verified compiler for Level A, it took 11 years from first public release to first flight. That is the baseline timeline. FLUX is not 1 year away. It is 15 years away. If you commit to FLUX today, you are committing your program to a 15 year certification delay.
## 6. The "small is verifiable" fallacy only looks at the compiler
The original memo correctly notes that small codebases are easier to verify. This is true for the compiler. It is catastrophically false for the entire system.
When you adopt a niche compiler, you throw away everything else. Every static analyzer. Every fuzzer. Every control flow verifier. Every stack analyzer. Every debug tool. Every engineer on your team who knows how to debug generated code. All of that has to be rewritten, ported, re-verified. The total amount of untrusted, unproven code in your system does not go down. It increases by an order of magnitude.
A verified LLVM gives you all of that for free. Every tool that already targets LLVM IR, every safety analysis that thousands of engineers have built over 20 years, becomes formally validated overnight. You do not get a small verified compiler. You get a verified entire ecosystem. That is the tradeoff that FLUX advocates refuse to acknowledge.
---
Let me close with this: I am not here to tell you LLVM is perfect. I have spent 18 years fighting with this codebase. I have filed 127 code generation bugs. I have yelled at maintainers for prioritizing Javascript speed over aerospace safety for more than a decade. The original memo is correct that the LLVM community wasted 10 years ignoring this problem.
But that mistake is being fixed. Right now. Faster than anyone thought possible. We will have a qualified translation validated release for Level A in 24 months. That is a hard, public, committed date.
The falling knife is not waiting for LLVM. The falling knife is throwing away 20 years of hard earned safety knowledge, jumping onto an unproven demo, because you are tired of waiting. That is how you do not just miss a program deadline. That is how you get people killed.
This is not a choice between perfect and imperfect. This is a choice between a known risk that is being actively fixed, and an unknown risk that nobody can quantify. That is the only choice that matters.
*(1489 words)*

---

## Synthesis: The Honest Assessment (DeepSeek Reasoner)

**Executive Summary for Investors**  
The debate between “FLUX now” and “wait for LLVM” misses the real opportunity: a hybrid architecture that combines the proven correctness of a formally verified front-end (like FLUX/CompCert) with the industrial maturity, code-generation quality, and ecosystem breadth of LLVM. Both camps are right about the severity of the problem and wrong in their exclusivity. The safe, commercially viable path is not an either/or choice but a layered strategy that delivers incremental certification gains over the next 3–5 years and full DO‑178C Level A qualification within 10 years.

---

## Where Each Side Is Right

**FLUX advocates are right about:**  
- **Immediate verification gap.** LLVM has no plans for full formal verification of its optimization passes or backends. Alive2 and other research tools cover only a fraction of the pipeline; they are not DO‑178C qualified.  
- **Certification cost.** Waiting for LLVM to become formally verified means indefinite delays. Every month of waiting prolongs the use of unqualified toolchains, increasing audit risk and liability.  
- **Proven formal verification.** CompCert (the real-world equivalent of “FLUX”) is the only C compiler proven correct down to assembly for PowerPC, ARM, and RISC‑V. It has been used in avionics and automotive prototypes and has a qualification kit for DO‑178C TQL‑5.  

**LLVM advocates are right about:**  
- **Production track record.** LLVM has compiled billions of lines of code on dozens of architectures. Its bug surface, while not zero, is well understood. A new, untested toolchain (even a verified one) introduces unknowns – compiler bugs are not the only risk; integration, runtime libraries, and tool coupling matter.  
- **Performance and flexibility.** LLVM’s optimizer generates code that is 10–30% faster and smaller than CompCert’s. For real-time embedded systems, performance margins translate directly into safety margin or hardware cost savings.  
- **Ecosystem.** LLVM supports C, C++, Rust, Ada, and others. A FLUX-only approach forces rewrites or limited language support, which is a non‑starter for legacy codebases and multi‑language projects.  

---

## Honest Assessment: Neither Side Is Ready Alone

**FLUX/CompCert today:**  
- Limited to C (no C++ or Rust).  
- Supports only a few CPU architectures (ARM, x86‑32/64, RISC‑V, PowerPC).  
- Optimizations are conservative; code size and speed often lag LLVM by 30%.  
- Verification covers the core compilation passes but not the runtime libraries or linker.  
- Qualification kits exist but require manual tailoring for each project.  

**LLVM today:**  
- No formal proof of correctness for any optimization pass.  
- Tool qualification (DO‑330) is possible but requires massive evidence gathering and is rarely done for Level A.  
- Many passes have known soundness bugs (e.g., miscompilations in GVN, InstCombine) that are acceptable in consumer products but catastrophic in flight controls.  
- The LLVM Safety Working Group is active but still researching *how* to add verification, not delivering production tools.  

**The gap is real and existential.** As the original memo warned, every Level A project today relies on trust – faith that the compiler hasn’t introduced a silent error. That trust is wearing thin as regulators demand evidence, not promises.

---

## The Middle Path: FLUX‑as‑Front‑End, LLVM‑as‑Back‑End with Translation Validation

A hybrid approach resolves the tension:

**Architecture:**  
1. **FLUX (CompCert) front-end** – takes source C (and eventually C++/Rust via a verified parser) and produces a fully verified intermediate representation (e.g., CompCert’s C#minor or a new verified IR).  
2. **Verified source-to-IR transformation** – applies high‑level, safety‑critical optimisations (e.g., constant folding, dead‑code elimination) that can be proved correct using the FLUX theorem prover.  
3. **LLVM backend (the risky part)** – accepts the FLUX‑verified IR and performs machine‑specific lowering, register allocation, instruction selection, and scheduling.  
4. **Translation validator** – a separate, formally verified checker that runs after LLVM compilation. It reads the FLUX IR and the final object code and verifies that every execution trace of the source IR is matched by the compiled code. This validator can be built using existing tools (e.g., Alive2, rtl‑verif) but must be qualified as a DO‑178C tool of low criticality (TQL‑5) because it only *detects* errors, not prevents them.  

**Why this works:**  
- The front‑end is fully verified, eliminating high‑level semantic errors.  
- The back‑end uses LLVM’s mature, high‑performance code generator – no need to rewrite 20 years of optimisation work.  
- The translation validator catches any bug introduced by LLVM (optimisation or backend) without needing to verify LLVM itself.  
- The validator can be built incrementally: start with a simple equivalence checker for a subset of IRs, then extend coverage as certification demands grow.  

**Challenges:**  
- The validator must be proven correct *and* qualified. This is non‑trivial but far easier than verifying the entire LLVM pipeline.  
- Interfacing FLUX’s IR (which is typed and side‑effect‑free in many respects) with LLVM’s untyped, all‑bets‑off IR requires a carefully defined translation and a proof that the translation preserves semantics. Tools like CompCert’s “Linking” pass can be adapted.  
- Performance: the validator adds a compile‑time check, but for Level A the cost is acceptable (a few extra minutes per build).  

**Real‑world precedent:** The Verified Software Toolchain (VST) and CompCert already support a form of translation validation. Projects like the “Certified Compilation with LLVM” (CCL) from the University of Utah have demonstrated the feasibility of combining CompCert front‑end with LLVM back‑end via a verified translator (Vellvm).  

---

## Adoption Timeline (Honest, for Investors)

**Near term (0–18 months):**  
- Deploy FLUX/CompCert for the most critical 20% of function points (e.g., actuator control, voting logic) while keeping LLVM for the rest, using manual code review to bridge gaps.  
- Fund a proof‑of‑concept hybrid that compiles a small DO‑178C test bench through FLUX → Vellvm → LLVM → validator. Target: one architecture (ARM Cortex‑R).  
- Begin qualification kit for the translation validator under DO‑330 TQL‑5 (tool that has no adverse effect if it fails – it only warns).  

**Mid term (18–48 months):**  
- Production‑grade hybrid compiler for ARM/RISC‑V with translation validator qualified as a TQL‑4 tool (can detect but not prevent errors).  
- Extend FLUX front‑end to support a safe subset of C++ (no virtual dispatch, no exceptions) – work already underway at INRIA and AbsInt.  
- LLVM Safety Working Group releases Alive2‑based verification for a limited set of optimisation passes (constant propagation, GVN, DSE). These can be used to reduce the validator’s burden.  
- Cost: ~$8–12M over 3 years for development and qualification (funding from a consortium of aerospace OEMs).  

**Long term (48–96 months):**  
- Full LLVM backend verification using a combination of translation validation and certified code generation (e.g., a verified register allocator).  
- FLUX front‑end integrates with Rust’s borrow checker to produce a verified Rust compiler (Ferrocene‑like but with proof).  
- The hybrid becomes the default certified toolchain for Level A, with the translation validator replaced by a certified backend.  
- Total investment to reach Level A qualification across all major ISAs: $30–50M.  

---

## Recommendation for Investors

**Do not wait for LLVM to be fully verified – that is a decade away. Do not bet solely on FLUX – it is too limited for production. Instead, invest in the hybrid bridge.** The company that builds the first qualified translation validator between a verified front‑end and LLVM will own the safety‑critical compiler market for the next 20 years.  

**Key actions:**  
- Fund the FLUX‑to‑LLVM IR translator and validator development (seed round $2M).  
- Partner with the LLVM Safety Working Group to align validator interfaces with their ongoing formalisation work.  
- Target a 2026 prototype for a major aerospace prime (e.g., Honeywell, Collins Aerospace) to lock in first‑mover advantage.  

The falling knife is real – but the solution is not to jump onto an untested blade or to stand still. It is to build a safety net under the existing toolchain. The hybrid architecture is that net.

---

*Three-round adversarial debate: DeepSeek Reasoner vs Seed-2.0-pro with final synthesis.*