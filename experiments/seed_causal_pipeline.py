#!/usr/bin/env python3
"""
seed_causal_pipeline.py — Seed's Causal Pipeline
=================================================

Automatic oscillation detection and sub-room spawning.

Mechanism: The room-play system detects when a room is oscillating
(repeating patterns) and automatically spawns a sub-room to explore
the oscillation's structure.

Components:
1. OscillationDetector — autocorrelation-based oscillation detection
2. SubRoomSpawner — spawns compressed-timescale sub-rooms
3. CausalTracker — Granger causality + causal graph
4. Pipeline — orchestrates everything across 5 PlayRooms

Random seed: 42
"""

from __future__ import annotations

import json
import math
import os
import random
import sys
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

# ─── Configuration ──────────────────────────────────────────────────────────

SEED = 42
NUM_ROOMS = 5
NUM_ROUNDS = 500
STATE_DIM = 8
AUTOCORR_THRESHOLD = 0.7
CONSECUTIVE_TRIGGER = 3
MAX_LAG = 50
GRANGER_MAX_LAG = 10
GRANGER_SIGNIFICANCE = 0.05
SUBROOM_TIME_COMPRESSION = 3.0  # sub-rooms experience time 3x faster

np.random.seed(SEED)
random.seed(SEED)

# ─── PlayRoom (simplified from room_play.py patterns) ───────────────────────

class PlayRoom:
    """A room that PLAYS — has attitude, not function.
    
    Each room runs its own dynamics and produces an output stream.
    The dynamics are nonlinear (sinusoidal + noise + coupling) to create
    rich oscillatory behavior.
    """
    
    def __init__(self, room_id: str, state_dim: int = STATE_DIM, 
                 natural_freq: Optional[float] = None):
        self.room_id = room_id
        self.state_dim = state_dim
        self.state = np.random.randn(state_dim) * 0.1
        self.natural_freq = natural_freq or np.random.uniform(0.05, 0.3)
        self.phase = np.random.uniform(0, 2 * np.pi)
        self.damping = np.random.uniform(0.01, 0.05)
        self.coupling_strength = np.random.uniform(0.01, 0.08)
        self.nonlinearity = np.random.uniform(0.1, 0.5)
        self.output_history: List[float] = []
        self.state_history: List[np.ndarray] = []
        self.round = 0
        
    def step(self, neighbors: List['PlayRoom']) -> float:
        """One round of play. Returns scalar output."""
        self.round += 1
        
        # Natural oscillation
        self.phase += self.natural_freq
        
        # Neighbor coupling — creates entrainment and feedback
        coupling = 0.0
        for nbr in neighbors:
            if nbr.output_history:
                coupling += self.coupling_strength * nbr.output_history[-1]
        
        # Nonlinear self-interaction
        state_norm = np.linalg.norm(self.state)
        nonlinear = self.nonlinearity * np.sin(state_norm)
        
        # State dynamics: damped oscillator with coupling
        noise = np.random.randn(self.state_dim) * 0.02
        self.state += (
            -self.damping * self.state  # damping
            + coupling * np.sin(self.state)  # coupling
            + nonlinear * np.cos(self.state)  # nonlinearity
            + 0.1 * np.sin(self.phase + np.arange(self.state_dim) * 0.5)  # oscillation drive
            + noise  # noise
        )
        
        # Output = projection of state
        output = float(np.mean(self.state) + 0.3 * np.sin(self.phase))
        self.output_history.append(output)
        self.state_history.append(self.state.copy())
        
        return output


# ─── 1. OscillationDetector ─────────────────────────────────────────────────

@dataclass
class OscillationReport:
    """Report from detecting an oscillation."""
    room_id: str
    detected_round: int
    lag: int  # period in rounds
    frequency: float  # 1/period
    amplitude: float
    decay_rate: float
    autocorrelation: float
    consecutive_count: int

class OscillationDetector:
    """Monitors a room's output stream for oscillation.
    
    Detects oscillation using autocorrelation (peaks at lag > 1).
    Triggers when autocorrelation at any lag > 0.7 for 3 consecutive observations.
    Measures frequency, amplitude, and decay.
    """
    
    def __init__(self, max_lag: int = MAX_LAG, threshold: float = AUTOCORR_THRESHOLD,
                 consecutive: int = CONSECUTIVE_TRIGGER):
        self.max_lag = max_lag
        self.threshold = threshold
        self.consecutive_trigger = consecutive
        # Per-room tracking
        self.consecutive_counts: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
        self.detected: Dict[str, OscillationReport] = {}
        
    def compute_autocorrelation(self, series: List[float], lag: int) -> float:
        """Normalized autocorrelation at given lag."""
        if len(series) < lag + 2:
            return 0.0
        arr = np.array(series[-(self.max_lag * 4):])  # use recent window
        if lag >= len(arr):
            return 0.0
        mean = np.mean(arr)
        var = np.var(arr)
        if var < 1e-12:
            return 0.0
        autocorr = np.mean((arr[:-lag] - mean) * (arr[lag:] - mean)) / var
        return float(autocorr)
    
    def measure_oscillation(self, series: List[float], lag: int) -> Tuple[float, float, float]:
        """Measure amplitude, frequency, decay of oscillation at given lag."""
        if len(series) < lag * 4:
            return 0.0, 0.0, 0.0
        
        arr = np.array(series)
        # Frequency from lag
        frequency = 1.0 / lag if lag > 0 else 0.0
        
        # Amplitude: std of the signal
        amplitude = float(np.std(arr[-lag*4:]))
        
        # Decay: compare amplitude in first half vs second half of window
        window = arr[-lag*4:]
        half = len(window) // 2
        amp_first = np.std(window[:half])
        amp_second = np.std(window[half:])
        if amp_first > 1e-12:
            decay = float((amp_first - amp_second) / amp_first)
        else:
            decay = 0.0
            
        return amplitude, frequency, decay
    
    def check_room(self, room: PlayRoom) -> Optional[OscillationReport]:
        """Check a room for oscillation. Returns report if newly detected."""
        if room.room_id in self.detected:
            return None
        if len(room.output_history) < self.max_lag * 2:
            return None
            
        for lag in range(2, self.max_lag + 1):
            ac = self.compute_autocorrelation(room.output_history, lag)
            
            if ac > self.threshold:
                self.consecutive_counts[room.room_id][lag] += 1
                if self.consecutive_counts[room.room_id][lag] >= self.consecutive_trigger:
                    amplitude, frequency, decay = self.measure_oscillation(
                        room.output_history, lag
                    )
                    report = OscillationReport(
                        room_id=room.room_id,
                        detected_round=room.round,
                        lag=lag,
                        frequency=frequency,
                        amplitude=amplitude,
                        decay_rate=decay,
                        autocorrelation=ac,
                        consecutive_count=self.consecutive_counts[room.room_id][lag],
                    )
                    self.detected[room.room_id] = report
                    return report
            else:
                self.consecutive_counts[room.room_id][lag] = 0
                
        return None


# ─── 2. SubRoomSpawner ──────────────────────────────────────────────────────

@dataclass
class SubRoom:
    """A sub-room spawned to explore a parent's oscillation."""
    sub_room_id: str
    parent_id: str
    spawn_round: int
    state_at_spawn: np.ndarray
    time_compression: float
    period: int
    amplitude: float
    phase_space: List[Tuple[float, float]]  # (phase, amplitude) pairs
    structure: str  # description of oscillation structure
    completed: bool = False
    exploration_rounds: int = 0
    
class SubRoomSpawner:
    """When oscillation detected, spawns a sub-room that:
    - Inherits parent state at oscillation onset
    - Has compressed time scale (experiences time faster)
    - Explores the oscillation's phase space
    - Reports back structure
    """
    
    def __init__(self, time_compression: float = SUBROOM_TIME_COMPRESSION):
        self.time_compression = time_compression
        self.sub_rooms: Dict[str, SubRoom] = {}
        self.catalog: List[Dict[str, Any]] = []
        
    def spawn(self, parent: PlayRoom, report: OscillationReport) -> SubRoom:
        """Spawn a sub-room to explore the parent's oscillation."""
        sub_id = f"sub_{parent.room_id}_r{report.detected_round}"
        
        sub = SubRoom(
            sub_room_id=sub_id,
            parent_id=parent.room_id,
            spawn_round=report.detected_round,
            state_at_spawn=parent.state.copy(),
            time_compression=self.time_compression,
            period=report.lag,
            amplitude=report.amplitude,
            phase_space=[],
            structure="exploring",
        )
        
        # Run the sub-room exploration: compressed timescale
        # The sub-room runs faster and explores phase space
        exploration_rounds = int(report.lag * self.time_compression * 4)
        state = parent.state.copy()
        phase_space = []
        
        for t in range(exploration_rounds):
            # Compressed time: advance phase faster
            compressed_phase = t * parent.natural_freq * self.time_compression
            
            # Simulate with parent's dynamics but faster
            noise = np.random.randn(len(state)) * 0.01
            state += (
                -parent.damping * state * self.time_compression
                + 0.1 * np.sin(compressed_phase + np.arange(len(state)) * 0.5)
                + noise
            )
            
            # Record phase space point
            output = float(np.mean(state))
            phase_angle = (compressed_phase % (2 * math.pi)) / (2 * math.pi) * report.lag
            phase_space.append((float(phase_angle), output))
        
        # Analyze phase space structure
        amplitudes = [abs(p[1]) for p in phase_space]
        phases = [p[0] for p in phase_space]
        
        # Classify structure
        amp_range = max(amplitudes) - min(amplitudes)
        if amp_range < 0.1:
            structure = "limit_cycle"
        elif amp_range < 0.5:
            structure = "quasi_periodic"
        else:
            structure = "chaotic_attractor"
        
        sub.phase_space = phase_space
        sub.structure = structure
        sub.exploration_rounds = exploration_rounds
        sub.completed = True
        
        self.sub_rooms[sub_id] = sub
        
        # Add to catalog
        self.catalog.append({
            "sub_room_id": sub_id,
            "parent_id": parent.room_id,
            "spawn_round": report.detected_round,
            "period": report.lag,
            "amplitude": report.amplitude,
            "frequency": report.frequency,
            "decay_rate": report.decay_rate,
            "structure": structure,
            "exploration_rounds": exploration_rounds,
            "time_compression": self.time_compression,
            "phase_space_size": len(phase_space),
            "amplitude_range": float(amp_range),
        })
        
        return sub


# ─── 3. CausalTracker ───────────────────────────────────────────────────────

@dataclass
class CausalEdge:
    """An edge in the causal graph."""
    source: str
    target: str
    granger_f: float
    granger_p: float
    lag: int
    direction: str  # "A→B", "B→A", "A↔B"

class CausalTracker:
    """Builds a causal graph using Granger causality.
    
    Tests: does room A's past predict room B's present
    beyond what B's own past predicts?
    """
    
    def __init__(self, max_lag: int = GRANGER_MAX_LAG):
        self.max_lag = max_lag
        self.edges: List[CausalEdge] = []
        self.causal_graph: Dict[str, Set[str]] = defaultdict(set)
        
    def _lag_regression(self, y: np.ndarray, x_lags: np.ndarray, 
                        y_lags: np.ndarray) -> Tuple[float, float]:
        """Simple OLS regression. Returns (RSS, n)."""
        n = len(y)
        if n < self.max_lag + 5:
            return float('inf'), n
        # Restricted model: y ~ y_lags
        Y_r = np.column_stack([y_lags, np.ones(n)])
        try:
            beta_r = np.linalg.lstsq(Y_r, y, rcond=None)[0]
            rss_r = float(np.sum((y - Y_r @ beta_r) ** 2))
        except np.linalg.LinAlgError:
            rss_r = float('inf')
        
        # Unrestricted model: y ~ y_lags + x_lags
        Y_u = np.column_stack([y_lags, x_lags, np.ones(n)])
        try:
            beta_u = np.linalg.lstsq(Y_u, y, rcond=None)[0]
            rss_u = float(np.sum((y - Y_u @ beta_u) ** 2))
        except np.linalg.LinAlgError:
            rss_u = float('inf')
            
        return rss_r, rss_u
    
    def granger_test(self, source_outputs: List[float], 
                     target_outputs: List[float],
                     lag: int) -> Tuple[float, float]:
        """Granger causality test: does source predict target?
        
        Returns (F-statistic, p-value).
        """
        x = np.array(source_outputs)
        y = np.array(target_outputs)
        
        n = len(y) - lag
        if n < lag + 5:
            return 0.0, 1.0
        
        # Build lag matrices
        y_target = y[lag:]
        y_lags = np.column_stack([y[lag-k-1:-k-1] for k in range(lag)])
        x_lags = np.column_stack([x[lag-k-1:-k-1] for k in range(lag)])
        
        # Align lengths
        min_len = min(len(y_target), len(y_lags), len(x_lags))
        y_target = y_target[:min_len]
        y_lags = y_lags[:min_len]
        x_lags = x_lags[:min_len]
        
        rss_r, rss_u = self._lag_regression(y_target, x_lags, y_lags)
        
        if rss_u <= 0 or rss_r == float('inf'):
            return 0.0, 1.0
            
        # F-test
        df_num = lag
        df_den = min_len - 2 * lag - 1
        if df_den <= 0:
            return 0.0, 1.0
            
        f_stat = ((rss_r - rss_u) / df_num) / (rss_u / df_den)
        
        # Approximate p-value using chi-squared (F ≈ chi²/df for large n)
        from scipy.stats import f as f_dist
        try:
            p_value = float(1.0 - f_dist.cdf(f_stat, df_num, df_den))
        except Exception:
            p_value = 0.05 if f_stat > 3.0 else 0.5
            
        return float(f_stat), float(p_value)
    
    def build_graph(self, rooms: Dict[str, PlayRoom]) -> List[CausalEdge]:
        """Build full causal graph between all room pairs."""
        self.edges = []
        self.causal_graph = defaultdict(set)
        
        room_ids = list(rooms.keys())
        
        for i, src_id in enumerate(room_ids):
            for j, tgt_id in enumerate(room_ids):
                if src_id == tgt_id:
                    continue
                    
                src_outputs = rooms[src_id].output_history
                tgt_outputs = rooms[tgt_id].output_history
                
                if len(src_outputs) < self.max_lag * 3:
                    continue
                
                # Test at multiple lags, take best
                best_f, best_p, best_lag = 0.0, 1.0, 1
                for lag in range(1, self.max_lag + 1):
                    f_stat, p_val = self.granger_test(src_outputs, tgt_outputs, lag)
                    if f_stat > best_f:
                        best_f, best_p, best_lag = f_stat, p_val, lag
                
                if best_p < 0.10:  # relaxed threshold for graph building
                    edge = CausalEdge(
                        source=src_id,
                        target=tgt_id,
                        granger_f=best_f,
                        granger_p=best_p,
                        lag=best_lag,
                        direction=f"{src_id}→{tgt_id}",
                    )
                    self.edges.append(edge)
                    self.causal_graph[src_id].add(tgt_id)
        
        # Detect bidirectional (feedback loops)
        edge_pairs = {}
        for e in self.edges:
            key = tuple(sorted([e.source, e.target]))
            if key in edge_pairs:
                edge_pairs[key].append(e)
            else:
                edge_pairs[key] = [e]
        
        for key, pair in edge_pairs.items():
            if len(pair) == 2:
                for e in pair:
                    e.direction = f"{key[0]}↔{key[1]}"
        
        return self.edges
    
    def find_chains(self, min_length: int = 3) -> List[List[str]]:
        """Find causal chains (A→B→C→...)."""
        chains = []
        
        def dfs(node: str, path: List[str], visited: Set[str]):
            if len(path) >= min_length:
                chains.append(path.copy())
            for neighbor in self.causal_graph.get(node, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    dfs(neighbor, path + [neighbor], visited)
                    visited.remove(neighbor)
        
        for room_id in self.causal_graph:
            dfs(room_id, [room_id], {room_id})
        
        # Deduplicate and sort by length
        unique = []
        seen = set()
        for chain in sorted(chains, key=len, reverse=True):
            key = tuple(chain)
            if key not in seen:
                seen.add(key)
                unique.append(chain)
        
        return unique
    
    def find_feedback_loops(self) -> List[List[str]]:
        """Find feedback loops (cycles in causal graph)."""
        loops = []
        room_ids = set(self.causal_graph.keys())
        for k in self.causal_graph:
            for v in self.causal_graph[k]:
                room_ids.add(v)
        
        for start in room_ids:
            # BFS for cycles back to start
            visited = set()
            queue = [(start, [start])]
            while queue:
                node, path = queue.pop(0)
                for nbr in self.causal_graph.get(node, set()):
                    if nbr == start and len(path) >= 2:
                        loops.append(path + [start])
                    elif nbr not in visited and len(path) < 6:
                        visited.add(nbr)
                        queue.append((nbr, path + [nbr]))
        
        # Deduplicate
        unique = []
        seen = set()
        for loop in loops:
            key = tuple(sorted(loop[:-1]))
            if key not in seen:
                seen.add(key)
                unique.append(loop)
        
        return unique


# ─── 4. Pipeline ────────────────────────────────────────────────────────────

@dataclass
class PipelineResult:
    """Results from the full pipeline run."""
    rounds: int
    rooms: int
    oscillations_detected: int
    sub_rooms_spawned: int
    causal_edges: int
    feedback_loops: int
    causal_chains: int
    oscillation_catalog: List[Dict[str, Any]]
    sub_room_catalog: List[Dict[str, Any]]
    causal_edges_detail: List[Dict[str, Any]]
    feedback_loops_detail: List[List[str]]
    chains_detail: List[List[str]]
    room_summaries: Dict[str, Dict[str, Any]]


def run_pipeline() -> PipelineResult:
    """Run the full Seed causal pipeline."""
    print("=" * 70)
    print("SEED CAUSAL PIPELINE")
    print("=" * 70)
    print(f"Rooms: {NUM_ROOMS}  |  Rounds: {NUM_ROUNDS}  |  Seed: {SEED}")
    print(f"State dim: {STATE_DIM}  |  Autocorr threshold: {AUTOCORR_THRESHOLD}")
    print(f"Consecutive trigger: {CONSECUTIVE_TRIGGER}  |  Max lag: {MAX_LAG}")
    print()
    
    # Create rooms with different natural frequencies
    freqs = [0.08, 0.12, 0.18, 0.22, 0.28]
    rooms: Dict[str, PlayRoom] = {}
    for i in range(NUM_ROOMS):
        rid = f"room_{chr(65+i)}"  # room_A through room_E
        rooms[rid] = PlayRoom(
            room_id=rid, 
            state_dim=STATE_DIM,
            natural_freq=freqs[i],
        )
    
    print("Rooms created:")
    for rid, r in rooms.items():
        print(f"  {rid}: freq={r.natural_freq:.3f}, damping={r.damping:.3f}, "
              f"coupling={r.coupling_strength:.3f}, nonlin={r.nonlinearity:.3f}")
    print()
    
    # Initialize components
    detector = OscillationDetector()
    spawner = SubRoomSpawner()
    tracker = CausalTracker()
    
    # ── Run simulation ──
    print("Running simulation...")
    oscillation_events: List[Dict[str, Any]] = []
    
    for round_num in range(1, NUM_ROUNDS + 1):
        # Each room plays with all others as neighbors
        room_list = list(rooms.values())
        for room in room_list:
            neighbors = [r for r in room_list if r.room_id != room.room_id]
            room.step(neighbors)
        
        # Check for oscillations every 10 rounds (after warm-up)
        if round_num >= 30 and round_num % 10 == 0:
            for room in room_list:
                report = detector.check_room(room)
                if report:
                    print(f"  ⚡ Round {round_num}: Oscillation detected in {room.room_id}! "
                          f"lag={report.lag}, freq={report.frequency:.4f}, "
                          f"amp={report.amplitude:.4f}, ac={report.autocorrelation:.3f}")
                    
                    # Spawn sub-room
                    sub = spawner.spawn(room, report)
                    print(f"    → Spawned {sub.sub_room_id}: structure={sub.structure}, "
                          f"exploration_rounds={sub.exploration_rounds}")
                    
                    oscillation_events.append({
                        "round": round_num,
                        "room": room.room_id,
                        "sub_room": sub.sub_room_id,
                        "lag": report.lag,
                        "amplitude": report.amplitude,
                        "structure": sub.structure,
                    })
        
        # Progress
        if round_num % 100 == 0:
            print(f"  ... round {round_num}/{NUM_ROUNDS}")
    
    print(f"\nSimulation complete. {len(oscillation_events)} oscillations detected.\n")
    
    # ── Build causal graph ──
    print("Building causal graph...")
    edges = tracker.build_graph(rooms)
    print(f"  {len(edges)} causal edges found.")
    
    # Significant edges (p < 0.05)
    sig_edges = [e for e in edges if e.granger_p < GRANGER_SIGNIFICANCE]
    print(f"  {len(sig_edges)} significant at p < {GRANGER_SIGNIFICANCE}")
    
    # Find chains and loops
    chains = tracker.find_chains(min_length=3)
    loops = tracker.find_feedback_loops()
    
    print(f"  {len(chains)} causal chains (length ≥ 3)")
    print(f"  {len(loops)} feedback loops")
    
    # Print edges
    if edges:
        print("\n  Causal edges:")
        for e in sorted(edges, key=lambda x: x.granger_p):
            sig = "*" if e.granger_p < 0.05 else ""
            print(f"    {e.direction}: F={e.granger_f:.2f}, p={e.granger_p:.4f}, "
                  f"lag={e.lag} {sig}")
    
    if chains:
        print("\n  Causal chains:")
        for chain in chains[:10]:
            print(f"    {' → '.join(chain)}")
    
    if loops:
        print("\n  Feedback loops:")
        for loop in loops:
            print(f"    {' → '.join(loop)}")
    
    # ── Room summaries ──
    room_summaries = {}
    print("\nRoom summaries:")
    for rid, room in rooms.items():
        outputs = np.array(room.output_history)
        summary = {
            "mean_output": float(np.mean(outputs)),
            "std_output": float(np.std(outputs)),
            "min_output": float(np.min(outputs)),
            "max_output": float(np.max(outputs)),
            "final_state_norm": float(np.linalg.norm(room.state)),
            "natural_freq": room.natural_freq,
            "damping": room.damping,
            "oscillation_detected": rid in detector.detected,
        }
        if rid in detector.detected:
            det = detector.detected[rid]
            summary["oscillation_lag"] = det.lag
            summary["oscillation_freq"] = det.frequency
            summary["oscillation_amplitude"] = det.amplitude
            summary["oscillation_decay"] = det.decay_rate
            summary["oscillation_autocorr"] = det.autocorrelation
        room_summaries[rid] = summary
        osc_str = f"OSC@lag={det.lag}" if rid in detector.detected else "no oscillation"
        print(f"  {rid}: mean={summary['mean_output']:.4f}, std={summary['std_output']:.4f}, "
              f"{osc_str}")
    
    # Build result
    result = PipelineResult(
        rounds=NUM_ROUNDS,
        rooms=NUM_ROOMS,
        oscillations_detected=len(oscillation_events),
        sub_rooms_spawned=len(spawner.catalog),
        causal_edges=len(edges),
        feedback_loops=len(loops),
        causal_chains=len(chains),
        oscillation_catalog=oscillation_events,
        sub_room_catalog=spawner.catalog,
        causal_edges_detail=[
            {
                "direction": e.direction,
                "f_stat": e.granger_f,
                "p_value": e.granger_p,
                "lag": e.lag,
            }
            for e in edges
        ],
        feedback_loops_detail=loops,
        chains_detail=chains,
        room_summaries=room_summaries,
    )
    
    return result


# ─── 5. Save results ────────────────────────────────────────────────────────

def save_results(result: PipelineResult, path: str):
    """Save results to markdown."""
    
    md = f"""# SEED Causal Pipeline Results

**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}  
**Seed:** {SEED}  
**Rooms:** {result.rooms}  
**Rounds:** {result.rounds}

---

## Summary

| Metric | Value |
|--------|-------|
| Oscillations Detected | {result.oscillations_detected} |
| Sub-Rooms Spawned | {result.sub_rooms_spawned} |
| Causal Edges | {result.causal_edges} |
| Feedback Loops | {result.feedback_loops} |
| Causal Chains (≥3) | {result.causal_chains} |

---

## Room Summaries

| Room | Mean | Std | Oscillation |
|------|------|-----|-------------|
"""
    
    for rid, s in sorted(result.room_summaries.items()):
        osc = "—" 
        if s.get("oscillation_detected"):
            osc = f"lag={s['oscillation_lag']}, f={s['oscillation_freq']:.4f}"
        md += f"| {rid} | {s['mean_output']:.4f} | {s['std_output']:.4f} | {osc} |\n"
    
    md += """
---

## Oscillation Catalog

"""
    if result.oscillation_catalog:
        md += "| Round | Room | Sub-Room | Period | Amplitude | Structure |\n"
        md += "|-------|------|----------|--------|-----------|----------|\n"
        for o in result.oscillation_catalog:
            md += f"| {o['round']} | {o['room']} | {o['sub_room']} | {o['lag']} | {o['amplitude']:.4f} | {o['structure']} |\n"
    else:
        md += "No oscillations detected.\n"
    
    md += """
---

## Sub-Room Inventory

"""
    if result.sub_room_catalog:
        md += "| Sub-Room | Parent | Spawn Round | Period | Structure | Amplitude Range | Exploration Rounds |\n"
        md += "|----------|--------|-------------|--------|-----------|----------------|-------------------|\n"
        for s in result.sub_room_catalog:
            md += f"| {s['sub_room_id']} | {s['parent_id']} | {s['spawn_round']} | {s['period']} | {s['structure']} | {s['amplitude_range']:.4f} | {s['exploration_rounds']} |\n"
    else:
        md += "No sub-rooms spawned.\n"
    
    md += """
---

## Causal Graph

### Edges (Granger Causality)

"""
    if result.causal_edges_detail:
        md += "| Direction | F-stat | p-value | Lag | Significant |\n"
        md += "|-----------|--------|---------|-----|-------------|\n"
        for e in sorted(result.causal_edges_detail, key=lambda x: x['p_value']):
            sig = "✓" if e['p_value'] < 0.05 else ""
            md += f"| {e['direction']} | {e['f_stat']:.2f} | {e['p_value']:.4f} | {e['lag']} | {sig} |\n"
    else:
        md += "No causal edges detected.\n"
    
    md += """
### Feedback Loops

"""
    if result.feedback_loops_detail:
        for i, loop in enumerate(result.feedback_loops_detail, 1):
            md += f"{i}. {' → '.join(loop)}\n"
    else:
        md += "No feedback loops detected.\n"
    
    md += """
### Causal Chains (length ≥ 3)

"""
    if result.chains_detail:
        for i, chain in enumerate(result.chains_detail[:20], 1):
            md += f"{i}. {' → '.join(chain)}\n"
        if len(result.chains_detail) > 20:
            md += f"\n... and {len(result.chains_detail) - 20} more chains.\n"
    else:
        md += "No causal chains of length ≥ 3 detected.\n"
    
    md += """
---

## Architecture

```
┌──────────┐     ┌──────────────────┐     ┌──────────────┐
│ PlayRoom │────▶│ OscillationDetector │────▶│ SubRoomSpawner │
│ (5 rooms)│     │ (autocorrelation) │     │ (phase space)  │
└──────────┘     └──────────────────┘     └──────────────┘
       │                                          │
       │         ┌──────────────────┐             │
       └────────▶│  CausalTracker   │◀────────────┘
                 │ (Granger test)   │
                 └──────────────────┘
                          │
                          ▼
                   Causal Graph
                  ┌──────────────┐
                  │ Edges + Chains│
                  │ + Feedback    │
                  └──────────────┘
```

---

*Generated by seed_causal_pipeline.py — Seed's Causal Pipeline*
"""
    
    with open(path, 'w') as f:
        f.write(md)
    print(f"\nResults saved to {path}")


# ─── Main ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Ensure scipy is available for p-value computation
    try:
        from scipy.stats import f as _f
    except ImportError:
        print("Installing scipy...")
        os.system("pip install scipy -q")
    
    result = run_pipeline()
    
    results_path = os.path.join(os.path.dirname(__file__), "SEED-CAUSAL-PIPELINE-RESULTS.md")
    save_results(result, results_path)
    
    print("\n" + "=" * 70)
    print("SEED CAUSAL PIPELINE COMPLETE")
    print("=" * 70)
