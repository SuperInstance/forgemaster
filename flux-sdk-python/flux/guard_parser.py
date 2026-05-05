"""Simple parser for GUARD constraint syntax.

Parses declarations of the form::

    constraint <name> with priority <LEVEL> {
        <var> in [<lo>, <hi>];
    }

Multiple constraints can appear in a single source string.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple

# ── Data ──────────────────────────────────────────────────────────────
@dataclass
class GuardConstraint:
    """A single parsed GUARD constraint."""
    name: str
    lo: int
    hi: int
    priority: str
    variable: str


# ── Pattern ───────────────────────────────────────────────────────────
_CONSTRAINT_RE = re.compile(
    r"constraint\s+(?P<name>\w+)\s+with\s+priority\s+(?P<priority>\w+)\s*\{"
    r"\s*(?P<var>\w+)\s+in\s*\[\s*(?P<lo>-?\d+)\s*,\s*(?P<hi>-?\d+)\s*\]\s*;\s*\}",
    re.MULTILINE,
)


def parse_guard(source: str) -> List[GuardConstraint]:
    """Parse a GUARD source string into a list of constraints.

    Args:
        source: GUARD constraint source text.

    Returns:
        List of :class:`GuardConstraint` instances.

    Raises:
        ValueError: If no constraints are found.
    """
    results: List[GuardConstraint] = []
    for m in _CONSTRAINT_RE.finditer(source):
        results.append(
            GuardConstraint(
                name=m.group("name"),
                lo=int(m.group("lo")),
                hi=int(m.group("hi")),
                priority=m.group("priority"),
                variable=m.group("var"),
            )
        )
    if not results:
        raise ValueError("No valid GUARD constraints found in source")
    return results


def constraints_to_tuples(constraints: List[GuardConstraint]) -> List[Tuple[str, int, int, str]]:
    """Shorthand: list of (name, lo, hi, priority) tuples."""
    return [(c.name, c.lo, c.hi, c.priority) for c in constraints]
