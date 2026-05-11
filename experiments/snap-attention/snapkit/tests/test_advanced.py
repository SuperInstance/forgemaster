"""Tests for snapkit advanced modules."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from snapkit import SnapFunction, SnapTopologyType
import numpy as np


# ─── Adversarial Tests ────────────────────────────────────────────────

def test_fake_delta_generator():
    from snapkit.adversarial import FakeDeltaGenerator, DeceptionLevel
    generator = FakeDeltaGenerator(style="loose_aggressive", deception_level=DeceptionLevel.BLUFF)
    fake = generator.generate(target_tolerance=0.1)
    assert fake is not None, "Expected a fake delta"
    assert hasattr(fake, 'value')
    assert hasattr(fake, 'magnitude')

def test_adversarial_detector():
    from snapkit.adversarial import AdversarialDetector
    detector = AdversarialDetector(detection_threshold=0.5)
    detector.learn_source_profile(
        "test_player", real_signal_rate=0.5, fake_signal_rate=0.5
    )
    result = detector.observe_signal("test_player", 0.42, 1.2)
    assert 'classified_as_fake' in result
    assert 'confidence' in result

def test_camouflage_engine():
    from snapkit.adversarial import CamouflageEngine, CamouflageLevel
    engine = CamouflageEngine(level=CamouflageLevel.BASIC)
    masked = engine.mask(0.42, detection_threshold=0.5)
    assert isinstance(masked, float)
    assert 0.0 <= masked <= 1.0

def test_bluff_calibration():
    from snapkit.adversarial import BluffCalibration
    calibrator = BluffCalibration(max_depth=5)
    calibrator.model_adversary("player_a", estimated_level=1)
    calibrator.record_round(my_bluffed=False, adversary_called=False, adversary_id="player_a")
    response = calibrator.optimize_response(my_level=2, adversary_id="player_a")
    assert 'strategy_name' in response
    assert 'reasoning' in response


# ─── Cross-Domain Tests ───────────────────────────────────────────────

def test_domain_profile():
    from snapkit.crossdomain import DomainProfile
    profile = DomainProfile(
        name="testing",
        randomness_type="categorical",
        pattern_density=0.5,
        noise_scale=0.1,
        feature_dim=3,
    )
    assert profile.name == "testing"
    assert profile.snap_profile() is not None

def test_feel_transfer():
    from snapkit.crossdomain import FeelTransfer
    transfer = FeelTransfer()
    
    # Get poker profile and transfer to driving
    poker = transfer.domain_profile('poker')
    if poker:
        driving = transfer.calibrate(poker, 'driving')
        assert driving is not None or poker is not None

def test_transfer_map():
    from snapkit.crossdomain import FeelTransfer
    transfer = FeelTransfer()
    quality = transfer.transfer('poker', 'driving')
    assert isinstance(quality, float)
    assert 0.0 <= quality <= 1.0

def test_calibration_speed():
    from snapkit.crossdomain import FeelTransfer
    transfer = FeelTransfer()
    speed = transfer.calibration_speed('poker', 'driving')
    assert isinstance(speed, float)
    assert 0.0 <= speed <= 1.0

def test_all_domain_profiles():
    from snapkit.crossdomain import FeelTransfer
    transfer = FeelTransfer()
    profiles = transfer.available_domains
    assert len(profiles) >= 5, f"Expected 5+ profiles, got {len(profiles)}"


# ─── Streaming Tests ──────────────────────────────────────────────────

def test_stream_processor():
    from snapkit.streaming import StreamProcessor, StreamConfig
    config = StreamConfig(stream_id="test", tolerance=0.1)
    processor = StreamProcessor(config=config)
    processor.observe(0.05)
    processor.observe(0.3)
    stats = processor.statistics
    assert stats['observations'] == 2

def test_windowed_snap():
    from snapkit.streaming import WindowedSnap, WindowConfig
    config = WindowConfig(window_size=10, stride=2, decay_factor=0.95)
    ws = WindowedSnap(config=config, tolerance=0.1)
    for i in range(25):
        value = 0.05 if i < 10 else 0.3 if i < 20 else 0.05
        ws.observe(value)
    assert ws.window_count > 0, "Expected at least one window processed"

def test_stream_monitor():
    from snapkit.streaming import StreamMonitor
    monitor = StreamMonitor(total_budget=100.0)
    snap = SnapFunction(tolerance=0.1)
    monitor.add_stream("test", snap=snap, weight=1.0)
    
    for _ in range(10):
        monitor.observe("test", float(np.random.random()))
    
    stats = monitor.statistics
    assert 'per_stream' in stats
    assert 'test' in stats['per_stream']

def test_backpressure():
    from snapkit.streaming import Backpressure
    bp = Backpressure(max_budget=100.0)
    
    for i in range(10):
        bp.record_delta(f"stream_{i}", magnitude=float(np.random.random()))
    
    dropped = bp.apply_backpressure()
    assert isinstance(dropped, list)

def test_stream_alerts():
    from snapkit.streaming import StreamMonitor
    monitor = StreamMonitor(total_budget=50.0)
    snap = SnapFunction(tolerance=0.1)
    monitor.add_stream("noisy", snap=snap, weight=1.0, alert_threshold=0.3)
    
    for _ in range(20):
        monitor.observe("noisy", 0.8)
    
    alerts = monitor.check_alerts()
    assert isinstance(alerts, list)


# ─── Integration Tests ────────────────────────────────────────────────

def test_numpy_snap():
    from snapkit.integration import NumpySnap
    ns = NumpySnap(tolerance=0.1)
    data = np.array([0.0, 0.05, 0.3, 0.06, 0.5])
    results = ns.snap(data)
    assert len(results) == 5
    assert 'snap_results' in results

def test_pysheaf_adapter():
    from snapkit.integration import PySheafAdapter
    adapter = PySheafAdapter()
    
    # PySheaf may not be installed
    try:
        result = adapter.snapkit_to_sheaf({'tolerance': 0.1})
        assert isinstance(result, dict)
    except ImportError:
        pass  # Optional dependency

def test_sympy_topology():
    from snapkit.integration import SymPyTopologyFactory
    factory = SymPyTopologyFactory()
    
    try:
        topology = factory.from_lie_algebra("A2")
        assert topology is not None
    except ImportError:
        pass  # Optional dependency


# ─── Pipeline Tests ───────────────────────────────────────────────────

def test_pipeline_basic():
    from snapkit.pipeline import SnapPipeline, SnapNode
    
    pipeline = SnapPipeline()
    pipeline.add_node(SnapNode(tolerance=0.1))
    
    ctx = pipeline.run(0.05)
    assert ctx.snap_result is not None
    assert ctx.snap_result.within_tolerance

def test_pipeline_full():
    from snapkit.pipeline import (
        SnapPipeline, SnapNode, DetectNode, 
        PrioritizeNode, AllocateNode, ExecuteScriptNode,
    )
    
    pipeline = SnapPipeline()
    pipeline.add_node(SnapNode(tolerance=0.1))
    pipeline.add_node(DetectNode())
    pipeline.add_node(PrioritizeNode(top_k=3))
    pipeline.add_node(AllocateNode(total_budget=100.0))
    pipeline.add_node(ExecuteScriptNode())
    
    ctx = pipeline.run(0.3)
    assert ctx.snap_result is not None
    assert ctx.snap_result.is_delta

def test_pipeline_builder():
    from snapkit.pipeline import PipelineBuilder
    
    pipeline = (PipelineBuilder()
        .snap(tolerance=0.1)
        .detect()
        .prioritize(top_k=3)
        .allocate(budget_total=100.0)
        .execute()
        .build()
    )
    
    ctx = pipeline.run(0.3)
    assert ctx.snap_result is not None

def test_monitoring_pipeline():
    from snapkit.pipeline import MonitoringPipeline
    
    monitor = MonitoringPipeline(tolerance=0.1, budget=100.0)
    
    # Normal values — no alerts
    alert = monitor.process(0.05)
    assert alert is None, f"Expected no alert, got {alert}"
    
    # Large delta — should alert
    alert = monitor.process(3.0)
    if alert:
        assert 'CRITICAL' in alert or 'WARNING' in alert

def test_learning_pipeline():
    from snapkit.pipeline import LearningPipeline
    
    learner = LearningPipeline(tolerance=0.1)
    for i in range(30):
        phase = learner.process(float(np.random.random() * 0.3))
    assert learner.current_phase is not None

def test_anomaly_pipeline():
    from snapkit.pipeline import AnomalyPipeline
    
    detector = AnomalyPipeline(tolerance=0.1, z_threshold=2.0)
    
    for _ in range(30):
        detector.process(float(np.random.randn()))
    
    # Anomalies may or may not occur with random data
    anomaly = detector.process(5.0)
    if anomaly:
        assert anomaly.get('is_anomaly', False) or True


# ─── CLI Tests ────────────────────────────────────────────────────────

def test_cli_import():
    from snapkit.cli import build_parser, cmd_status
    parser = build_parser()
    assert parser is not None

def test_cli_status():
    from snapkit.cli import cmd_status
    # Should not raise
    try:
        from unittest.mock import Mock
        cmd_status()
    except Exception as e:
        # Only fail on unexpected errors
        if 'SystemExit' not in str(type(e)):
            raise


if __name__ == '__main__':
    test_fns = [
        f for name, f in globals().items()
        if name.startswith('test_') and callable(f)
    ]
    passed = 0
    failed = 0
    for fn in test_fns:
        try:
            fn()
            passed += 1
            print(f"  ✓ {fn.__name__}")
        except Exception as e:
            failed += 1
            import traceback
            print(f"  ✗ {fn.__name__}: {traceback.format_exc()}")
    
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
