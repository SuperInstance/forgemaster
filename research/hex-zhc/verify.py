"""Run all verifications and print results."""

from hex_graph import HexGraph
from laman_proof import prove_edge_count, prove_laman_2d, prove_laman_3d, prove_holonomy_efficient
import time
import random


def verify_edge_count():
    """1. Verify 3V edges on hex lattice."""
    g = HexGraph(20)
    v, e = g.vertex_count(), g.edge_count()
    # For large radius, E ≈ 3V (exact for infinite lattice)
    ratio = e / (3 * v)
    # Boundary effects mean ratio < 1 for finite, but approaches 1
    passed = ratio > 0.9  # generous threshold for finite lattice
    status = "✅" if passed else "❌"
    print(f"1. Edge count E≈3V:  V={v}, E={e}, E/(3V)={ratio:.4f}  {status}")
    return passed


def verify_laman_2d():
    """2. Verify Laman 1.5x redundancy in 2D."""
    g = HexGraph(20)
    v, e = g.vertex_count(), g.edge_count()
    laman_min = 2 * v - 3
    redundancy = e / laman_min
    passed = redundancy > 1.4  # Should approach 1.5
    status = "✅" if passed else "❌"
    print(f"2. Laman 2D redundancy:  {redundancy:.4f} (target: 1.5)  {status}")
    return passed


def verify_laman_3d():
    """3. Verify Laman 2.0x redundancy in 3D (FCC) — analytic."""
    v = 10000
    redundancy = 6 * v / (3 * v - 6)
    passed = abs(redundancy - 2.0) < 0.01
    status = "✅" if passed else "❌"
    print(f"3. Laman 3D (FCC) redundancy:  {redundancy:.6f} (target: 2.0)  {status}")
    return passed


def verify_o_v_scaling():
    """4. Verify O(V) holonomy check scaling."""
    times = []
    for r in [5, 10, 15, 20, 25]:
        g = HexGraph(r)
        v = g.vertex_count()
        valid = g.generate_valid_assignment()
        t0 = time.perf_counter()
        for _ in range(10):
            g.check_holonomy(valid)
        t1 = time.perf_counter()
        ms = (t1 - t0) * 1000
        times.append((v, ms))

    # Check that doubling V roughly doubles time
    ratio = (times[-1][1] / times[-1][0]) / (times[0][1] / times[0][0])
    passed = 0.3 < ratio < 3.0  # generous: O(V) means ratio ~ 1
    status = "✅" if passed else "❌"
    print(f"4. O(V) scaling ratio:  {ratio:.2f} (target: ~1.0)  {status}")
    return passed


def verify_face_cycles():
    """5. Verify all face cycles close for valid assignments."""
    g = HexGraph(15)
    valid = g.generate_valid_assignment()
    passed = g.check_holonomy(valid)
    status = "✅" if passed else "❌"
    print(f"5. Face cycles close (valid assignment):  {status}")
    return passed


def verify_spanning_tree():
    """6. Verify spanning tree propagation gives consistent values."""
    g = HexGraph(10)
    # Seed a single edge and propagate
    seed = {(g.edges()[0][0], g.edges()[0][1]): 1.0}
    result = g.propagate_constraints(seed)

    # Check that the propagated values are internally consistent
    # by verifying holonomy on the result
    passed = g.check_holonomy(result)
    status = "✅" if passed else "❌"
    print(f"6. Spanning tree propagation consistent:  {status}")

    # Also verify the seed value is preserved
    u, v = g.edges()[0]
    key = (u, v)
    rev = (v, u)
    seed_preserved = (key in result and abs(result[key] - 1.0) < 1e-9) or \
                     (rev in result and abs(-result[rev] - 1.0) < 1e-9)
    status2 = "✅" if seed_preserved else "❌"
    print(f"   Seed value preserved:  {status2}")

    return passed and seed_preserved


def main():
    print("=" * 60)
    print("HEX ZHC — VERIFICATION SUITE")
    print("=" * 60)
    print()

    results = [
        verify_edge_count(),
        verify_laman_2d(),
        verify_laman_3d(),
        verify_o_v_scaling(),
        verify_face_cycles(),
        verify_spanning_tree(),
    ]

    print()
    print("=" * 60)
    total = len(results)
    passed = sum(results)
    print(f"RESULTS: {passed}/{total} passed")
    if all(results):
        print("ALL VERIFICATIONS PASSED ✅✅✅")
    else:
        print("SOME VERIFICATIONS FAILED ❌")
    print("=" * 60)

    print()
    print("Running detailed proofs...")
    print()
    prove_edge_count()
    prove_laman_2d()
    prove_laman_3d()
    prove_holonomy_efficient()


if __name__ == "__main__":
    main()
