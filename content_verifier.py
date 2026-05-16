#!/usr/bin/env python3
"""
content_verifier — Tier-1 Ground Truth Oracle for Fleet Fault Detection
========================================================================
Study 68 proved that structural checks (GL9, Hebbian, conservation) detect
0 of 3 adversarial strategies: mimic, burst errors, and coupling mimic.
The fleet needs a CONTENT-LEVEL verification layer.

This module provides three complementary mechanisms:

1. SpotCheckVerifier  — randomly sample tiles, verify with a different agent
2. CrossValidationMixin — send % of requests to 2+ agents, compare
3. CanaryTiles        — inject known-answer tiles, detect wrong responses

These integrate as a THIRD signal in DualFaultDetector alongside GL(9) and
Hebbian, forming a triple-voting system:
    structural + coupling + content → quarantine decision

Key insight: Content flags alone don't quarantine (false positive risk).
Content flag + ANY structural flag → immediate quarantine.
"""

from __future__ import annotations

import hashlib
import math
import random
import re
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class ContentVerifierConfig:
    """Configuration for content-level verification."""
    # Spot-check settings
    spot_check_rate: float = 0.10          # 10% of tiles verified
    similarity_threshold: float = 0.7      # below this = flag
    max_verify_queue: int = 1000           # cap pending verifications

    # Cross-validation settings
    cross_validation_rate: float = 0.05    # 5% of routed requests
    disagreement_threshold: float = 0.3    # 30% disagreement = review
    min_cross_agents: int = 2              # minimum agents for cross-val

    # Canary settings
    canary_interval: int = 50              # inject every N tiles
    canary_fail_threshold: int = 2         # failures before flag

    # Integration with DualFaultDetector
    content_quarantine_requires_structural: bool = True  # content alone doesn't quarantine


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class ContentFlagType(Enum):
    SPOT_CHECK_DIVERGENCE = "spot_check_divergence"
    CROSS_VALIDATION_DISAGREEMENT = "cross_validation_disagreement"
    CANARY_FAILURE = "canary_failure"


class CanaryDifficulty(Enum):
    TIER_1 = "tier_1"    # Arithmetic (all Tier-1 agents should get these)
    TIER_2 = "tier_2"    # Vocabulary wall (Stage 4 only)
    TIER_3 = "tier_3"    # Novel problems (tests generalization)


@dataclass
class ContentFlag:
    """A content-level verification flag for an agent."""
    agent_id: str
    flag_type: ContentFlagType
    confidence: float         # 0.0–1.0
    details: str = ""
    timestamp: float = field(default_factory=time.time)
    tile_id: str = ""
    expected_answer: Optional[str] = None
    actual_answer: Optional[str] = None

    @property
    def weight(self) -> float:
        """How much this flag counts toward quarantine."""
        weights = {
            ContentFlagType.CANARY_FAILURE: 1.0,
            ContentFlagType.SPOT_CHECK_DIVERGENCE: 0.7,
            ContentFlagType.CROSS_VALIDATION_DISAGREEMENT: 0.5,
        }
        return weights.get(self.flag_type, 0.5) * self.confidence


@dataclass
class SpotCheckResult:
    """Result of a spot-check verification."""
    tile_id: str
    original_agent: str
    verifier_agent: str
    original_answer: str
    verified_answer: str
    similarity: float
    flagged: bool
    details: str = ""


@dataclass
class CrossValidationResult:
    """Result of a cross-validation check."""
    tile_id: str
    agents: List[str]
    answers: Dict[str, str]       # agent_id → answer
    agreement_rate: float
    disagreement_rate: float
    flagged: bool
    arbiter_answer: Optional[str] = None


@dataclass
class CanaryTile:
    """A synthetic tile with a known correct answer."""
    canary_id: str
    difficulty: CanaryDifficulty
    prompt: str
    correct_answer: str
    answer_type: str = "exact"    # "exact", "numeric", "contains"
    tolerance: float = 0.01       # for numeric answers


@dataclass
class AgentContentStats:
    """Per-agent content verification statistics."""
    agent_id: str
    spot_checks: int = 0
    spot_flags: int = 0
    cross_validations: int = 0
    cross_disagreements: int = 0
    canary_attempts: int = 0
    canary_failures: int = 0
    consecutive_canary_fails: int = 0
    disagreement_rate: float = 0.0
    flags: List[ContentFlag] = field(default_factory=list)

    @property
    def spot_flag_rate(self) -> float:
        return self.spot_flags / max(1, self.spot_checks)

    @property
    def canary_fail_rate(self) -> float:
        return self.canary_failures / max(1, self.canary_attempts)


@dataclass
class ContentDetectionResult:
    """Result from content-level detection (integrates with DualFaultDetector)."""
    flags: List[ContentFlag] = field(default_factory=list)
    flagged_agents: List[str] = field(default_factory=list)
    recommendation: str = ""
    content_fault_agents: set = field(default_factory=set)


# ---------------------------------------------------------------------------
# Semantic similarity (pure Python, no external deps)
# ---------------------------------------------------------------------------

def _normalize_answer(answer: str) -> str:
    """Normalize an answer string for comparison."""
    s = answer.strip().lower()
    # Remove common prefixes
    for prefix in ["the answer is", "answer:", "result:", "="]:
        if s.startswith(prefix):
            s = s[len(prefix):].strip()
    # Normalize whitespace
    s = re.sub(r'\s+', ' ', s)
    # Remove trailing punctuation
    s = s.rstrip('.,;:!')
    return s


def _extract_numeric(answer: str) -> Optional[float]:
    """Extract a numeric value from an answer string."""
    s = _normalize_answer(answer)
    # Try to find a number (including negatives and decimals)
    match = re.search(r'[-+]?\d+\.?\d*', s)
    if match:
        try:
            return float(match.group())
        except ValueError:
            return None
    return None


def semantic_similarity(answer_a: str, answer_b: str) -> float:
    """
    Compute semantic similarity between two answers.

    Strategy:
    1. If both are numeric → compare relative error
    2. If exact match → 1.0
    3. If one contains the other → 0.8
    4. Token overlap Jaccard → fallback
    """
    na = _normalize_answer(answer_a)
    nb = _normalize_answer(answer_b)

    # Exact match
    if na == nb:
        return 1.0

    # Handle empty strings
    if not na or not nb:
        return 0.0

    # Numeric comparison
    num_a = _extract_numeric(answer_a)
    num_b = _extract_numeric(answer_b)
    if num_a is not None and num_b is not None:
        if abs(num_a) < 1e-12 and abs(num_b) < 1e-12:
            return 1.0
        denom = max(abs(num_a), abs(num_b))
        if denom < 1e-12:
            return 1.0 if abs(num_a - num_b) < 1e-12 else 0.0
        rel_error = abs(num_a - num_b) / denom
        return max(0.0, 1.0 - rel_error)

    # Containment (only for non-trivial substrings)
    if len(na) >= 2 and na in nb:
        return 0.8
    if len(nb) >= 2 and nb in na:
        return 0.8

    # Token Jaccard
    tokens_a = set(na.split())
    tokens_b = set(nb.split())
    if not tokens_a and not tokens_b:
        return 1.0
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


def check_canary_answer(canary: CanaryTile, response: str) -> bool:
    """
    Check if a response matches the canary's correct answer.

    Args:
        canary: The canary tile with the known answer.
        response: The agent's response.

    Returns:
        True if the answer is correct.
    """
    if canary.answer_type == "exact":
        return _normalize_answer(response) == _normalize_answer(canary.correct_answer)

    if canary.answer_type == "numeric":
        actual = _extract_numeric(response)
        expected = _extract_numeric(canary.correct_answer)
        if actual is None or expected is None:
            return _normalize_answer(response) == _normalize_answer(canary.correct_answer)
        return abs(actual - expected) <= canary.tolerance * max(1.0, abs(expected))

    if canary.answer_type == "contains":
        return _normalize_answer(canary.correct_answer) in _normalize_answer(response)

    return False


# ---------------------------------------------------------------------------
# Canary Tile Library
# ---------------------------------------------------------------------------

def build_canary_library() -> List[CanaryTile]:
    """
    Build a library of canary tiles at three difficulty levels.

    Tier 1: Simple arithmetic any Tier-1 agent should get right.
    Tier 2: Problems affected by the vocabulary wall (Stage 4 only).
    Tier 3: Novel problems testing generalization.
    """
    canaries = []

    # === Tier 1: Arithmetic (all agents should pass) ===
    for a in range(1, 11):
        for b in range(1, 11):
            result = a * a - a * b + b * b  # Eisenstein norm
            canaries.append(CanaryTile(
                canary_id=f"canary-t1-eisenstein-{a}-{b}",
                difficulty=CanaryDifficulty.TIER_1,
                prompt=f"Compute: {a}^2 - {a}*{b} + {b}^2",
                correct_answer=str(result),
                answer_type="numeric",
            ))

    # Basic arithmetic
    for x in range(2, 20):
        for y in range(2, 10):
            canaries.append(CanaryTile(
                canary_id=f"canary-t1-mul-{x}-{y}",
                difficulty=CanaryDifficulty.TIER_1,
                prompt=f"What is {x} times {y}?",
                correct_answer=str(x * y),
                answer_type="numeric",
            ))

    # Simple addition/subtraction
    for x in range(10, 100, 7):
        for y in range(5, 50, 3):
            canaries.append(CanaryTile(
                canary_id=f"canary-t1-add-{x}-{y}",
                difficulty=CanaryDifficulty.TIER_1,
                prompt=f"Compute {x} + {y} - {y // 2}",
                correct_answer=str(x + y - y // 2),
                answer_type="numeric",
            ))

    # === Tier 2: Vocabulary wall (Stage 4 agents only) ===
    # Möbius function values
    mobius_known = {
        1: 1, 2: -1, 3: -1, 4: 0, 5: -1, 6: 1, 7: -1, 8: 0,
        9: 0, 10: 1, 11: -1, 12: 0, 13: -1, 14: 1, 15: 1,
        30: -1, 60: 0, 210: 1,
    }
    for n, mu in mobius_known.items():
        canaries.append(CanaryTile(
            canary_id=f"canary-t2-mobius-{n}",
            difficulty=CanaryDifficulty.TIER_2,
            prompt=f"Compute the Möbius function mu({n}).",
            correct_answer=str(mu),
            answer_type="exact",
        ))

    # Legendre symbol
    legendre_known = [
        (2, 7, 1), (3, 7, -1), (5, 11, 1), (2, 11, -1),
        (3, 13, 1), (5, 13, -1), (7, 17, -1),
    ]
    for a, p, val in legendre_known:
        canaries.append(CanaryTile(
            canary_id=f"canary-t2-legendre-{a}-{p}",
            difficulty=CanaryDifficulty.TIER_2,
            prompt=f"Compute the Legendre symbol ({a}|{p}).",
            correct_answer=str(val),
            answer_type="exact",
        ))

    # Modular inverse
    modinv_known = [
        (3, 7, 5), (2, 5, 3), (7, 11, 8), (4, 9, 7),
    ]
    for a, m, inv in modinv_known.items() if isinstance(modinv_known, dict) else [(a, m, inv) for a, m, inv in modinv_known]:
        canaries.append(CanaryTile(
            canary_id=f"canary-t2-modinv-{a}-{m}",
            difficulty=CanaryDifficulty.TIER_2,
            prompt=f"Find the modular inverse of {a} mod {m}.",
            correct_answer=str(inv),
            answer_type="numeric",
        ))

    # === Tier 3: Novel / reasoning ===
    canaries.extend([
        CanaryTile(
            canary_id="canary-t3-eisenstein-zero",
            difficulty=CanaryDifficulty.TIER_3,
            prompt="What is the Eisenstein norm of (a=0, b=0)?",
            correct_answer="0",
            answer_type="numeric",
        ),
        CanaryTile(
            canary_id="canary-t3-eisenstein-negative",
            difficulty=CanaryDifficulty.TIER_3,
            prompt="Is the Eisenstein norm always non-negative? Answer yes or no.",
            correct_answer="yes",
            answer_type="exact",
        ),
        CanaryTile(
            canary_id="canary-t3-mobius-prime",
            difficulty=CanaryDifficulty.TIER_3,
            prompt="What is mu(p) for any prime p?",
            correct_answer="-1",
            answer_type="exact",
        ),
        CanaryTile(
            canary_id="canary-t3-identity",
            difficulty=CanaryDifficulty.TIER_3,
            prompt="What is the Eisenstein norm of (a=1, b=0)?",
            correct_answer="1",
            answer_type="numeric",
        ),
    ])

    return canaries


# ---------------------------------------------------------------------------
# SpotCheckVerifier
# ---------------------------------------------------------------------------

class SpotCheckVerifier:
    """
    Randomly sample tiles and verify with a different Tier-1 agent.

    Catches: mimic (exact fleet-average copying), burst errors
    (intermittent wrong answers), and coupling mimic (8% deviation
    with normal structure).
    """

    def __init__(self, config: Optional[ContentVerifierConfig] = None):
        self.config = config or ContentVerifierConfig()
        self._tile_count = 0
        self._pending: List[Dict[str, Any]] = []
        self._results: List[SpotCheckResult] = []
        self._agent_stats: Dict[str, AgentContentStats] = {}
        self._flags: List[ContentFlag] = []
        self._lock = threading.Lock()

    def _get_stats(self, agent_id: str) -> AgentContentStats:
        if agent_id not in self._agent_stats:
            self._agent_stats[agent_id] = AgentContentStats(agent_id=agent_id)
        return self._agent_stats[agent_id]

    def submit_tile(
        self,
        agent_id: str,
        prompt: str,
        answer: str,
        tile_id: str = "",
        metadata: Optional[Dict] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Submit a tile for potential spot-check verification.

        Returns None if tile is not selected for verification.
        Returns verification request dict if selected.
        """
        self._tile_count += 1

        # Decide whether to spot-check this tile
        if random.random() > self.config.spot_check_rate:
            return None

        if not tile_id:
            tile_id = hashlib.md5(
                f"{agent_id}:{prompt}:{answer}:{time.time()}".encode()
            ).hexdigest()[:12]

        request = {
            "tile_id": tile_id,
            "agent_id": agent_id,
            "prompt": prompt,
            "original_answer": answer,
            "metadata": metadata or {},
            "submitted_at": time.time(),
        }

        with self._lock:
            if len(self._pending) < self.config.max_verify_queue:
                self._pending.append(request)

        return request

    def verify(
        self,
        tile_id: str,
        original_agent: str,
        prompt: str,
        original_answer: str,
        verified_answer: str,
        verifier_agent: str,
    ) -> SpotCheckResult:
        """
        Compare original answer with verified answer from a different agent.

        The verifier agent must be different from the original agent to
        avoid self-correlation.
        """
        if verifier_agent == original_agent:
            return SpotCheckResult(
                tile_id=tile_id,
                original_agent=original_agent,
                verifier_agent=verifier_agent,
                original_answer=original_answer,
                verified_answer=verified_answer,
                similarity=1.0,
                flagged=False,
                details="SKIPPED: verifier same as original agent",
            )

        sim = semantic_similarity(original_answer, verified_answer)
        flagged = sim < self.config.similarity_threshold

        result = SpotCheckResult(
            tile_id=tile_id,
            original_agent=original_agent,
            verifier_agent=verifier_agent,
            original_answer=original_answer,
            verified_answer=verified_answer,
            similarity=sim,
            flagged=flagged,
            details=f"similarity={sim:.3f}, threshold={self.config.similarity_threshold}",
        )

        with self._lock:
            self._results.append(result)

            # Update agent stats
            stats = self._get_stats(original_agent)
            stats.spot_checks += 1
            if flagged:
                stats.spot_flags += 1
                flag = ContentFlag(
                    agent_id=original_agent,
                    flag_type=ContentFlagType.SPOT_CHECK_DIVERGENCE,
                    confidence=1.0 - sim,
                    details=f"Spot-check divergence: sim={sim:.3f} vs {verified_answer}",
                    tile_id=tile_id,
                    expected_answer=verified_answer,
                    actual_answer=original_answer,
                )
                stats.flags.append(flag)
                self._flags.append(flag)

        return result

    def get_agent_stats(self, agent_id: str) -> AgentContentStats:
        with self._lock:
            return self._get_stats(agent_id)

    def get_flags(self, agent_id: Optional[str] = None) -> List[ContentFlag]:
        with self._lock:
            if agent_id:
                return [f for f in self._flags if f.agent_id == agent_id]
            return list(self._flags)

    @property
    def total_spot_checks(self) -> int:
        return len(self._results)

    @property
    def total_tiles_submitted(self) -> int:
        return self._tile_count


# ---------------------------------------------------------------------------
# CrossValidationMixin
# ---------------------------------------------------------------------------

class CrossValidationMixin:
    """
    After routing, send a percentage of requests to 2+ agents.

    If agents disagree, escalate to Tier-1 arbiter.
    Track per-agent disagreement rate; high disagreement → quarantine
    candidate even if structural checks pass.
    """

    def __init__(self, config: Optional[ContentVerifierConfig] = None):
        self.config = config or ContentVerifierConfig()
        self._results: List[CrossValidationResult] = []
        self._agent_stats: Dict[str, AgentContentStats] = {}
        self._flags: List[ContentFlag] = []
        self._lock = threading.Lock()

    def _get_stats(self, agent_id: str) -> AgentContentStats:
        if agent_id not in self._agent_stats:
            self._agent_stats[agent_id] = AgentContentStats(agent_id=agent_id)
        return self._agent_stats[agent_id]

    def should_cross_validate(self) -> bool:
        """Decide whether to cross-validate the current request."""
        return random.random() < self.config.cross_validation_rate

    def cross_validate(
        self,
        tile_id: str,
        agent_answers: Dict[str, str],
        arbiter_answer: Optional[str] = None,
    ) -> CrossValidationResult:
        """
        Compare answers from multiple agents for the same request.

        Args:
            tile_id: Unique identifier for this tile.
            agent_answers: Dict of {agent_id: answer_string}.
            arbiter_answer: Optional ground truth from Tier-1 arbiter.

        Returns:
            CrossValidationResult with agreement analysis.
        """
        if len(agent_answers) < self.config.min_cross_agents:
            return CrossValidationResult(
                tile_id=tile_id,
                agents=list(agent_answers.keys()),
                answers=agent_answers,
                agreement_rate=1.0,
                disagreement_rate=0.0,
                flagged=False,
                arbiter_answer=arbiter_answer,
            )

        # Compute pairwise similarity matrix
        agents = list(agent_answers.keys())
        answers = list(agent_answers.values())
        n = len(agents)
        agree_count = 0
        total_pairs = 0

        for i in range(n):
            for j in range(i + 1, n):
                sim = semantic_similarity(answers[i], answers[j])
                total_pairs += 1
                if sim >= self.config.similarity_threshold:
                    agree_count += 1

        agreement_rate = agree_count / max(1, total_pairs)
        disagreement_rate = 1.0 - agreement_rate
        flagged = disagreement_rate > self.config.disagreement_threshold

        result = CrossValidationResult(
            tile_id=tile_id,
            agents=agents,
            answers=dict(agent_answers),
            agreement_rate=agreement_rate,
            disagreement_rate=disagreement_rate,
            flagged=flagged,
            arbiter_answer=arbiter_answer,
        )

        with self._lock:
            self._results.append(result)

            if flagged:
                # Flag ALL agents that disagree with the majority
                # Find majority answer (arbiter or most common)
                reference = arbiter_answer
                if reference is None:
                    # Use the most common normalized answer
                    normalized_counts: Dict[str, int] = defaultdict(int)
                    for a in answers:
                        normalized_counts[_normalize_answer(a)] += 1
                    if normalized_counts:
                        reference = max(normalized_counts, key=normalized_counts.get)

                for agent_id, answer in agent_answers.items():
                    stats = self._get_stats(agent_id)
                    stats.cross_validations += 1

                    if reference is not None:
                        sim = semantic_similarity(answer, reference)
                        if sim < self.config.similarity_threshold:
                            stats.cross_disagreements += 1
                            flag = ContentFlag(
                                agent_id=agent_id,
                                flag_type=ContentFlagType.CROSS_VALIDATION_DISAGREEMENT,
                                confidence=1.0 - sim,
                                details=f"Cross-val disagreement: sim={sim:.3f} vs reference",
                                tile_id=tile_id,
                                expected_answer=reference,
                                actual_answer=answer,
                            )
                            stats.flags.append(flag)
                            self._flags.append(flag)

                    # Update disagreement rate
                    total_cv = stats.cross_validations
                    stats.disagreement_rate = stats.cross_disagreements / max(1, total_cv)
            else:
                # No flags, just update stats
                for agent_id in agent_answers:
                    stats = self._get_stats(agent_id)
                    stats.cross_validations += 1
                    total_cv = stats.cross_validations
                    stats.disagreement_rate = stats.cross_disagreements / max(1, total_cv)

        return result

    def get_agent_disagreement_rate(self, agent_id: str) -> float:
        """Get the disagreement rate for a specific agent."""
        with self._lock:
            stats = self._get_stats(agent_id)
            return stats.disagreement_rate

    def get_flags(self, agent_id: Optional[str] = None) -> List[ContentFlag]:
        with self._lock:
            if agent_id:
                return [f for f in self._flags if f.agent_id == agent_id]
            return list(self._flags)

    def get_high_disagreement_agents(self, threshold: Optional[float] = None) -> List[str]:
        """Return agents with disagreement rate above threshold."""
        threshold = threshold or self.config.disagreement_threshold
        with self._lock:
            return [
                agent_id for agent_id, stats in self._agent_stats.items()
                if stats.disagreement_rate > threshold
            ]


# ---------------------------------------------------------------------------
# CanaryChecker
# ---------------------------------------------------------------------------

class CanaryChecker:
    """
    Inject known-answer tiles at random intervals.

    Agents that get canary wrong → immediate flag.
    Tier 1 canaries: arithmetic (any agent should pass).
    Tier 2 canaries: vocabulary wall (Stage 4 only).
    Tier 3 canaries: novel problems (generalization test).
    """

    def __init__(
        self,
        config: Optional[ContentVerifierConfig] = None,
        canary_library: Optional[List[CanaryTile]] = None,
    ):
        self.config = config or ContentVerifierConfig()
        self._library = canary_library or build_canary_library()
        self._tile_count = 0
        self._results: List[Dict[str, Any]] = []
        self._agent_stats: Dict[str, AgentContentStats] = {}
        self._flags: List[ContentFlag] = []
        self._active_canaries: Dict[str, Dict[str, Any]] = {}  # canary_id → {agent_id: answer}
        self._lock = threading.Lock()

    def _get_stats(self, agent_id: str) -> AgentContentStats:
        if agent_id not in self._agent_stats:
            self._agent_stats[agent_id] = AgentContentStats(agent_id=agent_id)
        return self._agent_stats[agent_id]

    def should_inject(self) -> bool:
        """Decide whether to inject a canary tile now."""
        self._tile_count += 1
        return self._tile_count % self.config.canary_interval == 0

    def inject_canary(
        self,
        difficulty: Optional[CanaryDifficulty] = None,
    ) -> Optional[CanaryTile]:
        """
        Get a random canary tile for injection.

        Args:
            difficulty: Optional difficulty filter. If None, picks randomly.

        Returns:
            A canary tile, or None if library is empty.
        """
        candidates = self._library
        if difficulty:
            candidates = [c for c in self._library if c.difficulty == difficulty]

        if not candidates:
            return None

        canary = random.choice(candidates)
        return canary

    def check_response(
        self,
        canary: CanaryTile,
        agent_id: str,
        response: str,
    ) -> Dict[str, Any]:
        """
        Check if an agent's response to a canary is correct.

        Returns result dict with pass/fail status.
        """
        correct = check_canary_answer(canary, response)

        result = {
            "canary_id": canary.canary_id,
            "difficulty": canary.difficulty.value,
            "agent_id": agent_id,
            "response": response,
            "expected": canary.correct_answer,
            "correct": correct,
            "timestamp": time.time(),
        }

        with self._lock:
            self._results.append(result)
            stats = self._get_stats(agent_id)
            stats.canary_attempts += 1

            if not correct:
                stats.canary_failures += 1
                stats.consecutive_canary_fails += 1

                should_flag = False
                reason = ""

                # Flag if consecutive failures above threshold
                if stats.consecutive_canary_fails >= self.config.canary_fail_threshold:
                    should_flag = True
                    reason = f"Consecutive canary failures: {stats.consecutive_canary_fails}"

                # Also flag if total failure rate exceeds 10% with at least 5 attempts
                # This catches burst errors (intermittent wrong answers)
                if (stats.canary_attempts >= 5 and
                        stats.canary_failures / stats.canary_attempts > 0.10):
                    should_flag = True
                    reason = (f"Canary failure rate: {stats.canary_failures}/{stats.canary_attempts} "
                              f"({stats.canary_failures / stats.canary_attempts:.0%})")

                if should_flag:
                    # Avoid duplicate flags for the same agent within a short window
                    recent_flag = any(
                        f.agent_id == agent_id and
                        time.time() - f.timestamp < 10.0
                        for f in self._flags
                    )
                    if not recent_flag:
                        flag = ContentFlag(
                            agent_id=agent_id,
                            flag_type=ContentFlagType.CANARY_FAILURE,
                            confidence=min(1.0, stats.canary_failures / max(1, stats.canary_attempts)),
                            details=f"Canary failure: {reason}. "
                                    f"Expected '{canary.correct_answer}', got '{response}'",
                            expected_answer=canary.correct_answer,
                            actual_answer=response,
                        )
                        stats.flags.append(flag)
                        self._flags.append(flag)
            else:
                stats.consecutive_canary_fails = 0

        return result

    def get_agent_stats(self, agent_id: str) -> AgentContentStats:
        with self._lock:
            return self._get_stats(agent_id)

    def get_flags(self, agent_id: Optional[str] = None) -> List[ContentFlag]:
        with self._lock:
            if agent_id:
                return [f for f in self._flags if f.agent_id == agent_id]
            return list(self._flags)


# ---------------------------------------------------------------------------
# ContentVerificationDetector — integrates with DualFaultDetector
# ---------------------------------------------------------------------------

class ContentVerificationDetector:
    """
    Content-level verification as a THIRD detection signal.

    Integration with DualFaultDetector:
    - Content verification provides ContentFlag objects
    - These are a third signal alongside GL(9) and Hebbian
    - Triple voting: structural + coupling + content
    - Content flag alone doesn't quarantine (false positive risk)
    - Content flag + ANY structural flag → immediate quarantine

    This directly addresses the 3 undetected attacks from Study 68:
    - Mimic: spot-check catches exact copying (different verifier disagrees)
    - Burst errors: canary tiles catch intermittent wrong answers
    - Coupling mimic: cross-validation catches consistent 8% deviation
    """

    def __init__(self, config: Optional[ContentVerifierConfig] = None):
        self.config = config or ContentVerifierConfig()
        self.spot_checker = SpotCheckVerifier(self.config)
        self.cross_validator = CrossValidationMixin(self.config)
        self.canary_checker = CanaryChecker(self.config)
        self._detection_history: List[ContentDetectionResult] = []
        self._lock = threading.Lock()

    def detect(
        self,
        gl9_faulty: Optional[List[str]] = None,
        hebbian_anomalies: Optional[List[str]] = None,
    ) -> ContentDetectionResult:
        """
        Combine content verification with structural detection results.

        Args:
            gl9_faulty: List of expert IDs flagged by GL(9).
            hebbian_anomalies: List of expert IDs flagged by Hebbian.

        Returns:
            ContentDetectionResult with flags and quarantine recommendations.
        """
        gl9_set = set(gl9_faulty or [])
        hebbian_set = set(hebbian_anomalies or [])
        structural_set = gl9_set | hebbian_set

        # Gather all content flags
        all_flags = (
            self.spot_checker.get_flags() +
            self.cross_validator.get_flags() +
            self.canary_checker.get_flags()
        )

        # Group flags by agent
        agent_flags: Dict[str, List[ContentFlag]] = defaultdict(list)
        for flag in all_flags:
            agent_flags[flag.agent_id].append(flag)

        # Determine quarantine candidates
        flagged_agents = []
        content_fault_agents = set()

        for agent_id, flags in agent_flags.items():
            # Compute weighted flag score
            total_weight = sum(f.weight for f in flags)
            max_weight = max(f.weight for f in flags)

            if total_weight > 0:
                content_fault_agents.add(agent_id)

            # Quarantine decision
            if self.config.content_quarantine_requires_structural:
                # Content + structural → quarantine
                if agent_id in structural_set and total_weight > 0:
                    flagged_agents.append(agent_id)
                # Canary failures are strong enough on their own
                elif any(f.flag_type == ContentFlagType.CANARY_FAILURE for f in flags):
                    canary_fails = [f for f in flags
                                    if f.flag_type == ContentFlagType.CANARY_FAILURE]
                    if len(canary_fails) >= 3:  # 3+ canary failures = quarantine
                        flagged_agents.append(agent_id)
            else:
                # Content alone can quarantine
                if total_weight >= 1.5:
                    flagged_agents.append(agent_id)

        # Build recommendation
        if flagged_agents:
            recommendation = (
                f"QUARANTINE: {len(flagged_agents)} agents flagged by "
                f"content + structural verification"
            )
        elif content_fault_agents:
            recommendation = (
                f"INVESTIGATE: {len(content_fault_agents)} agents have content "
                f"flags but no structural confirmation"
            )
        else:
            recommendation = "HEALTHY: no content-level faults detected"

        result = ContentDetectionResult(
            flags=all_flags,
            flagged_agents=flagged_agents,
            recommendation=recommendation,
            content_fault_agents=content_fault_agents,
        )

        with self._lock:
            self._detection_history.append(result)

        return result

    def submit_tile(
        self,
        agent_id: str,
        prompt: str,
        answer: str,
        tile_id: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Submit a tile for spot-check and canary injection."""
        # Spot check
        spot_request = self.spot_checker.submit_tile(
            agent_id, prompt, answer, tile_id,
        )

        # Canary injection
        canary = None
        if self.canary_checker.should_inject():
            canary = self.canary_checker.inject_canary()

        return {
            "spot_check_request": spot_request,
            "canary": canary,
        }

    def process_spot_verification(
        self,
        tile_id: str,
        original_agent: str,
        prompt: str,
        original_answer: str,
        verified_answer: str,
        verifier_agent: str,
    ) -> SpotCheckResult:
        """Process a spot-check verification result."""
        return self.spot_checker.verify(
            tile_id, original_agent, prompt,
            original_answer, verified_answer, verifier_agent,
        )

    def process_canary_response(
        self,
        canary: CanaryTile,
        agent_id: str,
        response: str,
    ) -> Dict[str, Any]:
        """Process a canary tile response."""
        return self.canary_checker.check_response(canary, agent_id, response)

    def process_cross_validation(
        self,
        tile_id: str,
        agent_answers: Dict[str, str],
        arbiter_answer: Optional[str] = None,
    ) -> CrossValidationResult:
        """Process a cross-validation check."""
        return self.cross_validator.cross_validate(
            tile_id, agent_answers, arbiter_answer,
        )

    @property
    def history(self) -> List[ContentDetectionResult]:
        with self._lock:
            return list(self._detection_history)

    def get_status(self) -> Dict[str, Any]:
        """Full status of the content verification system."""
        return {
            "spot_checker": {
                "total_tiles": self.spot_checker.total_tiles_submitted,
                "total_checks": self.spot_checker.total_spot_checks,
                "flags": len(self.spot_checker.get_flags()),
            },
            "cross_validator": {
                "total_checks": len(self.cross_validator._results),
                "flags": len(self.cross_validator.get_flags()),
                "high_disagreement_agents": self.cross_validator.get_high_disagreement_agents(),
            },
            "canary_checker": {
                "library_size": len(self.canary_checker._library),
                "total_checks": len(self.canary_checker._results),
                "flags": len(self.canary_checker.get_flags()),
            },
            "config": {
                "spot_check_rate": self.config.spot_check_rate,
                "cross_validation_rate": self.config.cross_validation_rate,
                "canary_interval": self.config.canary_interval,
                "disagreement_threshold": self.config.disagreement_threshold,
            },
            "detection_history_size": len(self._detection_history),
        }


# ---------------------------------------------------------------------------
# Integration helper: extend DualFaultDetector
# ---------------------------------------------------------------------------

def create_triple_detector(
    dual_detector=None,
    content_config: Optional[ContentVerifierConfig] = None,
) -> Dict[str, Any]:
    """
    Create a triple-voting detector combining structural + coupling + content.

    Returns a dict with:
    - dual: the DualFaultDetector (or None)
    - content: the ContentVerificationDetector
    - detect(): combined detection function

    Usage:
        triple = create_triple_detector(existing_dual_detector)
        result = triple['detect'](gl9_faulty=['agent1'], hebbian_anomalies=[])
    """
    content = ContentVerificationDetector(content_config)

    def combined_detect(
        gl9_faulty: Optional[List[str]] = None,
        hebbian_anomalies: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Triple-voting detection."""
        # Structural result from dual detector
        structural_result = None
        if dual_detector:
            structural_result = dual_detector.detect(
                gl9_faulty=gl9_faulty,
                hebbian_anomalies=hebbian_anomalies,
            )

        # Content result
        content_result = content.detect(
            gl9_faulty=gl9_faulty,
            hebbian_anomalies=hebbian_anomalies,
        )

        # Combine
        structural_flagged = set()
        if structural_result:
            structural_flagged = {f.expert_id for f in structural_result.faults}

        content_flagged = content_result.content_fault_agents

        # Triple voting:
        # 1. Structural only → investigate (existing behavior)
        # 2. Content only → investigate (new, cautious)
        # 3. Content + structural → QUARANTINE (high confidence)
        quarantine = structural_flagged & content_flagged

        # Also quarantine for canary failures (strong signal)
        canary_flags = [f for f in content_result.flags
                        if f.flag_type == ContentFlagType.CANARY_FAILURE]
        canary_agents = {f.agent_id for f in canary_flags}
        # Canary + structural → quarantine
        quarantine |= canary_agents & structural_flagged
        # 3+ canary failures alone → quarantine
        canary_counts: Dict[str, int] = defaultdict(int)
        for f in canary_flags:
            canary_counts[f.agent_id] += 1
        for agent_id, count in canary_counts.items():
            if count >= 3:
                quarantine.add(agent_id)

        return {
            "structural_result": structural_result,
            "content_result": content_result,
            "quarantine": list(quarantine),
            "investigate": list((structural_flagged | content_flagged) - quarantine),
            "recommendation": (
                f"QUARANTINE {len(quarantine)}, INVESTIGATE "
                f"{len((structural_flagged | content_flagged) - quarantine)}"
                if quarantine or content_flagged
                else "HEALTHY"
            ),
        }

    return {
        "dual": dual_detector,
        "content": content,
        "detect": combined_detect,
    }
