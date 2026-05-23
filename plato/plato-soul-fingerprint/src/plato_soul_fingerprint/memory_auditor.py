"""Constraint-verified memory auditing.

Check MEMORY.md assertions against source data.
Holonomy verification for knowledge — the "forge's quality control" for
the fleet's long-term memory system.
"""

import re
import os
from typing import List, Dict, Any, Tuple


def extract_assertions(memory_path: str) -> List[Dict[str, Any]]:
    """Extract checkable assertions from a MEMORY.md file.

    Looks for patterns like:
    - "**47 plato-* crates on crates.io**"
    - "**40/40 PyPI packages live**"
    - "RTX 4050, 6141 MiB VRAM"
    - "rustc 1.75.0"

    Returns list of {line_number, text, category, value_hint} dicts.
    """
    assertions = []

    if not os.path.isfile(memory_path):
        return assertions

    with open(memory_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            continue

        # Number assertions: "47 plato-* crates", "40/40 PyPI"
        num_patterns = [
            (r'\*\*(\d+)\s+([^*]+)\*\*', 'bold_number'),
            (r'(\d+)/(\d+)\s+([^*\n]+)', 'fraction'),
            (r'(\d+)\s+(?:plato-|crates|tests|repos)', 'count'),
        ]

        for pattern, category in num_patterns:
            m = re.search(pattern, stripped)
            if m:
                assertions.append({
                    "line": i,
                    "text": stripped[:100],
                    "category": category,
                    "match": m.group(0),
                    "groups": m.groups(),
                })
                break

    return assertions


def check_crate_count(claimed: int, prefix: str = "plato-") -> Dict[str, Any]:
    """Verify crate count by checking crates.io (via cargo search)."""
    import subprocess
    try:
        result = subprocess.run(
            ["cargo", "search", prefix, "--limit", str(claimed + 10)],
            capture_output=True, text=True, timeout=30
        )
        actual = 0
        for line in result.stdout.splitlines():
            if line.startswith(prefix):
                actual += 1
        return {
            "claimed": claimed,
            "actual": actual,
            "status": "verified" if actual >= claimed else "stale",
            "detail": f"Found {actual} crates matching '{prefix}*' on crates.io"
        }
    except Exception as e:
        return {"claimed": claimed, "status": "error", "detail": str(e)}


def audit_memory(memory_path: str) -> Dict[str, Any]:
    """Run a full audit of MEMORY.md against verifiable claims.

    Returns audit report with status for each checkable assertion.
    """
    assertions = extract_assertions(memory_path)
    results = []

    for a in assertions:
        if a["category"] == "bold_number":
            text = a["match"]
            # Try to extract what kind of number it is
            lower = text.lower()
            if "crate" in lower:
                m = re.search(r'\*\*(\d+)\s', text)
                if m:
                    claimed = int(m.group(1))
                    check = check_crate_count(claimed)
                    check["assertion"] = text
                    results.append(check)
                    continue

        results.append({
            "assertion": a["match"],
            "line": a["line"],
            "status": "unverified",
            "detail": "No automated check available"
        })

    verified = sum(1 for r in results if r["status"] == "verified")
    stale = sum(1 for r in results if r["status"] == "stale")

    return {
        "total_assertions": len(assertions),
        "verified": verified,
        "stale": stale,
        "results": results,
    }


def memory_report(memory_path: str) -> str:
    """Generate a human-readable memory audit report."""
    audit = audit_memory(memory_path)

    lines = [
        "=" * 50,
        "MEMORY AUDIT REPORT",
        "=" * 50,
        f"File: {memory_path}",
        f"Assertions found: {audit['total_assertions']}",
        f"Verified: {audit['verified']}",
        f"Stale: {audit['stale']}",
        "",
    ]

    for r in audit["results"]:
        status_icon = {"verified": "✓", "stale": "⚠", "unverified": "?"}.get(r["status"], "?")
        lines.append(f"  {status_icon} Line {r.get('line', '?')}: {r.get('assertion', '?')[:60]}")
        if "detail" in r:
            lines.append(f"    → {r['detail']}")

    lines.append("")
    lines.append("=" * 50)
    return "\n".join(lines)
