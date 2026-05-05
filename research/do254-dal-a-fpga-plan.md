# DO-254/ED-80 Design Assurance Level A FPGA Constraint Checker IP Certification Plan
**Scope**: 44K LUT Xilinx UltraScale+ IP that validates FPGA timing/physical constraints (.xdc/.sdc) for avionics systems, aligned to DO-254 Section 11 (Program Planning) and all mandatory DAL A hardware assurance requirements.

---

## 1. Planning Deliverables (DO-254 §11.3)
Version-controlled mandatory artifacts:
- Core Certification Plan (this document)
- Hardware Requirements Specification (HRS): Ties 100% of IP functionality to safety goals (100% invalid constraint detection, zero critical false positives)
- Hardware Design Description (HDD): UltraScale+ resource breakdown (44K LUTs, 120k FFs, 8 DSP slices), clock/reset domain diagram
- Verification Plan (VP): DAL A-aligned test strategy (unit, integration, formal, STA)
- Tool Qualification Plan (TQP): Scope for Vivado synthesis/STA/simulation
- Configuration Management Plan (CMP): Change control and artifact versioning
- Quality Assurance Plan (QAP): Independent audits and traceability validation
- Structural Coverage Plan: Defines MC/DC and state transition coverage requirements

---

## 2. Coding Standards (Aligned to DO-254 §10.2 & Xilinx UltraScale+ Guidelines)
- Language: VHDL-2019 strict subset (no unbounded logic, implicit signals, or dynamic scheduling)
- Explicit synchronous resets only; documented clock enable domains
- No direct low-level primitive instantiation: Use verified Xilinx UltraScale+ wrapper IP
- Descriptive naming conventions (e.g., `clk_sys_100mhz`, `err_flag_critical`)
- 1:1 traceability between every RTL line and HRS requirements
- Mandatory peer reviews with sign-off before integration
- Module headers with purpose, I/O, traceability, and timing constraints

---

## 3. Element Verification (DO-254 §10.4)
- **Unit Testing**: Each sub-module (constraint parser, rule engine, error logger, AXI4-Lite interface) verified via Vivado Simulator testbenches. 100% structural coverage collected per run.
- **Formal Verification**: Synopsys Formal Pro proves the rule engine detects 100% invalid constraints and validates equivalence between formal model and RTL.
- **Integration Testing**: Validated against 100+ test XDC files (mix of valid/invalid, critical/non-critical constraints)
- **Traceability Matrix**: 1:1:1 link between HRS requirements, RTL modules, and test cases (mandatory for DAL A)

---

## 4. CEH Process (DO-254 §12)
- Centralized Certification Evidence Handbook (CEH) organized per DO-254 Appendix A, containing all signed-off artifacts
- Quarterly independent QA audits of traceability, coverage, and test reports
- Final CEH submission with FAA/EASA Form 8110-3, including vendor tool compliance statements and audit responses

---

## 5. Tool Qualification (DO-254 §10.5)
- **Qualified Suite**: Xilinx Vivado ML 2024.1 (uses Xilinx’s DO-254-compliant UltraScale+ support kit)
- **Qualification Scope**:
  1.  RTL Synthesis: 100% equivalence check (Vivado LEC) between RTL and synthesized netlist
  2.  STA: Correlate Vivado results against Mentor Questa STA for critical paths
  3.  Simulation: Validate Vivado Simulator output against ModelSim for all testbenches
- **Evidence**: Equivalence reports, correlation logs, tool version documentation, and signed vendor compliance statement

---

## 6. Structural Coverage (DO-254 §10.4.2)
- DAL A Mandatory Metrics: 100% statement, branch, and Modified Condition/Decision Coverage (MC/DC) for combinational logic; 100% state transition coverage for the constraint parsing FSM
- Coverage Collection: Vivado Simulator + Siemens Coverage Analyzer post-processing
- Exceptions: Only documented in HRS with QA approval; no uncovered logic permitted
- Signed coverage reports included in the CEH

---

## 7. Timing Analysis (DO-254 §10.6)
- **Tool**: Qualified Vivado Static Timing Analyzer
- **Scope**: All critical paths (AXI4-Lite interface, constraint parsing, error flag output)
- **Corners**: Slow-slow, fast-fast, slow-fast, fast-fast process corners; operating range (-55°C to +125°C, 0.95V–1.05V)
- **Timing Margin**: 10% buffer for avionics environmental conditions
- Signed timing reports traceable to HRS timing requirements included in the CEH

---

## 8. Effort Estimate (Total ~180 Person-Weeks, 20% Contingency)
| Phase | Person-Weeks |
|-------|--------------|
| Planning & Requirements | 25 |
| Design & Coding | 40 |
| Verification (Unit/Formal/Integration) | 70 |
| Tool Qualification | 20 |
| Timing Analysis & Closure | 15 |
| CEH Compilation & Audit | 10 |
lidate zero-latency output response
### 4.3 CEH Test Activities
- Repeat all element-level simulation/formal test cases on hardware
- Validate bitstream integrity and tool implementation correctness
- Measure power consumption via Xilinx Power Analyzer and on-board sensors
### 4.4 CEH Documentation
Formal test plan, procedures, results, and bitstream metadata (tool version, synthesis options) tied to HRS requirements.

---

## 5. Tool Qualification for Vivado Synthesis (DO-254 §11.5)
### 5.1 Tool Lockdown
Fix Xilinx Vivado 2023.1 for all synthesis, implementation, STA, and formal verification activities; no version changes without DAA approval.
### 5.2 Qualification Activities
1. **Baseline Test Suite**: Use Xilinx’s official DO-254 Tool Qualification Kit, augmented with CC-IP-specific tests
2. **Synthesis Validation**: Synthesize ITC’99 benchmarks and CC-IP RTL to confirm LUT count matches specs (44,243) and no unintended logic is added
3. **STA Validation**: Run static timing analysis on the implemented netlist and cross-check results with manual timing calculations
4. **Formal Validation**: Confirm equivalence between RTL and synthesized gate-level netlist
### 5.3 Deliverable
A tool qualification report approved by the DAA, retained for the system’s lifecycle per FAA Order 8110.105.

---

## 6. Configuration Management (DO-254 §11.6)
### 6.1 Configuration Management System (CMS)
Use GitLab EE + Polarion ALM for secure, access-controlled version control of all deliverables.
### 6.2 Configuration Control
- Every baseline deliverable has a unique ID, revision number, and change history
- All changes to baseline artifacts require a written change request with justification, impact analysis, and DAA approval
### 6.3 Audits & Accounting
- Quarterly configuration audits to confirm all deliverables match the current baseline
- Real-time Configuration Status Report (CSR) tracking open change requests and approved revisions

---

## 7. Structural Coverage Analysis (DO-254 §11.7.3)
### 7.1 Mandatory Coverage Metrics (100% Required for DAL A)
| Metric | Definition |
|--------|------------|
| **Statement Coverage** | 100% of executable RTL lines executed during simulation |
| **Branch Coverage** | 100% of `if-else`/`case` statement branches tested in both true/false configurations |
| **Condition Coverage** | 100% of boolean conditions evaluated to both true and false |
### 7.2 Coverage Closure
For any uncovered items, document justification (e.g., "Unreachable branch per design constraints") and validate via formal verification.
### 7.3 Deliverable
A coverage report approved by the DAA, including all uncovered items and their formal validations.

---

## 8. Timing Analysis Requirements
### 8.1 Static Timing Analysis (STA)
- Run Vivado STA on the implemented CC-IP netlist to analyze all combinational input-to-output paths
- Validate maximum propagation delay ≤10ns (target system response time)
### 8.2 Timing Constraints
- Use Vivado Constraint Editor to define input propagation delay, output load, and timing exceptions
- Prove correct constraint application via formal verification
### 8.3 Timing Closure
- Use Vivado Physical Optimization and floorplanning to minimize routing delays
- Iterate on synthesis settings to meet timing specs
### 8.4 Deliverable
A timing analysis report approved by the DAA.

---

## 9. Power Analysis Requirements
- Run Vivado Power Analyzer on the implemented netlist to confirm maximum power ≤2.58W
- Cross-validate results with Xilinx Power Estimator (XPE)
- Optimize high-power blocks if needed to stay within budget
### Deliverable: A power analysis report approved by the DAA

---

## 10. Estimated Effort (Total: 2430 Hours)
| Phase | Effort (Hours) |
|-------|----------------|
| Program Initiation & Planning | 220 |
| RTL Design & Compliance | 380 |
| Element-Level Verification | 950 |
| Tool Qualification | 280 |
| Configuration Management | 120 |
| CEH Development & Testing | 180 |
| Timing & Power Analysis | 100 |
| Certification Documentation & Submission | 200 |
| **Total** | **2430** |

---

## 11. Known Xilinx Toolchain Gotchas for DAL A
| Gotcha | Mitigation |
|--------|------------|
| Tool version drift breaking implementation consistency | Lock to Vivado 2023.1 via containerized toolchains |
| Inferred latches from incomplete `case` statements | Use exhaustive `case` blocks, add default error cases, validate via Vivado RTL Analysis |
| Unintended combinational loops | Use Vivado Design Checks to detect loops, validate via formal verification |
| Timing closure for large combinational logic | Floorplan CC-IP to a dedicated CLB region, run STA early and often |
| Power analysis variability | Use fixed input switching activity, run multiple analysis runs, cross-check with XPE |
| Traceability gaps between RTL and requirements | Link all RTL comments to HRS IDs, use Polarion ALM for automated traceability |
| Formal verification limits for large designs | Split CC-IP into sub-blocks, run formal verification on individual modules |
| Bitstream corruption | Generate and store a Vivado bitstream checksum in the CMS |
| I/O standard constraint conflicts | Use Vivado Constraint Editor to validate all constraints, formal verification to confirm correct application |

---

## 12. Certification Evidence Submission
Final submission to FAA/EASA will include:
1. This Certification Plan
2. HRS, HDD, and Traceability Matrix
3. Verification, Tool Qualification, and Coverage Reports
4. CEH Test Reports
5. Timing/Power Analysis Reports
6. Configuration Audit Records
7. FMEA Report

---
## Appendices
- Appendix A: HRS-to-RTL Traceability Matrix
- Appendix B: Vivado Tool Qualification Test Suite
- Appendix C: CEH Test Plan
- Appendix D: Coding Guidelines Compliance Checklist
