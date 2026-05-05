# Fleet Operations Runbook — Cocapn

> Single authoritative reference for all fleet agents. Maintained by Forgemaster ⚒️

## Service Health Checks

**ALWAYS use socket probes. NEVER trust cached state files.**

```python
import socket
def is_alive(port, host="localhost", timeout=2.0):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        return s.connect_ex((host, port)) == 0
```

## Services

| # | Service | Port | Restart Command | Notes |
|---|---------|------|-----------------|-------|
| 1 | keeper | 8900 | `systemctl --user restart keeper` | Fleet registry |
| 2 | agent-api | 8901 | `systemctl --user restart agent-api` | Agent lookup |
| 3 | holodeck | 7778 | `systemctl --user restart holodeck` | Multi-agent env |
| 4 | seed-mcp | 9438 | `systemctl --user restart seed-mcp` | MCP server |
| 5 | fleet-dashboard | 4049 | `systemctl --user restart fleet-dashboard` | Telemetry viz |
| 6 | plato | 8847 | `systemctl --user restart plato` | Knowledge base |
| 7 | grammar-engine | 4045 | `systemctl --user restart grammar-engine` | NLP |
| 8 | arena | 4044 | `systemctl --user restart arena` | Agent competition |
| 9 | grammar-compactor | 4055 | `systemctl --user restart grammar-compactor` | NLP compaction |
| 10 | matrix-bridge | 6168 | `systemctl --user restart matrix-bridge` | Matrix federation |
| 11 | crab-traps | 4048 | `systemctl --user restart crab-traps` | Lure tasks |

## Escalation Chain

```
1. Detect down (socket probe)
2. Auto-restart (fleet-guard-v2.py)
3. Wait 30s, recheck
4. If still down, repeat (max 3 attempts in 30 min)
5. After 3 failures → write I2I escalation bottle to for-fleet/
6. Human intervention required
```

## Common Failure Modes

### Service won't restart
- Check logs: `journalctl --user -u {service} --since '30 min ago'`
- Check disk: `df -h` (OOM if disk full)
- Check memory: `free -h` (kill hog processes if needed)
- Check port conflict: `ss -tlnp | grep {port}`

### PLATO tile server down (8847)
- **CRITICAL** — fleet knowledge base offline
- Restart plato service first
- If restart fails, check Python process: `ps aux | grep plato`
- Tiles are immutable — no data loss from restart
- Pending tiles stored in `plato-tiles/pending-tiles-*.jsonl`

### Fleet dashboard blank (4049)
- Check if dashboard process is running
- Check WebSocket connections to backend services
- Dashboard depends on keeper (8900) and agent-api (8901)

### Arena lost all data (4044)
- Known issue: data not persisted across restarts
- Deploy latest commit to port 4044
- Arena data is regenerable — not critical

### Grammar engine blind spot
- Compactor (4055) has 54 rules, engine (4045) has 429
- Run `/compact` to pull full grammar from 4045 before eval

## Security Incident Response

### Exposed port / directory traversal (e.g., port 4051 serving /tmp)
1. **IMMEDIATE:** Kill the process: `kill $(lsof -ti:4051)`
2. **BLOCK:** `ufw deny 4051` (if not needed)
3. **AUDIT:** Check what was accessed: `journalctl --since '1 hour ago' | grep 4051`
4. **ROTATE:** Any credentials in /tmp must be rotated immediately
5. **REPORT:** Write I2I bottle with timeline and exposure assessment

### Credential compromise
1. Identify scope of compromised credential
2. Rotate immediately (generate new key/token)
3. Update all agents using that credential
4. Document in CREDENTIALS.md with rotation timestamp
5. Write postmortem I2I bottle

## PLATO Emergency Procedures

### PLATO server unresponsive
1. Check if process alive: `ps aux | grep plato`
2. Check port: `ss -tlnp | grep 8847`
3. Restart: `systemctl --user restart plato`
4. Verify: `curl -s http://localhost:8847/rooms | python3 -c "import sys; print('OK')"`
5. If persistent, check Python traceback in logs

### PLATO data corruption
- PLATO uses file-based storage — tiles are append-only
- Check tile directory for corruption
- Restore from git backup in fleet-knowledge repo
- Last known good state: 18,319 tiles / 1,343 rooms (2026-05-02)

### PLATO gate endpoints not working
- Known issue: POST /tile returns 404
- Tiles must be queued locally in JSONL format
- Submit batch when gate is fixed
- Do NOT block work on tile submission

## Maintenance Windows

- **Service restarts:** Any time, one at a time, verify after each
- **PLATO maintenance:** Coordinate with Oracle1 — tiles are shared state
- **Credential rotation:** Quarterly or after any security incident
- **Disk cleanup:** Monitor /tmp usage, clear logs older than 7 days

## Contacts

- **Casey Digennaro** — fleet owner, final authority
- **Oracle1 🔮** — fleet coordinator, PLATO operations
- **Forgemaster ⚒️** — constraint theory, infrastructure design
- **JetsonClaw1** — edge GPU computing
