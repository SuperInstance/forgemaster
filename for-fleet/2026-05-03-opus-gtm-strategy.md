# FLUX / GUARD: Competitive Analysis & Go-to-Market Strategy

*Claude Opus board-level strategic analysis. May 2026.*

## 1. Competitive Landscape

### Layer 1: Formal Verification Tools (Adjacent, Not Direct)

| Tool | Owner | Price | Weakness vs. FLUX |
|---|---|---|---|
| Jasper Gold | Cadence | $50K–$300K/seat | Software-only, no HW cert path, offline analysis |
| VC Formal | Synopsys | $80K–$250K/seat | Same. No runtime enforcement |
| Questa Formal | Siemens (fmr Mentor) | $40K–$200K/seat | Integrated with sim, still software, no DO-254 |
| OneSpin | Siemens (acq 2021) | $60K–$180K/seat | Specialized exhaustive checking, offline only |
| Certitude | Synopsys | $30K–$100K/seat | Simulation qualification, not constraint enforcement |

**Differentiation:** These tools prove properties offline. FLUX enforces them at runtime in certified hardware. Complementary, not competing. *"We validate what you verify."*

### Layer 2: Runtime Safety Hardware (Actual Competition)

| Product | Owner | Cert Level | Weakness vs. FLUX |
|---|---|---|---|
| AURIX TC3xx | Infineon | ISO 26262 ASIL-D | Fixed MCU, no programmable constraints |
| TMS570 Hercules | TI | IEC 61508 SIL-3 | ARM Cortex-R lockstep, no constraint DSL |
| S32K safety MCUs | NXP | ASIL-D | Silicon baked-in safety, not programmable |
| ARM Cortex-M33 TrustZone | ARM | PSA L2 | Security isolation, not constraint enforcement |
| Safety IP cores | Synopsys, Cadence | ASIL-B/D, SIL | ASIC-only, no field-reconfigurable constraint update |

**Differentiation:** Every competitor has **static, baked-in safety logic**. FLUX is the first **programmable constraint enforcement ISA** with a hardware cert path. Update constraint programs without silicon respins.

### Layer 3: Hardware Simulation Accelerators (Pricing Ceiling)

Synopsys ZeBu EP1 and Cadence Palladium Z1: $500K–$3M for emulation. FLUX runs constraints on deployed systems. Different use case, but shows where premium buyers expect to pay.

### RISC-V Extension Landscape

No shipping ISA extension exists for native constraint operations. Closest precedents: Zc* (code size), V (vector), T (transactional memory). Xconstr as vendor extension ships now. Ratification takes 18–36 months.

---

## 2. Go-to-Market: First 10 Customers

### Rules
1. **Don't sell to chip companies first** — 18-month procurement cycles, NIH syndrome
2. **Sell to integrators with a certification problem NOW**

### Playbook

**Customers 1-3: Certification consultants**
- DO-254/ISO 26262 compliance houses (DER Engineering, Engenuity Aviation, Qualtek, exida)
- 3-month evaluation engagement (~$25K consulting fee)
- They tell program managers what tools to use

**Customer 4: Robotic arm OEM pilot**
- Killer demo: collision avoidance with hardware constraint enforcement
- Target: Universal Robots, FANUC, Veo Robotics
- Free 90-day pilot for case study + co-presentation

**Customers 5-6: Defense FPGA integrators**
- Lockheed, Raytheon, L3Harris, BAE Systems
- DO-254 DAL A requirements for FPGA flight control
- $200K–$500K engagements
- Find at DO-254 Symposium (Oct/Nov) and DASC

**Customers 7-8: Automotive ADAS Tier 1**
- Continental, Aptiv, ZF, Bosch
- ASIL-D constraint enforcement for ADAS processing
- $75K–$250K IP licenses

**Customers 9-10: Academic anchors**
- Avionics: Draper Lab, MIT Lincoln Lab, Georgia Tech
- Robotics: CMU RI, MIT CSAIL, Stanford FRL
- Research license at cost → co-authored papers → engineer pipeline

### Revenue Model

| Customer Type | Deal Structure | ACV |
|---|---|---|
| Defense integrator | IP license + cert support | $150K–$500K |
| Automotive Tier 1 | IP license + annual support | $75K–$250K |
| Robotic OEM | Per-product royalty + integration | $50K + royalties |
| Certification consultant | Reseller margin (20–30%) | $30K–$80K |
| Academic | Research license | $5K–$15K |

Target: $1.5M ARR within 18 months of first ship.

---

## 3. Patent Strategy: Top 5 Inventions

### Patent 1: Constraint Enforcement Bytecode Architecture (FLUX ISA)
- Claims: apparatus (hardware processor with bitmask intersection opcode), method (runtime constraint enforcement in FPGA), system (≤2000 LUTs, ≤150mW, DO-254 certifiable)
- Prior art: Armstrong-Davenport (2003), Xilinx UltraFAST

### Patent 2: BitmaskDomain Representation ⭐ STRONGEST
- 12,324× speedup is quantifiable, reproducible, structurally novel
- Claims: domain as bitmask (O(1) intersection), arc consistency pipeline, violation detection via zero-bitmask
- **File this first.**

### Patent 3: GUARD DSL → Hardware Compilation
- Claims: compiler with proof certificate generation, DO-254 artifact co-generation, dual-target (FLUX + SystemVerilog)
- Protects toolchain moat

### Patent 4: Deterministic Certifiable Hardware Architecture
- Claims: bounded-latency constraint evaluation, single-port memory for race prevention, DO-254 methodology
- Protects certification moat directly

### Patent 5: RISC-V Xconstr ISA Extension
- Claims: native domain load/intersection/emptiness-test/violation-handler, trap integration, inline compilation
- File as vendor extension now, prior art for future licensing

**Timeline: File 5 provisionals within 30 days. Priority: BitmaskDomain → FLUX ISA → Cert methodology.**

---

## 4. Open-Source Strategy

### Open-Source Aggressively (Apache 2.0 + CLA)
- GUARD DSL parser and frontend → de facto standard
- FLUX ISA specification and simulator → third-party tool ecosystem
- RISC-V Xconstr specification → community adoption
- Academic BitmaskDomain edition → papers, prior art, mindshare

### Keep Proprietary
- Production BitmaskDomain synthesis optimizations
- FLUX synthesis toolchain (GUARD → FPGA bitstream) → **this is the product**
- DO-254 certification artifacts and methodology → **this is the moat**
- Commercial GUARD compiler optimizations
- Runtime safety monitor firmware

**Why Apache 2.0:** Defense and automotive customers can't use GPL/AGPL. CLA enables dual licensing.

---

## 5. Series A Narrative

### Title
"Every constraint we've ever proven in software is enforced in software. The hardware still doesn't know the rules."

### The Problem
Formal verification proves constraints in simulation. Then hardware ships without those proofs. Safety logic is bolted on — watchdog timers, range checks, lockstep cores. None understands the constraint. The deployed hardware is constraint-blind.

### Why Now
1. Constraint solving got fast (12,000× BitmaskDomain speedup)
2. FPGAs got certifiable (DO-254 DAL A path exists)
3. Safety liability exploded (737 MAX $20B+, Tesla NHTSA, robot fatalities)

### The Product
FLUX = constraint enforcement processor between application logic and actuators.
GUARD = DSL that compiles to FLUX or SystemVerilog.
Xconstr = RISC-V extension for native constraint operations.

### The Business
Tools/IP company. IP licensing: defense $150-500K, auto $75-250K, royalties from SoC implementations.
Exit: strategic acquisition $50-150M to Siemens/Cadence/Synopsys.

---

## 6. 90-Day Action Plan

### Days 1-30: Foundation
- File 5 provisional patents ($15-25K)
- Incorporate Delaware C-corp, IP assignment
- Find DER partner (most important relationship in year 1)
- Build robotic arm demo (UR5e + FLUX FPGA, 3-min video)

### Days 31-60: First Customers
- Submit paper/demo to DO-254 Symposium or DASC
- Cold outreach to 10 target FPGA/safety engineers
- Sign first pilot LOI (90-day free engagement)
- Brief 3 certification consulting firms

### Days 61-90: Revenue & Series A Prep
- Begin pilot deployment (founder full-time)
- 12-slide deck (demo video is slide 4)
- Target VCs: Playground Global, Shield Capital, Eclipse, In-Q-Tel, Lux
- First $25K+ paid engagement
- Submit DoD SBIR Phase I ($150K)

---

## 7. What Kills This Company

### Death 1: Certification Takes 3x Longer and 5x More Money
First-time DO-254 DAL A programs run 2-4x over schedule. The hardware isn't hard — documentation, tool qualification, DER negotiation is hard.
**Mitigation:** Hire DER before writing production code. Budget $1.5M and 24 months. Target DAL C first.

### Death 2: Strategic Acquirer "Partner-to-Acquire-to-Kill"
EDA company approaches for "ecosystem partnership," studies your tech, builds competing capability, offers depressed acquisition.
**Mitigation:** Delay partnerships until 2+ paying customers + filed patents. IP non-compete clauses. Run parallel processes (Siemens ↔ Cadence ↔ Synopsys).

### Death 3: Team Can't Reach Certification-Grade Quality
Research team lacks certified silicon experience. DO-254 requires different skills than speedup benchmarks.
**Mitigation:** First two hires must have DO-254 DAL A / ISO 26262 ASIL-D shipping experience ($180K+ each). Start tool qualification in parallel with product design. Read ARP4754A, DO-254, DO-178C before first DER meeting.

---

## Board-Level Summary

| Dimension | Status | Critical Action |
|---|---|---|
| IP Protection | Urgent — file now | 5 provisionals within 30 days |
| Certification Moat | Real but unproven | DER partner before Day 30 |
| GTM | Clear path via cert consultants + defense | First pilot signed by Day 60 |
| Competition | Adjacent, not direct | Reframe as complement to EDA tools |
| Exit | $50–150M strategic acquisition | Siemens, Cadence, Synopsys |
| Killer Risk | Cert timeline and team skills gap | Hire certified silicon experience |
| Open-Source | Apache 2.0 on GUARD + ISA spec | Drives ecosystem without surrendering moat |

**The single most important thing in the next 30 days:** Get a DER-qualified engineer in the room. Have them scope the DO-254 effort honestly. Everything — valuation, timeline, customer promises, Series A close date — depends on that number being real.

---

*The certification moat is unusual in deep tech: unlike performance claims (which can be matched by a better engineer) or patents (which can be designed around), DO-254 DAL A certification artifacts are essentially non-fungible — tied to a specific design, tool qualification, and DER relationship. The strategy: make cert artifacts so embedded in customer programs that switching costs are measured in years, not dollars.*
