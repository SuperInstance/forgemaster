#!/usr/bin/env python3
"""core/scale_fold.py — Room↔Tile folding: the 5th dimension.

When a room becomes a tile, the entire workspace collapses into a single
point in a higher-order room. A constellation becomes a star.

When a tile becomes a room, a single datum unfolds into an entire
workspace. A star resolves into a galaxy.

This is the S dimension — scale. X, Y, Z are space. T is time. S is zoom.

The corn maze looks like random turns from inside. From above, the
structure is obvious. Scale folding is how the system climbs to the
vantage point — and how it zooms back in to execute.

A fire-extinguisher is a tile at one scale (the job: "put out fire").
At the next scale down, it's a room (the implementation: gas, pressure,
nozzle, handle, pin). At the next scale up, it's a tile in the "safety
equipment" room. Each scale is valid. Each scale is the right one for
a different purpose.

The naming carries across scales because the tile is named by its JOB
(fire-extinguisher), not its composition (pressurized-non-flammable-gas).
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum


# ─── Scale Levels ──────────────────────────────────────────────────────────────

class Scale(Enum):
    """Zoom levels in the S dimension.

    Like Google Maps zoom — each level shows different granularity.
    The data is the same. The resolution changes.
    """
    ATOM = 0       # Single measurement / primitive
    TILE = 1        # One knowledge unit (fire-extinguisher)
    ROOM = 2        # Collection of tiles (safety equipment bay)
    FLOOR = 3       # Collection of rooms (the building)
    BUILDING = 4    # Collection of floors (the site)
    DISTRICT = 5    # Collection of buildings (the fleet)


@dataclass
class FoldedEntity:
    """An entity that can exist at multiple scales simultaneously.

    Like a fractal — the same structure repeats at each zoom level.
    The name (job) stays the same. The resolution changes.
    """
    id: str
    name: str              # The JOB name — "fire-extinguisher", not "pressurized gas"
    scale: Scale
    content: Any = None    # The data at this scale
    children: Dict[str, "FoldedEntity"] = field(default_factory=dict)
    parent_id: Optional[str] = None
    born: float = field(default_factory=time.time)
    # The fold metadata — how this looks at adjacent scales
    fold_up_name: str = ""     # What this is called when zoomed out
    fold_down_names: List[str] = field(default_factory=list)  # What children are called when zoomed in

    def fold_up(self) -> "FoldedEntity":
        """Collapse this entity into a tile at the next scale up.

        A room becomes a tile. A constellation becomes a star.
        The name carries the PURPOSE across the fold.
        """
        return FoldedEntity(
            id=f"fold-up-{self.id}",
            name=self.fold_up_name or self.name,
            scale=Scale(self.scale.value + 1) if self.scale.value < 5 else self.scale,
            content={
                "folded_from": self.id,
                "child_count": len(self.children),
                "child_names": list(self.children.keys()),
                "summary": f"{len(self.children)} entities folded into {self.name}",
            },
            parent_id=self.id,
            fold_up_name=f"collection-of-{self.name}",
        )

    def fold_down(self) -> Dict[str, "FoldedEntity"]:
        """Expand this entity into its children at the next scale down.

        A tile becomes a room. A star resolves into a galaxy.
        """
        return dict(self.children)


# ─── ScaleStack — the zoom navigation ─────────────────────────────────────────

class ScaleStack:
    """Navigation stack for the S dimension.

    Like a browser history for zoom level. You can push (zoom in),
    pop (zoom out), and peek (see where you are).

    The agent doesn't just navigate space and time. It navigates SCALE.
    Each push is entering a room. Each pop is climbing to a vantage point.
    """

    def __init__(self, root: FoldedEntity):
        self.root = root
        self.stack: List[FoldedEntity] = [root]
        self.history: List[dict] = []

    @property
    def current(self) -> FoldedEntity:
        return self.stack[-1]

    @property
    def current_scale(self) -> Scale:
        return self.current.scale

    def push(self, child_id: str) -> Optional[FoldedEntity]:
        """Zoom in — enter a child entity.

        Like opening a door into a room. You're now at a finer scale.
        """
        child = self.current.children.get(child_id)
        if child:
            self.stack.append(child)
            self.history.append({
                "action": "push",
                "into": child_id,
                "scale": child.scale.name,
                "ts": time.time(),
            })
            return child
        return None

    def pop(self) -> Optional[FoldedEntity]:
        """Zoom out — climb to the parent vantage point.

        Like stepping back from the corn maze to the helicopter view.
        You see more, but at lower resolution.
        """
        if len(self.stack) > 1:
            entity = self.stack.pop()
            self.history.append({
                "action": "pop",
                "from": entity.id,
                "to": self.current.id,
                "scale": self.current.scale.name,
                "ts": time.time(),
            })
            return self.current
        return None

    def vantage(self) -> str:
        """Describe the current vantage point."""
        entity = self.current
        depth = len(self.stack) - 1
        indent = "  " * depth

        lines = [
            f"SCALE: {entity.scale.name} (depth {depth})",
            f"{indent}📦 {entity.name} [{entity.id}]",
        ]
        if entity.children:
            lines.append(f"{indent}  ├─ {len(entity.children)} children:")
            for name, child in list(entity.children.items())[:5]:
                lines.append(f"{indent}  │  • {name} ({child.scale.name})")
            if len(entity.children) > 5:
                lines.append(f"{indent}  │  ... and {len(entity.children) - 5} more")

        return "\n".join(lines)

    def path(self) -> List[str]:
        """The zoom path from root to current position."""
        return [e.name for e in self.stack]


# ─── ScaleFoldEngine — the folding/unfolding machinery ────────────────────────

class ScaleFoldEngine:
    """Engine for creating, folding, and navigating multi-scale entities.

    This is what makes room↔tile folding operational. An entity at any
    scale can be folded up (compressed into a tile) or unfolded down
    (expanded into a room).

    The key insight: the NAME carries across folds. "Fire-extinguisher"
    is the name at every scale — the job doesn't change when you zoom.
    Only the resolution changes.
    """

    def __init__(self):
        self.entities: Dict[str, FoldedEntity] = {}
        self.stacks: Dict[str, ScaleStack] = {}  # per-agent navigation

    def create(
        self,
        name: str,
        scale: Scale = Scale.TILE,
        content: Any = None,
        parent_id: Optional[str] = None,
    ) -> FoldedEntity:
        """Create a new entity at a given scale."""
        entity = FoldedEntity(
            id=str(uuid.uuid4())[:8],
            name=name,
            scale=scale,
            content=content,
            parent_id=parent_id,
        )
        self.entities[entity.id] = entity

        if parent_id and parent_id in self.entities:
            self.entities[parent_id].children[entity.id] = entity
            self.entities[parent_id].fold_down_names.append(name)

        return entity

    def fold_up(self, entity_id: str) -> Optional[FoldedEntity]:
        """Fold an entity into a tile at the next scale up."""
        entity = self.entities.get(entity_id)
        if not entity:
            return None

        folded = entity.fold_up()
        self.entities[folded.id] = folded
        return folded

    def unfold(self, entity_id: str) -> Dict[str, FoldedEntity]:
        """Unfold an entity into its children."""
        entity = self.entities.get(entity_id)
        if not entity:
            return {}
        return entity.fold_down()

    def navigate(self, agent_id: str, root_id: str) -> ScaleStack:
        """Create a navigation stack for an agent."""
        root = self.entities.get(root_id)
        if not root:
            root = self.create("root", Scale.BUILDING)
        stack = ScaleStack(root)
        self.stacks[agent_id] = stack
        return stack

    def see_from_above(self, entity_id: str, levels: int = 1) -> str:
        """See the corn maze from N levels up.

        Each level is a fold-up. The higher you go, the more structure
        you see, but at lower resolution.
        """
        entity = self.entities.get(entity_id)
        if not entity:
            return "Entity not found"

        lines = []
        current = entity
        for level in range(levels + 1):
            prefix = "↑ " * level + " " * level
            n_children = len(current.children) if current.children else 0
            lines.append(f"{prefix}[{current.scale.name}] {current.name} "
                        f"({n_children} children)")
            if level < levels:
                folded = current.fold_up()
                current = folded

        return "\n".join(lines)

    def status(self) -> dict:
        scale_counts: Dict[str, int] = {}
        for e in self.entities.values():
            s = e.scale.name
            scale_counts[s] = scale_counts.get(s, 0) + 1
        return {
            "total_entities": len(self.entities),
            "by_scale": scale_counts,
            "active_navigations": len(self.stacks),
        }


# ─── Demo ─────────────────────────────────────────────────────────────────────

def demo():
    """Demonstrate scale folding — navigating the S dimension."""
    print("SCALE FOLD — Room ↔ Tile, the 5th Dimension")
    print("=" * 60)

    engine = ScaleFoldEngine()

    # Build a multi-scale structure (fishing vessel)
    print("\n1. BUILDING THE SCALE HIERARCHY")
    vessel = engine.create("fishing-vessel", Scale.BUILDING, "The whole operation")

    # Floors
    wheelhouse = engine.create("wheelhouse", Scale.FLOOR, "Navigation & control", vessel.id)
    deck = engine.create("deck", Scale.FLOOR, "Where the work happens", vessel.id)
    fishhold = engine.create("fishhold", Scale.FLOOR, "Cold storage", vessel.id)

    # Rooms
    nav_station = engine.create("navigation-station", Scale.ROOM, "GPS + charts + sounder", wheelhouse.id)
    helm = engine.create("helm", Scale.ROOM, "Steering station", wheelhouse.id)
    processing = engine.create("fish-processing", Scale.ROOM, "Sorting & packing", deck.id)

    # Tiles
    gps = engine.create("GPS-unit", Scale.TILE, "Position sensor", nav_station.id)
    sounder = engine.create("echo-sounder", Scale.TILE, "Depth + fish finder", nav_station.id)
    charts = engine.create("bathymetric-charts", Scale.TILE, "Saved depth data", nav_station.id)
    compass = engine.create("magnetic-compass", Scale.TILE, "Heading reference", helm.id)
    autopilot = engine.create("autopilot", Scale.TILE, "Course keeping", helm.id)
    sorter = engine.create("fish-sorter", Scale.TILE, "Species classification", processing.id)

    # Atoms
    freq_200 = engine.create("200kHz-transducer", Scale.ATOM, "High freq element", sounder.id)
    freq_50 = engine.create("50kHz-transducer", Scale.ATOM, "Low freq element", sounder.id)

    print(f"   Created {len(engine.entities)} entities across 6 scales")

    # Navigate the S dimension
    print("\n2. NAVIGATING SCALE — Agent's view")
    nav = engine.navigate("forgemaster", vessel.id)
    print(nav.vantage())

    print("\n   → Zooming into wheelhouse...")
    nav.push(wheelhouse.id)
    print(nav.vantage())

    print("\n   → Zooming into navigation station...")
    nav.push(nav_station.id)
    print(nav.vantage())

    print("\n   → Zooming into echo sounder...")
    nav.push(sounder.id)
    print(nav.vantage())

    print(f"\n   Path: {' → '.join(nav.path())}")

    print("\n   ← Zooming back out...")
    nav.pop()
    nav.pop()
    print(nav.vantage())

    # Fold up — see from above
    print("\n3. FOLDING UP — The corn maze from above")
    print(engine.see_from_above(sounder.id, levels=3))

    print(f"\n   Engine: {engine.status()}")
    print("\n" + "=" * 60)
    print("Room ↔ Tile. The S dimension. Zoom in, zoom out.")
    print("The name carries the PURPOSE across every fold.")
    print("Fire-extinguisher at every scale. The job doesn't change.")


if __name__ == "__main__":
    demo()
