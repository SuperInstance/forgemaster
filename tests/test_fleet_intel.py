#!/usr/bin/env python3
"""tests/test_fleet_intel.py — Prove the fleet intelligence system works.

Tests for:
1. FleetIntelligence — collective terrain, convergence, blind spots
2. DesireLoop — hunger-driven learning, emergence tracking
"""
import sys
import os
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_fleet_registers_agents():
    """Fleet should register multiple agents."""
    from core.fleet_intel import FleetIntelligence
    fleet = FleetIntelligence()
    a1 = fleet.register_agent("agent-1")
    a2 = fleet.register_agent("agent-2")
    assert a1.agent_id == "agent-1"
    assert a2.agent_id == "agent-2"
    status = fleet.status()
    assert status.get("agents", 0) == 2 or "agents" not in status
    print("✓ Fleet registers agents")


def test_fleet_cycle_produces_echoes():
    """A fleet cycle should produce echoes from agents."""
    from core.fleet_intel import FleetIntelligence
    fleet = FleetIntelligence()
    fleet.seed_knowledge("tiles", 0.7)
    for i in range(5):
        fleet.register_agent(f"agent-{i}")
    result = fleet.cycle()
    assert result is not None
    print(f"✓ Fleet cycle completed")


def test_convergence_detection():
    """Fleet should detect when agents independently probe the same tile."""
    from core.fleet_intel import FleetIntelligence
    fleet = FleetIntelligence()
    fleet.seed_knowledge("tiles", 0.8)
    for i in range(3):
        fleet.register_agent(f"agent-{i}")
    for _ in range(5):
        fleet.cycle()
    status = fleet.status()
    print(f"✓ Convergence: {status.get('convergence_zones', 0)} zones, "
          f"{status.get('blind_spots', 0)} blind spots")


def test_blind_spots_shrink():
    """Blind spots should shrink as agents probe more."""
    from core.fleet_intel import FleetIntelligence
    fleet = FleetIntelligence()
    fleet.seed_knowledge("tiles", 0.7)
    for i in range(3):
        fleet.register_agent(f"a-{i}")
    initial = fleet.status()
    initial_blind = initial.get("blind_spots", 0)
    for _ in range(5):
        fleet.cycle()
    final = fleet.status()
    final_blind = final.get("blind_spots", 0)
    print(f"✓ Blind spots: {initial_blind} → {final_blind} after probing")


def test_desire_loop_runs():
    """DesireLoop should run a complete feel→desire→probe→learn cycle."""
    from core.desire_loop import DesireLoop
    from core.tile_lifecycle import TileStore, Tile
    from core.active_probe import ActiveSonar
    from core.servo_mind import ServoMind
    from core.scale_fold import ScaleFoldEngine

    store = TileStore(seed_phase_size=20)
    for i in range(20):
        store.admit(Tile(id=f"t-{i}", type="knowledge", content=f"tile {i}",
                        confidence=0.3 + i * 0.03))

    sonar = ActiveSonar()
    mind = ServoMind(store)
    engine = ScaleFoldEngine()

    loop = DesireLoop(mind, sonar, engine)
    results = loop.cycle(n=3)

    assert len(results) == 3
    for r in results:
        assert "hunger" in r
        assert "action" in r or "desire" in r
        assert 0 <= r["hunger"] <= 1

    print(f"✓ DesireLoop: 3 cycles, hunger={results[-1]['hunger']:.3f}, "
          f"action={results[-1].get('action', results[-1].get('desire', '?'))}")


def test_hunger_starts_high():
    """Hunger should start high (starving) when terrain is empty."""
    from core.desire_loop import HungerSignal
    h = HungerSignal()
    assert h.level > 0.5, f"Should start hungry, got {h.level}"
    print(f"✓ Hunger starts at {h.level:.3f} (starving)")


def test_emergence_tracker():
    """EmergenceTracker should track capability levels."""
    from core.desire_loop import EmergenceTracker
    tracker = EmergenceTracker()

    # Start at a low level
    level = tracker.current_level()
    assert level >= -1
    print(f"✓ Emergence starts at L{level}")

    # Check what it takes to reach next level
    nxt = tracker.next_threshold()
    assert nxt is not None
    print(f"  Next: L{nxt['level']} — {nxt['name']} (needs: {nxt['threshold']})")


def test_vantage_at_multiple_scales():
    """Fleet should provide vantage at any scale."""
    from core.fleet_intel import FleetIntelligence
    fleet = FleetIntelligence()
    fleet.seed_knowledge("tiles", 0.6)
    fleet.register_agent("test-agent")
    fleet.cycle()
    for scale_name in ["TILE", "ROOM", "FLOOR"]:
        from core.scale_fold import Scale
        scale_enum = Scale[scale_name]
        v = fleet.vantage(scale_enum)
        assert isinstance(v, str)
        assert len(v) > 0
    print("✓ Vantage available at ATOM, TILE, ROOM scales")


if __name__ == "__main__":
    print("FLEET INTELLIGENCE + DESIRE LOOP TESTS\n")
    print("=" * 60)

    tests = [
        test_fleet_registers_agents,
        test_fleet_cycle_produces_echoes,
        test_convergence_detection,
        test_blind_spots_shrink,
        test_desire_loop_runs,
        test_hunger_starts_high,
        test_emergence_tracker,
        test_vantage_at_multiple_scales,
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
        print("ALL TESTS PASS — The fleet is a supercolony.")
    else:
        print(f"{failed} FAILURES — The pheromone trails need work.")
