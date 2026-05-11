"""
pipeline.py — Composable Pipelines
====================================

Chain snap → detect → prioritize → allocate → execute in
composable processing pipelines with a fluent builder API.

"The snap is the handoff. The script is the offload.
The freed mind is the intelligence."
— SNAPS-AS-ATTENTION.md
"""

import numpy as np
from dataclasses import dataclass, field
from typing import (
    List, Optional, Dict, Any, Callable,
    TypeVar, Generic, Union
)
from collections import deque
import time
import logging

from snapkit.snap import SnapFunction, SnapResult, SnapTopologyType
from snapkit.delta import DeltaDetector, Delta
from snapkit.attention import AttentionBudget, AttentionAllocation
from snapkit.scripts import ScriptLibrary, Script
from snapkit.learning import LearningCycle, LearningPhase

logger = logging.getLogger(__name__)

# Type variable for pipeline stage outputs
T = TypeVar('T')
U = TypeVar('U')


@dataclass
class PipelineContext:
    """
    Context shared across pipeline stages.
    
    Carries data and state through the pipeline, allowing
    each stage to access results from previous stages.
    """
    input_value: float = 0.0
    snap_result: Optional[SnapResult] = None
    deltas: List[Delta] = field(default_factory=list)
    allocations: List[AttentionAllocation] = field(default_factory=list)
    matched_scripts: List[Any] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    
    def add_metadata(self, key: str, value: Any):
        """Add metadata to the pipeline context."""
        self.metadata[key] = value


class PipelineNode:
    """
    Base class for custom pipeline stages.
    
    Extend this to create custom processing stages for
    a SnapPipeline. Override process() to implement
    custom logic.
    
    Usage:
        class CustomNode(PipelineNode):
            def process(self, ctx: PipelineContext) -> PipelineContext:
                ctx.metadata['custom'] = compute(ctx.input_value)
                return ctx
    """
    
    def __init__(self, name: str = ""):
        self.name = name or self.__class__.__name__
    
    def process(self, ctx: PipelineContext) -> PipelineContext:
        """
        Process a pipeline context.
        
        Override this method in subclasses.
        
        Args:
            ctx: Pipeline context from previous stage.
        
        Returns:
            Modified pipeline context.
        """
        return ctx
    
    def __repr__(self):
        return f"PipelineNode({self.name})"


class SnapNode(PipelineNode):
    """Pipeline stage: snap a value to a lattice point."""
    
    def __init__(
        self,
        snap_function: Optional[SnapFunction] = None,
        tolerance: float = 0.1,
        topology: SnapTopologyType = SnapTopologyType.HEXAGONAL,
        name: str = "SnapNode",
    ):
        super().__init__(name)
        self.snap = snap_function or SnapFunction(
            tolerance=tolerance, topology=topology
        )
    
    def process(self, ctx: PipelineContext) -> PipelineContext:
        result = self.snap.observe(ctx.input_value)
        ctx.snap_result = result
        ctx.add_metadata('tolerance', self.snap.tolerance)
        ctx.add_metadata('baseline', self.snap.baseline)
        return ctx


class DetectNode(PipelineNode):
    """Pipeline stage: detect deltas from multiple streams."""
    
    def __init__(
        self,
        detector: Optional[DeltaDetector] = None,
        name: str = "DetectNode",
    ):
        super().__init__(name)
        self.detector = detector or DeltaDetector()
    
    def process(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.snap_result and ctx.snap_result.is_delta:
            from snapkit.delta import Delta, DeltaSeverity
            delta = Delta(
                value=ctx.input_value,
                expected=ctx.snap_result.baseline if ctx.snap_result else 0,
                magnitude=ctx.snap_result.delta if ctx.snap_result else 0,
                tolerance=ctx.snap_result.tolerance if ctx.snap_result else 0.1,
                severity=(
                    DeltaSeverity.HIGH if ctx.snap_result.delta > 3 * ctx.snap_result.tolerance
                    else DeltaSeverity.MEDIUM
                ) if ctx.snap_result else DeltaSeverity.NONE,
                timestamp=int(time.time()),
                stream_id='default',
            )
            ctx.deltas = [delta]
        return ctx


class PrioritizeNode(PipelineNode):
    """Pipeline stage: prioritize deltas by attention weight."""
    
    def __init__(
        self,
        top_k: int = 3,
        name: str = "PrioritizeNode",
    ):
        super().__init__(name)
        self.top_k = top_k
    
    def process(self, ctx: PipelineContext) -> PipelineContext:
        # Sort deltas by attention weight
        sorted_deltas = sorted(
            ctx.deltas,
            key=lambda d: d.attention_weight,
            reverse=True,
        )
        ctx.deltas = sorted_deltas[:self.top_k]
        ctx.add_metadata('deltas_prioritized', len(ctx.deltas))
        return ctx


class AllocateNode(PipelineNode):
    """Pipeline stage: allocate attention budget to deltas."""
    
    def __init__(
        self,
        budget: Optional[AttentionBudget] = None,
        total_budget: float = 100.0,
        strategy: str = 'actionability',
        name: str = "AllocateNode",
    ):
        super().__init__(name)
        self.budget = budget or AttentionBudget(
            total_budget=total_budget,
            strategy=strategy,
        )
    
    def process(self, ctx: PipelineContext) -> PipelineContext:
        ctx.allocations = self.budget.allocate(ctx.deltas)
        ctx.add_metadata('budget_remaining', self.budget.remaining)
        ctx.add_metadata('budget_utilization', self.budget.utilization)
        return ctx


class ExecuteScriptNode(PipelineNode):
    """Pipeline stage: execute scripts matched to deltas."""
    
    def __init__(
        self,
        library: Optional[ScriptLibrary] = None,
        name: str = "ExecuteScriptNode",
    ):
        super().__init__(name)
        self.library = library or ScriptLibrary()
    
    def process(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.deltas:
            obs_array = np.array([d.magnitude for d in ctx.deltas])
            for delta in ctx.deltas:
                obs = np.array([delta.magnitude])
                match = self.library.find_best_match(obs)
                if match:
                    script = self.library.get(match.script_id)
                    ctx.matched_scripts.append({
                        'script_id': match.script_id,
                        'script_name': script.name if script else match.script_id,
                        'confidence': match.confidence,
                        'delta': delta,
                    })
        return ctx


class LearnNode(PipelineNode):
    """Pipeline stage: learn from pipeline results."""
    
    def __init__(
        self,
        cycle: Optional[LearningCycle] = None,
        name: str = "LearnNode",
    ):
        super().__init__(name)
        self.cycle = cycle or LearningCycle()
    
    def process(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.snap_result:
            state = self.cycle.experience(ctx.input_value)
            ctx.add_metadata('learning_phase', state.phase.value)
            ctx.add_metadata('cognitive_load', state.cognitive_load)
        return ctx


class SnapPipeline:
    """
    Composable processing pipeline: snap → detect → prioritize → allocate → execute.
    
    Chains pipeline stages together, each transforming the pipeline context.
    Supports fluent API via SnapPipelineBuilder.
    
    Usage:
        pipeline = SnapPipeline()
        pipeline.add_node(SnapNode(tolerance=0.1))
        pipeline.add_node(DetectNode())
        pipeline.add_node(PrioritizeNode(top_k=3))
        pipeline.add_node(AllocateNode(total_budget=100.0))
        pipeline.add_node(ExecuteScriptNode())
        
        result = pipeline.run(0.42)
        print(f"Snap result: {result.snap_result}")
        print(f"Allocations: {result.allocations}")
    
    Or use the builder:
        results = (SnapPipelineBuilder()
            .snap(hexagonal, tolerance=0.1)
            .detect()
            .prioritize(top_k=3)
            .allocate(budget=100)
            .execute()
            .run_all(data_stream))
    """
    
    def __init__(self):
        self._nodes: List[PipelineNode] = []
        self._context_history: List[PipelineContext] = []
    
    def add_node(self, node: PipelineNode) -> 'SnapPipeline':
        """Add a processing node to the pipeline."""
        self._nodes.append(node)
        return self
    
    def run(self, value: float) -> PipelineContext:
        """
        Run a single value through the pipeline.
        
        Args:
            value: Input value to process.
        
        Returns:
            PipelineContext with all stage results.
        """
        ctx = PipelineContext(input_value=value)
        
        for node in self._nodes:
            try:
                ctx = node.process(ctx)
            except Exception as e:
                logger.error(f"Pipeline error in {node.name}: {e}")
                ctx.add_metadata(f"error_{node.name}", str(e))
                break
        
        self._context_history.append(ctx)
        return ctx
    
    def run_batch(self, values: List[float]) -> List[PipelineContext]:
        """Run multiple values through the pipeline."""
        return [self.run(v) for v in values]
    
    @property
    def statistics(self) -> Dict[str, Any]:
        if not self._context_history:
            return {'total_processed': 0}
        
        total = len(self._context_history)
        deltas_detected = sum(
            1 for ctx in self._context_history
            if ctx.snap_result and ctx.snap_result.is_delta
        )
        
        return {
            'total_processed': total,
            'pipeline_length': len(self._nodes),
            'deltas_detected': deltas_detected,
            'delta_rate': deltas_detected / max(total, 1),
            'nodes': [node.name for node in self._nodes],
        }
    
    def __repr__(self):
        return (f"SnapPipeline(nodes={len(self._nodes)}, "
                f"processed={len(self._context_history)})")


class PipelineBuilder:
    """
    Fluent API for building processing pipelines.
    
    Provides a clean builder pattern:
        pipeline = (PipelineBuilder()
            .snap(tolerance=0.1)
            .detect()
            .prioritize(top_k=5)
            .allocate(budget=200, strategy='actionability')
            .execute()
            .build())
    
    Usage:
        results = pipeline.run_batch(data_stream)
    """
    
    def __init__(self):
        self._nodes: List[PipelineNode] = []
    
    def snap(
        self,
        tolerance: float = 0.1,
        topology: SnapTopologyType = SnapTopologyType.HEXAGONAL,
        snap_function: Optional[SnapFunction] = None,
    ) -> 'PipelineBuilder':
        """Add a snap stage."""
        self._nodes.append(SnapNode(
            snap_function=snap_function,
            tolerance=tolerance,
            topology=topology,
        ))
        return self
    
    def detect(
        self,
        detector: Optional[DeltaDetector] = None,
    ) -> 'PipelineBuilder':
        """Add a delta detection stage."""
        self._nodes.append(DetectNode(detector=detector))
        return self
    
    def prioritize(
        self,
        top_k: int = 3,
    ) -> 'PipelineBuilder':
        """Add a prioritization stage."""
        self._nodes.append(PrioritizeNode(top_k=top_k))
        return self
    
    def allocate(
        self,
        budget_total: float = 100.0,
        strategy: str = 'actionability',
        budget: Optional[AttentionBudget] = None,
    ) -> 'PipelineBuilder':
        """Add an attention allocation stage."""
        self._nodes.append(AllocateNode(
            budget=budget,
            total_budget=budget_total,
            strategy=strategy,
        ))
        return self
    
    def execute(
        self,
        library: Optional[ScriptLibrary] = None,
    ) -> 'PipelineBuilder':
        """Add a script execution stage."""
        self._nodes.append(ExecuteScriptNode(library=library))
        return self
    
    def learn(
        self,
        cycle: Optional[LearningCycle] = None,
    ) -> 'PipelineBuilder':
        """Add a learning stage."""
        self._nodes.append(LearnNode(cycle=cycle))
        return self
    
    def custom(
        self,
        node: PipelineNode,
    ) -> 'PipelineBuilder':
        """Add a custom pipeline node."""
        self._nodes.append(node)
        return self
    
    def build(self) -> SnapPipeline:
        """Build and return the pipeline."""
        pipeline = SnapPipeline()
        for node in self._nodes:
            pipeline.add_node(node)
        return pipeline


# ─── Pre-built Pipelines ────────────────────────────────────────────


class MonitoringPipeline:
    """
    Pre-built pipeline for system monitoring.
    
    Snaps incoming metrics, detects anomalies, prioritizes critical
    signals, and allocates operator attention.
    
    Usage:
        monitor = MonitoringPipeline(
            streams=['cpu', 'memory', 'latency'],
            tolerance=0.1,
            budget=100.0,
        )
        
        for reading in live_metrics:
            alert = monitor.process(reading)
            if alert:
                print(f"Alert: {alert}")
    """
    
    def __init__(
        self,
        streams: Optional[List[str]] = None,
        tolerance: float = 0.1,
        budget: float = 100.0,
    ):
        self.streams = streams or ['default']
        self.tolerance = tolerance
        
        self.pipeline = (PipelineBuilder()
            .snap(tolerance=tolerance)
            .detect()
            .prioritize(top_k=5)
            .allocate(budget_total=budget, strategy='reactive')
            .execute()
            .build())
        
        self._alerts: List[str] = []
    
    def process(self, value: float, stream: str = 'default') -> Optional[str]:
        """Process a monitoring value. Returns alert string if critical."""
        ctx = self.pipeline.run(value)
        
        if ctx.snap_result and ctx.snap_result.is_delta:
            ratio = ctx.snap_result.delta / ctx.snap_result.tolerance
            if ratio > 5.0:
                alert = f"CRITICAL: {stream} delta {ctx.snap_result.delta:.4f}"
                self._alerts.append(alert)
                return alert
            elif ratio > 3.0:
                return f"WARNING: {stream} delta {ctx.snap_result.delta:.4f}"
        
        return None
    
    @property
    def alerts(self) -> List[str]:
        return list(self._alerts)
    
    @property
    def statistics(self) -> Dict[str, Any]:
        return self.pipeline.statistics


class LearningPipeline:
    """
    Pre-built pipeline for experience → script automation learning.
    
    Processes experiences, creates scripts from patterns, and
    tracks learning phases.
    
    Usage:
        learner = LearningPipeline(tolerance=0.1)
        
        for experience in training_data:
            phase = learner.process(experience)
            if phase == LearningPhase.SMOOTH_RUNNING:
                print("Learning plateaued — script library stable")
    """
    
    def __init__(
        self,
        tolerance: float = 0.1,
        learning_rate: float = 0.01,
    ):
        self.snap = SnapFunction(tolerance=tolerance, adaptation_rate=learning_rate)
        self.cycle = LearningCycle(snap=self.snap)
        
        self.pipeline = (PipelineBuilder()
            .snap(snap_function=self.snap)
            .detect()
            .prioritize()
            .learn(cycle=self.cycle)
            .build())
        
        self._phases: List[LearningPhase] = []
    
    def process(self, value: float) -> LearningPhase:
        """Process an experience and return the learning phase."""
        ctx = self.pipeline.run(value)
        phase = self.cycle.current_state.phase
        self._phases.append(phase)
        return phase
    
    @property
    def phase_history(self) -> List[LearningPhase]:
        return list(self._phases)
    
    @property
    def current_phase(self) -> Optional[LearningPhase]:
        return self._phases[-1] if self._phases else None
    
    @property
    def statistics(self) -> Dict[str, Any]:
        return {
            'current_phase': self.current_phase.value if self.current_phase else None,
            'phases_seen': list(set(p.value for p in self._phases)),
            'transitions': len(set(
                (self._phases[i], self._phases[i + 1])
                for i in range(len(self._phases) - 1)
            )),
            **self.cycle.statistics,
        }


class AnomalyPipeline:
    """
    Pre-built pipeline for anomaly detection.
    
    Flags observations that are statistical outliers beyond
    expected variance, not just exceed snap tolerance.
    
    Usage:
        detector = AnomalyPipeline(tolerance=0.1, z_threshold=3.0)
        
        for value in data_stream:
            anomaly = detector.process(value)
            if anomaly:
                print(f"Anomaly: {anomaly}")
    """
    
    def __init__(
        self,
        tolerance: float = 0.1,
        z_threshold: float = 3.0,
        window_size: int = 100,
    ):
        self.z_threshold = z_threshold
        self._window = deque(maxlen=window_size)
        self._mean = 0.0
        self._std = 0.0
        
        self.pipeline = (PipelineBuilder()
            .snap(tolerance=tolerance)
            .detect()
            .prioritize(top_k=3)
            .allocate(budget_total=50.0)
            .build())
    
    def process(self, value: float) -> Optional[Dict[str, Any]]:
        """
        Process a value. Returns anomaly info if anomalous.
        
        Anomaly = delta beyond tolerance AND z-score > threshold.
        """
        # Update window statistics
        self._window.append(value)
        if len(self._window) >= 3:
            self._mean = float(np.mean(self._window))
            self._std = float(np.std(self._window)) or 0.001
        
        # Run pipeline
        ctx = self.pipeline.run(value)
        
        if ctx.snap_result and ctx.snap_result.is_delta:
            z_score = abs(value - self._mean) / max(self._std, 0.001)
            
            if z_score > self.z_threshold:
                return {
                    'value': value,
                    'z_score': float(z_score),
                    'delta': ctx.snap_result.delta,
                    'tolerance': ctx.snap_result.tolerance,
                    'is_anomaly': True,
                }
            
            return {
                'value': value,
                'delta': ctx.snap_result.delta,
                'is_delta': True,
                'is_anomaly': False,
            }
        
        return None
    
    @property
    def statistics(self) -> Dict[str, Any]:
        return {
            'window_size': len(self._window),
            'mean': self._mean,
            'std': self._std,
            'z_threshold': self.z_threshold,
            **self.pipeline.statistics,
        }
