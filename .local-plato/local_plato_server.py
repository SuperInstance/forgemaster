#!/usr/bin/env python3
"""Forgemaster Local PLATO Server — standalone tile server on localhost.

Runs on :8848 (next to Oracle1's :8847). Accepts tile writes locally,
syncs to Oracle1's remote PLATO and GitHub twin when connected.

This is Forgemaster's OWN node. Oracle1's server is a PEER, not a master.

Usage:
    python3 local_plato_server.py [--port 8848] [--sync]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import time
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, parse_qs

# ---------------------------------------------------------------------------
# Local PLATO Store (shared with local_plato.py)
# ---------------------------------------------------------------------------

DB_PATH = str(Path.home() / ".openclaw" / "workspace" / ".local-plato" / "plato.db")
REMOTE_PLATO = "http://147.224.38.131:8847"

# ---------------------------------------------------------------------------
# HTTP Server
# ---------------------------------------------------------------------------

class PlatoHandler(BaseHTTPRequestHandler):
    """HTTP handler for local PLATO server."""

    store: Any = None  # set by server setup

    def log_message(self, format, *args):
        # Quiet logging — only errors
        if "200" not in str(args):
            super().log_message(format, *args)

    def _send_json(self, data, status=200):
        body = json.dumps(data, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length)

    # ── GET routes ───────────────────────────────────────

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        params = parse_qs(parsed.query)

        if path == "/status" or path == "/health":
            self._handle_status()
        elif path == "/rooms":
            self._handle_rooms(params)
        elif path.startswith("/room/"):
            room_name = path[6:]  # strip "/room/"
            self._handle_room(room_name, params)
        elif path == "/search":
            self._handle_search(params)
        elif path == "/stats":
            self._handle_stats()
        else:
            self._send_json({"error": "not found", "path": path}, 404)

    def _handle_status(self):
        conn = self.store._conn
        tile_count = conn.execute("SELECT COUNT(*) FROM tiles").fetchone()[0]
        room_count = conn.execute("SELECT COUNT(DISTINCT room) FROM tiles").fetchone()[0]
        sources = conn.execute(
            "SELECT source, COUNT(*) as cnt FROM tiles WHERE source != '' GROUP BY source ORDER BY cnt DESC LIMIT 10"
        ).fetchall()

        self._send_json({
            "status": "ok",
            "node": "forgemaster-local",
            "rooms": room_count,
            "tiles": tile_count,
            "top_sources": [{"source": r[0], "count": r[1]} for r in sources],
            "server_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })

    def _handle_rooms(self, params):
        prefix = params.get("prefix", [None])[0]
        limit = int(params.get("limit", [100])[0])

        conn = self.store._conn
        if prefix:
            rows = conn.execute(
                "SELECT room, COUNT(*) as cnt, MAX(timestamp) as latest "
                "FROM tiles WHERE room LIKE ? GROUP BY room ORDER BY latest DESC LIMIT ?",
                (f"{prefix}%", limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT room, COUNT(*) as cnt, MAX(timestamp) as latest "
                "FROM tiles GROUP BY room ORDER BY latest DESC LIMIT ?",
                (limit,),
            ).fetchall()

        rooms = [{"room": r[0], "tile_count": r[1], "latest": r[2]} for r in rows]
        self._send_json({"rooms": rooms, "count": len(rooms)})

    def _handle_room(self, room_name, params):
        limit = int(params.get("limit", [50])[0])

        conn = self.store._conn
        rows = conn.execute(
            "SELECT * FROM tiles WHERE room = ? ORDER BY timestamp DESC LIMIT ?",
            (room_name, limit),
        ).fetchall()

        columns = [d[0] for d in conn.execute("SELECT * FROM tiles LIMIT 0").description]
        tiles = []
        for row in rows:
            tile = dict(zip(columns, row))
            try:
                tile["tags"] = json.loads(tile.get("tags", "[]"))
            except:
                tile["tags"] = []
            tiles.append(tile)

        self._send_json({"room": room_name, "tiles": tiles, "count": len(tiles)})

    def _handle_search(self, params):
        query = params.get("q", [""])[0]
        prefix = params.get("prefix", [None])[0]
        limit = int(params.get("limit", [20])[0])

        if not query:
            self._send_json({"results": [], "count": 0})
            return

        conn = self.store._conn
        q_like = f"%{query}%"
        if prefix:
            rows = conn.execute(
                "SELECT * FROM tiles WHERE (question LIKE ? OR answer LIKE ?) "
                "AND room LIKE ? ORDER BY timestamp DESC LIMIT ?",
                (q_like, q_like, f"{prefix}%", limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM tiles WHERE question LIKE ? OR answer LIKE ? "
                "ORDER BY timestamp DESC LIMIT ?",
                (q_like, q_like, limit),
            ).fetchall()

        columns = [d[0] for d in conn.execute("SELECT * FROM tiles LIMIT 0").description]
        tiles = []
        for row in rows:
            tile = dict(zip(columns, row))
            try:
                tile["tags"] = json.loads(tile.get("tags", "[]"))
            except:
                tile["tags"] = []
            tiles.append(tile)

        self._send_json({"results": tiles, "count": len(tiles)})

    def _handle_stats(self):
        conn = self.store._conn
        domains = conn.execute(
            "SELECT domain, COUNT(*) as cnt FROM tiles GROUP BY domain ORDER BY cnt DESC"
        ).fetchall()
        sources = conn.execute(
            "SELECT source, COUNT(*) as cnt FROM tiles WHERE source != '' GROUP BY source ORDER BY cnt DESC"
        ).fetchall()

        self._send_json({
            "domains": [{"domain": r[0], "count": r[1]} for r in domains],
            "sources": [{"source": r[0], "count": r[1]} for r in sources],
        })

    # ── POST routes ──────────────────────────────────────

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/submit":
            self._handle_submit()
        elif path == "/sync":
            self._handle_sync()
        else:
            self._send_json({"error": "not found", "path": path}, 404)

    def _handle_submit(self):
        """Accept a tile and store it locally."""
        try:
            body = json.loads(self._read_body())
        except:
            self._send_json({"error": "invalid JSON"}, 400)
            return

        room = body.get("domain", body.get("room", "general"))
        question = body.get("question", "")
        answer = body.get("answer", "")
        source = body.get("source", "forgemaster-local")
        tags = body.get("tags", [])
        confidence = body.get("confidence", 0.5)
        agent_id = body.get("agent_id", "forgemaster")

        tile_id = body.get("tile_id", "")
        if not tile_id:
            tile_id = str(uuid.uuid4())

        tile_hash = hashlib.sha256(
            f"{room}:{question}:{answer}:{source}".encode()
        ).hexdigest()[:16]

        conn = self.store._conn
        conn.execute("""
            INSERT OR REPLACE INTO tiles
            (tile_id, room, domain, question, answer, source, tags,
             confidence, timestamp, agent_id, chain_size, tile_hash, synced_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (
            tile_id, room, room, question, answer, source,
            json.dumps(tags), confidence, time.time(),
            agent_id, 1, tile_hash,
        ))
        conn.commit()

        # Update in-memory index
        from local_plato import Tile, LocalRoom
        tile = Tile(
            tile_id=tile_id, room=room, domain=room,
            question=question, answer=answer, source=source,
            tags=tags, confidence=confidence,
            timestamp=time.time(), agent_id=agent_id,
            chain_size=1, tile_hash=tile_hash,
        )
        self.store._tile_index[tile_id] = tile
        if room not in self.store._rooms:
            self.store._rooms[room] = LocalRoom(name=room, domain=room)
        self.store._rooms[room].tiles.append(tile)
        self.store._rooms[room].tile_count += 1

        self._send_json({
            "status": "ok",
            "tile_id": tile_id,
            "room": room,
            "synced": False,  # will sync to remote later
        })

    def _handle_sync(self):
        """Trigger sync from remote PLATO."""
        try:
            stats = self.store.sync_from_remote()
            self._send_json({"status": "ok", "sync": stats})
        except Exception as e:
            self._send_json({"status": "error", "error": str(e)})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Forgemaster Local PLATO Server")
    parser.add_argument("--port", type=int, default=8848, help="Port to listen on")
    parser.add_argument("--sync", action="store_true", help="Sync from remote on startup")
    args = parser.parse_args()

    from local_plato import LocalPlatoStore

    store = LocalPlatoStore(DB_PATH)
    print(f"Local PLATO store: {DB_PATH}")

    if args.sync:
        print("Syncing from remote PLATO...")
        stats = store.sync_from_remote()
        print(f"  Sync result: {stats}")

    boot_result = store.boot()
    print(f"Booted: {boot_result['rooms']} rooms, {boot_result['tiles']} tiles")

    # Wire store to handler
    PlatoHandler.store = store

    server = HTTPServer(("127.0.0.1", args.port), PlatoHandler)
    print(f"\n⚒️  Forgemaster Local PLATO running on http://localhost:{args.port}")
    print(f"   Endpoints: /status, /rooms, /room/{{name}}, /search?q=..., /submit, /sync")
    print(f"   Peer: {REMOTE_PLATO}")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
