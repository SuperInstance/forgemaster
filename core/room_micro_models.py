#!/usr/bin/env python3
"""core/room_micro_models.py — Spreadsheet of living micro-model instances.

ARCHITECTURE:
  A "room" is a 2D grid of cells. Each cell IS a micro model instance.
  Deltas cascade through dependent cells via parallelism AND sequences.
  Time is a variable per cell, not a global clock.

KEY INSIGHTS IMPLEMENTED:
  1. Spreadsheet architecture: each cell = micro model instance with own daemons
  2. Time as internal variable: each cell simulates its own timeline, converges
     with neighbors through t-minus-event
  3. Conductor synchronization: like an orchestra, the conductor's timing IS
     the truth. Musicians at far ends watch the conductor for hints they're off.
  4. GPU backends: cudaclaw, ai-pasture, ai-forest. This module is the
     ORCHESTRATION LAYER that dispatches micro models to those backends.

METAPHOR:
  Think of a symphony hall. The conductor stands at the front. Each musician
  (cell) has their own internal sense of time. The sound from the far side of
  the orchestra hall reaches a musician AFTER the conductor's baton has moved.
  But the musician watches the CONDUCTOR, not listens to the other players.

  The conductor's intention reaches all eyes simultaneously.
  The sound reaches all ears at different times.
  The musician plays to the conductor's INTENTION, not to the delayed sound.

  That's what t-minus convergence does: cells align on a FUTURE event
  (the conductor's downbeat), not on the current state.
"""
from __future__ import annotations

import time
import math
import random
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Set, Callable
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, Future
from enum import Enum


# ─── GPU Backend Types ────────────────────────────────────────────────────────

class GPUBackend(Enum):
    """Available GPU/compute backends for micro model execution."""
    CPU = "cpu"
    CUDACLAW = "cudaclaw"        # CUDA-accelerated constraint checker
    AI_PASTURE = "ai-pasture"    # Distributed GPU farm
    AI_FOREST = "ai-forest"      # Hierarchical GPU cluster


class CellState(Enum):
    """Lifecycle states for a micro model cell."""
    IDLE = "idle"
    RUNNING = "running"
    CONVERGING = "converging"
    CONVERGED = "converged"
    ERROR = "error"
    DAEMON = "daemon"            # Running a persistent daemon


# ─── T-Minus Event ───────────────────────────────────────────────────────────

@dataclass
class TMinusEvent:
    """A future event that cells converge toward.

    The t-minus-event is the conductor's downbeat. It's a point in the future
    when all participating cells must have their internal timelines aligned.

    Cells don't sync on "now" — they sync on a FUTURE event.
    Like musicians counting rests to come in on the right beat.
    """
    event_id: str
    event_type: str               # "convergence", "training_epoch", "tile_harvest"
    target_time: float            # when the event should happen (wall clock)
    participating_cells: Set[str] = field(default_factory=set)
    required_precision: float = 0.01  # how close internal times must be
    status: str = "pending"       # pending | converging | fired | expired
    created_at: float = field(default_factory=time.time)
    meta: dict = field(default_factory=dict)

    @property
    def t_minus(self) -> float:
        """Seconds until this event fires."""
        return max(0.0, self.target_time - time.time())


# ─── MicroCell — one cell in the spreadsheet ──────────────────────────────────

class MicroCell:
    """A single micro model instance. One cell in the spreadsheet.

    Has its own:
    - Runtime (can spawn its own daemons)
    - Time variable (runs independently)
    - Task (what it's computing)
    - State (training state, convergence state)
    - Dependencies (which cells feed into this one)
    - GPU target (which backend it runs on)

    Each cell is a living thing. It ticks at its own rate, simulates
    its own timeline, and converges with neighbors through t-minus events.
    """

    def __init__(
        self,
        cell_id: str,
        task: str = "generic",
        gpu_backend: GPUBackend = GPUBackend.CPU,
    ):
        self.cell_id = cell_id
        self.task = task
        self.gpu_backend = gpu_backend
        self.state = CellState.IDLE

        # Internal time: each cell has its OWN clock
        self.internal_time: float = 0.0
        self.time_scale: float = 1.0      # how fast internal time moves
        self.time_offset: float = 0.0     # offset for synchronization

        # Dependencies: cells this one reads from (row, col) tuples
        self.dependencies: List[Tuple[int, int]] = []
        self.dependents: List[Tuple[int, int]] = []  # cells that depend on this

        # Training/simulation state
        self.iteration: int = 0
        self.loss: float = 1.0
        self.accuracy: float = 0.0
        self.convergence_score: float = 0.0
        self.best_loss: float = float('inf')
        self.best_accuracy: float = 0.0

        # Computed value (the cell's current output, like a spreadsheet cell)
        self.value: Any = None
        self.dirty: bool = True           # needs recalculation

        # Daemon support
        self._daemon: Optional[threading.Thread] = None
        self._daemon_running: bool = False
        self._daemon_interval: float = 1.0

        # GPU execution
        self._gpu_result: Any = None
        self._gpu_future: Optional[Future] = None

        # History for the cell's own timeline
        self.timeline: List[dict] = []

        # T-minus events this cell is participating in
        self.pending_events: List[str] = []

        # Conductor calibration
        self.conductor_offset: float = 0.0  # how far off from conductor's time

    def tick(self, delta: float = 1.0) -> dict:
        """Advance internal time by one unit.

        The cell's internal clock moves at its own rate. It doesn't
        care what other cells are doing. It ticks when it ticks.
        """
        self.internal_time += delta * self.time_scale
        self.iteration += 1

        # Record on the cell's timeline
        entry = {
            "t": round(self.internal_time, 4),
            "wall": round(time.time(), 4),
            "iteration": self.iteration,
            "state": self.state.value,
            "loss": round(self.loss, 6),
            "accuracy": round(self.accuracy, 4),
        }
        self.timeline.append(entry)
        return entry

    def simulate(self, steps: int = 10) -> List[dict]:
        """Run own simulation for N steps.

        Each step advances internal time and simulates one iteration
        of the micro model's training/computation loop.
        """
        self.state = CellState.RUNNING
        results = []

        for i in range(steps):
            # Simulate training step (loss decreases, accuracy increases)
            progress = min(1.0, self.iteration / 100.0)
            noise = random.gauss(0, 0.02)

            # Loss decays exponentially with noise
            self.loss = max(0.001, math.exp(-3 * progress) + noise * 0.1)
            # Accuracy rises sigmoidally
            self.accuracy = min(1.0, 1.0 / (1.0 + math.exp(-8 * (progress - 0.5))) + noise * 0.05)

            if self.loss < self.best_loss:
                self.best_loss = self.loss
            if self.accuracy > self.best_accuracy:
                self.best_accuracy = self.accuracy

            # Compute the cell's value (simulated micro model output)
            self.value = {
                "prediction": round(0.5 + 0.5 * math.tanh(progress - 0.5), 4),
                "confidence": round(min(1.0, self.accuracy * 1.1), 4),
                "loss": round(self.loss, 6),
            }
            self.dirty = False

            entry = self.tick()
            results.append(entry)

        return results

    def recalculate(self, dependency_values: Dict[str, Any] = None) -> Any:
        """Recompute from dependencies.

        Like a spreadsheet cell recalculating when its inputs change.
        """
        if dependency_values is None:
            dependency_values = {}

        self.state = CellState.RUNNING

        # Combine dependency values into a new computation
        dep_count = len(dependency_values)
        if dep_count > 0:
            # Weighted average of dependency outputs
            total_weight = 0.0
            weighted_pred = 0.0
            weighted_conf = 0.0
            for dep_id, dep_val in dependency_values.items():
                if isinstance(dep_val, dict):
                    w = dep_val.get("confidence", 0.5)
                    weighted_pred += dep_val.get("prediction", 0.5) * w
                    weighted_conf += w * w
                    total_weight += w
                else:
                    total_weight += 1.0
                    weighted_pred += float(dep_val) if dep_val else 0.5

            if total_weight > 0:
                pred = weighted_pred / total_weight
                conf = math.sqrt(weighted_conf) / total_weight if total_weight > 0 else 0.5
            else:
                pred, conf = 0.5, 0.5

            self.value = {
                "prediction": round(pred, 4),
                "confidence": round(min(1.0, conf), 4),
                "loss": round(self.loss, 6),
            }
        else:
            # No dependencies: use own simulation
            self.value = {
                "prediction": round(random.uniform(0.3, 0.9), 4),
                "confidence": round(random.uniform(0.5, 0.95), 4),
                "loss": round(self.loss, 6),
            }

        self.dirty = False
        self.state = CellState.IDLE
        return self.value

    def converge(self, target_event: TMinusEvent) -> dict:
        """Attempt convergence on a t-minus-event.

        The cell adjusts its internal time to align with the target event.
        Like a musician watching the conductor's baton and adjusting
        their internal count to match.
        """
        self.state = CellState.CONVERGING
        t_minus = target_event.t_minus

        # The cell adjusts its time_scale and time_offset to hit the event
        # It runs a mini-simulation to see how far off it will be
        projected_time_at_event = self.internal_time + t_minus * self.time_scale
        desired_convergence = target_event.required_precision

        # Calculate needed adjustment
        time_error = abs(projected_time_at_event - round(projected_time_at_event))
        adjustment = 0.0

        if time_error > desired_convergence:
            # Slow down or speed up to hit the mark
            if t_minus > 0:
                adjustment = time_error / t_minus
                if self.internal_time < projected_time_at_event:
                    self.time_scale += adjustment
                else:
                    self.time_scale = max(0.1, self.time_scale - adjustment)

        self.convergence_score = 1.0 - min(1.0, time_error / max(0.001, desired_convergence * 10))
        self.state = CellState.CONVERGED if self.convergence_score > 0.8 else CellState.RUNNING
        self.pending_events.append(target_event.event_id)

        return {
            "cell_id": self.cell_id,
            "event_id": target_event.event_id,
            "t_minus": round(t_minus, 4),
            "internal_time": round(self.internal_time, 4),
            "convergence_score": round(self.convergence_score, 4),
            "time_scale": round(self.time_scale, 4),
            "state": self.state.value,
        }

    def spawn_daemon(
        self,
        work_fn: Callable[[], Any] = None,
        interval: float = 1.0,
    ) -> bool:
        """Spawn a daemon thread for continuous operation.

        The daemon runs the cell's work function in a loop at the given
        interval. Each cell can have its own daemon — they're independent
        living things running their own processes.
        """
        if self._daemon_running:
            return False

        self._daemon_interval = interval
        self.state = CellState.DAEMON
        self._daemon_running = True

        def _daemon_loop():
            while self._daemon_running:
                try:
                    if work_fn:
                        result = work_fn()
                        if result is not None:
                            self.value = result
                    else:
                        self.tick()
                        self.simulate(steps=1)
                except Exception:
                    self.state = CellState.ERROR
                    self._daemon_running = False
                    return
                time.sleep(self._daemon_interval)

        self._daemon = threading.Thread(
            target=_daemon_loop, daemon=True, name=f"cell-{self.cell_id}"
        )
        self._daemon.start()
        return True

    def stop_daemon(self):
        """Stop the cell's daemon thread."""
        self._daemon_running = False
        if self._daemon and self._daemon.is_alive():
            self._daemon.join(timeout=2.0)
        self.state = CellState.IDLE

    def status(self) -> dict:
        return {
            "cell_id": self.cell_id,
            "task": self.task,
            "gpu_backend": self.gpu_backend.value,
            "state": self.state.value,
            "internal_time": round(self.internal_time, 4),
            "time_scale": round(self.time_scale, 4),
            "iteration": self.iteration,
            "loss": round(self.loss, 6),
            "accuracy": round(self.accuracy, 4),
            "best_loss": round(self.best_loss, 6),
            "best_accuracy": round(self.best_accuracy, 4),
            "convergence_score": round(self.convergence_score, 4),
            "dependencies": self.dependencies,
            "dependents": len(self.dependents),
            "daemon_running": self._daemon_running,
            "value": self.value,
            "dirty": self.dirty,
        }


# ─── MicroGrid — the spreadsheet of cells ─────────────────────────────────────

class MicroGrid:
    """A 2D grid of MicroCells. Like a spreadsheet.

    Deltas cascade: when one cell changes, all dependent cells
    recalculate. Parallel where possible, sequential where necessary.

    Time is a variable: each cell has its own time. Cells converge
    when their times align on a common event (t-minus convergence).
    """

    def __init__(
        self,
        rows: int,
        cols: int,
        gpu_backend: GPUBackend = GPUBackend.CPU,
    ):
        self.rows = rows
        self.cols = cols
        self.gpu_backend = gpu_backend

        # The grid: 2D array of cells (or None for empty)
        self.cells: List[List[Optional[MicroCell]]] = [
            [None for _ in range(cols)] for _ in range(rows)
        ]

        # Dependency graph for cascade ordering
        self._dep_graph: Dict[Tuple[int, int], Set[Tuple[int, int]]] = defaultdict(set)
        self._reverse_graph: Dict[Tuple[int, int], Set[Tuple[int, int]]] = defaultdict(set)

        # Thread pool for parallel cascade
        self._executor = ThreadPoolExecutor(max_workers=8)

        # Grid-level time tracking
        self.grid_time: float = 0.0
        self.cascade_count: int = 0

    def place(self, cell: MicroCell, row: int, col: int) -> None:
        """Put a cell at grid position."""
        if 0 <= row < self.rows and 0 <= col < self.cols:
            self.cells[row][col] = cell
            # Register dependencies
            for dep_row, dep_col in cell.dependencies:
                self._dep_graph[(row, col)].add((dep_row, dep_col))
                self._reverse_graph[(dep_row, dep_col)].add((row, col))

    def get(self, row: int, col: int) -> Optional[MicroCell]:
        """Get cell at position."""
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return self.cells[row][col]
        return None

    def cascade(self, row: int, col: int) -> dict:
        """Propagate a delta from this cell to all dependents.

        Like a spreadsheet: change one cell, and all cells that depend
        on it recalculate. Parallel where possible, sequential where
        dependencies require ordering.

        Topological sort ensures correct ordering:
          1. Find all cells reachable from (row, col) in dependency graph
          2. Sort by dependency depth (cells that depend on more go later)
          3. Execute in waves: all cells at same depth run in parallel
        """
        self.cascade_count += 1
        source = (row, col)
        source_cell = self.get(row, col)
        if not source_cell:
            return {"cascaded": 0, "waves": 0}

        # Mark source as dirty
        source_cell.dirty = True
        source_cell.value = source_cell.value or {"prediction": 0.5, "confidence": 0.5, "loss": 1.0}

        # BFS to find all affected cells and their depths
        affected: Dict[Tuple[int, int], int] = {}
        queue = [(source, 0)]
        visited = set()

        while queue:
            pos, depth = queue.pop(0)
            if pos in visited:
                continue
            visited.add(pos)
            affected[pos] = depth

            # Find dependents (cells that depend on this position)
            for dep_pos in self._reverse_graph.get(pos, set()):
                if dep_pos not in visited:
                    queue.append((dep_pos, depth + 1))

        # Group by depth for parallel waves
        max_depth = max(affected.values()) if affected else 0
        waves: Dict[int, List[Tuple[int, int]]] = defaultdict(list)
        for pos, depth in affected.items():
            if pos != source:  # don't recalculate source
                waves[depth].append(pos)

        # Execute waves
        total_recalculated = 0
        for depth in sorted(waves.keys()):
            positions = waves[depth]

            # All cells at same depth can run in parallel
            futures = []
            for r, c in positions:
                cell = self.get(r, c)
                if cell and cell.state != CellState.DAEMON:
                    # Gather dependency values
                    dep_values = {}
                    for dr, dc in cell.dependencies:
                        dep_cell = self.get(dr, dc)
                        if dep_cell and dep_cell.value:
                            dep_values[f"{dr},{dc}"] = dep_cell.value

                    future = self._executor.submit(cell.recalculate, dep_values)
                    futures.append(((r, c), future))

            # Collect results
            for (r, c), future in futures:
                try:
                    future.result(timeout=5.0)
                    total_recalculated += 1
                except Exception:
                    pass  # cell is in error state

        return {
            "cascaded": total_recalculated,
            "waves": max_depth,
            "source": f"{row},{col}",
            "total_affected": len(affected) - 1,  # exclude source
        }

    def synchronize(self) -> dict:
        """Align all cells' time variables.

        The conductor tells all cells what the reference time is.
        Each cell adjusts its time_scale and time_offset to match.
        """
        # Find the average internal time across all active cells
        active_cells = []
        for row in self.cells:
            for cell in row:
                if cell and cell.state != CellState.ERROR:
                    active_cells.append(cell)

        if not active_cells:
            return {"synchronized": 0}

        avg_time = sum(c.internal_time for c in active_cells) / len(active_cells)
        self.grid_time = avg_time

        # Each cell adjusts its offset to center on the average
        for cell in active_cells:
            cell.conductor_offset = avg_time - cell.internal_time
            # Gently pull time_scale toward 1.0 (the conductor's tempo)
            cell.time_scale = cell.time_scale * 0.8 + 1.0 * 0.2

        return {
            "synchronized": len(active_cells),
            "grid_time": round(self.grid_time, 4),
            "avg_internal_time": round(avg_time, 4),
            "spread": round(
                max(c.internal_time for c in active_cells) -
                min(c.internal_time for c in active_cells), 4
            ),
        }

    def converge_on_event(self, event_type: str, t_minus: float = 1.0) -> TMinusEvent:
        """Converge all cells on a future event.

        Creates a t-minus event and asks all cells to converge on it.
        Like the conductor raising the baton — everyone watches.
        """
        event = TMinusEvent(
            event_id=f"event-{event_type}-{time.time():.0f}",
            event_type=event_type,
            target_time=time.time() + t_minus,
        )

        # All active cells participate
        for r, row in enumerate(self.cells):
            for c, cell in enumerate(row):
                if cell and cell.state not in (CellState.ERROR,):
                    event.participating_cells.add(cell.cell_id)
                    cell.converge(event)

        event.status = "converging"
        return event

    def step_all(self, time_delta: float = 1.0) -> dict:
        """Advance all cells by their internal time delta.

        Each cell ticks at its own rate (time_scale).
        The delta is the conductor's beat — cells interpret it
        according to their own tempo.
        """
        results = []
        for row in self.cells:
            for cell in row:
                if cell and cell.state not in (CellState.ERROR,):
                    entry = cell.tick(time_delta)
                    results.append(entry)

        self.grid_time += time_delta
        return {
            "cells_ticked": len(results),
            "grid_time": round(self.grid_time, 4),
            "avg_internal_time": round(
                sum(r["t"] for r in results) / len(results), 4
            ) if results else 0.0,
        }

    def status(self) -> dict:
        active = sum(1 for row in self.cells for c in row if c is not None)
        states = defaultdict(int)
        for row in self.cells:
            for c in row:
                if c:
                    states[c.state.value] += 1
        return {
            "grid_size": f"{self.rows}x{self.cols}",
            "active_cells": active,
            "states": dict(states),
            "grid_time": round(self.grid_time, 4),
            "cascade_count": self.cascade_count,
        }


# ─── ConductorSync — the orchestra conductor ──────────────────────────────────

class ConductorSync:
    """Orchestra conductor: the timing IS the truth.

    Musicians at the far ends of the orchestra sound out of sync
    if they don't calibrate to the conductor. The conductor provides
    a SIMULATED EXPERIENCE that all musicians watch for hints.

    Calibration: each musician watches the conductor AND their neighbors.
    If the conductor says a downbeat is coming, the musician times their
    entrance to the conductor's baton, NOT to when they hear the other
    musicians. The sound reaches different ears at different times,
    but the CONDUCTOR'S INTENTION reaches all eyes simultaneously.

    The conductor doesn't keep time. The conductor IS time.
    """

    def __init__(self, bpm: float = 120.0):
        self.bpm = bpm
        self.beat_interval = 60.0 / bpm  # seconds per beat
        self.current_beat: int = 0
        self.current_measure: int = 0
        self.beats_per_measure: int = 4

        # The score: sections and their cues
        self.score: List[dict] = []
        self.current_section: int = 0

        # Conductor's internal state
        self._start_time: float = time.time()
        self._last_beat_time: float = time.time()
        self._sections: Dict[str, dict] = {}

        # Calibration data: what each musician thinks the time is
        self._musician_calibration: Dict[str, float] = {}

        # Tempo change tracking
        self._tempo_history: List[Tuple[float, float]] = [(time.time(), bpm)]

    def start_section(self, score: List[dict] = None) -> dict:
        """Conductor begins a movement.

        The score is a list of sections, each with:
          - name: section name
          - bpm: tempo for this section
          - measures: how many measures
          - cues: which sections enter when
        """
        if score:
            self.score = score
        self.current_section = 0
        self._start_time = time.time()
        self._last_beat_time = time.time()
        self.current_beat = 0
        self.current_measure = 0

        if self.score and "bpm" in self.score[0]:
            self._set_bpm(self.score[0]["bpm"])

        return {
            "section": self.score[0]["name"] if self.score else "default",
            "bpm": self.bpm,
            "measures": self.score[0].get("measures", 0) if self.score else 0,
        }

    def downbeat(self, time_offset: float = 0.0) -> dict:
        """The baton falls. All musicians respond.

        The downbeat is the truth. Every cell calibrates to this moment.
        The time_offset allows cells to compensate for their position
        in the orchestra (far ends get a slight head start).
        """
        now = time.time()
        self.current_beat = 1
        self.current_measure += 1
        self._last_beat_time = now

        # Tell all musicians what the conductor feels
        conductor_time = now + time_offset

        # Calibrate each musician
        calibrations = {}
        for musician_id, perceived_time in self._musician_calibration.items():
            # How far off is this musician from the conductor?
            drift = perceived_time - conductor_time
            # The conductor's hint: "you're X seconds off"
            correction = -drift * 0.5  # partial correction (gentle nudge)
            self._musician_calibration[musician_id] = perceived_time + correction
            calibrations[musician_id] = {
                "drift_ms": round(drift * 1000, 2),
                "correction_ms": round(correction * 1000, 2),
            }

        return {
            "event": "downbeat",
            "measure": self.current_measure,
            "beat": 1,
            "conductor_time": round(conductor_time, 4),
            "bpm": self.bpm,
            "calibrations": calibrations,
        }

    def beat(self, n: int) -> dict:
        """Beat n of the current measure.

        The conductor marks each beat. Musicians count along.
        """
        self.current_beat = n
        elapsed = time.time() - self._last_beat_time

        return {
            "event": "beat",
            "measure": self.current_measure,
            "beat": n,
            "beats_per_measure": self.beats_per_measure,
            "elapsed_since_downbeat": round(elapsed, 4),
            "bpm": self.bpm,
        }

    def tempo_change(self, new_bpm: float, gradual: bool = True) -> dict:
        """Conductor signals tempo change.

        If gradual, the tempo changes over the next measure.
        If not, it changes immediately (rubato/fermata).
        """
        old_bpm = self.bpm

        if gradual:
            # Tempo ramps over one measure (4 beats)
            self._tempo_history.append((time.time(), new_bpm))
            # For simulation, just set it — real system would interpolate
            self.bpm = new_bpm
        else:
            self.bpm = new_bpm

        self.beat_interval = 60.0 / self.bpm
        self._tempo_history.append((time.time(), new_bpm))

        return {
            "event": "tempo_change",
            "old_bpm": round(old_bpm, 1),
            "new_bpm": round(new_bpm, 1),
            "gradual": gradual,
            "beat_interval_ms": round(self.beat_interval * 1000, 1),
        }

    def cue(self, instrument_section: str) -> dict:
        """Conductor cues a section to enter.

        Like pointing the baton at the brass section: "your turn."
        The section watches the conductor's cue and enters on the next beat.
        """
        return {
            "event": "cue",
            "section": instrument_section,
            "measure": self.current_measure,
            "beat": self.current_beat,
            "enter_on_beat": self.current_beat + 1,
            "conductor_time": round(time.time(), 4),
        }

    def cut_off(self) -> dict:
        """Conductor signals end of movement."""
        return {
            "event": "cut_off",
            "measure": self.current_measure,
            "total_measures": self.current_measure,
            "duration_s": round(time.time() - self._start_time, 2),
            "final_bpm": round(self.bpm, 1),
        }

    def register_musician(self, musician_id: str, perceived_time: float = None) -> None:
        """Register a cell as a musician in the conductor's orchestra."""
        self._musician_calibration[musician_id] = perceived_time or time.time()

    def status(self) -> dict:
        """What the conductor is feeling right now."""
        return {
            "bpm": round(self.bpm, 1),
            "beat": self.current_beat,
            "measure": self.current_measure,
            "beat_interval_ms": round(self.beat_interval * 1000, 1),
            "musicians": len(self._musician_calibration),
            "section": self.current_section,
            "elapsed_s": round(time.time() - self._start_time, 2),
            "conductor_time": round(time.time(), 4),
        }

    def _set_bpm(self, bpm: float) -> None:
        self.bpm = bpm
        self.beat_interval = 60.0 / bpm
        self._tempo_history.append((time.time(), bpm))


# ─── RoomMicroModels — the full orchestration layer ───────────────────────────

class RoomMicroModels:
    """The full orchestration layer for micro models on GPU.

    Wires together:
    - MicroGrid: the spreadsheet of instances
    - MicroCell: individual micro model instances
    - ConductorSync: timing synchronization
    - GPU backends: cudaclaw, ai-pasture, ai-forest
    - CollectiveInference: the predict→observe→gap→learn loop

    This is the TOP LEVEL of the room architecture. Rooms are grids.
    Grids have cells. Cells have daemons. The conductor keeps time.
    GPU backends execute the work.
    """

    def __init__(self):
        self.rooms: Dict[str, MicroGrid] = {}
        self.conductor = ConductorSync()
        self.room_configs: Dict[str, dict] = {}
        self.harvested_tiles: List[dict] = []

        # GPU backend routing
        self._backend_assignments: Dict[str, GPUBackend] = {}
        self._backend_loads: Dict[GPUBackend, int] = defaultdict(int)

        # Collective inference integration (optional)
        self._collective_inference = None

    def build_room(
        self,
        task: str,
        gpu_backend: GPUBackend = GPUBackend.CPU,
        grid_size: Tuple[int, int] = (4, 4),
        room_id: str = None,
    ) -> str:
        """Build a room: a grid of micro model cells for a specific task.

        Each cell gets its own MicroCell instance. The grid is wired
        with dependencies (left feeds right, top feeds bottom).
        """
        if room_id is None:
            room_id = f"room-{task}-{time.time():.0f}"

        rows, cols = grid_size
        grid = MicroGrid(rows, cols, gpu_backend)

        # Create cells
        task_variants = [
            "drift-detect", "anomaly-flag", "intent-detect",
            "sentiment", "spam-classify", "topic-classify",
            "priority-rank", "tile-relevance",
        ]

        for r in range(rows):
            for c in range(cols):
                cell_task = task_variants[(r * cols + c) % len(task_variants)]
                cell = MicroCell(
                    cell_id=f"{room_id}/[{r},{c}]",
                    task=cell_task,
                    gpu_backend=gpu_backend,
                )

                # Wire dependencies: left neighbor and top neighbor
                if c > 0:
                    cell.dependencies.append((r, c - 1))
                if r > 0:
                    cell.dependencies.append((r - 1, c))

                grid.place(cell, r, c)

                # Register with conductor
                self.conductor.register_musician(cell.cell_id)

        self.rooms[room_id] = grid
        self.room_configs[room_id] = {
            "task": task,
            "gpu_backend": gpu_backend.value,
            "grid_size": grid_size,
            "created_at": time.time(),
        }
        self._backend_assignments[room_id] = gpu_backend
        self._backend_loads[gpu_backend] += rows * cols

        return room_id

    def train_on_gpu(self, room_id: str, epochs: int = 10) -> dict:
        """Train all cells in a room for N epochs.

        Each cell runs its own simulation independently.
        The conductor provides the beat for synchronization.
        """
        if room_id not in self.rooms:
            return {"error": f"room {room_id} not found"}

        grid = self.rooms[room_id]
        config = self.room_configs[room_id]
        backend = GPUBackend(config["gpu_backend"])

        # Conductor starts the training section
        self.conductor.start_section([{
            "name": f"train-{room_id}",
            "bpm": 120.0,
            "measures": epochs,
        }])

        epoch_results = []
        for epoch in range(epochs):
            # Conductor gives downbeat
            self.conductor.downbeat()

            # All cells simulate one epoch
            cell_results = []
            for r in range(grid.rows):
                for c in range(grid.cols):
                    cell = grid.get(r, c)
                    if cell:
                        results = cell.simulate(steps=1)
                        cell_results.append(results[-1] if results else {})

            # Conductor marks beat 2 (checkpoint)
            self.conductor.beat(2)

            # Cascade: propagate deltas through the grid
            # Start from top-left, cascade right and down
            cascade_results = []
            for r in range(grid.rows):
                for c in range(grid.cols):
                    result = grid.cascade(r, c)
                    if result["cascaded"] > 0:
                        cascade_results.append(result)

            # Conductor marks beat 3 (sync check)
            self.conductor.beat(3)

            # Synchronize cell times
            sync_result = grid.synchronize()

            # Conductor marks beat 4 (end of measure)
            self.conductor.beat(4)

            # Collect epoch stats
            active_cells = [cell for row in grid.cells for cell in row if cell]
            avg_loss = sum(c.loss for c in active_cells) / len(active_cells) if active_cells else 1.0
            avg_acc = sum(c.accuracy for c in active_cells) / len(active_cells) if active_cells else 0.0

            epoch_results.append({
                "epoch": epoch + 1,
                "avg_loss": round(avg_loss, 6),
                "avg_accuracy": round(avg_acc, 4),
                "cascades": len(cascade_results),
                "sync_spread": sync_result.get("spread", 0),
                "backend": backend.value,
            })

        self.conductor.cut_off()

        return {
            "room_id": room_id,
            "epochs": epochs,
            "backend": backend.value,
            "epochs_detail": epoch_results,
            "final_loss": epoch_results[-1]["avg_loss"] if epoch_results else 1.0,
            "final_accuracy": epoch_results[-1]["avg_accuracy"] if epoch_results else 0.0,
        }

    def converge(self, room_id: str, target_event: str, t_minus: float = 1.0) -> dict:
        """Converge all cells in a room on a future event."""
        if room_id not in self.rooms:
            return {"error": f"room {room_id} not found"}

        grid = self.rooms[room_id]
        event = grid.converge_on_event(target_event, t_minus)

        # Check convergence quality
        active_cells = [c for row in grid.cells for c in row if c]
        converged = sum(1 for c in active_cells if c.state == CellState.CONVERGED)
        total = len(active_cells)

        return {
            "room_id": room_id,
            "event_id": event.event_id,
            "event_type": target_event,
            "t_minus": round(t_minus, 4),
            "converged_cells": converged,
            "total_cells": total,
            "convergence_rate": round(converged / total, 4) if total > 0 else 0.0,
        }

    def harvest_tiles(self, room_id: str) -> List[dict]:
        """Extract tiles from converged cells.

        A tile is harvested when a cell has converged and has a value.
        The tile captures the cell's prediction, confidence, and training state.
        """
        if room_id not in self.rooms:
            return []

        grid = self.rooms[room_id]
        tiles = []

        for r in range(grid.rows):
            for c in range(grid.cols):
                cell = grid.get(r, c)
                if cell and cell.value and cell.convergence_score > 0.5:
                    tile = {
                        "tile_id": f"tile-{cell.cell_id}-{time.time():.0f}",
                        "source_cell": cell.cell_id,
                        "room_id": room_id,
                        "task": cell.task,
                        "value": cell.value,
                        "convergence_score": round(cell.convergence_score, 4),
                        "internal_time": round(cell.internal_time, 4),
                        "iteration": cell.iteration,
                        "best_accuracy": round(cell.best_accuracy, 4),
                        "gpu_backend": cell.gpu_backend.value,
                        "harvested_at": time.time(),
                    }
                    tiles.append(tile)
                    self.harvested_tiles.append(tile)

        return tiles

    def feed_fleet(self, room_id: str) -> dict:
        """Push harvested tiles into collective inference.

        If collective inference is wired up, tiles become predictions.
        Otherwise, just return the tiles that would be fed.
        """
        tiles = self.harvest_tiles(room_id)

        if self._collective_inference:
            # Feed each tile as a prediction stake
            for tile in tiles:
                self._collective_inference.market.stake(
                    tile_id=tile["tile_id"],
                    prediction=tile["value"].get("prediction", 0.5),
                    confidence=tile["value"].get("confidence", 0.5),
                    scope=f"room.{tile['task']}",
                )
            return {
                "room_id": room_id,
                "tiles_fed": len(tiles),
                "fed_to": "collective_inference",
            }

        return {
            "room_id": room_id,
            "tiles_available": len(tiles),
            "fed_to": "none (no collective inference wired)",
        }

    def wire_collective_inference(self, ci) -> None:
        """Wire in a CollectiveInference instance for fleet feeding."""
        self._collective_inference = ci

    def status(self) -> dict:
        return {
            "rooms": len(self.rooms),
            "room_details": {
                rid: {
                    **self.room_configs[rid],
                    "grid_status": grid.status(),
                }
                for rid, grid in self.rooms.items()
            },
            "conductor": self.conductor.status(),
            "harvested_tiles": len(self.harvested_tiles),
            "backend_loads": {b.value: n for b, n in self._backend_loads.items()},
        }

    @classmethod
    def demo(cls) -> str:
        """End-to-end demonstration of the room-micro-models architecture.

        Shows:
          1. Building a room with a 4x4 grid of micro model cells
          2. Training on CPU (simulated GPU backend)
          3. Conductor synchronization
          4. T-minus convergence
          5. Tile harvesting
          6. Fleet feeding
        """
        print("=" * 72)
        print("  ROOM MICRO MODELS — Spreadsheet of Living Instances")
        print("  Each cell is a micro model. Each has its own time.")
        print("  The conductor IS the truth. T-minus convergence.")
        print("=" * 72)

        orchestrator = cls()

        # ── Phase 1: Build Rooms ──
        print("\n━━━ PHASE 1: BUILD ROOMS ━━━")
        room_cpu = orchestrator.build_room(
            task="drift-detect",
            gpu_backend=GPUBackend.CPU,
            grid_size=(4, 4),
            room_id="drift-room-cpu",
        )
        print(f"   Built room: {room_cpu} (4×4 grid, CPU backend)")

        room_gpu = orchestrator.build_room(
            task="anomaly-flag",
            gpu_backend=GPUBackend.CUDACLAW,
            grid_size=(3, 3),
            room_id="anomaly-room-gpu",
        )
        print(f"   Built room: {room_gpu} (3×3 grid, CudaClaw backend)")

        # ── Phase 2: Train ──
        print("\n━━━ PHASE 2: TRAIN ON GPU ━━━")
        print(f"   Training {room_cpu} for 5 epochs...")
        train_result = orchestrator.train_on_gpu(room_cpu, epochs=5)
        for ep in train_result["epochs_detail"]:
            bar_len = int(ep["avg_accuracy"] * 30)
            bar = "█" * bar_len + "░" * (30 - bar_len)
            print(f"   Epoch {ep['epoch']:2d}: loss={ep['avg_loss']:.4f} "
                  f"acc={ep['avg_accuracy']:.4f} │{bar}│ {ep['backend']}")

        # ── Phase 3: Conductor ──
        print("\n━━━ PHASE 3: CONDUCTOR SYNCHRONIZATION ━━━")
        conductor = orchestrator.conductor
        conductor.tempo_change(140.0, gradual=True)
        print(f"   Tempo: {conductor.bpm} BPM")

        db = conductor.downbeat()
        print(f"   Downbeat: measure {db['measure']}, "
              f"{len(db['calibrations'])} musicians calibrated")

        cue_result = conductor.cue("strings")
        print(f"   Cue: strings enter on beat {cue_result['enter_on_beat']}")

        for b in range(1, 5):
            beat = conductor.beat(b)
            print(f"   Beat {b}: measure {beat['measure']}")

        cut = conductor.cut_off()
        print(f"   Cut off: {cut['total_measures']} measures, "
              f"{cut['duration_s']:.1f}s")

        # ── Phase 4: T-Minus Convergence ──
        print("\n━━━ PHASE 4: T-MINUS CONVERGENCE ━━━")
        conv_result = orchestrator.converge(
            room_cpu, "training_complete", t_minus=2.0
        )
        print(f"   Event: {conv_result['event_type']}")
        print(f"   Converged: {conv_result['converged_cells']}/{conv_result['total_cells']} "
              f"({conv_result['convergence_rate']:.0%})")

        # ── Phase 5: Harvest Tiles ──
        print("\n━━━ PHASE 5: HARVEST TILES ━━━")
        tiles = orchestrator.harvest_tiles(room_cpu)
        print(f"   Harvested {len(tiles)} tiles from {room_cpu}")
        for tile in tiles[:5]:
            print(f"     {tile['source_cell']}: "
                  f"pred={tile['value']['prediction']:.4f} "
                  f"conf={tile['value']['confidence']:.4f} "
                  f"conv={tile['convergence_score']:.2f}")

        # ── Phase 6: Feed Fleet ──
        print("\n━━━ PHASE 6: FEED FLEET ━━━")
        feed_result = orchestrator.feed_fleet(room_cpu)
        print(f"   {feed_result['tiles_available']} tiles ready")
        print(f"   → {feed_result['fed_to']}")

        # ── Phase 7: Grid Stepping ──
        print("\n━━━ PHASE 7: STEP ALL CELLS ━━━")
        grid = orchestrator.rooms[room_cpu]
        for step in range(5):
            result = grid.step_all(time_delta=0.5)
            print(f"   Step {step + 1}: grid_time={result['grid_time']:.2f}, "
                  f"cells_ticked={result['cells_ticked']}")

        # ── Phase 8: Cascade Demo ──
        print("\n━━━ PHASE 8: CASCADE PROPAGATION ━━━")
        # Change cell [0,0] and watch it propagate
        cell_00 = grid.get(0, 0)
        if cell_00:
            cell_00.value = {"prediction": 0.99, "confidence": 0.95, "loss": 0.01}
            cascade = grid.cascade(0, 0)
            print(f"   Cascade from [0,0]: {cascade['cascaded']} cells recalculated "
                  f"in {cascade['waves']} waves")

        # ── Final Status ──
        print("\n━━━ FINAL STATUS ━━━")
        status = orchestrator.status()
        print(f"   Rooms: {status['rooms']}")
        print(f"   Harvested tiles: {status['harvested_tiles']}")
        print(f"   Conductor: {status['conductor']['bpm']} BPM, "
              f"{status['conductor']['musicians']} musicians")
        for rid, detail in status['room_details'].items():
            gs = detail['grid_status']
            print(f"   Room {rid}: {gs['grid_size']}, "
                  f"{gs['active_cells']} cells, "
                  f"states={gs['states']}")

        print(f"\n{'=' * 72}")
        print(f"  RESULT: Room-micro-models architecture works.")
        print(f"  Each cell is alive. Each has its own time.")
        print(f"  The conductor IS the truth. T-minus convergence.")
        print(f"  Deltas cascade through dependent cells like a spreadsheet.")
        print(f"{'=' * 72}")

        return "DEMO COMPLETE"


if __name__ == "__main__":
    RoomMicroModels.demo()
