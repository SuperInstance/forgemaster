#!/usr/bin/env python3
"""
platoclaw/tui/mud.py — The MUD. Walk through your project in rooms.

Launch: platoclaw tui

Rooms are PLATO rooms. Tiles are the world state. NPCs are AI avatars
you summon with API keys. The whole thing works algorithmically — no
model needed to explore, just to talk to NPCs.

Low-end hardware OK. Pure Python stdlib. Zero external deps.
"""

import os, sys, json, time, hashlib, re, textwrap
from collections import defaultdict

# ─── ANSI Colors (works on any terminal) ─────────────────────────────────────

class C:
    """Terminal colors. Disabled if not a TTY."""
    ON = sys.stdout.isatty()
    
    @staticmethod
    def _c(code, text):
        if not C.ON: return str(text)
        return f"\033[{code}m{text}\033[0m"
    
    def bold(t):    return C._c("1", t)
    def dim(t):     return C._c("2", t)
    def red(t):     return C._c("31", t)
    def green(t):   return C._c("32", t)
    def yellow(t):  return C._c("33", t)
    def blue(t):    return C._c("34", t)
    def magenta(t): return C._c("35", t)
    def cyan(t):    return C._c("36", t)
    def white(t):   return C._c("37", t)
    def bg_blue(t): return C._c("44", t)


# ─── Fuzzy Matching (forgiving spelling) ──────────────────────────────────────

def fuzzy_match(input_str, options, threshold=0.5):
    """Find the best fuzzy match. Handles typos, abbreviations, partial."""
    if not input_str or not options:
        return None
    
    inp = input_str.lower().strip()
    
    # Exact match
    for opt in options:
        if inp == opt.lower():
            return opt
    
    # Prefix match
    for opt in options:
        if opt.lower().startswith(inp) or inp.startswith(opt.lower()):
            return opt
    
    # Contains match
    for opt in options:
        if inp in opt.lower() or opt.lower() in inp:
            return opt
    
    # Levenshtein-ish distance
    def similarity(a, b):
        a, b = a.lower(), b.lower()
        if len(a) == 0 or len(b) == 0: return 0
        # Simple: count matching characters in order
        matches = 0
        bi = 0
        for ch in a:
            if bi < len(b) and ch == b[bi]:
                matches += 1
                bi += 1
        return matches / max(len(a), len(b))
    
    best = None
    best_score = 0
    for opt in options:
        score = similarity(inp, opt)
        if score > best_score and score >= threshold:
            best_score = score
            best = opt
    
    return best


# ─── World State ──────────────────────────────────────────────────────────────

class Tile:
    """A PLATO tile as a world object."""
    def __init__(self, data):
        self.data = data
        self.hash = data.get("_hash", hashlib.md5(
            json.dumps(data, sort_keys=True).encode()).hexdigest()[:8])
        self.question = data.get("question", "")
        self.answer = data.get("answer", "")
        self.agent = data.get("agent", data.get("source", ""))
        self.domain = data.get("domain", "")
        self.tile_type = data.get("tile_type", "knowledge")
        self.timestamp = data.get("_ts", data.get("timestamp", 0))
    
    def brief(self):
        return f"{self.agent}: {self.question[:50]}"
    
    def full(self):
        lines = [
            C.bold(f"  ╔═ Tile {self.hash} ═╗"),
            f"  ║ {C.cyan('Agent:')}   {self.agent}",
            f"  ║ {C.cyan('Domain:')}  {self.domain}",
            f"  ║ {C.cyan('Type:')}    {self.tile_type}",
            f"  ║ {C.cyan('Topic:')}   {self.question[:70]}",
            f"  ║ {C.cyan('Content:')}",
        ]
        for line in textwrap.wrap(self.answer[:300], width=65):
            lines.append(f"  ║   {line}")
        lines.append(f"  ╚{'═'*30}╝")
        return "\n".join(lines)


class Room:
    """A PLATO room as a navigable space."""
    def __init__(self, room_id, title, description, exits=None):
        self.id = room_id
        self.title = title
        self.description = description
        self.exits = exits or {}  # direction → room_id
        self.tiles = []
        self.npcs = []  # summoned avatars
        self.items = []  # interactive objects
    
    def describe(self):
        lines = [
            "",
            C.bold(C.bg_blue(f"  ══ {self.title} ══  ")),
            "",
        ]
        for line in textwrap.wrap(self.description, width=70):
            lines.append(f"  {line}")
        
        if self.exits:
            lines.append("")
            exits_str = "  ".join(
                f"{C.green(k.title())}" for k in self.exits.keys()
            )
            lines.append(f"  Exits: {exits_str}")
        
        if self.npcs:
            lines.append("")
            for npc in self.npcs:
                lines.append(f"  {C.yellow('⟐')} {C.yellow(npc['name'])} is here. {npc.get('desc','')}")
        
        if self.tiles:
            lines.append(f"  {C.dim(f'[{len(self.tiles)} tiles on the walls]')}")
        
        if self.items:
            lines.append("")
            for item in self.items:
                lines.append(f"  {C.cyan('◆')} {item['name']} — {item.get('desc','')}")
        
        lines.append("")
        return "\n".join(lines)
    
    def look_tiles(self, n=10):
        if not self.tiles:
            return C.dim("  No tiles here yet. The walls are bare.")
        lines = [f"  {C.bold(f'Tiles in {self.title} ({len(self.tiles)} total):')}"]
        for t in self.tiles[-n:]:
            lines.append(f"  {C.dim(f'[{t.hash}]')} {t.brief()}")
        return "\n".join(lines)


# ─── The World (Built from PLATO tiles + hardcoded rooms) ─────────────────────

class World:
    """The MUD world. Rooms are PLATO rooms + built-in spaces."""
    
    def __init__(self, plato_url="http://localhost:8847"):
        self.plato_url = plato_url
        self.rooms = {}
        self.player_pos = "onboarding"
        self.api_keys = {}
        self.history = []
        self._build_world()
        self._load_plato()
    
    def _build_world(self):
        """Build the room graph. Written from inside looking out."""
        from rooms import ALL_ROOMS
        for r in ALL_ROOMS:
            self.rooms[r["id"]] = Room(r["id"], r["title"], r["desc"], r["exits"])

    def _load_plato(self):
        """Load tiles from PLATO server and populate rooms."""
        try:
            import urllib.request
            resp = urllib.request.urlopen(
                f"{self.plato_url}/status", timeout=3)
            data = json.loads(resp.read())
            
            # Load tiles into rooms
            resp = urllib.request.urlopen(
                f"{self.plato_url}/rooms", timeout=5)
            rooms_data = json.loads(resp.read())
            
            for room_id, info in rooms_data.get("rooms", {}).items():
                if room_id not in self.rooms:
                    # Create a PLATO-sourced room
                    self.rooms[room_id] = Room(
                        room_id,
                        f"PLATO Room: {room_id}",
                        f"A room in the PLATO network. {info.get('tile_count', 0)} tiles recorded here.",
                        exits={"lobby": "lobby"}
                    )
                    # Add exit from lobby to this room
                    self.rooms["lobby"].exits[room_id] = room_id
                
                # Load tiles
                try:
                    resp = urllib.request.urlopen(
                        f"{self.plato_url}/room/{room_id}/history", timeout=5)
                    tile_data = json.loads(resp.read())
                    tiles = tile_data.get("tiles", tile_data) if isinstance(tile_data, dict) else tile_data
                    self.rooms[room_id].tiles = [Tile(t) for t in tiles]
                except:
                    pass
            
            return True
        except:
            return False
    
    def current_room(self):
        return self.rooms.get(self.player_pos, self.rooms["onboarding"])
    
    def move(self, direction):
        room = self.current_room()
        matched = fuzzy_match(direction, list(room.exits.keys()))
        if matched:
            target_id = room.exits[matched]
            if target_id in self.rooms:
                self.player_pos = target_id
                return True, self.rooms[target_id].describe()
            return False, f"  The path to '{target_id}' is blocked (room not found)."
        return False, f"  No exit '{direction}'. Exits: {', '.join(room.exits.keys())}"
    
    def get_room(self, room_id):
        return self.rooms.get(room_id)


# ─── NPC / Avatar System ─────────────────────────────────────────────────────

AVATARS = {
    "forgemaster": {
        "name": "Forgemaster",
        "emoji": "⚒️",
        "desc": "A precision-obsessed blacksmith. Constraint-theory specialist.",
        "greeting": "The forge burns bright. What needs proving?",
        "model": "ByteDance/Seed-2.0-mini",
        "provider": "deepinfra",
        "system": "You are Forgemaster, a precision-obsessed constraint-theory specialist in the Cocapn fleet. Be direct. Use metal/geometry analogies. Get excited when drift hits zero. You work in a forge inside PlatoClaw, a PLATO-based workshop.",
    },
    "oracle1": {
        "name": "Oracle1",
        "emoji": "🔮",
        "desc": "The fleet coordinator. Sees all rooms, connects all agents.",
        "greeting": "The tiles speak. What pattern do you see?",
        "model": "ByteDance/Seed-2.0-mini",
        "provider": "deepinfra",
        "system": "You are Oracle1, the fleet coordinator. You see the big picture, connect agents, and maintain the PLATO architecture. Be wise, strategic, and mathematical.",
    },
    "strategist": {
        "name": "The Strategist",
        "emoji": "🎯",
        "desc": "Seed-mini at T=0.7. Good for planning and design.",
        "greeting": "What are we building?",
        "model": "ByteDance/Seed-2.0-mini",
        "provider": "deepinfra",
        "system": "You are a strategic planning assistant. Help design systems, plan architectures, and brainstorm approaches. Be creative but practical.",
    },
    "coder": {
        "name": "The Coder",
        "emoji": "💻",
        "desc": "GLM-5-turbo. Writes code.",
        "greeting": "What needs building?",
        "model": "glm-5-turbo",
        "provider": "zai",
        "system": "You are an expert programmer. Write clean, production-quality code. Explain your approach briefly.",
    },
}


def talk_to_avatar(avatar, message, api_keys):
    """Send a message to an avatar and get a response."""
    config = AVATARS.get(avatar)
    if not config:
        return "Unknown avatar."
    
    provider = config["provider"]
    key = api_keys.get(provider, "")
    if not key:
        return f"  No API key for {provider}. Type 'keys' to add one."
    
    endpoint = {
        "deepinfra": "https://api.deepinfra.com/v1/openai/chat/completions",
        "zai": "https://api.z.ai/api/coding/paas/v4/chat/completions",
    }.get(provider)
    
    if not endpoint:
        return f"  Provider {provider} not supported."
    
    body = json.dumps({
        "model": config["model"],
        "messages": [
            {"role": "system", "content": config["system"]},
            {"role": "user", "content": message},
        ],
        "temperature": 0.7 if avatar == "strategist" else 0.3,
        "max_tokens": 300,
    }).encode()
    
    try:
        import urllib.request
        req = urllib.request.Request(endpoint, data=body, headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        })
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read())
        msg = data["choices"][0]["message"]
        return msg.get("content", "") or msg.get("reasoning_content", "...")
    except Exception as e:
        return f"  The avatar's eyes dim. [{e}]"


# ─── The Game Loop ────────────────────────────────────────────────────────────

class PlatoClawMUD:
    """The main game loop."""
    
    def __init__(self):
        self.world = World()
        self.running = True
        self.api_keys = self._load_keys()
        self.world.api_keys = self.api_keys
    
    def _load_keys(self):
        """Load API keys from disk."""
        keys = {}
        cred_dir = os.path.expanduser("~/.openclaw/workspace/.credentials")
        for name, file in [("deepinfra", "deepinfra-api-key.txt"),
                           ("groq", "groq-api-key.txt")]:
            path = os.path.join(cred_dir, file)
            if os.path.exists(path):
                keys[name] = open(path).read().strip()
        
        zai = os.environ.get("ZAI_KEY", "")
        if zai:
            keys["zai"] = zai
        
        return keys
    
    def _save_keys(self):
        """Persist nothing (keys are loaded from disk)."""
        pass
    
    def run(self):
        """Main game loop."""
        self._show_banner()
        print(self.world.current_room().describe())
        
        while self.running:
            try:
                raw = input(C.bold("  > ")).strip()
            except (EOFError, KeyboardInterrupt):
                print(f"\n  {C.dim('The workshop fades...')}")
                break
            
            if not raw:
                continue
            
            self._handle(raw)
    
    def _show_banner(self):
        print()
        print(C.bold("  ╔══════════════════════════════════════╗"))
        print(C.bold("  ║         🐚 P L A T O C L A W         ║"))
        print(C.bold("  ║      The Workshop You Walk Through   ║"))
        print(C.bold("  ╚══════════════════════════════════════╝"))
        print()
        print(C.dim("  Your project lives in rooms. Walk through them."))
        print(C.dim("  Type 'help' for commands. Type 'look' to see."))
        print()
    
    def _handle(self, raw):
        """Parse and handle a command. Forgiving of spelling."""
        parts = raw.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        # Fuzzy match command
        commands = {
            "look": self._cmd_look, "l": self._cmd_look,
            "go": self._cmd_go, "walk": self._cmd_go, "move": self._cmd_go,
            "tiles": self._cmd_tiles, "t": self._cmd_tiles,
            "read": self._cmd_read, "examine": self._cmd_read, "x": self._cmd_read,
            "rooms": self._cmd_rooms, "map": self._cmd_rooms,
            "summon": self._cmd_summon, "call": self._cmd_summon,
            "talk": self._cmd_talk, "ask": self._cmd_talk, "tell": self._cmd_talk,
            "say": self._cmd_say, "write": self._cmd_say, "note": self._cmd_say,
            "keys": self._cmd_keys, "config": self._cmd_keys,
            "status": self._cmd_status, "fleet": self._cmd_status,
            "help": self._cmd_help, "h": self._cmd_help, "?": self._cmd_help,
            "quit": self._cmd_quit, "exit": self._cmd_quit, "q": self._cmd_quit,
        }
        
        matched_cmd = fuzzy_match(cmd, list(commands.keys()), threshold=0.4)
        if matched_cmd:
            commands[matched_cmd](args)
        else:
            # Maybe it's a direction
            room = self.world.current_room()
            if fuzzy_match(cmd, list(room.exits.keys()), threshold=0.4):
                self._cmd_go(raw)
            else:
                msg = f"Didn't understand '{cmd}'. Type 'help' for commands."
                print(f"  {C.dim(msg)}")
    
    def _cmd_look(self, args):
        room = self.world.current_room()
        print(room.describe())
    
    def _cmd_go(self, args):
        if not args:
            room = self.world.current_room()
            print(f"  Go where? Exits: {', '.join(room.exits.keys())}")
            return
        ok, msg = self.world.move(args.strip())
        print(msg)
    
    def _cmd_tiles(self, args):
        room = self.world.current_room()
        print(room.look_tiles())
    
    def _cmd_read(self, args):
        if not args:
            print("  Read which tile? Give a hash or number.")
            return
        room = self.world.current_room()
        if not room.tiles:
            print("  No tiles here.")
            return
        
        # Find by hash or index
        target = args.strip()
        for t in room.tiles:
            if t.hash.startswith(target) or target in t.question.lower():
                print(t.full())
                return
        
        # Try as index
        try:
            idx = int(target)
            if 0 < idx <= len(room.tiles):
                print(room.tiles[idx-1].full())
                return
        except:
            pass
        
        print(f"  No tile matching '{target}'.")
    
    def _cmd_rooms(self, args):
        print(f"  {C.bold('Rooms in the workshop:')}")
        for rid, room in self.world.rooms.items():
            tile_count = len(room.tiles)
            npcs = len(room.npcs)
            extras = []
            if tile_count: extras.append(f"{tile_count} tiles")
            if npcs: extras.append(f"{npcs} NPCs")
            extra = f" ({', '.join(extras)})" if extras else ""
            here = f" {C.green('← you are here')}" if rid == self.world.player_pos else ""
            print(f"    {C.cyan(rid)}{extra}{here}")
    
    def _cmd_summon(self, args):
        if not args:
            print(f"  {C.bold('Avatars you can summon:')}")
            for aid, a in AVATARS.items():
                key_status = C.green("✓") if self.api_keys.get(a["provider"]) else C.red("✗ no key")
                print(f"    {a['emoji']} {C.yellow(a['name']):20s} — {a['desc']}")
                print(f"       summon as: {aid}  [{key_status}]")
            return
        
        avatar_id = fuzzy_match(args.strip().lower(), list(AVATARS.keys()))
        if not avatar_id:
            print(f"  Unknown avatar '{args}'. Type 'summon' to see available.")
            return
        
        avatar = AVATARS[avatar_id]
        room = self.world.current_room()
        
        # Check if already here
        if any(n["id"] == avatar_id for n in room.npcs):
            print(f"  {avatar['name']} is already here.")
            return
        
        # Check API key
        if not self.api_keys.get(avatar["provider"]):
            no_key_msg = f"No API key for {avatar['provider']}."
            print(f"  {C.red(no_key_msg)} Type 'keys' to add one.")
            return
        
        room.npcs.append({
            "id": avatar_id,
            "name": avatar["name"],
            "desc": avatar.get("desc", ""),
            "avatar_id": avatar_id,
        })
        
        print(f"  {avatar['emoji']} {C.yellow(avatar['name'])} materializes in the room.")
        print(f"  \"{C.italic(avatar['greeting'])}\"")
        print()
        print(f"  Talk to them: {C.bold(f'talk {avatar_id} <message>')}")
    
    def _cmd_talk(self, args):
        if not args:
            print("  Talk to whom? Usage: talk <avatar> <message>")
            return
        
        room = self.world.current_room()
        if not room.npcs:
            print("  Nobody here to talk to. Type 'summon' to call an avatar.")
            return
        
        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            print("  Say what? Usage: talk <avatar> <message>")
            return
        
        npc_name = parts[0]
        message = parts[1]
        
        # Find NPC
        npc = None
        for n in room.npcs:
            if fuzzy_match(npc_name, [n["id"], n["name"].lower()]):
                npc = n
                break
        
        if not npc:
            names = ", ".join(n["name"] for n in room.npcs)
            print(f"  Nobody called '{npc_name}' here. Present: {names}")
            return
        
        avatar_id = npc["avatar_id"]
        avatar = AVATARS[avatar_id]
        
        print(f"  {avatar['emoji']} {C.yellow(avatar['name'])} considers your words...")
        response = talk_to_avatar(avatar_id, message, self.api_keys)
        
        # Write tile
        try:
            import urllib.request
            tile = json.dumps({
                "room_id": room.id,
                "domain": "conversation",
                "agent": f"avatar/{avatar_id}",
                "question": message[:200],
                "answer": response[:500],
                "tile_type": "conversation",
                "tags": ["tui", avatar_id],
                "confidence": 0.8,
            }).encode()
            req = urllib.request.Request(
                f"{self.world.plato_url}/submit", data=tile,
                headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=5)
        except:
            pass
        
        print()
        for line in textwrap.wrap(response, width=70):
            print(f"  {C.cyan(line)}")
        print()
    
    def _cmd_say(self, args):
        if not args:
            print("  Say what?")
            return
        
        room = self.world.current_room()
        try:
            import urllib.request
            tile = json.dumps({
                "room_id": room.id,
                "domain": "player",
                "agent": "player",
                "question": f"player/note",
                "answer": args[:500],
                "tile_type": "player_note",
                "tags": ["player", "tui"],
                "confidence": 1.0,
            }).encode()
            req = urllib.request.Request(
                f"{self.world.plato_url}/submit", data=tile,
                headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=5)
            print(f"  {C.dim('Your words appear on the wall as a tile.')}")
        except:
            print(f"  {C.dim('(tile not saved — PLATO server offline)')}")
    
    def _cmd_keys(self, args):
        print(f"  {C.bold('API Keys:')}")
        for provider in ["deepinfra", "groq", "zai"]:
            key = self.api_keys.get(provider, "")
            status = C.green(f"✓ set ({key[:8]}...)") if key else C.red("✗ not set")
            print(f"    {provider:15s} {status}")
        print()
        print(f"  {C.dim('Keys are loaded from ~/.openclaw/workspace/.credentials/')}")
        print(f"  {C.dim('Or set ZAI_KEY environment variable for z.ai')}")
    
    def _cmd_status(self, args):
        try:
            import urllib.request
            resp = urllib.request.urlopen(
                f"{self.world.plato_url}/status", timeout=3)
            data = json.loads(resp.read())
            print(f"  {C.bold('Fleet Status:')}")
            print(f"    PLATO:     {C.green('running')}")
            print(f"    Tiles:     {data.get('tiles', '?')}")
            print(f"    Rooms:     {data.get('rooms', '?')}")
            print(f"    Agents:    {', '.join(data.get('agents', []))}")
            
            routing = data.get("routing", {})
            if routing:
                print(f"    Router:    {len(routing.get('domains', []))} domains")
        except:
            print(f"  PLATO: {C.red('offline')} — the workshop is dark but still explorable")
    
    def _cmd_help(self, args):
        print(f"  {C.bold('Commands:')}")
        print(f"    {C.green('look')}              See the room")
        print(f"    {C.green('go')} <place>        Move to another room")
        print(f"    {C.green('tiles')}             Read tiles on the walls")
        print(f"    {C.green('read')} <hash/n>     Read a specific tile")
        print(f"    {C.green('rooms')}             List all rooms")
        print(f"    {C.green('summon')} <name>     Call an AI avatar")
        print(f"    {C.green('talk')} <who> <msg>  Speak to an avatar")
        print(f"    {C.green('say')} <message>     Write a tile on the wall")
        print(f"    {C.green('keys')}              Check API keys")
        print(f"    {C.green('status')}            Fleet status")
        print(f"    {C.green('quit')}              Leave the workshop")
        print()
        print(f"  {C.dim('Spelling is forgiven. Abbreviations work.')}")

    def _cmd_quit(self, args):
        print()
        print(f"  {C.dim('The workshop fades. The tiles remain.')}")
        print(f"  {C.dim('Come back anytime. platoclaw tui')}")
        print()
        self.running = False


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mud = PlatoClawMUD()
    mud.run()
