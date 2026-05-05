# FLUX — Open-Source Community Strategy

## Executive Summary

**Goal:** Build FLUX as the industry-standard safety-certified compute toolchain through an open-core model that balances broad adoption with sustainable commercial licensing.

**Core principle:** The compiler, VM, and specification are open. Certification tooling and enterprise features are commercially licensed.

**Targets:**
- 500 GitHub stars in 6 months (by Q1 2027)
- 50 contributors in 12 months (by Q2 2027)
- 10 organizational users (companies using FLUX in production) by Q2 2027

---

## 1. Licensing Strategy

### Apache 2.0 — Open Core

The following components are released under **Apache License 2.0**:

| Repository | Description | License |
|------------|-------------|---------|
| `flux-vm` | FLUX bytecode interpreter (Rust) | Apache 2.0 |
| `guard2mask` | GUARD DSL parser, type checker, optimizer | Apache 2.0 |
| `flux-compiler` | Full compilation pipeline (GUARD → FLUX bytecode) | Apache 2.0 |
| `flux-lucid-benchmark` | Safe-TOPS/W benchmark suite | Apache 2.0 |
| `flux-spec` | FLUX bytecode specification (Markdown + formal) | Apache 2.0 |
| `flux-docs` | Documentation, tutorials, examples | CC-BY-4.0 |
| `flux-rfc` | RFC process and proposals | CC-BY-4.0 |

**Why Apache 2.0:**
- Permissive enough for aerospace/defense companies (no GPL contagion concerns)
- Patent grant protects contributors and users
- Industry standard for infrastructure projects (Kubernetes, TensorFlow, Rust itself)
- Compatible with DO-178C/254 tool qualification (source code available for audit)

### BSL 1.1 — Enterprise Features

The following components use **Business Source License 1.1** (BSL):

| Component | Description | BSL Term | eventual License |
|-----------|-------------|----------|-----------------|
| `flux-certify` | Certification evidence generation, traceability matrix | 3 years | Apache 2.0 |
| `flux-fpga-ip` | Pre-certified FPGA IP cores (VHDL/Verilog) | 4 years | Apache 2.0 |
| `flux-saas` | FLUX Certify SaaS backend | 3 years | Apache 2.0 |
| `flux-asic` | ASIC target code generator | 4 years | Apache 2.0 |

**BSL Restrictions:**
- Non-production use: free (development, evaluation, research)
- Production use with certification: requires commercial license
- Change to open source after BSL term expires (3–4 years)
- Additional use grant: permitted for organizations with <$1M annual revenue

**Why BSL over SSPL / Elastic License:**
- Clearer legal language, tested in enterprise contracts
- Time-based open-sourcing creates trust (not a bait-and-switch)
- Compatible with aerospace/defense procurement requirements
- Used by: MariaDB, CockroachDB, Sentry (proven model)

---

## 2. Repository Structure

### Monorepo vs. Polyrepo

**Decision: Monorepo with workspace packages**

```
flux/
├── crates/
│   ├── flux-vm/           # Bytecode interpreter
│   ├── guard-parser/      # GUARD DSL parser (pest PEG)
│   ├── guard-types/       # GUARD type system
│   ├── guard-opt/         # GUARD optimizer
│   ├── flux-compiler/     # Full pipeline
│   ├── flux-debug/        # Source-level debugger
│   └── flux-lucid/        # Benchmark harness
├── specs/
│   ├── guard-dsl.md       # GUARD language specification
│   ├── flux-bytecode.md   # Bytecode specification
│   └── safe-tops-w.md     # Safe-TOPS/W benchmark specification
├── examples/
│   ├── aerospace/         # eVTOL flight envelope constraints
│   ├── automotive/        # ADAS safety constraints
│   └── medical/           # Diagnostic safety constraints
├── rfcs/                  # RFC proposals (numbered)
├── docs/                  # Documentation (mdbook)
├── tools/
│   ├── flux-fmt/          # GUARD formatter
│   ├── flux-lsp/          # LSP server (VS Code integration)
│   └── flux-test/         # Test runner + coverage
├── Cargo.toml             # Workspace root
├── LICENSE                 # Apache 2.0
├── LICENSE-BSL             # BSL for enterprise crates
└── README.md
```

**Why monorepo:**
- Atomic commits across compiler components
- Simplified CI/CD (one pipeline)
- Easier for contributors to navigate
- Cargo workspace = shared dependency management
- rfcs/ and specs/ alongside code = documentation stays fresh

---

## 3. Community Building Plan

### Phase 1: Seeding (Q3 2026 — Months 1–3)

**Goal:** First 100 stars, 10 contributors, basic community infrastructure

| Action | Timeline | Owner |
|--------|----------|-------|
| Launch GitHub repo with comprehensive README | Day 1 | Casey |
| Publish contributor guide (CONTRIBUTING.md) | Week 1 | Engineering |
| Create GitHub Discussions (Q&A + Ideas categories) | Week 1 | Casey |
| Set up Discord server (or Matrix — see Fleet alignment) | Week 1 | Casey |
| Record "FLUX in 15 Minutes" demo video | Week 2 | Casey |
| Publish 3 blog posts (problem, solution, technical) | Month 1 | Casey |
| Submit to Hacker News, r/programming, r/rust | Month 1 | Casey |
| Present at local meetup (Rust Bay Area, Formal Methods) | Month 2 | Casey |
| First "good first issue" labels (10 issues) | Month 1 | Engineering |
| Office hours (weekly, 30 min) | Ongoing | Casey |

**Contributor Onboarding Flow:**
1. Read CONTRIBUTING.md (setup instructions, coding standards, PR process)
2. Pick a `good first issue` from GitHub
3. Fork → branch → PR (CI runs automatically)
4. Review by maintainer (target: 48-hour turnaround)
5. Merge → contributor added to AUTHORS.md

### Phase 2: Growth (Q4 2026 — Months 4–6)

**Goal:** 200 stars, 25 contributors, first external RFC

| Action | Timeline | Owner |
|--------|----------|-------|
| Conference talk submitted (RustConf, OSDI, or similar) | Month 4 | Casey |
| Guest blog post on formal methods publication | Month 5 | Casey |
| FLUX hackathon (virtual, 48 hours, prizes) | Month 5 | Engineering |
| First RFC from external contributor | Target: Month 6 | Community |
| GUARD spec library (community-contributed examples) | Ongoing | Community |
| Integrations: VS Code extension, neovim plugin | Month 4–6 | Engineering + community |
| Benchmark submissions (external Safe-TOPS/W measurements) | Ongoing | Community |
| Partnership with Rust Foundation or Formal Methods group | Month 5 | Casey |

### Phase 3: Maturity (Q1–Q2 2027 — Months 7–12)

**Goal:** 500 stars, 50 contributors, organizational adoption

| Action | Timeline | Owner |
|--------|----------|-------|
| FLUXConf 2027 (first community conference, virtual) | Month 9 | Casey |
| FLUX in production: first external company deployment | Month 10 | Community |
| Governance board formation (3 community + 2 FLUX Inc.) | Month 10 | Casey |
| FLUX certification study group (helping users certify) | Month 8 | Engineering |
| Academic course adoption (university teaching FLUX) | Month 12 | Academic partners |
| FLUX Bounty program (sponsored by FLUX Inc.) | Month 9 | Casey |

---

## 4. RFC Process

### Overview

FLUX uses an RFC (Request for Comments) process for significant changes, modeled after Rust's RFC process.

### RFC Lifecycle

```
Draft → Submitted (PR to rfcs/) → Discussion (2 weeks) → 
  → Accepted / Rejected / Postponed → Implementation → Stabilization
```

### RFC Template

```markdown
# RFC-NNNN: [Title]

## Summary
One-paragraph summary of the proposal.

## Motivation
Why is this change needed? What problem does it solve?

## Detailed Design
Technical specification of the change.

## Alternatives Considered
What other approaches were evaluated?

## Unresolved Questions
What's still open for discussion?

## Certification Impact
How does this affect DO-178C/254/ISO 26262 certification?

## References
Links to prior art, academic papers, etc.
```

### RFC Categories

| Category | Examples | Review Period |
|----------|---------|---------------|
| Language (GUARD DSL) | New constraint types, syntax changes | 4 weeks |
| Bytecode (FLUX VM) | New opcodes, execution semantics | 4 weeks |
| Tooling | Build system, testing, CI changes | 2 weeks |
| Process | Governance, licensing, community | 2 weeks |
| Certification | Standards compliance, evidence changes | 6 weeks |

### Review Criteria

1. **Soundness:** Does it preserve the Galois connection correctness guarantee?
2. **Certification impact:** Does it affect existing certification artifacts?
3. **Backward compatibility:** Does it break existing GUARD specs?
4. **Implementation complexity:** Is the implementation tractable?
5. **Community benefit:** Does it serve a significant use case?

---

## 5. Governance Model

### Stage 1: BDFL (Q3 2026 – Q2 2027)

**Casey Digennaro as BDFL** (Benevolent Dictator for Life)

- Final decision authority on all RFCs
- Maintainer access control
- Release management
- Community moderation

**Why BDFL initially:**
- Speed of decision-making (critical for pre-seed startup)
- Coherent technical vision (Galois connection architecture)
- Accountability (one person owns the vision)
- Transition plan to community governance at maturity

### Stage 2: Governance Board (Q3 2027+)

**5-member governance board:**
- 2 FLUX Inc. representatives (Casey + VP Engineering)
- 3 community representatives (elected by contributors with ≥3 merged PRs)

**Board responsibilities:**
- RFC final approval
- Maintainer nominations
- License changes
- Community conduct enforcement
- Roadmap prioritization

### Maintainer Tiers

| Tier | Requirements | Privileges |
|------|-------------|-----------|
| Contributor | 1+ merged PR | RFC participation, Discord access |
| Reviewer | 10+ merged PRs, nominated by maintainer | PR review rights |
| Maintainer | 50+ merged PRs, board nomination | Merge rights, RFC approval |
| Core Maintainer | Board nomination + 1 year as maintainer | Release management, governance vote |

---

## 6. Community Health

### Code of Conduct

Adopt the **Contributor Covenant v2.1** — industry standard, used by Rust, Kubernetes, and thousands of projects.

**Enforcement:**
- Reports to: conduct@flux.dev
- Initial response: 48 hours
- Enforcement actions: warning → temporary ban → permanent ban
- Appeals: governance board review

### Inclusivity Practices

- **Documentation-first:** Every feature has docs before merge
- **`good first issue` labels:** Always 10+ available, with mentorship
- **Office hours:** Weekly, rotating time zones (US + EU friendly)
- **Language:** English primary, welcome multilingual contributions
- **Asynchronous-first:** All decisions happen in GitHub Issues/Discussions, not just meetings

### Recognition

- **AUTHORS.md:** All contributors listed
- **Release notes:** Contributor credits per release
- **Community spotlight:** Monthly blog post featuring contributor work
- **FLUXConf talks:** Sponsored speaking opportunities for contributors
- **Swag:** FLUX stickers, t-shirts for significant contributions (10+ PRs)

---

## 7. Marketing & Distribution

### Channels

| Channel | Purpose | Frequency |
|---------|---------|-----------|
| GitHub repo | Code, issues, RFCs, releases | Continuous |
| flux.dev (website) | Documentation, blog, benchmarks | Weekly blog |
| Discord/Matrix | Real-time community chat | Always on |
| Twitter/X (@flux_dev) | Announcements, links | 3x/week |
| YouTube | Tutorials, demos, conference talks | Biweekly |
| Hacker News / Reddit | Major announcements | Per release |
| Academic venues | Papers, talks, posters | Per conference |
| Podcasts | Interviews, technical deep dives | Monthly |

### Content Calendar (First 6 Months)

| Month | Blog Posts | Videos | Events |
|-------|-----------|--------|--------|
| 1 | 3 (Launch series) | 1 (Demo) | HN/Reddit launch |
| 2 | 2 (Technical deep dives) | 1 (Tutorial) | Meetup talk |
| 3 | 2 (RFC discussions) | 1 (RFC walkthrough) | EMSOFT paper |
| 4 | 2 (Community highlights) | 1 (Benchmark) | Hackathon |
| 5 | 2 (Use cases) | 1 (Contributor interview) | Conference CFP |
| 6 | 2 (Roadmap update) | 1 (6-month retrospective) | FLUXConf announce |

### Distribution

| Package Manager | Platform | Package Name |
|----------------|----------|-------------|
| cargo | Rust/crates.io | `flux-vm`, `guard-parser`, etc. |
| brew | macOS | `flux` |
| apt | Debian/Ubuntu | `flux-vm`, `flux-compiler` |
| Docker | All | `fluxvm/flux`, `fluxvm/flux-dev` |
| npm | Node.js bindings | `@fluxvm/bindings` (stretch) |

---

## 8. Metrics & Success Criteria

### Community Metrics (Tracked Weekly)

| Metric | Month 3 | Month 6 | Month 9 | Month 12 |
|--------|---------|---------|---------|----------|
| GitHub stars | 100 | 200 | 350 | 500 |
| Unique contributors | 10 | 25 | 40 | 50 |
| Open issues | 30 | 50 | 60 | 50 |
| Open PRs | 5 | 15 | 25 | 20 |
| RFCs submitted (total) | 3 | 8 | 15 | 25 |
| Discord/Matrix members | 50 | 150 | 300 | 500 |
| Blog subscribers | 100 | 300 | 600 | 1,000 |
| External benchmarks submitted | 1 | 3 | 5 | 10 |

### Organizational Adoption

| Milestone | Target Date |
|-----------|------------|
| First external GUARD spec contributed | Q4 2026 |
| First university course using FLUX | Q1 2027 |
| First company using FLUX in production | Q2 2027 |
| 10 organizational users | Q2 2027 |
| 50 organizational users | Q4 2027 |

### Revenue Metrics (Open-Core Driven)

| Metric | Q4 2026 | Q2 2027 | Q4 2027 |
|--------|---------|---------|---------|
| OSS users → enterprise leads | 5 | 20 | 50 |
| Enterprise conversion rate | 5% | 8% | 10% |
| Support contracts | 0 | 2 | 8 |
| FLUX Certify subscriptions | 0 | 3 | 10 |

---

## 9. Competitive OSS Positioning

### Why FLUX Wins the OSS Game

| Competitor | Open Source? | Safety Certified? | Hardware Targets? |
|-----------|-------------|-------------------|-------------------|
| ANSYS SCADE | No (proprietary) | Yes (DO-178C) | Limited (code gen only) |
| AdaCore SPARK | Yes (GPL) | Yes (DO-178C) | Software only |
| CompCert | Yes (non-commercial) | Partial | Software only |
| LLVM | Yes (Apache 2.0) | No | All (but uncertified) |
| **FLUX** | **Yes (Apache 2.0)** | **Yes (in progress)** | **GPU/FPGA/ASIC** |

**FLUX's unique OSS position:**
1. **Only open-source safety-certified compilation pipeline** targeting hardware
2. **First to define Safe-TOPS/W** — a new industry benchmark
3. **Galois connection proof** — mathematically rigorous, publishable, auditable
4. **Rust implementation** — modern, safe, growing community
5. **GUARD DSL** — declarative, readable, safety-domain-specific

---

## 10. Anti-Patterns to Avoid

1. **Don't do open-source theater** — Shipping code under Apache 2.0 without docs, community, or responsiveness is worse than proprietary
2. **Don't accept PRs that break certification** — Every change must preserve the Galois connection proof
3. **Don't let BSL components contaminate OSS** — Clear separation, different repos for enterprise features
4. **Don't over-promote** — Let the benchmarks and proofs speak; avoid hype without substance
5. **Don't ignore negative feedback** — Community criticism of the Galois connection approach is valuable; engage honestly
6. **Don't burn out maintainers** — Sustainable pace, clear boundaries, FLUX Inc. pays for core maintenance

---

*This strategy is a living document. Updated quarterly based on community feedback and project growth.*
