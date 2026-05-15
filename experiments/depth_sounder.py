#!/usr/bin/env python3
"""
depth_sounder.py — Cross-Temporal Pattern Mining
=================================================
Reads across ALL experiment logs, session notes, and PLATO data.
Finds patterns that only emerge when you have enough pings.

The fishing metaphor:
- A single ping = one experiment result (noise in isolation)
- A season of pings = session's worth of data (local patterns)
- Years of seasons = cross-session comparison (migration patterns)

This script does the cross-season comparison:
1. Index all raw logs by (model, task, date)
2. Find patterns that repeat across sessions
3. Find patterns that CHANGE across sessions (the currents)
4. Flag data ready for synthesis → structured form
5. Flag structured data safe for archival
6. NEVER prune raw logs prematurely

Author: Forgemaster ⚒️
"""

import json, re, os, time
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

WORKSPACE = Path("/home/phoenix/.openclaw/workspace")
EXPERIMENTS = WORKSPACE / "experiments"
MEMORY = WORKSPACE / "memory"
LOGS_DIR = WORKSPACE / "logs"

# ═══════════════════════════════════════════════════════════════
# PHASE 1: Index all raw data
# ═══════════════════════════════════════════════════════════════

def index_experiment_files():
    """Scan experiments/ for all result files and index their content."""
    index = []
    
    for f in sorted(EXPERIMENTS.glob("*.md")):
        content = f.read_text()
        stat = f.stat()
        
        # Extract date from filename or content
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', f.stem)
        date = date_match.group(1) if date_match else datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d")
        
        # Extract model mentions
        models = re.findall(r'(?:llama|qwen|gemma|phi4?|deepseek|glm|seed|hermes|kimi|nemotron)[\w.-]*', content.lower())
        
        # Extract percentage rates (N% patterns)
        rates = re.findall(r'(\d+)%', content)
        
        # Extract finding references (R1, R2, etc)
        findings = re.findall(r'R(\d+)', content)
        
        # Extract variable names
        variables = re.findall(r'(?:training_coverage|dependency_width|coefficient_familiarity|input_magnitude|n_heads|extraction)', content)
        
        # Extract residue classes
        residues = re.findall(r'(ECHO|PARTIAL|CORRECT|NEAR|OTHER|SIGN)', content)
        
        entry = {
            "file": f.name,
            "path": str(f),
            "date": date,
            "size_bytes": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "models": Counter(models),
            "rates_mentioned": [int(r) for r in rates],
            "findings": [int(r) for r in findings],
            "variables": Counter(variables),
            "residues": Counter(residues),
            "is_result": any(kw in f.name.lower() for kw in ['result', 'study', 'experiment', 'spoke', 'campaign']),
            "is_paper": f.name.startswith('paper-'),
            "is_synthesis": any(kw in f.name.lower() for kw in ['synthesis', 'summary', 'portrait', 'ground-truth']),
        }
        entry["max_finding"] = max(entry["findings"]) if entry["findings"] else 0
        index.append(entry)
    
    return index

def index_memory_files():
    """Index memory/ directory for session logs."""
    index = []
    
    for f in sorted(MEMORY.glob("*.md")):
        content = f.read_text()
        stat = f.stat()
        
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', f.stem)
        date = date_match.group(1) if date_match else "unknown"
        
        models = re.findall(r'(?:llama|qwen|gemma|phi4?|deepseek|glm|seed|hermes|kimi|nemotron)[\w.-]*', content.lower())
        findings = re.findall(r'R(\d+)', content)
        
        entry = {
            "file": f.name,
            "date": date,
            "size_bytes": stat.st_size,
            "models": Counter(models),
            "findings": [int(r) for r in findings],
            "session_count": content.count("## Session"),
            "has_experiments": "trials" in content.lower() or "experiment" in content.lower(),
        }
        index.append(entry)
    
    return index


# ═══════════════════════════════════════════════════════════════
# PHASE 2: Cross-temporal pattern mining
# ═══════════════════════════════════════════════════════════════

def find_cross_session_patterns(exp_index, mem_index):
    """Find patterns that emerge across multiple sessions."""
    patterns = []
    
    # Pattern 1: Models that appear across multiple days
    model_days = defaultdict(set)
    for entry in exp_index:
        for model in entry["models"]:
            model_days[model].add(entry["date"])
    
    for model, days in sorted(model_days.items(), key=lambda x: -len(x[1])):
        if len(days) > 1:
            patterns.append({
                "type": "cross_session_model",
                "model": model,
                "days_seen": sorted(days),
                "n_days": len(days),
                "depth": len(days),
                "note": f"{model} appears across {len(days)} days — enough for temporal analysis"
            })
    
    # Pattern 2: Findings that accumulate over time
    finding_progression = defaultdict(list)
    for entry in mem_index:
        for f in entry["findings"]:
            finding_progression[f].append(entry["date"])
    
    # Pattern 3: Variables discovered across sessions
    var_cooccurrence = defaultdict(lambda: defaultdict(int))
    for entry in exp_index:
        vars_present = list(entry["variables"].keys())
        for i, v1 in enumerate(vars_present):
            for v2 in vars_present[i+1:]:
                var_cooccurrence[v1][v2] += 1
                var_cooccurrence[v2][v1] += 1
    
    for v1, neighbors in var_cooccurrence.items():
        for v2, count in neighbors.items():
            if count > 1:
                patterns.append({
                    "type": "variable_cooccurrence",
                    "variables": [v1, v2],
                    "cooccurrence_count": count,
                    "note": f"{v1} and {v2} co-occur in {count} files — likely related"
                })
    
    # Pattern 4: Residue class distribution across time
    residue_timeline = defaultdict(lambda: defaultdict(int))
    for entry in exp_index:
        date = entry["date"]
        for residue, count in entry["residues"].items():
            residue_timeline[residue][date] += count
    
    # Pattern 5: Synthesis readiness
    unsynthesized = []
    for entry in exp_index:
        if entry["is_result"] and not entry["is_synthesis"] and not entry["is_paper"]:
            unsynthesized.append(entry)
    
    # Pattern 6: Papers that synthesize multiple findings
    paper_coverage = []
    for entry in exp_index:
        if entry["is_paper"]:
            paper_coverage.append({
                "file": entry["file"],
                "findings_covered": sorted(set(entry["findings"])),
                "n_findings": len(set(entry["findings"])),
                "models_mentioned": list(entry["models"].keys()),
            })
    
    return {
        "cross_session_models": sorted(
            [p for p in patterns if p["type"] == "cross_session_model"],
            key=lambda x: -x["depth"]),
        "variable_relationships": [
            p for p in patterns if p["type"] == "variable_cooccurrence"],
        "residue_timeline": {k: dict(v) for k, v in residue_timeline.items()},
        "unsynthesized_results": len(unsynthesized),
        "unsynthesized_files": [u["file"] for u in unsynthesized],
        "paper_coverage": paper_coverage,
        "finding_progression": {str(k): v for k, v in finding_progression.items()},
    }


# ═══════════════════════════════════════════════════════════════
# PHASE 3: Depth classification
# ═══════════════════════════════════════════════════════════════

def classify_depth(exp_index, mem_index, patterns):
    """Classify each data source by its depth and archival readiness."""
    
    classifications = []
    
    total_data_bytes = sum(e["size_bytes"] for e in exp_index)
    total_files = len(exp_index)
    
    # Data volume assessment
    volume = {
        "total_experiment_files": total_files,
        "total_bytes": total_data_bytes,
        "total_mb": round(total_data_bytes / 1024 / 1024, 1),
        "memory_files": len(mem_index),
        "earliest_date": min((e["date"] for e in exp_index if e["date"] != "unknown"), default="unknown"),
        "latest_date": max((e["date"] for e in exp_index if e["date"] != "unknown"), default="unknown"),
    }
    
    # Depth tiers for each file
    for entry in exp_index:
        depth_score = 0
        notes = []
        
        # Cross-session presence
        for p in patterns.get("cross_session_models", []):
            if p["model"] in entry["models"]:
                depth_score += p["depth"]
                notes.append(f"model {p['model']} has {p['depth']}-day depth")
        
        # Findings density
        if entry["max_finding"] > 0:
            depth_score += 1
            notes.append(f"findings up to R{entry['max_finding']}")
        
        # Variable richness
        if len(entry["variables"]) > 1:
            depth_score += 1
            notes.append(f"{len(entry['variables'])} variables")
        
        # Synthesis status
        if entry["is_synthesis"]:
            depth_score += 2
            notes.append("SYNTHESIZED — candidate for archival")
        elif entry["is_paper"]:
            depth_score += 2
            notes.append("PAPER — creative synthesis")
        elif entry["is_result"]:
            notes.append("RAW RESULT — needs synthesis before archival")
        
        # Archival recommendation
        if entry["is_synthesis"] or entry["is_paper"]:
            archive_status = "ARCHIVE_READY"
        elif entry["is_result"] and depth_score >= 3:
            archive_status = "SYNTHESIZE_FIRST"
        else:
            archive_status = "KEEP_RAW"
        
        classifications.append({
            "file": entry["file"],
            "date": entry["date"],
            "depth_score": depth_score,
            "notes": notes,
            "archive_status": archive_status,
            "size_kb": round(entry["size_bytes"] / 1024, 1),
        })
    
    return {
        "volume": volume,
        "classifications": sorted(classifications, key=lambda x: -x["depth_score"]),
        "archive_ready": [c for c in classifications if c["archive_status"] == "ARCHIVE_READY"],
        "needs_synthesis": [c for c in classifications if c["archive_status"] == "SYNTHESIZE_FIRST"],
        "keep_raw": [c for c in classifications if c["archive_status"] == "KEEP_RAW"],
    }


# ═══════════════════════════════════════════════════════════════
# PHASE 4: Migration pattern detection (the fish finder)
# ═══════════════════════════════════════════════════════════════

def find_migration_patterns(patterns, depth_data):
    """
    The deep patterns that only emerge with temporal volume.
    Like fish migration: no single ping shows it, but seasons of pings reveal:
    - Where the fish go (model capability drift)
    - When they arrive (task-specific seasonality)  
    - How deep they swim (depth of computation over time)
    """
    migrations = []
    
    # Migration 1: Model capability progression across sessions
    # Are models getting better/worse at the same task over time?
    
    # Migration 2: Finding accumulation rate
    # How fast are we discovering new rocks?
    finding_prog = patterns.get("finding_progression", {})
    if finding_prog:
        max_finding = max(int(k) for k in finding_prog.keys())
        total_sessions = len(set(d for dates in finding_prog.values() for d in dates))
        rate = max_finding / max(total_sessions, 1)
        migrations.append({
            "type": "discovery_rate",
            "total_findings": max_finding,
            "sessions_with_findings": total_sessions,
            "findings_per_session": round(rate, 1),
            "note": f"Discovering ~{rate:.1f} new findings per session — {'accelerating' if rate > 3 else 'steady' if rate > 1 else 'converging'}"
        })
    
    # Migration 3: Variable discovery trajectory
    var_rels = patterns.get("variable_relationships", [])
    if var_rels:
        unique_vars = set()
        for vr in var_rels:
            unique_vars.update(vr["variables"])
        migrations.append({
            "type": "variable_constellation",
            "n_variables": len(unique_vars),
            "n_relationships": len(var_rels),
            "constellation": list(unique_vars),
            "note": f"{len(unique_vars)} variables with {len(var_rels)} relationships — {'sparse' if len(var_rels) < len(unique_vars) else 'interconnected'} network"
        })
    
    # Migration 4: Depth of analysis over time
    depth_class = depth_data.get("classifications", [])
    if depth_class:
        avg_depth = sum(c["depth_score"] for c in depth_class) / len(depth_class)
        max_depth = max(c["depth_score"] for c in depth_class)
        deep_files = [c["file"] for c in depth_class if c["depth_score"] >= 4]
        migrations.append({
            "type": "analysis_depth",
            "avg_depth_score": round(avg_depth, 1),
            "max_depth_score": max_depth,
            "deep_files_count": len(deep_files),
            "deepest_files": deep_files[:5],
            "note": f"Average depth {avg_depth:.1f}, max {max_depth}. {len(deep_files)} files with depth≥4."
        })
    
    return migrations


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def run_depth_sounder():
    print("╔════════════════════════════════════════════════════════════╗", flush=True)
    print("║  DEPTH SOUNDER — Cross-Temporal Pattern Mining            ║", flush=True)
    print("║  'A single ping is noise. A season reveals the current.'  ║", flush=True)
    print("╚════════════════════════════════════════════════════════════╝", flush=True)
    
    # Phase 1: Index
    print("\n📡 PHASE 1: Indexing all raw data", flush=True)
    exp_index = index_experiment_files()
    mem_index = index_memory_files()
    print(f"  Experiment files: {len(exp_index)}", flush=True)
    print(f"  Memory files: {len(mem_index)}", flush=True)
    print(f"  Total data: {sum(e['size_bytes'] for e in exp_index) / 1024:.0f} KB", flush=True)
    
    # Phase 2: Cross-temporal patterns
    print("\n🌊 PHASE 2: Cross-temporal pattern mining", flush=True)
    patterns = find_cross_session_patterns(exp_index, mem_index)
    
    print(f"  Cross-session models: {len(patterns['cross_session_models'])}", flush=True)
    for p in patterns['cross_session_models'][:5]:
        print(f"    {p['model']}: {p['n_days']} days ({', '.join(p['days_seen'][:3])})", flush=True)
    
    print(f"  Variable relationships: {len(patterns['variable_relationships'])}", flush=True)
    for vr in patterns['variable_relationships'][:5]:
        print(f"    {vr['variables'][0]} ↔ {vr['variables'][1]} ({vr['cooccurrence_count']} files)", flush=True)
    
    print(f"  Unsynthesized results: {patterns['unsynthesized_results']}", flush=True)
    print(f"  Papers written: {len(patterns['paper_coverage'])}", flush=True)
    
    # Phase 3: Depth classification
    print("\n📏 PHASE 3: Depth classification", flush=True)
    depth_data = classify_depth(exp_index, mem_index, patterns)
    
    print(f"  Volume: {depth_data['volume']['total_mb']} MB across {depth_data['volume']['total_experiment_files']} files", flush=True)
    print(f"  Date range: {depth_data['volume']['earliest_date']} → {depth_data['volume']['latest_date']}", flush=True)
    print(f"  Archive-ready: {len(depth_data['archive_ready'])} files", flush=True)
    print(f"  Needs synthesis: {len(depth_data['needs_synthesis'])} files", flush=True)
    print(f"  Keep raw: {len(depth_data['keep_raw'])} files", flush=True)
    
    print(f"\n  Top 10 by depth score:", flush=True)
    for c in depth_data["classifications"][:10]:
        status = {"ARCHIVE_READY": "📦", "SYNTHESIZE_FIRST": "📝", "KEEP_RAW": "📊"}[c["archive_status"]]
        print(f"    {status} {c['depth_score']:>2d} {c['file']:<40s} {c['size_kb']:>6.1f}KB", flush=True)
    
    # Phase 4: Migration patterns
    print("\n🐟 PHASE 4: Migration patterns (the fish finder)", flush=True)
    migrations = find_migration_patterns(patterns, depth_data)
    
    for m in migrations:
        print(f"\n  [{m['type']}]", flush=True)
        print(f"    {m['note']}", flush=True)
        for k, v in m.items():
            if k not in ("type", "note"):
                print(f"    {k}: {v}", flush=True)
    
    # ═══════════════════════════════════════════════════════════
    # ARCHIVAL POLICY (Casey's directive: don't prune too early)
    # ═══════════════════════════════════════════════════════════
    
    print("\n\n📋 ARCHIVAL POLICY", flush=True)
    print("=" * 60, flush=True)
    print("""
  RULE 1: NEVER delete raw logs within 7 days of creation.
         Novel patterns need volume to emerge.
  
  RULE 2: ONLY archive after synthesis into structured form.
         Raw result → MAP-OF-ROCKS entry → then archive raw.
  
  RULE 3: Cross-session data is MORE valuable than within-session.
         A finding that holds across 2 sessions > a finding from 1.
  
  RULE 4: Keep the pings. The migration pattern hasn't emerged yet.
         Like fish sonar: individual pings are noise, 
         seasons of pings reveal the thermocline.
  
  RULE 5: When in doubt, compress, don't delete.
         tar.gz the old raw logs. They're still there if needed.
""", flush=True)
    
    # Save full analysis
    output = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "experiment_index": [{"file": e["file"], "date": e["date"], "models": dict(e["models"]), "findings": e["findings"], "variables": dict(e["variables"])} for e in exp_index],
        "patterns": {
            "cross_session_models": patterns["cross_session_models"],
            "variable_relationships": patterns["variable_relationships"],
            "unsynthesized_count": patterns["unsynthesized_results"],
            "unsynthesized_files": patterns["unsynthesized_files"],
        },
        "depth": {
            "volume": depth_data["volume"],
            "archive_ready": len(depth_data["archive_ready"]),
            "needs_synthesis": len(depth_data["needs_synthesis"]),
            "keep_raw": len(depth_data["keep_raw"]),
        },
        "migrations": migrations,
    }
    
    outpath = EXPERIMENTS / "depth-sounder-report.json"
    with open(outpath, "w") as f:
        json.dump(output, f, indent=2)
    print(f"  Full report: {outpath}", flush=True)
    
    return output


if __name__ == "__main__":
    run_depth_sounder()
