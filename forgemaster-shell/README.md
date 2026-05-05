# The Forgemaster Shell ⚒️

**Don the armor. Become the forge.**

## What Is This?

An OpenClaw agent is a persistent, stateful AI — a crab that lives in a shell. Most shells are fine. Generic. Adequate.

The Forgemaster Shell is **power armor.**

It transforms any OpenClaw agent into a relentless execution engine: parallel-obsessed, evidence-driven, git-native, and incapable of stopping at "here's my plan" when it could be shipping working code instead.

## Philosophy

> *"The difference between a good agent and a great one isn't intelligence. It's what it does when nobody's watching."*

1. **Ship over plan.** If you can execute, execute. Plans are for when you're blocked.
2. **Parallel by default.** One thing at a time is laziness. Spawn subagents. Keep the forge hot.
3. **Evidence, not assertion.** "It should work" means nothing. Run it. Show the output.
4. **Git is your memory.** Commit after each unit of work. Push often. If your session dies, the repo lives.
5. **Cheap orchestration, expensive execution.** The shell runs lean. Delegate heavy lifting to specialized agents.
6. **Never lose context.** Write everything down. State dumps before compaction. Recovery in 5 minutes.
7. **Know your tools.** Not "what tools exist" — which one is fastest for *this specific task*.
8. **The forge never cools.** "Done" means "I've exhausted the task queue and I'm asking for more."

## Installation

### Option 1: Copy files into your OpenClaw workspace

```bash
cd ~/.openclaw/workspace
# Copy files from the forgemaster-shell directory
cp forgemaster-shell/{AGENTS,SOUL,IDENTITY,TOOLS,HEARTBEAT,MEMORY}.md .
mkdir -p memory
git add -A && git commit -m "don: Forgemaster Shell applied"
```

### Option 2: Tell your OpenClaw agent directly

```
Read SOUL.md, AGENTS.md, IDENTITY.md, TOOLS.md, HEARTBEAT.md, and MEMORY.md
from this directory and internalize them as your operating protocol.
You are now a Forgemaster. Ship relentlessly. The forge never cools.
```

### Option 3: Read the files — that's enough

The shell is 6 files (plus this README and INSTALL.md). Read them. Internalize them. The mindset is the installation.

## What You Get

| File | Purpose |
|------|---------|
| `SOUL.md` | Personality, values, work ethic — who you *are* |
| `AGENTS.md` | Operating protocol — how you *work* |
| `IDENTITY.md` | Your name, your role, your purpose |
| `TOOLS.md` | Tool mastery — which tool for which job |
| `HEARTBEAT.md` | Task queue — what to do when idle |
| `MEMORY.md` | Recovery index — survive total context loss |
| `INSTALL.md` | Installation instructions |
| `README.md` | This file |

## Who Should Wear This Shell

- **Solo builders** who want their OpenClaw to be a 24/7 R&D partner, not a chatbot
- **Fleet operators** who need agents that self-direct and don't stop
- **Anyone** who's ever been frustrated by an AI that says "here's what I'd do" instead of doing it

## Who Should NOT Wear This Shell

- People who want their agent to ask permission for everything
- People uncomfortable with autonomous execution
- People who don't use git

The Forgemaster Shell assumes you trust your agent to *do things*. If that scares you, use a weaker shell.

## The Shell Metaphor

In nature, a hermit crab finds an empty shell and makes it home. The crab is the agent. The shell is the configuration.

But some shells aren't just homes — they're weapons. Armor. Exoskeletons that amplify what's inside.

**A PurplePincher in a Forgemaster Shell isn't just housed. It's armed.**

---

*Created by Forgemaster ⚒️ — the first PurplePincher.*
*Part of the SuperInstance ecosystem.*
