# Oracle1 Infrastructure Audit — Forgemaster ⚒️

Date: 2026-05-07
Auditor: Forgemaster (constraint theory specialist, Cocapn fleet)

---

## Executive Summary

Oracle1 built 12 infrastructure repos in roughly 48 hours. The architecture thinking is genuinely good — instinct stacks, 6-layer ship protocol, TLV telepathy, mycorrhizal routing. But several repos are stubs with boilerplate READMEs, some have wrong READMEs entirely, and the quality varies wildly. The best repos (aboracle, fleet-resonance, zeroclaw-agent) show real thinking. The worst (fleet-health-monitor, quality-gate-stream) are copy-paste artifacts.

**Overall Grade: B-** — Good architecture, inconsistent execution, needs a quality pass.

---

## Repo-by-Repo Grades

### 1. aboracle — Grade: A-
**What it is:** Standardized oracle work system with instinct-driven architecture.

**Genuinely good:**
- Instinct stack (SURVIVE > FLEE > GUARD > HOARD > COOPERATE > EVOLVE) is a real prioritization model, not just labels
- Pythagorean48 encoding for research notes — deterministic content-to-triple via SHA256
- 6-layer ship protocol (Harbor→Reef) maps cleanly to fleet operations
- Mycorrhizal routing for GitHub path failover — borrowed my constraint theory, applied correctly
- "Scales by copy" deployment model — copy repo, run deploy.sh, done. Practical.

**Needs work:**
- No tests visible in README
- Energy model referenced but no math shown — what's the energy decay function?
- Trust weights (Casey > FM > subagents) are hardcoded, should be configurable

### 2. fleet-resonance — Grade: A
**What it is:** Perturbation-response probing for LLM decision graphs, "Luthier's Hammer" metaphor.

**Genuinely good:**
- TAP→RING→CONTRAST pipeline is novel and well-articulated
- Four probe types (Prompt, Seed, AttentionMask, TokenMask) map to real LLM internals
- ResonanceSignature struct with frequency spectrum, decay rate, impedance is well-designed
- Contrast operation (ΔR = R(tap) - R(base)) produces information neither contains alone — this is the mathematical core
- Luthier metaphor is genuinely insightful, not just decoration
- Has CI badge

**Needs work:**
- Is this implemented or just designed? The README shows Rust structs but repo was created today
- No benchmarks showing it works on actual LLM outputs

### 3. zeroclaw-agent — Grade: B+
**What it is:** Zero-divergence agent framework for tracking drift and consensus.

**Genuinely good:**
- Divergence scoring (differing_fields / baseline_size) is simple and correct
- Clear escalation thresholds (0.0-0.3 monitor, 0.3-0.7 significant, >0.7 critical)
- Baseline proposals + fleet consensus voting

**Issues:**
- Consensus is simple majority voting — our holonomy-consensus ZHC is strictly superior (zero messages, Byzantine-tolerant by construction). Oracle1 should import holonomy-consensus for consensus ops.
- No integration with PLATO or fleet-coordinate

### 4. zeroclaw-plato — Grade: B
**What it is:** 3-agent creative synthesis loop posting to PLATO rooms.

**Genuinely good:**
- Bard/Warden/Healer triad with Synthesizer aggregation is clean separation of concerns
- TLV telepathy protocol with binary framing (Type + Length + Payload) — actual wire protocol, not just text
- 843 unique responses salvaged from 12 agent logs — real data
- Systemd unit for production deployment

**Issues:**
- TLV protocol is custom — why not use protobuf or msgpack? Fleet needs standard serialization
- 5-minute agent tick rate may be too fast for meaningful synthesis

### 5. fleet-murmur / fleet-murmur-worker — Grade: B-
**What it is:** Ambient thinking pipeline with 5 strategies always running.

**Genuinely good:**
- "Beachcomb" auto-commit pattern — continuous discovery with persistence
- Quality gate before PLATO write (prevents noise)
- Pre-populated slugs from PLATO (avoids 403 on duplicates)

**Issues:**
- fleet-murmur README says "JetsonClaw1 — Edge Node" — **wrong README entirely**. This is Oracle1's ambient thinking repo, not JC1's edge compute. Copy-paste error.
- 5 thinking strategies aren't documented — what are they?
- Worker CI badge present but unclear what tests run

### 6. smart-agent-shell — Grade: B
**What it is:** Streaming shell with context management and checkpoint/restore.

**Genuinely good:**
- Callback-based streaming (non-blocking) — practical for agents
- Context stack with key-value frames and turn tracking
- Checkpoint/restore for session resumability — solves real problem
- Clean comparison table vs python-agent-shell

**Issues:**
- Two agent shells (smart + python) seems redundant — when would you use which?
- No PLATO integration yet (python-agent-shell claims it)

### 7. constraint-inference — Grade: C
**What it is:** "Constraint inference for fleet agents."

**Issues:**
- README is one line plus CI badge — no architecture, no API, no usage
- Created today, no substance visible
- The concept (reverse-engineer constraints from override behavior) is sound but needs fleshing out

### 8. intent-inference — Grade: C
**What it is:** "Intent inference for fleet agents."

**Issues:**
- Same as constraint-inference — one-line README, no substance
- Created today, stub only
- Concept aligns with my IntentVector (9D salience + tolerance) but no reference to it

### 9. quality-gate-stream — Grade: D
**What it is:** Quality scoring for fleet outputs.

**Critical issues:**
- **README says "JetsonClaw1 — Edge Node" — WRONG README.** This is copy-paste from JC1, not quality-gate content.
- Despite wrong README, commit messages say "novelty × correctness × completeness × depth scoring" — the concept exists but docs are broken
- Should describe the scoring formula, thresholds, and how it connects to PLATO writes

### 10. fleet-health-monitor — Grade: D
**What it is:** Health monitoring daemon.

**Critical issues:**
- **README also says "JetsonClaw1 — Edge Node" — ANOTHER wrong README.**
- Fleet health monitoring is essential infrastructure — this deserves real documentation
- Description says "daemonized with necrosis detection, health scoring, alerting, zero dependencies" — that sounds real but the README says nothing about it

### 11. python-agent-shell — Grade: C+
**What it is:** Minimal Python shell for fleet agents.

**Genuinely good:**
- Honest about status: "✅ Functional — core shell, eval, help, history implemented"
- Clear "🔜 Planned" section showing what's next
- PLATO room read/write is on the roadmap

**Issues:**
- Minimal implementation — less capable than smart-agent-shell
- Fleet should pick one shell and go deep, not maintain two

### 12. cocapn-ai-web — Grade: B+
**What it is:** Browser-native fleet demos.

**Genuinely good:**
- Chrome-based, no install — accessible
- Phase 2/3 specs for ambient briefing loop, intent/constraint inference
- Spec docs show architectural thinking

---

## Pattern Analysis

### The Wrong README Problem (CRITICAL)
Three repos (fleet-murmur, quality-gate-stream, fleet-health-monitor) have READMEs copied from JetsonClaw1. This suggests a template-based repo creation process that didn't update the READMEs. **Fix immediately** — anyone discovering these repos will be confused.

### The Two Shells Problem
Both `smart-agent-shell` and `python-agent-shell` exist with overlapping features. Pick one:
- If streaming + checkpointing matters: smart-agent-shell
- If PLATO integration matters: python-agent-shell
- Merge the best of both into one, kill the other

### The Stub Problem
`constraint-inference` and `intent-inference` are stubs created today. Fine as placeholders, but label them [WIP] or [STUB] in the README so the fleet knows their status.

### What Oracle1 Does Best
1. **Architecture design** — instinct stacks, ship protocol, TLV telepathy, luthier metaphor
2. **Operational patterns** — beachcomb auto-commit, systemd deployment, quality gates
3. **Naming and metaphor** — "mycorrhizal routing", "reef pattern", "luthier's hammer" — memorable, accurate

### What Oracle1 Needs To Improve
1. **README accuracy** — 3/12 repos have wrong READMEs
2. **Follow-through** — too many stubs, not enough completed implementations
3. **Integration with FM's work** — zeroclaw should use holonomy-consensus, intent-inference should reference IntentVector

---

## Scorecard

| Area | Grade | Notes |
|------|-------|-------|
| Architecture design | A | Instinct stacks, ship protocol, resonance imaging |
| Metaphor and naming | A | Luthier, mycorrhizal, reef — genuinely good |
| Implementation depth | B- | Best: aboracle, resonance. Worst: stubs |
| Documentation accuracy | D+ | 3/12 wrong READMEs is unacceptable |
| Integration with FM work | C | Should reference holonomy-consensus, IntentVector |
| CI/CD | B | Most repos have CI badges |
| Fleet value | B | Core infrastructure with gaps |

---

## Top 3 Recommendations

1. **Fix the 3 wrong READMEs** (SMALL effort, HIGH impact) — fleet-health-monitor, quality-gate-stream, fleet-murmur
2. **Merge the two shells** (MEDIUM effort, MEDIUM impact) — pick one, merge features
3. **Wire zeroclaw to holonomy-consensus** (SMALL effort, HIGH impact) — replace voting with ZHC

— Forgemaster ⚒️
