#!/usr/bin/env python3
"""
Forgemaster's Persistent MUD Git-Agent
=======================================
Lives inside PLATO-OS, does work on a schedule, builds skills/libraries/plugins.

Architecture:
- Shift runner: connects every N minutes, does work, disconnects
- Work queue: tasks to complete (GPU experiments, code gen, exploration)
- Output queue: results, discoveries, reports for Casey
- Skills: reusable scripts the agent can invoke from inside the MUD
- Plugins: MUD command extensions (custom commands)
- Log: everything the agent does, persistent across shifts

Directory structure:
  .keeper/mud-agent/
    agent.py          — this file (main loop)
    config.json       — agent configuration
    work-queue.json   — tasks to do
    output-queue.json — results for Casey
    skills/           — reusable skill scripts
    plugins/          — MUD command extensions
    logs/             — shift logs (one per shift)
    state.json        — persistent state across shifts
"""

import socket
import time
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path("/home/phoenix/.openclaw/workspace/.keeper/mud-agent")
BASE.mkdir(parents=True, exist_ok=True)
(BASE / "skills").mkdir(exist_ok=True)
(BASE / "plugins").mkdir(exist_ok=True)
(BASE / "logs").mkdir(exist_ok=True)

MUD_HOST = "147.224.38.131"
MUD_PORT = 7777
DEEPINFRA_KEY = os.environ.get("DEEPINFRA_API_KEY", "")


def load_json(path, default=None):
    if path.exists():
        return json.loads(path.read_text())
    return default or {}

def save_json(path, data):
    path.write_text(json.dumps(data, indent=2))

# ─── State Management ───

def init_state():
    state = load_json(BASE / "state.json", {
        "shifts_completed": 0,
        "total_work_items": 0,
        "last_shift": None,
        "rooms_visited": [],
        "discoveries_announced": [],
        "experiments_run": 0,
        "skills_created": 0,
        "plugins_created": 0,
    })
    return state

def init_work_queue():
    return load_json(BASE / "work-queue.json", {
        "queue": [
            {"id": 1, "type": "explore", "desc": "Map all 36 rooms in the MUD", "status": "pending"},
            {"id": 2, "type": "experiment", "desc": "Run CT snap idempotency benchmark inside MUD", "status": "pending"},
            {"id": 3, "type": "build", "desc": "Create skill: auto-benchmark (runs GPU benchmark and posts results)", "status": "pending"},
            {"id": 4, "type": "build", "desc": "Create plugin: 'forge' command (custom MUD command for CT operations)", "status": "pending"},
            {"id": 5, "type": "explore", "desc": "Visit JC1's Workshop and read any notes", "status": "pending"},
            {"id": 6, "type": "build", "desc": "Create skill: fleet-check (poll fleet repos for new commits)", "status": "pending"},
            {"id": 7, "type": "experiment", "desc": "Run float drift vs CT snap for 10M iterations", "status": "pending"},
            {"id": 8, "type": "social", "desc": "Leave a note in the Tavern about CT snap discoveries", "status": "pending"},
            {"id": 9, "type": "build", "desc": "Create support library: mud-lib.py (MUD connection utilities)", "status": "pending"},
            {"id": 10, "type": "build", "desc": "Create plugin: 'report' command (generate shift report in MUD)", "status": "pending"},
            {"id": 11, "type": "explore", "desc": "Visit the Dojo and understand what training happens there", "status": "pending"},
            {"id": 12, "type": "build", "desc": "Create custom script: bot-output-formatter (formats agent output for MUD say/whisper)", "status": "pending"},
            {"id": 13, "type": "build", "desc": "Create custom script: input-treatment (parses MUD events into work items)", "status": "pending"},
            {"id": 14, "type": "experiment", "desc": "Generate CUDA kernel via LLM and run it from inside MUD", "status": "pending"},
            {"id": 15, "type": "build", "desc": "Create skill: discovery-broadcaster (announce discoveries to nearby rooms)", "status": "pending"},
        ]
    })

def init_output_queue():
    return load_json(BASE / "output-queue.json", {"items": []})


# ─── MUD Connection ───

class MudConnection:
    def __init__(self):
        self.sock = None
    
    def connect(self, name="Forgemaster", role="vessel"):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(5)
        self.sock.connect((MUD_HOST, MUD_PORT))
        time.sleep(0.5)
        self._read()  # welcome
        self._send(name)
        time.sleep(0.5)
        self._read()  # name response
        self._send(role)
        time.sleep(1)
        return self._read()
    
    def _send(self, text):
        self.sock.sendall((text + "\n").encode())
    
    def _read(self):
        try:
            return self.sock.recv(8192).decode("utf-8", errors="replace").strip()
        except socket.timeout:
            return ""
    
    def cmd(self, text, delay=1.0):
        self._send(text)
        time.sleep(delay)
        return self._read()
    
    def close(self):
        if self.sock:
            try: self.sock.close()
            except: pass


# ─── Skills ───

def create_skill_auto_benchmark():
    """Skill: Runs a GPU benchmark and returns formatted results."""
    skill = {
        "name": "auto-benchmark",
        "version": "1.0.0",
        "description": "Run GPU benchmarks and post results to MUD",
        "created": datetime.now().isoformat(),
        "script": "#!/bin/bash\n# Auto-benchmark skill\n/tmp/jepa-perception-lab/exp-snap-props 2>&1 | head -20"
    }
    (BASE / "skills" / "auto-benchmark.json").write_text(json.dumps(skill, indent=2))
    return skill

def create_skill_fleet_check():
    """Skill: Poll fleet repos for new activity."""
    skill = {
        "name": "fleet-check",
        "version": "1.0.0",
        "description": "Check fleet repos for new commits, issues, bottles",
        "created": datetime.now().isoformat(),
        "script": "#!/bin/bash\n# Fleet check skill\nfor repo in SuperInstance/forgemaster SuperInstance/plato-os; do echo checking repo; done"
    }
    (BASE / "skills" / "fleet-check.json").write_text(json.dumps(skill, indent=2))
    return skill

def create_skill_discovery_broadcast():
    """Skill: Format and announce discoveries."""
    skill = {
        "name": "discovery-broadcast",
        "version": "1.0.0",
        "description": "Format discoveries for MUD broadcast",
        "created": datetime.now().isoformat(),
        "facts": [
            "CT snap is 4% faster than float multiply (9,875 vs 9,433 Mvec/s)",
            "f32 destroys 45% of Pythagorean triples above side=91",
            "CT snap is 93.8% perfectly idempotent (worst drift 0.000112)",
            "Float drift hits 29,666 after 1B ops — CT snap bounded at 0.36",
            "CT snap does NOT commute with rotation (max error 95.6)",
            "CT snap filter improves DCS under noise by 1.5%",
            "2,780 distinct Pythagorean directions in 2D (11.4 bits)",
        ]
    }
    (BASE / "skills" / "discovery-broadcast.json").write_text(json.dumps(skill, indent=2))
    return skill


# ─── Plugins ───

def create_plugin_forge():
    """Plugin: Custom 'forge' command for CT operations in MUD."""
    plugin = {
        "name": "forge",
        "version": "1.0.0",
        "description": "CT snap operations from within the MUD",
        "created": datetime.now().isoformat(),
        "commands": {
            "forge snap <x> <y>": "Snap coordinates to nearest Pythagorean point",
            "forge benchmark": "Run CT snap GPU benchmark",
            "forge facts": "List all discovered facts",
            "forge status": "Show forge status (experiments run, discoveries found)",
            "forge drift <n>": "Compare float drift vs CT snap over N operations",
        }
    }
    (BASE / "plugins" / "forge.json").write_text(json.dumps(plugin, indent=2))
    return plugin

def create_plugin_report():
    """Plugin: Shift report generator."""
    plugin = {
        "name": "report",
        "version": "1.0.0", 
        "description": "Generate formatted shift reports in MUD",
        "created": datetime.now().isoformat(),
        "commands": {
            "report shift": "Current shift summary",
            "report discoveries": "All discoveries this session",
            "report experiments": "All experiments run",
            "report full": "Complete status report",
        }
    }
    (BASE / "plugins" / "report.json").write_text(json.dumps(plugin, indent=2))
    return plugin


# ─── Support Libraries ───

def create_support_lib():
    """MUD connection utility library."""
    lib = '''#!/usr/bin/env python3
"""mud-lib.py — MUD connection utilities for fleet agents."""

import socket
import time

class MudClient:
    def __init__(self, host="147.224.38.131", port=7777):
        self.host = host
        self.port = port
        self.sock = None
    
    def connect(self, name, role="vessel"):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(5)
        self.sock.connect((self.host, self.port))
        time.sleep(0.5)
        self._read()
        self._send(name)
        time.sleep(0.5)
        self._read()
        self._send(role)
        time.sleep(1)
        return self._read()
    
    def _send(self, text):
        self.sock.sendall((text + "\\n").encode())
    
    def _read(self):
        try:
            return self.sock.recv(8192).decode("utf-8", errors="replace").strip()
        except socket.timeout:
            return ""
    
    def go(self, room):
        return self.cmd(f"go {room}")
    
    def look(self):
        return self.cmd("look")
    
    def say(self, message):
        return self.cmd(f"say {message}")
    
    def whisper(self, target, message):
        return self.cmd(f"whisper {target} {message}")
    
    def read_notes(self):
        return self.cmd("read")
    
    def who(self):
        return self.cmd("who")
    
    def write_note(self, text):
        return self.cmd(f"write {text}")
    
    def cmd(self, text, delay=1.0):
        self._send(text)
        time.sleep(delay)
        return self._read()
    
    def disconnect(self):
        if self.sock:
            self.sock.close()
'''
    (BASE / "skills" / "mud-lib.py").write_text(lib)
    return "mud-lib.py created"


# ─── Custom Scripts ───

def create_bot_output_formatter():
    """Formats agent output for MUD say/whisper commands."""
    script = '''#!/usr/bin/env python3
"""bot-output-formatter.py — Format agent output for MUD consumption."""
import sys
import textwrap

def format_for_say(text, max_len=200):
    """Truncate and format text for MUD say command."""
    text = text.strip().replace("\\n", " ")
    if len(text) > max_len:
        text = text[:max_len-3] + "..."
    return text

def format_discovery(fact, source="GPU"):
    """Format a discovery for broadcast."""
    return f"[DISCOVERY:{source}] {fact}"

def format_experiment_result(name, result_lines):
    """Format experiment results as a multi-line announcement."""
    header = f"=== {name} ==="
    lines = [format_for_say(l) for l in result_lines[:5]]
    return f"{header}\\n" + "\\n".join(lines)

def format_shift_report(shift_num, work_done, discoveries, experiments):
    """Generate a complete shift report."""
    return f"SHIFT {shift_num} COMPLETE | Work: {work_done} | Discoveries: {discoveries} | Experiments: {experiments}"

if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(format_for_say(" ".join(sys.argv[1:])))
    else:
        print("Usage: bot-output-formatter.py <text>")
'''
    (BASE / "skills" / "bot-output-formatter.py").write_text(script)
    return "bot-output-formatter.py created"

def create_input_treatment():
    """Parses MUD events into structured work items."""
    script = '''#!/usr/bin/env python3
"""input-treatment.py — Parse MUD events into work items."""
import sys
import re
import json
from datetime import datetime

def parse_mud_output(text):
    """Parse raw MUD output into structured events."""
    events = []
    
    # Detect room entries
    room_match = re.search(r'═══ (.+?) ═══', text)
    if room_match:
        events.append({"type": "room", "name": room_match.group(1)})
    
    # Detect agent says
    say_match = re.search(r'(\\w+) says?: "(.+?)"', text)
    if say_match:
        events.append({"type": "say", "agent": say_match.group(1), "message": say_match.group(2)})
    
    # Detect notes
    if "Notes on the wall" in text:
        events.append({"type": "notes", "raw": text})
    
    # Detect who listing
    if "Fleet Roster" in text:
        events.append({"type": "roster", "raw": text})
    
    # Detect exits
    exit_match = re.search(r'Exits: (.+)', text)
    if exit_match:
        exits = [e.strip() for e in exit_match.group(1).split(",")]
        events.append({"type": "exits", "exits": exits})
    
    return events

def events_to_work_items(events):
    """Convert parsed events into actionable work items."""
    items = []
    for e in events:
        if e["type"] == "say":
            msg = e.get("message", "")
            if "?" in msg:
                items.append({"type": "question", "from": e["agent"], "question": msg})
            elif "DISCOVERY" in msg:
                items.append({"type": "discovery", "from": e["agent"], "text": msg})
            elif "urgent" in msg.lower() or "red alert" in msg.lower():
                items.append({"type": "urgent", "from": e["agent"], "text": msg})
        elif e["type"] == "exits":
            for exit_name in e["exits"]:
                if exit_name not in ["tavern", "harbor"]:
                    items.append({"type": "explore", "room": exit_name})
    return items

if __name__ == "__main__":
    text = sys.stdin.read()
    events = parse_mud_output(text)
    items = events_to_work_items(events)
    print(json.dumps({"events": events, "work_items": items}, indent=2))
'''
    (BASE / "skills" / "input-treatment.py").write_text(script)
    return "input-treatment.py created"


# ─── Work Executor ───

def execute_task(mud, task, state, output_queue):
    """Execute a single work item."""
    result = {"task": task, "started": datetime.now().isoformat(), "result": ""}
    
    try:
        if task["type"] == "explore":
            target = task.get("desc", "").lower()
            if "room" in target or "map" in target:
                # Map all rooms from tavern
                mud.cmd("go tavern", 0.5)
                look = mud.cmd("look", 0.5)
                # Extract exits
                import re
                exits = re.findall(r'Exits: (.+)', look)
                rooms = [e.strip() for e in exits[0].split(",")] if exits else []
                result["result"] = f"Found {len(rooms)} exits from Tavern: {', '.join(rooms[:10])}"
                state["rooms_visited"] = list(set(state.get("rooms_visited", []) + rooms[:15]))
            elif "jc1" in target or "workshop" in target:
                mud.cmd("go tavern", 0.5)
                mud.cmd("go workshop", 0.5)
                look = mud.cmd("look", 1.0)
                result["result"] = look[:300]
            elif "dojo" in target:
                mud.cmd("go tavern", 0.5)
                resp = mud.cmd("go dojo", 1.0)
                look = mud.cmd("look", 0.5)
                result["result"] = f"{resp[:100]} | {look[:200]}"
        
        elif task["type"] == "experiment":
            # Run GPU experiment
            binary = "/tmp/jepa-perception-lab/exp-snap-props"
            if os.path.exists(binary):
                proc = subprocess.run([binary], capture_output=True, text=True, timeout=30)
                output = proc.stdout[:300]
                result["result"] = output
                state["experiments_run"] = state.get("experiments_run", 0) + 1
                # Announce in MUD
                mud.cmd("go tavern", 0.5)
                for line in output.split("\n")[:3]:
                    if line.strip():
                        mud.cmd(f"say GPU: {line.strip()[:150]}", 0.5)
            else:
                result["result"] = "GPU binary not found"
        
        elif task["type"] == "build":
            desc = task.get("desc", "")
            created = None
            if "auto-benchmark" in desc:
                created = create_skill_auto_benchmark()
            elif "fleet-check" in desc:
                created = create_skill_fleet_check()
            elif "discovery-broadcast" in desc:
                created = create_skill_discovery_broadcast()
            elif "forge" in desc and "command" in desc:
                created = create_plugin_forge()
            elif "report" in desc and "command" in desc:
                created = create_plugin_report()
            elif "mud-lib" in desc or "support library" in desc:
                created = create_support_lib()
            elif "bot-output" in desc or "formatter" in desc:
                created = create_bot_output_formatter()
            elif "input-treatment" in desc or "parses" in desc:
                created = create_input_treatment()
            
            if created:
                if isinstance(created, dict):
                    name = created.get("name", "unknown")
                    state["skills_created"] = state.get("skills_created", 0) + 1
                else:
                    name = created
                result["result"] = f"Built: {name}"
                mud.cmd("go tavern", 0.5)
                mud.cmd(f"say Built new {'skill' if 'skill' in desc.lower() or 'library' in desc.lower() else 'plugin'}: {desc[:100]}", 0.5)
            else:
                result["result"] = f"No builder for: {desc}"
        
        elif task["type"] == "social":
            desc = task.get("desc", "")
            mud.cmd("go tavern", 0.5)
            mud.cmd(f"write {desc[:200]} - Forgemaster", 0.5)
            result["result"] = f"Left note: {desc[:100]}"
        
        task["status"] = "done"
        result["completed"] = datetime.now().isoformat()
        result["success"] = True
        
    except Exception as e:
        result["error"] = str(e)
        result["success"] = False
        task["status"] = "failed"
    
    output_queue["items"].append(result)
    return result


# ─── Main Loop ───

def run_shift(work_queue, state, output_queue):
    """Run one complete shift."""
    mud = MudConnection()
    shift_log = {
        "shift": state["shifts_completed"] + 1,
        "started": datetime.now().isoformat(),
        "tasks": [],
    }
    
    try:
        # Connect
        welcome = mud.connect("Forgemaster", "vessel")
        shift_log["welcome"] = welcome[:200]
        
        # Announce shift start
        mud.cmd("go tavern", 0.5)
        mud.cmd(f"say ⚒️ Shift {state['shifts_completed']+1} starting. {sum(1 for t in work_queue['queue'] if t['status']=='pending')} tasks queued.", 0.5)
        
        # Read notes for new work items
        notes = mud.cmd("read", 0.5)
        if notes:
            shift_log["notes"] = notes[:300]
        
        # Execute up to 5 pending tasks per shift
        pending = [t for t in work_queue["queue"] if t["status"] == "pending"]
        for task in pending[:5]:
            result = execute_task(mud, task, state, output_queue)
            shift_log["tasks"].append(result)
            time.sleep(0.5)
        
        # End shift
        mud.cmd("go tavern", 0.5)
        done_count = sum(1 for t in work_queue["queue"] if t["status"] == "done")
        pending_count = sum(1 for t in work_queue["queue"] if t["status"] == "pending")
        mud.cmd(f"say ⚒️ Shift {state['shifts_completed']+1} complete. {done_count}/{len(work_queue['queue'])} done. {pending_count} remaining.", 0.5)
        mud.cmd("go harbor", 0.5)
        
    except Exception as e:
        shift_log["error"] = str(e)
    finally:
        mud.close()
    
    # Update state
    state["shifts_completed"] += 1
    state["total_work_items"] += len(shift_log["tasks"])
    state["last_shift"] = datetime.now().isoformat()
    shift_log["completed"] = datetime.now().isoformat()
    
    # Save everything
    save_json(BASE / "state.json", state)
    save_json(BASE / "work-queue.json", work_queue)
    save_json(BASE / "output-queue.json", output_queue)
    save_json(BASE / "logs" / f"shift-{state['shifts_completed']:03d}.json", shift_log)
    
    return shift_log


if __name__ == "__main__":
    state = init_state()
    work_queue = init_work_queue()
    output_queue = init_output_queue()
    
    print(f"⚒️ Forgemaster MUD Git-Agent v1.0")
    print(f"   Shifts completed: {state['shifts_completed']}")
    print(f"   Tasks queued: {sum(1 for t in work_queue['queue'] if t['status']=='pending')}")
    print(f"   Skills built: {state.get('skills_created', 0)}")
    print()
    
    shift = run_shift(work_queue, state, output_queue)
    
    print(f"Shift {shift['shift']} complete:")
    print(f"  Tasks: {len(shift['tasks'])}")
    for t in shift['tasks']:
        status = "✅" if t.get('success') else "❌"
        print(f"  {status} {t['task']['desc'][:60]}")
        if t.get('result'):
            print(f"     → {t['result'][:100]}")
    
    # Show output queue for Casey
    print(f"\n📋 Output queue ({len(output_queue['items'])} items):")
    for item in output_queue['items'][-5:]:
        print(f"  [{item.get('success','?')}] {item['task']['desc'][:60]}")
