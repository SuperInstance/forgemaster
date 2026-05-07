"""Benchmark hex graph operations: timing vs vertex count."""

import time
import sys

from hex_graph import HexGraph


def benchmark():
    print("=" * 70)
    print("BENCHMARK: Hex Graph Operations vs Size")
    print("=" * 70)
    print()
    print(f"{'Radius':>7} {'V':>7} {'E':>7} {'F':>7} "
          f"{'Build(ms)':>10} {'Holonomy(ms)':>13} {'V/time':>10}")
    print("-" * 70)

    results = []

    for r in range(1, 31):
        t0 = time.perf_counter()
        g = HexGraph(r)
        t1 = time.perf_counter()
        build_ms = (t1 - t0) * 1000

        valid = g.generate_valid_assignment()

        t2 = time.perf_counter()
        g.check_holonomy(valid)
        t3 = time.perf_counter()
        holo_ms = (t3 - t2) * 1000

        v = g.vertex_count()
        e = g.edge_count()
        f = g.face_count()
        v_per_ms = v / holo_ms if holo_ms > 0 else float('inf')

        results.append((r, v, e, f, build_ms, holo_ms, v_per_ms))
        print(f"{r:>7} {v:>7} {e:>7} {f:>7} "
              f"{build_ms:>10.3f} {holo_ms:>13.4f} {v_per_ms:>10.1f}")

    # Check linearity
    print()
    print("Linearity check (holonomy time / V should be roughly constant):")
    small = results[4]  # R=5
    large = results[24]  # R=25
    ratio_small = small[5] / small[1] if small[1] > 0 else 0
    ratio_large = large[5] / large[1] if large[1] > 0 else 0
    print(f"  R=5:  time/V = {ratio_small:.6f} ms/vertex")
    print(f"  R=25: time/V = {ratio_large:.6f} ms/vertex")
    print(f"  Ratio: {ratio_large / ratio_small:.2f}x (should be ~1.0 for O(V))")
    print()

    # Try to plot if matplotlib available
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        vs = [r[1] for r in results]
        times = [r[5] for r in results]

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(vs, times, 'b-o', markersize=3, label='Holonomy check time')
        # Linear fit
        if len(vs) > 1:
            import numpy as np
            coeffs = np.polyfit(vs, times, 1)
            fit_line = np.poly1d(coeffs)
            ax.plot(vs, fit_line(vs), 'r--', label=f'Linear fit: {coeffs[0]:.6f}V + {coeffs[1]:.4f}')
        ax.set_xlabel('Vertex Count (V)')
        ax.set_ylabel('Holonomy Check Time (ms)')
        ax.set_title('Hex ZHC: O(V) Holonomy Check Scaling')
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig('/home/phoenix/.openclaw/workspace/research/hex-zhc/benchmark.png', dpi=150)
        print("Plot saved to benchmark.png")
    except ImportError:
        print("(matplotlib not available, skipping plot)")


if __name__ == "__main__":
    benchmark()
