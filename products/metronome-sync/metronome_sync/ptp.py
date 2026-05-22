"""PTP offset estimation — the heart of anti-fragile clock sync.

Provides multiple strategies for computing clock offsets from peer measurements:
  NAIVE       — unweighted average (breaks under latency)
  CRISTIAN    — RTT-weighted Cristian's algorithm
  PTP         — Precision Time Protocol style (symmetric path assumption)
  EXPONENTIAL — exponential moving average of PTP offsets
"""

from __future__ import annotations

from enum import Enum, auto
from fractions import Fraction
from dataclasses import dataclass, field
from typing import List, Tuple


class PtpMode(Enum):
    NAIVE = auto()
    CRISTIAN = auto()
    PTP = auto()
    EXPONENTIAL = auto()


@dataclass
class PeerSample:
    """One measurement from a remote peer."""
    local_sent: Fraction       # our clock when we sent the probe
    remote_recv: Fraction      # their clock when they received it
    remote_sent: Fraction      # their clock when they replied
    local_recv: Fraction       # our clock when we got the reply
    weight: Fraction = Fraction(1)  # staleness weight (1 = freshest)

    @property
    def rtt(self) -> Fraction:
        """Round-trip time (local frame)."""
        return self.local_recv - self.local_sent

    @property
    def staleness(self) -> Fraction:
        """Inverse freshness — older samples have higher staleness."""
        return Fraction(1) - self.weight


def compute_offset(
    local_time: Fraction,
    remote_time: Fraction,
    rtt: Fraction,
    mode: PtpMode = PtpMode.PTP,
) -> Fraction:
    """Estimate the offset of *our* clock relative to the peer.

    Returns a Fraction ``offset`` such that ``our_time + offset ≈ peer_time``.
    A positive offset means our clock is behind the peer.
    """
    if rtt < 0:
        raise ValueError("RTT cannot be negative")

    if mode == PtpMode.NAIVE:
        # Unweighted difference — simple but wrong under latency
        return remote_time - local_time

    if mode == PtpMode.CRISTIAN:
        # Cristian's algorithm: estimate one-way delay = RTT/2
        if rtt == 0:
            return remote_time - local_time
        one_way = rtt / 2
        return (remote_time - one_way) - local_time

    if mode == PtpMode.PTP:
        # PTP offset: θ = ((t1 - t0) + (t2 - t3)) / 2
        # Here simplified: offset = (remote - local) - RTT/2
        # which equals: remote_time - (local_time + RTT/2)
        if rtt == 0:
            return remote_time - local_time
        return remote_time - (local_time + rtt / 2)

    if mode == PtpMode.EXPONENTIAL:
        # Same as PTP but designed to be used with EMA externally
        if rtt == 0:
            return remote_time - local_time
        return remote_time - (local_time + rtt / 2)

    raise ValueError(f"Unknown PtpMode: {mode}")


def compute_offset_from_sample(sample: PeerSample, mode: PtpMode = PtpMode.PTP) -> Fraction:
    """Compute offset from a full four-timestamp sample.

    Uses the standard PTP formula:
        θ = ((remote_recv - local_sent) + (remote_sent - local_recv)) / 2
    """
    offset_raw = (
        (sample.remote_recv - sample.local_sent)
        + (sample.remote_sent - sample.local_recv)
    ) / 2
    # Weight by staleness — fresher samples contribute more
    return offset_raw * sample.weight


def weighted_offsets(
    samples: List[PeerSample],
    mode: PtpMode = PtpMode.PTP,
) -> Fraction:
    """Combine multiple peer offsets into one weighted correction.

    Each sample is weighted by its staleness factor (1 = freshest).
    """
    if not samples:
        return Fraction(0)

    total_weight = Fraction(0)
    weighted_sum = Fraction(0)

    for s in samples:
        w = s.weight
        offset = compute_offset_from_sample(s, mode)
        weighted_sum += offset * w
        total_weight += w

    if total_weight == 0:
        return Fraction(0)

    return weighted_sum / total_weight


class OffsetEstimator:
    """Maintains an EMA of PTP offsets for smooth corrections."""

    def __init__(self, alpha: Fraction = Fraction(1, 2)):
        self.alpha = alpha          # EMA smoothing factor
        self.ema: Fraction | None = None
        self._samples: int = 0

    def update(self, offset: Fraction) -> Fraction:
        """Feed a new offset; returns the current EMA."""
        self._samples += 1
        if self.ema is None:
            self.ema = offset
        else:
            self.ema = self.alpha * offset + (1 - self.alpha) * self.ema
        return self.ema

    @property
    def value(self) -> Fraction:
        return self.ema if self.ema is not None else Fraction(0)

    @property
    def sample_count(self) -> int:
        return self._samples

    def reset(self) -> None:
        self.ema = None
        self._samples = 0
