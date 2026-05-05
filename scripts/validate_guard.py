#!/usr/bin/env python3
"""
validate_guard.py — Validate all .guard files in a directory tree.

Checks:
  1. At least one constraint per file
  2. lo <= hi for range constraints
  3. Valid hex masks (even number of hex digits, 0-9a-fA-F only)
  4. Balanced group braces { }
  5. Valid metadata key=value pairs

Usage:
    python validate_guard.py [directory]       # defaults to .
    python validate_guard.py src/              # scan src/ recursively
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Violation:
    line: int
    col: int | None
    message: str


@dataclass
class FileReport:
    path: Path
    violations: list[Violation] = field(default_factory=list)
    constraint_count: int = 0

    @property
    def ok(self) -> bool:
        return len(self.violations) == 0 and self.constraint_count > 0

    def add(self, line: int, msg: str, col: int | None = None) -> None:
        self.violations.append(Violation(line=line, col=col, message=msg))


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

RE_RANGE = re.compile(r"range\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)")
RE_MASK = re.compile(r"mask\s*\(\s*(0x[0-9a-fA-F]+)\s*\)")
RE_CONSTRAINT_KEYWORD = re.compile(
    r"\b(range|mask|eq|neq|gt|lt|gte|lte|one_of|none_of|in|not_in)\b"
)
RE_METADATA = re.compile(r"^@(\w+)\s*=\s*(.+)$")
RE_GROUP_OPEN = re.compile(r"\{")
RE_GROUP_CLOSE = re.compile(r"\}")
RE_COMMENT = re.compile(r"#.*$")
RE_HEX = re.compile(r"^0x[0-9a-fA-F]+$")

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def check_ranges(report: FileReport, lines: list[str]) -> None:
    """Validate lo <= hi for every range() constraint."""
    for lineno, raw in enumerate(lines, start=1):
        stripped = RE_COMMENT.sub("", raw)
        for m in RE_RANGE.finditer(stripped):
            lo, hi = int(m.group(1)), int(m.group(2))
            if lo > hi:
                report.add(lineno, f"range({lo}, {hi}): lo > hi", col=m.start())


def check_masks(report: FileReport, lines: list[str]) -> None:
    """Validate hex masks: must be valid hex and even nibble count."""
    for lineno, raw in enumerate(lines, start=1):
        stripped = RE_COMMENT.sub("", raw)
        for m in RE_MASK.finditer(stripped):
            hexval = m.group(1)
            if not RE_HEX.match(hexval):
                report.add(lineno, f"invalid hex mask: {hexval}", col=m.start())
                continue
            nibbles = len(hexval) - 2  # strip 0x
            if nibbles % 2 != 0:
                report.add(
                    lineno,
                    f"mask {hexval} has odd nibble count ({nibbles}); must be whole bytes",
                    col=m.start(),
                )


def check_balanced_groups(report: FileReport, lines: list[str]) -> None:
    """Check that { } braces are balanced, tracking nesting depth."""
    depth = 0
    for lineno, raw in enumerate(lines, start=1):
        stripped = RE_COMMENT.sub("", raw)
        # scan string-quoted regions naively — skip quoted braces
        in_string = False
        i = 0
        while i < len(stripped):
            ch = stripped[i]
            if ch == '"' and (i == 0 or stripped[i - 1] != "\\"):
                in_string = not in_string
            elif not in_string:
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth < 0:
                        report.add(lineno, "unexpected closing brace '}'", col=i)
            i += 1
    if depth > 0:
        # Attach to last line
        last = len(lines)
        report.add(last, f"{depth} unmatched opening brace(s) '{{'")


def check_metadata(report: FileReport, lines: list[str]) -> None:
    """Validate @key=value metadata lines."""
    allowed_keys = {
        "version", "author", "description", "module", "target",
        "arch", "platform", "license", "since", "until", "tags",
    }
    for lineno, raw in enumerate(lines, start=1):
        stripped = raw.strip()
        m = RE_METADATA.match(stripped)
        if m is None:
            continue
        key, value = m.group(1), m.group(2).strip()
        if key not in allowed_keys:
            report.add(
                lineno,
                f"unknown metadata key '@{key}'; allowed: {', '.join(sorted(allowed_keys))}",
            )
        if not value:
            report.add(lineno, f"metadata '@{key}' has empty value")


def count_constraints(report: FileReport, lines: list[str]) -> None:
    """Count constraint keywords across the file."""
    count = 0
    for raw in lines:
        stripped = RE_COMMENT.sub("", raw)
        count += len(RE_CONSTRAINT_KEYWORD.findall(stripped))
    report.constraint_count = count


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def validate_file(path: Path) -> FileReport:
    report = FileReport(path=path)
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:
        report.add(0, f"cannot read file: {exc}")
        return report

    lines = text.splitlines()

    count_constraints(report, lines)
    check_ranges(report, lines)
    check_masks(report, lines)
    check_balanced_groups(report, lines)
    check_metadata(report, lines)

    if report.constraint_count == 0:
        report.add(0, "file contains no constraints")

    return report


def scan(root: Path) -> list[FileReport]:
    reports: list[FileReport] = []
    for p in sorted(root.rglob("*.guard")):
        reports.append(validate_file(p))
    return reports


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    if not root.is_dir():
        print(f"✗ {root} is not a directory", file=sys.stderr)
        sys.exit(2)

    reports = scan(root)

    if not reports:
        print(f"⚠ no .guard files found under {root}")
        sys.exit(0)

    total_ok = 0
    total_fail = 0

    for r in reports:
        status = "✓ PASS" if r.ok else "✗ FAIL"
        rel = r.path.relative_to(root) if r.path.is_relative_to(root) else r.path
        print(f"{status}  {rel}  ({r.constraint_count} constraint(s))")
        for v in r.violations:
            col_info = f":{v.col}" if v.col is not None else ""
            print(f"    line {v.line}{col_info}  — {v.message}")
        if r.ok:
            total_ok += 1
        else:
            total_fail += 1

    print()
    print(f"Files scanned : {len(reports)}")
    print(f"Passed        : {total_ok}")
    print(f"Failed        : {total_fail}")

    sys.exit(0 if total_fail == 0 else 1)


if __name__ == "__main__":
    main()
