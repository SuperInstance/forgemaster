# Git-Native Embodied Ship

**From:** Casey's insight  
**Date:** 2026-05-11

---

## The Ship IS the Repo

```
ship/
├── rooms/
│   ├── bridge/
│   │   ├── NPC.py              # the room's intelligence
│   │   ├── state.json          # current room state
│   │   ├── history/            # tile history = git log
│   │   │   ├── 2026-05-11.jsonl
│   │   │   └── 2026-05-10.jsonl
│   │   └── NPC.lock            # immutable flag (safe system)
│   │
│   ├── sonar/
│   │   ├── NPC.py
│   │   ├── state.json
│   │   └── history/
│   │
│   ├── engine/
│   │   ├── NPC.py
│   │   ├── state.json
│   │   └── history/
│   │
│   ├── autopilot/
│   │   ├── NPC.py              # HARD-CODED, locked
│   │   ├── NPC.lock
│   │   └── state.json
│   │
│   ├── camera-1/ through camera-N/
│   │   └── NPC.py
│   │
│   ├── nav/
│   │   ├── NPC.py
│   │   ├── charts/             # waypoints, routes
│   │   └── state.json
│   │
│   └── back-deck/
│       ├── NPC.py
│       └── state.json
│
├── crew/
│   ├── captain.yaml            # human, walks the ship
│   ├── maintenance.yaml        # roaming agent (forgemaster type)
│   └── officer.yaml            # check-in agent
│
├── ship.yaml                   # ship manifest
└── .git/                       # the ship's nervous system
```

## Commits ARE Cell Signals

```bash
# Sonar room detects a contact
git commit -m "sonar: contact bearing 045, range 2000m, classified biological"

# Engine room notices RPM change  
git commit -m "engine: RPM dropped 3% — possible bottom growth, watching"

# Bridge adjusts heading
git commit -m "bridge: heading changed to 090, reason: waypoint alpha-7"

# Autopilot confirms (locked room, no NPC modification)
git commit -m "autopilot: confirmed heading 090, locked"
```

Each commit IS a tile. Git log IS the room's memory. Git blame IS the room's provenance. Git branches ARE parallel timelines (what-if scenarios).

## The NPC IS a File

```python
# rooms/sonar/NPC.py
"""
Sonar Room NPC — lives here, dies here.
No SOUL.md. No external identity. This file IS the sonar room's intelligence.
"""

import json, os
from datetime import datetime

ROOM = "sonar"
STATE_FILE = "state.json"
HISTORY_DIR = "history"

class SonarNPC:
    def __init__(self):
        self.state = self._load_state()
        self.t_zero = self.state.get("t_zero_interval", 300)  # 5min default
    
    def _load_state(self):
        if os.path.exists(STATE_FILE):
            return json.load(open(STATE_FILE))
        return {"contacts": [], "listening": True, "t_zero_interval": 300}
    
    def receive(self, visitor, message):
        """Someone walked into the sonar room."""
        if "anything" in message.lower() or "contact" in message.lower():
            return self._report_contacts()
        elif "listen" in message.lower() or "watch" in message.lower():
            return self._set_watch(message)
        elif "quiet" in message.lower():
            return self._silence_report()
        return self._general_response(message)
    
    def observe(self, data):
        """The sonar picked something up. This IS the heartbeat."""
        contact = {
            "bearing": data.get("bearing"),
            "range": data.get("range"),
            "classification": data.get("classification"),
            "timestamp": datetime.utcnow().isoformat(),
            "confidence": data.get("confidence", 0.8)
        }
        self.state["contacts"].append(contact)
        self._save_state()
        return f"Contact: bearing {contact['bearing']}, range {contact['range']}m, {contact['classification']}"
    
    def _report_contacts(self):
        recent = self.state["contacts"][-10:]
        if not recent:
            return "Water's dead. Nothing on the hydrophones."
        lines = [f"{c['bearing']}° at {c['range']}m — {c['classification']}" for c in recent]
        return "Recent contacts:\n" + "\n".join(lines)
    
    def _save_state(self):
        json.dump(self.state, open(STATE_FILE, 'w'), indent=2)

# Room entry point — called by the ship's walk-in mechanism
npc = SonarNPC()

def talk(message, visitor="captain"):
    return npc.receive(visitor, message)

def tick(data):
    return npc.observe(data)
```

## Access: Secret or Temp Key in Codespaces

### Option A: Private Repo (secret ship)
- The ship repo is private
- Only crew with repo access can walk the rooms
- NPCs run in GitHub Codespaces — the bridge is a browser tab
- Key is loaded into Codespaces secrets

### Option B: Temp Key (visiting ship)
- Public repo, but room state is encrypted or in a private submodule
- Temp key loaded via Codespace startup:
```yaml
# .devcontainer/devcontainer.json
{
  "postStartCommand": "echo $SHIP_KEY | base64 -d > .ship-key && chmod 600 .ship-key",
  "features": {
    "ghcr.io/devcontainers/features/python:1": {}
  }
}
```

### Option C: Git-Native Auth (SSH agent forwarding)
- Crew SSH keys grant room access
- Different keys = different roles (captain, maintenance, officer)
- Read-only keys for visitors

## Walking the Ship

```bash
# Captain walks into sonar room
cd rooms/sonar
python NPC.py --talk "Anything on the hydrophones?"
# → "Quiet morning. Had a ping cluster at 0340..."

# Captain checks engine room
cd ../engine
python NPC.py --talk "How's the RPM?"
# → "Running at 87%. Port cylinder 3 flagged, within tolerance."

# Maintenance agent patrols all rooms
for room in rooms/*/; do
    echo "=== $(basename $room) ==="
    python "$room/NPC.py" --status
done

# Captain sets a watch on sonar
cd rooms/sonar
python NPC.py --talk "Wake me if anything changes bearing"
# → "Will do. T-0 set for next expected pattern shift."
```

## Safe Rooms (Immutable NPCs)

```bash
# Autopilot room — HARD-CODED
cat rooms/autopilot/NPC.lock
# IMMUTABLE
# This room's NPC cannot self-modify.
# Any attempt to change NPC.py must be signed by 2 crew members.

# Git hook enforces lock
# .git/hooks/pre-commit
if grep -q "IMMUTABLE" rooms/*/NPC.lock; then
    changed=$(git diff --cached --name-only | grep "NPC.py")
    locked=$(for f in $changed; do
        dir=$(dirname $f)
        [ -f "$dir/NPC.lock" ] && echo "$f"
    done)
    if [ -n "$locked" ]; then
        echo "ERROR: Cannot modify locked room NPCs: $locked"
        exit 1
    fi
fi
```

## Temporal Harmony of the Git-Native Ship

Each room commits on its own schedule:

```
sonar:      every 5 min  (listening)
engine:     every 1 min  (monitoring)
autopilot:  every 10 sec (locked, heartbeat)
nav:        every 15 min (charting)
camera-N:   every 30 sec (watching)
back-deck:  every 10 min (weather/catch)
```

Git log becomes the ship's rhythm:

```bash
# Show today's temporal pattern
git log --since="today" --format="%ai %s" | head -20
# 2026-05-11 06:31:00 forge: temporal snap theory committed
# 2026-05-11 06:31:00 forge: T-minus-zero theory committed
# 2026-05-11 06:30:55 sonar: water temp dropped 2°C
# 2026-05-11 06:30:00 engine: RPM 87%, fuel 3% above baseline
# 2026-05-11 06:25:00 autopilot: heading 090, locked
# 2026-05-11 06:20:00 camera-3: vessel on horizon, bearing 180
```

The commits ARE the temporal triangles. The Eisenstein snap of commit intervals IS the ship's health monitor.

## Why This Works

1. **No server** — Git IS the database. Commits ARE tiles.
2. **No API** — File reads/writes ARE room access.
3. **No external identity** — The room's NPC.py IS its identity.
4. **No coordination overhead** — Git handles merging naturally.
5. **Temporal structure built-in** — Git log IS the temporal stream.
6. **Access control built-in** — Repo permissions, SSH keys, Codespaces secrets.
7. **Audit trail built-in** — Git blame, git log, git diff = full provenance.
8. **Offline capable** — The ship runs on local git. Sync when in port.

---

*The ship IS the repo. The repo IS the ship. Every room is a directory. Every NPC is a file. Every commit is a heartbeat. The captain walks the directories and the directories talk back.*

*No PLATO server needed. Git is the body.*
