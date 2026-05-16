#!/usr/bin/env python3
"""
flux_substrate.py — Flux Substrate Translation Experiment
=========================================================
Tests whether knowledge discovered by one model can survive translation
through other models. The thesis: different models are different perceptual
substrates (Greek vs Chinese). Can we compile between them?

Models: Seed-2.0-mini, Hermes-70B, Qwen3.6-35B
Modes:  DIRECT, EXPLAINED, TILED, ANTI_TRANSLATED
Tests:  sort, reverse, dedup, second_largest, moving_average
"""

import json
import os
import sys
import time
import hashlib
import urllib.request
import urllib.error
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Config ──────────────────────────────────────────────────────────────

KEY_PATH = Path.home() / ".openclaw" / "workspace" / ".credentials" / "deepinfra-api-key.txt"
ENDPOINT = "https://api.deepinfra.com/v1/openai/chat/completions"
API_KEY = KEY_PATH.read_text().strip() if KEY_PATH.exists() else os.environ.get("DEEPINFRA_KEY", "")
TIMEOUT = 90  # seconds per call

MODELS = {
    "seed-mini": "ByteDance/Seed-2.0-mini",
    "hermes-70b": "NousResearch/Hermes-3-Llama-3.1-70B",
    "qwen-35b": "Qwen/Qwen3.6-35B-A3B",
}

MODEL_NAMES = list(MODELS.keys())
# All 6 ordered pairs
MODEL_PAIRS = [(a, b) for a in MODEL_NAMES for b in MODEL_NAMES if a != b]

MODES = ["DIRECT", "EXPLAINED", "TILED", "ANTI_TRANSLATED"]

# ── Test Functions ──────────────────────────────────────────────────────

TEST_FUNCTIONS = {
    "sort": {
        "difficulty": "easy",
        "description": "Sort a list of numbers in ascending order",
        "tiles": [
            {"in": [3, 1, 4, 1, 5, 9, 2, 6], "out": [1, 1, 2, 3, 4, 5, 6, 9]},
            {"in": [10, -1, 0, 7], "out": [-1, 0, 7, 10]},
            {"in": [5], "out": [5]},
            {"in": [], "out": []},
        ],
        "verify": lambda f, tiles: all(f(t["in"]) == t["out"] for t in tiles),
    },
    "reverse": {
        "difficulty": "easy",
        "description": "Reverse a list of numbers",
        "tiles": [
            {"in": [1, 2, 3, 4, 5], "out": [5, 4, 3, 2, 1]},
            {"in": [9], "out": [9]},
            {"in": [], "out": []},
            {"in": [3, 1, 4], "out": [4, 1, 3]},
        ],
        "verify": lambda f, tiles: all(f(t["in"]) == t["out"] for t in tiles),
    },
    "dedup": {
        "difficulty": "medium",
        "description": "Remove duplicates from a list, preserving order of first occurrence",
        "tiles": [
            {"in": [1, 2, 3, 2, 1, 4], "out": [1, 2, 3, 4]},
            {"in": [5, 5, 5, 5], "out": [5]},
            {"in": [1, 2, 3], "out": [1, 2, 3]},
            {"in": [], "out": []},
        ],
        "verify": lambda f, tiles: all(f(t["in"]) == t["out"] for t in tiles),
    },
    "second_largest": {
        "difficulty": "medium",
        "description": "Find the second largest number in a list",
        "tiles": [
            {"in": [5, 2, 8, 1, 9, 3], "out": 8},
            {"in": [1, 1, 2, 2], "out": 2},
            {"in": [10, 5], "out": 5},
            {"in": [7, 7, 7, 8], "out": 7},
        ],
        "verify": lambda f, tiles: all(f(t["in"]) == t["out"] for t in tiles),
    },
    "moving_average": {
        "difficulty": "hard",
        "description": "Compute moving average with window size 3",
        "tiles": [
            {"in": [1, 2, 3, 4, 5], "out": [2.0, 3.0, 4.0]},
            {"in": [10, 20, 30], "out": [20.0]},
            {"in": [1, 1, 1, 1], "out": [1.0, 1.0]},
            {"in": [0, 0, 0], "out": [0.0]},
        ],
        "verify": lambda f, tiles: all(
            all(abs(a - b) < 0.001 for a, b in zip(f(t["in"]), t["out"]))
            for t in tiles
        ),
    },
}


# ── API Call ────────────────────────────────────────────────────────────

def call_model(model_key: str, messages: List[Dict[str, str]], max_tokens: int = 1024, temperature: float = 0.2) -> str:
    """Call a model via DeepInfra API. Returns content string."""
    model_id = MODELS[model_key]
    payload = json.dumps({
        "model": model_id,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode()

    req = urllib.request.Request(
        ENDPOINT,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"__ERROR__: {type(e).__name__}: {e}"


# ── Stage 1: Discovery — Model A discovers a function from tiles ────────

DISCOVERY_SYSTEM = """You are a precise function discovery engine. Given input→output examples (tiles),
infer the function and implement it as a Python function. Return ONLY the function code, nothing else.
The function must handle all the given examples correctly."""

DISCOVERY_PROMPT = """Given these input→output tiles, discover and implement the underlying function.

Tiles:
{tiles}

Function description hint: {description}

Write a single Python function called `discovered_fn` that takes a single argument (the input)
and returns the correct output. Return ONLY the function code, no explanation."""


def discover_function(model_key: str, func_name: str) -> Tuple[str, str]:
    """Model A discovers a function from tiles. Returns (code, explanation)."""
    func_info = TEST_FUNCTIONS[func_name]
    tiles_str = "\n".join(f"  input: {t['in']} → output: {t['out']}" for t in func_info["tiles"])

    messages = [
        {"role": "system", "content": DISCOVERY_SYSTEM},
        {"role": "user", "content": DISCOVERY_PROMPT.format(tiles=tiles_str, description=func_info["description"])},
    ]

    code = call_model(model_key, messages, max_tokens=512, temperature=0.1)
    return code


EXPLAIN_SYSTEM = """You are explaining a function you discovered. Explain what the function does in plain natural language.
Be precise enough that another programmer could reimplement it from your explanation alone."""

EXPLAIN_PROMPT = """You discovered a function. Here is the code:

```python
{code}
```

The function handles these examples:
{tiles}

Explain in natural language EXACTLY what this function does, including:
1. What the inputs and outputs are
2. The step-by-step algorithm
3. Any edge cases
4. The exact data transformations

Be precise — someone who has NEVER seen this code must be able to recreate it from your explanation."""


def explain_function(model_key: str, code: str, func_name: str) -> str:
    """Model explains its function in natural language."""
    func_info = TEST_FUNCTIONS[func_name]
    tiles_str = "\n".join(f"  input: {t['in']} → output: {t['out']}" for t in func_info["tiles"])

    messages = [
        {"role": "system", "content": EXPLAIN_SYSTEM},
        {"role": "user", "content": EXPLAIN_PROMPT.format(code=code, tiles=tiles_str)},
    ]

    return call_model(model_key, messages, max_tokens=512, temperature=0.2)


ANTI_TRANSLATE_SYSTEM = """You are a creative communicator. You must explain a function you discovered,
but using OPPOSITE vocabulary from what would be natural. 
- If the function is mathematical, explain it like telling a STORY about everyday objects
- If the function is about lists/arrays, explain it using metaphors of people in line, books on shelves, etc.
- If it involves numbers, use words like "items", "things", "pieces" instead of "numbers" or "integers"
- Avoid ANY technical programming terms — no "array", "loop", "index", "iterate", "variable", "function"
- Use casual everyday language, as if explaining to a child

The key constraint: your explanation must be PRECISE enough that someone could recreate the exact function from it."""


def anti_translate(model_key: str, code: str, func_name: str) -> str:
    """Model explains its function using opposite vocabulary."""
    func_info = TEST_FUNCTIONS[func_name]
    tiles_str = "\n".join(f"  input: {t['in']} → output: {t['out']}" for t in func_info["tiles"])

    messages = [
        {"role": "system", "content": ANTI_TRANSLATE_SYSTEM},
        {"role": "user", "content": EXPLAIN_PROMPT.format(code=code, tiles=tiles_str) + "\n\nRemember: use OPPOSITE vocabulary. No technical terms."},
    ]

    return call_model(model_key, messages, max_tokens=512, temperature=0.3)


# ── Stage 2: Translation — Model B reproduces from Model A's output ────

TRANSLATE_SYSTEM = """You are a precise code implementation engine. You will receive a description, code, or examples
from another system. Your job is to implement a Python function that matches the described behavior.
Return ONLY the function code, nothing else."""

TRANSLATE_DIRECT_PROMPT = """Here is a Python function written by another system:

```python
{code}
```

Implement EXACTLY this same function. Call it `translated_fn`. Return ONLY the function code."""

TRANSLATE_EXPLAINED_PROMPT = """Another system described a function to you. Here is their explanation:

{explanation}

Implement a Python function called `translated_fn` that matches this description exactly.
The function should handle these test cases:
{tiles}

Return ONLY the function code."""

TRANSLATE_TILED_PROMPT = """You are given ONLY input→output examples (tiles) of a function.
You must figure out what the function does and implement it.

Tiles:
{tiles}

Function hint: {description}

Implement a Python function called `translated_fn` that produces the correct output for any input of this type.
Return ONLY the function code."""

TRANSLATE_ANTI_PROMPT = """Another system described a function using casual, non-technical language.
Here is their description:

{explanation}

Despite the casual language, this describes a precise function that handles these cases:
{tiles}

Implement a Python function called `translated_fn` that matches this behavior exactly.
Return ONLY the function code."""


def translate(model_key: str, mode: str, code: str, explanation: str, anti_explanation: str, func_name: str) -> str:
    """Model B translates Model A's output into its own implementation."""
    func_info = TEST_FUNCTIONS[func_name]
    tiles_str = "\n".join(f"  input: {t['in']} → output: {t['out']}" for t in func_info["tiles"])

    if mode == "DIRECT":
        prompt = TRANSLATE_DIRECT_PROMPT.format(code=code)
    elif mode == "EXPLAINED":
        prompt = TRANSLATE_EXPLAINED_PROMPT.format(explanation=explanation, tiles=tiles_str)
    elif mode == "TILED":
        prompt = TRANSLATE_TILED_PROMPT.format(tiles=tiles_str, description=func_info["description"])
    elif mode == "ANTI_TRANSLATED":
        prompt = TRANSLATE_ANTI_PROMPT.format(explanation=anti_explanation, tiles=tiles_str)
    else:
        raise ValueError(f"Unknown mode: {mode}")

    messages = [
        {"role": "system", "content": TRANSLATE_SYSTEM},
        {"role": "user", "content": prompt},
    ]

    return call_model(model_key, messages, max_tokens=512, temperature=0.1)


# ── Stage 3: Second Hop — Model C translates Model B's output ──────────

def second_hop(model_key: str, mode: str, translated_code: str, translated_explanation: str,
               translated_anti: str, func_name: str) -> str:
    """Model C translates Model B's output. Same as translate but with B's output."""
    return translate(model_key, mode, translated_code, translated_explanation, translated_anti, func_name)


# ── Verification ────────────────────────────────────────────────────────

def extract_function(code: str) -> Optional[callable]:
    """Extract a function from model output code. Returns callable or None."""
    # Clean up common issues
    code = code.strip()
    if code.startswith("```python"):
        code = code[9:]
    elif code.startswith("```"):
        code = code[3:]
    if code.endswith("```"):
        code = code[:-3]
    code = code.strip()

    # Try to find function definition
    try:
        namespace = {}
        exec(code, namespace)
        # Find the function
        for name in ["translated_fn", "discovered_fn", "fn", "function"]:
            if name in namespace and callable(namespace[name]):
                return namespace[name]
        # Fall back to last callable
        for v in namespace.values():
            if callable(v):
                return v
    except Exception:
        pass
    return None


def verify_correctness(code: str, func_name: str) -> Dict[str, Any]:
    """Verify a code snippet against test tiles. Returns {correct: bool, details: str}."""
    fn = extract_function(code)
    if fn is None:
        return {"correct": False, "details": "Could not extract function"}

    func_info = TEST_FUNCTIONS[func_name]
    tiles = func_info["tiles"]
    verify_fn = func_info["verify"]

    try:
        result = verify_fn(fn, tiles)
        if result:
            return {"correct": True, "details": "All tiles pass"}
        else:
            # Check which tiles fail
            failures = []
            for i, t in enumerate(tiles):
                try:
                    got = fn(t["in"])
                    if got != t["out"] and not (isinstance(got, list) and isinstance(t["out"], list) and
                                                all(abs(a - b) < 0.001 for a, b in zip(got, t["out"]))):
                        failures.append(f"  tile {i}: expected {t['out']}, got {got}")
                except Exception as e:
                    failures.append(f"  tile {i}: error: {e}")
            return {"correct": False, "details": f"{len(failures)} tiles fail:\n" + "\n".join(failures)}
    except Exception as e:
        return {"correct": False, "details": f"Verification error: {e}"}


# ── Main Experiment ─────────────────────────────────────────────────────

@dataclass
class TranslationResult:
    """Result of a single translation chain."""
    func_name: str
    difficulty: str
    source_model: str
    mode: str
    hop: int  # 1 = A→B, 2 = A→B→C

    # Chain info
    chain: str = ""  # e.g. "seed-mini → hermes-70b"

    # Outputs
    original_code: str = ""
    translated_code: str = ""
    explanation: str = ""
    anti_explanation: str = ""

    # Results
    original_correct: bool = False
    translated_correct: bool = False
    details: str = ""

    # Timing
    elapsed_s: float = 0.0

    # Error tracking
    error: str = ""


def run_single_chain(
    source_model: str,
    target_model: str,
    second_model: str,  # for 2-hop
    func_name: str,
    mode: str,
    hop: int,
) -> TranslationResult:
    """Run a single translation chain."""
    func_info = TEST_FUNCTIONS[func_name]
    result = TranslationResult(
        func_name=func_name,
        difficulty=func_info["difficulty"],
        source_model=source_model,
        mode=mode,
        hop=hop,
        chain=f"{source_model} → {target_model}" + (f" → {second_model}" if hop == 2 else ""),
    )

    start = time.time()

    try:
        # Step 1: Source discovers the function
        original_code = discover_function(source_model, func_name)
        result.original_code = original_code

        if original_code.startswith("__ERROR__"):
            result.error = f"Discovery failed: {original_code}"
            result.elapsed_s = time.time() - start
            return result

        # Verify original
        orig_verify = verify_correctness(original_code, func_name)
        result.original_correct = orig_verify["correct"]

        if not orig_verify["correct"]:
            result.details = f"Original incorrect: {orig_verify['details']}"
            result.elapsed_s = time.time() - start
            return result

        # Generate explanations (needed for non-DIRECT modes)
        explanation = ""
        anti_explanation = ""
        if mode in ["EXPLAINED", "ANTI_TRANSLATED"]:
            explanation = explain_function(source_model, original_code, func_name)
            if explanation.startswith("__ERROR__"):
                result.error = f"Explanation failed: {explanation}"
                result.elapsed_s = time.time() - start
                return result

        if mode == "ANTI_TRANSLATED":
            anti_explanation = anti_translate(source_model, original_code, func_name)
            if anti_explanation.startswith("__ERROR__"):
                result.error = f"Anti-translation failed: {anti_explanation}"
                result.elapsed_s = time.time() - start
                return result

        result.explanation = explanation
        result.anti_explanation = anti_explanation

        # Step 2: Target translates (hop 1)
        translated_code = translate(target_model, mode, original_code, explanation, anti_explanation, func_name)

        if translated_code.startswith("__ERROR__"):
            result.error = f"Translation failed: {translated_code}"
            result.elapsed_s = time.time() - start
            return result

        # If 2-hop, translate again
        if hop == 2:
            # Generate explanations from target's translation for 2nd hop
            hop2_explanation = ""
            hop2_anti = ""
            if mode in ["EXPLAINED", "ANTI_TRANSLATED"]:
                hop2_explanation = explain_function(target_model, translated_code, func_name)
                if hop2_explanation.startswith("__ERROR__"):
                    hop2_explanation = explanation  # fallback to original
            if mode == "ANTI_TRANSLATED":
                hop2_anti = anti_translate(target_model, translated_code, func_name)
                if hop2_anti.startswith("__ERROR__"):
                    hop2_anti = anti_explanation  # fallback

            translated_code = translate(second_model, mode, translated_code, hop2_explanation, hop2_anti, func_name)

            if translated_code.startswith("__ERROR__"):
                result.error = f"2nd hop failed: {translated_code}"
                result.elapsed_s = time.time() - start
                return result

        result.translated_code = translated_code

        # Verify translation
        trans_verify = verify_correctness(translated_code, func_name)
        result.translated_correct = trans_verify["correct"]
        result.details = trans_verify["details"]

    except Exception as e:
        result.error = f"Exception: {type(e).__name__}: {e}"

    result.elapsed_s = time.time() - start
    return result


def run_experiment(
    models: List[str] = None,
    functions: List[str] = None,
    modes: List[str] = None,
    run_2hop: bool = True,
    run_2hop_exclude_modes: List[str] = None,
    max_workers: int = 3,
) -> Dict[str, Any]:
    """Run the full flux substrate translation experiment."""

    if models is None:
        models = MODEL_NAMES
    if functions is None:
        functions = list(TEST_FUNCTIONS.keys())
    if modes is None:
        modes = MODES

    # Build all chains
    chains = []
    pairs = [(a, b) for a in models for b in models if a != b]

    for func_name in functions:
        for mode in modes:
            for src, tgt in pairs:
                # 1-hop
                chains.append((src, tgt, None, func_name, mode, 1))
                # 2-hop: A→B→C where C is the remaining model
                if run_2hop and mode not in (run_2hop_exclude_modes or []):
                    remaining = [m for m in models if m != src and m != tgt]
                    if remaining:
                        chains.append((src, tgt, remaining[0], func_name, mode, 2))

    print(f"{'='*70}", flush=True)
    print(f"  Flux Substrate Translation Experiment", flush=True)
    print(f"{'='*70}", flush=True)
    print(f"  Chains: {len(chains)}", flush=True)
    print(f"  Models: {models}", flush=True)
    print(f"  Functions: {functions}", flush=True)
    print(f"  Modes: {modes}", flush=True)
    print(f"  2-hop: {run_2hop}", flush=True)
    print(f"  Max workers: {max_workers}", flush=True)
    print(flush=True)

    results = []
    completed = 0
    total = len(chains)

    # Run chains serially for reliability (API calls can be slow/flaky)
    for chain in chains:
        src, tgt, sec, fn, mode, hop = chain
        completed += 1
        try:
            result = run_single_chain(*chain)
            results.append(result)
            status = "✓" if result.translated_correct else "✗"
            err = f" [ERR: {result.error[:60]}]" if result.error else ""
            print(f"  [{completed:3d}/{total}] {status} {result.chain:30s} | {result.func_name:15s} | {result.mode:18s} | {result.elapsed_s:.1f}s{err}", flush=True)
        except Exception as e:
            print(f"  [{completed:3d}/{total}] ✗ EXCEPTION: {e}", flush=True)
            results.append(TranslationResult(
                func_name=fn, difficulty=TEST_FUNCTIONS[fn]["difficulty"],
                source_model=src, mode=mode, hop=hop,
                chain=f"{src} → {tgt}" + (f" → {sec}" if hop == 2 else ""),
                error=f"Exception: {e}",
            ))

    return {"chains": chains, "results": results}


def analyze_results(results: List[TranslationResult]) -> Dict[str, Any]:
    """Analyze experiment results and return structured summary."""
    analysis = {
        "total_chains": len(results),
        "errors": sum(1 for r in results if r.error),
        "valid_chains": 0,
        "by_mode": {},
        "by_difficulty": {},
        "by_hop": {},
        "by_pair": {},
        "by_function": {},
        "survival_1hop": {},
        "survival_2hop": {},
        "substrate_distance": {},
        "best_mode": "",
        "anti_translate_helps": False,
    }

    valid = [r for r in results if not r.error and r.original_correct]
    analysis["valid_chains"] = len(valid)

    if not valid:
        return analysis

    # Overall survival rate
    survival = sum(1 for r in valid if r.translated_correct) / len(valid)
    analysis["overall_survival"] = survival

    # By mode
    for mode in MODES:
        mode_results = [r for r in valid if r.mode == mode]
        if mode_results:
            correct = sum(1 for r in mode_results if r.translated_correct)
            analysis["by_mode"][mode] = {
                "total": len(mode_results),
                "correct": correct,
                "rate": correct / len(mode_results),
            }

    # Best mode
    mode_rates = {m: analysis["by_mode"].get(m, {}).get("rate", 0) for m in MODES if m in analysis["by_mode"]}
    if mode_rates:
        analysis["best_mode"] = max(mode_rates, key=mode_rates.get)

    # By difficulty
    for diff in ["easy", "medium", "hard"]:
        diff_results = [r for r in valid if r.difficulty == diff]
        if diff_results:
            correct = sum(1 for r in diff_results if r.translated_correct)
            analysis["by_difficulty"][diff] = {
                "total": len(diff_results),
                "correct": correct,
                "rate": correct / len(diff_results),
            }

    # By hop
    for hop in [1, 2]:
        hop_results = [r for r in valid if r.hop == hop]
        if hop_results:
            correct = sum(1 for r in hop_results if r.translated_correct)
            analysis["by_hop"][hop] = {
                "total": len(hop_results),
                "correct": correct,
                "rate": correct / len(hop_results),
            }

    # By model pair (1-hop only)
    for src in MODEL_NAMES:
        for tgt in MODEL_NAMES:
            if src == tgt:
                continue
            pair_results = [r for r in valid if r.source_model == src and r.hop == 1
                          and r.chain.startswith(f"{src} → {tgt}")]
            if pair_results:
                correct = sum(1 for r in pair_results if r.translated_correct)
                analysis["by_pair"][f"{src}→{tgt}"] = {
                    "total": len(pair_results),
                    "correct": correct,
                    "rate": correct / len(pair_results),
                }

    # By function
    for func_name in TEST_FUNCTIONS:
        func_results = [r for r in valid if r.func_name == func_name]
        if func_results:
            correct = sum(1 for r in func_results if r.translated_correct)
            analysis["by_function"][func_name] = {
                "total": len(func_results),
                "correct": correct,
                "rate": correct / len(func_results),
            }

    # Survival: 1-hop vs 2-hop
    hop1 = [r for r in valid if r.hop == 1]
    hop2 = [r for r in valid if r.hop == 2]
    if hop1:
        analysis["survival_1hop"] = sum(1 for r in hop1 if r.translated_correct) / len(hop1)
    if hop2:
        analysis["survival_2hop"] = sum(1 for r in hop2 if r.translated_correct) / len(hop2)

    # Signal decay: compare 1-hop to 2-hop
    if hop1 and hop2:
        analysis["signal_decay"] = analysis["survival_1hop"] - analysis["survival_2hop"]

    # Substrate distance: does Seed→Hermes survive better than Hermes→Qwen?
    for src in MODEL_NAMES:
        for tgt in MODEL_NAMES:
            if src == tgt:
                continue
            pair_key = f"{src}→{tgt}"
            pair_1hop = [r for r in valid if r.hop == 1 and r.source_model == src
                        and r.chain.startswith(f"{src} → {tgt}")]
            if pair_1hop:
                correct = sum(1 for r in pair_1hop if r.translated_correct)
                analysis["substrate_distance"][pair_key] = correct / len(pair_1hop)

    # Anti-translation: does it help?
    anti_results = [r for r in valid if r.mode == "ANTI_TRANSLATED"]
    direct_results = [r for r in valid if r.mode == "DIRECT"]
    if anti_results and direct_results:
        anti_rate = sum(1 for r in anti_results if r.translated_correct) / len(anti_results)
        direct_rate = sum(1 for r in direct_results if r.translated_correct) / len(direct_results)
        analysis["anti_translate_helps"] = anti_rate > direct_rate
        analysis["anti_vs_direct"] = {"anti_rate": anti_rate, "direct_rate": direct_rate, "delta": anti_rate - direct_rate}

    return analysis


def format_results_markdown(results: List[TranslationResult], analysis: Dict[str, Any]) -> str:
    """Format results as markdown report."""
    lines = []
    a = analysis

    lines.append("# Flux Substrate Translation Experiment — Results")
    lines.append("")
    lines.append("## Overview")
    lines.append("")
    lines.append(f"- **Total chains tested:** {a['total_chains']}")
    lines.append(f"- **Valid chains:** {a['valid_chains']}")
    lines.append(f"- **Errors:** {a['errors']}")
    if "overall_survival" in a:
        lines.append(f"- **Overall survival rate:** {a['overall_survival']:.1%}")
    lines.append("")

    # Survival by mode
    lines.append("## 1. Translation Mode Comparison")
    lines.append("")
    lines.append("| Mode | Total | Correct | Rate |")
    lines.append("|------|-------|---------|------|")
    for mode in MODES:
        if mode in a["by_mode"]:
            m = a["by_mode"][mode]
            lines.append(f"| {mode} | {m['total']} | {m['correct']} | {m['rate']:.1%} |")
    lines.append("")
    lines.append(f"**Best mode:** {a.get('best_mode', 'N/A')}")
    if "anti_vs_direct" in a:
        avd = a["anti_vs_direct"]
        lines.append(f"")
        lines.append(f"**Anti-translation vs Direct:** Anti={avd['anti_rate']:.1%}, Direct={avd['direct_rate']:.1%}, Δ={avd['delta']:+.1%}")
        lines.append(f"Anti-translation {'HELPS' if a['anti_translate_helps'] else 'does NOT help'} signal survival.")
    lines.append("")

    # Survival by difficulty
    lines.append("## 2. Survival by Difficulty")
    lines.append("")
    lines.append("| Difficulty | Total | Correct | Rate |")
    lines.append("|------------|-------|---------|------|")
    for diff in ["easy", "medium", "hard"]:
        if diff in a["by_difficulty"]:
            d = a["by_difficulty"][diff]
            lines.append(f"| {diff} | {d['total']} | {d['correct']} | {d['rate']:.1%} |")
    lines.append("")

    # Signal decay
    lines.append("## 3. Signal Decay (1-hop vs 2-hop)")
    lines.append("")
    if "survival_1hop" in a:
        lines.append(f"- **1-hop survival:** {a['survival_1hop']:.1%}")
    if "survival_2hop" in a:
        lines.append(f"- **2-hop survival:** {a['survival_2hop']:.1%}")
    if "signal_decay" in a:
        lines.append(f"- **Signal decay:** {a['signal_decay']:.1%} (lost in second translation)")
    lines.append("")

    # Substrate distance
    lines.append("## 4. Substrate Distance (1-hop model pairs)")
    lines.append("")
    lines.append("| Source → Target | Total | Correct | Rate |")
    lines.append("|-----------------|-------|---------|------|")
    for pair_key, pdata in sorted(a.get("substrate_distance", {}).items(), key=lambda x: -x[1]):
        pair_data = a["by_pair"].get(pair_key, {})
        lines.append(f"| {pair_key:20s} | {pair_data.get('total', '?')} | {pair_data.get('correct', '?')} | {pdata:.1%} |")
    lines.append("")
    lines.append("**Key question:** Does Seed→Hermes survive better than Hermes→Qwen?")
    lines.append("")

    # By function
    lines.append("## 5. Per-Function Survival")
    lines.append("")
    lines.append("| Function | Difficulty | Total | Correct | Rate |")
    lines.append("|----------|------------|-------|---------|------|")
    for func_name, fdata in a.get("by_function", {}).items():
        diff = TEST_FUNCTIONS[func_name]["difficulty"]
        lines.append(f"| {func_name} | {diff} | {fdata['total']} | {fdata['correct']} | {fdata['rate']:.1%} |")
    lines.append("")

    # Detailed results table (sample)
    lines.append("## 6. Detailed Results (1-hop, all modes)")
    lines.append("")
    lines.append("| Chain | Function | Mode | Correct | Details |")
    lines.append("|-------|----------|------|---------|---------|")
    for r in results:
        if r.hop == 1 and not r.error:
            status = "✓" if r.translated_correct else "✗"
            detail = r.details[:50] if r.details else ""
            lines.append(f"| {r.chain} | {r.func_name} | {r.mode} | {status} | {detail} |")
    lines.append("")

    # Key findings
    lines.append("## 7. Key Findings")
    lines.append("")

    findings = []

    if "overall_survival" in a:
        findings.append(f"1. **Overall survival rate:** {a['overall_survival']:.1%} — {'Strong' if a['overall_survival'] > 0.8 else 'Moderate' if a['overall_survival'] > 0.5 else 'Weak'} signal transmission across substrates.")

    if a.get("best_mode"):
        findings.append(f"2. **Best translation mode:** {a['best_mode']}")

    if "anti_vs_direct" in a:
        avd = a["anti_vs_direct"]
        if a["anti_translate_helps"]:
            findings.append(f"3. **Anti-translation HELPS** — using opposite vocabulary improves survival by {avd['delta']:+.1%}. The fleet translator thesis is validated.")
        else:
            findings.append(f"3. **Anti-translation does NOT help** — direct code transfer works better by {abs(avd['delta']):.1%}. The opposite-vocabulary approach loses signal.")

    if "signal_decay" in a:
        findings.append(f"4. **Signal decay:** {a['signal_decay']:.1%} lost per hop. After 2 translations, {'signal is well-preserved' if a['signal_decay'] < 0.2 else 'significant signal is lost'}.")

    # Difficulty gradient
    easy_rate = a.get("by_difficulty", {}).get("easy", {}).get("rate", 0)
    hard_rate = a.get("by_difficulty", {}).get("hard", {}).get("rate", 0)
    if easy_rate > 0 and hard_rate > 0:
        findings.append(f"5. **Difficulty gradient:** Easy={easy_rate:.1%}, Hard={hard_rate:.1%}. {'Hard functions lose significantly more signal' if easy_rate - hard_rate > 0.2 else 'Signal loss is consistent across difficulties'}.")

    # Substrate distance
    sd = a.get("substrate_distance", {})
    if len(sd) >= 2:
        best_pair = max(sd, key=sd.get)
        worst_pair = min(sd, key=sd.get)
        findings.append(f"6. **Substrate distance:** Best pair={best_pair} ({sd[best_pair]:.1%}), Worst pair={worst_pair} ({sd[worst_pair]:.1%})")

    for f in findings:
        lines.append(f"   {f}")
    lines.append("")

    # Conclusion
    lines.append("## 8. Conclusion")
    lines.append("")
    if a.get("anti_translate_helps"):
        lines.append("The Flux thesis is **partially validated**. Anti-translation (opposite vocabulary) does improve")
        lines.append("cross-substrate survival in some cases, suggesting that different models DO have different")
        lines.append("perceptual substrates, and that translating into a model's 'native language' helps signal transmission.")
    else:
        lines.append("The Flux thesis is **not strongly supported** by this experiment. Direct code transfer")
        lines.append("outperforms opposite-vocabulary explanations, suggesting that code is already a universal")
        lines.append("substrate across models, and that natural-language rephrasing (in any vocabulary) adds noise.")
    lines.append("")
    if "signal_decay" in a:
        if a["signal_decay"] < 0.15:
            lines.append("Signal decay is low — tiles survive multi-hop translation well. The PLATO tile protocol")
            lines.append("should work across heterogeneous model fleets.")
        else:
            lines.append("Signal decay is significant — knowledge loses fidelity with each translation hop.")
            lines.append("The PLATO protocol should minimize translation hops and prefer direct tile passing.")
    lines.append("")

    return "\n".join(lines)


# ── Entry Point ─────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Flux Substrate Translation Experiment")
    parser.add_argument("--quick", action="store_true", help="Run a quick subset (2 functions, 2 modes, 1-hop only)")
    parser.add_argument("--no-2hop", action="store_true", help="Skip 2-hop chains")
    parser.add_argument("--no-2hop-anti", action="store_true", help="Skip 2-hop for ANTI_TRANSLATED mode")
    parser.add_argument("--models", nargs="+", default=None, help="Model keys to test")
    parser.add_argument("--functions", nargs="+", default=None, help="Functions to test")
    parser.add_argument("--modes", nargs="+", default=None, help="Translation modes to test")
    parser.add_argument("--workers", type=int, default=3, help="Max concurrent API calls")
    parser.add_argument("--output", default=None, help="Output file for results markdown")
    args = parser.parse_args()

    models = args.models or MODEL_NAMES
    functions = args.functions or list(TEST_FUNCTIONS.keys())
    modes = args.modes or MODES

    if args.quick:
        functions = ["sort", "moving_average"]
        modes = ["DIRECT", "ANTI_TRANSLATED"]

    print(f"\n  Flux Substrate Translation Experiment")
    print(f"  Models: {models}")
    print(f"  Functions: {functions}")
    print(f"  Modes: {modes}")
    print(f"  2-hop: {not args.no_2hop}")
    print(f"  Workers: {args.workers}")
    print()

    # Run experiment
    data = run_experiment(
        models=models,
        functions=functions,
        modes=modes,
        run_2hop=not args.no_2hop,
        run_2hop_exclude_modes=["ANTI_TRANSLATED"] if args.no_2hop_anti else [],
        max_workers=args.workers,
    )

    results = data["results"]

    # Analyze
    analysis = analyze_results(results)

    # Format report
    report = format_results_markdown(results, analysis)

    # Save
    output_path = args.output or str(Path(__file__).parent / "FLUX-SUBSTRATE-RESULTS.md")
    Path(output_path).write_text(report)
    print(f"\n  Results saved to: {output_path}")

    # Print summary
    print(f"\n{'='*70}")
    print(f"  Summary")
    print(f"{'='*70}")
    if "overall_survival" in analysis:
        print(f"  Overall survival: {analysis['overall_survival']:.1%}")
    print(f"  Best mode: {analysis.get('best_mode', 'N/A')}")
    if "anti_vs_direct" in analysis:
        avd = analysis["anti_vs_direct"]
        print(f"  Anti-translate vs Direct: {avd['anti_rate']:.1%} vs {avd['direct_rate']:.1%} (Δ={avd['delta']:+.1%})")
        print(f"  Anti-translate {'HELPS' if analysis['anti_translate_helps'] else 'does NOT help'}")
    if "signal_decay" in analysis:
        print(f"  Signal decay per hop: {analysis['signal_decay']:.1%}")
    print()


if __name__ == "__main__":
    main()
