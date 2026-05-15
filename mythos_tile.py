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
from typing import Any, Dict, List, Optional


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
