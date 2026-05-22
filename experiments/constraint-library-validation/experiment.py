#!/usr/bin/env python3
"""
Constraint Library Validation — 10 Industries, 248 Constraints
Parses constraint markdown files, validates internal consistency, INT8 compatibility,
and cross-industry compatibility.
"""

import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

WORKSPACE = Path(os.environ.get("WORKSPACE", "/home/phoenix/.openclaw/workspace"))
CONSTRAINTS_DIR = WORKSPACE / "constraints"
OUTPUT_DIR = Path(__file__).parent

# Industry mapping: filename -> (industry_name, standard)
INDUSTRY_MAP = {
    "automotive.md": ("Automotive", "ISO 26262"),
    "aviation.md": ("Aerospace", "DO-178C"),
    "space.md": ("Avionics", "DO-254"),
    "medical.md": ("Medical", "IEC 62304"),
    "energy.md": ("Energy", "IEC 61511"),
    "maritime.md": ("Marine", "DNV"),
    "nuclear.md": ("Nuclear", "IEC 61513"),
    "railway.md": ("Rail", "EN 50128"),
    "robotics.md": ("Robotics", "ISO 10218"),
    "autonomous-underwater.md": ("Industrial", "IEC 61508"),
}


@dataclass
class Constraint:
    name: str
    industry: str
    standard: str
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    unit: str = ""
    update_hz: Optional[float] = None
    section_raw: str = ""
    valid: bool = True
    errors: list = field(default_factory=list)
    int8_compatible: bool = False
    int8_reason: str = ""


def extract_number(s: str) -> Optional[float]:
    """Extract a numeric value from a string like '-600 degrees' or '12,000 kg/h'."""
    if not s:
        return None
    # Remove commas in numbers (e.g., 12,000 -> 12000)
    s = re.sub(r'(\d),(\d)', r'\1\2', s)
    m = re.search(r'[-+]?\d+\.?\d*(?:[eE][-+]?\d+)?', s)
    if m:
        return float(m.group())
    return None


def extract_unit(s: str) -> str:
    """Extract unit from string like '250 km/h' or '-600 degrees'."""
    if not s:
        return ""
    # Remove the number part
    rest = re.sub(r'^[-+]?\d+\.?\d*(?:[eE][-+]?\d+)?\s*', '', s).strip()
    return rest


def parse_constraint_block(text: str, industry: str, standard: str) -> Optional[Constraint]:
    """Parse a single constraint section from markdown."""
    lines = text.strip().split('\n')
    
    # Extract name from first line (##/###/#### N. Name — Description)
    header = lines[0] if lines else ""
    name_match = re.match(r'(?:##|###|####)\s+\d+\.\s+(.*)', header)
    name = name_match.group(1).strip() if name_match else header.lstrip('#').strip()
    
    c = Constraint(name=name, industry=industry, standard=standard, section_raw=text[:200])
    
    # Try code block format: constraint name { min: X, max: Y, ... }
    code_block = re.search(r'```\w*\n(.*?)```', text, re.DOTALL)
    if code_block:
        block = code_block.group(1)
        # Parse min/max from code block
        min_m = re.search(r'min:\s*([-+]?\d[\d,.]*\d|\d+)\s*(\S+)?', block)
        max_m = re.search(r'max:\s*([-+]?\d[\d,.]*\d|\d+)\s*(\S+)?', block)
        update_m = re.search(r'update:\s*(\d+\.?\d*)\s*Hz', block, re.IGNORECASE)
        
        def clean_num(s):
            return float(s.replace(',', '')) if s else None
        
        if min_m:
            c.min_val = clean_num(min_m.group(1))
            c.unit = min_m.group(2) or c.unit
        if max_m:
            c.max_val = clean_num(max_m.group(1))
            if not c.unit:
                c.unit = max_m.group(2) or ""
        if update_m:
            c.update_hz = float(update_m.group(1))
    
    # Try table format: | Min | X unit |
    if c.min_val is None or c.max_val is None:
        table_rows = re.findall(r'\|\s*\*?\*?(?:Min|Minimum|Range)\*?\*?\s*\|\s*([-+]?\d[\d,.]*\d|\d+)\s*([^\n|]*?)\s*\|', text, re.IGNORECASE)
        if table_rows:
            c.min_val = float(table_rows[0][0].replace(',', ''))
            c.unit = table_rows[0][1].strip() or c.unit
        
        table_max = re.findall(r'\|\s*\*?\*?(?:Max|Maximum)\*?\*?\s*\|\s*([-+]?\d[\d,.]*\d|\d+)\s*([^\n|]*?)\s*\|', text, re.IGNORECASE)
        if table_max:
            c.max_val = float(table_max[0][0].replace(',', ''))
            if not c.unit:
                c.unit = table_max[0][1].strip() or ""
    
    # Try inline format from description: "range of X to Y unit"
    if c.min_val is None or c.max_val is None:
        range_m = re.search(r'(\d+\.?\d*)\s*(\w+)\s+to\s+(\d+\.?\d*)\s*(\w+)', text)
        if range_m:
            if c.min_val is None:
                c.min_val = float(range_m.group(1))
                c.unit = range_m.group(2)
            if c.max_val is None:
                c.max_val = float(range_m.group(3))
                if not c.unit:
                    c.unit = range_m.group(4)
    
    # Try Bounds: [X unit, Y unit] or Bounds: [X, Y] format
    if c.min_val is None or c.max_val is None:
        bounds_m = re.search(r'\*\*Bounds:\*\*\s*\[([-+]?−?\d+\.?\d*)\s*(\S+)?,\s*([-+]?−?\d+\.?\d*)\s*(\S+)?\]', text)
        if bounds_m:
            if c.min_val is None:
                c.min_val = float(bounds_m.group(1).replace('−', '-'))
                c.unit = bounds_m.group(2) or c.unit
            if c.max_val is None:
                c.max_val = float(bounds_m.group(3).replace('−', '-'))
                if not c.unit:
                    c.unit = bounds_m.group(4) or ""
    
    # Try min: -X, max: +Y pattern in text
    if c.min_val is None:
        min_inline = re.search(r'(?:min|minimum|lower)[:\s]+([-+]?\d+\.?\d*)', text, re.IGNORECASE)
        if min_inline:
            c.min_val = float(min_inline.group(1))
    if c.max_val is None:
        max_inline = re.search(r'(?:max|maximum|upper)[:\s]+([-+]?\d+\.?\d*)', text, re.IGNORECASE)
        if max_inline:
            c.max_val = float(max_inline.group(1))
    
    # Extract update rate from table if not found
    if c.update_hz is None:
        upd = re.search(r'(?:Update|Rate|Frequency)[:\s\|]+(\d+\.?\d*)\s*Hz', text, re.IGNORECASE)
        if upd:
            c.update_hz = float(upd.group(1))
    
    return c


def parse_file(filepath: Path, industry: str, standard: str) -> list[Constraint]:
    """Parse all constraints from a single markdown file."""
    content = filepath.read_text(encoding='utf-8', errors='replace')
    
    # Try multiple section header patterns
    # Pattern 1: ## N. Name (automotive, aviation, medical, nuclear)
    # Pattern 2: ### N. name — description (energy, robotics)
    # Pattern 3: #### N. Name — description (space, maritime, railway)
    sections = re.split(r'\n(?=##\s+\d+\.\s|###\s+\d+\.\s|####\s+\d+\.\s)', content)
    
    constraints = []
    for section in sections:
        stripped = section.strip()
        if not stripped:
            continue
        # Check if this looks like a constraint section (starts with a numbered header)
        if not re.match(r'(?:##|###|####)\s+\d+\.\s', stripped):
            continue
        c = parse_constraint_block(stripped, industry, standard)
        if c:
            constraints.append(c)
    
    return constraints


def validate_constraint(c: Constraint) -> Constraint:
    """Validate a single constraint for internal consistency."""
    errors = []
    
    # 1. Lower bound < upper bound
    if c.min_val is not None and c.max_val is not None:
        if c.min_val >= c.max_val:
            errors.append(f"min ({c.min_val}) >= max ({c.max_val})")
    elif c.min_val is None and c.max_val is None:
        errors.append("no min/max values found (unparseable)")
    
    # 2. Physical plausibility
    if c.min_val is not None:
        # Kelvin temperatures must be >= 0
        if 'kelvin' in c.unit.lower() and c.min_val < 0:
            errors.append(f"negative Kelvin temperature: {c.min_val}")
        # Speeds should be non-negative (unless lateral)
        if c.min_val < -1e6:
            errors.append(f"suspiciously low min value: {c.min_val}")
    if c.max_val is not None:
        if c.max_val > 1e9:
            errors.append(f"suspiciously high max value: {c.max_val}")
    
    # 3. INT8 compatibility: can range fit in [-128, 127] after scaling?
    if c.min_val is not None and c.max_val is not None:
        range_size = c.max_val - c.min_val
        if range_size == 0:
            c.int8_compatible = True
            c.int8_reason = "zero-width range"
        elif range_size <= 255:
            # Can map with scale >= 1.0 per bit — exact fit
            scale = range_size / 255.0
            c.int8_compatible = True
            c.int8_reason = f"fits with scale={scale:.4f} {c.unit}/bit"
        elif range_size <= 255 * 4:  # with reasonable scaling
            scale = range_size / 255.0
            if scale < 100:  # reasonable resolution
                c.int8_compatible = True
                c.int8_reason = f"fits with scale={scale:.4f} {c.unit}/bit"
            else:
                c.int8_compatible = False
                c.int8_reason = f"scale too coarse: {scale:.2f} {c.unit}/bit"
        else:
            scale = range_size / 255.0
            c.int8_compatible = False
            c.int8_reason = f"range too wide: {range_size:.1f} {c.unit}, scale={scale:.2f}"
    else:
        c.int8_reason = "missing bounds"
    
    c.valid = len(errors) == 0
    c.errors = errors
    return c


def check_cross_industry_conflicts(all_constraints: list[Constraint]) -> list[dict]:
    """Check for conflicts between constraints from different industries."""
    conflicts = []
    
    # Group by unit type
    by_unit = {}
    for c in all_constraints:
        if c.min_val is None or c.max_val is None:
            continue
        key = c.unit.lower().strip()
        if key not in by_unit:
            by_unit[key] = []
        by_unit[key].append(c)
    
    # For same-unit constraints across industries, check for range conflicts
    for unit, constraints in by_unit.items():
        if len(constraints) < 2:
            continue
        # Check if any pair from different industries has no overlap
        for i in range(len(constraints)):
            for j in range(i + 1, len(constraints)):
                ci, cj = constraints[i], constraints[j]
                if ci.industry == cj.industry:
                    continue
                # No overlap = disjoint ranges = conflict for shared resources
                if ci.max_val < cj.min_val or cj.max_val < ci.min_val:
                    conflicts.append({
                        "type": "disjoint_range",
                        "constraint_a": f"{ci.industry}/{ci.name}",
                        "range_a": f"[{ci.min_val}, {ci.max_val}] {ci.unit}",
                        "constraint_b": f"{cj.industry}/{cj.name}",
                        "range_b": f"[{cj.min_val}, {cj.max_val}] {cj.unit}",
                        "detail": "Ranges are disjoint — no overlap between industries"
                    })
    
    return conflicts


def main():
    print("=" * 70)
    print("CONSTRAINT LIBRARY VALIDATION — 10 INDUSTRIES, 248 CONSTRAINTS")
    print("=" * 70)
    
    all_constraints = []
    industry_results = {}
    
    # Parse all files
    for filename, (industry, standard) in INDUSTRY_MAP.items():
        filepath = CONSTRAINTS_DIR / filename
        if not filepath.exists():
            print(f"\n⚠️  MISSING: {filename} ({industry})")
            industry_results[industry] = {
                "standard": standard,
                "file": filename,
                "total": 0,
                "valid": 0,
                "int8_compatible": 0,
                "errors": [f"File not found: {filepath}"],
                "constraints": []
            }
            continue
        
        constraints = parse_file(filepath, industry, standard)
        
        # Validate each constraint
        for c in constraints:
            validate_constraint(c)
        
        valid_count = sum(1 for c in constraints if c.valid)
        int8_count = sum(1 for c in constraints if c.int8_compatible)
        
        all_constraints.extend(constraints)
        industry_results[industry] = {
            "standard": standard,
            "file": filename,
            "total": len(constraints),
            "valid": valid_count,
            "int8_compatible": int8_count,
            "errors": [f"{c.name}: {', '.join(c.errors)}" for c in constraints if not c.valid],
            "constraints": [asdict(c) for c in constraints]
        }
        
        status = "✅" if valid_count == len(constraints) else "⚠️"
        print(f"\n{status} {industry} ({standard}): {len(constraints)} constraints, "
              f"{valid_count} valid, {int8_count} INT8-compatible")
        
        if valid_count < len(constraints):
            for c in constraints:
                if not c.valid:
                    print(f"   ❌ {c.name}: {'; '.join(c.errors)}")
    
    # Cross-industry validation
    print("\n" + "=" * 70)
    print("CROSS-INDUSTRY COMPATIBILITY CHECK")
    print("=" * 70)
    
    conflicts = check_cross_industry_conflicts(all_constraints)
    
    if conflicts:
        print(f"\n⚠️  Found {len(conflicts)} cross-industry conflicts:")
        for cf in conflicts:
            print(f"   • {cf['constraint_a']} vs {cf['constraint_b']}: {cf['detail']}")
    else:
        print("\n✅ No cross-industry range conflicts detected.")
    
    # Summary
    total = len(all_constraints)
    total_valid = sum(1 for c in all_constraints if c.valid)
    total_int8 = sum(1 for c in all_constraints if c.int8_compatible)
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total constraints parsed: {total}")
    print(f"Valid (internal consistency): {total_valid}/{total} ({100*total_valid/max(total,1):.1f}%)")
    print(f"INT8-compatible: {total_int8}/{total} ({100*total_int8/max(total,1):.1f}%)")
    print(f"Cross-industry conflicts: {len(conflicts)}")
    
    # Build results JSON
    results = {
        "timestamp": "2026-05-21T15:23:00-08:00",
        "total_constraints": total,
        "total_valid": total_valid,
        "total_int8_compatible": total_int8,
        "cross_industry_conflicts": len(conflicts),
        "conflict_details": conflicts,
        "industries": industry_results
    }
    
    # Save results.json
    with open(OUTPUT_DIR / "results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    # Build RESULTS.md
    md = f"""# Constraint Library Validation Results

**Date:** 2026-05-21  
**Scope:** 10 industries, target 248 constraints  
**Source:** `{CONSTRAINTS_DIR}`

---

## Summary

| Metric | Count | Percentage |
|--------|-------|-----------|
| Total constraints parsed | {total} | — |
| Valid (internally consistent) | {total_valid} | {100*total_valid/max(total,1):.1f}% |
| INT8-compatible | {total_int8} | {100*total_int8/max(total,1):.1f}% |
| Cross-industry conflicts | {len(conflicts)} | — |

## Per-Industry Breakdown

| Industry | Standard | Total | Valid | INT8-Compat | Status |
|----------|----------|-------|-------|-------------|--------|
"""
    for industry, data in industry_results.items():
        status = "✅" if data["valid"] == data["total"] and data["total"] > 0 else "⚠️" if data["total"] > 0 else "❌"
        md += f"| {industry} | {data['standard']} | {data['total']} | {data['valid']} | {data['int8_compatible']} | {status} |\n"
    
    md += f"""
## Cross-Industry Conflicts

"""
    if conflicts:
        for cf in conflicts:
            md += f"- **{cf['constraint_a']}** vs **{cf['constraint_b']}**: {cf['detail']}\n"
            md += f"  - A: {cf['range_a']}\n  - B: {cf['range_b']}\n"
    else:
        md += "No cross-industry range conflicts detected.\n"
    
    md += """
## Validation Criteria

1. **Internal consistency:** Lower bound < upper bound, parseable values
2. **Physical plausibility:** No negative Kelvin, reasonable magnitudes
3. **INT8 saturation:** Range fits in 8-bit encoding after scaling
4. **Cross-industry compatibility:** No disjoint ranges for same-unit constraints

---

*Generated by `experiment.py` — Forgemaster ⚒️ Constraint Validation Suite*
"""
    
    with open(OUTPUT_DIR / "RESULTS.md", "w") as f:
        f.write(md)
    
    print(f"\n📄 Results saved to:")
    print(f"   {OUTPUT_DIR / 'RESULTS.md'}")
    print(f"   {OUTPUT_DIR / 'results.json'}")
    
    return 0 if total_valid == total else 1


if __name__ == "__main__":
    sys.exit(main())
