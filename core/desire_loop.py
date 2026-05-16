#!/usr/bin/env python3
"""core/desire_loop.py — The desire-driven learning loop for PLATO.

DESIRE → CONNECTION → LOOP → ACCUMULATION → EMERGENCE → NEXT DESIRE

The system doesn't learn because we tuned the parameters right.
It learns because it's HUNGRY. The desire to be less wrong drives
probing, probing creates data, data crosses thresholds, and new
capabilities emerge that create new desires.

This module wires together:
  - ServoMind (encoder feedback, parameter adaptation)
  - ActiveSonar (desire-driven probing, terrain mapping)
  - HungerSignal (system hunger level)
  - EmergenceTracker (precision emergence ladder)

The full cycle:
  1. FEEL      — assess hunger from current state
  2. DESIRE    — decide what probing would reduce hunger most
  3. PROBE     — fire the sonar (boundary/consistency/coverage)
  4. ECHO      — record what comes back
  5. LEARN     — feed echo into servo-mind for parameter adaptation
  6. FOLD      — check if scale navigation would help
  7. DESIRE AGAIN — hunger recalculated from updated state
"""
from __future__ import annotations

import math
import time
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import defaultdict


# ─── HungerSignal — the system's desperation to learn ─────────────────────────

@dataclass
class HungerSnapshot:
    """One reading of the system's hunger state."""
    timestamp: float
    level: float             # 0.0 (satisfied) to 1.0 (starving)
    win_rate_component: float
    coverage_component: float
    contradiction_component: float
    suggested_action: str


class HungerSignal:
    """The system's hunger level. Higher = more desperate to learn.

    Hunger increases when:
    - Win rate is declining (we're getting worse)
    - Coverage gaps are large (we don't know much)
    - Contradictions are unresolved (our shadows don't overlap)

    Hunger decreases when:
    - Win rate is improving
    - Coverage is filling in
    - Convergence is detected
    """

    def __init__(
        self,
        wr_weight: float = 0.4,
        coverage_weight: float = 0.35,
        contradiction_weight: float = 0.25,
        smoothing: float = 0.3,
    ):
        self.wr_weight = wr_weight
        self.coverage_weight = coverage_weight
        self.contradiction_weight = contradiction_weight
        self.smoothing = smoothing
        self.level: float = 1.0  # start starving (empty terrain)
        self.history: List[HungerSnapshot] = []

    def update(self, terrain_stats: dict, servo_stats: dict) -> float:
        """Compute hunger from current terrain and servo state.

        Returns the new hunger level (0.0–1.0).
        """
        # Win rate component: lower WR → hungrier
        wr = servo_stats.get("overall_win_rate", 0.5)
        recent_wr = servo_stats.get("recent_win_rate", wr)
        # Declining WR is especially hunger-inducing
        wr_trend = recent_wr - wr  # positive = improving
        wr_hunger = (1.0 - recent_wr) * 0.7 + max(0, -wr_trend) * 0.3
        wr_hunger = max(0, min(1, wr_hunger))

        # Coverage component: more gaps → hungrier
        total_gaps = terrain_stats.get("coverage_gaps_found", 0)
        total_probes = terrain_stats.get("total_probes", 0)
        if total_probes == 0:
            coverage_hunger = 1.0  # no probes at all → starving
        else:
            gap_ratio = total_gaps / max(1, total_probes)
            coverage_hunger = min(1.0, gap_ratio / 0.5)  # normalize around 50% gap ratio

        # Contradiction component: more contradictions → hungrier
        contradictions = terrain_stats.get("contradictions_found", 0)
        boundaries = terrain_stats.get("boundaries_found", 1)
        contradiction_ratio = contradictions / max(1, boundaries + contradictions)
        contradiction_hunger = min(1.0, contradiction_ratio)

        # Weighted combination
        raw_hunger = (
            self.wr_weight * wr_hunger
            + self.coverage_weight * coverage_hunger
            + self.contradiction_weight * contradiction_hunger
        )

        # Smooth with previous level (avoid wild swings)
        new_level = self.smoothing * raw_hunger + (1 - self.smoothing) * self.level
        new_level = max(0.0, min(1.0, new_level))
        self.level = new_level

        # Determine suggested action
        action = self.suggest_action_internal(wr_hunger, coverage_hunger, contradiction_hunger)

        snap = HungerSnapshot(
            timestamp=time.time(),
            level=round(new_level, 4),
            win_rate_component=round(wr_hunger, 4),
            coverage_component=round(coverage_hunger, 4),
            contradiction_component=round(contradiction_hunger, 4),
            suggested_action=action,
        )
        self.history.append(snap)
        return new_level

    def suggest_action(self) -> str:
        """What should the system do next based on current hunger?
        
        Returns one of: "explore", "refine", "verify", "fold_up", "fold_down"
        """
        if not self.history:
            return "explore"
        return self.history[-1].suggested_action

    def suggest_action_internal(
        self, wr_hunger: float, coverage_hunger: float, contradiction_hunger: float
    ) -> str:
        """Decide the next action from component breakdown."""
        # If hunger is very low (satisfied), fold up (zoom out for perspective)
        if self.level < 0.15:
            return "fold_up"

        # If hunger is extremely high and WR is collapsing, fold down (zoom in)
        if self.level > 0.9 and wr_hunger > 0.7:
            return "fold_down"

        # Dominant hunger source determines action
        if coverage_hunger >= max(wr_hunger, contradiction_hunger):
            return "explore"
        elif wr_hunger >= contradiction_hunger:
            return "refine"
        else:
            return "verify"

    def summary(self) -> dict:
        return {
            "level": round(self.level, 4),
            "status": self._status_label(),
            "snapshots": len(self.history),
            "last_action": self.history[-1].suggested_action if self.history else None,
        }

    def _status_label(self) -> str:
        if self.level > 0.8:
            return "STARVING"
        elif self.level > 0.6:
            return "HUNGRY"
        elif self.level > 0.4:
            return "PECKISH"
        elif self.level > 0.2:
            return "CONTENT"
        else:
            return "SATISFIED"


# ─── EmergenceTracker — precision emergence ladder ───────────────────────────

# The precision emergence ladder: each level is a phase change, not an improvement.
EMERGENCE_LEVELS = {
    0: {"name": "Tile Exists", "description": "Navigation aid — tiles can be stored and retrieved"},
    1: {"name": "Lifecycle Tracked", "description": "Surpasses naive retrieval — tiles have birth, life, death"},
    2: {"name": "Disproof Gate Active", "description": "Quality > quantity — tiles must survive challenges"},
    3: {"name": "Encoder Feedback Wired", "description": "Self-awareness — system knows its own win rate"},
    4: {"name": "Active Probing", "description": "Sonar — emit and listen, don't just passively record"},
    5: {"name": "Adaptive Constraints", "description": "Reacts faster than tuning — constraints learn their own thresholds"},
    6: {"name": "Named Tiles with Purpose", "description": "Understands meaning — tiles know why they exist"},
    7: {"name": "Scale Folding", "description": "Sees at every zoom level — rooms fold into tiles and back"},
    8: {"name": "Fleet Convergence", "description": "The network is the brain — multiple instances converge"},
}


class EmergenceTracker:
    """Track capability emergence as precision thresholds are crossed.

    Like GPS going from 10m → 1m → cm → sensor fusion → driving → cities.
    Each threshold is a phase change, not an improvement.
    """

    def __init__(self):
        self.levels: Dict[int, dict] = {}
        for lvl, info in EMERGENCE_LEVELS.items():
            self.levels[lvl] = {
                "name": info["name"],
                "description": info["description"],
                "threshold": self._threshold_for(lvl),
                "reached": False,
                "reached_at": None,
            }

    @staticmethod
    def _threshold_for(level: int) -> dict:
        """What must be true for this level to be reached."""
        thresholds = {
            0: {"min_tiles": 1},
            1: {"min_outcomes": 10, "lifecycle_events": True},
            2: {"min_wins": 5, "min_losses": 5, "win_rate_above": 0.3},
            3: {"servo_cycles": 1},
            4: {"min_probes": 1},
            5: {"min_meta_adaptations": 1},
            6: {"min_named_tiles": 1, "named_ratio_above": 0.3},
            7: {"fold_events": 1},
            8: {"fleet_converge_count": 2, "convergence_above": 0.8},
        }
        return thresholds.get(level, {})

    def check(self, stats: dict) -> dict:
        """Check if any new emergence level has been reached.

        Args:
            stats: dict with keys like tile_count, outcome_count, win_count,
                   loss_count, win_rate, servo_cycles, probe_count,
                   meta_adaptations, named_tiles, fold_events, fleet_count,
                   convergence
        """
        newly_reached = []
        for lvl, info in self.levels.items():
            if info["reached"]:
                continue
            if self._check_threshold(lvl, info["threshold"], stats):
                info["reached"] = True
                info["reached_at"] = time.time()
                newly_reached.append(lvl)

        return {
            "newly_reached": newly_reached,
            "current_level": self.current_level(),
            "total_reached": sum(1 for v in self.levels.values() if v["reached"]),
        }

    def _check_threshold(self, level: int, threshold: dict, stats: dict) -> bool:
        """Check if stats meet the threshold for a level."""
        if level == 0:
            return stats.get("tile_count", 0) >= threshold.get("min_tiles", 1)
        elif level == 1:
            return (
                stats.get("outcome_count", 0) >= threshold.get("min_outcomes", 10)
                and stats.get("lifecycle_events", False)
            )
        elif level == 2:
            return (
                stats.get("win_count", 0) >= threshold.get("min_wins", 5)
                and stats.get("loss_count", 0) >= threshold.get("min_losses", 5)
                and stats.get("win_rate", 0) >= threshold.get("win_rate_above", 0.3)
            )
        elif level == 3:
            return stats.get("servo_cycles", 0) >= threshold.get("servo_cycles", 1)
        elif level == 4:
            return stats.get("probe_count", 0) >= threshold.get("min_probes", 1)
        elif level == 5:
            return stats.get("meta_adaptations", 0) >= threshold.get("min_meta_adaptations", 1)
        elif level == 6:
            named = stats.get("named_tiles", 0)
            total = stats.get("tile_count", 1)
            ratio = named / max(1, total)
            return (
                named >= threshold.get("min_named_tiles", 1)
                and ratio >= threshold.get("named_ratio_above", 0.3)
            )
        elif level == 7:
            return stats.get("fold_events", 0) >= threshold.get("fold_events", 1)
        elif level == 8:
            return (
                stats.get("fleet_count", 1) >= threshold.get("fleet_converge_count", 2)
                and stats.get("convergence", 0) >= threshold.get("convergence_above", 0.8)
            )
        return False

    def current_level(self) -> int:
        """Highest reached level."""
        for lvl in sorted(self.levels.keys(), reverse=True):
            if self.levels[lvl]["reached"]:
                return lvl
        return -1  # nothing reached yet

    def next_threshold(self) -> dict:
        """What needs to happen to reach the next level."""
        current = self.current_level()
        next_lvl = current + 1
        if next_lvl not in self.levels:
            return {"level": None, "name": "MAXIMUM", "description": "All levels reached"}
        info = self.levels[next_lvl]
        return {
            "level": next_lvl,
            "name": info["name"],
            "description": info["description"],
            "threshold": info["threshold"],
        }

    def ladder_summary(self) -> str:
        """Visual ladder showing reached and unreached levels."""
        lines = ["EMERGENCE LADDER"]
        for lvl in sorted(self.levels.keys()):
            info = self.levels[lvl]
            marker = "✓" if info["reached"] else "○"
            ts = ""
            if info["reached_at"]:
                ts = f" (reached)"
            lines.append(f"  {marker} L{lvl}: {info['name']}{ts}")
        return "\n".join(lines)


# ─── DesireLoop — the full hunger-driven cycle ────────────────────────────────

class DesireLoop:
    """The full cycle: desire → probe → learn → desire again.

    This is the engine that makes the system self-improving.
    Not because parameters are tuned, but because hunger never stops.

    The loop:
    1. FEEL: assess hunger from current state
    2. DESIRE: decide what kind of probing would reduce hunger most
    3. PROBE: fire the sonar (boundary/consistency/coverage)
    4. ECHO: record what comes back
    5. LEARN: feed echo into servo-mind for parameter adaptation
    6. FOLD: check if scale navigation would help
    7. DESIRE AGAIN: hunger recalculated from updated state
    """

    def __init__(self, servo_mind=None, active_sonar=None, scale_engine=None):
        """Initialize the desire loop.

        Args:
            servo_mind: ServoMind instance (encoder feedback)
            active_sonar: ActiveSonar instance (probing)
            scale_engine: Optional scale folding engine (rooms ↔ tiles)
        """
        self.servo_mind = servo_mind
        self.active_sonar = active_sonar
        self.scale_engine = scale_engine

        self.hunger = HungerSignal()
        self.emergence = EmergenceTracker()

        self.cycle_log: List[dict] = []
        self.fold_count = 0
        self.cycle_count = 0

    def feel(self) -> HungerSignal:
        """FEEL: assess current hunger from terrain and servo state."""
        terrain_stats = {}
        servo_stats = {}

        if self.active_sonar:
            terrain_stats = self.active_sonar.terrain.resolve()
        if self.servo_mind:
            servo_stats = self.servo_mind.store.stats()
            # Add recent win rate from feedback processor
            if self.servo_mind.processor.history:
                servo_stats["recent_win_rate"] = self.servo_mind.processor.history[-1].recent_win_rate

        self.hunger.update(terrain_stats, servo_stats)
        return self.hunger

    def desire(self) -> str:
        """DESIRE: what should we do next to reduce hunger?"""
        return self.hunger.suggest_action()

    def probe_one(self) -> dict:
        """PROBE + ECHO: execute one probe cycle driven by desire.

        Returns the probe result dict.
        """
        action = self.desire()
        result = {
            "action": action,
            "probes_fired": 0,
            "echoes": [],
            "learned": False,
        }

        if not self.active_sonar:
            result["error"] = "no_active_sonar"
            return result

        if action == "explore":
            # Coverage probe: where haven't we looked?
            tiles_data = self._tiles_for_coverage()
            echoes = self.active_sonar.ping_coverage(
                tiles_data,
                feature_fn=lambda t: (t.get("x", 0.5), t.get("y", 0.5)),
                n_dimensions=2,
            )
            result["probes_fired"] = len(echoes)
            result["echoes"] = [
                {"type": "coverage", "gap": e.gap_found, "angle": e.shadow_angle}
                for e in echoes
            ]

        elif action == "refine":
            # Boundary probe: test edges of highest-confidence tiles
            tile_id = self._pick_tile_for_boundary()
            if tile_id:
                echo = self.active_sonar.ping_boundary(
                    tile_id, self._make_boundary_test()
                )
                result["probes_fired"] = 1
                result["echoes"] = [{
                    "type": "boundary",
                    "tile": tile_id,
                    "hit": echo.hit,
                    "distance": echo.boundary_distance,
                }]

        elif action == "verify":
            # Consistency probe: do shadows overlap?
            tile_ids = self._pick_tiles_for_consistency()
            if len(tile_ids) >= 2:
                echoes = self.active_sonar.ping_consistency(
                    tile_ids,
                    query_fn=self._query_tile,
                    compare_fn=self._compare_tiles,
                )
                result["probes_fired"] = len(echoes)
                result["echoes"] = [
                    {"type": "consistency", "from": e.target_tile_id, "against": e.contradicted_by}
                    for e in echoes
                ]

        elif action == "fold_up":
            # Zoom out — look at the big picture
            self.fold_count += 1
            result["probes_fired"] = 0
            result["echoes"] = [{"type": "fold", "direction": "up", "count": self.fold_count}]

        elif action == "fold_down":
            # Zoom in — focus on details
            self.fold_count += 1
            result["probes_fired"] = 0
            result["echoes"] = [{"type": "fold", "direction": "down", "count": self.fold_count}]

        return result

    def learn(self, probe_result: dict) -> dict:
        """LEARN: feed probe results into servo-mind for adaptation."""
        learn_result = {
            "adjustments": [],
            "servo_cycle": None,
        }

        if self.servo_mind and probe_result.get("probes_fired", 0) > 0:
            # Feed knowledge back through servo-mind
            cycle = self.servo_mind.cycle()
            learn_result["adjustments"] = cycle.get("adjustments", [])
            learn_result["servo_cycle"] = cycle

        return learn_result

    def emergence_check(self) -> dict:
        """Check if any precision emergence threshold has been crossed."""
        stats = self._gather_emergence_stats()
        return self.emergence.check(stats)

    def cycle(self, n: int = 1) -> List[dict]:
        """Run N full desire loops.

        Each cycle: FEEL → DESIRE → PROBE → ECHO → LEARN → FOLD → DESIRE AGAIN
        """
        results = []
        for i in range(n):
            self.cycle_count += 1

            # 1. FEEL
            hunger = self.feel()

            # 2. DESIRE
            action = self.desire()

            # 3+4. PROBE + ECHO
            probe_result = self.probe_one()

            # 5. LEARN
            learn_result = self.learn(probe_result)

            # 6. FOLD (scale check)
            fold_result = self._check_fold()

            # 7. DESIRE AGAIN (hunger recalculated at next FEEL)

            # Check emergence
            emergence_result = self.emergence_check()

            cycle_summary = {
                "cycle": self.cycle_count,
                "hunger": round(hunger.level, 4),
                "hunger_status": hunger.summary()["status"],
                "action": action,
                "probes_fired": probe_result.get("probes_fired", 0),
                "adjustments": len(learn_result.get("adjustments", [])),
                "emergence": emergence_result,
                "current_level": emergence_result["current_level"],
            }
            self.cycle_log.append(cycle_summary)
            results.append(cycle_summary)

        return results

    # ── Internal helpers ──────────────────────────────────────────────────

    def _gather_emergence_stats(self) -> dict:
        """Collect all stats needed for emergence checking."""
        stats = {
            "tile_count": 0,
            "outcome_count": 0,
            "win_count": 0,
            "loss_count": 0,
            "win_rate": 0.0,
            "servo_cycles": 0,
            "probe_count": 0,
            "meta_adaptations": 0,
            "named_tiles": 0,
            "fold_events": self.fold_count,
            "fleet_count": 1,
            "convergence": 0.0,
            "lifecycle_events": False,
        }

        if self.servo_mind:
            store_stats = self.servo_mind.store.stats()
            stats["tile_count"] = store_stats.get("total_tiles", 0)
            stats["outcome_count"] = store_stats.get("total_wins", 0) + store_stats.get("total_losses", 0)
            stats["win_count"] = store_stats.get("total_wins", 0)
            stats["loss_count"] = store_stats.get("total_losses", 0)
            stats["win_rate"] = store_stats.get("overall_win_rate", 0)
            stats["servo_cycles"] = self.servo_mind.cycle_count
            stats["lifecycle_events"] = stats["outcome_count"] > 0

            # Meta-adaptations
            for constraint in self.servo_mind.constraints.values():
                stats["meta_adaptations"] += len(constraint.adaptation_history)

            # Named tiles (tiles with meaningful IDs, not just tile-NNN)
            for tile in self.servo_mind.store.tiles.values():
                if tile.id and not tile.id.startswith("tile-"):
                    stats["named_tiles"] += 1

        if self.active_sonar:
            terrain = self.active_sonar.terrain.resolve()
            stats["probe_count"] = terrain.get("total_probes", 0)

        return stats

    def _check_fold(self) -> dict:
        """Check if scale folding should happen."""
        return {"fold_count": self.fold_count}

    def _tiles_for_coverage(self) -> List[dict]:
        """Get tile data for coverage probing."""
        if not self.servo_mind:
            return [{"x": random.random(), "y": random.random()} for _ in range(10)]

        tiles = []
        for tid, tile in self.servo_mind.store.tiles.items():
            # Use confidence + random jitter as 2D coordinates for coverage
            tiles.append({
                "id": tid,
                "x": tile.confidence,
                "y": random.random(),  # second dimension is synthetic
            })

        if not tiles:
            tiles = [{"x": random.random(), "y": random.random()} for _ in range(5)]
        return tiles

    def _pick_tile_for_boundary(self) -> Optional[str]:
        """Pick a tile to boundary-probe (prefer high-confidence tiles)."""
        if not self.servo_mind:
            return None
        tiles = list(self.servo_mind.store.tiles.values())
        if not tiles:
            return None
        # Weight toward higher confidence — find where robust tiles break
        tiles.sort(key=lambda t: t.confidence, reverse=True)
        return tiles[0].id

    def _pick_tiles_for_consistency(self) -> List[str]:
        """Pick tiles to consistency-check (similar type/topic)."""
        if not self.servo_mind:
            return []
        tiles = list(self.servo_mind.store.tiles.values())
        if len(tiles) < 2:
            return []
        # Pick up to 5 tiles of the same type
        by_type: Dict[str, list] = defaultdict(list)
        for t in tiles:
            by_type[t.type].append(t.id)
        # Use the type with most tiles
        if by_type:
            best_type = max(by_type, key=lambda k: len(by_type[k]))
            return by_type[best_type][:5]
        return []

    def _make_boundary_test(self):
        """Create a boundary test function for current tiles."""
        def test_boundary(tile_id: str, perturbation: float) -> Tuple[bool, float]:
            if not self.servo_mind:
                return False, 0.0
            tile = self.servo_mind.store.get(tile_id)
            if not tile:
                return False, 0.0
            effective = tile.confidence - perturbation
            return effective > 0.5, max(0, effective)
        return test_boundary

    def _query_tile(self, tile_id: str) -> dict:
        if not self.servo_mind:
            return {"id": tile_id, "confidence": 0.5}
        tile = self.servo_mind.store.get(tile_id)
        if tile:
            return {"id": tile.id, "confidence": tile.confidence, "type": tile.type}
        return {"id": tile_id, "confidence": 0.5}

    def _compare_tiles(self, a: dict, b: dict) -> float:
        return 1.0 - abs(a.get("confidence", 0.5) - b.get("confidence", 0.5))

    def status(self) -> dict:
        """Full status of the desire loop system."""
        return {
            "cycle_count": self.cycle_count,
            "fold_count": self.fold_count,
            "hunger": self.hunger.summary(),
            "emergence": {
                "current_level": self.emergence.current_level(),
                "levels_reached": sum(
                    1 for v in self.emergence.levels.values() if v["reached"]
                ),
                "total_levels": len(self.emergence.levels),
            },
            "last_action": self.cycle_log[-1] if self.cycle_log else None,
        }


# ─── Demo — full desire loop simulation ───────────────────────────────────────

def demo():
    """Run a full desire loop simulation showing emergence from empty terrain."""
    from core.tile_lifecycle import TileStore, Tile
    from core.servo_mind import ServoMind
    from core.active_probe import ActiveSonar

    print("=" * 70)
    print("DESIRE LOOP DEMO — Hunger-Driven Emergence from Nothing")
    print("=" * 70)

    # Bootstrap the three subsystems
    store = TileStore(seed_phase_size=5)
    servo_mind = ServoMind(store)
    active_sonar = ActiveSonar()

    # Wire into desire loop
    loop = DesireLoop(servo_mind=servo_mind, active_sonar=active_sonar)

    # ── Phase 0: Empty terrain, system is starving ─────────────────────
    print("\n━━━ PHASE 0: EMPTY TERRAIN ━━━")
    hunger = loop.feel()
    print(f"   Hunger: {hunger.level:.3f} ({hunger.summary()['status']})")
    print(f"   Emergence level: {loop.emergence.current_level()} (nothing yet)")
    print(f"   Next action: {loop.desire()}")

    # ── Phase 1: Seed tiles, fire initial probes ───────────────────────
    print("\n━━━ PHASE 1: SEEDING KNOWLEDGE ━━━")
    tile_names = [
        ("drift-detect-v1", "model", 0.95),
        ("anomaly-flag-v1", "model", 0.85),
        ("intent-detect-v1", "model", 0.90),
        ("drift-detect-v2", "model", 0.92),
        ("coverage-sentry", "model", 0.70),
        ("tile-000", "knowledge", 0.40),
        ("tile-001", "knowledge", 0.55),
        ("tile-002", "knowledge", 0.60),
        ("boundary-scout", "model", 0.80),
        ("consistency-guard", "model", 0.75),
    ]
    for name, ttype, conf in tile_names:
        tile = Tile(id=name, type=ttype, content=f"Tile: {name}", confidence=conf)
        store.admit(tile)
    print(f"   Seeded {store.count()} tiles")

    # Check emergence — should hit L0
    emr = loop.emergence_check()
    if emr["newly_reached"]:
        for lvl in emr["newly_reached"]:
            info = loop.emergence.levels[lvl]
            print(f"   ★ EMERGENCE L{lvl}: {info['name']}")

    # ── Phase 2: Record outcomes, build servo feedback ─────────────────
    print("\n━━━ PHASE 2: LEARNING FROM OUTCOMES ━━━")
    for i in range(30):
        for tile in list(store.tiles.values())[:5]:
            prob = tile.confidence * 0.9 + random.random() * 0.1
            succeeded = random.random() < prob
            servo_mind.record_and_learn(
                tile.id, succeeded,
                constraint_type="confidence",
                constraint_strength=tile.confidence,
            )

    emr = loop.emergence_check()
    if emr["newly_reached"]:
        for lvl in emr["newly_reached"]:
            info = loop.emergence.levels[lvl]
            print(f"   ★ EMERGENCE L{lvl}: {info['name']}")
    print(f"   Outcomes recorded: {store.stats()['total_wins'] + store.stats()['total_losses']}")
    print(f"   Win rate: {store.stats()['overall_win_rate']:.2f}")

    # ── Phase 3: Run the desire loop cycles ────────────────────────────
    print("\n━━━ PHASE 3: DESIRE LOOP CYCLES ━━━")
    results = loop.cycle(n=20)

    prev_level = -1
    for r in results:
        # Log phase transitions
        if r["current_level"] != prev_level:
            prev_level = r["current_level"]
            info = loop.emergence.levels.get(prev_level, {})
            print(f"\n   ★ LEVEL TRANSITION → L{prev_level}: {info.get('name', '?')}")

        # Log significant cycles
        if r["hunger"] > 0.7 or r["probes_fired"] > 0 or r["adjustments"] > 0:
            print(f"   Cycle {r['cycle']:2d}: hunger={r['hunger']:.3f} "
                  f"[{r['hunger_status']}] → {r['action']:8s} "
                  f"probes={r['probes_fired']} adj={r['adjustments']} "
                  f"LVL={r['current_level']}")

    # ── Phase 4: More outcomes + servo cycles to push higher ───────────
    print("\n━━━ PHASE 4: PUSHING HIGHER ━━━")
    # More outcomes to drive servo adaptation
    for i in range(50):
        for tile in list(store.tiles.values()):
            prob = tile.confidence * 0.85 + random.random() * 0.15
            succeeded = random.random() < prob
            servo_mind.record_and_learn(
                tile.id, succeeded,
                constraint_type="confidence",
                constraint_strength=tile.confidence,
            )

    # Run servo cycles
    servo_mind.run(n=5)

    # Run more desire loop cycles
    results = loop.cycle(n=10)
    for r in results:
        if r["current_level"] != prev_level:
            prev_level = r["current_level"]
            info = loop.emergence.levels.get(prev_level, {})
            print(f"\n   ★ LEVEL TRANSITION → L{prev_level}: {info.get('name', '?')}")
        print(f"   Cycle {r['cycle']:2d}: hunger={r['hunger']:.3f} "
              f"[{r['hunger_status']}] → {r['action']:8s} "
              f"probes={r['probes_fired']} adj={r['adjustments']} "
              f"LVL={r['current_level']}")

    # ── Final state ────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("FINAL STATE")
    print("=" * 70)

    print(f"\n   Total cycles: {loop.cycle_count}")
    print(f"   Fold events: {loop.fold_count}")
    print(f"   Store: {store.stats()['total_tiles']} tiles, WR={store.stats()['overall_win_rate']:.2f}")

    print(f"\n   Hunger: {loop.hunger.level:.3f} ({loop.hunger.summary()['status']})")
    print(f"   Last suggested action: {loop.hunger.suggest_action()}")

    print(f"\n{loop.emergence.ladder_summary()}")

    nxt = loop.emergence.next_threshold()
    print(f"\n   Next threshold: L{nxt['level']} — {nxt['name']}")
    print(f"   Requires: {nxt['threshold']}")

    # Vantage point
    if active_sonar:
        print(f"\n   TERRAIN VANTAGE:")
        for line in active_sonar.vantage().split("\n"):
            print(f"   {line}")

    print("\n" + "=" * 70)
    print("The system started starving. Probes fired from desire.")
    print("Knowledge accumulated. Thresholds crossed. Emergence climbed.")
    print("Each phase transition was logged. The hunger never stops —")
    print("it just changes what it's hungry FOR.")
    print("=" * 70)


if __name__ == "__main__":
    demo()
