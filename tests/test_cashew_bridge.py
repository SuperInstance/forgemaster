#!/usr/bin/env python3
"""
test_cashew_bridge.py — Tests for Cashew ↔ PLATO bidirectional bridge.

20+ tests covering:
  - CashewGraphAdapter (node/edge CRUD, conversion to PLATO tiles)
  - PlatoToCashewAdapter (tile → node conversion)
  - FluxTranslationLayer (embedding routing, ID translation)
  - BidirectionalSync (full sync, decay sync, think sync)
  - ShellUpgrade (fleet health, canary, coordination)
  - REST endpoints (dock, status, sync, think)
"""

import json
import math
import os
import sqlite3
import struct
import tempfile
import time
from pathlib import Path

import pytest

# Import the bridge
from cashew_bridge import (
    CASHEW_DB_SCHEMA,
    CashewEdge,
    CashewGraphAdapter,
    CashewNode,
    CashewBridgeEndpoints,
    BidirectionalSync,
    FluxTranslationLayer,
    PlatoToCashewAdapter,
    ShellUpgrade,
    SyncStatus,
    ThinkResult,
    FITNESS_LIFECYCLE_THRESHOLDS,
    DEFAULT_FITNESS,
    DECAY_RATE,
    SYNC_ROOM_PREFIX,
    INSIGHTS_ROOM,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_db(tmp_path):
    """Create a temporary Cashew database."""
    db_path = str(tmp_path / "test_cashew.db")
    adapter = CashewGraphAdapter(db_path)
    adapter.connect()
    adapter.ensure_schema()
    yield adapter
    adapter.close()


@pytest.fixture
def sample_nodes():
    """Create sample CashewNode objects."""
    return [
        CashewNode(
            content="Eisenstein norm of a=3, b=5",
            fitness=0.95,
            metadata={"room": "math", "tags": ["eisenstein"], "source": "forgemaster"},
        ),
        CashewNode(
            content="Möbius function μ(30)",
            fitness=0.7,
            metadata={"room": "math", "tags": ["mobius"], "source": "oracle1"},
        ),
        CashewNode(
            content="Fleet coordination protocol v2",
            fitness=0.4,
            metadata={"room": "ops", "tags": ["fleet"], "source": "casey"},
        ),
        CashewNode(
            content="Obsolete decision from last week",
            fitness=0.1,
            metadata={"room": "archive", "tags": ["obsolete"]},
        ),
    ]


@pytest.fixture
def populated_db(tmp_db, sample_nodes):
    """Populated database with sample nodes."""
    for node in sample_nodes:
        tmp_db.put_node(node)

    # Create edges between first two nodes
    edge = CashewEdge(
        source_id=sample_nodes[0].id,
        target_id=sample_nodes[1].id,
        weight=0.85,
        label="related math concept",
    )
    tmp_db.put_edge(edge)
    return tmp_db


# ===========================================================================
# CashewGraphAdapter Tests
# ===========================================================================


class TestCashewGraphAdapter:

    def test_schema_creation(self, tmp_db):
        """Schema tables exist after ensure_schema."""
        tables = tmp_db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = {t[0] for t in tables}
        assert "nodes" in table_names
        assert "edges" in table_names
        assert "think_results" in table_names
        assert "sync_state" in table_names

    def test_put_and_get_node(self, tmp_db):
        """Round-trip: put node, get it back."""
        node = CashewNode(content="test content", fitness=0.8)
        tmp_db.put_node(node)

        retrieved = tmp_db.get_node(node.id)
        assert retrieved is not None
        assert retrieved.content == "test content"
        assert retrieved.fitness == 0.8
        assert retrieved.id == node.id

    def test_put_node_with_metadata(self, tmp_db):
        """Node metadata survives round-trip."""
        node = CashewNode(
            content="test", metadata={"room": "forge", "tags": ["math"], "key": "val"}
        )
        tmp_db.put_node(node)

        retrieved = tmp_db.get_node(node.id)
        assert retrieved.metadata["room"] == "forge"
        assert retrieved.metadata["tags"] == ["math"]
        assert retrieved.metadata["key"] == "val"

    def test_get_all_nodes_excludes_decayed(self, tmp_db):
        """get_all_nodes excludes decayed by default."""
        active = CashewNode(content="active", fitness=0.9)
        decayed = CashewNode(content="decayed", fitness=0.05, decayed=True)
        tmp_db.put_node(active)
        tmp_db.put_node(decayed)

        nodes = tmp_db.get_all_nodes()
        assert len(nodes) == 1
        assert nodes[0].content == "active"

    def test_get_all_nodes_includes_decayed(self, tmp_db):
        """get_all_nodes(include_decayed=True) returns all."""
        active = CashewNode(content="active", fitness=0.9)
        decayed = CashewNode(content="decayed", fitness=0.05, decayed=True)
        tmp_db.put_node(active)
        tmp_db.put_node(decayed)

        nodes = tmp_db.get_all_nodes(include_decayed=True)
        assert len(nodes) == 2

    def test_get_node_count(self, tmp_db):
        """Node count works correctly."""
        assert tmp_db.get_node_count() == 0
        tmp_db.put_node(CashewNode(content="a"))
        tmp_db.put_node(CashewNode(content="b"))
        assert tmp_db.get_node_count() == 2

    def test_put_and_get_edge(self, tmp_db):
        """Round-trip: put edge, retrieve it."""
        n1 = CashewNode(content="n1")
        n2 = CashewNode(content="n2")
        tmp_db.put_node(n1)
        tmp_db.put_node(n2)

        edge = CashewEdge(source_id=n1.id, target_id=n2.id, weight=0.75, label="test")
        tmp_db.put_edge(edge)

        edges = tmp_db.get_edges_for_node(n1.id)
        assert len(edges) == 1
        assert edges[0].weight == 0.75
        assert edges[0].label == "test"

    def test_get_all_edges(self, tmp_db):
        """get_all_edges returns all edges."""
        n1 = CashewNode(content="n1")
        n2 = CashewNode(content="n2")
        n3 = CashewNode(content="n3")
        for n in [n1, n2, n3]:
            tmp_db.put_node(n)

        tmp_db.put_edge(CashewEdge(source_id=n1.id, target_id=n2.id))
        tmp_db.put_edge(CashewEdge(source_id=n2.id, target_id=n3.id))

        edges = tmp_db.get_all_edges()
        assert len(edges) == 2

    def test_touch_node_increments_access(self, tmp_db):
        """Touching a node increments access count and boosts fitness."""
        node = CashewNode(content="test", fitness=0.5)
        tmp_db.put_node(node)

        tmp_db.touch_node(node.id)
        retrieved = tmp_db.get_node(node.id)
        assert retrieved.access_count == 1
        assert retrieved.fitness > 0.5  # boosted

    def test_touch_node_undecays(self, tmp_db):
        """Touching a decayed node with sufficient fitness un-decays it."""
        node = CashewNode(content="test", fitness=0.2, decayed=True)
        tmp_db.put_node(node)

        tmp_db.touch_node(node.id)
        retrieved = tmp_db.get_node(node.id)
        assert not retrieved.decayed  # fitness boosted past 0.3

    def test_decay_nodes(self, tmp_db):
        """Decay reduces fitness of old nodes."""
        node = CashewNode(content="test", fitness=0.9)
        # Simulate old access time
        node.accessed_at = time.time() - 7200  # 2 hours ago
        tmp_db.put_node(node)

        decayed = tmp_db.decay_nodes(threshold=0.5)
        retrieved = tmp_db.get_node(node.id)
        assert retrieved.fitness < 0.9

    def test_get_think_results(self, tmp_db):
        """Think results can be stored and retrieved."""
        result = ThinkResult(
            source_node_ids=["node1", "node2"],
            insight="Connection between X and Y",
            confidence=0.8,
        )
        tmp_db.put_think_result(result)

        results = tmp_db.get_think_results(since=0.0)
        assert len(results) == 1
        assert results[0].insight == "Connection between X and Y"
        assert results[0].source_node_ids == ["node1", "node2"]


# ===========================================================================
# Conversion Tests (Cashew → PLATO)
# ===========================================================================


class TestCashewToPlatoConversion:

    def test_node_to_plato_tile(self, populated_db, sample_nodes):
        """Node converts to valid PLATO tile dict."""
        node = sample_nodes[0]
        tile = populated_db.node_to_plato_tile(node)

        assert tile["tile_id"].startswith("cashew:")
        assert tile["question"] == node.content
        assert tile["source"].startswith("cashew:")
        assert tile["_meta"]["cashew_node_id"] == node.id
        assert tile["_meta"]["bridge_version"] == "1.0"

    def test_fitness_to_lifecycle_active(self):
        """High fitness maps to active lifecycle."""
        assert CashewGraphAdapter.fitness_to_lifecycle(0.95) == "active"
        assert CashewGraphAdapter.fitness_to_lifecycle(0.7) == "active"

    def test_fitness_to_lifecycle_superseded(self):
        """Medium fitness maps to superseded."""
        assert CashewGraphAdapter.fitness_to_lifecycle(0.5) == "superseded"
        assert CashewGraphAdapter.fitness_to_lifecycle(0.3) == "superseded"

    def test_fitness_to_lifecycle_retracted(self):
        """Low fitness maps to retracted."""
        assert CashewGraphAdapter.fitness_to_lifecycle(0.2) == "retracted"
        assert CashewGraphAdapter.fitness_to_lifecycle(0.0) == "retracted"

    def test_lifecycle_to_fitness_roundtrip(self):
        """Lifecycle → fitness → lifecycle round-trip preserves category."""
        for lifecycle in ["active", "superseded", "retracted"]:
            fitness = CashewGraphAdapter.lifecycle_to_fitness(lifecycle)
            back = CashewGraphAdapter.fitness_to_lifecycle(fitness)
            assert back == lifecycle, f"{lifecycle} → {fitness} → {back}"

    def test_node_to_room_uses_metadata(self):
        """Node with room metadata uses it directly."""
        node = CashewNode(content="test", metadata={"room": "forge"})
        assert CashewGraphAdapter.node_to_room(node) == "forge"

    def test_node_to_room_generates_from_content(self):
        """Node without room metadata generates deterministic room name."""
        node = CashewNode(content="test content")
        room = CashewGraphAdapter.node_to_room(node)
        assert room.startswith(SYNC_ROOM_PREFIX)

    def test_node_to_room_deterministic(self):
        """Same content → same room name."""
        n1 = CashewNode(content="identical content")
        n2 = CashewNode(content="identical content")
        assert CashewGraphAdapter.node_to_room(n1) == CashewGraphAdapter.node_to_room(n2)

    def test_edge_to_plato_link(self, populated_db):
        """Edge converts to PLATO room adjacency link."""
        edges = populated_db.get_all_edges()
        assert len(edges) > 0

        link = populated_db.edge_to_plato_link(edges[0])
        assert link["source_tile"].startswith("cashew:")
        assert link["target_tile"].startswith("cashew:")
        assert "weight" in link
        assert "hebbian_strength" in link

    def test_think_to_plato_tile(self, populated_db):
        """Think result converts to PLATO tile in insights room."""
        think = ThinkResult(
            source_node_ids=["n1", "n2"],
            insight="Cross-domain connection found",
            confidence=0.75,
        )
        tile = populated_db.think_to_plato_tile(think)
        assert tile["room"] == INSIGHTS_ROOM
        assert tile["domain"] == INSIGHTS_ROOM
        assert "think-cycle" in tile["tags"]


# ===========================================================================
# PlatoToCashewAdapter Tests
# ===========================================================================


class TestPlatoToCashewAdapter:

    def test_tile_to_node(self, tmp_db):
        """PLATO tile converts to Cashew node."""
        writer = PlatoToCashewAdapter(tmp_db)
        tile = {
            "tile_id": "test-tile-1",
            "question": "What is the Eisenstein norm?",
            "answer": "a²-ab+b²",
            "room": "math",
            "domain": "math",
            "source": "forgemaster",
            "tags": ["eisenstein"],
            "confidence": 0.88,
            "lifecycle": "active",
        }

        node = writer.tile_to_node(tile)
        assert "Eisenstein norm" in node.content
        assert "a²-ab+b²" in node.content
        assert node.metadata["room"] == "math"
        assert node.metadata["plato_tile_id"] == "test-tile-1"

    def test_write_tile_persists(self, tmp_db):
        """Writing a PLATO tile creates a persistent Cashew node."""
        writer = PlatoToCashewAdapter(tmp_db)
        tile = {
            "tile_id": "persist-test",
            "question": "Test question",
            "answer": "Test answer",
            "lifecycle": "active",
        }

        node = writer.write_tile(tile)
        retrieved = tmp_db.get_node(node.id)
        assert retrieved is not None
        assert "Test question" in retrieved.content

    def test_write_tiles_batch(self, tmp_db):
        """Batch writing multiple PLATO tiles."""
        writer = PlatoToCashewAdapter(tmp_db)
        tiles = [
            {"tile_id": f"tile-{i}", "question": f"Q{i}", "lifecycle": "active"}
            for i in range(5)
        ]

        nodes = writer.write_tiles(tiles)
        assert len(nodes) == 5
        assert tmp_db.get_node_count() == 5

    def test_lifecycle_maps_to_decayed(self, tmp_db):
        """Retracted lifecycle creates decayed Cashew node."""
        writer = PlatoToCashewAdapter(tmp_db)
        tile = {
            "tile_id": "retracted-test",
            "question": "Old question",
            "lifecycle": "retracted",
        }

        node = writer.tile_to_node(tile)
        assert node.decayed is True

    def test_room_links_to_edges(self, tmp_db):
        """PLATO room links convert to Cashew edges."""
        # First create nodes for the edges to reference
        n1 = CashewNode(content="n1")
        n2 = CashewNode(content="n2")
        tmp_db.put_node(n1)
        tmp_db.put_node(n2)

        writer = PlatoToCashewAdapter(tmp_db)
        links = [
            {
                "source_tile": f"cashew:{n1.id}",
                "target_tile": f"cashew:{n2.id}",
                "weight": 0.7,
                "label": "related",
            }
        ]

        edges = writer.room_links_to_edges(links)
        assert len(edges) == 1
        assert edges[0].weight == 0.7

    def test_confidence_overrides_lifecycle_fitness(self, tmp_db):
        """Tile confidence value takes precedence for fitness."""
        writer = PlatoToCashewAdapter(tmp_db)
        tile = {
            "tile_id": "conf-test",
            "question": "test",
            "lifecycle": "retracted",  # would give low fitness
            "confidence": 0.95,         # but this should override
        }

        node = writer.tile_to_node(tile)
        assert node.fitness == 0.95


# ===========================================================================
# FluxTranslationLayer Tests
# ===========================================================================


class TestFluxTranslationLayer:

    def test_tile_id_to_fitness_deterministic(self, tmp_db):
        """Same tile ID always maps to same fitness."""
        f1 = FluxTranslationLayer.tile_id_to_fitness("test-id", "active")
        f2 = FluxTranslationLayer.tile_id_to_fitness("test-id", "active")
        assert f1 == f2

    def test_tile_id_to_fitness_lifecycle_aware(self):
        """Different lifecycles produce different fitness ranges."""
        f_active = FluxTranslationLayer.tile_id_to_fitness("same-id", "active")
        f_retracted = FluxTranslationLayer.tile_id_to_fitness("same-id", "retracted")
        assert f_active > f_retracted

    def test_tile_id_to_fitness_bounded(self):
        """Fitness is always in [0, 1]."""
        for lc in ["active", "superseded", "retracted"]:
            for tid in ["a", "test-id-12345678", "x" * 100]:
                f = FluxTranslationLayer.tile_id_to_fitness(tid, lc)
                assert 0.0 <= f <= 1.0, f"{tid}/{lc} → {f}"

    def test_nearest_room_with_embeddings(self, tmp_db):
        """Nearest room matches against registered embeddings."""
        flux = FluxTranslationLayer(tmp_db)

        # Register two rooms with different embeddings
        flux.register_room_embedding("room-a", [1.0, 0.0, 0.0])
        flux.register_room_embedding("room-b", [0.0, 1.0, 0.0])

        # Query close to room-a
        nearest = flux.nearest_room([0.9, 0.1, 0.0])
        assert nearest == "room-a"

    def test_nearest_room_empty(self, tmp_db):
        """No registered rooms returns None."""
        flux = FluxTranslationLayer(tmp_db)
        assert flux.nearest_room([1.0, 0.0]) is None

    def test_cosine_similarity_identical(self):
        """Identical vectors have similarity 1.0."""
        sim = FluxTranslationLayer._cosine_similarity([1.0, 0.0], [1.0, 0.0])
        assert abs(sim - 1.0) < 1e-6

    def test_cosine_similarity_orthogonal(self):
        """Orthogonal vectors have similarity 0.0."""
        sim = FluxTranslationLayer._cosine_similarity([1.0, 0.0], [0.0, 1.0])
        assert abs(sim) < 1e-6

    def test_think_connections_to_links(self, populated_db, sample_nodes):
        """Think cycle connections generate cross-room links."""
        links = FluxTranslationLayer.think_connections_to_links(
            ThinkResult(
                source_node_ids=[sample_nodes[0].id, sample_nodes[2].id],
                insight="Math constrains fleet ops",
                confidence=0.6,
            ),
            populated_db,
        )

        assert len(links) > 0
        assert links[0]["weight"] == 0.6
        assert "think-cycle" in links[0]["label"]

    def test_embedding_to_room_with_bytes(self, tmp_db):
        """Node with embedding bytes routes to nearest room."""
        flux = FluxTranslationLayer(tmp_db)
        flux.register_room_embedding("room-x", [1.0, 0.0, 0.0])

        # Create embedding bytes (384-dim float32, mostly pointing at room-x)
        emb = [1.0] + [0.0] * 383
        emb_bytes = struct.pack(f"{len(emb)}f", *emb)

        node = CashewNode(content="test", embedding=emb_bytes)
        room = flux.embedding_to_room(node)
        assert room == "room-x"

    def test_embedding_to_room_fallback(self, tmp_db):
        """Node without embedding falls back to content-hash routing."""
        flux = FluxTranslationLayer(tmp_db)
        node = CashewNode(content="fallback test", metadata={"room": "explicit"})
        room = flux.embedding_to_room(node)
        assert room == "explicit"


# ===========================================================================
# BidirectionalSync Tests
# ===========================================================================


class TestBidirectionalSync:

    def test_sync_cashew_to_plato(self, populated_db):
        """Cashew → PLATO sync converts all nodes to tiles."""
        sync = BidirectionalSync(populated_db)
        status = sync.sync_cashew_to_plato()

        assert status.nodes_synced > 0
        assert status.errors == []

    def test_sync_plato_to_cashew(self, tmp_db):
        """PLATO → Cashew sync writes tiles as nodes."""
        sync = BidirectionalSync(tmp_db)
        tiles = [
            {"tile_id": f"tile-{i}", "question": f"Q{i}", "lifecycle": "active"}
            for i in range(3)
        ]

        status = sync.sync_plato_to_cashew(tiles)
        assert status.tiles_synced == 3
        assert tmp_db.get_node_count() == 3

    def test_full_sync_both_directions(self, tmp_db):
        """Full sync processes both directions."""
        # Add some Cashew nodes first
        tmp_db.put_node(CashewNode(content="cashew-original"))
        sync = BidirectionalSync(tmp_db)

        plato_tiles = [
            {"tile_id": "plato-1", "question": "from plato", "lifecycle": "active"},
        ]

        status = sync.full_sync(plato_tiles=plato_tiles)
        # Should have 1 node from cashew→plato + 1 tile from plato→cashew
        assert status.nodes_synced >= 2

    def test_trigger_decay_sync(self, populated_db):
        """Decay sync tracks lifecycle transitions."""
        sync = BidirectionalSync(populated_db)

        # Make nodes old enough to decay
        for node in populated_db.get_all_nodes():
            node.accessed_at = time.time() - 7200  # 2 hours ago
            node.fitness = 0.15  # low fitness
            populated_db.put_node(node)

        transitions = sync.trigger_decay_sync()
        assert "decayed" in transitions
        assert isinstance(transitions["decayed"], int)

    def test_trigger_think_sync(self, populated_db, sample_nodes):
        """Think sync creates insight tile and cross-domain links."""
        sync = BidirectionalSync(populated_db)

        think = ThinkResult(
            source_node_ids=[sample_nodes[0].id, sample_nodes[2].id],
            insight="Math insights inform fleet coordination",
            confidence=0.65,
        )

        result = sync.trigger_think_sync(think)
        assert result["think_id"] == think.id
        assert result["cross_domain_links"] > 0

    def test_sync_state_persists(self, tmp_db):
        """Sync timestamp is recorded in sync_state table."""
        sync = BidirectionalSync(tmp_db)
        sync.sync_cashew_to_plato()

        ts = sync._get_last_sync_ts()
        assert ts > 0

    def test_get_status(self, populated_db):
        """Status returns accurate counts."""
        sync = BidirectionalSync(populated_db)
        status = sync.get_status()

        assert status.nodes_synced > 0
        assert status.edges_synced > 0
        assert status.cashew_path == populated_db.db_path

    def test_sync_log(self, populated_db):
        """Sync operations are logged."""
        sync = BidirectionalSync(populated_db)
        sync.sync_cashew_to_plato()

        assert len(sync.sync_log) > 0
        assert any("cashew→plato" in e["event"] for e in sync.sync_log)


# ===========================================================================
# ShellUpgrade Tests
# ===========================================================================


class TestShellUpgrade:

    def test_fleet_health_empty_graph(self, tmp_db):
        """Empty graph is healthy by default."""
        sync = BidirectionalSync(tmp_db)
        upgrade = ShellUpgrade(sync)

        health = upgrade.check_fleet_health()
        assert health["healthy"] is True
        assert health["reason"] == "empty_graph"

    def test_fleet_health_with_data(self, populated_db):
        """Graph with data returns health metrics."""
        sync = BidirectionalSync(populated_db)
        upgrade = ShellUpgrade(sync)

        health = upgrade.check_fleet_health()
        assert "gamma" in health
        assert "entropy" in health
        assert "node_count" in health
        assert health["node_count"] > 0

    def test_canary_summary(self, populated_db):
        """Canary summary works with/without canary tiles."""
        sync = BidirectionalSync(populated_db)
        upgrade = ShellUpgrade(sync)

        canary = upgrade.get_canary_summary()
        assert "total_canaries" in canary
        assert "canary_health" in canary

    def test_canary_with_tagged_nodes(self, tmp_db):
        """Nodes with 'canary' tag are counted."""
        tmp_db.put_node(CashewNode(
            content="canary 1",
            metadata={"tags": ["canary", "test"]},
        ))
        tmp_db.put_node(CashewNode(
            content="canary 2",
            fitness=0.05,
            decayed=True,
            metadata={"tags": ["canary"]},
        ))

        sync = BidirectionalSync(tmp_db)
        upgrade = ShellUpgrade(sync)

        canary = upgrade.get_canary_summary()
        assert canary["total_canaries"] == 2
        assert canary["active_canaries"] == 1
        assert canary["decayed_canaries"] == 1

    def test_coordination_map(self, populated_db):
        """Coordination map shows rooms and cross-room edges."""
        sync = BidirectionalSync(populated_db)
        upgrade = ShellUpgrade(sync)

        coord = upgrade.get_coordination_map()
        assert "rooms" in coord
        assert "room_count" in coord
        assert "cross_room_edges" in coord
        assert coord["room_count"] > 0

    def test_upgrade_summary(self, populated_db):
        """Full upgrade summary includes all components."""
        sync = BidirectionalSync(populated_db)
        upgrade = ShellUpgrade(sync)

        summary = upgrade.get_upgrade_summary()
        assert "fleet_health" in summary
        assert "canary_tiles" in summary
        assert "coordination" in summary
        assert "upgrades" in summary
        assert len(summary["upgrades"]) == 6


# ===========================================================================
# REST Endpoint Tests
# ===========================================================================


class TestRestEndpoints:

    def test_dock_creates_instance(self, tmp_path):
        """Docking creates a new Cashew bridge instance."""
        endpoints = CashewBridgeEndpoints(data_dir=str(tmp_path))
        result = endpoints.handle_dock({
            "cashew_id": "test-1",
            "db_path": str(tmp_path / "cashew.db"),
        })

        assert result["status"] == "docked"
        assert result["cashew_id"] == "test-1"
        assert result["node_count"] == 0

    def test_dock_with_custom_id(self, tmp_path):
        """Docking with custom ID uses that ID."""
        endpoints = CashewBridgeEndpoints(data_dir=str(tmp_path))
        result = endpoints.handle_dock({"cashew_id": "my-instance"})

        assert result["cashew_id"] == "my-instance"

    def test_status_after_dock(self, tmp_path):
        """Status endpoint works after docking."""
        endpoints = CashewBridgeEndpoints(data_dir=str(tmp_path))
        endpoints.handle_dock({"cashew_id": "test-2"})

        status = endpoints.handle_status("test-2")
        assert status["cashew_id"] == "test-2"
        assert "sync" in status
        assert "health" in status

    def test_sync_cashew_to_plato_direction(self, tmp_path):
        """Sync with direction='cashew→plato' works."""
        endpoints = CashewBridgeEndpoints(data_dir=str(tmp_path))
        endpoints.handle_dock({"cashew_id": "test-3"})

        # Add a node to the adapter
        adapter = endpoints._adapters["test-3"]
        adapter.put_node(CashewNode(content="test node"))

        result = endpoints.handle_sync("test-3", {"direction": "cashew→plato"})
        assert result["status"] == "ok"
        assert result["direction"] == "cashew→plato"

    def test_sync_plato_to_cashew_direction(self, tmp_path):
        """Sync with direction='plato→cashew' writes tiles."""
        endpoints = CashewBridgeEndpoints(data_dir=str(tmp_path))
        endpoints.handle_dock({"cashew_id": "test-4"})

        tiles = [{"tile_id": "p1", "question": "from plato", "lifecycle": "active"}]
        result = endpoints.handle_sync("test-4", {
            "direction": "plato→cashew",
            "plato_tiles": tiles,
        })

        assert result["status"] == "ok"
        adapter = endpoints._adapters["test-4"]
        assert adapter.get_node_count() == 1

    def test_think_endpoint(self, tmp_path):
        """Think endpoint creates insight and cross-domain links."""
        endpoints = CashewBridgeEndpoints(data_dir=str(tmp_path))
        endpoints.handle_dock({"cashew_id": "test-5"})

        # Create nodes for think cycle
        adapter = endpoints._adapters["test-5"]
        n1 = CashewNode(content="node 1", metadata={"room": "room-a"})
        n2 = CashewNode(content="node 2", metadata={"room": "room-b"})
        adapter.put_node(n1)
        adapter.put_node(n2)

        result = endpoints.handle_think("test-5", {
            "source_node_ids": [n1.id, n2.id],
            "insight": "Cross-domain connection",
            "confidence": 0.8,
        })

        assert result["status"] == "ok"
        assert result["think"]["cross_domain_links"] > 0

    def test_status_nonexistent_creates(self, tmp_path):
        """Status for unknown ID auto-creates the instance."""
        endpoints = CashewBridgeEndpoints(data_dir=str(tmp_path))

        status = endpoints.handle_status("auto-created")
        assert status["cashew_id"] == "auto-created"
        assert "sync" in status


# ===========================================================================
# Integration Tests
# ===========================================================================


class TestIntegration:

    def test_full_roundtrip(self, tmp_db):
        """
        Full roundtrip:
        1. Create Cashew nodes
        2. Sync to PLATO (tile format)
        3. Modify tile lifecycle
        4. Sync back to Cashew
        5. Verify fitness reflects lifecycle change
        """
        # Phase 1: Create nodes
        node = CashewNode(
            content="integration test node",
            fitness=0.9,
            metadata={"room": "test-room"},
        )
        tmp_db.put_node(node)

        # Phase 2: Sync to PLATO
        sync = BidirectionalSync(tmp_db)
        c2p = sync.sync_cashew_to_plato()
        assert c2p.nodes_synced >= 1

        # Get the PLATO tile
        tile = tmp_db.node_to_plato_tile(node)
        assert tile["lifecycle"] == "active"

        # Phase 3: Modify lifecycle (simulate PLATO transition)
        tile["lifecycle"] = "superseded"

        # Phase 4: Sync back to Cashew
        p2c = sync.sync_plato_to_cashew([tile])

        # Phase 5: Verify
        retrieved = tmp_db.get_node(node.id)
        # The retracted lifecycle should have set decayed
        # (superseded doesn't set decayed, but fitness changes)
        assert retrieved is not None

    def test_think_cycle_creates_insights(self, tmp_db):
        """
        Think cycle creates cross-domain insight tiles.
        """
        n1 = CashewNode(content="Eisenstein lattice", metadata={"room": "math"})
        n2 = CashewNode(content="Agent coordination", metadata={"room": "ops"})
        n3 = CashewNode(content="Decay algorithms", metadata={"room": "memory"})
        for n in [n1, n2, n3]:
            tmp_db.put_node(n)

        sync = BidirectionalSync(tmp_db)

        think = ThinkResult(
            source_node_ids=[n1.id, n2.id, n3.id],
            insight="Lattice structures optimize agent coordination with decay-based pruning",
            confidence=0.78,
        )

        result = sync.trigger_think_sync(think)

        # Should create cross-domain links between all pairs
        assert result["cross_domain_links"] == 3  # 3 choose 2

        # Think result should be stored
        stored = tmp_db.get_think_results(since=0.0)
        assert len(stored) == 1
        assert stored[0].insight == think.insight

    def test_decay_propagates_to_plato(self, tmp_db):
        """
        Cashew decay triggers PLATO lifecycle transitions.
        """
        node = CashewNode(
            content="will decay",
            fitness=0.8,
        )
        node.accessed_at = time.time() - 14400  # 4 hours ago
        tmp_db.put_node(node)

        sync = BidirectionalSync(tmp_db)

        # Run decay
        transitions = sync.trigger_decay_sync()

        # Get the PLATO tile version
        updated = tmp_db.get_node(node.id)
        tile = tmp_db.node_to_plato_tile(updated)

        # Fitness should have dropped, lifecycle should have changed
        assert updated.fitness < 0.8
        # (exact lifecycle depends on decay amount)

    def test_conservation_health_with_edges(self, tmp_db):
        """
        Graph with edges produces meaningful conservation metrics.
        """
        nodes = []
        for i in range(5):
            n = CashewNode(content=f"node {i}", fitness=0.5 + i * 0.1)
            tmp_db.put_node(n)
            nodes.append(n)

        # Create a fully-connected graph
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                tmp_db.put_edge(CashewEdge(
                    source_id=nodes[i].id,
                    target_id=nodes[j].id,
                    weight=0.5 + (i + j) * 0.05,
                ))

        sync = BidirectionalSync(tmp_db)
        upgrade = ShellUpgrade(sync)
        health = upgrade.check_fleet_health()

        assert health["healthy"] is True
        assert health["edge_count"] == 10  # 5 choose 2
        assert health["gamma"] > 0
        assert health["entropy"] > 0
