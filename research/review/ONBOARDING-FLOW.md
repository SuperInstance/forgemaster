# Onboarding Flow Audit

**Audited:** 2026-05-17 | **Auditor:** Forgemaster ⚒️

---

## 1. CURRENT STATE

### What a developer sees at github.com/SuperInstance

**The org profile.** A GitHub organization with 80+ repos. The org-level README/profile is the workspace README, which is... the Forgemaster workspace README. It's written for *Casey and the fleet*, not for newcomers. It leads with "Monorepo for the Forgemaster constraint-theory fleet agent" — insider language that means nothing to someone who just read a tweet about spectral conservation.

**No "start here" repo.** There is no `.github` profile repo, no `superinstance.github.io`, no `getting-started` repo. A newcomer lands on a wall of 80+ repos with no guidance.

**Published packages exist but are buried.** 6 packages on crates.io, 4 on PyPI, 1 on npm — but you'd never know it from the org page. The workspace README lists some crates but mixes them with fleet-internal stuff (plato-matrix-bridge, fleet-murmur) that's irrelevant to newcomers.

**Internal docs exist but aren't public-facing.** ASSEMBLY-GUIDE.md and ECOSYSTEM-MAP.md are excellent onboarding documents — for someone already inside. They live in the Forgemaster workspace, not in any public repo.

### Specific problems

| Problem | Impact |
|---------|--------|
| No org-level profile README | Newcomer sees raw repo list, no narrative |
| Workspace README is fleet-internal | "Forgemaster ⚒️ fleet agent" means nothing to outsiders |
| 80+ repos with no taxonomy | Can't tell what's core vs. research vs. infra |
| No GETTING-STARTED.md anywhere | No 5-minute path from discovery to running code |
| Published packages unlinked from org page | `pip install constraint-theory` works but nobody knows to try it |
| Assembly patterns are internal-only | Great quick-start code exists but isn't public |
| No "choose your adventure" paths | Math people, ML people, and embedded people all see the same wall |

### What IS good

- **6 published packages** with real `cargo add` / `pip install` commands
- **ASSEMBLY-GUIDE.md** has perfect quick-start patterns (Pattern 1: 4 lines, Pattern 2: 8 lines)
- **ECOSYSTEM-MAP.md** has clear dependency graph and "assembly recipes"
- **655+ tests** — the code works, it's just not accessible
- **Every component is independently installable** — the architecture is already modular

---

## 2. IDEAL FLOW

The 5-minute path from tweet to running code:

```
Tweet: "spectral conservation in neural networks"
  ↓
github.com/SuperInstance
  ↓ (org README with 3-path choice)
  ├─ "Just want the math" → cargo add eisenstein → 5-line example
  ├─ "Want intelligent rooms" → pip install plato-escalation-gate → 8-line example
  └─ "Want the full ecosystem" → clone superinstance/plato-training → 15-line example
  ↓
Running code in < 2 minutes
  ↓
"Next steps" link to deeper docs
```

**Timeline:**
- 0:00 — Land on org page, read 3-sentence pitch
- 0:30 — Choose a path, see install command
- 1:00 — Run install command
- 1:30 — Copy-paste working example
- 2:00 — See output, understand what happened
- 5:00 — Read "how it works", explore related packages

---

## 3. MISSING PIECES

### Critical (blocks onboarding entirely)

1. **Org profile README** — A `.github` repo with a public-facing README
2. **GETTING-STARTED.md** — The 5-minute path document (created below)
3. **Repo descriptions** — Every repo needs a 1-line GitHub description

### Important (blocks understanding)

4. **Assembly guide in a public repo** — ASSEMBLY-GUIDE.md is perfect but internal-only
5. **"Start here" badge/link** — Pin a repo or add to org profile
6. **Package landing pages** — Links from org page to crates.io/PyPI

### Nice to have

7. **Interactive demos** — A `constraint-demos` web playground
8. **Architecture diagram** — One image that shows the stack
9. **Discord/Discussions link** — Community entry point

---

## 4. RECOMMENDED FIXES

### Fix 1: Create org profile repo (CRITICAL)

**Create:** `SuperInstance/.github` repo with `README.md`

Content: The public-facing version of what we do. 20 lines max. Three paths. Link to GETTING-STARTED.

### Fix 2: Publish GETTING-STARTED.md (CRITICAL)

**Create:** `SuperInstance/.github/GETTING-STARTED.md` or `SuperInstance/getting-started` repo

Use the document created at `/home/phoenix/.openclaw/workspace/GETTING-STARTED.md` (below).

### Fix 3: Pin repos on org page (IMPORTANT)

Pin these repos on github.com/SuperInstance:
1. `constraint-theory-core` — "Start here for the math"
2. `plato-model-ocean` — "Start here for intelligent rooms"
3. `flux-lucid` — "Start here for the full ecosystem"

### Fix 4: Add repo descriptions (IMPORTANT)

Every repo needs a GitHub description. Top priority:

| Repo | Suggested description |
|------|-----------------------|
| eisenstein | Zero-drift Eisenstein integer arithmetic — no_std, runs on anything |
| spectral-conservation | Spectral conservation monitor for neural networks |
| constraint-theory-core | Formally verified constraint satisfaction (278M+ test cases) |
| plato-model-ocean | Cellular intelligence ecosystem — evolving models that know when to ask for help |
| plato-escalation-gate | 737-parameter gate that decides when to call an LLM (4KB, runs anywhere) |
| plato-room-intelligence | Multi-head room model with provenance tracking |
| tensor-spline | SplineLinear: 20× compression at same accuracy |
| flux-lucid | Unified constraint theory: CDCL, LLVM, AVX-512, GL(9) consensus |
| dodecet-encoder | Eisenstein snap→dodecet perception and temporal intelligence |

### Fix 5: Add quick-start to each published package's README

Every published package repo needs:
- One-sentence "what this does"
- `pip install` / `cargo add` command
- 10-line working example
- Link to GETTING-STARTED.md

### Fix 6: Make ASSEMBLY-GUIDE.md public

Move or copy `ASSEMBLY-GUIDE.md` to `SuperInstance/.github/ASSEMBLY-GUIDE.md` or a dedicated `docs` repo.

### Priority Order

1. Create `.github` profile repo with org README → **immediate visibility fix**
2. Create GETTING-STARTED.md → **5-minute path fix**
3. Pin repos → **navigation fix**
4. Add repo descriptions → **discoverability fix**
5. Package-level quick-starts → **depth fix**
6. Public assembly guide → **architecture understanding fix**
