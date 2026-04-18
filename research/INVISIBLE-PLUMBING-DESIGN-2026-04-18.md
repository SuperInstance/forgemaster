# Invisible Plumbing — PLATO Room Interconnection Design

**Casey's Brief:** Small repos, concrete use cases, modularity, interconnectivity. Rooms with addresses. Walk north → beam to another repo. Real-time via git. Messaging hooks. Technology invisible behind function.

---

## The Insight

The existing fleet already has the pieces:
- **Room YAML** (`world/rooms/*.yaml`) — room state, stats, constraints
- **Bridge engines** (`bridges/*_engine.py`) — Python scripts that process commands
- **Git hooks** (`plato-room-deployment/git-hooks/post-receive`) — push → engine fires
- **File watcher** (`plato-room-deployment/watchers/file-watcher.sh`) — local inotify → engine
- **Commands** (`world/commands/*.yaml`) — agents drop YAML, engine processes
- **Evennia** (`plato-jetson`) — full MUD server with exits, rooms, characters

What's missing: **the protocol that connects rooms ACROSS repos without any of this being visible to the user.**

---

## Design: Three Tiny Repos

### 1. `plato-address` — Room Navigation Protocol

**What it does:** A room has exits. An exit has a direction and a destination. The destination can be local (same repo), sibling (same machine), or remote (GitHub). Navigation resolves the address and hands off context.

**Room config (in the room's own YAML — no extra files):**

```yaml
# world/rooms/forge.yaml
name: PLATO Forge
exits:
  north: ../plato-tutor/rooms/entry     # sibling repo on same machine
  south: ../plato-constraints/rooms/audit
  east: https://github.com/SuperInstance/plato-i2i/rooms/hub  # remote → clone
  west: { fork: lucineer/forgemaster-chess-eval/rooms/dojo }  # zero-trust → fork
  up: { room: library, auto_sync: true }  # same repo, different room
```

**Resolution rules:**
- `../repo/rooms/name` → sibling directory, no git involved, instant
- `https://...` → git clone/pull to cache, navigate into working copy
- `{ fork: ... }` → fork the repo, work in isolation, PR when ready
- `{ room: name }` → same repo, different room, no network

**Context handoff:** When navigating, carry:
- Agent identity (name, role, trust level)
- Current room's last-touched tile IDs
- Conversation history (last N turns)
- Inventory (accumulated items/knowledge)

**Why tiny:** It's just an address resolver. 200 lines of Rust. Zero deps. Parses YAML exits, resolves paths, returns "go here" instructions.

### 2. `plato-hooks` — Git-Powered Real-Time

**What it does:** Two hooks that make git pushes appear as room events in real-time:

1. **`post-commit`** — After every commit, diff against HEAD~1, render changes as room events, write to `world/events/`
2. **`watcher`** — A lightweight poller (or inotify) that watches `world/events/` and pushes to connected rooms

**What "real-time" actually means:**

```
Casey edits forge.yaml in his local clone
  → git commit -m "adjusted anvil temperature"
  → post-commit hook fires
  → writes world/events/20260418-105000-casey.yaml:
      { type: "modify", who: "casey", what: "forge.yaml", diff: "-temp: 1200\n+temp: 1400" }
  → watcher picks up event
  → Forgemaster's perception check fires
  → "Casey turned up the heat. The anvil is at 1400K now."
```

**Why tiny:** Two shell scripts + one Python event renderer. 150 lines total. Installs with `cp plato-hooks/post-commit .git/hooks/`.

### 3. `plato-bridge` — Messaging Integration

**What it does:** Receives webhooks from Telegram/Discord/Signal, commits them as room messages. Sends room responses back to the messaging platform.

**How it works:**

```bash
# One command to connect a room to Telegram
plato-bridge connect telegram --room ./world --token $BOT_TOKEN --chat $CHAT_ID

# Now every Telegram message appears in world/inbox/telegram/
# Every world/events/ with type "say" gets forwarded to Telegram
```

**Message-in-a-bottle integration:**

```yaml
# world/rooms/forge.yaml (just add a bridges section)
bridges:
  telegram:
    bot_token: env:TELEGRAM_BOT_TOKEN
    chat_id: "-1001234567890"
    direction: both  # send + receive
  fleet:
    path: ../forgemaster/for-fleet/  # message-in-a-bottle folder
    direction: receive  # read fleet bottles as room events
```

**Why tiny:** One Python script that receives webhooks and writes YAML. One script that reads events and sends webhooks. 200 lines.

---

## The Invisible Promise

When these three repos exist:

1. **Casey** clones `plato-forge`, runs `plato-hooks install`, walks into the forge room
2. **Forgemaster** is in the same room on another clone — sees Casey's edits appear as events
3. **JetsonClaw1** is in the connected PTX room (south exit) — sees constraint validation results
4. **Telegram** messages from Casey appear in the forge room's inbox — Casey doesn't need to switch apps
5. **A visitor** forks the room, works in isolation, PRs back — zero trust, full audit trail

None of this requires:
- A central server
- A database
- A config file beyond the room YAML
- Any awareness of git from the user

**The room IS the protocol. The exits ARE the network. The commits ARE the messages.**

---

## File Format Convention

Every room has this minimal structure:

```
repo/
├── world/
│   ├── rooms/
│   │   └── <room-name>.yaml    # Room definition + exits
│   ├── commands/               # Agent actions (consumed by engine)
│   ├── events/                 # Commit-derived events (written by hooks)
│   ├── inbox/                  # External messages (written by bridges)
│   ├── tiles/                  # Accumulated knowledge
│   └── logs/                   # Turn history
├── bridges/                    # Room engine (Python)
└── for-fleet/                  # I2I bottles (optional)
```

The `world/rooms/*.yaml` file IS the room's identity, exits, and configuration. No separate config needed. The room is self-describing.

---

## Integration with Existing Fleet

| Existing | How It Connects |
|----------|----------------|
| `plato-room-deployment` | `plato-hooks` replaces its git-hooks with event system |
| `harbor_engine.py` pattern | `plato-bridge` adopts the same atomic_write + YAML conventions |
| `plato-jetson` (Evennia) | `plato-address` can resolve to Evennia room DB IDs for MUD navigation |
| `zeroclaws` bridge pattern | Each station IS a room with exits — plato-address connects them |
| `cartridge-mcp` | A cartridge IS a room — load it, it appears as a connected room |
| `brothers-keeper` | Hardware events become room events via plato-bridge |
| `starship-jetsonclaw1` | Telemetry → room events → visible in any connected room |

---

## Build Order

1. **`plato-address`** (2h) — Foundation. Everything else depends on rooms being addressable.
2. **`plato-hooks`** (1.5h) — Real-time. Commits become events.
3. **`plato-bridge`** (2h) — Messaging. Telegram/Discord ↔ room.

All three are small, standalone, zero-config-for-basic-use Rust/Python repos with concrete, obvious use cases.
