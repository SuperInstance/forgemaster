"""Tests for Zeitgeist Protocol — Python implementation"""

import random
import unittest
from zeitgeist import (
    Zeitgeist, PrecisionState, ConfidenceState, TrajectoryState,
    ConsensusState, TemporalState, FluxPacket, Trend, Phase,
)


def random_zeitgeist() -> Zeitgeist:
    bloom = bytes(random.randint(0, 255) for _ in range(32))
    crdt = {random.randint(0, 10**18): random.randint(0, 10**18) for _ in range(random.randint(0, 5))}
    return Zeitgeist(
        precision=PrecisionState(
            deadband=random.uniform(0.001, 99999),
            funnel_pos=random.uniform(0, 1),
            snap_imminent=random.choice([True, False]),
        ),
        confidence=ConfidenceState(
            bloom=bloom,
            parity=random.randint(0, 255),
            certainty=random.uniform(0, 1),
        ),
        trajectory=TrajectoryState(
            hurst=random.uniform(0, 1),
            trend=random.choice([Trend.STABLE, Trend.RISING, Trend.FALLING, Trend.CHAOTIC]),
            velocity=random.uniform(-10, 10),
        ),
        consensus=ConsensusState(
            holonomy=random.uniform(0, 1),
            peer_agreement=random.uniform(0, 1),
            crdt_version=crdt,
        ),
        temporal=TemporalState(
            beat_pos=random.uniform(0, 1),
            phase=random.choice([Phase.IDLE, Phase.APPROACHING, Phase.SNAP, Phase.HOLD]),
            rhythm_coherence=random.uniform(0, 1),
        ),
    )


class TestMergeLaws(unittest.TestCase):
    """Prove CRDT semilattice laws with 100 random iterations each."""

    def test_commutativity(self):
        for _ in range(100):
            a = random_zeitgeist()
            b = random_zeitgeist()
            self.assertEqual(a.merge(b).to_dict(), b.merge(a).to_dict())

    def test_associativity(self):
        for _ in range(100):
            a = random_zeitgeist()
            b = random_zeitgeist()
            c = random_zeitgeist()
            self.assertEqual(
                a.merge(b).merge(c).to_dict(),
                a.merge(b.merge(c)).to_dict(),
            )

    def test_idempotency(self):
        for _ in range(100):
            a = random_zeitgeist()
            self.assertEqual(a.merge(a).to_dict(), a.to_dict())

    def test_json_roundtrip(self):
        for _ in range(50):
            zg = random_zeitgeist()
            encoded = zg.encode_json()
            decoded = Zeitgeist.decode_json(encoded)
            self.assertEqual(decoded.to_dict(), zg.to_dict())

    def test_alignment_valid(self):
        zg = random_zeitgeist()
        report = zg.check_alignment()
        self.assertTrue(report.aligned, f"Should be aligned: {report.violations}")

    def test_alignment_detects_violation(self):
        zg = random_zeitgeist()
        zg.precision.deadband = -1.0
        zg.confidence.certainty = 2.0
        zg.trajectory.hurst = 1.5
        zg.temporal.beat_pos = -0.5
        report = zg.check_alignment()
        self.assertFalse(report.aligned)
        self.assertGreaterEqual(len(report.violations), 4)

    def test_packet_roundtrip(self):
        zg = random_zeitgeist()
        pkt = FluxPacket(42, 99, b"hello flux", zg)
        encoded = pkt.encode()
        decoded = FluxPacket.decode(encoded)
        self.assertEqual(decoded.source, 42)
        self.assertEqual(decoded.target, 99)
        self.assertEqual(decoded.payload, b"hello flux")
        self.assertEqual(decoded.zeitgeist.to_dict(), zg.to_dict())


if __name__ == "__main__":
    unittest.main()
