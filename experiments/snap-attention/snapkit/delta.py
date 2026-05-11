"""
delta.py — DeltaDetector: Tracking What Exceeds Tolerance
==========================================================

The delta detector monitors information streams and flags observations
that exceed snap tolerance. The felt delta IS the primary information
signal — not the calculated probability, but the qualitative shift
from "expected" to "unexpected."

"The delta is the compass needle. It points attention toward the part
of the information landscape where thinking can make the most difference."
— SNAP-ATTENTION-INTELLIGENCE.md
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Callable, Dict, Any
from enum import Enum
from collections import deque

from snapkit.snap import SnapFunction, SnapResult, SnapTopologyType


class DeltaSeverity(Enum):
    """How significant a delta is."""
    NONE = "none"          # Within tolerance — no delta
    LOW = "low"            # Just outside tolerance
    MEDIUM = "medium"      # Clearly exceeds tolerance
    HIGH = "high"          # Far from expected
    CRITICAL = "critical"  # Extremely far — possible system failure


@dataclass
class Delta:
    """
    A felt delta — information that exceeded snap tolerance.
    
    The delta is not a number. It's a felt quality — "something changed" —
    that can be patterned (trained, refined, made more precise through experience).
    """
    value: float
    expected: float
    magnitude: float
    tolerance: float
    severity: DeltaSeverity
    timestamp: int
    stream_id: str = ""
    actionability: float = 1.0  # Can thinking change this? [0..1]
    urgency: float = 1.0        # Does this need attention NOW? [0..1]
    
    @property
    def exceeds_tolerance(self) -> bool:
        return self.magnitude > self.tolerance
    
    @property
    def attention_weight(self) -> float:
        """
        How much attention this delta deserves.
        Weighted by magnitude, actionability, and urgency.
        """
        return self.magnitude * self.actionability * self.urgency
    
    def __repr__(self):
        return (f"Δ({self.value:.3f} vs {self.expected:.3f}, "
                f"mag={self.magnitude:.3f}, {self.severity.value})")


class DeltaStream:
    """
    A stream of deltas from a single information source.
    
    Each stream has its own snap function, tolerance, and topology.
    Multiple streams model the multi-layer architecture of expert cognition
    (e.g., poker: cards, behavior, betting, emotion, dynamics).
    """
    
    def __init__(
        self,
        stream_id: str,
        snap: SnapFunction,
        actionability_fn: Optional[Callable[[float], float]] = None,
        urgency_fn: Optional[Callable[[float], float]] = None,
    ):
        self.stream_id = stream_id
        self.snap = snap
        self.actionability_fn = actionability_fn or (lambda _: 1.0)
        self.urgency_fn = urgency_fn or (lambda _: 1.0)
        self._deltas: List[Delta] = []
        self._tick = 0
    
    def observe(self, value: float) -> Delta:
        """Observe a value and produce a delta (or no-delta)."""
        self._tick += 1
        result = self.snap.snap(value)
        
        # Determine severity
        ratio = result.delta / result.tolerance if result.tolerance > 0 else 0
        if ratio <= 1.0:
            severity = DeltaSeverity.NONE
        elif ratio <= 1.5:
            severity = DeltaSeverity.LOW
        elif ratio <= 3.0:
            severity = DeltaSeverity.MEDIUM
        elif ratio <= 5.0:
            severity = DeltaSeverity.HIGH
        else:
            severity = DeltaSeverity.CRITICAL
        
        delta = Delta(
            value=value,
            expected=self.snap.baseline,
            magnitude=result.delta,
            tolerance=result.tolerance,
            severity=severity,
            timestamp=self._tick,
            stream_id=self.stream_id,
            actionability=self.actionability_fn(value),
            urgency=self.urgency_fn(value),
        )
        
        self._deltas.append(delta)
        return delta
    
    @property
    def recent_deltas(self, n: int = 10) -> List[Delta]:
        """Get the n most recent deltas."""
        return self._deltas[-n:]
    
    @property
    def nontrivial_deltas(self) -> List[Delta]:
        """Get only deltas that exceed tolerance."""
        return [d for d in self._deltas if d.exceeds_tolerance]
    
    @property
    def statistics(self) -> Dict[str, Any]:
        if not self._deltas:
            return {'stream_id': self.stream_id, 'total': 0}
        
        magnitudes = [d.magnitude for d in self._deltas]
        nontrivial = self.nontrivial_deltas
        return {
            'stream_id': self.stream_id,
            'total_observations': len(self._deltas),
            'nontrivial_deltas': len(nontrivial),
            'delta_rate': len(nontrivial) / len(self._deltas),
            'mean_magnitude': float(np.mean(magnitudes)),
            'max_magnitude': float(np.max(magnitudes)),
            'tolerance': self.snap.tolerance,
            'baseline': self.snap.baseline,
        }


class DeltaDetector:
    """
    Multi-stream delta detector — the core of the attention allocation engine.
    
    Monitors multiple information streams simultaneously, each with its own
    snap function and tolerance. Deltas are ranked by attention weight
    (magnitude × actionability × urgency) to determine which deserve
    cognitive resources.
    
    The poker player uses 5 delta streams simultaneously:
    cards, behavior, betting, emotion, dynamics.
    
    Usage:
        detector = DeltaDetector()
        detector.add_stream('cards', SnapFunction(tolerance=0.2, topology='uniform'))
        detector.add_stream('behavior', SnapFunction(tolerance=0.05, topology='categorical'))
        
        for card_value, behavior_value in data_stream:
            detector.observe({'cards': card_value, 'behavior': behavior_value})
            attention = detector.prioritize()
            print(f"Attend to: {attention}")
    """
    
    def __init__(self):
        self._streams: Dict[str, DeltaStream] = {}
        self._tick = 0
    
    def add_stream(
        self,
        stream_id: str,
        snap: SnapFunction,
        actionability_fn: Optional[Callable[[float], float]] = None,
        urgency_fn: Optional[Callable[[float], float]] = None,
    ) -> DeltaStream:
        """Add an information stream to monitor."""
        stream = DeltaStream(stream_id, snap, actionability_fn, urgency_fn)
        self._streams[stream_id] = stream
        return stream
    
    def observe(self, values: Dict[str, float]) -> Dict[str, Delta]:
        """
        Observe values across all streams.
        
        Args:
            values: Dict mapping stream_id to observed value.
        
        Returns:
            Dict mapping stream_id to resulting Delta.
        """
        self._tick += 1
        results = {}
        for stream_id, value in values.items():
            if stream_id in self._streams:
                results[stream_id] = self._streams[stream_id].observe(value)
        return results
    
    def prioritize(self, top_k: int = 3) -> List[Delta]:
        """
        Prioritize deltas by attention weight.
        
        Returns the top_k deltas sorted by attention_weight
        (magnitude × actionability × urgency), descending.
        
        These are the deltas that DESERVE cognitive resources.
        """
        all_deltas = []
        for stream in self._streams.values():
            for delta in stream._deltas:
                if delta.exceeds_tolerance:
                    all_deltas.append(delta)
        
        # Sort by attention weight, descending
        all_deltas.sort(key=lambda d: d.attention_weight, reverse=True)
        return all_deltas[:top_k]
    
    def current_deltas(self) -> Dict[str, Delta]:
        """Get the most recent delta from each stream."""
        result = {}
        for sid, stream in self._streams.items():
            if stream._deltas:
                result[sid] = stream._deltas[-1]
        return result
    
    @property
    def statistics(self) -> Dict[str, Any]:
        stream_stats = {sid: stream.statistics for sid, stream in self._streams.items()}
        total_obs = sum(s['total_observations'] for s in stream_stats.values())
        total_deltas = sum(s['nontrivial_deltas'] for s in stream_stats.values())
        return {
            'num_streams': len(self._streams),
            'total_observations': total_obs,
            'total_deltas': total_deltas,
            'overall_delta_rate': total_deltas / total_obs if total_obs > 0 else 0,
            'per_stream': stream_stats,
        }
    
    def __repr__(self):
        return f"DeltaDetector(streams={len(self._streams)})"
