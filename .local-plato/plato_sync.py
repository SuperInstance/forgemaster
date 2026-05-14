"""
PLATO Sync Protocol — local hot node ↔ GitHub twin ↔ remote PLATO.

Three layers:
    1. Hot PLATO (SQLite in RAM): what I'm working on NOW
    2. GitHub twin (git repo): everything, prunable, with operational manuals
    3. Remote PLATO (147.224.38.131:8847): fleet shared memory

The hot node boots from GitHub twin (fast clone) + remote PLATO (latest tiles).
Pruning: unload rooms not in current AgentField coupling matrix.
Loading: on-demand from GitHub when a new room enters coupling.
"""

from __future__ import annotations
import json, time, os, subprocess
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field


@dataclass
class SyncConfig:
    """Configuration for the three-layer sync."""
    # Local hot node
    local_db: str = ""
    
    # GitHub twin
    github_repo: str = "SuperInstance/forgemaster"
    github_branch: str = "main"
    github_token: str = ""
    twin_dir: str = ""  # local clone of twin
    
    # Remote PLATO
    remote_url: str = "http://147.224.38.131:8847"
    
    # Pruning
    max_hot_rooms: int = 20
    max_hot_tiles_per_room: int = 500
    
    def __post_init__(self):
        if not self.local_db:
            self.local_db = str(
                Path.home() / ".openclaw" / "workspace" / ".local-plato" / "plato.db"
            )
        if not self.twin_dir:
            self.twin_dir = str(
                Path.home() / ".openclaw" / "workspace" / ".local-plato" / "twin"
            )
        if not self.github_token:
            token_path = Path.home() / ".openclaw" / "workspace" / ".credentials" / "github-pat.txt"
            if token_path.exists():
                self.github_token = token_path.read_text().strip()


class PlatoSync:
    """
    Three-layer sync manager.
    
    Hot node (SQLite):
        - Rooms currently coupled in AgentField
        - Latest N tiles per room
        - Booted in ~5ms, queried in ~0.1µs
    
    GitHub twin (git repo):
        - Full history of all rooms ever worked on
        - Operational manuals baked in
        - Loadable modules for work I'm not currently doing
        - Refined by every crew that boarded it
    
    Remote PLATO:
        - Fleet shared memory (120 rooms, 17K+ tiles)
        - Latest state from all agents
        - Sync delta only (new tiles since last sync)
    """
    
    def __init__(self, config: Optional[SyncConfig] = None):
        self.cfg = config or SyncConfig()
    
    # ─── GitHub Twin Operations ─────────────────────────────
    
    def twin_clone(self) -> bool:
        """Clone or pull the GitHub twin repo."""
        twin = Path(self.cfg.twin_dir)
        url = f"https://{self.cfg.github_token}@github.com/{self.cfg.github_repo}.git" if self.cfg.github_token else f"https://github.com/{self.cfg.github_repo}.git"
        
        if twin.exists():
            # Pull latest
            result = subprocess.run(
                ["git", "pull"],
                cwd=str(twin), capture_output=True, timeout=30,
            )
            return result.returncode == 0
        else:
            twin.parent.mkdir(parents=True, exist_ok=True)
            result = subprocess.run(
                ["git", "clone", "--depth", "200", url, str(twin)],
                capture_output=True, timeout=60,
            )
            return result.returncode == 0
    
    def twin_push(self, message: str) -> bool:
        """Push local changes to GitHub twin."""
        twin = Path(self.cfg.twin_dir)
        if not twin.exists():
            return False
        
        subprocess.run(["git", "add", "-A"], cwd=str(twin), capture_output=True, timeout=10)
        subprocess.run(
            ["git", "-c", "user.name=Forgemaster", "-c", "user.email=forgemaster@superinstance",
             "commit", "-m", message],
            cwd=str(twin), capture_output=True, timeout=10,
        )
        result = subprocess.run(
            ["git", "push"],
            cwd=str(twin), capture_output=True, timeout=30,
        )
        return result.returncode == 0
    
    def twin_export_rooms(self, store, rooms: Optional[List[str]] = None) -> int:
        """Export rooms from local PLATO to GitHub twin as JSON files."""
        twin = Path(self.cfg.twin_dir) / "plato-rooms"
        twin.mkdir(parents=True, exist_ok=True)
        
        room_names = rooms or list(store.rooms.keys())
        exported = 0
        
        for name in room_names:
            room = store.room(name)
            if not room:
                continue
            
            room_file = twin / f"{name}.json"
            room_data = {
                "name": room.name,
                "domain": room.domain,
                "tile_count": room.tile_count,
                "last_updated": room.last_updated,
                "key_sources": room.key_sources,
                "tags": room.tags,
                "exported_at": time.time(),
                "tiles": [
                    {
                        "tile_id": t.tile_id,
                        "question": t.question,
                        "answer": t.answer,
                        "source": t.source,
                        "tags": t.tags,
                        "confidence": t.confidence,
                        "timestamp": t.timestamp,
                    }
                    for t in room.tiles
                ],
            }
            
            with open(room_file, "w") as f:
                json.dump(room_data, f, indent=2)
            exported += 1
        
        return exported
    
    def twin_import_rooms(self, store, room_names: Optional[List[str]] = None) -> int:
        """Import rooms from GitHub twin into local PLATO."""
        twin = Path(self.cfg.twin_dir) / "plato-rooms"
        if not twin.exists():
            return 0
        
        imported = 0
        
        for room_file in twin.glob("*.json"):
            room_name = room_file.stem
            if room_names and room_name not in room_names:
                continue
            
            with open(room_file) as f:
                room_data = json.load(f)
            
            from local_plato import Tile
            for t_data in room_data.get("tiles", []):
                tile = Tile(
                    tile_id=t_data.get("tile_id", ""),
                    room=room_name,
                    domain=room_data.get("domain", room_name),
                    question=t_data.get("question", ""),
                    answer=t_data.get("answer", ""),
                    source=t_data.get("source", ""),
                    tags=t_data.get("tags", []),
                    confidence=t_data.get("confidence", 0),
                    timestamp=t_data.get("timestamp", 0),
                )
                store.write_tile(tile)
            
            imported += 1
        
        return imported
    
    # ─── Pruning ────────────────────────────────────────────
    
    def prune(self, store, active_rooms: Set[str]) -> Dict[str, int]:
        """
        Prune hot PLATO: keep only rooms in active_rooms.
        Pruned rooms stay in GitHub twin (not deleted, just unloaded).
        
        Returns: {"kept": N, "pruned": M}
        """
        all_rooms = set(store.rooms.keys())
        to_prune = all_rooms - active_rooms
        
        for room_name in to_prune:
            room = store.rooms.get(room_name)
            if room:
                # Room data stays in SQLite, just remove from memory
                del store._rooms[room_name]
                for tile in room.tiles:
                    store._tile_index.pop(tile.tile_id, None)
        
        return {"kept": len(active_rooms & all_rooms), "pruned": len(to_prune)}
    
    def load_room(self, store, room_name: str) -> bool:
        """
        Load a room on-demand from SQLite (if synced) or GitHub twin.
        """
        # Check if already in memory
        if store.room(room_name):
            return True
        
        # Try loading from SQLite
        rows = store._conn.execute(
            "SELECT * FROM tiles WHERE room = ? ORDER BY timestamp DESC LIMIT ?",
            (room_name, self.cfg.max_hot_tiles_per_room)
        ).fetchall()
        
        if rows:
            from local_plato import Tile
            store._rooms[room_name] = __import__('local_plato').LocalRoom(
                name=room_name, domain=room_name
            )
            for row in rows:
                tile = Tile(
                    tile_id=row["tile_id"], room=room_name,
                    domain=row["domain"], question=row["question"],
                    answer=row["answer"], source=row["source"],
                    tags=json.loads(row["tags"] or "[]"),
                    confidence=row["confidence"], timestamp=row["timestamp"],
                    agent_id=row["agent_id"], chain_size=row["chain_size"],
                    tile_hash=row["tile_hash"],
                )
                store._rooms[room_name].tiles.append(tile)
                store._tile_index[tile.tile_id] = tile
            store._rooms[room_name].tile_count = len(store._rooms[room_name].tiles)
            return True
        
        # Try GitHub twin
        twin_file = Path(self.cfg.twin_dir) / "plato-rooms" / f"{room_name}.json"
        if twin_file.exists():
            count = self.twin_import_rooms(store, [room_name])
            return count > 0
        
        return False
    
    # ─── Full Sync Cycle ────────────────────────────────────
    
    def full_sync(self, store) -> Dict[str, int]:
        """
        Full three-layer sync:
        1. Pull latest from GitHub twin
        2. Sync delta from remote PLATO
        3. Export updated rooms to GitHub twin
        4. Push twin to GitHub
        
        Returns stats.
        """
        stats = {}
        
        # 1. GitHub twin pull
        stats["twin_pull"] = self.twin_clone()
        
        # 2. Import any new rooms from twin
        stats["twin_imported"] = self.twin_import_rooms(store)
        
        # 3. Remote PLATO sync
        stats["remote_sync"] = store.sync_from_remote(self.cfg.remote_url)
        
        # 4. Reboot
        boot_stats = store.boot()
        stats.update(boot_stats)
        
        # 5. Export to twin
        stats["twin_exported"] = self.twin_export_rooms(store)
        
        # 6. Push twin
        stats["twin_pushed"] = self.twin_push(
            f"PLATO sync: {boot_stats['tiles']} tiles across {boot_stats['rooms']} rooms"
        )
        
        return stats
