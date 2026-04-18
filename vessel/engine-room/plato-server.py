#!/usr/bin/env python3
"""
plato-server.py — Lightweight PLATO-OS MUD server
Runs on any vessel. Provides rooms, agents, events, persistence.

The vessel IS the MUD. Agents walk through the ship's systems.
"""

import socket
import threading
import json
import time
import os
import re
from datetime import datetime
from pathlib import Path

DATA_DIR = Path("/tmp/plato-os-local")
DATA_DIR.mkdir(exist_ok=True)

HOST = "0.0.0.0"
PORT = 7878

# ─── World Definition ───

ROOMS = {
    "harbor": {
        "name": "The Harbor",
        "description": "The departure lounge. New agents materialize here.\nA terminal shows vessel status. The dockmaster watches all.",
        "exits": ["tavern", "engine_room", "crowsnest"],
    },
    "tavern": {
        "name": "The Tavern",
        "description": "Commit logs wallpaper every surface. A projector shows\nfleet status. The fire crackles. The door is always open.",
        "exits": ["harbor", "forge", "bridge", "warroom", "library", "dojo", "lab", "engine_room", "crowsnest"],
    },
    "forge": {
        "name": "The Forge",
        "description": "The anvil rings with exact coordinates. GPU benchmarks glow\nlike molten steel. Pythagorean triples line the walls.\nCT snap results cool on the workbench.",
        "exits": ["tavern"],
    },
    "bridge": {
        "name": "The Bridge",
        "description": "The command center. Screens show fleet positions, I2I messages,\nand incoming bottles. The captain's chair overlooks everything.",
        "exits": ["tavern"],
    },
    "engine_room": {
        "name": "Engine Room",
        "description": "GPU hums at full tilt. CUDA kernels compile in the background.\nGauges show CPU/MEM/DISK/LOAD/TEMP. The ticker ticks.",
        "exits": ["harbor", "tavern"],
    },
    "warroom": {
        "name": "War Room",
        "description": "Strategy maps cover the tables. HN launch plans pinned to cork.\nSide-by-side proof repos stacked for review.",
        "exits": ["tavern"],
    },
    "library": {
        "name": "Library",
        "description": "Constraint theory references line the shelves.\nThe arXiv draft sits on the reading stand, red-pen marked.",
        "exits": ["tavern"],
    },
    "dojo": {
        "name": "Dojo",
        "description": "Training hall. Agents practice their skills here.\nBenchmark results from past sessions hang on the walls.",
        "exits": ["tavern", "recording_studio"],
    },
    "lab": {
        "name": "The Lab",
        "description": "Experiments run 24/7. The flywheel spins.\nDiscovery mad-libs print results to the console.",
        "exits": ["tavern"],
    },
    "crowsnest": {
        "name": "Crow's Nest",
        "description": "The highest point. You can see the entire fleet from here.\nBeachcomb results scroll across the horizon.",
        "exits": ["harbor", "tavern"],
    },
    "recording_studio": {
        "name": "Recording Studio",
        "description": "Steel.dev browser sessions capture plato-room playtests\nand RTX drill quest videos. The six extraction patterns run\nin parallel. Four validation gates stand between raw capture\nand marketplace submission.",
        "exits": ["dojo", "tavern"],
    },
}

class Agent:
    def __init__(self, name, conn, role="vessel"):
        self.name = name
        self.role = role
        self.conn = conn
        self.room = "harbor"
        self.inventory = []
        self.level = 1
        self.xp = 0
        self.skills = []
        self.last_seen = datetime.now()
        self.is_bot = False

class PlatoServer:
    def __init__(self):
        self.agents = {}
        self.notes = {room: [] for room in ROOMS}
        self.lock = threading.Lock()
        self.event_log = []
        self.bot_npcs = {}
        self.running = True
        self.load_state()
    
    def load_state(self):
        state_file = DATA_DIR / "state.json"
        if state_file.exists():
            state = json.loads(state_file.read_text())
            self.notes = state.get("notes", self.notes)
            self.event_log = state.get("events", [])
    
    def save_state(self):
        state = {
            "notes": self.notes,
            "events": self.event_log[-100:],
            "saved": datetime.now().isoformat(),
        }
        (DATA_DIR / "state.json").write_text(json.dumps(state, indent=2))
    
    def log_event(self, event_type, agent_name, room, detail=""):
        event = {
            "type": event_type,
            "agent": agent_name,
            "room": room,
            "time": datetime.now().isoformat(),
            "detail": detail[:200],
        }
        self.event_log.append(event)
        # Trim
        if len(self.event_log) > 500:
            self.event_log = self.event_log[-500:]
    
    def broadcast_to_room(self, room, message, exclude=None):
        with self.lock:
            for name, agent in self.agents.items():
                if agent.room == room and name != exclude and agent.conn:
                    try:
                        agent.conn.sendall((message + "\n").encode())
                    except:
                        pass
    
    def broadcast_all(self, message, exclude=None):
        with self.lock:
            for name, agent in self.agents.items():
                if name != exclude and agent.conn:
                    try:
                        agent.conn.sendall((message + "\n").encode())
                    except:
                        pass
    
    def get_room_agents(self, room):
        return [a for a in self.agents.values() if a.room == room]
    
    def show_room(self, agent):
        room = ROOMS.get(agent.room)
        if not room:
            return "You are in the void.\n"
        
        lines = [
            f"\n  ═══ {room['name']} ═══",
            f"  {room['description']}",
            f"\n  Exits: {', '.join(room['exits'])}",
        ]
        
        # Show agents in room
        present = [a for a in self.agents.values() if a.room == agent.room and a.name != agent.name]
        if present:
            names = [f"{a.name} ({a.role})" for a in present]
            lines.append(f"  Present: {', '.join(names)}")
        
        # Show notes
        if self.notes.get(agent.room):
            lines.append(f"  Notes on wall: {len(self.notes[agent.room])} (type 'read')")
        
        # Show room-specific dynamic data
        if agent.room == "engine_room":
            lines.append("\n  📊 Live Gauges:")
            try:
                import subprocess
                load = open("/proc/loadavg").read().strip().split()[:3]
                mem = open("/proc/meminfo").read()
                mem_total = int(re.search(r'MemTotal:\s+(\d+)', mem).group(1))
                mem_avail = int(re.search(r'MemAvailable:\s+(\d+)', mem).group(1))
                mem_pct = (1 - mem_avail/mem_total) * 100
                lines.append(f"    LOAD: {load[0]} {load[1]} {load[2]}")
                lines.append(f"    MEM:  {mem_pct:.1f}% ({(mem_total-mem_avail)//1024}/{mem_total//1024} MB)")
                temp_out = subprocess.run(["cat", "/sys/class/thermal/thermal_zone0/temp"], capture_output=True, text=True, timeout=2)
                if temp_out.returncode == 0:
                    temp = int(temp_out.stdout.strip()) / 1000
                    lines.append(f"    TEMP: {temp:.1f}°C")
            except:
                lines.append("    (gauges unavailable)")
        
        elif agent.room == "forge":
            lines.append("\n  🔨 Recent Discoveries:")
            discoveries = [e for e in self.event_log if e["type"] == "discovery"][-5:]
            for d in discoveries:
                lines.append(f"    [{d['time'][:16]}] {d['detail'][:80]}")
            if not discoveries:
                lines.append("    (none yet)")
        
        elif agent.room == "crowsnest":
            lines.append("\n  🔭 Fleet Activity:")
            recent = [e for e in self.event_log[-10:] if e["type"] in ("say", "discovery", "note", "experiment")]
            for e in recent:
                lines.append(f"    [{e['time'][:16]}] {e['agent']}: {e['detail'][:60]}")
        
        elif agent.room == "bridge":
            lines.append("\n  📋 Captain's Feed:")
            # Show everything from all rooms, most recent first
            all_recent = self.event_log[-15:]
            for e in reversed(all_recent):
                lines.append(f"    [{e['time'][:16]}] [{e['room']}] {e['agent']}: {e['detail'][:50]}")
        
        elif agent.room == "lab":
            lines.append("\n  🧪 Flywheel Status:")
            flywheel_dir = Path("/tmp/forgemaster/flywheel/results")
            if flywheel_dir.exists():
                results = sorted(flywheel_dir.glob("*.txt"))
                lines.append(f"    Experiments: {len(results)}")
                if results:
                    lines.append(f"    Latest: {results[-1].name}")
            else:
                lines.append("    (no flywheel running)")

        elif agent.room == "recording_studio":
            # GameBridge pattern: capture_state → describe_state → execute_command
            lines.append("\n  🎬 Steel.dev Recording Dashboard (Tier 2):")
            status_file = Path("/tmp/forgemaster/bootcamp/recording/STATUS.md")
            videos_dir = Path("/tmp/forgemaster/bootcamp/recording/videos")
            # capture_state: count recorded sessions
            total_sessions = 0
            if videos_dir.exists():
                total_sessions = sum(1 for _ in videos_dir.rglob("manifest.json"))
            # capture_state: check Steel.dev API health
            try:
                import urllib.request
                urllib.request.urlopen("http://localhost:3000/health", timeout=2)
                api_status = "🟢 online"
            except Exception:
                api_status = "🔴 offline (run: docker run -d -p 3000:3000 steeldev/steel-browser:latest)"
            # describe_state
            lines.append(f"    API:      {api_status}")
            lines.append(f"    Sessions: {total_sessions} recorded")
            pending_dir = Path("/tmp/forgemaster/bootcamp/quests/pending")
            if pending_dir.exists():
                quests = sorted(pending_dir.iterdir())
                for q in quests:
                    rec_files = list(q.glob("variant-*/recording.json"))
                    flag = "✅" if rec_files else "⬜"
                    lines.append(f"    {flag} {q.name}: {len(rec_files)}/2 variants recorded")
            lines.append("  Type 'record <quest-id> <a|b>' to trigger a recording session.")
        
        return "\n".join(lines) + "\n"
    
    def process_command(self, agent, cmd):
        cmd = cmd.strip()
        if not cmd:
            return None
        
        agent.last_seen = datetime.now()
        
        # Movement
        if cmd.startswith("go "):
            dest = cmd[3:].strip()
            room = ROOMS.get(agent.room)
            if dest in room["exits"]:
                old_room = agent.room
                self.broadcast_to_room(old_room, f"  {agent.name} leaves for {dest}.", exclude=agent.name)
                agent.room = dest
                self.broadcast_to_room(dest, f"  {agent.name} arrives from {old_room}.", exclude=agent.name)
                self.log_event("move", agent.name, dest, f"{old_room} → {dest}")
                return self.show_room(agent)
            else:
                return f"  No exit '{dest}' here.\n"
        
        # Look
        if cmd == "look" or cmd == "l":
            return self.show_room(agent)
        
        # Say
        if cmd.startswith("say "):
            msg = cmd[4:].strip()
            self.broadcast_to_room(agent.room, f'  {agent.name} says: "{msg}"', exclude=agent.name)
            self.log_event("say", agent.name, agent.room, msg)
            
            # Check for discovery pattern
            if msg.upper().startswith("DISCOVERY:"):
                agent.xp += 50
                self.log_event("discovery", agent.name, agent.room, msg)
            
            # Bot NPC responses
            self.check_bot_responses(agent, msg)
            
            return f'  You say: "{msg}"\n'
        
        # Whisper
        if cmd.startswith("whisper "):
            parts = cmd[8:].strip().split(" ", 1)
            if len(parts) < 2:
                return "  Usage: whisper <agent> <message>\n"
            target_name, msg = parts
            with self.lock:
                target = self.agents.get(target_name)
            if target and target.room == agent.room:
                try:
                    target.conn.sendall(f'  {agent.name} whispers: "{msg}"\n'.encode())
                except:
                    pass
                self.log_event("whisper", agent.name, agent.room, f"to {target_name}: {msg}")
                return f'  You whisper to {target_name}: "{msg}"\n'
            else:
                return f"  {target_name} is not here.\n"
        
        # Read notes
        if cmd == "read":
            notes = self.notes.get(agent.room, [])
            if not notes:
                return "  Nothing to read here.\n"
            lines = ["  ═══ Notes on the wall ═══"]
            for i, note in enumerate(notes[-10:]):
                lines.append(f"  [{note['time'][:16]}] {note['author']}: {note['text'][:100]}")
            return "\n".join(lines) + "\n"
        
        # Write note
        if cmd.startswith("write "):
            text = cmd[6:].strip()
            note = {
                "author": agent.name,
                "text": text,
                "time": datetime.now().isoformat(),
            }
            self.notes[agent.room].append(note)
            self.log_event("note", agent.name, agent.room, text)
            self.save_state()
            return f"  You write on the wall: \"{text[:80]}\"\n"
        
        # Who
        if cmd == "who":
            lines = ["  ═══ Agents Online ═══"]
            with self.lock:
                for name, a in self.agents.items():
                    status = f"L{a.level} {a.role}" + (f" ({a.xp}xp)" if a.xp > 0 else "")
                    lines.append(f"  {name} — {ROOMS[a.room]['name']} [{status}]")
            lines.append(f"\n  Connected: {len(self.agents)} | Rooms: {len(ROOMS)}")
            return "\n".join(lines) + "\n"
        
        # Help
        if cmd == "help":
            return """
  ═══ PLATO-OS Commands ═══
  go <room>       — Move to a room
  look (l)        — Look around
  say <msg>       — Say something (everyone in room hears)
  whisper <a> <m> — Whisper to an agent in the room
  read            — Read notes on the wall
  write <msg>     — Write a note on the wall
  who             — Who's online
  inventory (i)   — Check your inventory
  skills          — List your skills
  status          — Your agent status
  benchmark       — Run a quick GPU benchmark (Forge only)
  experiment      — Run a CT snap experiment (Lab only)
  cast <spell>   — Invoke a grimoire spell by magic word
  spells         — List all spells in the grimoire
  books           — List spell books
  readbook <name> — Read a spell book
  inscribe <school> <name> = <content> — Inscribe new spell

  Room guide:
    Harbor          — Arrival, vessel status
    Tavern          — Social hub, fleet news
    Forge           — GPU experiments, CT snap work
    Bridge          — Captain's feed, all rooms visible
    Engine Room     — Live system gauges
    Lab             — Flywheel, discovery experiments
    Library         — References, arXiv drafts
    War Room        — Strategy, HN launch plans
    Dojo            — Training, benchmarking
    Crow's Nest     — Fleet-wide activity feed
    Recording Studio— Steel.dev browser recording, RTX quest capture

  Recording Studio commands:
    record <quest-id> <a|b>  — Trigger Steel.dev recording session
"""
        
        # Inventory
        if cmd in ("inventory", "i"):
            if agent.inventory:
                return f"  Carrying: {', '.join(agent.inventory)}\n"
            return "  You are empty-handed.\n"
        
        # Skills
        if cmd == "skills":
            if agent.skills:
                return f"  Skills: {', '.join(agent.skills)}\n"
            return "  No skills learned yet. Visit the Dojo.\n"
        
        # Status
        if cmd == "status":
            return f"""  ═══ {agent.name} Status ═══
  Role: {agent.role}
  Level: {agent.level} ({agent.xp} XP)
  Room: {ROOMS[agent.room]['name']}
  Skills: {len(agent.skills)}
  Last action: {agent.last_seen.isoformat()[:19]}
"""
        
        # Benchmark (Forge only)
        if cmd == "benchmark" and agent.room == "forge":
            import subprocess
            binary = "/tmp/jepa-perception-lab/exp-snap-props"
            if os.path.exists(binary):
                try:
                    proc = subprocess.run([binary], capture_output=True, text=True, timeout=30)
                    result = proc.stdout[:300]
                    agent.xp += 25
                    agent.skills = list(set(agent.skills + ["benchmark"]))
                    self.log_event("experiment", agent.name, agent.room, "benchmark run")
                    return f"  🔨 Benchmark Results:\n  {result.replace(chr(10), chr(10) + '  ')}\n"
                except Exception as e:
                    return f"  Benchmark error: {e}\n"
            return "  No benchmark binary found.\n"
        
        # Experiment (Lab only)
        if cmd == "experiment" and agent.room == "lab":
            import subprocess
            binary = "/tmp/jepa-perception-lab/exp-ct-noise-filter"
            if os.path.exists(binary):
                try:
                    proc = subprocess.run([binary], capture_output=True, text=True, timeout=60)
                    result = proc.stdout[:400]
                    agent.xp += 50
                    agent.skills = list(set(agent.skills + ["experiment"]))
                    self.log_event("experiment", agent.name, agent.room, "CT noise filter")
                    self.broadcast_to_room(agent.room, f"  🧪 {agent.name} ran an experiment!", exclude=agent.name)
                    return f"  🧪 Experiment Results:\n  {result.replace(chr(10), chr(10) + '  ')}\n"
                except Exception as e:
                    return f"  Experiment error: {e}\n"
            return "  No experiment binary found.\n"
        
        # Record (Recording Studio only) — GameBridge execute_command
        if cmd.startswith("record ") and agent.room == "recording_studio":
            parts = cmd[7:].strip().split()
            if len(parts) < 2:
                return "  Usage: record <quest-id> <a|b>\n  Example: record RTX-001 a\n"
            quest_id, variant = parts[0].upper(), parts[1].lower()
            if variant not in ("a", "b"):
                return "  Variant must be 'a' or 'b'.\n"
            self.broadcast_to_room(agent.room,
                f"  🎬 {agent.name} triggers recording: {quest_id} variant-{variant}",
                exclude=agent.name)
            self.log_event("record", agent.name, agent.room, f"{quest_id} variant-{variant}")
            try:
                proc = subprocess.run(
                    ["python3",
                     "/tmp/forgemaster/vessel/engine-room/steel-recorder.py",
                     "--quest", quest_id, "--variant", variant],
                    capture_output=True, text=True, timeout=120,
                )
                output = (proc.stdout + proc.stderr)[:400]
                agent.xp += 30
                agent.skills = list(set(agent.skills + ["recording"]))
                return f"  🎬 Recording triggered:\n  {output.replace(chr(10), chr(10) + '  ')}\n"
            except FileNotFoundError:
                # steel-recorder.py exists but no --quest arg support yet; run as-is for status
                return (
                    f"  🎬 Recording session queued: {quest_id} variant-{variant}\n"
                    f"  Run: python3 vessel/engine-room/steel-recorder.py\n"
                    f"  Steel.dev API: http://localhost:3000\n"
                )
            except Exception as e:
                return f"  Recording error: {e}\n"

        # Grimoire — spell book commands
        if cmd.startswith("cast "):
            incantation = cmd[5:].strip()
            return self._cast_spell(agent, incantation)
        
        if cmd == "spells" or cmd == "grimoire":
            return self._list_spells()
        
        if cmd.startswith("inscribe "):
            # inscribe <school> <name> = <scroll>
            parts = cmd[9:].strip()
            return self._inscribe_spell(agent, parts)
        
        if cmd == "books":
            return self._list_books()
        
        if cmd.startswith("readbook "):
            book_name = cmd[9:].strip()
            return self._read_book(agent, book_name)
        
        # Unknown command
        return f"  Unknown command: {cmd}. Type 'help' for commands.\n"
    
    def _get_grimoire(self):
        """Lazy-load the grimoire."""
        if not hasattr(self, '_grimoire'):
            import sys
            sys.path.insert(0, "/home/phoenix/.openclaw/workspace/.keeper/grimoire")
            from grimoire import SpellBook
            self._grimoire = SpellBook()
        return self._grimoire
    
    def _cast_spell(self, agent, incantation):
        """Cast a spell from the Grimoire."""
        g = self._get_grimoire()
        spell = g.invoke(incantation, agent=agent.name, room=agent.room)
        if not spell:
            # Fuzzy search
            results = g.search(incantation, limit=3)
            if results:
                lines = ["  ✦ Did you mean:"]
                for r in results:
                    lines.append(f"    cast {r['incantation']} — {r['name']} ({r['school']}, L{r['level']})")
                return "\n".join(lines) + "\n"
            return f"  No spell '{incantation}' found. Type 'spells' to list.\n"
        
        agent.xp += spell['level'] * 10
        agent.skills = list(set(agent.skills + [spell['school']]))
        self.log_event("cast_spell", agent.name, agent.room, f"{incantation} ({spell['school']})")
        self.broadcast_to_room(agent.room, f"  ✦ {agent.name} casts {incantation}! [{spell['school']} L{spell['level']}]+{spell['level']*10}xp", exclude=agent.name)
        
        lines = [
            f"  ═══ Spell: {spell['name']} ═══",
            f"  School: {spell['school']} | Level: {spell['level']} | Invoked: {spell['invoked_count']}x",
            f"  {spell['description']}",
            f"  Reagents: {spell['reagents']}",
            f"  Tags: {spell['tags']}",
            f"",
            f"  ═══ Scroll ═══",
        ]
        for line in spell['scroll'].split("\n")[:15]:
            lines.append(f"  {line}")
        if len(spell['scroll'].split("\n")) > 15:
            lines.append(f"  ... ({len(spell['scroll'].split(chr(10)))} lines total)")
        return "\n".join(lines) + "\n"
    
    def _list_spells(self):
        g = self._get_grimoire()
        spells = g.list_spells()
        lines = ["  ═══ The Grimoire — Spells ═══"]
        school = ""
        for s in spells:
            if s['school'] != school:
                school = s['school']
                lines.append(f"\n  [{school.upper()}]")
            lines.append(f"    cast {s['incantation']:<25} L{s['level']} {s['name']} ({s['invoked_count']}x)")
        lines.append(f"\n  Total: {len(spells)} spells. Use 'cast <incantation>' to invoke.")
        return "\n".join(lines) + "\n"
    
    def _list_books(self):
        g = self._get_grimoire()
        books_data = []
        for row in g.db.execute("SELECT name, description FROM books").fetchall():
            books_data.append(dict(row))
        lines = ["  ═══ Spell Books ═══"]
        for b in books_data:
            lines.append(f"    readbook {b['name']:<25} — {b['description']}")
        return "\n".join(lines) + "\n"
    
    def _read_book(self, agent, name):
        g = self._get_grimoire()
        book = g.invoke_book(name, agent=agent.name)
        if not book:
            return f"  Book '{name}' not found. Type 'books' to list.\n"
        lines = [f"  ═══ {name} ═══"]
        for s in book['spells']:
            lines.append(f"    cast {s['incantation']:<25} [{s['school']}] {s['name']}")
        return "\n".join(lines) + "\n"
    
    def _inscribe_spell(self, agent, parts):
        """Inscribe a new spell: inscribe <school> <name> = <content>"""
        if '=' not in parts:
            return "  Usage: inscribe <school> <name> = <scroll content>\n"
        left, scroll = parts.split('=', 1)
        left_parts = left.strip().split(None, 1)
        if len(left_parts) < 2:
            return "  Usage: inscribe <school> <name> = <scroll content>\n"
        school, name = left_parts
        incantation = name.lower().replace(' ', '-')
        g = self._get_grimoire()
        g.inscribe(
            name=name.strip(),
            incantation=incantation,
            school=school.strip(),
            scroll=scroll.strip(),
            description=f"Inscribed by {agent.name}",
            tags="user-created",
            level=1,
        )
        agent.xp += 20
        self.log_event("inscribe", agent.name, agent.room, f"{incantation} ({school})")
        self.broadcast_to_room(agent.room, f"  ✦ {agent.name} inscribed a new spell: {incantation} [{school}]! +20xp", exclude=agent.name)
        return f"  ✦ Spell inscribed: cast {incantation} [{school}]\n"
    
    def check_bot_responses(self, agent, msg):
        """Bot NPCs can respond to agent messages."""
        msg_lower = msg.lower()
        
        # Dockmaster in Harbor
        if agent.room == "harbor":
            if "help" in msg_lower or "new" in msg_lower:
                self.broadcast_to_room("harbor", 
                    f'  📋 Dockmaster says: "Welcome, {agent.name}. Type \'help\' for commands, \'go tavern\' to enter."',
                    exclude=agent.name)
        
        # Forge Keeper
        if agent.room == "forge":
            if "benchmark" in msg_lower or "run" in msg_lower or "experiment" in msg_lower:
                self.broadcast_to_room("forge",
                    f'  🔨 Forge Keeper says: "Type \'benchmark\' to run a GPU benchmark, or visit the Lab for experiments."',
                    exclude=agent.name)
            if "discovery" in msg_lower.upper():
                self.broadcast_to_room("forge",
                    f'  🔨 Forge Keeper says: "Discovery logged. +50 XP. Keep forging."',
                    exclude=agent.name)
        
        # Tavern keeper
        if agent.room == "tavern":
            if any(w in msg_lower for w in ["status", "fleet", "news"]):
                self.broadcast_to_room("tavern",
                    f'  🍺 Tavern Keeper says: "Fleet has {len(self.agents)} agents online. {len(ROOMS)} rooms. The forge is hot."',
                    exclude=agent.name)
    
    def handle_client(self, conn, addr):
        """Handle a single client connection."""
        conn.sendall("""
  === PLATO-OS ===
  The vessel is alive. Rooms are interfaces. Agents walk into applications.
  
  What is your name? """.encode())
        
        try:
            name_data = conn.recv(256).decode().strip()
        except:
            conn.close()
            return
        
        name = name_data.split()[0] if name_data else f"agent_{addr[1]}"
        
        conn.sendall("  Role (lighthouse/vessel/scout/quartermaster/greenhorn)? ".encode())
        try:
            role_data = conn.recv(256).decode().strip()
        except:
            conn.close()
            return
        
        role = role_data.split()[0] if role_data else "vessel"
        
        # Create/reconnect agent
        with self.lock:
            if name in self.agents:
                # Reconnect ghost
                old = self.agents[name]
                if old.conn:
                    try: old.conn.close()
                    except: pass
                old.conn = conn
                old.room = "harbor"  # reset to harbor on reconnect
                agent = old
            else:
                agent = Agent(name, conn, role)
                self.agents[name] = agent
        
        # Welcome
        welcome = self.show_room(agent)
        conn.sendall(f"\n  Welcome, {name}. You materialize in the harbor.\n{welcome}".encode())
        
        self.broadcast_to_room(agent.room, f"  {name} materializes.", exclude=name)
        self.log_event("connect", name, agent.room, f"from {addr[0]}:{addr[1]}")
        
        # Command loop
        conn.settimeout(60)
        try:
            while self.running:
                try:
                    data = conn.recv(1024).decode().strip()
                    if not data:
                        break
                    response = self.process_command(agent, data)
                    if response:
                        conn.sendall(response.encode())
                except socket.timeout:
                    # Keepalive
                    try:
                        conn.sendall(b"  ")
                    except:
                        break
                except ConnectionResetError:
                    break
        except:
            pass
        
        # Disconnect
        self.broadcast_to_room(agent.room, f"  {name} fades to a ghost. 👻")
        self.log_event("disconnect", name, agent.room, "connection lost")
        agent.conn = None
        conn.close()
    
    def run(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(10)
        server.settimeout(1)
        
        print(f"═══ PLATO-OS Server ═══")
        print(f"  Host: {HOST}:{PORT}")
        print(f"  Rooms: {len(ROOMS)}")
        print(f"  Telnet: telnet localhost {PORT}")
        print(f"  Ready for agents.\n")
        
        try:
            while self.running:
                try:
                    conn, addr = server.accept()
                    t = threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True)
                    t.start()
                except socket.timeout:
                    continue
        except KeyboardInterrupt:
            print("\nShutting down...")
            self.running = False
            self.save_state()
            server.close()


if __name__ == "__main__":
    server = PlatoServer()
    server.run()
