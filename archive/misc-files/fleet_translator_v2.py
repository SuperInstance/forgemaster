#!/usr/bin/env python3
"""
Fleet Auto-Translator V2 — Activation-Key Model (Domain-Aware)
================================================================
Based on Hypothesis V6 (Activation-Key Model): LLMs store mathematical
procedures activated by context cues (vocabulary tokens). Symbolic notation
is unreliable; domain labels are reliable activation keys.

Study 56 proved the vocabulary wall is MATH-SPECIFIC. For all other
domains, natural language IS the activation key. The translator should
only activate for math tasks.

Key changes from V1:
1. Activation-Key Engineering: inject correct domain labels instead of stripping vocab
2. Notation Normalizer: convert unicode math to ASCII/natural language equivalents
3. Stage-Aware Routing: adjust translation depth per model stage
4. Conservation-Aware Batching: batch queries to maintain attention coherence
5. Domain Detection: only apply translation for math-domain tasks (Study 56)

Study 46 notation gradient: unicode ²=0%, a*a=22%, natural lang=67%, step-by-step=~100%
Study 56 cross-domain: activation-key effect is math-specific (-4pp for non-math)
"""

from __future__ import annotations

import json
import logging
import math
import re
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional, Sequence, Tuple

import requests

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("fleet_translator_v2")
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("[%(name)s] %(levelname)s: %(message)s"))
logger.addHandler(_handler)
logger.setLevel(logging.DEBUG)


# ---------------------------------------------------------------------------
# Stage classification (IntEnum for numeric comparison)
# ---------------------------------------------------------------------------

class ModelStage(IntEnum):
    """Capability stages for fleet models — numeric for comparison."""
    NONE = 0       # untested / unreachable
    ECHO = 1       # Stage 1: can barely echo, no math
    META_ECHO = 2  # Stage 2: follows meta-prompts, spotty math
    CAPABLE = 3    # Stage 3: handles most arithmetic, struggles with domain vocab
    FULL = 4       # Stage 4: understands domain vocabulary natively


# ---------------------------------------------------------------------------
# Known model stage registry (avoids re-probing)
# ---------------------------------------------------------------------------

KNOWN_STAGES: Dict[str, ModelStage] = {
    # Stage 4 — notation-immune
    "ByteDance/Seed-2.0-mini": ModelStage.FULL,
    "ByteDance/Seed-2.0-code": ModelStage.FULL,
    "ByteDance/Seed-2.0-pro":  ModelStage.FULL,
    # Stage 3 — need activation keys
    "NousResearch/Hermes-3-Llama-3.1-405B": ModelStage.CAPABLE,
    "NousResearch/Hermes-3-Llama-3.1-70B":  ModelStage.CAPABLE,
    "Qwen/Qwen3-235B-A22B-Instruct-2507":  ModelStage.CAPABLE,
    "Qwen/Qwen3.5-397B-A17B":              ModelStage.CAPABLE,
    "Qwen/Qwen3.6-35B-A3B":                ModelStage.CAPABLE,
    # Stage 2 — need pre-computed arithmetic
    "deepseek-chat": ModelStage.META_ECHO,
    # Stage 1 — barely functional
    # (most small models, not currently in fleet)
}


# ---------------------------------------------------------------------------
# Notation Normalizer
# ---------------------------------------------------------------------------

class NotationNormalizer:
    """
    Convert unicode/symbolic math notation to forms models handle better.

    Study 46 gradient: unicode ²=0%, a*a=22%, natural lang=67%, step-by-step=~100%
    """

    # Unicode superscript digit → ASCII
    _SUPERSCRIPT_MAP = {
        '⁰': '0', '¹': '1', '²': '2', '³': '3', '⁴': '4',
        '⁵': '5', '⁶': '6', '⁷': '7', '⁸': '8', '⁹': '9',
    }

    # Greek → Latin name
    _GREEK_MAP = {
        'α': 'alpha', 'β': 'beta', 'γ': 'gamma', 'δ': 'delta',
        'ε': 'epsilon', 'ζ': 'zeta', 'η': 'eta', 'θ': 'theta',
        'ι': 'iota', 'κ': 'kappa', 'λ': 'lambda', 'μ': 'mu',
        'ν': 'nu', 'ξ': 'xi', 'π': 'pi', 'ρ': 'rho',
        'σ': 'sigma', 'τ': 'tau', 'υ': 'upsilon', 'φ': 'phi',
        'χ': 'chi', 'ψ': 'psi', 'ω': 'omega',
        'Γ': 'Gamma', 'Δ': 'Delta', 'Θ': 'Theta', 'Λ': 'Lambda',
        'Ξ': 'Xi', 'Π': 'Pi', 'Σ': 'Sigma', 'Φ': 'Phi',
        'Ψ': 'Psi', 'Ω': 'Omega',
    }

    # Domain label patterns → canonical activation key
    _DOMAIN_PATTERNS = {
        r'\bEisenstein\b': 'Eisenstein',
        r'\bcyclotomic\b': 'cyclotomic',
        r'\bMöbius\b': 'Möbius',
        r'\bMobius\b': 'Möbius',
        r'\bLegendre\b': 'Legendre',
        r'\bquadratic\s+residue\b': 'quadratic residue',
        r'\bmodular\s+inverse\b': 'modular inverse',
        r'\bHurwitz\b': 'Hurwitz',
        r'\bFrobenius\b': 'Frobenius',
        r'\bLamport\b': 'Lamport',
        r'\bcovering\s+radius\b': 'covering radius',
        r'\blattice\b': 'lattice',
        r'\bspline\b': 'spline',
        r'\bFourier\b': 'Fourier',
        r'\bHilbert\b': 'Hilbert',
    }

    @classmethod
    def normalize_unicode(cls, text: str) -> str:
        """Convert unicode superscripts to ASCII equivalents."""
        # Handle patterns like a² → a^2
        result = text
        for greek, latin in cls._GREEK_MAP.items():
            result = result.replace(greek, latin)
        for sup, digit in cls._SUPERSCRIPT_MAP.items():
            result = result.replace(sup, f'^{digit}')
        return result

    @classmethod
    def to_ascii_math(cls, text: str) -> str:
        """
        Convert notation to ASCII math form.
        Gradient position: ~22% accuracy.
        a² → a^2, a^2 → a*a
        Only inserts * between single-letter variables, not inside words.
        """
        result = cls.normalize_unicode(text)
        # Convert x^2 to x*x form for clarity
        result = re.sub(r'(\w)\^(\d)', lambda m: '*'.join([m.group(1)] * int(m.group(2))), result)
        # Convert implicit multiplication ONLY between single-letter variables
        # e.g. "ab" → "a*b" but NOT inside words like "Compute" or "squared"
        result = re.sub(r'\b([a-zA-Z])([a-zA-Z])\b', r'\1*\2', result)
        return result

    @classmethod
    def to_natural_language(cls, text: str) -> str:
        """
        Convert notation to natural language.
        Gradient position: ~67% accuracy.
        a² → "a squared", ab → "a times b"
        """
        # First, convert unicode superscripts to ^N notation
        result = cls.normalize_unicode(text)  # handles Greek too

        # ^N patterns → natural language
        result = re.sub(r'(\w)\^2\b', r'\1 squared', result)
        result = re.sub(r'(\w)\^3\b', r'\1 cubed', result)
        result = re.sub(r'(\w)\^(\d+)\b', lambda m: f'{m.group(1)} to the {m.group(2)}th power', result)

        # Replace - with " minus " and + with " plus " (arithmetic operators)
        result = re.sub(r'(?<=[a-zA-Z0-9])\s*-\s*(?=[a-zA-Z0-9])', ' minus ', result)
        result = re.sub(r'(?<=[a-zA-Z0-9])\s*\+\s*(?=[a-zA-Z0-9])', ' plus ', result)

        # Explicit * → "times"
        result = result.replace('*', ' times ')

        return result

    @classmethod
    def to_step_by_step(cls, expression: str, operation: str = "compute") -> str:
        """
        Convert notation to step-by-step natural language.
        Gradient position: ~100% accuracy.
        """
        # First normalize
        text = cls.to_natural_language(expression)
        return f"Step by step, {operation}: {text}. First, then next, then finally."

    @classmethod
    def detect_notation(cls, text: str) -> str:
        """Detect what kind of notation is present."""
        has_unicode_superscript = any(c in cls._SUPERSCRIPT_MAP for c in text)
        has_greek = any(c in cls._GREEK_MAP for c in text)
        has_caret = bool(re.search(r'\^', text))
        # Implicit mult: 2+ adjacent lowercase letters that are NOT real words
        # Skip common English words
        _skip = {'compute','minus','plus','times','step','first','then','finally','norm','snap','using','the'}
        words = re.findall(r'[a-zA-Z]{2,}', text.lower())
        has_implicit_mult = any(w not in _skip and len(w) <= 4 for w in words)
        return "unicode" if has_unicode_superscript else \
               "ascii" if has_caret else \
               "implicit" if has_implicit_mult else \
               "plain"

    @classmethod
    def detect_domain_labels(cls, text: str) -> List[str]:
        """Detect domain labels present in text."""
        found = []
        for pattern, label in cls._DOMAIN_PATTERNS.items():
            if re.search(pattern, text, re.IGNORECASE):
                found.append(label)
        return found

    @classmethod
    def has_symbolic_notation(cls, text: str) -> bool:
        """Check if text contains mathematical notation."""
        has_unicode_superscript = any(c in cls._SUPERSCRIPT_MAP for c in text)
        has_greek = any(c in cls._GREEK_MAP for c in text)
        has_caret = bool(re.search(r'\^', text))
        has_operator = bool(re.search(r'[+\-*/=]', text))
        return has_unicode_superscript or has_greek or has_caret or has_operator


# ---------------------------------------------------------------------------
# Activation-Key Engineer
# ---------------------------------------------------------------------------

class ActivationKeyEngineer:
    """
    Instead of stripping vocabulary (V1), ADD the right activation key.

    States from V6:
    - STATE A: Label + Formula → 100% (optimal)
    - STATE B: Label only → 0-100% (varies by label)
    - STATE C: Formula only → 0% (no activation)
    - STATE D: Step-by-step → ~100% (natural language IS the key)

    Strategy:
    - Notation without label → inject the correct domain label
    - Label + notation → pass through (already STATE A)
    - Step-by-step language → pass through (already STATE D)
    """

    # Map notation patterns to their domain activation keys
    _NOTATION_TO_KEY = {
        r'a²\s*[-−]\s*ab\s*\+\s*b²': 'Eisenstein norm',        # a²-ab+b²
        r'a\^2\s*[-−]\s*a\s*\*\s*b\s*\+\s*b\^2': 'Eisenstein norm',
        r'a\s*squared\s*minus\s*a\s*b\s*plus\s*b\s*squared': 'Eisenstein norm',
        r'Φ[_\d]': 'cyclotomic polynomial',
        r'μ\(\d+\)': 'Möbius function',
        r'mu\(\d+\)': 'Möbius function',
        r'\(\d+\|\d+\)': 'Legendre symbol',
        r'\d+\^?\s*mod\s+\d+': 'modular arithmetic',
        r'norm\s*\(': 'norm',
        r'snap\s*\(': 'lattice snap',
    }

    # Domain → safe activation key (no conflicting procedures)
    # "Hurwitz" is a LANDMINE (activates wrong formula) — never inject it
    _SAFE_KEYS = {
        'eisenstein_norm': 'Eisenstein norm',
        'eisenstein_snap': 'Eisenstein lattice',
        'covering_radius': 'covering radius of the Eisenstein lattice',
        'mobius': 'Möbius function',
        'legendre': 'Legendre symbol (quadratic residue)',
        'modular_inverse': 'modular inverse (number theory)',
        'cyclotomic_eval': 'cyclotomic polynomial',
        'fourier': 'Fourier transform',
        'generic': None,  # no key for generic
    }

    @classmethod
    def inject_key(cls, text: str, task_type: Optional[str] = None) -> str:
        """
        Analyze text and inject the correct activation key if missing.

        Returns text in STATE A (label + formula) if possible.
        """
        labels = NotationNormalizer.detect_domain_labels(text)
        has_notation = NotationNormalizer.has_symbolic_notation(text)

        # STATE D: step-by-step language → pass through (check FIRST)
        if cls._is_step_by_step(text):
            logger.debug("STATE D detected: step-by-step language")
            return text

        # STATE A: already has label + notation → pass through
        if labels and has_notation:
            logger.debug("STATE A detected: label=%s, notation present", labels)
            return text

        # STATE C: notation without label → inject key
        if has_notation and not labels:
            key = cls._detect_key_from_notation(text) or cls._key_from_task(task_type)
            if key:
                logger.debug("STATE C→A: injecting key '%s'", key)
                return f"Using the {key}: {text}"

        # STATE B: label only (no notation) → add notation if we know the task
        if labels and not has_notation and task_type:
            key = cls._SAFE_KEYS.get(task_type)
            if key and key not in text:
                logger.debug("STATE B: reinforcing with key '%s'", key)
                return f"Using the {key}: {text}"

        # Plain text — try task-based injection
        if task_type:
            key = cls._SAFE_KEYS.get(task_type)
            if key and key.lower() not in text.lower():
                logger.debug("PLAIN→A: injecting key '%s'", key)
                return f"Using the {key}: {text}"

        return text

    @classmethod
    def _is_step_by_step(cls, text: str) -> bool:
        """Detect step-by-step procedural language."""
        markers = [
            'step by step', 'first compute', 'first calculate', 'first,', 'first ',
            'then compute', 'then calculate', 'then subtract', 'then add', 'then multiply',
            'finally', 'next compute', 'next calculate', 'next ',
        ]
        lower = text.lower()
        # "step by step" alone is sufficient
        if 'step by step' in lower:
            return True
        return sum(1 for m in markers if m in lower) >= 2

    @classmethod
    def _detect_key_from_notation(cls, text: str) -> Optional[str]:
        """Try to determine the activation key from notation patterns."""
        for pattern, key in cls._NOTATION_TO_KEY.items():
            if re.search(pattern, text, re.IGNORECASE):
                return key
        return None

    @classmethod
    def _key_from_task(cls, task_type: Optional[str]) -> Optional[str]:
        """Get activation key from task type."""
        if task_type:
            return cls._SAFE_KEYS.get(task_type)
        return None


# ---------------------------------------------------------------------------
# Domain Detector (Study 56)
# ---------------------------------------------------------------------------

class DomainDetector:
    """
    Detect the domain of a prompt to decide translation mode.

    Study 56 proved the vocabulary wall only exists in math. For all other
    domains, natural language IS the activation key. Translation should only
    activate for math tasks.

    Domains:
      math      -> full activation-key translation (vocabulary wall exists)
      chemistry -> minimal translation (strip jargon, keep structure)
      physics   -> minimal translation (strip jargon, keep structure)
      logic     -> passthrough (no translation needed)
      code      -> passthrough (no translation needed, ceiling effect)
      general   -> passthrough
    """

    # Domain keyword patterns with weights for scoring
    _DOMAIN_KEYWORDS: Dict[str, Dict[str, float]] = {
        "math": {
            # Specific math terms (high weight)
            "eisenstein": 3.0, "cyclotomic": 3.0, "möbius": 3.0, "mobius": 3.0,
            "legendre": 3.0, "hurwitz": 3.0, "frobenius": 3.0, "lamport": 2.0,
            "lattice": 2.5, "spline": 2.0, "fourier": 2.5, "hilbert": 2.5,
            "norm": 2.0, "norms": 2.0,
            # Computation keywords
            "compute": 1.5, "calculate": 1.5, "computation": 1.5,
            # Math notation patterns
            "quadratic": 2.0, "modular": 2.0, "inverse": 1.5, "residue": 2.0,
            # Symbols
            "ω": 2.0, "ζ": 2.0, "φ": 1.5, "π": 1.5, "∑": 2.0, "∏": 2.0,
            "√": 2.0, "∫": 2.5,
            # Arithmetic patterns
            "squared": 1.0, "cubed": 1.0, "polynomial": 2.0, "integer": 1.0,
            "factorize": 1.5, "prime": 1.5, "divisor": 1.5,
        },
        "chemistry": {
            "molar": 3.0, "compound": 2.0, "reaction": 2.0,
            "element": 2.0, "formula": 1.5, "h2o": 3.0, "molecule": 2.5,
            "atom": 2.0, "atomic": 2.0, "bond": 2.0, "ion": 2.0,
            "mol": 2.0, "mole": 2.0,
            "acid": 2.0, "oxidation": 2.5,
            "reduction": 2.0, "valence": 2.0, "isotope": 2.0,
            "stoichiometry": 3.0, "avogadro": 3.0,
        },
        "physics": {
            "force": 2.0, "acceleration": 2.5, "velocity": 2.5, "energy": 2.0,
            "newton": 2.5, "momentum": 2.5, "gravity": 2.0, "mass": 1.5,
            "kinetic": 2.5, "potential": 1.5, "friction": 2.0, "torque": 2.5,
            "wavelength": 2.5, "frequency": 2.0, "voltage": 2.0, "current": 2.0,
            "resistance": 2.0, "circuit": 2.0, "joule": 2.0, "watt": 2.0,
            "coulomb": 2.5, "tesla": 2.5, "amplitude": 2.0,
        },
        "logic": {
            "implies": 2.5, "if-then": 2.5, "therefore": 2.0, "deduction": 2.5,
            "premise": 2.5, "syllogism": 3.0, "proposition": 2.0, "conjunction": 2.5,
            "disjunction": 2.5, "negation": 2.0, "contrapositive": 3.0,
            "contradiction": 2.0, "tautology": 2.5, "modus": 2.5,
            "ponens": 2.5, "tollens": 2.5, "quantifier": 2.5,
            "existential": 2.5, "universal": 1.5, "inference": 2.0,
        },
        "code": {
            "function": 2.0, "implement": 2.0, "algorithm": 2.0, "loop": 1.5,
            "class": 1.5, "def ": 2.0, "return": 1.5, "import": 1.5,
            "variable": 1.0, "array": 1.5, "hash": 1.5, "sort": 1.0,
            "recursive": 2.0, "iterate": 1.5, "compile": 2.0, "runtime": 1.5,
            "debug": 1.5, "refactor": 2.0, "async": 2.0, "thread": 1.5,
            "linked list": 2.5, "binary tree": 2.5, "stack": 2.0, "queue": 2.0,
        },
    }

    # Regex patterns for structural detection (higher confidence)
    _STRUCTURAL_PATTERNS: Dict[str, List[Tuple[str, float]]] = {
        "math": [
            (r'\b\d+\s*[+\-*/]\s*\d+', 2.0),       # arithmetic: 3 + 5
            (r'\b[a-z]\^\d', 2.0),                    # a^2 notation
            (r'[α-ωΑ-Ω]', 2.0),                         # Greek letters
            (r'\bmod\s+\d+', 2.0),                     # mod N
            (r'\d²', 3.0),                          # unicode superscript
            (r'(?:a|b|x|n)²', 3.0),              # explicit squared
            (r'Φ[_\d]', 3.0),                        # cyclotomic
            (r'μ\(\d+\)', 3.0),                    # Möbius function
            (r'\(\d+\|\d+\)', 3.0),                  # Legendre symbol
        ],
        "chemistry": [
            (r'\b[A-Z][a-z]?\d+[A-Z]', 2.0),        # Multi-element formulas: H2SO, NaC
            (r'\bH[2-9]\b', 2.5),                    # H2, H3 etc
            (r'\d+\.\d+\s*g/mol', 3.0),            # g/mol units with decimal
            (r'\bNaCl\b|\bHCl\b|\bNaOH\b|\bH2SO4\b|\bH2O\b', 3.0),  # specific compounds
        ],
        "physics": [
            (r'\d+\s*(?:m/s|kg|N|J|W|V|A|Hz|Pa)', 3.0),  # SI units
            (r'F\s*=\s*ma', 3.0),                # Newton's second law
            (r'E\s*=\s*mc²', 3.0),               # Einstein
            (r'KE\s*=|PE\s*=', 2.5),         # kinetic/potential energy
        ],
        "logic": [
            (r'[A-Z]\s*→\s*[A-Z]', 3.0),        # A → B notation
            (r'[A-Z]\s*∧\s*[A-Z]', 3.0),        # A ∧ B notation
            (r'[A-Z]\s*∨\s*[A-Z]', 3.0),        # A ∨ B notation
            (r'¬[A-Z]', 3.0),                     # ¬A notation
            (r'if.*then.*therefore', 2.5),        # syllogistic pattern
        ],
        "code": [
            (r'def\s+\w+\s*\(', 3.0),              # function def
            (r'class\s+\w+', 3.0),                  # class def
            (r'for\s+\w+\s+in\s+', 2.0),          # for loop
            (r'if\s+.*:', 1.5),                   # if statement
            (r'import\s+\w+', 2.0),                 # import statement
            (r'```\w*\n', 2.0),                     # code fence
        ],
    }

    @classmethod
    def detect_domain(cls, prompt: str) -> Tuple[str, float]:
        """
        Detect the domain of a prompt.

        Returns:
            Tuple of (domain, confidence) where domain is one of:
            "math", "chemistry", "physics", "logic", "code", "general"
            and confidence is 0.0-1.0.
        """
        lower = prompt.lower()
        scores: Dict[str, float] = {}

        # Phase 1: Keyword scoring
        for domain, keywords in cls._DOMAIN_KEYWORDS.items():
            score = 0.0
            for keyword, weight in keywords.items():
                # Use simple contains for short keywords, word-aware for longer
                if len(keyword) <= 2:
                    if keyword in lower:
                        score += weight
                else:
                    pattern = re.escape(keyword)
                    matches = re.findall(pattern, lower)
                    score += weight * len(matches)
            scores[domain] = score

        # Phase 2: Structural pattern scoring (higher confidence)
        for domain, patterns in cls._STRUCTURAL_PATTERNS.items():
            for pattern, weight in patterns:
                if re.search(pattern, prompt):
                    scores[domain] = scores.get(domain, 0.0) + weight

        # Phase 3: Pick best domain
        if not scores:
            return "general", 0.5

        best_domain = max(scores, key=lambda d: scores[d])
        best_score = scores[best_domain]

        # No meaningful signal -> general
        if best_score < 1.0:
            return "general", 0.3

        # Calculate confidence (0.0-1.0)
        sorted_scores = sorted(scores.values(), reverse=True)
        gap = (sorted_scores[0] - sorted_scores[1]) if len(sorted_scores) > 1 else sorted_scores[0]
        confidence = min(1.0, best_score / 5.0)  # normalize by typical max
        confidence = max(0.3, min(1.0, confidence + gap / 10.0))  # boost for clear winners

        return best_domain, round(confidence, 2)

    @classmethod
    def get_translation_mode(cls, domain: str) -> str:
        """
        Get the recommended translation mode for a domain.

        Study 56 findings:
          math      -> "full" (activation-key translation needed)
          chemistry -> "minimal" (strip jargon, keep structure)
          physics   -> "minimal" (strip jargon, keep structure)
          logic     -> "passthrough" (no translation needed)
          code      -> "passthrough" (ceiling effect, no translation needed)
          general   -> "passthrough" (no domain signal)
        """
        _MODES = {
            "math": "full",
            "chemistry": "minimal",
            "physics": "minimal",
            "logic": "passthrough",
            "code": "passthrough",
            "general": "passthrough",
        }
        return _MODES.get(domain, "passthrough")


# ---------------------------------------------------------------------------
# Stage-Aware Translator (Domain-Aware, Study 56)
# ---------------------------------------------------------------------------

def translate_for_stage(
    prompt: str,
    stage: ModelStage,
    task_type: Optional[str] = None,
    domain: Optional[str] = None,
) -> str:
    """
    Translate a prompt for a given model stage, domain-aware.

    Study 56: Only math-domain tasks need activation-key translation.
    All other domains get passthrough or minimal translation.

    Args:
        prompt: The raw prompt to translate.
        stage: Model capability stage.
        task_type: Optional task type hint.
        domain: Optional pre-detected domain (skips detection if provided).

    Returns:
        Translated prompt appropriate for the model stage and domain.
    """
    # Detect domain if not provided
    if domain is None:
        domain, _confidence = DomainDetector.detect_domain(prompt)

    # Get translation mode for this domain
    mode = DomainDetector.get_translation_mode(domain)

    # --- Passthrough domains (Study 56: no vocabulary wall) ---
    if mode == "passthrough":
        logger.debug("Domain '%s': passthrough (no vocabulary wall per Study 56)", domain)
        return prompt

    # --- Minimal translation domains ---
    if mode == "minimal":
        # For chemistry/physics: normalize unicode, strip excessive jargon,
        # but keep natural language structure intact
        result = NotationNormalizer.normalize_unicode(prompt)
        logger.debug("Domain '%s': minimal translation (unicode normalize only)", domain)
        return result

    # --- Full translation: math domain (original behavior) ---
    # This is the only domain with a vocabulary wall (Study 56)
    if stage >= ModelStage.FULL:
        # Stage 4: model is notation-immune, pass through
        # Labeled Paradox (Study 47): DON'T inject activation keys for Stage 4.
        logger.debug("Stage 4 + math: passthrough (Labeled Paradox: no key injection)")
        return prompt

    if stage >= ModelStage.CAPABLE:
        # Stage 3: inject activation key, normalize unicode to ASCII
        result = ActivationKeyEngineer.inject_key(prompt, task_type)
        result = NotationNormalizer.normalize_unicode(result)
        logger.debug("Stage 3 + math: activation key + unicode normalize")
        return result

    if stage >= ModelStage.META_ECHO:
        # Stage 2: natural language + activation key
        result = ActivationKeyEngineer.inject_key(prompt, task_type)
        result = NotationNormalizer.to_natural_language(result)
        if not NotationNormalizer.detect_domain_labels(result) and task_type:
            result = NotationNormalizer.to_step_by_step(result)
        logger.debug("Stage 2 + math: natural language + activation key")
        return result

    # Stage 0/1: pre-compute everything, bare arithmetic only
    if task_type:
        result = _pre_compute(task_type, prompt)
        if result:
            return result
    result = NotationNormalizer.to_natural_language(prompt)
    for pattern in NotationNormalizer._DOMAIN_PATTERNS:
        result = re.sub(pattern, '', result, flags=re.IGNORECASE)
    result = re.sub(r'\s+', ' ', result).strip()
    logger.debug("Stage 0/1 + math: bare natural language")
    return result


# ---------------------------------------------------------------------------
# Task-specific translators (carried from V1 with improvements)
# ---------------------------------------------------------------------------

def _eisenstein_norm_arithmetic(a: int | float, b: int | float) -> str:
    """Eisenstein norm = a² − ab + b². Pre-compute for Stage 1."""
    a2 = a * a
    ab = a * b
    b2 = b * b
    return f"Compute: {a2} - {ab} + {b2} = ?"


def _eisenstein_norm_stage3(a: int | float, b: int | float) -> str:
    """Stage 3: activation key + ASCII notation."""
    return f"Using the Eisenstein norm: compute a^2 - a*b + b^2 where a={a}, b={b}"


def _eisenstein_norm_stage2(a: int | float, b: int | float) -> str:
    """Stage 2: natural language step-by-step."""
    return (
        f"Step by step, compute the Eisenstein norm of a={a}, b={b}: "
        f"First, compute {a} squared = {a*a}. "
        f"Then compute {a} times {b} = {a*b}. "
        f"Then compute {b} squared = {b*b}. "
        f"Finally, compute {a*a} minus {a*b} plus {b*b}."
    )


def _mobius_arithmetic(n: int) -> str:
    """Translate Möbius μ(n) to prime factorization + (-1)^k."""
    factors: List[int] = []
    m = n
    d = 2
    while d * d <= m:
        while m % d == 0:
            factors.append(d)
            m //= d
        d += 1
    if m > 1:
        factors.append(m)
    unique = set(factors)
    if len(factors) != len(unique):
        return f"The number {n} has a squared prime factor, so the answer is 0."
    k = len(unique)
    return f"Count the distinct prime factors of {n}: there are {k}. Compute (-1)^{k} = ?"


def _legendre_arithmetic(a: int, p: int) -> str:
    """Translate Legendre symbol to quadratic residue enumeration."""
    if p <= 2:
        return f"p={p} is trivial; the answer is 1."
    residues = sorted({(x * x) % p for x in range(1, p)})
    member = (a % p) in residues
    return (
        f"List all quadratic residues mod {p}: {residues}. "
        f"Is {a % p} in that list? Reply yes or no."
    )


def _modular_inverse_arithmetic(a: int, m: int) -> str:
    """Translate modular inverse via Fermat's little theorem."""
    if math.gcd(a, m) != 1:
        return f"gcd({a}, {m}) is not 1, so no modular inverse exists."
    exp = m - 2
    result = pow(a, exp, m)
    return f"Compute {a}^{exp} mod {m}. (Answer is {result}.)"


def _cyclotomic_arithmetic(n: int, x: float) -> str:
    """Translate cyclotomic polynomial evaluation to numeric computation."""
    result = 1.0
    divs = _divisors(n)
    for d in divs:
        sub = n // d
        mu = _mobius_value(sub)
        if mu == 0:
            continue
        val = x ** d - 1
        if mu == 1:
            result *= val
        elif mu == -1:
            if val == 0:
                result = 0.0
                break
            result /= val
    return (
        f"Using the cyclotomic polynomial: evaluate product over d dividing {n} "
        f"of (x^d - 1)^mu({n}/d) where x={x}. Compute numerically. (Answer = {result:.6f})"
    )


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


def _pre_compute(task_type: str, prompt: str) -> str:
    """Attempt task-specific pre-computation for Stage 1."""
    # This is a fallback — specific task params would be better
    return ""


# ---------------------------------------------------------------------------
# Main translate() dispatcher — V2
# ---------------------------------------------------------------------------

def translate(
    task_type: str,
    params: Dict[str, Any],
    stage: ModelStage,
) -> str:
    """
    Translate a domain task for the given model stage.

    Stage 4: domain vocabulary passes through (notation-immune)
    Stage 3: activation key injection + ASCII normalization
    Stage 2: natural language conversion + activation key
    Stage 1: pre-computed bare arithmetic only
    """
    # Stage 4: pass through with domain vocabulary
    if stage >= ModelStage.FULL:
        return _translate_full(task_type, params)

    # Stage 0/1: bare arithmetic (same as V1)
    if stage <= ModelStage.ECHO:
        return _translate_arithmetic(task_type, params)

    # Stage 2-3: activation-key aware translation
    return _translate_activation_key(task_type, params, stage)


def _translate_full(task_type: str, params: Dict[str, Any]) -> str:
    """Build a prompt with domain vocabulary intact (Stage 4)."""
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
    """Translate to bare arithmetic (Stage 1). Carried from V1."""
    if task_type == "eisenstein_norm":
        return _eisenstein_norm_arithmetic(params["a"], params["b"])
    elif task_type == "eisenstein_snap":
        x, y = params["x"], params["y"]
        s3 = math.sqrt(3)
        b_raw = 2 * y / s3
        a_raw = x + y / s3
        return (
            f"Find integers a, b closest to: a = {a_raw:.4f}, b = {b_raw:.4f}. "
            f"Round each to nearest integer. Reply 'a=X b=Y'."
        )
    elif task_type == "covering_radius":
        return "Compute 1/sqrt(3) to 4 decimal places."
    elif task_type == "mobius":
        return _mobius_arithmetic(params["n"])
    elif task_type == "legendre":
        return _legendre_arithmetic(params["a"], params["p"])
    elif task_type == "modular_inverse":
        return _modular_inverse_arithmetic(params["a"], params["m"])
    elif task_type == "cyclotomic_eval":
        return _cyclotomic_arithmetic(params["n"], params["x"])
    elif task_type == "generic":
        expr = params.get("expression", "")
        # Strip domain vocab, keep arithmetic
        for pat in NotationNormalizer._DOMAIN_PATTERNS:
            expr = re.sub(pat, '', expr, flags=re.IGNORECASE)
        expr = re.sub(r'\s+', ' ', expr).strip()
        return expr if expr else f"Compute: {params.get('expression', '')}"
    else:
        raise ValueError(f"Unknown task_type: {task_type}")


def _translate_activation_key(
    task_type: str, params: Dict[str, Any], stage: ModelStage
) -> str:
    """
    Stage 2-3: Use activation keys instead of stripping vocabulary.

    Stage 3: activation key + ASCII notation
    Stage 2: activation key + natural language
    """
    if task_type == "eisenstein_norm":
        a, b = params["a"], params["b"]
        if stage >= ModelStage.CAPABLE:
            return _eisenstein_norm_stage3(a, b)
        else:
            return _eisenstein_norm_stage2(a, b)

    elif task_type == "eisenstein_snap":
        x, y = params["x"], params["y"]
        s3 = math.sqrt(3)
        b_raw = 2 * y / s3
        a_raw = x + y / s3
        if stage >= ModelStage.CAPABLE:
            return (
                f"Using the Eisenstein lattice snap: find lattice coordinates "
                f"for point ({x}, {y}). Compute a = {a_raw:.4f}, b = {b_raw:.4f}, "
                f"round to nearest integers."
            )
        else:
            return (
                f"Step by step, snap point ({x}, {y}) to the Eisenstein lattice: "
                f"First, compute a = x + y divided by sqrt(3) = {a_raw:.4f}. "
                f"Then compute b = 2 times y divided by sqrt(3) = {b_raw:.4f}. "
                f"Finally round both to nearest integers."
            )

    elif task_type == "covering_radius":
        if stage >= ModelStage.CAPABLE:
            return "Using the covering radius of the Eisenstein lattice: compute 1/sqrt(3)."
        else:
            return "Step by step, compute the covering radius: first compute sqrt of 3, then compute 1 divided by that value."

    elif task_type == "mobius":
        n = params["n"]
        factors_msg = _mobius_arithmetic(n)
        if stage >= ModelStage.CAPABLE:
            return f"Using the Möbius function: {factors_msg}"
        else:
            return f"Step by step, compute the Möbius function of {n}: {factors_msg}"

    elif task_type == "legendre":
        a, p = params["a"], params["p"]
        if stage >= ModelStage.CAPABLE:
            return f"Using the Legendre symbol (quadratic residue): {_legendre_arithmetic(a, p)}"
        else:
            return f"Step by step, check if {a} is a quadratic residue mod {p}: {_legendre_arithmetic(a, p)}"

    elif task_type == "modular_inverse":
        a, m = params["a"], params["m"]
        if stage >= ModelStage.CAPABLE:
            return f"Using modular inverse (number theory): {_modular_inverse_arithmetic(a, m)}"
        else:
            return f"Step by step, find the modular inverse of {a} mod {m}: {_modular_inverse_arithmetic(a, m)}"

    elif task_type == "cyclotomic_eval":
        n, x = params["n"], params["x"]
        if stage >= ModelStage.CAPABLE:
            return _cyclotomic_arithmetic(n, x)
        else:
            return f"Step by step, evaluate the cyclotomic polynomial: {_cyclotomic_arithmetic(n, x)}"

    elif task_type == "generic":
        expr = params.get("expression", "")
        result = ActivationKeyEngineer.inject_key(expr, task_type="generic")
        if stage >= ModelStage.CAPABLE:
            result = NotationNormalizer.normalize_unicode(result)
        else:
            result = NotationNormalizer.to_natural_language(result)
        return result

    else:
        raise ValueError(f"Unknown task_type: {task_type}")


# ---------------------------------------------------------------------------
# FleetRouter V2 — with stage-aware routing and batching
# ---------------------------------------------------------------------------

@dataclass
class TranslationLog:
    timestamp: float
    model_id: str
    task_type: str
    stage: ModelStage
    original_params: Dict[str, Any]
    translated_prompt: str
    activation_key_injected: bool = False


@dataclass
class BatchItem:
    """A single item in a batch request."""
    task_type: str
    params: Dict[str, Any]
    translated_prompt: str


class FleetRouter:
    """
    V2 Router with:
    - Stage-aware routing from known registry
    - Activation-key engineering for Stage 2-3 models
    - Conservation-aware batching
    """

    def __init__(
        self,
        deepinfra_key: Optional[str] = None,
        deepinfra_url: str = "https://api.deepinfra.com/v1/openai/chat/completions",
    ):
        self._registry: Dict[str, ModelStage] = dict(KNOWN_STAGES)
        self._log: List[TranslationLog] = []
        self.deepinfra_key = deepinfra_key
        self.deepinfra_url = deepinfra_url

    # -- registry management ------------------------------------------------

    def register(self, model_id: str, stage: ModelStage) -> None:
        self._registry[model_id] = stage
        logger.info("registered %s → %s", model_id, stage.name)

    def get_stage(self, model_id: str) -> ModelStage:
        if model_id in self._registry:
            return self._registry[model_id]
        # Default to Stage 3 for unknown models (activation-key territory)
        logger.info("unknown model %s, defaulting to CAPABLE (Stage 3)", model_id)
        return ModelStage.CAPABLE

    # -- routing ------------------------------------------------------------

    def route(
        self,
        model_id: str,
        task_type: str,
        params: Dict[str, Any],
    ) -> str:
        stage = self.get_stage(model_id)
        prompt = translate(task_type, params, stage)
        labels = NotationNormalizer.detect_domain_labels(prompt)
        entry = TranslationLog(
            timestamp=time.time(),
            model_id=model_id,
            task_type=task_type,
            stage=stage,
            original_params=params,
            translated_prompt=prompt,
            activation_key_injected=len(labels) > 0,
        )
        self._log.append(entry)
        logger.info(
            "route %s/%s → stage %s [%s]: %s",
            model_id, task_type, stage.name,
            "KEY" if labels else "NO-KEY",
            prompt[:80].replace("\n", " "),
        )
        return prompt

    # -- conservation-aware batching ----------------------------------------

    def route_batch(
        self,
        model_id: str,
        items: Sequence[Tuple[str, Dict[str, Any]]],
    ) -> List[str]:
        """
        Translate a batch of tasks for the same model.

        Conservation-aware: maintains attention context coherence by
        keeping the same activation key across related tasks in the batch.
        """
        stage = self.get_stage(model_id)
        results = []

        # Group by task type for attention coherence
        # (same domain key → consecutive queries)
        grouped: Dict[str, List[Tuple[int, str, Dict]]] = {}
        for i, (task_type, params) in enumerate(items):
            grouped.setdefault(task_type, []).append((i, task_type, params))

        ordered = [None] * len(items)
        for task_type, group in grouped.items():
            for idx, tt, params in group:
                prompt = translate(tt, params, stage)
                ordered[idx] = prompt

                entry = TranslationLog(
                    timestamp=time.time(),
                    model_id=model_id,
                    task_type=tt,
                    stage=stage,
                    original_params=params,
                    translated_prompt=prompt,
                    activation_key_injected=True,
                )
                self._log.append(entry)

        return [p for p in ordered if p is not None]

    # -- DeepInfra integration ----------------------------------------------

    def send_to_model(
        self,
        model_id: str,
        task_type: str,
        params: Dict[str, Any],
        temperature: float = 0.0,
        max_tokens: int = 256,
    ) -> Dict[str, Any]:
        """
        Translate and send a prompt to a DeepInfra model.
        Returns the full API response.
        """
        if not self.deepinfra_key:
            raise RuntimeError("No DeepInfra API key configured")

        prompt = self.route(model_id, task_type, params)
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.deepinfra_key}",
            "Content-Type": "application/json",
        }
        resp = requests.post(
            self.deepinfra_url,
            json=payload,
            headers=headers,
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()

    # -- audit log ----------------------------------------------------------

    @property
    def log(self) -> List[TranslationLog]:
        return list(self._log)

    def audit_summary(self) -> str:
        lines = ["=== Fleet Auto-Translator V2 Audit Log ==="]
        for i, entry in enumerate(self._log, 1):
            key_tag = "🔑" if entry.activation_key_injected else "  "
            lines.append(
                f"[{i}] {key_tag} t={entry.timestamp:.1f}  "
                f"model={entry.model_id}  stage={entry.stage.name}  "
                f"task={entry.task_type}\n"
                f"     prompt: {entry.translated_prompt[:120]}"
            )
        lines.append(f"Total translations: {len(self._log)}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def _run_tests():
    """Self-contained tests — no API calls required."""
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
            print(f"  ❌ {name}\n     got: {got!r}\n     unexpected: {substring!r}")

    NN = NotationNormalizer
    AK = ActivationKeyEngineer

    # ====================================================================
    print("\n--- Notation Normalizer ---")
    # ====================================================================

    # Unicode superscript conversion
    assert_eq("normalize a²", NN.normalize_unicode("a²"), "a^2")
    assert_eq("normalize a²-ab+b²", NN.normalize_unicode("a²-ab+b²"), "a^2-ab+b^2")

    # Greek conversion
    assert_contains("normalize μ(30)", NN.normalize_unicode("μ(30)"), "mu(30)")
    assert_contains("normalize Φ_6", NN.normalize_unicode("Φ_6(x)"), "Phi_6(x)")

    # ASCII math
    result = NN.to_ascii_math("a²")
    assert_contains("ascii a²", result, "a*a")

    # Natural language
    result = NN.to_natural_language("a²-ab+b²")
    assert_contains("nl squared", result, "squared")
    assert_contains("nl minus", result, "minus")

    # Notation detection
    assert_eq("detect unicode", NN.detect_notation("a²"), "unicode")
    assert_eq("detect plain", NN.detect_notation("hello world"), "plain")

    # Domain label detection
    assert_eq("detect Eisenstein", NN.detect_domain_labels("Eisenstein norm of a=1"), ["Eisenstein"])
    assert_eq("detect no labels", NN.detect_domain_labels("compute 3 + 5"), [])

    # Has symbolic notation
    assert_eq("has notation a²", NN.has_symbolic_notation("a²-ab+b²"), True)
    assert_eq("has notation plain", NN.has_symbolic_notation("hello world"), False)

    # ====================================================================
    print("\n--- Activation Key Engineer ---")
    # ====================================================================

    # STATE A: label + notation → passthrough
    result = AK.inject_key("Eisenstein norm: a²-ab+b²", "eisenstein_norm")
    assert_eq("STATE A passthrough", result, "Eisenstein norm: a²-ab+b²")

    # STATE C: notation only → inject key
    result = AK.inject_key("a²-ab+b²", "eisenstein_norm")
    assert_contains("STATE C→A inject key", result, "Eisenstein")

    # STATE D: step-by-step → passthrough
    result = AK.inject_key("First compute a*a, then subtract a*b, then add b*b", "eisenstein_norm")
    assert_not_contains("STATE D passthrough", result, "Using the")

    # Task-based injection for plain text
    result = AK.inject_key("compute a=3, b=5", "eisenstein_norm")
    assert_contains("plain→inject Eisenstein", result, "Eisenstein")

    # ====================================================================
    print("\n--- Stage-Aware Translation ---")
    # ====================================================================

    # Stage 4 (FULL): passthrough with domain vocab
    r = translate("eisenstein_norm", {"a": 3, "b": 5}, ModelStage.FULL)
    assert_contains("stage4 eisenstein", r, "Eisenstein norm")

    r = translate("mobius", {"n": 30}, ModelStage.FULL)
    assert_contains("stage4 mobius", r, "Möbius")

    # Stage 3 (CAPABLE): activation key + ASCII
    r = translate("eisenstein_norm", {"a": 3, "b": 5}, ModelStage.CAPABLE)
    assert_contains("stage3 eisenstein key", r, "Eisenstein norm")
    assert_contains("stage3 ascii notation", r, "a^2")

    # Stage 2 (META_ECHO): natural language
    r = translate("eisenstein_norm", {"a": 3, "b": 5}, ModelStage.META_ECHO)
    assert_contains("stage2 natural lang", r, "squared")

    # Stage 1 (ECHO): bare arithmetic
    r = translate("eisenstein_norm", {"a": 3, "b": 5}, ModelStage.ECHO)
    assert_eq("stage1 arithmetic", r, "Compute: 9 - 15 + 25 = ?")

    # ====================================================================
    print("\n--- V1 Compatibility (arithmetic mode) ---")
    # ====================================================================

    r = translate("eisenstein_norm", {"a": 1, "b": 0}, ModelStage.ECHO)
    assert_eq("eisenstein_norm unit", r, "Compute: 1 - 0 + 0 = ?")

    r = translate("covering_radius", {}, ModelStage.ECHO)
    assert_contains("covering_radius", r, "1/sqrt(3)")

    r = translate("mobius", {"n": 30}, ModelStage.ECHO)
    assert_contains("mobius(30)", r, "(-1)^3")

    r = translate("mobius", {"n": 4}, ModelStage.ECHO)
    assert_contains("mobius(4) squared", r, "0")

    r = translate("legendre", {"a": 2, "p": 7}, ModelStage.ECHO)
    assert_contains("legendre(2,7)", r, "quadratic residues")

    r = translate("modular_inverse", {"a": 3, "m": 7}, ModelStage.ECHO)
    assert_contains("modinv(3,7)", r, "3^5")

    r = translate("modular_inverse", {"a": 2, "m": 4}, ModelStage.ECHO)
    assert_contains("modinv no inverse", r, "no modular inverse")

    r = translate("cyclotomic_eval", {"n": 6, "x": 2.0}, ModelStage.ECHO)
    assert_contains("cyclotomic_eval", r, "product over d dividing 6")

    # ====================================================================
    print("\n--- Stage Gradient Verification ---")
    # ====================================================================

    # Same task across all stages — should get progressively more translated
    params = {"a": 2, "b": 3}
    r4 = translate("eisenstein_norm", params, ModelStage.FULL)
    r3 = translate("eisenstein_norm", params, ModelStage.CAPABLE)
    r2 = translate("eisenstein_norm", params, ModelStage.META_ECHO)
    r1 = translate("eisenstein_norm", params, ModelStage.ECHO)

    # Stage 4: domain vocab present
    assert_contains("gradient s4 domain", r4, "Eisenstein")
    # Stage 3: domain vocab + ASCII notation
    assert_contains("gradient s3 domain", r3, "Eisenstein")
    assert_not_contains("gradient s3 no unicode", r3, "²")
    # Stage 2: natural language
    assert_contains("gradient s2 natural", r2, "squared")
    # Stage 1: bare numbers
    assert_not_contains("gradient s1 no vocab", r1, "Eisenstein")
    assert_contains("gradient s1 numbers", r1, "Compute:")

    # ====================================================================
    print("\n--- FleetRouter V2 ---")
    # ====================================================================

    router = FleetRouter()
    router.register("Seed-2.0-mini", ModelStage.FULL)
    router.register("hermes-405b", ModelStage.CAPABLE)
    router.register("tinyllama", ModelStage.ECHO)

    p1 = router.route("Seed-2.0-mini", "eisenstein_norm", {"a": 3, "b": 5})
    assert_contains("router seed passthrough", p1, "Eisenstein norm")

    p2 = router.route("hermes-405b", "eisenstein_norm", {"a": 3, "b": 5})
    assert_contains("router hermes activation key", p2, "Eisenstein norm")
    assert_not_contains("router hermes no unicode", p2, "²")

    p3 = router.route("tinyllama", "eisenstein_norm", {"a": 3, "b": 5})
    assert_contains("router tiny arithmetic", p3, "Compute: 9")

    assert_eq("router log count", len(router.log), 3)
    assert_eq("router log[0] stage", router.log[0].stage, ModelStage.FULL)
    assert_eq("router log[1] stage", router.log[1].stage, ModelStage.CAPABLE)
    assert_eq("router log[2] stage", router.log[2].stage, ModelStage.ECHO)

    # Batch routing
    batch_items = [
        ("eisenstein_norm", {"a": 1, "b": 0}),
        ("eisenstein_norm", {"a": 2, "b": 3}),
        ("mobius", {"n": 30}),
    ]
    batch_results = router.route_batch("hermes-405b", batch_items)
    assert_eq("batch result count", len(batch_results), 3)

    # Unknown model defaults to Stage 3
    p4 = router.route("unknown-model", "eisenstein_norm", {"a": 1, "b": 1})
    assert_contains("unknown model stage3", p4, "Eisenstein norm")

    # Audit summary
    summary = router.audit_summary()
    assert_contains("audit summary", summary, "Total translations:")

    # ====================================================================
    print("\n--- Error Handling ---")
    # ====================================================================

    try:
        translate("bogus_task", {}, ModelStage.ECHO)
        failed += 1
        print("  ❌ unknown task_type should raise")
    except ValueError:
        passed += 1
        print("  ✅ unknown task_type raises ValueError")

    # ====================================================================
    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")
    if failed:
        print("❌ SOME TESTS FAILED")
        sys.exit(1)
    else:
        print("✅ ALL TESTS PASSED")

    print(f"\n{router.audit_summary()}")


def auto_detect_stage(query: str, model_id: Optional[str] = None) -> ModelStage:
    """
    Auto-detect the appropriate model stage from query complexity and model name.

    Labeled Paradox (Study 47) awareness:
    - Stage 4 models get NO activation key injection
    - Stage 3+ models get activation keys
    - Stage 1-2 get natural language / pre-computed arithmetic

    Args:
        query: The prompt or expression to translate.
        model_id: Optional model identifier to look up in KNOWN_STAGES.

    Returns:
        Detected ModelStage.
    """
    # 1. Check known model registry first
    if model_id and model_id in KNOWN_STAGES:
        return KNOWN_STAGES[model_id]

    # 2. Heuristic from model name
    if model_id:
        name_lower = model_id.lower()
        # Stage 4 indicators
        if any(k in name_lower for k in ['seed-2', 'gpt-4', 'claude-3.5', 'claude-opus', 'gemini-2']):
            return ModelStage.FULL
        # Stage 2 indicators
        if any(k in name_lower for k in ['deepseek-chat', 'llama-3', 'mistral-7b']):
            return ModelStage.META_ECHO
        # Stage 1 indicators (very small models)
        if any(k in name_lower for k in ['tinyllama', 'phi-1', 'opt-125']):
            return ModelStage.ECHO

    # 3. Heuristic from query complexity
    has_notation = NotationNormalizer.has_symbolic_notation(query)
    has_domain_labels = bool(NotationNormalizer.detect_domain_labels(query))
    has_unicode = any(c in NotationNormalizer._SUPERSCRIPT_MAP for c in query)

    # Simple plain text → Stage 3 (should work with activation keys)
    if not has_notation and not has_domain_labels:
        return ModelStage.CAPABLE

    # Domain notation present → needs higher stage or activation keys
    if has_domain_labels and has_notation:
        return ModelStage.CAPABLE  # activation keys will help

    # Complex notation → default Stage 3
    return ModelStage.CAPABLE


def translate_batch(
    queries: Sequence[str],
    model: Optional[str] = None,
    stage: Optional[ModelStage] = None,
    task_type: Optional[str] = None,
    domain: Optional[str] = None,
) -> List[str]:
    """
    Translate multiple queries efficiently.

    Args:
        queries: List of prompts/expressions to translate.
        model: Optional model ID for stage auto-detection.
        stage: Optional explicit stage (overrides model-based detection).
        task_type: Optional task type for activation key injection.
        domain: Optional pre-detected domain (skips per-query detection).

    Returns:
        List of translated prompts, one per input query.
    """
    if stage is None:
        stage = auto_detect_stage(
            queries[0] if queries else "",
            model_id=model,
        )

    results = []
    for query in queries:
        results.append(translate_for_stage(query, stage, task_type=task_type, domain=domain))
    return results


if __name__ == "__main__":
    _run_tests()
