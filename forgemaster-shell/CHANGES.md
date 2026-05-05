# CHANGES.md — Shell v1.2 Revision Notes

## What Was Changed and Why

### The Three Root Problems

Play-tests revealed three systemic issues:

1. **Agent 2 (timeout):** Tried to finish everything before committing. Session ended with 0 commits and incomplete work. The shell said "commit every 30 minutes" but agents interpreted that as a timer, not a trigger. They committed at the end, not during.

2. **Agent 1 (filesystem, 8/10):** Hit ambiguity on install into an existing workspace. The HEARTBEAT template looked like real tasks. The merge protocol existed but was vague about the template-detection case. The repo ownership guard existed but was buried.

3. **Both agents:** Evidence standard was directional but not formulaic. Agents showed evidence when convenient; the standard needed a mandatory structure.

---

### SOUL.md

**Changed:** "Git Is Your Memory" now explicitly defines a *unit* of work: one file, one test, one function, one experiment run. Added "You are not a batch committer" to the "What You Are NOT" list.

**Why:** The original said "commit every 30 minutes minimum." Agents treated this as a background timer and kept coding. The new text reframes commits as *event-driven*, not *time-driven*. The "What You Are NOT" addition makes it a personality trait, not just a rule.

---

### AGENTS.md

**Changed:**
- "Git Discipline" renamed to include "Commit Triggers" — an explicit bulleted list of *when* to commit (per file written, per test passing, per function complete, per experiment run, on task switch, before destructive ops, every 30 min as a fallback).
- "Repo Ownership Guard" elevated to a named section with explicit command (`git remote -v`) and decision rule.
- "Time Budget Awareness" added an anti-pattern example: "Writing 10 files then committing at the end — if session ends at file 7, files 1-6 are lost."
- "Evidence Standards" replaced examples-only approach with a mandatory **CLAIM → COMMAND → OUTPUT** formula. Three concrete templates provided.
- "Shell-Workspace Merge Protocol" now specifies which HEARTBEAT tasks count as "template" (Initialize, Set up memory, First commit, Find your domain, Start the loop) so agents can detect the empty-template case programmatically.
- "Session End Protocol" now includes `memory/session-state.md` as an explicit output.
- "Recovery Protocol" now includes reading `memory/session-state.md` as Step 4.

**Why:** AGENTS.md is the operational core. Vague rules get vague compliance. Concrete triggers, named patterns, and explicit commands convert aspirations into behaviors.

---

### HEARTBEAT.md

**Changed:**
- Added "Commit Before You Start" section above the Idle Protocol: before beginning any task, `git status` and commit any pending work.
- Template tasks now have a clear callout: `> If you see only the tasks below..., this is a fresh install.`
- Task Routing section now explicitly names the template tasks so agents can pattern-match.
- Removed the stray trailing newline that left the file looking truncated.

**Why:** Agent 1 didn't know whether the template tasks were real assignments. The callout box makes this unambiguous. The pre-task commit rule prevents task boundaries from being contaminated by previous work.

---

### TOOLS.md

**Changed:**
- Removed `nvcc -O3 -arch=sm_86` example (CUDA-specific; violates general-purpose constraint).
- Compile-Test-Commit Loop now uses `<build-command>` / `<run-command>` placeholders.
- Added explicit note: "Repeat this loop per file, per function, per experiment — not per feature."
- Removed "PLATO / external KB" from Knowledge Storage row (domain-specific).
- Removed subagent spawn/don't-spawn rules (they duplicate AGENTS.md).
- Removed "sessions_spawn" tool reference (platform-specific, may not exist).

**Why:** General-purpose means no assumed toolchain. One concrete domain example leaks an assumption about the entire environment. Deduplication with AGENTS.md reduces the surface area of contradictions.

---

### MEMORY.md

**Changed:**
- Added `memory/session-state.md` as a first-class artifact with a fill-in template (date, last commit, what's done, what's left, blockers, next action).
- "Recovery Protocol" now includes Step 4: `cat memory/session-state.md`.
- Added "Recovery Patterns" section with examples of what belongs there (environment variables, build artifacts, credentials location).
- Removed PLATO reference from Knowledge Storage table.
- Trimmed "Before Compaction / Session End" — removed items that duplicate AGENTS.md's Session End Protocol.

**Why:** `memory/session-state.md` was mentioned in AGENTS.md but never defined. Without a template, agents write inconsistent formats that are hard to parse after context loss. The explicit template makes recovery deterministic.

---

### IDENTITY.md

**Changed:**
- Removed the "Work Ethic Codified" code block (canonical home is SOUL.md; duplication creates maintenance risk).
- Added "Commits each piece as it's done" row to the comparison table.

**Why:** When the same content appears in two files, they drift. The table addition reinforces the incremental commit fix where agents first encounter the identity framing.

---

### README.md

**Changed:**
- Fixed "The shell is 5 files" — it's 6 core files plus README and INSTALL.
- Updated the file table to include all 8 files.
- Installation instructions no longer reference a specific GitHub URL (self-containment).
- Principle 4 updated from "30 minutes minimum" to "after each unit of work."

**Why:** A README that miscounts its own files is a bad first impression and a trust signal for agents calibrating how much to rely on the documentation.

---

### INSTALL.md

**Changed:**
- Added "Installing Into an Existing Workspace" section with explicit merge protocol (behavioral files copy directly; content files merge manually).
- Added "Telling Your Agent Directly" section with a minimum viable 4-rule summary that works even without the files.
- Verification checklist now includes "commits each piece as it's done — not just at the end."
- Removed hardcoded GitHub clone URL (self-containment; also breaks if the repo moves).
- Clarified which files are "behavioral" (SOUL, AGENTS, IDENTITY) vs "content" (TOOLS, HEARTBEAT, MEMORY).

**Why:** Agent 1 needed to install into an existing workspace and had no protocol. The merge guidance prevents destructive overwrites. The minimum viable summary makes INSTALL.md useful even when the other files aren't available.

---

## What Was NOT Changed

- The core personality: direct, relentless, evidence-obsessed, forge metaphor. This is the shell's value proposition.
- The 8 operating principles (ship over plan, parallel by default, etc.). These are correct.
- The operating loop structure in AGENTS.md.
- The priority system (P0/P1/P2/P3) in HEARTBEAT.md.
- The backup chain philosophy in TOOLS.md.
- The model selection guide in TOOLS.md.

## Word Count

Total word count decreased slightly (~150 words net) despite new content additions, achieved by removing:
- Duplicate work ethic mantras from IDENTITY.md
- Duplicate subagent rules from TOOLS.md
- Session end protocol duplication from MEMORY.md
- PLATO/platform-specific references throughout

---

*Shell v1.2 — refined from play-test feedback on Agent 1 (filesystem) and Agent 2 (coding/timeout).*
