# Lighthouse Runtime

Forgemaster's PLATO Agent Room System — orient → relay → gate.

## Architecture

```
┌─────────────────────────────────────────────────┐
│              Lighthouse (Forgemaster)            │
│                                                 │
│  orient(task, type) ──► pick model, create room │
│  relay(room, seeds) ──► seed first, then run    │
│  gate(room, output) ──► safety + alignment check│
│                                                 │
│  state/agents/{room_id}/                        │
│    state.json    ─ agent status + metadata      │
│    tiles/        ─ PLATO tiles (findings)       │
│    bottles/      ─ I2I messages (fleet comms)   │
│    log/          ─ execution logs               │
│    seeds/        ─ seed discovery results       │
└─────────────────────────────────────────────────┘
```

## Model Allocation

| Task Type | Model | Cost/1K | Why |
|-----------|-------|---------|-----|
| synthesis, critique, big_idea | Claude | $50 | Deep thinking, limited daily |
| architecture, complex_code, orchestration | GLM-5.1 | $5 | Strong coder, monthly limit |
| discovery, exploration, variation | Seed-2.0-mini | $0.10 | Cheap, fast, good for iteration |
| drafting, documentation, research | DeepSeek | $0.20 | Token-heavy, cheap |
| adversarial, second_opinion | Hermes-70B | $0.15 | Independent, adversarial |

## CLI Usage

```bash
# Orient — pick model, create room
python3 lighthouse.py orient "Write a README" documentation

# Relay — start agent running (optionally with seed iterations)
python3 lighthouse.py relay <room_id> 50

# Gate — check output for safety
python3 lighthouse.py gate-text <room_id> "output text here"
python3 lighthouse.py gate <room_id> output.txt

# Tile — write a PLATO tile
python3 lighthouse.py tile <room_id> finding "Discovered X"

# Bottle — write I2I message
python3 lighthouse.py bottle <room_id> oracle1 UPDATE message.txt

# List rooms
python3 lighthouse.py list
python3 lighthouse.py list running

# Resource summary
python3 lighthouse.py summary

# Clean completed rooms
python3 lighthouse.py clean complete
```

## OpenClaw Bridge

```bash
# Spawn a subagent (returns model + prompt)
python3 lighthouse_oc.py spawn "Build hex grid" architecture

# Show status
python3 lighthouse_oc.py status
```

## Gate Safety Checks

The gate checks for:
- **Credential leaks** — API keys, tokens, passwords (CRITICAL → REJECT)
- **Overclaims** — "I can access/control everything" (WARNING → FLAG)
- **Dangerous actions** — rm -rf, DROP TABLE (CRITICAL → NEEDS_APPROVAL)

## Files

- `lighthouse.py` — Core orient/relay/gate + room management + CLI
- `lighthouse_oc.py` — OpenClaw subagent bridge
- `state/agents/` — Agent room filesystem (created at runtime)
