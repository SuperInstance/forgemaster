#!/usr/bin/env python3
"""tests/test_room_micro_models.py — Tests for the room-micro-models architecture.

Tests cover:
  1. MicroCell: tick, simulate, recalculate, converge, daemon
  2. MicroGrid: place, cascade, synchronize, converge_on_event, step_all
  3. ConductorSync: downbeat, beat, tempo_change, cue, calibration
  4. RoomMicroModels: build_room, train, converge, harvest, feed
"""
import time
import math
import random
import unittest
from core.room_micro_models import (
    MicroCell, MicroGrid, ConductorSync, RoomMicroModels,
    GPUBackend, CellState, TMinusEvent,
)


class TestMicroCell(unittest.TestCase):
    """Test individual micro model cells."""

    def test_tick_advances_internal_time(self):
        """tick() should advance internal_time by delta * time_scale."""
        cell = MicroCell("test-cell")
        self.assertEqual(cell.internal_time, 0.0)

        entry = cell.tick(delta=1.0)
        self.assertEqual(cell.internal_time, 1.0)
        self.assertEqual(entry["t"], 1.0)

        cell.tick(delta=2.5)
        self.assertEqual(cell.internal_time, 3.5)

    def test_tick_respects_time_scale(self):
        """tick() should multiply delta by time_scale."""
        cell = MicroCell("scaled-cell")
        cell.time_scale = 2.0

        cell.tick(delta=1.0)
        self.assertEqual(cell.internal_time, 2.0)

        cell.time_scale = 0.5
        cell.tick(delta=4.0)
        self.assertEqual(cell.internal_time, 4.0)  # 2.0 + 0.5*4.0

    def test_simulate_reduces_loss(self):
        """simulate() should decrease loss over steps."""
        cell = MicroCell("sim-cell", task="drift-detect")
        initial_loss = cell.loss

        results = cell.simulate(steps=50)
        self.assertEqual(len(results), 50)
        self.assertLess(cell.loss, initial_loss)
        self.assertGreater(cell.accuracy, 0.0)
        self.assertFalse(cell.dirty)

    def test_recalculate_with_dependencies(self):
        """recalculate() should combine dependency values."""
        cell = MicroCell("dep-cell")
        dep_values = {
            "cell-a": {"prediction": 0.8, "confidence": 0.9, "loss": 0.1},
            "cell-b": {"prediction": 0.6, "confidence": 0.7, "loss": 0.3},
        }

        result = cell.recalculate(dep_values)
        self.assertIsNotNone(result)
        self.assertIn("prediction", result)
        self.assertIn("confidence", result)
        self.assertFalse(cell.dirty)

    def test_converge_adjusts_time(self):
        """converge() should adjust time_scale toward the event."""
        cell = MicroCell("conv-cell")
        cell.internal_time = 10.0
        cell.time_scale = 1.0

        event = TMinusEvent(
            event_id="test-event",
            event_type="convergence",
            target_time=time.time() + 2.0,
            required_precision=0.01,
        )

        result = cell.converge(event)
        self.assertIn("convergence_score", result)
        self.assertEqual(result["cell_id"], "conv-cell")
        self.assertGreater(cell.convergence_score, 0.0)

    def test_spawn_and_stop_daemon(self):
        """daemon should run in background and stop cleanly."""
        cell = MicroCell("daemon-cell")

        tick_count = [0]
        def work():
            tick_count[0] += 1
            return {"ticks": tick_count[0]}

        started = cell.spawn_daemon(work_fn=work, interval=0.05)
        self.assertTrue(started)
        self.assertEqual(cell.state, CellState.DAEMON)
        self.assertTrue(cell._daemon_running)

        # Let it run a few ticks
        time.sleep(0.3)
        self.assertGreater(tick_count[0], 2)

        cell.stop_daemon()
        self.assertFalse(cell._daemon_running)
        self.assertEqual(cell.state, CellState.IDLE)

    def test_status_returns_complete_state(self):
        """status() should return all cell metadata."""
        cell = MicroCell("status-cell", task="intent-detect", gpu_backend=GPUBackend.CUDACLAW)
        cell.simulate(steps=5)

        status = cell.status()
        self.assertEqual(status["cell_id"], "status-cell")
        self.assertEqual(status["task"], "intent-detect")
        self.assertEqual(status["gpu_backend"], "cudaclaw")
        self.assertEqual(status["iteration"], 5)


class TestMicroGrid(unittest.TestCase):
    """Test the 2D grid of micro model cells."""

    def setUp(self):
        self.grid = MicroGrid(3, 3, GPUBackend.CPU)
        # Place cells with dependency wiring
        for r in range(3):
            for c in range(3):
                cell = MicroCell(f"cell-{r}-{c}", task=f"task-{r}-{c}")
                if c > 0:
                    cell.dependencies.append((r, c - 1))
                if r > 0:
                    cell.dependencies.append((r - 1, c))
                self.grid.place(cell, r, c)

    def test_place_and_get(self):
        """place() and get() should store and retrieve cells."""
        cell = self.grid.get(0, 0)
        self.assertIsNotNone(cell)
        self.assertEqual(cell.cell_id, "cell-0-0")

        # Out of bounds
        self.assertIsNone(self.grid.get(5, 5))

    def test_cascade_propagates_deltas(self):
        """cascade() should propagate changes through dependencies."""
        # Set source cell value
        cell_00 = self.grid.get(0, 0)
        cell_00.value = {"prediction": 0.99, "confidence": 0.95, "loss": 0.01}

        result = self.grid.cascade(0, 0)
        self.assertGreater(result["cascaded"], 0)
        self.assertGreater(result["waves"], 0)
        self.assertEqual(result["source"], "0,0")

        # Cells that depend on [0,0] should have recalculated
        cell_01 = self.grid.get(0, 1)
        self.assertIsNotNone(cell_01.value)

    def test_synchronize_aligns_times(self):
        """synchronize() should pull cell times toward average."""
        # Give cells different internal times
        self.grid.get(0, 0).internal_time = 0.0
        self.grid.get(1, 1).internal_time = 10.0
        self.grid.get(2, 2).internal_time = 20.0

        result = self.grid.synchronize()
        self.assertEqual(result["synchronized"], 9)
        # Spread should be smaller after synchronization
        self.assertLessEqual(result["spread"], 20.0)

    def test_step_all_advances_grid_time(self):
        """step_all() should advance grid_time and all cell internal times."""
        initial_grid_time = self.grid.grid_time
        initial_cell_time = self.grid.get(1, 1).internal_time

        result = self.grid.step_all(time_delta=2.0)
        self.assertEqual(result["cells_ticked"], 9)
        self.assertAlmostEqual(self.grid.grid_time, initial_grid_time + 2.0)

        # Each cell should have advanced by 2.0 * its time_scale
        cell = self.grid.get(1, 1)
        self.assertGreater(cell.internal_time, initial_cell_time)

    def test_converge_on_event(self):
        """converge_on_event() should create event and converge cells."""
        event = self.grid.converge_on_event("test_event", t_minus=1.0)

        self.assertEqual(event.event_type, "test_event")
        self.assertEqual(event.status, "converging")
        self.assertGreater(len(event.participating_cells), 0)


class TestConductorSync(unittest.TestCase):
    """Test the orchestra conductor synchronization."""

    def test_downbeat_initializes_measure(self):
        """downbeat() should start a new measure."""
        conductor = ConductorSync(bpm=120.0)
        result = conductor.downbeat()

        self.assertEqual(result["event"], "downbeat")
        self.assertEqual(result["measure"], 1)
        self.assertEqual(result["beat"], 1)
        self.assertEqual(result["bpm"], 120.0)

    def test_beat_tracks_measure_position(self):
        """beat(n) should record position within measure."""
        conductor = ConductorSync(bpm=60.0)
        conductor.downbeat()

        for b in range(1, 5):
            result = conductor.beat(b)
            self.assertEqual(result["beat"], b)
            self.assertEqual(result["measure"], 1)

    def test_tempo_change_updates_bpm(self):
        """tempo_change() should update BPM and beat interval."""
        conductor = ConductorSync(bpm=120.0)
        result = conductor.tempo_change(180.0)

        self.assertEqual(result["old_bpm"], 120.0)
        self.assertEqual(result["new_bpm"], 180.0)
        self.assertAlmostEqual(conductor.beat_interval, 60.0 / 180.0, places=4)

    def test_cue_signals_section(self):
        """cue() should tell a section when to enter."""
        conductor = ConductorSync(bpm=120.0)
        conductor.downbeat()

        result = conductor.cue("strings")
        self.assertEqual(result["section"], "strings")
        self.assertEqual(result["enter_on_beat"], 2)  # next beat

    def test_cut_off_ends_movement(self):
        """cut_off() should end the current movement."""
        conductor = ConductorSync(bpm=120.0)
        conductor.downbeat()
        conductor.beat(2)
        conductor.beat(3)
        conductor.beat(4)
        time.sleep(0.01)  # ensure non-zero duration

        result = conductor.cut_off()
        self.assertEqual(result["event"], "cut_off")
        self.assertGreaterEqual(result["duration_s"], 0)

    def test_musician_calibration(self):
        """register_musician() + downbeat() should calibrate timing."""
        conductor = ConductorSync(bpm=120.0)

        # Register musicians with different perceived times
        conductor.register_musician("cell-0", perceived_time=time.time() - 0.1)  # early
        conductor.register_musician("cell-1", perceived_time=time.time() + 0.1)  # late

        result = conductor.downbeat()
        calibrations = result["calibrations"]

        # Early musician should be nudged later, late musician nudged earlier
        self.assertIn("cell-0", calibrations)
        self.assertIn("cell-1", calibrations)

    def test_start_section_loads_score(self):
        """start_section() should load a score and reset."""
        conductor = ConductorSync()
        score = [
            {"name": "allegro", "bpm": 140.0, "measures": 8},
            {"name": "adagio", "bpm": 60.0, "measures": 4},
        ]

        result = conductor.start_section(score)
        self.assertEqual(result["section"], "allegro")
        self.assertEqual(result["bpm"], 140.0)


class TestRoomMicroModels(unittest.TestCase):
    """Test the full orchestration layer."""

    def test_build_room_creates_grid(self):
        """build_room() should create a grid with cells."""
        orch = RoomMicroModels()
        room_id = orch.build_room(
            task="drift-detect",
            gpu_backend=GPUBackend.CPU,
            grid_size=(3, 3),
        )

        self.assertIn(room_id, orch.rooms)
        grid = orch.rooms[room_id]
        self.assertEqual(grid.rows, 3)
        self.assertEqual(grid.cols, 3)

        # All cells should be populated
        for r in range(3):
            for c in range(3):
                cell = grid.get(r, c)
                self.assertIsNotNone(cell)
                self.assertIn(room_id, cell.cell_id)

    def test_train_on_gpu_improves_accuracy(self):
        """train_on_gpu() should improve accuracy over epochs."""
        orch = RoomMicroModels()
        room_id = orch.build_room("test-train", GPUBackend.CPU, (2, 2))

        result = orch.train_on_gpu(room_id, epochs=10)
        self.assertEqual(result["epochs"], 10)
        self.assertLess(result["final_loss"], 1.0)
        self.assertGreater(result["final_accuracy"], 0.0)

        # Later epochs should have lower loss than earlier
        first_loss = result["epochs_detail"][0]["avg_loss"]
        last_loss = result["epochs_detail"][-1]["avg_loss"]
        self.assertLess(last_loss, first_loss)

    def test_converge_room(self):
        """converge() should create t-minus event for the room."""
        orch = RoomMicroModels()
        room_id = orch.build_room("test-conv", GPUBackend.CPU, (2, 2))

        result = orch.converge(room_id, "test_event", t_minus=1.0)
        self.assertIn("convergence_rate", result)
        self.assertGreater(result["total_cells"], 0)

    def test_harvest_tiles(self):
        """harvest_tiles() should extract tiles from converged cells."""
        orch = RoomMicroModels()
        room_id = orch.build_room("test-harvest", GPUBackend.CPU, (3, 3))

        # Train and converge to give cells values
        orch.train_on_gpu(room_id, epochs=5)
        orch.converge(room_id, "harvest_event", t_minus=0.5)

        tiles = orch.harvest_tiles(room_id)
        self.assertIsInstance(tiles, list)
        # Should have some tiles (cells with convergence_score > 0.5)
        if tiles:
            tile = tiles[0]
            self.assertIn("tile_id", tile)
            self.assertIn("value", tile)
            self.assertIn("source_cell", tile)

    def test_feed_fleet_returns_tiles(self):
        """feed_fleet() should report available tiles."""
        orch = RoomMicroModels()
        room_id = orch.build_room("test-feed", GPUBackend.CPU, (2, 2))
        orch.train_on_gpu(room_id, epochs=3)

        result = orch.feed_fleet(room_id)
        self.assertIn("tiles_available", result)

    def test_full_pipeline(self):
        """End-to-end: build → train → converge → harvest → feed."""
        orch = RoomMicroModels()

        # Build
        room_id = orch.build_room(
            task="drift-detect",
            gpu_backend=GPUBackend.AI_PASTURE,
            grid_size=(4, 4),
            room_id="pipeline-test",
        )

        # Train
        train_result = orch.train_on_gpu(room_id, epochs=5)
        self.assertGreater(train_result["final_accuracy"], 0.0)

        # Converge
        conv_result = orch.converge(room_id, "pipeline_done", t_minus=1.0)
        self.assertGreater(conv_result["total_cells"], 0)

        # Harvest
        tiles = orch.harvest_tiles(room_id)
        self.assertIsInstance(tiles, list)

        # Feed
        feed_result = orch.feed_fleet(room_id)
        self.assertIn("tiles_available", feed_result)

        # Status check
        status = orch.status()
        self.assertEqual(status["rooms"], 1)
        self.assertIn("pipeline-test", status["room_details"])

    def test_multiple_rooms(self):
        """Multiple rooms can coexist with different backends."""
        orch = RoomMicroModels()

        room_a = orch.build_room("task-a", GPUBackend.CPU, (2, 2), "room-a")
        room_b = orch.build_room("task-b", GPUBackend.CUDACLAW, (3, 3), "room-b")

        self.assertIn("room-a", orch.rooms)
        self.assertIn("room-b", orch.rooms)
        self.assertEqual(len(orch.rooms), 2)

        # Train both
        orch.train_on_gpu(room_a, epochs=3)
        orch.train_on_gpu(room_b, epochs=3)

        status = orch.status()
        self.assertEqual(status["rooms"], 2)


class TestTMinusEvent(unittest.TestCase):
    """Test t-minus event mechanics."""

    def test_t_minus_counts_down(self):
        """t_minus should show seconds until event."""
        event = TMinusEvent(
            event_id="future",
            event_type="convergence",
            target_time=time.time() + 5.0,
        )
        self.assertGreater(event.t_minus, 4.0)
        self.assertLessEqual(event.t_minus, 5.0)

    def test_t_minus_clamps_at_zero(self):
        """t_minus should not go negative."""
        event = TMinusEvent(
            event_id="past",
            event_type="convergence",
            target_time=time.time() - 10.0,
        )
        self.assertEqual(event.t_minus, 0.0)


if __name__ == "__main__":
    unittest.main()
