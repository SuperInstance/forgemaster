#!/usr/bin/env python3
"""
Temporal Compression — run daily at midnight via cron.
Takes raw tick logs and compresses older data.
Stores variance summaries instead of raw ticks for aged data.
"""

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

TICKER_DIR = Path(os.path.expanduser("~/.openclaw/workspace/.keeper/ticker"))
RAW_DIR = TICKER_DIR / "raw"
COMPRESSED_DIR = TICKER_DIR / "compressed"
COMPRESSED_DIR.mkdir(parents=True, exist_ok=True)

def parse_tick(line):
    """Parse a raw tick line into a dict."""
    try:
        parts = line.split(" | ")
        return {
            "timestamp": parts[0].strip(),
            "cpu": float(re.search(r'CPU:([\d.]+)%', line).group(1)),
            "mem_pct": float(re.search(r'MEM:\d+/\d+MB\(([\d.]+)%\)', line).group(1)),
            "disk_pct": int(re.search(r'DISK:(\d+)%', line).group(1)),
            "load": float(re.search(r'LOAD:([\d.]+)', line).group(1)),
        }
    except:
        return None

def compress_day(date_str, ticks):
    """Compress a day's ticks into a summary."""
    if not ticks:
        return None
    
    cpus = [t["cpu"] for t in ticks if t]
    mems = [t["mem_pct"] for t in ticks if t]
    loads = [t["load"] for t in ticks if t]
    
    if not cpus:
        return None
    
    summary = {
        "date": date_str,
        "ticks": len(ticks),
        "cpu": {
            "avg": round(sum(cpus)/len(cpus), 1),
            "peak": round(max(cpus), 1),
            "min": round(min(cpus), 1),
            "peak_time": ticks[cpus.index(max(cpus))]["timestamp"] if ticks else None,
        },
        "memory": {
            "avg": round(sum(mems)/len(mems), 1),
            "peak": round(max(mems), 1),
            "min": round(min(mems), 1),
        },
        "load": {
            "avg": round(sum(loads)/len(loads), 2),
            "peak": round(max(loads), 2),
        },
        "anomalies": [],
    }
    
    # Flag anomalies (values > 2x average)
    if max(cpus) > sum(cpus)/len(cpus) * 2:
        summary["anomalies"].append(f"CPU spike to {max(cpus)}% (avg {sum(cpus)/len(cpus):.0f}%)")
    if max(mems) > sum(mems)/len(mems) * 2:
        summary["anomalies"].append(f"Memory spike to {max(mems)}% (avg {sum(mems)/len(mems):.0f}%)")
    
    return summary

def main():
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Compress yesterday's raw data
    raw_file = RAW_DIR / f"{yesterday}.log"
    if raw_file.exists():
        lines = raw_file.read_text().strip().split("\n")
        ticks = [parse_tick(l) for l in lines]
        summary = compress_day(yesterday, ticks)
        
        if summary:
            out_file = COMPRESSED_DIR / f"{yesterday}.json"
            out_file.write_text(json.dumps(summary, indent=2))
            print(f"Compressed {len(ticks)} ticks for {yesterday} → {out_file}")
            
            # Keep raw for 7 days, then delete
            week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            old_raw = RAW_DIR / f"{week_ago}.log"
            if old_raw.exists():
                old_raw.unlink()
                print(f"Deleted raw ticks older than 7 days: {week_ago}")
    
    # Compress week-old daily summaries into weekly
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    # TODO: weekly/monthly rollup
    
    print(f"Compression complete for {yesterday}")

if __name__ == "__main__":
    main()
