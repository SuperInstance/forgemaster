# FLUX-LUCID — Investor One-Pager v2

---

## One-Line Pitch

**FLUX-LUCID is the first silicon-level constraint enforcement unit for AI inference — moving the root of trust from software to hardware so certified autonomous systems can legally deploy.**

---

## Problem

Uncertified AI is legally undeployable in safety-critical markets. Software-based safety layers (hypervisors, runtime monitors) fail DO-254/ISO 26262 audits because they are vulnerable to bit-flips, adversarial inputs, and non-deterministic execution paths. The result: $175B in addressable AI-enabled hardware is locked out of aerospace, automotive, and medical deployment. No current AI accelerator — NVIDIA, Qualcomm, or Tesla — carries a hardware safety certification. They score zero on any formal safety metric.

---

## Solution

FLUX-LUCID enforces behavioral constraints at the silicon layer — not in software.

- **FLUX Constraint VM**: Formally specified virtual machine with 42 opcodes and provable execution bounds, verified in Coq. Constraints cannot be bypassed at runtime.
- **Mask-Locked Inference**: Weights are immutable at deployment. No adversarial weight-space attack surface. This is a deliberate architectural choice — edge certification requires immutability; model updates ship as new masks.
- **Safe-TOPS/W**: A new benchmark weighting inference throughput by verified safety compliance. FPGA prototype achieves 28.8 Safe-TOPS/W. Every competing chip scores zero: no hardware-enforced constraint boundary exists in any current design.

Why not just wrap a standard chip in software? Because software safety layers fail certification audits. DO-254 DAL A requires the root of trust to be in silicon — it cannot be delegated to a hypervisor or a runtime monitor.

---

## Traction

| Milestone | Status |
|---|---|
| 20 published open-source packages | Complete |
| 74+ automated tests | Passing |
| EMSOFT-format academic paper (35KB, 464 lines) | Complete |
| FPGA prototype (Artix-7) at 28.8 Safe-TOPS/W | Running |
| 4 provisional patent drafts | Filed |
| DO-254 DAL A certification roadmap | Executing |

---

## Market

- **DO-254 / ISO 26262 AI hardware TAM**: $175B
- **eVTOL** (Joby, Archer, Wisk): $30B by 2030 — FAA/EASA require deterministic, certifiable AI inference; no current accelerator qualifies
- **Automotive L4/L5**: ISO 26262 ASIL-D mandates hardware-level functional safety for perception and control; no AI inference chip holds this certification today
- **Entry wedge**: eVTOL OEMs face a binary choice — certifiable inference silicon or no AI. We are the only credible hardware path to first flight.

---

## Business Model

- **IP licensing**: FLUX constraint VM core licensed per chip to OEMs and Tier-1 suppliers ($0.50–$2.00/unit royalty at volume)
- **Tool licensing**: FLUX constraint toolchain (compiler, verifier, simulator) as annual developer SaaS
- **NRE + reference design**: Custom constraint profiles for specific platforms (one-time engagement fee)
- **Exit comparables**: ARM IP acquisitions ($50–150M Series B/C); strategic acquirers include Honeywell, Collins Aerospace, Synopsys, Cadence

---

## Team

**Casey Digennaro** — founder, constraint theory research, FLUX architecture design, formal verification pipeline lead.

**Cocapn Fleet** — 9-agent AI engineering system. Shipped 20 packages, 74+ tests, 35KB academic paper, and full FPGA prototype in parallel. Production-grade HDL, Coq proofs, and benchmark infrastructure.

Research focus: hardware-enforced constraint satisfaction, ternary ROM inference, DO-254 compliance architecture.

---

## Ask

**$500K–$1.5M pre-seed**

| Use of capital | Allocation |
|---|---|
| 22nm test chip tape-out (TSMC / GlobalFoundries) | $1.0–1.2M |
| EDA toolchain + physical design | $150K |
| DO-254 DAL A certification consultant engagement | $100K |
| 12-month runway to Series A | Remainder |

**Series A trigger**: Test chip silicon validated, first OEM letter of intent signed, DO-254 milestone documented.

---

*FLUX-LUCID · Constraint Enforcement Silicon for Certified AI*
*Contact: Casey Digennaro*
