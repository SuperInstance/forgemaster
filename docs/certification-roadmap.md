# FLUX — Technical Roadmap for Certification

## Executive Summary

**Goal:** Achieve safety certification for the FLUX constraint-to-silicon pipeline across three major standards:
1. **DO-178C DAL A** — Airborne software (aerospace)
2. **DO-254 DAL A** — Airborne electronic hardware (FPGA/ASIC)
3. **ISO 26262 ASIL D** — Automotive functional safety

**Timeline:** 18 months (Q3 2026 – Q4 2027)
**Budget:** $2.0M
**Outcome:** FLUX compiler + VM + FPGA IP cores certified for safety-critical deployment

---

## Part 1: DO-178C DAL A — Airborne Software Certification

### Overview

DO-178C is the primary standard for airborne software. DAL A (catastrophic failure condition) is the highest integrity level, requiring:
- Tool Qualification Level 1 (TQL-1) for development tools
- 100% structural coverage (MC/DC — Modified Condition/Decision Coverage)
- Full traceability from requirements → code → tests → evidence

### FLUX Certification Strategy

**FLUX as a Development Tool (TQL-1):**

The FLUX compiler is classified as a software development tool under DO-178C §12.2. Because FLUX generates code that executes in safety-critical contexts, it requires TQL-1 qualification — the most rigorous level.

| Requirement | FLUX Approach | Evidence Artifact |
|-------------|--------------|-------------------|
| Tool Operational Requirements (TOR) | GUARD DSL specification + FLUX bytecode semantics | TOR document |
| Tool Development Standards | Coding standard (MISRA-C subset for Rust), review checklist | Coding standard doc |
| Tool Verification | Formal proof (Galois connection) + MC/DC test suite | Proof document + test results |
| Tool Configuration Management | Git-based, deterministic builds, reproducible artifacts | CI/CD logs, release tags |
| Tool Quality Assurance | Independent review, static analysis, formal inspections | Review records |
| Structural Coverage | 100% MC/DC on compiler core, 100% statement on toolchain | Coverage reports (LLVM-cov) |

### Detailed Timeline — DO-178C DAL A

| Phase | Dates | Activities | Deliverables |
|-------|-------|-----------|--------------|
| **1. Planning** | Q3 2026 (Month 1–3) | PSAC drafting, DER engagement, plan reviews | Plan for Software Aspects of Certification (PSAC) |
| **2. Requirements** | Q4 2026 (Month 4–6) | Software requirements for FLUX compiler, traceability matrix | Software Requirements Specification (SRS) |
| **3. Design** | Q1 2027 (Month 7–9) | Software architecture, design standards, formal design reviews | Software Design Description (SDD) |
| **4. Implementation** | Q1–Q2 2027 (Month 7–12) | FLUX compiler + VM implementation, coding to standards | Source code + review records |
| **5. Verification** | Q2–Q3 2027 (Month 10–15) | Unit testing, integration testing, MC/DC analysis, formal proofs | Test results + coverage reports |
| **6. Certification** | Q3–Q4 2027 (Month 15–18) | DER review, FAA audit, certification liaison | Certification recommendation |

### Structural Coverage Strategy

**MC/DC (Modified Condition/Decision Coverage):**
- Each condition in a decision independently affects the outcome
- FLUX compiler core: ~15K lines of Rust
- Target: 100% MC/DC on compiler pipeline (parser → type checker → optimizer → code generator)
- Tool: `llvm-cov` + custom MC/DC analysis for Galois connection proof points
- Approach: Property-based testing (QuickCheck-style) to generate MC/DC-adequate test suites

**Statement Coverage:**
- 100% on all FLUX toolchain code (compiler, VM, debugger, certifier)
- Exclude: test harness, build scripts, unreachable error paths (documented justification)

**Decision Coverage:**
- 100% on all boolean decisions in compiler core
- Galois connection proof points verified via formal proof + test double-coverage

### Tool Qualification Package (TQL-1)

| Artifact | Description | Estimated Size |
|----------|-------------|---------------|
| Tool Operational Requirements | What FLUX is supposed to do | 50 pages |
| Tool Development Plan | How FLUX is developed | 30 pages |
| Tool Verification Plan | How FLUX is verified | 40 pages |
| Tool Configuration Index | Version-controlled artifact list | 20 pages |
| Source Code | FLUX compiler + VM (Rust) | ~15K LOC |
| Test Cases & Results | Unit + integration + MC/DC | ~5K test cases |
| Coverage Reports | MC/DC, statement, decision | Auto-generated |
| Formal Proof | Galois connection correctness | 80 pages |
| Tool Qualification Completion Report | Summary of compliance | 30 pages |

---

## Part 2: DO-254 DAL A — Airborne Electronic Hardware Certification

### Overview

DO-254 covers complex electronic hardware (CEH) — FPGAs, ASICs, and programmable logic. DAL A requires:
- Element-level analysis for all hardware elements
- Structured design methodology
- Independent verification and validation

### FLUX Certification Strategy

**FLUX FPGA IP Cores as Complex Electronic Hardware:**

FLUX-generated FPGA bitstreams are CEH under DO-254. The certification strategy covers:

1. **FLUX VM FPGA Implementation** — The FLUX bytecode interpreter implemented in VHDL/Verilog for FPGA targets
2. **FLUX Code Generator** — The tool that produces FPGA-specific implementations from FLUX bytecode
3. **FLUX IP Cores** — Pre-certified IP blocks for common safety functions (watchdog, interlock, bounds checker)

### Detailed Timeline — DO-254 DAL A

| Phase | Dates | Activities | Deliverables |
|-------|-------|-----------|--------------|
| **1. Planning** | Q3 2026 (Month 1–3) | PHAC drafting, hardware DER engagement | Plan for Hardware Aspects of Certification (PHAC) |
| **2. Requirements** | Q4 2026 (Month 4–6) | Hardware requirements, element analysis plan | Hardware Requirements Specification (HRS) |
| **3. Design** | Q1 2027 (Month 7–9) | HDL design, architectural analysis, FMEA | Hardware Design Description (HDD) |
| **4. Implementation** | Q1–Q2 2027 (Month 7–12) | VHDL/Verilog coding, synthesis, place & route | HDL source + synthesis reports |
| **5. Verification** | Q2–Q3 2027 (Month 10–15) | Simulation, timing analysis, gate-level verification | Simulation results + timing reports |
| **6. Certification** | Q3–Q4 2027 (Month 15–18) | DER review, environmental testing (if applicable) | Certification recommendation |

### Element Analysis Strategy

**Complex Electronic Hardware Elements:**

| Element | Type | DAL | Analysis Method |
|---------|------|-----|----------------|
| FLUX VM Core | CEH | A | Formal verification (model checking) |
| FLUX Bytecode Loader | CEH | A | Formal verification + simulation |
| Safety Interlock IP | CEH | A | Formal verification + fault injection |
| Bounds Checker IP | CEH | A | Formal verification + structural test |
| Xilinx UltraScale+ Fabric | COTS | A | Vendor data + integration analysis |
| Intel Agilex Fabric | COTS | A | Vendor data + integration analysis |

### FPGA-Specific Certification Artifacts

| Artifact | Description |
|----------|-------------|
| Hardware Accomplishment Summary | Compliance demonstration |
| HDL Source Code | VHDL/Verilog for all FLUX IP |
| Synthesis Constraints | Timing, area, power constraints |
| Gate-Level Netlist | Post-synthesis, post-place-and-route |
| Timing Analysis Report | Static timing analysis (STA) results |
| Simulation Testbench | Functional + fault-injection testbenches |
| FPGA Vendor Certification Data | Xilinx/Intel certification documentation |

---

## Part 3: ISO 26262 ASIL D — Automotive Functional Safety

### Overview

ISO 26262 covers automotive functional safety. ASIL D is the highest level, required for:
- Steering, braking, and powertrain control
- ADAS L4/L5 autonomous driving
- Battery management systems

### FLUX Certification Strategy

**FLUX as a Safety Element out of Context (SEooC):**

FLUX is developed as a SEooC — a safety element designed to be integrated into various automotive systems. This allows us to certify FLUX independently, then customers integrate it into their specific ASIL D contexts.

| ISO 26262 Part | FLUX Scope | Key Requirements |
|----------------|-----------|-----------------|
| Part 4 (Product dev at system level) | Integration guidelines | System-level safety requirements |
| Part 5 (Hardware development) | FPGA implementation | Hardware metrics (SPFM ≥ 99%, LFM ≥ 90%) |
| Part 6 (Software development) | FLUX compiler + VM | Software safety requirements, unit testing |
| Part 8 (Supporting processes) | Configuration management, documentation | Process compliance evidence |
| Part 10 (Guidelines) | ASIL D guidelines applied | All ASIL D requirements met |

### Software Component Qualification (Part 6, Clause 12)

FLUX compiler and VM must be qualified as software components per ISO 26262-6 Clause 12:

| Requirement | FLUX Approach |
|-------------|--------------|
| Software safety requirements specification | GUARD DSL serves as formal safety requirement language |
| Software architectural design | Documented architecture with safety analysis |
| Software unit design & implementation | Coding standard compliance (MISRA-C for Rust subset) |
| Software unit verification | Unit testing + formal proof (Galois connection) |
| Software integration & testing | Integration testing + structural coverage |
| Software verification | Static analysis, dynamic analysis, formal verification |

### Detailed Timeline — ISO 26262 ASIL D

| Phase | Dates | Activities | Deliverables |
|-------|-------|-----------|--------------|
| **1. Planning** | Q1 2027 (Month 7–9) | Safety plan, SEooC specification, assessor engagement | Safety Plan + SEooC Specification |
| **2. Hazard Analysis** | Q1 2027 (Month 8–9) | HARA for FLUX use cases, ASIL determination | HARA Report |
| **3. Requirements** | Q2 2027 (Month 10–12) | Safety requirements, TSR, SSR | Safety Requirements Specification |
| **4. Design & Implementation** | Q2–Q3 2027 (Month 10–14) | Software/hardware design to ASIL D standards | Design documents + source |
| **5. Verification** | Q3 2027 (Month 13–16) | Unit/integration testing, coverage analysis, formal verification | Test reports + coverage |
| **6. Assessment** | Q4 2027 (Month 16–18) | Third-party assessment (TÜV/TÜV SÜD) | Assessment report |

### Hardware Safety Metrics (Part 5)

For FPGA implementations, FLUX must meet:

| Metric | ASIL D Requirement | FLUX Target | Method |
|--------|-------------------|-------------|--------|
| SPFM (Single Point Fault Metric) | ≥ 99% | 99.5% | FMEDA analysis |
| LFM (Latent Fault Metric) | ≥ 90% | 92% | FMEDA analysis |
| PMHF (Probabilistic Metric for HW Failure) | < 10 FIT | < 5 FIT | Reliability prediction |

---

## Certification Budget Breakdown

| Category | DO-178C | DO-254 | ISO 26262 | Total |
|----------|---------|--------|-----------|-------|
| DER/Assessor fees | $300K | $200K | $150K | $650K |
| Testing tools & infrastructure | $150K | $200K | $100K | $450K |
| FPGA boards & lab equipment | $50K | $150K | $50K | $250K |
| Personnel (certification-focused) | $200K | $150K | $150K | $500K |
| Legal & administrative | $50K | $50K | $50K | $150K |
| **Total** | **$750K** | **$750K** | **$500K** | **$2.0M** |

---

## Key Dependencies & Risks

### Dependencies

| Dependency | Impact | Mitigation |
|-----------|--------|------------|
| DER availability (DO-178C/254) | High — can't proceed without DER | Engage 3 DERs, secure commitment Q3 2026 |
| TÜV assessor availability (ISO 26262) | Medium — long lead time | Engage Q1 2027, book assessment slots |
| FPGA vendor certification data | High — needed for DO-254 COTS analysis | Early engagement with Xilinx/Intel FAEs |
| Galois connection proof acceptance | Critical — foundation of certification claim | External formal verification review (MIT partnership) |
| Rust language certification precedent | Medium — no DO-178C Rust precedent yet | Document safety case for Rust; engage FAA early |

### Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| FAA questions Galois connection as sufficient proof | Medium | High | Supplement with traditional testing; engage FAA research office |
| MC/DC coverage gaps in compiler | Medium | Medium | Property-based testing + targeted unit tests |
| FPGA timing closure fails on safety constraints | Low | High | Safety constraint simplification; target lower-performance certified path |
| DO-254 COTS data unavailable from vendors | Medium | High | Qualify COTS components independently; redundant design |
| ISO 26262 assessor rejects SEooC approach | Low | Medium | Engage assessor early, align on SEooC boundaries |

---

## Certification Team Structure

| Role | FTE | Start Date | Responsibilities |
|------|-----|-----------|-----------------|
| Certification Lead | 1.0 | Q3 2026 | Overall certification strategy, DER/assessor liaison |
| Formal Methods Engineer | 1.0 | Q3 2026 | Galois connection proofs, formal verification, MC/DC analysis |
| FPGA/HDL Engineer | 1.0 | Q4 2026 | VHDL/Verilog implementation, synthesis, timing, DO-254 artifacts |
| Software Test Engineer | 1.0 | Q1 2027 | Test case development, coverage analysis, DO-178C evidence |
| Safety Analyst | 0.5 | Q1 2027 | HARA, FMEDA, FMEA, safety case documentation |
| DER (external) | 0.25 | Q3 2026 | DO-178C/254 guidance, review, recommendation |
| ISO 26262 Assessor (external) | 0.25 | Q1 2027 | ASIL D assessment, compliance review |

---

## Success Criteria

1. **DO-178C:** FAA accepts TQL-1 qualification for FLUX compiler (certification recommendation letter)
2. **DO-254:** Hardware DER issues certification recommendation for FLUX FPGA IP cores
3. **ISO 26262:** TÜV issues ASIL D compliance report for FLUX as SEooC
4. **Safe-TOPS/W ≥ 25** on certified FPGA path (Xilinx UltraScale+)
5. **Zero open certification findings** at final review
6. **Full traceability** from GUARD specs → FLUX bytecode → FPGA LUT mapping → test cases

---

*This roadmap is a living document. Updated quarterly based on DER/assessor feedback and project progress.*
