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
from snapkit.scripts import ScriptLibrary, Script, ScriptStatus


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
    
    # ─── Phase Transition Detection ──────────────────────────────────
    
    def detect_phase_transition(self, lookback: int = 10) -> Optional[Dict[str, Any]]:
        """
        Detect phase transitions with details about the trigger/cause.
        
        Args:
            lookback: Number of recent states to check for transitions.
        
        Returns:
            Dict with transition details, or None if no transition.
        """
        if len(self._history) < 2:
            return None
        
        recent = self._history[-lookback:]
        if len(recent) < 2:
            return None
        
        transitions = []
        for i in range(1, len(recent)):
            if recent[i].phase != recent[i - 1].phase:
                transitions.append({
                    'from': recent[i - 1].phase.value,
                    'to': recent[i].phase.value,
                    'at_experience': recent[i].total_experiences,
                    'load_before': recent[i - 1].cognitive_load,
                    'load_after': recent[i].cognitive_load,
                    'delta_rate_before': 1 - recent[i - 1].snap_hit_rate,
                    'delta_rate_after': 1 - recent[i].snap_hit_rate,
                })
        
        if transitions:
            return transitions[-1]
        return None
    
    # ─── Learning Rate Adaptation ─────────────────────────────────────
    
    def adapt_learning_rate(self) -> float:
        """
        Adapt the snap's adaptation rate based on current cognitive load.
        
        High load → fast learning (tighter tolerance, more attention)
        Low load → slow learning (looser tolerance, less attention)
        
        Returns:
            The new adaptation rate.
        """
        load = self._compute_cognitive_load()
        new_rate = 0.001 + load * 0.099
        self.snap.adaptation_rate = new_rate
        return new_rate
    
    # ─── Forgetting Curve ────────────────────────────────────────────
    
    def apply_forgetting(self, decay_rate: float = 0.01):
        """
        Apply forgetting: scripts decay in confidence if not used.
        
        Borrowed from Ebbinghaus: unused scripts lose strength.
        This prevents the library from filling with stale patterns.
        
        Args:
            decay_rate: How fast scripts decay per experience.
        """
        for script in self.library._scripts.values():
            if script.status != ScriptStatus.ACTIVE:
                continue
            
            uses_ago = self._total_experiences - script.last_used
            if uses_ago > 100:
                decay = decay_rate * (uses_ago / 100)
                script.confidence = max(0.1, script.confidence - decay)
                
                if script.confidence < 0.2:
                    script.status = ScriptStatus.DEGRADED
    
    # ─── Transfer Learning ───────────────────────────────────────────
    
    def transfer_knowledge(
        self,
        other_cycle: 'LearningCycle',
        script_ids: Optional[List[str]] = None,
    ) -> int:
        """
        Transfer learned scripts from another LearningCycle.
        
        Enables cross-domain learning: scripts learned in one
        domain can be imported to bootstrap learning in another.
        
        Args:
            other_cycle: LearningCycle to import from.
            script_ids: Specific scripts to transfer (None = all active).
        
        Returns:
            Number of scripts transferred.
        """
        if script_ids:
            scripts_to_transfer = [
                other_cycle.library.get(sid)
                for sid in script_ids
                if other_cycle.library.get(sid) is not None
            ]
        else:
            scripts_to_transfer = [
                s for s in other_cycle.library._scripts.values()
                if s.status == ScriptStatus.ACTIVE
            ]
        
        count = 0
        for script in scripts_to_transfer:
            imported = Script(
                id=f"imported_{script.id}",
                name=f"[imported] {script.name}",
                trigger_pattern=script.trigger_pattern.copy(),
                response=script.response,
                context={
                    'source_domain': 'cross_domain_transfer',
                    'original_id': script.id,
                    'original_name': script.name,
                    'imported_at': self._total_experiences,
                },
                status=ScriptStatus.DRAFT,
            )
            self.library.add_script(imported)
            count += 1
        
        return count

    def __repr__(self):
        state = self.current_state
        return (f"LearningCycle({state.phase.value}, "
                f"exp={state.total_experiences}, "
                f"scripts={state.scripts_active}, "
                f"load={state.cognitive_load:.2f})")


# ─── ExperienceBuffer ─────────────────────────────────────────────────

@dataclass
class Experience:
    """A single experience record for the buffer."""
    observation: float
    delta: float
    was_scripted: bool
    script_id: Optional[str]
    timestamp: int
    outcome: Optional[float] = None


class ExperienceBuffer:
    """
    Stores and replays experiences for learning.
    
    Like rehearsal in memory consolidation: the buffer stores
    recent experiences and replays them during quiet periods
    to strengthen scripts.
    
    Usage:
        buffer = ExperienceBuffer(capacity=1000)
        buffer.store(observation=0.42, delta=0.05, was_scripted=True, script_id=None)
        
        for experience in buffer.sample(32):
            print(f"Replaying: {experience.observation}")
    """
    
    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self._buffer: List[Experience] = []
        self._position = 0
        self._full = False
    
    def store(
        self,
        observation: float,
        delta: float,
        was_scripted: bool,
        script_id: Optional[str] = None,
        outcome: Optional[float] = None,
    ):
        """Store an experience in the buffer."""
        experience = Experience(
            observation=observation,
            delta=delta,
            was_scripted=was_scripted,
            script_id=script_id,
            timestamp=len(self._buffer),
            outcome=outcome,
        )
        
        if len(self._buffer) < self.capacity:
            self._buffer.append(experience)
        else:
            self._buffer[self._position] = experience
            self._position = (self._position + 1) % self.capacity
            self._full = True
    
    def sample(self, n: int) -> List[Experience]:
        """Sample n random experiences from the buffer."""
        available = len(self._buffer)
        if available == 0:
            return []
        n = min(n, available)
        indices = np.random.choice(available, size=n, replace=False)
        return [self._buffer[i] for i in indices]
    
    def replay(self, cycle: LearningCycle, n: int = 32):
        """Replay experiences through a LearningCycle."""
        samples = self.sample(n)
        for exp in samples:
            cycle.experience(exp.observation)
            if exp.was_scripted and exp.script_id:
                script = cycle.library.get(exp.script_id)
                if script:
                    script.record_use(success=True)
    
    @property
    def size(self) -> int:
        return len(self._buffer)
    
    @property
    def is_full(self) -> bool:
        return self._full or len(self._buffer) >= self.capacity
    
    @property
    def statistics(self) -> Dict[str, Any]:
        return {
            'capacity': self.capacity,
            'size': len(self._buffer),
            'is_full': self._full or len(self._buffer) >= self.capacity,
            'scripted_fraction': sum(1 for e in self._buffer if e.was_scripted) / max(len(self._buffer), 1),
            'delta_fraction': sum(1 for e in self._buffer if e.delta > 0) / max(len(self._buffer), 1),
        }
    
    def __repr__(self):
        return f"ExperienceBuffer(size={len(self._buffer)}/{self.capacity})"
