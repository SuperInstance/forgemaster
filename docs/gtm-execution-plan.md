# FLUX — Go-to-Market Execution Plan

## Overview

**Product:** FLUX constraint-to-silicon pipeline (GUARD DSL → FLUX bytecode → GPU/FPGA/ASIC)
**Target market:** Safety-critical compute certification (aerospace, automotive, medical, defense)
**GTM motion:** Open-core bottom-up (developer adoption) + enterprise top-down (certification programs)
**Timeline:** Q3 2026 – Q2 2027 (4 quarters, pre-seed runway)

---

## Q3 2026: Foundation — OSS Release + Academic Credibility

### Theme: "Prove the Science"

**Key Deliverables:**

| Milestone | Owner | Target Date | Success Metric |
|-----------|-------|-------------|----------------|
| OSS release (flux-vm, guard2mask, flux-compiler) | Engineering | Jul 15 | Public GitHub, Apache 2.0 |
| FLUX-LUCID benchmark publication | Casey | Aug 1 | ArXiv preprint + blog |
| EMSOFT paper submission | Casey + academic partner | Aug 15 | Submitted, peer review |
| Website launch (flux.dev) | Marketing/Casey | Jul 1 | Live with docs + benchmark |
| Contributor guide + RFC process published | Engineering | Jul 30 | RFC-0001 merged |
| 3 academic partnerships formalized | Casey | Sep 30 | Signed MOUs |

**Budget:** $150K (cloud infra, website, academic collaboration stipends)

**Detailed Actions:**

1. **July 2026 — OSS Launch**
   - Publish GitHub monorepo: `flux-vm`, `guard2mask`, `flux-compiler`, `flux-lucid-benchmark`
   - Release binary packages: `brew install flux`, `apt install flux-vm`, Docker images
   - Publish comprehensive docs: GUARD DSL reference, FLUX bytecode spec, getting-started tutorial
   - Record 15-minute demo video: GUARD constraint → FLUX bytecode → FPGA execution with Safe-TOPS/W measurement
   - Blog post series: "Why Safe-TOPS/W = 0 for Every GPU", "The Galois Connection That Makes FLUX Work", "Your First GUARD Constraint"

2. **August 2026 — Academic Push**
   - Submit EMSOFT paper: "FLUX: Provably Correct Compilation of Safety Constraints to Hardware"
   - ArXiv preprint simultaneously
   - Present at local meetups (Bay Area formal methods, embedded systems groups)
   - Engage r/programming, Hacker News, formal methods community (Coq/Isabelle mailing lists)

3. **September 2026 — Community Seeding**
   - First RFC: FLUX bytecode v2 extensions for ASIC targets
   - Office hours (weekly Zoom): Casey + engineering answering community questions
   - Target: 100 GitHub stars, 10 external contributors filing issues/PRs

**Risks & Mitigations:**
- *Risk:* EMSOFT rejection → Submit to CAV, TACAS, or POPL as backup
- *Risk:* Low OSS adoption → Focus on academic partnerships as early champions
- *Risk:* Community finds specification bugs → Welcome it; fast turnaround on issues = credibility

---

## Q4 2026: Validation — Pilot Partners + FPGA Demo

### Theme: "Prove the Product"

**Key Deliverables:**

| Milestone | Owner | Target Date | Success Metric |
|-----------|-------|-------------|----------------|
| 3 pilot LOIs signed (eVTOL/aerospace) | BD/Casey | Oct 31 | Signed LOIs with pilot scope |
| FPGA IP demo (Xilinx UltraScale+) | Engineering | Nov 15 | Live demo, Safe-TOPS/W on real board |
| FLUX Certify alpha (internal) | Engineering | Dec 15 | Internal SaaS platform operational |
| First external GUARD spec contributed | Community | Dec 31 | Non-FLUX-authored spec in repo |
| Conference presentation (DICET or similar) | Casey | Nov 30 | Talk accepted + delivered |
| 200 GitHub stars | All | Dec 31 | Star count |

**Budget:** $250K (FPGA dev boards, pilot support, conference travel, BD expenses)

**Pilot Partner Strategy:**

1. **Pilot #1 — eVTOL OEM (Target: Joby, Archer, or Beta Technologies)**
   - Use case: Flight control constraint verification on FPGA
   - Offer: Free FLUX consulting for 6 months + certification evidence package
   - Ask: Public case study + letter of intent for FLUX Certify
   - Timeline: Oct–Dec 2026 integration, Jan 2027 first certification artifact

2. **Pilot #2 — Aerospace Tier 1 (Target: Collins, Honeywell, or Moog)**
   - Use case: DO-254 FPGA element analysis automation
   - Offer: FLUX compiler integrated into their existing DO-254 toolchain
   - Ask: Co-presentation at conference + purchase order for FLUX Certify

3. **Pilot #3 — Defense Prime (Target: Lockheed, Northrop, or Raytheon)**
   - Use case: EW signal processing constraint verification
   - Offer: Custom GUARD spec development for their signal chain
   - Ask: SBIR/STTR co-proposal + procurement pathway

**FPGA IP Demo (Critical Path):**
- Target hardware: Xilinx Zynq UltraScale+ ZCU102 (widely available, certifiable)
- Demo flow: GUARD spec → FLUX compile → FPGA bitstream → Safe-TOPS/W measurement
- Deliverable: Video + reproducible benchmark kit (board + SD card + instructions)
- Stretch goal: Run on Intel Agilex 7 as second platform proof

**Risks & Mitigations:**
- *Risk:* Pilots want features not yet built → Scope tightly, focus on one use case per pilot
- *Risk:* FPGA demo reveals performance gap → Optimize bytecode interpreter, document honestly
- *Risk:* BD cycle too slow → Casey does direct founder-to-founder outreach, skip enterprise sales

---

## Q1 2027: Product-Market Fit — SaaS Beta + Third-Party Validation

### Theme: "Prove the Market"

**Key Deliverables:**

| Milestone | Owner | Target Date | Success Metric |
|-----------|-------|-------------|----------------|
| FLUX Certify SaaS private beta | Engineering | Jan 31 | 5 beta users (3 pilots + 2 new) |
| Safe-TOPS/W third-party validation | External lab | Feb 28 | Published independent report |
| DO-178C tool qualification plan submitted | Engineering + DER | Mar 15 | FAA acknowledgment of PSAC |
| 3 pilot → paid conversion (≥$200K TCV each) | BD/Casey | Mar 31 | Signed contracts |
| 350 GitHub stars, 25 contributors | All | Mar 31 | Community metrics |
| Series A deck finalized | Casey | Mar 15 | Deck reviewed by 3 VCs |
| Hire VP Engineering + 2 senior engineers | Casey/Recruiting | Mar 31 | Onboarded |

**Budget:** $600K (SaaS infra, third-party validation, hires, legal for contracts)

**FLUX Certify SaaS — MVP Feature Set:**

1. **GUARD Spec Upload & Validation**
   - Parse GUARD DSL, check well-formedness, report constraint coverage
   - Visual constraint explorer (interactive graph)

2. **FLUX Compilation Dashboard**
   - Compile GUARD → FLUX bytecode with proof artifacts
   - Structural coverage report (MC/DC, statement, decision)
   - Certification evidence package export (DO-178C/254 compatible)

3. **FPGA Target Selection**
   - Pre-qualified targets: Xilinx UltraScale+, Intel Agilex
   - One-click bitstream generation + Safe-TOPS/W measurement
   - Certification artifact bundle download

4. **Traceability Matrix**
   - Requirement → GUARD spec → FLUX bytecode → FPGA LUT mapping
   - Export to IBM DOORS, Jama Connect, or CSV

**Third-Party Validation Strategy:**
- Partner with independent test lab (target: DNV, TÜV SÜD, or UL)
- Provide FLUX-LUCID benchmark kit (FPGA board + pre-built bitstreams)
- Ask lab to independently measure Safe-TOPS/W and verify compilation correctness claims
- Publish results regardless of outcome (credibility > perfection)
- Timeline: 8-week engagement, $80K budget

**Series A Preparation:**
- Target raise: $20–30M Series A (Q2 2027 close)
- Target investors: Deep tech / defense-tech VCs (a16z American Dynamism, Founders Fund, Lux Capital, DCVC)
- Key metrics for pitch: 3 paid customers, validated Safe-TOPS/W, growing OSS community, DO-178C pathway started

**Risks & Mitigations:**
- *Risk:* Third-party validation reveals lower Safe-TOPS/W → Document methodology, improve compiler, be transparent
- *Risk:* SaaS beta is buggy → Restrict to 5 carefully supported users, weekly bug triage
- *Risk:* Pilot contracts delayed → Offer extended free trials, focus on relationship over revenue timing

---

## Q2 2027: Scale — Series A + Certification Campaign

### Theme: "Prove the Trajectory"

**Key Deliverables:**

| Milestone | Owner | Target Date | Success Metric |
|-----------|-------|-------------|----------------|
| Series A term sheet signed | Casey | May 31 | $20–30M at agreeable terms |
| DO-178C DAL A certification campaign kickoff | Engineering + DER | Apr 15 | PSAC approved by FAA |
| DO-254 DAL A element analysis started | Engineering | Apr 30 | First artifact package |
| FLUX Certify GA (general availability) | Engineering | Jun 15 | 10+ paying customers |
| 500 GitHub stars, 50 contributors | All | Jun 30 | Community metrics |
| ISO 26262 ASIL D pre-assessment | Engineering + assessor | Jun 30 | Assessment report |
| 6 total enterprise customers | BD | Jun 30 | Signed contracts |
| Revenue run-rate: $8M ARR | Finance | Jun 30 | Bookings + pipeline |

**Budget:** $400K (Series A legal, certification kick-off, conference sponsorships)

**Series A Execution:**
- Target close: end of May 2027
- Use of proceeds: 18-month certification push (DO-178C DAL A + DO-254 DAL A + ISO 26262 ASIL D)
- Key narrative: "First company to certify GPU/FPGA compute for safety-critical systems"
- Data room: customer contracts, Safe-TOPS/W validation, patent portfolio, OSS metrics, team bios

**Certification Campaign Kickoff:**
- Engage DER (Designated Engineering Representative) for DO-178C guidance
- Engage FAA-certified lab for DO-254 testing
- Begin Tool Qualification Level 1 (TQL-1) package for FLUX compiler
- Target: DO-178C DAL A tool qualification by Q4 2027

**FLUX Certify GA Launch:**
- Pricing: $100K/yr (standard), $300K/yr (with certification support), $500K/yr (full service)
- Launch event: Host "Safe Compute Summit" (virtual + in-person, target 500 attendees)
- Press: TechCrunch, IEEE Spectrum, Aviation Week exclusive
- Customer success: Publish case studies from 3 pilot partners

**Risks & Mitigations:**
- *Risk:* Series A terms unfavorable → Bootstrap on pilot revenue, raise smaller bridge
- *Risk:* FAA rejects PSAC → Engage DER earlier, revise plan, resubmit (6-8 week cycle)
- *Risk:* Key hire unavailable → Offer competitive equity + mission appeal (safety-critical = meaningful)

---

## Key Metrics Dashboard (Tracked Monthly)

| Metric | Q3 2026 Target | Q4 2026 Target | Q1 2027 Target | Q2 2027 Target |
|--------|---------------|---------------|---------------|---------------|
| GitHub stars | 100 | 200 | 350 | 500 |
| External contributors | 10 | 15 | 25 | 50 |
| Enterprise customers (signed) | 0 | 0 | 3 | 6 |
| ARR | $0 | $0 | $600K | $8M |
| Safe-TOPS/W (FLUX-LUCID) | 20.17 | 22+ | 25+ (validated) | 25+ (validated) |
| Team size | 2 | 3 | 6 | 8 |
| Patents filed | 1 | 2 | 3 | 4 |
| Conference talks | 1 | 2 | 3 | 4 |

---

## Budget Summary

| Quarter | Spend | Cumulative |
|---------|-------|------------|
| Q3 2026 | $150K | $150K |
| Q4 2026 | $250K | $400K |
| Q1 2027 | $600K | $1.0M |
| Q2 2027 | $400K | $1.4M |
| **Total (12 months)** | **$1.4M** | — |

*Remaining $3.6M of pre-seed held for certification costs and extended runway through Series A.*

---

## Success Criteria for Series A Readiness (Q2 2027)

1. ✅ 3+ paying enterprise customers ($200K+ TCV each)
2. ✅ Safe-TOPS/W independently validated by third-party lab
3. ✅ FLUX Certify SaaS in GA with 10+ users
4. ✅ DO-178C PSAC approved, certification campaign underway
5. ✅ 500+ GitHub stars, 50+ contributors
6. ✅ Revenue run-rate ≥ $6M ARR
7. ✅ Team of 6+ (including VP Eng + formal methods lead)
8. ✅ 3+ patents filed

*If ≥6 of 8 criteria met → proceed with Series A raise.*
