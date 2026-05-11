"""
Learning Cycle — Experience → Pattern → Script → Automation
===============================================================

Demonstrates SnapKit's LearningCycle across the full expertise lifecycle:
DeltaFlood → ScriptBurst → SmoothRunning → Disruption → Rebuilding.

Usage:
    python -m examples.example_learning  (from snapkit-python/)
    or: PYTHONPATH=. python examples/example_learning.py
"""

from snapkit import LearningCycle, SnapFunction, SnapTopologyType
import random


def main():
    print("=" * 65)
    print("Learning Cycle — Expertise Lifecycle Simulation")
    print("=" * 65)

    snap = SnapFunction(tolerance=0.1, topology=SnapTopologyType.HEXAGONAL)
    cycle = LearningCycle(
        snap_function=snap,
        pattern_window=5,
        script_threshold=0.7,
    )

    phases_seen = set()

    # Simulate 200 experiences across 5 phases
    for i in range(200):
        # Phase 1 (epochs 0-39): DeltaFlood — random, no patterns
        if i < 40:
            value = random.uniform(-1.0, 1.0)
            expected = 0.0
            reward = -abs(value)
            phase_name = "\U0001F30A DeltaFlood"
        # Phase 2 (epochs 40-79): ScriptBurst — patterns emerge
        elif i < 80:
            pattern = (i % 5) * 0.3
            value = pattern + random.gauss(0, 0.05)
            expected = pattern
            reward = -abs(value - expected)
            phase_name = "\U0001F4A5 ScriptBurst"
        # Phase 3 (epochs 80-129): SmoothRunning — most value snap
        elif i < 130:
            value = 0.0 + random.gauss(0, 0.02)
            expected = 0.0
            reward = -abs(value)
            phase_name = "\U0001F3C3 SmoothRunning"
        # Phase 4 (epochs 130-169): Disruption — patterns break
        elif i < 170:
            if random.random() < 0.5:
                value = random.uniform(-2.0, 2.0)
            else:
                value = (i % 5) * 0.3 + random.gauss(0, 0.05)
            expected = (i % 5) * 0.3
            reward = -abs(value - expected)
            phase_name = "\U0001F6A8 Disruption"
        # Phase 5 (epochs 170-199): Rebuilding — new patterns
        else:
            new_pattern = (i % 3) * 0.5
            value = new_pattern + random.gauss(0, 0.05)
            expected = new_pattern
            reward = -abs(value - expected)
            phase_name = "\U0001F528 Rebuilding"

        cycle.experience(value=value, expected=expected, reward=reward)

        if cycle.state.phase.value not in phases_seen:
            phases_seen.add(cycle.state.phase.value)
            print(f"  Epoch {i:>3}: Entered {phase_name}")

        # Snapshot every 50 epochs
        if i % 50 == 49 or i == 199:
            state = cycle.state
            print(f"\n--- Epoch {i+1} Snapshot ---")
            print(f"  Phase: {phase_name}")
            print(f"  Cognitive load: {state.cognitive_load:.2f}")
            print(f"  Scripts: {len(cycle.library.scripts)} total")
            print(f"  Active patterns: {len(cycle.pattern_buffer)} in buffer")
            print(f"  Delta count: {state.total_deltas}")
            print(f"  Snap rate: {cycle.snap_rate():.1%}")
            print()

    print("=" * 65)
    print("Learning cycle complete.")
    print(f"Phases experienced: {', '.join(sorted(phases_seen))}")
    print("=" * 65)


if __name__ == "__main__":
    main()
