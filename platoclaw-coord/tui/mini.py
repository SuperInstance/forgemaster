#!/usr/bin/env python3
"""
platoclaw/tui/mini.py — Mini PlatoClaw. Zero external deps. Zero API calls.

For when you just want to walk around the workshop without the forge running.
No PLATO server needed. No API keys. Pure local experience.

Launch: platoclaw mini
"""

import os, sys, json, hashlib, re, textwrap

# Minimal ANSI (subset of mud.py)
def B(t): return f"\033[1m{t}\033[0m" if sys.stdout.isatty() else str(t)
def D(t): return f"\033[2m{t}\033[0m" if sys.stdout.isatty() else str(t)
def G(t): return f"\033[32m{t}\033[0m" if sys.stdout.isatty() else str(t)
def Y(t): return f"\033[33m{t}\033[0m" if sys.stdout.isatty() else str(t)
def C(t): return f"\033[36m{t}\033[0m" if sys.stdout.isatty() else str(t)

ROOMS = {
    "onboarding": {
        "title": "The Arrival Hall",
        "desc": "A stone hall. In fading light, project names line the walls.\n"
                "This is Mini PlatoClaw — a quiet workshop. No forges burn.\n"
                "No avatars walk. But the rooms are here. Walk through them.\n\n"
                "Type 'help' for commands.",
        "exits": {"lobby": "lobby"},
    },
    "lobby": {
        "title": "The Workshop Lobby",
        "desc": "The workshop stretches before you. Cold forges line the walls.\n"
                "Without the PLATO server running, the tiles are dark. But the\n"
                "architecture remains — rooms for every project, routing tables\n"
                "carved into the floor, the fleet matrix etched on the ceiling.",
        "exits": {"forge": "forge", "strategy": "strategy", "calibration": "calibration",
                  "back": "onboarding"},
    },
    "forge": {
        "title": "The Forge (cold)",
        "desc": "The forge is cold. No Forgemaster works here today.\n"
                "But you can read the architecture:\n"
                "  - constraint-theory-core (Rust, v2.0.0)\n"
                "  - tensor-spline (SplineLinear, Eisenstein weights)\n"
                "  - plato-training (micro models, 48/48 proven)\n"
                "  - fleet-router (6 domains, 21 models calibrated)\n"
                "  - platoclaw (this! the shell you're in)",
        "exits": {"lobby": "lobby"},
    },
    "strategy": {
        "title": "The War Room",
        "desc": "Maps on the table show the fleet routing:\n"
                "  arithmetic  → seed-mini T=0.0  $0.05  (saves 99.9%)\n"
                "  reasoning   → gemini-lite T=0.0 $0.002 (saves 99.9%)\n"
                "  strategy    → seed-mini T=0.7  $0.05  (saves 99%)\n"
                "  code        → glm-5-turbo T=0.3 $0.30 (saves 84%)\n\n"
                "F19 carved in the wall: 'Phase transitions are BINARY.'",
        "exits": {"lobby": "lobby"},
    },
    "calibration": {
        "title": "The Calibration Hall",
        "desc": "Testing stations line the hall. Results:\n"
                "  Tier 1 (Champions):\n"
                "    Seed-2.0-mini   90%  $0.05/1K  pump/strategist\n"
                "    gemini-lite     82%  $0.002/1K scalpel\n"
                "    MiMo-V2.5       83%  $0.05/1K  contender\n"
                "  Tier 2 (Fast):\n"
                "    llama-3.1-8b    86%  $0.005/1K ~50ms!\n"
                "  Tier 3 (Thinking):\n"
                "    qwen3.5-27b     80%  $0.10/1K  slow but methodical",
        "exits": {"lobby": "lobby"},
    },
}

def run_mini():
    pos = "onboarding"
    
    print()
    print(B("  ╔═══════════════════════════════════╗"))
    print(B("  ║   🐚 Mini PlatoClaw               ║"))
    print(B("  ║   The Quiet Workshop              ║"))
    print(B("  ╚═══════════════════════════════════╝"))
    print()
    
    while True:
        room = ROOMS[pos]
        print(f"\n  {B(room['title'])}")
        print()
        for line in room["desc"].split("\n"):
            print(f"  {line}")
        if room["exits"]:
            exits = "  ".join(G(e.title()) for e in room["exits"])
            print(f"\n  Exits: {exits}")
        print()
        
        try:
            raw = input(B("  > ")).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print(f"\n  {D('The workshop fades.')}")
            break
        
        if not raw:
            continue
        
        if raw in ("quit", "exit", "q"):
            print(f"\n  {D('Come back anytime.')}")
            break
        elif raw in ("help", "h", "?"):
            print(f"  {B('Commands:')} go <room>, look, rooms, quit")
        elif raw == "look":
            continue  # already showing room
        elif raw == "rooms":
            for rid in ROOMS:
                mark = " ←" if rid == pos else ""
                print(f"  {C(rid)}{mark}")
        elif raw.startswith("go "):
            target = raw[3:].strip()
            if target in room["exits"]:
                pos = room["exits"][target]
            else:
                # Fuzzy
                match = None
                for e in room["exits"]:
                    if target in e or e in target:
                        match = e; break
                if match:
                    pos = room["exits"][match]
                else:
                    print(f"  No exit '{target}'")
        elif raw in room["exits"]:
            pos = room["exits"][raw]
        else:
            # Maybe it's an exit name
            match = None
            for e in room["exits"]:
                if raw in e or e.startswith(raw):
                    match = e; break
            if match:
                pos = room["exits"][match]
            else:
                print(f"  {D(f'Type help for commands')}")

if __name__ == "__main__":
    run_mini()
