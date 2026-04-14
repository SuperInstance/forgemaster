# 🔐 Brothers-Keeper Protocol

> A lightweight daemon that lives outside the agent loop. Guardian of keys, monitor of health, lifeline when the captain goes down.

## Architecture

```
┌─────────────────────────────────────────────────┐
│  FORGEMASTER (Captain)                          │
│  OpenClaw agent, runs in session loop            │
│  Talks to Keeper via heartbeat file              │
│  Can ask Keeper for API keys on demand           │
├─────────────────────────────────────────────────┤
│  KEEPER (Brothers-Keeper)                       │
│  Lightweight shell daemon, runs via system cron  │
│  Monitors: gateway health, heartbeat freshness   │
│  Proxies: API keys to git-agents via temp files  │
│  Heals: restarts gateway, kills zombies          │
│  Logs: human-readable status every cycle         │
├─────────────────────────────────────────────────┤
│  GIT-AGENTS (Crew)                              │
│  Pi, Aider, Claude Code, etc.                   │
│  Ask Keeper for keys, don't store them           │
│  Report status via exit codes                    │
└─────────────────────────────────────────────────┘
```

## Communication

### Captain → Keeper (every 5 minutes)
Write to `~/.openclaw/workspace/.keeper/heartbeat.json`:
```json
{
  "timestamp": "2026-04-14T10:55:00-08:00",
  "status": "working",
  "crew": ["quiet-prairie:running", "nimble-canyon:failed"],
  "last_action": "pushed vector-search proof",
  "watch": "2026-04-14 0800-1055 AKDT",
  "proofs_done": 4,
  "proofs_building": 1
}
```

### Keeper → Captain (every 10 minutes)
Write to `~/.openclaw/workspace/.keeper/keeper-response.json`:
```json
{
  "timestamp": "2026-04-14T10:50:00-08:00",
  "gateway": "running",
  "gateway_pid": 951,
  "cpu_pct": 23,
  "mem_used_gb": 4.2,
  "mem_total_gb": 8.0,
  "disk_free_gb": 127,
  "load_1m": 1.2,
  "active_processes": ["claude:2", "node:1", "pi:0"],
  "actions_taken": [],
  "warnings": []
}
```

### Brothers-Keeper Protocol (both silent for 15+ minutes)
1. Keeper notices heartbeat is stale (>15 min)
2. Keeper checks: is gateway running? Is the agent session alive?
3. If gateway down: `openclaw gateway restart`
4. If agent frozen: check for zombie processes, kill if needed
5. If disk full: clean /tmp, cargo cache, old targets
6. Log all actions to `~/.openclaw/workspace/.keeper/keeper.log`
7. If Keeper itself is down: the captain notices keeper-response is stale, uses heartbeat cron to restart it

## API Key Proxy

### Requesting a Key
Git-agents write to `~/.openclaw/workspace/.keeper/key-request.json`:
```json
{
  "requester": "pi-agent-001",
  "provider": "groq",
  "timestamp": "2026-04-14T10:55:00-08:00"
}
```

Keeper responds by writing the key to a temp file:
```bash
~/.openclaw/workspace/.keeper/keys/groq-<requester>-<timestamp>.key
# File auto-deletes after 60 seconds
```

### Why This Matters
- Git-agents cloned from other vessels don't need keys baked in
- Rapid prototyping: spin up a Pi agent, it asks Keeper, gets a key, works
- Key rotation: change once in Keeper, all agents get new key
- Audit: Keeper logs every key request
