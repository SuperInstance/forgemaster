"""
Poker Attention Engine — Multi-Stream Delta Detection
=======================================================

Demonstrates SnapKit's core pipeline: snap → detect → allocate.

Models a poker player's attention across multiple opponents.
Each opponent is a data stream. The snap function determines
what's "routine" behavior. Deltas exceeding tolerance trigger
attention allocation.

Usage:
    python -m examples.example_poker  (from snapkit-python/)
    or: PYTHONPATH=. python examples/example_poker.py
"""

from snapkit import SnapFunction, SnapTopologyType, DeltaDetector, AttentionBudget
import random


def main():
    print("=" * 60)
    print("Poker Attention Engine")
    print("=" * 60)

    # 1. Create a snap with very tight tolerance (poker tells are subtle)
    snap = SnapFunction(tolerance=0.05, topology=SnapTopologyType.BINARY)

    # 2. Multi-stream delta detector — one stream per opponent
    detector = DeltaDetector()

    opponents = [
        ("Alice", 0.8, 0.6),   # name, actionability, urgency
        ("Bob", 0.5, 0.9),
        ("Charlie", 0.3, 0.2),
        ("Diana", 0.9, 0.7),
    ]

    for name, actionability, urgency in opponents:
        detector.add_stream(
            snap,
            stream_id=name,
            actionability_fn=lambda d, a=actionability: a,
            urgency_fn=lambda d, u=urgency: u,
        )

    # 3. Finite attention budget
    budget = AttentionBudget(total_budget=100.0, strategy='actionability')

    # 4. Simulate 10 rounds of observation
    print(f"\n{'Round':>5}  {'Stream':<12}  {'Value':>6}  {'Delta':>8}  {'Attention':>10}  {'Status'}")
    print("-" * 65)

    for round_num in range(10):
        observations = {}
        for name, _, _ in opponents:
            # Simulate behavior: most values within tolerance, occasional tells
            if random.random() < 0.3:  # 30% tell rate
                observations[name] = random.uniform(0.2, 0.5)
            else:
                observations[name] = random.uniform(-0.02, 0.02)

        # Detect deltas
        deltas = detector.observe(observations)

        # Allocate attention
        prioritized = detector.prioritize(max_results=4)
        allocations = budget.allocate(prioritized)

        # Report
        for alloc in allocations:
            status = "⚠ DELTA" if not alloc.delta.exceeds_tolerance else "ATTEND"
            print(f"{round_num:>5}  {alloc.delta.stream_id:<12}  {alloc.delta.value:>6.2f}  "
                  f"{alloc.delta.magnitude:>8.4f}  {alloc.allocated:>8.2f}  {status}")

        if not allocations:
            print(f"{round_num:>5}  {'(all snapped)':<12}  {'—':>6}  {'—':>8}  {'—':>10}  \u2713 ROUTINE")

        # Slight budget recovery between rounds
        budget.total_budget = min(100.0, budget.total_budget + 5.0)

    # Summary
    info = budget.attention_insight()
    print(f"\n--- Attention Insight ---")
    for insight in info.get('insights', []):
        print(f"[{insight['severity'].upper()}] {insight['message']}")

    print(f"\nUtilization: {budget.utilization:.1%}")
    print(f"Strategy: {budget.strategy}")
    print("Done.")


if __name__ == "__main__":
    main()
