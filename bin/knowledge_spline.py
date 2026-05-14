"""
knowledge_spline.py — The decomposition engine as a B-spline over truth.

Every successful verification is an ON-curve anchor point.
Every failure is an OFF-curve control point.
The spline interpolates through what we know and bends around what we don't.

The maturation of the shell IS the spline gaining resolution:
  More anchors → tighter spline → less interpolation → more certain

The failures aren't waste. They're the handles that shape the curve.
Without off-curve points, the spline is just a straight line through
a few scattered truths — no shape, no understanding of the boundary.

Casey's insight: the spline is the knowledge. The batton IS the instrument.
"""

import math
import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ─── The Knowledge Spline ─────────────────────────────────────────

@dataclass
class Anchor:
    """A verification result on the knowledge spline."""
    point: Tuple[float, ...]        # Coordinates in conjecture space
    result: bool                    # True = on-curve (verified), False = off-curve (failure)
    conjecture: str                 # What was tested
    verifier: str                   # Which verifier ran
    delta: float = 0.0             # Distance from boundary (0 = edge case)
    timestamp: float = 0.0
    flux_program: Optional[str] = None  # Compiled FLUX bytecode name if autonomous


class KnowledgeSpline:
    """
    A B-spline over verification results.
    
    On-curve anchors (successes): the spline passes through these.
    Off-curve anchors (failures): control points that shape the boundary.
    
    The spline's curvature IS the system's understanding of where
    the safe region ends and the unknown begins.
    """
    
    def __init__(self):
        self.on_curve: List[Anchor] = []     # Verified truths
        self.off_curve: List[Anchor] = []    # Known failures / boundary cases
        self.flux_programs: List[str] = []   # Compiled autonomous capabilities
        self.api_calls_total: int = 0
        self.api_calls_by_phase: dict = {}   # Track maturation
    
    def add_success(self, point, conjecture, verifier, delta, flux_program=None):
        """Add an on-curve anchor — a verified truth the spline passes through."""
        anchor = Anchor(
            point=point, result=True, conjecture=conjecture,
            verifier=verifier, delta=delta, flux_program=flux_program
        )
        self.on_curve.append(anchor)
        if flux_program:
            self.flux_programs.append(flux_program)
    
    def add_failure(self, point, conjecture, verifier, delta):
        """Add an off-curve control point — a failure that shapes the boundary."""
        anchor = Anchor(
            point=point, result=False, conjecture=conjecture,
            verifier=verifier, delta=delta
        )
        self.off_curve.append(anchor)
    
    def curvature_at(self, point: Tuple[float, ...]) -> float:
        """
        How curvy is the spline near this point?
        High curvature = near the boundary of knowledge.
        Low curvature = deep in verified territory.
        """
        if not self.on_curve:
            return float('inf')  # Unknown territory
        
        # Find nearest on-curve and off-curve anchors
        min_on = min(self._dist(point, a.point) for a in self.on_curve)
        min_off = (min(self._dist(point, a.point) for a in self.off_curve)
                   if self.off_curve else float('inf'))
        
        # Curvature = how close to the boundary
        # Deep inside: min_on small, min_off large → low curvature
        # Near edge: min_on ≈ min_off → high curvature
        if min_off == float('inf'):
            return min_on  # No failures known, curvature = distance from nearest truth
        
        return min_on / (min_on + min_off)  # 0 = on top of truth, 1 = at boundary
    
    def coverage(self) -> float:
        """What fraction of the nearby space is on-curve (verified)?"""
        if not self.on_curve:
            return 0.0
        total = len(self.on_curve) + len(self.off_curve)
        return len(self.on_curve) / total if total > 0 else 0.0
    
    def boundary_resolution(self) -> float:
        """
        How well do we know the boundary between true and false?
        High = many anchors on both sides of the boundary.
        Low = one-sided (all successes or all failures).
        """
        if not self.on_curve or not self.off_curve:
            return 0.0
        
        # Find off-curve points that are CLOSE to on-curve points
        boundary_pairs = 0
        for off in self.off_curve:
            for on in self.on_curve:
                if self._dist(off.point, on.point) < 2.0:  # Nearby
                    boundary_pairs += 1
                    break
        
        return boundary_pairs / len(self.off_curve)
    
    def maturation_level(self) -> str:
        """Where are we on the maturation curve?"""
        n = len(self.flux_programs)
        if n >= 200: return "autonomous"
        if n >= 60:  return "template"
        if n >= 20:  return "compiled"
        if n >= 6:   return "equipped"
        return "infant"
    
    def api_efficiency(self) -> float:
        """
        API calls per new anchor point.
        Mature system: many anchors per call (decomposition produces multiple verifiable subs).
        Infant system: one call per anchor.
        """
        total_anchors = len(self.on_curve) + len(self.off_curve)
        if self.api_calls_total == 0:
            return 0.0
        return total_anchors / self.api_calls_total
    
    def _dist(self, a, b):
        return math.sqrt(sum((x-y)**2 for x, y in zip(a, b)))
    
    def summary(self) -> dict:
        return {
            "on_curve_anchors": len(self.on_curve),
            "off_curve_anchors": len(self.off_curve),
            "flux_programs": len(self.flux_programs),
            "coverage": f"{self.coverage()*100:.1f}%",
            "boundary_resolution": f"{self.boundary_resolution()*100:.1f}%",
            "maturation": self.maturation_level(),
            "api_efficiency": f"{self.api_efficiency():.2f} anchors/call",
            "model_needed": {
                "autonomous": ["none"] * len(self.flux_programs),
                "still_needs_api": len(self.on_curve) - len(self.flux_programs),
            },
        }


# ─── The Spline Learns From Failures ──────────────────────────────

def demonstrate_spline():
    """
    Show how the knowledge spline evolves as verification results come in.
    Successes are on-curve. Failures are the handles that shape understanding.
    """
    spline = KnowledgeSpline()
    
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  THE KNOWLEDGE SPLINE — Anchors of Truth and Failure   ║")
    print("╚══════════════════════════════════════════════════════════╝")
    
    # Phase 1: First verifications — sparse on-curve points
    print("\n  Phase 1: First anchors (6 verifiers, 6 on-curve points)")
    verifications = [
        ((0, 0), "snap_idempotence", "eisenstein_snap", 0.0, "snap_idempotence"),
        ((1, 0), "covering_radius", "eisenstein_snap", 0.001, "covering_radius"),
        ((0, 1), "norm_multiplicative", "norm", 0.0, "norm_multiplicative"),
        ((1, 1), "dodecet_cardinality", "dodecet_snap", 0.0, "dodecet_cardinality"),
        ((-1, 0), "drift_bounded", "constraint_walk", 0.03, "drift_bounded"),
        ((0, -1), "hex_closest_pack", "eisenstein_snap", 0.0, "hex_closest_pack"),
    ]
    spline.api_calls_total = 3  # 3 decomposition calls to discover these
    
    for point, conj, verif, delta, flux in verifications:
        spline.add_success(point, conj, verif, delta, flux)
    
    s = spline.summary()
    print(f"    {s['on_curve_anchors']} on-curve, {s['off_curve_anchors']} off-curve")
    print(f"    Coverage: {s['coverage']}")
    print(f"    API efficiency: {s['api_efficiency']}")
    print(f"    Maturation: {s['maturation']}")
    print(f"    Spline shape: ● ● ● ● ● ●  (6 dots, no shape yet)")
    
    # Phase 2: The snap bug — a FAILURE that becomes a handle
    print("\n  Phase 2: The snap bug — off-curve anchor discovered")
    print("    (The old snap had 95K failures. Each failure is a control point.)")
    
    # The bug was at large coordinates — far from origin
    failure_points = [
        ((10, 15), "snap_idempotence_fail", "old_snap", 2.3),
        ((-8, 20), "snap_idempotence_fail", "old_snap", 1.8),
        ((25, -10), "covering_radius_fail", "old_snap", 32.0),
        ((15, 30), "snap_idempotence_fail", "old_snap", 4.1),
    ]
    
    for point, conj, verif, delta in failure_points:
        spline.add_failure(point, conj, verif, delta)
    
    s = spline.summary()
    print(f"    {s['on_curve_anchors']} on-curve, {s['off_curve_anchors']} off-curve")
    print(f"    Coverage: {s['coverage']}")
    print(f"    Boundary resolution: {s['boundary_resolution']}")
    print(f"    Spline shape: ●─●─●   ╳─╳─╳  (on-curve truth, off-curve failure)")
    print(f"                   \\  |  /")
    print(f"                    shape emerges from the handles")
    
    # Phase 3: After fix — failures become new on-curve anchors
    print("\n  Phase 3: After fix — failures become truths")
    print("    (Fixed snap, re-ran at same coordinates. Now they pass.)")
    
    for point, conj, verif, delta in failure_points:
        spline.add_success(point, f"{conj}_FIXED", "eisenstein_snap_v2", 0.001, None)
    spline.api_calls_total += 1
    
    s = spline.summary()
    print(f"    {s['on_curve_anchors']} on-curve, {s['off_curve_anchors']} off-curve (historical)")
    print(f"    Coverage: {s['coverage']}")
    print(f"    The off-curve points are STILL THERE — they're the handles")
    print(f"    that taught us where the bug was. The spline remembers.")
    
    # Phase 4: Exploration fills in the boundary
    print("\n  Phase 4: Exploration — finding the boundary's shape")
    print("    (Running verifiers at edge cases near known failures)")
    
    random.seed(42)
    edge_cases = 0
    for _ in range(100):
        # Points near the boundary of the old failures
        x = random.gauss(10, 5)
        y = random.gauss(15, 5)
        point = (x, y)
        curvature = spline.curvature_at(point)
        
        if curvature > 0.3:  # Near boundary
            edge_cases += 1
            # Simulate: most pass, some fail near the boundary
            if random.random() < 0.1:  # 10% failure rate at boundary
                spline.add_failure(point, "boundary_exploration", "eisenstein_snap", 0.4)
            else:
                spline.add_success(point, "boundary_exploration", "eisenstein_snap", 0.2, None)
    
    spline.api_calls_total += 2
    
    s = spline.summary()
    print(f"    Explored {edge_cases} boundary-adjacent points")
    print(f"    {s['on_curve_anchors']} on-curve, {s['off_curve_anchors']} off-curve")
    print(f"    Coverage: {s['coverage']}")
    print(f"    Boundary resolution: {s['boundary_resolution']}")
    
    # The maturation curve
    print("\n  ═══════════════════════════════════════════════════")
    print("  THE SPLINE'S MATURATION")
    print("  ═══════════════════════════════════════════════════")
    print(f"  Anchors: {spline.summary()['on_curve_anchors']} on-curve, {spline.summary()['off_curve_anchors']} off-curve")
    print(f"  FLUX programs: {len(spline.flux_programs)} autonomous capabilities")
    print(f"  API efficiency: {spline.api_efficiency():.1f} anchors per call")
    print(f"  Maturation: {spline.maturation_level()}")
    print()
    print("  The successes are where the spline passes through certainty.")
    print("  The failures are the handles that give the spline its shape.")
    print("  Without both, it's just a straight line through scattered dots.")
    print()
    print("  Every success is an anchor ON the batton spline.")
    print("  Every failure is an anchor OFF the batton.")
    print("  The spline IS the knowledge. The batton IS the instrument.")


if __name__ == "__main__":
    demonstrate_spline()
