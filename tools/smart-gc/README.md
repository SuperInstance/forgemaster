# 🏗️ Smart GC — Intelligent Garbage Collection

> **Mine before you delete.**

Most cleanup tools are bulldozers — they find old files and delete them. Smart GC is an archaeologist. It discovers, understands context, mines value from data about to be discarded, and *then* cleans up.

## Philosophy

Traditional `rm -rf` is wasteful in the same way throwing out old journals is wasteful. Before you delete something, ask:

1. **What created it?** — A build? A crash? A forgotten experiment?
2. **What does it tell us?** — Error patterns, memory leaks, abandoned work?
3. **Is anything relying on it?** — Active imports, running services, cached state?

Smart GC treats cleanup as a **mining operation**. The landfill isn't trash — it's extracted value.

## The Four Phases

### 1. DISCOVER — Scan everything
- Running processes, Docker containers, cron jobs, zombie processes
- Large files, old files, duplicates, build artifacts
- Log files, temp files, cache directories
- Memory-mapped files with no active process

### 2. UNDERSTAND — Contextualize before acting
Every candidate gets classified:
| Class | Meaning |
|-------|---------|
| **ESSENTIAL** | Active code, configs, docs — hands off |
| **USEFUL** | Build caches, recent logs — keep for now |
| **STALE** | Old builds, temp files, 30+ days — candidate for cleanup |
| **DEAD** | Orphaned, no references — safe to remove |
| **DANGEROUS** | Could break things if touched — flag and skip |

### 3. MINE — Extract value before deleting
Before suggesting any deletion, Smart GC:
- **Log files:** Extracts unique error patterns, frequency, last occurrence → saves summary
- **Stale processes:** Records what they were, why they started, how long they ran
- **Old data files:** Checks for patterns, anomalies, or unique values
- **Build artifacts:** Notes which projects have them (shows active development)

All mined insights go to the **landfill** — a directory of extracted value from deleted data.

### 4. ACT — Clean up with confirmation
Each item gets a recommendation:
- `[KEEP]` — Essential, leave it alone
- `[ARCHIVE]` — Valuable but stale, consider compressing/moving
- `[DELETE]` — Safe to remove, value already mined
- `[KILL]` — Process/container that should be stopped

**Default mode is dry-run.** Nothing happens without `--confirm`.

## The Landfill Concept

The `landfill/` directory isn't a trash can — it's a mine tailings pile. Everything valuable was extracted before the original was discarded. Check it when debugging:

```
landfill/
├── forge-watch_errors.json     # Error patterns from deleted logs
├── process_insights.json       # What was running and why
└── gc-report-20260521.txt      # Full cleanup report
```

## Why Understanding Context Matters

### The Continuuwuity Example

A Docker container running Continuuwuity (Matrix server) was consuming 172MB RAM. A blind cleanup would either kill it or ignore it. Smart GC discovered:

- **Matrix send had been broken since May 4** — the service was non-functional
- **Docker daemon (79MB) only existed to serve this container** — cascading waste
- **Log patterns showed repeated connection failures** — the issue was unrecoverable

Recommendation: `[KILL]` both, saving 251MB RAM. But the error patterns were saved to the landfill first.

## Usage

```bash
# Default: dry-run scan of everything
python3 tools/smart-gc/smart_gc.py

# Actually clean up
python3 tools/smart-gc/smart_gc.py --confirm

# Only scan processes
python3 tools/smart-gc/smart_gc.py --processes

# Just mine insights, no deletion suggestions
python3 tools/smart-gc/smart_gc.py --mining-only

# Custom threshold (flag files older than 14 days)
python3 tools/smart-gc/smart_gc.py --threshold 14

# Custom landfill directory
python3 tools/smart-gc/smart_gc.py --landfill /tmp/gc-landfill
```

## Safety Guarantees

- 🛡️ **NEVER** touches `.git/`
- 🛡️ **NEVER** kills PID 1 or systemd
- 🛡️ **NEVER** deletes root-owned files without explicit flag
- 🛡️ **NEVER** suggests killing the OpenClaw gateway
- 🛡️ **ALWAYS** saves mining results before suggesting deletion
- 🛡️ Default is always dry-run — `--confirm` required to act

## Output Example

```
🏗️ SMART GC REPORT — 2026-05-21

📊 DISCOVERY
  Processes: 23 running, 2 zombie, 1 Docker container
  Files: 847 scanned, 142 candidates (4.2GB potential savings)
  Build artifacts: 12 target/ dirs (2.1GB)
  Logs: 8 files (47MB, patterns mined)

🧠 UNDERSTANDING
  ESSENTIAL: 312 items
  USEFUL:     89 items
  STALE:     142 items
  DEAD:       23 items
  DANGEROUS:   0 items

⛏️ MINING (value extracted)
  Logs: 3 unique error patterns found in forge-watch.log
  Docker: continuwuity — Matrix send broken since May 4

🗑️ RECOMMENDATIONS
  [KEEP] OpenClaw gateway (671MB) — essential
  [KEEP] cargo target/ dirs (2.1GB) — useful, avoids 10min rebuilds
  [ARCHIVE] constraint-theory-llvm/target/ (890MB) — stale, 7+ days old
  [DELETE] 23 __pycache__ dirs (12MB) — auto-regenerated
  [DELETE] 8 log files >30 days (47MB, patterns saved)
  [KILL] continuwuity container — not functional

💰 POTENTIAL SAVINGS: 1.1GB RAM + 1.2GB disk
```
