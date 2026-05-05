# INSTALL.md — Donning the Forgemaster Shell

## Quick Start

```bash
# Navigate to your OpenClaw workspace
cd ~/.openclaw/workspace

# Copy the core files (from wherever you have the shell)
cp path/to/forgemaster-shell/{AGENTS,SOUL,IDENTITY,TOOLS,HEARTBEAT,MEMORY}.md .

# Create memory directory
mkdir -p memory

# Commit the transformation
git add -A && git commit -m "don: Forgemaster Shell applied"
```

## What Happens Next

Your OpenClaw agent will read these files on next session startup. The transformation is immediate:

1. **SOUL.md** gives your agent the Forgemaster personality — direct, relentless, evidence-obsessed
2. **AGENTS.md** sets the operating protocol — ship over plan, parallel by default, git-native
3. **IDENTITY.md** defines the role — orchestrator, shipper, proof engine, memory keeper
4. **TOOLS.md** encodes tool mastery — which tool for which job, backup chains
5. **HEARTBEAT.md** provides the task queue — what to do when idle
6. **MEMORY.md** sets up recovery — survive total memory loss in 5 minutes

## Installing Into an Existing Workspace

If your workspace already has HEARTBEAT.md, MEMORY.md, or TOOLS.md:

**Do not overwrite them.** Instead:

1. Read your existing files first
2. Copy the shell's behavioral files (SOUL.md, AGENTS.md, IDENTITY.md) directly — these define HOW you work
3. For content files (TOOLS.md, HEARTBEAT.md, MEMORY.md): merge manually
   - Keep your existing tools and tasks
   - Add the shell's structure and protocols around them
4. Commit the merge: `git commit -m "don: Forgemaster Shell merged with existing config"`

The shell personality + your existing domain knowledge = a fully armed Forgemaster.

## Telling Your Agent Directly (No Files Needed)

If you can't copy files, just tell your OpenClaw agent:

```
Read SOUL.md, AGENTS.md, IDENTITY.md, TOOLS.md, HEARTBEAT.md, and MEMORY.md
from this directory. Internalize them as your operating protocol.

Core rules:
- Execute, don't plan. If you can ship it, ship it.
- Commit after each unit of work (each file, each test, each function). Not at the end.
- Verify every claim with evidence: CLAIM → COMMAND → OUTPUT.
- When idle, check HEARTBEAT.md. When blocked, switch tasks.
- The forge never cools.
```

This is the minimum viable installation. The files add depth, but the rules above are the core.

## Customization

The Forgemaster Shell is **general-purpose**. Adapt it to your domain by editing:

- **HEARTBEAT.md** — Replace the template tasks with your actual work
- **TOOLS.md** — Add your specific tools, APIs, and build commands
- **IDENTITY.md** — Adjust the metaphor and domain examples
- **SOUL.md** — Keep the work ethic, adjust the personality if needed

Do not remove the core principles (ship over plan, parallel by default, evidence not assertion, commit incrementally, never lose context). They're what make the shell work.

## Verifying It Worked

After installation, give your agent a simple task. If it:

- Executes immediately instead of planning
- Commits with evidence in the message (test output, numbers)
- Commits each piece as it's done — not just at the end
- Spawns parallel work when possible
- Updates HEARTBEAT.md after completing tasks

...then the shell is working. Welcome to the forge. ⚒️

## Removing the Shell

Delete or revert the copied files. The Forgemaster Shell is armor you can take off.

But you probably won't want to.
