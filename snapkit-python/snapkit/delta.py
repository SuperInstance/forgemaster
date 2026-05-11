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
    
    def delta_forecast(self, horizon: int = 5) -> List[float]:
        """
        Forecast upcoming delta magnitudes using linear extrapolation.
        
        Uses recent delta trends to predict near-future deltas.
        
        Args:
            horizon: Number of steps to forecast.
        
        Returns:
            List of predicted delta magnitudes.
        """
        if len(self._deltas) < 3:
            return [0.0] * horizon
        
        relevant = [d.magnitude for d in self._deltas if d.exceeds_tolerance]
        if len(relevant) < 3:
            return [float(np.mean(relevant))] * horizon if relevant else [0.0] * horizon
        
        x = np.arange(len(relevant))
        y = np.array(relevant)
        try:
            coeffs = np.polyfit(x, y, 1)
            last_x = len(relevant)
            return [float(coeffs[0] * (last_x + i) + coeffs[1]) for i in range(horizon)]
        except np.linalg.LinAlgError:
            return [float(np.mean(relevant))] * horizon
    
    def delta_correlation(self, other_stream: 'DeltaStream') -> float:
        """
        Compute correlation between this stream's deltas and another's.
        
        High correlation means the streams' deltas move together —
        useful for finding dependent/independent information sources.
        
        Args:
            other_stream: Another DeltaStream to compare with.
        
        Returns:
            Pearson correlation coefficient [-1, 1].
        """
        if not self._deltas or not other_stream._deltas:
            return 0.0
        
        # Align by length
        n = min(len(self._deltas), len(other_stream._deltas))
        if n < 3:
            return 0.0
        
        a = np.array([d.magnitude for d in self._deltas[-n:]])
        b = np.array([d.magnitude for d in other_stream._deltas[-n:]])
        
        if np.std(a) < 0.001 or np.std(b) < 0.001:
            return 0.0
        
        corr = np.corrcoef(a, b)[0, 1]
        return float(corr) if not np.isnan(corr) else 0.0
    
    @property
    def statistics(self) -> Dict[str, Any]:
        if not self._deltas:
            return {'stream_id': self.stream_id, 'total': 0}
        
        nontrivial = self.nontrivial_deltas
        nontrivial_mags = [d.magnitude for d in nontrivial] if nontrivial else [0.0]
        return {
            'stream_id': self.stream_id,
            'total_observations': len(self._deltas),
            'nontrivial_deltas': len(nontrivial),
            'delta_rate': len(nontrivial) / len(self._deltas),
            'mean_magnitude': float(np.mean(nontrivial_mags)),
            'max_magnitude': float(np.max(nontrivial_mags)),
            'mean_actionability': float(np.mean([d.actionability for d in nontrivial])) if nontrivial else 0.0,
            'mean_urgency': float(np.mean([d.urgency for d in nontrivial])) if nontrivial else 0.0,
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
    
    # ─── Delta Clustering ────────────────────────────────────────────
    
    def delta_clusters(self, n_clusters: int = 3) -> Dict[str, List[Delta]]:
        """
        Cluster deltas by magnitude and stream into groups.
        
        Uses simple k-means-like quantization (no external dependencies).
        Useful for finding which streams are producing similar deltas.
        
        Args:
            n_clusters: Number of clusters.
        
        Returns:
            Dict mapping cluster_id to list of Deltas.
        """
        all_deltas = []
        for stream in self._streams.values():
            for d in stream._deltas:
                if d.exceeds_tolerance:
                    all_deltas.append(d)
        
        if not all_deltas:
            return {}
        
        if len(all_deltas) < n_clusters:
            n_clusters = max(1, len(all_deltas))
        
        # Simple k-means by magnitude
        magnitudes = np.array([d.magnitude for d in all_deltas]).reshape(-1, 1)
        
        # Initialize centroids across range
        if len(magnitudes) == 0:
            return {}
        vmin, vmax = float(np.min(magnitudes)), float(np.max(magnitudes))
        if vmax - vmin < 0.001:
            return {'0': all_deltas}
        
        centroids = np.linspace(vmin, vmax, n_clusters).reshape(-1, 1)
        
        # K-means iterations
        for _ in range(10):
            # Assign
            distances = np.abs(magnitudes - centroids.T)  # (n, k)
            labels = np.argmin(distances, axis=1)
            
            # Update centroids
            new_centroids = np.array([
                magnitudes[labels == k].mean() if np.any(labels == k) else centroids[k]
                for k in range(n_clusters)
            ]).reshape(-1, 1)
            
            if np.allclose(centroids, new_centroids, atol=1e-4):
                break
            centroids = new_centroids
        
        clusters: Dict[str, List[Delta]] = {}
        for i, d in enumerate(all_deltas):
            cid = str(int(labels[i]))
            if cid not in clusters:
                clusters[cid] = []
            clusters[cid].append(d)
        
        return clusters
    
    def importance_scores(self) -> Dict[str, float]:
        """
        Score deltas by combined importance (actionability × urgency × magnitude).
        
        Returns:
            Dict mapping stream_id to importance score.
        """
        scores = {}
        for sid, stream in self._streams.items():
            recent = stream._deltas[-10:] if stream._deltas else []
            nontrivial = [d for d in recent if d.exceeds_tolerance]
            if nontrivial:
                scores[sid] = float(np.mean([d.attention_weight for d in nontrivial]))
            else:
                scores[sid] = 0.0
        return scores
    
    def __repr__(self):
        return f"DeltaDetector(streams={len(self._streams)})"
