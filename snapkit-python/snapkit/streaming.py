"""
streaming.py — Real-Time Stream Processing
===========================================

For production use with live data streams. Supports numpy arrays,
pandas DataFrames (optional), and plain iterables in real-time.

Thread-safe for concurrent stream processing with:
- Sliding window snap with time-decaying tolerance
- Stream monitoring with alerting
- Backpressure when attention budget is exhausted
"""

import numpy as np
from dataclasses import dataclass, field
from typing import (
    List, Optional, Dict, Any, Callable, 
    Generator, Iterator, Union, Tuple
)
from collections import deque
import threading
import time
import logging

from snapkit.snap import SnapFunction, SnapResult, SnapTopologyType
from snapkit.delta import Delta, DeltaDetector, DeltaSeverity

logger = logging.getLogger(__name__)


@dataclass
class StreamConfig:
    """Configuration for a single data stream."""
    stream_id: str
    tolerance: float = 0.1
    topology: SnapTopologyType = SnapTopologyType.HEXAGONAL
    window_size: int = 100           # Sliding window size
    decay_rate: float = 0.01        # Time decay rate for old observations
    alert_threshold: float = 0.8    # Alert when budget utilization exceeds this
    adaptation_rate: float = 0.01
    buffer_size: int = 1000         # Max buffer before backpressure triggers


@dataclass
class StreamAlert:
    """Alert generated when a stream exceeds attention budget."""
    stream_id: str
    alert_type: str              # 'delta_flood', 'budget_exhausted', 'threshold_exceeded'
    severity: str                # 'info', 'warning', 'critical'
    message: str
    timestamp: float
    metric_value: float
    threshold: float
    
    def __repr__(self):
        return (f"Alert({self.stream_id}: {self.alert_type}, "
                f"sev={self.severity}, {self.message})")


class WindowedSnap:
    """
    Sliding window snap with time-decaying tolerance.
    
    Maintains a rolling window of observations and adjusts tolerance
    based on recent delta rate. High delta rates tighten tolerance
    (more attention). Low delta rates loosen tolerance (less attention).
    
    Args:
        config: Stream configuration.
    
    Usage:
        snap = WindowedSnap(StreamConfig(
            stream_id="vitals",
            tolerance=0.1,
            window_size=50,
        ))
        
        for value in vital_signals:
            result = snap.observe(value)
            if result.is_delta:
                print(f"Delta detected in {snap.config.stream_id}")
    """
    
    def __init__(self, config: StreamConfig):
        self.config = config
        self._snap = SnapFunction(
            tolerance=config.tolerance,
            topology=config.topology,
            adaptation_rate=config.adaptation_rate,
        )
        self._window: deque = deque(maxlen=config.window_size)
        self._timestamps: deque = deque(maxlen=config.window_size)
        self._delta_count = 0
        self._total_count = 0
        self._lock = threading.Lock()
    
    def observe(self, value: float) -> SnapResult:
        """
        Observe a value with sliding window and adaptive tolerance.
        
        Thread-safe. Adjusts tolerance based on recent delta rate.
        """
        with self._lock:
            result = self._snap.observe(value)
            now = time.time()
            
            self._window.append(value)
            self._timestamps.append(now)
            self._total_count += 1
            
            if result.is_delta:
                self._delta_count += 1
            
            # Time-decaying tolerance adjustment
            self._adapt_tolerance()
            
            return result
    
    def observe_batch(self, values: List[float]) -> List[SnapResult]:
        """Observe a batch of values."""
        return [self.observe(v) for v in values]
    
    def _adapt_tolerance(self):
        """Adjust tolerance based on recent delta rate and time decay."""
        if len(self._window) < self.config.window_size // 2:
            return
        
        # Compute recent delta rate
        window_deltas = sum(
            1 for i in range(len(self._window))
            if abs(self._window[i] - self._snap.baseline) > self._snap.tolerance
        )
        delta_rate = window_deltas / len(self._window)
        
        # Time decay: older observations have less weight
        if len(self._timestamps) > 1:
            age_weights = np.array([
                np.exp(-self.config.decay_rate * (time.time() - t))
                for t in self._timestamps
            ])
            weighted_deltas = sum(
                age_weights[i] for i in range(len(self._window))
                if abs(self._window[i] - self._snap.baseline) > self._snap.tolerance
            )
            delta_rate = weighted_deltas / max(sum(age_weights), 0.01)
        
        # Adjust: high delta rate → tighten tolerance (more attention)
        #         low delta rate → loosen tolerance (less attention)
        target_tolerance = self.config.tolerance
        
        if delta_rate > 0.3:
            # High delta rate → tighten
            target_tolerance = self.config.tolerance * max(0.5, 1.0 - delta_rate)
        elif delta_rate < 0.05:
            # Very low delta rate → loosen slightly (might be too tight)
            target_tolerance = self.config.tolerance * 1.1
        
        # Smooth adjustment
        self._snap.tolerance += 0.1 * (target_tolerance - self._snap.tolerance)
        self._snap.tolerance = max(self._snap.tolerance, 0.001)
    
    @property
    def statistics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                'stream_id': self.config.stream_id,
                'total_observations': self._total_count,
                'window_size': len(self._window),
                'current_tolerance': self._snap.tolerance,
                'baseline': self._snap.baseline,
                'delta_rate': self._delta_count / max(self._total_count, 1),
                'snap_rate': self._snap.snap_rate,
            }
    
    @property
    def current_tolerance(self) -> float:
        return self._snap.tolerance
    
    def __repr__(self):
        return (f"WindowedSnap({self.config.stream_id}, "
                f"tol={self._snap.tolerance:.4f}, "
                f"win={len(self._window)})")


class StreamProcessor:
    """
    Processes data streams in real-time with snap compression.
    
    Supports processing from:
    - numpy arrays
    - pandas DataFrames (if pandas is installed)
    - Python iterables
    - Generators
    
    Args:
        configs: List of StreamConfig for each stream.
    
    Usage:
        processor = StreamProcessor([
            StreamConfig("temperature", tolerance=0.5),
            StreamConfig("pressure", tolerance=0.1),
        ])
        
        # Process from iterable
        for value in temperature_data:
            result = processor.process("temperature", value)
        
        # Process from numpy array
        results = processor.process_batch("pressure", pressure_data)
        
        # Process from generator
        for value in live_stream():
            result = processor.process("temperature", value)
    """
    
    def __init__(self, configs: Optional[List[StreamConfig]] = None):
        self._streams: Dict[str, WindowedSnap] = {}
        self._detector = DeltaDetector()
        self._alerts: List[StreamAlert] = []
        self._lock = threading.Lock()
        
        if configs:
            for config in configs:
                self.add_stream(config)
    
    def add_stream(self, config: StreamConfig) -> WindowedSnap:
        """Add a new stream to monitor."""
        snap = WindowedSnap(config)
        self._streams[config.stream_id] = snap
        return snap
    
    def process(self, stream_id: str, value: float) -> SnapResult:
        """
        Process a single value from a stream.
        
        Returns the snap result. If the stream doesn't exist,
        creates it with default config.
        """
        if stream_id not in self._streams:
            self.add_stream(StreamConfig(stream_id=stream_id))
        
        result = self._streams[stream_id].observe(value)
        
        # Check for alert conditions
        self._check_alert(result)
        
        return result
    
    def process_batch(
        self, stream_id: str, values: Union[List[float], np.ndarray]
    ) -> List[SnapResult]:
        """Process a batch of values from a stream."""
        if isinstance(values, np.ndarray):
            values = values.tolist()
        return [self.process(stream_id, v) for v in values]
    
    def process_dataframe(
        self,
        dataframe: Any,
        column_mapping: Optional[Dict[str, str]] = None,
    ) -> Dict[str, List[SnapResult]]:
        """
        Process a pandas DataFrame.
        
        Args:
            dataframe: pandas DataFrame instance.
            column_mapping: Dict mapping column names to stream_ids.
                If None, column names are used as stream_ids.
        
        Returns:
            Dict mapping stream_id to list of SnapResults.
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "pandas is required for DataFrame processing. "
                "Install it with: pip install pandas"
            )
        
        if not isinstance(dataframe, pd.DataFrame):
            raise TypeError(f"Expected pandas DataFrame, got {type(dataframe)}")
        
        mapping = column_mapping or {col: col for col in dataframe.columns}
        results: Dict[str, List[SnapResult]] = {}
        
        for col, stream_id in mapping.items():
            if col not in dataframe.columns:
                logger.warning(f"Column '{col}' not found in DataFrame")
                continue
            
            values = dataframe[col].dropna()
            results[stream_id] = self.process_batch(stream_id, values.tolist())
        
        return results
    
    def process_generator(
        self,
        generator: Generator[Tuple[str, float], None, None],
    ) -> Generator[Tuple[str, SnapResult], None, None]:
        """
        Process values from a generator yielding (stream_id, value) tuples.
        
        Supports processing live data streams indefinitely.
        """
        for stream_id, value in generator:
            yield stream_id, self.process(stream_id, value)
    
    def _check_alert(self, result: SnapResult):
        """Check if an alert should be raised."""
        if result.is_delta:
            recent = self._alerts[-10:] if self._alerts else []
            recent_count = sum(
                1 for a in recent 
                if a.alert_type == 'delta_flood'
            )
            
            if recent_count >= 8:
                # Delta flood
                self._alerts.append(StreamAlert(
                    stream_id='',
                    alert_type='delta_flood',
                    severity='critical',
                    message='Multiple streams experiencing delta floods',
                    timestamp=time.time(),
                    metric_value=result.delta,
                    threshold=result.tolerance,
                ))
    
    def get_alerts(self, clear: bool = False) -> List[StreamAlert]:
        """Get pending alerts."""
        alerts = list(self._alerts)
        if clear:
            self._alerts.clear()
        return alerts
    
    @property
    def stream_ids(self) -> List[str]:
        return list(self._streams.keys())
    
    @property
    def statistics(self) -> Dict[str, Any]:
        return {
            'num_streams': len(self._streams),
            'pending_alerts': len(self._alerts),
            'per_stream': {
                sid: snap.statistics for sid, snap in self._streams.items()
            },
        }
    
    def __repr__(self):
        return f"StreamProcessor(streams={len(self._streams)}, alerts={len(self._alerts)})"


class StreamMonitor:
    """
    Monitors multiple streams and produces alerts when deltas exceed budget.
    
    Maintains an attention budget across all streams. When aggregate delta
    rate exceeds budget, raises alerts. Useful for system monitoring where
    you need to know when the deltas are overwhelming capacity.
    
    Args:
        total_budget: Maximum attention across all streams.
        check_interval: How often to check budget (in observations).
    
    Usage:
        monitor = StreamMonitor(total_budget=100.0)
        
        monitor.add_stream("cpu", SnapFunction(tolerance=5.0))
        monitor.add_stream("memory", SnapFunction(tolerance=10.0))
        monitor.add_stream("latency", SnapFunction(tolerance=50.0))
        
        for value in cpu_usage:
            monitor.observe("cpu", value)
            alerts = monitor.check_alerts()
            for alert in alerts:
                print(f"ALERT: {alert.message}")
    """
    
    def __init__(
        self,
        total_budget: float = 100.0,
        check_interval: int = 10,
    ):
        self.total_budget = total_budget
        self.check_interval = check_interval
        self._streams: Dict[str, Dict[str, Any]] = {}
        self._observation_count = 0
        self._budget_used = 0.0
        self._alerts: List[StreamAlert] = []
        self._lock = threading.Lock()
    
    def add_stream(
        self,
        stream_id: str,
        snap: Optional[SnapFunction] = None,
        weight: float = 1.0,
    ):
        """Add a stream to monitor."""
        self._streams[stream_id] = {
            'snap': snap or SnapFunction(tolerance=0.1),
            'weight': weight,
            'delta_count': 0,
            'obs_count': 0,
            'budget_consumed': 0.0,
        }
    
    def observe(self, stream_id: str, value: float) -> SnapResult:
        """
        Observe a value on a stream and track budget consumption.
        """
        if stream_id not in self._streams:
            raise KeyError(f"Unknown stream: {stream_id}")
        
        stream = self._streams[stream_id]
        result = stream['snap'].observe(value)
        
        stream['obs_count'] += 1
        if result.is_delta:
            stream['delta_count'] += 1
            # Budget consumption = delta magnitude * stream weight
            consumption = result.delta * stream['weight']
            stream['budget_consumed'] += consumption
            self._budget_used += consumption
        
        self._observation_count += 1
        
        # Periodic check
        if self._observation_count % self.check_interval == 0:
            self._check_budget()
        
        return result
    
    def _check_budget(self):
        """Check if any streams are exceeding budget."""
        with self._lock:
            for stream_id, stream in self._streams.items():
                if stream['obs_count'] < self.check_interval:
                    continue
                
                avg_consumption = stream['budget_consumed'] / max(stream['obs_count'], 1)
                expected_share = self.total_budget * stream['weight']
                
                if avg_consumption > expected_share:
                    self._alerts.append(StreamAlert(
                        stream_id=stream_id,
                        alert_type='budget_exhausted',
                        severity='warning',
                        message=f'Stream {stream_id} exceeding budget share',
                        timestamp=time.time(),
                        metric_value=avg_consumption,
                        threshold=expected_share,
                    ))
    
    def check_alerts(self, clear: bool = True) -> List[StreamAlert]:
        """Get and optionally clear alerts."""
        alerts = list(self._alerts)
        if clear:
            self._alerts.clear()
        return alerts
    
    def reset(self):
        """Reset all stream statistics."""
        self._observation_count = 0
        self._budget_used = 0.0
        for stream in self._streams.values():
            stream['delta_count'] = 0
            stream['obs_count'] = 0
            stream['budget_consumed'] = 0.0
    
    @property
    def utilization(self) -> float:
        """Fraction of budget used across all streams."""
        return min(1.0, self._budget_used / max(self.total_budget, 0.01))
    
    @property
    def statistics(self) -> Dict[str, Any]:
        return {
            'total_budget': self.total_budget,
            'budget_used': self._budget_used,
            'utilization': self.utilization,
            'num_streams': len(self._streams),
            'total_observations': self._observation_count,
            'pending_alerts': len(self._alerts),
            'per_stream': {
                sid: {
                    'obs_count': s['obs_count'],
                    'delta_count': s['delta_count'],
                    'weight': s['weight'],
                    'budget_consumed': s['budget_consumed'],
                }
                for sid, s in self._streams.items()
            },
        }
    
    def __repr__(self):
        return (f"StreamMonitor(streams={len(self._streams)}, "
                f"util={self.utilization:.1%}, "
                f"alerts={len(self._alerts)})")


class Backpressure:
    """
    Intelligent delta dropping when attention budget is exhausted.
    
    When the attention budget is exceeded, not all deltas are equally
    important. Backpressure drops low-priority deltas first, ensuring
    that critical signals always get through.
    
    Priority pyramid:
    1. CRITICAL: Safety/security deltas (never dropped)
    2. HIGH: Urgent, actionable deltas (rarely dropped)
    3. MEDIUM: Notable but not urgent (dropped under pressure)
    4. LOW: Interesting but low-actionability (dropped first)
    5. TRIVIAL: Noise (always dropped when budget pressured)
    
    Args:
        max_buffer: Maximum number of pending deltas.
        drop_strategy: How to choose which deltas to drop.
    
    Usage:
        backpressure = Backpressure(max_buffer=100)
        for delta in incoming_deltas:
            if backpressure.can_process(delta):
                process(delta)
            else:
                backpressure.drop(delta, reason="budget exhausted")
    """
    
    def __init__(
        self,
        max_buffer: int = 100,
        drop_strategy: str = 'lowest_priority',
    ):
        self.max_buffer = max_buffer
        self.drop_strategy = drop_strategy
        self._buffer: List[Delta] = []
        self._dropped: List[Dict[str, Any]] = []
        self._processed: List[Delta] = []
        self._critical_seen = 0
        self._lock = threading.Lock()
    
    def can_process(self, delta: Delta) -> bool:
        """
        Check if a delta can be processed.
        
        CRITICAL deltas always get through. Others depend on buffer state.
        """
        with self._lock:
            if delta.severity == DeltaSeverity.CRITICAL:
                self._critical_seen += 1
                return True
            
            if len(self._buffer) >= self.max_buffer:
                return False
            
            self._buffer.append(delta)
            return True
    
    def process(self, delta: Delta) -> bool:
        """
        Process a delta, dropping a lower-priority one if buffer is full.
        
        Returns True if delta was processed, False if it was dropped.
        """
        if self.can_process(delta):
            self._processed.append(delta)
            return True
        else:
            self.drop(delta, reason="buffer_full")
            return False
    
    def drop(self, delta: Delta, reason: str = "backpressure"):
        """Record a dropped delta."""
        self._dropped.append({
            'delta': delta,
            'reason': reason,
            'timestamp': time.time(),
        })
    
    def clear_buffer(self):
        """Clear the pending buffer (drop all non-critical)."""
        with self._lock:
            # Keep only critical deltas
            self._buffer = [
                d for d in self._buffer 
                if d.severity == DeltaSeverity.CRITICAL
            ]
    
    @property
    def drop_rate(self) -> float:
        """Fraction of deltas that have been dropped."""
        total = len(self._dropped) + len(self._processed)
        return len(self._dropped) / max(total, 1)
    
    @property
    def buffer_utilization(self) -> float:
        """How full the buffer is."""
        return len(self._buffer) / max(self.max_buffer, 1)
    
    @property
    def statistics(self) -> Dict[str, Any]:
        return {
            'buffer_size': len(self._buffer),
            'max_buffer': self.max_buffer,
            'buffer_utilization': self.buffer_utilization,
            'processed': len(self._processed),
            'dropped': len(self._dropped),
            'drop_rate': self.drop_rate,
            'critical_deltas': self._critical_seen,
        }
    
    def __repr__(self):
        return (f"Backpressure(buffer={len(self._buffer)}/{self.max_buffer}, "
                f"drop_rate={self.drop_rate:.1%})")
