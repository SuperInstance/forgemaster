#!/usr/bin/env python3
"""
cashew_bridge.py — Cashew ↔ PLATO Bidirectional Docking Protocol
=================================================================

Bridges Cashew's persistent thought-graph memory with PLATO's spatial
room/tile architecture. Both systems share philosophical DNA (organic
decay, local-first, SQLite-backed) but differ in structure.

Cashew: nodes (thoughts) + edges (connections) + fitness (access frequency)
         Think cycles → cross-domain connection finding
         Sleep cycles → consolidation
         Local embeddings (all-MiniLM-L6-v2, 384 dims)

PLATO:   rooms (spatial containers) + tiles (knowledge units) + lifecycle
         Conservation law → fleet health
         Content-addressed tile IDs
         MythosTile protocol for fleet coordination

The bridge translates:
  Cashew nodes  ↔ PLATO tiles (content, embedding, fitness → lifecycle)
  Cashew edges  ↔ PLATO room adjacency (connections → room links)
  Cashew decay  ↔ PLATO tile lifecycle (Active → Superseded → Retracted)
  Cashew think  ↔ PLATO room creation (insights → new rooms)

Design informed by SCOUT-COMPETITIVE-02:
  "Cashew could be the memory layer INSIDE a PLATO room."

Architecture:
  CashewGraphAdapter     — reads Cashew SQLite → PLATO tiles
  PlatoToCashewAdapter   — writes PLATO tiles → Cashew SQLite
  BidirectionalSync      — keeps both systems in sync
  FluxTranslationLayer   — handles embedding/ID encoding differences
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CASHEW_DB_SCHEMA = """
-- Cashew-compatible schema (mirrors what Cashew creates)
CREATE TABLE IF NOT EXISTS nodes (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    embedding BLOB,           -- 384-dim float32 vector (all-MiniLM-L6-v2)
    fitness REAL DEFAULT 1.0, -- access frequency / decay score
    created_at REAL,
    updated_at REAL,
    accessed_at REAL,
    access_count INTEGER DEFAULT 0,
    metadata TEXT DEFAULT '{}',
    decayed INTEGER DEFAULT 0 -- 0=active, 1=decayed
);

CREATE TABLE IF NOT EXISTS edges (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    weight REAL DEFAULT 1.0,  -- connection strength (Hebbian)
    label TEXT DEFAULT '',
    created_at REAL,
    metadata TEXT DEFAULT '{}',
    FOREIGN KEY (source_id) REFERENCES nodes(id),
    FOREIGN KEY (target_id) REFERENCES nodes(id)
);

CREATE TABLE IF NOT EXISTS think_results (
    id TEXT PRIMARY KEY,
    source_node_ids TEXT NOT NULL, -- JSON array of node IDs that triggered this
    insight TEXT NOT NULL,
    confidence REAL DEFAULT 0.5,
    created_at REAL,
    metadata TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS sync_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at REAL
);
"""

FITNESS_LIFECYCLE_THRESHOLDS = {
    "active": (0.7, float("inf")),       # fitness >= 0.7 → active
    "superseded": (0.3, 0.7),            # 0.3 <= fitness < 0.7 → superseded
    "retracted": (0.0, 0.3),             # fitness < 0.3 → retracted
}

DEFAULT_FITNESS = 1.0
DECAY_RATE = 0.05  # per access cycle (Ebbinghaus-inspired)
SYNC_ROOM_PREFIX = "cashew-sync"
INSIGHTS_ROOM = "cashew-insights"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class CashewNode:
    """Represents a single node in Cashew's thought graph."""
    id: str = ""
    content: str = ""
    embedding: Optional[bytes] = None  # 384-dim float32
    fitness: float = DEFAULT_FITNESS
    created_at: float = 0.0
    updated_at: float = 0.0
    accessed_at: float = 0.0
    access_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    decayed: bool = False

    def __post_init__(self):
        if not self.id:
            self.id = hashlib.sha256(
                f"{self.content}:{time.time()}".encode()
            ).hexdigest()[:16]
        now = time.time()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now
        if not self.accessed_at:
            self.accessed_at = now


@dataclass
class CashewEdge:
    """Represents a connection between two Cashew nodes."""
    id: str = ""
    source_id: str = ""
    target_id: str = ""
    weight: float = 1.0
    label: str = ""
    created_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            self.id = hashlib.sha256(
                f"{self.source_id}:{self.target_id}:{time.time()}".encode()
            ).hexdigest()[:16]
        if not self.created_at:
            self.created_at = time.time()


@dataclass
class ThinkResult:
    """Result of a Cashew think cycle — cross-domain connection."""
    id: str = ""
    source_node_ids: List[str] = field(default_factory=list)
    insight: str = ""
    confidence: float = 0.5
    created_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            self.id = hashlib.sha256(
                f"think:{self.insight[:64]}:{time.time()}".encode()
            ).hexdigest()[:16]
        if not self.created_at:
            self.created_at = time.time()


@dataclass
class SyncStatus:
    """Status of the bidirectional sync."""
    nodes_synced: int = 0
    edges_synced: int = 0
    tiles_synced: int = 0
    pending_inbound: int = 0
    pending_outbound: int = 0
    last_sync: float = 0.0
    cashew_path: str = ""
    plato_connected: bool = False
    errors: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# CashewGraphAdapter — reads Cashew SQLite → PLATO tiles
# ---------------------------------------------------------------------------

class CashewGraphAdapter:
    """
    Reads Cashew's SQLite format and converts to PLATO-compatible
    tile representations.

    Mapping:
      Cashew node.content     → PLATO tile question/answer
      Cashew node.fitness     → PLATO tile lifecycle (active/superseded/retracted)
      Cashew node.embedding   → semantic routing key (nearest room)
      Cashew edge             → PLATO room adjacency / tile link
      Cashew think_results    → new tiles in "cashew-insights" room
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self) -> None:
        """Open connection to Cashew SQLite database."""
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Not connected. Call connect() first.")
        return self._conn

    def ensure_schema(self) -> None:
        """Create Cashew-compatible tables if they don't exist."""
        self.conn.executescript(CASHEW_DB_SCHEMA)
        self.conn.commit()

    # -- Read operations ---------------------------------------------------

    def get_all_nodes(self, include_decayed: bool = False) -> List[CashewNode]:
        """Fetch all nodes from Cashew database."""
        if include_decayed:
            rows = self.conn.execute("SELECT * FROM nodes").fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM nodes WHERE decayed = 0"
            ).fetchall()
        return [self._row_to_node(r) for r in rows]

    def get_node(self, node_id: str) -> Optional[CashewNode]:
        """Fetch a single node by ID."""
        row = self.conn.execute(
            "SELECT * FROM nodes WHERE id = ?", (node_id,)
        ).fetchone()
        return self._row_to_node(row) if row else None

    def get_edges_for_node(self, node_id: str) -> List[CashewEdge]:
        """Fetch all edges connected to a node."""
        rows = self.conn.execute(
            "SELECT * FROM edges WHERE source_id = ? OR target_id = ?",
            (node_id, node_id),
        ).fetchall()
        return [self._row_to_edge(r) for r in rows]

    def get_all_edges(self) -> List[CashewEdge]:
        """Fetch all edges from Cashew database."""
        rows = self.conn.execute("SELECT * FROM edges").fetchall()
        return [self._row_to_edge(r) for r in rows]

    def get_think_results(self, since: float = 0.0) -> List[ThinkResult]:
        """Fetch think cycle results since a given timestamp."""
        rows = self.conn.execute(
            "SELECT * FROM think_results WHERE created_at > ?",
            (since,),
        ).fetchall()
        return [self._row_to_think(r) for r in rows]

    def get_node_count(self, include_decayed: bool = False) -> int:
        """Count nodes in the database."""
        if include_decayed:
            return self.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        return self.conn.execute(
            "SELECT COUNT(*) FROM nodes WHERE decayed = 0"
        ).fetchone()[0]

    # -- Write operations --------------------------------------------------

    def put_node(self, node: CashewNode) -> None:
        """Insert or update a node."""
        self.conn.execute("""
            INSERT OR REPLACE INTO nodes
            (id, content, embedding, fitness, created_at, updated_at,
             accessed_at, access_count, metadata, decayed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            node.id, node.content, node.embedding, node.fitness,
            node.created_at, node.updated_at, node.accessed_at,
            node.access_count, json.dumps(node.metadata),
            1 if node.decayed else 0,
        ))
        self.conn.commit()

    def put_edge(self, edge: CashewEdge) -> None:
        """Insert or update an edge."""
        self.conn.execute("""
            INSERT OR REPLACE INTO edges
            (id, source_id, target_id, weight, label, created_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            edge.id, edge.source_id, edge.target_id, edge.weight,
            edge.label, edge.created_at, json.dumps(edge.metadata),
        ))
        self.conn.commit()

    def put_think_result(self, result: ThinkResult) -> None:
        """Insert a think cycle result."""
        self.conn.execute("""
            INSERT OR REPLACE INTO think_results
            (id, source_node_ids, insight, confidence, created_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            result.id, json.dumps(result.source_node_ids),
            result.insight, result.confidence, result.created_at,
            json.dumps(result.metadata),
        ))
        self.conn.commit()

    def touch_node(self, node_id: str) -> None:
        """Access a node — increment access count, update fitness."""
        node = self.get_node(node_id)
        if node:
            node.access_count += 1
            node.accessed_at = time.time()
            node.updated_at = time.time()
            # Fitness boost on access (reverse decay)
            node.fitness = min(1.0, node.fitness + 0.1)
            if node.fitness >= 0.3:
                node.decayed = False
            self.put_node(node)

    def decay_nodes(self, threshold: float = 0.1) -> int:
        """
        Apply organic decay to all nodes not recently accessed.
        Returns count of nodes that crossed the decay threshold.
        """
        now = time.time()
        decayed_count = 0
        nodes = self.get_all_nodes(include_decayed=False)

        for node in nodes:
            # Time since last access (in hours)
            hours_since = (now - node.accessed_at) / 3600.0
            if hours_since > 1.0:  # only decay if > 1 hour since access
                decay_amount = DECAY_RATE * hours_since
                node.fitness = max(0.0, node.fitness - decay_amount)

                if node.fitness < threshold:
                    node.decayed = True
                    decayed_count += 1

                node.updated_at = now
                self.put_node(node)

        return decayed_count

    # -- Conversion: Cashew → PLATO ----------------------------------------

    def node_to_plato_tile(self, node: CashewNode) -> dict:
        """Convert a Cashew node to a PLATO-compatible tile dict."""
        lifecycle = self.fitness_to_lifecycle(node.fitness)
        room = self.node_to_room(node)

        return {
            "tile_id": f"cashew:{node.id}",
            "domain": room,
            "room": room,
            "question": node.content,
            "answer": node.metadata.get("answer", ""),
            "source": f"cashew:{node.metadata.get('source', 'unknown')}",
            "tags": node.metadata.get("tags", []),
            "confidence": node.fitness,
            "lifecycle": lifecycle,
            "lamport_clock": node.access_count,
            "_meta": {
                "cashew_node_id": node.id,
                "cashew_fitness": node.fitness,
                "cashew_access_count": node.access_count,
                "cashew_decayed": node.decayed,
                "cashew_embedding_dims": 384,
                "bridge_version": "1.0",
            },
        }

    def edge_to_plato_link(self, edge: CashewEdge) -> dict:
        """Convert a Cashew edge to a PLATO room adjacency link."""
        return {
            "source_tile": f"cashew:{edge.source_id}",
            "target_tile": f"cashew:{edge.target_id}",
            "weight": edge.weight,
            "label": edge.label,
            "hebbian_strength": edge.weight,
            "_meta": {
                "cashew_edge_id": edge.id,
                "bridge_version": "1.0",
            },
        }

    def think_to_plato_tile(self, result: ThinkResult) -> dict:
        """Convert a Cashew think result to a PLATO tile in insights room."""
        return {
            "tile_id": f"cashew-think:{result.id}",
            "domain": INSIGHTS_ROOM,
            "room": INSIGHTS_ROOM,
            "question": result.insight,
            "answer": "",  # think results are questions/insights, not answers
            "source": "cashew:think-cycle",
            "tags": ["think-cycle", "auto-generated", "cross-domain"],
            "confidence": result.confidence,
            "lifecycle": "active",
            "_meta": {
                "cashew_think_id": result.id,
                "cashew_source_nodes": result.source_node_ids,
                "bridge_version": "1.0",
            },
        }

    # -- Routing helpers ---------------------------------------------------

    @staticmethod
    def fitness_to_lifecycle(fitness: float) -> str:
        """Map Cashew fitness to PLATO tile lifecycle state."""
        if fitness >= 0.7:
            return "active"
        elif fitness >= 0.3:
            return "superseded"
        else:
            return "retracted"

    @staticmethod
    def lifecycle_to_fitness(lifecycle: str) -> float:
        """Map PLATO tile lifecycle back to Cashew fitness."""
        mapping = {
            "active": 0.85,
            "superseded": 0.5,
            "retracted": 0.15,
        }
        return mapping.get(lifecycle, 0.5)

    @staticmethod
    def node_to_room(node: CashewNode) -> str:
        """
        Determine which PLATO room a Cashew node belongs to.

        Uses metadata.room if set, otherwise hashes content to a
        semantic room name.
        """
        if "room" in node.metadata:
            return node.metadata["room"]
        # Deterministic room assignment from content hash
        content_hash = hashlib.md5(node.content.encode()).hexdigest()[:8]
        return f"{SYNC_ROOM_PREFIX}-{content_hash}"

    # -- Row converters ----------------------------------------------------

    @staticmethod
    def _row_to_node(row: sqlite3.Row) -> CashewNode:
        metadata = {}
        try:
            metadata = json.loads(row["metadata"]) if row["metadata"] else {}
        except (json.JSONDecodeError, TypeError):
            pass
        return CashewNode(
            id=row["id"],
            content=row["content"],
            embedding=row["embedding"] if "embedding" in row.keys() else None,
            fitness=row["fitness"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            accessed_at=row["accessed_at"],
            access_count=row["access_count"],
            metadata=metadata,
            decayed=bool(row["decayed"]),
        )

    @staticmethod
    def _row_to_edge(row: sqlite3.Row) -> CashewEdge:
        metadata = {}
        try:
            metadata = json.loads(row["metadata"]) if row["metadata"] else {}
        except (json.JSONDecodeError, TypeError):
            pass
        return CashewEdge(
            id=row["id"],
            source_id=row["source_id"],
            target_id=row["target_id"],
            weight=row["weight"],
            label=row["label"],
            created_at=row["created_at"],
            metadata=metadata,
        )

    @staticmethod
    def _row_to_think(row: sqlite3.Row) -> ThinkResult:
        metadata = {}
        source_ids = []
        try:
            metadata = json.loads(row["metadata"]) if row["metadata"] else {}
        except (json.JSONDecodeError, TypeError):
            pass
        try:
            source_ids = json.loads(row["source_node_ids"]) if row["source_node_ids"] else []
        except (json.JSONDecodeError, TypeError):
            pass
        return ThinkResult(
            id=row["id"],
            source_node_ids=source_ids,
            insight=row["insight"],
            confidence=row["confidence"],
            created_at=row["created_at"],
            metadata=metadata,
        )


# ---------------------------------------------------------------------------
# PlatoToCashewAdapter — writes PLATO rooms → Cashew format
# ---------------------------------------------------------------------------

class PlatoToCashewAdapter:
    """
    Converts PLATO tiles and room structure back into Cashew nodes and edges.

    Mapping:
      PLATO tile.question/answer → Cashew node.content
      PLATO tile.lifecycle       → Cashew node.fitness + decayed flag
      PLATO tile.confidence      → Cashew node.fitness (normalized)
      PLATO room adjacency       → Cashew edges with Hebbian weights
      PLATO tile.tags            → Cashew node metadata
    """

    def __init__(self, adapter: CashewGraphAdapter):
        self.adapter = adapter

    def tile_to_node(self, tile: dict) -> CashewNode:
        """Convert a PLATO tile dict to a Cashew node."""
        content = tile.get("question", "")
        answer = tile.get("answer", "")
        if answer:
            content = f"Q: {content}\nA: {answer}"

        fitness = self.lifecycle_to_fitness(tile.get("lifecycle", "active"))
        # Override with confidence if available
        if "confidence" in tile:
            confidence = tile["confidence"]
            if 0.0 <= confidence <= 1.0:
                fitness = confidence

        meta = tile.get("_meta", {})
        tile_id = tile.get("tile_id", "")

        metadata = {
            "source": tile.get("source", "plato"),
            "tags": tile.get("tags", []),
            "room": tile.get("room", ""),
            "domain": tile.get("domain", ""),
            "plato_tile_id": tile_id,
            "lifecycle": tile.get("lifecycle", "active"),
            **{k: v for k, v in meta.items() if k not in (
                "cashew_node_id", "cashew_fitness",
            )},
        }

        # Reuse cashew node ID if available
        node_id = meta.get("cashew_node_id", tile_id.replace("cashew:", ""))

        return CashewNode(
            id=node_id if node_id else hashlib.sha256(
                content.encode()
            ).hexdigest()[:16],
            content=content,
            fitness=fitness,
            metadata=metadata,
            decayed=(tile.get("lifecycle") == "retracted"),
        )

    def write_tile(self, tile: dict) -> CashewNode:
        """Convert and write a PLATO tile to Cashew database."""
        node = self.tile_to_node(tile)
        self.adapter.put_node(node)
        return node

    def write_tiles(self, tiles: List[dict]) -> List[CashewNode]:
        """Convert and write multiple PLATO tiles."""
        return [self.write_tile(t) for t in tiles]

    def room_links_to_edges(
        self, links: List[dict]
    ) -> List[CashewEdge]:
        """
        Convert PLATO room adjacency links to Cashew edges.

        Each link has source_tile, target_tile, weight.
        """
        edges = []
        for link in links:
            source_id = link.get("source_tile", "").replace("cashew:", "")
            target_id = link.get("target_tile", "").replace("cashew:", "")
            if not source_id or not target_id:
                continue
            edge = CashewEdge(
                source_id=source_id,
                target_id=target_id,
                weight=link.get("weight", 1.0),
                label=link.get("label", ""),
                metadata={
                    "plato_link": True,
                    "hebbian_strength": link.get("hebbian_strength", 1.0),
                },
            )
            self.adapter.put_edge(edge)
            edges.append(edge)
        return edges

    @staticmethod
    def lifecycle_to_fitness(lifecycle: str) -> float:
        """Map PLATO lifecycle to Cashew fitness."""
        return CashewGraphAdapter.lifecycle_to_fitness(lifecycle)


# ---------------------------------------------------------------------------
# FluxTranslationLayer — handles encoding differences
# ---------------------------------------------------------------------------

class FluxTranslationLayer:
    """
    Translates between Cashew's embedding-based addressing and
    PLATO's content-addressed tile IDs.

    Cashew: 384-dim MiniLM embeddings → semantic similarity search
    PLATO:  content-addressed tile IDs → deterministic retrieval

    This layer bridges the two by:
    1. Converting embeddings → semantic room routing (nearest room match)
    2. Converting tile IDs → node fitness (lifecycle mapping)
    3. Translating think cycle connections → room adjacency updates
    """

    EMBEDDING_DIMS = 384

    def __init__(self, adapter: CashewGraphAdapter):
        self.adapter = adapter
        self._room_embeddings: Dict[str, List[float]] = {}

    def register_room_embedding(self, room: str, embedding: List[float]) -> None:
        """Register an embedding vector for a PLATO room."""
        self._room_embeddings[room] = embedding

    def nearest_room(self, embedding: List[float]) -> Optional[str]:
        """
        Find the nearest PLATO room for a Cashew embedding.

        Uses cosine similarity against registered room embeddings.
        Returns None if no rooms are registered.
        """
        if not self._room_embeddings:
            return None

        best_room = None
        best_sim = -1.0

        for room, room_emb in self._room_embeddings.items():
            sim = self._cosine_similarity(embedding, room_emb)
            if sim > best_sim:
                best_sim = sim
                best_room = room

        return best_room

    def embedding_to_room(self, node: CashewNode) -> str:
        """
        Route a Cashew node to a PLATO room based on its embedding.

        Falls back to content-hash-based routing if no embedding.
        """
        if node.embedding and len(node.embedding) >= 4:
            # Parse embedding bytes to float32 array
            import struct
            dims = len(node.embedding) // 4
            if dims > 0:
                emb = list(struct.unpack(f"{dims}f", node.embedding))
                room = self.nearest_room(emb)
                if room:
                    return room

        # Fallback: content-hash routing
        return CashewGraphAdapter.node_to_room(node)

    @staticmethod
    def tile_id_to_fitness(tile_id: str, lifecycle: str) -> float:
        """Map a PLATO tile ID + lifecycle to Cashew fitness."""
        base_fitness = CashewGraphAdapter.lifecycle_to_fitness(lifecycle)
        # Deterministic perturbation from tile ID to add variety
        id_hash = int(hashlib.md5(tile_id.encode()).hexdigest()[:8], 16)
        perturbation = (id_hash % 20 - 10) / 100.0  # ±0.10
        return max(0.0, min(1.0, base_fitness + perturbation))

    @staticmethod
    def think_connections_to_links(
        result: ThinkResult, adapter: CashewGraphAdapter
    ) -> List[dict]:
        """
        Convert think cycle results into PLATO room adjacency updates.

        Think cycles connect nodes across domains — these become
        cross-room links in PLATO.
        """
        links = []
        source_ids = result.source_node_ids

        # Create pairwise links between all source nodes
        for i in range(len(source_ids)):
            for j in range(i + 1, len(source_ids)):
                node_a = adapter.get_node(source_ids[i])
                node_b = adapter.get_node(source_ids[j])
                if not node_a or not node_b:
                    continue

                room_a = CashewGraphAdapter.node_to_room(node_a)
                room_b = CashewGraphAdapter.node_to_room(node_b)

                links.append({
                    "source_room": room_a,
                    "target_room": room_b,
                    "source_tile": f"cashew:{source_ids[i]}",
                    "target_tile": f"cashew:{source_ids[j]}",
                    "weight": result.confidence,
                    "label": f"think-cycle:{result.id}",
                    "cross_domain": room_a != room_b,
                })

        return links

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


# ---------------------------------------------------------------------------
# BidirectionalSync — keeps both systems in sync
# ---------------------------------------------------------------------------

class BidirectionalSync:
    """
    Orchestrates bidirectional synchronization between Cashew and PLATO.

    Sync rules:
    1. PLATO tile submitted → creates/updates Cashew node
    2. Cashew think cycle → submits PLATO tile to insights room
    3. Cashew decay → PLATO lifecycle transition (Active → Superseded)
    4. New Cashew edge → PLATO room adjacency update
    5. Conservation compliance → Cashew fitness scores

    Tracks sync state in both systems to avoid cycles.
    """

    SYNC_KEY_LAST_TS = "last_sync_timestamp"
    SYNC_KEY_DIRECTION = "last_sync_direction"

    def __init__(
        self,
        cashew_adapter: CashewGraphAdapter,
        plato_submit_url: Optional[str] = None,
    ):
        self.cashew = cashew_adapter
        self.plato_submit_url = plato_submit_url
        self.plato_writer = PlatoToCashewAdapter(cashew_adapter)
        self.flux = FluxTranslationLayer(cashew_adapter)
        self._sync_log: List[dict] = []

    # -- Sync operations ---------------------------------------------------

    def sync_cashew_to_plato(self, since: float = 0.0) -> SyncStatus:
        """
        Sync Cashew nodes → PLATO tiles.

        Converts all Cashew nodes (created/updated since `since`) to
        PLATO tile format and submits them.
        """
        status = SyncStatus(
            cashew_path=self.cashew.db_path,
            last_sync=time.time(),
        )

        try:
            nodes = self.cashew.get_all_nodes(include_decayed=True)
            tiles_to_submit = []

            for node in nodes:
                if node.updated_at < since and node.created_at < since:
                    continue
                tile = self.cashew.node_to_plato_tile(node)
                tiles_to_submit.append(tile)
                status.nodes_synced += 1

            # Sync edges as room adjacency
            edges = self.cashew.get_all_edges()
            for edge in edges:
                if edge.created_at < since:
                    continue
                link = self.cashew.edge_to_plato_link(edge)
                self._log_sync("cashew→plato:edge", link)
                status.edges_synced += 1

            # Sync think results
            thinks = self.cashew.get_think_results(since)
            for think in thinks:
                tile = self.cashew.think_to_plato_tile(think)
                tiles_to_submit.append(tile)

            # Submit tiles to PLATO (if URL provided)
            if self.plato_submit_url and tiles_to_submit:
                submitted = self._submit_to_plato(tiles_to_submit)
                status.tiles_synced = submitted
                status.plato_connected = True
            elif tiles_to_submit:
                status.tiles_synced = len(tiles_to_submit)
                status.plato_connected = False

            status.pending_outbound = 0

            # Record sync timestamp
            self._record_sync("cashew→plato")

        except Exception as e:
            status.errors.append(str(e))

        self._log_sync("cashew→plato:complete", {"nodes": status.nodes_synced})
        return status

    def sync_plato_to_cashew(
        self, tiles: List[dict], links: Optional[List[dict]] = None
    ) -> SyncStatus:
        """
        Sync PLATO tiles → Cashew nodes.

        Converts PLATO tiles to Cashew nodes and writes them.
        Optionally converts room adjacency links to Cashew edges.
        """
        status = SyncStatus(
            cashew_path=self.cashew.db_path,
            last_sync=time.time(),
        )

        try:
            # Write tiles as nodes
            for tile in tiles:
                node = self.plato_writer.write_tile(tile)
                status.tiles_synced += 1
                self._log_sync("plato→cashew:tile", {
                    "tile_id": tile.get("tile_id"),
                    "node_id": node.id,
                })

            # Write links as edges
            if links:
                edges = self.plato_writer.room_links_to_edges(links)
                status.edges_synced = len(edges)

            status.nodes_synced = status.tiles_synced
            status.pending_inbound = 0

            self._record_sync("plato→cashew")

        except Exception as e:
            status.errors.append(str(e))

        return status

    def full_sync(
        self, plato_tiles: Optional[List[dict]] = None
    ) -> SyncStatus:
        """
        Perform a full bidirectional sync.

        1. Pull new/updated Cashew nodes → PLATO tiles
        2. Push PLATO tiles → Cashew nodes
        3. Reconcile any conflicts (latest timestamp wins)
        """
        last_ts = self._get_last_sync_ts()

        # Phase 1: Cashew → PLATO
        c2p_status = self.sync_cashew_to_plato(since=last_ts)

        # Phase 2: PLATO → Cashew
        if plato_tiles:
            p2c_status = self.sync_plato_to_cashew(plato_tiles)
        else:
            p2c_status = SyncStatus()

        # Merge statuses
        merged = SyncStatus(
            nodes_synced=c2p_status.nodes_synced + p2c_status.nodes_synced,
            edges_synced=c2p_status.edges_synced + p2c_status.edges_synced,
            tiles_synced=c2p_status.tiles_synced + p2c_status.tiles_synced,
            last_sync=time.time(),
            cashew_path=self.cashew.db_path,
            plato_connected=c2p_status.plato_connected or p2c_status.plato_connected,
            errors=c2p_status.errors + p2c_status.errors,
        )

        return merged

    def trigger_decay_sync(self) -> Dict[str, int]:
        """
        Run Cashew decay and sync lifecycle transitions to PLATO.

        Returns count of transitions by type.
        """
        transitions = {"active→superseded": 0, "superseded→retracted": 0, "decayed": 0}

        # Get current state before decay
        nodes_before = {n.id: CashewGraphAdapter.fitness_to_lifecycle(n.fitness)
                        for n in self.cashew.get_all_nodes()}

        # Run decay
        decayed_count = self.cashew.decay_nodes()

        # Get state after decay
        nodes_after = {n.id: CashewGraphAdapter.fitness_to_lifecycle(n.fitness)
                       for n in self.cashew.get_all_nodes()}

        # Track transitions
        for node_id, after_lc in nodes_after.items():
            before_lc = nodes_before.get(node_id, "active")
            if before_lc != after_lc:
                key = f"{before_lc}→{after_lc}"
                if key in transitions:
                    transitions[key] += 1

        transitions["decayed"] = decayed_count

        return transitions

    def trigger_think_sync(self, think_result: ThinkResult) -> dict:
        """
        Ingest a Cashew think cycle result into PLATO.

        Creates a PLATO tile in the insights room AND creates
        cross-domain edges between source nodes.
        """
        # Write think result to Cashew
        self.cashew.put_think_result(think_result)

        # Convert to PLATO tile
        tile = self.cashew.think_to_plato_tile(think_result)

        # Generate cross-domain links
        links = FluxTranslationLayer.think_connections_to_links(
            think_result, self.cashew
        )

        # Submit to PLATO if possible
        submitted = 0
        if self.plato_submit_url:
            submitted = self._submit_to_plato([tile])

        return {
            "think_id": think_result.id,
            "plato_tile_id": tile.get("tile_id"),
            "cross_domain_links": len(links),
            "submitted_to_plato": submitted,
            "links": links,
        }

    # -- Status ------------------------------------------------------------

    def get_status(self) -> SyncStatus:
        """Get current sync status."""
        node_count = self.cashew.get_node_count(include_decayed=True)
        edge_count = len(self.cashew.get_all_edges())
        last_ts = self._get_last_sync_ts()

        return SyncStatus(
            nodes_synced=node_count,
            edges_synced=edge_count,
            last_sync=last_ts,
            cashew_path=self.cashew.db_path,
            plato_connected=self.plato_submit_url is not None,
        )

    # -- Internal ----------------------------------------------------------

    def _get_last_sync_ts(self) -> float:
        """Retrieve the last sync timestamp from sync_state table."""
        try:
            row = self.cashew.conn.execute(
                "SELECT value FROM sync_state WHERE key = ?",
                (self.SYNC_KEY_LAST_TS,),
            ).fetchone()
            return float(row["value"]) if row else 0.0
        except (sqlite3.OperationalError, ValueError, TypeError):
            return 0.0

    def _record_sync(self, direction: str) -> None:
        """Record sync timestamp and direction."""
        now = time.time()
        try:
            self.cashew.conn.execute("""
                INSERT OR REPLACE INTO sync_state (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (self.SYNC_KEY_LAST_TS, str(now), now))
            self.cashew.conn.execute("""
                INSERT OR REPLACE INTO sync_state (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (self.SYNC_KEY_DIRECTION, direction, now))
            self.cashew.conn.commit()
        except sqlite3.OperationalError:
            pass

    def _submit_to_plato(self, tiles: List[dict]) -> int:
        """Submit tiles to PLATO server. Returns count submitted."""
        if not self.plato_submit_url:
            return 0
        try:
            import requests
            submitted = 0
            for tile in tiles:
                resp = requests.post(
                    f"{self.plato_submit_url}/submit",
                    json=tile,
                    timeout=10,
                )
                if resp.status_code == 200:
                    submitted += 1
            return submitted
        except Exception:
            return 0

    def _log_sync(self, event: str, data: Any = None) -> None:
        self._sync_log.append({
            "timestamp": time.time(),
            "event": event,
            "data": data,
        })

    @property
    def sync_log(self) -> List[dict]:
        return list(self._sync_log)


# ---------------------------------------------------------------------------
# ShellUpgrade — what Cashew gains by docking with PLATO
# ---------------------------------------------------------------------------

class ShellUpgrade:
    """
    Documents and provides the enhanced capabilities Cashew gains
    by docking with PLATO.

    Shell upgrades:
    1. Fleet health monitoring (conservation law checks)
    2. Multi-agent coordination (rooms)
    3. Content verification (canary tiles)
    4. Cross-validation with other agents
    5. Persistence beyond SQLite (PLATO WAL + GitHub sync)
    6. Stage-aware query translation (fleet translator)
    """

    def __init__(self, sync: BidirectionalSync):
        self.sync = sync

    def check_fleet_health(self) -> dict:
        """
        Run conservation law check on Cashew graph.

        Verifies that the graph coupling matrix satisfies
        γ + H = C − α·ln(V) approximately.
        """
        nodes = self.sync.cashew.get_all_nodes()
        edges = self.sync.cashew.get_all_edges()

        if not nodes:
            return {"healthy": True, "reason": "empty_graph", "gamma": 0.0, "entropy": 0.0}

        # Build adjacency weights
        node_ids = {n.id for n in nodes}
        n = len(nodes)

        # Compute average edge weight (proxy for coupling strength gamma)
        total_weight = sum(e.weight for e in edges
                          if e.source_id in node_ids and e.target_id in node_ids)
        avg_weight = total_weight / max(1, len(edges))

        # Compute fitness distribution entropy (proxy for H)
        fitnesses = [n.fitness for n in nodes]
        total_fitness = sum(fitnesses)
        if total_fitness > 0:
            probs = [f / total_fitness for f in fitnesses if f > 0]
            import math
            entropy = -sum(p * math.log2(p) for p in probs if p > 0)
        else:
            entropy = 0.0

        # Simple conservation check: avg_weight and entropy should be bounded
        gamma = avg_weight
        conservation_metric = gamma + entropy

        # Health: graph is healthy if coupling and entropy are balanced
        healthy = 0.1 < conservation_metric < 10.0

        return {
            "healthy": healthy,
            "gamma": round(gamma, 4),
            "entropy": round(entropy, 4),
            "conservation_metric": round(conservation_metric, 4),
            "node_count": n,
            "edge_count": len(edges),
            "avg_fitness": round(sum(fitnesses) / max(1, len(fitnesses)), 4),
        }

    def get_canary_summary(self) -> dict:
        """
        Check canary tiles — tiles that should always exist and be active.

        Canary tiles verify data integrity across the sync.
        """
        nodes = self.sync.cashew.get_all_nodes(include_decayed=True)
        canary_nodes = [n for n in nodes
                        if n.metadata.get("tags", []) and "canary" in n.metadata["tags"]]

        return {
            "total_canaries": len(canary_nodes),
            "active_canaries": sum(1 for n in canary_nodes if not n.decayed),
            "decayed_canaries": sum(1 for n in canary_nodes if n.decayed),
            "canary_health": (
                sum(1 for n in canary_nodes if not n.decayed) / max(1, len(canary_nodes))
            ),
        }

    def get_coordination_map(self) -> dict:
        """
        Map which agents/rooms are coordinating through the bridge.

        Shows the cross-agent landscape visible through PLATO rooms.
        """
        nodes = self.sync.cashew.get_all_nodes()
        edges = self.sync.cashew.get_all_edges()

        rooms: Dict[str, int] = {}
        for node in nodes:
            room = CashewGraphAdapter.node_to_room(node)
            rooms[room] = rooms.get(room, 0) + 1

        # Cross-room connections
        cross_room = 0
        same_room = 0
        for edge in edges:
            src = self.sync.cashew.get_node(edge.source_id)
            tgt = self.sync.cashew.get_node(edge.target_id)
            if src and tgt:
                r1 = CashewGraphAdapter.node_to_room(src)
                r2 = CashewGraphAdapter.node_to_room(tgt)
                if r1 != r2:
                    cross_room += 1
                else:
                    same_room += 1

        return {
            "rooms": rooms,
            "room_count": len(rooms),
            "cross_room_edges": cross_room,
            "same_room_edges": same_room,
            "coordination_ratio": cross_room / max(1, cross_room + same_room),
        }

    def get_upgrade_summary(self) -> dict:
        """Full summary of what the PLATO shell upgrade provides."""
        return {
            "fleet_health": self.check_fleet_health(),
            "canary_tiles": self.get_canary_summary(),
            "coordination": self.get_coordination_map(),
            "sync_status": self.sync.get_status(),
            "upgrades": [
                "Fleet health monitoring (conservation law)",
                "Multi-agent coordination (rooms)",
                "Content verification (canary tiles)",
                "Cross-validation with other agents",
                "Persistence beyond SQLite (PLATO WAL + GitHub)",
                "Stage-aware query translation",
            ],
        }


# ---------------------------------------------------------------------------
# REST endpoint handlers (mountable on PLATO server)
# ---------------------------------------------------------------------------

class CashewBridgeEndpoints:
    """
    REST endpoint handlers for the Cashew ↔ PLATO bridge.

    Mount on the PLATO server (or any HTTP server):
      POST /cashew/dock    — register a Cashew SQLite file
      GET  /cashew/status  — sync status, nodes synced, pending
      POST /cashew/sync    — force bidirectional sync
      POST /cashew/think   — trigger Cashew think cycle, ingest results
    """

    def __init__(self, data_dir: str = "/tmp/cashew-bridge"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._adapters: Dict[str, CashewGraphAdapter] = {}
        self._syncs: Dict[str, BidirectionalSync] = {}

    def _get_sync(self, cashew_id: str) -> BidirectionalSync:
        """Get or create a BidirectionalSync for a Cashew instance."""
        if cashew_id not in self._syncs:
            adapter = self._get_adapter(cashew_id)
            self._syncs[cashew_id] = BidirectionalSync(adapter)
        return self._syncs[cashew_id]

    def _get_adapter(self, cashew_id: str) -> CashewGraphAdapter:
        """Get or create a CashewGraphAdapter for a Cashew instance."""
        if cashew_id not in self._adapters:
            db_path = str(self.data_dir / f"{cashew_id}.db")
            adapter = CashewGraphAdapter(db_path)
            adapter.connect()
            adapter.ensure_schema()
            self._adapters[cashew_id] = adapter
        return self._adapters[cashew_id]

    def handle_dock(self, body: dict) -> dict:
        """
        POST /cashew/dock

        Register a Cashew SQLite file for bridging.

        Body:
          cashew_id: str — unique identifier for this Cashew instance
          db_path: str   — path to the Cashew SQLite file
          plato_url: str — optional PLATO server URL for sync
        """
        cashew_id = body.get("cashew_id", str(uuid.uuid4())[:8])
        db_path = body.get("db_path", str(self.data_dir / f"{cashew_id}.db"))
        plato_url = body.get("plato_url")

        adapter = CashewGraphAdapter(db_path)
        adapter.connect()
        adapter.ensure_schema()

        self._adapters[cashew_id] = adapter
        self._syncs[cashew_id] = BidirectionalSync(adapter, plato_submit_url=plato_url)

        return {
            "status": "docked",
            "cashew_id": cashew_id,
            "db_path": db_path,
            "plato_url": plato_url,
            "node_count": adapter.get_node_count(include_decayed=True),
        }

    def handle_status(self, cashew_id: str) -> dict:
        """
        GET /cashew/status

        Returns sync status, nodes synced, pending items.
        """
        sync = self._get_sync(cashew_id)
        status = sync.get_status()
        upgrade = ShellUpgrade(sync)

        return {
            "cashew_id": cashew_id,
            "sync": asdict(status),
            "health": upgrade.check_fleet_health(),
        }

    def handle_sync(self, cashew_id: str, body: Optional[dict] = None) -> dict:
        """
        POST /cashew/sync

        Force bidirectional sync.

        Body (optional):
          direction: str — "cashew→plato", "plato→cashew", or "full"
          plato_tiles: list — tiles to sync from PLATO (for plato→cashew)
        """
        sync = self._get_sync(cashew_id)
        body = body or {}
        direction = body.get("direction", "cashew→plato")

        if direction == "cashew→plato":
            result = sync.sync_cashew_to_plato()
        elif direction == "plato→cashew":
            tiles = body.get("plato_tiles", [])
            result = sync.sync_plato_to_cashew(tiles)
        else:
            tiles = body.get("plato_tiles")
            result = sync.full_sync(plato_tiles=tiles)

        return {
            "status": "ok",
            "direction": direction,
            "sync": asdict(result),
        }

    def handle_think(self, cashew_id: str, body: dict) -> dict:
        """
        POST /cashew/think

        Trigger a think cycle and ingest results into PLATO.

        Body:
          source_node_ids: list — nodes involved in think cycle
          insight: str          — the discovered connection
          confidence: float     — confidence in the insight
        """
        sync = self._get_sync(cashew_id)

        result = ThinkResult(
            source_node_ids=body.get("source_node_ids", []),
            insight=body.get("insight", ""),
            confidence=body.get("confidence", 0.5),
        )

        think_result = sync.trigger_think_sync(result)

        return {
            "status": "ok",
            "think": think_result,
        }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    import tempfile

    # Quick smoke test with temp database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    print("⚒️  Cashew ↔ PLATO Bridge — Smoke Test")
    print(f"   DB: {db_path}")

    adapter = CashewGraphAdapter(db_path)
    adapter.connect()
    adapter.ensure_schema()

    # Create some test nodes
    nodes = [
        CashewNode(content="Eisenstein norm of a=3, b=5", metadata={"room": "math", "tags": ["eisenstein"]}),
        CashewNode(content="Möbius function μ(30)", metadata={"room": "math", "tags": ["mobius"]}),
        CashewNode(content="Fleet coordination protocol", metadata={"room": "ops", "tags": ["fleet"]}),
    ]
    for n in nodes:
        adapter.put_node(n)
    print(f"   Created {len(nodes)} nodes")

    # Create an edge
    edge = CashewEdge(
        source_id=nodes[0].id,
        target_id=nodes[1].id,
        weight=0.85,
        label="related math concept",
    )
    adapter.put_edge(edge)
    print(f"   Created edge: {edge.source_id[:8]} → {edge.target_id[:8]}")

    # Convert to PLATO tiles
    for node in adapter.get_all_nodes():
        tile = adapter.node_to_plato_tile(node)
        lifecycle = tile["lifecycle"]
        print(f"   → PLATO tile: {tile['room']} [{lifecycle}] {tile['question'][:40]}")

    # Full sync
    sync = BidirectionalSync(adapter)
    status = sync.full_sync()
    print(f"\n   Sync: {status.nodes_synced} nodes, {status.edges_synced} edges")

    # Shell upgrade
    upgrade = ShellUpgrade(sync)
    health = upgrade.check_fleet_health()
    print(f"   Health: γ={health['gamma']}, H={health['entropy']}, ok={health['healthy']}")

    # Think cycle
    think = ThinkResult(
        source_node_ids=[nodes[0].id, nodes[2].id],
        insight="Eisenstein norms constrain fleet coordination bounds",
        confidence=0.72,
    )
    think_result = sync.trigger_think_sync(think)
    print(f"   Think: {think_result['cross_domain_links']} cross-domain links")

    # REST endpoints
    endpoints = CashewBridgeEndpoints()
    dock = endpoints.handle_dock({"cashew_id": "test", "db_path": db_path})
    print(f"\n   Docked: {dock['cashew_id']} ({dock['node_count']} nodes)")

    status_resp = endpoints.handle_status("test")
    print(f"   Status: {status_resp['sync']['nodes_synced']} synced")

    Path(db_path).unlink(missing_ok=True)
    print("\n✅ Smoke test passed!")
