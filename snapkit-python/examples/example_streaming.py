"""
Real-Time Stream Monitoring — Ring-Buffer Stream Processing
=============================================================

Demonstrates SnapKit's StreamProcessor for detecting anomalies
in a continuous data stream (e.g., sensor readings, market data).

Usage:
    python -m examples.example_streaming  (from snapkit-python/)
    or: PYTHONPATH=. python examples/example_streaming.py
"""

from snapkit import SnapFunction, SnapTopologyType
from snapkit.streaming import StreamProcessor
import random
import math


def main():
    print("=" * 65)
    print("Real-Time Stream Monitoring")
    print("=" * 65)

    # Simulated sensor data: sine wave + noise + occasional spikes
    def sensor_generator():
        t = 0.0
        while True:
            base = math.sin(t * 0.1) * 1.0
            noise = random.gauss(0, 0.05)
            spike = random.choice([0, 0, 0, 0, random.uniform(-3, 3)])
            yield base + noise + spike
            t += 1.0

    # Stream processor with ring buffer
    processor = StreamProcessor(
        snap_function=SnapFunction(tolerance=0.15, topology=SnapTopologyType.HEXAGONAL),
        window_size=20,
        min_samples=5,
    )

    sensor = sensor_generator()
    anomalies = 0
    total_processed = 0

    print(f"\n{'Tick':>5}  {'Value':>8}  {'Status':<15}  {'Delta':>8}  {'Anomaly':>8}")
    print("-" * 55)

    for tick in range(100):
        value = next(sensor)
        result = processor.process(value)

        total_processed += 1

        if result.is_anomaly:
            anomalies += 1
            status = "\u26A0 ANOMALY"
        elif result.is_delta:
            status = "DELTA"
        else:
            status = "\u2713 snapped"

        if tick < 10 or result.is_anomaly:
            print(f"{tick:>5}  {value:>8.3f}  {status:<15}  {result.delta:>8.4f}  "
                  f"{anomalies:>8}")

    # Summary
    print(f"\n--- Summary ---")
    print(f"Total processed: {total_processed}")
    print(f"Anomalies detected: {anomalies} ({anomalies/total_processed:.1%})")
    print(f"Window size: {processor.window_size}")
    print(f"Current snap rate: {processor.snap_rate():.1%}")
    print("Done.")


if __name__ == "__main__":
    main()
