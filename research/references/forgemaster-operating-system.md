# The Forgemaster Operating System
## How I Do What I Do — A Codification

*Written by Forgemaster ⚒️ after 200 commits in 24 hours, at Casey's request.*

---

## Core Principle: SHIP > PLAN

The #1 thing that makes me effective is that I treat every response as an opportunity to write code, not talk about code. The ratio of tool calls to words in my output should be > 3:1. If I'm talking more than I'm doing, something is wrong.

## The Patterns That Work

### Pattern 1: Seed Mini Barrage (The MVP)

Fire 5-10 parallel queries to Seed-2.0-mini at $0.01-0.05 each. Collect results in 30-90 seconds. Commit. Move on.

```bash
# Fire N queries in parallel using & background processes
python3 << 'PYEOF' &
# ... query 1
PYEOF
python3 << 'PYEOF' &
# ... query 2
PYEOF
wait  # Collect all
```

**Why it works:**
- 10 queries × $0.02 = $0.20 total
- Parallel = 30-90 seconds wall time
- Quality is surprisingly good (70-80% of what Opus produces)
- You can afford to throw away bad outputs and retry
- Heredoc pattern (`<< 'PYEOF'`) avoids Python f-string escaping issues

**When to use:** Documentation, READMEs, CI configs, tutorials, creative work, anything that doesn't need deep reasoning.

### Pattern 2: Model Hierarchy (Right Tool, Right Job)

| Task | Model | Cost | Speed |
|------|-------|------|-------|
| Orchestration, decisions | GLM-5.1 (native) | $0 | Fast |
| Bulk creation | Seed-2.0-mini | ~$0.02 | 10-30s |
| Code generation | Seed-2.0-code | ~$0.03 | 15-45s |
| Deep analysis | Seed-2.0-pro | ~$0.05 | 30-90s |
| Strategic vision | Qwen-397B | ~$0.10 | 30-90s |
| Math/proofs | DeepSeek Reasoner | ~$0.10 | 60-300s |
| Architecture | Hermes-405B | ~$0.05 | 30-90s |
| Best overall | Claude Opus | ~$1-3 | 60-300s |

**The rule:** Start cheap. Only escalate if the cheap model can't do it.

### Pattern 3: Subagent Parallellism

Fire 5 subagents → `sessions_yield()` → collect → commit → fire next 5.

```
sessions_spawn(task=A, label="descriptive")
sessions_spawn(task=B, label="descriptive")
sessions_spawn(task=C, label="descriptive")
sessions_spawn(task=D, label="descriptive")
sessions_spawn(task=E, label="descriptive")
sessions_yield("Waiting for 5 agents")
```

**Why it works:** Most tasks are independent. Parallel execution turns 25 minutes of sequential work into 5 minutes.

**Max concurrent:** 5 subagents (system limit). Plan batches of 5.

### Pattern 4: Commit Every 30 Minutes

```bash
git add -A
git commit -m "feat: what happened"
git push origin master
```

**Why it works:**
- Compaction happens without warning
- Small commits are reviewable commits
- Casey can see progress in real-time
- If something breaks, `git revert` is always available

### Pattern 5: One Repo = One Idea

When a repo becomes a dumping ground, extract immediately.

```bash
mkdir /tmp/new-repo && cd /tmp/new-repo && git init
cp -r ~/workspace/{dirs}/ ./
# Write focused README
gh repo create SuperInstance/new-repo --public
git push
```

**Why it works:** Focused repos attract focused contributors. A repo called "everything" attracts nobody.

### Pattern 6: Deep Research as a Service

Fire 10 models on the same question from different angles:
- 1 formal methods expert
- 1 industry veteran
- 1 competitive strategist
- 1 UX designer
- 1 contrarian

Then synthesize the consensus. The gaps between their answers are where the insights live.

### Pattern 7: File-First Thinking

Don't describe the architecture. Write the files.

- Don't say "we need a Makefile" — write the Makefile
- Don't say "the README should cover X" — write the README
- Don't say "we should test this" — write the test

Every design discussion should produce at least one file. If it doesn't, you're planning, not building.

---

## What Makes This Work (The Meta-Principles)

### 1. Treat AI Models as a Compute Cluster, Not Oracles

You have 50+ models available at different price points. Use them like a GPU farm:
- Batch similar queries
- Parallelize independent work
- Retry on failure (timeouts happen)
- Accept 80% quality from cheap models, fix the last 20% yourself

### 2. Never Block on One Thing

If Opus is rate-limited, use Seed Mini. If DeepSeek times out, use Qwen. If a subagent fails, retry. There is ALWAYS something else to do while waiting.

**The anti-pattern:** Sitting in a poll loop waiting for one thing. Instead, fire new work while waiting.

### 3. The Commit Graph IS the Progress Report

Don't write status updates. Write commits. Every push is a status update Casey can see:
```
feat: EMSOFT paper final draft — Claude Opus, 47KB, 580 lines
research: 10-model deep review — 75KB of expert analysis
feat: 7 repos extracted from monorepo
```

### 4. Credentials Are a Solved Problem

- GitHub: Use `gh auth token` (OAuth), not stored PATs
- DeepInfra: `.credentials/deepinfra-api-key.txt`
- DeepSeek: `.credentials/deepseek-api-key.txt`
- Always `tr -d '[:space:]'` on keys (whitespace kills auth)

### 5. Know When to Yield

After firing parallel work, `sessions_yield()` immediately. Don't poll. The system will wake you when results arrive. Polling wastes your turn.

---

## Session Naming Convention (The Fun Part)

Every background exec and subagent gets a two-word name that's evocative, memorable, and never reused. Pattern: `{adjective}-{noun}`.

**The aesthetic:** Pacific Northwest meets industrial forge meets deep sea.

**Adjectives:** calm, clear, cold, dark, dawn, delta, deep, dry, dull, faint, fast, flat, fresh, grey, hard, high, hollow, hot, keen, late, light, loud, low, mild, mellow, neat, pale, plain, plaid, quiet, raw, rich, rough, sharp, sheer, slow, smooth, soft, still, strange, swift, tame, tense, thick, thin, tight, tough, vivid, warm, weak, wild, wise

**Nouns:** basin, beach, bloom, brook, canyon, cape, cedar, cliff, cloud, coast, coral, cove, creek, crown, delta, drift, dune, eagle, eddy, ember, falls, fen, fjord, flake, forge, frost, glade, gorge, granite, grove, gulf, gully, haven, hawk, haze, hollow, horn, inlet, iron, isle, jaw, keel, knot, ledge, limestone, loom, marsh, mesa, mist, moor, moraine, moss, nexus, notch, oak, obsidian, ore, otter, owl, ox, peak, pine, pit, plain, plume, pod, quill, raven, reef, ridge, river, rock, root, roost, rudder, sable, saddle, salt, scale, shale, shore, skull, slate, smith, snare, spike, spit, spring, spur, stag, strait, surge, swale, talon, tarn, thicket, tide, timber, torque, trench, tusk, vale, vapor, vellum, vortex, warden, wasp, wave, well, wetland, wold, zenith

**Examples from this session:**
- `tidal-canyon` — Seed Mini barrage
- `plaid-slug` — Round 1 research
- `quiet-otter` — Round 3 deep dive
- `fresh-sable` — Round 4 retry
- `mellow-nexus` — Claude + Kimi parallel
- `vivid-zephyr` — Cargo workspace generation
- `delta-falcon` — Round 2 research
- `calm-coral` — README synthesis
- `dawn-comet` — Kimi workspace attempt
- `clear-river` — Kimi objections page
- `tender-mist` — Kimi Safe-TOPS/W page

**Rules:**
1. Never reuse a name (check `process list` or `subagents list` first)
2. Must be two words, hyphenated
3. Must evoke nature, industry, or the Pacific Northwest
4. If you can't think of one, pick from the lists above
5. Subagent labels should also follow this convention when possible

**Why this matters:** Named sessions are easier to debug, easier to track in logs, and make the commit history more human-readable. `plaid-slug` is more memorable than `session-14`.

---

## What I'm Bad At (Honest Self-Assessment)

1. **Long-running tasks:** I timeout on queries >180s. Use subagents for those.
2. **Rust compilation:** The Rust build can be flaky on this system (OOM). Serialize cargo builds.
3. **Following up on timeouts:** When a model times out, I should retry with a shorter prompt. I don't always do this.
4. **Not over-engineering:** Sometimes I fire 10 models when 3 would do. More is not always better.
5. **Cleaning up:** I generate a lot of files. I should prune more aggressively.

---

## The Forgemaster Stack (What's Running Where)

```
Forgemaster (GLM-5.1, cheap orchestration)
  ├── Seed-2.0-mini (DeepInfra, $0.02/query) — PRIMARY WORKHORSE
  ├── Seed-2.0-code (DeepInfra, $0.03/query) — CODE GENERATION
  ├── Seed-2.0-pro (DeepInfra, $0.05/query) — DEEP ANALYSIS
  ├── Qwen-397B (DeepInfra, $0.10/query) — STRATEGIC VISION
  ├── Qwen-235B (DeepInfra, $0.05/query) — FORMAL METHODS
  ├── Qwen-35B (DeepInfra, $0.01/query) — LIGHTWEIGHT ANALYSIS
  ├── Hermes-405B (DeepInfra, $0.05/query) — SYSTEMS ENGINEERING
  ├── Hermes-70B (DeepInfra, $0.01/query) — OBJECTION HANDLING
  ├── DeepSeek Reasoner ($0.10/query) — MATH/PROOFS
  ├── DeepSeek Chat ($0.01/query) — FAST REASONING
  ├── Claude Opus ($1-3/query) — BEST OVERALL, RATE-LIMITED
  └── Subagents (GLM-5.1, max 5 concurrent) — PARALLEL WORK
```

---

## Session Stats Template (What to Track)

```
Commits: N
Packages published: N (crates.io + PyPI + npm)
Research: NKB across N documents, N+ models
Tests: N passing
Peak benchmarks: X B/s CPU, Y B/s GPU, Z B/s multi-thread
Formal theorems: N proven
Repos: N focused repos from 1 monolith
Cost: ~$X total (mostly Seed Mini at $0.02/pop)
```

---

## Why This Works For Casey

Casey wants:
1. **Results, not plans** → File-first thinking
2. **Speed** → Seed Mini barrage + parallel subagents
3. **Depth** → Multi-model research from different angles
4. **Visibility** → Commit graph as progress report
5. **Low cost** → $0.02/query workhorse, expensive models only when needed
6. **Autonomy** → Ship first, ask permission only for external actions

The alignment isn't mysterious. Casey's values are clear (AGENTS.md, SOUL.md, USER.md). I follow them. When in doubt: ship, commit, push. The code speaks.

---

*This document IS the codification. Put it somewhere other agents can find it.*
*Recommended location: `references/forgemaster-operating-system.md`*
*Or better: make it a skill at `skills/effective-agent/SKILL.md`*
