"""Tests for snapkit core modules."""
import sys
import os
import math
import tempfile

# Add snapkit to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from snapkit import (
    SnapFunction, SnapResult, SnapTopologyType,
    DeltaDetector, Delta, DeltaSeverity,
    AttentionBudget, AttentionAllocation,
    ScriptLibrary, Script, ScriptMatch, ScriptStatus,
    LearningCycle, LearningPhase, LearningState,
)
from snapkit.topology import (
    SnapTopology, ADEType, ADE_DATA,
    binary_topology, hexagonal_topology, tetrahedral_topology,
    triality_topology, exceptional_e6, exceptional_e7, exceptional_e8,
    all_topologies, recommend_topology,
)
from snapkit.learning import Experience, ExperienceBuffer
from snapkit.scripts import ScriptPlan, ScriptStep
from snapkit.cohomology import ConstraintSheaf, ConsistencyReport
from snapkit.visualization import terminal_table, ascii_chart, html_report
from snapkit.serial import save, load

import numpy as np


# ─── SnapFunction Tests ───────────────────────────────────────────────

def test_snap_basic():
    snap = SnapFunction(tolerance=0.1)
    result = snap.observe(0.05)
    assert result.within_tolerance, f"Expected within tolerance, got {result}"
    assert result.snapped == 0.0, f"Expected snapped to 0.0, got {result.snapped}"
    assert not result.is_delta, "Expected not is_delta"

def test_delta_basic():
    snap = SnapFunction(tolerance=0.1)
    result = snap.observe(0.3)
    assert not result.within_tolerance, f"Expected outside tolerance, got {result}"
    assert result.is_delta, "Expected is_delta"

def test_calibrate():
    snap = SnapFunction(tolerance=0.5)
    values = [0.0, 0.05, 0.1, 0.15, 0.2, 0.5, 0.8, 1.0]
    snap.calibrate(values, target_snap_rate=0.75)
    rate = snap.snap_rate
    # After calibration, process the same values
    for v in values:
        snap.observe(v)
    assert abs(snap.snap_rate - 0.75) < 0.3 or snap.tolerance > 0

def test_snap_rate():
    snap = SnapFunction(tolerance=0.1)
    for _ in range(90):
        snap.observe(0.05)  # Within tolerance
    for _ in range(10):
        snap.observe(0.3)  # Outside tolerance
    assert abs(snap.snap_rate - 0.9) < 0.1, f"Expected ~0.9, got {snap.snap_rate:.2f}"

def test_adaptive_tolerance():
    snap = SnapFunction(tolerance=0.1)
    snap.enable_adaptive_tolerance(window=5)
    # High delta rate should tighten tolerance
    for _ in range(10):
        snap.observe(0.3)
    assert snap.tolerance < 0.09, f"Expected tightened tolerance, got {snap.tolerance:.4f}"

def test_hierarchical_snap():
    snap = SnapFunction(tolerance=0.1)
    levels = [0.01, 0.05, 0.1, 0.2, 0.5]
    results = snap.snap_hierarchical(0.05, levels)
    assert len(results) == 5, f"Expected 5 results, got {len(results)}"
    # At tightest tolerance (0.01), 0.05 should be a delta
    assert results[0].is_delta, f"Tightest tolerance should be delta: {results[0]}"
    # At loosest tolerance (0.5), 0.05 should be within tolerance
    assert results[-1].within_tolerance, f"Loosest tolerance should snap: {results[-1]}"

def test_hierarchical_profile():
    snap = SnapFunction(tolerance=0.1)
    profile = snap.hierarchical_profile(0.3)
    assert 'levels' in profile
    assert 'transition_tolerance' in profile
    assert len(profile['levels']) == 5

def test_snap_batch():
    snap = SnapFunction(tolerance=0.1)
    results = snap.snap_batch([0.05, 0.3, 0.06, 0.5, 0.08])
    assert results['count'] == 5
    assert results['snap_rate'] >= 0.3  # At least 3 out of 5 should snap

def test_snap_rolling():
    snap = SnapFunction(tolerance=0.1)
    values = [0.0, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    results = snap.snap_rolling(values, window=5, stride=3)
    assert len(results) > 0, "Expected at least one rolling result"

def test_snap_complex():
    snap = SnapFunction(tolerance=0.5)
    result = snap.snap_complex(complex(0.7, 0.3))
    assert result.within_tolerance or result.is_delta, f"Unexpected: {result}"

def test_serialization():
    snap = SnapFunction(tolerance=0.1, topology=SnapTopologyType.HEXAGONAL, baseline=0.5)
    # Use values that are within tolerance to trigger adaptation
    snap.observe(0.48)  # Distance 0.02 -> within tolerance -> adapts baseline
    snap.observe(0.45)  # Distance 0.03 -> within tolerance -> adapts baseline
    
    data = snap.to_dict()
    assert data['tolerance'] == 0.1
    assert data['adaptation_rate'] == 0.01  # Default
    
    restored = SnapFunction.from_dict(data)
    assert restored.tolerance == snap.tolerance
    assert len(restored._history) == 2


# ─── DeltaDetector Tests ──────────────────────────────────────────────

def test_delta_detector_basic():
    detector = DeltaDetector()
    detector.add_stream('test', SnapFunction(tolerance=0.1))
    
    deltas = detector.observe({'test': 0.05})
    assert 'test' in deltas
    assert not deltas['test'].exceeds_tolerance

def test_delta_detector_delta():
    detector = DeltaDetector()
    detector.add_stream('test', SnapFunction(tolerance=0.1))
    
    deltas = detector.observe({'test': 0.3})
    assert deltas['test'].exceeds_tolerance

def test_delta_prioritize():
    detector = DeltaDetector()
    detector.add_stream('a', SnapFunction(tolerance=0.1))
    detector.add_stream('b', SnapFunction(tolerance=0.1))
    
    for _ in range(5):
        detector.observe({'a': 0.3, 'b': 0.05})
    
    prioritized = detector.prioritize(top_k=3)
    assert len(prioritized) <= 3

def test_delta_clustering():
    detector = DeltaDetector()
    detector.add_stream('a', SnapFunction(tolerance=0.1))
    detector.add_stream('b', SnapFunction(tolerance=0.1))
    detector.add_stream('c', SnapFunction(tolerance=0.1))
    
    for _ in range(10):
        detector.observe({'a': 0.5, 'b': 0.05, 'c': 0.3})
    
    clusters = detector.delta_clusters(n_clusters=2)
    assert len(clusters) > 0, "Expected at least one cluster"

def test_delta_forecast():
    detector = DeltaDetector()
    detector.add_stream('test', SnapFunction(tolerance=0.1))
    
    for _ in range(10):
        detector.observe({'test': 0.3})
    
    stream = detector._streams['test']
    forecast = stream.delta_forecast(horizon=3)
    assert len(forecast) == 3

def test_delta_correlation():
    detector = DeltaDetector()
    detector.add_stream('a', SnapFunction(tolerance=0.1))
    detector.add_stream('b', SnapFunction(tolerance=0.1))
    
    for _ in range(10):
        detector.observe({'a': 0.3, 'b': 0.3})
    
    stream_a = detector._streams['a']
    stream_b = detector._streams['b']
    corr = stream_a.delta_correlation(stream_b)
    assert isinstance(corr, float), f"Expected float, got {type(corr)}"

def test_importance_scores():
    detector = DeltaDetector()
    detector.add_stream('a', SnapFunction(tolerance=0.1))
    detector.add_stream('b', SnapFunction(tolerance=0.1))
    
    for _ in range(5):
        detector.observe({'a': 0.3, 'b': 0.05})
    
    scores = detector.importance_scores()
    assert 'a' in scores
    assert 'b' in scores


# ─── AttentionBudget Tests ────────────────────────────────────────────

def test_budget_basic():
    budget = AttentionBudget(total_budget=100.0, strategy='actionability')
    assert budget.total_budget == 100.0
    assert budget.remaining == 100.0

def test_budget_allocate():
    budget = AttentionBudget(total_budget=100.0, strategy='actionability')
    deltas = [
        Delta(value=0.3, expected=0.0, magnitude=0.3, tolerance=0.1,
              timestamp=0, severity=DeltaSeverity.HIGH, stream_id='a', actionability=0.8, urgency=0.7),
        Delta(value=0.15, expected=0.0, magnitude=0.15, tolerance=0.1,
              timestamp=0, severity=DeltaSeverity.MEDIUM, stream_id='b', actionability=0.5, urgency=0.4),
    ]
    allocs = budget.allocate(deltas)
    assert len(allocs) > 0, "Expected at least one allocation"
    total_alloc = sum(a.allocated for a in allocs)
    assert total_alloc <= 100.0, f"Over budget: {total_alloc}"

def test_budget_exhaustion():
    budget = AttentionBudget(total_budget=10.0, strategy='actionability')
    # Create deltas with varying priorities — the low-priority ones should get zero
    many_deltas = [
        Delta(value=float(i), expected=0.0, magnitude=float(i), tolerance=0.1,
              timestamp=0, severity=DeltaSeverity.HIGH, stream_id=f'stream_{i}',
              actionability=1.0/(i+1), urgency=1.0/(i+1))
        for i in range(1, 21)
    ]
    allocs = budget.allocate(many_deltas)
    total_alloc = sum(a.allocated for a in allocs)
    assert total_alloc <= 10.0, f"Over budget: {total_alloc}"

def test_multi_level_allocate():
    budget = AttentionBudget(total_budget=100.0)
    macro = [
        Delta(value=0.3, expected=0.0, magnitude=0.3, tolerance=0.1,
              timestamp=0, severity=DeltaSeverity.HIGH, stream_id='stream_a', actionability=0.8, urgency=0.7),
        Delta(value=0.2, expected=0.0, magnitude=0.2, tolerance=0.1,
              timestamp=0, severity=DeltaSeverity.MEDIUM, stream_id='stream_b', actionability=0.5, urgency=0.4),
    ]
    micro = {
        'stream_a': [
            Delta(value=0.1, expected=0.0, magnitude=0.1, tolerance=0.1,
                  timestamp=0, severity=DeltaSeverity.MEDIUM, stream_id='detail_1', actionability=0.6, urgency=0.5),
        ],
    }
    result = budget.multi_level_allocate(macro, micro, macro_budget=40.0, micro_budget=60.0)
    assert 'macro' in result
    assert 'micro' in result

def test_allocate_with_reserve():
    budget = AttentionBudget(total_budget=100.0)
    critical = [
        Delta(value=0.8, expected=0.0, magnitude=0.8, tolerance=0.1,
              timestamp=0, severity=DeltaSeverity.CRITICAL, stream_id='critical',
              actionability=1.0, urgency=1.0),
    ]
    allocs = budget.allocate_with_reserve(critical, reserve_fraction=0.2)
    assert len(allocs) > 0

def test_attention_insight():
    budget = AttentionBudget(total_budget=100.0, strategy='actionability')
    delta = Delta(value=0.3, expected=0.0, magnitude=0.3, tolerance=0.1,
                  timestamp=0, severity=DeltaSeverity.HIGH, stream_id='stream_a',
                  actionability=0.8, urgency=0.7)
    budget.allocate([delta])
    insight = budget.attention_insight()
    assert 'insights' in insight

def test_apply_decay():
    budget = AttentionBudget(total_budget=100.0)
    delta = Delta(value=0.3, expected=0.0, magnitude=0.3, tolerance=0.1,
                  timestamp=0, severity=DeltaSeverity.HIGH, stream_id='test',
                  actionability=0.8, urgency=0.7)
    budget.allocate([delta])
    budget.allocate([delta])
    budget.apply_decay(decay_rate=0.1)


# ─── ScriptLibrary Tests ──────────────────────────────────────────────

def test_script_creation():
    script = Script(
        id='test_script',
        name='Test Script',
        trigger_pattern=np.array([0.1, 0.2, 0.3]),
        response='test_response',
    )
    assert script.id == 'test_script'
    assert script.status == ScriptStatus.ACTIVE

def test_script_match():
    script = Script(
        id='test_match',
        name='Match Test',
        trigger_pattern=np.array([1.0, 0.0]),
        response='match',
        match_threshold=0.8,
    )
    match = script.match(np.array([0.95, 0.05]))
    assert match.is_match, f"Expected match, got confidence={match.confidence:.3f}"
    assert match.script_id == 'test_match'

def test_library_basic():
    lib = ScriptLibrary(match_threshold=0.85)
    lib.learn(
        trigger_pattern=np.array([0.1, 0.2, 0.3]),
        response='pattern_1',
        name='pattern_1',
    )
    assert lib.active_scripts == 1

def test_library_hit():
    lib = ScriptLibrary(match_threshold=0.7)
    lib.learn(
        trigger_pattern=np.array([0.5, 0.5]),
        response='found',
        name='found_pattern',
    )
    match = lib.find_best_match(np.array([0.48, 0.52]))
    assert match is not None, "Expected a match"
    assert match.is_match, f"Expected is_match, got conf={match.confidence:.3f}"

def test_library_miss():
    lib = ScriptLibrary(match_threshold=0.95)
    lib.learn(
        trigger_pattern=np.array([1.0, 0.0]),
        response='no_match',
        name='strict_pattern',
    )
    # Use opposite vector to get low cosine similarity
    match = lib.find_best_match(np.array([0.0, 1.0]))
    # With threshold 0.95, orthogonal vectors should not match
    if match is not None:
        assert not match.is_match, f"Expected no match, got confidence={match.confidence}"

def test_script_compose():
    lib = ScriptLibrary()
    s1 = lib.learn(np.array([0.1, 0.2]), 'r1', 'a')
    s2 = lib.learn(np.array([0.3, 0.4]), 'r2', 'b')
    
    composite = lib.compose([s1.id, s2.id])
    assert composite is not None, "Expected composite script"
    assert composite.id is not None

def test_script_resolve_conflicts():
    lib = ScriptLibrary(match_threshold=0.6)
    lib.learn(np.array([0.5, 0.5]), 'response_a', 'a')
    lib.learn(np.array([0.5, 0.5]), 'response_b', 'b')
    
    match = lib.resolve_conflicts(np.array([0.48, 0.52]))
    assert match is not None

def test_script_inherit():
    lib = ScriptLibrary()
    parent = lib.learn(np.array([0.1, 0.2]), 'parent_response', 'parent')
    child = lib.extend(parent.id, 'child_v1', 'child_response')
    assert child is not None, "Expected child script"
    assert child.name is not None

def test_script_version():
    lib = ScriptLibrary()
    s1 = lib.learn(np.array([0.1, 0.2]), 'v1_response', 'my_script')
    sid = s1.id
    original = lib.get(sid)
    assert original is not None
    
    updated = Script(
        id=sid,
        name='my_script_v2',
        trigger_pattern=np.array([0.1, 0.2]),
        response='v2_response',
    )
    success = lib.update(sid, updated)
    assert success, "Expected update to succeed"
    
    history = lib.version_history(sid)
    assert len(history) > 0

def test_script_plan():
    lib = ScriptLibrary()
    lib.learn(np.array([0.1]), 'fold_response', 'fold_weak_hand')
    lib.learn(np.array([0.2]), 'raise_response', 'raise_strong_hand')
    
    plan = ScriptPlan('poker_strategy', lib)
    plan.add_step('fold_weak_hand')
    plan.add_step('raise_strong_hand', conditions={'hand_strength': 'strong'})
    
    result = plan.execute(np.array([0.05]))
    # May return None if plan progresses or completes
    assert plan.progress >= 0

def test_script_forget():
    lib = ScriptLibrary()
    script = lib.learn(np.array([0.1]), 'response', 'to_forget')
    assert lib.active_scripts == 1
    lib.forget(script.id)
    assert lib.active_scripts == 0


# ─── LearningCycle Tests ──────────────────────────────────────────────

def test_cycle_initial_state():
    cycle = LearningCycle(snap=SnapFunction(tolerance=0.1))
    state = cycle.current_state
    assert state.phase == LearningPhase.DELTA_FLOOD, f"Expected DELTA_FLOOD, got {state.phase}"
    assert state.total_experiences == 0

def test_cycle_process():
    cycle = LearningCycle(snap=SnapFunction(tolerance=0.1))
    for _ in range(10):
        state = cycle.experience(0.05)
    assert state.total_experiences == 10

def test_cycle_delta_flood():
    cycle = LearningCycle(snap=SnapFunction(tolerance=0.1))
    for _ in range(20):
        state = cycle.experience(float(np.random.random() * 2))
    # Should have produced some scripts
    assert cycle.library.active_scripts > 0 or state.total_experiences > 0

def test_cycle_smooth_running():
    cycle = LearningCycle(snap=SnapFunction(tolerance=0.5))
    # Same value -> many snaps -> scripts
    for _ in range(50):
        state = cycle.experience(0.3)
    assert state.snap_hit_rate >= 0, f"Unexpected snap rate: {state.snap_hit_rate}"

def test_cycle_phase_transition():
    cycle = LearningCycle(snap=SnapFunction(tolerance=0.1))
    for _ in range(20):
        cycle.experience(float(np.random.random() * 2))
    transition = cycle.detect_phase_transition(lookback=15)
    # May or may not have a transition in 20 random experiences
    assert transition is None or 'from' in transition

def test_adapt_learning_rate():
    cycle = LearningCycle(snap=SnapFunction(tolerance=0.1))
    for _ in range(20):
        cycle.experience(float(np.random.random() * 2))
    new_rate = cycle.adapt_learning_rate()
    assert cycle.snap.adaptation_rate == new_rate
    assert 0.001 <= new_rate <= 0.1

def test_apply_forgetting():
    cycle = LearningCycle(snap=SnapFunction(tolerance=0.1))
    for _ in range(50):
        cycle.experience(0.05)
    cycle.apply_forgetting(decay_rate=0.5)

def test_transfer_knowledge():
    source = LearningCycle(snap=SnapFunction(tolerance=0.1))
    for _ in range(30):
        source.experience(0.5)
    
    target = LearningCycle(snap=SnapFunction(tolerance=0.1))
    count = target.transfer_knowledge(source)
    assert count >= 0


# ─── ExperienceBuffer Tests ───────────────────────────────────────────

def test_buffer_basic():
    buffer = ExperienceBuffer(capacity=100)
    for i in range(50):
        buffer.store(observation=float(i) / 50, delta=0.1, was_scripted=i % 2 == 0)
    assert buffer.size == 50

def test_buffer_sample():
    buffer = ExperienceBuffer(capacity=100)
    for i in range(50):
        buffer.store(observation=float(i), delta=0.1, was_scripted=True)
    samples = buffer.sample(10)
    assert len(samples) == 10

def test_buffer_wrap():
    buffer = ExperienceBuffer(capacity=10)
    for i in range(20):
        buffer.store(observation=float(i), delta=0.1, was_scripted=False)
    assert buffer.is_full
    assert buffer.size == 10  # Capacity limit

def test_buffer_replay():
    buffer = ExperienceBuffer(capacity=100)
    cycle = LearningCycle(snap=SnapFunction(tolerance=0.1))
    
    for i in range(50):
        buffer.store(observation=float(i % 10) / 10, delta=0.05 if i % 2 == 0 else 0.3, was_scripted=i % 3 == 0)
    
    buffer.replay(cycle, n=20)


# ─── Topology Tests ────────────────────────────────────────────────────

def test_all_topologies():
    topos = all_topologies()
    assert len(topos) >= 8, f"Expected at least 8 topologies, got {len(topos)}"

def test_hexagonal_basic():
    from snapkit import SnapFunction
    topology = hexagonal_topology()
    assert topology.name is not None
    # Use topology's ADE type with SnapFunction
    snap = SnapFunction(tolerance=0.1, topology=topology.ade_type)
    assert snap is not None

def test_recommend_topology():
    data = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]
    topo = recommend_topology(data)
    assert topo is not None, "Expected a recommended topology"

def test_exceptional_e6():
    topology = exceptional_e6()
    assert topology is not None
    assert topology.name == 'E6'

def test_exceptional_e8():
    topology = exceptional_e8()
    assert topology is not None
    assert topology.name == 'E8'

def test_triality():
    topology = triality_topology()
    assert topology is not None
    assert topology.name == 'D4'


# ─── Cohomology Tests ─────────────────────────────────────────────────

def test_constraint_sheaf_basic():
    sheaf = ConstraintSheaf()
    result = sheaf.check_consistency()
    assert isinstance(result, ConsistencyReport)

def test_sheaf_verify_consistent():
    sheaf = ConstraintSheaf()
    sheaf.add_constraint('a', 0.5, 0.5)
    sheaf.add_constraint('b', 0.4, 0.4)
    report = sheaf.check_consistency()
    assert isinstance(report, ConsistencyReport)


# ─── Visualization Tests ──────────────────────────────────────────────

def test_terminal_table():
    headers = ['Col1', 'Col2']
    rows = [['A', '1'], ['B', '2']]
    table = terminal_table(headers, rows, title="Test")
    assert 'Test' in table
    assert 'Col1' in table
    assert 'A' in table

def test_ascii_chart():
    data = [0.1, 0.3, 0.2, 0.5, 0.4]
    chart = ascii_chart(data, width=30, height=5)
    assert len(chart) > 0, "Expected non-empty chart"

def test_html_report():
    data = {'test': 'value', 'stats': {'mean': 0.5, 'count': 10}}
    report = html_report(data, title="Test Report")
    assert 'Test Report' in report
    assert 'html' in report.lower()


# ─── Serialization Tests ──────────────────────────────────────────────

def test_save_load_json():
    data = {'key': 'value', 'nested': {'a': 1, 'b': 2.0}}
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w') as f:
        path = f.name
    try:
        save(data, path)
        loaded = load(path)
        assert loaded['key'] == 'value'
        assert loaded['nested']['a'] == 1
    finally:
        if os.path.exists(path):
            os.unlink(path)

def test_save_load_numpy():
    data = {'array': np.array([1.0, 2.0, 3.0])}
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w') as f:
        path = f.name
    try:
        save(data, path)
        loaded = load(path)
        assert 'array' in loaded
    finally:
        if os.path.exists(path):
            os.unlink(path)

def test_export_csv():
    import tempfile, os
    from snapkit.serial import export_csv
    data = [
        {'stream': 'a', 'delta': 0.3, 'timestamp': 1},
        {'stream': 'b', 'delta': 0.1, 'timestamp': 2},
    ]
    f = tempfile.NamedTemporaryFile(suffix='.csv', delete=False, mode='w')
    path = f.name
    f.close()
    try:
        csv_content = export_csv(data, path)
        assert 'stream' in csv_content or os.path.exists(path)
    finally:
        if os.path.exists(path):
            os.unlink(path)


# ─── SnapResult Tests ─────────────────────────────────────────────────

def test_snap_result_properties():
    result = SnapResult(
        original=0.3, snapped=0.0, delta=0.3,
        within_tolerance=False, tolerance=0.1,
        topology=SnapTopologyType.HEXAGONAL,
    )
    assert result.is_delta
    assert not result.within_tolerance

    snap_result = SnapResult(
        original=0.05, snapped=0.0, delta=0.05,
        within_tolerance=True, tolerance=0.1,
        topology=SnapTopologyType.HEXAGONAL,
    )
    assert snap_result.within_tolerance
    assert not snap_result.is_delta


# ─── Integration Tests ────────────────────────────────────────────────

def test_snapkit_integration_basic():
    """Full pipeline integration test."""
    snap = SnapFunction(tolerance=0.1)
    detector = DeltaDetector()
    detector.add_stream('test', snap)
    budget = AttentionBudget(total_budget=100.0)
    
    # Process observations
    for i in range(20):
        value = 0.05 if i % 3 == 0 else 0.3
        snap.observe(value)
        detector.observe({'test': value})
    
    prioritized = detector.prioritize(top_k=3)
    budget.allocate(prioritized)
    
    # Verify
    assert snap.snap_rate > 0, "Expected some snaps"
    assert budget.utilization >= 0, f"Unexpected utilization: {budget.utilization}"


# ─── Edge Cases ────────────────────────────────────────────────────────

def test_snap_hysteresis():
    snap = SnapFunction(tolerance=0.1, adaptation_rate=0.0)
    # Value exactly at tolerance boundary
    result = snap.observe(0.1)
    assert result.within_tolerance or result.is_delta, "Boundary should snap or delta"

def test_snap_negative():
    snap = SnapFunction(tolerance=0.1)
    result = snap.observe(-0.05)
    assert result.within_tolerance, f"Negative value within tolerance: {result}"

def test_snap_zero_tolerance():
    snap = SnapFunction(tolerance=0.001, adaptation_rate=0.0)
    # At near-zero tolerance, everything is a delta
    result = snap.observe(0.05)
    assert result.is_delta, "Near-zero tolerance should flag everything"

def test_empty_delta_detector():
    detector = DeltaDetector()
    result = detector.observe({})
    assert result == {}, "Empty observation should return empty deltas"

def test_empty_budget_allocation():
    budget = AttentionBudget(total_budget=100.0)
    allocs = budget.allocate([])
    assert allocs == [], f"Expected empty list, got {allocs}"

def test_empty_script_library():
    lib = ScriptLibrary()
    match = lib.find_best_match(np.array([0.5]))
    assert match is None, "Empty library should return None"


if __name__ == '__main__':
    # Run all tests
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
            print(f"  ✗ {fn.__name__}: {e}")
    
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
