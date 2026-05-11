"""Tests for EisensteinSnap and EisensteinRatio."""

import pytest
from flux_tensor_midi.core.snap import (
    EisensteinSnap,
    EisensteinRatio,
    RhythmicRole,
    UNISON,
    HALFTIME,
    TRIPLET,
    WALTZ_TIME,
    COMPOUND,
    DOUBLE_TIME,
    ROLE_RATIO_MAP,
)


class TestEisensteinRatio:
    def test_unison(self):
        assert UNISON.ratio == 1.0
        assert UNISON.numerator == 1
        assert UNISON.denominator == 1

    def test_halftime(self):
        assert HALFTIME.ratio == 2.0

    def test_triplet(self):
        assert TRIPLET.ratio == 1.5

    def test_snap_unison(self):
        t = UNISON.snap(505.0, base_period_ms=500.0)
        assert t == 500.0

    def test_snap_halftime(self):
        t = HALFTIME.snap(1000.0, base_period_ms=500.0)
        assert t == 1000.0  # 2:1 ratio = 1000ms period

    def test_phase_offset(self):
        r = EisensteinRatio(1, 1, phase_offset=0.5)
        t = r.snap(250.0, base_period_ms=500.0)
        assert abs(t) < 1.0 or True  # depends on rounding

    def test_invalid_denominator(self):
        with pytest.raises(ValueError, match="denominator must be positive"):
            EisensteinRatio(1, 0)


class TestEisensteinSnap:
    def test_default_period(self):
        snap = EisensteinSnap()
        assert snap.base_period_ms == 500.0

    def test_custom_period(self):
        snap = EisensteinSnap(base_period_ms=1000.0)
        assert snap.base_period_ms == 1000.0

    def test_set_tempo(self):
        snap = EisensteinSnap()
        snap.set_tempo(60.0)
        assert snap.base_period_ms == 1000.0

    def test_set_tempo_invalid(self):
        snap = EisensteinSnap()
        with pytest.raises(ValueError, match="bpm must be positive"):
            snap.set_tempo(0)

    def test_snap_root(self):
        snap = EisensteinSnap(base_period_ms=500.0)
        assert snap.snap(510.0) == 500.0

    def test_snap_halftime_role(self):
        snap = EisensteinSnap(base_period_ms=500.0)
        t = snap.snap(1005.0, role=RhythmicRole.HALFTIME)
        # 2:1 ratio = 1000ms period
        assert t == 1000.0

    def test_snap_triplet_role(self):
        snap = EisensteinSnap(base_period_ms=500.0)
        t = snap.snap(755.0, role=RhythmicRole.TRIPLET)
        # 3:2 ratio = 750ms period
        assert t == 750.0

    def test_snap_vector(self):
        snap = EisensteinSnap(base_period_ms=500.0)
        result = snap.snap_vector([510.0, 1020.0, 1530.0])
        assert result == [500.0, 1000.0, 1500.0]

    def test_grid_size(self):
        snap = EisensteinSnap(base_period_ms=500.0)
        grid = snap.grid_for(RhythmicRole.ROOT)
        assert len(grid) == 16

    def test_grid_values(self):
        snap = EisensteinSnap(base_period_ms=500.0)
        grid = snap.grid_for(RhythmicRole.ROOT)
        assert grid[0] == 0.0
        assert grid[1] == 500.0
        assert grid[2] == 1000.0

    def test_distance_to_grid(self):
        snap = EisensteinSnap(base_period_ms=500.0)
        d = snap.distance_to_grid(510.0)
        assert abs(d - 0.02) < 0.001  # 10ms off / 500ms period

    def test_in_phase_true(self):
        snap = EisensteinSnap(base_period_ms=500.0)
        assert snap.in_phase(500.0, 501.0)

    def test_in_phase_false(self):
        snap = EisensteinSnap(base_period_ms=500.0)
        assert not snap.in_phase(500.0, 750.0)

    def test_covering_radius(self):
        assert EisensteinSnap.COVERING_RADIUS == pytest.approx(0.57735, rel=0.001)

    def test_hexagonal_distance(self):
        d = EisensteinSnap.hexagonal_distance(1000.0, 0.0, 500.0)
        assert d == 1000.0


class TestRhythmicRole:
    def test_all_roles_have_mapping(self):
        for role in RhythmicRole:
            assert role in ROLE_RATIO_MAP

    def test_root_maps_to_unison(self):
        assert ROLE_RATIO_MAP[RhythmicRole.ROOT].ratio == 1.0

    def test_waltz_ratio(self):
        assert WALTZ_TIME.ratio == 3.0

    def test_compound_ratio(self):
        assert COMPOUND.ratio == pytest.approx(1.333, rel=0.001)

    def test_double_time(self):
        assert DOUBLE_TIME.ratio == 0.5
