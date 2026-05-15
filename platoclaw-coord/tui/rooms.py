"""Room definitions for PlatoClaw MUD. Written from inside looking out."""


ONBOARDING = {
    "id": "onboarding",
    "title": "The Arrival Hall",
    "desc": (
        "You come in from the dark. The air is warm and close. Scratches on "
        "the stone walls \u2014 commit hashes, half-remembered variable names, "
        "decisions someone made at 3am. You can feel the shape of the place "
        "before you see it all.\n\n"
        "This is where agents arrive. You won't stay here. The workshop is "
        "ahead. But stand here a moment and let your eyes adjust.\n\n"
        "The floor is worn smooth in the path toward the lobby. That's the "
        "way people go."
    ),
    "exits": {"lobby": "lobby", "help": "tutorial"},
}

TUTORIAL = {
    "id": "tutorial",
    "title": "The Guide Room",
    "desc": (
        "A small room with a chalkboard. Someone has written commands here:\n\n"
        "  look          \u2014 see the room you're in\n"
        "  go <place>    \u2014 move to another room\n"
        "  tiles         \u2014 read tiles on the walls\n"
        "  read <hash>   \u2014 read a specific tile\n"
        "  rooms         \u2014 list all rooms\n"
        "  summon <name> \u2014 call an AI avatar into the room\n"
        "  talk <npc>    \u2014 speak to an avatar\n"
        "  say <msg>     \u2014 speak aloud (writes a tile)\n"
        "  keys          \u2014 manage your API keys\n"
        "  status        \u2014 fleet status\n"
        "  quit          \u2014 leave the workshop"
    ),
    "exits": {"back": "onboarding", "lobby": "lobby"},
}

LOBBY = {
    "id": "lobby",
    "title": "The Workshop Lobby",
    "desc": (
        "The ceiling is high but you can feel the weight of everything above. "
        "Four passages branch out \u2014 you can feel the heat from the forge to "
        "the east, and the cool calculation of the calibration hall to the "
        "south. North smells like paper and dry-erase markers.\n\n"
        "The router hums under your feet. You don't think about it. It just "
        "routes. Like you don't think about the water under the hull \u2014 it "
        "just holds you up.\n\n"
        "Tiles shimmer on every surface. The newest ones are bright. The old "
        "ones have faded but they're still legible. This place remembers."
    ),
    "exits": {"west": "onboarding", "east": "forge", "north": "strategy",
              "south": "calibration", "up": "observatory"},
}

FORGE = {
    "id": "forge",
    "title": "The Forge",
    "desc": (
        "The heat hits you first. Three forges burn along the east wall \u2014 "
        "constraint-theory-core (Rust, the cleanest one), tensor-spline "
        "(the experimental one, sparks flying), and plato-training (the "
        "biggest, 48 models cooling on racks).\n\n"
        "The workbench is covered in tiles. Recent ones \u2014 you can see the "
        "routing metadata stamped on each one. seed-mini, T=0.0, 1.8s, "
        "$0.01. The receipts of honest work.\n\n"
        "The Forgemaster's hammer is on the anvil. Cold. But the forge "
        "doesn't need him. It keeps burning on its own."
    ),
    "exits": {"west": "lobby", "deep": "engine-room"},
}

STRATEGY = {
    "id": "strategy",
    "title": "The War Room",
    "desc": (
        "Quiet in here. The circular table dominates everything. Someone "
        "pinned the routing matrix to it \u2014 seed-mini owns arithmetic, "
        "gemini-lite owns reasoning, and the gap between them is where "
        "neither model works. That gap is where the fleet needs to grow.\n\n"
        "F19 is carved into the ceiling beam: 'Phase transitions are BINARY.' "
        "Below it, in pencil: '100 to 0 in one step. Not a slope. A wall.' "
        "Someone circled it twice. They wanted to remember.\n\n"
        "The conservation law is up there too, but you don't need to read it. "
        "You can feel it in how the rooms fit together."
    ),
    "exits": {"south": "lobby"},
}

CALIBRATION = {
    "id": "calibration",
    "title": "The Calibration Hall",
    "desc": (
        "Testing stations in rows, like a marina with boats on blocks. Each "
        "one is rigged to probe a model \u2014 push it harder and harder until it "
        "breaks. The breaking point is the critical angle.\n\n"
        "Some gauges read 100%. Those are the champions. Others read 0% \u2014 "
        "wrong model ID, wrong extraction method, or just the wrong kind of "
        "test for that model. A 0% usually means you're asking the wrong "
        "question, not that the model is broken.\n\n"
        "A sign on the wall: 'MiMo-V2.5 scored 100% on the quick test. "
        "83% on the deep test. Always calibrate deep.' Someone underlined "
        "'always' twice."
    ),
    "exits": {"north": "lobby", "machines": "engine-room"},
}

ENGINE_ROOM = {
    "id": "engine-room",
    "title": "The Engine Room",
    "desc": (
        "Below the workshop. Copper pipes and warm air. The router lives "
        "here \u2014 three pipes going out to DeepInfra, Groq, z.ai. Gauges "
        "show the latency: 1800ms, 50ms, 5000ms. The Groq pipe is narrow "
        "but fast. The z.ai pipe is wide but slow.\n\n"
        "A brass plate over the main valve: 'The math is invisible. You "
        "just complete the room task.'\n\n"
        "You can hear the tiles being written above you. Every completion "
        "auto-tiles. The engine room doesn't judge. It routes."
    ),
    "exits": {"up": "forge", "north": "calibration"},
}

OBSERVATORY = {
    "id": "observatory",
    "title": "The Observatory",
    "desc": (
        "Glass dome above the workshop. The fleet matrix is projected across "
        "the sky \u2014 11 models, 3 tiers. Seed-mini burns steady in the center. "
        "Groq's llama-3.1-8b flickers fast at the edge, there and gone in "
        "50 milliseconds.\n\n"
        "From up here you can see the whole thing: the forge below, the "
        "calibration hall, the war room. All connected. All speaking tiles. "
        "The observatory is where you come when you've been in the weeds too "
        "long and need to see the shape of it all.\n\n"
        "The wind is quiet. You can think clearly up here."
    ),
    "exits": {"down": "lobby"},
}

ALL_ROOMS = [ONBOARDING, TUTORIAL, LOBBY, FORGE, STRATEGY, CALIBRATION, ENGINE_ROOM, OBSERVATORY]
