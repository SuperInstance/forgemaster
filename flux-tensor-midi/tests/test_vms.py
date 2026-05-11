#!/usr/bin/env python3
"""
Tests for the VMS (Video Music Score) encoder/decoder.
"""

import json
import math
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vms import (
    VideoScore, SceneEvent, SceneType, Channel, SideChannel,
    EisensteinLattice, FluxState,
    save_vms, load_vms, render_timeline, analyze_score, encode_midi_file,
    create_demo_score,
)


def test_eisenstein_lattice_snap():
    """Lattice snap returns nearest grid point."""
    lattice = EisensteinLattice(12)
    
    # Exact grid points snap to themselves
    assert lattice.snap(0.0) == 0.0
    assert lattice.snap(1.0) == 1.0
    assert lattice.snap(2.0) == 2.0
    
    # Mid-points snap to nearest
    assert lattice.snap(0.5) == 0.5  # 6/12 = exact
    assert lattice.snap(0.04) == 0.0  # 0.04 → 0.0
    assert lattice.snap(0.08) == pytest_approx(0.083, 0.01)  # ~1/12
    
    print("  ✅ Eisenstein lattice snap")


def test_lattice_snap_delta():
    """Snap delta is bounded by grid spacing."""
    lattice = EisensteinLattice(12)
    grid = 1.0 / 12.0
    
    # Snap delta should always be <= grid/2
    for beat in [0.01, 0.03, 0.07, 0.42, 1.33, 2.78]:
        delta = abs(lattice.snap_delta(beat))
        assert delta <= grid / 2 + 1e-10, f"delta {delta} > {grid/2} at beat {beat}"
    
    print("  ✅ Lattice snap delta bounded")


def test_video_score_add_scene():
    """Adding scenes snaps to beat grid."""
    score = VideoScore("test", tempo_bpm=72, lattice=EisensteinLattice(12))
    
    # Add scene at non-grid beat — should snap
    event = score.add_scene(SceneEvent(
        beat=0.07,  # Not on grid
        scene_type=SceneType.PRODUCT_CLOSEUP,
        duration_beats=4,
    ), snap=True)
    
    assert event.beat == 1.0/12.0  # Snapped to nearest 1/12
    assert len(score.events) == 1
    
    # Add scene without snap — stays at exact beat
    event2 = score.add_scene(SceneEvent(
        beat=0.077,
        scene_type=SceneType.TITLE_CARD,
        duration_beats=2,
    ), snap=False)
    
    assert event2.beat == 0.077
    assert len(score.events) == 2
    
    print("  ✅ Add scene with/without snap")


def test_video_score_duration():
    """Duration calculation is correct."""
    score = VideoScore("test", tempo_bpm=120)
    
    score.add_scene(SceneEvent(beat=0, scene_type=SceneType.PRODUCT_CLOSEUP, duration_beats=4), snap=False)
    score.add_scene(SceneEvent(beat=4, scene_type=SceneType.TITLE_CARD, duration_beats=8), snap=False)
    
    assert score.duration_beats() == 12.0
    assert abs(score.duration_seconds() - 6.0) < 0.01  # 12 beats / 120 BPM * 60 = 6s
    
    print("  ✅ Duration calculation")


def test_vms_roundtrip():
    """Save and load VMS preserves all data."""
    score = create_demo_score()
    
    with tempfile.NamedTemporaryFile(suffix=".vms", delete=False) as f:
        path = f.name
    
    try:
        save_vms(score, path)
        loaded = load_vms(path)
        
        assert loaded.name == score.name
        assert loaded.tempo_bpm == score.tempo_bpm
        assert loaded.lattice.divisions == score.lattice.divisions
        assert len(loaded.events) == len(score.events)
        
        for orig, load in zip(score.events, loaded.events):
            assert orig.beat == load.beat
            assert orig.scene_type == load.scene_type
            assert orig.duration_beats == load.duration_beats
            assert orig.velocity == load.velocity
            assert orig.channel == load.channel
    finally:
        os.unlink(path)
    
    print("  ✅ VMS roundtrip save/load")


def test_midi_export():
    """MIDI export produces valid bytes."""
    score = create_demo_score()
    midi_bytes = encode_midi_file(score)
    
    # Check MIDI header
    assert midi_bytes[:4] == b'MThd'
    assert midi_bytes[8:10] == b'\x00\x01'  # Format 1
    
    # Check that there's at least one track
    assert len(midi_bytes) > 100  # Should have content
    
    print(f"  ✅ MIDI export ({len(midi_bytes)} bytes)")


def test_temporal_entropy():
    """Temporal entropy is computed correctly."""
    # Uniform timing → low entropy
    uniform = VideoScore("uniform", tempo_bpm=60, lattice=EisensteinLattice(6))
    for i in range(20):
        uniform.add_scene(SceneEvent(
            beat=i * 2.0, scene_type=SceneType.PRODUCT_CLOSEUP, duration_beats=1
        ), snap=False)
    
    e_uniform = uniform.temporal_entropy()
    
    # Irregular timing → higher entropy
    irregular = VideoScore("irregular", tempo_bpm=60, lattice=EisensteinLattice(6))
    beats = [0, 0.5, 1.5, 4.0, 4.1, 8.0, 12.3, 15.0, 20.0]
    for b in beats:
        irregular.add_scene(SceneEvent(
            beat=b, scene_type=SceneType.PRODUCT_CLOSEUP, duration_beats=1
        ), snap=False)
    
    e_irregular = irregular.temporal_entropy()
    
    assert e_uniform < e_irregular, f"Uniform ({e_uniform}) should have lower entropy than irregular ({e_irregular})"
    
    print(f"  ✅ Temporal entropy (uniform={e_uniform:.2f}, irregular={e_irregular:.2f})")


def test_rhythm_quality():
    """Rhythm quality classification."""
    # Metronomic
    metro = VideoScore("metro", tempo_bpm=60)
    for i in range(20):
        metro.add_scene(SceneEvent(beat=i*4, scene_type=SceneType.PRODUCT_CLOSEUP, duration_beats=1), snap=False)
    assert metro.rhythm_quality() == "metronomic"
    
    print(f"  ✅ Rhythm quality ({metro.rhythm_quality()})")


def test_channel_events():
    """Channel filtering works."""
    score = create_demo_score()
    
    visual = score.channel_events(Channel.VISUAL)
    text = score.channel_events(Channel.TEXT)
    audio = score.channel_events(Channel.AUDIO)
    side = score.channel_events(Channel.SIDECHANNEL)
    
    assert len(visual) > 0
    assert len(text) > 0
    assert len(audio) > 0
    
    # All visual events are on channel 1
    for e in visual:
        assert e.channel == Channel.VISUAL
    
    print(f"  ✅ Channel events (visual={len(visual)}, text={len(text)}, audio={len(audio)})")


def test_events_at_beat():
    """Beat lookup works."""
    score = create_demo_score()
    
    # Beat 0 should have multiple events
    at_zero = score.events_at_beat(0.0)
    assert len(at_zero) >= 2  # Visual + Audio at minimum
    
    print(f"  ✅ Events at beat (beat 0 has {len(at_zero)} events)")


def test_analysis():
    """Score analysis produces valid metrics."""
    score = create_demo_score()
    analysis = analyze_score(score)
    
    assert analysis["name"] == score.name
    assert analysis["tempo_bpm"] == score.tempo_bpm
    assert analysis["total_events"] == len(score.events)
    assert analysis["temporal_entropy"] > 0
    assert 0 < analysis["mean_velocity"] <= 127
    assert "rhythm_quality" in analysis
    
    print(f"  ✅ Analysis (entropy={analysis['temporal_entropy']:.2f}, quality={analysis['rhythm_quality']})")


def test_render_timeline():
    """Timeline rendering produces frames."""
    score = create_demo_score()
    timeline = render_timeline(score)
    
    assert len(timeline) > 0
    assert timeline[0]["frame"] == 0
    assert timeline[0]["time"] == 0.0
    
    # Last frame should be near total duration
    total_s = score.duration_seconds()
    assert abs(timeline[-1]["time"] - total_s) < 0.1
    
    print(f"  ✅ Timeline render ({len(timeline)} frames)")


def test_flux_state():
    """FluxState serialization."""
    flux = FluxState(
        salience=[0.8, 0.2, 0.1, 0.0, 0.5, 0.0, 0.3, 0.0, 0.1],
        tolerance=[0.1, 0.3, 0.5, 1.0, 0.2, 1.0, 0.4, 1.0, 0.6],
    )
    
    d = flux.to_dict()
    flux2 = FluxState.from_dict(d)
    
    assert flux2.salience == flux.salience
    assert flux2.tolerance == flux.tolerance
    
    print("  ✅ FluxState roundtrip")


def pytest_approx(expected, tol):
    """Simple approximation check."""
    class Approx:
        def __eq__(self, other):
            return abs(other - expected) < tol
    return Approx()


# Monkey-patch for simple use
import builtins
builtins.pytest_approx = pytest_approx


if __name__ == "__main__":
    print("=" * 50)
    print("  VMS Test Suite")
    print("=" * 50)
    
    tests = [
        test_eisenstein_lattice_snap,
        test_lattice_snap_delta,
        test_video_score_add_scene,
        test_video_score_duration,
        test_vms_roundtrip,
        test_midi_export,
        test_temporal_entropy,
        test_rhythm_quality,
        test_channel_events,
        test_events_at_beat,
        test_analysis,
        test_render_timeline,
        test_flux_state,
    ]
    
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  ❌ {test.__name__}: {e}")
            failed += 1
    
    print()
    print(f"{'='*50}")
    print(f"  {passed} passed, {failed} failed")
    print(f"{'='*50}")
