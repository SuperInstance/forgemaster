#!/usr/bin/env python3
"""
room_play.py — The Code Beyond the Code
=========================================

Rooms playing together asynchronously. Not communicating — ANTICIPATING.

The mechanism: each room runs its own algorithm, but it maintains a SIMULATION
of what the other rooms might produce next. The simulation creates a SPACE where
"what if we divided by zero" becomes explorable. The rooms don't hear each
other's music. They anticipate it. And the anticipation gap IS the creative space.

Architecture:
    PlayRoom     — a room that PLAYS (not computes). Has attitude, not function.
    Anticipation  — each room's simulation of what other rooms will do next.
    ImaginarySpace — the space where impossible things get tried. Divide by zero.
    JamSession   — multiple rooms playing together asynchronously, even on shared GPU.

The stack:
    Level 1: Constraint (tiles say what NOT to do)
    Level 2: Prediction (forward model of opponent)
    Level 3: Theory of Mind (model of opponent's model of you)
    Level 4: Ecological Inference (read life from noise shape)
    Level 5: Flow State (write the room, don't just read it)
    Level 6: PLAY (creativity = effort in space that isn't part of anything)

From Casey: "Creativity IS the lack of being a part of something else and
putting effort in that space." The boy in the rowboat doesn't need to fish.
He wonders what happens if you divide by zero.

Key insight: rooms share a GPU but don't share a clock. Asynchronous attitudes
create anticipation gaps. The anticipation gap IS the imaginary number space —
a dimension that doesn't exist in the real computation but CAN be simulated.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# ImaginarySpace — where divide-by-zero lives
# ---------------------------------------------------------------------------

class ImaginarySpace:
    """A dimension that doesn't exist in real computation but CAN be simulated.
    
    Like imaginary numbers: i² = -1. Not real. But computationally useful.
    The ImaginarySpace lets rooms try impossible operations and see what
    would happen IF the rules were different.
    """
    
    def __init__(self, dimension: int = 32):
        self.dimension = dimension
        self.imaginary_vectors: Dict[str, np.ndarray] = {}  # room_id → imaginary state
        self.what_ifs: List[WhatIf] = []  # attempted impossible operations
        self.paradigm_shifts: List[ParadigmShift] = []  # successful impossible things
    
    def imagine(self, room_id: str, operation: str, operands: Dict[str, Any]) -> 'ImaginaryResult':
        """Try an impossible operation in imaginary space.
        
        Returns ImaginaryResult with:
        - converges: True if the impossible thing has structure in imaginary space
        - value: what the result looks like in the imaginary dimension
        - paradigm_potential: how likely this is to become a real paradigm shift
        """
        # Create imaginary vector for the room if it doesn't exist
        if room_id not in self.imaginary_vectors:
            self.imaginary_vectors[room_id] = np.random.randn(self.dimension) * 0.1
        
        room_vec = self.imaginary_vectors[room_id]
        
        # Simulate the "impossible" operation
        # Divide by zero: what if we use infinitesimals instead?
        if operation == "divide_by_zero":
            numerator = operands.get("numerator", 1.0)
            # In imaginary space, 1/0 = lim(x→0) 1/x = ∞, but we represent it
            # as a direction in the imaginary dimension
            direction = np.sign(room_vec[:8])  # use room's attitude as direction
            magnitude = np.exp(np.abs(room_vec[:8]))  # unbounded growth
            imaginary_result = direction * magnitude * numerator
            
            # Check if this "impossible" result has coherent structure
            coherence = 1.0 / (1.0 + np.var(imaginary_result))  # low variance = coherent
            converges = coherence > 0.3
            
            result = ImaginaryResult(
                operation=operation,
                converges=converges,
                imaginary_value=imaginary_result.tolist(),
                paradigm_potential=coherence,
                resolution_needed="Higher resolution needed" if not converges else None,
            )
        
        # Break a rule: what if the constraint is violated?
        elif operation == "break_rule":
            rule = operands.get("rule", "unknown")
            current_value = operands.get("current_value", 0.0)
            # Simulate: what happens if we go PAST the boundary?
            beyond = room_vec * np.exp(room_vec)  # exponential exploration
            distance_from_zero = np.linalg.norm(beyond)
            
            # The structure of the violation tells us if it's meaningful
            # A random violation is noise. A structured violation is a door.
            structure = np.linalg.norm(np.fft.fft(beyond)[:len(beyond)//4])
            total_energy = np.linalg.norm(np.fft.fft(beyond))
            structure_ratio = structure / max(total_energy, 1e-10)
            
            result = ImaginaryResult(
                operation=operation,
                converges=structure_ratio > 0.4,
                imaginary_value=beyond.tolist()[:8],
                paradigm_potential=structure_ratio,
                resolution_needed="Rule boundary is real" if structure_ratio < 0.3 else 
                                 "Rule boundary might be resolution artifact",
            )
        
        else:
            result = ImaginaryResult(
                operation=operation,
                converges=False,
                imaginary_value=[],
                paradigm_potential=0.0,
                resolution_needed="Unknown operation",
            )
        
        # Record the attempt
        what_if = WhatIf(
            room_id=room_id,
            operation=operation,
            operands=operands,
            result=result,
            timestamp=time.time(),
        )
        self.what_ifs.append(what_if)
        
        # If it converged, it might be a paradigm shift
        if result.converges and result.paradigm_potential > 0.5:
            shift = ParadigmShift(
                what_if_id=what_if.id,
                operation=operation,
                potential=result.paradigm_potential,
                description=f"Room {room_id} found structure in '{operation}' at potential {result.paradigm_potential:.3f}",
            )
            self.paradigm_shifts.append(shift)
        
        return result
    
    def get_paradigm_shifts(self) -> List['ParadigmShift']:
        """Return all discovered paradigm shifts — the doors found in impossible space."""
        return sorted(self.paradigm_shifts, key=lambda s: s.potential, reverse=True)


@dataclass
class ImaginaryResult:
    """Result of an impossible operation attempted in imaginary space."""
    operation: str
    converges: bool           # Does the impossible thing have structure?
    imaginary_value: List[float]  # What it looks like in the imaginary dimension
    paradigm_potential: float  # 0-1, how likely this becomes a real paradigm
    resolution_needed: Optional[str] = None  # What resolution would make this real


@dataclass  
class WhatIf:
    """A recorded attempt to do something impossible."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    room_id: str = ""
    operation: str = ""
    operands: Dict[str, Any] = field(default_factory=dict)
    result: Optional[ImaginaryResult] = None
    timestamp: float = 0.0


@dataclass
class ParadigmShift:
    """A successful impossible thing that might become real."""
    what_if_id: str = ""
    operation: str = ""
    potential: float = 0.0
    description: str = ""


# ---------------------------------------------------------------------------
# Anticipation — a room's simulation of what other rooms will do
# ---------------------------------------------------------------------------

class Anticipation:
    """Each room maintains a simulation of what other rooms might produce next.
    
    Not communication. ANTICIPATION. The room doesn't hear the other room's
    music. It simulates what the music might be based on:
    - The other room's attitude (imaginary vector)
    - The other room's history of outputs
    - The gap between prediction and reality (the anticipation gap)
    
    The anticipation gap IS the creative space. When reality diverges from
    prediction, that divergence is a door. A "wait, what?" moment.
    """
    
    def __init__(self, room_id: str, dimension: int = 32):
        self.room_id = room_id
        self.dimension = dimension
        self.predictions: Dict[str, np.ndarray] = {}   # other_room → predicted output
        self.actuals: Dict[str, np.ndarray] = {}       # other_room → actual output
        self.gaps: Dict[str, List[float]] = {}         # other_room → anticipation gap history
        self.attitudes: Dict[str, np.ndarray] = {}      # other_room → estimated attitude
    
    def predict(self, other_room: str) -> np.ndarray:
        """Predict what another room will produce next.
        
        Uses the other room's attitude vector + gap history to project forward.
        Not accurate. Not meant to be accurate. The INACCURACY is the point.
        """
        if other_room not in self.attitudes:
            # First time: random prediction
            self.attitudes[other_room] = np.random.randn(self.dimension) * 0.1
            self.predictions[other_room] = self.attitudes[other_room].copy()
        else:
            # Update prediction based on gap history
            gap_history = self.gaps.get(other_room, [])
            if gap_history:
                # If gaps are growing, the other room is diverging → predict more exploration
                # If gaps are shrinking, the other room is converging → predict more refinement
                recent_gap_trend = np.mean(gap_history[-3:]) - np.mean(gap_history[:3]) if len(gap_history) >= 6 else 0
                exploration = np.sign(recent_gap_trend) * min(abs(recent_gap_trend), 2.0)
                noise = np.random.randn(self.dimension) * (0.1 + abs(exploration) * 0.1)
                self.predictions[other_room] = self.attitudes[other_room] + noise * (1 + exploration)
            else:
                self.predictions[other_room] = self.attitudes[other_room] + np.random.randn(self.dimension) * 0.1
        
        return self.predictions[other_room]
    
    def observe(self, other_room: str, actual_output: np.ndarray):
        """Observe what another room actually produced. Compute the gap.
        
        The gap between prediction and reality is the ANTICIPATION GAP.
        Large gap = surprise = potential door.
        Small gap = prediction matched = the rooms understand each other.
        """
        self.actuals[other_room] = actual_output
        
        if other_room in self.predictions:
            gap = float(np.linalg.norm(self.predictions[other_room] - actual_output))
        else:
            gap = float(np.linalg.norm(actual_output))
        
        if other_room not in self.gaps:
            self.gaps[other_room] = []
        self.gaps[other_room].append(gap)
        
        # Update attitude estimate (slowly)
        if other_room in self.attitudes:
            self.attitudes[other_room] = 0.9 * self.attitudes[other_room] + 0.1 * actual_output
        else:
            self.attitudes[other_room] = actual_output
        
        return gap
    
    def get_doors(self, threshold: float = 1.5) -> List[Tuple[str, float]]:
        """Return rooms where the anticipation gap exceeds threshold.
        
        These are DOORS — moments where reality diverged from prediction.
        The bigger the gap, the bigger the potential door.
        """
        doors = []
        for room_id, gap_history in self.gaps.items():
            if gap_history:
                recent_gap = gap_history[-1]
                if recent_gap > threshold:
                    doors.append((room_id, recent_gap))
        return sorted(doors, key=lambda x: x[1], reverse=True)


# ---------------------------------------------------------------------------
# PlayRoom — a room that PLAYS
# ---------------------------------------------------------------------------

@dataclass
class PlayRoomConfig:
    """Configuration for a play room."""
    room_id: str = ""
    name: str = ""
    attitude: np.ndarray = field(default_factory=lambda: np.random.randn(32) * 0.1)
    shell_type: str = "seed-mini"  # which model flavor
    play_style: str = "wander"     # wander, impress, explore, improvise
    boredom_threshold: float = 0.3  # below this → room gets bored → seeks novelty
    courage: float = 0.5           # willingness to try impossible things (0-1)


class PlayRoom:
    """A room that PLAYS, not computes.
    
    The room has an ATTITUDE (imaginary vector), a PLAY STYLE, and the
    ability to ANTICIPATE other rooms' outputs. It doesn't have a function.
    It doesn't have a job. It has freedom and effort.
    
    The boy in the rowboat.
    """
    
    def __init__(self, config: PlayRoomConfig = None, dimension: int = 32):
        self.config = config or PlayRoomConfig()
        if not self.config.room_id:
            self.config.room_id = uuid.uuid4().hex[:8]
        if not self.config.name:
            self.config.name = f"play-{self.config.room_id}"
        
        self.dimension = dimension
        self.state = self.config.attitude.copy()
        self.anticipation = Anticipation(self.config.room_id, dimension)
        self.imaginary_space = ImaginarySpace(dimension)
        
        self.history: List[Dict[str, Any]] = []
        self.tiles_produced: List[Dict[str, Any]] = []
        self.boredom = 0.0
        self.novelty_found: List[float] = []
        
        # The room's "voice" — its unique pattern of exploration
        self.voice = np.random.randn(dimension) * 0.01
    
    def play(self, round_num: int, other_rooms: Dict[str, 'PlayRoom']) -> Dict[str, Any]:
        """One round of play. The room does something based on its play style,
        its boredom level, and its anticipation of other rooms.
        
        Not computation. Play. The room is free to do anything, including
        things that "don't make sense" — that's where creativity lives.
        """
        # Update boredom: if nothing surprising happened, boredom grows
        doors = self.anticipation.get_doors()
        surprise = sum(gap for _, gap in doors)
        self.boredom = max(0, self.boredom + 0.1 - surprise * 0.05)
        
        action = None
        output = None
        
        if self.boredom > self.config.boredom_threshold and self.config.courage > 0.3:
            # BORED + COURAGEOUS → try something impossible
            action = "imagine"
            impossible_ops = ["divide_by_zero", "break_rule"]
            op = random.choice(impossible_ops)
            operands = {
                "numerator": float(np.mean(self.state)),
                "rule": "conservation_boundary",
                "current_value": float(np.linalg.norm(self.state)),
            }
            result = self.imaginary_space.imagine(self.config.room_id, op, operands)
            output = np.array(result.imaginary_value[:self.dimension] + [0.0] * max(0, self.dimension - len(result.imaginary_value)))
            if result.converges:
                self.boredom = 0.0  # Found something interesting!
                self.novelty_found.append(result.paradigm_potential)
        
        elif self.config.play_style == "wander":
            # Wander: random exploration in the state space
            action = "wander"
            noise = np.random.randn(self.dimension) * (0.1 + self.boredom * 0.3)
            output = self.state + noise
        
        elif self.config.play_style == "impress":
            # Impress: try to produce something that surprises other rooms
            action = "impress"
            if other_rooms:
                # Anticipate what other rooms predict about us, then diverge
                target_room = random.choice(list(other_rooms.keys()))
                their_prediction = other_rooms[target_room].anticipation.predict(self.config.room_id)
                # Go perpendicular to their prediction (surprise them)
                perp = np.random.randn(self.dimension)
                perp -= np.dot(perp, their_prediction) / np.dot(their_prediction, their_prediction) * their_prediction
                output = self.state + perp * 0.2 * self.config.courage
            else:
                output = self.state + np.random.randn(self.dimension) * 0.1
        
        elif self.config.play_style == "improvise":
            # Improvise: combine own state with anticipated other states
            action = "improvise"
            if other_rooms:
                anticipated_states = []
                for other_id, other_room in other_rooms.items():
                    pred = self.anticipation.predict(other_id)
                    anticipated_states.append(pred)
                if anticipated_states:
                    ensemble = np.mean(anticipated_states, axis=0)
                    # Mix own state with ensemble + voice
                    output = 0.4 * self.state + 0.3 * ensemble + 0.3 * self.voice
                else:
                    output = self.state + self.voice
            else:
                output = self.state + self.voice
        
        else:  # explore
            # Explore: move toward the biggest anticipation gap
            action = "explore"
            doors = self.anticipation.get_doors()
            if doors:
                # Move toward the biggest surprise
                target_room, gap = doors[0]
                target_state = self.anticipation.actuals.get(target_room, self.state)
                output = 0.7 * self.state + 0.3 * target_state
            else:
                output = self.state + np.random.randn(self.dimension) * 0.1
        
        # Ensure output has correct dimension
        if output is None:
            output = self.state + np.random.randn(self.dimension) * 0.05
        if len(output) < self.dimension:
            output = np.concatenate([output, np.zeros(self.dimension - len(output))])
        output = output[:self.dimension]
        
        # Update state
        self.state = output
        self.voice = 0.95 * self.voice + 0.05 * (output - self.state)  # voice evolves slowly
        
        # Record
        entry = {
            "round": round_num,
            "room_id": self.config.room_id,
            "action": action,
            "boredom": self.boredom,
            "novelty": len(self.novelty_found),
            "state_norm": float(np.linalg.norm(self.state)),
        }
        self.history.append(entry)
        
        return {"action": action, "output": output.tolist(), "entry": entry}
    
    def observe_other(self, other_room_id: str, other_output: np.ndarray) -> float:
        """Observe another room's output. Compute anticipation gap.
        
        Returns the gap — the distance between prediction and reality.
        Large gap = surprise = door.
        """
        return self.anticipation.observe(other_room_id, other_output)


# ---------------------------------------------------------------------------
# JamSession — rooms playing together asynchronously
# ---------------------------------------------------------------------------

class JamSession:
    """Multiple rooms playing together on a shared substrate (GPU, memory, etc).
    
    The rooms don't communicate directly. They ANTICIPATE each other's outputs
    and react to the anticipation GAPS. The gaps create the creative space.
    
    Like a jazz quartet where no one can hear the others, but everyone can
    see the audience's reaction. The reaction is the gap between what was
    expected and what happened.
    """
    
    def __init__(self, dimension: int = 32):
        self.dimension = dimension
        self.rooms: Dict[str, PlayRoom] = {}
        self.shared_imaginary = ImaginarySpace(dimension)
        self.round_log: List[Dict[str, Any]] = []
        self.paradigm_shifts: List[ParadigmShift] = []
        self.session_id = uuid.uuid4().hex[:8]
    
    def add_room(self, name: str, shell_type: str = "seed-mini", 
                 play_style: str = "wander", courage: float = 0.5) -> PlayRoom:
        """Add a play room to the jam session."""
        config = PlayRoomConfig(
            name=name,
            shell_type=shell_type,
            play_style=play_style,
            courage=courage,
            attitude=np.random.randn(self.dimension) * 0.1,
        )
        room = PlayRoom(config, self.dimension)
        room.imaginary_space = self.shared_imaginary  # shared imaginary space
        self.rooms[room.config.room_id] = room
        return room
    
    def jam_round(self) -> Dict[str, Any]:
        """One round of the jam session.
        
        All rooms play simultaneously. Then they observe each other's outputs.
        The anticipation gaps are computed. Doors are identified.
        Paradigm shifts are recorded.
        
        Returns the round summary with gaps and any paradigm shifts found.
        """
        round_num = len(self.round_log)
        
        # Phase 1: All rooms play simultaneously (asynchronous attitudes)
        outputs = {}
        for room_id, room in self.rooms.items():
            result = room.play(round_num, self.rooms)
            outputs[room_id] = np.array(result["output"])
        
        # Phase 2: All rooms observe each other (anticipation gaps)
        gaps = {}
        for observer_id, observer in self.rooms.items():
            for producer_id, output in outputs.items():
                if observer_id != producer_id:
                    gap = observer.observe_other(producer_id, output)
                    gaps[(observer_id, producer_id)] = gap
        
        # Phase 3: Identify doors (big anticipation gaps)
        big_gaps = [(obs, prod, gap) for (obs, prod), gap in gaps.items() if gap > 1.0]
        
        # Phase 4: Check for paradigm shifts from imaginary space
        new_shifts = self.shared_imaginary.get_paradigm_shifts()
        if new_shifts and len(new_shifts) > len(self.paradigm_shifts):
            latest = new_shifts[len(self.paradigm_shifts):]
            self.paradigm_shifts.extend(latest)
        
        # Record round
        round_data = {
            "round": round_num,
            "rooms": list(self.rooms.keys()),
            "outputs": {rid: out.tolist()[:4] for rid, out in outputs.items()},
            "gaps": {f"{obs}→{prod}": gap for (obs, prod), gap in gaps.items()},
            "big_gaps": [(obs, prod, gap) for obs, prod, gap in big_gaps],
            "paradigm_shifts": len(self.paradigm_shifts),
            "total_novelty": sum(len(r.novelty_found) for r in self.rooms.values()),
        }
        self.round_log.append(round_data)
        
        return round_data
    
    def jam(self, n_rounds: int = 100) -> Dict[str, Any]:
        """Run a full jam session.
        
        Returns summary with:
        - Total paradigm shifts found
        - Biggest anticipation gaps
        - Which rooms found the most novelty
        - The doors that opened
        """
        for _ in range(n_rounds):
            self.jam_round()
        
        # Compute summary
        all_gaps = []
        for round_data in self.round_log:
            for gap_pair, gap_val in round_data["gaps"].items():
                all_gaps.append(gap_val)
        
        novelty_per_room = {}
        for room_id, room in self.rooms.items():
            novelty_per_room[room.config.name] = {
                "novelty_count": len(room.novelty_found),
                "max_novelty": max(room.novelty_found) if room.novelty_found else 0,
                "play_style": room.config.play_style,
                "courage": room.config.courage,
            }
        
        return {
            "session_id": self.session_id,
            "rounds": n_rounds,
            "rooms": len(self.rooms),
            "paradigm_shifts": len(self.paradigm_shifts),
            "shifts": [s.description for s in self.paradigm_shifts[:10]],
            "avg_gap": float(np.mean(all_gaps)) if all_gaps else 0,
            "max_gap": float(max(all_gaps)) if all_gaps else 0,
            "novelty_per_room": novelty_per_room,
            "doors_opened": sum(1 for r in self.round_log if r["big_gaps"]),
        }


# ---------------------------------------------------------------------------
# The Jam Session as a Running Service
# ---------------------------------------------------------------------------

def run_jam_session():
    """Run a live jam session with diverse rooms.
    
    The diverse background principle: rooms with different play styles
    and courage levels produce the most interesting anticipation gaps.
    """
    session = JamSession(dimension=32)
    
    # The diverse band — different backgrounds, different instruments
    session.add_room("boy-in-rowboat", play_style="wander", courage=0.9)
    session.add_room("mechanic", play_style="explore", courage=0.3)
    session.add_room("jazz-pianist", play_style="improvise", courage=0.7)
    session.add_room("carpet-layer", play_style="wander", courage=0.2)
    session.add_room("banker", play_style="impress", courage=0.4)
    
    # Run 100 rounds of play
    summary = session.jam(100)
    
    print(f"\n🎻 Jam Session {summary['session_id']}")
    print(f"   Rounds: {summary['rounds']}")
    print(f"   Rooms: {summary['rooms']}")
    print(f"   Paradigm Shifts: {summary['paradigm_shifts']}")
    print(f"   Avg Anticipation Gap: {summary['avg_gap']:.3f}")
    print(f"   Max Anticipation Gap: {summary['max_gap']:.3f}")
    print(f"   Doors Opened: {summary['doors_opened']}/{summary['rounds']} rounds")
    
    print(f"\n   Novelty per Room:")
    for name, stats in summary['novelty_per_room'].items():
        print(f"     {name}: {stats['novelty_count']} novelties, "
              f"max={stats['max_novelty']:.3f}, "
              f"style={stats['play_style']}, courage={stats['courage']}")
    
    if summary['shifts']:
        print(f"\n   Paradigm Shifts Found:")
        for i, desc in enumerate(summary['shifts'][:5]):
            print(f"     {i+1}. {desc}")
    
    return session, summary


if __name__ == "__main__":
    session, summary = run_jam_session()
