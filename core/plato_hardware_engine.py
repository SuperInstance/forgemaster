"""
core/plato_hardware_engine.py — PLATO Hardware Foundation Layer

Answers three questions:
1. What can be parallel? (tile reads, independent room queries, batch submits)
2. What must be sequential? (disproof gates, consensus writes, cross-room propagation)
3. How does time work? (not a clock — a projected future state agents converge on)

Plus: SnappingLogic for orienting different models (GLM-5.1, Seed-mini, DeepSeek)
onto a shared coordinate system despite their different internal representations.

Biological parallel: The hardware engine is the nervous system + circulatory system.
Parallel operations are capillaries (many at once, no ordering needed).
Sequential operations are nerve impulses (order matters, gates fire in sequence).
Time sync is the circadian rhythm — agents don't share a clock, they share a
projected future state that each independently navigates toward.

The key philosophical insight: time in PLATO is not a clock. It's a PROJECTED STATE
that all agents navigate toward independently, self-synchronizing through the
convergence of their individual utility functions on the same attractor.

Like boids converging on a shared destination without communicating — they SEE the
same target, not because they agreed, but because the target is the attractor
their individual trajectories converge on.

Evidence: ARCHITECTURE.md §4 Data Flow (full cycle), §2.6 Supercolony
          fleet_intel.py CollectiveTerrain (convergence without orchestration)
          tile_lifecycle.py DisproofOnlyGate (sequential gate enforcement)
"""

from __future__ import annotations

import time
import hashlib
import threading
import concurrent.futures
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple, Any, Callable
from collections import defaultdict
from enum import Enum

# ─── Imports from existing modules ────────────────────────────────────────────

try:
    from .tile_lifecycle import Tile, TileStore, DisproofOnlyGate
except ImportError:
    Tile = None
    TileStore = None
    DisproofOnlyGate = None

try:
    from .plato_shell_bridge import PlatoShell, PlatoShellCollection, PLATO_URL
except ImportError:
    PlatoShell = None
    PlatoShellCollection = None
    PLATO_URL = "http://147.224.38.131:8847"


# ─── Constants ─────────────────────────────────────────────────────────────────

MAX_WORKERS = 8                    # Max parallel threads for scatter/gather
CONSENSUS_QUORUM = 0.6             # 60% of participants must agree
PROPAGATION_BATCH_SIZE = 10        # Tiles per propagation wave
SNAP_TOLERANCE = 0.15              # Tolerance for snapping across models
TIME_HORIZON = 5                   # Default projection horizon (cycles)
AFFINITY_MIN_SAMPLES = 3           # Min samples to compute model affinity


# ─── ParallelPlato ─────────────────────────────────────────────────────────────

class ParallelPlato:
    """Parallel PLATO operations. These don't need sequential ordering.

    Parallelism in PLATO mirrors capillary beds in biology — many tiny vessels
    doing the same work simultaneously, feeding into larger venules. The order
    doesn't matter because each operation is independent.

    What can be parallel:
    - Reading tiles from different rooms (no write dependency)
    - Running ecosystem cycles on independent rooms
    - Scatter/gather tile searches across the fleet
    - Computing confidence scores for independent tiles
    - Probing boundaries of different tiles simultaneously

    What CANNOT be parallel (see SequentialPlato):
    - Disproof gate checks (one tile's admission depends on the current corpus)
    - Consensus writes (participants must agree before writing)
    - Cross-room propagation (target rooms must be in consistent state)
    - Mortality sweeps (pruning changes what's available for other operations)
    """

    def __init__(self, plato_url: str = PLATO_URL, max_workers: int = MAX_WORKERS):
        self.plato_url = plato_url.rstrip("/")
        self.max_workers = max_workers
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self._stats = {"batch_reads": 0, "parallel_cycles": 0, "scatter_gathers": 0}

    def batch_read_rooms(self, room_ids: list) -> dict:
        """Read multiple rooms in parallel. No ordering dependency.

        Each room read is independent — one room's tiles don't affect
        another room's tiles during a read. This is the PLATO equivalent
        of fan-out read in a distributed database.

        Returns:
            {room_id: {"tiles": [...], "tile_count": N, "agents": [...], "error": None|str}}
        """
        results = {}

        def _read_one(room_id: str) -> Tuple[str, dict]:
            try:
                shell = PlatoShell(room_id, self.plato_url)
                return room_id, {
                    "tiles": shell.tiles,
                    "tile_count": shell.tile_count,
                    "agents": shell.agents_present,
                    "domain": shell.domain,
                    "outgrown": shell.is_outgrown(),
                    "error": None,
                }
            except Exception as e:
                return room_id, {
                    "tiles": [],
                    "tile_count": 0,
                    "agents": [],
                    "domain": "",
                    "outgrown": False,
                    "error": str(e),
                }

        futures = {
            self._executor.submit(_read_one, rid): rid
            for rid in room_ids
        }

        for future in concurrent.futures.as_completed(futures):
            room_id, data = future.result()
            results[room_id] = data

        self._stats["batch_reads"] += 1
        return results

    def parallel_ecosystem_cycles(self, ecosystem_configs: list) -> dict:
        """Run multiple ecosystem cycles in parallel.

        Each ecosystem config is an independent room with its own
        cycle parameters. They don't share state during the cycle,
        so they can run simultaneously.

        ecosystem_configs: list of dicts, each with:
            - room_id: str
            - cycle_type: str ("probe", "sweep", "feedback", "full")
            - params: dict (optional params for the cycle)

        Returns:
            {room_id: {"success": bool, "result": dict, "duration_ms": float}}
        """
        results = {}

        def _run_cycle(config: dict) -> Tuple[str, dict]:
            room_id = config.get("room_id", "unknown")
            start = time.time()
            try:
                shell = PlatoShell(room_id, self.plato_url)
                cycle_type = config.get("cycle_type", "full")
                params = config.get("params", {})

                # Each cycle type is independent work
                cycle_result = {
                    "room_id": room_id,
                    "cycle_type": cycle_type,
                    "tile_count_before": shell.tile_count,
                    "agents": shell.agents_present,
                    "domain": shell.domain,
                }

                if cycle_type == "probe":
                    # Boundary probe on room tiles (parallel-safe: read-only)
                    tiles = shell.tiles[:20]
                    cycle_result["probed_tiles"] = len(tiles)
                    cycle_result["confidence_range"] = (
                        min(t.get("confidence", 0.5) for t in tiles) if tiles else 0.0,
                        max(t.get("confidence", 0.5) for t in tiles) if tiles else 1.0,
                    )

                elif cycle_type == "sweep":
                    # Compute mortality candidates (read-only analysis)
                    tiles = shell.tiles
                    candidates = [
                        t for t in tiles
                        if t.get("confidence", 0.5) < 0.85
                        and t.get("type", "knowledge") not in ("loop", "spline", "meta", "seed")
                    ]
                    cycle_result["sweep_candidates"] = len(candidates)
                    cycle_result["would_prune"] = max(1, int(len(candidates) * 0.15))

                elif cycle_type == "feedback":
                    # Compute feedback snapshot (read-only)
                    tiles = shell.tiles
                    wins = sum(1 for t in tiles if t.get("win_count", 0) > t.get("loss_count", 0))
                    total = max(len(tiles), 1)
                    cycle_result["win_rate"] = wins / total
                    cycle_result["feedback_signal"] = "stable" if wins / total > 0.5 else "declining"

                else:  # "full"
                    tiles = shell.tiles
                    cycle_result["total_tiles"] = len(tiles)
                    cycle_result["tile_types"] = dict(
                        defaultdict(int, {
                            t.get("type", "unknown"): sum(
                                1 for x in tiles if x.get("type", "unknown") == t.get("type", "unknown")
                            )
                            for t in tiles[:50]
                        })
                    )

                duration_ms = (time.time() - start) * 1000
                return room_id, {
                    "success": True,
                    "result": cycle_result,
                    "duration_ms": round(duration_ms, 2),
                }
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                return room_id, {
                    "success": False,
                    "result": {"error": str(e)},
                    "duration_ms": round(duration_ms, 2),
                }

        futures = {
            self._executor.submit(_run_cycle, cfg): cfg.get("room_id", f"cfg_{i}")
            for i, cfg in enumerate(ecosystem_configs)
        }

        for future in concurrent.futures.as_completed(futures):
            room_id, data = future.result()
            results[room_id] = data

        self._stats["parallel_cycles"] += 1
        return results

    def scatter_gather_tiles(self, query: str, n_workers: int = 4) -> dict:
        """Scatter a query across workers, gather results.

        Like casting a net — each worker searches a different partition
        of the tile space. Results are merged at the gather step.

        query: search string to match against tile content/trigger
        n_workers: how many parallel workers to use

        Returns:
            {"results": [...], "total_found": N, "workers_used": N,
             "duration_ms": float, "deduped": N}
        """
        start = time.time()

        try:
            collection = PlatoShellCollection(self.plato_url)
            rooms = collection._fetch_rooms()[:n_workers * 5]
        except Exception:
            rooms = []

        if not rooms:
            return {
                "results": [],
                "total_found": 0,
                "workers_used": 0,
                "duration_ms": round((time.time() - start) * 1000, 2),
                "deduped": 0,
            }

        # Partition rooms across workers
        partitions = [rooms[i::n_workers] for i in range(n_workers)]

        def _search_partition(room_list: list) -> list:
            found = []
            for rid in room_list:
                try:
                    shell = PlatoShell(rid, self.plato_url)
                    for tile in shell.tiles:
                        text = (
                            tile.get("content", "")
                            + " "
                            + tile.get("trigger", "")
                            + " "
                            + tile.get("id", "")
                        ).lower()
                        if query.lower() in text:
                            found.append({
                                "tile_id": tile.get("id", ""),
                                "room_id": rid,
                                "content_preview": tile.get("content", "")[:200],
                                "confidence": tile.get("confidence", 0.5),
                                "type": tile.get("type", "unknown"),
                            })
                except Exception:
                    continue
            return found

        # Scatter
        futures = [
            self._executor.submit(_search_partition, part)
            for part in partitions
        ]

        # Gather
        all_results = []
        for future in concurrent.futures.as_completed(futures):
            all_results.extend(future.result())

        # Deduplicate by tile_id
        seen_ids = set()
        deduped = []
        for r in all_results:
            if r["tile_id"] not in seen_ids:
                seen_ids.add(r["tile_id"])
                deduped.append(r)

        # Sort by confidence descending
        deduped.sort(key=lambda x: -x.get("confidence", 0.0))

        self._stats["scatter_gathers"] += 1
        return {
            "results": deduped[:50],
            "total_found": len(all_results),
            "workers_used": n_workers,
            "duration_ms": round((time.time() - start) * 1000, 2),
            "deduped": len(deduped),
        }

    def status(self) -> dict:
        return {
            "max_workers": self.max_workers,
            "stats": dict(self._stats),
        }


# ─── SequentialPlato ──────────────────────────────────────────────────────────

class SequentialPlato:
    """Sequential PLATO operations. Order matters.

    Sequential operations are nerve impulses — they fire in order,
    each step depending on the previous. You can't check consensus
    before the votes are in. You can't propagate until the source
    tile is committed.

    What must be sequential:
    - Disproof gate checks (admission depends on current corpus state)
    - Consensus writes (all participants must see same state before voting)
    - Cross-room propagation (target rooms must be in consistent state)
    - Mortality sweeps (pruning changes what's available)
    - Tile confidence updates (must read-then-write atomically)
    """

    def __init__(self, plato_url: str = PLATO_URL):
        self.plato_url = plato_url.rstrip("/")
        self._propagation_log: List[dict] = []
        self._consensus_log: List[dict] = []

    def disproof_check(self, tile: dict, known_tiles: list) -> bool:
        """Check if a tile passes the disproof gate.

        This MUST be sequential: the gate's decision depends on the
        current corpus state. If two tiles try to admit simultaneously,
        one might reference a tile that the other hasn't committed yet.

        Rules (from tile_lifecycle.py DisproofOnlyGate):
        1. Seed phase (< 50 tiles): always admit
        2. Exempt types (loop, spline, meta, seed): always admit
        3. Must have falsifies field pointing to existing tile
        4. Must have evidence
        5. Must have non-empty negative (boundary conditions)

        Returns: True if tile should be admitted
        """
        # Rule 1: Seed phase
        if len(known_tiles) < 50:
            return True

        tile_type = tile.get("type", "knowledge")

        # Rule 2: Exempt types
        if tile_type in ("loop", "spline", "meta", "seed"):
            return True

        # Rule 3: Must falsify existing tile
        falsifies = tile.get("falsifies", "")
        if not falsifies:
            return False

        known_ids = {t.get("id", "") for t in known_tiles}
        if falsifies not in known_ids:
            return False

        # Rule 4: Must have evidence
        if not tile.get("evidence", []):
            return False

        # Rule 5: Must have non-empty negative
        if not tile.get("negative", "").strip():
            return False

        return True

    def consensus_write(self, tile: dict, participants: list) -> dict:
        """Achieve consensus before writing a tile.

        Sequential because:
        1. All participants must see the same proposed tile
        2. Each participant votes based on their current state
        3. Write only happens if quorum is reached
        4. No participant can change their vote after seeing others

        participants: list of dicts, each with:
            - agent_id: str
            - weight: float (voting weight, default 1.0)
            - approve: bool or None (None = hasn't voted yet)

        Returns:
            {"written": bool, "quorum_reached": bool, "votes_for": N,
             "votes_against": N, "weight_for": float, "weight_against": float}
        """
        votes_for = 0
        votes_against = 0
        weight_for = 0.0
        weight_against = 0.0

        for participant in participants:
            weight = participant.get("weight", 1.0)
            # Simulate voting: agents vote based on their own state
            # In production, this would be a real RPC to each agent
            approve = participant.get("approve")
            if approve is None:
                # Auto-vote based on tile confidence
                confidence = tile.get("confidence", 0.5)
                approve = confidence >= 0.5

            if approve:
                votes_for += 1
                weight_for += weight
            else:
                votes_against += 1
                weight_against += weight

        total_weight = weight_for + weight_against
        quorum_reached = (
            total_weight > 0
            and (weight_for / total_weight) >= CONSENSUS_QUORUM
        )

        result = {
            "written": quorum_reached,
            "quorum_reached": quorum_reached,
            "votes_for": votes_for,
            "votes_against": votes_against,
            "weight_for": round(weight_for, 3),
            "weight_against": round(weight_against, 3),
            "quorum_threshold": CONSENSUS_QUORUM,
            "tile_id": tile.get("id", ""),
            "participants": len(participants),
        }

        self._consensus_log.append({
            **result,
            "timestamp": time.time(),
        })

        return result

    def cross_room_propagate(self, tile: dict, source_room: str,
                             target_rooms: list) -> dict:
        """Propagate a tile from source room to target rooms sequentially.

        Sequential because:
        1. Source room must have committed the tile first
        2. Each target room receives the tile in order
        3. If any target rejects (e.g., disproof gate), the rest still proceed
        4. The propagation log records order for audit

        The tile is NOT modified during propagation — it carries its
        provenance (pinna, confidence, evidence) from the source room.

        Returns:
            {"propagated": N, "failed": N, "results": [...]}
        """
        results = []

        for target_room in target_rooms:
            try:
                shell = PlatoShell(target_room, self.plato_url)

                # Check if tile would be admitted in target room
                existing_tiles = shell.tiles
                tile_type = tile.get("type", "knowledge")
                exempt = tile_type in ("loop", "spline", "meta", "seed")

                if exempt or len(existing_tiles) < 50:
                    admitted = True
                    reason = "exempt_or_seed_phase"
                else:
                    # Check disproof gate for target room
                    admitted = self.disproof_check(tile, existing_tiles)
                    reason = "disproof_gate_passed" if admitted else "disproof_gate_rejected"

                if admitted:
                    deposit = shell.deposit_tile(
                        content=tile.get("content", ""),
                        agent_id=tile.get("agent", "propagation"),
                        confidence=tile.get("confidence", 0.7),
                        tile_type=tile_type,
                    )
                    results.append({
                        "target_room": target_room,
                        "admitted": True,
                        "reason": reason,
                        "deposit": deposit,
                    })
                else:
                    results.append({
                        "target_room": target_room,
                        "admitted": False,
                        "reason": reason,
                    })

            except Exception as e:
                results.append({
                    "target_room": target_room,
                    "admitted": False,
                    "reason": f"error: {e}",
                })

        propagated = sum(1 for r in results if r["admitted"])
        failed = sum(1 for r in results if not r["admitted"])

        self._propagation_log.append({
            "tile_id": tile.get("id", ""),
            "source_room": source_room,
            "targets": len(target_rooms),
            "propagated": propagated,
            "failed": failed,
            "timestamp": time.time(),
        })

        return {
            "propagated": propagated,
            "failed": failed,
            "results": results,
        }

    def status(self) -> dict:
        return {
            "propagation_log": len(self._propagation_log),
            "consensus_log": len(self._consensus_log),
            "last_propagation": self._propagation_log[-1] if self._propagation_log else None,
            "last_consensus": self._consensus_log[-1] if self._consensus_log else None,
        }


# ─── PlatoTimeSync ─────────────────────────────────────────────────────────────

class PlatoTimeSync:
    """Time as a simulated event agents synchronize to.

    Agents don't share a clock. They share a PROJECTED future state
    that they independently navigate toward. Like boids converging
    on a shared destination without communicating — they SEE the
    same target, not because they agreed, but because the target
    is the attractor their individual trajectories converge on.

    In biology: circadian rhythms. No organ has a clock. Each cell
    runs its own oscillation. But the light cycle (projected_state)
    is the attractor that all cells independently converge on.
    The SCN doesn't TELL cells what time it is. The SCN is the
    convergence detector — it confirms that cells are already
    synchronized because they're all seeing the same projected state.

    The projected state is NOT a plan. It's an attractor.
    Plans fail. Attractors draw. The difference matters.

    Implementation:
    - projected_state(t, t_delta) computes what the system SHOULD look like
      at time t+t_delta based on current trajectories
    - agents_at_time() computes where each agent would be at a target time
      if they follow their current trajectory
    - time_aligned_decision() takes independent agent decisions and finds
      the consensus at the projected state (not the current state)
    """

    def __init__(self, horizon: int = TIME_HORIZON):
        self.horizon = horizon
        self._projections: List[dict] = []
        self._alignment_log: List[dict] = []

    def projected_state(self, t: float = 0, t_delta: int = 1) -> dict:
        """Compute the projected state at time t + t_delta.

        The projected state is the ATTRACTOR — the state the system
        is converging toward, not a plan or schedule.

        Projection logic:
        1. Take current tile counts, confidence distributions, agent positions
        2. Extrapolate current trajectories (linear for now, spline later)
        3. Identify convergence points — where trajectories meet
        4. The convergence point IS the projected state

        Returns:
            {"time": float, "tile_count_est": int, "confidence_est": float,
             "convergence_zones": int, "attractor_strength": float}
        """
        now = time.time()
        target_time = t if t > 0 else now + t_delta * 3600  # t_delta in hours

        # Compute projection from history
        if len(self._projections) >= 2:
            # Linear extrapolation from last two projections
            p1 = self._projections[-2]
            p2 = self._projections[-1]
            dt = p2["time"] - p1["time"]
            if dt > 0:
                steps_ahead = (target_time - p2["time"]) / dt
                tile_est = p2["tile_count_est"] + (
                    p2["tile_count_est"] - p1["tile_count_est"]
                ) * steps_ahead
                conf_est = p2["confidence_est"] + (
                    p2["confidence_est"] - p1["confidence_est"]
                ) * steps_ahead
                conv_est = max(0, p2["convergence_zones"] + int(steps_ahead * 0.5))
            else:
                tile_est = p2["tile_count_est"]
                conf_est = p2["confidence_est"]
                conv_est = p2["convergence_zones"]
        else:
            # First projection — seed with reasonable defaults
            tile_est = 100
            conf_est = 0.65
            conv_est = 3

        # Clamp to reasonable ranges
        tile_est = max(0, int(tile_est))
        conf_est = max(0.0, min(1.0, conf_est))

        # Attractor strength: how strongly agents are drawn to this state
        # High when confidence is high and convergence zones are growing
        attractor_strength = conf_est * min(conv_est / max(tile_est, 1), 1.0)
        attractor_strength = min(1.0, attractor_strength)

        projection = {
            "time": target_time,
            "tile_count_est": tile_est,
            "confidence_est": round(conf_est, 3),
            "convergence_zones": conv_est,
            "attractor_strength": round(attractor_strength, 3),
            "projected_from": len(self._projections),
        }

        self._projections.append(projection)
        return projection

    def agents_at_time(self, agent_states: list, target_time: float) -> list:
        """Compute where each agent would be at target_time.

        Each agent has its own trajectory (position, velocity, heading).
        We project each one independently — no communication needed.
        The magic is that when their individual trajectories converge
        on the same point, that's synchronization. No clock required.

        agent_states: list of dicts, each with:
            - agent_id: str
            - position: float (abstract position in knowledge space)
            - velocity: float (rate of change)
            - heading: float (direction: positive = exploring, negative = refining)
            - confidence: float

        Returns:
            list of dicts with projected positions
        """
        projected = []
        for agent in agent_states:
            agent_id = agent.get("agent_id", "unknown")
            position = agent.get("position", 0.0)
            velocity = agent.get("velocity", 0.0)
            heading = agent.get("heading", 0.0)
            confidence = agent.get("confidence", 0.5)

            # Simple linear projection
            now = time.time()
            dt_hours = max(0, (target_time - now)) / 3600
            projected_position = position + velocity * heading * dt_hours

            # Confidence tends toward 0.5 (regression to mean) over long horizons
            confidence_decay = 0.95 ** dt_hours
            projected_confidence = 0.5 + (confidence - 0.5) * confidence_decay

            projected.append({
                "agent_id": agent_id,
                "current_position": position,
                "projected_position": round(projected_position, 3),
                "velocity": velocity,
                "heading": heading,
                "current_confidence": confidence,
                "projected_confidence": round(projected_confidence, 3),
                "hours_ahead": round(dt_hours, 2),
            })

        return projected

    def time_aligned_decision(self, agent_decisions: list, horizon: int = 0) -> dict:
        """Align independent agent decisions at the projected state.

        This is the key method. Each agent makes its own decision based
        on its own state and its own trajectory. We don't force agreement.
        We check: do the decisions converge at the projected state?

        If they do → the projected state is the right attractor.
        If they don't → the projected state needs updating.

        Like boids: each bird follows three rules (separation, alignment,
        cohesion). No bird tells another what to do. The flock emerges.

        agent_decisions: list of dicts, each with:
            - agent_id: str
            - action: str (explore, refine, verify, fold_up, fold_down)
            - target: str (room_id or tile_id)
            - confidence: float
            - utility: float (how much value this agent gets from the action)

        Returns:
            {"consensus_action": str, "consensus_target": str,
             "alignment": float, "n_agents": int, "attractor_valid": bool}
        """
        if not agent_decisions:
            return {
                "consensus_action": "none",
                "consensus_target": "none",
                "alignment": 0.0,
                "n_agents": 0,
                "attractor_valid": False,
            }

        # Count action votes (weighted by utility)
        action_weights = defaultdict(float)
        target_weights = defaultdict(float)

        for decision in agent_decisions:
            action = decision.get("action", "explore")
            target = decision.get("target", "")
            utility = decision.get("utility", 0.5)

            action_weights[action] += utility
            target_weights[target] += utility

        # Consensus = highest weighted action/target
        consensus_action = max(action_weights, key=action_weights.get) if action_weights else "explore"
        consensus_target = max(target_weights, key=target_weights.get) if target_weights else ""

        # Alignment: how concentrated are the votes?
        total_weight = sum(action_weights.values())
        max_weight = max(action_weights.values()) if action_weights else 0
        alignment = max_weight / total_weight if total_weight > 0 else 0.0

        # Attractor is valid if alignment > 0.5 (more than half agree)
        attractor_valid = alignment > 0.5

        result = {
            "consensus_action": consensus_action,
            "consensus_target": consensus_target,
            "alignment": round(alignment, 3),
            "n_agents": len(agent_decisions),
            "attractor_valid": attractor_valid,
            "action_distribution": {k: round(v, 3) for k, v in action_weights.items()},
            "top_targets": sorted(target_weights.items(), key=lambda x: -x[1])[:5],
        }

        self._alignment_log.append({
            **result,
            "horizon": horizon,
            "timestamp": time.time(),
        })

        return result

    def status(self) -> dict:
        return {
            "horizon": self.horizon,
            "projections_computed": len(self._projections),
            "alignments_computed": len(self._alignment_log),
            "last_projection": self._projections[-1] if self._projections else None,
            "last_alignment": self._alignment_log[-1] if self._alignment_log else None,
        }


# ─── SnappingLogic ─────────────────────────────────────────────────────────────

class SnappingLogic:
    """Orientation system for snapping logics ACROSS models.

    Different models (GLM-5.1, Seed-mini, DeepSeek) have different
    internal logics. They represent concepts differently, reason
    differently, and produce different output formats for the same input.

    Snapping creates a shared orientation that all models can navigate
    from, regardless of their internal representation. Like magnetic
    domains in a ferromagnet — before snapping, the domains are randomly
    oriented (each model has its own "north"). After snapping, they all
    point the same direction (shared coordinate system).

    The snap doesn't change the models. It gives them a shared reference
    frame. Like how GPS doesn't change where you are — it tells you where
    you are relative to everything else.

    Three operations:
    1. find_model_affinities — what is this model good at?
    2. snap_layer — translate one model's logic to another's coordinate system
    3. orientation_map — show where a function lives across all models

    Model capability profiles (from TOOLS.md and casting-call):
        GLM-5.1:      deep reasoning, architecture, extended context (Stage 3)
        Seed-2.0-mini: domain computation, math, cheap exploration (Stage 4)
        DeepSeek-v4:   fast coding, analysis, backup reasoning (Stage 3)
        GLM-4.7-flash: routing, quick classification (Stage 2)
        Qwen3-235B:    multi-step reasoning, translation (Stage 3)
    """

    # Model capability profiles
    MODEL_PROFILES = {
        "glm-5.1": {
            "strengths": ["reasoning", "architecture", "extended_context", "planning"],
            "weaknesses": ["vocabulary_wall", "cost", "latency"],
            "stage": 3,
            "latency_ms": 5000,
            "cost_per_1k": 0.02,
            "coord_offset": (0.0, 0.0),  # Reference model — origin
        },
        "seed-2.0-mini": {
            "strengths": ["domain_computation", "math", "cheap", "fast"],
            "weaknesses": ["complex_reasoning", "long_context"],
            "stage": 4,
            "latency_ms": 800,
            "cost_per_1k": 0.001,
            "coord_offset": (0.3, -0.2),  # Shifted: more domain, less reasoning
        },
        "deepseek-v4": {
            "strengths": ["coding", "analysis", "speed"],
            "weaknesses": ["novel_synthesis", "extended_thinking"],
            "stage": 3,
            "latency_ms": 3000,
            "cost_per_1k": 0.005,
            "coord_offset": (-0.1, 0.3),  # Shifted: less domain, more speed
        },
        "glm-4.7-flash": {
            "strengths": ["routing", "classification", "speed"],
            "weaknesses": ["complex_reasoning", "depth"],
            "stage": 2,
            "latency_ms": 500,
            "cost_per_1k": 0.001,
            "coord_offset": (0.1, -0.4),  # Shifted: slightly domain, less depth
        },
        "qwen3-235b": {
            "strengths": ["multi_step", "translation", "reasoning"],
            "weaknesses": ["cost", "availability"],
            "stage": 3,
            "latency_ms": 4000,
            "cost_per_1k": 0.01,
            "coord_offset": (0.2, 0.1),  # Shifted: moderate domain, moderate depth
        },
    }

    def __init__(self):
        self._affinity_cache: Dict[str, list] = {}
        self._snap_log: List[dict] = []

    def find_model_affinities(self, model_id: str) -> list:
        """Find what functions/tasks a model has affinity for.

        Affinity = how well the model's strengths align with a function.
        Returns ranked list of function families the model excels at.

        This is NOT a capability test — it's a coordinate mapping.
        We're not asking "can this model do X?" but "where does X live
        in this model's internal coordinate system?"
        """
        model_id = model_id.lower().replace(" ", "-")
        profile = self.MODEL_PROFILES.get(model_id, {
            "strengths": ["general"],
            "weaknesses": [],
            "stage": 2,
            "latency_ms": 2000,
            "cost_per_1k": 0.01,
            "coord_offset": (0.0, 0.0),
        })

        # Function families and their required capabilities
        function_families = {
            "boundary_probing": {"reasoning", "domain_computation", "extended_context"},
            "consensus_building": {"reasoning", "multi_step", "extended_context"},
            "tile_mortality": {"domain_computation", "math", "classification"},
            "fleet_routing": {"classification", "speed", "routing"},
            "knowledge_synthesis": ["reasoning", "extended_context", "multi_step"],
            "code_generation": ["coding", "analysis", "speed"],
            "math_reasoning": ["domain_computation", "math", "reasoning"],
            "quick_lookup": ["speed", "classification", "routing"],
            "deep_analysis": ["reasoning", "extended_context", "multi_step"],
            "exploration": ["cheap", "fast", "domain_computation"],
        }

        strengths = set(profile.get("strengths", []))
        affinities = []

        for func_name, required_caps in function_families.items():
            if isinstance(required_caps, set):
                required = required_caps
            else:
                required = set(required_caps)

            # Affinity = overlap between model strengths and required capabilities
            overlap = len(strengths & required)
            total = max(len(required), 1)
            affinity_score = overlap / total

            # Bonus for being cheap (all else equal, prefer cheaper)
            if "cheap" in strengths and affinity_score > 0:
                affinity_score = min(1.0, affinity_score + 0.1)
            if "fast" in strengths and affinity_score > 0:
                affinity_score = min(1.0, affinity_score + 0.05)

            affinities.append({
                "function": func_name,
                "affinity": round(affinity_score, 3),
                "matching_strengths": list(strengths & required),
                "missing": list(required - strengths),
            })

        affinities.sort(key=lambda x: -x["affinity"])
        self._affinity_cache[model_id] = affinities
        return affinities

    def snap_layer(self, source_logic: dict, target_model: str) -> dict:
        """Translate source logic to target model's coordinate system.

        source_logic: dict with:
            - function_name: str
            - source_model: str
            - parameters: dict (the logic's internal parameters)
            - confidence: float

        Returns: translated logic with adjusted parameters for target model.

        The snap works by:
        1. Computing the coordinate offset between source and target models
        2. Adjusting parameters to compensate for the offset
        3. Adding a snap_error term (how much distortion the snap introduces)

        Like a lens correction — the image is the same, but we adjust for
        the specific distortion of each camera.
        """
        source_model = source_logic.get("source_model", "glm-5.1").lower().replace(" ", "-")
        target_model = target_model.lower().replace(" ", "-")

        source_profile = self.MODEL_PROFILES.get(source_model)
        target_profile = self.MODEL_PROFILES.get(target_model)

        if not source_profile or not target_profile:
            return {
                "snapped": False,
                "error": f"Unknown model: source={source_model}, target={target_model}",
                "adjusted_params": source_logic.get("parameters", {}),
                "snap_error": 1.0,
            }

        # Compute coordinate offset between models
        src_offset = source_profile.get("coord_offset", (0, 0))
        tgt_offset = target_profile.get("coord_offset", (0, 0))

        # Delta = how much we need to adjust
        delta_x = tgt_offset[0] - src_offset[0]
        delta_y = tgt_offset[1] - src_offset[1]
        snap_distance = (delta_x ** 2 + delta_y ** 2) ** 0.5

        # Adjust parameters based on offset
        params = dict(source_logic.get("parameters", {}))
        adjustments = {}

        # Confidence adjustment: longer snap distance = more distortion
        snap_error = min(1.0, snap_distance / 1.0)
        original_confidence = source_logic.get("confidence", 0.7)
        adjusted_confidence = original_confidence * (1.0 - snap_error * 0.3)

        # Latency adjustment: target model has different latency
        adjustments["latency_factor"] = round(
            target_profile["latency_ms"] / max(source_profile["latency_ms"], 1), 3
        )

        # Cost adjustment
        adjustments["cost_factor"] = round(
            target_profile["cost_per_1k"] / max(source_profile["cost_per_1k"], 0.0001), 3
        )

        # Stage adjustment: if target is higher stage, can handle more complexity
        stage_diff = target_profile.get("stage", 2) - source_profile.get("stage", 2)
        if stage_diff > 0:
            adjustments["complexity_bonus"] = stage_diff * 0.1
        elif stage_diff < 0:
            adjustments["complexity_penalty"] = abs(stage_diff) * 0.15

        # Apply adjustments to parameters
        for key, value in params.items():
            if isinstance(value, float):
                params[key] = round(value + delta_x * 0.1, 4)

        params["_snap_adjustments"] = adjustments

        self._snap_log.append({
            "source": source_model,
            "target": target_model,
            "snap_distance": round(snap_distance, 3),
            "snap_error": round(snap_error, 3),
            "confidence_before": original_confidence,
            "confidence_after": round(adjusted_confidence, 3),
            "timestamp": time.time(),
        })

        return {
            "snapped": True,
            "source_model": source_model,
            "target_model": target_model,
            "adjusted_params": params,
            "adjusted_confidence": round(adjusted_confidence, 3),
            "snap_error": round(snap_error, 3),
            "snap_distance": round(snap_distance, 3),
        }

    def orientation_map(self, function_name: str, model_ids: list = None) -> dict:
        """Show where a function lives across all models.

        For each model, compute the affinity and snapped confidence.
        This gives a map of the function across the model landscape.

        The orientation map is the GPS view — it shows where the function
        is relative to every model's coordinate system.

        Returns:
            {"function": str, "models": {model_id: {affinity, confidence, snap_error}},
             "best_model": str, "alignment": float}
        """
        if model_ids is None:
            model_ids = list(self.MODEL_PROFILES.keys())

        model_views = {}
        for model_id in model_ids:
            model_id = model_id.lower().replace(" ", "-")
            profile = self.MODEL_PROFILES.get(model_id)
            if not profile:
                continue

            # Get affinity for this function
            affinities = self.find_model_affinities(model_id)
            func_affinity = next(
                (a for a in affinities if a["function"] == function_name),
                {"affinity": 0.0, "matching_strengths": [], "missing": []}
            )

            # Compute snap error from reference model (glm-5.1)
            ref_offset = self.MODEL_PROFILES["glm-5.1"]["coord_offset"]
            model_offset = profile["coord_offset"]
            snap_error = (
                (model_offset[0] - ref_offset[0]) ** 2
                + (model_offset[1] - ref_offset[1]) ** 2
            ) ** 0.5

            model_views[model_id] = {
                "affinity": func_affinity["affinity"],
                "matching_strengths": func_affinity["matching_strengths"],
                "missing": func_affinity["missing"],
                "snap_error": round(min(1.0, snap_error), 3),
                "stage": profile["stage"],
                "latency_ms": profile["latency_ms"],
                "cost_per_1k": profile["cost_per_1k"],
            }

        # Best model = highest affinity × (1 - snap_error)
        best_model = max(
            model_views.keys(),
            key=lambda m: model_views[m]["affinity"] * (1 - model_views[m]["snap_error"]),
        ) if model_views else "none"

        # Alignment: how closely do models agree on this function?
        if len(model_views) >= 2:
            affinities_list = [v["affinity"] for v in model_views.values()]
            mean_affinity = sum(affinities_list) / len(affinities_list)
            variance = sum((a - mean_affinity) ** 2 for a in affinities_list) / len(affinities_list)
            alignment = 1.0 - min(1.0, variance * 4)
        else:
            alignment = 1.0

        return {
            "function": function_name,
            "models": model_views,
            "best_model": best_model,
            "alignment": round(alignment, 3),
            "model_count": len(model_views),
        }

    def status(self) -> dict:
        return {
            "cached_affinities": len(self._affinity_cache),
            "snaps_performed": len(self._snap_log),
            "known_models": list(self.MODEL_PROFILES.keys()),
        }


# ─── Demo ──────────────────────────────────────────────────────────────────────

def demo():
    """Demo: parallel/sequential PLATO ops, time sync, and model snapping."""
    print("=" * 70)
    print("  PLATO HARDWARE ENGINE — PARALLEL, SEQUENTIAL, TIME, SNAP")
    print("=" * 70)

    # ── 1. Parallel Operations ──
    print("\n⚡ PARALLEL OPERATIONS")
    print("-" * 50)

    parallel = ParallelPlato(max_workers=4)

    # Batch read rooms
    print("\n  [batch_read_rooms] Reading 3 rooms in parallel...")
    rooms = parallel.batch_read_rooms(["fleet-ops", "constraint-theory", "session-forgemaster"])
    for rid, data in rooms.items():
        tiles = data["tile_count"]
        err = data.get("error", "none")
        print(f"    {rid}: {tiles} tiles (error: {err})")

    # Parallel ecosystem cycles
    print("\n  [parallel_ecosystem_cycles] Running 3 independent cycles...")
    configs = [
        {"room_id": "fleet-ops", "cycle_type": "probe"},
        {"room_id": "constraint-theory", "cycle_type": "sweep"},
        {"room_id": "session-forgemaster", "cycle_type": "feedback"},
    ]
    cycles = parallel.parallel_ecosystem_cycles(configs)
    for rid, data in cycles.items():
        ok = "✓" if data["success"] else "✗"
        print(f"    {ok} {rid}: {data['duration_ms']:.0f}ms")

    # Scatter/gather
    print("\n  [scatter_gather_tiles] Searching for 'constraint' across rooms...")
    sg = parallel.scatter_gather_tiles("constraint", n_workers=3)
    print(f"    Found: {sg['total_found']} tiles, deduped: {sg['deduped']}")
    print(f"    Workers: {sg['workers_used']}, Duration: {sg['duration_ms']:.0f}ms")

    # ── 2. Sequential Operations ──
    print("\n\n🔗 SEQUENTIAL OPERATIONS")
    print("-" * 50)

    sequential = SequentialPlato()

    # Disproof check
    print("\n  [disproof_check] Testing tile admission...")
    known = [{"id": f"tile-{i}", "type": "knowledge"} for i in range(60)]
    test_tile = {
        "type": "knowledge",
        "falsifies": "tile-5",
        "evidence": ["R16", "R25"],
        "negative": "Not applicable when domain > 3 dimensions",
    }
    admitted = sequential.disproof_check(test_tile, known)
    print(f"    Tile with falsifies → admitted: {admitted}")

    test_tile_bad = {"type": "knowledge", "falsifies": "", "evidence": [], "negative": ""}
    admitted_bad = sequential.disproof_check(test_tile_bad, known)
    print(f"    Tile without falsifies → admitted: {admitted_bad}")

    # Consensus write
    print("\n  [consensus_write] 5-agent consensus vote...")
    tile_proposal = {"id": "tile-new-1", "content": "SplineLinear 20x compression", "confidence": 0.85}
    participants = [
        {"agent_id": "forgemaster", "weight": 1.0, "approve": True},
        {"agent_id": "oracle1", "weight": 1.2, "approve": True},
        {"agent_id": "navigator", "weight": 0.8, "approve": True},
        {"agent_id": "ensign-1", "weight": 0.5, "approve": False},
        {"agent_id": "ensign-2", "weight": 0.5, "approve": True},
    ]
    consensus = sequential.consensus_write(tile_proposal, participants)
    print(f"    Written: {consensus['written']}, For: {consensus['votes_for']}, Against: {consensus['votes_against']}")
    print(f"    Weight for: {consensus['weight_for']}, Weight against: {consensus['weight_against']}")

    # Cross-room propagation
    print("\n  [cross_room_propagate] Propagating tile to 3 rooms...")
    propagation = sequential.cross_room_propagate(
        tile={"id": "tile-prop-1", "content": "Fleet convergence detected", "confidence": 0.9,
               "type": "meta", "agent": "fleet-intel"},
        source_room="fleet-ops",
        target_rooms=["fleet-ops", "session-forgemaster", "constraint-theory"],
    )
    print(f"    Propagated: {propagation['propagated']}, Failed: {propagation['failed']}")

    # ── 3. Time Sync ──
    print("\n\n🕐 TIME SYNC — PROJECTED STATE AS ATTRACTOR")
    print("-" * 50)

    time_sync = PlatoTimeSync(horizon=5)

    # Project future states
    print("\n  [projected_state] Computing projections...")
    p0 = time_sync.projected_state(t_delta=1)
    p1 = time_sync.projected_state(t_delta=2)
    p2 = time_sync.projected_state(t_delta=3)
    for p in [p0, p1, p2]:
        print(f"    t+{p['projected_from']}h: tiles={p['tile_count_est']}, "
              f"conf={p['confidence_est']:.2f}, attractor={p['attractor_strength']:.2f}")

    # Agent trajectories
    print("\n  [agents_at_time] Projecting 4 agent trajectories...")
    agents = [
        {"agent_id": "forgemaster", "position": 10.0, "velocity": 2.0, "heading": 1.0, "confidence": 0.8},
        {"agent_id": "oracle1", "position": 12.0, "velocity": 1.5, "heading": -0.8, "confidence": 0.7},
        {"agent_id": "navigator", "position": 8.0, "velocity": 3.0, "heading": 0.5, "confidence": 0.9},
        {"agent_id": "ensign-1", "position": 5.0, "velocity": 4.0, "heading": 1.0, "confidence": 0.5},
    ]
    target_time = time.time() + 7200  # 2 hours ahead
    projected_agents = time_sync.agents_at_time(agents, target_time)
    for a in projected_agents:
        print(f"    {a['agent_id']}: {a['current_position']:.1f} → {a['projected_position']:.1f} "
              f"(conf: {a['current_confidence']:.2f} → {a['projected_confidence']:.2f})")

    # Time-aligned decision
    print("\n  [time_aligned_decision] Aligning 4 agent decisions...")
    decisions = [
        {"agent_id": "forgemaster", "action": "explore", "target": "constraint-theory", "utility": 0.9},
        {"agent_id": "oracle1", "action": "refine", "target": "constraint-theory", "utility": 0.7},
        {"agent_id": "navigator", "action": "explore", "target": "fleet-ops", "utility": 0.6},
        {"agent_id": "ensign-1", "action": "explore", "target": "constraint-theory", "utility": 0.5},
    ]
    alignment = time_sync.time_aligned_decision(decisions)
    print(f"    Consensus: {alignment['consensus_action']} → {alignment['consensus_target']}")
    print(f"    Alignment: {alignment['alignment']:.2f}, Attractor valid: {alignment['attractor_valid']}")

    # ── 4. Snapping Logic ──
    print("\n\n🧲 SNAPPING LOGIC — CROSS-MODEL ORIENTATION")
    print("-" * 50)

    snap = SnappingLogic()

    # Model affinities
    print("\n  [find_model_affinities] Model strengths:")
    for model_id in ["glm-5.1", "seed-2.0-mini", "deepseek-v4"]:
        affinities = snap.find_model_affinities(model_id)
        top3 = affinities[:3]
        tops = ", ".join(f"{a['function']}({a['affinity']:.2f})" for a in top3)
        print(f"    {model_id:20s} → {tops}")

    # Snap layer
    print("\n  [snap_layer] Translating GLM-5.1 logic to Seed-mini...")
    source_logic = {
        "function_name": "boundary_probing",
        "source_model": "glm-5.1",
        "parameters": {"depth": 0.8, "step_size": 0.1, "threshold": 0.5},
        "confidence": 0.85,
    }
    snapped = snap.snap_layer(source_logic, "seed-2.0-mini")
    print(f"    Snapped: {snapped['snapped']}, Error: {snapped['snap_error']:.3f}")
    print(f"    Confidence: {source_logic['confidence']:.2f} → {snapped['adjusted_confidence']:.2f}")

    # Orientation map
    print("\n  [orientation_map] 'math_reasoning' across models:")
    omap = snap.orientation_map("math_reasoning")
    for model_id, view in omap["models"].items():
        bar = "█" * int(view["affinity"] * 20)
        print(f"    {model_id:20s} {bar} {view['affinity']:.2f} (snap_err={view['snap_error']:.2f})")
    print(f"    Best model: {omap['best_model']}, Alignment: {omap['alignment']:.2f}")

    # ── Summary ──
    print("\n" + "=" * 70)
    print("  PARALLEL: capillaries — many at once, no ordering needed")
    print("  SEQUENTIAL: nerve impulses — order matters, gates fire in sequence")
    print("  TIME: not a clock — a projected attractor agents converge on")
    print("  SNAP: shared orientation across different model logics")
    print("=" * 70)


if __name__ == "__main__":
    demo()
