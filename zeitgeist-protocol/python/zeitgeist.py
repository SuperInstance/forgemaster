"""
Zeitgeist Protocol — Pure Python implementation

CRDT semilattice capturing five dimensions of agent alignment.
Merge is commutative, associative, and idempotent.
"""

from __future__ import annotations
import struct
import json
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# ── Enums ──────────────────────────────────────────────────

class Trend:
    STABLE = 0
    RISING = 1
    FALLING = 2
    CHAOTIC = 3

class Phase:
    IDLE = 0
    APPROACHING = 1
    SNAP = 2
    HOLD = 3

# ── Sub-states ─────────────────────────────────────────────

@dataclass
class PrecisionState:
    deadband: float = 500000.0
    funnel_pos: float = 0.0
    snap_imminent: bool = False

    COVERING_RADIUS = 1e6

    def check_alignment(self) -> List[str]:
        v = []
        if self.deadband <= 0:
            v.append("precision.deadband must be > 0")
        if self.deadband >= self.COVERING_RADIUS:
            v.append("precision.deadband must be < covering_radius")
        return v

    def merge(self, other: PrecisionState) -> PrecisionState:
        return PrecisionState(
            deadband=min(self.deadband, other.deadband),
            funnel_pos=max(self.funnel_pos, other.funnel_pos),
            snap_imminent=self.snap_imminent or other.snap_imminent,
        )


@dataclass
class ConfidenceState:
    bloom: bytes = field(default_factory=lambda: b'\x00' * 32)
    parity: int = 0
    certainty: float = 0.0

    def check_alignment(self) -> List[str]:
        v = []
        if not (0.0 <= self.certainty <= 1.0):
            v.append("confidence.certainty must be 0-1")
        return v

    def merge(self, other: ConfidenceState) -> ConfidenceState:
        bloom = bytes(a | b for a, b in zip(self.bloom, other.bloom))
        return ConfidenceState(
            bloom=bloom,
            parity=self.parity | other.parity,
            certainty=max(self.certainty, other.certainty),
        )


@dataclass
class TrajectoryState:
    hurst: float = 0.5
    trend: int = Trend.STABLE
    velocity: float = 0.0

    def check_alignment(self) -> List[str]:
        v = []
        if not (0.0 <= self.hurst <= 1.0):
            v.append("trajectory.hurst must be 0-1")
        return v

    def merge(self, other: TrajectoryState) -> TrajectoryState:
        trend = self.trend if self.trend == other.trend else Trend.CHAOTIC
        return TrajectoryState(
            hurst=min(self.hurst, other.hurst),
            trend=trend,
            velocity=max(self.velocity, other.velocity),
        )


@dataclass
class ConsensusState:
    holonomy: float = 0.0
    peer_agreement: float = 1.0
    crdt_version: Dict[int, int] = field(default_factory=dict)

    def check_alignment(self) -> List[str]:
        v = []
        if not (0.0 <= self.peer_agreement <= 1.0):
            v.append("consensus.peer_agreement must be 0-1")
        return v

    def merge(self, other: ConsensusState) -> ConsensusState:
        v = dict(self.crdt_version)
        for k, val in other.crdt_version.items():
            v[k] = max(v.get(k, 0), val)
        return ConsensusState(
            holonomy=min(self.holonomy, other.holonomy),
            peer_agreement=max(self.peer_agreement, other.peer_agreement),
            crdt_version=v,
        )


@dataclass
class TemporalState:
    beat_pos: float = 0.0
    phase: int = Phase.IDLE
    rhythm_coherence: float = 1.0

    def check_alignment(self) -> List[str]:
        v = []
        if not (0.0 <= self.beat_pos <= 1.0):
            v.append("temporal.beat_pos must be 0-1")
        if not (0.0 <= self.rhythm_coherence <= 1.0):
            v.append("temporal.rhythm_coherence must be 0-1")
        return v

    def merge(self, other: TemporalState) -> TemporalState:
        return TemporalState(
            beat_pos=max(self.beat_pos, other.beat_pos),
            phase=max(self.phase, other.phase),
            rhythm_coherence=max(self.rhythm_coherence, other.rhythm_coherence),
        )


# ── Zeitgeist ──────────────────────────────────────────────

@dataclass
class AlignmentReport:
    aligned: bool
    violations: List[str]


@dataclass
class Zeitgeist:
    precision: PrecisionState = field(default_factory=PrecisionState)
    confidence: ConfidenceState = field(default_factory=ConfidenceState)
    trajectory: TrajectoryState = field(default_factory=TrajectoryState)
    consensus: ConsensusState = field(default_factory=ConsensusState)
    temporal: TemporalState = field(default_factory=TemporalState)

    def merge(self, other: Zeitgeist) -> Zeitgeist:
        return Zeitgeist(
            precision=self.precision.merge(other.precision),
            confidence=self.confidence.merge(other.confidence),
            trajectory=self.trajectory.merge(other.trajectory),
            consensus=self.consensus.merge(other.consensus),
            temporal=self.temporal.merge(other.temporal),
        )

    def check_alignment(self) -> AlignmentReport:
        violations = []
        violations.extend(self.precision.check_alignment())
        violations.extend(self.confidence.check_alignment())
        violations.extend(self.trajectory.check_alignment())
        violations.extend(self.consensus.check_alignment())
        violations.extend(self.temporal.check_alignment())
        return AlignmentReport(aligned=len(violations) == 0, violations=violations)

    def to_dict(self) -> dict:
        return {
            "precision": {
                "deadband": self.precision.deadband,
                "funnel_pos": self.precision.funnel_pos,
                "snap_imminent": self.precision.snap_imminent,
            },
            "confidence": {
                "bloom": self.confidence.bloom.hex(),
                "parity": self.confidence.parity,
                "certainty": self.confidence.certainty,
            },
            "trajectory": {
                "hurst": self.trajectory.hurst,
                "trend": self.trajectory.trend,
                "velocity": self.trajectory.velocity,
            },
            "consensus": {
                "holonomy": self.consensus.holonomy,
                "peer_agreement": self.consensus.peer_agreement,
                "crdt_version": self.consensus.crdt_version,
            },
            "temporal": {
                "beat_pos": self.temporal.beat_pos,
                "phase": self.temporal.phase,
                "rhythm_coherence": self.temporal.rhythm_coherence,
            },
        }

    @classmethod
    def from_dict(cls, d: dict) -> Zeitgeist:
        return cls(
            precision=PrecisionState(**d["precision"]),
            confidence=ConfidenceState(
                bloom=bytes.fromhex(d["confidence"]["bloom"]),
                parity=d["confidence"]["parity"],
                certainty=d["confidence"]["certainty"],
            ),
            trajectory=TrajectoryState(**d["trajectory"]),
            consensus=ConsensusState(
                holonomy=d["consensus"]["holonomy"],
                peer_agreement=d["consensus"]["peer_agreement"],
                crdt_version={int(k): v for k, v in d["consensus"]["crdt_version"].items()},
            ),
            temporal=TemporalState(**d["temporal"]),
        )

    def encode_json(self) -> bytes:
        return json.dumps(self.to_dict()).encode()

    @classmethod
    def decode_json(cls, data: bytes) -> Zeitgeist:
        return cls.from_dict(json.loads(data))


# ── FLUX Packet ────────────────────────────────────────────

FLUX_MAGIC = b'FLUX'

class FluxPacket:
    def __init__(self, source: int, target: int, payload: bytes,
                 zeitgeist: Zeitgeist, version: int = 1, flags: int = 0,
                 timestamp: float = 0.0):
        self.magic = FLUX_MAGIC
        self.version = version
        self.flags = flags
        self.source = source
        self.target = target
        self.timestamp = timestamp or __import__('time').time()
        self.payload = payload
        self.zeitgeist = zeitgeist
        self.parity = 0

    def encode(self) -> bytes:
        zg_bytes = self.zeitgeist.encode_json()
        header = b''.join([
            self.magic,
            struct.pack('>H', self.version),
            struct.pack('B', self.flags),
            struct.pack('>I', self.source),
            struct.pack('>I', self.target),
            struct.pack('>d', self.timestamp),
            struct.pack('>I', len(self.payload)),
            struct.pack('>I', len(zg_bytes)),
        ])
        # Compute parity
        p = 0
        for b in header:
            p ^= b
        for b in self.payload:
            p ^= b
        for b in zg_bytes:
            p ^= b
        return header + self.payload + zg_bytes + struct.pack('B', p)

    @classmethod
    def decode(cls, data: bytes) -> FluxPacket:
        if len(data) < 31:
            raise ValueError("Packet too short")
        magic = data[0:4]
        if magic != FLUX_MAGIC:
            raise ValueError(f"Invalid magic: {magic!r}")
        version = struct.unpack('>H', data[4:6])[0]
        flags = data[6]
        source = struct.unpack('>I', data[7:11])[0]
        target = struct.unpack('>I', data[11:15])[0]
        timestamp = struct.unpack('>d', data[15:23])[0]
        payload_len = struct.unpack('>I', data[23:27])[0]
        zg_len = struct.unpack('>I', data[27:31])[0]
        expected = 31 + payload_len + zg_len + 1
        if len(data) < expected:
            raise ValueError(f"Truncated: need {expected}, got {len(data)}")
        payload = data[31:31 + payload_len]
        zg_data = data[31 + payload_len:31 + payload_len + zg_len]
        parity = data[31 + payload_len + zg_len]
        # Verify
        p = 0
        for b in data[:31]:
            p ^= b
        for b in payload:
            p ^= b
        for b in zg_data:
            p ^= b
        if p != parity:
            raise ValueError(f"Parity mismatch: computed {p:#x}, got {parity:#x}")
        zg = Zeitgeist.decode_json(zg_data)
        pkt = cls(source, target, payload, zg, version, flags, timestamp)
        pkt.parity = parity
        return pkt
