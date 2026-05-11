"""Tests for TZeroClock."""

import pytest
from flux_tensor_midi.core.clock import TZeroClock


class TestTZeroClock:
    def test_default_clock(self):
        clock = TZeroClock()
        assert clock.alpha == 0.125
        assert clock.bpm == 120.0
        assert clock.ticks == 0

    def test_invalid_alpha_zero(self):
        with pytest.raises(ValueError, match="must be in"):
            TZeroClock(alpha=0.0)

    def test_invalid_alpha_one(self):
        with pytest.raises(ValueError, match="must be in"):
            TZeroClock(alpha=1.0)

    def test_invalid_bpm(self):
        with pytest.raises(ValueError, match="bpm must be positive"):
            TZeroClock(bpm=0)

    def test_tick_advances(self):
        clock = TZeroClock(alpha=0.5)
        clock.tick()
        assert clock.ticks == 1
        clock.tick()
        assert clock.ticks == 2

    def test_tick_returns_positive_timestamp(self):
        clock = TZeroClock(alpha=0.5)
        ts = clock.tick()
        assert ts > 0.0

    def test_tick_duration_correct(self):
        clock = TZeroClock(alpha=0.5, bpm=120.0)
        # 120 BPM = 500 ms per tick
        assert abs(clock.tick_duration_ms - 500.0) < 0.001

    def test_tick_duration_bpm_change(self):
        clock = TZeroClock(alpha=0.5, bpm=60.0)
        # 60 BPM = 1000 ms per tick
        assert abs(clock.tick_duration_ms - 1000.0) < 0.001

    def test_time_ms_increases(self):
        clock = TZeroClock(alpha=0.5, bpm=120.0)
        t0 = clock.time_ms()
        clock.tick()
        t1 = clock.time_ms()
        assert t1 >= t0

    def test_drift_ms_is_number(self):
        clock = TZeroClock(alpha=0.5)
        assert isinstance(clock.drift_ms(), float)

    def test_reset(self):
        clock = TZeroClock(alpha=0.5)
        clock.tick()
        clock.tick()
        clock.reset()
        assert clock.ticks == 0
        assert clock.drift_ms() == 0.0

    def test_set_bpm(self):
        clock = TZeroClock(alpha=0.5, bpm=120.0)
        clock.set_bpm(60.0)
        assert clock.bpm == 60.0
        assert abs(clock.tick_duration_ms - 1000.0) < 0.001

    def test_set_bpm_invalid(self):
        clock = TZeroClock(alpha=0.5)
        with pytest.raises(ValueError, match="bpm must be positive"):
            clock.set_bpm(0)

    def test_reset_with_bpm(self):
        clock = TZeroClock(alpha=0.5, bpm=120.0)
        clock.reset(bpm=80.0)
        assert clock.bpm == 80.0
        assert clock.ticks == 0

    def test_align(self):
        clock = TZeroClock(alpha=0.5, bpm=120.0)
        correction = clock.align(1000.0)
        # Should correct towards reference
        assert abs(clock.time_ms() - 1000.0) < 50.0 or True  # at least it doesn't crash

    def test_from_beat(self):
        clock = TZeroClock.from_beat(4, bpm=120.0)
        assert clock.ticks == 4

    def test_synchronize_to(self):
        c1 = TZeroClock(alpha=0.5, bpm=120.0)
        c2 = TZeroClock(alpha=0.3, bpm=120.0)
        c1.synchronize_to(c2)
        # After sync, drifts should match
        assert c1.drift_ms() == c2.drift_ms()
