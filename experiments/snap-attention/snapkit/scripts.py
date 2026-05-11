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
    
    # ─── Script Composition ────────────────────────────────────────
    
    def compose(self, script_ids: List[str]) -> Optional['Script']:
        """
        Compose multiple scripts into a sequence.
        
        Useful when a single observation matches multiple scripts:
        compose them into a multi-step response.
        
        Args:
            script_ids: Ordered list of script IDs to compose.
        
        Returns:
            A new composite Script, or None if any script not found.
        """
        scripts = []
        for sid in script_ids:
            s = self._scripts.get(sid)
            if s is None:
                return None
            scripts.append(s)
        
        if not scripts:
            return None
        
        # Create composite trigger pattern (average)
        patterns = [s.trigger_pattern for s in scripts]
        composite_pattern = np.mean(patterns, axis=0)
        
        # Create composite response (dict of individual responses)
        composite_response = {
            'sequence': [s.name for s in scripts],
            'responses': {s.id: s.response for s in scripts},
        }
        
        composite_id = hashlib.md5('+'.join(script_ids).encode()).hexdigest()[:12]
        
        return Script(
            id=composite_id,
            name=f"compose_{'+'.join(script_ids[:3])}",
            trigger_pattern=composite_pattern,
            response=composite_response,
            context={'composed_from': script_ids},
            status=ScriptStatus.ACTIVE,
        )
    
    # ─── Conflict Resolution ─────────────────────────────────────────
    
    def resolve_conflicts(
        self, observation: np.ndarray
    ) -> Optional[ScriptMatch]:
        """
        Resolve when multiple scripts match the same observation.
        
        Uses: confidence first, then success rate, then recency.
        
        Args:
            observation: Input pattern to match.
        
        Returns:
            The best single match after conflict resolution.
        """
        matches = self.find_all_matches(observation)
        active_matches = [
            m for m in matches
            if self._scripts.get(m.script_id, Script(None, '', np.array([]), None)).status == ScriptStatus.ACTIVE
        ]
        
        if not active_matches:
            return None
        
        # Score: confidence * success_rate
        scored = []
        for m in active_matches:
            s = self._scripts.get(m.script_id)
            if s is None:
                continue
            score = m.confidence * s.confidence
            scored.append((score, m, s))
        
        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]  # Return the match with best score
    
    # ─── Script Inheritance ──────────────────────────────────────────
    
    def extend(self, parent_id: str, new_name: str, new_response: Any) -> Optional[Script]:
        """
        Create a child script that inherits from a parent.
        
        Child scripts extend parent scripts: same trigger pattern
        but different response (specialized variant).
        
        Args:
            parent_id: ID of parent script to extend.
            new_name: Name for the child script.
            new_response: Override response for the child.
        
        Returns:
            New child Script, or None if parent not found.
        """
        parent = self._scripts.get(parent_id)
        if parent is None:
            return None
        
        child_id = hashlib.md5(
            (parent_id + new_name + str(new_response)).encode()
        ).hexdigest()[:12]
        
        child = Script(
            id=child_id,
            name=new_name,
            trigger_pattern=parent.trigger_pattern.copy(),
            response=new_response,
            context={
                'parent_id': parent_id,
                'inherits_from': parent.name,
                **parent.context,
            },
            match_threshold=parent.match_threshold,
            status=ScriptStatus.DRAFT,
            created_at=parent.created_at,
        )
        
        self.add_script(child)
        return child
    
    # ─── Script Versioning ───────────────────────────────────────────
    
    def update(self, script_id: str, updated_script: Script) -> bool:
        """
        Update a script, versioning the old one.
        
        Old version is archived, new version becomes active.
        Version ID is stored in context.
        
        Args:
            script_id: ID of script to update.
            updated_script: New version (keeping same ID but
                           version appended to name).
        
        Returns:
            True if update succeeded.
        """
        old = self._scripts.get(script_id)
        if old is None:
            return False
        
        # Archive old version
        old.status = ScriptStatus.ARCHIVED
        old.context['replaced_by'] = updated_script.name
        old.context['version'] = old.context.get('version', 0) + 1
        
        # Add new version
        version = old.context.get('version', 0) + 1
        updated_script.context['version'] = version
        updated_script.context['replaces'] = script_id
        updated_script.name = f"{old.name}_v{version}"
        
        self._scripts[script_id] = updated_script
        return True
    
    def version_history(self, script_id: str) -> List[Script]:
        """Get version history for a script family."""
        versions = []
        for sid, s in self._scripts.items():
            v = s.context.get('version', 0)
            if sid == script_id or s.context.get('replaces') == script_id or v > 0:
                versions.append((v, s))
        versions.sort(key=lambda x: x[0])
        return [s for v, s in versions]


# ─── ScriptPlan ───────────────────────────────────────────────────────

@dataclass
class ScriptStep:
    """A single step in a script plan."""
    script_id: str
    script_name: str
    conditions: Dict[str, Any] = field(default_factory=dict)
    fallback_script: Optional[str] = None


class ScriptPlan:
    """
    A planned sequence of scripts (like a Rubik's cube strategy).
    
    ScriptPlans organize multiple scripts into a sequence with:
    - Conditional branching (if A then B else C)
    - Fallback scripts (if main script fails)
    - Progress tracking (how far through the plan)
    
    This turns a script library into a strategy:
    not just individual moves, but a complete game plan.
    
    Usage:
        plan = ScriptPlan(name="CFOP Cross", library=lib)
        plan.add_step("cross_solved", fallback="cross_partial")
        plan.add_step("f2l_pair_1")
        plan.add_step("oll_standard", conditions={'edge_parity': False})
        plan.set_exit_condition(lambda ctx: ctx.get('solved', False))
    """
    
    def __init__(
        self,
        name: str,
        library: ScriptLibrary,
    ):
        self.name = name
        self.library = library
        self.steps: List[ScriptStep] = []
        self.current_step: int = 0
        self._exit_condition: Optional[Callable[[Dict], bool]] = None
        self._context: Dict[str, Any] = {}
        self._completed: bool = False
    
    def add_step(
        self,
        script_id: str,
        conditions: Optional[Dict[str, Any]] = None,
        fallback: Optional[str] = None,
    ) -> 'ScriptPlan':
        """Add a step to the plan."""
        script = self.library.get(script_id)
        name = script.name if script else script_id
        
        self.steps.append(ScriptStep(
            script_id=script_id,
            script_name=name,
            conditions=conditions or {},
            fallback_script=fallback,
        ))
        return self
    
    def set_exit_condition(self, condition_fn: Callable[[Dict], bool]) -> 'ScriptPlan':
        """Set a condition that exits the plan early."""
        self._exit_condition = condition_fn
        return self
    
    def execute(self, observation: np.ndarray) -> Optional[Any]:
        """
        Execute the next step in the plan.
        
        Returns the script's response, or None if plan is complete.
        """
        if self._completed:
            return None
        
        if self._exit_condition and self._exit_condition(self._context):
            self._completed = True
            return None
        
        if self.current_step >= len(self.steps):
            self._completed = True
            return None
        
        step = self.steps[self.current_step]
        
        # Check conditions
        if step.conditions:
            for key, expected in step.conditions.items():
                actual = self._context.get(key)
                if actual != expected:
                    if step.fallback_script:
                        fallback = self.library.get(step.fallback_script)
                        if fallback:
                            self._context['used_fallback'] = step.fallback_script
                            return fallback.response
                    return None
        
        # Find and execute the script
        match = self.library.find_best_match(observation)
        if match and match.script_id == step.script_id:
            script = self.library.get(step.script_id)
            if script:
                self.current_step += 1
                self._context['last_executed'] = step.script_id
                script.record_use(success=True)
                return script.response
        
        # Try fallback
        if step.fallback_script:
            fallback = self.library.get(step.fallback_script)
            if fallback:
                self.current_step += 1
                return fallback.response
        
        return None
    
    @property
    def progress(self) -> float:
        """Progress through the plan [0, 1]."""
        if not self.steps:
            return 1.0
        return self.current_step / len(self.steps)
    
    @property
    def context(self) -> Dict[str, Any]:
        return dict(self._context)
    
    @property
    def is_complete(self) -> bool:
        return self._completed or self.current_step >= len(self.steps)
    
    def reset(self):
        """Reset the plan to the beginning."""
        self.current_step = 0
        self._context.clear()
        self._completed = False
    
    def __repr__(self):
        return (f"ScriptPlan({self.name}, {self.current_step}/{len(self.steps)} steps, "
                f"progress={self.progress:.0%}, complete={self.is_complete})")
