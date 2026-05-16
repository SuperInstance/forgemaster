"""Tests for PLATO WAL → GitHub sync (plato_sync.py).

Mocks git commands so no actual pushes happen during tests.
"""

import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure we can import plato_sync from the parent dir
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from plato_sync import PlatoSync, SyncConfig, SyncState


class TestSyncConfig(unittest.TestCase):
    """Test SyncConfig defaults and path resolution."""

    def test_default_paths_resolve(self):
        cfg = SyncConfig()
        self.assertTrue(cfg.local_db.endswith("plato.db"))
        self.assertTrue(cfg.wal_path.endswith("tile-wal.jsonl"))
        self.assertTrue(cfg.sync_state_path.endswith(".sync-state.json"))
        self.assertTrue(cfg.twin_dir.endswith("twin"))
        self.assertEqual(cfg.flush_interval, 50)
        self.assertEqual(cfg.github_repo, "SuperInstance/forgemaster")

    def test_custom_paths(self):
        cfg = SyncConfig(
            local_db="/tmp/test.db",
            wal_path="/tmp/test-wal.jsonl",
            sync_state_path="/tmp/test-state.json",
            twin_dir="/tmp/test-twin",
            flush_interval=25,
        )
        self.assertEqual(cfg.local_db, "/tmp/test.db")
        self.assertEqual(cfg.wal_path, "/tmp/test-wal.jsonl")
        self.assertEqual(cfg.flush_interval, 25)


class TestSyncState(unittest.TestCase):
    """Test SyncState serialization."""

    def test_round_trip(self):
        state = SyncState(
            last_flush_time=1000.0,
            last_flush_tile_count=50,
            total_tiles_synced=500,
            total_flushes=10,
            last_wal_line=500,
        )
        data = state.to_dict()
        restored = SyncState.from_dict(data)
        self.assertEqual(restored.last_flush_time, 1000.0)
        self.assertEqual(restored.total_tiles_synced, 500)
        self.assertEqual(restored.total_flushes, 10)
        self.assertEqual(restored.last_wal_line, 500)

    def test_defaults(self):
        state = SyncState()
        self.assertEqual(state.last_flush_time, 0.0)
        self.assertEqual(state.total_tiles_synced, 0)
        self.assertEqual(state.last_wal_line, 0)


class TestWALReading(unittest.TestCase):
    """Test WAL file reading and entry extraction."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.wal_path = os.path.join(self.tmpdir, "test-wal.jsonl")
        self.state_path = os.path.join(self.tmpdir, ".sync-state.json")
        self.twin_dir = os.path.join(self.tmpdir, "twin")
        self.cfg = SyncConfig(
            wal_path=self.wal_path,
            sync_state_path=self.state_path,
            twin_dir=self.twin_dir,
            flush_interval=5,
        )
        self.sync = PlatoSync(self.cfg)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_wal(self, entries):
        with open(self.wal_path, "w") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")

    def test_read_wal_lines_empty(self):
        lines = self.sync._read_wal_lines()
        self.assertEqual(lines, [])

    def test_read_wal_lines_with_entries(self):
        self._write_wal([
            {"tile_id": "1", "room": "r1"},
            {"tile_id": "2", "room": "r2"},
        ])
        lines = self.sync._read_wal_lines()
        self.assertEqual(len(lines), 2)

    def test_get_new_entries_all(self):
        self._write_wal([
            {"tile_id": "1", "room": "r1"},
            {"tile_id": "2", "room": "r2"},
        ])
        entries = self.sync._get_new_entries()
        self.assertEqual(len(entries), 2)

    def test_get_new_entries_since_last(self):
        self._write_wal([
            {"tile_id": "1", "room": "r1"},
            {"tile_id": "2", "room": "r2"},
            {"tile_id": "3", "room": "r3"},
        ])
        # Simulate: already flushed first 2 lines
        self.sync._state.last_wal_line = 2
        entries = self.sync._get_new_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["tile_id"], "3")

    def test_count_pending(self):
        self._write_wal([
            {"tile_id": "1", "room": "r1"},
            {"tile_id": "2", "room": "r2"},
        ])
        self.assertEqual(self.sync._count_pending(), 2)

        self.sync._state.last_wal_line = 1
        self.assertEqual(self.sync._count_pending(), 1)

    def test_count_pending_empty(self):
        self.assertEqual(self.sync._count_pending(), 0)


class TestFlushToGitHub(unittest.TestCase):
    """Test the flush logic with mocked git commands."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.wal_path = os.path.join(self.tmpdir, "test-wal.jsonl")
        self.state_path = os.path.join(self.tmpdir, ".sync-state.json")
        self.twin_dir = os.path.join(self.tmpdir, "twin")
        self.cfg = SyncConfig(
            wal_path=self.wal_path,
            sync_state_path=self.state_path,
            twin_dir=self.twin_dir,
            flush_interval=5,
        )
        # Create a fake twin repo with .git
        os.makedirs(os.path.join(self.twin_dir, ".git"), exist_ok=True)
        self.sync = PlatoSync(self.cfg)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_wal(self, entries):
        with open(self.wal_path, "w") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")

    @patch("plato_sync.subprocess.run")
    def test_flush_nothing(self, mock_run):
        result = self.sync.flush_to_github()
        self.assertEqual(result["status"], "nothing to flush")
        mock_run.assert_not_called()

    @patch("plato_sync.subprocess.run")
    def test_flush_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        self._write_wal([
            {"tile_id": "1", "room": "room-a", "answer": "tile1"},
            {"tile_id": "2", "room": "room-a", "answer": "tile2"},
            {"tile_id": "3", "room": "room-b", "answer": "tile3"},
        ])

        result = self.sync.flush_to_github()

        self.assertEqual(result["status"], "flushed")
        self.assertEqual(result["tiles"], 3)
        self.assertEqual(result["push_ok"], True)
        self.assertIn("room-a", result["rooms"])
        self.assertIn("room-b", result["rooms"])

        # State should be updated
        self.assertEqual(self.sync._state.last_wal_line, 3)
        self.assertEqual(self.sync._state.total_tiles_synced, 3)
        self.assertEqual(self.sync._state.total_flushes, 1)
        self.assertGreater(self.sync._state.last_flush_time, 0)

        # State file should exist
        state_data = json.loads(Path(self.state_path).read_text())
        self.assertEqual(state_data["total_tiles_synced"], 3)

    @patch("plato_sync.subprocess.run")
    def test_flush_push_failure_keeps_state(self, mock_run):
        # First call (git add): succeeds. commit succeeds. push fails.
        mock_run.side_effect = [
            MagicMock(returncode=0),  # git add
            MagicMock(returncode=0),  # git commit
            MagicMock(returncode=1),  # git push fails
        ]
        self._write_wal([{"tile_id": "1", "room": "r1"}])

        result = self.sync.flush_to_github()
        self.assertEqual(result["status"], "push_failed")
        self.assertEqual(result["push_ok"], False)

        # State should NOT advance (so tiles stay pending)
        self.assertEqual(self.sync._state.last_wal_line, 0)

    @patch("plato_sync.subprocess.run")
    def test_flush_writes_plato_data(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        self._write_wal([
            {"tile_id": "1", "room": "test-room", "data": "hello"},
        ])

        self.sync.flush_to_github()

        # Check plato-data/test-room.jsonl was written
        data_file = Path(self.twin_dir) / "plato-data" / "test-room.jsonl"
        self.assertTrue(data_file.exists())
        lines = data_file.read_text().strip().split("\n")
        self.assertEqual(len(lines), 1)
        entry = json.loads(lines[0])
        self.assertEqual(entry["tile_id"], "1")

    @patch("plato_sync.subprocess.run")
    def test_flush_incremental(self, mock_run):
        """Two flushes: second only picks up new entries."""
        mock_run.return_value = MagicMock(returncode=0)

        # First batch
        self._write_wal([
            {"tile_id": "1", "room": "r1"},
            {"tile_id": "2", "room": "r1"},
        ])
        result1 = self.sync.flush_to_github()
        self.assertEqual(result1["tiles"], 2)

        # Append more to WAL
        with open(self.wal_path, "a") as f:
            f.write(json.dumps({"tile_id": "3", "room": "r1"}) + "\n")
            f.write(json.dumps({"tile_id": "4", "room": "r2"}) + "\n")

        result2 = self.sync.flush_to_github()
        self.assertEqual(result2["tiles"], 2)
        self.assertEqual(self.sync._state.total_tiles_synced, 4)


class TestGetStatus(unittest.TestCase):
    """Test get_status endpoint data."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.wal_path = os.path.join(self.tmpdir, "test-wal.jsonl")
        self.state_path = os.path.join(self.tmpdir, ".sync-state.json")
        self.twin_dir = os.path.join(self.tmpdir, "twin")
        self.cfg = SyncConfig(
            wal_path=self.wal_path,
            sync_state_path=self.state_path,
            twin_dir=self.twin_dir,
            flush_interval=10,
        )
        self.sync = PlatoSync(self.cfg)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_status_initial(self):
        status = self.sync.get_status()
        self.assertEqual(status["wal_total"], 0)
        self.assertEqual(status["wal_pending"], 0)
        self.assertEqual(status["total_flushes"], 0)
        self.assertIsNone(status["last_flush_time_iso"])
        self.assertEqual(status["flush_interval"], 10)

    def test_status_with_pending(self):
        with open(self.wal_path, "w") as f:
            f.write(json.dumps({"tile_id": "1"}) + "\n")
            f.write(json.dumps({"tile_id": "2"}) + "\n")

        status = self.sync.get_status()
        self.assertEqual(status["wal_total"], 2)
        self.assertEqual(status["wal_pending"], 2)

    def test_status_after_partial_flush(self):
        with open(self.wal_path, "w") as f:
            for i in range(5):
                f.write(json.dumps({"tile_id": str(i)}) + "\n")

        self.sync._state.last_wal_line = 3
        status = self.sync.get_status()
        self.assertEqual(status["wal_total"], 5)
        self.assertEqual(status["wal_pending"], 2)


class TestRecovery(unittest.TestCase):
    """Test startup recovery logic."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.wal_path = os.path.join(self.tmpdir, "test-wal.jsonl")
        self.state_path = os.path.join(self.tmpdir, ".sync-state.json")
        self.twin_dir = os.path.join(self.tmpdir, "twin")
        os.makedirs(os.path.join(self.twin_dir, ".git"), exist_ok=True)
        self.cfg = SyncConfig(
            wal_path=self.wal_path,
            sync_state_path=self.state_path,
            twin_dir=self.twin_dir,
        )
        self.sync = PlatoSync(self.cfg)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch("plato_sync.subprocess.run")
    def test_recovery_no_pending(self, mock_run):
        result = self.sync.recover_on_startup()
        self.assertEqual(result["status"], "no recovery needed")
        mock_run.assert_not_called()

    @patch("plato_sync.subprocess.run")
    def test_recovery_flushes_unsynced(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        with open(self.wal_path, "w") as f:
            f.write(json.dumps({"tile_id": "1", "room": "r1"}) + "\n")
            f.write(json.dumps({"tile_id": "2", "room": "r2"}) + "\n")

        result = self.sync.recover_on_startup()
        self.assertEqual(result["recovery"], True)
        self.assertIn("tiles", result)


class TestStatePersistence(unittest.TestCase):
    """Test that sync state survives PlatoSync restarts."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.state_path = os.path.join(self.tmpdir, ".sync-state.json")
        self.wal_path = os.path.join(self.tmpdir, "test-wal.jsonl")
        self.twin_dir = os.path.join(self.tmpdir, "twin")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_state_survives_restart(self):
        cfg = SyncConfig(
            wal_path=self.wal_path,
            sync_state_path=self.state_path,
            twin_dir=self.twin_dir,
        )

        # First instance: write state
        sync1 = PlatoSync(cfg)
        sync1._state.total_tiles_synced = 42
        sync1._state.last_wal_line = 10
        sync1._save_state()

        # Second instance: read state back
        sync2 = PlatoSync(cfg)
        self.assertEqual(sync2._state.total_tiles_synced, 42)
        self.assertEqual(sync2._state.last_wal_line, 10)


if __name__ == "__main__":
    unittest.main()
