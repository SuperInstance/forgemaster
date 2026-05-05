#!/usr/bin/env python3
"""Sorting algorithm benchmark — Forgemaster Shell playtest.

Implements bubble, insertion, merge, quick, and timsort (built-in sorted()).
Benchmarks each on arrays of size 100, 1000, 10000, 100000.
10 runs per combination, reports mean ± stddev.
Outputs a formatted markdown table to stdout.
"""

import time
import random
import statistics
import sys

# ---------------------------------------------------------------------------
# Sorting algorithms
# ---------------------------------------------------------------------------

def bubble_sort(arr):
    a = arr[:]
    n = len(a)
    for i in range(n):
        for j in range(0, n - i - 1):
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]
    return a

def insertion_sort(arr):
    a = arr[:]
    for i in range(1, len(a)):
        key = a[i]
        j = i - 1
        while j >= 0 and a[j] > key:
            a[j + 1] = a[j]
            j -= 1
        a[j + 1] = key
    return a

def merge_sort(arr):
    a = arr[:]
    if len(a) <= 1:
        return a
    mid = len(a) // 2
    left = merge_sort(a[:mid])
    right = merge_sort(a[mid:])
    # merge
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result

def quick_sort(arr):
    a = arr[:]
    def _qs(lo, hi):
        if lo >= hi:
            return
        pivot = a[hi]
        idx = lo
        for i in range(lo, hi):
            if a[i] <= pivot:
                a[i], a[idx] = a[idx], a[i]
                idx += 1
        a[idx], a[hi] = a[hi], a[idx]
        _qs(lo, idx - 1)
        _qs(idx + 1, hi)
    _qs(0, len(a) - 1)
    return a

def timsort(arr):
    return sorted(arr)

# ---------------------------------------------------------------------------
# Benchmark harness
# ---------------------------------------------------------------------------

ALGORITHMS = [
    ("Bubble Sort",    bubble_sort),
    ("Insertion Sort", insertion_sort),
    ("Merge Sort",     merge_sort),
    ("Quick Sort",     quick_sort),
    ("Timsort",        timsort),
]

SIZES = [100, 1_000, 10_000, 100_000]
RUNS  = 10

def benchmark(func, data):
    """Return list of elapsed seconds (RUNS trials)."""
    times = []
    for _ in range(RUNS):
        start = time.perf_counter()
        func(data)
        elapsed = time.perf_counter() - start
        times.append(elapsed)
    return times

def main():
    random.seed(42)
    # Pre-generate one master array per size (copy inside each sort)
    master = {s: [random.randint(0, s * 10) for _ in range(s)] for s in SIZES}

    # Collect results: { (name, size): (mean, stddev) }
    results = {}

    for size in SIZES:
        data = master[size]
        for name, func in ALGORITHMS:
            # Skip O(n²) sorts on large arrays (they'd take forever)
            if name in ("Bubble Sort", "Insertion Sort") and size >= 100_000:
                results[(name, size)] = ("—", "—")
                continue
            times = benchmark(func, data)
            mean = statistics.mean(times)
            std  = statistics.stdev(times) if len(times) > 1 else 0.0
            results[(name, size)] = (mean, std)

    # ---- Markdown table ----
    col_sizes = SIZES
    header = "| Algorithm         | " + " | ".join(f"n={s:>7}" for s in col_sizes) + " |"
    sep    = "|-------------------|" + "|".join(["----------------" for _ in col_sizes]) + "|"

    lines = [
        "# Sorting Algorithm Benchmarks",
        "",
        f"**Runs per cell:** {RUNS}  ",
        f"**Random seed:** 42  ",
        f"**Values:** mean ± stddev (seconds)  ",
        "",
        header,
        sep,
    ]

    for name, _ in ALGORITHMS:
        cells = []
        for size in col_sizes:
            mean, std = results[(name, size)]
            if isinstance(mean, str):
                cells.append("— (skipped)")
            else:
                cells.append(f"{mean:.6f} ± {std:.6f}")
        lines.append(f"| {name:<18}| " + " | ".join(f"{c:>14}" for c in cells) + " |")

    lines.append("")
    print("\n".join(lines))

if __name__ == "__main__":
    main()
