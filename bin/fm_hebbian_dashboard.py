#!/usr/bin/env python3
"""Forgemaster Hebbian Dashboard — real-time ASCII visualization.

Connects to:
  - PLATO server on :8848
  - Hebbian service on :8849

Shows:
  - Cluster visualization (ASCII art)
  - Conservation compliance
  - Top Hebbian connections
  - Emergent stages
  - Updates every 5 seconds

Usage:
    python3 bin/fm_hebbian_dashboard.py
    python3 bin/fm_hebbian_dashboard.py --interval 3
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from collections import defaultdict


HEBBIAN_URL = "http://localhost:8849"
PLATO_URL = "http://localhost:8848"
INTERVAL = 5  # seconds


# ── Colors (ANSI) ──
class C:
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    RESET = "\033[0m"


def api_get(url: str, timeout: int = 5) -> dict:
    try:
        return json.loads(urllib.request.urlopen(url, timeout=timeout).read())
    except Exception as e:
        return {"error": str(e)}


def clear_screen():
    os.system("clear" if os.name != "nt" else "cls")


def bar(value: float, width: int = 30, filled: str = "█", empty: str = "░") -> str:
    filled_len = int(abs(value) * width)
    return filled * filled_len + empty * (width - filled_len)


def stage_label(stage: int) -> str:
    labels = {0: f"{C.DIM}Cold{C.RESET}", 1: f"{C.RED}Exploring{C.RESET}",
              3: f"{C.YELLOW}Operational{C.RESET}", 4: f"{C.GREEN}Mastery{C.RESET}"}
    return labels.get(stage, f"{C.DIM}?{C.RESET}")


def render_dashboard(hebbian: dict, plato: dict, clusters: list,
                     weights: dict, stages: dict, conservation: dict):
    clear_screen()
    now = time.strftime("%H:%M:%S")
    
    print(f"{C.BOLD}{C.CYAN}⚒️  FORGEMASTER HEBBIAN DASHBOARD{C.RESET}  {C.DIM}{now}{C.RESET}")
    print(f"{C.DIM}{'━' * 60}{C.RESET}")
    
    # ── Status line ──
    status = hebbian.get("status", "?")
    rooms = hebbian.get("rooms", 0)
    events = hebbian.get("flow_events", 0)
    kernel_updates = hebbian.get("kernel_updates", 0)
    compliance = hebbian.get("compliance_rate", 0)
    
    status_color = C.GREEN if status == "running" else C.RED
    print(f"  PLATO: {plato.get('status', '?')}  |  "
          f"Hebbian: {status_color}{status}{C.RESET}  |  "
          f"Rooms: {C.BOLD}{rooms}{C.RESET}")
    
    # ── Conservation ──
    cons = conservation.get("conservation", {})
    gamma = cons.get("gamma", 0)
    H = cons.get("H", 0)
    gamma_H = cons.get("sum", 0)
    predicted = cons.get("predicted", 0)
    deviation = cons.get("deviation", 0)
    conserved = cons.get("conserved", False)
    
    cons_marker = f"{C.GREEN}✓ CONSERVED{C.RESET}" if conserved else f"{C.RED}✗ VIOLATION{C.RESET}"
    
    print(f"\n{C.BOLD}  CONSERVATION LAW{C.RESET}  {cons_marker}")
    print(f"  ┌─────────────────────────────────────────────────┐")
    
    # γ bar
    gamma_bar = bar(gamma, 20)
    print(f"  │ γ (algebraic)  {gamma_bar} {gamma:.4f} │")
    
    # H bar
    H_bar = bar(H, 20)
    print(f"  │ H (entropy)    {H_bar} {H:.4f} │")
    
    # γ+H
    target_bar_width = 20
    offset = int(deviation * 100)
    pointer_pos = min(max(10 + offset, 0), 20)
    ruler = "─" * pointer_pos + "▲" + "─" * (target_bar_width - pointer_pos - 1)
    
    dev_color = C.GREEN if abs(deviation) < 0.05 else (C.YELLOW if abs(deviation) < 0.10 else C.RED)
    print(f"  │ γ+H = {gamma_H:.4f}  target = {predicted:.4f}         │")
    print(f"  │ {dev_color}deviation = {deviation:+.4f}{C.RESET}                        │")
    print(f"  │ [{ruler}]  │")
    print(f"  │ Compliance: {compliance:.1%}  ({kernel_updates} updates)   │")
    print(f"  └─────────────────────────────────────────────────┘")
    
    # ── Weight Matrix ──
    ws = weights.get("weight_stats", {})
    top_conn = weights.get("top_connections", [])[:8]
    nonzero = ws.get("nonzero", 0)
    total = rooms * rooms if rooms > 0 else 1
    density = nonzero / total if total > 0 else 0
    
    print(f"\n{C.BOLD}  HEBBIAN WEIGHT MATRIX{C.RESET}  density={density:.1%}  "
          f"max={ws.get('max', 0):.4f}  mean={ws.get('mean', 0):.4f}")
    
    print(f"  ┌─────────────────────────────────────────────────┐")
    for conn in top_conn:
        src = conn.get("source", "?")[:20].ljust(20)
        dst = conn.get("dest", "?")[:15].ljust(15)
        w = conn.get("weight", 0)
        w_bar = bar(w / max(ws.get("max", 1), 0.001), 10)
        print(f"  │ {C.CYAN}{src}{C.RESET} → {C.MAGENTA}{dst}{C.RESET} {w_bar} {w:.4f} │")
    print(f"  └─────────────────────────────────────────────────┘")
    
    # ── Clusters ──
    n_clusters = len(clusters)
    print(f"\n{C.BOLD}  ROOM CLUSTERS ({n_clusters}){C.RESET}")
    
    for cluster in clusters:
        cid = cluster.get("cluster_id", 0)
        room_list = cluster.get("rooms", [])
        size = cluster.get("size", 0)
        internal = cluster.get("avg_internal_strength", 0)
        dominant = cluster.get("dominant_tile_types", [])
        
        print(f"  ┌─ Cluster {cid} ({size} rooms, strength={internal:.4f}) ────────────┐")
        
        # ASCII cluster visualization
        cols = 3
        for i in range(0, len(room_list), cols):
            row_rooms = room_list[i:i+cols]
            room_str = "  ".join(f"{C.BOLD}{r}{C.RESET}" for r in row_rooms)
            print(f"  │  {room_str}")
        
        if dominant:
            print(f"  │  {C.DIM}types: {', '.join(dominant)}{C.RESET}")
        print(f"  └─────────────────────────────────────────────────┘")
    
    # ── Stages ──
    print(f"\n{C.BOLD}  EMERGENT STAGES{C.RESET}")
    print(f"  ┌─────────────────────────────────────────────────┐")
    for room, stage in sorted(stages.items(), key=lambda x: -x[1]):
        stage_str = stage_label(stage)
        print(f"  │  {room[:25]:25s} Stage {stage} {stage_str}")
    print(f"  └─────────────────────────────────────────────────┘")
    
    # ── Footer ──
    print(f"\n{C.DIM}  PLATO: {plato.get('tiles', 0)} tiles across {plato.get('rooms', 0)} rooms  "
          f"│  Hebbian: {events} flow events  │  Ctrl+C to exit{C.RESET}")


def main():
    parser = argparse.ArgumentParser(description="Forgemaster Hebbian Dashboard")
    parser.add_argument("--interval", type=int, default=INTERVAL, help="Refresh interval (seconds)")
    parser.add_argument("--once", action="store_true", help="Render once and exit")
    args = parser.parse_args()
    
    print(f"Connecting to PLATO (:8848) and Hebbian (:8849)...")
    
    try:
        while True:
            hebbian = api_get(f"{HEBBIAN_URL}/status")
            plato = api_get(f"{PLATO_URL}/status")
            clusters = api_get(f"{HEBBIAN_URL}/clusters")
            weights = api_get(f"{HEBBIAN_URL}/weights")
            stages = api_get(f"{HEBBIAN_URL}/stages")
            conservation = api_get(f"{HEBBIAN_URL}/conservation")
            
            if "error" in hebbian:
                print(f"Hebbian service error: {hebbian['error']}")
                print(f"Make sure fleet_hebbian_service.py is running on :8849")
                if args.once:
                    sys.exit(1)
                time.sleep(args.interval)
                continue
            
            render_dashboard(hebbian, plato, clusters, weights, stages, conservation)
            
            if args.once:
                break
            
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print(f"\n{C.DIM}Dashboard stopped.{C.RESET}")


if __name__ == "__main__":
    main()
