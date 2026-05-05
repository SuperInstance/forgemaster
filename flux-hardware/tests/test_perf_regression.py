#!/usr/bin/env python3
"""
Performance Regression Test Framework for GUARD Compiler

Loads .guard files, compiles them, benchmarks 10M iterations,
compares against baseline.json, and fails if regression >5%.

Usage:
    pytest test_perf_regression.py -v --benchmark-only
    pytest test_perf_regression.py -v --benchmark-only --update-baseline
    pytest test_perf_regression.py -v --benchmark-only --guard-dir /path/to/guards

Generates: perf_regression_report.md
"""

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GUARDC_BIN = os.environ.get("GUARDC_BIN", "guardc")
GUARD_DIR = os.environ.get(
    "GUARD_DIR", str(Path(__file__).parent.parent / "guards")
)
BASELINE_FILE = Path(__file__).parent / "baseline.json"
REPORT_FILE = Path(__file__).parent / "perf_regression_report.md"
ITERATIONS = int(os.environ.get("PERF_ITERATIONS", "10_000_000"))
REGRESSION_THRESHOLD = float(os.environ.get("PERF_REGRESSION_THRESHOLD", "0.05"))
WARMUP_ITERATIONS = int(os.environ.get("PERF_WARMUP", "100_000"))
TIMEOUT_PER_TEST = int(os.environ.get("PERF_TIMEOUT", "300"))  # seconds


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class BenchmarkResult:
    """Result from benchmarking a single .guard file."""

    guard_file: str
    iterations: int
    total_ns: int
    mean_ns: float
    median_ns: float
    min_ns: int
    max_ns: int
    p50_ns: float
    p95_ns: float
    p99_ns: float
    compile_time_ms: int
    binary_size_bytes: int
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class ComparisonResult:
    """Comparison between current result and baseline."""

    guard_file: str
    baseline_mean_ns: float
    current_mean_ns: float
    delta_percent: float
    verdict: str  # "PASS", "FAIL", "NEW", "SKIP"
    details: str = ""


# ---------------------------------------------------------------------------
# GUARD Compiler Interface
# ---------------------------------------------------------------------------


def compile_guard(guard_file: Path, output_dir: Path) -> Tuple[Path, int]:
    """
    Compile a .guard file to a native binary using guardc.
    Returns (binary_path, compile_time_ms).
    """
    output_bin = output_dir / f"{guard_file.stem}_bench"
    output_dir.mkdir(parents=True, exist_ok=True)

    start = time.monotonic_ns()
    result = subprocess.run(
        [
            GUARDC_BIN,
            "compile",
            str(guard_file),
            "--output",
            str(output_bin),
            "--target",
            "native",
            "--release",
            "--bench-entry",
        ],
        capture_output=True,
        text=True,
        timeout=TIMEOUT_PER_TEST,
    )
    elapsed_ns = time.monotonic_ns() - start

    if result.returncode != 0:
        raise RuntimeError(
            f"guardc failed for {guard_file}:\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )

    if not output_bin.exists():
        raise FileNotFoundError(f"Expected binary not found: {output_bin}")

    compile_time_ms = elapsed_ns // 1_000_000
    return output_bin, compile_time_ms


def run_benchmark(
    binary: Path, iterations: int, warmup: int = WARMUP_ITERATIONS
) -> Dict[str, Any]:
    """
    Run the compiled benchmark binary and parse JSON output.
    The binary is expected to accept --iterations and --warmup flags
    and output JSON stats to stdout.
    """
    result = subprocess.run(
        [
            str(binary),
            "--iterations",
            str(iterations),
            "--warmup",
            str(warmup),
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        timeout=TIMEOUT_PER_TEST,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Benchmark binary failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

    return json.loads(result.stdout)


# ---------------------------------------------------------------------------
# Baseline Management
# ---------------------------------------------------------------------------


def load_baseline(path: Path = BASELINE_FILE) -> Dict[str, Dict[str, Any]]:
    """Load baseline results from JSON file."""
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def save_baseline(
    results: Dict[str, Dict[str, Any]], path: Path = BASELINE_FILE
) -> None:
    """Save baseline results to JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(results, f, indent=2, sort_keys=True)


# ---------------------------------------------------------------------------
# Comparison Logic
# ---------------------------------------------------------------------------


def compare_results(
    current: BenchmarkResult, baseline: Optional[Dict[str, Any]]
) -> ComparisonResult:
    """Compare current benchmark result against baseline."""
    if baseline is None:
        return ComparisonResult(
            guard_file=current.guard_file,
            baseline_mean_ns=0.0,
            current_mean_ns=current.mean_ns,
            delta_percent=0.0,
            verdict="NEW",
            details="No baseline found; result recorded as new baseline.",
        )

    baseline_mean = baseline.get("mean_ns", baseline.get("mean", 0.0))
    if baseline_mean == 0:
        return ComparisonResult(
            guard_file=current.guard_file,
            baseline_mean_ns=0.0,
            current_mean_ns=current.mean_ns,
            delta_percent=0.0,
            verdict="SKIP",
            details="Baseline has zero mean; cannot compare.",
        )

    delta = (current.mean_ns - baseline_mean) / baseline_mean

    if delta > REGRESSION_THRESHOLD:
        verdict = "FAIL"
        details = (
            f"Regression: {delta:.2%} slower than baseline "
            f"(threshold: {REGRESSION_THRESHOLD:.0%})"
        )
    elif delta < -REGRESSION_THRESHOLD:
        verdict = "PASS"
        details = f"Improvement: {abs(delta):.2%} faster than baseline"
    else:
        verdict = "PASS"
        details = f"Within threshold: {delta:+.2%} (threshold: ±{REGRESSION_THRESHOLD:.0%})"

    return ComparisonResult(
        guard_file=current.guard_file,
        baseline_mean_ns=baseline_mean,
        current_mean_ns=current.mean_ns,
        delta_percent=delta,
        verdict=verdict,
        details=details,
    )


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------


def generate_report(
    comparisons: List[ComparisonResult],
    results: List[BenchmarkResult],
    output_path: Path = REPORT_FILE,
) -> str:
    """Generate a markdown performance regression report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        "# Performance Regression Report",
        "",
        f"**Generated:** {now}",
        f"**Iterations per test:** {ITERATIONS:,}",
        f"**Regression threshold:** {REGRESSION_THRESHOLD:.0%}",
        f"**Guard directory:** `{GUARD_DIR}`",
        "",
        "## Summary",
        "",
    ]

    pass_count = sum(1 for c in comparisons if c.verdict == "PASS")
    fail_count = sum(1 for c in comparisons if c.verdict == "FAIL")
    new_count = sum(1 for c in comparisons if c.verdict == "NEW")
    skip_count = sum(1 for c in comparisons if c.verdict == "SKIP")

    lines.append(f"| Verdict | Count |")
    lines.append(f"|---------|-------|")
    lines.append(f"| ✅ PASS | {pass_count} |")
    lines.append(f"| ❌ FAIL | {fail_count} |")
    lines.append(f"| 🆕 NEW  | {new_count} |")
    lines.append(f"| ⏭️ SKIP | {skip_count} |")
    lines.append("")

    if fail_count > 0:
        lines.append("## ⚠️ Regressions Detected")
        lines.append("")
        lines.append("| Guard File | Baseline (ns) | Current (ns) | Delta |")
        lines.append("|------------|---------------|--------------|-------|")
        for c in comparisons:
            if c.verdict == "FAIL":
                lines.append(
                    f"| `{c.guard_file}` | {c.baseline_mean_ns:.1f} | "
                    f"{c.current_mean_ns:.1f} | {c.delta_percent:+.2%} |"
                )
        lines.append("")

    lines.append("## Detailed Results")
    lines.append("")
    lines.append(
        "| Guard File | Mean (ns) | Median (ns) | P95 (ns) | P99 (ns) | "
        "Compile (ms) | Binary Size | Verdict |"
    )
    lines.append(
        "|------------|-----------|-------------|----------|----------|"
        "-------------|-------------|---------|"
    )

    for comp, result in zip(comparisons, results):
        verdict_icon = {
            "PASS": "✅",
            "FAIL": "❌",
            "NEW": "🆕",
            "SKIP": "⏭️",
        }.get(comp.verdict, "?")
        binary_kb = result.binary_size_bytes / 1024
        lines.append(
            f"| `{result.guard_file}` | {result.mean_ns:.1f} | "
            f"{result.median_ns:.1f} | {result.p95_ns:.1f} | "
            f"{result.p99_ns:.1f} | {result.compile_time_ms} | "
            f"{binary_kb:.1f} KB | {verdict_icon} {comp.verdict} |"
        )

    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append(
        f"- Each test runs {ITERATIONS:,} iterations after "
        f"{WARMUP_ITERATIONS:,} warmup iterations."
    )
    lines.append(
        f"- A regression is flagged when the mean iteration time exceeds "
        f"the baseline by more than {REGRESSION_THRESHOLD:.0%}."
    )
    lines.append(
        "- To update baselines, run with `--update-baseline` flag."
    )
    lines.append("")
    lines.append("---")
    lines.append("*Generated by test_perf_regression.py — Forgemaster ⚒️*")
    lines.append("")

    report = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report)
    return report


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def discover_guard_files() -> List[Path]:
    """Find all .guard files in the configured directory."""
    guard_path = Path(GUARD_DIR)
    if not guard_path.exists():
        pytest.skip(f"Guard directory not found: {guard_path}")
    files = sorted(guard_path.glob("**/*.guard"))
    if not files:
        pytest.skip(f"No .guard files found in {guard_path}")
    return files


@pytest.fixture(scope="session")
def baseline_data():
    """Load baseline data once per session."""
    return load_baseline()


@pytest.fixture(scope="session")
def compiled_binaries(tmp_path_factory):
    """Compile all guard files and return a dict of {name: binary_path}."""
    guard_files = discover_guard_files()
    output_dir = tmp_path_factory.mktemp("compiled")
    binaries = {}

    for gf in guard_files:
        try:
            binary, compile_ms = compile_guard(gf, output_dir)
            binaries[gf.name] = {
                "binary": binary,
                "compile_ms": compile_ms,
                "size": binary.stat().st_size,
            }
        except (RuntimeError, FileNotFoundError) as e:
            pytest.warn(f"Failed to compile {gf.name}: {e}")

    return binaries


@pytest.fixture(scope="session")
def benchmark_results(compiled_binaries):
    """Run benchmarks on all compiled binaries."""
    results = []
    for name, info in compiled_binaries.items():
        try:
            stats = run_benchmark(info["binary"], ITERATIONS)
            results.append(
                BenchmarkResult(
                    guard_file=name,
                    iterations=ITERATIONS,
                    total_ns=stats.get("total_ns", 0),
                    mean_ns=stats.get("mean_ns", stats.get("mean", 0.0)),
                    median_ns=stats.get("median_ns", stats.get("median", 0.0)),
                    min_ns=stats.get("min_ns", 0),
                    max_ns=stats.get("max_ns", 0),
                    p50_ns=stats.get("p50_ns", stats.get("median_ns", 0.0)),
                    p95_ns=stats.get("p95_ns", 0.0),
                    p99_ns=stats.get("p99_ns", 0.0),
                    compile_time_ms=info["compile_ms"],
                    binary_size_bytes=info["size"],
                )
            )
        except (RuntimeError, json.JSONDecodeError) as e:
            pytest.warn(f"Benchmark failed for {name}: {e}")

    return results


@pytest.fixture(scope="session")
def comparison_results(benchmark_results, baseline_data):
    """Compare all benchmark results against baseline."""
    comparisons = []
    for result in benchmark_results:
        baseline_entry = baseline_data.get(result.guard_file)
        comp = compare_results(result, baseline_entry)
        comparisons.append(comp)
    return comparisons


# ---------------------------------------------------------------------------
# Test Classes
# ---------------------------------------------------------------------------


class TestPerformanceRegression:
    """Performance regression test suite."""

    def test_all_guard_files_compile(self, compiled_binaries):
        """Verify all .guard files compile successfully."""
        guard_files = discover_guard_files()
        compiled_names = set(compiled_binaries.keys())
        expected_names = {gf.name for gf in guard_files}

        failed = expected_names - compiled_names
        assert not failed, f"Failed to compile: {failed}"

    def test_no_regressions(self, comparison_results):
        """Fail if any benchmark shows >5% regression from baseline."""
        regressions = [
            c for c in comparison_results if c.verdict == "FAIL"
        ]
        if regressions:
            details = "\n".join(
                f"  - {r.guard_file}: {r.delta_percent:+.2%} ({r.details})"
                for r in regressions
            )
            pytest.fail(
                f"Performance regressions detected:\n{details}\n\n"
                f"Run with --update-baseline to accept new baselines."
            )

    def test_benchmarks_produce_valid_stats(self, benchmark_results):
        """Verify all benchmark results have valid statistics."""
        for result in benchmark_results:
            assert result.mean_ns > 0, f"{result.guard_file}: zero mean"
            assert result.median_ns > 0, f"{result.guard_file}: zero median"
            assert result.p95_ns >= result.median_ns, (
                f"{result.guard_file}: P95 < median (data inconsistency)"
            )
            assert result.p99_ns >= result.p95_ns, (
                f"{result.guard_file}: P99 < P95 (data inconsistency)"
            )

    @pytest.mark.parametrize("metric", ["mean_ns", "p95_ns", "p99_ns"])
    def test_no_extreme_outliers(self, benchmark_results, metric):
        """Check that no single benchmark is orders of magnitude slower than average."""
        values = [getattr(r, metric) for r in benchmark_results]
        if len(values) < 2:
            pytest.skip("Need at least 2 benchmarks for outlier detection")

        avg = sum(values) / len(values)
        for result in benchmark_results:
            val = getattr(result, metric)
            # Flag if more than 10x the average
            if val > avg * 10:
                pytest.fail(
                    f"{result.guard_file}: {metric}={val:.1f}ns is >10x "
                    f"average ({avg:.1f}ns)"
                )

    def test_report_generated(self, comparison_results, benchmark_results):
        """Verify the markdown report is generated."""
        report = generate_report(comparison_results, benchmark_results)
        assert REPORT_FILE.exists(), "Report file not created"
        assert len(report) > 100, "Report seems too short"

        # Ensure report mentions each guard file
        for result in benchmark_results:
            assert result.guard_file in report, (
                f"Report missing {result.guard_file}"
            )

    def test_compile_times_reasonable(self, compiled_binaries):
        """Verify compile times are under 60 seconds each."""
        for name, info in compiled_binaries.items():
            assert info["compile_ms"] < 60_000, (
                f"{name}: compile took {info['compile_ms']}ms (>60s)"
            )

    def test_binary_sizes_reasonable(self, compiled_binaries):
        """Verify compiled binaries are under 50 MB each."""
        for name, info in compiled_binaries.items():
            size_mb = info["size"] / (1024 * 1024)
            assert size_mb < 50, (
                f"{name}: binary is {size_mb:.1f}MB (>50MB limit)"
            )


# ---------------------------------------------------------------------------
# CLI Entry Point (standalone usage)
# ---------------------------------------------------------------------------


def main():
    """Run benchmarks standalone (outside pytest)."""
    import argparse

    parser = argparse.ArgumentParser(description="GUARD Performance Regression Tests")
    parser.add_argument(
        "--guard-dir", default=GUARD_DIR, help="Directory containing .guard files"
    )
    parser.add_argument(
        "--baseline", default=str(BASELINE_FILE), help="Baseline JSON file"
    )
    parser.add_argument(
        "--update-baseline", action="store_true", help="Update baseline with current results"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=ITERATIONS,
        help="Number of benchmark iterations",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=REGRESSION_THRESHOLD,
        help="Regression threshold (e.g. 0.05 for 5%%)",
    )
    args = parser.parse_args()

    global GUARD_DIR, ITERATIONS, REGRESSION_THRESHOLD
    GUARD_DIR = args.guard_dir
    ITERATIONS = args.iterations
    REGRESSION_THRESHOLD = args.threshold

    print(f"🔍 Discovering .guard files in {GUARD_DIR}...")
    guard_files = discover_guard_files()
    print(f"   Found {len(guard_files)} files")

    baseline = load_baseline(Path(args.baseline))
    print(f"📊 Loaded baseline with {len(baseline)} entries")

    results = []
    comparisons = []
    tmp_dir = Path("/tmp/guard-perf-build")

    for gf in guard_files:
        print(f"\n⚙️  Compiling {gf.name}...")
        try:
            binary, compile_ms = compile_guard(gf, tmp_dir)
            size = binary.stat().st_size
            print(f"   Compiled in {compile_ms}ms ({size / 1024:.1f} KB)")
        except RuntimeError as e:
            print(f"   ❌ Compile failed: {e}")
            continue

        print(f"   🏃 Benchmarking {ITERATIONS:,} iterations...")
        try:
            stats = run_benchmark(binary, ITERATIONS)
        except (RuntimeError, json.JSONDecodeError) as e:
            print(f"   ❌ Benchmark failed: {e}")
            continue

        result = BenchmarkResult(
            guard_file=gf.name,
            iterations=ITERATIONS,
            total_ns=stats.get("total_ns", 0),
            mean_ns=stats.get("mean_ns", stats.get("mean", 0.0)),
            median_ns=stats.get("median_ns", stats.get("median", 0.0)),
            min_ns=stats.get("min_ns", 0),
            max_ns=stats.get("max_ns", 0),
            p50_ns=stats.get("p50_ns", 0.0),
            p95_ns=stats.get("p95_ns", 0.0),
            p99_ns=stats.get("p99_ns", 0.0),
            compile_time_ms=compile_ms,
            binary_size_bytes=size,
        )
        results.append(result)

        comp = compare_results(result, baseline.get(gf.name))
        comparisons.append(comp)
        print(f"   {comp.verdict}: {comp.details}")

    # Generate report
    report = generate_report(comparisons, results)
    print(f"\n📄 Report written to {REPORT_FILE}")

    # Update baseline if requested
    if args.update_baseline:
        new_baseline = {}
        for r in results:
            new_baseline[r.guard_file] = {
                "mean_ns": r.mean_ns,
                "median_ns": r.median_ns,
                "p95_ns": r.p95_ns,
                "p99_ns": r.p99_ns,
                "min_ns": r.min_ns,
                "max_ns": r.max_ns,
                "compile_time_ms": r.compile_time_ms,
                "binary_size_bytes": r.binary_size_bytes,
                "iterations": r.iterations,
                "timestamp": r.timestamp,
            }
        save_baseline(new_baseline, Path(args.baseline))
        print(f"💾 Baseline updated: {args.baseline}")

    # Exit code
    failed = [c for c in comparisons if c.verdict == "FAIL"]
    if failed:
        print(f"\n❌ {len(failed)} regression(s) detected!")
        sys.exit(1)
    else:
        print(f"\n✅ All {len(comparisons)} benchmarks passed")
        sys.exit(0)


if __name__ == "__main__":
    main()
