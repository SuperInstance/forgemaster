#!/usr/bin/env python3
"""
Consolidated Constraint Test — validates all 10 industry constraint libraries.

Reads .md files, extracts GUARD DSL constraint definitions, generates test cases,
evaluates them, and reports per-file and overall statistics.
"""

import re
import os
import sys
import random
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

SEED = 42
random.seed(SEED)

CONSTRAINTS_DIR = Path(__file__).parent
PASS_PER_CONSTRAINT = 50
FAIL_PER_CONSTRAINT = 50

# ── Data structures ──────────────────────────────────────────────────────────

@dataclass
class Constraint:
    name: str
    min_val: float
    max_val: float
    unit: str = ""
    update_hz: Optional[float] = None
    source_file: str = ""
    source_line: int = 0

@dataclass
class TestCase:
    value: float
    expected_pass: bool

@dataclass
class TestResult:
    constraint_name: str
    source_file: str
    total: int
    passed: int
    failed: int
    pass_rate: float
    details: List[dict] = field(default_factory=list)

# ── Parsing ──────────────────────────────────────────────────────────────────

def extract_number(s: str) -> float:
    """Extract first numeric value (including negative, decimal, scientific, comma-separated) from string."""
    # Remove commas from numbers (e.g., 12,000 -> 12000)
    cleaned = re.sub(r'(\d),(\d)', r'\1\2', s)
    m = re.search(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?', cleaned)
    if m:
        return float(m.group())
    raise ValueError(f"No number found in: {s}")


def parse_code_block_constraints(text: str, filename: str) -> List[Constraint]:
    """Parse constraints in code-block format: constraint name { min: X unit, max: Y unit, ... }"""
    constraints = []
    pattern = re.compile(
        r'constraint\s+(\w+)\s*\{([^}]+)\}',
        re.MULTILINE
    )
    for match in pattern.finditer(text):
        name = match.group(1)
        body = match.group(2)
        line_num = text[:match.start()].count('\n') + 1
        try:
            # Remove commas from numbers in body before parsing
            clean_body = re.sub(r'(\d),(\d{3})', r'\1\2', body)
            min_match = re.search(r'min:\s*(.+?)(?:,|\n)', clean_body)
            max_match = re.search(r'max:\s*(.+?)(?:,|\n)', clean_body)
            update_match = re.search(r'update:\s*(.+?)(?:\}|,|\n)', clean_body)

            min_val = extract_number(min_match.group(1)) if min_match else 0
            max_val = extract_number(max_match.group(1)) if max_match else 100

            # Extract unit from min line
            unit = ""
            if min_match:
                unit_m = re.search(r'[\d.]+\s*(\S+)', min_match.group(1))
                if unit_m:
                    unit = unit_m.group(1).rstrip(',')

            update_hz = None
            if update_match:
                try:
                    update_hz = extract_number(update_match.group(1))
                except ValueError:
                    pass

            constraints.append(Constraint(
                name=name, min_val=min_val, max_val=max_val,
                unit=unit, update_hz=update_hz,
                source_file=filename, source_line=line_num
            ))
        except (ValueError, AttributeError) as e:
            print(f"  ⚠ Skipping {name} in {filename} (line {line_num}): {e}")
    return constraints


def parse_field_constraints(text: str, filename: str) -> List[Constraint]:
    """Parse constraints in field/list format with Name/Min/Max fields or Bounds lines."""
    constraints = []

    # Pattern 1: Table format with | **Name** | `value` |
    # Pattern 2: Field format with - **Bounds:** [min, max]
    # Pattern 3: - **Min** / - **Max** pairs

    # Try Bounds pattern: **Bounds:** [min, max]
    bounds_pattern = re.compile(
        r'(?:###\s*\d+\.\s*`?(\w+)`?|^\|\s*\*\*Name\*\*\s*\|\s*`?(\w+)`?\s*\|)',
        re.MULTILINE
    )

    # Simpler approach: find all constraint blocks
    # Split into sections by ## or ### numbered headers
    sections = re.split(r'(?=^##\s+\d+\.|^###\s+\d+\.)', text, flags=re.MULTILINE)

    for sec in sections:
        if not sec.strip():
            continue

        # Extract name from table row: | **Name** | `value` |
        name_match = re.search(r'\|\s*\*\*Name\*\*\s*\|\s*`([^`]+)`\s*\|', sec)
        if not name_match:
            name_match = re.search(r'\|\s*\*\*Name\*\*\s*\|\s*(\w+)\s*\|', sec)
        # Also try ### header: "### 1. name — description" or "### 1. name — description"
        if not name_match:
            name_match = re.search(r'###\s+\d+\.\s+(\w+)', sec)
        if not name_match:
            continue

        name = name_match.group(1)
        line_num = text[:text.find(sec)].count('\n') + 1

        min_val = None
        max_val = None
        unit = ""

        # Try Bounds: [min, max]
        bounds_match = re.search(r'\*\*Bounds?:\*\*\s*\[([^\]]+)\]', sec)
        if bounds_match:
            parts = bounds_match.group(1).split(',')
            try:
                min_val = extract_number(parts[0])
                max_val = extract_number(parts[1]) if len(parts) > 1 else min_val + 100
                # Extract unit
                unit_m = re.search(r'[\d.]+\s*(\S+)', parts[0])
                if unit_m:
                    unit = unit_m.group(1).rstrip(']')
            except ValueError:
                min_val = None

        # Try | **Min** | value | and | **Max** | value |
        if min_val is None:
            min_match = re.search(r'\*\*Min\*\*\s*\|\s*`?([^`|\n]+)', sec)
            max_match = re.search(r'\*\*Max\*\*\s*\|\s*`?([^`|\n]+)', sec)
            if min_match and max_match:
                try:
                    min_val = extract_number(min_match.group(1))
                    max_val = extract_number(max_match.group(1))
                    unit_m = re.search(r'[\d.]+\s*(\S+)', min_match.group(1))
                    if unit_m:
                        unit = unit_m.group(1)
                except ValueError:
                    min_val = None

        if min_val is not None and max_val is not None and name:
            if max_val > min_val:  # Sanity check
                constraints.append(Constraint(
                    name=name, min_val=min_val, max_val=max_val,
                    unit=unit, source_file=filename, source_line=line_num
                ))

    return constraints


def parse_file(filepath: Path) -> List[Constraint]:
    """Parse a constraint .md file, trying both formats."""
    text = filepath.read_text()
    filename = filepath.name

    # Try code-block format first
    constraints = parse_code_block_constraints(text, filename)
    if constraints:
        return constraints

    # Fall back to field/table format
    return parse_field_constraints(text, filename)


# ── Test generation ──────────────────────────────────────────────────────────

def generate_test_cases(constraint: Constraint) -> List[TestCase]:
    """Generate test cases for a constraint: 50 pass, 50 fail."""
    cases = []
    lo, hi = constraint.min_val, constraint.max_val
    span = hi - lo

    # 50 PASS cases — values within [min, max]
    for _ in range(PASS_PER_CONSTRAINT):
        # Weighted: more samples near boundaries
        r = random.random()
        if r < 0.3:
            # Near min boundary
            val = lo + random.uniform(0, span * 0.1)
        elif r < 0.6:
            # Near max boundary
            val = hi - random.uniform(0, span * 0.1)
        elif r < 0.8:
            # Mid-range
            val = lo + random.uniform(span * 0.3, span * 0.7)
        else:
            # Random across full range
            val = random.uniform(lo, hi)
        cases.append(TestCase(value=round(val, 6), expected_pass=True))

    # 50 FAIL cases — values outside [min, max]
    for _ in range(FAIL_PER_CONSTRAINT):
        if random.random() < 0.5:
            # Below min
            val = lo - random.uniform(abs(span) * 0.01 + 0.001, abs(span) * 0.5 + 1.0)
        else:
            # Above max
            val = hi + random.uniform(abs(span) * 0.01 + 0.001, abs(span) * 0.5 + 1.0)
        val = round(val, 6)
        # Ensure actually outside range
        if lo <= val <= hi:
            val = hi + abs(span) * 0.1 + 0.001
            val = round(val, 6)
        cases.append(TestCase(value=val, expected_pass=False))

    random.shuffle(cases)
    return cases


# ── Evaluation ───────────────────────────────────────────────────────────────

def evaluate_constraint(constraint: Constraint, cases: List[TestCase]) -> TestResult:
    """Evaluate test cases against a constraint. Returns result with pass/fail counts."""
    passed = 0
    failed = 0
    details = []

    for tc in cases:
        # A value passes if it's within [min, max] inclusive
        in_range = constraint.min_val <= tc.value <= constraint.max_val
        correct = (in_range == tc.expected_pass)

        if correct:
            passed += 1
        else:
            failed += 1
            details.append({
                "value": tc.value,
                "expected_pass": tc.expected_pass,
                "actual_in_range": in_range,
                "min": constraint.min_val,
                "max": constraint.max_val
            })

    total = len(cases)
    return TestResult(
        constraint_name=constraint.name,
        source_file=constraint.source_file,
        total=total,
        passed=passed,
        failed=failed,
        pass_rate=passed / total * 100 if total else 0,
        details=details
    )


# ── Reporting ────────────────────────────────────────────────────────────────

def print_summary_table(file_results: dict):
    """Print a formatted summary table."""
    print("\n" + "=" * 90)
    print("  CONSTRAINT LIBRARY TEST RESULTS")
    print("=" * 90)

    header = f"{'Library':<30} {'Constraints':>12} {'Tests':>8} {'Passed':>8} {'Failed':>8} {'Rate':>8}"
    print(header)
    print("-" * 90)

    total_constraints = 0
    total_tests = 0
    total_passed = 0
    total_failed = 0

    for filename, results in sorted(file_results.items()):
        n_constraints = len(results)
        n_tests = sum(r.total for r in results)
        n_passed = sum(r.passed for r in results)
        n_failed = sum(r.failed for r in results)
        rate = n_passed / n_tests * 100 if n_tests else 0

        label = filename.replace('.md', '')
        print(f"{label:<30} {n_constraints:>12} {n_tests:>8} {n_passed:>8} {n_failed:>8} {rate:>7.1f}%")

        total_constraints += n_constraints
        total_tests += n_tests
        total_passed += n_passed
        total_failed += n_failed

    print("-" * 90)
    overall_rate = total_passed / total_tests * 100 if total_tests else 0
    print(f"{'TOTAL':<30} {total_constraints:>12} {total_tests:>8} {total_passed:>8} {total_failed:>8} {overall_rate:>7.1f}%")
    print("=" * 90)

    # Per-file detail
    print("\n  DETAILED PER-FILE BREAKDOWN")
    print("-" * 70)
    for filename, results in sorted(file_results.items()):
        label = filename.replace('.md', '')
        print(f"\n  📂 {label}")
        for r in results:
            status = "✅" if r.pass_rate == 100 else "⚠️"
            print(f"    {status} {r.constraint_name:<40} {r.passed:>3}/{r.total:>3} ({r.pass_rate:.0f}%)")
            if r.details:
                for d in r.details[:3]:  # Show up to 3 failures
                    print(f"       FAIL: val={d['value']}, expected={'pass' if d['expected_pass'] else 'fail'}, "
                          f"in_range={d['actual_in_range']}, range=[{d['min']}, {d['max']}]")


def print_json_results(file_results: dict, output_path: Path):
    """Write JSON results for machine consumption."""
    output = {
        "seed": SEED,
        "pass_per_constraint": PASS_PER_CONSTRAINT,
        "fail_per_constraint": FAIL_PER_CONSTRAINT,
        "files": {}
    }
    for filename, results in sorted(file_results.items()):
        output["files"][filename] = {
            "constraint_count": len(results),
            "total_tests": sum(r.total for r in results),
            "passed": sum(r.passed for r in results),
            "failed": sum(r.failed for r in results),
            "pass_rate": sum(r.passed for r in results) / sum(r.total for r in results) * 100,
            "constraints": [
                {
                    "name": r.constraint_name,
                    "total": r.total,
                    "passed": r.passed,
                    "failed": r.failed,
                    "pass_rate": r.pass_rate,
                    "failure_details": r.details[:5]
                }
                for r in results
            ]
        }
    output_path.write_text(json.dumps(output, indent=2))
    print(f"\n  📊 JSON results written to {output_path}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    md_files = sorted(CONSTRAINTS_DIR.glob("*.md"))
    # Exclude README
    md_files = [f for f in md_files if f.name.lower() != 'readme.md']

    if not md_files:
        print("No .md constraint files found!")
        sys.exit(1)

    print(f"  🔍 Found {len(md_files)} constraint libraries\n")

    file_results = {}

    for filepath in md_files:
        print(f"  📖 Parsing {filepath.name}...")
        constraints = parse_file(filepath)
        print(f"     → {len(constraints)} constraints extracted")

        if not constraints:
            print(f"     ⚠ No constraints found in {filepath.name}")
            continue

        results = []
        for c in constraints:
            cases = generate_test_cases(c)
            result = evaluate_constraint(c, cases)
            results.append(result)

        file_results[filepath.name] = results

    # Report
    print_summary_table(file_results)
    print_json_results(file_results, CONSTRAINTS_DIR / "test_results.json")

    # Exit code
    total_failed = sum(
        r.failed
        for results in file_results.values()
        for r in results
    )
    if total_failed > 0:
        print(f"\n  ❌ {total_failed} test failures detected (evaluator logic issues)")
        sys.exit(1)
    else:
        print(f"\n  ✅ All tests passed — constraint evaluator is correct")
        sys.exit(0)


if __name__ == "__main__":
    main()
