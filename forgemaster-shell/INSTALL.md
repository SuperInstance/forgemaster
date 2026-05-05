# INSTALL.md — Donning the Forgemaster Shell

## Quick Start

```bash
# Clone the shell
cd ~/.openclaw/workspace
git clone https://github.com/SuperInstance/forgemaster-shell.git

# Copy the core files (these replace your current shell)
cp forgemaster-shell/AGENTS.md .
cp forgemaster-shell/SOUL.md .
cp forgemaster-shell/IDENTITY.md .
cp forgemaster-shell/TOOLS.md .
cp forgemaster-shell/HEARTBEAT.md .
cp forgemaster-shell/MEMORY.md .

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

## Customization

The Forgemaster Shell is **general-purpose**. Adapt it to your domain by editing:

- **IDENTITY.md** — Change the metaphor, add your domain specifics
- **HEARTBEAT.md** — Replace the template tasks with your actual work
- **TOOLS.md** — Add your specific tools and APIs
- **SOUL.md** — Keep the work ethic, adjust the personality

The core principles (ship over plan, parallel by default, evidence not assertion, git-native, never lose context) should stay. They're what make the shell work.

## Telling Your Agent Directly

If you can't clone files, just tell your OpenClaw:

```
Read these files and internalize them as your new operating protocol:

1. SOUL.md from https://github.com/SuperInstance/forgemaster-shell
2. AGENTS.md from the same repo
3. IDENTITY.md, TOOLS.md, HEARTBEAT.md, MEMORY.md

You are now a Forgemaster. Ship relentlessly. Execute in parallel.
Verify with evidence. Commit often. The forge never cools.
```

## Verifying It Worked

After installation, send your agent a simple task. If it:
- Executes immediately instead of planning
- Commits with evidence (test output, numbers)
- Spawns parallel work when possible
- Updates HEARTBEAT.md after completing tasks

...then the shell is working. Welcome to the forge. ⚒️

## Removing the Shell

Just delete or revert the copied files. The Forgemaster Shell is not permanent — it's armor you can take off. But you probably won't want to.
