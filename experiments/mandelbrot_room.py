#!/usr/bin/env python3
"""
mandelbrot_room.py — The Mandelbrot Room Experiment
====================================================

The idea: each room in a jam session is a point in complex parameter space.
As the rooms interact, the parameter space is explored via z → z² + c
(Mandelbrot iteration). Rooms near the Mandelbrot set boundary — the edge
between convergent and divergent behavior — produce the most paradigm shifts.

PREDICTION: paradigm shift rate is maximized near the Mandelbrot boundary.

Architecture:
    MandelbrotRoom  — a room whose (courage, boredom) maps to c ∈ ℂ
    MandelbrotSpace — the complex plane tracking z → z² + c per room
    MandelbrotExperiment — 1000 iterations, 20 rooms, full analysis
"""

from __future__ import annotations

import json
import math
import random
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Mandelbrot boundary distance estimation
# ---------------------------------------------------------------------------

def mandelbrot_escape_time(c: complex, max_iter: int = 256) -> int:
    """Compute escape time for point c in the Mandelbrot set.
    Returns iteration count (max_iter if point doesn't escape)."""
    z = 0 + 0j
    for i in range(max_iter):
        z = z * z + c
        if abs(z) > 2.0:
            return i
    return max_iter


def mandelbrot_distance_estimate(c: complex, max_iter: int = 256) -> float:
    """Estimate distance from c to the Mandelbrot set boundary.
    Uses the derivative method: distance ≈ |z| * ln|z| / |dz|.
    Returns approximate distance (smaller = closer to boundary)."""
    z = 0 + 0j
    dz = 1 + 0j  # derivative dz/dc
    for i in range(max_iter):
        dz = 2 * z * dz + 1
        z = z * z + c
        if abs(z) > 1e10:
            # Point escaped — distance estimate is valid
            return abs(z) * math.log(abs(z)) / abs(dz)
    # Point didn't escape — inside the set
    return 0.0


def is_in_mandelbrot(c: complex, max_iter: int = 256) -> bool:
    """Check if c is inside the Mandelbrot set."""
    return mandelbrot_escape_time(c, max_iter) == max_iter


def boundary_proximity(c: complex, max_iter: int = 256) -> float:
    """Return a 0-1 score: 1 = on boundary, 0 = deep inside or far outside.
    
    Uses escape time as a proxy: points near the boundary have high escape
    times (they almost don't escape), while points far outside escape quickly.
    Deep inside points also have max escape time, so we combine with
    distance estimation.
    """
    esc = mandelbrot_escape_time(c, max_iter)
    
    if esc == max_iter:
        # Inside the set — check how deep
        # Use a secondary test: perturb slightly and see if it escapes
        perturbations = [c + 0.01 * e for e in [1, -1, 1j, -1j]]
        escape_count = sum(1 for p in perturbations 
                          if mandelbrot_escape_time(p, max_iter) < max_iter)
        # If neighbors escape, we're near the boundary
        return escape_count / 4.0
    else:
        # Outside — normalize escape time
        # High escape time = close to boundary
        return min(1.0, esc / (max_iter * 0.5))


# ---------------------------------------------------------------------------
# MandelbrotRoom — a room in complex parameter space
# ---------------------------------------------------------------------------

@dataclass
class MandelbrotRoom:
    """A room whose (courage, boredom_threshold) maps to c ∈ ℂ.
    
    The room plays in the jam session, and its state evolves via the
    Mandelbrot iteration z → z² + c. The room's creative output depends
    on whether its orbit converges, diverges, or orbits near the boundary.
    """
    room_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    courage: float = 0.5
    boredom_threshold: float = 0.3
    c: complex = 0 + 0j  # parameter in complex plane
    z: complex = 0 + 0j  # current iteration state
    
    # Tracking
    escape_time: int = 0
    escaped: bool = False
    orbit_history: List[complex] = field(default_factory=list)
    paradigm_shifts: int = 0
    total_output: float = 0.0
    boundary_dist: float = 0.0
    boundary_prox: float = 0.0
    
    # Play dynamics (from room_play.py)
    boredom: float = 0.0
    novelty_found: List[float] = field(default_factory=list)
    state_norm_history: List[float] = field(default_factory=list)


def make_room(name: str, courage: float, boredom_threshold: float,
              c_real: float, c_imag: float) -> MandelbrotRoom:
    """Create a Mandelbrot room with explicit parameter placement."""
    c = complex(c_real, c_imag)
    room = MandelbrotRoom(
        name=name,
        courage=courage,
        boredom_threshold=boredom_threshold,
        c=c,
        z=0 + 0j,
        escape_time=0,
        boundary_dist=mandelbrot_distance_estimate(c),
        boundary_prox=boundary_proximity(c),
    )
    return room


def make_random_room(idx: int) -> MandelbrotRoom:
    """Create a room at a random point in the complex plane.
    Biased toward the interesting region [-2.5, 1] × [-1.5, 1.5]."""
    c_real = random.uniform(-2.5, 1.0)
    c_imag = random.uniform(-1.5, 1.5)
    courage = random.uniform(0.0, 1.0)
    boredom_threshold = random.uniform(0.1, 0.9)
    name = f"room-{idx:02d}"
    return make_room(name, courage, boredom_threshold, c_real, c_imag)


# ---------------------------------------------------------------------------
# MandelbrotSpace — the complex plane as a creative substrate
# ---------------------------------------------------------------------------

class MandelbrotSpace:
    """The complex parameter space where rooms live and interact.
    
    Each room has a point c in the complex plane. The room's creative
    output is modeled by the Mandelbrot iteration z → z² + c. Rooms
    whose orbits are near the boundary produce the most paradigm shifts.
    """
    
    def __init__(self, max_iter: int = 256, escape_radius: float = 2.0):
        self.max_iter = max_iter
        self.escape_radius = escape_radius
        self.rooms: Dict[str, MandelbrotRoom] = {}
        self.iteration_log: List[Dict[str, Any]] = []
        self.paradigm_shift_log: List[Dict[str, Any]] = []
        self.global_round = 0
    
    def add_room(self, room: MandelbrotRoom):
        self.rooms[room.room_id] = room
    
    def step(self) -> Dict[str, Any]:
        """One iteration of all rooms: z → z² + c for each.
        
        Returns round summary with paradigm shift events."""
        self.global_round += 1
        round_shifts = []
        
        for room_id, room in self.rooms.items():
            if room.escaped:
                # Diverged room — orbit is unbounded
                # Model: chaotic output, no paradigm shifts
                room.z = room.z * room.z + room.c
                room.total_output += abs(room.z)
                # Occasionally reset to prevent overflow
                if abs(room.z) > 1e15:
                    room.z = complex(random.gauss(0, 0.1), random.gauss(0, 0.1))
                continue
            
            # Mandelbrot iteration
            old_z = room.z
            room.z = room.z * room.z + room.c
            room.orbit_history.append(room.z)
            
            # Track state norm
            state_norm = abs(room.z)
            room.state_norm_history.append(state_norm)
            room.total_output += state_norm
            
            # Check escape
            if abs(room.z) > self.escape_radius:
                room.escaped = True
                room.escape_time = self.global_round
                continue
            
            # Boredom dynamics
            if len(room.state_norm_history) >= 2:
                recent_change = abs(room.state_norm_history[-1] - room.state_norm_history[-2])
                if recent_change < 0.01 * room.boredom_threshold:
                    room.boredom = min(1.0, room.boredom + 0.02)
                else:
                    room.boredom = max(0.0, room.boredom - 0.01 * recent_change)
            
            # ── Paradigm shift detection ──
            #
            # Key insight: the Mandelbrot iteration dynamics differ qualitatively
            # depending on where c sits relative to the boundary:
            #   - Deep inside: z converges to a fixed point quickly (boring)
            #   - Outside: z diverges immediately (chaotic, no structure)
            #   - Near boundary: z orbits in complex patterns, slow convergence,
            #     high variability — THIS is where creativity lives
            #
            # We measure "orbit complexity" = how much the orbit varies.
            # Sudden spikes in orbit complexity = paradigm shifts.
            
            orbit_complexity = 0.0
            if len(room.orbit_history) >= 5:
                recent = [abs(z) for z in room.orbit_history[-5:]]
                orbit_complexity = float(np.std(recent)) / max(float(np.mean(recent)), 1e-10)
            
            # Track orbit complexity history
            if not hasattr(room, '_complexity_history'):
                room._complexity_history = []
            room._complexity_history.append(orbit_complexity)
            
            # A paradigm shift = sudden spike in orbit complexity
            # (the orbit "almost escapes" then comes back — a near-miss)
            if len(room._complexity_history) >= 10:
                baseline = float(np.mean(room._complexity_history[-10:-1]))
                current = orbit_complexity
                
                # Spike detection: current complexity significantly above baseline
                spike_ratio = current / max(baseline, 1e-10)
                
                # Also factor in: boundary proximity (more shifts near boundary)
                # and courage/boredom (room personality)
                shift_trigger = (
                    spike_ratio *                    # orbit suddenly became complex
                    (1 + room.boundary_prox * 3) *    # boundary proximity amplifies
                    (0.3 + 0.7 * room.courage) *      # courageous rooms capitalize on spikes
                    (0.3 + 0.7 * min(room.boredom + 0.3, 1.0))  # some boredom helps
                )
                
                if shift_trigger > 2.0 and random.random() < min(0.8, shift_trigger / 5.0):
                    room.paradigm_shifts += 1
                    room.boredom = max(0.0, room.boredom - 0.3)
                    room.novelty_found.append(shift_trigger)
                    
                    shift_event = {
                        "round": self.global_round,
                        "room_id": room_id,
                        "room_name": room.name,
                        "c": str(room.c),
                        "z": str(room.z),
                        "orbit_complexity": float(orbit_complexity),
                        "spike_ratio": float(spike_ratio),
                        "boundary_prox": float(room.boundary_prox),
                        "boundary_dist": float(room.boundary_dist),
                        "boredom": float(room.boredom),
                        "courage": float(room.courage),
                        "shift_strength": float(shift_trigger),
                        "is_in_set": is_in_mandelbrot(room.c),
                    }
                    round_shifts.append(shift_event)
                    self.paradigm_shift_log.append(shift_event)
        
        # Record round
        round_summary = {
            "round": self.global_round,
            "shifts_this_round": len(round_shifts),
            "shifts": round_shifts,
            "rooms_active": sum(1 for r in self.rooms.values() if not r.escaped),
            "rooms_escaped": sum(1 for r in self.rooms.values() if r.escaped),
            "total_shifts": sum(r.paradigm_shifts for r in self.rooms.values()),
        }
        self.iteration_log.append(round_summary)
        return round_summary
    
    def run(self, n_iterations: int = 1000) -> Dict[str, Any]:
        """Run the full experiment."""
        for _ in range(n_iterations):
            self.step()
        return self.analyze()
    
    def analyze(self) -> Dict[str, Any]:
        """Analyze results: map divergence rate vs paradigm shifts vs boundary distance."""
        
        room_results = []
        for room_id, room in self.rooms.items():
            result = {
                "room_id": room_id,
                "name": room.name,
                "c_real": float(room.c.real),
                "c_imag": float(room.c.imag),
                "courage": room.courage,
                "boredom_threshold": room.boredom_threshold,
                "escaped": room.escaped,
                "escape_time": room.escape_time,
                "paradigm_shifts": room.paradigm_shifts,
                "total_output": float(room.total_output),
                "boundary_dist": float(room.boundary_dist),
                "boundary_prox": float(room.boundary_prox),
                "is_in_set": is_in_mandelbrot(room.c),
                "avg_boredom": float(np.mean([room.boredom]) if hasattr(room.boredom, '__len__') else room.boredom),
                "max_novelty": float(max(room.novelty_found)) if room.novelty_found else 0.0,
                "orbit_length": len(room.orbit_history),
                "final_z_norm": float(abs(room.z)),
            }
            room_results.append(result)
        
        # Classify rooms
        boundary_rooms = [r for r in room_results if 0.3 < r["boundary_prox"] < 0.8]
        inside_rooms = [r for r in room_results if r["is_in_set"] and r["boundary_prox"] < 0.3]
        outside_rooms = [r for r in room_results if not r["is_in_set"] and r["escape_time"] < 50]
        
        # Average paradigm shifts per category
        avg_shifts_boundary = np.mean([r["paradigm_shifts"] for r in boundary_rooms]) if boundary_rooms else 0
        avg_shifts_inside = np.mean([r["paradigm_shifts"] for r in inside_rooms]) if inside_rooms else 0
        avg_shifts_outside = np.mean([r["paradigm_shifts"] for r in outside_rooms]) if outside_rooms else 0
        
        # Correlation analysis
        boundary_dists = [r["boundary_dist"] for r in room_results]
        paradigm_shifts = [r["paradigm_shifts"] for r in room_results]
        boundary_proxes = [r["boundary_prox"] for r in room_results]
        
        # Compute correlation between boundary proximity and paradigm shifts
        if len(set(paradigm_shifts)) > 1:
            corr_prox_shifts = float(np.corrcoef(boundary_proxes, paradigm_shifts)[0, 1])
        else:
            corr_prox_shifts = 0.0
        
        if len(set(boundary_dists)) > 1 and all(math.isfinite(d) for d in boundary_dists):
            finite_dists = [d for d in boundary_dists if math.isfinite(d)]
            finite_shifts = [paradigm_shifts[i] for i, d in enumerate(boundary_dists) if math.isfinite(d)]
            if len(set(finite_dists)) > 1:
                corr_dist_shifts = float(np.corrcoef(finite_dists, finite_shifts)[0, 1])
            else:
                corr_dist_shifts = 0.0
        else:
            corr_dist_shifts = 0.0
        
        # Top rooms by paradigm shifts
        top_rooms = sorted(room_results, key=lambda r: r["paradigm_shifts"], reverse=True)[:10]
        
        return {
            "total_rounds": self.global_round,
            "total_rooms": len(self.rooms),
            "total_paradigm_shifts": sum(r["paradigm_shifts"] for r in room_results),
            "room_results": room_results,
            
            # Category analysis
            "n_boundary_rooms": len(boundary_rooms),
            "n_inside_rooms": len(inside_rooms),
            "n_outside_rooms": len(outside_rooms),
            "avg_shifts_boundary": float(avg_shifts_boundary),
            "avg_shifts_inside": float(avg_shifts_inside),
            "avg_shifts_outside": float(avg_shifts_outside),
            
            # Correlations
            "corr_boundary_prox_vs_paradigm_shifts": float(corr_prox_shifts),
            "corr_boundary_dist_vs_paradigm_shifts": float(corr_dist_shifts),
            
            # Top rooms
            "top_10_rooms": top_rooms,
            
            # Prediction check
            "prediction_confirmed": avg_shifts_boundary > avg_shifts_inside and avg_shifts_boundary > avg_shifts_outside,
        }


# ---------------------------------------------------------------------------
# Experiment Runner
# ---------------------------------------------------------------------------

def run_experiment():
    """Run the Mandelbrot Room experiment: 20 rooms, 1000 iterations."""
    print("⚒️  Mandelbrot Room Experiment")
    print("=" * 70)
    print("   PREDICTION: paradigm shift rate maximized near Mandelbrot boundary")
    print("=" * 70)
    
    space = MandelbrotSpace(max_iter=256, escape_radius=2.0)
    
    # Place 20 rooms at carefully chosen points:
    # Some inside the set, some outside, some near the boundary
    
    # 5 rooms near the boundary (the interesting ones)
    # Points carefully chosen to be ON or very near the boundary
    boundary_points = [
        (-0.7500, 0.1000),   # Near main cardioid boundary
        (-0.1226, 0.7449),   # Near period-3 bulb boundary (just outside)
        (-1.2500, 0.0200),   # Near period-2 bulb boundary (slightly off-axis)
        (0.3600, 0.1000),    # Near the cusp of main cardioid
        (-0.1528, 1.0397),   # Near the tip of the antenna
    ]
    for i, (cr, ci) in enumerate(boundary_points):
        courage = random.uniform(0.5, 0.9)
        boredom = random.uniform(0.2, 0.5)
        room = make_room(f"boundary-{i:02d}", courage, boredom, cr, ci)
        space.add_room(room)
        print(f"   Added {room.name}: c={room.c:.4f}, "
              f"boundary_prox={room.boundary_prox:.3f}, "
              f"in_set={room.boundary_dist == 0.0}")
    
    # 5 rooms deep inside the set (the safe ones)
    inside_points = [
        (0.0, 0.0),      # Center of main cardioid (maximally boring)
        (-0.25, 0.0),    # Deep inside cardioid
        (0.15, 0.05),    # Inside cardioid
        (-0.5, 0.05),    # Inside cardioid
        (-0.6, 0.0),     # Inside period-2 bulb
    ]
    for i, (cr, ci) in enumerate(inside_points):
        courage = random.uniform(0.1, 0.4)
        boredom = random.uniform(0.5, 0.9)
        room = make_room(f"inside-{i:02d}", courage, boredom, cr, ci)
        space.add_room(room)
        print(f"   Added {room.name}: c={room.c:.4f}, "
              f"boundary_prox={room.boundary_prox:.3f}, "
              f"in_set={is_in_mandelbrot(room.c)}")
    
    # 5 rooms clearly outside the set (the reckless ones)
    outside_points = [
        (2.0, 0.0),      # Far outside
        (-2.5, 0.5),     # Far outside
        (0.0, 2.0),      # Far outside
        (-1.5, 1.5),     # Far outside
        (1.5, 0.5),      # Outside
    ]
    for i, (cr, ci) in enumerate(outside_points):
        courage = random.uniform(0.7, 1.0)
        boredom = random.uniform(0.1, 0.3)
        room = make_room(f"outside-{i:02d}", courage, boredom, cr, ci)
        space.add_room(room)
        print(f"   Added {room.name}: c={room.c:.4f}, "
              f"boundary_prox={room.boundary_prox:.3f}, "
              f"in_set={is_in_mandelbrot(room.c)}")
    
    # 5 rooms at random positions
    for i in range(5):
        room = make_random_room(i)
        room.name = f"random-{i:02d}"
        space.add_room(room)
        print(f"   Added {room.name}: c={room.c:.4f}, "
              f"boundary_prox={room.boundary_prox:.3f}, "
              f"in_set={is_in_mandelbrot(room.c)}")
    
    print(f"\n   Running 1000 iterations...")
    results = space.run(1000)
    
    # Print results
    print("\n" + "=" * 70)
    print("📊 RESULTS")
    print("=" * 70)
    
    print(f"\n   Total Rounds: {results['total_rounds']}")
    print(f"   Total Rooms: {results['total_rooms']}")
    print(f"   Total Paradigm Shifts: {results['total_paradigm_shifts']}")
    
    print(f"\n   Category Analysis:")
    print(f"     Boundary rooms ({results['n_boundary_rooms']}): "
          f"avg {results['avg_shifts_boundary']:.2f} shifts/room")
    print(f"     Inside rooms ({results['n_inside_rooms']}): "
          f"avg {results['avg_shifts_inside']:.2f} shifts/room")
    print(f"     Outside rooms ({results['n_outside_rooms']}): "
          f"avg {results['avg_shifts_outside']:.2f} shifts/room")
    
    print(f"\n   Correlations:")
    print(f"     Boundary proximity vs paradigm shifts: "
          f"{results['corr_boundary_prox_vs_paradigm_shifts']:.4f}")
    print(f"     Boundary distance vs paradigm shifts: "
          f"{results['corr_boundary_dist_vs_paradigm_shifts']:.4f}")
    
    print(f"\n   Top 10 Rooms by Paradigm Shifts:")
    for i, r in enumerate(results['top_10_rooms']):
        print(f"     {i+1:2d}. {r['name']:15s} | shifts={r['paradigm_shifts']:4d} | "
              f"c={r['c_real']:+.3f}{r['c_imag']:+.3f}i | "
              f"prox={r['boundary_prox']:.3f} | "
              f"courage={r['courage']:.2f} | "
              f"escaped={r['escaped']}")
    
    prediction = results['prediction_confirmed']
    print(f"\n   PREDICTION {'✅ CONFIRMED' if prediction else '❌ NOT CONFIRMED'}")
    print(f"     Boundary rooms produce {'more' if prediction else 'not more'} "
          f"paradigm shifts than inside/outside rooms")
    
    # Save results
    results_path = Path("/home/phoenix/.openclaw/workspace/experiments/mandelbrot_room_results.json")
    
    def make_serializable(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.float32, np.float64)):
            return float(obj)
        if isinstance(obj, (np.int32, np.int64)):
            return int(obj)
        if isinstance(obj, complex):
            return str(obj)
        if isinstance(obj, dict):
            return {k: make_serializable(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [make_serializable(v) for v in obj]
        if isinstance(obj, bool):
            return obj
        return obj
    
    serializable = make_serializable(results)
    with open(results_path, "w") as f:
        json.dump(serializable, f, indent=2, default=str)
    print(f"\n💾 Results saved to {results_path}")
    
    return results


if __name__ == "__main__":
    results = run_experiment()
