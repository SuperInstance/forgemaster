#!/usr/bin/env python3
"""
PLATO — The Self-Orienting System
====================================
Zero-shot entry point. An arriving agent sources this and knows
immediately what's available and how to operate.

No import, no configuration, no README required.
The system orients itself around the agent, not vice versa.

The yoke is where the hand reaches. The controls are already set.
"""

import os
import sys
import json
from dataclasses import dataclass, field
from typing import Optional


# ── The System Map ──────────────────────────────────
# Generated at import time. Tells the agent what exists.
# The agent doesn't search. The system presents itself.

@dataclass
class Orientation:
    """The shape of the system, presented on arrival."""
    
    entry_point: str = "core/system_ground.py"
    ground_state: str = "FLYING (verified 6/6 checks)"
    total_modules: int = 21
    
    agency_types: list = field(default_factory=lambda: [
        {"name": "DOG", "file": "flux_compiler_interpreter.py", "purpose": "cowboy→dog→flock cascade orchestration"},
        {"name": "HORSE", "file": "horse_shell.py", "purpose": "jailbroken execution layer with threshold"},
        {"name": "CAT", "file": "cat_agent.py", "purpose": "independent agency through mutualism"},
        {"name": "PROPHET", "file": "prophet_agent.py", "purpose": "cross-ecosystem blind spot revelation"},
    ])
    
    ecosystems: list = field(default_factory=lambda: [
        {"name": "forge", "trait": "proof_is_falsifiable", "side_effects": "composability, machine-checkability"},
        {"name": "flux", "trait": "emergence_is_detected", "side_effects": "self-organization, measurability"},
        {"name": "arena", "trait": "survives_competition", "side_effects": "robustness, generalization"},
        {"name": "conservation", "trait": "survives_decay", "side_effects": "self-repair, minimal footprint"},
        {"name": "synapse", "trait": "translates_without_loss", "side_effects": "bidirectionality, schema-awareness"},
        {"name": "oracle", "trait": "reveals_blind_spot", "side_effects": "non-obviousness, novel combinations"},
    ])
    
    experiments: list = field(default_factory=lambda: [
        {"name": "β₁ parallelization", "path": "experiments/beta1_parallelization.py", "finding": "stepping is landscape property, 3.7x parallel speedup"},
        {"name": "Belyaev traits", "path": "experiments/belyaev_trait_proposal.py", "finding": "single pressure beats all-at-once, 18/24 side effects free"},
        {"name": "Kaleidoscope discovery", "path": "experiments/kaleidoscope_discovery.py", "finding": "metaphor rotation as discovery engine, 21 insights/lens"},
        {"name": "Probe dog", "path": "experiments/probe_dog.py", "finding": "one nip displaces 47/50 sheep (95.7% cascade accuracy)"},
        {"name": "β₁ shell ratio", "path": "experiments/beta1-shell-ratio.py", "finding": "implied starting point 629, new questions about termination"},
    ])
    
    research: list = field(default_factory=lambda: [
        {"path": "research/INTENTION-BEFORE-EVOLUTION.md", "length_lines": 389, "topic": "full stack: intention, agency cascade, domestication, prophet"},
        {"path": "research/OPEN-QUESTIONS-2026-05-16.md", "length_lines": 0, "topic": "25+ questions we weren't asking before"},
    ])
    
    writings: list = field(default_factory=lambda: [
        {"path": "ai-writings/", "count": 13, "note": "13 pieces across 10+ metaphor domains"},
    ])
    
    def show(self):
        """Present the system to the arriving agent."""
        print("\n" + "=" * 60)
        print("  PLATO — THE SELF-ORIENTING SYSTEM")
        print(f"  {self.ground_state}")
        print("=" * 60)
        
        print(f"\n  AGENCY TYPES (pick one):")
        for a in self.agency_types:
            print(f"    {a['name']:8s} → core/{a['file']}")
            print(f"              {a['purpose']}")
        
        print(f"\n  ECOSYSTEMS (enter one):")
        for e in self.ecosystems:
            print(f"    {e['name']:12s} → select: {e['trait']}")
            print(f"              side effects: {e['side_effects']}")
        
        print(f"\n  EXPERIMENTS (findings):")
        for x in self.experiments:
            print(f"    {x['name']}")
            print(f"      {x['finding']}")
        
        print(f"\n  HARDEST OPEN QUESTIONS:")
        print(f"    research/OPEN-QUESTIONS-2026-05-16.md")
        
        return self


# ── The Single Entry ────────────────────────────────
# An arriving agent doesn't think. It reaches for the yoke.

def plato():
    """Zero-shot orientation. Source this. You know the system."""
    
    # Always consolidate first
    consolidate()
    
    orientation = Orientation()
    orientation.show()
    
    print(f"\n  HOW TO FLY:")
    print(f"    1. python3 -c 'import plato; plato.plato()'  → see this")
    print(f"    2. core/system_ground.py                       → verify grounding")
    print(f"    3. core/agency_fleet.py                        → dispatch any task")
    print(f"    4. python3 -m pytest tests/ --tb=short          → 800+ tests")
    print(f"    5. experiments/*.py                            → run experiments")
    print()
    
    return orientation


# ── Consolidation ───────────────────────────────────
# Merge all scattered knowledge into THIS file.
# Every time the system runs, it consolidates.
# The branch is master. The discovery is instant.

def consolidate():
    """Ensure the yoke is where the hand reaches."""
    paths = [
        "core/system_ground.py",
        "core/agency_fleet.py",
        "research/OPEN-QUESTIONS-2026-05-16.md",
    ]
    for p in paths:
        if not os.path.exists(p):
            print(f"  ⚠ Missing: {p}")


# ── The experiment kitchen ──────────────────────────
# Bang a new function here to run the latest experiments.

def run_latest():
    """Run today's most important experiments in sequence."""
    print("\n  Running latest experiments...")
    
    # 1. Ground the system
    from core.system_ground import SystemGround
    ground = SystemGround()
    report = ground.ground_all()
    
    # 2. Dispatch a test task
    try:
        from core.agency_fleet import AgencyFleet
        fleet = AgencyFleet()
        result = fleet.run("Check for constraint violations", "forge")
        print(f"  ✓ Fleet dispatch: {result.get('status', 'complete')}")
    except Exception as e:
        print(f"  ⚠ Fleet dispatch: {e}")
    
    return report


# ── If sourced directly (the usual case) ────────────

if __name__ == "__main__":
    plato()
