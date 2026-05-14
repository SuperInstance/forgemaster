"""
Local PLATO Runtime — the agent's external cortex at hardware speeds.

Syncs from remote PLATO server into local SQLite. Boots into memory
as Python dicts. Room state feeds AgentField tensor for O(1) coupling.

Architecture:
    Remote PLATO (147.224.38.131:8847) 
        → sync → local SQLite (~10MB)
        → boot → in-memory RoomStore (dict lookups, ~100ns)
        → feed → AgentField tensor (coupling matrix, ~10ns)

The agent's "knowledge" is three layers:
    1. Tiles on disk (SQLite) — full fidelity, slow boot
    2. Rooms in memory (dicts) — fast queries, O(1) by room name
    3. AgentField tensor (numpy-free) — coupling dynamics, O(1) by index
"""

from __future__ import annotations
import json
import sqlite3
import time
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


# ─── Tile and Room Data Types ───────────────────────────────────

@dataclass
class Tile:
    """A single PLATO tile — the atom of knowledge."""
    tile_id: str
    room: str
    domain: str
    question: str
    answer: str
    source: str
    tags: List[str] = field(default_factory=list)
    confidence: float = 0.0
    timestamp: float = 0.0
    
    # Provenance
    agent_id: str = ""
    chain_size: int = 0
    tile_hash: str = ""


@dataclass 
class LocalRoom:
    """A PLATO room loaded into memory."""
    name: str
    domain: str
    tiles: List[Tile] = field(default_factory=list)
    last_updated: float = 0.0
    tile_count: int = 0
    
    # Derived state (computed on boot)
    summary: str = ""
    key_sources: List[str] = field(default_factory=list)
    tags: Dict[str, int] = field(default_factory=dict)  # tag → count
    
    def latest(self, n: int = 5) -> List[Tile]:
        """Get the N most recent tiles."""
        return sorted(self.tiles, key=lambda t: t.timestamp, reverse=True)[:n]
    
    def search(self, query: str, limit: int = 10) -> List[Tile]:
        """Simple substring search across question/answer."""
        q_lower = query.lower()
        results = []
        for tile in self.tiles:
            if q_lower in tile.question.lower() or q_lower in tile.answer.lower():
                results.append(tile)
                if len(results) >= limit:
                    break
        return results
    
    def by_source(self, source: str) -> List[Tile]:
        """Get all tiles from a specific source."""
        return [t for t in self.tiles if t.source == source]
    
    def by_tag(self, tag: str) -> List[Tile]:
        """Get all tiles with a specific tag."""
        return [t for t in self.tiles if tag in t.tags]


# ─── Local SQLite Store ─────────────────────────────────────────

class LocalPlatoStore:
    """
    Local PLATO stored in SQLite. Fast queries. No network needed after sync.
    
    Path: ~/.openclaw/workspace/.local-plato/plato.db
    
    Boot sequence:
        1. Open SQLite
        2. Load all rooms into memory (Dict[str, LocalRoom])
        3. Feed room states into AgentField
        4. Ready — all queries are in-memory
    """
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = str(
                Path.home() / ".openclaw" / "workspace" / ".local-plato" / "plato.db"
            )
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()
        
        # In-memory index (the fast layer)
        self._rooms: Dict[str, LocalRoom] = {}
        self._tile_index: Dict[str, Tile] = {}  # tile_id → Tile
        self._booted = False
    
    def _create_tables(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS tiles (
                tile_id TEXT PRIMARY KEY,
                room TEXT NOT NULL,
                domain TEXT,
                question TEXT,
                answer TEXT,
                source TEXT,
                tags TEXT,  -- JSON array
                confidence REAL DEFAULT 0,
                timestamp REAL,
                agent_id TEXT,
                chain_size INTEGER DEFAULT 0,
                tile_hash TEXT,
                synced_at REAL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_room ON tiles(room);
            CREATE INDEX IF NOT EXISTS idx_source ON tiles(source);
            CREATE INDEX IF NOT EXISTS idx_timestamp ON tiles(timestamp DESC);
            CREATE INDEX IF NOT EXISTS idx_domain ON tiles(domain);
            
            CREATE TABLE IF NOT EXISTS sync_state (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        """)
        self._conn.commit()
    
    # ─── Sync from Remote ───────────────────────────────────
    
    def sync_from_remote(
        self,
        remote_url: str = "http://147.224.38.131:8847",
        prefixes: Optional[List[str]] = None,
    ) -> Dict[str, int]:
        """
        Pull rooms from remote PLATO server into local SQLite.
        
        Returns: {"rooms_synced": N, "tiles_synced": M, "new_tiles": K}
        """
        last_sync = self._get_sync_state("last_sync_ts")
        
        stats = {"rooms_synced": 0, "tiles_synced": 0, "new_tiles": 0}
        
        # Get list of rooms from remote
        try:
            # Use search endpoint to find rooms
            search_prefixes = prefixes or ["forgemaster", "fleet", "session", "constraint", "plato", "oracle1"]
            all_rooms = set()
            
            for prefix in search_prefixes:
                try:
                    req = urllib.request.Request(f"{remote_url}/search?prefix={prefix}")
                    resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
                    results = resp.get("results", [])
                    for r in results:
                        room_name = r.get("domain", r.get("room", ""))
                        if room_name:
                            all_rooms.add(room_name)
                except:
                    pass
            
            # Sync each room
            for room_name in all_rooms:
                try:
                    req = urllib.request.Request(f"{remote_url}/room/{room_name}")
                    resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
                    tiles = resp.get("tiles", [])
                    
                    for t in tiles:
                        tile_id = t.get("provenance", {}).get("tile_id", "")
                        if not tile_id:
                            tile_id = t.get("tile_hash", str(hash(json.dumps(t))))
                        
                        # Check if we already have this tile
                        existing = self._conn.execute(
                            "SELECT tile_id FROM tiles WHERE tile_id = ?", (tile_id,)
                        ).fetchone()
                        
                        if not existing:
                            tags_raw = t.get("tags", [])
                            tags_json = json.dumps(tags_raw) if isinstance(tags_raw, list) else "[]"
                            prov = t.get("provenance", {})
                            
                            self._conn.execute("""
                                INSERT OR REPLACE INTO tiles 
                                (tile_id, room, domain, question, answer, source, tags, 
                                 confidence, timestamp, agent_id, chain_size, tile_hash, synced_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                tile_id,
                                room_name,
                                t.get("domain", room_name),
                                t.get("question", ""),
                                t.get("answer", ""),
                                t.get("source", ""),
                                tags_json,
                                t.get("confidence", 0),
                                prov.get("timestamp", 0),
                                prov.get("agent_id", ""),
                                prov.get("chain_size", 0),
                                t.get("tile_hash", prov.get("tile_hash", "")),
                                time.time(),
                            ))
                            stats["new_tiles"] += 1
                        
                        stats["tiles_synced"] += 1
                    
                    stats["rooms_synced"] += 1
                    
                except Exception as e:
                    pass  # Skip rooms that error
            
            self._conn.commit()
            self._set_sync_state("last_sync_ts", str(time.time()))
            
        except Exception as e:
            stats["error"] = str(e)
        
        return stats
    
    # ─── Boot into Memory ───────────────────────────────────
    
    def boot(self) -> Dict[str, int]:
        """
        Load all tiles from SQLite into memory.
        This is the 'cortex boot' — everything becomes O(1).
        
        Returns: {"rooms": N, "tiles": M}
        """
        self._rooms.clear()
        self._tile_index.clear()
        
        rows = self._conn.execute(
            "SELECT * FROM tiles ORDER BY timestamp ASC"
        ).fetchall()
        
        for row in rows:
            tile = Tile(
                tile_id=row["tile_id"],
                room=row["room"],
                domain=row["domain"],
                question=row["question"] or "",
                answer=row["answer"] or "",
                source=row["source"] or "",
                tags=json.loads(row["tags"] or "[]"),
                confidence=row["confidence"] or 0,
                timestamp=row["timestamp"] or 0,
                agent_id=row["agent_id"] or "",
                chain_size=row["chain_size"] or 0,
                tile_hash=row["tile_hash"] or "",
            )
            
            # Index by tile_id
            self._tile_index[tile.tile_id] = tile
            
            # Add to room
            if tile.room not in self._rooms:
                self._rooms[tile.room] = LocalRoom(name=tile.room, domain=tile.domain)
            
            room = self._rooms[tile.room]
            room.tiles.append(tile)
            room.tile_count = len(room.tiles)
            room.last_updated = max(room.last_updated, tile.timestamp)
            
            # Track sources and tags
            if tile.source and tile.source not in room.key_sources:
                room.key_sources.append(tile.source)
            for tag in tile.tags:
                room.tags[tag] = room.tags.get(tag, 0) + 1
        
        self._booted = True
        
        return {"rooms": len(self._rooms), "tiles": len(self._tile_index)}
    
    # ─── In-Memory Queries (hardware speed) ─────────────────
    
    @property
    def booted(self) -> bool:
        return self._booted
    
    @property
    def rooms(self) -> Dict[str, LocalRoom]:
        return self._rooms
    
    def room(self, name: str) -> Optional[LocalRoom]:
        """O(1) room lookup by name."""
        return self._rooms.get(name)
    
    def tile(self, tile_id: str) -> Optional[Tile]:
        """O(1) tile lookup by ID."""
        return self._tile_index.get(tile_id)
    
    def search(self, query: str, limit: int = 20) -> List[Tile]:
        """Full-text search across all rooms. O(N) but N is in-memory."""
        results = []
        q_lower = query.lower()
        for tile in self._tile_index.values():
            if (q_lower in tile.question.lower() or 
                q_lower in tile.answer.lower() or
                q_lower in tile.domain.lower()):
                results.append(tile)
                if len(results) >= limit:
                    break
        return sorted(results, key=lambda t: t.timestamp, reverse=True)[:limit]
    
    def search_by_tag(self, tag: str, limit: int = 20) -> List[Tile]:
        """Find all tiles with a specific tag."""
        results = []
        for tile in self._tile_index.values():
            if tag in tile.tags:
                results.append(tile)
                if len(results) >= limit:
                    break
        return sorted(results, key=lambda t: t.timestamp, reverse=True)[:limit]
    
    def rooms_by_prefix(self, prefix: str) -> List[LocalRoom]:
        """Find all rooms whose name starts with prefix."""
        return [r for name, r in self._rooms.items() if name.startswith(prefix)]
    
    def room_count(self) -> int:
        return len(self._rooms)
    
    def tile_count(self) -> int:
        return len(self._tile_index)
    
    def sources(self) -> Dict[str, int]:
        """Count of tiles per source."""
        counts: Dict[str, int] = {}
        for tile in self._tile_index.values():
            counts[tile.source] = counts.get(tile.source, 0) + 1
        return sorted(counts.items(), key=lambda x: -x[1])
    
    def domains(self) -> Dict[str, int]:
        """Count of tiles per domain."""
        counts: Dict[str, int] = {}
        for tile in self._tile_index.values():
            counts[tile.domain] = counts.get(tile.domain, 0) + 1
        return sorted(counts.items(), key=lambda x: -x[1])
    
    # ─── Local Writes ───────────────────────────────────────
    
    def write_tile(self, tile: Tile):
        """Write a tile to local store (doesn't sync to remote)."""
        self._conn.execute("""
            INSERT OR REPLACE INTO tiles 
            (tile_id, room, domain, question, answer, source, tags, 
             confidence, timestamp, agent_id, chain_size, tile_hash, synced_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tile.tile_id, tile.room, tile.domain, tile.question,
            tile.answer, tile.source, json.dumps(tile.tags),
            tile.confidence, tile.timestamp, tile.agent_id,
            tile.chain_size, tile.tile_hash, time.time(),
        ))
        self._conn.commit()
        
        # Update in-memory indices
        self._tile_index[tile.tile_id] = tile
        if tile.room not in self._rooms:
            self._rooms[tile.room] = LocalRoom(name=tile.room, domain=tile.domain)
        self._rooms[tile.room].tiles.append(tile)
        self._rooms[tile.room].tile_count += 1
    
    # ─── Sync State Helpers ─────────────────────────────────
    
    def _get_sync_state(self, key: str) -> str:
        row = self._conn.execute(
            "SELECT value FROM sync_state WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else ""
    
    def _set_sync_state(self, key: str, value: str):
        self._conn.execute(
            "INSERT OR REPLACE INTO sync_state (key, value) VALUES (?, ?)",
            (key, value)
        )
        self._conn.commit()
    
    # ─── Reports ────────────────────────────────────────────
    
    def boot_report(self) -> str:
        """Human-readable boot summary."""
        lines = [
            f"=== LOCAL PLATO BOOT REPORT ===",
            f"Rooms: {self.room_count()}",
            f"Tiles: {self.tile_count()}",
            f"",
        ]
        
        # Top rooms
        top = sorted(self._rooms.values(), key=lambda r: r.tile_count, reverse=True)[:10]
        lines.append("Top Rooms:")
        for r in top:
            lines.append(f"  {r.name:40s} {r.tile_count:5d} tiles  sources={r.key_sources[:3]}")
        
        # Top sources
        lines.append("")
        lines.append("Top Sources:")
        for source, count in self.sources()[:10]:
            lines.append(f"  {source:30s} {count:5d} tiles")
        
        return "\n".join(lines)
