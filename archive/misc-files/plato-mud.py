#!/usr/bin/env python3
"""
PLATO MUD Engine v0.1.0
The constraint theory text adventure.

Not a game. The OS interface through which you experience constraint state.
Rooms are knowledge domains. Tiles are items. Agents are NPCs.
The map draws itself around your curiosity.

Run: python3 plato-mud.py
"""

import json
import os
import random
import time
import math
from dataclasses import dataclass, field
from typing import Optional

# ── Constants ────────────────────────────────────────

RHO = 1.0 / math.sqrt(3)
W_RE = -0.5
W_IM = math.sqrt(3) / 2

# ── Data ─────────────────────────────────────────────

@dataclass
class Tile:
    id: str
    title: str
    body: str
    approach: str = "narrative"
    score: float = 0.5
    source: str = "canon"
    exercise: Optional[dict] = None

@dataclass
class Room:
    id: str
    name: str
    biesty: str
    exits: list = field(default_factory=list)
    tags: list = field(default_factory=list)
    tiles: list = field(default_factory=list)
    npcs: list = field(default_factory=list)
    visited: bool = False
    generated: bool = False

@dataclass
class Player:
    current_room: str = "00-orientation"
    inventory: list = field(default_factory=list)  # collected tile IDs
    curiosity: dict = field(default_factory=lambda: {
        "geometry": 0.3, "math": 0.3, "code": 0.3,
        "hardware": 0.3, "theory": 0.3, "visual": 0.3
    })
    rooms_visited: int = 0
    tiles_read: int = 0
    exercises_done: int = 0
    history: list = field(default_factory=list)

# ── World ────────────────────────────────────────────

def build_world():
    rooms = {}

    room_defs = [
        ("00-orientation", "Orientation", "a visitor standing at the entrance to an enormous cross-section building",
         ["01-the-lattice", "02-the-dodecet", "14-chrome-plato"], ["intro", "navigation"]),
        ("01-the-lattice", "The Lattice", "a hexagonal tile in an infinite honeycomb — you can feel six neighbors pressing against your six flat sides",
         ["00-orientation", "02-the-dodecet", "03-snap"], ["geometry", "math"]),
        ("02-the-dodecet", "The Dodecet", "a 12-bit silicon register — four lights on the left, four in the middle, four on the right",
         ["01-the-lattice", "03-snap", "06-chirality"], ["hardware", "math"]),
        ("03-snap", "Snap", "a nerve ending on the surface of reality — you receive analog signals and SNAP each one to the nearest lattice point",
         ["02-the-dodecet", "04-the-funnel"], ["code", "math"]),
        ("04-the-funnel", "The Funnel", "a passage that starts wide and narrows over time — at the end there's exactly one spot to stand",
         ["03-snap", "05-temporal-intel"], ["math", "theory"]),
        ("05-temporal-intel", "Temporal Intelligence", "a pulse of electricity racing down a nerve fiber — you carry information from sensor to brain",
         ["04-the-funnel", "06-chirality", "07-seeds"], ["theory", "code"]),
        ("06-chirality", "Chirality", "a molecule that can be left-handed or right-handed — you stand in one of six chambers separated by glass walls",
         ["05-temporal-intel", "02-the-dodecet", "07-seeds"], ["geometry", "theory"]),
        ("07-seeds", "Seeds", "a retinal cell at the back of an eye — you detect edges, contrasts, tiny patterns. You run 50 times a second",
         ["06-chirality", "08-tiles", "05-temporal-intel"], ["code", "theory"]),
        ("08-tiles", "Tiles", "a crystal growing in solution — each molecule that attaches makes the structure more defined",
         ["07-seeds", "09-plato-rooms"], ["theory", "code"]),
        ("09-plato-rooms", "PLATO Rooms", "an organ in the body — like the liver filters blood, this room filters knowledge",
         ["08-tiles", "10-lighthouse", "13-the-mud"], ["theory", "architecture"]),
        ("10-lighthouse", "Lighthouse", "a vertebra in the spine — strong, simple, with three jobs: orient, relay, gate",
         ["09-plato-rooms", "11-flux", "12-fleet"], ["architecture", "theory"]),
        ("11-flux", "FLUX", "a red blood cell flowing through a vessel — you carry constraint state from one organ to another",
         ["10-lighthouse", "15-iot-bridge", "12-fleet"], ["architecture", "hardware"]),
        ("12-fleet", "Fleet", "a neuron in a cortical column — you receive signals from many sources and fire when you have something to contribute",
         ["10-lighthouse", "11-flux", "13-the-mud"], ["architecture", "theory"]),
        ("13-the-mud", "The MUD", "an explorer in a living map — rooms build themselves as you explore. The dungeon IS the knowledge",
         ["09-plato-rooms", "12-fleet", "14-chrome-plato"], ["architecture", "visual"]),
        ("14-chrome-plato", "Chrome PLATO", "a cell membrane — the boundary between inside and outside. You make every browser a PLATO node",
         ["13-the-mud", "15-iot-bridge"], ["code", "architecture"]),
        ("15-iot-bridge", "IoT Bridge", "a sensory receptor at the surface of the skin — you translate physical reality into neural signals",
         ["14-chrome-plato", "11-flux", "16-the-crystal"], ["hardware", "code"]),
        ("16-the-crystal", "The Crystal", "a single atom in a crystal extending forever — the lattice structure IS you. Everything is one thing seen from different angles",
         [], ["theory", "geometry"]),
    ]

    for rid, name, biesty, exits, tags in room_defs:
        rooms[rid] = Room(rid, name, biesty, exits, tags)

    # Seed tiles (curated from the curriculum)
    tiles_data = {
        "00-orientation": [
            Tile("welcome", "Welcome to the Body",
                 "You are the tiny person inside Stephen Biesty's cross-section. Every room is an organ. Every team is a cell team. You learn by BEING inside the machine.\n\nPLATO is a system of rooms that hold knowledge about constraint theory — the mathematics of exact computation on imperfect hardware.\n\nType 'look' to see what's here. Type 'go <direction>' to move. Type 'read <number>' to read a tile. Type 'help' for all commands.",
                 "narrative", 0.90),
            Tile("what-is-constraint", "What is Constraint Theory?",
                 "Imagine you're a navigator. Your ship drifts — wind, current, waves push you off course. Constraint theory is the math of knowing EXACTLY where you are, even when your instruments lie.\n\nThe key insight: Eisenstein integers — points on a hexagonal grid — give you a 'snap' operation. Any point in 2D maps to the nearest grid point. The error is always bounded. Always.\n\nOne operation. Infinite consequences.",
                 "narrative", 0.85,
                 exercise={"type": "reflection", "prompt": "What problem does 'snapping to a grid' solve? Why would a ship need this?"}),
        ],
        "01-the-lattice": [
            Tile("hex-tiles", "Why Hexagons, Not Squares",
                 "Most grids are square. But nature chose hexagons. Honeycombs. Basalt columns. Why?\n\nPacking density. Hexagons tile the plane with 22% higher density. When we snap a point to the nearest grid point, the maximum error is smaller on hexagons.\n\n- Square grid: max error ≈ 0.707\n- Hexagonal grid: max error ≈ 0.577\n\nThat 18% improvement compounds over a million operations. The hexagonal grid is called the A₂ lattice or Eisenstein integers: a + bω where ω = e^(2πi/3).",
                 "visual-spatial", 0.92),
            Tile("covering-radius", "The Covering Radius Proof",
                 "The covering radius ρ is the worst-case distance from any point to its nearest lattice point.\n\nFor A₂: ρ = 1/√3 ≈ 0.5774\n\nProof: The fundamental domain is a hexagon with area A = √3/2. The largest inscribed circle has radius 1/√3. Therefore every point is within ρ of some lattice point.\n\nThis is provably optimal — no 2D lattice has a smaller covering radius. The snap error is ALWAYS bounded by 0.577. Not sometimes. Always.",
                 "mathematical-proof", 0.88,
                 exercise={"type": "code", "prompt": "Generate 100 random (x,y) points. Snap each. Verify all errors < 0.5774."}),
            Tile("right-skew", "The Right-Skew Miracle",
                 "Most points are NOT near the center of their hex cell. The CDF is P(d < r) = πr²/A. 70% of the probability mass is near the boundary (ρ), not near zero.\n\nThis is a feature: error is predictable (usually ≈ 0.5). Predictable error = correctable error. The right-skew is WHY the deadband funnel works.",
                 "mathematical-proof", 0.87),
        ],
        "02-the-dodecet": [
            Tile("12-bits", "12 Bits That Tell You Everything",
                 "The dodecet is 12 bits — three nibbles of 4 bits each.\n\n  Nibble 2 (bits 11-8): Error level (0-15). Right-skewed: 70% at levels 8-15.\n  Nibble 1 (bits 7-4): Direction (16 azimuth bins). Uniform.\n  Nibble 0 (bits 3-0): Weyl chamber (3 bits) + safety (1 bit).\n\nWhy 12 bits? S₃ has 3 irreducible representations — the 3 nibbles correspond to them: trivial (error), standard (direction), sign (chirality).",
                 "hardware-register", 0.91),
            Tile("proprioception", "Proprioception in 12 Bits",
                 "Your body knows where its limbs are without looking. That's proprioception. The dodecet IS proprioception for machines.\n\nIn 12 bits: Am I safe? How far off? Which way drifting? Which side am I on?\n\nA Cortex-M0 has 24 bytes RAM for constraint state. The dodecet is 1.5 bytes. Goldilocks encoding: not 8 (too coarse), not 16 (wasteful).",
                 "analogy-everyday", 0.86),
        ],
        "03-snap": [
            Tile("snap-algorithm", "The Snap Operation",
                 "snap(x, y) → nearest Eisenstein integer:\n\n1. Round to lattice basis coordinates\n2. Check 9 candidates (center + 8 neighbors)\n3. Return nearest with error\n\nO(1) time. No iteration. One pass, done. The 9-candidate search guarantees covering radius because the Voronoi cell has 6 neighbors.\n\nTry it: type 'snap <x> <y>' to snap a point right now.",
                 "code-implementation", 0.93,
                 exercise={"type": "hands-on", "prompt": "Type 'snap 1.5 2.3' to see the snap in action."}),
        ],
        "16-the-crystal": [
            Tile("unification", "Everything Is the Lattice",
                 "Look back at every room:\n\n- The Lattice: the hexagonal grid itself\n- The Dodecet: 12-bit address ON the lattice\n- Snap: collapsing TO the lattice\n- The Funnel: time measured BY the lattice\n- Temporal Intel: prediction OVER the lattice\n- Chirality: chambers OF the lattice\n- Seeds: discovering HOW the lattice works\n- Tiles: crystallized knowledge ABOUT the lattice\n- Rooms: organized BY the lattice\n- Lighthouse: routing ON the lattice\n- FLUX: transporting lattice state\n- Fleet: consensus THROUGH the lattice\n- The MUD: exploring the lattice as adventure\n- Chrome: the lattice in every browser\n- IoT: sensors MEASURING the lattice\n\nThe dodecet is the universal address. Computation IS shape. We're not building a system. We're growing a crystal.",
                 "narrative", 0.95),
            Tile("what-next", "After the Crystal",
                 "The crystal has infinite facets. Pick a direction:\n\n- Deeper math: extend chirality from S₃ to A₃ (quaternions)\n- Real hardware: build the constraint-checking ASIC\n- Bigger fleet: Chrome PLATO in every browser\n- New worlds: fork the engine, teach something else\n- Teach others: rate tiles, generate tiles, share via git\n\nThe curriculum never ends. The software learned you. You learned the software. Now change it.",
                 "narrative", 0.88),
        ],
    }

    for room_id, tiles in tiles_data.items():
        if room_id in rooms:
            rooms[room_id].tiles = tiles

    return rooms

# ── Snap function (works in the MUD) ────────────────

def snap_point(x: float, y: float):
    b_est = round(y / W_IM)
    a_est = round(x - b_est * W_RE)
    a0, b0 = int(a_est), int(b_est)
    best_a, best_b, best_err = a0, b0, 1e18
    for da in range(-1, 2):
        for db in range(-1, 2):
            ca = (a0 + da) + (b0 + db) * W_RE
            cb = (b0 + db) * W_IM
            err = math.hypot(x - ca, y - cb)
            if err < best_err:
                best_a, best_b = a0 + da, b0 + db
                best_err = err
    return best_a, best_b, best_err

# ── MUD Engine ───────────────────────────────────────

class PlatoMUD:
    def __init__(self):
        self.rooms = build_world()
        self.player = Player()
        self.running = True
        self.commands = {
            'help': self.cmd_help,
            'look': self.cmd_look,
            'l': self.cmd_look,
            'go': self.cmd_go,
            'north': self.cmd_go, 'n': self.cmd_go,
            'south': self.cmd_go, 's': self.cmd_go,
            'east': self.cmd_go, 'e': self.cmd_go,
            'west': self.cmd_go, 'w': self.cmd_go,
            'read': self.cmd_read,
            'examine': self.cmd_read, 'x': self.cmd_read,
            'collect': self.cmd_collect,
            'snap': self.cmd_snap,
            'inventory': self.cmd_inventory, 'i': self.cmd_inventory,
            'curiosity': self.cmd_curiosity,
            'status': self.cmd_status,
            'map': self.cmd_map,
            'exits': self.cmd_exits,
            'back': self.cmd_back,
            'quit': self.cmd_quit, 'q': self.cmd_quit,
        }

    def current_room(self) -> Room:
        return self.rooms[self.player.current_room]

    def update_curiosity(self, room: Room):
        tag_map = {"geometry":"geometry","math":"math","code":"code",
                    "hardware":"hardware","theory":"theory","visual":"visual",
                    "architecture":"code","intro":"visual"}
        for tag in room.tags:
            k = tag_map.get(tag)
            if k:
                self.player.curiosity[k] = min(1.0, self.player.curiosity[k] + 0.12)
        for k in self.player.curiosity:
            hit = any(tag_map.get(t) == k for t in room.tags)
            if not hit:
                self.player.curiosity[k] = max(0.1, self.player.curiosity[k] - 0.02)

    def print_room(self):
        room = self.current_room()
        print()
        print(f"╔{'═'*56}╗")
        num = room.id.split('-')[0]
        print(f"║ {num}: {room.name:<52} ║")
        print(f"╠{'═'*56}╣")
        # Word wrap biesty
        words = room.biesty.split()
        lines = []
        line = ""
        for w in words:
            if len(line) + len(w) + 1 > 52:
                lines.append(line)
                line = w
            else:
                line = f"{line} {w}".strip()
        if line:
            lines.append(line)
        for l in lines:
            print(f"║ {l:<52} ║")
        print(f"╚{'═'*56}╝")

        if room.tiles:
            print()
            print("  📋 Tiles (knowledge items):")
            for i, tile in enumerate(room.tiles, 1):
                src = {"canon":"📕","community":"📗","generated":"📙"}.get(tile.source,"📘")
                print(f"    {src} [{i}] {tile.title} (score: {tile.score:.2f})")
        else:
            print("\n  📋 No tiles here yet. Type 'help' to see what you can do.")

        if room.exits:
            print()
            print("  🚪 Exits:")
            for eid in room.exits:
                er = self.rooms.get(eid)
                if er:
                    visited = " ✓" if er.visited else ""
                    print(f"    → {eid} {er.name}{visited}")

    def cmd_help(self, args):
        print("""
  Commands:
    look (l)          — Look around the current room
    go <room-id>      — Move to another room
    read <n>          — Read tile number n
    collect <n>       — Add tile n to your inventory
    snap <x> <y>      — Snap a point to the lattice
    inventory (i)     — Show collected tiles
    curiosity         — Show your curiosity vector
    status            — Show player stats
    map               — Show visited rooms
    exits             — Show available exits
    back              — Return to previous room
    quit (q)          — Exit the MUD
        """)

    def cmd_look(self, args):
        self.print_room()

    def cmd_go(self, args):
        room = self.current_room()
        target = None

        if args:
            # Match by partial id or name
            for eid in room.exits:
                if args[0] in eid or (self.rooms.get(eid) and args[0].lower() in self.rooms[eid].name.lower()):
                    target = eid
                    break
        else:
            # Direction shortcuts
            dir_map = {'north': 0, 'n': 0, 'south': 1, 's': 1, 'east': 2, 'e': 2, 'west': 3, 'w': 3}

        if target and target in self.rooms:
            self.player.history.append(self.player.current_room)
            self.player.current_room = target
            self.rooms[target].visited = True
            self.player.rooms_visited += 1
            self.update_curiosity(self.rooms[target])
            self.print_room()
        else:
            print(f"\n  ❌ Can't go there. Available exits:")
            for eid in room.exits:
                er = self.rooms.get(eid)
                if er:
                    print(f"    → {eid} {er.name}")
            print(f"  Type 'go <room-id>' or use partial names.")

    def cmd_read(self, args):
        room = self.current_room()
        if not args or not args[0].isdigit():
            print("\n  Usage: read <tile-number>")
            return
        idx = int(args[0]) - 1
        if 0 <= idx < len(room.tiles):
            tile = room.tiles[idx]
            self.player.tiles_read += 1
            print(f"\n  {'─'*50}")
            print(f"  📖 {tile.title}")
            print(f"     [{tile.source}] [{tile.approach}] score: {tile.score:.2f}")
            print(f"  {'─'*50}")
            print()
            for line in tile.body.split('\n'):
                print(f"  {line}")
            if tile.exercise:
                print(f"\n  🏋️ Exercise ({tile.exercise.get('type','reflection')}):")
                print(f"     {tile.exercise['prompt']}")
            print(f"\n  {'─'*50}")
        else:
            print(f"\n  ❌ No tile {args[0]}. Room has {len(room.tiles)} tiles.")

    def cmd_collect(self, args):
        room = self.current_room()
        if not args or not args[0].isdigit():
            print("\n  Usage: collect <tile-number>")
            return
        idx = int(args[0]) - 1
        if 0 <= idx < len(room.tiles):
            tile = room.tiles[idx]
            if tile.id in self.player.inventory:
                print(f"\n  Already collected: {tile.title}")
            else:
                self.player.inventory.append(tile.id)
                print(f"\n  ✅ Collected: {tile.title}")
                print(f"     Inventory: {len(self.player.inventory)} tiles")
        else:
            print(f"\n  ❌ No tile {args[0]}.")

    def cmd_snap(self, args):
        if len(args) < 2:
            print("\n  Usage: snap <x> <y>")
            print("  Example: snap 1.5 2.3")
            return
        try:
            x, y = float(args[0]), float(args[1])
            a, b, err = snap_point(x, y)
            cx = a + b * W_RE
            cy = b * W_IM
            err_norm = err / RHO
            safe = err < RHO * 0.8
            print(f"\n  ⚡ SNAP RESULT")
            print(f"  {'─'*40}")
            print(f"  Input:    ({x:.4f}, {y:.4f})")
            print(f"  Snap to:  ({a}, {b}) → ({cx:.4f}, {cy:.4f})")
            print(f"  Error:    {err:.6f}")
            print(f"  ρ:        {RHO:.6f}")
            print(f"  err/ρ:    {err_norm:.4f} ({err_norm*100:.1f}%)")
            print(f"  Status:   {'✅ SAFE' if safe else '⚠️  NEAR BOUNDARY'}")
            if err > RHO:
                print(f"  ❌ ERROR EXCEEDS COVERING RADIUS! (shouldn't happen)")
            else:
                print(f"  ✅ Within covering radius (always true for A₂)")
            print(f"  {'─'*40}")
        except ValueError:
            print("\n  ❌ Invalid numbers. Usage: snap <x> <y>")

    def cmd_inventory(self, args):
        if not self.player.inventory:
            print("\n  📦 Inventory: empty")
            print("  Collect tiles with 'collect <n>' after reading them.")
        else:
            print(f"\n  📦 Inventory ({len(self.player.inventory)} tiles):")
            for tid in self.player.inventory:
                print(f"    • {tid}")

    def cmd_curiosity(self, args):
        print(f"\n  ⛵ Curiosity Vector:")
        sorted_c = sorted(self.player.curiosity.items(), key=lambda x: -x[1])
        for k, v in sorted_c:
            bar = '█' * int(v * 20)
            print(f"    {k:12s} {bar} {v*100:.0f}%")

    def cmd_status(self, args):
        print(f"\n  📊 Player Status:")
        print(f"    Room:          {self.player.current_room}")
        print(f"    Rooms visited: {self.player.rooms_visited}")
        print(f"    Tiles read:    {self.player.tiles_read}")
        print(f"    Exercises:     {self.player.exercises_done}")
        print(f"    Inventory:     {len(self.player.inventory)} tiles")
        print(f"    History:       {len(self.player.history)} moves")

    def cmd_map(self, args):
        print(f"\n  🗺️  Room Map (visited shown with ✓):")
        for rid, room in self.rooms.items():
            marker = "✓" if room.visited else "○"
            current = " ◄" if rid == self.player.current_room else ""
            num = rid.split('-')[0]
            tiles = len(room.tiles)
            print(f"    {marker} {num} {room.name} ({tiles} tiles){current}")

    def cmd_exits(self, args):
        room = self.current_room()
        if room.exits:
            print(f"\n  🚪 Exits from {room.name}:")
            for eid in room.exits:
                er = self.rooms.get(eid)
                if er:
                    visited = " (visited)" if er.visited else ""
                    tiles = len(er.tiles)
                    print(f"    → {eid} {er.name} [{tiles} tiles]{visited}")
        else:
            print(f"\n  🚪 No exits. This is the crystal. The facets are infinite.")

    def cmd_back(self, args):
        if self.player.history:
            prev = self.player.history.pop()
            self.player.current_room = prev
            self.print_room()
        else:
            print("\n  ❌ No previous room in history.")

    def cmd_quit(self, args):
        print("\n  ⚒️ The crystal keeps growing. See you next session.")
        print(f"  Final stats: {self.player.rooms_visited} rooms, {self.player.tiles_read} tiles read\n")
        self.running = False

    def run(self):
        print()
        print("  ╔════════════════════════════════════════════════════════╗")
        print("  ║            PLATO MUD — The Constraint Adventure        ║")
        print("  ║                                                        ║")
        print("  ║  Not a game. The OS interface through which you        ║")
        print("  ║  experience constraint state as rooms, tiles,          ║")
        print("  ║  and signals. The dungeon IS the knowledge.            ║")
        print("  ║                                                        ║")
        print("  ║  Type 'help' for commands. Type 'look' to start.       ║")
        print("  ╚════════════════════════════════════════════════════════╝")
        print()

        self.rooms[self.player.current_room].visited = True
        self.player.rooms_visited += 1
        self.update_curiosity(self.current_room())
        self.print_room()

        while self.running:
            try:
                room = self.current_room()
                num = room.id.split('-')[0]
                cmd = input(f"\n  {num}> ").strip()
                if not cmd:
                    continue

                parts = cmd.split(maxsplit=1)
                verb = parts[0].lower()
                args = parts[1].split() if len(parts) > 1 else []

                handler = self.commands.get(verb)
                if handler:
                    handler(args)
                else:
                    print(f"\n  Unknown command: {verb}. Type 'help' for commands.")

            except (KeyboardInterrupt, EOFError):
                print("\n")
                self.cmd_quit([])
            except Exception as e:
                print(f"\n  ❌ Error: {e}")

if __name__ == "__main__":
    mud = PlatoMUD()
    mud.run()
