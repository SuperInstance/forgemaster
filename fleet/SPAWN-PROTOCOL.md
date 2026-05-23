# SPAWN-PROTOCOL.md — How to Spawn and Monitor Subagents

## The Problem
Subagents running experiments on slow models (Qwen-4B, MiMo) would:
1. Timeout at 300s with no output
2. Get stuck in recursive loops
3. Die silently without saving partial results

## The Fix: spawn-monitor + Generous Timeouts

### Command Pattern
```bash
# Run with live monitoring, 600s timeout, kill on 120s stall
bin/spawn-monitor experiments/script.py --full

# Longer for deep runs
TIMEOUT=1200 bin/spawn-monitor experiments/script.py --full

# Quick test
TIMEOUT=120 bin/spawn-monitor experiments/script.py --quick
```

### Timeout Guidelines
| Task Type | Timeout | Reason |
|-----------|---------|--------|
| Quick test (10 probes) | 120s | Should finish fast |
| Single-model run (100 probes) | 300s | ~3s per query |
| Multi-model run (300 probes) | 600s | ~2s per query × 3 models |
| Deep iteration (1000 probes) | 1200s | Long but bounded |
| Claude Code synthesis | 900s | Reads files, generates docs |
| Overnight holodeck | 7200s | Unattended deep runs |

### Stall Detection
- No new output for 120s = kill (pointless recursion)
- Can override: `STALL_KILL=300 bin/spawn-monitor ...`

### Subagent Spawns via sessions_spawn
```python
# Use generous runTimeoutSeconds
sessions_spawn(
    task="...",
    mode="run",
    runTimeoutSeconds=600,  # NOT 300
)
```

### Monitoring Running Subagents
```bash
# Check what's alive
ps aux | grep python3 | grep experiments

# Watch a specific output file
tail -f /tmp/spawn-monitor.* 
```

### Early Kill Signals
If a subagent is stuck:
1. Check its last output: `tail -5 /tmp/spawn-monitor.XXXXX`
2. If genuinely stuck (repeating same query), kill it
3. Partial results in the output file are still valid — parse what you got
