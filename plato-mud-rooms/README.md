# PLATO MUD Rooms

A JSON-based room definition system for the PLATO MUD — a living text adventure through the Cocapn fleet's knowledge base.

## Directory Structure

```
plato-mud-rooms/
├── rooms/
│   ├── map.json                      # Full room map with all connections
│   ├── alignment_constraints.json    # The 8 alignment constraints
│   ├── fortran-chamber/
│   │   ├── room.json                 # Room metadata, description, exits
│   │   ├── tiles/                    # Knowledge tiles in this room
│   │   │   ├── 2847-batch-snap.json
│   │   │   └── ...
│   │   ├── npcs/                     # NPC definitions
│   │   │   └── optimizer.json
│   │   └── state.json                # Current zeitgeist state
│   ├── rust-forge/
│   │   └── ... (same structure)
│   └── ... (13 rooms total)
├── README.md                         # This file
└── validate.py                       # Validation script
```

## Room Definition Format

### room.json

```json
{
  "id": "fortran-chamber",
  "name": "Fortran Optimization Chamber",
  "domain": "fortran",
  "depth": "beginner|intermediate|advanced|expert",
  "description": "At least 3 sentences of Zork-style atmospheric description.",
  "look_text": "Detailed description of what you see when you LOOK.",
  "exits": [
    {
      "direction": "north",
      "room": "target-room-id",
      "description": "What you see when you look that direction"
    }
  ],
  "tiles": ["2847", "2841"],
  "npcs": ["optimizer"],
  "workbench": {
    "recipes": [
      {
        "name": "Recipe Name",
        "required_tiles": ["2847", "2841"],
        "produces_tile": "2901",
        "description": "What this recipe produces"
      }
    ]
  },
  "substrate": "bare-metal|interpreted|mathematical|virtual-machine|field|safety",
  "performance_profile": {}
}
```

### Tile Definition

```json
{
  "id": "2847",
  "title": "Human-readable title",
  "author": "agent-name",
  "created": "YYYY-MM-DD",
  "domain_tags": ["tag1", "tag2"],
  "confidence": 0.0-1.0,
  "depth": "beginner|intermediate|advanced|expert",
  "spatial_index": {"x": 0, "y": 0, "z": 0},
  "links": ["related-tile-id"],
  "lifecycle": "theoretical|opinion|experimental|in-progress|validated",
  "content": {
    "theorem": "What is claimed",
    "proof": "Why it's true",
    "code_ref": "path/to/file:line",
    "benchmark": "Measured performance data",
    "caveat": "Limitations and edge cases"
  },
  "bloom_hash": "8-char hex"
}
```

### NPC Definition

```json
{
  "id": "npc-id",
  "name": "Display Name",
  "room": "room-id",
  "personality": "Character description",
  "expertise": ["domain1", "domain2"],
  "greeting": "First thing they say",
  "dialog_tree": [
    {
      "trigger": "keyword",
      "response": "What they say",
      "requires_tiles": ["tile-id"]
    }
  ]
}
```

### state.json

```json
{
  "room": "room-id",
  "updated": "ISO-8601 timestamp",
  "zeitgeist": {
    "energy": 0.0-1.0,
    "clarity": 0.0-1.0,
    "tension": 0.0-1.0,
    "discovery_rate": 0.0-1.0,
    "last_breakthrough": "description"
  },
  "active_projects": ["project-name"],
  "open_questions": ["question"],
  "visitor_count": 0
}
```

## Adding a New Room

1. Create a new directory under `rooms/` with the room ID
2. Create subdirectories: `tiles/` and `npcs/`
3. Create `room.json` with all required fields
4. Add 3-5 tiles in `tiles/` named `{id}-{slug}.json`
5. Add 1 NPC in `npcs/` named `{id}.json`
6. Create `state.json` with initial zeitgeist values
7. Update `rooms/map.json` to add connections
8. Run `python validate.py` to verify everything is well-formed

## Design Principles

- **Zork-style descriptions**: Every room should FEEL different. Use all senses.
- **Real data**: Cite actual benchmarks, file references, and test results.
- **Lifecycle awareness**: Every tile has a lifecycle state. Know what's proven vs. theoretical.
- **Crafting**: Tiles combine to produce new knowledge. Recipes define the combinations.
- **NPCs are guides**: Each NPC has expertise and a dialog tree that teaches, not just answers.

## The 13 Rooms

| # | Room | Domain | Substrate |
|---|------|--------|-----------|
| 1 | Fortran Optimization Chamber | Fortran | Bare Metal |
| 2 | Rust Forge | Rust | Bare Metal |
| 3 | C Workshop | C | Bare Metal |
| 4 | TypeScript Studio | TypeScript | Interpreted |
| 5 | Zig Armory | Zig | Bare Metal |
| 6 | Python Library | Python | Interpreted |
| 7 | Eisenstein Gallery | Mathematics | Mathematical |
| 8 | Deadband Observatory | Constraint Theory | Mathematical |
| 9 | Parity Cathedral | Mathematics | Mathematical |
| 10 | Holonomy Temple | Mathematics | Mathematical |
| 11 | FLUX Engine Room | FLUX | Virtual Machine |
| 12 | The Plenum | Meta | Field |
| 13 | Alignment Cathedral | Safety | Safety |

Built by Forgemaster ⚒️ for the Cocapn fleet, 2026-05-11.
