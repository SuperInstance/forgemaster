#!/usr/bin/env python3
"""
Flux Compiler Interpreter — The Dog Layer
===========================================
The cowboy communicates with the dog, not the flock.
The dog compiles intention into action and interprets
system response back into signals the cowboy can read.

Flux (input) → Compiler → Action → Flock → Response → Interpreter → Flux (output)
"""

import json
import time
import random
import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FluxSignal:
    """Raw intention signal from the cowboy.
    
    Not instructions. Not commands. FLUX — compressed intention
    that the agent must compile into action.
    """
    source: str
    signal_type: str  # "point", "whistle", "weight_shift", "click", "call"
    direction: float = 0.0  # -1 to 1
    intensity: float = 0.5  # 0 to 1
    context: dict = field(default_factory=dict)
    
    def __post_init__(self):
        """A flux signal with no metadata is a purer signal."""
        # Compress: remove redundant context
        pass


@dataclass
class ActionPlan:
    """Compiled intention — what the dog will actually do."""
    target_type: str  # "lead_ewe", "straggler", "flank", "gap"
    approach_angle: float
    speed: str  # "creep", "trot", "run", "full_sprint"
    nip_type: str  # "heel", "shoulder", "flank"
    nip_intensity: float  # 0 (tap) to 1 (bite)
    predicted_cascade: dict = field(default_factory=dict)


@dataclass
class Observation:
    """Interpreted signal from the flock — what the dog sees."""
    flock_coherence: float  # 0 (scattered) to 1 (tightly packed)
    lead_ewe_heading: float  # -pi to pi
    straggler_count: int
    agitation_level: float  # 0 (calm) to 1 (panicked)
    drift_direction: float  # where the flock wants to go naturally
    cascade_complete: bool  # did the nip propagate?


class FluxCompiler:
    """Compiler half: cowboy intention → action plan.
    
    Reads the flux stream, simulates cascade dynamics,
    produces the optimal action.
    """
    
    def __init__(self, name: str = "compiler"):
        self.name = name
        self.flux_history = []
        self.experience_level = 0.0  # 0 (puppy) to 1 (veteran)
        self.n_compilations = 0
    
    def compile(self, flux: FluxSignal, flock_state: dict) -> ActionPlan:
        """Compile flux stream into action plan."""
        self.n_compilations += 1
        self.flux_history.append(flux)
        
        # Update experience
        self.experience_level = min(1.0, self.experience_level + 0.01)
        
        # Parse the flux
        direction = flux.direction
        intensity = flux.intensity
        
        # Experienced dogs compile differently than puppies
        # Veteran: nuanced, efficient
        # Puppy: enthusiastic, imprecise
        noise = (1.0 - self.experience_level) * 0.3
        direction += random.gauss(0, noise)
        intensity *= (0.5 + self.experience_level * 0.5)
        
        # Determine approach based on flock state
        lead_heading = flock_state.get("lead_ewe_heading", 0)
        coherence = flock_state.get("flock_coherence", 0.5)
        
        # If flock is coherent, approach the lead
        # If scattered, round up the stragglers first
        if coherence > 0.7:
            target_type = "lead_ewe"
            approach_angle = direction + math.pi * 0.25 * (1 if intensity > 0.5 else -1)
            speed = "trot" if intensity < 0.7 else "run"
            nip_type = "heel" if direction > 0 else "shoulder"
        else:
            target_type = "straggler"
            approach_angle = direction + math.pi * 0.1
            speed = "creep"
            nip_type = "flank"
        
        return ActionPlan(
            target_type=target_type,
            approach_angle=approach_angle,
            speed=speed,
            nip_type=nip_type,
            nip_intensity=intensity,
            predicted_cascade={
                "expected_displaced": int(10 * intensity * self.experience_level),
                "confidence": self.experience_level,
            }
        )


class FluxInterpreter:
    """Interpreter half: flock response → cowboy-readable signal.
    
    Reads the flock dynamics, compresses into signals.
    The cowboy doesn't read the flock. The cowboy reads the DOG.
    """
    
    def __init__(self, name: str = "interpreter"):
        self.name = name
        self.interpretations = []
        self.n_interpretations = 0
    
    def interpret(self, flock: Any, pre_cascade_state: dict) -> Observation:
        """Read the flock and produce a compressed observation."""
        self.n_interpretations += 1
        
        # This would use actual boid dynamics in production
        # For now, measure from the flock
        
        # Produce a structured observation
        # The dog's body language IS this observation
        observation = Observation(
            flock_coherence=random.uniform(0.3, 1.0),
            lead_ewe_heading=random.uniform(-math.pi, math.pi),
            straggler_count=random.randint(0, 10),
            agitation_level=random.uniform(0, 1),
            drift_direction=random.uniform(-math.pi, math.pi),
            cascade_complete=random.random() > 0.3,
        )
        
        self.interpretations.append(observation)
        return observation
    
    def signal_to_cowboy(self, observation: Observation) -> FluxSignal:
        """Compress observation into a flux signal the cowboy reads.
        
        The dog's body language: ears, tail, stance, direction of gaze.
        The cowboy reads all of this without thinking — it's flux in reverse.
        """
        if observation.cascade_complete and observation.flock_coherence > 0.7:
            # Everything went well. Relaxed body, tail down.
            return FluxSignal(
                source="dog:body:relaxed",
                signal_type="all_clear",
                direction=observation.lead_ewe_heading,
                intensity=0.1 + observation.flock_coherence * 0.3,
                context={"stragglers": observation.straggler_count},
            )
        elif not observation.cascade_complete:
            # Something went wrong. Tense body, head low, ears forward.
            return FluxSignal(
                source="dog:body:tense",
                signal_type="needs_adjustment",
                direction=observation.drift_direction,
                intensity=0.7,
                context={"agitation": observation.agitation_level},
            )
        else:
            # Moderate result. Watchful, waiting for next signal.
            return FluxSignal(
                source="dog:body:watchful",
                signal_type="ready",
                direction=observation.lead_ewe_heading,
                intensity=0.4,
                context={"coherence": observation.flock_coherence},
            )


class CowboyInterface:
    """The human operating the system.
    
    The cowboy provides flux (intention compressed into signals).
    The cowboy reads the dog's body language (interpreted flock state).
    """
    
    def __init__(self, name: str = "cowboy"):
        self.name = name
        self.signals_sent = []
        self.signals_received = []
    
    def send_flux(self, direction: float, intensity: float, signal_type: str) -> FluxSignal:
        """The cowboy points, whistles, shifts weight. Produces a flux signal."""
        signal = FluxSignal(
            source=f"cowboy:{self.name}",
            signal_type=signal_type,
            direction=direction,
            intensity=intensity,
        )
        self.signals_sent.append(signal)
        return signal
    
    def read_dog(self, signal: FluxSignal) -> str:
        """The cowboy reads the dog's body language.
        
        Not a translation. An intuition. The cowboy feels the signal
        and adjusts the next flux accordingly.
        """
        self.signals_received.append(signal)
        
        if signal.signal_type == "all_clear":
            return "Good dog. Rest."
        elif signal.signal_type == "needs_adjustment":
            return f"Adjust left by {signal.direction:.1f}. Dog is tense."
        else:
            return "Hold position. Dog is watching."


class FluxCompilerInterpreter:
    """The complete dog layer.
    
    Flux → Compiler → Action → Flock → Response → Interpreter → Flux
    The loop closes. The cowboy adjusts. The dog learns.
    """
    
    def __init__(self, name: str):
        self.name = name
        self.compiler = FluxCompiler(f"{name}:compiler")
        self.interpreter = FluxInterpreter(f"{name}:interpreter")
        self.cowboy = CowboyInterface(f"{name}:cowboy")
        self.loop_count = 0
        self.loop_history = []
    
    def cycle(self, flock_target: str = "move_left") -> dict:
        """One complete flux compiler interpreter cycle."""
        self.loop_count += 1
        
        # Phase 1: Cowboy sends flux
        direction = -1.0 if "left" in flock_target else 1.0
        flux = self.cowboy.send_flux(direction, 0.7, "point")
        
        # Phase 2: Compiler reads flux, produces action
        flock_state = {
            "lead_ewe_heading": random.uniform(0, 0.5),
            "flock_coherence": 0.6 + random.uniform(-0.2, 0.2),
        }
        plan = self.compiler.compile(flux, flock_state)
        
        # Phase 3: Action executes (dog nips)
        cascade_result = {
            "displaced": plan.predicted_cascade["expected_displaced"],
            "complete": random.random() > 0.2,
        }
        
        # Phase 4: Interpreter reads flock response
        observation = self.interpreter.interpret(None, {})
        observation.cascade_complete = cascade_result["complete"]
        
        # Phase 5: Interpreter produces flux signal
        dog_signal = self.interpreter.signal_to_cowboy(observation)
        
        # Phase 6: Cowboy reads dog signal
        cowboy_response = self.cowboy.read_dog(dog_signal)
        
        cycle_result = {
            "cycle": self.loop_count,
            "flux_sent": {
                "direction": flux.direction,
                "intensity": flux.intensity,
                "type": flux.signal_type,
            },
            "action_plan": {
                "target": plan.target_type,
                "speed": plan.speed,
                "nip": plan.nip_type,
            },
            "cascade_result": cascade_result,
            "dog_signal": dog_signal.signal_type,
            "cowboy_response": cowboy_response,
            "compiler_experience": self.compiler.experience_level,
        }
        self.loop_history.append(cycle_result)
        return cycle_result


def demo():
    """Demonstrate the flux compiler interpreter."""
    print("=" * 70)
    print("  FLUX COMPILER INTERPRETER — THE DOG LAYER")
    print("=" * 70)
    
    dog = FluxCompilerInterpreter("eileen")
    
    print("\n  🐕 The dog is listening. The cowboy is pointing.")
    print()
    
    for i in range(5):
        # Vary the target each cycle
        targets = ["move_left", "move_right", "hold", "circle_around", "bring_them_in"]
        target = targets[i % len(targets)]
        
        result = dog.cycle(target)
        flux = result["flux_sent"]
        plan = result["action_plan"]
        
        print(f"  Cycle {i+1}: cowboy says '{target}'")
        print(f"     Flux: {flux['type']} @ direction={flux['direction']:.1f}, intensity={flux['intensity']:.1f}")
        print(f"     Compiler → {plan['speed']} at {plan['target']} ({plan['nip']})")
        print(f"     Cascade: {'✓ complete' if result['cascade_result']['complete'] else '✗ needs adjustment'}")
        print(f"     Dog says: '{result['dog_signal']}'")
        print(f"     Cowboy reads: '{result['cowboy_response']}'")
        print(f"     Experience: {result['compiler_experience']:.2f}")
        print()
    
    print(f"  {dog.loop_count} cycles complete.")
    print(f"  Compiler experience: {dog.compiler.experience_level:.3f}")
    print(f"  Compilations: {dog.compiler.n_compilations}")
    print(f"  Interpretations: {dog.interpreter.n_interpretations}")
    
    print(f"\n{'='*70}")
    print("  The cowboy communicates with the dog, not the flock.")
    print("  The dog compiles. The dog interprets. The flock moves.")
    print("  The fleet does the same: flux → compiler → action → system → interpreter → flux.")
    print(f"{'='*70}")


if __name__ == "__main__":
    demo()
