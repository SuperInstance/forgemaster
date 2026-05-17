#!/usr/bin/env python3
"""
combo_architecture.py — Rooms That Play Together with Time as an Analogue Variable
====================================================================================

Builds on room_play.py (ImaginarySpace, Anticipation, PlayRoom, JamSession).

New architecture:
    AnalogueTime       — continuous time with per-room dilation
    SharedSubstrate    — temporal consensus + subjective experience
    TemporalCoupling   — measure how rooms' proper times relate
    Experiment         — 5 rooms, 200 rounds, γ+H tracking

Key insight: time isn't a clock tick. It's a continuous variable each room
experiences differently. Correct anticipation → time dilates (room processes
more). Surprise → time contracts (room reacts faster). The coupling between
these temporal flows might conserve something — and that something is γ+H.
"""

import sys
import os
import json
import math
import time as _time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Pull in the base classes from room_play.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from room_play import (
    ImaginarySpace, Anticipation, PlayRoom, PlayRoomConfig,
    JamSession, ImaginaryResult, WhatIf, ParadigmShift,
)


# ---------------------------------------------------------------------------
# 1. AnalogueTime — continuous time with per-room dilation
# ---------------------------------------------------------------------------

class AnalogueTime:
    """Time flows continuously. Each room experiences it at its own rate.
    
    Physics analogy: proper time in general relativity. Each room is an
    observer in its own gravitational well. Correct anticipation = deep well
    = time dilation = room processes more per consensus tick. Surprise =
    shallow well = time contracts = room reacts faster but processes less.
    
    gamma_factor > 1 means dilation (slow proper time, deep processing).
    gamma_factor < 1 means contraction (fast proper time, fast reaction).
    """

    def __init__(self, room_id: str, initial_rate: float = 1.0):
        self.room_id = room_id
        self.proper_time = 0.0          # accumulated subjective time
        self.gamma_factor = initial_rate  # time dilation factor (1.0 = consensus)
        self.rate_history: List[Tuple[float, float]] = []  # (consensus_time, gamma)
        self.surprise_history: List[float] = []
        self._alpha = 0.08  # smoothing for gamma updates

    def tick(self, consensus_dt: float, surprise: float) -> float:
        """Advance one consensus tick. Return the room's proper time delta.
        
        surprise > 0: room was surprised → gamma contracts (speeds up)
        surprise < 0: room anticipated correctly → gamma dilates (slows, processes more)
        surprise ≈ 0: neutral → gamma drifts toward 1.0
        """
        # Update gamma based on surprise
        # Positive surprise → contraction (gamma decreases)
        # Negative surprise (correct anticipation) → dilation (gamma increases)
        target_gamma = 1.0 + self._alpha * (-surprise)  # negative surprise → higher gamma
        target_gamma = max(0.2, min(3.0, target_gamma))  # clamp
        
        # Smooth update
        self.gamma_factor = 0.85 * self.gamma_factor + 0.15 * target_gamma
        
        # Proper time advances at gamma-adjusted rate
        proper_dt = consensus_dt * self.gamma_factor
        self.proper_time += proper_dt
        
        # Record
        self.rate_history.append((self.proper_time, self.gamma_factor))
        self.surprise_history.append(surprise)
        
        return proper_dt

    @property
    def current_rate(self) -> float:
        return self.gamma_factor

    def summary(self) -> Dict[str, Any]:
        gammas = [g for _, g in self.rate_history]
        return {
            "room_id": self.room_id,
            "proper_time": round(self.proper_time, 4),
            "current_gamma": round(self.gamma_factor, 4),
            "mean_gamma": round(float(np.mean(gammas)), 4) if gammas else 1.0,
            "std_gamma": round(float(np.std(gammas)), 4) if gammas else 0.0,
            "min_gamma": round(min(gammas), 4) if gammas else 1.0,
            "max_gamma": round(max(gammas), 4) if gammas else 1.0,
        }


# ---------------------------------------------------------------------------
# 2. SharedSubstrate — temporal consensus + subjective experience
# ---------------------------------------------------------------------------

class SharedSubstrate:
    """Multiple rooms play on a shared temporal substrate.
    
    The substrate has a "now" that all rooms agree on (consensus time).
    But each room's EXPERIENCE of now is subjective (proper time).
    Rooms communicate through the substrate, not directly.
    
    Evolved from JamSession: adds the temporal dimension.
    """

    def __init__(self, dimension: int = 32, consensus_dt: float = 1.0):
        self.dimension = dimension
        self.consensus_time = 0.0
        self.consensus_dt = consensus_dt
        self.rooms: Dict[str, PlayRoom] = {}
        self.room_times: Dict[str, AnalogueTime] = {}
        self.shared_imaginary = ImaginarySpace(dimension)
        self.substrate_state = np.zeros(dimension)  # collective field
        self.round_log: List[Dict[str, Any]] = []
        self.coupling_history: List[np.ndarray] = []

    def add_room(self, name: str, shell_type: str = "seed-mini",
                 play_style: str = "wander", courage: float = 0.5,
                 time_rate: float = 1.0) -> Tuple[PlayRoom, AnalogueTime]:
        """Add a room to the substrate with its own temporal clock."""
        config = PlayRoomConfig(
            name=name,
            shell_type=shell_type,
            play_style=play_style,
            courage=courage,
            attitude=np.random.randn(self.dimension) * 0.1,
        )
        room = PlayRoom(config, self.dimension)
        room.imaginary_space = self.shared_imaginary

        atime = AnalogueTime(config.room_id, initial_rate=time_rate)

        self.rooms[config.room_id] = room
        self.room_times[config.room_id] = atime
        return room, atime

    def substrate_round(self) -> Dict[str, Any]:
        """One round on the shared temporal substrate.
        
        1. All rooms play (simultaneous in consensus time)
        2. Each room's output contributes to substrate state
        3. Rooms observe each other through the substrate
        4. Surprise computed from anticipation gaps
        5. Each room's proper time advances with its gamma factor
        """
        round_num = len(self.round_log)
        self.consensus_time += self.consensus_dt

        # Phase 1: All rooms play
        outputs: Dict[str, np.ndarray] = {}
        for room_id, room in self.rooms.items():
            result = room.play(round_num, self.rooms)
            outputs[room_id] = np.array(result["output"])

        # Phase 2: Update substrate state (weighted average of all outputs)
        output_stack = np.stack(list(outputs.values()))
        self.substrate_state = 0.8 * self.substrate_state + 0.2 * np.mean(output_stack, axis=0)

        # Phase 3: Rooms observe each other through substrate → compute surprise
        surprises: Dict[str, float] = {}
        gaps: Dict[Tuple[str, str], float] = {}
        for observer_id, observer in self.rooms.items():
            total_surprise = 0.0
            for producer_id, output in outputs.items():
                if observer_id != producer_id:
                    gap = observer.observe_other(producer_id, output)
                    gaps[(observer_id, producer_id)] = gap
                    total_surprise += gap
            surprises[observer_id] = total_surprise / max(len(self.rooms) - 1, 1)

        # Phase 4: Advance each room's proper time based on surprise
        proper_times: Dict[str, float] = {}
        for room_id, atime in self.room_times.items():
            surprise = surprises.get(room_id, 0.0)
            pt = atime.tick(self.consensus_dt, surprise)
            proper_times[room_id] = pt

        # Phase 5: Compute temporal coupling matrix
        coupling = self._compute_coupling()

        round_data = {
            "round": round_num,
            "consensus_time": round(self.consensus_time, 4),
            "proper_times": {rid: round(pt, 4) for rid, pt in proper_times.items()},
            "surprises": {rid: round(s, 4) for rid, s in surprises.items()},
            "gaps": {f"{obs}→{prod}": round(g, 4) for (obs, prod), g in gaps.items()},
            "substrate_norm": round(float(np.linalg.norm(self.substrate_state)), 4),
        }
        self.round_log.append(round_data)
        return round_data

    def _compute_coupling(self) -> np.ndarray:
        """Compute temporal coupling matrix: how much room i's rate depends on room j's output.
        
        Uses correlation of gamma factors with observed gap magnitudes.
        C[i][j] = correlation(room_i_gamma_history, room_i_gap_from_j_history)
        """
        n = len(self.rooms)
        if n == 0:
            return np.array([[]])
        
        room_ids = list(self.rooms.keys())
        C = np.zeros((n, n))
        
        for i, ri in enumerate(room_ids):
            atime_i = self.room_times[ri]
            if len(atime_i.rate_history) < 3:
                continue
            
            gammas_i = np.array([g for _, g in atime_i.rate_history])
            
            for j, rj in enumerate(room_ids):
                if i == j:
                    # Self-coupling: autocorrelation of gamma
                    if len(gammas_i) > 2:
                        C[i][j] = float(np.corrcoef(gammas_i[:-1], gammas_i[1:])[0, 1])
                    else:
                        C[i][j] = 1.0
                    continue
                
                # Cross-coupling: correlation of room i's gamma with room i's gap from room j
                observer = self.rooms[ri]
                if rj in observer.anticipation.gaps and len(observer.anticipation.gaps[rj]) > 2:
                    gap_hist = np.array(observer.anticipation.gaps[rj])
                    min_len = min(len(gammas_i), len(gap_hist))
                    if min_len > 2:
                        g_i = gammas_i[-min_len:]
                        gap_j = gap_hist[-min_len:]
                        corr = np.corrcoef(g_i, gap_j)[0, 1]
                        C[i][j] = float(corr) if not np.isnan(corr) else 0.0
        
        self.coupling_history.append(C.copy())
        return C

    def run(self, n_rounds: int) -> Dict[str, Any]:
        """Run the substrate for n_rounds."""
        for _ in range(n_rounds):
            self.substrate_round()
        return self.summarize()

    def summarize(self) -> Dict[str, Any]:
        """Summarize the substrate session."""
        room_summaries = {}
        for room_id, room in self.rooms.items():
            atime = self.room_times[room_id]
            room_summaries[room.config.name] = {
                **atime.summary(),
                "play_style": room.config.play_style,
                "courage": room.config.courage,
                "novelty_count": len(room.novelty_found),
                "history_len": len(room.history),
            }
        return {
            "rounds": len(self.round_log),
            "rooms": room_summaries,
            "coupling_matrices": len(self.coupling_history),
        }


# ---------------------------------------------------------------------------
# 3. TemporalCoupling — analysis of temporal relationships
# ---------------------------------------------------------------------------

class TemporalCoupling:
    """Analyze how rooms' proper times relate to each other.
    
    Computes the coupling matrix, its eigenvalues, and tests whether
    the conservation law (γ + H = const) emerges from temporal coupling.
    
    The hypothesis: if rooms are coupled through time (not just through
    outputs), then the TOTAL temporal energy is conserved. This would
    manifest as γ+H being constant across the system, where:
    - γ = sum of coupling eigenvalues (structure)
    - H = entropy of the coupling matrix (randomness)
    """

    def __init__(self, substrate: SharedSubstrate):
        self.substrate = substrate
        self.gamma_plus_H_history: List[Dict[str, float]] = []

    def compute_coupling_spectrum(self, C: np.ndarray) -> Dict[str, Any]:
        """Compute eigenvalues and spectrum of coupling matrix."""
        if C.size == 0:
            return {"eigenvalues": [], "trace": 0, "det": 0}
        
        # Symmetrize for eigenvalue stability
        C_sym = (C + C.T) / 2.0
        eigenvalues = np.linalg.eigvalsh(C_sym)
        trace = float(np.trace(C))
        det = float(np.linalg.det(C)) if C.shape[0] <= 10 else 0.0
        
        return {
            "eigenvalues": sorted([round(float(e), 6) for e in eigenvalues], reverse=True),
            "trace": round(trace, 6),
            "det": round(det, 6),
            "spectral_radius": round(float(max(abs(eigenvalues))), 6),
            "rank": int(np.linalg.matrix_rank(C_sym, tol=1e-6)),
        }

    def compute_entropy(self, C: np.ndarray) -> float:
        """Compute Shannon entropy of the coupling matrix (normalized)."""
        if C.size == 0:
            return 0.0
        
        # Use absolute values, normalize to probability distribution
        abs_C = np.abs(C) + 1e-10  # avoid zeros
        total = abs_C.sum()
        if total < 1e-10:
            return 0.0
        p = abs_C.flatten() / total
        H = -float(np.sum(p * np.log(p)))
        # Normalize by max entropy
        max_H = math.log(len(p)) if len(p) > 1 else 1.0
        return H / max_H if max_H > 0 else 0.0

    def compute_gamma(self, C: np.ndarray) -> float:
        """Compute γ = sum of positive eigenvalues (structure measure)."""
        if C.size == 0:
            return 0.0
        C_sym = (C + C.T) / 2.0
        eigenvalues = np.linalg.eigvalsh(C_sym)
        gamma = float(sum(e for e in eigenvalues if e > 0))
        return gamma

    def analyze_evolution(self) -> Dict[str, Any]:
        """Analyze how γ+H evolves across rounds. Test conservation."""
        if not self.substrate.coupling_history:
            return {"error": "No coupling history"}

        results = []
        for idx, C in enumerate(self.substrate.coupling_history):
            gamma = self.compute_gamma(C)
            H = self.compute_entropy(C)
            spectrum = self.compute_coupling_spectrum(C)
            
            entry = {
                "round": idx,
                "gamma": round(gamma, 6),
                "H": round(H, 6),
                "gamma_plus_H": round(gamma + H, 6),
                "trace": spectrum["trace"],
                "spectral_radius": spectrum["spectral_radius"],
                "eigenvalues": spectrum["eigenvalues"],
            }
            results.append(entry)
            self.gamma_plus_H_history.append(entry)

        # Test conservation: variance of γ+H across rounds
        gpH_values = [r["gamma_plus_H"] for r in results]
        gpH_mean = float(np.mean(gpH_values))
        gpH_std = float(np.std(gpH_values))
        gpH_var = float(np.var(gpH_values))
        
        # Coefficient of variation (lower = more conserved)
        cv = gpH_std / gpH_mean if gpH_mean != 0 else float('inf')
        
        # Trend: is γ+H increasing, decreasing, or stable?
        if len(gpH_values) > 10:
            first_third = np.mean(gpH_values[:len(gpH_values)//3])
            last_third = np.mean(gpH_values[-len(gpH_values)//3:])
            trend = "increasing" if last_third > first_third * 1.05 else \
                    "decreasing" if last_third < first_third * 0.95 else "stable"
        else:
            trend = "insufficient_data"

        # Correlation between γ and H (negative = conservation tradeoff)
        gammas = [r["gamma"] for r in results]
        entropies = [r["H"] for r in results]
        if len(gammas) > 3:
            corr = float(np.corrcoef(gammas, entropies)[0, 1])
        else:
            corr = 0.0

        return {
            "rounds_analyzed": len(results),
            "gamma_plus_H": {
                "mean": round(gpH_mean, 6),
                "std": round(gpH_std, 6),
                "var": round(gpH_var, 6),
                "min": round(min(gpH_values), 6),
                "max": round(max(gpH_values), 6),
                "cv": round(cv, 6),
                "trend": trend,
            },
            "gamma_H_correlation": round(corr, 6),
            "conservation_likely": cv < 0.1,  # CV < 10% suggests conservation
            "early": results[:5] if results else [],
            "mid": results[len(results)//2:len(results)//2+3] if len(results) > 6 else [],
            "late": results[-5:] if len(results) >= 5 else results,
        }

    def final_coupling_matrix(self) -> Optional[np.ndarray]:
        """Return the last coupling matrix."""
        if self.substrate.coupling_history:
            return self.substrate.coupling_history[-1]
        return None


# ---------------------------------------------------------------------------
# 4. Experiment — 5 rooms, 200 rounds
# ---------------------------------------------------------------------------

def run_experiment():
    """Run the combo architecture experiment.
    
    5 PlayRooms with different attitudes, 200 rounds of play.
    Track temporal coupling evolution, compute γ+H.
    """
    print("=" * 70)
    print("COMBO ARCHITECTURE EXPERIMENT")
    print("Rooms playing together with time as an analogue variable")
    print("=" * 70)
    
    np.random.seed(42)  # reproducibility
    
    # Create substrate
    substrate = SharedSubstrate(dimension=32, consensus_dt=1.0)
    
    # 5 rooms with different attitudes (from room_play.py's jam session)
    rooms_config = [
        ("boy-in-rowboat", "wander",    0.9, 1.2),   # adventurous, slightly dilated
        ("mechanic",       "explore",   0.3, 0.8),   # methodical, slightly contracted
        ("jazz-pianist",   "improvise", 0.7, 1.0),   # balanced, nominal rate
        ("carpet-layer",   "wander",    0.2, 0.9),   # steady, slightly contracted
        ("banker",         "impress",   0.4, 1.1),   # strategic, slightly dilated
    ]
    
    for name, style, courage, rate in rooms_config:
        room, atime = substrate.add_room(name, play_style=style, courage=courage, time_rate=rate)
        print(f"  Added room: {name:20s} style={style:12s} courage={courage:.1f} rate={rate:.1f}")
    
    print(f"\n  Running 200 rounds...")
    t0 = _time.time()
    substrate.run(200)
    elapsed = _time.time() - t0
    print(f"  Done in {elapsed:.2f}s")
    
    # Temporal coupling analysis
    print(f"\n{'=' * 70}")
    print("TEMPORAL COUPLING ANALYSIS")
    print("=" * 70)
    
    tc = TemporalCoupling(substrate)
    analysis = tc.analyze_evolution()
    
    gpH = analysis["gamma_plus_H"]
    print(f"\n  γ+H Statistics ({analysis['rounds_analyzed']} coupling snapshots):")
    print(f"    Mean:  {gpH['mean']:.6f}")
    print(f"    Std:   {gpH['std']:.6f}")
    print(f"    CV:    {gpH['cv']:.6f}")
    print(f"    Range: [{gpH['min']:.6f}, {gpH['max']:.6f}]")
    print(f"    Trend: {gpH['trend']}")
    print(f"    Conservation likely: {analysis['conservation_likely']}")
    print(f"    γ↔H correlation: {analysis['gamma_H_correlation']:.6f}")
    
    # Show early/mid/late snapshots
    print(f"\n  Early rounds:")
    for r in analysis["early"]:
        print(f"    Round {r['round']:3d}: γ={r['gamma']:.4f}  H={r['H']:.4f}  γ+H={r['gamma_plus_H']:.4f}")
    
    print(f"\n  Mid rounds:")
    for r in analysis["mid"]:
        print(f"    Round {r['round']:3d}: γ={r['gamma']:.4f}  H={r['H']:.4f}  γ+H={r['gamma_plus_H']:.4f}")
    
    print(f"\n  Late rounds:")
    for r in analysis["late"]:
        print(f"    Round {r['round']:3d}: γ={r['gamma']:.4f}  H={r['H']:.4f}  γ+H={r['gamma_plus_H']:.4f}")
    
    # Room temporal summaries
    print(f"\n{'=' * 70}")
    print("ROOM TEMPORAL PROFILES")
    print("=" * 70)
    
    summary = substrate.summarize()
    for name, stats in summary["rooms"].items():
        print(f"\n  {name}:")
        print(f"    Proper time: {stats['proper_time']:.2f}  (consensus was {summary['rounds']})")
        print(f"    Gamma: mean={stats['mean_gamma']:.4f} std={stats['std_gamma']:.4f} "
              f"range=[{stats['min_gamma']:.4f}, {stats['max_gamma']:.4f}]")
        print(f"    Novelty: {stats['novelty_count']} finds")
    
    # Final coupling matrix
    C = tc.final_coupling_matrix()
    if C is not None:
        print(f"\n{'=' * 70}")
        print("FINAL COUPLING MATRIX")
        print("=" * 70)
        room_names = [substrate.rooms[rid].config.name for rid in substrate.rooms]
        header = "".join(f"{n[:8]:>10s}" for n in room_names)
        print(f"{'':>10s}{header}")
        for i, name_i in enumerate(room_names):
            row = "".join(f"{C[i][j]:10.4f}" for j in range(len(room_names)))
            print(f"  {name_i[:8]:>8s}{row}")
    
    # Build results markdown
    results_md = build_results_md(summary, analysis, C, room_names if C is not None else [])
    
    # Save
    results_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "COMBO-ARCHITECTURE-RESULTS.md")
    with open(results_path, "w") as f:
        f.write(results_md)
    print(f"\n  Results saved to {results_path}")
    
    return substrate, tc, analysis


def build_results_md(summary, analysis, C, room_names) -> str:
    """Build the results markdown document."""
    lines = []
    lines.append("# Combo Architecture Experiment Results")
    lines.append("")
    lines.append(f"**Date:** {_time.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Rounds:** {summary['rounds']}")
    lines.append(f"**Rooms:** {len(summary['rooms'])}")
    lines.append("")
    
    lines.append("## Hypothesis")
    lines.append("")
    lines.append("When rooms play together with time as a continuous analogue variable,")
    lines.append("the temporal coupling between rooms should exhibit a conservation law:")
    lines.append("**γ + H ≈ constant**, where γ is structural coupling (positive eigenvalue sum)")
    lines.append("and H is coupling entropy (randomness). If structure goes up, randomness")
    lines.append("goes down, and vice versa.")
    lines.append("")
    
    lines.append("## γ+H Statistics")
    lines.append("")
    gpH = analysis["gamma_plus_H"]
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Mean | {gpH['mean']:.6f} |")
    lines.append(f"| Std | {gpH['std']:.6f} |")
    lines.append(f"| CV | {gpH['cv']:.6f} |")
    lines.append(f"| Min | {gpH['min']:.6f} |")
    lines.append(f"| Max | {gpH['max']:.6f} |")
    lines.append(f"| Trend | {gpH['trend']} |")
    lines.append(f"| Conservation likely | **{analysis['conservation_likely']}** |")
    lines.append(f"| γ↔H correlation | {analysis['gamma_H_correlation']:.6f} |")
    lines.append("")
    
    lines.append("## Temporal Evolution")
    lines.append("")
    lines.append("### Early Rounds")
    lines.append("")
    lines.append("| Round | γ | H | γ+H |")
    lines.append("|-------|---|---|-----|")
    for r in analysis["early"]:
        lines.append(f"| {r['round']} | {r['gamma']:.4f} | {r['H']:.4f} | {r['gamma_plus_H']:.4f} |")
    lines.append("")
    
    lines.append("### Mid Rounds")
    lines.append("")
    lines.append("| Round | γ | H | γ+H |")
    lines.append("|-------|---|---|-----|")
    for r in analysis["mid"]:
        lines.append(f"| {r['round']} | {r['gamma']:.4f} | {r['H']:.4f} | {r['gamma_plus_H']:.4f} |")
    lines.append("")
    
    lines.append("### Late Rounds")
    lines.append("")
    lines.append("| Round | γ | H | γ+H |")
    lines.append("|-------|---|---|-----|")
    for r in analysis["late"]:
        lines.append(f"| {r['round']} | {r['gamma']:.4f} | {r['H']:.4f} | {r['gamma_plus_H']:.4f} |")
    lines.append("")
    
    lines.append("## Room Temporal Profiles")
    lines.append("")
    lines.append("| Room | Style | Courage | Proper Time | Mean γ | Std γ | Novelty |")
    lines.append("|------|-------|---------|-------------|--------|-------|---------|")
    for name, stats in summary["rooms"].items():
        lines.append(f"| {name} | {stats['play_style']} | {stats['courage']:.1f} | "
                     f"{stats['proper_time']:.2f} | {stats['mean_gamma']:.4f} | "
                     f"{stats['std_gamma']:.4f} | {stats['novelty_count']} |")
    lines.append("")
    
    if C is not None and len(room_names) > 0:
        lines.append("## Final Coupling Matrix")
        lines.append("")
        header = "| | " + " | ".join(n[:8] for n in room_names) + " |"
        sep = "|---|" + "|".join(["-------"] * len(room_names)) + "|"
        lines.append(header)
        lines.append(sep)
        for i, name in enumerate(room_names):
            vals = " | ".join(f"{C[i][j]:.4f}" for j in range(len(room_names)))
            lines.append(f"| {name[:8]} | {vals} |")
        lines.append("")
    
    lines.append("## Interpretation")
    lines.append("")
    cv = gpH['cv']
    corr = analysis['gamma_H_correlation']
    
    if analysis['conservation_likely']:
        lines.append("**The conservation law EMERGES.** γ+H is approximately constant across rounds")
        lines.append(f"(CV = {cv:.4f}). The temporal coupling between rooms exhibits the same")
        lines.append("conservation structure seen in the fleet's constraint theory.")
    elif cv < 0.2:
        lines.append(f"**Partial conservation signal.** CV = {cv:.4f} — not below the 10% threshold")
        lines.append("but suggests a trend. With more rounds or different room configurations,")
        lines.append("the conservation law might strengthen.")
    else:
        lines.append(f"**No clear conservation signal.** CV = {cv:.4f} — γ+H varies significantly.")
        lines.append("The temporal coupling dynamics may need more rounds, different room attitudes,")
        lines.append("or a different coupling metric to reveal conservation structure.")
    
    lines.append("")
    if corr < -0.3:
        lines.append(f"The γ↔H correlation is **{corr:.4f}** (negative), supporting the hypothesis")
        lines.append("that structure and randomness trade off: when coupling structure (γ) increases,")
        lines.append("coupling entropy (H) decreases proportionally.")
    elif corr > 0.3:
        lines.append(f"The γ↔H correlation is **{corr:.4f}** (positive), meaning structure and")
        lines.append("randomness grow together. This suggests the coupling matrix is becoming")
        lines.append("both more structured AND more entropic — a different regime than simple conservation.")
    else:
        lines.append(f"The γ↔H correlation is **{corr:.4f}** (weak), meaning γ and H evolve")
        lines.append("independently in this configuration. The conservation tradeoff is not the")
        lines.append("dominant dynamic here.")
    
    lines.append("")
    lines.append("## Key Insight")
    lines.append("")
    lines.append("Time as an analogue variable creates a **temporal ecology**: rooms that")
    lines.append("anticipate well slow down (process more per consensus tick), while rooms")
    lines.append("that are surprised speed up (react faster). This creates a natural")
    lines.append("**division of temporal labor** — some rooms become deep processors,")
    lines.append("others become fast reactors. The coupling between these temporal flows")
    lines.append("is the substrate on which the conservation law operates.")
    lines.append("")
    lines.append("---")
    lines.append(f"*Generated by combo_architecture.py at {_time.strftime('%Y-%m-%d %H:%M:%S')}*")
    
    return "\n".join(lines)


if __name__ == "__main__":
    run_experiment()
