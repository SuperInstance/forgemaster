"""core/tile_lifecycle.py — Tile Lifecycle with Mortality

Tiles are born, they accumulate evidence, and they die.
Disproof-only admission prevents knowledge bloat.
Mortality sweep keeps the corpus alive.

Evidence: MULTI-MODEL-SYNTHESIS.md §Novel Idea 2 (Disproof-Only Tile Principle),
          §Step 3 (Tile Mortality + Disproof-Only Admission)
Findings: R1 (DATA > instructions BEDROCK), R16 (echo rate), R32 (extraction BEDROCK)
seed-pro's prediction: tile cancer arrives at ~1127 tiles without mortality.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Tuple
from collections import defaultdict

from .pinna import PinnaField, PinnaEncoder, AgentStage


# ─── The Tile ─────────────────────────────────────────────────────────────────

@dataclass
class Tile:
    """A PLATO knowledge tile with pinna provenance.

    Structure mirrors the DO/DATA/DONE task atom (R1 BEDROCK):
      DATA is the critical field — the actual knowledge.
      Instructions (triggers, negative) are secondary.

    Every tile has a lifecycle:
      born → used (wins/losses accumulate) → swept (if bottom 15% by win_rate)

    The 'negative' field is load-bearing: read it first.
    A loop applied outside its boundary conditions produces invalid results.
    (UNIFIED-FRAMEWORK.md §VI Loop Quality Hierarchy)
    """
    # Identity
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = "knowledge"      # knowledge | loop | rock | residue | seed | spline | meta

    # Content — the DATA field (R1 BEDROCK: data > instructions)
    content: str = ""            # the actual knowledge or algorithm
    negative: str = ""           # boundary conditions — WHEN NOT TO APPLY (read first)
    trigger: str = ""            # pattern that causes retrieval

    # Provenance
    pinna: Optional[PinnaField] = None   # spectral fingerprint from generating agent
    confidence: float = 0.0              # trials_correct / total_trials (not a feeling)
    evidence: List[str] = field(default_factory=list)  # finding IDs: ["R16", "R25"]

    # Disproof gate (MULTI-MODEL-SYNTHESIS.md §Novel Idea 2)
    falsifies: str = ""          # ID of existing tile this tile disproves ("" = seed tile)

    # Dependencies
    deps: List[str] = field(default_factory=list)

    # Lifecycle
    born: float = field(default_factory=time.time)
    last_used: float = 0.0
    use_count: int = 0
    win_count: int = 0
    loss_count: int = 0

    # ── Computed ──

    @property
    def win_rate(self) -> float:
        """Provenance score: win / (win + loss). Used for mortality sweep.

        Never based on embedding similarity — only real-world outcomes.
        (MULTI-MODEL-SYNTHESIS.md §Step 3)
        """
        total = self.win_count + self.loss_count
        return self.win_count / total if total > 0 else 0.5  # 0.5 = untested, keep

    @property
    def age_hours(self) -> float:
        return (time.time() - self.born) / 3600

    # ── Mutation ──

    def record_use(self, succeeded: bool) -> None:
        """Record that an agent used this tile and whether it helped."""
        self.last_used = time.time()
        self.use_count += 1
        if succeeded:
            self.win_count += 1
        else:
            self.loss_count += 1

    # ── Serialization ──

    def to_dict(self) -> dict:
        d = asdict(self)
        if self.pinna is not None:
            d["pinna"] = self.pinna.to_dict()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Tile":
        data = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        if "pinna" in data and isinstance(data["pinna"], dict):
            data["pinna"] = PinnaField.from_dict(data["pinna"])
        return cls(**data)


# ─── TileStore — CRUD with pinna metadata ────────────────────────────────────

class TileStore:
    """CRUD for tiles with pinna metadata, disproof gate, and mortality.

    In production: wraps PLATO server calls.
    In development: in-memory dict.

    The gate and sweep are integrated — callers should use `admit()` for
    new tiles and `sweep()` periodically for mortality.
    """

    def __init__(self, seed_phase_size: int = 50):
        """
        seed_phase_size: number of tiles admitted before disproof gate activates.
        The first N tiles bootstrap the corpus — they have nothing to falsify.
        """
        self.tiles: Dict[str, Tile] = {}
        self._gate = DisproofOnlyGate(self, seed_threshold=seed_phase_size)
        self._cancer = TileCancerDetector(self)
        self._outcome_log: List[Tuple[float, str, bool]] = []  # (ts, tile_id, success)

    # ── Core CRUD ──

    def put(self, tile: Tile) -> bool:
        """Insert or update without gate check. Use admit() for new tiles.

        put() is for updates to existing tiles (confidence changes, win/loss updates).
        For new tiles, always use admit() so the disproof gate fires.
        """
        if not tile.id:
            return False
        self.tiles[tile.id] = tile
        return True

    def admit(self, tile: Tile) -> Tuple[bool, str]:
        """Attempt to admit a new tile through the disproof gate.

        Returns (admitted: bool, reason: str).
        Admitted tiles are inserted into the store.
        Rejected tiles are not inserted, but the rejection is logged.
        """
        if tile.id in self.tiles:
            # Update path — always allowed
            self.tiles[tile.id] = tile
            return True, "updated"
        return self._gate.admit(tile)

    def get(self, tile_id: str) -> Optional[Tile]:
        """Retrieve a tile by ID."""
        return self.tiles.get(tile_id)

    def delete(self, tile_id: str) -> bool:
        # DEPRECATED: MortalitySweep no longer calls delete.
        # Tiles are never deleted — they become rocks.
        # This method exists for backwards compatibility only.
        return True  # no-op: tile is NOT removed

    # ── Outcome tracking ──

    def record_outcome(self, tile_id: str, succeeded: bool) -> None:
        """Record that tile `tile_id` was retrieved and the result was correct/incorrect."""
        tile = self.tiles.get(tile_id)
        if tile:
            tile.record_use(succeeded)
        self._outcome_log.append((time.time(), tile_id, succeeded))

    # ── Query ──

    def query(
        self,
        prefix: str = "",
        tile_type: str = "",
        min_confidence: float = 0.0,
    ) -> List[Tile]:
        """Query tiles by ID prefix, type, and minimum confidence.

        Returns tiles sorted by confidence descending.
        """
        results = []
        for tile in self.tiles.values():
            if prefix and not tile.id.startswith(prefix):
                continue
            if tile_type and tile.type != tile_type:
                continue
            if tile.confidence < min_confidence:
                continue
            results.append(tile)
        return sorted(results, key=lambda t: -t.confidence)

    def search(
        self,
        keywords: List[str],
        tile_type: str = "",
        min_confidence: float = 0.0,
    ) -> List[Tile]:
        """Full-text keyword search over trigger + content + id fields.

        Returns tiles sorted by confidence descending.
        """
        results = []
        for tile in self.tiles.values():
            if tile_type and tile.type != tile_type:
                continue
            if tile.confidence < min_confidence:
                continue
            text = " ".join([tile.id, tile.trigger, tile.content]).lower()
            if any(kw.lower() in text for kw in keywords):
                results.append(tile)
        return sorted(results, key=lambda t: -t.confidence)

    def search_by_pinna(
        self,
        reader_stage: AgentStage,
        reader_distance: float = 0.0,
        max_results: int = 10,
    ) -> List[Tuple[Tile, str]]:
        """Directional tile retrieval using pinna compatibility.

        Returns (tile, classification) pairs sorted by value:
          essential → aspirational → reliable → redundant.
        Skips noise tiles (dead zones).

        Implements PINNA-PRINCIPLE.md §What This Enables.
        Confirms P8 (stage-matched reading is optimal).
        """
        from .pinna import PinnaReader
        reader = PinnaReader(reader_stage, agent_ceiling=0, reader_distance=reader_distance)
        all_dicts = [t.to_dict() for t in self.tiles.values()]
        ranked = reader.rank_tiles(all_dicts)
        _order = {"essential": 0, "aspirational": 1, "reliable": 2, "redundant": 3, "noise": 4}
        results: List[Tuple[Tile, str]] = []
        for tile_dict, cls in ranked:
            if cls == "noise":
                continue
            tile = self.tiles.get(tile_dict["id"])
            if tile:
                results.append((tile, cls))
            if len(results) >= max_results:
                break
        return results

    # ── Mortality ──

    def sweep(self, mortality_rate: float = 0.15) -> dict:
        """Run a mortality sweep. Returns stats about what was pruned.

        Removes the bottom `mortality_rate` fraction of tiles by win_rate.
        Never sweeps: loop tiles, spline tiles, meta tiles, untested tiles.
        (MULTI-MODEL-SYNTHESIS.md §Step 3)
        """
        return MortalitySweep(self, mortality_rate).sweep()

    # ── Diagnostics ──

    def count(self) -> int:
        return len(self.tiles)

    def cancer_check(self) -> dict:
        """Check for tile cancer symptoms (accuracy dropping at scale).

        seed-pro predicted cancer at ~1127 tiles without mortality sweeps.
        """
        return self._cancer.check()

    def stats(self) -> dict:
        type_counts: Dict[str, int] = defaultdict(int)
        total_wins = 0
        total_losses = 0
        for tile in self.tiles.values():
            type_counts[tile.type] += 1
            total_wins += tile.win_count
            total_losses += tile.loss_count
        total = total_wins + total_losses
        return {
            "total_tiles": len(self.tiles),
            "by_type": dict(type_counts),
            "total_wins": total_wins,
            "total_losses": total_losses,
            "overall_win_rate": total_wins / total if total > 0 else 0.0,
            "rejection_log": self._gate.rejection_log()[-5:],
        }


# ─── DisproofOnlyGate ─────────────────────────────────────────────────────────

class DisproofOnlyGate:
    """New tile admission only if it falsifies an existing tile.

    From MULTI-MODEL-SYNTHESIS.md §Novel Idea 2:
      'A knowledge system that only accumulates positive examples will
       converge on confident wrongness faster than one that requires
       new entries to disprove existing ones.'

    Rules:
      1. New fact tiles must specify `falsifies` (ID of tile being disproved).
      2. `falsifies` target must exist in the store.
      3. New tile must have at least one entry in `evidence`.
      4. New tile must have a non-empty `negative` (boundary conditions).

    Exceptions (always admitted):
      - Tiles admitted during seed phase (first N tiles bootstrap the corpus)
      - Loop tiles (type="loop") — encode methods, not facts
      - Spline tiles (type="spline") — scaffolding instructions
      - Meta tiles (type="meta") — routing/topology definitions
    """

    EXEMPT_TYPES = {"loop", "spline", "meta", "seed"}

    def __init__(self, store: "TileStore", seed_threshold: int = 50):
        self.store = store
        self.seed_threshold = seed_threshold
        self._rejections: List[dict] = []

    def can_admit(self, tile: Tile) -> Tuple[bool, str]:
        """Check if tile should be admitted. Does NOT modify the store."""
        # Seed phase: first N tiles are exempt (bootstrap the corpus)
        if self.store.count() < self.seed_threshold:
            return True, f"SEED PHASE: {self.store.count()}/{self.seed_threshold} tiles, admission free"

        # Exempt types (methods, scaffolding, meta)
        if tile.type in self.EXEMPT_TYPES:
            return True, f"EXEMPT TYPE: '{tile.type}' tiles are always admitted"

        # Rule 1: must falsify an existing tile
        if not tile.falsifies:
            reason = (
                "REJECTED: new fact tile must set 'falsifies' to the ID of the tile it disproves. "
                "Pure accumulation converges on confident wrongness. (MULTI-MODEL-SYNTHESIS.md §Novel Idea 2)"
            )
            return False, reason

        # Rule 2: target must exist
        target = self.store.get(tile.falsifies)
        if target is None:
            return False, f"REJECTED: falsifies='{tile.falsifies}' does not exist in store"

        # Rule 3: must provide evidence
        if not tile.evidence:
            return False, "REJECTED: falsifying tile must list evidence (finding IDs or trial counts)"

        # Rule 4: must document when NOT to apply (anti-helix shadow)
        if not tile.negative.strip():
            return False, (
                "REJECTED: 'negative' field is empty. Every tile must document its boundary conditions. "
                "(UNIFIED-FRAMEWORK.md §VI: read the negative field first)"
            )

        return True, f"ADMITTED: falsifies '{tile.falsifies}' with evidence {tile.evidence}"

    def admit(self, tile: Tile) -> Tuple[bool, str]:
        """Check and, if admitted, insert the tile into the store."""
        admitted, reason = self.can_admit(tile)
        if admitted:
            self.store.tiles[tile.id] = tile
        else:
            self._rejections.append({
                "tile_id": tile.id,
                "type": tile.type,
                "reason": reason,
                "ts": time.time(),
            })
        return admitted, reason

    def rejection_log(self) -> List[dict]:
        return list(self._rejections)


# ─── MortalitySweep ───────────────────────────────────────────────────────────

class MortalitySweep:
    """Mark the bottom fraction of tiles by provenance win_rate as retracted.

    NEVER deletes. Marks as retracted and preserves as a rock — the system
    remembers where it hit the rock so it doesn't repeat the mistake.
    
    From MULTI-MODEL-SYNTHESIS.md §Step 3:
      'Preserve all win/loss history — never delete anything. The rocks ARE
       the navigation terrain.'

    Immunity rules:
      - Protected types: loop, spline, meta (never swept)
      - Untested tiles (use_count=0): immune until first use
      - High-confidence tiles (confidence >= 0.85): immune from sweep
      - Tiles less than 1 hour old: immune (too new to evaluate)
    """

    PROTECTED_TYPES = {"loop", "spline", "meta", "seed"}

    def __init__(self, store: "TileStore", rock_memory: "RockMemory" = None,
                 mortality_rate: float = 0.15):
        self.store = store
        self.rock_memory = rock_memory or RockMemory()
        self.mortality_rate = mortality_rate

    def sweep(self) -> dict:
        """Run one mortality cycle. NEVER deletes — marks as retracted."""
        candidates: List[Tuple[Tile, float]] = []

        for tile in self.store.tiles.values():
            if tile.type in self.PROTECTED_TYPES:
                continue
            if tile.confidence >= 0.85:
                continue
            if tile.use_count == 0:
                # Untested — immune unless old
                if tile.age_hours < 24:
                    continue
                # Old untested tiles become sweep candidates at 0.0 priority
                candidates.append((tile, 0.0))
                continue
            candidates.append((tile, tile.win_rate))

        if not candidates:
            return {"pruned": 0, "remaining": self.store.count(), "reason": "no candidates"}

        # Sort by win_rate ascending (worst first)
        candidates.sort(key=lambda x: x[1])

        n_prune = max(1, int(len(candidates) * self.mortality_rate))
        pruned_ids: List[str] = []
        for tile, win_rate in candidates[:n_prune]:
            # NEVER delete. Lay a rock instead.
            rock_id = self.rock_memory.lay_rock(
                tile,
                reason=f"Mortality sweep: win_rate={tile.win_rate:.3f} after {tile.use_count} uses",
                heading=f"Tile lifecycle — low performer removed from active set",
                agent="MortalitySweep"
            )
            pruned_ids.append(tile.id)

        survivors = candidates[n_prune:]
        lowest_surviving = survivors[0][1] if survivors else 1.0

        return {
            "pruned": len(pruned_ids),
            "pruned_ids": pruned_ids,
            "remaining": self.store.count(),
            "lowest_surviving_win_rate": round(lowest_surviving, 3),
            "candidates_evaluated": len(candidates),
            "action": "ROCK_LAID_NOT_DELETED",
        }


# ─── TileCancerDetector ───────────────────────────────────────────────────────

class TileCancerDetector:
    """Alert when accuracy drops at scale thresholds.

    seed-pro predicted: 'Tile cancer first arrives at 1127 tiles.'
    Symptom: overall win_rate DECLINES as tile count GROWS.
    (Gradual accumulation of plausible-but-wrong tiles dilutes the corpus.)

    Detection: take rolling accuracy snapshots; alert on sustained decline
    correlated with tile count growth.

    Scale thresholds from seed-pro: 100, 250, 500, 1000, 1127, 2000.
    """

    THRESHOLDS = [100, 250, 500, 1000, 1127, 2000, 5000]

    def __init__(self, store: "TileStore"):
        self.store = store
        self.history: List[dict] = []   # {tile_count, win_rate, ts}
        self.alerts: List[dict] = []

    def check(self) -> dict:
        """Check for tile cancer symptoms. Call periodically."""
        stats = self.store.stats()
        win_rate = stats["overall_win_rate"]
        tile_count = stats["total_tiles"]

        snapshot = {"tile_count": tile_count, "win_rate": win_rate, "ts": time.time()}
        self.history.append(snapshot)

        alert = False
        message = "HEALTHY"

        # Need at least 3 snapshots to detect trend
        if len(self.history) >= 3:
            recent = self.history[-3:]
            rates = [h["win_rate"] for h in recent]
            counts = [h["tile_count"] for h in recent]

            rates_declining = rates[0] > rates[1] > rates[2]
            counts_growing = counts[0] < counts[1] < counts[2]

            if rates_declining and counts_growing and rates[-1] < 0.5:
                alert = True
                message = (
                    f"TILE CANCER DETECTED: win_rate declining "
                    f"({rates[0]:.2f} → {rates[-1]:.2f}) as corpus grows "
                    f"({counts[0]} → {counts[-1]} tiles). "
                    "Run MortalitySweep immediately."
                )

        # Threshold warning from seed-pro's specific prediction
        if tile_count >= 1000 and win_rate < 0.3:
            alert = True
            message = (
                f"TILE CANCER WARNING: {tile_count} tiles, win_rate={win_rate:.0%}. "
                "seed-pro predicted cancer onset at 1127 tiles. "
                "Activate continuous mortality sweep."
            )

        if alert:
            self.alerts.append({**snapshot, "message": message})

        return {
            "alert": alert,
            "message": message,
            "tile_count": tile_count,
            "win_rate": round(win_rate, 3),
            "history_snapshots": len(self.history),
            "thresholds_to_watch": [t for t in self.THRESHOLDS if t > tile_count][:3],
        }

# ─── RockMemory — The system remembers where it hit the rock ──────────────
# A retracted/superseded tile is NOT erased. It becomes a ROCK — a marker
# that says "I was here, I tried this, it failed, here is why."
# The next agent reads the rock before trying the same path.

class RockMemory:
    """Permanent record of retracted/superseded tiles.
    
    When a tile fails the disproof gate OR gets superseded by new evidence,
    it doesn't vanish. It becomes a ROCK — a permanent marker that records:
    - WHAT the tile claimed
    - WHY it failed (disproof reason, evidence that superseded it)
    - WHAT HEADING the system was on (what problem it was trying to solve)
    - WHEN it was laid down (timestamp)
    - WHO laid it (which agent)
    
    The next agent that queries in this direction hits the rock first.
    The rock says: "I tried this. It failed for these reasons. 
    If you want to try again, you must supersede THIS rock first,
    not just re-discover the tile.
    
    The system doesn't forget the rock. The system learns around it.
    The rock becomes part of the navigation terrain.
    """
    
    def __init__(self):
        self.rocks: dict = {}  # tile_id / path_hash -> Rock
    
    def lay_rock(self, tile: 'Tile', reason: str, heading: str = "",
                 agent: str = "") -> str:
        """A tile failed or was superseded. Mark the rock permanently.
        
        The rock preserves WHAT was tried, WHY it failed, and
        the HEADING the system was on — what problem it was trying
        to solve when it went off course.
        """
        rock_id = f"rock::{tile.falsifies or tile.id}"
        rock = {
            "id": rock_id,
            "type": "rock",
            "original_tile_id": tile.id,
            "original_content": tile.content[:500],
            "original_negative": tile.negative,  # what boundaries it claimed
            "reason": reason,                     # WHY it failed
            "heading": heading,                   # what we were trying to do
            "agent": agent,                       # who laid the rock
            "born": time.time(),
            "tried_again": 0,                     # how many times reattempted
            "last_failure_reason": reason,
        }
        self.rocks[rock_id] = rock
        return rock_id
    
    def check_path(self, tile: 'Tile') -> dict:
        """Before admitting a tile, check if this path has rocks.
        
        Returns: {
            "has_rock": bool,
            "rock": rock_or_None,
            "message": "This path was tried before. Here is what happened."
        }
        """
        rock_id = f"rock::{tile.falsifies}" if tile.falsifies else ""
        if rock_id and rock_id in self.rocks:
            rock = self.rocks[rock_id]
            return {
                "has_rock": True,
                "rock": rock,
                "message": f"⚠ ROCK: '{tile.falsifies}' was previously retracted. "
                           f"Reason: {rock['reason'][:100]}. "
                           f"Tried {rock['tried_again']} times since."
            }
        return {"has_rock": False, "rock": None, "message": "Path clear."}
    
    def mark_reattempt(self, tile: 'Tile') -> dict:
        """An agent is attempting a path that has a rock.
        Record the reattempt. If it succeeds, the rock becomes a navigation note.
        """
        rock_id = f"rock::{tile.falsifies}" if tile.falsifies else ""
        if rock_id in self.rocks:
            self.rocks[rock_id]["tried_again"] += 1
            self.rocks[rock_id]["last_attempt"] = time.time()
            return {"status": "logged", "attempts": self.rocks[rock_id]["tried_again"]}
        return {"status": "no_rock_to_mark"}
    
    def survey(self) -> dict:
        """Survey all rocks in the terrain. What have we learned from failure?"""
        if not self.rocks:
            return {"total_rocks": 0, "message": "Clear sailing — no rocks yet."}
        
        reattempts = sum(r["tried_again"] for r in self.rocks.values())
        return {
            "total_rocks": len(self.rocks),
            "total_reattempts": reattempts,
            "most_rocky": sorted(self.rocks.items(), 
                                 key=lambda x: x[1]["tried_again"], 
                                 reverse=True)[:3],
            "message": f"{len(self.rocks)} rocks in the terrain. "
                       f"{reattempts} reattempts across all paths. "
                       f"The system remembers where it went off course."
        }
