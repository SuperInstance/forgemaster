"""Tests for metronome-dashboard."""

import time
import threading

from metronome_dashboard.charts import bar_chart, heat_map, sparkline, _resample
from metronome_dashboard.simulator import Agent, AgentState, Fleet
from metronome_dashboard.cli import (
    build_agent_table,
    build_drift_panel,
    build_topology_panel,
    build_protocol_panel,
    build_latency_panel,
)


# ── charts.py ──────────────────────────────────────────────────────

class TestSparkline:
    def test_empty(self):
        assert sparkline([]) == ""

    def test_single_value(self):
        result = sparkline([5.0])
        assert len(result) == 40  # upsampled to default width

    def test_respects_width(self):
        result = sparkline([float(i) for i in range(100)], width=20)
        assert len(result) == 20

    def test_flat_line(self):
        result = sparkline([3.0] * 50, width=10)
        assert all(c == "▁" for c in result)

    def test_ascending(self):
        result = sparkline([float(i) for i in range(8)], width=8)
        assert result == "▁▂▃▄▅▆▇█"


class TestBarChart:
    def test_empty(self):
        assert bar_chart([], []) == ""

    def test_output_lines(self):
        result = bar_chart(["a", "b"], [1.0, 2.0])
        assert result.count("\n") == 1  # 2 lines = 1 newline

    def test_negative_values(self):
        result = bar_chart(["x"], [-1.0])
        assert "x" in result


class TestHeatMap:
    def test_empty(self):
        assert heat_map([]) == ""

    def test_single_row(self):
        result = heat_map([[1.0, 2.0, 3.0]])
        assert len(result) > 0

    def test_with_labels(self):
        result = heat_map([[0, 1], [1, 0]], row_labels=["A", "B"], col_labels=["X", "Y"])
        assert "A" in result
        assert "B" in result


class TestResample:
    def test_identity(self):
        vals = [1.0, 2.0, 3.0]
        assert _resample(vals, 3) == vals

    def test_downsample(self):
        result = _resample([float(i) for i in range(100)], 10)
        assert len(result) == 10

    def test_upsample(self):
        result = _resample([1.0, 2.0], 10)
        assert len(result) == 10


# ── simulator.py ──────────────────────────────────────────────────

class TestAgent:
    def test_tick_updates_offset(self):
        a = Agent(name="test", drift_rate=0.001)
        initial = a.true_offset
        a.tick(0.05)
        assert a.true_offset != initial

    def test_tick_records_history(self):
        a = Agent(name="test")
        a.tick(0.05)
        assert len(a.history) == 1

    def test_correct_reduces_offset(self):
        a = Agent(name="test", true_offset=0.01)
        a.correct(factor=0.8)
        assert abs(a.true_offset) < 0.01

    def test_state_locked_when_close(self):
        a = Agent(name="test", true_offset=1e-9, drift_rate=0.0, jitter_ns=0.0)
        a.tick(0.01)
        assert a.state == AgentState.LOCKED

    def test_history_capped(self):
        a = Agent(name="test")
        for _ in range(250):
            a.tick(0.01)
        assert len(a.history) <= 200


class TestFleet:
    def test_create_default(self):
        f = Fleet.create(n=5)
        assert len(f.agents) == 5

    def test_create_deterministic(self):
        f1 = Fleet.create(n=3, seed=7)
        f2 = Fleet.create(n=3, seed=7)
        assert f1.agents[0].true_offset == f2.agents[0].true_offset

    def test_latency_matrix_shape(self):
        f = Fleet.create(n=4)
        m = f.latency_matrix()
        assert len(m) == 4
        assert all(len(row) == 4 for row in m)

    def test_latency_matrix_zero_diagonal(self):
        f = Fleet.create(n=3)
        m = f.latency_matrix()
        for i in range(3):
            assert m[i][i] == 0.0

    def test_start_stop(self):
        f = Fleet.create(n=3)
        f.start()
        assert f.running
        time.sleep(0.3)
        f.stop()
        assert not f.running


# ── cli.py (panels, no live display) ──────────────────────────────

class TestPanels:
    def test_agent_table_renders(self):
        f = Fleet.create(n=5)
        table = build_agent_table(f)
        assert table is not None

    def test_drift_panel_renders(self):
        f = Fleet.create(n=3)
        for a in f.agents:
            for _ in range(10):
                a.tick(0.05)
        panel = build_drift_panel(f)
        assert panel is not None

    def test_topology_panel(self):
        f = Fleet.create(n=3)
        panel = build_topology_panel(f)
        assert panel is not None

    def test_protocol_panel(self):
        panel = build_protocol_panel()
        assert panel is not None

    def test_latency_panel_renders(self):
        f = Fleet.create(n=4)
        panel = build_latency_panel(f)
        assert panel is not None
