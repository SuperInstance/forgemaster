"""Unit tests for temporal snap (T-minus-0 detection)."""

import math
import unittest

from snapkit.temporal import TemporalSnap, TemporalResult, BeatGrid


class TestBeatGrid(unittest.TestCase):
    """Tests for the BeatGrid class."""

    def test_creation(self):
        grid = BeatGrid(period=1.0, phase=0.0)
        self.assertEqual(grid.period, 1.0)
        self.assertEqual(grid.phase, 0.0)

    def test_nearest_beat_on_grid(self):
        grid = BeatGrid(period=1.0, phase=0.0)
        for t in [0.0, 1.0, 2.0, 5.0, -3.0]:
            beat_time, idx = grid.nearest_beat(t)
            self.assertAlmostEqual(beat_time, t, places=10)

    def test_nearest_beat_off_grid(self):
        grid = BeatGrid(period=1.0, phase=0.0)
        # t=0.4 → nearest beat at 0.0
        bt, idx = grid.nearest_beat(0.4)
        self.assertAlmostEqual(bt, 0.0)
        self.assertEqual(idx, 0)

        # t=0.6 → nearest beat at 1.0
        bt, idx = grid.nearest_beat(0.6)
        self.assertAlmostEqual(bt, 1.0)
        self.assertEqual(idx, 1)

    def test_snap_on_beat(self):
        grid = BeatGrid(period=1.0, phase=0.0)
        result = grid.snap(0.05, tolerance=0.1)
        self.assertTrue(result.is_on_beat)
        self.assertAlmostEqual(result.snapped_time, 0.0)
        self.assertAlmostEqual(result.offset, 0.05)

    def test_snap_off_beat(self):
        grid = BeatGrid(period=1.0, phase=0.0)
        result = grid.snap(0.5, tolerance=0.1)
        self.assertFalse(result.is_on_beat)

    def test_phase_offset(self):
        grid = BeatGrid(period=2.0, phase=0.5)
        # t=0.5 should be on the grid
        result = grid.snap(0.5, tolerance=0.1)
        self.assertTrue(result.is_on_beat)
        self.assertAlmostEqual(result.snapped_time, 0.5)

    def test_beats_in_range(self):
        grid = BeatGrid(period=1.0, phase=0.0)
        beats = grid.beats_in_range(0.0, 3.0)
        self.assertEqual(len(beats), 4)  # 0, 1, 2, 3
        for i, b in enumerate(beats):
            self.assertAlmostEqual(b, float(i))

    def test_beats_in_range_empty(self):
        grid = BeatGrid(period=1.0, phase=0.0)
        beats = grid.beats_in_range(5.0, 3.0)  # reversed range
        self.assertEqual(len(beats), 0)

    def test_beat_phase(self):
        grid = BeatGrid(period=1.0, phase=0.0)
        result = grid.snap(0.25, tolerance=0.5)
        self.assertAlmostEqual(result.beat_phase, 0.25)

        result = grid.snap(0.75, tolerance=0.5)
        self.assertAlmostEqual(result.beat_phase, 0.75)

    def test_negative_period_raises(self):
        with self.assertRaises(ValueError):
            BeatGrid(period=-1.0)


class TestTemporalSnap(unittest.TestCase):
    """Tests for the TemporalSnap T-0 detector."""

    def test_basic_snap(self):
        grid = BeatGrid(period=1.0)
        snap = TemporalSnap(grid, tolerance=0.1)
        result = snap.observe(0.05, 0.5)
        self.assertIsInstance(result, TemporalResult)
        self.assertTrue(result.is_on_beat)

    def test_t0_detection_flat_signal(self):
        """A flat signal at zero should NOT trigger T-0 (no derivative sign change)."""
        grid = BeatGrid(period=1.0)
        snap = TemporalSnap(grid, t0_threshold=0.1)

        for i in range(10):
            result = snap.observe(float(i), 0.0)

        # Flat at zero — no sign change in derivative
        self.assertFalse(result.is_t_minus_0)

    def test_t0_detection_peak(self):
        """A signal that peaks (goes up then down) near zero should trigger T-0."""
        grid = BeatGrid(period=1.0)
        snap = TemporalSnap(grid, t0_threshold=0.5)

        # Rising signal approaching threshold
        values = [0.3, 0.1, 0.01, 0.1, 0.3]  # dip to near-zero then back up
        result = None
        for i, v in enumerate(values):
            result = snap.observe(float(i), v)

        # Should detect the T-0 at the minimum
        self.assertIsNotNone(result)

    def test_t0_no_detection_outside_threshold(self):
        """Signal far from zero should not trigger T-0."""
        grid = BeatGrid(period=1.0)
        snap = TemporalSnap(grid, t0_threshold=0.05)

        for i in range(10):
            result = snap.observe(float(i), 5.0)

        self.assertFalse(result.is_t_minus_0)

    def test_history_tracked(self):
        grid = BeatGrid(period=1.0)
        snap = TemporalSnap(grid)

        snap.observe(0.0, 1.0)
        snap.observe(1.0, 2.0)

        self.assertEqual(len(snap.history), 2)

    def test_reset_clears_history(self):
        grid = BeatGrid(period=1.0)
        snap = TemporalSnap(grid)

        snap.observe(0.0, 1.0)
        snap.observe(1.0, 2.0)
        snap.reset()

        self.assertEqual(len(snap.history), 0)

    def test_window_size_limit(self):
        """History should be bounded by 2 * t0_window."""
        grid = BeatGrid(period=1.0)
        snap = TemporalSnap(grid, t0_window=3)

        for i in range(100):
            snap.observe(float(i), float(i % 5))

        self.assertLessEqual(len(snap.history), 6)  # 2 * window


class TestTemporalResult(unittest.TestCase):
    """Tests for TemporalResult dataclass."""

    def test_immutable(self):
        result = TemporalResult(
            original_time=1.0,
            snapped_time=1.0,
            offset=0.0,
            is_on_beat=True,
            is_t_minus_0=False,
            beat_index=1,
            beat_phase=0.0,
        )
        with self.assertRaises(AttributeError):
            result.original_time = 2.0  # type: ignore


if __name__ == "__main__":
    unittest.main()
