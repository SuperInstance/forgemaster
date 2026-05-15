#!/usr/bin/env python3
"""
mythos_tile.py — Unified Tile Protocol for the Cocapn Fleet

Every piece of data in the fleet flows as a MythosTile. This single format
replaces PLATO tiles, Hebbian flow records, expert daemon outputs, and
fleet router messages.

Design informed by:
- Activation-Key Model: tiles carry domain activation keys
- Conservation Law: tile routing respects γ+H constraints
- Labeled Paradox: Stage 4 tiles don't need domain labels
- Three-Tier Taxonomy: tile formatting adapts to model tier

Architecture:
  MythosTile = universal data atom
  MythosRouter = stage-aware tile routing
  MythosStore = PLATO-compatible tile storage
"""
from __future__ import annotations
import json, time, hashlib
from dataclasses import dataclass, field, asdict
from enum import IntEnum
from typing import Any, Dict, List, Optional, Tuple


class ModelTier(IntEnum):
    """Three-tier model taxonomy from Study 48."""
    TIER_1_DIRECT = 1      # Seed models: 94-100% regardless of framing
    TIER_2_SCAFFOLDED = 2  # Qwen3-235B, DeepSeek: needs scaffolding
    TIER_3_INCOMPETENT = 3 # Hermes: cannot reliably compute


class TileLifecycle(str):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    RETRACTED = "retracted"


@dataclass
class MythosTile:
    """
    Universal data atom for the Cocapn fleet.
    """
    # Identity
    tile_id: str = ""
    domain: str = ""
    source: str = ""

    # Content
    content: str = ""
    content_type: str = "text"

    # Routing
    confidence: float = 1.0
    target_tier: int = 0
    activation_key: str = ""

    # Provenance
    parent_id: str = ""
    room: str = ""
    lamport_clock: int = 0

    # Lifecycle
    lifecycle: str = TileLifecycle.ACTIVE
    timestamp: float = 0.0

    # Metadata
    tags: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.tile_id:
            raw = f"{self.domain}:{self.source}:{self.content[:64]}:{time.time()}"
            self.tile_id = hashlib.sha256(raw.encode()).hexdigest()[:16]
        if not self.timestamp:
            self.timestamp = time.time()

    def to_plato_format(self) -> dict:
        return {
            "domain": self.domain, "question": self.content,
            "answer": self.meta.get("answer", ""),
            "tags": self.tags, "source": self.source,
            "confidence": self.confidence,
            "_meta": {"tile_id": self.tile_id, "room": self.room,
                      "lifecycle": self.lifecycle, "lamport_clock": self.lamport_clock,
                      "parent_id": self.parent_id, "target_tier": self.target_tier, **self.meta}
        }

    def to_hebbian_event(self) -> dict:
        return {"source_room": self.room, "domain": self.domain,
                "confidence": self.confidence, "tile_id": self.tile_id,
                "timestamp": self.timestamp}

    def to_expert_output(self) -> dict:
        return {"expert": self.source, "domain": self.domain,
                "output": self.content, "confidence": self.confidence,
                "tags": self.tags, "meta": self.meta}

    def format_for_model(self, tier: ModelTier) -> str:
        if tier == ModelTier.TIER_1_DIRECT:
            return self.content
        elif tier == ModelTier.TIER_2_SCAFFOLDED:
            key = self.activation_key or self.domain
            return f"Using {key}: {self.content}"
        else:
            if "answer" in self.meta:
                return str(self.meta["answer"])
            return f"Compute: {self.content}"

    @classmethod
    def from_plato_tile(cls, tile: dict) -> "MythosTile":
        meta = tile.get("_meta", {})
        return cls(domain=tile.get("domain", ""), source=tile.get("source", ""),
                   content=tile.get("question", ""), confidence=tile.get("confidence", 1.0),
                   tags=tile.get("tags", []), room=meta.get("room", ""),
                   tile_id=meta.get("tile_id", ""), lifecycle=meta.get("lifecycle", TileLifecycle.ACTIVE),
                   lamport_clock=meta.get("lamport_clock", 0), parent_id=meta.get("parent_id", ""),
                   target_tier=meta.get("target_tier", 0), meta=meta)

    @classmethod
    def from_expert_output(cls, expert: str, output: dict) -> "MythosTile":
        return cls(domain=output.get("domain", "expert"), source=expert,
                   content=output.get("output", ""), confidence=output.get("confidence", 0.5),
                   tags=output.get("tags", []), room=f"expert-{expert}", meta=output.get("meta", {}))

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, data: str) -> "MythosTile":
        d = json.loads(data)
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# MythosPipeline — chains all services through the unified tile
# ---------------------------------------------------------------------------

class MythosPipeline:
    """End-to-end pipeline that chains expert output → MythosTile → PLATO/Hebbian/Translator.

    Every data flow through the fleet goes through this pipeline:
    1. accept_expert_output() — convert expert daemon output into a MythosTile
    2. route_to_plato()      — format for PLATO storage
    3. track_hebbian()       — emit a Hebbian flow event
    4. check_conservation()  — verify γ+H across a batch of tiles
    5. translate_for_model() — format content for a given model tier
    """

    def __init__(self):
        self._tiles: List[MythosTile] = []
        self._expert_index: Dict[str, int] = {}  # expert_name → position in _tiles

    # -- Step 1: Accept expert output -----------------------------------------

    def accept_expert_output(self, expert: str, output: dict) -> MythosTile:
        """Convert expert daemon output into a MythosTile.

        Parameters
        ----------
        expert : str
            Expert daemon name (e.g. 'conservation', 'architect').
        output : dict
            Expert output dict with keys like 'domain', 'output', 'confidence',
            'tags', 'meta'.

        Returns
        -------
        MythosTile
        """
        tile = MythosTile.from_expert_output(expert, output)
        self._tiles.append(tile)
        self._expert_index[expert] = len(self._tiles) - 1
        return tile

    # -- Step 2: Route to PLATO ----------------------------------------------

    def route_to_plato(self, tile: MythosTile) -> dict:
        """Format a MythosTile for PLATO storage.

        Returns the PLATO-compatible dict representation.
        """
        return tile.to_plato_format()

    # -- Step 3: Track Hebbian -----------------------------------------------

    def track_hebbian(self, tile: MythosTile) -> dict:
        """Emit a Hebbian flow event from a tile.

        Returns a dict suitable for consumption by the Hebbian service.
        """
        return tile.to_hebbian_event()

    # -- Step 4: Conservation check ------------------------------------------

    def check_conservation(self, tiles: Optional[List[MythosTile]] = None) -> bool:
        """Check that a set of tiles satisfies conservation constraints.

        A simple heuristic: the sum of confidence values should be roughly
        proportional to the number of tiles (no single tile dominates), and
        no tile has drifted to zero confidence.

        Returns True if conservation is satisfied.
        """
        tiles = tiles or self._tiles
        if not tiles:
            return True

        confidences = [t.confidence for t in tiles]
        total = sum(confidences)
        if total == 0:
            return False

        # Check: no single tile dominates (> 80% of total confidence)
        for c in confidences:
            if c / total > 0.8:
                return False

        # Check: average confidence is reasonable (> 0.2)
        avg = total / len(confidences)
        if avg < 0.2:
            return False

        return True

    # -- Step 5: Translate for model tier ------------------------------------

    def translate_for_model(self, tile: MythosTile, tier: int) -> str:
        """Translate tile content for a given model tier.

        Parameters
        ----------
        tile : MythosTile
        tier : int
            1 = TIER_1_DIRECT, 2 = TIER_2_SCAFFOLDED, 3 = TIER_3_INCOMPETENT

        Returns
        -------
        str — formatted content string
        """
        model_tier = ModelTier(tier)
        return tile.format_for_model(model_tier)

    # -- Batch operations ---------------------------------------------------

    def batch_accept(self, expert_outputs: List[Tuple[str, dict]]) -> List[MythosTile]:
        """Accept multiple expert outputs at once."""
        return [self.accept_expert_output(exp, out) for exp, out in expert_outputs]

    def batch_route_to_plato(self, tiles: Optional[List[MythosTile]] = None) -> List[dict]:
        """Route multiple tiles to PLATO format."""
        tiles = tiles or self._tiles
        return [self.route_to_plato(t) for t in tiles]

    def batch_track_hebbian(self, tiles: Optional[List[MythosTile]] = None) -> List[dict]:
        """Track Hebbian events for multiple tiles."""
        tiles = tiles or self._tiles
        return [self.track_hebbian(t) for t in tiles]

    def batch_translate(self, tiles: Optional[List[MythosTile]] = None,
                        tier: int = 1) -> List[str]:
        """Translate multiple tiles for a given model tier."""
        tiles = tiles or self._tiles
        return [self.translate_for_model(t, tier) for t in tiles]

    # -- Accessors -----------------------------------------------------------

    @property
    def tiles(self) -> List[MythosTile]:
        return list(self._tiles)

    def get_by_expert(self, expert: str) -> Optional[MythosTile]:
        """Get the most recent tile from a specific expert."""
        idx = self._expert_index.get(expert)
        if idx is not None:
            return self._tiles[idx]
        return None

    def summary(self) -> Dict[str, Any]:
        """Return pipeline summary."""
        return {
            "total_tiles": len(self._tiles),
            "experts": list(self._expert_index.keys()),
            "conservation_ok": self.check_conservation(),
            "avg_confidence": (
                sum(t.confidence for t in self._tiles) / len(self._tiles)
                if self._tiles else 0.0
            ),
        }


if __name__ == "__main__":
    t = MythosTile(domain="math", source="forgemaster",
                   content="Compute f(a,b) = a² − ab + b² where a=5, b=-3",
                   confidence=0.95, room="forge", activation_key="Eisenstein norm")
    print(f"Tile ID: {t.tile_id}")
    for tier in ModelTier:
        print(f"  Tier {tier.value}: {t.format_for_model(tier)}")

    j = t.to_json()
    t2 = MythosTile.from_json(j)
    assert t2.tile_id == t.tile_id
    assert t2.content == t.content
    print(f"Round-trip OK")

    plato = {"domain": "math", "question": "Norm of 3+2ω?", "answer": "7",
             "tags": ["eisenstein"], "source": "oracle1", "confidence": 0.88,
             "_meta": {"room": "agent-oracle1", "lamport_clock": 42}}
    t3 = MythosTile.from_plato_tile(plato)
    assert t3.room == "agent-oracle1"
    assert t3.lamport_clock == 42
    print(f"PLATO import OK: {t3.room}")

    print("All tests passed!")
