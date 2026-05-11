"""
scripts.py — ScriptLibrary: Learned Patterns That Free Cognition
=================================================================

Scripts are compressed, pre-learned sequences that can be executed
without conscious thought. When a pattern snaps to a known script,
cognition is freed for higher-level planning.

"Scripts don't reduce MOVES, they reduce COGNITIVE LOAD. The planning
solver may use more total moves but THINKS less because scripts
execute automatically." — SNAPS-AS-ATTENTION.md
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any, Tuple
from enum import Enum
import hashlib


class ScriptStatus(Enum):
    DRAFT = "draft"        # Newly created, not yet verified
    ACTIVE = "active"      # Verified and in use
    DEGRADED = "degraded"  # Partially failing, needs update
    ARCHIVED = "archived"  # No longer used


@dataclass
class ScriptMatch:
    """Result of matching an observation against the script library."""
    script_id: str
    confidence: float       # How well the pattern matches [0..1]
    is_match: bool          # Above match threshold
    delta_from_template: float  # Distance from ideal pattern
    
    def __repr__(self):
        status = "MATCH" if self.is_match else "PARTIAL"
        return f"ScriptMatch({self.script_id}, conf={self.confidence:.2f}, {status})"


@dataclass
class Script:
    """
    A learned pattern that can be executed automatically.
    
    Scripts are the "vocabulary" of expertise. They encode:
    - A trigger pattern (what activates this script)
    - A response sequence (what the script does)
    - A context (when this script is appropriate)
    - Success/failure statistics (for monitoring)
    
    Like speedcubing algorithms or poker basic strategy:
    recognized automatically, executed without thinking.
    """
    id: str
    name: str
    trigger_pattern: np.ndarray       # The pattern that activates this script
    response: Any                      # The pre-computed response
    context: Dict[str, Any] = field(default_factory=dict)
    match_threshold: float = 0.85      # Minimum similarity to activate
    status: ScriptStatus = ScriptStatus.ACTIVE
    use_count: int = 0
    success_count: int = 0
    fail_count: int = 0
    last_used: int = 0                 # Timestamp of last use
    created_at: int = 0
    confidence: float = 1.0            # Current confidence in this script
    
    def match(self, observation: np.ndarray) -> ScriptMatch:
        """
        Check if an observation matches this script's trigger pattern.
        
        Uses cosine similarity between observation and trigger pattern.
        """
        if self.status != ScriptStatus.ACTIVE:
            return ScriptMatch(
                script_id=self.id,
                confidence=0.0,
                is_match=False,
                delta_from_template=float('inf'),
            )
        
        # Compute similarity
        if len(observation) != len(self.trigger_pattern):
            return ScriptMatch(
                script_id=self.id,
                confidence=0.0,
                is_match=False,
                delta_from_template=float('inf'),
            )
        
        # Cosine similarity
        norm_obs = np.linalg.norm(observation)
        norm_trig = np.linalg.norm(self.trigger_pattern)
        
        if norm_obs == 0 or norm_trig == 0:
            similarity = 0.0
        else:
            similarity = float(np.dot(observation, self.trigger_pattern) / (norm_obs * norm_trig))
        
        # Convert similarity [−1, 1] to confidence [0, 1]
        confidence = (similarity + 1) / 2
        
        # Distance from template
        delta = float(np.linalg.norm(observation - self.trigger_pattern))
        
        return ScriptMatch(
            script_id=self.id,
            confidence=confidence,
            is_match=confidence >= self.match_threshold,
            delta_from_template=delta,
        )
    
    def record_use(self, success: bool, timestamp: int = 0):
        """Record a use of this script."""
        self.use_count += 1
        self.last_used = timestamp
        if success:
            self.success_count += 1
        else:
            self.fail_count += 1
        self._update_confidence()
    
    def _update_confidence(self):
        """Update confidence based on success/failure history."""
        if self.use_count == 0:
            self.confidence = 1.0
            return
        # Exponential moving average of recent success rate
        success_rate = self.success_count / self.use_count
        # Weight recent failures more heavily
        self.confidence = success_rate * min(1.0, self.success_count / 5)
        
        # Degrade if failing
        if self.use_count > 5 and success_rate < 0.5:
            self.status = ScriptStatus.DEGRADED
    
    @property
    def success_rate(self) -> float:
        if self.use_count == 0:
            return 1.0
        return self.success_count / self.use_count


class ScriptLibrary:
    """
    Library of learned scripts — the system's "muscle memory."
    
    The script library stores pre-verified response sequences indexed
    by their trigger patterns. When an observation snaps to a known
    pattern, the corresponding script executes automatically, freeing
    cognition for planning.
    
    This is the Rubik's cube algorithm table, the poker basic strategy
    chart, the surgical technique catalog — compressed expertise that
    runs without thinking.
    
    Usage:
        library = ScriptLibrary(match_threshold=0.85)
        
        # Add a script
        library.add_script(Script(
            id='basic_strategy_fold',
            name='Fold weak hand out of position',
            trigger_pattern=np.array([0.1, 0.2, 0.3]),
            response='fold',
        ))
        
        # Match an observation
        match = library.find_best_match(np.array([0.12, 0.19, 0.31]))
        if match.is_match:
            script = library.get(match.script_id)
            print(f"Execute: {script.response}")
    """
    
    def __init__(self, match_threshold: float = 0.85):
        self.match_threshold = match_threshold
        self._scripts: Dict[str, Script] = {}
        self._hit_count = 0
        self._miss_count = 0
        self._tick = 0
    
    def add_script(self, script: Script) -> None:
        """Add a script to the library."""
        script.match_threshold = self.match_threshold
        self._scripts[script.id] = script
    
    def get(self, script_id: str) -> Optional[Script]:
        """Retrieve a script by ID."""
        return self._scripts.get(script_id)
    
    def find_best_match(self, observation: np.ndarray) -> Optional[ScriptMatch]:
        """
        Find the best matching script for an observation.
        
        Returns None if no script matches above threshold.
        """
        self._tick += 1
        
        if not self._scripts:
            self._miss_count += 1
            return None
        
        best_match = None
        best_confidence = 0.0
        
        for script in self._scripts.values():
            if script.status != ScriptStatus.ACTIVE:
                continue
            
            match = script.match(observation)
            if match.confidence > best_confidence:
                best_confidence = match.confidence
                best_match = match
        
        if best_match and best_match.is_match:
            self._hit_count += 1
            best_match.script = self._scripts[best_match.script_id]
        else:
            self._miss_count += 1
        
        return best_match
    
    def find_all_matches(self, observation: np.ndarray) -> List[ScriptMatch]:
        """Find all scripts that match an observation."""
        matches = []
        for script in self._scripts.values():
            match = script.match(observation)
            if match.confidence > 0.5:  # Loose threshold for multi-match
                matches.append(match)
        return sorted(matches, key=lambda m: m.confidence, reverse=True)
    
    def learn(
        self,
        trigger_pattern: np.ndarray,
        response: Any,
        name: str = "",
        context: Optional[Dict] = None,
    ) -> Script:
        """
        Learn a new script from a pattern-response pair.
        
        This is the "building" phase of the expertise cycle:
        a novel situation has been encountered, reasoned about,
        and the solution is cached as a script for future use.
        """
        script_id = hashlib.md5(
            trigger_pattern.tobytes() + str(response).encode()
        ).hexdigest()[:12]
        
        script = Script(
            id=script_id,
            name=name or f"script_{script_id}",
            trigger_pattern=trigger_pattern.copy(),
            response=response,
            context=context or {},
            status=ScriptStatus.ACTIVE,
            created_at=self._tick,
        )
        
        self.add_script(script)
        return script
    
    def forget(self, script_id: str) -> bool:
        """Archive a script (don't delete — might need to rebuild)."""
        script = self._scripts.get(script_id)
        if script:
            script.status = ScriptStatus.ARCHIVED
            return True
        return False
    
    def prune(self, min_uses: int = 3, min_success_rate: float = 0.3):
        """Remove scripts that are failing consistently."""
        for script in list(self._scripts.values()):
            if script.use_count >= min_uses and script.success_rate < min_success_rate:
                script.status = ScriptStatus.DEGRADED
    
    @property
    def hit_rate(self) -> float:
        """Fraction of lookups that found a matching script."""
        total = self._hit_count + self._miss_count
        return self._hit_count / total if total > 0 else 0.0
    
    @property
    def active_scripts(self) -> int:
        return sum(1 for s in self._scripts.values() if s.status == ScriptStatus.ACTIVE)
    
    @property
    def statistics(self) -> Dict:
        statuses = {}
        for s in self._scripts.values():
            statuses[s.status.value] = statuses.get(s.status.value, 0) + 1
        
        return {
            'total_scripts': len(self._scripts),
            'active_scripts': self.active_scripts,
            'hit_rate': self.hit_rate,
            'total_lookups': self._hit_count + self._miss_count,
            'status_distribution': statuses,
        }
    
    def __repr__(self):
        return (f"ScriptLibrary(active={self.active_scripts}, "
                f"hit_rate={self.hit_rate:.1%})")
