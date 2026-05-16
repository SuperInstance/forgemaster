"""
PLATO Sync Protocol — WAL → GitHub twin auto-flush.

Three layers:
    1. Hot PLATO (SQLite in RAM): what I'm working on NOW
    2. GitHub twin (git repo): everything, prunable, with operational manuals
    3. Remote PLATO (147.224.38.131:8847): fleet shared memory

The hot node boots from GitHub twin (fast clone) + remote PLATO (latest tiles).
Pruning: unload rooms not in current AgentField coupling matrix.
Loading: on-demand from GitHub when a new room enters coupling.

WAL Auto-Flush:
    - Every 50 tiles (configurable), flush WAL to GitHub twin
    - Track sync state in .sync-state.json
    - Threaded flush so HTTP responses aren't blocked
    - Recovery on startup: flush any unsynced tiles
"""

from __future__ import annotations
import json
import os
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


@dataclass
class SyncConfig:
    """Configuration for the three-layer sync."""
    # Local hot node
    local_db: str = ""

    # GitHub twin
    github_repo: str = "SuperInstance/forgemaster"
    github_branch: str = "main"
    github_token: str = ""
    twin_dir: str = ""

    # Remote PLATO
    remote_url: str = "http://147.224.38.131:8847"

    # Pruning
    max_hot_rooms: int = 20
    max_hot_tiles_per_room: int = 500

    # WAL flush
    wal_path: str = ""
    sync_state_path: str = ""
    flush_interval: int = 50  # tiles between flushes

    def __post_init__(self):
        base = Path.home() / ".openclaw" / "workspace" / ".local-plato"
        if not self.local_db:
            self.local_db = str(base / "plato.db")
        if not self.twin_dir:
            self.twin_dir = str(base / "twin")
        if not self.wal_path:
            self.wal_path = str(base / "tile-wal.jsonl")
        if not self.sync_state_path:
            self.sync_state_path = str(base / ".sync-state.json")
        if not self.github_token:
            token_path = Path.home() / ".openclaw" / "workspace" / ".credentials" / "github-pat.txt"
            if token_path.exists():
                self.github_token = token_path.read_text().strip()


@dataclass
class SyncState:
    """Tracks what's been synced to GitHub."""
    last_flush_time: float = 0.0
    last_flush_tile_count: int = 0
    total_tiles_synced: int = 0
    total_flushes: int = 0
    last_wal_line: int = 0  # line number in WAL we've flushed up to

    def to_dict(self) -> dict:
        return {
            "last_flush_time": self.last_flush_time,
            "last_flush_tile_count": self.last_flush_tile_count,
            "total_tiles_synced": self.total_tiles_synced,
            "total_flushes": self.total_flushes,
            "last_wal_line": self.last_wal_line,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SyncState":
        return cls(
            last_flush_time=data.get("last_flush_time", 0.0),
            last_flush_tile_count=data.get("last_flush_tile_count", 0),
            total_tiles_synced=data.get("total_tiles_synced", 0),
            total_flushes=data.get("total_flushes", 0),
            last_wal_line=data.get("last_wal_line", 0),
        )


class PlatoSync:
    """
    WAL → GitHub twin sync manager with auto-flush.

    Usage:
        sync = PlatoSync()
        sync.flush_to_github()        # manual flush
        sync.threaded_flush()         # non-blocking flush
        sync.get_status()             # current state
    """

    def __init__(self, config: Optional[SyncConfig] = None):
        self.cfg = config or SyncConfig()
        self._flush_lock = threading.Lock()
        self._state = self._load_state()

    # ─── State Management ──────────────────────────────────

    def _load_state(self) -> SyncState:
        path = Path(self.cfg.sync_state_path)
        if path.exists():
            try:
                data = json.loads(path.read_text())
                return SyncState.from_dict(data)
            except (json.JSONDecodeError, KeyError):
                pass
        return SyncState()

    def _save_state(self):
        path = Path(self.cfg.sync_state_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self._state.to_dict(), indent=2))

    # ─── WAL Reading ───────────────────────────────────────

    def _read_wal_lines(self) -> List[str]:
        """Read all lines from the WAL file."""
        wal = Path(self.cfg.wal_path)
        if not wal.exists():
            return []
        with open(wal) as f:
            return [line.strip() for line in f if line.strip()]

    def _get_new_entries(self) -> List[dict]:
        """Get WAL entries since last flush."""
        lines = self._read_wal_lines()
        new_lines = lines[self._state.last_wal_line:]
        entries = []
        for line in new_lines:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        return entries

    def _count_pending(self) -> int:
        """Count WAL entries not yet synced."""
        lines = self._read_wal_lines()
        return max(0, len(lines) - self._state.last_wal_line)

    # ─── GitHub Twin Operations ─────────────────────────────

    def _ensure_twin(self) -> bool:
        """Ensure the twin repo is cloned and ready."""
        twin = Path(self.cfg.twin_dir)
        if (twin / ".git").exists():
            return True
        return False

    def twin_clone(self) -> bool:
        """Clone or pull the GitHub twin repo."""
        twin = Path(self.cfg.twin_dir)
        url = f"https://{self.cfg.github_token}@github.com/{self.cfg.github_repo}.git" if self.cfg.github_token else f"https://github.com/{self.cfg.github_repo}.git"

        if twin.exists() and (twin / ".git").exists():
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
        if not twin.exists() or not (twin / ".git").exists():
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

    # ─── WAL → GitHub Flush ────────────────────────────────

    def flush_to_github(self) -> Dict[str, Any]:
        """
        Flush new WAL entries to GitHub twin under plato-data/.

        Steps:
        1. Read WAL entries since last flush (tracked by line number)
        2. Group by room → append to plato-data/{room}.jsonl
        3. git add/commit/push to SuperInstance/forgemaster
        4. Update sync state

        Returns flush result dict.
        """
        with self._flush_lock:
            return self._flush_internal()

    def _flush_internal(self) -> Dict[str, Any]:
        """Internal flush (caller holds lock)."""
        entries = self._get_new_entries()
        if not entries:
            return {"status": "nothing to flush", "pending": 0}

        twin = Path(self.cfg.twin_dir)
        if not self._ensure_twin():
            return {"status": "error", "error": "twin repo not available", "pending": len(entries)}

        # Group by room and append to plato-data/{room}.jsonl
        plato_data = twin / "plato-data"
        plato_data.mkdir(parents=True, exist_ok=True)
        rooms_updated: Dict[str, int] = {}

        for entry in entries:
            room = entry.get("room", "general")
            room_file = plato_data / f"{room}.jsonl"
            with open(room_file, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
            rooms_updated[room] = rooms_updated.get(room, 0) + 1

        # Git commit + push
        push_ok = False
        if (twin / ".git").exists():
            try:
                subprocess.run(
                    ["git", "add", "-A"], cwd=str(twin),
                    capture_output=True, timeout=10,
                )
                msg = f"PLATO WAL flush: {len(entries)} tiles across {len(rooms_updated)} rooms"
                subprocess.run(
                    ["git", "-c", "user.name=Forgemaster",
                     "-c", "user.email=forgemaster@superinstance",
                     "commit", "-m", msg],
                    cwd=str(twin), capture_output=True, timeout=10,
                )
                result = subprocess.run(
                    ["git", "push"],
                    cwd=str(twin), capture_output=True, timeout=30,
                )
                push_ok = result.returncode == 0
            except (subprocess.TimeoutExpired, OSError) as e:
                return {
                    "status": "error",
                    "error": str(e),
                    "pending": len(entries),
                }

        if push_ok:
            # Update sync state — advance the WAL line pointer
            all_lines = self._read_wal_lines()
            self._state.last_wal_line = len(all_lines)
            self._state.last_flush_time = time.time()
            self._state.last_flush_tile_count = len(entries)
            self._state.total_tiles_synced += len(entries)
            self._state.total_flushes += 1
            self._save_state()

            return {
                "status": "flushed",
                "tiles": len(entries),
                "rooms": dict(rooms_updated),
                "push_ok": True,
            }
        else:
            # Push failed — entries stay in WAL, retry next cycle
            return {
                "status": "push_failed",
                "tiles": len(entries),
                "rooms": dict(rooms_updated),
                "push_ok": False,
                "pending": len(entries),
            }

    def threaded_flush(self) -> threading.Thread:
        """Start a flush in a background thread (non-blocking)."""
        t = threading.Thread(target=self.flush_to_github, daemon=True)
        t.start()
        return t

    # ─── Status ────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Get current sync status."""
        wal_lines = self._read_wal_lines()
        total_wal = len(wal_lines)
        pending = max(0, total_wal - self._state.last_wal_line)

        return {
            "last_flush_time": self._state.last_flush_time,
            "last_flush_time_iso": (
                time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self._state.last_flush_time))
                if self._state.last_flush_time > 0 else None
            ),
            "last_flush_tiles": self._state.last_flush_tile_count,
            "total_tiles_synced": self._state.total_tiles_synced,
            "total_flushes": self._state.total_flushes,
            "wal_total": total_wal,
            "wal_pending": pending,
            "flush_interval": self.cfg.flush_interval,
            "twin_ready": self._ensure_twin(),
        }

    # ─── Startup Recovery ──────────────────────────────────

    def recover_on_startup(self) -> Dict[str, Any]:
        """
        Check for unsynced tiles in WAL and flush them.
        Called on server startup.
        """
        pending = self._count_pending()
        if pending == 0:
            return {"status": "no recovery needed", "pending": 0}

        # Attempt flush of unsynced tiles
        result = self.flush_to_github()
        result["recovery"] = True
        return result

    # ─── Pruning ────────────────────────────────────────────

    def prune(self, store, active_rooms: Set[str]) -> Dict[str, int]:
        """
        Prune hot PLATO: keep only rooms in active_rooms.
        Pruned rooms stay in GitHub twin (not deleted, just unloaded).
        """
        all_rooms = set(store.rooms.keys())
        to_prune = all_rooms - active_rooms

        for room_name in to_prune:
            room = store.rooms.get(room_name)
            if room:
                del store._rooms[room_name]
                for tile in room.tiles:
                    store._tile_index.pop(tile.tile_id, None)

        return {"kept": len(active_rooms & all_rooms), "pruned": len(to_prune)}

    def load_room(self, store, room_name: str) -> bool:
        """Load a room on-demand from SQLite or GitHub twin."""
        if store.room(room_name):
            return True

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
        """
        stats: Dict[str, Any] = {}

        stats["twin_pull"] = self.twin_clone()
        stats["twin_imported"] = self.twin_import_rooms(store)
        stats["remote_sync"] = store.sync_from_remote(self.cfg.remote_url)

        boot_stats = store.boot()
        stats.update(boot_stats)

        stats["twin_exported"] = self.twin_export_rooms(store)
        stats["twin_pushed"] = self.twin_push(
            f"PLATO sync: {boot_stats['tiles']} tiles across {boot_stats['rooms']} rooms"
        )

        return stats
