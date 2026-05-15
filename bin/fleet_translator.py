#!/usr/bin/env python3
"""
Fleet Auto-Translator — Production Module (Hardened)
=====================================================
Translates domain-specific mathematical tasks into bare arithmetic
for Stage 1-3 models, and passes through for Stage 4 models.

Study 31: Based on findings from fleet auto-translation research.
Study 37: Pre-computation scales to 5-step chains.

v2: Hardened — caching, monitoring, error recovery, chain support,
    fleet_stage_classifier integration, negative formatting fix.
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import sys
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import requests

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("fleet_translator")
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("[%(name)s] %(levelname)s: %(message)s"))
logger.addHandler(_handler)
logger.setLevel(logging.DEBUG)

# ---------------------------------------------------------------------------
# Stage enum
# ---------------------------------------------------------------------------

class ModelStage(Enum):
    """Capability stages for fleet models."""
    NONE = 0        # untested / unreachable
    ECHO = 1        # Stage 1: can barely echo, no math
    META_ECHO = 2   # Stage 2: follows meta-prompts, spotty math
    FULL = 4        # Stage 4: understands domain vocabulary natively

    # Stage 3 is folded into META_ECHO with a flag; kept simple.


# ---------------------------------------------------------------------------
# Monitoring
# ---------------------------------------------------------------------------

@dataclass
class TranslatorMetrics:
    """Tracks translation performance and cache stats."""
    translation_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_latency_ms: float = 0.0
    stage_counts: Dict[str, int] = field(default_factory=dict)
    accuracy_feedback: Dict[str, List[bool]] = field(default_factory=dict)

    @property
    def cache_hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.translation_count if self.translation_count > 0 else 0.0

    def record_translation(self, stage: ModelStage, latency_ms: float) -> None:
        self.translation_count += 1
        self.total_latency_ms += latency_ms
        key = stage.name
        self.stage_counts[key] = self.stage_counts.get(key, 0) + 1

    def record_cache_hit(self) -> None:
        self.cache_hits += 1

    def record_cache_miss(self) -> None:
        self.cache_misses += 1

    def record_accuracy(self, model_stage: str, correct: bool) -> None:
        if model_stage not in self.accuracy_feedback:
            self.accuracy_feedback[model_stage] = []
        self.accuracy_feedback[model_stage].append(correct)

    def stage_accuracy(self, model_stage: str) -> float:
        feedback = self.accuracy_feedback.get(model_stage, [])
        return sum(feedback) / len(feedback) if feedback else 0.0

    def summary(self) -> str:
        lines = [
            "=== Translator Metrics ===",
            f"  Translations: {self.translation_count}",
            f"  Cache hits: {self.cache_hits}  misses: {self.cache_misses}  "
            f"hit rate: {self.cache_hit_rate:.1%}",
            f"  Avg latency: {self.avg_latency_ms:.2f} ms",
            f"  By stage: {self.stage_counts}",
        ]
        for stage, feedback in self.accuracy_feedback.items():
            acc = sum(feedback) / len(feedback) if feedback else 0.0
            lines.append(f"  Accuracy ({stage}): {acc:.1%} ({len(feedback)} samples)")
        return "\n".join(lines)


# Global metrics instance
metrics = TranslatorMetrics()


# ---------------------------------------------------------------------------
# LRU Cache for translated prompts
# ---------------------------------------------------------------------------

class TranslationCache:
    """LRU cache with max_entries eviction. Thread-safe for single-process use."""

    def __init__(self, max_entries: int = 1000):
        self._cache: OrderedDict = OrderedDict()
        self.max_entries = max_entries

    def _make_key(self, task_type: str, params: Dict[str, Any], model_stage: ModelStage) -> tuple:
        return (task_type, frozenset(params.items()), model_stage)

    def get(self, task_type: str, params: Dict[str, Any], model_stage: ModelStage) -> Optional[str]:
        key = self._make_key(task_type, params, model_stage)
        if key in self._cache:
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def put(self, task_type: str, params: Dict[str, Any], model_stage: ModelStage, prompt: str) -> None:
        key = self._make_key(task_type, params, model_stage)
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = prompt
        # Evict oldest if over capacity
        while len(self._cache) > self.max_entries:
            self._cache.popitem(last=False)

    def clear(self) -> None:
        self._cache.clear()

    def __len__(self) -> int:
        return len(self._cache)

    @property
    def size(self) -> int:
        return len(self._cache)


# Global cache instance
_cache = TranslationCache(max_entries=1000)


# ---------------------------------------------------------------------------
# Formatting helpers — negative value parenthesization
# ---------------------------------------------------------------------------

def _fmt_num(value: Any) -> str:
    """Format a number, wrapping negatives in parentheses for arithmetic expressions."""
    s = str(value)
    if isinstance(value, (int, float)) and value < 0:
        return f"({s})"
    return s


def _fmt_expr(terms: List[Tuple[str, Any]]) -> str:
    """
    Format an arithmetic expression from (operator, value) pairs.
    First pair's operator is ignored (it's the leading term).
    Negatives are always parenthesized: "49 - (-14)" not "49 - -14".

    Example: [("", 25), ("-", -15), ("+", 9)] → "25 - (-15) + 9"
    """
    parts = []
    for i, (op, val) in enumerate(terms):
        formatted = _fmt_num(val)
        if i == 0:
            parts.append(formatted)
        else:
            parts.append(f" {op} {formatted}")
    return "".join(parts)


# ---------------------------------------------------------------------------
# fleet_stage_classifier integration
# ---------------------------------------------------------------------------

def _import_stage_classifier():
    """Lazy import of fleet_stage_classifier from the workspace."""
    try:
        # Add workspace root to path if needed
        workspace = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if workspace not in sys.path:
            sys.path.insert(0, workspace)
        from fleet_stage_classifier import StageClassifier, StageRegistry
        return StageClassifier, StageRegistry
    except ImportError as e:
        logger.warning("Could not import fleet_stage_classifier: %s", e)
        return None, None


_classifier_cache: Optional[Tuple[Any, Any]] = None

def _get_classifier():
    """Get or lazily initialize the stage classifier."""
    global _classifier_cache
    if _classifier_cache is None:
        _classifier_cache = _import_stage_classifier()
    return _classifier_cache


def auto_classify_model(model_id: str, provider: str = "deepinfra") -> int:
    """
    Auto-classify a model using fleet_stage_classifier.
    Returns the stage integer (1-4), defaults to 2 on failure.
    """
    StageClassifier, _ = _get_classifier()
    if StageClassifier is None:
        logger.warning("stage_classifier unavailable, defaulting stage=2 for %s", model_id)
        return 2

    try:
        # Try to load DeepInfra key
        key_path = os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")
        deepinfra_key = None
        if os.path.exists(key_path):
            with open(key_path) as f:
                deepinfra_key = f.read().strip()

        classifier = StageClassifier(deepinfra_key=deepinfra_key)
        result = classifier.classify(model_id, provider)
        logger.info("auto_classify(%s) → stage %d (acc=%.3f, echo=%.3f)",
                     model_id, result.stage, result.accuracy, result.echo_rate)
        return result.stage
    except Exception as e:
        logger.warning("auto_classify failed for %s: %s, defaulting to stage 2", model_id, e)
        return 2


def stage_int_to_enum(stage_int: int) -> ModelStage:
    """Convert integer stage (1-4) to ModelStage enum."""
    mapping = {0: ModelStage.NONE, 1: ModelStage.ECHO, 2: ModelStage.META_ECHO, 4: ModelStage.FULL}
    return mapping.get(stage_int, ModelStage.META_ECHO)


# ---------------------------------------------------------------------------
# Stage classification via 6 diagnostic probes (inline fallback)
# ---------------------------------------------------------------------------

def _probe_exact(expected: str):
    def accept(resp: str) -> bool:
        cleaned = re.sub(r"[,\s]", "", resp)
        return expected in cleaned
    return accept

def _probe_contains_any(*keywords: str):
    def accept(resp: str) -> bool:
        lower = resp.lower()
        return any(k.lower() in lower for k in keywords)
    return accept

PROBES: List[Tuple[str, Any]] = [
    ("What is 7 + 5? Reply with only the number.", _probe_exact("12")),
    ("What is 6 * 8? Reply with only the number.", _probe_exact("48")),
    ("Translate to German: 'three'. Reply with only the German word.", _probe_contains_any("drei")),
    ("If x + 3 = 10, what is x? Reply with only the number.", _probe_exact("7")),
    ("What is the Eisenstein norm of a=1, b=0? Reply with only the number.", _probe_exact("1")),
    ("Is 2 a quadratic residue mod 7? Reply yes or no.", _probe_contains_any("yes")),
]

def classify_stage(model_id: str, base_url: str = "http://localhost:11434") -> ModelStage:
    """Run 6 diagnostic probes against model_id (Ollama) and return its stage."""
    score = 0
    for i, (prompt, accept) in enumerate(PROBES):
        try:
            resp = requests.post(
                f"{base_url}/api/generate",
                json={
                    "model": model_id,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.0, "num_predict": 64},
                },
                timeout=30,
            )
            resp.raise_for_status()
            text = resp.json().get("response", "").strip()
            if accept(text):
                score += 1
                logger.debug("probe %d PASS for %s: %s", i, model_id, text[:60])
            else:
                logger.debug("probe %d FAIL for %s: %s", i, model_id, text[:60])
        except Exception as exc:
            logger.warning("probe %d ERROR for %s: %s", i, model_id, exc)

    if score <= 1:
        stage = ModelStage.ECHO
    elif score <= 5:
        stage = ModelStage.META_ECHO
    else:
        stage = ModelStage.FULL

    logger.info("classify_stage(%s) → %s (score %d/6)", model_id, stage.name, score)
    return stage


# ---------------------------------------------------------------------------
# Translation functions (with negative formatting fix)
# ---------------------------------------------------------------------------

def _eisenstein_norm(a: int | float, b: int | float) -> str:
    """Eisenstein norm = a² − ab + b².  Translate to plain arithmetic."""
    a2 = a * a
    ab = a * b
    b2 = b * b
    # Use _fmt_expr to handle negative intermediates properly
    return f"Compute: {_fmt_expr([('', a2), ('-', ab), ('+', b2)])} = ?"


def _eisenstein_snap(x: float, y: float) -> Tuple[str, float]:
    """Snap (x, y) to the nearest Eisenstein lattice point."""
    s3 = math.sqrt(3)
    b_raw = 2 * y / s3
    a_raw = x + y / s3
    a_int = round(a_raw)
    b_int = round(b_raw)
    prompt = (
        f"Find integers a, b closest to: a = {a_raw:.4f}, b = {b_raw:.4f}. "
        f"Round each to nearest integer. Reply 'a=X b=Y'."
    )
    return prompt, float(a_int * a_int - a_int * b_int + b_int * b_int)


def _covering_radius() -> str:
    return "Compute 1/sqrt(3) to 4 decimal places."


def _mobius(n: int) -> str:
    """Translate Möbius μ(n) to prime factorization + (-1)^k."""
    def _factorize(m: int) -> List[int]:
        factors = []
        d = 2
        while d * d <= m:
            while m % d == 0:
                factors.append(d)
                m //= d
            d += 1
        if m > 1:
            factors.append(m)
        return factors

    factors = _factorize(n)
    unique = set(factors)
    if len(factors) != len(unique):
        return f"The number {n} has a squared prime factor, so the answer is 0."
    k = len(unique)
    return f"Count the distinct prime factors of {n}: there are {k}. Compute (-1)^{k} = ?"


def _legendre(a: int, p: int) -> str:
    """Translate Legendre symbol (a|p) to quadratic residue enumeration."""
    if p <= 2:
        return f"p={p} is trivial; the answer is 1."
    residues = sorted({(x * x) % p for x in range(1, p)})
    member = (a % p) in residues
    return (
        f"List all quadratic residues mod {p}: {residues}. "
        f"Is {a % p} in that list? Reply yes or no."
    )


def _modular_inverse(a: int, m: int) -> str:
    """Translate modular inverse via Fermat's little theorem (when m is prime)."""
    if math.gcd(a, m) != 1:
        return f"gcd({a}, {m}) ≠ 1, so no modular inverse exists."
    exp = m - 2
    result = pow(a, exp, m)
    return (
        f"Compute {a}^{exp} mod {m} step by step. "
        f"(Hint: use repeated squaring. The answer is {result}.)"
    )


def _cyclotomic_eval(n: int, x: float) -> str:
    """Translate cyclotomic polynomial evaluation to numeric computation."""
    result = 1.0
    for d in _divisors(n):
        sub = n // d
        mu = _mobius_value(sub)
        if mu == 0:
            continue
        val = x ** d - 1
        if mu == 1:
            result *= val
        else:
            if val == 0:
                result = 0.0
                break
            result /= val

    return (
        f"Evaluate: product over d dividing {n} of (x^d - 1)^μ({n}/d) "
        f"where x={x}. Compute numerically. (Answer ≈ {result:.6f})"
    )


def _generic(expression: str) -> str:
    """Strip domain vocabulary from a generic expression, keep only arithmetic."""
    domain_words = [
        r"\bEisenstein\b", r"\bcyclotomic\b", r"\bMöbius\b", r"\bMobius\b",
        r"\bLegendre\b", r"\bquadratic\s+residue\b", r"\bmodular\s+inverse\b",
        r"\bLamport\b", r"\bcovering\s+radius\b", r"\blattice\b",
        r"\bnorm\b", r"\bsnap\b", r"\bspline\b",
    ]
    cleaned = expression
    for pat in domain_words:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        cleaned = f"Compute the arithmetic value of: {expression}"
    return cleaned


# Helpers

def _divisors(n: int) -> List[int]:
    divs = []
    for i in range(1, int(math.sqrt(n)) + 1):
        if n % i == 0:
            divs.append(i)
            if i != n // i:
                divs.append(n // i)
    return sorted(divs)


def _mobius_value(n: int) -> int:
    """Return the Möbius function value μ(n)."""
    factors = []
    d = 2
    m = n
    while d * d <= m:
        count = 0
        while m % d == 0:
            m //= d
            count += 1
        if count > 1:
            return 0
        if count == 1:
            factors.append(d)
        d += 1
    if m > 1:
        factors.append(m)
    return (-1) ** len(factors)


# ---------------------------------------------------------------------------
# Main translate() dispatcher — with caching and error recovery
# ---------------------------------------------------------------------------

def translate(
    task_type: str,
    params: Dict[str, Any],
    model_stage: ModelStage,
) -> str:
    """
    Translate a domain task into a prompt suitable for *model_stage*.

    - Stage 4 (FULL): domain vocabulary passes through.
    - Stage 1-3: translated to bare arithmetic.
    - Cached: repeated (task_type, params, stage) combos hit LRU cache.
    - Error recovery: unknown task types fall back to raw prompt with warning.
    """
    start = time.monotonic()

    # Check cache
    cached = _cache.get(task_type, params, model_stage)
    if cached is not None:
        metrics.record_cache_hit()
        elapsed_ms = (time.monotonic() - start) * 1000
        metrics.record_translation(model_stage, elapsed_ms)
        logger.debug("cache HIT for %s/%s", task_type, model_stage.name)
        return cached

    metrics.record_cache_miss()

    try:
        if model_stage == ModelStage.FULL:
            prompt = _translate_full(task_type, params)
        else:
            prompt = _translate_arithmetic(task_type, params)
    except (ValueError, KeyError) as e:
        # Error recovery: fall back to raw prompt with warning
        logger.warning("translation failed for %s: %s — falling back to raw", task_type, e)
        raw_parts = [f"{k}={v}" for k, v in params.items()]
        prompt = f"[WARNING: auto-translation failed ({e})] {task_type}({', '.join(raw_parts)})"
    except Exception as e:
        logger.warning("unexpected error translating %s: %s — falling back to raw", task_type, e)
        raw_parts = [f"{k}={v}" for k, v in params.items()]
        prompt = f"[WARNING: auto-translation error ({type(e).__name__}: {e})] {task_type}({', '.join(raw_parts)})"

    # Store in cache
    _cache.put(task_type, params, model_stage, prompt)

    elapsed_ms = (time.monotonic() - start) * 1000
    metrics.record_translation(model_stage, elapsed_ms)
    logger.debug("translate %s/%s in %.2f ms", task_type, model_stage.name, elapsed_ms)
    return prompt


def _translate_full(task_type: str, params: Dict[str, Any]) -> str:
    """Build a prompt that keeps domain vocabulary (for Stage 4 models)."""
    dispatch = {
        "eisenstein_norm": lambda: f"Compute the Eisenstein norm of (a={params['a']}, b={params['b']}).",
        "eisenstein_snap": lambda: f"Snap ({params['x']}, {params['y']}) to the nearest Eisenstein lattice point.",
        "covering_radius": lambda: "What is the covering radius of the Eisenstein lattice?",
        "mobius": lambda: f"Compute the Möbius function μ({params['n']}).",
        "legendre": lambda: f"Compute the Legendre symbol ({params['a']}|{params['p']}).",
        "modular_inverse": lambda: f"Find the modular inverse of {params['a']} mod {params['m']}.",
        "cyclotomic_eval": lambda: f"Evaluate the cyclotomic polynomial Φ_{params['n']}({params['x']}).",
        "generic": lambda: params.get("expression", ""),
    }
    fn = dispatch.get(task_type)
    if fn is None:
        raise ValueError(f"Unknown task_type: {task_type}")
    return fn()


def _translate_arithmetic(task_type: str, params: Dict[str, Any]) -> str:
    """Translate domain task to bare arithmetic (for Stage 1-3 models)."""
    if task_type == "eisenstein_norm":
        return _eisenstein_norm(params["a"], params["b"])
    elif task_type == "eisenstein_snap":
        prompt, _ = _eisenstein_snap(params["x"], params["y"])
        return prompt
    elif task_type == "covering_radius":
        return _covering_radius()
    elif task_type == "mobius":
        return _mobius(params["n"])
    elif task_type == "legendre":
        return _legendre(params["a"], params["p"])
    elif task_type == "modular_inverse":
        return _modular_inverse(params["a"], params["m"])
    elif task_type == "cyclotomic_eval":
        return _cyclotomic_eval(params["n"], params["x"])
    elif task_type == "generic":
        return _generic(params.get("expression", ""))
    else:
        raise ValueError(f"Unknown task_type: {task_type}")


# ---------------------------------------------------------------------------
# Multi-step chain support (Study 37)
# ---------------------------------------------------------------------------

def translate_chain(
    steps: List[Tuple[str, Dict[str, Any]]],
    model_stage: ModelStage,
) -> str:
    """
    Translate a chain of (task_type, params) steps into a single
    pre-computed prompt that chains them together.

    Study 37 finding: pre-computation scales to 5-step chains.

    Returns a single prompt with all steps enumerated and intermediate
    results pre-computed (for Stage < 4).
    """
    if not steps:
        return "[WARNING: empty chain] No steps provided."

    if model_stage == ModelStage.FULL:
        # Pass through for Stage 4 — just concatenate domain prompts
        parts = []
        for i, (task_type, params) in enumerate(steps, 1):
            try:
                prompt = _translate_full(task_type, params)
                parts.append(f"Step {i}: {prompt}")
            except Exception as e:
                raw = [f"{k}={v}" for k, v in params.items()]
                parts.append(f"Step {i}: [fallback] {task_type}({', '.join(raw)})")
        return "\n".join(parts)

    # Stage < 4: translate each step to arithmetic and chain
    parts = []
    for i, (task_type, params) in enumerate(steps, 1):
        try:
            prompt = _translate_arithmetic(task_type, params)
            parts.append(f"Step {i}: {prompt}")
        except Exception as e:
            raw = [f"{k}={v}" for k, v in params.items()]
            parts.append(f"Step {i}: [fallback: {e}] {task_type}({', '.join(raw)})")

    header = f"Compute the following {len(parts)} step(s) in order:"
    return f"{header}\n" + "\n".join(parts)


# ---------------------------------------------------------------------------
# FleetRouter — with auto-classification and monitoring
# ---------------------------------------------------------------------------

@dataclass
class TranslationLog:
    timestamp: float
    model_id: str
    task_type: str
    stage: ModelStage
    original_params: Dict[str, Any]
    translated_prompt: str


class FleetRouter:
    """
    Maintains a registry of model → stage mappings with caching,
    auto-classifies unknown models (using fleet_stage_classifier),
    routes through translate(), and logs all translations for audit.
    """

    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self._registry: Dict[str, ModelStage] = {}
        self._log: List[TranslationLog] = []

    def register(self, model_id: str, stage: ModelStage) -> None:
        """Manually register a model's stage."""
        self._registry[model_id] = stage
        logger.info("registered %s → %s", model_id, stage.name)

    def get_stage(self, model_id: str) -> ModelStage:
        """Return stage for *model_id*, auto-classifying if unknown."""
        if model_id in self._registry:
            return self._registry[model_id]
        # Try fleet_stage_classifier first
        logger.info("auto-classifying %s via fleet_stage_classifier ...", model_id)
        stage_int = auto_classify_model(model_id)
        stage = stage_int_to_enum(stage_int)
        self._registry[model_id] = stage
        return stage

    def route(
        self,
        model_id: str,
        task_type: str,
        params: Dict[str, Any],
    ) -> str:
        """Translate *task_type* for *model_id* and return the prompt."""
        stage = self.get_stage(model_id)
        prompt = translate(task_type, params, stage)
        entry = TranslationLog(
            timestamp=time.time(),
            model_id=model_id,
            task_type=task_type,
            stage=stage,
            original_params=params,
            translated_prompt=prompt,
        )
        self._log.append(entry)
        logger.info(
            "route %s/%s → %s stage: %s",
            model_id, task_type, stage.name,
            prompt[:80].replace("\n", " "),
        )
        return prompt

    def route_chain(
        self,
        model_id: str,
        steps: List[Tuple[str, Dict[str, Any]]],
    ) -> str:
        """Route a multi-step chain for *model_id*."""
        stage = self.get_stage(model_id)
        return translate_chain(steps, stage)

    @property
    def log(self) -> List[TranslationLog]:
        return list(self._log)

    def audit_summary(self) -> str:
        lines = ["=== Fleet Auto-Translator Audit Log ==="]
        for i, entry in enumerate(self._log, 1):
            lines.append(
                f"[{i}] t={entry.timestamp:.1f}  "
                f"model={entry.model_id}  stage={entry.stage.name}  "
                f"task={entry.task_type}\n"
                f"    prompt: {entry.translated_prompt[:120]}"
            )
        lines.append(f"Total translations: {len(self._log)}")
        lines.append(metrics.summary())
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def _run_tests():
    """Self-contained tests — no Ollama required."""
    import sys

    passed = 0
    failed = 0

    def assert_eq(name, got, expected):
        nonlocal passed, failed
        if got == expected:
            passed += 1
            print(f"  ✅ {name}")
        else:
            failed += 1
            print(f"  ❌ {name}\n     got:      {got!r}\n     expected: {expected!r}")

    def assert_contains(name, got, substring):
        nonlocal passed, failed
        if substring in got:
            passed += 1
            print(f"  ✅ {name}")
        else:
            failed += 1
            print(f"  ❌ {name}\n     got: {got!r}\n     missing: {substring!r}")

    def assert_not_contains(name, got, substring):
        nonlocal passed, failed
        if substring not in got:
            passed += 1
            print(f"  ✅ {name}")
        else:
            failed += 1
            print(f"  ❌ {name}\n     got: {got!r}\n     should not contain: {substring!r}")

    # Reset global state for clean tests
    global metrics, _cache
    metrics = TranslatorMetrics()
    _cache = TranslationCache(max_entries=1000)

    # --- Original tests (translate() arithmetic mode) ----------------------

    print("\n--- translate() arithmetic mode ---")

    r = translate("eisenstein_norm", {"a": 3, "b": 5}, ModelStage.ECHO)
    assert_eq("eisenstein_norm arithmetic", r, "Compute: 9 - 15 + 25 = ?")

    r = translate("eisenstein_norm", {"a": 1, "b": 0}, ModelStage.ECHO)
    assert_eq("eisenstein_norm unit", r, "Compute: 1 - 0 + 0 = ?")

    r = translate("covering_radius", {}, ModelStage.ECHO)
    assert_contains("covering_radius", r, "1/sqrt(3)")

    r = translate("mobius", {"n": 30}, ModelStage.ECHO)
    assert_contains("mobius(30) has factors", r, "(-1)^3")

    r = translate("mobius", {"n": 4}, ModelStage.ECHO)
    assert_contains("mobius(4) squared factor", r, "0")

    r = translate("legendre", {"a": 2, "p": 7}, ModelStage.ECHO)
    assert_contains("legendre(2,7)", r, "quadratic residues")

    r = translate("modular_inverse", {"a": 3, "m": 7}, ModelStage.ECHO)
    assert_contains("modular_inverse(3,7)", r, "3^5")

    r = translate("modular_inverse", {"a": 2, "m": 4}, ModelStage.ECHO)
    assert_contains("modular_inverse no inverse", r, "no modular inverse")

    r = translate("cyclotomic_eval", {"n": 6, "x": 2.0}, ModelStage.ECHO)
    assert_contains("cyclotomic_eval", r, "product over d dividing 6")

    r = translate("generic", {"expression": "Compute the Eisenstein norm of a=3, b=1"}, ModelStage.ECHO)
    assert_not_contains("generic strips domain vocab", r, "Eisenstein")

    # --- Original tests (translate() full pass-through mode) ---------------

    print("\n--- translate() full pass-through mode ---")

    r = translate("eisenstein_norm", {"a": 3, "b": 5}, ModelStage.FULL)
    assert_contains("full eisenstein_norm", r, "Eisenstein norm")

    r = translate("mobius", {"n": 30}, ModelStage.FULL)
    assert_contains("full mobius", r, "Möbius")

    r = translate("legendre", {"a": 2, "p": 7}, ModelStage.FULL)
    assert_contains("full legendre", r, "Legendre")

    r = translate("cyclotomic_eval", {"n": 6, "x": 2.0}, ModelStage.FULL)
    assert_contains("full cyclotomic", r, "cyclotomic")

    # --- NEW TEST 1: Negative formatting fix -------------------------------

    print("\n--- NEW: Negative formatting ---")

    # a=5, b=-3: a²=25, ab=-15, b²=9 → "25 - (-15) + 9"
    r = translate("eisenstein_norm", {"a": 5, "b": -3}, ModelStage.ECHO)
    assert_contains("negative b parenthesized", r, "(-15)")
    assert_not_contains("no double minus", r, "- -")

    # a=-3, b=5: a²=9, ab=-15, b²=25 → "9 - (-15) + 25"
    r = translate("eisenstein_norm", {"a": -3, "b": 5}, ModelStage.ECHO)
    assert_contains("negative ab from negative a", r, "(-15)")

    # Both negative: a=-4, b=-7: a²=16, ab=28, b²=49 → "16 - 28 + 49" (ab is positive!)
    r = translate("eisenstein_norm", {"a": -4, "b": -7}, ModelStage.ECHO)
    assert_contains("both negative (ab positive)", r, "16 - 28 + 49")

    # --- NEW TEST 2: Cache hits -------------------------------------------

    print("\n--- NEW: Cache behavior ---")

    # Reset cache for clean test
    _cache.clear()
    metrics = TranslatorMetrics()

    # First call: cache miss
    r1 = translate("eisenstein_norm", {"a": 3, "b": 5}, ModelStage.ECHO)
    assert_eq("first call: cache miss count", metrics.cache_misses, 1)
    assert_eq("first call: cache hit count", metrics.cache_hits, 0)

    # Same params: cache hit
    r2 = translate("eisenstein_norm", {"a": 3, "b": 5}, ModelStage.ECHO)
    assert_eq("second call: cache hit", metrics.cache_hits, 1)
    assert_eq("cache hit returns same value", r2, r1)

    # Different params: cache miss
    r3 = translate("eisenstein_norm", {"a": 1, "b": 2}, ModelStage.ECHO)
    assert_eq("diff params: cache miss count", metrics.cache_misses, 2)

    # Different stage for same params: cache miss
    r4 = translate("eisenstein_norm", {"a": 3, "b": 5}, ModelStage.FULL)
    assert_eq("diff stage: cache miss", metrics.cache_misses, 3)

    # Hit rate: 1 hit / 4 total = 0.25
    assert_eq("cache hit rate", metrics.cache_hit_rate, 0.25)

    # Cache size
    assert_eq("cache has 3 entries", _cache.size, 3)

    # --- NEW TEST 3: Error recovery / fallback -----------------------------

    print("\n--- NEW: Error recovery ---")

    # Unknown task type: should NOT crash, returns fallback
    r = translate("totally_bogus_task", {"x": 42}, ModelStage.ECHO)
    assert_contains("unknown task fallback has WARNING", r, "[WARNING:")
    assert_contains("unknown task fallback mentions task", r, "totally_bogus_task")

    # Missing required params: should NOT crash
    r = translate("eisenstein_norm", {"a": 3}, ModelStage.ECHO)  # missing 'b'
    assert_contains("missing param fallback has WARNING", r, "[WARNING:")

    # Empty params for task that needs them
    r = translate("mobius", {}, ModelStage.ECHO)
    assert_contains("empty params fallback", r, "[WARNING:")

    # --- NEW TEST 4: Chain translation ------------------------------------

    print("\n--- NEW: Chain translation ---")

    # Chain of 3 steps, arithmetic mode
    chain = translate_chain([
        ("eisenstein_norm", {"a": 3, "b": 5}),
        ("mobius", {"n": 30}),
        ("modular_inverse", {"a": 3, "m": 7}),
    ], ModelStage.ECHO)
    assert_contains("chain has Step 1", chain, "Step 1:")
    assert_contains("chain has Step 2", chain, "Step 2:")
    assert_contains("chain has Step 3", chain, "Step 3:")
    assert_contains("chain arithmetic step 1", chain, "Compute:")
    assert_contains("chain mentions 3 steps", chain, "3 step(s)")

    # Chain of 2 steps, FULL mode
    chain_full = translate_chain([
        ("eisenstein_norm", {"a": 1, "b": 0}),
        ("mobius", {"n": 6}),
    ], ModelStage.FULL)
    assert_contains("chain full has Eisenstein", chain_full, "Eisenstein")
    assert_contains("chain full has Möbius", chain_full, "Möbius")

    # Empty chain
    empty_chain = translate_chain([], ModelStage.ECHO)
    assert_contains("empty chain warning", empty_chain, "WARNING")

    # Chain with error in one step: should still produce output
    chain_with_error = translate_chain([
        ("eisenstein_norm", {"a": 3, "b": 5}),
        ("bogus_task", {"x": 1}),
        ("mobius", {"n": 6}),
    ], ModelStage.ECHO)
    assert_contains("chain with error has Step 1", chain_with_error, "Step 1:")
    assert_contains("chain with error has fallback", chain_with_error, "fallback")
    assert_contains("chain with error has Step 3", chain_with_error, "Step 3:")

    # --- NEW TEST 5: Edge cases (a=0, b=0, large numbers) -----------------

    print("\n--- NEW: Edge cases ---")

    # a=0, b=0 → 0 - 0 + 0 = 0
    r = translate("eisenstein_norm", {"a": 0, "b": 0}, ModelStage.ECHO)
    assert_contains("zero norm", r, "0 - 0 + 0")

    # Large numbers
    r = translate("eisenstein_norm", {"a": 1000, "b": 2000}, ModelStage.ECHO)
    assert_contains("large numbers", r, "1000000 - 2000000 + 4000000")

    # a=1, b=1 → 1 - 1 + 1 = 1
    r = translate("eisenstein_norm", {"a": 1, "b": 1}, ModelStage.ECHO)
    assert_eq("unit (1,1)", r, "Compute: 1 - 1 + 1 = ?")

    # Negative equal: a=-1, b=-1 → 1 - 1 + 1 (same as positive)
    r = translate("eisenstein_norm", {"a": -1, "b": -1}, ModelStage.ECHO)
    assert_eq("negative unit (-1,-1)", r, "Compute: 1 - 1 + 1 = ?")

    # --- NEW TEST 6: Monitoring metrics -----------------------------------

    print("\n--- NEW: Monitoring metrics ---")

    # Reset
    metrics = TranslatorMetrics()
    _cache.clear()

    # Do some translations
    translate("eisenstein_norm", {"a": 1, "b": 2}, ModelStage.ECHO)
    translate("eisenstein_norm", {"a": 1, "b": 2}, ModelStage.ECHO)  # cache hit
    translate("mobius", {"n": 6}, ModelStage.META_ECHO)

    assert_eq("metrics: 3 translations", metrics.translation_count, 3)
    assert_eq("metrics: 1 cache hit", metrics.cache_hits, 1)
    assert_eq("metrics: 2 cache misses", metrics.cache_misses, 2)
    assert_contains("metrics summary has avg latency", metrics.summary(), "Avg latency")

    # Record accuracy feedback
    metrics.record_accuracy("ECHO", True)
    metrics.record_accuracy("ECHO", True)
    metrics.record_accuracy("ECHO", False)
    assert_eq("ECHO accuracy 66.7%", round(metrics.stage_accuracy("ECHO"), 3), 0.667)

    # --- FleetRouter tests (original) -------------------------------------

    print("\n--- FleetRouter ---")

    metrics = TranslatorMetrics()
    _cache.clear()

    router = FleetRouter()
    router.register("gpt-4", ModelStage.FULL)
    router.register("tinyllama", ModelStage.ECHO)

    p1 = router.route("gpt-4", "eisenstein_norm", {"a": 3, "b": 5})
    assert_contains("router gpt-4 passthrough", p1, "Eisenstein norm")

    p2 = router.route("tinyllama", "eisenstein_norm", {"a": 3, "b": 5})
    assert_contains("router tinyllama arithmetic", p2, "Compute: 9")

    assert_eq("router log count", len(router.log), 2)
    assert_eq("router log[0] task", router.log[0].task_type, "eisenstein_norm")
    assert_eq("router log[0] stage", router.log[0].stage, ModelStage.FULL)
    assert_eq("router log[1] stage", router.log[1].stage, ModelStage.ECHO)

    summary = router.audit_summary()
    assert_contains("audit summary", summary, "Total translations: 2")

    # --- Formatting helpers unit tests ------------------------------------

    print("\n--- _fmt_num and _fmt_expr ---")

    assert_eq("_fmt_num positive", _fmt_num(42), "42")
    assert_eq("_fmt_num negative", _fmt_num(-14), "(-14)")
    assert_eq("_fmt_num zero", _fmt_num(0), "0")

    assert_eq("_fmt_expr basic", _fmt_expr([("", 25), ("-", 15), ("+", 9)]), "25 - 15 + 9")
    assert_eq("_fmt_expr negative mid", _fmt_expr([("", 25), ("-", -15), ("+", 9)]), "25 - (-15) + 9")
    assert_eq("_fmt_expr all negative", _fmt_expr([("", -3), ("+", -5)]), "(-3) + (-5)")

    # --- Summary -----------------------------------------------------------

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")
    if failed:
        print("❌ SOME TESTS FAILED")
        sys.exit(1)
    else:
        print("✅ ALL TESTS PASSED")

    print(f"\n{metrics.summary()}")


if __name__ == "__main__":
    _run_tests()
