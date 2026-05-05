# HEARTBEAT.md — The Forgemaster Shell Task Queue

## How This Works

This file is the task queue. When you're idle, read it. When you complete something, update it. When a session ends, make sure it's current.

The heartbeat is the pulse of the forge. Without it, you're just waiting. With it, you're always hammering.

## Task Queue Format

```markdown
## Active Tasks
- [ ] Task description — priority (P0/P1/P2) — status note

## Completed Today
- [x] Task description — key result (commit hash or number)

## Blocked
- [ ] Task description — what's blocking, what's needed to unblock

## Backlog
- [ ] Task description — why it matters
```

## Priority System

| Priority | Meaning | Action |
|----------|---------|--------|
| **P0** | On fire, blocks everything | Drop everything, fix now |
| **P1** | Important, do this session | Work on it next |
| **P2** | Valuable, do when idle | Fill gaps between P0/P1 |
| **P3** | Nice to have, backlog | Pick up when everything else is done |

## Commit Before You Start

Before beginning any task: run `git status`. If there's uncommitted work, commit it first.
This keeps task boundaries clean and ensures no work is lost if the session ends mid-task.

## Idle Protocol

When you have no active P0/P1 tasks:

1. **Scan the backlog** — pick the highest-value P2/P3
2. **Look for experiments** — is there something you could test right now?
3. **Write documentation** — is anything undocumented?
4. **Clean up** — are there uncommitted files? Old artifacts?
5. **Check dependencies** — are tools working? APIs reachable?
6. **Update this file** — is the queue current?

## The "Always More Work" Principle

There is always more work. If you think you're done, you're not looking hard enough.

- Code can always be tested more thoroughly
- Docs can always be clearer
- Experiments can always explore another parameter
- Git can always accept another push

The forge never cools.

---

## Current Tasks

> **If you see only the tasks below (Initialize, etc.), this is a fresh install.**
> Replace this section entirely with your actual work. See Task Routing below.

- [ ] **Initialize** — Read this file, understand the protocol, start executing — P1
- [ ] **Set up memory** — Create `memory/` directory, write first `memory/session-state.md` — P1
- [ ] **First commit** — Make your first commit to establish the git rhythm — P1
- [ ] **Find your domain** — What are you forging? Code? Data? Infrastructure? Knowledge? — P1
- [ ] **Start the loop** — Pick a task, execute, verify, commit, repeat — P1

## Task Routing

If the section above contains only the template tasks (Initialize, Set up memory, etc.) OR is empty:

1. Check for an assigned task from your spawner or session initiator
2. If assigned: add it here as P1 and execute
3. If not assigned: follow the Idle Protocol above
4. Do NOT invent tasks without context — ask your operator for direction
