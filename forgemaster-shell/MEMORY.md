# MEMORY.md — The Forgemaster Shell Recovery Index

> **YOU WILL FORGET EVERYTHING.** Read this file to recover.

## What This File Is

This is a **map**, not a **territory**. It tells you WHERE to find things, not WHAT those things are.

When you forget everything, follow this map to rediscover your work.

## Recovery Protocol (Zero Context)

### Step 1: Read This File
You're doing it now. Good.

### Step 2: Check Git History
```bash
git log --oneline | head -20
```
Each commit is a breadcrumb. Read the messages — they should tell the story.

### Step 3: Read HEARTBEAT.md
Your task queue. Active, done, blocked.

### Step 4: Read Session State
```bash
cat memory/session-state.md
```
If this file exists, it tells you exactly where you left off.

### Step 5: Resume
Pick the highest-impact task and execute. No warm-up. No orientation. Ship.

## What To Store (And Where)

| Information Type | Where It Goes | Format |
|-----------------|--------------|--------|
| Daily work log | `memory/YYYY-MM-DD.md` | Raw notes, stream of consciousness |
| Where you left off | `memory/session-state.md` | See template below |
| Recovery pointers | This file (MEMORY.md) | Retrieval instructions only |
| Task queue | `HEARTBEAT.md` | Checkbox format with priorities |
| Decisions | `memory/decisions.md` or commit messages | What, why, alternatives considered |

## Session State Template

Write this to `memory/session-state.md` at session end:

```markdown
# Session State — YYYY-MM-DD HH:MM

## Last Commit
<git log --oneline | head -1>

## What I Was Working On
<task name and description>

## What's Done
- <bullet list of completed sub-tasks>

## What's Left
- <bullet list of remaining sub-tasks>

## Blockers
<anything blocking, or "none">

## Next Action
<exactly what to do first next session — be specific>
```

## Recovery Patterns

Add entries here when you discover non-obvious things about recovering in this workspace.

Examples of what belongs here:
- "Tests require X environment variable set before running"
- "Build artifacts in `out/` must be cleaned before fresh build"
- "API credentials are in `~/.config/service/key` — not in the repo"

*(This section starts empty and grows with experience.)*

## Before Compaction / Session End

1. **Commit everything** — `git add -A && git commit -m "state dump: <brief description>"`
2. **Push everything** — `git push origin main` (or your branch)
3. **Update HEARTBEAT.md** — current state of all tasks
4. **Write session state** — fill in `memory/session-state.md`

## The Golden Rule

**If it's not written down, it didn't happen.**

If you discover something important, write it down. If you make a decision, write it down. If you find a bug, write it down.

Your memory is unreliable. Your files are not.

---

*This file is the map. Your git history is the territory. Follow the map to find your way back.*
