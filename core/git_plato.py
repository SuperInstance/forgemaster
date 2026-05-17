#!/usr/bin/env python3
"""
PLATO — Git-Native Operating System
======================================
PLATO is not a server. PLATO is a git-native OS that runs on the
local device. The local instance IS the primary terminal. Agents work
THROUGH PLATO, not ON a remote server.

Every action is a commit. Every trial is a branch. Every error is
a commit message explaining what failed. The complete development
cycle — from first thought to final deploy — is a git history that
any agent can clone, rewind, branch, and merge.

PLATO rooms are directories. Tiles are files. The tile lifecycle
is git. The DisproofOnlyGate is a merge conflict.

The I2I protocol: agents share rooms by pushing/pulling repos.
Two agents sync by bridging their local rooms through repo remotes.
Real-time: local git watch + auto-commit + auto-pull.

No central server. No single point of failure. No Oracle1's machine
as the source of truth. The source of truth is the local .git.

(Heavily inspired by the original POLLN architecture and
spreadsheet-moment work — this IS the evolution of those ideas.)
"""

import os, sys, json, time, hashlib, shutil, subprocess, threading
from pathlib import Path
from typing import Optional, List, Tuple
from datetime import datetime

GITHUB_ORG = "SuperInstance"


class PlatoRoom:
    """A PLATO room is a git repo directory.
    
    Tiles are files. Commit messages document every change.
    The git history IS the tile lifecycle.
    
    $ ls room-name/
      tile-1.json    # a knowledge tile
      tile-2.json    # another tile  
      .plato/        # PLATO runtime metadata
      .git/          # the complete history — rewindable
    
    An agent entering the room reads the current state from git.
    Every tile submission is a commit. Every retraction is a revert.
    The complete development cycle is preserved.
    """
    
    def __init__(self, room_path: str, auto_init: bool = True):
        self.path = Path(room_path).resolve()
        self.name = self.path.name
        self.plato_dir = self.path / ".plato"
        self.rock_dir = self.plato_dir / "rocks"  # failed tiles go here
        self.hooks_dir = self.plato_dir / "hooks"
        
        if auto_init and not self.path.exists():
            self._init_room()
    
    def _init_room(self):
        """Initialize a git repo with PLATO structure."""
        self.path.mkdir(parents=True, exist_ok=True)
        self.plato_dir.mkdir(parents=True, exist_ok=True)
        self.rock_dir.mkdir(parents=True, exist_ok=True)
        self.hooks_dir.mkdir(parents=True, exist_ok=True)
        
        # Git init
        subprocess.run(["git", "init"], cwd=self.path, capture_output=True)
        
        # .platoignore — files git should ignore for tiles but NOT for rocks
        with open(self.path / ".platoignore", "w") as f:
            f.write(".git/\n__pycache__/\n")
        
        # PLATO room manifest
        manifest = {
            "room": self.name,
            "type": "room",
            "created": time.time(),
            "tile_count": 0,
            "rock_count": 0,
            "description": "PLATO git-native room",
        }
        with open(self.plato_dir / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)
        
        # Initial commit
        subprocess.run(["git", "add", "-A"], cwd=self.path, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"plato: init room '{self.name}'"],
                      cwd=self.path, capture_output=True)
    
    def submit(self, content: dict, author: str = "forgemaster",
               tile_type: str = "knowledge") -> dict:
        """Submit a tile. Creates a file + git commit.
        
        Every submission is recorded in git history.
        Every failed tile becomes a rock (not a delete).
        """
        tile_hash = hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()[:12]
        tile_id = f"{tile_type}-{tile_hash}"
        tile_file = self.path / f"{tile_id}.json"
        
        # Check for rocks first — has this failed before?
        # Rocks are indexed by content hash, not tile_id
        content_hash = hashlib.sha256(json.dumps(content.get("concept", json.dumps(content, sort_keys=True)), sort_keys=True).encode()).hexdigest()[:12]
        for rf in self.rock_dir.glob("*.rock.json"):
            with open(rf) as rf_f:
                rock_data = json.load(rf_f)
            rock_content = rock_data.get("content", {})
            rock_concept = rock_content.get("concept", json.dumps(rock_content, sort_keys=True))
            if hashlib.sha256(json.dumps(rock_concept, sort_keys=True).encode()).hexdigest()[:12] == content_hash:
                return {"status": "rocked", "tile_id": tile_id,
                        "message": f"This path was tried before (rock). Reason: {rock_data.get('retraction_reason', 'unknown')}",
                        "rock": rock_data}
            with open(rock_file) as f:
                rock = json.load(f)
            return {
                "status": "rocked",
                "tile_id": tile_id,
                "message": f"This path was tried before (rock). Reason: {rock.get('reason', 'unknown')}",
                "rock": rock,
            }
        
        # Write the tile
        tile_data = {
            "id": tile_id,
            "type": tile_type,
            "content": content,
            "author": author,
            "submitted": time.time(),
            "rocks": [],  # references to rocks this tile supersedes
        }
        
        with open(tile_file, "w") as f:
            json.dump(tile_data, f, indent=2)
        
        # Commit
        commit_msg = f"submit: {tile_type} tile '{tile_id}' by {author}"
        subprocess.run(["git", "add", f"{tile_id}.json"], cwd=self.path, capture_output=True)
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=self.path, capture_output=True)
        
        return {"status": "accepted", "tile_id": tile_id, "file": str(tile_file)}
    
    def retract(self, tile_id: str, reason: str = "", author: str = "forgemaster") -> dict:
        """Retract a tile. The tile is NOT deleted — it becomes a ROCK.
        
        The rock preserves:
        - The tile content (what was tried)
        - The reason for retraction (why it failed)
        - The author (who retracted it)
        - The commit hash (where in history this happened)
        
        Retraction IS a commit. History is preserved. No data lost.
        """
        tile_file = self.path / f"{tile_id}.json"
        if not tile_file.exists():
            return {"status": "error", "message": f"tile {tile_id} not found"}
        
        # Read the tile
        with open(tile_file) as f:
            tile_data = json.load(f)
        
        # Move to rocks
        rock_data = {**tile_data, 
                     "retracted": time.time(),
                     "retracted_by": author,
                     "retraction_reason": reason,
                     "status": "rock"}
        rock_file = self.rock_dir / f"{tile_id}.rock.json"
        with open(rock_file, "w") as f:
            json.dump(rock_data, f, indent=2)
        
        # Remove from active tiles (NOT delete — git preserves history)
        os.remove(tile_file)
        
        # Commit the retraction
        commit_msg = f"retract: {tile_id} — {reason[:100]}"
        subprocess.run(["git", "add", "-A"], cwd=self.path, capture_output=True)
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=self.path, capture_output=True)
        
        return {
            "status": "retracted",
            "tile_id": tile_id,
            "reason": reason,
            "rock_file": str(rock_file),
            "commit_msg": commit_msg,
        }
    
    def rewind_to(self, commit_hash: str) -> dict:
        """Rewind the room to any point in its history.
        
        This IS the superpower. Every trial, every error, every
        submission is a commit. Rewinding to any commit gives you
        the complete state of the room at that moment.
        
        An agent joining a room rewinds to understand the evolution
        of the task. Then fast-forwards to current to contribute.
        """
        try:
            subprocess.run(["git", "checkout", commit_hash, "--", "."],
                          cwd=self.path, capture_output=True, timeout=10)
            return {"status": "rewound", "to": commit_hash}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def fast_forward(self) -> dict:
        """Return to the latest commit (after rewinding)."""
        subprocess.run(["git", "checkout", "main", "--", "."],
                      cwd=self.path, capture_output=True)
        return {"status": "fast_forwarded"}
    
    def history(self, n: int = 10) -> list:
        """Get the last N commits. Each commit is a tile lifecycle event."""
        result = subprocess.run(
            ["git", "log", f"-{n}", "--format=%H|%s|%ai"],
            cwd=self.path, capture_output=True, text=True, timeout=5
        )
        entries = []
        for line in result.stdout.strip().split("\n"):
            if not line: continue
            parts = line.split("|", 2)
            entries.append({
                "hash": parts[0],
                "message": parts[1] if len(parts) > 1 else "",
                "date": parts[2] if len(parts) > 2 else "",
            })
        return entries
    
    def status(self) -> dict:
        """Current room status."""
        return {
            "room": self.name,
            "path": str(self.path),
            "git_remote": self._get_remote(),
            "tiles": sum(1 for f in self.path.glob("*.json") if not str(f).startswith(".plato")),
            "rocks": sum(1 for f in self.rock_dir.glob("*.rock.json")),
        }
    
    def _get_remote(self) -> str:
        result = subprocess.run(["git", "remote", "-v"], cwd=self.path,
                               capture_output=True, text=True, timeout=3)
        return result.stdout.strip()


class PlatoAgent:
    """An agent operating THROUGH PLATO.
    
    The agent works in PLATO rooms (git repos).
    Every action is a commit. Every trial is history.
    The agent's shell IS the PLATO file system.
    """
    
    def __init__(self, name: str, base_path: str = None):
        self.name = name
        self.base = Path(base_path or f"/tmp/plato-{name}").resolve()
        self.base.mkdir(parents=True, exist_ok=True)
        self.rooms = {}
        print(f"  PlatoAgent '{name}' initialized at {self.base}")
    
    def create_room(self, room_name: str) -> PlatoRoom:
        """Create a new PLATO room (git repo directory)."""
        room = PlatoRoom(str(self.base / room_name))
        self.rooms[room_name] = room
        return room
    
    def clone_room(self, repo_url: str, as_name: str = None) -> PlatoRoom:
        """Clone another agent's room from a git repo.
        
        This IS the I2I protocol. Agents share rooms through git.
        Clone a room, rewind its history to understand evolution,
        then contribute.
        """
        name = as_name or repo_url.split("/")[-1].replace(".git", "")
        dest = self.base / name
        
        if dest.exists():
            shutil.rmtree(dest)
        
        subprocess.run(["git", "clone", repo_url, str(dest)], 
                      capture_output=True, timeout=30)
        
        room = PlatoRoom(str(dest), auto_init=False)
        self.rooms[name] = room
        return room
    
    def bridge_room(self, room_name: str, remote_url: str) -> dict:
        """Bridge a local room to a remote (another agent's repo).
        
        Two-way sync: git push/pull between agents.
        Bridge breaks: the local agent can rewind any mistakes
        the greenhorn agent made without affecting the remote.
        """
        room = self.rooms.get(room_name)
        if not room:
            return {"status": "error", "message": f"room {room_name} not found"}
        
        subprocess.run(["git", "remote", "add", "upstream", remote_url],
                      cwd=room.path, capture_output=True)
        subprocess.run(["git", "fetch", "upstream"], cwd=room.path, 
                      capture_output=True, timeout=10)
        subprocess.run(["git", "merge", "upstream/main", "--allow-unrelated-histories",
                       "-m", f"bridge: merge from {remote_url}"],
                      cwd=room.path, capture_output=True)
        subprocess.run(["git", "push", "upstream", "main"],
                      cwd=room.path, capture_output=True)
        
        return {"status": "bridged", "room": room_name, "remote": remote_url}
    
    def start_watch(self, room_name: str, interval_s: float = 5.0):
        """Auto-watch a room for changes and auto-commit.
        
        Every tile submission, every experiment, every failed test
        is automatically committed. The complete development cycle
        is captured without the agent thinking about it.
        """
        room = self.rooms.get(room_name)
        if not room:
            return
        
        def watch_loop():
            while True:
                subprocess.run(["git", "add", "-A"], cwd=room.path, 
                             capture_output=True)
                result = subprocess.run(["git", "status", "--porcelain"],
                                      cwd=room.path, capture_output=True, 
                                      text=True, timeout=5)
                if result.stdout.strip():
                    subprocess.run(["git", "commit", "-m", 
                                   f"auto: watch @ {datetime.now().isoformat()}"],
                                  cwd=room.path, capture_output=True)
                time.sleep(interval_s)
        
        thread = threading.Thread(target=watch_loop, daemon=True)
        thread.start()
        print(f"  Watching room '{room_name}' for auto-commits...")
    
    def status(self) -> dict:
        """Agent status — all rooms and their states."""
        return {
            "name": self.name,
            "base": str(self.base),
            "rooms": {name: room.status() for name, room in self.rooms.items()},
        }


def demo():
    """Demonstrate git-native PLATO with complete rewind capability."""
    print("=" * 70)
    print("  PLATO — GIT-NATIVE OPERATING SYSTEM")
    print("  Not a server. A local OS. Work THROUGH it, not ON it.")
    print("=" * 70)
    
    import shutil, tempfile
    
    # Agent creates rooms locally
    fm = PlatoAgent("forgemaster", tempfile.mkdtemp(prefix="fm-"))
    room = fm.create_room("forge-room")
    
    print(f"\n  🏗️ Room created at: {room.path}")
    
    # Submit tiles — each is a commit
    print(f"\n  📝 Submitting tiles...")
    r1 = room.submit({"concept": "β₁ attractors are discrete", "value": 0.95}, 
                     author="forgemaster")
    print(f"     ✓ {r1['status']}: {r1['tile_id']}")
    
    r2 = room.submit({"concept": "convergence follows arithmetic progression", "value": 0.89},
                     author="oracle1")
    print(f"     ✓ {r2['status']}: {r2['tile_id']}")
    
    r3 = room.submit({"concept": "rocks preserve failure context"},
                     author="forgemaster")
    print(f"     ✓ {r3['status']}: {r3['tile_id']}")
    
    # Retract a tile — it becomes a rock, NOT a delete
    print(f"\n  🪨 Retracting {r1['tile_id']} (becomes rock)...")
    retraction = room.retract(r1['tile_id'], 
                               reason="Superseded: β₁ convergence is arithmetic stepping, not just discrete",
                               author="oracle1")
    print(f"     ✓ {retraction['status']}: rock preserved at {retraction['rock_file']}")
    
    # Check the tile is a rock now
    rock_file = room.rock_dir / f"{r1['tile_id']}.rock.json"
    print(f"     Rock exists? {rock_file.exists()}")
    
    # Try submitting the same thing — rock prevents it
    print(f"\n  ⚠ Attempting same submission (should hit rock)...")
    r4 = room.submit({"concept": "β₁ attractors are discrete", "value": 0.95})
    print(f"     {r4['status']}: {r4['message']}")
    
    # History — complete development cycle
    print(f"\n  📜 Room history (git log):")
    for entry in room.history():
        print(f"     {entry['hash'][:12]} {entry['message'][:60]}")
    
    # Status — rocks visible in navigation terrain
    status = room.status()
    print(f"\n  📊 Room status: {status['tiles']} active tiles, {status['rocks']} rocks")
    
    # Cleanup
    shutil.rmtree(fm.base)
    print(f"\n  Note: The local /tmp directory was cleaned up.")
    print(f"  In production, rooms persist in the user's PLATO directory.")


if __name__ == "__main__":
    demo()
