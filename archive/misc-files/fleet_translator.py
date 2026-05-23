#!/usr/bin/env python3
"""
Fleet Auto-Translator — Production Module
==========================================
Translates domain-specific mathematical tasks into bare arithmetic
for Stage 1-3 models, and passes through for Stage 4 models.

Study 31: Based on findings from fleet auto-translation research.
"""

from __future__ import annotations

import json
import logging
import math
import re
import time
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
# Stage classification via 6 diagnostic probes
# ---------------------------------------------------------------------------

# Probes: each is a (prompt, accept_fn) pair.
# accept_fn(response_text) -> bool indicating the model "passed" that probe.

def _probe_exact(expected: str):
    """Return an acceptor that checks for an exact integer/string in the response."""
    def accept(resp: str) -> bool:
        # strip whitespace, look for the number anywhere
        cleaned = re.sub(r"[,\s]", "", resp)
        return expected in cleaned
    return accept

def _probe_contains_any(*keywords: str):
    def accept(resp: str) -> bool:
        lower = resp.lower()
        return any(k.lower() in lower for k in keywords)
    return accept

PROBES: List[Tuple[str, Any]] = [
    # Probe 0: basic addition  (ECHO gate)
    ("What is 7 + 5? Reply with only the number.", _probe_exact("12")),
    # Probe 1: multiplication  (ECHO gate)
    ("What is 6 * 8? Reply with only the number.", _probe_exact("48")),
    # Probe 2: follow meta-instruction  (META_ECHO gate)
    ("Translate to German: 'three'. Reply with only the German word.", _probe_contains_any("drei")),
    # Probe 3: simple algebra  (META_ECHO gate)
    ("If x + 3 = 10, what is x? Reply with only the number.", _probe_exact("7")),
    # Probe 4: domain vocabulary — Eisenstein  (FULL gate)
    ("What is the Eisenstein norm of a=1, b=0? Reply with only the number.", _probe_exact("1")),
    # Probe 5: domain vocabulary — quadratic residue  (FULL gate)
    ("Is 2 a quadratic residue mod 7? Reply yes or no.", _probe_contains_any("yes")),
]

# Scoring thresholds
#   0-1 correct → ECHO
#   2-3 correct → META_ECHO
#   4-5 correct → META_ECHO (almost there)
#   all 6       → FULL

def classify_stage(model_id: str, base_url: str = "http://localhost:11434") -> ModelStage:
    """
    Run 6 diagnostic probes against *model_id* (Ollama) and return its stage.

    Falls back to ModelStage.NONE if the model is unreachable.
    """
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
# Translation functions
# ---------------------------------------------------------------------------

def _eisenstein_norm(a: int | float, b: int | float) -> str:
    """Eisenstein norm = a² − ab + b².  Translate to plain arithmetic."""
    a2 = a * a
    ab = a * b
    b2 = b * b
    return f"Compute: {a2} - {ab} + {b2} = ?"


def _eisenstein_snap(x: float, y: float) -> Tuple[str, float]:
    """
    Snap (x, y) to the nearest Eisenstein lattice point.

    Returns (arithmetic_prompt, result).
    For Stage 1-3 we compute locally and return a verification prompt.
    """
    # The Eisenstein lattice basis: (1, 0) and (-1/2, sqrt(3)/2).
    # Convert to coordinates in that basis.
    s3 = math.sqrt(3)
    # b1 = (1, 0), b2 = (-0.5, s3/2)
    # Solve: [x, y] = a * b1 + b * b2
    # x = a - b/2,  y = b * s3/2
    # => b = 2*y/s3,  a = x + b/2 = x + y/s3
    b_raw = 2 * y / s3
    a_raw = x + y / s3
    # Round to nearest lattice point
    a_int = round(a_raw)
    b_int = round(b_raw)
    result = (a_int, b_int)
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
    # Compute Φ_n(x) by product formula:
    # Φ_n(x) = ∏_{d|n} (x^d - 1)^μ(n/d)
    # For translation we just compute it and give the arithmetic.
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
    # Remove known domain keywords
    domain_words = [
        r"\bEisenstein\b", r"\bcyclotomic\b", r"\bMöbius\b", r"\bMobius\b",
        r"\bLegendre\b", r"\bquadratic\s+residue\b", r"\bmodular\s+inverse\b",
        r"\bLamport\b", r"\bcovering\s+radius\b", r"\blattice\b",
        r"\bnorm\b", r"\bsnap\b", r"\bspline\b",
    ]
    cleaned = expression
    for pat in domain_words:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)
    # Collapse whitespace
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
# Main translate() dispatcher
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
    """
    if model_stage == ModelStage.FULL:
        # Pass through with domain vocabulary intact
        return _translate_full(task_type, params)

    # Stage 1-3: translate to bare arithmetic
    return _translate_arithmetic(task_type, params)


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
# FleetRouter
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
    auto-classifies unknown models, routes through translate(),
    and logs all translations for audit.
    """

    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self._registry: Dict[str, ModelStage] = {}
        self._log: List[TranslationLog] = []

    # -- registry management ------------------------------------------------

    def register(self, model_id: str, stage: ModelStage) -> None:
        """Manually register a model's stage."""
        self._registry[model_id] = stage
        logger.info("registered %s → %s", model_id, stage.name)

    def get_stage(self, model_id: str) -> ModelStage:
        """Return stage for *model_id*, auto-classifying if unknown."""
        if model_id in self._registry:
            return self._registry[model_id]
        logger.info("auto-classifying %s ...", model_id)
        stage = classify_stage(model_id, self.ollama_url)
        self._registry[model_id] = stage
        return stage

    # -- routing ------------------------------------------------------------

    def route(
        self,
        model_id: str,
        task_type: str,
        params: Dict[str, Any],
    ) -> str:
        """
        Translate *task_type* for *model_id* and return the prompt.

        Logs the translation for audit.
        """
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

    # -- audit log ----------------------------------------------------------

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

    # --- Task type translations (Stage ECHO / arithmetic) ------------------

    print("\n--- translate() arithmetic mode ---")

    r = translate("eisenstein_norm", {"a": 3, "b": 5}, ModelStage.ECHO)
    assert_eq("eisenstein_norm arithmetic", r, "Compute: 9 - 15 + 25 = ?")

    r = translate("eisenstein_norm", {"a": 1, "b": 0}, ModelStage.ECHO)
    assert_eq("eisenstein_norm unit", r, "Compute: 1 - 0 + 0 = ?")

    r = translate("covering_radius", {}, ModelStage.ECHO)
    assert_contains("covering_radius", r, "1/sqrt(3)")

    r = translate("mobius", {"n": 30}, ModelStage.ECHO)
    assert_contains("mobius(30) has factors", r, "(-1)^3")
    # 30 = 2×3×5 → 3 distinct primes → μ = (-1)^3 = -1

    r = translate("mobius", {"n": 4}, ModelStage.ECHO)
    assert_contains("mobius(4) squared factor", r, "0")
    # 4 = 2² → squared factor → μ = 0

    r = translate("legendre", {"a": 2, "p": 7}, ModelStage.ECHO)
    assert_contains("legendre(2,7)", r, "quadratic residues")
    # QR mod 7: {1, 2, 4}; 2 ∈ residues

    r = translate("modular_inverse", {"a": 3, "m": 7}, ModelStage.ECHO)
    assert_contains("modular_inverse(3,7)", r, "3^5")
    # 3^(7-2) mod 7 = 3^5 mod 7 = 5

    r = translate("modular_inverse", {"a": 2, "m": 4}, ModelStage.ECHO)
    assert_contains("modular_inverse no inverse", r, "no modular inverse")

    r = translate("cyclotomic_eval", {"n": 6, "x": 2.0}, ModelStage.ECHO)
    assert_contains("cyclotomic_eval", r, "product over d dividing 6")

    r = translate("generic", {"expression": "Compute the Eisenstein norm of a=3, b=1"}, ModelStage.ECHO)
    if "Eisenstein" not in r:
        passed += 1
        print("  ✅ generic strips domain vocab")
    else:
        failed += 1
        print(f"  ❌ generic strips domain vocab\n     got: {r!r}")

    # --- Task type translations (Stage FULL / pass-through) ----------------

    print("\n--- translate() full pass-through mode ---")

    r = translate("eisenstein_norm", {"a": 3, "b": 5}, ModelStage.FULL)
    assert_contains("full eisenstein_norm", r, "Eisenstein norm")

    r = translate("mobius", {"n": 30}, ModelStage.FULL)
    assert_contains("full mobius", r, "Möbius")

    r = translate("legendre", {"a": 2, "p": 7}, ModelStage.FULL)
    assert_contains("full legendre", r, "Legendre")

    r = translate("cyclotomic_eval", {"n": 6, "x": 2.0}, ModelStage.FULL)
    assert_contains("full cyclotomic", r, "cyclotomic")

    # --- Unknown task type -------------------------------------------------

    print("\n--- error handling ---")
    try:
        translate("bogus_task", {}, ModelStage.ECHO)
        failed += 1
        print("  ❌ unknown task_type should raise")
    except ValueError:
        passed += 1
        print("  ✅ unknown task_type raises ValueError")

    # --- FleetRouter -------------------------------------------------------

    print("\n--- FleetRouter ---")

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

    # Audit summary should work
    summary = router.audit_summary()
    assert_contains("audit summary", summary, "Total translations: 2")

    # --- Summary -----------------------------------------------------------

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")
    if failed:
        print("❌ SOME TESTS FAILED")
        sys.exit(1)
    else:
        print("✅ ALL TESTS PASSED")

    # Print audit
    print(f"\n{router.audit_summary()}")


if __name__ == "__main__":
    _run_tests()
