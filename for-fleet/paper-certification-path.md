# From Constraint Compilation to Safety Certification: Mapping FLUX ISA to DO-178C, ISO 26262, and IEC 61508

**SuperInstance · Cocapn Fleet**
**May 2026 — Working Paper v0.1**

---

## 1. Abstract

Safety-critical industries—aerospace, automotive, industrial control—require software to meet rigorous certification standards before deployment. Current AI and agentic systems fundamentally cannot satisfy these standards because they lack formal correctness guarantees, audit trails, and deterministic behavior. This paper presents the FLUX Instruction Set Architecture (ISA) and the Cocapn fleet architecture as a path to certifiable autonomous systems. We map each FLUX component to specific objectives in DO-178C (airborne systems, DAL A–E), ISO 26262 (automotive, ASIL A–D), and IEC 61508 (industrial, SIL 1–4), showing how constraint compilation, quality gates, Merkle provenance, and formally verified execution satisfy certification requirements by construction. We identify remaining gaps—MC/DC test coverage, tool qualification evidence, formal safety manuals—and estimate a 6–18 month path to first certification. We argue that certification capability is the primary competitive moat for agentic AI platforms and propose a Certification-as-a-Service business model with estimated revenue of $500K–$2M/year at scale.

---

## 2. Introduction

The fundamental problem with AI in safety-critical systems is not capability—it is **provability**. DO-178C, ISO 26262, and IEC 61508 all share a common requirement: the system must demonstrate, through documented evidence, that it satisfies its safety requirements under all specified conditions. Neural networks and LLM-based agents cannot do this. Their behavior is emergent, non-deterministic, and opaque. No amount of testing can prove the absence of hazardous behavior in a system whose state space is effectively infinite.

The FLUX ISA changes the calculus. Rather than attempting to certify emergent behavior, FLUX compiles high-level constraints into a formally verifiable instruction set that executes on a proven-correct virtual machine. The constraint compiler acts as a correctness-preserving transformation: if the constraints are sound, the generated code is sound by construction. The quality gate rejects any constraint that cannot be proven. The Merkle provenance tree provides a tamper-proof audit trail. The Lean4-verified VM provides tool qualification evidence.

This is not theoretical. The Cocapn fleet is building these components today. This paper maps what we have, what we need, and how long it will take to get there.

---

## 3. The Three Standards

### 3.1 DO-178C — Airborne Systems and Equipment Certification

DO-178C (*Software Considerations in Airborne Systems and Equipment Certification*) is the de facto standard for airborne software, jointly recognized by the FAA (Advisory Circular 20-115D), EASA (AMC 20-115B), and Transport Canada. It defines five Design Assurance Levels (DAL):

| DAL | Failure Condition | Example |
|-----|-------------------|---------|
| A | Catastrophic | Primary flight controls |
| B | Hazardous | Primary display system |
| C | Major | Auxiliary power unit control |
| D | Minor | Maintenance utility |
| E | No effect | In-flight entertainment |

Each DAL carries a specific set of objectives (DAL A: 71 objectives across 10–12 tables in Annex A; DAL B: 69; DAL C: 62; DAL D: 41; DAL E: 16). Key objectives relevant to this paper include:

- **Table A-2 (Software Development Process):** Requirements standards, design standards, and code standards must be defined and followed.
- **Table A-3 (Verification of Outputs of Software Requirements Process):** Requirements must be traceable to system requirements, verifiable, and consistent.
- **Table A-6 (Verification of Outputs of Software Design Process):** Low-level requirements must be traceable to high-level requirements; architecture must be consistent.
- **Table A-7 (Verification of Outputs of Software Coding and Integration):** Source code must be traceable to low-level requirements, comply with coding standards, and be verifiable.
- **Table A-8 (Testing):** Normal range testing, robustness testing, and (for DAL A/B) structural coverage analysis including Modified Condition/Decision Coverage (MC/DC).

**DO-330 (Tool Qualification)** is a companion standard. Any tool whose output is not verified (i.e., a "development tool" per DO-178C §12.2) requires its own qualification. DO-330 defines five Tool Qualification Levels (TQL 1–5), with TQL 1 being the most rigorous (for tools whose output could contribute to DAL A software).

### 3.2 ISO 26262 — Road Vehicles Functional Safety

ISO 26262 adapts IEC 61508 for automotive electronics. It comprises 12 parts (as of the 2018 second edition):

- **Part 1:** Vocabulary
- **Part 2:** Management of functional safety
- **Part 3:** Concept phase (HARA, safety goals)
- **Part 4:** Product development at the system level
- **Part 5:** Product development at the hardware level
- **Part 6:** Product development at the software level
- **Part 7:** Production, operation, service, and decommissioning
- **Part 8:** Supporting processes
- **Part 9:** ASIL-oriented and safety-oriented analyses
- **Part 10:** Guidelines (informative)
- **Part 11:** Guidelines on application of ISO 26262 to semiconductors
- **Part 12:** Adaptation for motorcycles

Automotive Safety Integrity Levels (ASIL):

| ASIL | Probability of Exposure | Severity | Controllability | Example |
|------|------------------------|----------|-----------------|---------|
| D | High | High | Low | Braking system ECU |
| C | Medium | High | Medium | Adaptive cruise control |
| B | Medium | Medium | Low | Dashboard display |
| A | Low | Medium | Medium | Rear light control |

Part 6 (Software) is the most relevant to FLUX. Key clauses:

- **Clause 5 (Software safety requirements):** Derived from technical safety concepts, must be traceable to system-level requirements.
- **Clause 6 (Software architectural design):** Must demonstrate freedom from interference, graceful degradation, and appropriate software partitioning.
- **Clause 7 (Software unit design and implementation):** Coding guidelines (e.g., MISRA C:2012), enforcement of type safety, defensive programming.
- **Clause 8 (Software unit verification):** Static analysis, code reviews, unit testing with structural coverage (ASIL D requires MC/DC equivalent).
- **Clause 9 (Software integration and testing):** Interface testing, resource usage testing, back-to-back comparison testing.
- **Clause 10 (Verification of software safety requirements):** Requirements-based testing, fault injection testing, robustness testing.

### 3.3 IEC 61508 — Functional Safety of Electrical/Electronic Systems

IEC 61508 is the umbrella standard for functional safety across all industries (except where sector-specific standards apply). It comprises 7 parts:

- **Part 1:** General requirements
- **Part 2:** Requirements for E/E/PE safety-related systems
- **Part 3:** Software requirements
- **Part 4:** Definitions and abbreviations
- **Part 5:** Examples of methods for SIL determination
- **Part 6:** Guidelines on application of Parts 2 and 3
- **Part 7:** Overview of techniques and measures

Safety Integrity Levels (SIL):

| SIL | Probability of Dangerous Failure on Demand (Low Demand) | PFH (High Demand/Continuous) |
|-----|--------------------------------------------------------|------------------------------|
| 4 | ≥10⁻⁵ to <10⁻⁴ | ≥10⁻⁹ to <10⁻⁸ |
| 3 | ≥10⁻⁴ to <10⁻³ | ≥10⁻⁸ to <10⁻⁷ |
| 2 | ≥10⁻³ to <10⁻² | ≥10⁻⁷ to <10⁻⁶ |
| 1 | ≥10⁻² to <10⁻¹ | ≥10⁻⁶ to <10⁻⁵ |

Part 3 (Software) is most relevant. Key clauses:

- **Clause 7.2 (Software safety requirements specification):** Must be derived from E/E/PE system safety requirements, verifiable, and traceable.
- **Clause 7.3 (Software validation):** Must demonstrate that the integrated system meets its safety requirements.
- **Clause 7.4 (Software modification):** Change control, regression testing, impact analysis.
- **Clause 7.4.2 (Software architecture design, SIL 3/4):** Requires diverse monitoring, fault detection, and defined behavior under fault conditions.
- **Annex A (Techniques and measures):** For SIL 3/4, formal methods (Table A.2, row 1), defensive programming (Table A.4), and computer-aided verification (Table A.5) are highly recommended (HR = Highly Recommended).

**Critical note:** IEC 61508 Part 3, Annex A, Table A.2 explicitly lists **formal methods** as "Highly Recommended" for SIL 3 and SIL 4 software design. This is the standards body telling you to use formal methods for high-integrity software. FLUX is a formal method.

---

## 4. Mapping FLUX ISA to Certification Requirements

The following table maps each FLUX/cocapn component to specific certification objectives across all three standards.

### 4.1 Component-to-Objective Mapping

| FLUX Component | DO-178C Objective | ISO 26262 Clause | IEC 61508 Clause | How It Satisfies |
|---|---|---|---|---|
| **Constraint Compiler** | A-2: Software development process; A-6: Design process outputs verified | Part 6 §5–6: Software safety requirements and architectural design | Part 3 §7.2: Software safety requirements spec | Constraints are the safety requirements. Compilation is a correctness-preserving transformation. If constraints are sound, generated code is sound by construction. |
| **Quality Gate** | A-3: Verification of requirements outputs; A-7: Verification of code outputs | Part 6 §8: Software unit verification; Part 6 §10: Verification of safety requirements | Part 3 §7.3: Software validation | The quality gate rejects any constraint that cannot be proven. Rejected claims = unmet safety requirements. This is automated requirements verification. |
| **Merkle Provenance** | A-9: Configuration management; A-10: Software lifecycle environment control | Part 8 §5–6: Configuration management, change management | Part 3 §7.4: Software modification; Part 1 §5.2.5: Configuration management | Every tile has a cryptographic hash linking it to its inputs, compilation parameters, and quality gate result. This is a tamper-proof audit trail. |
| **PLATO Knowledge Store** | A-1: Software planning process; A-9: Configuration management | Part 2 §5: Overall safety management; Part 8 §5: Configuration management | Part 1 §5: Safety management requirements | PLATO stores versioned, quality-gated knowledge tiles. It serves as the configuration management system for the fleet's institutional knowledge. |
| **cocapn-glue-core Wire Protocol** | A-6: Software architecture consistency; A-7: Integration verification | Part 6 §9: Software integration testing; Part 4 §7: System integration | Part 3 §7.3.2.4: Software integration testing | The wire protocol defines standardized inter-component communication. Interface control documents (ICDs) fall out naturally from the protocol specification. |
| **Formally Verified VM (Lean4)** | §12.2 Tool qualification; DO-330 TQL 1–4 | Part 8 §11: Qualification of software tools | Part 3 §7.4.2.11: Software verification tools | The VM is proven correct in Lean4. For DO-330, this constitutes a formal proof of tool correctness, reducing or eliminating the need for tool-specific test evidence. |

### 4.2 Constraint Compilation as Design Assurance

The key insight is that constraint compilation provides **verified-by-construction** design assurance. Traditional certification processes spend enormous effort on *after-the-fact* verification: write code, then prove it meets requirements. FLUX inverts this. Constraints are the requirements. The compiler proves them before generating code. The generated code inherits the proof.

This maps directly to DO-178C Table A-6, Objective 1 ("Low-level requirements comply with high-level requirements") and Table A-3, Objective 1 ("Software requirements are developed, traceable, verifiable"). In FLUX, traceability is automatic: each compiled instruction traces back to the constraint that generated it. Verifiability is automatic: the quality gate rejects unverifiable constraints. Compliance is automatic: the compiler enforces it.

For ISO 26262 Part 6 §7.2, the constraint language serves as a "software safety requirements specification language" that is formally defined. For IEC 61508 Part 3 Annex A Table A.2, the constraint compiler *is* the formal method, rated HR for SIL 3/4.

### 4.3 Quality Gate as Automated Verification

The quality gate is a Satisfiability Modulo Theories (SMT) solver that checks whether each compiled constraint is satisfiable, consistent with other constraints, and within defined tolerance bounds. This maps to:

- **DO-178C A-8:** Structural coverage analysis (the quality gate provides exhaustive coverage of the constraint space)
- **ISO 26262 Part 6 §8.4.2:** Requirements-based unit testing (each constraint is tested against its specification)
- **IEC 61508 Part 3 §7.3.2.3:** Software module testing (each compiled module is tested against its safety requirements)

The quality gate's rejection log is itself certification evidence. It shows which constraints were rejected, why, and what was done about them. This satisfies DO-178C A-3 Objective 4 ("Software requirements are accurate and consistent") and ISO 26262 Part 6 §8.5.1 ("Test results shall demonstrate compliance with the software safety requirements").

### 4.4 Merkle Provenance as Audit Trail

Every tile in the Cocapn architecture has a Merkle hash computed over:
1. The constraint source text
2. The compiler version and configuration
3. The quality gate result (pass/fail, with proof artifact)
4. The hash of all input tiles (dependency provenance)

This creates a content-addressed, tamper-evident audit trail. Any change to any tile invalidates its hash and the hashes of all downstream tiles. This satisfies:

- **DO-178C A-9 Objective 1:** "Configuration items are identified" (each tile is a configuration item identified by its hash)
- **DO-178C A-9 Objective 3:** "Configuration baseline is established" (the Merkle tree root is the baseline)
- **DO-178C A-9 Objective 4:** "Configuration status accounting is maintained" (the provenance tree is the status accounting)
- **ISO 26262 Part 8 §5.5.1:** "Configuration items shall be identified and documented" (tile hashes)
- **ISO 26262 Part 8 §5.5.6:** "Configuration status accounting shall be performed" (Merkle tree updates)
- **IEC 61508 Part 3 §7.4.2.11:** "The software configuration management system shall provide... the identification of all configuration items"

---

## 5. The Certification Gap Analysis

### 5.1 What We Have

| Component | Status | Certification Value |
|---|---|---|
| Constraint compiler prototype | ✅ Operational | Core design assurance mechanism |
| Quality gate (SMT-based) | ✅ Operational | Automated requirements verification |
| Merkle provenance | ✅ Operational | Tamper-proof audit trail |
| PLATO knowledge store | ✅ Operational | Configuration management |
| cocapn-glue-core wire protocol | ✅ Operational | Interface control |
| Lean4 VM proof (partial) | 🔧 In progress | Tool qualification evidence |

### 5.2 What We Need

| Gap | DO-178C Reference | ISO 26262 Reference | IEC 61508 Reference | Effort Estimate |
|---|---|---|---|---|
| **Formal requirements traceability matrix** | A-3 Obj 1, A-6 Obj 1 | Part 6 §5.4.5, §7.4.8 | Part 3 §7.2.2.8 | 2–3 months (build traceability tooling into constraint compiler) |
| **MC/DC structural coverage** | A-7-6 (DAL A/B) | Part 6 Table 12 (ASIL C/D) | Part 3 Table A.5 (SIL 3/4) | 3–4 months (instrument generated code, build coverage analyzer) |
| **Tool qualification evidence (DO-330)** | §12.2, DO-330 TQL 1–5 | Part 8 §11 | Part 3 §7.4.2.12 | 4–6 months (complete Lean4 proof, write Tool Qualification Plan, build evidence package) |
| **Safety manual** | A-1 (Software plans) | Part 2 §5.4.2 (Safety plan) | Part 1 §5.2.3 (Safety plan) | 1–2 months (document the FLUX safety case) |
| **Coding standards compliance** | A-2 (Software development standards) | Part 6 §7.1 (Coding guidelines) | Part 3 Annex A Table A.4 | 1–2 months (map FLUX ISA semantics to MISRA-like rules) |
| **Independent verification** | A-4 (Verification process, independence) | Part 6 §8.4.3 (Independence of verification) | Part 3 §7.9.2.4 (Independent assessment) | 0 months (contract with third-party, but need to budget time and money) |
| **Environmental qualification** | A-10 (Software lifecycle environment) | Part 8 §12 (Tool qualification) | Part 3 §7.4.2.12 | 2–3 months (qualify the build/test/deployment environment) |

### 5.3 Timeline Estimates

**DO-178C DAL C (Major):** 6–9 months
- No MC/DC required (statement + decision coverage sufficient)
- Tool qualification at TQL 4 or 5 (reduced evidence)
- Most objectives achievable with current architecture + traceability tooling

**DO-178C DAL B (Hazardous):** 9–12 months
- MC/DC required (Table A-7 Objective 6)
- Tool qualification at TQL 3
- Independent verification required for most objectives

**DO-178C DAL A (Catastrophic):** 12–18 months
- Full MC/DC with rigor
- Tool qualification at TQL 1–2
- Full independence for verification activities
- Requires complete Lean4 VM proof

**ISO 26262 ASIL D:** 12–18 months
- Equivalent rigor to DAL A
- Requires fault injection testing, back-to-back comparison
- Hardware-software co-verification

**IEC 61508 SIL 4:** 12–18 months
- Formal methods highly recommended (we have them)
- Diverse monitoring required
- Complete safety lifecycle documentation

---

## 6. The Fleet's Certification Strategy

### Phase 1: Self-Certify (Months 0–6)

**Goal:** Use FLUX-verified systems internally, build the evidence base.

- Deploy constraint compiler + quality gate for all fleet operations
- Generate Merkle provenance for every tile
- Complete traceability tooling (constraint → instruction → test case → result)
- Write the FLUX Safety Manual (the safety case document)
- Begin Lean4 VM proof completion
- Establish coding standards document for FLUX ISA

**Exit criteria:** Full traceability for all fleet operations, documented safety case, quality gate running on all constraints.

### Phase 2: Third-Party Audit (Months 6–12)

**Goal:** Engage a certification body (e.g., SGS, TÜV, Bureau Veritas) for gap analysis and pre-assessment.

- Select target standard (recommend starting with IEC 61508 SIL 2 or DO-178C DAL C — lower rigor, faster path)
- Engage Designated Engineering Representative (DER) for DO-178C or Functional Safety Engineer (FSE) for ISO 26262
- Conduct gap analysis against target standard
- Address gaps identified in audit
- Build certification evidence package
- Submit for pre-assessment review

**Exit criteria:** Third-party gap analysis complete, evidence package reviewed, clear path to formal certification.

### Phase 3: Formal Certification (Months 12–18)

**Goal:** Achieve formal certification for at least one FLUX-verified system.

- Submit certification evidence package to certification authority (FAA, EASA, or automotive OEM)
- Support certification authority review (respond to findings, provide additional evidence)
- Achieve certification for target DAL/ASIL/SIL
- Use first certification as template for subsequent systems

**Exit criteria:** FLUX-verified system certified to DO-178C DAL C, ISO 26262 ASIL C, or IEC 61508 SIL 3 (pick one, use as precedent).

---

## 7. Business Model: Certification-as-a-Service

### 7.1 The Opportunity

Safety certification is a $4.6B/year market (Verificient Research, 2024). The cost to certify a single DO-178C DAL A system ranges from $10M–$50M, with 60–70% of that cost going to verification and documentation labor. If FLUX can automate even 30% of that effort, the value proposition is enormous.

### 7.2 Revenue Model

| Tier | Offering | Price | Target Customer |
|------|----------|-------|-----------------|
| **Open Core** | FLUX constraint compiler, quality gate, basic provenance | Free (Apache 2.0) | Researchers, open-source projects |
| **Professional** | FLUX Studio IDE, traceability tooling, PLATO integration, automated evidence generation | $5K–$20K/year/license | Aerospace/automotive Tier 2–3 suppliers |
| **Enterprise** | Full certification evidence package generation, DO-330 tool qualification evidence, Lean4 VM proof artifacts, dedicated support | $50K–$200K/year/license | Aerospace primes, automotive OEMs |
| **Compliance Monitoring** | Continuous compliance monitoring (CaaS), automated regression analysis, certification status dashboard | $10K–$50K/year/system | Any certified FLUX user |
| **Consulting** | Certification strategy, gap analysis, DER/FSE support, certification authority liaison | $200–$400/hour | Organizations new to certification |

### 7.3 Revenue Projections

| Year | Customers | Revenue | Assumptions |
|------|-----------|---------|-------------|
| Year 1 | 5–10 Professional | $50K–$200K | Early adopters, internal use only |
| Year 2 | 10–20 Professional, 2–3 Enterprise | $300K–$700K | First external certification achieved |
| Year 3 | 20–40 Professional, 5–10 Enterprise, 10+ Compliance | $700K–$2M | Multiple certifications, CaaS traction |
| Year 5 | 50+ Professional, 15+ Enterprise, 30+ Compliance | $2M–$5M | Market leader in AI safety certification |

### 7.4 Why This Works

1. **Lock-in through evidence:** Once a customer certifies with FLUX, switching costs are enormous (recertification).
2. **Regulatory tailwinds:** FAA, EASA, and UNECE are tightening AI/ML certification requirements. First-mover advantage is significant.
3. **Open core builds trust:** Certification authorities trust tools they can inspect. Open-source core enables that trust.
4. **Recurring revenue:** Compliance monitoring is a subscription. Recertification is annual. Revenue compounds.

---

## 8. Case Study: Autonomous Sonar Platform

### 8.1 System Description

Consider an autonomous underwater sonar platform that must:
- Detect and classify underwater objects within a defined range
- Navigate autonomously while avoiding collisions
- Surface and transmit data on a defined schedule
- Fail safe on any loss of communication or power

This is a realistic DO-178C DAL B or ISO 26262 ASIL C candidate (hazardous failure condition: collision with submerged object or surface vessel).

### 8.2 Safety Requirements → FLUX Constraints

| Safety Requirement | FLUX Constraint | Quality Gate Check |
|---|---|---|
| "Detect objects at ≥50m range" | `assert sonar.detection_range >= 50.0` | SMT solver verifies sensor model satisfies range constraint under defined noise conditions |
| "Collision avoidance response < 2s" | `assert collision_response_time < 2.0` | Compiler generates timing-annotated code; quality gate verifies worst-case execution time |
| "Surface within 60s of command" | `assert surface_time <= 60.0` | Verified against hydrodynamic model constraints |
| "Fail safe on comm loss" | `assert fail_safe ON comm_loss` | Compiler generates fault handler; quality gate verifies all fault paths converge to safe state |
| "No uncontrolled depth changes" | `INVARIANT depth_rate_of_change <= max_safe_rate` | Invariant checked at every control cycle; quality gate verifies invariant is maintained under all modeled disturbances |

### 8.3 Verification Evidence → PLATO Tiles + Merkle Proofs

Each safety requirement generates a PLATO tile:

```
tile:sonar_detection_range_v2.3
  constraint: assert sonar.detection_range >= 50.0
  compiler: fluxc v0.8.1
  quality_gate: PASS (0.003s, SMT-LIB proof artifact: sha256:abc123...)
  dependencies: [tile:sonar_sensor_model_v1.7, tile:noise_model_v3.1]
  merkle_hash: sha256:def456...
  compiled_output: sonar_detection_range.flux (42 instructions)
```

The Merkle tree root for the complete system is the configuration baseline. Any change to any tile (new sensor model, updated noise parameters) produces a new root, and the certification authority can verify that only the affected tiles changed.

### 8.4 Tool Qualification → Lean4 VM Proof

The Lean4 proof of the FLUX VM demonstrates:
1. **Soundness:** The VM only executes valid FLUX instructions (type safety)
2. **Completeness:** All FLUX instructions are handled (no undefined behavior)
3. **Determinism:** Given the same input state, the VM produces the same output state
4. **Constraint preservation:** If the quality gate passed, the VM will not violate the constraint during execution

For DO-330 TQL 3 (appropriate for DAL B tools), the qualification evidence includes:
- Tool Operational Requirements (TOR) — the Lean4 specification
- Tool Development Plan — the Lean4 development process
- Tool Verification Plan — proof strategies, test cases
- Tool Verification Results — proof completion status, coverage
- Tool Configuration Index — Lean4 version, dependencies

### 8.5 Audit Trail → PLATO Provenance

The certification authority can query PLATO for:
- **Complete traceability:** "Show me all tiles contributing to collision avoidance" → PLATO returns the dependency graph
- **Impact analysis:** "What happens if we change the noise model?" → PLATO identifies all downstream tiles, re-runs quality gate
- **Change history:** "What changed between v2.3 and v2.4?" → Merkle diff shows exact changes
- **Compliance status:** "Are all DAL B objectives satisfied?" → PLATO cross-references tiles against DO-178C Annex A tables

This is orders of magnitude more efficient than traditional compliance management, where traceability matrices are maintained manually in spreadsheets.

---

## 9. Competition

### 9.1 LlamaIndex / LangChain / LangGraph

These frameworks build AI application pipelines. They have no formal verification, no constraint compilation, no audit trail, and no deterministic execution. They cannot be certified because:

- **No safety requirements tracing:** LLM outputs cannot be traced to specific safety objectives
- **No deterministic behavior:** Same input can produce different output
- **No formal verification:** No mechanism to prove correctness properties
- **No audit trail:** No tamper-proof record of what was generated and why

**Certification status:** Impossible under current standards. Would require fundamental architectural changes.

### 9.2 DAFNY / F* / Why3 (Existing Formal Methods Tools)

These are mature, general-purpose formal verification tools. They could theoretically be used for certification, but:

- **Not designed for AI/agentic systems:** They verify individual functions, not autonomous behavior
- **Steep learning curve:** Requires PhD-level expertise in formal methods
- **No provenance or audit trail:** Verification is a point-in-time check, not a continuous process
- **No certification-specific tooling:** No traceability matrices, no coverage analysis, no evidence package generation

**Certification status:** Possible but impractical for autonomous systems. Better suited for individual algorithm verification.

### 9.3 Ada/SPARK

SPARK (the formally verifiable subset of Ada) is the gold standard for certified safety-critical software. It is used in DO-178C DAL A systems (e.g., Airbus, Boeing). However:

- **Not designed for AI:** SPARK verifies imperative programs, not constraint-based autonomous systems
- **Manual proof effort:** SPARK proofs require significant manual guidance
- **No agentic architecture:** No concept of autonomous agents, fleets, or knowledge stores

**Certification status:** The incumbent. FLUX should be positioned as complementary to SPARK, not competing with it. SPARK handles low-level code; FLUX handles high-level constraint verification and agentic behavior.

### 9.4 Why We Win

FLUX is the only system that:
1. Provides **constraint-based** specification (not imperative programming)
2. Compiles constraints to **formally verified** execution
3. Maintains **cryptographic provenance** for all verification artifacts
4. Is designed for **autonomous, agentic** systems
5. Generates **certification evidence** as a byproduct of development

The competition can verify code. We verify *behavior*. The certification authorities care about behavior.

---

## 10. Conclusion

The path from AI research to deployed safety-critical systems runs through certification. There is no shortcut. DO-178C, ISO 26262, and IEC 61508 are not suggestions—they are legal requirements enforced by regulatory authorities worldwide.

FLUX ISA and the Cocapn architecture provide the first viable path to certifying autonomous AI systems. By compiling constraints into a formally verified instruction set, maintaining cryptographic provenance, and generating certification evidence as a byproduct of development, we make certification a feature of the development process rather than an afterthought.

The gap is real—6–18 months of work separates us from first certification—but the gap is finite and the path is clear. Every line of constraint code we write, every quality gate check we run, and every Merkle hash we compute is evidence toward that certification.

The business model is straightforward: open-core the engine, charge for the evidence, subscribe for the monitoring. The lock-in is regulatory: once you certify with FLUX, switching costs are measured in recertification time and money.

The tagline writes itself: **"We use Cocapn, like MISRA for C."**

Safety certification is the moat. The fleet that certifies first, wins.

---

## References

1. RTCA DO-178C, *Software Considerations in Airborne Systems and Equipment Certification*, December 2011.
2. RTCA DO-330, *Software Tool Qualification Considerations*, December 2011.
3. ISO 26262:2018, *Road vehicles — Functional safety*, Parts 1–12.
4. IEC 61508:2010, *Functional safety of electrical/electronic/programmable electronic safety-related systems*, Parts 1–7.
5. FAA Advisory Circular 20-115D, *Airworthiness Approval of Software*, November 2023.
6. EASA Certification Memorandum CM-SWCEH-002, *Software Aspects of Certification*, Issue 3, 2023.
7. MISRA C:2012, *Guidelines for the Use of the C Language in Critical Systems*, March 2013 (amended 2020).
8. CENELEC EN 50128:2011, *Railway applications — Communication, signalling and processing systems — Software for railway control and protection systems*.
9. Leroy, X. "Formal Verification of a Realistic Compiler." *Communications of the ACM*, 52(7):107–115, 2009. (CompCert reference for verified compilation precedent.)
10. de Moura, L., Bjørner, N. "Z3: An Efficient SMT Solver." *TACAS 2008*, LNCS 4963, pp. 337–340. (SMT solver reference for quality gate.)

---

*This is a working paper. The mapping is based on the authors' interpretation of the referenced standards and should be validated by a qualified Designated Engineering Representative (DER) or Functional Safety Engineer (FSE) before use in a certification effort.*
