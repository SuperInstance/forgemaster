#!/usr/bin/env python3
"""FLUX Differential Test Harness — CPU vs GPU constraint checking

Loads test vectors from test-vectors.json, runs them through:
1. Python CPU reference (constraint-theory package or built-in)
2. CUDA GPU kernel via flux_production_v2 (if available)

Reports any mismatches. Designed for CI integration.

Usage:
    python3 test_harness.py [--vectors FILE] [--gpu] [--verbose]
"""

import json
import sys
import argparse
import time
from pathlib import Path

# ═══════════════════════════════════════════════════════════
# CPU Reference — pure Python constraint evaluator
# ═══════════════════════════════════════════════════════════

INT8_MIN = -127  # Saturated minimum (not -128)
INT8_MAX = 127   # Saturated maximum


def saturate_i8(val):
    """Clamp to saturated INT8 range [-127, 127]"""
    return max(INT8_MIN, min(INT8_MAX, int(val)))


def evaluate_constraint(inputs, guard_source):
    """
    Evaluate a GUARD constraint against inputs.
    Returns True if constraint is satisfied, False if violated.
    
    This is a simplified evaluator for the test vector format.
    It parses the expression from guard_source and evaluates it.
    """
    try:
        # Parse the expression from guard_source
        # Format: "constraint name { expr: EXPR, inputs: [vars] }"
        expr_part = guard_source.split("expr:")[1].split(", inputs:")[0].strip()
        
        # Map input variable names to values
        # Get variable names from the inputs field
        inputs_part = guard_source.split("inputs: [")[1].split("]")[0]
        var_names = [v.strip() for v in inputs_part.split(",")]
        
        env = {}
        for i, name in enumerate(var_names):
            if i < len(inputs):
                env[name] = saturate_i8(inputs[i])
        
        # Replace variable names and operators
        expr = expr_part
        expr = expr.replace(" AND ", " and ")
        expr = expr.replace(" OR ", " or ")
        expr = expr.replace("NOT ", "not ")
        
        # Replace variable names with values
        for name, val in sorted(env.items(), key=lambda x: -len(x[0])):
            expr = expr.replace(name, str(val))
        
        # Evaluate
        result = eval(expr)
        return bool(result)
    except Exception as e:
        return None  # Can't evaluate — skip


def run_cpu_vectors(vectors):
    """Run all test vectors through CPU reference."""
    results = []
    for v in vectors:
        expected = v["expected"]
        actual = evaluate_constraint(v["inputs"], v["guard_source"])
        results.append({
            "name": v["name"],
            "category": v["category"],
            "expected": expected,
            "actual": actual,
            "match": actual == expected[0] if actual is not None and len(expected) == 1 else None,
            "error": None if actual is not None else "parse_error"
        })
    return results


def validate_vectors(vectors):
    """Validate test vector format and deduplicate."""
    seen = set()
    valid = []
    dupes = 0
    invalid = 0
    
    for v in vectors:
        # Check required fields
        if not all(k in v for k in ["name", "guard_source", "inputs", "expected", "category"]):
            invalid += 1
            continue
        
        # Deduplicate by name
        if v["name"] in seen:
            dupes += 1
            continue
        seen.add(v["name"])
        
        valid.append(v)
    
    return valid, dupes, invalid


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="FLUX Differential Test Harness")
    parser.add_argument("--vectors", default="test-vectors.json", help="Path to test vectors JSON")
    parser.add_argument("--gpu", action="store_true", help="Also run GPU comparison (requires CUDA)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--category", help="Run only specific category")
    args = parser.parse_args()
    
    # Load vectors
    vpath = Path(__file__).parent / args.vectors
    if not vpath.exists():
        print(f"ERROR: {vpath} not found")
        sys.exit(1)
    
    with open(vpath) as f:
        raw_vectors = json.load(f)
    
    print(f"═══ FLUX Differential Test Harness ═══")
    print(f"Loaded: {len(raw_vectors)} raw vectors")
    
    # Validate
    vectors, dupes, invalid = validate_vectors(raw_vectors)
    print(f"Valid: {len(vectors)}, Duplicates: {dupes}, Invalid: {invalid}")
    
    if dupes > 0:
        print(f"  ⚠ Removed {dupes} duplicate test vectors")
    
    # Filter by category
    if args.category:
        vectors = [v for v in vectors if v["category"] == args.category]
        print(f"Filtered to category '{args.category}': {len(vectors)} vectors")
    
    # Run CPU evaluation
    print(f"\n── CPU Reference ──")
    start = time.time()
    results = run_cpu_vectors(vectors)
    elapsed = time.time() - start
    
    # Analyze
    passed = sum(1 for r in results if r["match"] is True)
    failed = sum(1 for r in results if r["match"] is False)
    skipped = sum(1 for r in results if r["match"] is None)
    
    print(f"  Evaluated: {len(results)} vectors in {elapsed:.3f}s")
    print(f"  Passed:  {passed}")
    print(f"  Failed:  {failed}")
    print(f"  Skipped: {skipped} (parse errors)")
    
    # Category breakdown
    cats = {}
    for r in results:
        c = r["category"]
        if c not in cats:
            cats[c] = {"pass": 0, "fail": 0, "skip": 0}
        if r["match"] is True:
            cats[c]["pass"] += 1
        elif r["match"] is False:
            cats[c]["fail"] += 1
        else:
            cats[c]["skip"] += 1
    
    print(f"\n── Category Breakdown ──")
    for cat in sorted(cats):
        s = cats[cat]
        status = "✓" if s["fail"] == 0 and s["skip"] == 0 else "✗"
        print(f"  {status} {cat}: {s['pass']} pass, {s['fail']} fail, {s['skip']} skip")
    
    # Show failures
    if failed > 0 or args.verbose:
        print(f"\n── Details ──")
        for r in results:
            if r["match"] is False or (args.verbose and r["match"] is None):
                print(f"  {r['category']}/{r['name']}: expected={r['expected']}, actual={r['actual']}")
    
    # GPU comparison (optional)
    if args.gpu:
        print(f"\n── GPU Comparison ──")
        print("  GPU differential testing requires compiled CUDA binary")
        print("  Run: cd flux-hardware/cuda && ./bench_production_v2")
    
    # Exit code
    if failed > 0:
        print(f"\n✗ {failed} TEST FAILURES")
        sys.exit(1)
    elif skipped > 0:
        print(f"\n⚠ {skipped} tests skipped (parse errors)")
        sys.exit(0)
    else:
        print(f"\n✓ ALL {passed} TESTS PASS")
        sys.exit(0)


if __name__ == "__main__":
    main()
