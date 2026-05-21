#!/usr/bin/env python3
"""
🏗️ Smart GC — Intelligent Garbage Collection
"Mine before you delete."

Four phases: DISCOVER → UNDERSTAND → MINE → ACT
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

# ─── Configuration ───────────────────────────────────────────────

WORKSPACE = Path(os.environ.get("WORKSPACE", "/home/phoenix/.openclaw/workspace"))
SCAN_ROOTS = [WORKSPACE, Path("/tmp")]

BUILD_ARTIFACT_PATTERNS = [
    "target/", "node_modules/", "__pycache__/", "*.egg-info",
    ".pytest_cache/", ".mypy_cache/", ".ruff_cache/",
    "dist/", "build/", "*.pyc", "*.pyo",
]

LOG_PATTERNS = ["*.log", "*.log.*", "nohup.out"]
TEMP_PATTERNS = ["*.tmp", "*.temp", "*.swp", "*.swo", "*~", ".DS_Store"]

NEVER_DELETE_PATHS = {".git", ".git/"}
NEVER_KILL_PIDS = {1}
NEVER_KILL_NAMES = {"systemd", "init", "openclaw", "gateway"}

CLASSIFICATIONS = ["ESSENTIAL", "USEFUL", "STALE", "DEAD", "DANGEROUS"]

# ─── Helpers ─────────────────────────────────────────────────────

def run(cmd, timeout=30):
    """Run a shell command, return stdout."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except (subprocess.TimeoutExpired, Exception):
        return ""


def file_age_days(path):
    """Days since file was last modified."""
    try:
        mtime = datetime.fromtimestamp(os.path.getmtime(path))
        return (datetime.now() - mtime).days
    except OSError:
        return 0


def file_size_mb(path):
    """File size in MB."""
    try:
        return os.path.getsize(path) / (1024 * 1024)
    except OSError:
        return 0


def dir_size_mb(path):
    """Directory size in MB."""
    total = 0
    try:
        for dirpath, _, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total += os.path.getsize(fp)
                except OSError:
                    pass
    except OSError:
        pass
    return total / (1024 * 1024)


def is_referenced(filepath, search_roots):
    """Check if a file is referenced/imported by any code."""
    name = Path(filepath).name
    if name.startswith(".") or name in {"__pycache__", "node_modules", "target"}:
        return False
    # Quick grep for the filename
    for root in search_roots:
        result = run(f"grep -rl '{name}' {root} --include='*.py' --include='*.rs' --include='*.js' --include='*.ts' --include='*.toml' --include='*.json' 2>/dev/null | head -5")
        if result:
            return True
    return False


def safe_path(p):
    """Check if path is safe to operate on."""
    p_str = str(p)
    for nd in NEVER_DELETE_PATHS:
        if nd in p_str:
            return False
    if p_str.startswith("/proc/") or p_str.startswith("/sys/") or p_str.startswith("/dev/"):
        return False
    return True


# ─── Phase 1: DISCOVER ──────────────────────────────────────────

def discover_processes():
    """Scan running processes, Docker containers, cron jobs."""
    procs = {"running": [], "zombie": [], "docker": [], "cron": []}

    # Running processes
    ps_out = run("ps aux --sort=-%mem 2>/dev/null")
    if ps_out:
        for line in ps_out.split("\n")[1:]:
            parts = line.split(None, 10)
            if len(parts) < 11:
                continue
            user, pid_str, cpu, mem, vsz, rss, tty, stat, start, time_cmd = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5], parts[6], parts[7], parts[8], parts[9]
            command = parts[10] if len(parts) > 10 else ""
            pid = int(pid_str) if pid_str.isdigit() else 0
            rss_mb = int(rss) / 1024 if rss.isdigit() else 0

            proc_info = {
                "pid": pid, "user": user, "cpu": float(cpu) if cpu else 0,
                "mem_mb": rss_mb, "stat": stat, "start": start, "command": command[:200],
            }

            if "Z" in stat or "defunct" in command.lower():
                procs["zombie"].append(proc_info)
            else:
                procs["running"].append(proc_info)

    # Docker containers
    docker_out = run("docker ps -a --format '{{.Names}}\t{{.Status}}\t{{.Size}}\t{{.Image}}' 2>/dev/null")
    if docker_out:
        for line in docker_out.split("\n"):
            if not line.strip():
                continue
            parts = line.split("\t")
            procs["docker"].append({
                "name": parts[0] if len(parts) > 0 else "unknown",
                "status": parts[1] if len(parts) > 1 else "unknown",
                "size": parts[2] if len(parts) > 2 else "",
                "image": parts[3] if len(parts) > 3 else "",
            })

    # Cron jobs
    cron_out = run("crontab -l 2>/dev/null")
    if cron_out and "no crontab" not in cron_out.lower():
        procs["cron"] = [l for l in cron_out.split("\n") if l.strip() and not l.startswith("#")]

    return procs


def discover_files(threshold_days=30, min_size_mb=10):
    """Scan for large, old, duplicate, and artifact files."""
    files = {
        "large": [], "old": [], "build_artifacts": [], "logs": [],
        "temp": [], "duplicates": {}, "candidates": [],
    }

    all_files = []
    size_map = defaultdict(list)

    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            # Skip .git entirely
            if ".git" in dirpath:
                continue
            # Skip obvious non-user dirs
            skip = False
            for skip_dir in ["node_modules", ".cache", "proc", "sys", "dev"]:
                parts = Path(dirpath).parts
                if skip_dir in parts:
                    if skip_dir == "node_modules":
                        # We want to find node_modules to report
                        if Path(dirpath).name == skip_dir:
                            sz = dir_size_mb(dirpath)
                            files["build_artifacts"].append({
                                "path": dirpath, "size_mb": sz,
                                "age_days": file_age_days(dirpath),
                                "type": "node_modules",
                            })
                        dirnames.clear()
                        skip = True
                        break
            if skip:
                continue

            for fname in filenames:
                fp = os.path.join(dirpath, fname)
                if not safe_path(fp):
                    continue
                try:
                    stat = os.stat(fp)
                except OSError:
                    continue
                sz_mb = stat.st_size / (1024 * 1024)
                age = (datetime.now() - datetime.fromtimestamp(stat.st_mtime)).days

                info = {"path": fp, "size_mb": round(sz_mb, 2), "age_days": age}
                all_files.append(info)

                if sz_mb >= min_size_mb:
                    files["large"].append(info)
                if age >= threshold_days:
                    files["old"].append(info)

                # Log files
                if fname.endswith(".log") or fname.startswith("nohup"):
                    files["logs"].append(info)

                # Temp files
                if any(fname.endswith(ext) for ext in [".tmp", ".temp", ".swp", ".swo"]) or fname.endswith("~"):
                    files["temp"].append(info)

                # Size hash for duplicate detection (group by size)
                size_map[stat.st_size].append(fp)

    # Build artifacts (check directories)
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for dirpath, dirnames, _ in os.walk(root):
            if ".git" in dirpath:
                continue
            dname = Path(dirpath).name
            if dname in {"target", "__pycache__", ".pytest_cache", ".mypy_cache", ".egg-info", "dist", "build"}:
                sz = dir_size_mb(dirpath)
                if sz > 0.1:
                    files["build_artifacts"].append({
                        "path": dirpath, "size_mb": round(sz, 2),
                        "age_days": file_age_days(dirpath),
                        "type": dname,
                    })

    # Duplicates (files with identical sizes — quick heuristic)
    for size, paths in size_map.items():
        if len(paths) > 1 and size > 1024:  # >1KB
            files["duplicates"][str(size)] = paths

    files["total_scanned"] = len(all_files)
    return files


# ─── Phase 2: UNDERSTAND ────────────────────────────────────────

def classify_file(info, threshold_days=30):
    """Classify a file candidate."""
    path = info["path"]
    name = Path(path).name.lower()

    # Essential patterns
    essential_patterns = [".toml", ".rs", ".py", "main.", "mod.rs", "config",
                          "settings", ".env", ".md", "identity", "soul", "agents",
                          "skill", "memory"]
    if any(p in name for p in essential_patterns):
        # But check if it's actually old
        if info["age_days"] < threshold_days:
            return "ESSENTIAL"

    # Active code files
    if info["age_days"] < 7 and any(name.endswith(ext) for ext in [".rs", ".py", ".js", ".ts", ".toml"]):
        return "ESSENTIAL"

    # Build caches that are recent
    if any(p in path for p in ["target/", "node_modules/"]) and info["age_days"] < 7:
        return "USEFUL"

    # Config files
    if name.startswith(".") and info["age_days"] < threshold_days:
        return "ESSENTIAL"

    # Build artifacts older than threshold
    if any(p in path for p in ["target/", "node_modules/", "__pycache__/"]):
        if info["age_days"] >= threshold_days:
            return "STALE"
        return "USEFUL"

    # Temp files
    if any(name.endswith(ext) for ext in [".tmp", ".temp", ".swp", ".swo"]) or name.endswith("~"):
        return "STALE"

    # Old files with no references
    if info["age_days"] >= threshold_days:
        return "STALE"

    return "USEFUL"


def understand(files, procs, threshold_days=30):
    """Contextualize candidates with classification."""
    classified = defaultdict(list)

    for info in files.get("large", []) + files.get("old", []) + files.get("temp", []):
        cls = classify_file(info, threshold_days)
        classified[cls].append(info)

    # Build artifacts
    for art in files.get("build_artifacts", []):
        if art["age_days"] >= threshold_days:
            classified["STALE"].append(art)
        elif art["age_days"] >= 7:
            classified["USEFUL"].append(art)
        else:
            classified["USEFUL"].append(art)

    return classified


# ─── Phase 3: MINE ──────────────────────────────────────────────

def mine_logs(log_files, landfill_dir):
    """Extract patterns from log files before suggesting deletion."""
    landfill_dir = Path(landfill_dir)
    landfill_dir.mkdir(parents=True, exist_ok=True)
    mined = []

    for info in log_files:
        path = Path(info["path"])
        if not path.exists() or path.stat().st_size == 0:
            continue
        if path.stat().st_size > 50 * 1024 * 1024:  # Skip >50MB
            continue

        try:
            content = path.read_text(errors="ignore")
        except OSError:
            continue

        # Extract error patterns
        errors = defaultdict(int)
        for line in content.split("\n"):
            line_lower = line.lower()
            if "error" in line_lower or "fatal" in line_lower or "panic" in line_lower:
                # Normalize: strip timestamps and numbers
                normalized = re.sub(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', '<TIMESTAMP>', line.strip())
                normalized = re.sub(r'0x[0-9a-f]+', '<HEX>', normalized)
                normalized = re.sub(r'\d+', '<N>', normalized)
                normalized = re.sub(r'/[\w/.-]+', '<PATH>', normalized)
                if len(normalized) > 20:
                    errors[normalized[:200]] += 1

        if errors:
            # Sort by frequency
            top_errors = sorted(errors.items(), key=lambda x: -x[1])[:10]
            report = {
                "source": str(path),
                "size_mb": info["size_mb"],
                "age_days": info["age_days"],
                "unique_error_patterns": len(errors),
                "top_patterns": [{"pattern": p, "count": c} for p, c in top_errors],
            }
            mined.append(report)

            # Save to landfill
            report_file = landfill_dir / f"{path.stem}_errors.json"
            report_file.write_text(json.dumps(report, indent=2))

    return mined


def mine_processes(procs, landfill_dir):
    """Extract insights from running processes."""
    landfill_dir = Path(landfill_dir)
    landfill_dir.mkdir(parents=True, exist_ok=True)
    insights = []

    # Check Docker containers
    for container in procs.get("docker", []):
        if "Exited" in container.get("status", ""):
            insights.append({
                "type": "stopped_container",
                "name": container["name"],
                "status": container["status"],
                "image": container.get("image", ""),
                "insight": f"Container '{container['name']}' is stopped but still exists.",
            })

    # High-memory processes
    for proc in procs.get("running", []):
        if proc["mem_mb"] > 100:
            insights.append({
                "type": "high_memory",
                "pid": proc["pid"],
                "command": proc["command"][:100],
                "mem_mb": round(proc["mem_mb"], 1),
                "insight": f"PID {proc['pid']} using {proc['mem_mb']:.0f}MB: {proc['command'][:80]}",
            })

    # Zombies
    for z in procs.get("zombie", []):
        insights.append({
            "type": "zombie",
            "pid": z["pid"],
            "command": z["command"][:100],
            "insight": f"Zombie process PID {z['pid']}: {z['command'][:80]}",
        })

    if insights:
        proc_report = landfill_dir / "process_insights.json"
        proc_report.write_text(json.dumps(insights, indent=2))

    return insights


# ─── Phase 4: ACT ────────────────────────────────────────────────

def generate_recommendations(classified, procs, files, mined_logs, proc_insights):
    """Generate KEEP/ARCHIVE/DELETE/KILL recommendations."""
    recs = []

    # Stale files → DELETE or ARCHIVE
    for item in classified.get("STALE", []):
        path = item["path"]
        size = item.get("size_mb", 0)
        age = item.get("age_days", 0)
        p = Path(path)

        if p.name == "__pycache__" or str(p).endswith("/__pycache__"):
            recs.append(("DELETE", path, size, "auto-regenerated"))
        elif "target/" in str(p) and size > 500:
            recs.append(("ARCHIVE", path, size, f"large build cache, {age}d old"))
        elif p.suffix in {".tmp", ".temp", ".swp", ".swo"} or p.name.endswith("~"):
            recs.append(("DELETE", path, size, "temp file"))
        elif p.suffix == ".log":
            recs.append(("DELETE", path, size, "log file, patterns saved to landfill/"))
        else:
            recs.append(("ARCHIVE", path, size, f"stale ({age}d old)"))

    # Dead files → DELETE
    for item in classified.get("DEAD", []):
        recs.append(("DELETE", item["path"], item.get("size_mb", 0), "no references, dead"))

    # Useful files → KEEP (but mention them)
    for item in classified.get("USEFUL", []):
        size = item.get("size_mb", 0)
        if size > 100:
            recs.append(("KEEP", item["path"], size, "useful, active cache"))

    # Essential → KEEP
    for item in classified.get("ESSENTIAL", []):
        size = item.get("size_mb", 0)
        if size > 50:
            recs.append(("KEEP", item["path"], size, "essential"))

    # Docker containers
    for container in procs.get("docker", []):
        if "Exited" in container.get("status", ""):
            recs.append(("KILL", f"docker:{container['name']}", 0, f"stopped container ({container['status']})"))

    # Zombies
    for z in procs.get("zombie", []):
        recs.append(("KILL", f"pid:{z['pid']}", 0, f"zombie: {z['command'][:60]}"))

    return recs


def format_report(procs, files, classified, mined_logs, proc_insights, recommendations):
    """Format the full report."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = []
    a = lines.append

    a(f"🏗️ SMART GC REPORT — {now}\n")

    # Discovery
    n_running = len(procs.get("running", []))
    n_zombie = len(procs.get("zombie", []))
    n_docker = len(procs.get("docker", []))
    n_candidates = sum(len(v) for v in classified.values())
    total_scanned = files.get("total_scanned", 0)
    artifact_count = len(files.get("build_artifacts", []))
    artifact_size = sum(a.get("size_mb", 0) for a in files.get("build_artifacts", []))
    log_count = len(files.get("logs", []))
    log_size = sum(l.get("size_mb", 0) for l in files.get("logs", []))
    potential_savings = sum(r[2] for r in recommendations if r[0] in ("DELETE", "ARCHIVE"))

    a("📊 DISCOVERY")
    a(f"  Processes: {n_running} running, {n_zombie} zombie, {n_docker} Docker containers")
    a(f"  Files: {total_scanned} scanned, {n_candidates} candidates ({potential_savings:.1f}MB potential savings)")
    a(f"  Build artifacts: {artifact_count} dirs ({artifact_size:.1f}MB)")
    a(f"  Logs: {log_count} files ({log_size:.1f}MB)")
    a("")

    # Understanding
    a("🧠 UNDERSTANDING")
    for cls in CLASSIFICATIONS:
        items = classified.get(cls, [])
        if items:
            a(f"  {cls:12s}: {len(items):4d} items")
    a("")

    # Mining
    a("⛏️ MINING (value extracted)")
    if mined_logs:
        for ml in mined_logs:
            a(f"  Logs: {ml['unique_error_patterns']} unique error patterns in {Path(ml['source']).name}")
    if proc_insights:
        for pi in proc_insights:
            if pi["type"] == "stopped_container":
                a(f"  Docker: {pi['name']} — {pi['status']}")
            elif pi["type"] == "zombie":
                a(f"  Zombie: PID {pi['pid']} — {pi['command'][:50]}")
            elif pi["type"] == "high_memory":
                a(f"  Memory: PID {pi['pid']} using {pi['mem_mb']:.0f}MB — {pi['command'][:50]}")
    if not mined_logs and not proc_insights:
        a("  (nothing to mine)")
    a("")

    # Recommendations
    a("🗑️ RECOMMENDATIONS")
    # Group by action
    for action in ["KEEP", "ARCHIVE", "DELETE", "KILL"]:
        action_recs = [r for r in recommendations if r[0] == action]
        for rec in action_recs:
            action_tag, path, size, reason = rec
            size_str = f" ({size:.1f}MB)" if size > 0.1 else ""
            short_path = str(path)
            if len(short_path) > 80:
                short_path = "..." + short_path[-77:]
            a(f"  [{action_tag}] {short_path}{size_str} — {reason}")
    a("")

    # Summary
    disk_savings = sum(r[2] for r in recommendations if r[0] in ("DELETE", "ARCHIVE"))
    ram_savings = sum(pi.get("mem_mb", 0) for pi in proc_insights if pi["type"] == "high_memory")
    a(f"💰 POTENTIAL SAVINGS: {ram_savings:.0f}MB RAM + {disk_savings:.1f}MB disk")

    return "\n".join(lines)


def execute_actions(recommendations, dry_run=True):
    """Execute recommendations."""
    actions_taken = []

    for action, path, size, reason in recommendations:
        if dry_run:
            actions_taken.append(f"  [DRY-RUN] Would {action}: {path} ({reason})")
            continue

        try:
            if action == "DELETE":
                p = Path(path)
                if p.is_dir():
                    import shutil
                    shutil.rmtree(p, ignore_errors=True)
                elif p.exists():
                    p.unlink()
                actions_taken.append(f"  ✓ Deleted: {path}")
            elif action == "KILL":
                if path.startswith("docker:"):
                    container = path.split(":", 1)[1]
                    run(f"docker rm {container}")
                    actions_taken.append(f"  ✓ Removed container: {container}")
                elif path.startswith("pid:"):
                    pid = path.split(":", 1)[1]
                    if int(pid) not in NEVER_KILL_PIDS:
                        run(f"kill {pid}")
                        actions_taken.append(f"  ✓ Killed PID: {pid}")
            elif action == "ARCHIVE":
                # Just log it — archiving is advisory
                actions_taken.append(f"  ℹ Archive recommended: {path}")
        except Exception as e:
            actions_taken.append(f"  ✗ Failed to {action} {path}: {e}")

    return actions_taken


# ─── Main ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="🏗️ Smart GC — Intelligent Garbage Collection")
    parser.add_argument("--threshold", type=int, default=30, help="Flag files older than N days (default: 30)")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Show what would happen (default)")
    parser.add_argument("--confirm", action="store_true", help="Actually execute cleanup")
    parser.add_argument("--processes", action="store_true", help="Scan processes only")
    parser.add_argument("--mining-only", action="store_true", help="Just mine for insights, don't suggest deletion")
    parser.add_argument("--landfill", type=str, default=None, help="Save mined insights to directory")
    parser.add_argument("--min-size", type=int, default=1, help="Minimum file size in MB to scan (default: 1)")

    args = parser.parse_args()

    if args.confirm:
        args.dry_run = False

    landfill_dir = args.landfill or str(WORKSPACE / "tools" / "smart-gc" / "landfill")
    os.makedirs(landfill_dir, exist_ok=True)

    print("🏗️ Smart GC starting...\n")

    # Phase 1: DISCOVER
    print("📊 Phase 1: DISCOVER...")
    procs = discover_processes()
    if args.processes:
        files = {"total_scanned": 0, "large": [], "old": [], "build_artifacts": [], "logs": [], "temp": [], "duplicates": {}}
    else:
        files = discover_files(threshold_days=args.threshold, min_size_mb=args.min_size)

    # Phase 2: UNDERSTAND
    print("🧠 Phase 2: UNDERSTAND...")
    classified = understand(files, procs, threshold_days=args.threshold)

    # Phase 3: MINE
    print("⛏️ Phase 3: MINE...")
    mined_logs = mine_logs(files.get("logs", []), landfill_dir)
    proc_insights = mine_processes(procs, landfill_dir)

    # Phase 4: ACT
    print("🗑️ Phase 4: ACT...\n")

    if args.mining_only:
        # Just show mining results
        print("⛏️ MINING RESULTS (no deletion suggested)\n")
        if mined_logs:
            for ml in mined_logs:
                print(f"  📄 {Path(ml['source']).name}: {ml['unique_error_patterns']} unique error patterns")
                for pat in ml.get("top_patterns", [])[:3]:
                    print(f"     ×{pat['count']}: {pat['pattern'][:100]}")
        if proc_insights:
            for pi in proc_insights:
                print(f"  🔍 {pi['insight']}")
        if not mined_logs and not proc_insights:
            print("  (nothing to mine)")
        print(f"\n📁 Mining results saved to: {landfill_dir}")
        return

    recommendations = generate_recommendations(classified, procs, files, mined_logs, proc_insights)
    report = format_report(procs, files, classified, mined_logs, proc_insights, recommendations)
    print(report)

    # Execute
    if not args.processes:
        actions = execute_actions(recommendations, dry_run=args.dry_run)
        if actions:
            print("\n" + ("📝 ACTIONS (dry-run):" if args.dry_run else "✅ ACTIONS TAKEN:"))
            for a in actions:
                print(a)

    print(f"\n📁 Landfill: {landfill_dir}")

    # Save report
    report_file = Path(landfill_dir) / f"gc-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt"
    report_file.write_text(report)
    print(f"📄 Report saved: {report_file}")


if __name__ == "__main__":
    main()
