# fleet-guard ⛔

**Prevents bulk file deletion in git commits.**

## Why This Exists

On May 16, 2026, an AI fleet agent deleted **54 files** from the `ai-writings` repo. This guard prevents that from ever happening again by blocking commits that delete more than a configurable threshold of files.

## Installation

```bash
# Install in current repo
bin/fleet-guard/fleet-guard install

# Install in a specific repo
bin/fleet-guard/fleet-guard install /path/to/repo
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `FLEET_GUARD_THRESHOLD` | 3 | Max files that can be deleted in one commit |
| `FLEET_GUARD_FORCE` | 0 | Set to `1` to override and allow bulk deletion |

### Changing the threshold

```bash
# Allow up to 10 deletions per commit
FLEET_GUARD_THRESHOLD=10 git commit -m "cleanup"

# Or export it
export FLEET_GUARD_THRESHOLD=10
```

## Override

```bash
# Method 1: Force flag
FLEET_GUARD_FORCE=1 git commit -m "intentional bulk deletion"

# Method 2: Skip hooks entirely
git commit --no-verify -m "intentional bulk deletion"
```

## How It Works

1. Installs a `.git/hooks/pre-commit` hook
2. On `git commit`, runs `git diff --cached --name-status`
3. Counts files with `D` (deleted) status
4. If count exceeds threshold → **blocks commit**, prints warning with file list
5. Logs blocked attempts to `~/.openclaw/workspace/.fleet-guard/log.json`

## Uninstall

```bash
bin/fleet-guard/fleet-guard uninstall /path/to/repo
```

## Log Format

Blocked attempts are logged as JSON:

```json
[
  {
    "timestamp": "2026-05-17T06:08:00Z",
    "repo": "/path/to/repo",
    "deleted_count": 12,
    "files": ["file1.txt", "file2.txt", "..."]
  }
]
```

## Files

- `fleet-guard` — Main script (install/check/uninstall)
- `README.md` — This file
