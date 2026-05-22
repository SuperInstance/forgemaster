"""Core probe logic: simulate a fleet, measure offset/jitter/convergence, compare strategies."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np


@dataclass
class Peer:
    """A simulated peer in the fleet."""

    host: str
    port: int
    true_offset_ms: float = 0.0  # static offset from "true" time
    jitter_ms: float = 1.0  # network jitter (std dev)

    @classmethod
    def from_str(cls, s: str) -> "Peer":
        host, _, port = s.partition(":")
        return cls(host=host, port=int(port))


@dataclass
class SyncResult:
    """Result from a single sync strategy run."""

    strategy: str
    offsets: list[float] = field(default_factory=list)
    estimated_offset_ms: float = 0.0
    residual_offset_ms: float = 0.0
    jitter_ms: float = 0.0
    convergence_ticks: int = 0
    delta_ms: float = 0.0  # recommended uncertainty bound

    @property
    def score(self) -> float:
        """Lower is better."""
        return self.residual_offset_ms + 0.5 * self.jitter_ms + 0.1 * self.convergence_ticks


@dataclass
class ProbeConfig:
    """Configuration for a probe run."""

    peers: list[Peer] = field(default_factory=list)
    duration_s: float = 30.0
    tick_interval_s: float = 0.01  # 10ms ticks
    strategies: list[str] = field(default_factory=lambda: ["naive", "cristian", "ptp", "exponential"])
    initial_offset_ms: float = 50.0  # start this far off


def _simulate_exchange(peer: Peer, local_offset: float) -> tuple[float, float]:
    """Simulate an NTP-like exchange. Returns (estimated_offset, round_trip_time)."""
    network_delay = np.random.normal(0.5, peer.jitter_ms)  # one-way delay
    network_delay = max(0.01, network_delay)
    rtt = 2 * network_delay
    # What the peer reports as offset
    measured = peer.true_offset_ms + np.random.normal(0, peer.jitter_ms * 0.1)
    # Account for our local offset
    error = np.random.normal(0, rtt / 2)
    estimated = measured + error
    return estimated, rtt


def sync_naive(peers: list[Peer], n_ticks: int) -> SyncResult:
    """Naive: average all peer offsets, no weighting."""
    offsets = []
    local_offset = np.random.uniform(-50, 50)
    for tick in range(n_ticks):
        measurements = []
        for peer in peers:
            est, _ = _simulate_exchange(peer, local_offset)
            measurements.append(est)
        correction = np.mean(measurements)
        local_offset -= correction * 0.5  # simple proportional correction
        offsets.append(abs(local_offset))
        if abs(local_offset) < 0.1 and tick > 10:
            pass  # keep going for measurement

    return SyncResult(
        strategy="naive",
        offsets=offsets,
        estimated_offset_ms=local_offset,
        residual_offset_ms=abs(np.mean(offsets[-20:])),
        jitter_ms=float(np.std(offsets[-20:])),
        convergence_ticks=_find_convergence(offsets, threshold=0.5),
        delta_ms=float(np.std(offsets[-20:]) * 3),
    )


def sync_cristian(peers: list[Peer], n_ticks: int) -> SyncResult:
    """Cristian's algorithm: use min-RTT peer for best estimate."""
    offsets = []
    local_offset = np.random.uniform(-50, 50)
    for tick in range(n_ticks):
        best_est = 0.0
        best_rtt = float("inf")
        for peer in peers:
            est, rtt = _simulate_exchange(peer, local_offset)
            if rtt < best_rtt:
                best_rtt = rtt
                best_est = est
        # Cristian: offset = (T1 - T0 + T2 - T3) / 2
        correction = best_est - best_rtt / 2
        local_offset -= correction * 0.7
        offsets.append(abs(local_offset))

    return SyncResult(
        strategy="cristian",
        offsets=offsets,
        estimated_offset_ms=local_offset,
        residual_offset_ms=abs(np.mean(offsets[-20:])),
        jitter_ms=float(np.std(offsets[-20:])),
        convergence_ticks=_find_convergence(offsets, threshold=0.5),
        delta_ms=float(np.std(offsets[-20:]) * 3),
    )


def sync_ptp(peers: list[Peer], n_ticks: int) -> SyncResult:
    """PTP-like: best master clock selection with weighted correction."""
    offsets = []
    local_offset = np.random.uniform(-50, 50)
    # Select "best" peer (lowest jitter as proxy for stratum)
    best_peer = min(peers, key=lambda p: p.jitter_ms) if peers else peers[0]

    for tick in range(n_ticks):
        est, rtt = _simulate_exchange(best_peer, local_offset)
        # PTP correction: compensate for propagation delay
        correction = est - rtt / 2
        # PTP uses a PI controller
        proportional = correction * 0.6
        integral = correction * 0.1
        local_offset -= (proportional + integral)
        offsets.append(abs(local_offset))

    return SyncResult(
        strategy="ptp",
        offsets=offsets,
        estimated_offset_ms=local_offset,
        residual_offset_ms=abs(np.mean(offsets[-20:])),
        jitter_ms=float(np.std(offsets[-20:])),
        convergence_ticks=_find_convergence(offsets, threshold=0.5),
        delta_ms=float(np.std(offsets[-20:]) * 3),
    )


def sync_exponential(peers: list[Peer], n_ticks: int) -> SyncResult:
    """Exponential backoff sync: aggressive early, conservative late."""
    offsets = []
    local_offset = np.random.uniform(-50, 50)
    alpha = 0.9  # initial learning rate

    for tick in range(n_ticks):
        measurements = []
        for peer in peers:
            est, _ = _simulate_exchange(peer, local_offset)
            measurements.append(est)
        correction = np.mean(measurements)
        # Exponential decay of correction rate
        rate = alpha * (0.995 ** tick)
        local_offset -= correction * rate
        offsets.append(abs(local_offset))

    return SyncResult(
        strategy="exponential",
        offsets=offsets,
        estimated_offset_ms=local_offset,
        residual_offset_ms=abs(np.mean(offsets[-20:])),
        jitter_ms=float(np.std(offsets[-20:])),
        convergence_ticks=_find_convergence(offsets, threshold=0.5),
        delta_ms=float(np.std(offsets[-20:]) * 3),
    )


STRATEGIES = {
    "naive": sync_naive,
    "cristian": sync_cristian,
    "ptp": sync_ptp,
    "exponential": sync_exponential,
}


def _find_convergence(offsets: list[float], threshold: float = 0.5) -> int:
    """Find the first tick where offset stays below threshold for 20 ticks."""
    below_count = 0
    for i, o in enumerate(offsets):
        if o < threshold:
            below_count += 1
            if below_count >= 20:
                return i - 19
        else:
            below_count = 0
    return len(offsets)


def run_probe(config: ProbeConfig) -> list[SyncResult]:
    """Run all strategies and return results."""
    n_ticks = int(config.duration_s / config.tick_interval_s)
    n_ticks = max(n_ticks, 100)  # at least 100 ticks

    peers = config.peers or [
        Peer("localhost", 19840, true_offset_ms=0.0, jitter_ms=1.0),
        Peer("localhost", 19841, true_offset_ms=5.0, jitter_ms=2.0),
    ]

    results = []
    for name in config.strategies:
        fn = STRATEGIES.get(name)
        if fn is None:
            continue
        np.random.seed(42)  # reproducible
        result = fn(peers, n_ticks)
        results.append(result)

    return results


def benchmark_strategies(strategies: list[str], ticks: int = 1000) -> list[SyncResult]:
    """Run a quick benchmark with simulated peers."""
    config = ProbeConfig(
        peers=[
            Peer("peer-a", 19840, true_offset_ms=0.0, jitter_ms=0.5),
            Peer("peer-b", 19841, true_offset_ms=3.0, jitter_ms=1.5),
            Peer("peer-c", 19842, true_offset_ms=-2.0, jitter_ms=3.0),
        ],
        duration_s=ticks * 0.01,
        strategies=strategies,
    )
    return run_probe(config)


def rank_results(results: Sequence[SyncResult]) -> list[SyncResult]:
    """Rank results by score (lower is better)."""
    return sorted(results, key=lambda r: r.score)
