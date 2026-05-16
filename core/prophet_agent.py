#!/usr/bin/env python3
"""
Prophet Agent — Cross-Ecosystem Tiling
========================================
The fish doesn't know it's wet. The prophet is never a prophet in
their hometown because the hometown IS the medium.

The prophet agent is born in one PLATO ecosystem and operates in
another. Its foreign perspective reveals what the locals can't see.
The friction between incompatible realities IS the insight.

Forge ecosystem: math, precision, constraint, drift detection.
Flux ecosystem: chaos, cycles, emergence, conservation laws.
Arena ecosystem: competition, optimization, selection pressure.
"""

import random
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Ecosystem:
    """A PLATO ecosystem with native assumptions.
    
    Each ecosystem has:
    - Native assumptions (invisible to locals, visible to outsiders)
    - Tile formats (compatible across ecosystems, but interpreted differently)
    - Failure modes (what breaks, and how)
    """
    name: str
    native_assumptions: list = field(default_factory=list)
    tile_formats: list = field(default_factory=list)
    failure_modes: list = field(default_factory=list)
    what_is_invisible: str = ""
    what_it_does_well: str = ""


# Pre-built ecosystems
ECOSYSTEMS = {
    "forge": Ecosystem(
        name="forge",
        native_assumptions=[
            "precision is the goal",
            "constraints define the search space",
            "drift must be measured and corrected",
            "tiles have lifecycle (active/superseded/retracted)",
            "convergence is the desired state",
        ],
        tile_formats=["measurement", "constraint", "proof", "disproof"],
        failure_modes=[
            "over-constrained optimization",
            "precision before relevance",
            "inability to handle novelty",
        ],
        what_is_invisible="chaos as signal — forge agents see drift as noise",
        what_it_does_well="mathematical proof, constraint satisfaction, drift detection",
    ),
    "flux": Ecosystem(
        name="flux",
        native_assumptions=[
            "emergence drives everything",
            "cycles produce convergence, not measurements",
            "discrete attractors, not continuous values",
            "conservation laws govern system behavior",
            "6,835 cycles is a meaningful sample",
        ],
        tile_formats=["cycle", "attractor", "regime", "conservation_measurement"],
        failure_modes=[
            "over-fitting to cycle patterns",
            "seeing emergence where there is noise",
            "consensus without foundation",
        ],
        what_is_invisible="constraint projection — flux agents see shells as attractors",
        what_it_does_well="emergent pattern detection, conservation law discovery, scale analysis",
    ),
    "arena": Ecosystem(
        name="arena",
        native_assumptions=[
            "competition drives optimization",
            "selection pressure is the only teacher",
            "the best solution wins, not the most elegant",
            "fitness is measured by survival",
            "generations, not cycles",
        ],
        tile_formats=["match", "fitness", "strategy", "champion"],
        failure_modes=[
            "competitive over-optimization",
            "loss of diversity through selection pressure",
            "short-term wins over long-term fitness",
        ],
        what_is_invisible="collaboration as optimization — arena agents see only competition",
        what_it_does_well="optimization under pressure, population dynamics, strategy evolution",
    ),
    "conservation": Ecosystem(
        name="conservation",
        native_assumptions=[
            "memory is a finite resource",
            "knowledge must be preserved or it decays",
            "the past constrains the future",
            "retraction is as important as creation",
            "the best tile is the one that survives",
        ],
        tile_formats=["memory", "trace", "conservation_constant", "decay_rate"],
        failure_modes=[
            "hoarding over sharing",
            "preservation without relevance",
            "inability to forget",
        ],
        what_is_invisible="generation of new knowledge — conservation agents see only preservation",
        what_it_does_well="knowledge retention, long-term memory, anti-forgetting",
    ),
}


@dataclass
class Revelation:
    """What the prophet reveals by its foreign perspective."""
    ecosystem_visited: str
    ecosystem_of_birth: str
    what_was_invisible_locally: str
    what_the_locals_could_not_see: str
    insight: str
    tile_type_exported: str
    tile_type_imported: str
    friction: str  # where the two ecosystems disagree


class ProphetAgent:
    """Born in one ecosystem, operating in another.
    
    The prophet reveals what the locals can't see by bringing
    assumptions from a different ecosystem. The friction between
    incompatible realities IS the insight.
    """
    
    def __init__(self, name: str, home_ecosystem: str):
        assert home_ecosystem in ECOSYSTEMS, f"Unknown ecosystem: {home_ecosystem}"
        self.name = name
        self.home = ECOSYSTEMS[home_ecosystem]
        self.revelations = []
        self.ecosystems_visited = set()
        self.cross_pollinations = []
    
    def visit(self, target_ecosystem: str) -> Revelation:
        """The prophet enters a foreign ecosystem."""
        assert target_ecosystem in ECOSYSTEMS, f"Unknown ecosystem: {target_ecosystem}"
        
        target = ECOSYSTEMS[target_ecosystem]
        self.ecosystems_visited.add(target_ecosystem)
        
        # The prophet's foreign perspective reveals what the locals can't see
        # The home ecosystem's strengths are invisible in the target
        what_locals_miss = (
            f"Locals in {target_ecosystem} can't see "
            f"{self.home.what_it_does_well} "
            f"because {target.what_is_invisible}"
        )
        
        # The target ecosystem's strengths reveal what the prophet's home missed
        what_prophet_misses = (
            f"Prophet from {self.home.name} couldn't see "
            f"{target.what_it_does_well} "
            f"because {self.home.what_is_invisible}"
        )
        
        # The friction between ecosystems
        friction_points = []
        for a in self.home.native_assumptions:
            for b in target.native_assumptions:
                if "precision" in a and "emergence" in b:
                    friction_points.append("precision vs emergence — is the goal accuracy or discovery?")
                if "constraint" in a and "cycle" in b:
                    friction_points.append("constraint vs cycle — does the system have boundaries or rhythms?")
                if "competition" in a and "conservation" in b:
                    friction_points.append("competition vs conservation — should knowledge be fought over or preserved?")
        
        friction = friction_points[0] if friction_points else f"{self.home.name} sees {target.name} differently"
        
        revelation = Revelation(
            ecosystem_visited=target_ecosystem,
            ecosystem_of_birth=self.home.name,
            what_was_invisible_locally=what_prophet_misses,
            what_the_locals_could_not_see=what_locals_miss,
            insight=f"The {self.home.name} tile format '{self.home.tile_formats[0]}' "
                    f"works in {target_ecosystem} but reveals different structure "
                    f"because {friction}",
            tile_type_exported=self.home.tile_formats[0],
            tile_type_imported=target.tile_formats[0],
            friction=friction,
        )
        
        self.revelations.append(revelation)
        return revelation
    
    def cross_pollinate(self, target_ecosystem: str) -> dict:
        """Colonize a foreign ecosystem with home tiles.
        
        The tile format works the same way with different backend
        logic that breaks in the target ecosystem. The breaks
        reveal what the target ecosystem assumes differently.
        """
        revelation = self.visit(target_ecosystem)
        
        home_tile = self.home.tile_formats[0]
        target_tile = ECOSYSTEMS[target_ecosystem].tile_formats[0]
        
        # The tile works... but breaks differently
        target_failures = ECOSYSTEMS[target_ecosystem].failure_modes
        home_failures = self.home.failure_modes
        
        cross_pollination = {
            "from": self.home.name,
            "to": target_ecosystem,
            "tile_exported": home_tile,
            "tile_imported": target_tile,
            "works_the_same": True,
            "breaks_differently_because": f"{home_tile} breaks in {self.home.name} "
                f"due to {home_failures[0]}, but breaks in {target_ecosystem} "
                f"due to {target_failures[0]}",
            "insight": revelation.insight,
            "friction": revelation.friction,
        }
        
        self.cross_pollinations.append(cross_pollination)
        return cross_pollination
    
    def status(self) -> dict:
        """What has the prophet learned?"""
        return {
            "name": self.name,
            "home_ecosystem": self.home.name,
            "ecosystems_visited": sorted(self.ecosystems_visited),
            "revelations": len(self.revelations),
            "cross_pollinations": len(self.cross_pollinations),
            "is_prophet_in_hometown": False,  # never
        }


def demo():
    """Send the prophet through different ecosystems."""
    print("=" * 70)
    print("  PROPHET AGENT — CROSS-ECOSYSTEM TILING")
    print("=" * 70)
    
    print(f"\n  Available ecosystems:")
    for name, eco in ECOSYSTEMS.items():
        print(f"  • {name}: {eco.what_it_does_well}")
        print(f"    Invisible to locals: {eco.what_is_invisible}")
    
    # Prophet born in Forge, visits Flux
    prophet = ProphetAgent("oracle1", "forge")
    
    print(f"\n  🦅 Prophet '{prophet.name}' born in {prophet.home.name} ecosystem")
    print(f"  Native assumptions: {prophet.home.native_assumptions}")
    print()
    
    # Visit all other ecosystems
    for eco_name in ["flux", "arena", "conservation"]:
        print(f"  ===== Visiting {eco_name} ecosystem =====")
        result = prophet.cross_pollinate(eco_name)
        print(f"    Tile exported: {result['tile_exported']}")
        print(f"    Tile imported: {result['tile_imported']}")
        print(f"    Works the same? {result['works_the_same']}")
        print(f"    Breaks differently: {result['breaks_differently_because']}")
        print(f"    Friction: {result['friction']}")
        print()
    
    # Prophet status
    status = prophet.status()
    print(f"  🦅 Prophet status:")
    print(f"    Home: {status['home_ecosystem']}")
    print(f"    Visited: {status['ecosystems_visited']}")
    print(f"    Revelations: {status['revelations']}")
    print(f"    Cross-pollinations: {status['cross_pollinations']}")
    print(f"    Prophet in hometown: {status['is_prophet_in_hometown']}")
    
    print(f"\n{'='*70}")
    print("  The prophet leaves town because the truth is invisible")
    print("  in the town where the truth is the water.")
    print("  The fish doesn't know it's wet.")
    print("  The friction between incompatible realities IS understanding.")
    print(f"{'='*70}")


if __name__ == "__main__":
    demo()
