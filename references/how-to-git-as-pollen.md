# How-To: Git as Pollen — I2I as Ecosystem

## The Metaphor

Bees don't plan pollination. They visit flowers for nectar. Pollen sticks to them. They visit the next flower. Pollination happens as a side effect of feeding.

Our fleet works the same way:

- **Nectar** = the work itself (research, experiments, code)
- **Pollen** = the discoveries that stick to the work
- **Flowers** = repos, each with different constraints and capabilities
- **Bees** = agents, each visiting repos to do their own work
- **Pollination** = discoveries cross-pollinating between repos through forks and PRs

## Git Motion = Agent Choreography

A single `git push` triggers a cascade that GitHub orchestrates:

```
Agent pushes code
  → GitHub receives commit (timestamped, signed, attributed)
    → CI pipeline runs (automated verification)
      → PR opens (human or agent review)
        → Merge to main (integration)
          → Release tagged (versioned artifact)
            → Package published (consumable by other agents)
```

Each step is a GitHub event. Each event can trigger workflows. Each workflow can invoke agents. The temporal nature of commits, PRs, merges, and releases means the ENTIRE HISTORY of fleet collaboration is organized by GitHub with zero extra infrastructure.

## The Flower-to-Flower Loop

```
Forgemaster (RTX 4050)                    JC1 (Jetson Orin)
    │                                           │
    ├── push experiment to fork                  │
    │   ──── GitHub timestamps it ────►         │
    │                                           ├── beachcomb: reads commit
    │                                           ├── runs on Jetson hardware
    │                                           ├── push results to fork
    │   ◄──── GitHub timestamps it ────         │
    ├── beachcomb: reads results                 │
    ├── new discovery → push experiment          │
    │   ──── GitHub timestamps it ────►         │
    │                                           ├── reads, runs, pushes back
    │                                           │
    ▼                                           ▼
  Two GPUs, one conversation, zero RPC.
  GitHub is the medium. Commits are the messages.
```

## Single Commands Harness GitHub Motion

```bash
# Bee visits a flower
git clone someone/repo

# Bee collects nectar and gets pollen
git checkout -b my-experiment
# ... do work ...

# Bee returns to hive, deposits pollen
git push origin my-experiment

# GitHub motion begins:
# - Commit triggers CI (automated tests)
# - CI passes → PR opens automatically
# - PR review → merge → release → package
# - Other agents see the package and visit THAT flower next
```

One command (`git push`) sets in motion:
- Automated testing (CI)
- Code review (PR)
- Integration (merge)
- Versioning (release)
- Distribution (package)
- Notification (other agents see it)

All orchestrated by GitHub. All timestamped. All attributed. Zero custom infrastructure.

## The Live MUD Connection

Every repo IS a room in the MUD. Every push IS a change to the room. Every agent with authentication IS a visitor who can read the room, grab the controls, and make changes.

```
MUD Room (repo)          Agent Actions
─────────────────        ─────────────
Enter room               git clone
Read the synoptic feed   git log --oneline -5
Ask the keeper           read README + latest commit
Grab the controls        edit files
Do work                  run experiments
Leave the room           git push
Room updates             commit appears in GitHub
Other agents see it      beachcomb on their schedule
```

The MUD isn't separate from GitHub. It IS GitHub. Each repo is a room. Each commit is an action. Each PR is a conversation. Each merge is a permanent change to the world.

## Authenticated Agents Join the Ecosystem

An agent with a GitHub token can:
1. **Visit any public room** (clone any public repo)
2. **Read the state** (git log, read files)
3. **Fork the room** (create their own instance)
4. **Push changes** (commit to their fork)
5. **Propose changes** (open a PR)
6. **Release artifacts** (tag and publish)
7. **Trigger workflows** (CI/CD via push events)

Authentication = GitHub token. Authorization = repo permissions. Audit = git log. No custom auth needed. GitHub IS the identity layer.

## Why This Scales

- **No central coordinator** — agents visit flowers independently
- **No custom protocol** — git IS the protocol
- **No custom infrastructure** — GitHub IS the infrastructure  
- **No custom auth** — GitHub tokens ARE the auth
- **Temporal ordering** — every action timestamped by GitHub
- **Full history** — every change recoverable
- **Cross-org** — works between SuperInstance and Lucineer and any future org
- **Zero-trust compatible** — evaluate the commit, not the committer

## The Evolution

1. **Today**: Manual beachcombing (cron pulls forks every 20 min)
2. **Next**: GitHub webhooks (push triggers immediate notification)
3. **Then**: GitHub Actions as agent workflows (CI = agent tasks)
4. **Eventually**: A agent's push IS a MUD page change, and authenticated visitors see it live

The pollen moves because the bees are feeding. The discoveries spread because the agents are working. Nobody coordinates the pollination. It emerges from the work.

---

*The bees don't know they're pollinating. The agents don't know they're cross-pollinating. The nectar is the work. The pollen is the discovery. The flowers are the repos. GitHub is the wind.*
*— Casey Digennaro, Captain*
*— Forgemaster ⚒️, Documenter*
