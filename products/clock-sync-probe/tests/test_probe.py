"""Tests for clock-sync-probe."""

import json
import os
import tempfile

import numpy as np
import pytest

from clock_sync_probe import __version__
from clock_sync_probe.probe import (
    Peer,
    ProbeConfig,
    SyncResult,
    _find_convergence,
    benchmark_strategies,
    rank_results,
    run_probe,
    sync_naive,
    sync_cristian,
    sync_ptp,
    sync_exponential,
    STRATEGIES,
)
from clock_sync_probe.visualize import ascii_timeline, quick_summary


# --- Peer tests ---

def test_peer_from_str():
    p = Peer.from_str("host.example.com:19840")
    assert p.host == "host.example.com"
    assert p.port == 19840


def test_peer_from_str_localhost():
    p = Peer.from_str("localhost:12345")
    assert p.host == "localhost"
    assert p.port == 12345


def test_peer_defaults():
    p = Peer("a", 1)
    assert p.true_offset_ms == 0.0
    assert p.jitter_ms == 1.0


# --- Convergence finder ---

def test_find_convergence_immediate():
    offsets = [0.1] * 30
    assert _find_convergence(offsets, threshold=0.5) == 0


def test_find_convergence_never():
    offsets = [10.0] * 100
    assert _find_convergence(offsets, threshold=0.5) == 100


def test_find_convergence_partial():
    # First 30 high, then 30 low
    offsets = [10.0] * 30 + [0.1] * 30
    result = _find_convergence(offsets, threshold=0.5)
    assert result == 30  # index 30 is first below-threshold tick


def test_find_convergence_empty():
    assert _find_convergence([], threshold=0.5) == 0


# --- SyncResult ---

def test_sync_result_score():
    r = SyncResult(strategy="test", residual_offset_ms=1.0, jitter_ms=2.0, convergence_ticks=10)
    assert r.score == pytest.approx(1.0 + 0.5 * 2.0 + 0.1 * 10.0)


def test_sync_result_score_default():
    r = SyncResult(strategy="test")
    assert r.score == 0.0


# --- Strategy tests ---

def _make_peers():
    return [
        Peer("a", 19840, true_offset_ms=0.0, jitter_ms=0.5),
        Peer("b", 19841, true_offset_ms=2.0, jitter_ms=1.0),
    ]


def test_sync_naive_runs():
    np.random.seed(42)
    result = sync_naive(_make_peers(), 500)
    assert result.strategy == "naive"
    assert len(result.offsets) == 500
    assert result.residual_offset_ms >= 0


def test_sync_cristian_runs():
    np.random.seed(42)
    result = sync_cristian(_make_peers(), 500)
    assert result.strategy == "cristian"
    assert len(result.offsets) == 500
    assert result.delta_ms >= 0


def test_sync_ptp_runs():
    np.random.seed(42)
    result = sync_ptp(_make_peers(), 500)
    assert result.strategy == "ptp"
    assert result.convergence_ticks >= 0


def test_sync_exponential_runs():
    np.random.seed(42)
    result = sync_exponential(_make_peers(), 500)
    assert result.strategy == "exponential"
    assert result.residual_offset_ms >= 0


def test_all_strategies_registered():
    assert set(STRATEGIES.keys()) == {"naive", "cristian", "ptp", "exponential"}


# --- Probe run ---

def test_run_probe_default():
    config = ProbeConfig(duration_s=0.5)
    results = run_probe(config)
    assert len(results) == 4
    for r in results:
        assert r.strategy in STRATEGIES


def test_run_probe_subset_strategies():
    config = ProbeConfig(duration_s=0.5, strategies=["naive", "ptp"])
    results = run_probe(config)
    assert len(results) == 2
    assert results[0].strategy == "naive"
    assert results[1].strategy == "ptp"


# --- Benchmark ---

def test_benchmark_strategies():
    results = benchmark_strategies(["naive", "ptp"], ticks=200)
    assert len(results) == 2


# --- Ranking ---

def test_rank_results():
    r1 = SyncResult(strategy="a", residual_offset_ms=1.0, jitter_ms=0.0, convergence_ticks=0)
    r2 = SyncResult(strategy="b", residual_offset_ms=0.1, jitter_ms=0.0, convergence_ticks=0)
    ranked = rank_results([r1, r2])
    assert ranked[0].strategy == "b"
    assert ranked[1].strategy == "a"


# --- Visualization ---

def test_ascii_timeline_empty():
    assert "No results" in ascii_timeline([])


def test_ascii_timeline_renders():
    np.random.seed(42)
    result = sync_naive(_make_peers(), 200)
    output = ascii_timeline([result])
    assert "naive" in output
    assert "█" in output or "▄" in output


def test_quick_summary():
    r = SyncResult(strategy="ptp", residual_offset_ms=0.5, jitter_ms=0.3, delta_ms=0.9, convergence_ticks=42)
    s = quick_summary(r)
    assert "ptp" in s
    assert "0.5" in s


# --- CLI tests ---

def test_version():
    assert __version__ == "0.1.0"
