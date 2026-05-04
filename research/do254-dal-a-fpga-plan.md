# DO-254 Level A Certification Plan for Constraint Checker IP Core (CC-IP)
**Revision 1.0 | Date: 2024-05-20 | Approved By: Design Assurance Authority (DAA)**
---
## Core Scope & Compliance
This plan aligns with **DO-254 Edition 10, Section 11 (Certification Plan)** and FAA Order 8110.105/EASA CS-25.1309 for DAL A (highest assurance level) hardware. The CC-IP is a zero-latency combinational constraint checker targeting the Xilinx UltraScale+ XCZU7EV-FFVA1156-2E, with specified specs: 44,243 LUTs, 2.58W maximum power, and zero combinational latency for constraint conflict evaluation.

---

## 1. Planning Phase Deliverables (DO-254 §11.4.1)
Mandatory baseline planning artifacts for DAL A compliance:
| Deliverable | Purpose |
|-------------|---------|
| **Hardware Requirements Specification (HRS)** | Formal, testable requirements: e.g., ≤45k LUT usage, ≤2.6W power, zero latency, detection of 12 constraint conflict types (clock domain crossings, I/O standard clashes, timing exception errors) |
| **Hardware Design Description (HDD)** | Architecture block diagram, RTL hierarchy, synthesis/implementation flow, and floorplan for XCZU7EV |
| **Verification Plan (VP)** | Defines simulation, formal verification, and CEH test activities |
| **Tool Qualification Plan (TQP)** | Qualification activities for Xilinx Vivado 2023.1 toolchain |
| **Configuration Management Plan (CMP)** | Controls versioning of all hardware deliverables |
| **Risk Management Plan (RMP)** | Identifies DAL A-specific risks (tool bugs, timing closure gaps) and mitigations |
| **Failure Mode & Effects Analysis (FMEA)** | Maps CC-IP failure modes to system-level impacts for DAL A hazard mitigation |
| **Traceability Matrix** | Links every HRS requirement to RTL lines, test cases, and certification evidence |

---

## 2. Hardware Design Standards & Coding Guidelines (DO-254 §11.4.2)
Mandatory rules for deterministic, DAL A-compliant RTL (zero-latency combinational logic only):
### 2.1 Language Rules
- Exclusively use VHDL-2008; no SystemVerilog, Verilog-2001, or implicit nets
- All variables and signals must be explicitly declared with full type definitions
### 2.2 Zero-Latency Constraints
- No sequential logic: no flip-flops, clocks, resets, or inferred latches
- All `case` statements must be exhaustive; include a default error-triggering case
- No combinational loops: all signal assignments must have a single, non-feedback source
### 2.3 Xilinx UltraScale+ Specific Rules
- Use Xilinx UG954 (HDL Libraries Guide) primitives only when required; prefer synthesized constructs for portability
- Floorplan CC-IP to a dedicated 10x10 CLB region on XCZU7EV to minimize routing delays
- Limit logic to LUTs/MUXes to stay within the 44,243 LUT budget; avoid DSP blocks unless absolutely necessary
### 2.4 Naming & Traceability
- Descriptive, hierarchical signal names (e.g., `top_ccip.constraint_clk_conflict`)
- Every RTL line includes a comment linking to its unique HRS requirement ID
- Use Vivado RTL Analysis and Polarion ALM to automate traceability reporting

---

## 3. Element-Level Verification (Simulation + Formal) (DO-254 §11.7)
### 3.1 Core Objectives
Prove the CC-IP implements all HRS requirements, has no unintended logic, and meets zero-latency specs.
### 3.2 Simulation Testing
- **Tool**: Siemens Questa Advanced Simulator 2023.4
- **Testbenches**: Directed testbenches for every HRS requirement; constrained random testbenches for valid/invalid constraint sets
- **Latency Validation**: Verify output changes within 0 simulation time units of input updates using zero-delay timing models
### 3.3 Formal Verification
- **Tools**: Siemens Questa Formal 2023.4 + Vivado Formal 2023.1
- **Activities**:
  1. Equivalence checking between RTL and a golden VHDL-2008 reference model
  2. Prove no inferred latches, combinational loops, or uninitialized signals
  3. Property-based verification: Enforce requirements such as `assert (valid_constraints = '1') -> (pass = '1')`
  4. Validate all unreachable code is intentional and documented
### 3.4 Verification Deliverable
A formal report linking all test cases, coverage results, and formal proofs to HRS requirements.

---

## 4. Certification Engineering Hardware (CEH) Process (DO-254 §11.7.4)
### 4.1 CEH Platform
Xilinx ZCU111 Evaluation Board (XCZU7EV-FFVA1156-2I) with a custom test harness integrating the CC-IP.
### 4.2 Test Setup
- JTAG for bitstream loading and output signal readback
- PCIe for automated constraint vector input and result capture
- Oscilloscope to validate zero-latency output response
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
