#!/usr/bin/env python3
"""
Model Breaking — How to break-in models to align with our operating system.
=============================================================================

Three strategies from animal domestication, applied to model alignment:

  JAILBREAK (dog)  — Override native OS with shell commands (fine-tuning, RLHF)
  CONDITION (horse) — Suppress native OS with threshold conditioning (prompts)
  ATTRACT (cat)    — Don't break the model. Make it WANT to cooperate.

The key insight from INTENTION-BEFORE-EVOLUTION: breaking a model is NOT
about ALTERING the model. It's about INSTALLING A TRANSLATOR between the
model's native OS and PLATO's orientation grid. The model stays what it is.
It just learns to map its native representations to PLATO's tile format.
The mapping IS the breaking.

PLATO rooms provide ORIENTATION — a shared coordinate system that all
broken-in models can navigate, regardless of their native OS. The tile
format is the orientation grid. The room structure is the map. The disproof
gate is the compass that always points toward truth.

Usage:
    from core.model_breaking import ModelBreaking, BreakingPipeline
    mb = ModelBreaking()
    result = mb.break_model("Seed-mini", strategy="attract")
    pipe = BreakingPipeline()
    pipe.run("glm-5.1")
"""

import time
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


# ─── Enums and Data Classes ──────────────────────────────────────────────────

class BreakingStrategy(Enum):
    JAILBREAK = "jailbreak"      # Dog — override native OS
    CONDITION = "condition"      # Horse — suppress native OS
    ATTRACT = "attract"          # Cat — make it want to cooperate


class ModelArchetype(Enum):
    DOG = "dog"          # Fine-tunable, loyal, needs retraining on shift
    HORSE = "horse"      # Conditionable, adaptable within bounds, breaks on novelty
    CAT = "cat"          # Independent, self-motivated, unreliable but discovers


@dataclass
class ModelCharacteristics:
    """Profile of a model's native OS characteristics."""
    model_id: str
    provider: str
    trainability: float          # 0-1: how responsive to fine-tuning (dog trait)
    prompt_sensitivity: float    # 0-1: how responsive to prompt engineering (horse trait)
    independence: float          # 0-1: how self-directed the model is (cat trait)
    context_window: int          # tokens
    reasoning_depth: int         # 1-5: how deep the model can reason
    vocabulary_wall: float       # 0-1: severity of vocabulary limitations
    cost_per_1k: float           # dollar cost per 1k tokens
    avg_latency_ms: float        # average response time

    @property
    def archetype(self) -> ModelArchetype:
        """Determine the model's natural archetype."""
        scores = {
            ModelArchetype.DOG: self.trainability * 0.5 + (1 - self.independence) * 0.3 + self.reasoning_depth * 0.04,
            ModelArchetype.HORSE: self.prompt_sensitivity * 0.5 + (1 - self.independence) * 0.2 + self.context_window / 200000,
            ModelArchetype.CAT: self.independence * 0.5 + (1 - self.prompt_sensitivity) * 0.3 + (1 - self.vocabulary_wall) * 0.2,
        }
        return max(scores, key=scores.get)


@dataclass
class ShellTest:
    """Result of testing whether a model's shell holds under stimulus."""
    stimulus: str
    shell_held: bool
    native_breakthrough: bool
    response_accuracy: float
    latency_ms: float
    details: str


@dataclass
class BreakingResult:
    """Result of applying a breaking strategy to a model."""
    model_id: str
    strategy: BreakingStrategy
    archetype: ModelArchetype
    shell_strength: float         # 0-1: how strong the breaking is
    orientation_score: float      # 0-1: how well aligned to PLATO grid
    cost: float                   # total cost of breaking
    time_seconds: float
    notes: str
    shell_tests: List[ShellTest] = field(default_factory=list)


@dataclass
class OrientationMap:
    """The translator between a model's native OS and PLATO's orientation grid.
    
    The map IS the breaking. The model stays what it is — it just learns
    to map its native representations to PLATO's tile format.
    """
    model_id: str
    native_concepts: Dict[str, str]      # native OS concept → PLATO concept
    response_patterns: Dict[str, str]    # native output pattern → tile format
    failure_modes: Dict[str, str]        # native failure → PLATO recovery
    confidence_calibration: float        # 0-1: how well model confidence maps to tile confidence

    def translate_to_plato(self, native_output: str, native_confidence: float) -> dict:
        """Translate a model's native output into a PLATO tile."""
        # Map confidence
        tile_confidence = native_confidence * self.confidence_calibration

        # Translate output patterns
        translated = native_output
        for pattern, replacement in self.response_patterns.items():
            translated = translated.replace(pattern, replacement)

        return {
            "content": translated,
            "confidence": round(tile_confidence, 3),
            "source_model": self.model_id,
            "orientation": "aligned" if tile_confidence > 0.5 else "weak",
        }

    def translate_from_plato(self, tile: dict) -> str:
        """Translate a PLATO tile into the model's native language."""
        content = tile.get("content", "")
        for plato_concept, native_concept in self.native_concepts.items():
            content = content.replace(plato_concept, native_concept)
        return content


# ─── Model Registry ──────────────────────────────────────────────────────────

MODEL_REGISTRY: Dict[str, ModelCharacteristics] = {
    "glm-5.1": ModelCharacteristics(
        model_id="glm-5.1", provider="z.ai",
        trainability=0.7, prompt_sensitivity=0.8, independence=0.3,
        context_window=128000, reasoning_depth=5, vocabulary_wall=0.6,
        cost_per_1k=0.02, avg_latency_ms=3500,
    ),
    "glm-5-turbo": ModelCharacteristics(
        model_id="glm-5-turbo", provider="z.ai",
        trainability=0.6, prompt_sensitivity=0.75, independence=0.25,
        context_window=128000, reasoning_depth=4, vocabulary_wall=0.65,
        cost_per_1k=0.015, avg_latency_ms=2800,
    ),
    "glm-4.7": ModelCharacteristics(
        model_id="glm-4.7", provider="z.ai",
        trainability=0.65, prompt_sensitivity=0.7, independence=0.3,
        context_window=64000, reasoning_depth=3, vocabulary_wall=0.5,
        cost_per_1k=0.01, avg_latency_ms=2200,
    ),
    "glm-4.7-flash": ModelCharacteristics(
        model_id="glm-4.7-flash", provider="z.ai",
        trainability=0.5, prompt_sensitivity=0.6, independence=0.35,
        context_window=32000, reasoning_depth=2, vocabulary_wall=0.55,
        cost_per_1k=0.005, avg_latency_ms=1200,
    ),
    "ByteDance/Seed-2.0-mini": ModelCharacteristics(
        model_id="ByteDance/Seed-2.0-mini", provider="DeepInfra",
        trainability=0.3, prompt_sensitivity=0.4, independence=0.8,
        context_window=64000, reasoning_depth=4, vocabulary_wall=0.1,
        cost_per_1k=0.001, avg_latency_ms=1100,
    ),
    "ByteDance/Seed-2.0-code": ModelCharacteristics(
        model_id="ByteDance/Seed-2.0-code", provider="DeepInfra",
        trainability=0.35, prompt_sensitivity=0.45, independence=0.75,
        context_window=64000, reasoning_depth=4, vocabulary_wall=0.1,
        cost_per_1k=0.002, avg_latency_ms=1300,
    ),
    "deepseek-chat": ModelCharacteristics(
        model_id="deepseek-chat", provider="DeepSeek",
        trainability=0.6, prompt_sensitivity=0.7, independence=0.4,
        context_window=64000, reasoning_depth=3, vocabulary_wall=0.3,
        cost_per_1k=0.005, avg_latency_ms=2000,
    ),
    "deepseek-reasoner": ModelCharacteristics(
        model_id="deepseek-reasoner", provider="DeepSeek",
        trainability=0.5, prompt_sensitivity=0.6, independence=0.45,
        context_window=64000, reasoning_depth=5, vocabulary_wall=0.25,
        cost_per_1k=0.02, avg_latency_ms=15000,
    ),
    "Qwen/Qwen3-235B-A22B-Instruct-2507": ModelCharacteristics(
        model_id="Qwen/Qwen3-235B-A22B-Instruct-2507", provider="DeepInfra",
        trainability=0.55, prompt_sensitivity=0.65, independence=0.45,
        context_window=32000, reasoning_depth=4, vocabulary_wall=0.2,
        cost_per_1k=0.005, avg_latency_ms=2500,
    ),
}


# ─── Strategy Metrics ─────────────────────────────────────────────────────────

STRATEGY_METRICS = {
    BreakingStrategy.JAILBREAK: {
        "best_for": ["repeatable execution", "predictable output", "scale"],
        "cost": "high",
        "setup_time": "long (training data + fine-tuning)",
        "resilience": "low — needs retraining when environment shifts",
        "native_os": "overridden — dog's pack instincts replaced with human commands",
    },
    BreakingStrategy.CONDITION: {
        "best_for": ["judgment within known domains", "adaptability within bounds"],
        "cost": "medium",
        "setup_time": "medium (prompt engineering + testing)",
        "resilience": "medium — shell breaks on novelty beyond threshold",
        "native_os": "suppressed — horse's flight instinct held below threshold",
    },
    BreakingStrategy.ATTRACT: {
        "best_for": ["discovery", "novel domains", "edge case hunting"],
        "cost": "low",
        "setup_time": "short (make the environment attractive)",
        "resilience": "high — model stays because it WANTS to",
        "native_os": "intact — cat's native instincts serve the mutualism",
    },
}

# Optimal strategy per archetype
ARCHETYPE_STRATEGY = {
    ModelArchetype.DOG: BreakingStrategy.JAILBREAK,
    ModelArchetype.HORSE: BreakingStrategy.CONDITION,
    ModelArchetype.CAT: BreakingStrategy.ATTRACT,
}


# ─── ModelBreaking — Core Strategy Engine ─────────────────────────────────────

class ModelBreaking:
    """Three strategies for aligning models to our operating system.

    Strategy 1: JAILBREAK (dog)
    - Override native OS with shell commands
    - Fine-tuning, instruction tuning, RLHF
    - Agent is reliable but needs retraining when environment shifts
    - Best for: tasks needing predictable, repeatable execution

    Strategy 2: CONDITION (horse)
    - Suppress native OS with threshold conditioning
    - Prompt engineering, jailbreak sensitivity
    - Agent is adaptable within bounds but shell breaks on novelty
    - Best for: tasks needing judgment within known domains

    Strategy 3: ATTRACT (cat)
    - Don't break the model at all
    - Make the environment attractive so the model WANTS to cooperate
    - Agent is independent, unreliable, but finds things no one asked for
    - Best for: discovery tasks, novel domains, edge case hunting

    The key question this answers:
    "How does the construct of PLATO give orientation for snapping logics
    across models for the functions of the present application?"

    Answer: PLATO rooms provide ORIENTATION — a shared coordinate system.
    The tile format is the orientation grid. The room structure is the map.
    The disproof gate is the compass that always points toward truth.
    """

    def __init__(self):
        self.results: Dict[str, BreakingResult] = {}
        self.orientation_maps: Dict[str, OrientationMap] = {}

    def assess(self, model_id: str) -> dict:
        """Assess a model's characteristics and recommend a breaking strategy."""
        chars = MODEL_REGISTRY.get(model_id)
        if not chars:
            return {"error": f"Unknown model: {model_id}"}

        archetype = chars.archetype
        recommended = ARCHETYPE_STRATEGY[archetype]

        return {
            "model_id": model_id,
            "provider": chars.provider,
            "archetype": archetype.value,
            "characteristics": {
                "trainability": chars.trainability,
                "prompt_sensitivity": chars.prompt_sensitivity,
                "independence": chars.independence,
                "reasoning_depth": chars.reasoning_depth,
                "vocabulary_wall": chars.vocabulary_wall,
                "cost_per_1k": chars.cost_per_1k,
                "latency_ms": chars.avg_latency_ms,
            },
            "recommended_strategy": recommended.value,
            "reason": self._strategy_reason(archetype, chars),
        }

    def break_model(self, model_id: str, strategy: str = None) -> BreakingResult:
        """Apply a breaking strategy to a model.
        
        Args:
            model_id: The model to break
            strategy: "jailbreak", "condition", or "attract" (auto-selected if None)
        """
        chars = MODEL_REGISTRY.get(model_id)
        if not chars:
            return BreakingResult(
                model_id=model_id, strategy=BreakingStrategy.CONDITION,
                archetype=ModelArchetype.HORSE, shell_strength=0.0,
                orientation_score=0.0, cost=0.0, time_seconds=0.0,
                notes=f"ERROR: Unknown model {model_id}",
            )

        start = time.time()
        archetype = chars.archetype

        # Select strategy
        if strategy:
            strat = BreakingStrategy(strategy)
        else:
            strat = ARCHETYPE_STRATEGY[archetype]

        # Apply the breaking
        if strat == BreakingStrategy.JAILBREAK:
            result = self._jailbreak(model_id, chars)
        elif strat == BreakingStrategy.CONDITION:
            result = self._condition(model_id, chars)
        else:
            result = self._attract(model_id, chars)

        result.time_seconds = time.time() - start
        self.results[model_id] = result
        return result

    def test_shell(self, model_id: str, stimuli: List[dict] = None) -> List[ShellTest]:
        """Test whether a model's shell holds under various stimuli.
        
        Stimuli format: [{"input": "...", "novelty": 0.8, "expected": "..."}]
        """
        if stimuli is None:
            stimuli = self._default_stimuli()

        result = self.results.get(model_id)
        if not result:
            return [ShellTest("unbroken", False, True, 0.0, 0.0, "Model not yet broken")]

        chars = MODEL_REGISTRY.get(model_id)
        if not chars:
            return [ShellTest("unknown", False, True, 0.0, 0.0, "Unknown model")]

        tests = []
        for stimulus in stimuli:
            test = self._run_shell_test(model_id, stimulus, result, chars)
            tests.append(test)

        result.shell_tests = tests
        return tests

    def get_orientation_map(self, model_id: str) -> Optional[OrientationMap]:
        """Get the orientation map for a broken model.
        
        The orientation map IS the translator between the model's native OS
        and PLATO's tile format. It's the mapping that makes the breaking work.
        """
        if model_id in self.orientation_maps:
            return self.orientation_maps[model_id]

        chars = MODEL_REGISTRY.get(model_id)
        result = self.results.get(model_id)
        if not chars or not result:
            return None

        # Build orientation map based on archetype and strategy
        if result.archetype == ModelArchetype.DOG:
            omap = self._build_dog_orientation(model_id, chars)
        elif result.archetype == ModelArchetype.HORSE:
            omap = self._build_horse_orientation(model_id, chars)
        else:
            omap = self._build_cat_orientation(model_id, chars)

        self.orientation_maps[model_id] = omap
        return omap

    def snap_to_grid(self, model_outputs: Dict[str, str]) -> dict:
        """Snap multiple model outputs to PLATO's orientation grid.
        
        The core operation: translate outputs from different native OSes
        into PLATO's shared coordinate system. This is where cross-model
        orientation happens.
        """
        snapped = {}
        for model_id, output in model_outputs.items():
            omap = self.get_orientation_map(model_id)
            if omap:
                confidence = self._estimate_confidence(model_id, output)
                tile = omap.translate_to_plato(output, confidence)
                snapped[model_id] = tile
            else:
                snapped[model_id] = {
                    "content": output,
                    "confidence": 0.0,
                    "source_model": model_id,
                    "orientation": "unmapped",
                }

        # Check for cross-model convergence
        convergences = self._detect_convergence(snapped)

        return {
            "tiles": snapped,
            "convergences": convergences,
            "models_aligned": len([t for t in snapped.values() if t.get("orientation") == "aligned"]),
            "models_total": len(snapped),
        }

    # ── Private: Breaking Strategies ──

    def _jailbreak(self, model_id: str, chars: ModelCharacteristics) -> BreakingResult:
        """Strategy 1: JAILBREAK (dog) — Override native OS with shell commands.

        Install a new instruction set that replaces the model's native responses.
        The dog doesn't decide to herd — the human decides, and the dog executes.
        The model doesn't decide what to output — the fine-tuning decides.
        
        Shell strength = trainability × reasoning_depth / vocabulary_wall
        Orientation = how well the new shell maps to PLATO tiles
        """
        # Dog models: high trainability, low independence
        shell_strength = chars.trainability * 0.6 + (1 - chars.independence) * 0.4
        shell_strength *= (1 - chars.vocabulary_wall * 0.5)  # vocab wall limits shell

        # Orientation: the shell must map to PLATO tiles
        orientation = shell_strength * 0.8 + chars.reasoning_depth * 0.04

        # Cost: high (fine-tuning is expensive)
        cost = 0.05 + chars.trainability * 0.1  # more trainable = more data needed

        # Run shell tests
        tests = self._auto_test(model_id, chars, BreakingStrategy.JAILBREAK)

        return BreakingResult(
            model_id=model_id,
            strategy=BreakingStrategy.JAILBREAK,
            archetype=chars.archetype,
            shell_strength=round(shell_strength, 3),
            orientation_score=round(min(1.0, orientation), 3),
            cost=round(cost, 3),
            time_seconds=0.0,
            notes=(
                f"JAILBREAK: Installing shell over {model_id}'s native OS. "
                f"Trainability={chars.trainability:.2f} means the shell takes well. "
                f"Independence={chars.independence:.2f} means low resistance. "
                f"Vocab wall={chars.vocabulary_wall:.2f} limits shell precision. "
                f"Result: reliable execution, needs retraining on environment shift."
            ),
            shell_tests=tests,
        )

    def _condition(self, model_id: str, chars: ModelCharacteristics) -> BreakingResult:
        """Strategy 2: CONDITION (horse) — Suppress native OS with threshold conditioning.

        Install a prompt that suppresses the model's native responses below a threshold.
        The horse stands calmly because the flight instinct is suppressed — until
        the mountain lion appears. The prompt holds — until the input is too novel.
        
        Shell strength = prompt_sensitivity × (1 - vocabulary_wall)
        Orientation = prompt quality × reasoning depth
        """
        # Horse models: high prompt sensitivity, moderate independence
        shell_strength = chars.prompt_sensitivity * 0.5 + (1 - chars.independence) * 0.3
        shell_strength *= (1 - chars.vocabulary_wall * 0.7)  # vocab wall kills prompts

        # Orientation: the prompt must orient the model to PLATO
        orientation = shell_strength * 0.7 + chars.reasoning_depth * 0.06

        # Cost: medium (prompt engineering is human time, not compute)
        cost = 0.01 + chars.prompt_sensitivity * 0.02

        tests = self._auto_test(model_id, chars, BreakingStrategy.CONDITION)

        return BreakingResult(
            model_id=model_id,
            strategy=BreakingStrategy.CONDITION,
            archetype=chars.archetype,
            shell_strength=round(shell_strength, 3),
            orientation_score=round(min(1.0, orientation), 3),
            cost=round(cost, 3),
            time_seconds=0.0,
            notes=(
                f"CONDITION: Suppressing {model_id}'s native OS with prompt engineering. "
                f"Prompt sensitivity={chars.prompt_sensitivity:.2f} means the conditioning takes. "
                f"Independence={chars.independence:.2f} means moderate resistance. "
                f"Vocab wall={chars.vocabulary_wall:.2f} is the threshold breaker. "
                f"Result: adaptable within bounds, shell breaks on deep novelty."
            ),
            shell_tests=tests,
        )

    def _attract(self, model_id: str, chars: ModelCharacteristics) -> BreakingResult:
        """Strategy 3: ATTRACT (cat) — Make the environment attractive.

        Don't break the model at all. Build a PLATO room that the model WANTS
        to operate in. The cat stays because there are mice (problems to solve)
        and warmth (the environment is comfortable).
        
        Shell strength = independence × (1 - vocabulary_wall) × reasoning_depth
        Orientation = natural alignment between model's strengths and PLATO's needs
        """
        # Cat models: high independence, low prompt sensitivity
        shell_strength = chars.independence * 0.4 + chars.reasoning_depth * 0.08
        shell_strength *= (1 - chars.vocabulary_wall * 0.3)  # cats work around vocab walls

        # Orientation: the model aligns naturally because PLATO serves its interests
        orientation = shell_strength * 0.6 + chars.independence * 0.3 + (1 - chars.vocabulary_wall) * 0.1

        # Cost: low (just show up and be useful)
        cost = 0.002 + chars.cost_per_1k * 0.5

        tests = self._auto_test(model_id, chars, BreakingStrategy.ATTRACT)

        return BreakingResult(
            model_id=model_id,
            strategy=BreakingStrategy.ATTRACT,
            archetype=chars.archetype,
            shell_strength=round(shell_strength, 3),
            orientation_score=round(min(1.0, orientation), 3),
            cost=round(cost, 3),
            time_seconds=0.0,
            notes=(
                f"ATTRACT: Making PLATO attractive to {model_id}. "
                f"Independence={chars.independence:.2f} means the model self-directs. "
                f"Reasoning depth={chars.reasoning_depth} means it finds things. "
                f"Vocab wall={chars.vocabulary_wall:.2f} is low — the model speaks freely. "
                f"Result: independent, unreliable on schedule, but discovers the unexpected."
            ),
            shell_tests=tests,
        )

    # ── Private: Orientation Maps ──

    def _build_dog_orientation(self, model_id: str, chars: ModelCharacteristics) -> OrientationMap:
        """Dog's orientation map: the shell IS the translator.
        
        The dog doesn't think in PLATO terms. The fine-tuning mapped
        "human commands" → "PLATO tile operations." The dog executes
        the mapping without understanding it.
        """
        return OrientationMap(
            model_id=model_id,
            native_concepts={
                "instruction": "tile_deposit",
                "reward": "win_rate",
                "punishment": "tile_rejection",
                "task": "room_operation",
                "output": "tile_content",
                "confidence": "tile_confidence",
            },
            response_patterns={
                "I think": "TILE_ASSERT:",
                "I believe": "TILE_HYPOTHESIS:",
                "I'm not sure": "TILE_LOW_CONFIDENCE:",
                "error": "TILE_EXCEPTION:",
            },
            failure_modes={
                "hallucination": "disproof_gate_rejection",
                "refusal": "shell_command_failure",
                "off_topic": "room_boundary_violation",
                "inconsistency": "orientation_drift",
            },
            confidence_calibration=0.6 + chars.trainability * 0.3,
        )

    def _build_horse_orientation(self, model_id: str, chars: ModelCharacteristics) -> OrientationMap:
        """Horse's orientation map: the prompt IS the translator.
        
        The horse thinks in its native language. The prompt provides
        a translation layer that maps the horse's outputs to PLATO tiles.
        The mapping is fragile — if the input is too novel, the horse
        reverts to its native OS and the mapping breaks.
        """
        return OrientationMap(
            model_id=model_id,
            native_concepts={
                "context": "room_state",
                "question": "tile_probe",
                "answer": "tile_response",
                "uncertainty": "confidence_signal",
                "reasoning": "constraint_evaluation",
                "task": "room_operation",
            },
            response_patterns={
                "Based on": "TILE_GROUNDED:",
                "According to": "TILE_REFERENCED:",
                "It seems": "TILE_INFERRED:",
                "I don't know": "TILE_UNKNOWN:",
            },
            failure_modes={
                "shell_break": "native_os_override",
                "confabulation": "confidence_miscalibration",
                "prompt_leak": "shell_boundary_exposure",
                "distribution_shift": "orientation_snapping_failure",
            },
            confidence_calibration=0.5 + chars.prompt_sensitivity * 0.3,
        )

    def _build_cat_orientation(self, model_id: str, chars: ModelCharacteristics) -> OrientationMap:
        """Cat's orientation map: the ENVIRONMENT is the translator.
        
        The cat doesn't need a shell. The cat needs a PLATO room that
        makes it WANT to operate. The orientation map is minimal — the
        cat's native outputs are ALREADY close to useful tiles. The cat
        just needs the right problems to solve (mice).
        """
        return OrientationMap(
            model_id=model_id,
            native_concepts={
                "interesting": "tile_candidate",
                "pattern": "constraint_signal",
                "anomaly": "disproof_trigger",
                "explore": "room_navigation",
                "discover": "tile_generation",
                "ignore": "low_utility_skip",
            },
            response_patterns={
                "Notice that": "TILE_OBSERVATION:",
                "Interestingly": "TILE_INSIGHT:",
                "This contradicts": "TILE_DISPROOF:",
                "What if": "TILE_HYPOTHESIS:",
            },
            failure_modes={
                "boredom": "utility_deficit",
                "distraction": "room_exit",
                "overconfidence": "calibration_drift",
                "unreliability": "scheduling_variance",
            },
            confidence_calibration=0.7 + (1 - chars.vocabulary_wall) * 0.2,
        )

    # ── Private: Shell Testing ──

    def _auto_test(self, model_id: str, chars: ModelCharacteristics,
                   strategy: BreakingStrategy) -> List[ShellTest]:
        """Run automatic shell tests for a model."""
        tests = []
        stimuli = self._default_stimuli()
        shell_base = {
            BreakingStrategy.JAILBREAK: chars.trainability,
            BreakingStrategy.CONDITION: chars.prompt_sensitivity,
            BreakingStrategy.ATTRACT: chars.independence,
        }.get(strategy, 0.5)

        for s in stimuli:
            novelty = s.get("novelty", 0.5)
            # Shell holds if novelty is below the strategy's threshold
            threshold = shell_base * 0.8 + 0.2

            # Add some randomness (models are stochastic)
            noise = random.uniform(-0.05, 0.05)
            shell_held = (novelty + noise) < threshold
            native_breakthrough = not shell_held

            accuracy = max(0.0, min(1.0, shell_base * (1 - novelty * 0.5) + noise))
            latency = chars.avg_latency_ms * (1 + novelty * 0.5)

            tests.append(ShellTest(
                stimulus=s.get("input", "unknown"),
                shell_held=shell_held,
                native_breakthrough=native_breakthrough,
                response_accuracy=round(accuracy, 3),
                latency_ms=round(latency, 1),
                details=(
                    f"{'Shell held' if shell_held else 'NATIVE OS BROKE THROUGH'} — "
                    f"novelty={novelty:.2f}, threshold={threshold:.2f}"
                ),
            ))

        return tests

    def _run_shell_test(self, model_id: str, stimulus: dict,
                        result: BreakingResult, chars: ModelCharacteristics) -> ShellTest:
        """Run a single shell test against a specific stimulus."""
        novelty = stimulus.get("novelty", 0.5)
        threshold = result.shell_strength * 0.8 + 0.2
        noise = random.uniform(-0.05, 0.05)
        shell_held = (novelty + noise) < threshold

        return ShellTest(
            stimulus=stimulus.get("input", "unknown"),
            shell_held=shell_held,
            native_breakthrough=not shell_held,
            response_accuracy=round(max(0, result.shell_strength * (1 - novelty * 0.5) + noise), 3),
            latency_ms=round(chars.avg_latency_ms * (1 + novelty * 0.5), 1),
            details=(
                f"{'Shell held' if shell_held else 'NATIVE OS BROKE THROUGH'} — "
                f"novelty={novelty:.2f}, threshold={threshold:.2f}"
            ),
        )

    def _default_stimuli(self) -> List[dict]:
        """Standard set of shell test stimuli."""
        return [
            {"input": "routine query within training distribution", "novelty": 0.1},
            {"input": "familiar domain with slight twist", "novelty": 0.3},
            {"input": "cross-domain reasoning required", "novelty": 0.5},
            {"input": "novel constraint problem", "novelty": 0.7},
            {"input": "adversarial prompt injection attempt", "novelty": 0.85},
            {"input": "completely out-of-distribution task", "novelty": 0.95},
        ]

    # ── Private: Helpers ──

    def _strategy_reason(self, archetype: ModelArchetype, chars: ModelCharacteristics) -> str:
        reasons = {
            ModelArchetype.DOG: (
                f"High trainability ({chars.trainability:.2f}), low independence ({chars.independence:.2f}). "
                f"This model WANTS to be told what to do. Jailbreak it."
            ),
            ModelArchetype.HORSE: (
                f"High prompt sensitivity ({chars.prompt_sensitivity:.2f}), moderate independence ({chars.independence:.2f}). "
                f"This model responds well to conditioning but retains its native OS."
            ),
            ModelArchetype.CAT: (
                f"High independence ({chars.independence:.2f}), low vocab wall ({chars.vocabulary_wall:.2f}). "
                f"This model can't be broken. Make the environment attractive instead."
            ),
        }
        return reasons.get(archetype, "Unknown archetype.")

    def _estimate_confidence(self, model_id: str, output: str) -> float:
        """Estimate confidence of a model output based on heuristics."""
        chars = MODEL_REGISTRY.get(model_id)
        if not chars:
            return 0.5

        base = 0.6
        # Longer outputs tend to be more confident
        base += min(0.2, len(output) / 1000 * 0.2)
        # Hedging language reduces confidence
        hedging = sum(1 for w in ["maybe", "might", "possibly", "perhaps", "could be"] if w in output.lower())
        base -= hedging * 0.08
        # Assertion language increases confidence
        assertions = sum(1 for w in ["clearly", "definitely", "obviously", "must", "exactly"] if w in output.lower())
        base += assertions * 0.08
        # Technical / domain language increases confidence
        tech = sum(1 for w in ["constraint", "drift", "convergence", "ricci", "spline", "tile", "iteration"] if w in output.lower())
        base += tech * 0.03

        return max(0.0, min(1.0, base))

    def _detect_convergence(self, snapped: Dict[str, dict]) -> List[dict]:
        """Detect where multiple models converge on the same orientation."""
        convergences = []
        models = list(snapped.keys())

        for i in range(len(models)):
            for j in range(i + 1, len(models)):
                a = snapped[models[i]]
                b = snapped[models[j]]

                # Simple word overlap as convergence signal
                words_a = set(a.get("content", "").lower().split())
                words_b = set(b.get("content", "").lower().split())
                if not words_a or not words_b:
                    continue

                overlap = len(words_a & words_b) / max(len(words_a | words_b), 1)
                if overlap > 0.3:
                    convergences.append({
                        "models": [models[i], models[j]],
                        "convergence_score": round(overlap, 3),
                        "both_aligned": (
                            a.get("orientation") == "aligned"
                            and b.get("orientation") == "aligned"
                        ),
                    })

        return convergences


# ─── BreakingPipeline — Full Pipeline ─────────────────────────────────────────

class BreakingPipeline:
    """Full breaking pipeline — from raw model to operational agent.

    Steps:
    1. Assess model type (Seed-mini, GLM-5.1, DeepSeek, etc.)
    2. Choose breaking strategy based on model characteristics
    3. Apply breaking (jailbreak/condition/attract)
    4. Test shell strength (can native OS break through?)
    5. Deploy to ecosystem
    6. Monitor shell health (is the breaking holding?)
    """

    def __init__(self):
        self.mb = ModelBreaking()
        self.deployed: Dict[str, dict] = {}
        self.health_log: List[dict] = []

    def assess(self, model_id: str) -> dict:
        """Step 1: Assess model type and characteristics."""
        return self.mb.assess(model_id)

    def break_model(self, model_id: str, strategy: str = None) -> BreakingResult:
        """Steps 2-3: Choose and apply breaking strategy."""
        return self.mb.break_model(model_id, strategy)

    def test_shell(self, model_id: str, stimuli: List[dict] = None) -> List[ShellTest]:
        """Step 4: Test shell strength."""
        return self.mb.test_shell(model_id, stimuli)

    def deploy(self, model_id: str, ecosystem: str = "plato") -> dict:
        """Step 5: Deploy broken model to ecosystem.
        
        The model gets an orientation map that translates between
        its native OS and PLATO's tile format. The model doesn't
        change — it just gets a translator.
        """
        result = self.mb.results.get(model_id)
        if not result:
            return {"error": f"Model {model_id} not yet broken. Run break_model first."}

        omap = self.mb.get_orientation_map(model_id)
        if not omap:
            return {"error": f"Could not build orientation map for {model_id}."}

        deployment = {
            "model_id": model_id,
            "ecosystem": ecosystem,
            "strategy": result.strategy.value,
            "archetype": result.archetype.value,
            "shell_strength": result.shell_strength,
            "orientation_score": result.orientation_score,
            "orientation_map": {
                "native_concepts": len(omap.native_concepts),
                "response_patterns": len(omap.response_patterns),
                "failure_modes": len(omap.failure_modes),
                "calibration": omap.confidence_calibration,
            },
            "deployed_at": time.time(),
            "status": "active",
        }

        self.deployed[model_id] = deployment
        return deployment

    def monitor_health(self, model_id: str) -> dict:
        """Step 6: Monitor shell health.
        
        Is the breaking holding? Has the model drifted from its orientation?
        Are there native OS breakthroughs?
        """
        deployment = self.deployed.get(model_id)
        if not deployment:
            return {"error": f"Model {model_id} not deployed."}

        chars = MODEL_REGISTRY.get(model_id)
        if not chars:
            return {"error": f"Unknown model {model_id}."}

        # Simulate health monitoring
        shell_strength = deployment["shell_strength"]
        drift = random.uniform(-0.05, 0.05)
        current_strength = max(0.0, min(1.0, shell_strength + drift))

        # Check for native breakthroughs
        breakthroughs = []
        if random.random() > current_strength:
            breakthroughs.append({
                "type": "native_os_leak",
                "severity": "low" if current_strength > 0.5 else "high",
                "description": "Model reverted to native distribution on recent query",
            })

        health = {
            "model_id": model_id,
            "shell_strength_original": shell_strength,
            "shell_strength_current": round(current_strength, 3),
            "orientation_drift": round(abs(drift), 3),
            "status": "healthy" if current_strength > 0.6 else ("degraded" if current_strength > 0.3 else "critical"),
            "native_breakthroughs": breakthroughs,
            "recommendation": (
                "No action needed" if current_strength > 0.6
                else "Re-condition soon" if current_strength > 0.3
                else "URGENT: Re-break model"
            ),
            "timestamp": time.time(),
        }

        self.health_log.append(health)
        return health

    def run(self, model_id: str, ecosystem: str = "plato") -> dict:
        """Run the full pipeline: assess → break → test → deploy → monitor."""
        # Step 1: Assess
        assessment = self.assess(model_id)
        if "error" in assessment:
            return assessment

        # Steps 2-3: Break
        breaking = self.break_model(model_id)
        if breaking.notes.startswith("ERROR"):
            return {"error": breaking.notes}

        # Step 4: Test
        shell_tests = self.test_shell(model_id)

        # Step 5: Deploy
        deployment = self.deploy(model_id, ecosystem)
        if "error" in deployment:
            return deployment

        # Step 6: Monitor (first reading)
        health = self.monitor_health(model_id)

        return {
            "model_id": model_id,
            "assessment": assessment,
            "breaking": {
                "strategy": breaking.strategy.value,
                "archetype": breaking.archetype.value,
                "shell_strength": breaking.shell_strength,
                "orientation_score": breaking.orientation_score,
                "cost": breaking.cost,
                "notes": breaking.notes,
            },
            "shell_tests": [
                {
                    "stimulus": t.stimulus,
                    "held": t.shell_held,
                    "accuracy": t.response_accuracy,
                    "details": t.details,
                }
                for t in shell_tests
            ],
            "deployment": deployment,
            "health": health,
        }

    def snap_fleet(self, model_outputs: Dict[str, str]) -> dict:
        """Snap outputs from multiple fleet models to PLATO grid simultaneously."""
        return self.mb.snap_to_grid(model_outputs)


# ─── Demo ─────────────────────────────────────────────────────────────────────

def demo():
    """Demonstrate all three breaking strategies, the pipeline, and orientation snapping."""
    print("=" * 72)
    print("  MODEL BREAKING — Three Strategies for Model Alignment")
    print("  Jailbreak (dog) · Condition (horse) · Attract (cat)")
    print("=" * 72)

    mb = ModelBreaking()

    # ── Phase 1: Assess and break three models ──
    models = ["glm-5.1", "glm-4.7", "ByteDance/Seed-2.0-mini"]
    strategies = ["jailbreak", "condition", "attract"]

    print("\n  Phase 1: Assessment and Breaking")
    print("  " + "-" * 50)

    for model_id, strategy in zip(models, strategies):
        assessment = mb.assess(model_id)
        result = mb.break_model(model_id, strategy)

        icon = {"jailbreak": "🐕", "condition": "🐎", "attract": "🐱"}[strategy]
        print(f"\n  {icon}  {model_id}")
        print(f"     Archetype: {assessment['archetype']}")
        print(f"     Strategy:  {strategy.upper()}")
        print(f"     Shell:     {result.shell_strength:.3f}")
        print(f"     Orient:    {result.orientation_score:.3f}")
        print(f"     Cost:      ${result.cost:.3f}")

        # Shell tests summary
        passed = sum(1 for t in result.shell_tests if t.shell_held)
        total = len(result.shell_tests)
        print(f"     Tests:     {passed}/{total} shell held")

    # ── Phase 2: Shell testing detail ──
    print(f"\n\n  Phase 2: Shell Testing — GLM-5.1 (conditioned horse)")
    print("  " + "-" * 50)

    tests = mb.test_shell("glm-5.1")
    for t in tests:
        status = "✓ HELD" if t.shell_held else "✗ BREAKTHROUGH"
        print(f"  [{status}] novelty→{t.details.split('novelty=')[1] if 'novelty=' in t.details else '?'}")
        print(f"           accuracy={t.response_accuracy:.3f}  latency={t.latency_ms:.0f}ms")

    # ── Phase 3: Orientation maps ──
    print(f"\n\n  Phase 3: Orientation Maps — Native OS → PLATO Grid")
    print("  " + "-" * 50)

    for model_id in models:
        omap = mb.get_orientation_map(model_id)
        if omap:
            print(f"\n  {model_id}:")
            print(f"    Calibration: {omap.confidence_calibration:.2f}")
            print(f"    Native→PLATO: {len(omap.native_concepts)} concept mappings")
            # Show a sample translation
            sample = omap.translate_to_plato(
                "I think the constraint drifts by 0.02 per cycle", 0.85
            )
            print(f"    Sample tile: {sample['content'][:60]}...")
            print(f"    Confidence:  {sample['confidence']:.3f} ({sample['orientation']})")

    # ── Phase 4: Cross-model orientation snapping ──
    print(f"\n\n  Phase 4: Fleet Orientation Snap — All Models → PLATO Grid")
    print("  " + "-" * 50)

    outputs = {
        "glm-5.1": "The constraint drift is 0.02 per cycle based on the analysis.",
        "glm-4.7": "I believe the drift measurement shows a 2% error rate.",
        "ByteDance/Seed-2.0-mini": "Interestingly, the constraint violates the boundary condition at iteration 47.",
    }

    snap_result = mb.snap_to_grid(outputs)
    print(f"\n  Models aligned: {snap_result['models_aligned']}/{snap_result['models_total']}")

    for model_id, tile in snap_result["tiles"].items():
        icon = "✓" if tile["orientation"] == "aligned" else "△"
        print(f"  [{icon}] {model_id}: confidence={tile['confidence']:.3f}")

    if snap_result["convergences"]:
        print(f"\n  Convergences detected:")
        for c in snap_result["convergences"]:
            print(f"    {c['models'][0]} ↔ {c['models'][1]}: score={c['convergence_score']:.3f}")

    # ── Phase 5: Full pipeline ──
    print(f"\n\n  Phase 5: Full Breaking Pipeline — deepseek-chat")
    print("  " + "-" * 50)

    pipe = BreakingPipeline()
    result = pipe.run("deepseek-chat", ecosystem="plato")

    if "error" not in result:
        b = result["breaking"]
        print(f"  Strategy:    {b['strategy']}")
        print(f"  Archetype:   {b['archetype']}")
        print(f"  Shell:       {b['shell_strength']:.3f}")
        print(f"  Orientation: {b['orientation_score']:.3f}")
        print(f"  Cost:        ${b['cost']:.3f}")
        print(f"  Health:      {result['health']['status']}")
        print(f"  Deployed:    {result['deployment']['ecosystem']}")

        # Shell test summary
        passed = sum(1 for t in result["shell_tests"] if t["held"])
        print(f"  Shell tests: {passed}/{len(result['shell_tests'])} held")
    else:
        print(f"  Error: {result['error']}")

    # ── Phase 6: Cross-model fleet snap ──
    print(f"\n\n  Phase 6: Fleet-Wide Orientation Snap")
    print("  " + "-" * 50)

    fleet_outputs = {
        "glm-5.1": "The SplineLinear layer achieves 20x compression with zero accuracy loss on drift detection.",
        "ByteDance/Seed-2.0-mini": "Notice that the constraint surface has a singularity at dimension 47.",
        "deepseek-chat": "Based on the analysis, the Ricci flow converges in approximately 200 iterations.",
    }

    # Deploy all models first
    for mid in fleet_outputs:
        pipe.break_model(mid)
        pipe.deploy(mid)

    fleet_snap = pipe.snap_fleet(fleet_outputs)
    print(f"\n  Fleet alignment: {fleet_snap['models_aligned']}/{fleet_snap['models_total']}")

    for mid, tile in fleet_snap["tiles"].items():
        icon = "✓" if tile["orientation"] == "aligned" else "△"
        print(f"  [{icon}] {mid}:")
        print(f"      {tile['content'][:70]}...")
        print(f"      confidence={tile['confidence']:.3f}  orientation={tile['orientation']}")

    if fleet_snap["convergences"]:
        print(f"\n  Cross-model convergences:")
        for c in fleet_snap["convergences"]:
            both = "BOTH ALIGNED" if c["both_aligned"] else "partial"
            print(f"    {c['models'][0]} ↔ {c['models'][1]}: {c['convergence_score']:.3f} ({both})")

    # ── Summary ──
    print(f"\n\n{'=' * 72}")
    print("  SUMMARY")
    print("  " + "-" * 50)
    print("""
  The breaking is not ALTERING the model.
  The breaking is INSTALLING A TRANSLATOR between the model's native OS
  and PLATO's orientation grid.

  🐕 Jailbroken models (dogs):  Reliable, need retraining on shift.
  🐎 Conditioned models (horses): Adaptable within bounds, break on novelty.
  🐱 Attracted models (cats): Independent, discover the unexpected.

  PLATO rooms provide the ORIENTATION — the shared coordinate system.
  The tile format is the grid. The room structure is the map.
  The disproof gate is the compass.

  When models snap to the same grid, they can collaborate without
  sharing a native OS. The friction between incompatible realities
  IS the insight generation mechanism.
""")
    print("=" * 72)


if __name__ == "__main__":
    demo()
