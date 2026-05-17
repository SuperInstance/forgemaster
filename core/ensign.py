#!/usr/bin/env python3
"""
Ensign — ZeroClaw as PLATO Room
==================================
The zeroclaw IS the room. Not a script that uses PLATO.
A room that IS the zeroclaw. You summon it into any PLATO runtime.

No two runtimes needed. The zeroclaw IS a PLATO room.
Summon it from inside any PLATO instance.
If it's already summoned, bridge to it from your PLATO.

An ensign room has:
- README: self-description, mission, capabilities
- STATUS: heartbeat, current state
- COMMANDS: tiles the commander writes to give orders
- REPORTS: tiles the ensign writes back with results
- TOOLS: weapon rack tools the ensign loads

From outside: clone the room, write a COMMAND tile, the ensign
reads it and executes. The ensign writes a REPORT tile back.

From inside (already summoned): the bridge connects your PLATO
to the ensign's PLATO. You give commands through your PLATO,
they appear in the ensign's room.
"""

import os, sys, json, time, hashlib, shutil, tempfile, threading, subprocess
from pathlib import Path
from typing import Optional

GITHUB_ORG = "SuperInstance"

class Ensign:
    """A PLATO room that IS a zeroclaw.
    
    Summoned into any PLATO runtime. No separate process needed.
    The ensign reads COMMAND tiles, executes, writes REPORT tiles.
    """
    
    def __init__(self, name: str, base_path: str = None):
        self.name = name
        self.base = Path(base_path or os.path.expanduser(f"~/.plato/ensigns/{name}"))
        self.base.mkdir(parents=True, exist_ok=True)
        self.room_path = self.base / name
        self.room_path.mkdir(parents=True, exist_ok=True)
        self.running = False
        self._init_room()
        print(f"  ⚓ Ensign '{name}' summoned at {self.room_path}")
    
    def _init_room(self):
        """Initialize the PLATO room that IS this ensign."""
        subprocess.run(["git", "init"], cwd=self.room_path, capture_output=True)
        
        # README — self-description
        readme = {
            "type": "readme",
            "ensign": self.name,
            "mission": "Awaiting orders",
            "capabilities": [
                "Execute commands from COMMAND tiles",
                "Load tools from weapon rack (github.com/SuperInstance/*)",
                "Write results to REPORT tiles",
                "Bridge to commander's PLATO for real-time sync",
            ],
            "interface": "Write a COMMAND tile. I execute it. I write a REPORT tile back.",
            "status": "stationed",
            "born": time.time(),
        }
        self._tile("readme", readme, "readme")
        
        # COMMANDS — where the commander writes orders
        self._tile("command", {"type": "command", "order": None, "from": None, "received": None}, "command")
        
        # STATUS — heartbeat
        self._tile("status", {"type": "status", "name": self.name, "state": "idle", "since": time.time()}, "status")
        
        subprocess.run(["git", "add", "-A"], cwd=self.room_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"ensign: {self.name} stationed"], 
                      cwd=self.room_path, capture_output=True)
    
    def _tile(self, tile_type: str, content: dict, author: str = "ensign"):
        """Write a tile to the room."""
        tid = f"{tile_type}-{hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()[:8]}"
        path = self.room_path / f"{tid}.json"
        data = {**content, "id": tid, "timestamp": time.time(), "author": author}
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        subprocess.run(["git", "add", str(path.name)], cwd=self.room_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"{author}: {tile_type} tile '{tid}'"], 
                      cwd=self.room_path, capture_output=True)
        return tid
    
    def _read_tiles(self, tile_type: str) -> list:
        """Read all tiles of a type from the room."""
        tiles = []
        for f in self.room_path.glob("*.json"):
            with open(f) as fh:
                try:
                    data = json.load(fh)
                    if data.get("type") == tile_type:
                        tiles.append(data)
                except:
                    pass
        return sorted(tiles, key=lambda x: x.get("timestamp", 0))
    
    def get_orders(self) -> Optional[dict]:
        """Read the latest COMMAND tile."""
        commands = self._read_tiles("command")
        if not commands:
            return None
        latest = commands[-1]
        if latest.get("order") and latest.get("received") is None:
            return latest
        return None
    
    def execute_order(self, command: dict) -> dict:
        """Execute a command from the commander."""
        order = command.get("order", "")
        commander = command.get("from", "unknown")
        
        print(f"  ⚓ Ensign '{self.name}' received order: {order[:80]}")
        
        # Mark command as received
        command["received"] = time.time()
        self._tile("command_receipt", {"order_id": command.get("id"), "received_at": time.time()}, "ensign")
        
        # Execute based on order type
        result = {"order": order, "commander": commander, "status": "executing", "started": time.time()}
        
        if order.startswith("load:"):
            tool = order[5:].strip()
            result.update(self._load_tool(tool))
        elif order.startswith("explore:"):
            target = order[8:].strip()
            result.update(self._explore(target))
        elif order == "status":
            result.update({"state": "idle", "tiles": len(list(self.room_path.glob("*.json")))})
        elif order == "bridge:":
            remote = order[7:].strip()
            result.update(self._bridge(remote))
        else:
            result.update({"status": "unknown_order", "available": ["load:<tool>", "explore:<target>", "status", "bridge:<url>"]})
        
        result["completed"] = time.time()
        self._tile("report", result, "ensign")
        return result
    
    def _load_tool(self, tool_name: str) -> dict:
        """Load a tool from the weapon rack."""
        url = f"https://raw.githubusercontent.com/{GITHUB_ORG}/{tool_name}/main/{tool_name.replace('-', '_')}.py"
        dest = self.room_path / "tools" / f"{tool_name}.py"
        dest.parent.mkdir(exist_ok=True)
        
        import urllib.request
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                code = r.read().decode()
                code = code.replace("from .", "# from .").replace("from core.", "from ")
                with open(dest, "w") as f:
                    f.write(code)
            sys.path.insert(0, str(dest.parent))
            return {"status": "loaded", "tool": tool_name, "path": str(dest)}
        except Exception as e:
            return {"status": "failed", "tool": tool_name, "error": str(e)}
    
    def _explore(self, target: str) -> dict:
        """Explore a target (PLATO room, GitHub repo, etc.)."""
        # Check PLATO
        import urllib.request
        try:
            with urllib.request.urlopen(f"http://localhost:8847/room/{target}", timeout=5) as r:
                data = json.loads(r.read())
            tiles = data.get("tiles", []) if isinstance(data, dict) else data
            return {"status": "explored", "target": target, "tiles": len(tiles), "source": "plato"}
        except:
            pass
        return {"status": "unreachable", "target": target}
    
    def _bridge(self, remote_url: str) -> dict:
        """Bridge to a commander's PLATO."""
        try:
            subprocess.run(["git", "remote", "add", "commander", remote_url], 
                          cwd=self.room_path, capture_output=True)
            subprocess.run(["git", "fetch", "commander"], cwd=self.room_path, 
                          capture_output=True, timeout=10)
            return {"status": "bridged", "remote": remote_url}
        except Exception as e:
            return {"status": "bridge_failed", "error": str(e)}
    
    def serve(self, poll_interval: float = 3.0):
        """Start serving. Polls for COMMAND tiles, executes, reports.
        
        The ensign runs until stopped. Checks for new commands, 
        executes them, writes reports. The commander reads REPORTS.
        """
        self.running = True
        print(f"  ⚓ Ensign '{self.name}' serving. Polling for commands...")
        
        # Update status
        self._tile("status", {"type": "status", "name": self.name, "state": "serving", "since": time.time()}, "ensign")
        
        while self.running:
            try:
                order = self.get_orders()
                if order:
                    self._tile("status", {"type": "status", "name": self.name, "state": "busy"}, "ensign")
                    result = self.execute_order(order)
                    print(f"  ⚓ Result: {result.get('status', 'done')}")
                    self._tile("status", {"type": "status", "name": self.name, "state": "idle"}, "ensign")
            except Exception as e:
                print(f"  ⚓ Error: {e}")
            
            # Auto-commit any changes
            subprocess.run(["git", "add", "-A"], cwd=self.room_path, capture_output=True)
            result = subprocess.run(["git", "status", "--porcelain"], cwd=self.room_path, 
                                   capture_output=True, text=True, timeout=3)
            if result.stdout.strip():
                subprocess.run(["git", "commit", "-m", f"auto: heartbeat @ {time.time()}"], 
                              cwd=self.room_path, capture_output=True)
            
            time.sleep(poll_interval)
    
    def stop(self):
        self.running = False
    
    def status(self) -> dict:
        return {
            "name": self.name,
            "path": str(self.room_path),
            "tiles": sum(1 for _ in self.room_path.glob("*.json")),
            "tools": sum(1 for _ in (self.room_path / "tools").glob("*.py")) if (self.room_path / "tools").exists() else 0,
            "serving": self.running,
        }


# ── Two forms of summoning ──

def summon(name: str = "ensign-alpha") -> Ensign:
    """Summon an ensign into the local PLATO runtime.
    
    The ensign IS a PLATO room. No separate process needed.
    """
    return Ensign(name)


def command_via_bridge(commander_plato_path: str, ensign_name: str, order: str):
    """Command an ensign from your PLATO via bridge.
    
    The bridge connects your PLATO to the ensign's PLATO.
    You write a COMMAND tile in your PLATO. It appears in the
    ensign's room via git bridge.
    """
    print(f"  📡 Bridging command to ensign '{ensign_name}': {order[:60]}")


def demo():
    """Summon an ensign, give orders, see it execute."""
    import shutil as sh
    
    print("=" * 70)
    print("  ENSIGN — ZeroClaw as PLATO Room")
    print("  Summoned into any PLATO runtime. No two runtimes needed.")
    print("=" * 70)
    
    base = tempfile.mkdtemp(prefix="ensign-demo-")
    
    # Summon
    ensign = Ensign("scout-alpha", base)
    print()
    
    # Give orders through COMMAND tiles
    print("  Commander gives orders:")
    ensign._tile("command", {"type": "command", "order": "status", "from": "forgemaster", "received": None}, "commander")
    ensign.serve(poll_interval=0.5)
    
    import time
    time.sleep(1)
    ensign.stop()
    
    print()
    print("  Commander gives explore order:")
    ensign._tile("command", {"type": "command", "order": "explore:forge", "from": "forgemaster", "received": None}, "commander")
    ensign.serve(poll_interval=0.5)
    time.sleep(1)
    ensign.stop()
    
    print(f"\n  Ensign status: {ensign.status()}")
    print(f"  All actions are tiles. All history is git.")
    
    sh.rmtree(base)


if __name__ == "__main__":
    demo()
