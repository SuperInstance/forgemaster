# FLUX Strategic Action Plan
**Source:** Kimi 100-Agent R&D Swarm (2026-05-05) — 100K+ words across 10 missions
**Status:** Working draft for Casey
**Date:** 2026-05-04

---

## IMMEDIATE — 48 Hours (P0 Vulnerabilities)

### P0-1: Supply Chain Compromise (M1 Agent 9 — Critical)
- [ ] Run `cargo tree` on all 14 crates; generate full transitive dependency list
- [ ] Pin every dependency in `Cargo.lock` and commit; enable `--locked` in all CI builds
- [ ] Audit `bitvec`, `half`, `hashbrown` specifically — these touch INT8 x8 packing primitives
- [ ] Enable `cargo-audit` in CI; fail build on any RUSTSEC advisory
- [ ] Move critical deps to vendored `vendor/` subtree or internal mirror

### P0-2: FLUX-C VM Bytecode Injection / Partial Escape (M1 Agent 6 — Critical)
- [ ] Audit `LD.KERNEL` + `ST.SHARED` + `BRA.WARP` instruction combinations for arbitrary memory access
- [ ] Implement cryptographic signing of FLUX-C bytecode: sign at compile time, verify at VM load time
- [ ] Add bytecode whitelist validator that rejects instruction sequences outside approved safe patterns
- [ ] Document threat model boundary: FLUX-C must be treated as untrusted input, not trusted internal artifact

### P0-3: INT8 Overflow — Silent Wraparound (M1 Agent 1 — feeds P1 but needs immediate doc)
- [ ] Write a one-page "INT8 Safety Boundary" document now: what values are safe, what wraps silently
- [ ] Add compile-time warning (stderr) when GUARD DSL compiles a constraint where input range exceeds INT8_MAX (127) or INT8 unsigned boundary (255)
- [ ] Disable INT8 packing by default for any constraint where range analysis cannot prove bounded inputs

---

## THIS WEEK — Days 3–7

### Test Vector Integration (M5 — 6,500 vectors)
- [ ] Locate `test-vectors.json` (already in repo root per git status — untracked)
- [ ] Create `tests/vectors/` directory; move file there; commit
- [ ] Write harness: parse JSON, feed each vector to FLUX-C VM, assert expected output
- [ ] Integrate into CI — every PR must pass all 6,500 vectors
- [ ] Target: <2.1% overlap confirmed (swarm claims this; verify with dedup check)
- [ ] Add vector categories to CI matrix: boundary values, adversarial, domain-specific, performance stress

### Code Module Extraction (M9 — 10 runnable modules)
- [ ] Locate M9 outputs in `kimi-swarm-results/`; catalog the 10 modules
- [ ] Priority order for extraction: Wasm VM, gRPC service, eBPF filter (highest utility)
- [ ] For each module: run as-is, fix compilation errors, add to `examples/` or `crates/`
- [ ] Identify which modules overlap with existing crates (avoid duplication)
- [ ] Target: at least 3 modules compiling and passing their own tests by end of week

### Proof Boundary Document (M1 Cross-Mission — Security + Correctness)
- [ ] Write `docs/proof-boundaries.md` — one clear document stating:
  - What the 38 formal proofs cover
  - What they explicitly do NOT cover (INT8 representation gap, hardware assumptions, compiler host trust)
  - The Galois connection falsification risk (M1 Agent 7): where the abstract domain diverges from concrete INT8 semantics
- [ ] This document is a prerequisite for DO-330 TOR and investor due diligence

### Domain Constraint Libraries (M2 — 248 GUARD constraints, 10 industries)
- [ ] Locate M2 outputs; extract the 4 universal archetypes: Rate-of-Change Limits, Spatial Envelopes, Interlock Dependencies, Power Budgets
- [ ] Create `constraints/` directory with one file per domain (aerospace, automotive, medical, nuclear, etc.)
- [ ] Validate each constraint compiles and produces expected FLUX-C output
- [ ] Tag constraints with severity/standard (DO-178C, ISO 26262, IEC 61508, IEC 62304)

---

## THIS MONTH — Weeks 2–4

### Certification Path Initiation (DO-330 → $435K, 18 months)
- [ ] **Week 2:** Contact TÜV SÜD functional safety team in Munich — request intro meeting
  - Target: signed engagement letter by end of month ($25K deposit budgeted)
- [ ] **Week 2:** Draft Tool Operational Requirements (TOR) outline — DO-330 template exists from M10 Agent 6
- [ ] **Week 3:** Post job listing for Functional Safety Manager ($120K salary; hire by Month 2 per roadmap)
  - Source: embedded world attendees, INCOSE, SAE International safety-critical mailing lists
- [ ] **Week 4:** Internal test suite kickoff — target 100% opcode coverage for all 43 FLUX-C opcodes
- [ ] Budget reality check: $435K over 18 months breaks down as $205K (Phase 1) + $125K (Phase 2) + $105K (Phase 3)
  - Phase 1 alone needs to start this month or the 18-month clock slips

### Blog Post Publication — Content Pipeline Ready (M6 — 10 posts)
- [ ] Locate M6 outputs in `kimi-swarm-results/`
- [ ] Publish in swarm-recommended sequence:
  - **Week 2:** Hook posts (Posts 1, 5, 6) — "Why Your GPU Can't Prove Anything" is the lead
  - **Week 3:** Deep technical (Posts 2, 3, 7)
  - **Week 4:** Industry/benchmark (Posts 4, 8, 9)
  - **Month 2:** Vision post (Post 10)
- [ ] Each post needs: code examples that compile, benchmark numbers verified against actual hardware, links to crates.io
- [ ] Publish to: FLUX blog, dev.to, Hacker News (Show HN), r/rust, r/embedded, LinkedIn

### Competitive Positioning
- [ ] Register trademarks: GUARD™ and FLUX™ (M10 Agent 5 — critical, easy to miss)
- [ ] Apply to NVIDIA Inception program (startup program, free credits, co-marketing)
- [ ] Contact Lynx Software (acquired CoreAVI Nov 2024) — GPU safety overlap, fastest partnership path
- [ ] Submit EMSOFT paper with M3 sections — check next submission deadline
- [ ] Update crates.io README files to include: 90.2B c/s benchmark, Galois connection summary, certification roadmap status

---

## KEY DECISIONS NEEDED — Casey Must Decide

### 1. Pricing Strategy (Month 6 decision; groundwork needed now)
**Context:** M10 Agent 2 proposes: Free Community → Pro $299/seat/mo → Team $599/seat/mo → Enterprise custom ($12K–$25K/seat/yr) → Cloud $0.50/1M checks
**Question for Casey:**
- Do you anchor on value (20% discount to Polyspace ~$5K/seat/yr) or undercut aggressively (50–70% cheaper)?
- Cloud consumption pricing: opt-in feature or default for CI/CD integrations?
- Certification kits: $15K–$25K standalone vs. bundled with Enterprise tier?

### 2. Certification Investment Decision (Must commit or not by end of May)
**Context:** $435K over 18 months unlocks 100% of addressable market; without it, only 20% (early adopters). First revenue shifts from Month 6-8 to Month 14-18 without certification.
**Question for Casey:**
- Commit to DO-330 first (aviation, 18 months, $435K base)? Or ISO 26262 first (automotive, potentially faster market)?
- Fund from personal runway or require Seed close first?
- If Seed not closing fast: minimum viable certification spend is Phase 1 only ($205K) to hold timeline

### 3. Open Source Boundaries
**Context:** Apache 2.0 is currently correct for the safety-critical buyer base. The swarm (M10 Agent 5) strongly recommends never changing the license. But the moat is NOT the code.
**Question for Casey:**
- What stays Apache 2.0 forever: core GUARD compiler, FLUX-C VM, all 14 crates — is this committed publicly?
- What is commercial-only: GPU acceleration layer, certification kits, domain constraint libraries, enterprise integrations?
- Will you offer enterprise source licensing ($500K+/yr deals, e.g., Boeing/Airbus in-house forks)?

### 4. Multi-Tenancy / Cloud Deployment Scope
**Context:** M1 (Agent 2, M8 synthesis) found that RTX 4050 + no ECC + no MIG creates practical timing side-channels and Rowhammer risk in multi-tenant environments. Cloud product needs A100/H100 with MIG.
**Question for Casey:**
- Is FLUX Cloud a Year 1 product or Year 2? The roadmap says Month 7 beta — is that viable without ECC hardware?
- Single-tenant on-prem only until A100/H100 infrastructure is in place?

### 5. Seed Raise vs. Bootstrap
**Context:** M10 roadmap builds around $3.5M Seed. Budget: $2.25M salaries (10 hires) + $435K certification + $815K ops/contingency.
**Question for Casey:**
- If Seed closes in Month 1: execute roadmap as written
- If Seed delayed 3–6 months: cut to 4 hires, delay FSM to Month 3, Phase 1 certification only
- If bootstrapping: certifications slip 12 months; addressable market stays at 20%; risk window open for first GPU-native competitor

---

## METRICS TO TRACK — Weekly

| Metric | Now | Month 3 Target | Month 12 Target |
|--------|-----|---------------|-----------------|
| crates.io downloads (total) | — | 2,000 | 20,000 |
| GitHub stars | — | 500 | 3,500 |
| CI passing test vectors | 0 | 6,500 | 6,500 + new |
| Paying customers | 0 | 0 | 20 |
| ARR | $0 | $0 | $500K |
| TÜV SÜD status | Not contacted | Intro held | Pre-assessment |
| Blog posts published | 0 | 6 | 10 |
| P0 vulns closed | 0/3 | 3/3 | 3/3 |

---

*Generated from 100-agent Kimi R&D Swarm output — 2026-05-05*
*Primary sources: M1 (Attack Surface), M5 (Test Vectors), M6 (Blog), M9 (Code), M10 (Strategy)*
