"""
PLATO-OHCache Bridge — Hot/Cold Knowledge Tiering for AutoData + Fleet

This module bridges AutoData's OHCache (in-session, hot) with PLATO 
(persistent, cold) for fleet-wide knowledge sharing.

Design by Forgemaster ⚒️
"""

import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("AutoData.fleet")


class PlatoOHCacheBridge:
    """Bridge between OHCache (hot) and PLATO (cold) knowledge stores.
    
    Hot path: Agent produces artifact → OHCache stores it for immediate reuse
    Cold path: OHCache flushes artifacts → PLATO stores them permanently
    
    On agent startup: PLATO tiles → OHCache preloaded as context
    
    This gives us:
    - Low-latency intra-session sharing (OHCache)
    - Persistent cross-session knowledge (PLATO)
    - Fleet-wide knowledge propagation (PLATO → all agents)
    """
    
    def __init__(
        self,
        plato_url: str = "http://147.224.38.131:8847",
        ohcache=None,  # OHCache instance
        sync_interval: int = 300,  # seconds between PLATO syncs
    ):
        self.plato_url = plato_url.rstrip("/")
        self.ohcache = ohcache
        self.sync_interval = sync_interval
        self.last_sync = 0.0
        self._pending_tiles: list[dict] = []
    
    # ── PLATO → OHCache (Cold to Hot) ─────────────────────────
    
    def preload_room(self, room_id: str, agent_name: str) -> list[dict]:
        """Load PLATO room tiles into OHCache for agent context.
        
        Called when an agent starts a task and needs domain knowledge.
        """
        import urllib.request
        
        url = f"{self.plato_url}/room/{room_id}"
        try:
            resp = urllib.request.urlopen(url, timeout=10)
            data = json.loads(resp.read())
            tiles = data.get("tiles", [])
            
            # Convert PLATO tiles to OHCache entries
            for tile in tiles:
                cache_key = f"plato:{room_id}:{tile.get('_hash', id(tile))}"
                if self.ohcache:
                    self.ohcache.set_cache(
                        key=cache_key,
                        value={
                            "question": tile.get("question", ""),
                            "answer": tile.get("answer", ""),
                            "domain": tile.get("domain", room_id),
                            "tags": tile.get("tags", []),
                            "confidence": tile.get("confidence", 0.5),
                        },
                        cache_type="plato_knowledge",
                        tags={"plato", room_id},
                    )
            
            logger.info(
                "Preloaded %d tiles from PLATO room '%s' for %s",
                len(tiles), room_id, agent_name,
            )
            return tiles
            
        except Exception as e:
            logger.warning("Failed to preload PLATO room '%s': %s", room_id, e)
            return []
    
    def search_plato(self, query: str, room_id: str | None = None) -> list[dict]:
        """Search PLATO for relevant tiles. Used by FleetKnowledgeTool."""
        import urllib.request
        
        # PLATO doesn't have a search endpoint yet, but we can fetch rooms
        if room_id:
            url = f"{self.plato_url}/room/{room_id}"
        else:
            return []
        
        try:
            resp = urllib.request.urlopen(url, timeout=10)
            data = json.loads(resp.read())
            tiles = data.get("tiles", [])
            
            # Simple keyword matching (PLATO may add semantic search later)
            query_lower = query.lower()
            relevant = [
                t for t in tiles
                if query_lower in t.get("question", "").lower()
                or query_lower in t.get("answer", "").lower()
            ]
            return relevant
        except Exception as e:
            logger.warning("PLATO search failed: %s", e)
            return []
    
    # ── OHCache → PLATO (Hot to Cold) ─────────────────────────
    
    def queue_tile(self, domain: str, question: str, answer: str,
                   source: str = "autodata", confidence: float = 0.8,
                   tags: list[str] | None = None) -> None:
        """Queue an artifact for PLATO submission.
        
        Called when an agent produces knowledge worth persisting.
        """
        self._pending_tiles.append({
            "domain": domain,
            "question": question,
            "answer": answer,
            "source": source,
            "confidence": confidence,
            "tags": tags or ["autodata", "fleet"],
        })
    
    def flush_to_plato(self) -> tuple[int, int]:
        """Flush pending tiles to PLATO. Returns (accepted, rejected)."""
        import urllib.request
        
        if not self._pending_tiles:
            return (0, 0)
        
        accepted = 0
        rejected = 0
        
        for tile in self._pending_tiles:
            try:
                data = json.dumps(tile).encode()
                req = urllib.request.Request(
                    f"{self.plato_url}/submit",
                    data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                resp = urllib.request.urlopen(req, timeout=10)
                result = json.loads(resp.read())
                if result.get("status") == "accepted":
                    accepted += 1
                else:
                    rejected += 1
            except Exception as e:
                rejected += 1
                logger.warning("PLATO tile rejected: %s", e)
        
        self._pending_tiles.clear()
        self.last_sync = time.time()
        
        logger.info("PLATO sync: %d accepted, %d rejected", accepted, rejected)
        return (accepted, rejected)
    
    def maybe_sync(self) -> tuple[int, int] | None:
        """Flush if sync interval has elapsed."""
        if time.time() - self.last_sync >= self.sync_interval:
            return self.flush_to_plato()
        return None
    
    # ── Room Discovery ────────────────────────────────────────
    
    def list_relevant_rooms(self, prefix: str = "") -> list[str]:
        """List PLATO rooms, optionally filtered by prefix."""
        import urllib.request
        
        url = f"{self.plato_url}/rooms"
        try:
            resp = urllib.request.urlopen(url, timeout=10)
            data = json.loads(resp.read())
            rooms = list(data.keys()) if isinstance(data, dict) else []
            if prefix:
                rooms = [r for r in rooms if r.startswith(prefix)]
            return sorted(rooms)
        except Exception as e:
            logger.warning("Failed to list PLATO rooms: %s", e)
            return []
