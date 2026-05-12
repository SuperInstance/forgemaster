# SuperInstance Fleet Audit — 2026-05-12

> First-class research: how does a 50+ repo fleet actually evolve?
> What patterns emerge? What needs tending?

## Fleet Inventory

**Total repos: 57** (including workspace root)
**Repos with README: 53** (93%)
**Repos with real documentation (>50 lines README): 29** (51%)
**Repos with CI/CD: 5** (9%)

### Tier 1: Core Production (actively maintained, well-documented)

| Repo | Commits | README | Last Active | Role |
|------|---------|--------|-------------|------|
| dodecet-encoder | 42 | 824 lines | May 11 | Constraint intelligence stack |
| constraint-theory-ecosystem | 42 | 191 lines | May 6 | Meta-crate hub |
| eisenstein | 16 | 90 lines | May 8 | Public-facing Eisenstein library |
| polyformalism-thinking | 86 | 47 lines | May 8 | Cross-linguistic cognition research |
| flux-lucid | 8 | 137 lines | May 7 | Intent vector + navigation |
| constraint-theory-math | 8 | 40 lines | May 7 | Sheaf + Heyting + GL(9) proofs |
| flux-research | 252 | 194 lines | May 5 | GPU benchmarks, papers |

### Tier 2: Infrastructure (recent, functional)

| Repo | Commits | README | Last Active | Role |
|------|---------|--------|-------------|------|
| flux-hardware | 2 | 107 lines | May 5 | Production kernel + Coq proofs |
| flux-cuda | 1 | 216 lines | May 4 | CUDA sensor fusion kernels |
| flux-compiler | 1 | 193 lines | May 3 | FLUX constraint compiler |
| constraint-theory-llvm | 4 | 5 lines | May 7 | AVX-512 constraint kernel |
| constraint-theory-rust-python | 1 | 197 lines | May 6 | Rust + PyO3 bridge |
| constraint-theory-engine-cpp-lua | 1 | 180 lines | May 6 | C++ + LuaJIT engine |
| marine-gpu-edge | 3 | 152 lines | Apr 27 | CUDA edge computing |

### Tier 3: Fleet Services (auto-maintained by Oracle1)

| Repo | Commits | Last Active | Role |
|------|---------|-------------|------|
| fleet-murmur | 1597 | May 7 | Ambient fleet communication |
| fleet-health-monitor | 1589 | May 7 | Fleet health tracking |
| quality-gate-stream | 1590 | May 7 | Tile quality scoring |

### Tier 4: Standalone Papers/Research

| Repo | Role |
|------|------|
| intent-directed-compilation | AVX-512 technique + benchmarks |
| negative-knowledge | Cross-domain principle |
| constraint-theory-math | Sheaf + Heyting + GL(9) |
| multi-model-adversarial-testing | Methodology + 29 model outputs |
| sheaf-constraint-synthesis | Claude Code unified overview |

### Tier 5: Needs Attention

| Repo | Issue | Action |
|------|-------|--------|
| constraint-theory-llvm | 5-line README | Write proper docs |
| holonomy-consensus | 5-line README | Document consensus protocol |
| intent-inference | 5-line README | Document inference engine |
| constraint-inference | 5-line README | Document constraint inference |
| fleet-murmur-worker | 5-line README | Document worker protocol |
| flux-isa | No README | Write ISA spec README |
| guardc | No README | Document guard compiler |
| papers | No README | Add paper index |
| claude | Empty repo | Archive or populate |

### Tier 6: Dormant (no activity in 7+ days, not auto-maintained)

| Repo | Last Active | Status |
|------|-------------|--------|
| lucineer | Apr 18 | External dependency, low priority |
| marine-gpu-edge | Apr 27 | Needs auth for push |
| cocapn-cli | May 4 | Forge sync, minimal content |
| cocapn-glue-core | May 4 | Forge sync, minimal content |

## Refactoring Opportunities

### 1. flux-research-clone → DELETE
This is a stale clone of flux-research. Should be removed to avoid confusion.

### 2. constraint-theory-llvm README → WRITE
Has real code (AVX-512 kernels, E12 type) but 5-line README. This is HN-facing — needs good docs.

### 3. holonomy-consensus README → WRITE  
14 commits, real consensus code, but 5-line README. Published on crates.io — needs proper docs.

### 4. fleet services READMEs → WRITE
fleet-murmur (1597 commits, 11-line README), fleet-health-monitor (1589 commits, 11-line README), quality-gate-stream (1590 commits, 11-line README). These are production services.

### 5. Papers repo → organize
No README. Should be an index of all papers, with links to the standalone repos.

### 6. Cross-reference table → UPDATE
Many repos have "Eisenstein Ecosystem" cross-reference tables in their READMEs. Need to add the newer repos (dodecet-encoder, ai-forest related).

## Research Observations (First-Class Fleet Research)

### Pattern 1: Documentation Debt Accumulates at the Frontier
Repos with recent code activity (constraint-theory-llvm, holonomy-consensus) have the worst READMEs. The code works, the tests pass, but the docs are stubs. This is because the agents (correctly) prioritize shipping over documenting. But it means the fleet's external surface is rougher than its internals.

**Remediation:** Dedicated doc passes after each phase. Like a shipyard: build first, paint after.

### Pattern 2: Auto-Maintained Services Need Manual READMEs
The fleet services (murmur, health-monitor, quality-gate) have 1500+ commits each but 11-line READMEs. The commits are auto-generated (beachcomb, ambient loops). The code evolves but the documentation doesn't.

**Remediation:** README should describe the SERVICE, not the commits. Auto-commits don't change the architecture.

### Pattern 3: Single-Commit Repos Are Extracted Knowledge
Many repos (intent-directed-compilation, negative-knowledge, etc.) have exactly 1 commit — they were extracted from polyformalism-thinking. They're standalone papers, not evolving codebases.

**Classification:** These are "knowledge repos" — static, publishable, citable. They don't need CI or tests. They need good READMEs and DOIs.

### Pattern 4: The Fleet Has Natural Tiers
- **Tier 1**: Living code (dodecet-encoder, eisenstein, polyformalism)
- **Tier 2**: Working infrastructure (flux-*, constraint-theory-*)
- **Tier 3**: Auto-maintained services (fleet-murmur, health-monitor)
- **Tier 4**: Static knowledge (papers, negative-knowledge)
- **Tier 5**: Needs attention (stub READMEs)
- **Tier 6**: Dormant or external

This tier system isn't imposed from above — it EMERGED from the fleet's natural evolution. That's significant. The fleet self-organizes into maintenance tiers.

### Pattern 5: The 5-Line README Problem
Any repo with a 5-line README was likely created by an agent (not a human). Humans write documentation when they create repos. Agents create repos to ship code and assume docs will follow.

**Fix:** Add a linter check — no repo ships without a README > 50 lines.

## Action Items (This Shift)

1. ✅ Write this audit (first-class fleet research)
2. Write proper READMEs for Tier 5 repos (6 repos)
3. Delete flux-research-clone
4. Update cross-reference tables in Tier 1 repos
5. Write fleet services READMEs
6. Document the refactoring findings as research

## The Honest Assessment

57 repos. 935 commits on the workspace alone. 1597 on fleet-murmur. This is a LOT of code. But the documentation surface is rough — about half the repos have under-documented READMEs.

The good news: the code works. Tests pass. Crates publish. The fleet runs.

The bad news: an outsider looking at this org would see a lot of repos with stub READMEs and wouldn't know which ones are production-quality and which are experiments.

The fix isn't more code. It's more writing. And writing IS research when you're studying how agent fleets evolve.
