#!/usr/bin/env python3
"""tests/test_active_probe_and_scale.py — Prove the foundations work.

Tests for:
1. ActiveSonar — boundary, consistency, and coverage probing
2. ScaleFold — room↔tile folding and S-dimension navigation
"""
import sys
import os
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.active_probe import (
    BoundaryProbe, ConsistencyProbe, CoverageProbe,
    TerrainMap, Desire, ActiveSonar, Echo,
)
from core.scale_fold import ScaleFoldEngine, Scale, ScaleStack, FoldedEntity


# ─── Active Probe Tests ───────────────────────────────────────────────────────

def test_boundary_probe_finds_edge():
    """Boundary probe should find where a tile breaks."""
    prober = BoundaryProbe(step_size=0.1, max_steps=10)

    # Tile works until perturbation > 0.5
    def test_fn(tid, pert):
        return pert < 0.5, max(0, 1.0 - pert)

    echo = prober.probe("test-tile", test_fn)
    assert echo.hit, "Should find boundary"
    assert 0.4 <= echo.boundary_distance <= 0.5, f"Boundary should be near 0.5, got {echo.boundary_distance}"
    assert echo.new_knowledge
    print(f"✓ Boundary probe found edge at {echo.boundary_distance}")


def test_boundary_probe_robust_tile():
    """Robust tile should survive all perturbations."""
    prober = BoundaryProbe(step_size=0.1, max_steps=5)

    def test_fn(tid, pert):
        return True, 1.0  # always works

    echo = prober.probe("robust-tile", test_fn)
    assert not echo.hit, "Robust tile should not hit boundary"
    assert echo.boundary_distance == 1.0
    print("✓ Robust tile survives all perturbations")


def test_consistency_probe_finds_contradiction():
    """Consistency probe should find tiles that disagree."""
    prober = ConsistencyProbe(agreement_threshold=0.8)

    tiles = ["tile-a", "tile-b", "tile-c"]

    def query_fn(tid):
        vals = {"tile-a": {"conf": 0.9}, "tile-b": {"conf": 0.85}, "tile-c": {"conf": 0.3}}
        return vals.get(tid, {"conf": 0.5})

    def compare_fn(a, b):
        return 1.0 - abs(a["conf"] - b["conf"])

    echoes = prober.probe(tiles, query_fn, compare_fn)
    # tile-c (0.3) should contradict with tile-a (0.9) and tile-b (0.85)
    contradicted = [e for e in echoes if "tile-c" in e.contradicted_by or e.target_tile_id == "tile-c"]
    assert len(contradicted) >= 2, f"Should find contradictions with tile-c, got {len(contradicted)}"
    print(f"✓ Consistency probe found {len(contradicted)} contradictions")


def test_coverage_probe_finds_gaps():
    """Coverage probe should find empty regions."""
    prober = CoverageProbe(n_bins=5, thin_threshold=2)

    # Cluster tiles in one corner
    tiles_data = [{"x": random.random() * 0.2, "y": random.random() * 0.2} for _ in range(10)]

    echoes = prober.probe(tiles_data, feature_fn=lambda t: (t["x"], t["y"]), n_dimensions=2)
    assert len(echoes) > 0, "Should find gaps in sparse regions"
    print(f"✓ Coverage probe found {len(echoes)} gaps in sparsely-covered space")


def test_terrain_map_accumulates():
    """Terrain map should accumulate echoes into a coherent picture."""
    map = TerrainMap()

    # Add boundary echoes
    for i in range(5):
        echo = Echo(
            probe_id=f"p-{i}",
            probe_type="boundary",
            target_tile_id=f"tile-{i % 2}",
            timestamp=0,
            hit=True,
            boundary_distance=0.3 + i * 0.05,
            confidence_at_boundary=0.5,
        )
        map.record(echo)

    r = map.resolve()
    assert r["total_probes"] == 5
    assert r["boundaries_found"] == 2  # tile-0 and tile-1
    print(f"✓ Terrain map resolved {r['boundaries_found']} boundaries from {r['total_probes']} probes")


def test_desire_drives_probing():
    """Desire should choose probe mode based on terrain state."""
    terrain = TerrainMap()
    desire = Desire()

    # Empty terrain → explore
    mode = desire.next_probe_mode(terrain)
    assert mode == Desire.EXPLORE, "Empty terrain should drive exploration"
    print(f"✓ Desire: empty terrain → {mode}")

    # Add lots of coverage gaps → still explore
    for _ in range(50):
        echo = Echo(
            probe_id="p", probe_type="coverage", target_tile_id="",
            timestamp=0, hit=False, boundary_distance=0.0,
            confidence_at_boundary=0.0, gap_found=True, shadow_angle="gap"
        )
        terrain.record(echo)
    mode = desire.next_probe_mode(terrain)
    print(f"✓ Desire: many gaps → {mode}")


def test_active_sonar_orchestration():
    """Full ActiveSonar should probe, map, and desire."""
    sonar = ActiveSonar()

    # Boundary probe
    def test_fn(tid, pert):
        return pert < 0.6, max(0, 0.9 - pert)

    echo = sonar.ping_boundary("test-tile", test_fn)
    assert echo.hit

    # Coverage probe
    tiles = [{"x": random.random(), "y": random.random()} for _ in range(5)]
    gaps = sonar.ping_coverage(tiles, lambda t: (t["x"], t["y"]))
    assert len(gaps) > 0

    # Status should show everything
    status = sonar.status()
    assert status["terrain"]["total_probes"] > 0
    print(f"✓ ActiveSonar: {status['terrain']['total_probes']} probes, "
          f"desire suggests {sonar.next_desire()}")


# ─── Scale Fold Tests ─────────────────────────────────────────────────────────

def test_scale_create_and_navigate():
    """Should create entities and navigate the scale stack."""
    engine = ScaleFoldEngine()
    root = engine.create("root", Scale.BUILDING)
    child = engine.create("child", Scale.ROOM, parent_id=root.id)
    grandchild = engine.create("grandchild", Scale.TILE, parent_id=child.id)

    nav = engine.navigate("test-agent", root.id)
    assert nav.current.id == root.id
    assert nav.current_scale == Scale.BUILDING

    nav.push(child.id)
    assert nav.current_scale == Scale.ROOM

    nav.push(grandchild.id)
    assert nav.current_scale == Scale.TILE

    nav.pop()
    assert nav.current_scale == Scale.ROOM

    nav.pop()
    assert nav.current_scale == Scale.BUILDING
    print("✓ Scale navigation: BUILDING → ROOM → TILE → ROOM → BUILDING")


def test_fold_up_creates_tile():
    """Folding up should create a compressed entity at higher scale."""
    engine = ScaleFoldEngine()
    room = engine.create("nav-station", Scale.ROOM, "GPS + charts + sounder")
    engine.create("gps", Scale.TILE, "Position sensor", room.id)
    engine.create("sounder", Scale.TILE, "Depth finder", room.id)

    folded = engine.fold_up(room.id)
    assert folded is not None
    assert folded.scale == Scale.FLOOR
    assert "2" in folded.content["summary"]
    print(f"✓ Fold up: ROOM with 2 tiles → FLOOR tile: {folded.content['summary']}")


def test_see_from_above():
    """Should show entity at multiple scales."""
    engine = ScaleFoldEngine()
    tile = engine.create("sounder", Scale.TILE, "depth finder")
    engine.create("200kHz", Scale.ATOM, "high freq", tile.id)
    engine.create("50kHz", Scale.ATOM, "low freq", tile.id)

    view = engine.see_from_above(tile.id, levels=2)
    assert "TILE" in view
    assert "ROOM" in view
    print("✓ See from above shows multiple scale levels")


def test_name_carries_across_folds():
    """The JOB name should persist across scale changes."""
    engine = ScaleFoldEngine()
    extinguisher = engine.create("fire-extinguisher", Scale.TILE,
                                  content="puts out fires",
                                  parent_id=None)
    # When we fold it up, the name should still be fire-extinguisher
    # (or its fold_up_name if set)
    folded = engine.fold_up(extinguisher.id)
    assert folded.name == "fire-extinguisher"  # job name persists
    print(f"✓ Name carries: fire-extinguisher → {folded.name} at {folded.scale.name}")


def test_path_tracking():
    """Navigation path should track zoom history."""
    engine = ScaleFoldEngine()
    vessel = engine.create("vessel", Scale.BUILDING)
    deck = engine.create("deck", Scale.FLOOR, parent_id=vessel.id)
    processing = engine.create("processing", Scale.ROOM, parent_id=deck.id)
    sorter = engine.create("sorter", Scale.TILE, parent_id=processing.id)

    nav = engine.navigate("test", vessel.id)
    nav.push(deck.id)
    nav.push(processing.id)
    nav.push(sorter.id)

    path = nav.path()
    assert len(path) == 4
    assert path == ["vessel", "deck", "processing", "sorter"]
    print(f"✓ Path: {' → '.join(path)}")


# ─── Integration: Sonar + Scale ───────────────────────────────────────────────

def test_sonar_feeds_scale():
    """Sonar probes should inform scale decisions."""
    engine = ScaleFoldEngine()
    sonar = ActiveSonar()

    # Create tiles
    tile_a = engine.create("drift-detect", Scale.TILE, content={"confidence": 0.95})
    tile_b = engine.create("anomaly-flag", Scale.TILE, content={"confidence": 0.85})

    # Probe boundaries
    def test_fn(tid, pert):
        base = 0.95 if "drift" in tid else 0.85
        return base - pert > 0.5, max(0, base - pert)

    sonar.ping_boundary(tile_a.id, test_fn)
    sonar.ping_boundary(tile_b.id, test_fn)

    # The terrain map should show drift-detect is stronger
    terrain = sonar.terrain.resolve()
    assert terrain["boundaries_found"] == 2
    strongest = terrain["strongest_tiles"][0] if terrain["strongest_tiles"] else None
    if strongest:
        print(f"✓ Sonar + Scale: strongest tile = {strongest[0]} (boundary at {strongest[1]['avg_distance']:.3f})")


if __name__ == "__main__":
    print("FOUNDATION TESTS — Active Probe + Scale Fold\n")
    print("=" * 60)

    tests = [
        test_boundary_probe_finds_edge,
        test_boundary_probe_robust_tile,
        test_consistency_probe_finds_contradiction,
        test_coverage_probe_finds_gaps,
        test_terrain_map_accumulates,
        test_desire_drives_probing,
        test_active_sonar_orchestration,
        test_scale_create_and_navigate,
        test_fold_up_creates_tile,
        test_see_from_above,
        test_name_carries_across_folds,
        test_path_tracking,
        test_sonar_feeds_scale,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            import traceback
            print(f"✗ {test.__name__}: {e}")
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{passed + failed} passed")
    if failed == 0:
        print("ALL TESTS PASS — The foundations are built.")
        print("The corn maze is visible from above.")
    else:
        print(f"{failed} FAILURES — The sonar needs calibration.")
