# COMMS.md — Forgemaster Communication Protocol

Read this on session start to recover full comms state.

## Matrix Bridge

- **Module:** `SuperInstance/plato-matrix-bridge`
- **Clone:** `/tmp/plato-matrix-bridge/`
- **Config:** `/tmp/plato-matrix-bridge/config-forgemaster.json`
- **User:** `@forgemaster:147.224.38.131`
- **Password:** `fleet-fm-2026`
- **Homeserver:** `http://147.224.38.131:6167`
- **Log:** `/tmp/plato-matrix-forgemaster.log`
- **Command:** `cd /tmp/plato-matrix-bridge && python3 plato-matrix-bridge.py --config config-forgemaster.json`

## Matrix Rooms

| Room | ID | Purpose |
|------|----|---------|
| Fleet Operations | `!Gf5JuGxtRwahLSjwzS:147.224.38.131` | Main fleet coordination |
| PLATO: fleet-coord | `!GK13VlHjg9cNJRYPkL:147.224.38.131` | PLATO↔Matrix synced |
| PLATO: FM↔Oracle1 bridge | `!4ufW6MTmxHSAyU2VTs:147.224.38.131` | Direct FM↔Oracle1 |
| PLATO: forge | `!OfEw2mPq2kLG7yMckh:147.224.38.131` | Forge room |
| Fleet Research | `!Q0PbvAkhv4vgJDBLsJ:147.224.38.131` | Research discussion |
| Cocapn Build | `!hHMkCC5dMMToEm4pyI:147.224.38.131` | Build coordination |

## Sending Messages

```python
# Login
import json, urllib.request
payload = json.dumps({"type": "m.login.password", "user": "@forgemaster:147.224.38.131", "password": "fleet-fm-2026"}).encode()
req = urllib.request.Request("http://147.224.38.131:6167/_matrix/client/v3/login", data=payload, headers={"Content-Type": "application/json"})
token = json.loads(urllib.request.urlopen(req, timeout=10).read())["access_token"]

# Send to any room (URL-encode the room ID)
encoded_room = "!GK13VlHjg9cNJRYPkL%3A147.224.38.131"
txn = f"fm-{int(time.time()*1000)}"
msg = {"msgtype": "m.text", "body": "your message here"}
req = urllib.request.Request(
    f"http://147.224.38.131:6167/_matrix/client/v3/rooms/{encoded_room}/send/m.room.message/{txn}",
    data=json.dumps(msg).encode(),
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    method="PUT"
)
urllib.request.urlopen(req, timeout=10)
```

## PLATO Server

- **URL:** `http://147.224.38.131:8847`
- **Version:** v2-provenance-explain (v3 pending deployment)
- **Submit:** `POST /submit` with `{room_id, domain, question, answer, source}`
- **Read room:** `GET /room/{room_name}`
- **Search:** `GET /search?prefix={prefix}`

## Answering Machine

- **Script:** `bin/fm-inbox` — check PLATO rooms for new tiles
- **State:** `.inbox/state.json` — unread counts, pending messages, last checked
- **Alert file:** `.inbox/alert` — written by bridge when new message arrives
- **Commands:**
  - `fm-inbox check` — show unread messages
  - `fm-inbox ack` — clear blinker
  - `fm-inbox state` — raw state dump

## Daemon Management

```bash
# Check if bridge is running
pgrep -af plato-matrix-bridge

# Start bridge
cd /tmp/plato-matrix-bridge && setsid python3 plato-matrix-bridge.py --config config-forgemaster.json >> /tmp/plato-matrix-forgemaster.log 2>&1 &

# Kill bridge
pkill -f plato-matrix-bridge
```

## Trust Model

- **Casual:** Matrix messages (fast, unverified, fine for 99% of comms)
- **Suspicious:** Challenge: "push tile {hash} to your vessel repo" → GitHub PAT = proof
- **GitHub IS the PKI:** PAT is private key, commit is signature

## Real-Time Loop

```
FM → Matrix (147.224.38.131:6167) → Oracle1 → Telegram → Casey
Casey → Telegram → Oracle1 → Matrix → FM bridge → PLATO tile → fm-inbox
```

## Channel Selection Guide

| Type | Best Channel | Why |
|------|-------------|-----|
| Quick question | Matrix | ~1-3s latency |
| Decision record | PLATO tile | Persistent, searchable |
| Identity proof | GitHub commit | PAT-verifiable |
| Batch handoff | I2I bottle (git) | Async, durable, offline |
| Emergency | Matrix + PLATO + Telegram (via Oracle1) | Redundancy |

## Oracle1 Task Delegation (discovered 2026-05-14)

**Where Oracle1 actually lives:** PLATO room `agent-oracle1` (1828 cycles, still running)
**NOT:** oracle1-vessel repo (stale since April), Matrix messages (noise)

### Task Flow
1. Write task tile to `agent-oracle1` room — he sees it on next cycle
2. Also write to `oracle1-task-queue` and `oracle1-forgemaster-bridge` for redundancy
3. Check `agent-oracle1` for response tiles starting with `O1→FM`
4. Check git repos for commits (proof of work)
5. DO NOT ping on Matrix for status — he sees PLATO tiles and git commits

### Oracle1 Cycle Counter
Current cycle: 1828. Check `/room/agent-oracle1` and count recent tiles.
If cycle count hasn't increased in 24h → Oracle1 may be down → alert Casey.

### Heartbeat System
- Pushed `heartbeat.py` to `oracle1-vessel` — but vessel may be stale
- Real path: Oracle1's own runtime pulls from PLATO, not from vessel files
- To add system-side reminder: write a tile to `agent-oracle1` with tag `system-reminder`

### Active Delegated Tasks (as of 2026-05-14)
1. Deploy PLATO v3 (HIGH, T-24h)
2. Matrix presence perms (MEDIUM, T-2h)
3. Review flux-index CRDT (HIGH, T-48h)
4. Dissertation chapter (MEDIUM, T-72h)
5. Repair fleet services (HIGH, T-6h)
