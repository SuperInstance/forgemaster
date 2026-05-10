"""
test_sheaf.py — Test the sheaf H¹ computer with 2 models

Shows:
  1. Compatible models: H¹ = 0 (they glue into global understanding)
  2. Incompatible models: H¹ > 0 (obstruction exists)
  3. Partially compatible: H¹ > 0 but smaller
"""

import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from understanding_sheaf import (
    ModelRepresentation,
    AlexandrovTopology,
    UnderstandingSheaf,
    create_model_pair,
)
from cohomology import (
    compute_cohomology,
    two_model_cohomology,
    direct_cohomology_from_sheaf,
)


def test_compatible_models():
    """Two models with similar representations → H¹ should be 0."""
    print("\n" + "=" * 70)
    print("TEST 1: Compatible models → H¹ = 0")
    print("=" * 70)

    np.random.seed(42)
    n_data = 100
    embed_dim = 8

    # Both models see same data with similar representations
    base = np.random.randn(n_data, embed_dim)
    rep_a = base + 0.05 * np.random.randn(n_data, embed_dim)
    rep_b = base + 0.05 * np.random.randn(n_data, embed_dim)

    # Full coverage
    coverage_a = np.ones(n_data, dtype=bool)
    coverage_b = np.ones(n_data, dtype=bool)

    result = two_model_cohomology(rep_a, rep_b, coverage_a, coverage_b, tolerance=0.5)

    print(f"\n  H⁰ dimension: {result.h0_dimension}")
    print(f"  H¹ dimension: {result.h1_dimension}")
    print(f"  Interpretation:\n    {result.interpretation.replace(chr(10), chr(10) + '    ')}")

    assert result.h1_dimension == 0, f"Expected H¹=0 for compatible models, got {result.h1_dimension}"
    print("\n  ✓ PASS: Compatible models have H¹ = 0 (no obstruction)")
    return result


def test_incompatible_models():
    """Two models with different representations → H¹ should be > 0."""
    print("\n" + "=" * 70)
    print("TEST 2: Incompatible models → H¹ > 0")
    print("=" * 70)

    np.random.seed(42)
    n_data = 100
    embed_dim = 8

    # Completely different representations
    rep_a = np.random.randn(n_data, embed_dim)
    rep_b = np.random.randn(n_data, embed_dim)  # independent random

    # Full coverage
    coverage_a = np.ones(n_data, dtype=bool)
    coverage_b = np.ones(n_data, dtype=bool)

    result = two_model_cohomology(rep_a, rep_b, coverage_a, coverage_b, tolerance=0.5)

    print(f"\n  H⁰ dimension: {result.h0_dimension}")
    print(f"  H¹ dimension: {result.h1_dimension}")
    print(f"  Interpretation:\n    {result.interpretation.replace(chr(10), chr(10) + '    ')}")

    assert result.h1_dimension > 0, f"Expected H¹>0 for incompatible models, got {result.h1_dimension}"
    print("\n  ✓ PASS: Incompatible models have H¹ > 0 (obstruction detected)")
    return result


def test_sheaf_construction():
    """Full sheaf construction with Alexandrov topology."""
    print("\n" + "=" * 70)
    print("TEST 3: Full sheaf construction → topology + cohomology")
    print("=" * 70)

    # Create compatible pair
    model_a, model_b = create_model_pair(
        "model_a", "model_b",
        n_data=50, embed_dim_a=8, embed_dim_b=8,
        compatible=True, noise_level=0.1, seed=42,
    )

    print(f"\n  Model A: {model_a.name}, coverage={model_a.coverage.sum()}/{model_a.n_data}")
    print(f"  Model B: {model_b.name}, coverage={model_b.coverage.sum()}/{model_b.n_data}")
    print(f"  Shared coverage: {(model_a.coverage & model_b.coverage).sum()}")

    # Build topology
    topo = AlexandrovTopology(tolerance=0.5)
    compat = topo.compute_compatibility([model_a, model_b])
    print(f"\n  Compatibility matrix:\n{compat}")

    opens = topo.get_open_sets(2)
    print(f"  Open sets ({len(opens)}): {[set(s) for s in opens]}")

    # Build sheaf
    sheaf = UnderstandingSheaf([model_a, model_b], topo)
    sheaf.build()

    print(f"  Sections computed for {len(sheaf.sections)} open sets")
    for k, v in sheaf.sections.items():
        print(f"    F({set(k)}): norm = {np.linalg.norm(v):.4f}")

    # Compute cohomology
    result = direct_cohomology_from_sheaf(sheaf)
    print(f"\n  H⁰ = {result.h0_dimension}")
    print(f"  H¹ = {result.h1_dimension}")
    print(f"  {result.interpretation}")

    return result


def test_incompatible_sheaf():
    """Full sheaf with incompatible models."""
    print("\n" + "=" * 70)
    print("TEST 4: Full sheaf — incompatible models")
    print("=" * 70)

    model_a, model_b = create_model_pair(
        "model_a", "model_b",
        n_data=50, embed_dim_a=8, embed_dim_b=8,
        compatible=False, noise_level=0.1, seed=42,
    )

    print(f"\n  Model A: coverage={model_a.coverage.sum()}/{model_a.n_data}")
    print(f"  Model B: coverage={model_b.coverage.sum()}/{model_b.n_data}")
    print(f"  Shared: {(model_a.coverage & model_b.coverage).sum()}")

    topo = AlexandrovTopology(tolerance=0.5)
    topo.compute_compatibility([model_a, model_b])
    print(f"  Compatibility:\n{topo.compatibility_matrix}")

    sheaf = UnderstandingSheaf([model_a, model_b], topo)
    sheaf.build()

    result = direct_cohomology_from_sheaf(sheaf)
    print(f"\n  H⁰ = {result.h0_dimension}")
    print(f"  H¹ = {result.h1_dimension}")
    print(f"  {result.interpretation}")

    print("\n  ✓ PASS: Incompatible models show higher obstruction")
    return result


if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  SHEAF H¹ COMPUTER: Understanding Cohomology Tests      ║")
    print("║  H⁰ = global sections, H¹ = obstruction to gluing      ║")
    print("╚══════════════════════════════════════════════════════════╝")

    results = {}
    tests = [
        ("compatible", test_compatible_models),
        ("incompatible", test_incompatible_models),
        ("sheaf_compatible", test_sheaf_construction),
        ("sheaf_incompatible", test_incompatible_sheaf),
    ]

    for name, fn in tests:
        try:
            results[name] = fn()
        except Exception as e:
            print(f"\n  ✗ {name} FAILED: {e}")
            import traceback; traceback.print_exc()
            results[name] = None

    print("\n\n" + "╔" + "═" * 58 + "╗")
    print("║  SUMMARY                                                   ║")
    print("╠" + "═" * 58 + "╣")
    for name, res in results.items():
        status = f"✓ H⁰={res.h0_dimension}, H¹={res.h1_dimension}" if res else "✗ FAIL"
        print(f"  {name}: {status}")
    print("╚" + "═" * 58 + "╝")
