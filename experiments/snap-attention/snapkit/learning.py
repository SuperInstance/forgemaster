"""
learning.py — LearningCycle: Experience → Pattern → Script → Automation
=========================================================================

Expertise follows a cyclic pattern: experience builds scripts, scripts
free cognition, freed cognition enables planning, planning handles
novelty, and novelty builds new scripts.

"The mind oscillates between building scripts (thinking, slow) and
running scripts (automatic, fast), monitoring for deltas, and
rebuilding when deltas accumulate."
— SNAP-ATTENTION-INTELLIGENCE.md, Section 5.5
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum

from snapkit.snap import SnapFunction
from snapkit.delta import DeltaDetector, Delta
from snapkit.scripts import ScriptLibrary, Script


class LearningPhase(Enum):
    """Phases of the expertise cycle."""
    DELTA_FLOOD = "delta_flood"    # No scripts — everything is novel
    SCRIPT_BURST = "script_burst"  # Patterns emerging — rapid script creation
    SMOOTH_RUNNING = "smooth"      # Most things snap to scripts — low load
    DISRUPTION = "disruption"      # Accumulated deltas — scripts failing
    REBUILDING = "rebuilding"      # Constructing new scripts from deltas


@dataclass
class LearningState:
    """Current state of the learning cycle."""
    phase: LearningPhase
    total_experiences: int
    scripts_built: int
    scripts_active: int
    cognitive_load: float         # 0.0 = fully automated, 1.0 = full attention
    snap_hit_rate: float          # Fraction of observations that snap to known patterns
    delta_rate: float             # Fraction of novel observations
    phase_transitions: int        # How many times phase has changed
    
    def __repr__(self):
        return (f"LearningState({self.phase.value}, "
                f"experiences={self.total_experiences}, "
                f"scripts={self.scripts_active}, "
                f"load={self.cognitive_load:.2f})")


class LearningCycle:
    """
    The cycle of expertise: experience → pattern → script → automation.
    
    Models the four modes of expert cognition:
    1. Building scripts (attention-heavy, slow)
    2. Running scripts (automatic, attention-free)
    3. Monitoring for deltas (light attention)
    4. Rebuilding when deltas accumulate (back to building)
    
    Args:
        snap: The snap function for detecting deltas.
        detector: Delta detector for multi-stream monitoring.
        library: Script library for storing learned patterns.
        novelty_threshold: How many consecutive deltas before rebuilding.
        script_creation_threshold: How many similar deltas before creating a script.
    
    Usage:
        cycle = LearningCycle(snap=SnapFunction(tolerance=0.1))
        
        for observation in experience_stream:
            state = cycle.experience(observation)
            print(f"Phase: {state.phase}, Load: {state.cognitive_load:.2f}")
    """
    
    def __init__(
        self,
        snap: Optional[SnapFunction] = None,
        detector: Optional[DeltaDetector] = None,
        library: Optional[ScriptLibrary] = None,
        novelty_threshold: int = 5,
        script_creation_threshold: int = 3,
    ):
        self.snap = snap or SnapFunction(tolerance=0.1)
        self.detector = detector or DeltaDetector()
        self.library = library or ScriptLibrary()
        self.novelty_threshold = novelty_threshold
        self.script_creation_threshold = script_creation_threshold
        
        # Internal state
        self._total_experiences = 0
        self._consecutive_deltas = 0
        self._pending_deltas: List[Dict] = []  # Deltas awaiting script creation
        self._phase = LearningPhase.DELTA_FLOOD
        self._phase_transitions = 0
        self._history: List[LearningState] = []
    
    def experience(self, observation: float, context: Optional[Dict] = None) -> LearningState:
        """
        Process a new experience through the learning cycle.
        
        Returns the current LearningState after processing.
        """
        self._total_experiences += 1
        
        # Step 1: Snap the observation
        result = self.snap.observe(observation)
        
        # Step 2: Check for delta
        if result.is_delta:
            self._consecutive_deltas += 1
            self._pending_deltas.append({
                'value': observation,
                'expected': self.snap.baseline,
                'delta': result.delta,
                'context': context or {},
            })
        else:
            self._consecutive_deltas = 0
        
        # Step 3: Check for script match (if library has scripts)
        if self.library.active_scripts > 0:
            obs_array = np.array([observation])
            match = self.library.find_best_match(obs_array)
            if match and match.is_match:
                self._consecutive_deltas = 0
                script = self.library.get(match.script_id)
                if script:
                    script.record_use(True, self._total_experiences)
        
        # Step 4: Create scripts from accumulated patterns
        if len(self._pending_deltas) >= self.script_creation_threshold:
            self._create_script_from_deltas()
        
        # Step 5: Update phase
        self._update_phase()
        
        # Record state
        state = self.current_state
        self._history.append(state)
        
        return state
    
    def _create_script_from_deltas(self):
        """Create a new script from accumulated similar deltas."""
        if not self._pending_deltas:
            return
        
        # Cluster similar deltas
        values = np.array([d['value'] for d in self._pending_deltas])
        mean_val = np.mean(values)
        
        # Create a script triggered by the mean pattern
        trigger = np.array([mean_val])
        response = {'action': 'handle', 'value': mean_val}
        
        self.library.learn(
            trigger_pattern=trigger,
            response=response,
            name=f"auto_script_{self._total_experiences}",
            context=self._pending_deltas[0].get('context', {}),
        )
        
        self._pending_deltas.clear()
    
    def _update_phase(self):
        """Update the learning phase based on current state."""
        old_phase = self._phase
        hit_rate = self.library.hit_rate
        load = self._compute_cognitive_load()
        
        if self.library.active_scripts == 0:
            self._phase = LearningPhase.DELTA_FLOOD
        elif self._consecutive_deltas >= self.novelty_threshold:
            self._phase = LearningPhase.DISRUPTION
            if self._consecutive_deltas >= self.novelty_threshold * 2:
                self._phase = LearningPhase.REBUILDING
        elif hit_rate > 0.7:
            self._phase = LearningPhase.SMOOTH_RUNNING
        elif self.library.active_scripts > 0 and hit_rate < 0.3:
            self._phase = LearningPhase.SCRIPT_BURST
        else:
            self._phase = LearningPhase.SCRIPT_BURST
        
        if self._phase != old_phase:
            self._phase_transitions += 1
    
    def _compute_cognitive_load(self) -> float:
        """
        Compute current cognitive load [0..1].
        
        0.0 = fully automated (everything snaps to scripts)
        1.0 = full attention (everything is novel)
        """
        if self._total_experiences == 0:
            return 1.0
        
        # Load = fraction of recent experiences that were deltas
        recent = self._history[-100:] if len(self._history) > 100 else self._history
        if not recent:
            return 1.0
        
        delta_fraction = 1.0 - self.snap.snap_rate
        script_coverage = self.library.hit_rate
        
        # Combined load: deltas that scripts don't cover
        load = delta_fraction * (1.0 - script_coverage)
        return float(np.clip(load, 0.0, 1.0))
    
    @property
    def current_state(self) -> LearningState:
        """Get the current learning state."""
        return LearningState(
            phase=self._phase,
            total_experiences=self._total_experiences,
            scripts_built=len(self.library._scripts),
            scripts_active=self.library.active_scripts,
            cognitive_load=self._compute_cognitive_load(),
            snap_hit_rate=self.snap.snap_rate,
            delta_rate=self.snap.delta_rate,
            phase_transitions=self._phase_transitions,
        )
    
    @property
    def phase_history(self) -> List[LearningPhase]:
        """Get the history of phase transitions."""
        return [s.phase for s in self._history]
    
    @property
    def statistics(self) -> Dict:
        return {
            'current_phase': self._phase.value,
            'total_experiences': self._total_experiences,
            'scripts_built': len(self.library._scripts),
            'scripts_active': self.library.active_scripts,
            'cognitive_load': self._compute_cognitive_load(),
            'snap_hit_rate': self.snap.snap_rate,
            'delta_rate': self.snap.delta_rate,
            'library_stats': self.library.statistics,
            'snap_stats': self.snap.statistics,
        }
    
    def __repr__(self):
        state = self.current_state
        return (f"LearningCycle({state.phase.value}, "
                f"exp={state.total_experiences}, "
                f"scripts={state.scripts_active}, "
                f"load={state.cognitive_load:.2f})")
