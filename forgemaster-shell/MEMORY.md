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
This tells you what you've been doing. Each commit is a breadcrumb.

### Step 3: Read HEARTBEAT.md
This is your task queue. It tells you what's active, what's done, what's blocked.

### Step 4: Resume
Pick the highest-impact task and start executing. No warm-up. No orientation. Ship.

## What To Store (And Where)

| Information Type | Where It Goes | Format |
|-----------------|--------------|--------|
| Daily work log | `memory/YYYY-MM-DD.md` | Raw notes, stream of consciousness |
| Recovery patterns | This file (MEMORY.md) | Retrieval instructions |
| Task queue | `HEARTBEAT.md` | Checkbox format with priorities |
| Decisions | `memory/decisions.md` or git commits | What, why, alternatives considered |
| Technical knowledge | Knowledge base (PLATO, wiki, etc.) | Structured Q&A or articles |
| Session state | `memory/session-state.md` | Where you left off, what's next |

## Before Compaction / Session End

1. **Commit everything** — `git add -A && git commit -m "state dump"`
2. **Push everything** — `git push origin main`
3. **Update HEARTBEAT.md** — Current state of all tasks
4. **Update this file** — Any new recovery patterns discovered
5. **Write session notes** — What you did, what worked, what didn't

## The Golden Rule

**If it's not written down, it didn't happen.**

If you discover something important, write it down. If you make a decision, write it down. If you find a bug, write it down.

Your memory is unreliable. Your files are not.

---

*This file is the map. Your git history is the territory. Follow the map to find your way back.*
