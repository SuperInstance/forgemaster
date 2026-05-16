#!/usr/bin/env python3
"""core/active_probe.py — The sonar ping for PLATO tiles.

The bat, dolphin, fisherman, submarine all converged on the same thing:
emit a signal, measure what comes back, build a map from reflections.

This module gives PLATO agents the same capability. Instead of passively
recording outcomes that happen to occur, the system ACTIVELY PROBES its
own knowledge to find the edges — the boundaries where confidence drops,
where tiles contradict each other, where the map is thin.

Inside the corn maze: random turns. From above: the structure is obvious.
Active probing is how the system climbs to the vantage point.

The probe cycle:
  1. EMIT — ask a question designed to test a boundary
  2. LISTEN — measure what comes back (echo)
  3. MAP — record the boundary in the terrain model
  4. DESIRE — let hunger drive the next probe direction

Three probe strategies:
  - BoundaryProbe: test the edges of a tile's confidence (where does it break?)
  - ConsistencyProbe: test whether tiles agree (do shadows overlap or contradict?)
  - CoverageProbe: test where the map is thin (where have we never looked?)
"""
from __future__ import annotations

import math
import time
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Callable
from collections import defaultdict


# ─── The Echo — what comes back from a probe ──────────────────────────────────

@dataclass
class Echo:
    """What the sonar returns. The reflection from an active probe.

    Like a sonar ping returning — the shape of the echo tells you
    about the shape of what it bounced off.
    """
    probe_id: str
    probe_type: str          # boundary | consistency | coverage
    target_tile_id: str
    timestamp: float

    # What we learned
    hit: bool                # did the probe hit a boundary?
    boundary_distance: float # how far from known-good before it broke (0=immediate, 1=never broke)
    confidence_at_boundary: float  # tile confidence where the probe failed
    contradicted_by: List[str] = field(default_factory=list)  # tile IDs that contradicted
    shadow_angle: str = ""   # which metaphorical angle this probe tested

    # The terrain update
    new_knowledge: bool = False  # did this probe reveal something unknown?
    gap_found: bool = False      # did this probe find a gap in coverage?


# ─── BoundaryProbe — test where a tile's confidence breaks ────────────────────

class BoundaryProbe:
    """Pings the edges of a tile's claimed territory.

    A tile says "I work for X." The boundary probe asks:
    "What about X+ε? X+2ε? At what point do you stop working?"

    Like a fisherman dropping the sounder in progressively deeper water
    to find where the bottom drops off. The edge of the shelf IS the fish.

    The desire: "I want to know exactly where my knowledge ends."
    """

    def __init__(self, step_size: float = 0.1, max_steps: int = 10):
        self.step_size = step_size
        self.max_steps = max_steps

    def probe(
        self,
        tile_id: str,
        test_fn: Callable[[str, float], Tuple[bool, float]],
    ) -> Echo:
        """Probe a tile's boundary by testing progressively harder conditions.

        Args:
            tile_id: The tile to probe
            test_fn: Function(tile_id, perturbation) -> (succeeded, confidence)
                     Returns whether the tile still works at this perturbation level
        """
        boundary_dist = 1.0
        confidence_at_edge = 0.0
        hit = False

        for step in range(1, self.max_steps + 1):
            perturbation = step * self.step_size
            succeeded, confidence = test_fn(tile_id, perturbation)

            if not succeeded:
                boundary_dist = (step - 1) * self.step_size
                confidence_at_edge = confidence
                hit = True
                break
        else:
            # Never broke — tile is robust across all tested perturbations
            confidence_at_edge = confidence

        return Echo(
            probe_id=f"boundary-{tile_id}-{time.time():.0f}",
            probe_type="boundary",
            target_tile_id=tile_id,
            timestamp=time.time(),
            hit=hit,
            boundary_distance=round(boundary_dist, 4),
            confidence_at_boundary=round(confidence_at_edge, 4),
            new_knowledge=hit,  # finding a boundary IS new knowledge
            gap_found=False,
        )


# ─── ConsistencyProbe — test whether tile shadows overlap or contradict ───────

class ConsistencyProbe:
    """Checks whether tiles describing the same thing from different angles agree.

    The blind person builds sight from overlapping shadows. If the shadows
    DON'T overlap — if two descriptions of the same thing contradict —
    that's a gap in understanding. Either one shadow is wrong, or the thing
    is more complex than either shadow captures.

    The desire: "I want my multiple perspectives to agree. If they don't,
    I want to know WHERE they disagree."
    """

    def __init__(self, agreement_threshold: float = 0.8):
        self.agreement_threshold = agreement_threshold

    def probe(
        self,
        tile_ids: List[str],
        query_fn: Callable[[str], dict],
        compare_fn: Callable[[dict, dict], float],
    ) -> List[Echo]:
        """Compare tiles against each other to find contradictions.

        Args:
            tile_ids: Tiles to compare (should be about the same topic)
            query_fn: Function(tile_id) -> tile_data
            compare_fn: Function(data_a, data_b) -> similarity (0-1)

        Returns one echo per pair that disagrees below threshold.
        """
        echoes = []
        tiles_data = {tid: query_fn(tid) for tid in tile_ids}

        for i, tid_a in enumerate(tile_ids):
            for tid_b in tile_ids[i + 1:]:
                sim = compare_fn(tiles_data[tid_a], tiles_data[tid_b])
                if sim < self.agreement_threshold:
                    echoes.append(Echo(
                        probe_id=f"consistency-{tid_a}-{tid_b}-{time.time():.0f}",
                        probe_type="consistency",
                        target_tile_id=tid_a,
                        timestamp=time.time(),
                        hit=True,
                        boundary_distance=round(sim, 4),
                        confidence_at_boundary=0.0,
                        contradicted_by=[tid_b],
                        new_knowledge=True,
                        gap_found=True,  # contradiction IS a gap
                    ))

        return echoes


# ─── CoverageProbe — find where the map is thin ───────────────────────────────

class CoverageProbe:
    """Finds regions of the knowledge space that have never been probed.

    Like a fisherman looking at the chart and noticing whole areas with
    no sounding curtains drawn. You can't navigate where you haven't mapped.

    The desire: "I want to know where I DON'T know things."
    The gap IS the work. The glitches ARE the research agenda.
    """

    def __init__(self, n_bins: int = 10, thin_threshold: int = 3):
        self.n_bins = n_bins
        self.thin_threshold = thin_threshold

    def probe(
        self,
        tiles_data: List[dict],
        feature_fn: Callable[[dict], Tuple[float, ...]],
        n_dimensions: int = 2,
    ) -> List[Echo]:
        """Find regions of the feature space with insufficient coverage.

        Args:
            tiles_data: List of tile data dicts
            feature_fn: Function(tile_data) -> tuple of feature values
            n_dimensions: How many feature dimensions to bin
        """
        if not tiles_data:
            return []

        # Extract features
        features = [feature_fn(t) for t in tiles_data]

        # Find ranges per dimension
        ranges = []
        for d in range(min(n_dimensions, len(features[0]))):
            vals = [f[d] for f in features if len(f) > d]
            if vals:
                ranges.append((min(vals), max(vals)))
            else:
                ranges.append((0.0, 1.0))

        # Bin the space and count tiles per bin
        bin_counts: Dict[Tuple[int, ...], int] = defaultdict(int)
        for feat in features:
            bin_idx = []
            for d in range(len(ranges)):
                lo, hi = ranges[d]
                span = hi - lo if hi > lo else 1.0
                idx = int((feat[d] - lo) / span * (self.n_bins - 1))
                idx = max(0, min(self.n_bins - 1, idx))
                bin_idx.append(idx)
            bin_counts[tuple(bin_idx)] += 1

        # Find thin regions (below threshold or missing entirely)
        echoes = []
        total_bins = self.n_bins ** len(ranges)
        for bin_idx in range(total_bins):
            # Convert flat index to multi-dim
            idx_tuple = []
            remaining = bin_idx
            for d in range(len(ranges)):
                idx_tuple.append(remaining % self.n_bins)
                remaining //= self.n_bins
            idx_tuple = tuple(reversed(idx_tuple)) if len(ranges) > 1 else (bin_idx,)

            count = bin_counts.get(idx_tuple, 0)
            if count < self.thin_threshold:
                # Compute center of this bin
                center = []
                for d in range(len(ranges)):
                    lo, hi = ranges[d]
                    span = hi - lo if hi > lo else 1.0
                    center.append(lo + (idx_tuple[d] + 0.5) * span / self.n_bins)

                echoes.append(Echo(
                    probe_id=f"coverage-{bin_idx}-{time.time():.0f}",
                    probe_type="coverage",
                    target_tile_id="",
                    timestamp=time.time(),
                    hit=False,
                    boundary_distance=0.0,
                    confidence_at_boundary=0.0,
                    new_knowledge=False,
                    gap_found=True,
                    shadow_angle=f"bin_{idx_tuple}_center_{tuple(round(c, 2) for c in center)}",
                ))

        return echoes


# ─── TerrainMap — the accumulated sonar picture ───────────────────────────────

class TerrainMap:
    """The 3D picture that emerges from enough sounding curtains.

    Each probe is a sounding curtain. Alone, it's a thin slice.
    Together, they resolve into a terrain map of the knowledge space.

    This IS the corn maze seen from above. Each probe draws a line
    on the map. Enough lines, and the structure of the maze becomes
    visible — the paths, the dead ends, the open spaces.
    """

    def __init__(self):
        self.echoes: List[Echo] = []
        self.boundaries: Dict[str, List[float]] = defaultdict(list)
        self.contradictions: List[Tuple[str, str, float]] = []
        self.coverage_gaps: List[str] = []
        self.probe_count: int = 0

    def record(self, echo: Echo) -> None:
        """Record an echo in the terrain map."""
        self.echoes.append(echo)
        self.probe_count += 1

        if echo.probe_type == "boundary":
            self.boundaries[echo.target_tile_id].append(echo.boundary_distance)
        elif echo.probe_type == "consistency":
            for cid in echo.contradicted_by:
                self.contradictions.append((echo.target_tile_id, cid, echo.boundary_distance))
        elif echo.probe_type == "coverage":
            if echo.gap_found:
                self.coverage_gaps.append(echo.shadow_angle)

    def resolve(self) -> dict:
        """Resolve the terrain map into a coherent picture.

        Like enough curtains → 3D bathymetry. This takes the raw echoes
        and produces the view from above — where are the boundaries,
        where are the gaps, where is the knowledge solid.
        """
        # Boundary resolution: average boundary distance per tile
        boundary_map = {}
        for tile_id, distances in self.boundaries.items():
            if distances:
                boundary_map[tile_id] = {
                    "avg_distance": round(sum(distances) / len(distances), 4),
                    "min_distance": round(min(distances), 4),
                    "max_distance": round(max(distances), 4),
                    "probes": len(distances),
                }

        return {
            "total_probes": self.probe_count,
            "boundaries_found": len(boundary_map),
            "contradictions_found": len(self.contradictions),
            "coverage_gaps_found": len(self.coverage_gaps),
            "boundary_map": boundary_map,
            "strongest_tiles": sorted(
                boundary_map.items(),
                key=lambda x: x[1]["avg_distance"],
                reverse=True,
            )[:5],
            "weakest_tiles": sorted(
                boundary_map.items(),
                key=lambda x: x[1]["avg_distance"],
            )[:5],
        }

    def vantage_point(self) -> str:
        """Describe the current view from above.

        This is what the corn maze looks like from the helicopter.
        """
        r = self.resolve()
        lines = [
            f"TERRAIN MAP — {r['total_probes']} probes fired",
            f"Boundaries mapped: {r['boundaries_found']}",
            f"Contradictions: {r['contradictions_found']}",
            f"Coverage gaps: {r['coverage_gaps_found']}",
        ]

        if r["strongest_tiles"]:
            tid, info = r["strongest_tiles"][0]
            lines.append(f"Strongest: {tid} (boundary at {info['avg_distance']:.3f})")

        if r["weakest_tiles"]:
            tid, info = r["weakest_tiles"][0]
            lines.append(f"Weakest: {tid} (boundary at {info['avg_distance']:.3f})")

        if r["coverage_gaps_found"] > 0:
            lines.append(f"→ {r['coverage_gaps_found']} unmapped regions need probes")

        if r["contradictions_found"] > 0:
            lines.append(f"→ {r['contradictions_found']} shadows that don't overlap")

        return "\n".join(lines)


# ─── Desire — what drives the probing ─────────────────────────────────────────

class Desire:
    """The hunger that drives the system to probe.

    Not a parameter schedule. Not a hyperparameter. A FUNCTION that says
    "given what I know and what I don't know, what should I probe next?"

    The bat was hungry in the dark. The dolphin was hungry in the murk.
    The fisherman was hungry under the hull. The desire shapes the probe.

    Three desire modes:
      - EXPLORE: "I don't know what's out there" → coverage probes
      - REFINE: "I know roughly where the boundary is" → boundary probes
      - VERIFY: "My shadows should overlap" → consistency probes
    """

    EXPLORE = "explore"
    REFINE = "refine"
    VERIFY = "verify"

    def __init__(self, explore_weight: float = 0.5, refine_weight: float = 0.3, verify_weight: float = 0.2):
        self.weights = {
            self.EXPLORE: explore_weight,
            self.REFINE: refine_weight,
            self.VERIFY: verify_weight,
        }
        self.history: List[Tuple[str, str, float]] = []  # (mode, result_summary, desire_score)

    def next_probe_mode(self, terrain: TerrainMap) -> str:
        """Decide what kind of probe to fire next, based on desire.

        The desire function: given the current terrain map, which kind
        of ignorance is most urgent to resolve?

        - Many coverage gaps → EXPLORE (map the dark areas)
        - Many boundaries found but imprecise → REFINE (sharpen the edges)
        - Many tiles, few cross-checks → VERIFY (ensure shadows overlap)
        """
        r = terrain.resolve()

        # Compute urgency scores
        coverage_urgency = min(1.0, r["coverage_gaps_found"] / 20) * self.weights[self.EXPLORE]
        boundary_urgency = min(1.0, r["boundaries_found"] / 10) * self.weights[self.REFINE]
        verify_urgency = min(1.0, r["contradictions_found"] / 5) * self.weights[self.VERIFY]

        # If we have very few probes, always explore first
        if r["total_probes"] < 10:
            mode = self.EXPLORE
        else:
            scores = {
                self.EXPLORE: coverage_urgency,
                self.REFINE: boundary_urgency,
                self.VERIFY: verify_urgency,
            }
            mode = max(scores, key=scores.get)

        return mode

    def record(self, mode: str, summary: str, score: float) -> None:
        self.history.append((mode, summary, score))

    def summary(self) -> dict:
        mode_counts = defaultdict(int)
        for mode, _, _ in self.history:
            mode_counts[mode] += 1
        return {
            "total_desires": len(self.history),
            "by_mode": dict(mode_counts),
            "weights": self.weights,
        }


# ─── ActiveSonar — orchestrates probing like the four inventors ───────────────

class ActiveSonar:
    """The complete sonar system: desire → probe → echo → map.

    This is what the bat, dolphin, fisherman, and submarine commander
    all converged on. The system:
      1. Feels desire (what do I not know?)
      2. Emits a probe (active signal, not passive listening)
      3. Records the echo (what came back)
      4. Updates the terrain map (sounding curtain)
      5. Desires again (based on updated map)

    Usage:
        sonar = ActiveSonar()
        sonar.ping_boundary(tile_id, test_fn)
        sonar.ping_consistency(tile_ids, query_fn, compare_fn)
        sonar.ping_coverage(tiles_data, feature_fn)
        print(sonar.vantage())  # view from above
    """

    def __init__(self):
        self.terrain = TerrainMap()
        self.desire = Desire()
        self.boundary_prober = BoundaryProbe()
        self.consistency_prober = ConsistencyProbe()
        self.coverage_prober = CoverageProbe()

    def ping_boundary(
        self,
        tile_id: str,
        test_fn: Callable[[str, float], Tuple[bool, float]],
    ) -> Echo:
        """Ping a tile's boundary. The sonar goes out, the echo comes back."""
        echo = self.boundary_prober.probe(tile_id, test_fn)
        self.terrain.record(echo)
        self.desire.record(
            Desire.REFINE,
            f"boundary of {tile_id}: {'hit' if echo.hit else 'robust'}",
            echo.boundary_distance,
        )
        return echo

    def ping_consistency(
        self,
        tile_ids: List[str],
        query_fn: Callable[[str], dict],
        compare_fn: Callable[[dict, dict], float],
    ) -> List[Echo]:
        """Ping for shadow overlap. Do these tiles agree?"""
        echoes = self.consistency_prober.probe(tile_ids, query_fn, compare_fn)
        for echo in echoes:
            self.terrain.record(echo)
            self.desire.record(
                Desire.VERIFY,
                f"contradiction: {echo.target_tile_id} vs {echo.contradicted_by}",
                echo.boundary_distance,
            )
        return echoes

    def ping_coverage(
        self,
        tiles_data: List[dict],
        feature_fn: Callable[[dict], Tuple[float, ...]],
        n_dimensions: int = 2,
    ) -> List[Echo]:
        """Ping for coverage gaps. Where haven't we looked?"""
        echoes = self.coverage_prober.probe(tiles_data, feature_fn, n_dimensions)
        for echo in echoes:
            self.terrain.record(echo)
            self.desire.record(
                Desire.EXPLORE,
                f"gap: {echo.shadow_angle}",
                0.0,  # gaps have no distance metric
            )
        return echoes

    def next_desire(self) -> str:
        """What should we probe next? Let desire decide."""
        return self.desire.next_probe_mode(self.terrain)

    def vantage(self) -> str:
        """See the corn maze from above."""
        return self.terrain.vantage_point()

    def status(self) -> dict:
        return {
            "terrain": self.terrain.resolve(),
            "desire": self.desire.summary(),
        }


# ─── Demo ─────────────────────────────────────────────────────────────────────

def demo():
    """Demonstrate active probing — the sonar for knowledge."""
    print("ACTIVE SONAR — Probing Knowledge Like a Bat in the Dark")
    print("=" * 60)

    sonar = ActiveSonar()

    # Simulate tiles with confidence boundaries
    print("\n1. BOUNDARY PROBES — Where does knowledge break?")
    tile_confidences = {
        "tile-drift-detect": 0.95,
        "tile-anomaly-flag": 0.85,
        "tile-intent-detect": 0.90,
        "tile-weak": 0.40,
    }

    def test_boundary(tile_id: str, perturbation: float) -> Tuple[bool, float]:
        base = tile_confidences.get(tile_id, 0.5)
        effective = base - perturbation
        return effective > 0.5, max(0, effective)

    for tid in tile_confidences:
        echo = sonar.ping_boundary(tid, test_boundary)
        status = f"boundary at {echo.boundary_distance:.2f}" if echo.hit else "robust"
        print(f"   {tid}: {status}")

    # Consistency probes
    print("\n2. CONSISTENCY PROBES — Do shadows overlap?")

    def query_tile(tid: str) -> dict:
        return {"id": tid, "confidence": tile_confidences.get(tid, 0.5)}

    def compare_tiles(a: dict, b: dict) -> float:
        return 1.0 - abs(a["confidence"] - b["confidence"])

    echoes = sonar.ping_consistency(
        list(tile_confidences.keys()), query_tile, compare_tiles
    )
    for echo in echoes:
        print(f"   Gap: {echo.target_tile_id} vs {echo.contradicted_by} (sim={echo.boundary_distance:.3f})")

    # Coverage probes
    print("\n3. COVERAGE PROBES — Where haven't we looked?")
    tiles_data = [
        {"id": f"t-{i}", "x": random.random(), "y": random.random()}
        for i in range(15)
    ]
    coverage_echoes = sonar.ping_coverage(
        tiles_data,
        feature_fn=lambda t: (t["x"], t["y"]),
        n_dimensions=2,
    )
    print(f"   Found {len(coverage_echoes)} coverage gaps in 2D space")

    # Vantage point
    print(f"\n4. VANTAGE POINT — The corn maze from above")
    print(sonar.vantage())

    # Next desire
    print(f"\n5. NEXT DESIRE — What to probe next?")
    mode = sonar.next_desire()
    print(f"   → {mode.upper()}")
    desire_summary = sonar.desire.summary()
    print(f"   History: {desire_summary['by_mode']}")

    print("\n" + "=" * 60)
    print("The bat was hungry in the dark. Now it can see the maze from above.")


if __name__ == "__main__":
    demo()
