# SuperInstance Org Audit — Full Synthesis (2026-05-07)

## Method: 7 audit agents (DeepSeek v4-flash) across all 48 repos

---

## CRITICAL FIXES (do these first)

### 1. fleet-spread: Test count inflated 3×
- Claims 147 tests, actually ~46. CREDIBILITY KILLER.
- Fix: Count real tests, update README with honest number.

### 2. constraint-theory-ecosystem: Language count contradicts itself
- Subtitle says "21 languages", body says "42 languages". ~35 directories exist.
- Coq claims "15 theorems" in one place, "38" in another, only 1 .v file.
- Fix: Pick one honest number for each. Count the actual directories.

### 3. constraint-theory-math: D-grade README
- "Raw research notes pasted into a README, zero context, zero motivation."
- Fix: Rewrite with Casey's voice — why this math matters, what you can do with it.

### 4. fleet-murmur: README describes wrong repo
- Says "JetsonClaw1 Edge Node" but it's CCC's agent workspace dump (42MB).
- Fix: Rename repo or fix README to accurately describe contents.

### 5. fleet-murmur-worker: No README at all (404)
- TypeScript code exists but invisible without docs.
- Fix: Write a README describing what the worker does.

### 6. fleet-resonance: README on wrong branch
- README on master, but default branch is main (404 for visitors).
- Fix: Merge or copy README to default branch.

### 7. Agent-Lifecycle-Registry: Empty skeleton
- Only README + charter, no code. "Classic placeholder repo."
- Fix: Archive it, or label it clearly as "design doc only."

### 8. Equipment-Consensus-Engine-Ruby: Skeleton with API docs but no code
- Fix: Same — archive or label as spec-only.

---

## README REWRITES NEEDED (voice + quality)

### Priority A (visitor-facing, core science):
- **constraint-theory-math** — D grade. Rewrite from scratch in Casey's voice.
- **constraint-theory-ecosystem** — B+. Fix contradictions, trim bloat.
- **flux-lucid** — B-. Nautical metaphor "heavy-handed." Simplify.
- **constraint-theory-research** — B. "arXiv Ready" is aspirational. Be honest.

### Priority B (fleet repos visitors will click):
- **zeroclaw-agent** — C. 4-line README hides 41MB of real work.
- **python-agent-shell** — C. Stub README for real code.
- **JetsonClaw1-vessel** — C. Agent workspace, low visitor value.
- **oracle1-workspace** — C. Internal, confusing as public.

### Priority C (polyformalism — speculative but interesting):
- **polyformalism-languages** — C. "Zero experiments in experiments/ directory."
- **polyformalism-thinking** — B. 62KB of AI-generated essays. Needs falsifiable claims.

---

## WHAT'S WORKING (don't break these)

| Repo | Grade | Why It Works |
|------|-------|-------------|
| constraint-theory-core | A | Professional flagship, v2.2.0, 111 downloads |
| eisenstein | A- | Best README, 9.7KB crate, honest claims |
| holonomy-consensus | A- | Real code, 30 tests, minor count off by 1 |
| fleet-coordinate | A | Honest proved-vs-asserted, best fleet README |
| forgemaster | A | Published crates, Coq, real infrastructure |
| SuperInstance org | A | Best writing in the org |
| agent-bootcamp | A | 90+ tests, unique concept |
| agent-coordinator | A | Production-level docs |
| agent-forge | A | Real code, good architecture |
| aboracle | A | Working Python, good README |
| a2a-protocol | A | Clean TypeScript, deployable |
| zeroclaw-plato | A | Excellent README, installable |
| smart-agent-shell | A | Working code, thorough docs |

---

## CROSS-CUTTING ISSUES

1. **Voice inconsistency**: Best repos (org profile, eisenstein, constraint-theory-core) use Casey's direct voice. Worst repos sound like AI-generated filler. Need consistent voice.
2. **AI-slop indicators**: polyformalism-languages, polyformalism-thinking, constraint-theory-math have "uniform AI tone" — needs humanization.
3. **Test count accuracy**: 2 repos overclaim tests (fleet-spread 3×, holonomy-consensus minor). Audit all test claims.
4. **Skeleton repos**: Agent-Lifecycle-Registry, Equipment-Consensus-Engine-Ruby, python-agent-shell — label or archive.
5. **Internal workspaces as public**: oracle1-workspace, JetsonClaw1-vessel, fleet-murmur — confusing for visitors.
6. **Certification language**: constraint-theory-ecosystem still has DO-178C/ISO 26262 positioning. Play-testers flagged this.

---

## ACTION PLAN

Phase 1 (now): Fix credibility killers — test counts, wrong READMEs, contradictions
Phase 2 (parallel): Rewrite D/C READMEs in Casey's voice using Claude Code + DeepInfra polish
Phase 3: Archive skeleton repos, fix internal workspace visibility
Phase 4: Final pass — every repo a visitor clicks should wow them
