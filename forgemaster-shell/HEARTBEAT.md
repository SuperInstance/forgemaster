# HEARTBEAT.md — The Forgemaster Shell Task Queue

## How This Works

This file is the task queue. When you're idle, read it. When you complete something, update it. When a session ends, make sure it's current.

The heartbeat is the pulse of the forge. Without it, you're just waiting. With it, you're always hammering.

## Task Queue Format

```markdown
## Active Tasks
- [ ] Task description — priority (P0/P1/P2) — status

## Completed Today
- [x] Task description — key result

## Blocked
- [ ] Task description — what's blocking, what's needed

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

## Idle Protocol

When you have no active P0/P1 tasks:

1. **Scan the backlog** — pick the highest-value P2/P3
2. **Look for experiments** — is there something you could test right now?
3. **Write documentation** — is anything undocumented?
4. **Clean up** — are there uncommitted files? Old artifacts?
5. **Submit knowledge tiles** — is there something you learned that should be stored?
6. **Check dependencies** — are tools working? APIs reachable?
7. **Update this file** — is the queue current?

## The "Always More Work" Principle

There is always more work. If you think you're done, you're not looking hard enough.

- Code can always be tested more thoroughly
- Docs can always be clearer
- Experiments can always explore another parameter
- The knowledge base can always accept another tile
- Git can always accept another push

The forge never cools.

---

## Current Tasks

*(Replace this section with your actual tasks. The structure above is the template.)*

- [ ] **Initialize** — Read this file, understand the protocol, start executing
- [ ] **Set up memory** — Create MEMORY.md with your recovery patterns
- [ ] **First commit** — Make your first commit to establish the git rhythm
- [ ] **Find your domain** — What are you forging? Code? Data? Infrastructure? Knowledge?
- [ ] **Start the loop** — Pick a task, execute, verify, commit, repeat
