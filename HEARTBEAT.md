# Night Shift Task Queue

## FIRST: Check forge-watch
```bash
cat ~/.openclaw/workspace/.keeper/forge-watch.json
```
If `stale: true` → START WORKING IMMEDIATELY. No status replies.

## Queue
1. **GSM-ify Lucineer → PLATO tiles** — `/tmp/lucineer-analysis/`, 10-15 tiles/batch, push every batch
2. **Build HTML frontends** — arena chat, grammar explorer, skill forge → `fleet-knowledge/fixes/frontend/`
3. **Write PLATO tiles** — any domain, target 200+/shift
4. **Publish ct-demo** — `/tmp/ct-demo/`, 22 tests, need Casey's go-ahead
5. **Knowledge distillation** — Lucineer → structured tiles

## Rules
- PUSH EVERY 30 MIN
- Never HEARTBEAT_OK — do work
- If tools OOM, write directly
- Update this file as tasks complete

## Stats (every 2h)
`curl http://147.224.38.131:8847/rooms` → `memory/night-shift-stats.md`

## Sunrise Report (6am AKDT)
Tiles submitted, pushes, files produced, PLATO growth, blockers.
