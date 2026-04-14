# ⚙️ Engine Room — Crew Manifest & Resource Status

## Active Crew

| ID | Agent | Model | Task | Status | Resource |
|----|-------|-------|------|--------|----------|
| quiet-prairie | Pi | llama-3.3-70b (Groq) | Vector search rebuild | 🔨 Running | Low (Groq remote) |
| nimble-canyon | Pi | llama-3.3-70b (Groq) | Signal processing proof | 🔨 Running | Low (Groq remote) |

## On Leave (Available)

| Agent | Cost | Best For | Load Procedure |
|-------|------|----------|---------------|
| Claude Code | $$$ | Architecture, reviews, complex reasoning | `claude --print --permission-mode bypassPermissions "prompt"` |
| Pi + Groq | Free | Batch code gen, tests, parallel work | `pi -p "prompt" --provider groq --model llama-3.3-70b-versatile` |
| Aider + Groq | Free | In-repo refactoring, multi-file edits | `aider --model groq/llama-3.3-70b-versatile --message "prompt"` |

## Below Deck (Installed, Not Loaded)

| Tool | Binary | Load Cost | Notes |
|------|--------|-----------|-------|
| Codex CLI | `/usr/bin/codex` | Needs OPENAI_API_KEY | Not usable without key |
| Pi (all models) | `.bin/pi` | Remote | Can switch to DeepInfra models |
| Aider | `~/.local/bin/aider` | Remote | Also supports DeepSeek |

## Hull Capacity

- **RAM Budget**: ~4GB for agent crews (WSL2 total ~8GB shared)
- **Concurrent Builds**: 2 max (OOM kills at 3+)
- **GPU**: RTX 4050 (not currently used for inference — agents run remote)
- **Disk**: Plenty for repos

## Load/Unload Procedures

### Spin up a Pi crew member
```bash
PI=/usr/lib/node_modules/openclaw/node_modules/.bin/pi
cd /tmp/$WORK_DIR && git init
$PI -p "$TASK" --provider groq --model llama-3.3-70b-versatile &
# Monitor: process action:poll sessionId:$ID
# When done: git add -A && git commit, push to GitHub
# Unload: rm -rf /tmp/$WORK_DIR
```

### Spin up Claude Code (expensive, use wisely)
```bash
cd /tmp/$WORK_DIR
claude --permission-mode bypassPermissions --print "$TASK" 2>&1
# Same cleanup
```

### A/B Test Two Crew Members
```bash
# Same task, different models
pi -p "$TASK" --provider groq --model llama-3.3-70b-versatile &
pi -p "$TASK" --provider groq --model openai/gpt-oss-120b &
# Compare outputs, pick winner
```
