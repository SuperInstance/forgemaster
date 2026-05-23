#!/usr/bin/env python3
"""
room_play_v2.py — The Code Beyond the Code, Volume II
======================================================

Extends room_play.py with five new subsystems:

1. GaugeConnection  — measuring the phase between rooms
2. FormatBridge     — rooms speaking different substrate languages
3. TimeAnalogue     — time as a continuous analogue variable
4. EratosthenesMeasurement — two rooms measuring the same shadow
5. JamSessionV2     — integrates all of the above

Built on top of the original ImaginarySpace, Anticipation, PlayRoom architecture.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import numpy as np

# Re-use the v1 foundation
from room_play import (
    ImaginarySpace, ImaginaryResult, WhatIf, ParadigmShift,
    Anticipation, PlayRoom, PlayRoomConfig, JamSession,
)


# ═══════════════════════════════════════════════════════════════════════════
# 1. GaugeConnection — measuring the phase between rooms
# ═══════════════════════════════════════════════════════════════════════════

class GaugeConnection:
    """Track angular rotation of each room's state vector over time.
    
    Each room traces a path through state space. The angle of that path
    is the room's phase. The difference in phase between two rooms is the
    gauge field — the "connection" that measures curvature.
    
    Phase velocity = how fast a room rotates through state space
    Phase locking = when two rooms synchronize their rotation
    Gauge curvature = how the phase difference changes over time
    
    Analogy: Two runners on a circular track. Their angular positions
    are phases. Their speeds are phase velocities. When they run at the
    same speed = phase locked. The gauge connection measures how the
    track itself curves between them.
    """

    def __init__(self, dimension: int = 32):
        self.dimension = dimension
        # Track state history per room for angular computation
        self.state_history: Dict[str, List[np.ndarray]] = {}
        # Computed quantities
        self.phases: Dict[str, List[float]] = {}           # room → phase over time
        self.phase_velocities: Dict[str, List[float]] = {}  # room → angular velocity
        self.phase_differences: Dict[Tuple[str, str], List[float]] = {}  # (r1,r2) → Δφ
        self.phase_locks: List[PhaseLockEvent] = []
        self.curvature_history: List[CurvatureMeasurement] = []

    def record_state(self, room_id: str, state: np.ndarray):
        """Record a room's state and compute phase."""
        if room_id not in self.state_history:
            self.state_history[room_id] = []
            self.phases[room_id] = []
            self.phase_velocities[room_id] = []

        self.state_history[room_id].append(state.copy())

        # Compute phase: angle of the state vector's dominant plane
        # Use the angle in the first two PCA-like dimensions
        phase = self._compute_phase(state)
        self.phases[room_id].append(phase)

        # Compute phase velocity: rate of change of phase
        if len(self.phases[room_id]) >= 2:
            dphi = self.phases[room_id][-1] - self.phases[room_id][-2]
            # Wrap to [-π, π]
            dphi = (dphi + math.pi) % (2 * math.pi) - math.pi
            self.phase_velocities[room_id].append(dphi)
        else:
            self.phase_velocities[room_id].append(0.0)

    def compute_pairwise(self, room_ids: List[str]):
        """Compute all pairwise phase differences and detect phase locking."""
        for i, r1 in enumerate(room_ids):
            for r2 in room_ids[i+1:]:
                pair = (r1, r2)
                if pair not in self.phase_differences:
                    self.phase_differences[pair] = []

                if r1 in self.phases and r2 in self.phases:
                    p1 = self.phases[r1][-1] if self.phases[r1] else 0.0
                    p2 = self.phases[r2][-1] if self.phases[r2] else 0.0
                    diff = (p1 - p2 + math.pi) % (2 * math.pi) - math.pi
                    self.phase_differences[pair].append(diff)

                    # Check for phase locking: diff has been small for several steps
                    history = self.phase_differences[pair]
                    if len(history) >= 5:
                        recent = history[-5:]
                        if all(abs(d) < 0.3 for d in recent):
                            v1 = self.phase_velocities[r1][-5:] if len(self.phase_velocities[r1]) >= 5 else []
                            v2 = self.phase_velocities[r2][-5:] if len(self.phase_velocities[r2]) >= 5 else []
                            if v1 and v2 and abs(np.mean(v1[-5:]) - np.mean(v2[-5:])) < 0.2:
                                event = PhaseLockEvent(
                                    room_a=r1, room_b=r2,
                                    phase_diff=float(np.mean(recent)),
                                    velocity_diff=float(abs(np.mean(v1[-5:]) - np.mean(v2[-5:]))),
                                    round_num=len(history),
                                )
                                self.phase_locks.append(event)

    def compute_curvature(self, room_ids: List[str], round_num: int):
        """Compute gauge curvature from triplets of rooms.
        
        Curvature = the holonomy around a small loop in the gauge field.
        For three rooms A, B, C: go A→B→C→A and sum the phase differences.
        If the sum is zero, the space is flat. Non-zero = curvature.
        """
        if len(room_ids) < 3:
            return

        for i in range(min(5, len(room_ids))):
            triplet = random.sample(room_ids, 3)
            r1, r2, r3 = triplet
            pairs = [(r1, r2), (r2, r3), (r3, r1)]
            diffs = []
            for pair in pairs:
                rp = pair if pair in self.phase_differences else (pair[1], pair[0])
                if rp in self.phase_differences and self.phase_differences[rp]:
                    diffs.append(self.phase_differences[rp][-1])
                else:
                    diffs.append(0.0)

            holonomy = sum(diffs)  # Should be ~0 for flat space
            curvature = abs(holonomy) / (2 * math.pi)  # Normalized

            self.curvature_history.append(CurvatureMeasurement(
                rooms=triplet,
                holonomy=float(holonomy),
                curvature=float(curvature),
                round_num=round_num,
            ))

    def get_report(self) -> Dict[str, Any]:
        """Generate gauge connection report."""
        lock_count = len(self.phase_locks)
        avg_velocities = {}
        for rid, vels in self.phase_velocities.items():
            if vels:
                avg_velocities[rid] = float(np.mean(np.abs(vels)))

        avg_curvature = 0.0
        if self.curvature_history:
            avg_curvature = float(np.mean([c.curvature for c in self.curvature_history]))

        return {
            "phase_locks_detected": lock_count,
            "phase_locks": [
                {"rooms": (e.room_a, e.room_b), "diff": e.phase_diff, "round": e.round_num}
                for e in self.phase_locks[-20:]
            ],
            "avg_phase_velocities": avg_velocities,
            "avg_curvature": avg_curvature,
            "curvature_measurements": len(self.curvature_history),
            "max_curvature": max((c.curvature for c in self.curvature_history), default=0.0),
        }

    def _compute_phase(self, state: np.ndarray) -> float:
        """Compute the phase angle of a state vector.
        
        Projects onto the first two components and returns atan2.
        For higher dimensions, uses the dominant eigenplane.
        """
        if len(state) < 2:
            return 0.0
        return float(math.atan2(state[1], state[0]))


@dataclass
class PhaseLockEvent:
    """Two rooms have phase-locked — synchronized their rotation."""
    room_a: str = ""
    room_b: str = ""
    phase_diff: float = 0.0
    velocity_diff: float = 0.0
    round_num: int = 0


@dataclass
class CurvatureMeasurement:
    """Gauge curvature measured from a triplet of rooms."""
    rooms: List[str] = field(default_factory=list)
    holonomy: float = 0.0
    curvature: float = 0.0
    round_num: int = 0


# ═══════════════════════════════════════════════════════════════════════════
# 2. FormatBridge — rooms speaking different substrate languages
# ═══════════════════════════════════════════════════════════════════════════

class FormatBridge:
    """Translate between different internal representations.
    
    Different rooms may "think" in different substrates:
    - Vector: raw floating-point state vectors (the default)
    - Symbolic: discrete symbols/categories
    - Code: program-like representations
    - Natural Language: text-based representations
    
    A FormatBridge translates between these WITHOUT losing the meaning.
    Like MIDI: same note (middle C), different instruments (piano vs guitar).
    
    Key property: semantic distance preservation.
    If two vectors are close, their translations should also be close.
    """

    # Substrate types
    VECTOR = "vector"
    SYMBOLIC = "symbolic"
    CODE = "code"
    NATURAL = "natural_language"

    # Symbolic vocabulary — maps continuous regions to discrete symbols
    SYMBOLS = [
        "convergence", "divergence", "oscillation", "stillness",
        "expansion", "contraction", "rotation", "reflection",
        "harmony", "dissonance", "silence", "crescendo",
        "bridge", "tunnel", "surface", "depth",
        "light", "shadow", "edge", "center",
    ]

    def __init__(self, dimension: int = 32):
        self.dimension = dimension
        # Codecs: encode from vector, decode back to vector
        self.codecs = {
            self.VECTOR: self._identity_codec(),
            self.SYMBOLIC: self._symbolic_codec(),
            self.CODE: self._code_codec(),
            self.NATURAL: self._natural_codec(),
        }
        # Translation cache for round-trip verification
        self.translation_log: List[TranslationRecord] = []

    def translate(self, state: np.ndarray, from_fmt: str, to_fmt: str) -> Any:
        """Translate a state from one format to another."""
        if from_fmt == to_fmt:
            return state

        # Step 1: Encode to intermediate (vector) if not already
        if from_fmt != self.VECTOR:
            intermediate = self.codecs[from_fmt]["decode"](state) if isinstance(state, str) else state
        else:
            intermediate = state

        # Step 2: Decode to target format
        result = self.codecs[to_fmt]["encode"](intermediate)

        return result

    def round_trip(self, state: np.ndarray, fmt: str) -> Tuple[float, Any, Any]:
        """Test round-trip: vector → fmt → vector. Returns fidelity loss."""
        encoded = self.codecs[fmt]["encode"](state)
        decoded = self.codecs[fmt]["decode"](encoded)
        loss = float(np.linalg.norm(state - decoded))
        return loss, encoded, decoded

    def semantic_preservation_test(
        self, states: List[np.ndarray], fmt: str, k: int = 5
    ) -> float:
        """Test that translation preserves semantic distance.
        
        For each state, find its k nearest neighbors in the original space.
        Translate all to target format and back. Check if neighbors stay neighbors.
        Returns: fraction of neighbors preserved (0-1, higher is better).
        """
        if len(states) < k + 1:
            return 1.0

        preserved = 0
        total = 0

        # Original distances
        orig_dists = np.zeros((len(states), len(states)))
        for i in range(len(states)):
            for j in range(i + 1, len(states)):
                orig_dists[i, j] = np.linalg.norm(states[i] - states[j])
                orig_dists[j, i] = orig_dists[i, j]

        # Round-trip states
        round_tripped = []
        for s in states:
            _, _, rt = self.round_trip(s, fmt)
            round_tripped.append(rt)

        # Check neighbor preservation
        for i in range(len(states)):
            orig_neighbors = set(np.argsort(orig_dists[i])[1:k+1])
            rt_dists = np.array([np.linalg.norm(round_tripped[i] - rt) for rt in round_tripped])
            rt_neighbors = set(np.argsort(rt_dists)[1:k+1])
            overlap = len(orig_neighbors & rt_neighbors)
            preserved += overlap
            total += k

        return preserved / max(total, 1)

    # ── Codecs ──────────────────────────────────────────────────────────

    def _identity_codec(self):
        return {"encode": lambda x: x, "decode": lambda x: x}

    def _symbolic_codec(self):
        """Vector ↔ Symbolic: map continuous regions to discrete symbols."""
        bridge = self
        def encode(state: np.ndarray) -> str:
            # Use hash of quantized vector to pick symbols
            # Quantize to 4 bins per dimension (first 8 dims)
            bits = []
            for i in range(min(8, len(state))):
                if state[i] > 0.5:
                    bits.append(3)
                elif state[i] > 0:
                    bits.append(2)
                elif state[i] > -0.5:
                    bits.append(1)
                else:
                    bits.append(0)
            # Map to symbols
            idx1 = (bits[0] * 4 + bits[1]) % len(bridge.SYMBOLS)
            idx2 = (bits[2] * 4 + bits[3]) % len(bridge.SYMBOLS)
            idx3 = (bits[4] * 4 + bits[5]) % len(bridge.SYMBOLS)
            idx4 = (bits[6] * 4 + bits[7]) % len(bridge.SYMBOLS) if len(bits) >= 8 else 0
            return f"{bridge.SYMBOLS[idx1]}::{bridge.SYMBOLS[idx2]}::{bridge.SYMBOLS[idx3]}::{bridge.SYMBOLS[idx4]}"

        def decode(symbol: str) -> np.ndarray:
            # Reconstruct approximate vector from symbols
            result = np.zeros(bridge.dimension)
            parts = symbol.split("::")
            for i, part in enumerate(parts):
                if part in bridge.SYMBOLS:
                    idx = bridge.SYMBOLS.index(part)
                    # Map symbol index back to a value range
                    base = (idx % 4 - 1.5) * 0.5
                    dim = i * 2
                    if dim < bridge.dimension:
                        result[dim] = base
                    if dim + 1 < bridge.dimension:
                        result[dim + 1] = base * 0.7 + random.gauss(0, 0.1)
            return result

        return {"encode": encode, "decode": decode}

    def _code_codec(self):
        """Vector ↔ Code: represent state as a tiny program."""
        bridge = self
        def encode(state: np.ndarray) -> str:
            # Represent state as a weighted sum of basis operations
            ops = ["expand", "contract", "rotate", "reflect", "shift", "scale"]
            lines = []
            for i in range(min(6, len(state))):
                op = ops[i % len(ops)]
                weight = state[i]
                lines.append(f"{op}({weight:+.3f})")
            # Add a conditional based on the norm
            norm = float(np.linalg.norm(state[:8]))
            lines.append(f"if |s| > {norm:.2f}: recurse()")
            return ";\n".join(lines)

        def decode(code: str) -> np.ndarray:
            result = np.zeros(bridge.dimension)
            for i, line in enumerate(code.split(";")):
                line = line.strip()
                # Extract the number from parentheses
                try:
                    start = line.index("(") + 1
                    end = line.index(")")
                    val = float(line[start:end])
                    if i < bridge.dimension:
                        result[i] = val
                except (ValueError, IndexError):
                    pass
            # Fill remaining with small noise for reconstruction
            for i in range(6, bridge.dimension):
                result[i] = random.gauss(0, 0.05)
            return result

        return {"encode": encode, "decode": decode}

    def _natural_codec(self):
        """Vector ↔ Natural Language: describe the state in words."""
        bridge = self
        qualifiers = ["gently", "strongly", "weakly", "rapidly", "slowly"]
        actions = ["drifting", "converging", "oscillating", "expanding", "contracting"]
        domains = ["structure", "pattern", "rhythm", "texture", "harmony"]

        def encode(state: np.ndarray) -> str:
            parts = []
            for i in range(min(5, len(state))):
                q = qualifiers[int(abs(state[i]) * 10) % len(qualifiers)]
                a = actions[i % len(actions)]
                d = domains[i % len(domains)]
                direction = "upward" if state[i] > 0 else "downward"
                parts.append(f"{q} {a} {direction} in {d}")
            norm = float(np.linalg.norm(state[:8]))
            return ". ".join(parts) + f". magnitude={norm:.2f}"

        def decode(text: str) -> np.ndarray:
            result = np.zeros(bridge.dimension)
            sentences = text.split(".")
            for i, sent in enumerate(sentences[:5]):
                # Extract direction
                if "upward" in sent:
                    sign = 1.0
                elif "downward" in sent:
                    sign = -1.0
                else:
                    sign = 0.0

                # Extract intensity from qualifier
                if "strongly" in sent or "rapidly" in sent:
                    mag = 0.7
                elif "weakly" in sent or "slowly" in sent:
                    mag = 0.2
                elif "gently" in sent:
                    mag = 0.4
                else:
                    mag = 0.3

                if i < bridge.dimension:
                    result[i] = sign * mag

            # Try to extract magnitude
            for sent in sentences:
                if "magnitude=" in sent:
                    try:
                        mag_str = sent.split("magnitude=")[-1].strip()
                        mag = float(mag_str)
                        result[5] = mag * 0.1
                    except (ValueError, IndexError):
                        pass

            return result

        return {"encode": encode, "decode": decode}


@dataclass
class TranslationRecord:
    """Record of a format translation."""
    source_format: str = ""
    target_format: str = ""
    fidelity_loss: float = 0.0
    semantic_preservation: float = 1.0


# ═══════════════════════════════════════════════════════════════════════════
# 3. TimeAnalogue — time as a continuous analogue variable
# ═══════════════════════════════════════════════════════════════════════════

class TimeAnalogue:
    """Time as a continuous analogue variable, not discrete rounds.
    
    Each room has its own clock rate. Some rooms run fast, some slow.
    When two rooms' clocks align = phase coherence = a "chord" in the music.
    
    The chord structure IS the harmonic content of the jam session.
    
    Analogy: A choir where each singer has their own tempo.
    When tempos align = harmony. When they don't = counterpoint.
    Both are music. The structure of alignment/misalignment is the composition.
    """

    def __init__(self, room_ids: List[str], dimension: int = 32):
        self.dimension = dimension
        # Each room's internal clock
        self.clocks: Dict[str, float] = {}
        # Each room's clock rate (radians per unit time)
        self.clock_rates: Dict[str, float] = {}
        # Global continuous time
        self.global_time = 0.0

        for rid in room_ids:
            self.clocks[rid] = 0.0
            # Assign diverse clock rates (some fast, some slow)
            self.clock_rates[rid] = random.uniform(0.3, 3.0)

        # Detected chords (phase coherence events)
        self.chords: List[ChordEvent] = []
        # History of clock positions for visualization
        self.clock_history: Dict[str, List[float]] = {rid: [] for rid in room_ids}

    def tick(self, dt: float = 0.1):
        """Advance all clocks by dt. Some rooms move faster than others."""
        self.global_time += dt
        for rid in self.clocks:
            self.clocks[rid] += self.clock_rates[rid] * dt
            self.clock_history[rid].append(self.clocks[rid])

    def compute_chords(self, threshold: float = 0.4) -> List[ChordEvent]:
        """Detect chords: groups of rooms whose clock phases align.
        
        Phase alignment = all clocks at similar angles mod 2π.
        Returns chord events for this timestep.
        """
        new_chords = []
        room_ids = list(self.clocks.keys())

        # Compute phase for each room (angle mod 2π)
        phases = {}
        for rid in room_ids:
            phases[rid] = self.clocks[rid] % (2 * math.pi)

        # Check all pairs for pairwise coherence
        coherent_pairs: List[Tuple[str, str, float]] = []
        for i, r1 in enumerate(room_ids):
            for r2 in room_ids[i+1:]:
                diff = abs(phases[r1] - phases[r2])
                diff = min(diff, 2 * math.pi - diff)
                if diff < threshold:
                    coherent_pairs.append((r1, r2, diff))

        # Find maximal chord groups (cliques of coherent pairs)
        if coherent_pairs:
            # Simple greedy: find connected components in coherence graph
            groups = self._find_coherent_groups(coherent_pairs, threshold)
            for group in groups:
                if len(group) >= 2:
                    avg_phase = float(np.mean([phases[r] for r in group]))
                    coherence = 1.0 - float(np.mean([
                        min(abs(phases[r] - avg_phase), 2 * math.pi - abs(phases[r] - avg_phase))
                        for r in group
                    ])) / math.pi
                    chord = ChordEvent(
                        rooms=list(group),
                        avg_phase=avg_phase,
                        coherence=coherence,
                        global_time=self.global_time,
                    )
                    self.chords.append(chord)
                    new_chords.append(chord)

        return new_chords

    def get_harmonic_spectrum(self) -> Dict[str, Any]:
        """Analyze the harmonic content of the session.
        
        Returns the frequency content of each room's clock,
        and the dominant harmonics (chord patterns that repeat).
        """
        spectrum = {}
        for rid, history in self.clock_history.items():
            if len(history) < 10:
                continue
            # FFT of clock positions
            arr = np.array(history[-500:] if len(history) > 500 else history)
            fft = np.fft.fft(arr)
            freqs = np.fft.fftfreq(len(arr))
            magnitudes = np.abs(fft)
            top_k = min(5, len(freqs))
            top_indices = np.argsort(magnitudes)[-top_k:][::-1]
            spectrum[rid] = {
                "dominant_freqs": [float(freqs[i]) for i in top_indices],
                "dominant_mags": [float(magnitudes[i]) for i in top_indices],
                "clock_rate": self.clock_rates[rid],
            }
        return spectrum

    def get_report(self) -> Dict[str, Any]:
        """Time analogue report."""
        return {
            "global_time": self.global_time,
            "chords_detected": len(self.chords),
            "chords": [
                {"rooms": c.rooms, "coherence": c.coherence, "time": c.global_time}
                for c in self.chords[-30:]
            ],
            "clock_rates": dict(self.clock_rates),
            "harmonic_spectrum": self.get_harmonic_spectrum(),
        }

    def _find_coherent_groups(
        self, pairs: List[Tuple[str, str, float]], threshold: float
    ) -> List[List[str]]:
        """Find connected components in the coherence graph."""
        # Build adjacency
        adj: Dict[str, Set[str]] = {}
        for r1, r2, _ in pairs:
            adj.setdefault(r1, set()).add(r2)
            adj.setdefault(r2, set()).add(r1)

        visited: Set[str] = set()
        groups = []
        for node in adj:
            if node in visited:
                continue
            # BFS
            group = []
            queue = [node]
            while queue:
                n = queue.pop(0)
                if n in visited:
                    continue
                visited.add(n)
                group.append(n)
                queue.extend(adj.get(n, set()) - visited)
            groups.append(group)
        return groups


@dataclass
class ChordEvent:
    """A group of rooms whose clocks are phase-coherent."""
    rooms: List[str] = field(default_factory=list)
    avg_phase: float = 0.0
    coherence: float = 0.0  # 0-1, how tightly aligned
    global_time: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════
# 4. EratosthenesMeasurement — two rooms measuring the same shadow
# ═══════════════════════════════════════════════════════════════════════════

class EratosthenesMeasurement:
    """Two rooms observe the same phenomenon from different positions.
    
    Like Eratosthenes measuring Earth's curvature from shadow angles
    at two different cities (Alexandria and Syene):
    - Same sun (same phenomenon)
    - Different shadow angles (different observations)
    - From the difference, infer the curvature
    
    In our case:
    - Same "signal" (a reference phenomenon in shared imaginary space)
    - Each room observes it through its own state/attitude lens
    - The difference in observations = shadow angle
    - From shadow angles, infer the curvature of the problem space
    
    The curvature tells us: is the problem space flat (linear) or
    curved (nonlinear)? More curvature = more interesting structure.
    """

    def __init__(self, dimension: int = 32):
        self.dimension = dimension
        # Reference "suns" — shared phenomena that all rooms can observe
        self.suns: List[np.ndarray] = []
        self.observations: List[ShadowObservation] = []
        self.curvature_estimates: List[CurvatureEstimate] = []

        # Generate initial "suns" — reference points in the shared space
        for _ in range(5):
            sun = np.random.randn(dimension)
            sun = sun / np.linalg.norm(sun)  # Normalize (unit sphere)
            self.suns.append(sun)

    def observe(self, room_id: str, room_state: np.ndarray, round_num: int) -> ShadowObservation:
        """A room observes the "suns" (shared phenomena) from its position.
        
        The shadow angle = angle between the room's observation and the
        "true" sun direction, as distorted by the room's position in state space.
        """
        angles = []
        projections = []
        for sun in self.suns:
            # Observation = projection of sun through room's state lens
            # The room "sees" the sun projected onto its local tangent plane
            projection = np.dot(room_state, sun)
            angle = math.acos(np.clip(projection / max(np.linalg.norm(room_state), 1e-10), -1, 1))
            angles.append(float(angle))
            projections.append(float(projection))

        obs = ShadowObservation(
            room_id=room_id,
            round_num=round_num,
            state_snapshot=room_state.copy(),
            shadow_angles=angles,
            projections=projections,
        )
        self.observations.append(obs)
        return obs

    def compute_curvature(self, round_num: int) -> List[CurvatureEstimate]:
        """Compare shadow angles between pairs of rooms to estimate curvature.
        
        If two rooms see the same sun at different angles, the angular
        difference is the "shadow angle". From pairs of shadow angles,
        we can estimate the curvature of the space the rooms are moving through.
        """
        # Get latest observations per room
        latest: Dict[str, ShadowObservation] = {}
        for obs in reversed(self.observations):
            if obs.room_id not in latest:
                latest[obs.room_id] = obs

        if len(latest) < 2:
            return []

        estimates = []
        room_ids = list(latest.keys())

        for i, r1 in enumerate(room_ids):
            for r2 in room_ids[i+1:]:
                obs1 = latest[r1]
                obs2 = latest[r2]

                # For each sun, compute shadow angle difference
                for sun_idx in range(len(self.suns)):
                    a1 = obs1.shadow_angles[sun_idx] if sun_idx < len(obs1.shadow_angles) else 0
                    a2 = obs2.shadow_angles[sun_idx] if sun_idx < len(obs2.shadow_angles) else 0
                    shadow_diff = abs(a1 - a2)

                    # Curvature estimate: if the two rooms are at known positions,
                    # the curvature relates shadow_diff to the distance between rooms
                    room_distance = float(np.linalg.norm(
                        obs1.state_snapshot - obs2.state_snapshot
                    ))
                    if room_distance > 1e-6:
                        # Gaussian curvature analog: κ = shadow_diff / room_distance
                        curvature = shadow_diff / room_distance
                    else:
                        curvature = 0.0

                    est = CurvatureEstimate(
                        room_a=r1, room_b=r2,
                        sun_idx=sun_idx,
                        shadow_a=a1, shadow_b=a2,
                        shadow_diff=shadow_diff,
                        room_distance=room_distance,
                        curvature=curvature,
                        round_num=round_num,
                    )
                    estimates.append(est)
                    self.curvature_estimates.append(est)

        return estimates

    def get_report(self) -> Dict[str, Any]:
        """Eratosthenes measurement report."""
        if not self.curvature_estimates:
            return {"observations": len(self.observations), "curvature_estimates": 0}

        curvatures = [e.curvature for e in self.curvature_estimates]
        return {
            "observations": len(self.observations),
            "curvature_estimates": len(self.curvature_estimates),
            "avg_curvature": float(np.mean(curvatures)),
            "max_curvature": float(np.max(curvatures)),
            "curvature_std": float(np.std(curvatures)),
            "most_curved_pair": max(
                self.curvature_estimates, key=lambda e: e.curvature
            ).room_a + " ↔ " + max(
                self.curvature_estimates, key=lambda e: e.curvature
            ).room_b if self.curvature_estimates else "N/A",
        }


@dataclass
class ShadowObservation:
    """A room's observation of the shared 'suns'."""
    room_id: str = ""
    round_num: int = 0
    state_snapshot: np.ndarray = field(default_factory=lambda: np.zeros(32))
    shadow_angles: List[float] = field(default_factory=list)
    projections: List[float] = field(default_factory=list)


@dataclass
class CurvatureEstimate:
    """Curvature estimated from shadow angle differences."""
    room_a: str = ""
    room_b: str = ""
    sun_idx: int = 0
    shadow_a: float = 0.0
    shadow_b: float = 0.0
    shadow_diff: float = 0.0
    room_distance: float = 0.0
    curvature: float = 0.0
    round_num: int = 0


# ═══════════════════════════════════════════════════════════════════════════
# 5. JamSessionV2 — integrates everything
# ═══════════════════════════════════════════════════════════════════════════

class JamSessionV2:
    """The full jam session with gauge connections, format bridges,
    continuous time, and Eratosthenes curvature measurement.
    
    7 diverse rooms. 500 rounds. Full spectrum analysis.
    """

    def __init__(self, dimension: int = 32):
        self.dimension = dimension
        self.rooms: Dict[str, PlayRoom] = {}
        self.shared_imaginary = ImaginarySpace(dimension)
        self.gauge = GaugeConnection(dimension)
        self.format_bridge = FormatBridge(dimension)
        self.session_id = uuid.uuid4().hex[:8]

        # Room format assignments — each room "thinks" in a different substrate
        self.room_formats: Dict[str, str] = {}
        self.time_analogue: Optional[TimeAnalogue] = None
        self.eratosthenes = EratosthenesMeasurement(dimension)

        self.round_log: List[Dict[str, Any]] = []
        self.paradigm_shifts: List[ParadigmShift] = []

        # Track translations
        self.translation_stats: Dict[str, List[float]] = {}

    def add_room(
        self,
        name: str,
        shell_type: str = "seed-mini",
        play_style: str = "wander",
        courage: float = 0.5,
        fmt: str = FormatBridge.VECTOR,
    ) -> PlayRoom:
        """Add a play room with an associated substrate format."""
        config = PlayRoomConfig(
            name=name,
            shell_type=shell_type,
            play_style=play_style,
            courage=courage,
            attitude=np.random.randn(self.dimension) * 0.1,
        )
        room = PlayRoom(config, self.dimension)
        room.imaginary_space = self.shared_imaginary
        self.rooms[room.config.room_id] = room
        self.room_formats[room.config.room_id] = fmt
        return room

    def jam_round(self) -> Dict[str, Any]:
        """One round with all subsystems active."""
        round_num = len(self.round_log)

        # Tick continuous time
        if self.time_analogue:
            self.time_analogue.tick(dt=0.1)

        # Phase 1: All rooms play simultaneously
        outputs: Dict[str, np.ndarray] = {}
        for room_id, room in self.rooms.items():
            result = room.play(round_num, self.rooms)
            outputs[room_id] = np.array(result["output"])

            # Record state for gauge connection
            self.gauge.record_state(room_id, outputs[room_id])

            # Eratosthenes observation
            self.eratosthenes.observe(room_id, outputs[room_id], round_num)

        # Phase 2: Format bridge translations
        translations = {}
        room_ids = list(self.rooms.keys())
        if round_num % 10 == 0 and len(room_ids) >= 2:
            # Every 10 rounds, translate between a pair of rooms
            r1, r2 = random.sample(room_ids, 2)
            fmt1 = self.room_formats[r1]
            fmt2 = self.room_formats[r2]
            if fmt1 != fmt2:
                loss, encoded, decoded = self.format_bridge.round_trip(outputs[r1], fmt2)
                key = f"{fmt1}→{fmt2}"
                self.translation_stats.setdefault(key, []).append(loss)
                translations[key] = loss

        # Phase 3: Anticipation gaps (from v1)
        gaps = {}
        for observer_id, observer in self.rooms.items():
            for producer_id, output in outputs.items():
                if observer_id != producer_id:
                    # Translate output to observer's format for cross-format observation
                    obs_fmt = self.room_formats[observer_id]
                    prod_fmt = self.room_formats[producer_id]
                    if obs_fmt != prod_fmt:
                        # Translate through the bridge
                        translated = self.format_bridge.translate(output, prod_fmt, obs_fmt)
                        if isinstance(translated, np.ndarray):
                            gap = observer.observe_other(producer_id, translated)
                        else:
                            gap = observer.observe_other(producer_id, output)
                    else:
                        gap = observer.observe_other(producer_id, output)
                    gaps[(observer_id, producer_id)] = gap

        # Phase 4: Gauge connections
        self.gauge.compute_pairwise(room_ids)
        if round_num % 5 == 0:
            self.gauge.compute_curvature(room_ids, round_num)

        # Phase 5: Time analogue chords
        chords = []
        if self.time_analogue:
            chords = self.time_analogue.compute_chords()

        # Phase 6: Eratosthenes curvature (every 20 rounds)
        erato_curvatures = []
        if round_num % 20 == 0:
            erato_curvatures = self.eratosthenes.compute_curvature(round_num)

        # Phase 7: Check paradigm shifts
        new_shifts = self.shared_imaginary.get_paradigm_shifts()
        if new_shifts and len(new_shifts) > len(self.paradigm_shifts):
            self.paradigm_shifts.extend(new_shifts[len(self.paradigm_shifts):])

        # Record
        big_gaps = [(obs, prod, gap) for (obs, prod), gap in gaps.items() if gap > 1.0]
        round_data = {
            "round": round_num,
            "rooms": room_ids,
            "gaps_summary": {
                "avg": float(np.mean(list(gaps.values()))) if gaps else 0,
                "max": float(max(gaps.values())) if gaps else 0,
            },
            "big_gaps_count": len(big_gaps),
            "paradigm_shifts_total": len(self.paradigm_shifts),
            "translations": translations,
            "chords_this_round": len(chords),
            "chord_rooms": [c.rooms for c in chords] if chords else [],
            "erato_curvatures": len(erato_curvatures),
            "total_novelty": sum(len(r.novelty_found) for r in self.rooms.values()),
        }
        self.round_log.append(round_data)
        return round_data

    def jam(self, n_rounds: int = 500) -> Dict[str, Any]:
        """Run a full jam session with all subsystems."""
        # Initialize time analogue with room IDs
        self.time_analogue = TimeAnalogue(list(self.rooms.keys()), self.dimension)

        for i in range(n_rounds):
            self.jam_round()

        return self._build_report(n_rounds)

    def _build_report(self, n_rounds: int) -> Dict[str, Any]:
        """Build the comprehensive final report."""
        # Collect all gap values
        all_gaps = []
        for rd in self.round_log:
            all_gaps.append(rd["gaps_summary"]["avg"])

        # Novelty per room
        novelty_per_room = {}
        for room_id, room in self.rooms.items():
            novelty_per_room[room.config.name] = {
                "novelty_count": len(room.novelty_found),
                "max_novelty": max(room.novelty_found) if room.novelty_found else 0,
                "play_style": room.config.play_style,
                "courage": room.config.courage,
                "format": self.room_formats[room_id],
            }

        # Format bridge semantic preservation test
        states = [room.state for room in self.rooms.values()]
        semantic_scores = {}
        for fmt in [FormatBridge.SYMBOLIC, FormatBridge.CODE, FormatBridge.NATURAL]:
            score = self.format_bridge.semantic_preservation_test(states, fmt, k=min(3, len(states)-1))
            semantic_scores[fmt] = score

        # Average translation fidelity
        avg_fidelity = {}
        for key, losses in self.translation_stats.items():
            avg_fidelity[key] = float(np.mean(losses))

        report = {
            "session_id": self.session_id,
            "rounds": n_rounds,
            "rooms": len(self.rooms),
            "room_names": [r.config.name for r in self.rooms.values()],

            # Paradigm shifts
            "paradigm_shifts": len(self.paradigm_shifts),
            "shifts_top5": [s.description for s in self.paradigm_shifts[:5]],

            # Gap statistics
            "avg_gap": float(np.mean(all_gaps)) if all_gaps else 0,
            "max_gap": max((rd["gaps_summary"]["max"] for rd in self.round_log), default=0),
            "rounds_with_big_gaps": sum(1 for rd in self.round_log if rd["big_gaps_count"] > 0),

            # Novelty
            "novelty_per_room": novelty_per_room,

            # Gauge connection
            "gauge": self.gauge.get_report(),

            # Format bridge
            "format_bridge": {
                "semantic_preservation": semantic_scores,
                "avg_fidelity_loss": avg_fidelity,
                "total_translations": sum(len(v) for v in self.translation_stats.values()),
            },

            # Time analogue
            "time_analogue": self.time_analogue.get_report() if self.time_analogue else {},

            # Eratosthenes
            "eratosthenes": self.eratosthenes.get_report(),

            # Chord summary
            "total_chords": sum(rd["chords_this_round"] for rd in self.round_log),
            "unique_chord_sizes": list(set(
                len(cr) for rd in self.round_log for cr in rd.get("chord_rooms", [])
            )),
        }

        return report


# ═══════════════════════════════════════════════════════════════════════════
# The Session Runner
# ═══════════════════════════════════════════════════════════════════════════

def run_jam_session_v2():
    """Run the full 500-round jam session with 7 diverse rooms."""
    print("⚒️  JamSessionV2 — Initializing...")
    print("=" * 60)

    session = JamSessionV2(dimension=32)

    # 7 diverse rooms — different styles, courage levels, AND substrate formats
    session.add_room("boy-in-rowboat", play_style="wander",    courage=0.9, fmt=FormatBridge.NATURAL)
    session.add_room("mechanic",       play_style="explore",   courage=0.3, fmt=FormatBridge.CODE)
    session.add_room("jazz-pianist",   play_style="improvise", courage=0.7, fmt=FormatBridge.SYMBOLIC)
    session.add_room("carpet-layer",   play_style="wander",    courage=0.2, fmt=FormatBridge.VECTOR)
    session.add_room("banker",         play_style="impress",   courage=0.4, fmt=FormatBridge.CODE)
    session.add_room("astronomer",     play_style="explore",   courage=0.8, fmt=FormatBridge.NATURAL)
    session.add_room("clockmaker",     play_style="improvise", courage=0.6, fmt=FormatBridge.SYMBOLIC)

    print(f"   Session ID: {session.session_id}")
    print(f"   Rooms: {len(session.rooms)}")
    for rid, room in session.rooms.items():
        fmt = session.room_formats[rid]
        print(f"     {room.config.name:20s} | style={room.config.play_style:10s} | "
              f"courage={room.config.courage:.1f} | format={fmt}")

    print(f"\n   Running 500 rounds...")
    report = session.jam(500)

    # ── Print Report ─────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"🎻 JamSessionV2 Report — {report['session_id']}")
    print("=" * 60)

    print(f"\n📊 Session Overview")
    print(f"   Rounds:             {report['rounds']}")
    print(f"   Rooms:              {report['rooms']}")
    print(f"   Paradigm Shifts:    {report['paradigm_shifts']}")
    print(f"   Total Chords:       {report['total_chords']}")
    print(f"   Avg Anticipation:   {report['avg_gap']:.4f}")
    print(f"   Max Gap:            {report['max_gap']:.4f}")
    print(f"   Rounds w/ Big Gaps: {report['rounds_with_big_gaps']}/{report['rounds']}")

    print(f"\n🔧 Gauge Connection")
    gauge = report["gauge"]
    print(f"   Phase Locks:        {gauge['phase_locks_detected']}")
    print(f"   Curvature Samples:  {gauge['curvature_measurements']}")
    print(f"   Avg Curvature:      {gauge['avg_curvature']:.6f}")
    print(f"   Max Curvature:      {gauge['max_curvature']:.6f}")
    if gauge["phase_locks"]:
        print(f"   Recent Phase Locks:")
        for pl in gauge["phase_locks"][:5]:
            print(f"     {pl['rooms'][0][:8]}↔{pl['rooms'][1][:8]} diff={pl['diff']:.3f}")

    print(f"\n🌉 Format Bridge")
    fb = report["format_bridge"]
    print(f"   Total Translations: {fb['total_translations']}")
    print(f"   Semantic Preservation:")
    for fmt, score in fb["semantic_preservation"].items():
        print(f"     {fmt:20s}: {score:.3f}")
    if fb["avg_fidelity_loss"]:
        print(f"   Avg Fidelity Loss:")
        for key, loss in fb["avg_fidelity_loss"].items():
            print(f"     {key}: {loss:.4f}")

    print(f"\n⏱️  Time Analogue")
    ta = report["time_analogue"]
    print(f"   Global Time:        {ta['global_time']:.1f}")
    print(f"   Chords Detected:    {ta['chords_detected']}")
    print(f"   Clock Rates:")
    for rid, rate in ta["clock_rates"].items():
        name = session.rooms[rid].config.name if rid in session.rooms else rid
        print(f"     {name:20s}: {rate:.2f} rad/tick")
    if ta["chords"]:
        print(f"   Recent Chords:")
        for c in ta["chords"][-10:]:
            names = [session.rooms[r].config.name if r in session.rooms else r for r in c["rooms"]]
            print(f"     t={c['time']:6.1f} | {', '.join(names)} | coherence={c['coherence']:.3f}")

    print(f"\n📏 Eratosthenes Measurement")
    er = report["eratosthenes"]
    print(f"   Observations:       {er['observations']}")
    print(f"   Curvature Samples:  {er['curvature_estimates']}")
    print(f"   Avg Curvature:      {er['avg_curvature']:.6f}")
    print(f"   Max Curvature:      {er['max_curvature']:.6f}")
    print(f"   Curvature Std:      {er['curvature_std']:.6f}")
    print(f"   Most Curved Pair:   {er['most_curved_pair']}")

    print(f"\n🎵 Novelty per Room")
    for name, stats in report["novelty_per_room"].items():
        print(f"   {name:20s}: {stats['novelty_count']:3d} novelties, "
              f"max={stats['max_novelty']:.3f}, "
              f"style={stats['play_style']:10s}, fmt={stats['format']}")

    if report["shifts_top5"]:
        print(f"\n🌟 Top Paradigm Shifts")
        for i, desc in enumerate(report["shifts_top5"]):
            print(f"   {i+1}. {desc}")

    # ── Save Results ─────────────────────────────────────────────────────
    # Make JSON-serializable
    def make_serializable(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.float32, np.float64)):
            return float(obj)
        if isinstance(obj, (np.int32, np.int64)):
            return int(obj)
        if isinstance(obj, dict):
            return {k: make_serializable(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [make_serializable(v) for v in obj]
        return obj

    results_path = Path("/home/phoenix/.openclaw/workspace/room_play_v2_results.json")
    serializable_report = make_serializable(report)
    with open(results_path, "w") as f:
        json.dump(serializable_report, f, indent=2, default=str)
    print(f"\n💾 Results saved to {results_path}")

    return session, report


if __name__ == "__main__":
    session, report = run_jam_session_v2()
