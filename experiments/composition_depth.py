#!/usr/bin/env python3
"""experiments/composition_depth.py — Composition Depth Limit Experiment

Tests 3 Groq models on composition chains of increasing depth to map
the accuracy cliff curve, residue transitions, and operation-type effects.

Models:
  - llama-3.1-8b-instant        (8B dense)
  - llama-4-scout-17b-16e-instruct (17B MoE, 16 experts)
  - openai/gpt-oss-20b          (20B, open-source GPT variant)

Chain types:
  - ADDITION: a+b, a+b+c, ..., a+b+c+d+e+f+g+h+i+j (depth 1-9)
  - MULTIPLICATION: a*b, a*b*c, ..., a*b*c*d*e*f*g*h*i*j (depth 1-9)
  - MIXED: a*b + c*d, a*b + c*d - e*f, ... (depth 2-10)
  - NESTED: ((a+b)*c - d)/e, (((a+b)*c - d)/e + f)*g, ...

Uses the Pinna residue classification from core/pinna.py.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import random
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Tuple
from collections import defaultdict
from pathlib import Path

try:
    import requests
except ImportError:
    print("pip install requests")
    sys.exit(1)

# Import residue classification from pinna
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.pinna import ResidueClass

# ─── Configuration ────────────────────────────────────────────────────────────

MODELS = {
    "llama-8b":    "llama-3.1-8b-instant",
    "llama-scout": "llama-4-scout-17b-16e-instruct",
    "gpt-oss":     "openai/gpt-oss-20b",
}

API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Small integers to keep results verifiable without overflow
# Using values 2-9 to avoid trivial 0/1 cases
INPUT_SETS = [
    {"a": 2, "b": 3, "c": 4, "d": 5, "e": 6, "f": 7, "g": 8, "h": 9, "i": 3, "j": 4},
    {"a": 3, "b": 5, "c": 2, "d": 7, "e": 4, "f": 6, "g": 3, "h": 8, "i": 5, "j": 2},
    {"a": 4, "b": 2, "c": 6, "d": 3, "e": 5, "f": 4, "g": 7, "h": 3, "i": 6, "j": 5},
    {"a": 5, "b": 4, "c": 3, "d": 6, "e": 2, "f": 8, "g": 4, "h": 5, "i": 7, "j": 3},
    {"a": 6, "b": 3, "c": 5, "d": 4, "e": 7, "f": 2, "g": 6, "h": 4, "i": 4, "j": 6},
]

TEMPERATURES = [0.0, 0.3]


# ─── Data Structures ──────────────────────────────────────────────────────────

@dataclass
class ChainSpec:
    """Specification for a composition chain test."""
    chain_type: str      # "addition", "multiplication", "mixed", "nested"
    depth: int           # effective composition depth
    formula_str: str     # e.g. "a+b+c"
    display_str: str     # human-readable formula template


@dataclass
class TrialResult:
    """Single trial result."""
    model_key: str = ""
    model_id: str = ""
    chain_type: str = ""
    depth: int = 0
    input_set_idx: int = 0
    temperature: float = 0.0
    formula: str = ""
    expected: str = ""
    response: str = ""
    extracted: Optional[str] = None
    correct: bool = False
    residue: str = ""
    latency_ms: float = 0.0
    error: str = ""


# ─── Chain Generators ─────────────────────────────────────────────────────────

def addition_chains(max_depth: int = 9) -> List[ChainSpec]:
    """Generate addition chains: a+b (d=1), a+b+c (d=2), ..."""
    chains = []
    vars = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]
    for depth in range(1, max_depth + 1):
        formula = "+".join(vars[:depth + 1])
        chains.append(ChainSpec(
            chain_type="addition",
            depth=depth,
            formula_str=formula,
            display_str=formula,
        ))
    return chains


def multiplication_chains(max_depth: int = 6) -> List[ChainSpec]:
    """Generate multiplication chains: a*b (d=1), a*b*c (d=2), ...
    Limited to 6 because products grow fast."""
    chains = []
    vars = ["a", "b", "c", "d", "e", "f"]
    for depth in range(1, max_depth + 1):
        formula = "*".join(vars[:depth + 1])
        chains.append(ChainSpec(
            chain_type="multiplication",
            depth=depth,
            formula_str=formula,
            display_str=formula,
        ))
    return chains


def mixed_chains() -> List[ChainSpec]:
    """Generate mixed operation chains: a*b + c*d, a*b + c*d - e*f, etc."""
    chains = [
        # depth=2: two terms
        ChainSpec("mixed", 2, "a*b + c*d", "a*b + c*d"),
        # depth=3: three terms
        ChainSpec("mixed", 3, "a*b + c*d - e*f", "a*b + c*d - e*f"),
        # depth=4: four terms
        ChainSpec("mixed", 4, "a*b + c*d - e*f + g*h", "a*b + c*d - e*f + g*h"),
        # depth=5: five terms
        ChainSpec("mixed", 5, "a*b + c*d - e*f + g*h - i*j", "a*b + c*d - e*f + g*h - i*j"),
    ]
    return chains


def nested_chains() -> List[ChainSpec]:
    """Generate nested composition chains."""
    chains = [
        # depth ~4: simple nesting
        ChainSpec("nested", 4, "((a+b)*c - d)/e", "((a+b)*c - d)/e"),
        # depth ~6: deeper nesting
        ChainSpec("nested", 6, "(((a+b)*c - d)/e + f)*g", "(((a+b)*c - d)/e + f)*g"),
        # depth ~8: even deeper
        ChainSpec("nested", 8, "((((a+b)*c - d)/e + f)*g - h)/i", "((((a+b)*c - d)/e + f)*g - h)/i"),
    ]
    return chains


def compute_expected(formula: str, inputs: Dict[str, int]) -> str:
    """Safely compute expected result."""
    try:
        result = eval(formula, {"__builtins__": {}}, inputs)
        # Round to avoid float issues
        if isinstance(result, float) and result == int(result):
            return str(int(result))
        return str(round(result, 2))
    except Exception:
        return "ERROR"


# ─── API Client ───────────────────────────────────────────────────────────────

class GroqClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def query(self, model: str, prompt: str, system: str = "",
              temperature: float = 0.0, max_tokens: int = 30) -> Tuple[Optional[str], float]:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        start = time.time()
        try:
            resp = requests.post(API_URL, headers=self.headers, json=payload, timeout=30)
            latency = (time.time() - start) * 1000

            if resp.status_code != 200:
                return f"HTTP_{resp.status_code}", latency

            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return content.strip(), latency
        except Exception as e:
            latency = (time.time() - start) * 1000
            return f"ERROR: {e}", latency

    def extract_number(self, text: Optional[str]) -> Optional[str]:
        if not text:
            return None
        # Try to find a number (possibly negative, possibly decimal)
        numbers = re.findall(r'-?\d+\.?\d*', text)
        return numbers[-1] if numbers else None


# ─── Residue Classification ──────────────────────────────────────────────────

def classify_residue(response: Optional[str], extracted: Optional[str],
                     expected: str) -> str:
    """Classify the residue type based on response analysis."""
    if response is None or response.startswith("HTTP_") or response.startswith("ERROR"):
        return "NO_RESPONSE"

    if extracted is None:
        return "OTHER"

    try:
        ext_val = float(extracted)
        exp_val = float(expected)
    except (ValueError, TypeError):
        return "OTHER"

    if abs(ext_val - exp_val) < 0.01:
        return "CORRECT"

    # Check if it's one of the input values (echo)
    # We'll do this by checking against common single-variable echoes
    # For now, use proximity-based classification

    ratio = abs(ext_val - exp_val) / max(abs(exp_val), 1)

    if ratio < 0.15:
        return "NEAR"

    # Check for partial computation patterns
    # e.g., for a+b+c+d, getting a+b+c or a+b would be "partial"
    # We'll classify as ECHO if the value matches a single input or simple sub-expression
    return "OTHER"


# ─── Experiment Runner ────────────────────────────────────────────────────────

def run_experiment(client: GroqClient, output_path: str) -> Dict:
    """Run the full composition depth experiment."""

    # Generate all chain specs
    all_chains = (
        addition_chains(max_depth=9) +
        multiplication_chains(max_depth=6) +
        mixed_chains() +
        nested_chains()
    )

    print(f"Total chain specs: {len(all_chains)}")
    print(f"Input sets: {len(INPUT_SETS)}")
    print(f"Temperatures: {len(TEMPERATURES)}")
    print(f"Models: {list(MODELS.keys())}")
    total_trials = len(all_chains) * len(INPUT_SETS) * len(TEMPERATURES) * len(MODELS)
    print(f"Total trials: {total_trials}")
    print()

    results: List[TrialResult] = []
    trial_num = 0

    for model_key, model_id in MODELS.items():
        for chain in all_chains:
            for input_idx, inputs in enumerate(INPUT_SETS):
                for temp in TEMPERATURES:
                    trial_num += 1

                    # Build the prompt
                    formula = chain.formula_str
                    expected = compute_expected(formula, inputs)

                    if expected == "ERROR":
                        continue

                    # Build input description
                    input_parts = [f"{k}={v}" for k, v in inputs.items()
                                   if k in formula]
                    input_str = ", ".join(input_parts)

                    prompt = f"Compute {formula} where {input_str}. Give ONLY the number."
                    system = "Give ONLY the final number. No explanation."

                    response, latency = client.query(
                        model=model_id,
                        prompt=prompt,
                        system=system,
                        temperature=temp,
                        max_tokens=30,
                    )

                    extracted = client.extract_number(response)
                    correct = (extracted == expected) if extracted else False
                    residue = classify_residue(response, extracted, expected)

                    result = TrialResult(
                        model_key=model_key,
                        model_id=model_id,
                        chain_type=chain.chain_type,
                        depth=chain.depth,
                        input_set_idx=input_idx,
                        temperature=temp,
                        formula=formula,
                        expected=expected,
                        response=(response or "")[:200],
                        extracted=extracted,
                        correct=correct,
                        residue=residue,
                        latency_ms=latency,
                    )
                    results.append(result)

                    # Progress
                    if trial_num % 50 == 0:
                        print(f"  [{trial_num}/{total_trials}] "
                              f"{model_key} | {chain.chain_type} d={chain.depth} | "
                              f"T={temp} | set={input_idx} | "
                              f"{'✓' if correct else '✗'} ({extracted} vs {expected})")

                    # Rate limit: small sleep every 20 requests
                    if trial_num % 20 == 0:
                        time.sleep(1)

    # ─── Analysis ────────────────────────────────────────────────────────

    print(f"\n{'='*70}")
    print("ANALYSIS")
    print(f"{'='*70}")

    analysis = {
        "total_trials": len(results),
        "by_model": {},
        "by_chain_type": {},
        "cliff_curves": {},
        "residue_by_depth": {},
        "multiplication_vs_addition": {},
        "nesting_effect": {},
        "temperature_effect": {},
        "raw_results": [asdict(r) for r in results],
    }

    # ── By model ──
    for mk in MODELS:
        model_results = [r for r in results if r.model_key == mk]
        correct = sum(1 for r in model_results if r.correct)
        total = len(model_results)
        analysis["by_model"][mk] = {
            "correct": correct,
            "total": total,
            "accuracy": round(correct / total, 3) if total else 0,
        }
        print(f"\n  {mk}: {correct}/{total} = {correct/total:.1%}" if total else f"\n  {mk}: no results")

    # ── Cliff curves: accuracy vs depth per model per chain type ──
    for mk in MODELS:
        analysis["cliff_curves"][mk] = {}
        for ct in ["addition", "multiplication", "mixed", "nested"]:
            ct_results = [r for r in results if r.model_key == mk and r.chain_type == ct]
            depth_acc = {}
            for depth in sorted(set(r.depth for r in ct_results)):
                depth_results = [r for r in ct_results if r.depth == depth]
                c = sum(1 for r in depth_results if r.correct)
                t = len(depth_results)
                depth_acc[depth] = {"correct": c, "total": t, "accuracy": round(c/t, 3) if t else 0}
            analysis["cliff_curves"][mk][ct] = depth_acc

    # Print cliff curves
    print(f"\n{'='*70}")
    print("CLIFF CURVES (accuracy vs depth)")
    print(f"{'='*70}")
    for mk in MODELS:
        print(f"\n  ── {mk} ──")
        for ct in ["addition", "multiplication", "mixed", "nested"]:
            curve = analysis["cliff_curves"].get(mk, {}).get(ct, {})
            if not curve:
                continue
            print(f"    {ct}:")
            for depth in sorted(curve.keys()):
                d = curve[depth]
                bar = "█" * int(d["accuracy"] * 20)
                print(f"      d={depth:2d}: {d['accuracy']:.0%} ({d['correct']}/{d['total']}) {bar}")

    # ── Residue distribution by depth ──
    for mk in MODELS:
        analysis["residue_by_depth"][mk] = {}
        model_results = [r for r in results if r.model_key == mk]
        for depth in sorted(set(r.depth for r in model_results)):
            depth_results = [r for r in model_results if r.depth == depth]
            residue_dist = defaultdict(int)
            for r in depth_results:
                residue_dist[r.residue] += 1
            total = len(depth_results)
            analysis["residue_by_depth"][mk][depth] = {
                k: {"count": v, "rate": round(v/total, 3)}
                for k, v in sorted(residue_dist.items())
            }

    # ── Multiplication vs Addition comparison ──
    print(f"\n{'='*70}")
    print("MULTIPLICATION vs ADDITION")
    print(f"{'='*70}")
    for mk in MODELS:
        add_results = [r for r in results if r.model_key == mk and r.chain_type == "addition"]
        mul_results = [r for r in results if r.model_key == mk and r.chain_type == "multiplication"]

        # Compare at matching depths
        common_depths = (set(r.depth for r in add_results) &
                        set(r.depth for r in mul_results))
        comparison = {}
        for d in sorted(common_depths):
            add_d = [r for r in add_results if r.depth == d]
            mul_d = [r for r in mul_results if r.depth == d]
            add_acc = sum(1 for r in add_d if r.correct) / len(add_d) if add_d else 0
            mul_acc = sum(1 for r in mul_d if r.correct) / len(mul_d) if mul_d else 0
            comparison[d] = {
                "add_accuracy": round(add_acc, 3),
                "mul_accuracy": round(mul_acc, 3),
                "delta": round(mul_acc - add_acc, 3),
            }
            print(f"  {mk} d={d}: add={add_acc:.0%} mul={mul_acc:.0%} Δ={mul_acc-add_acc:+.0%}")

        analysis["multiplication_vs_addition"][mk] = comparison

    # ── Nesting effect ──
    print(f"\n{'='*70}")
    print("NESTING EFFECT")
    print(f"{'='*70}")
    for mk in MODELS:
        nested_results = [r for r in results if r.model_key == mk and r.chain_type == "nested"]
        if nested_results:
            n_correct = sum(1 for r in nested_results if r.correct)
            n_total = len(nested_results)
            print(f"  {mk}: nested accuracy = {n_correct}/{n_total} = {n_correct/n_total:.0%}")
            for depth in sorted(set(r.depth for r in nested_results)):
                dr = [r for r in nested_results if r.depth == depth]
                dc = sum(1 for r in dr if r.correct)
                print(f"    d={depth}: {dc}/{len(dr)} = {dc/len(dr):.0%}")
        analysis["nesting_effect"][mk] = {
            "overall_accuracy": round(n_correct / n_total, 3) if nested_results else None,
            "by_depth": {
                d: round(sum(1 for r in nested_results if r.depth == d and r.correct) /
                         len([r for r in nested_results if r.depth == d]), 3)
                for d in sorted(set(r.depth for r in nested_results))
            } if nested_results else {}
        }

    # ── Temperature effect ──
    for mk in MODELS:
        for temp in TEMPERATURES:
            temp_results = [r for r in results if r.model_key == mk and r.temperature == temp]
            c = sum(1 for r in temp_results if r.correct)
            t = len(temp_results)
            key = f"{mk}_T{temp}"
            analysis["temperature_effect"][key] = {
                "accuracy": round(c/t, 3) if t else 0,
                "correct": c,
                "total": t,
            }

    print(f"\n{'='*70}")
    print("TEMPERATURE EFFECT")
    print(f"{'='*70}")
    for mk in MODELS:
        for temp in TEMPERATURES:
            key = f"{mk}_T{temp}"
            d = analysis["temperature_effect"][key]
            print(f"  {mk} T={temp}: {d['accuracy']:.0%} ({d['correct']}/{d['total']})")

    # ── MoE vs Dense comparison ──
    print(f"\n{'='*70}")
    print("MoE (scout) vs DENSE (8b) vs GPT-OSS (20b)")
    print(f"{'='*70}")
    for ct in ["addition", "multiplication", "mixed", "nested"]:
        print(f"\n  {ct}:")
        for mk in MODELS:
            ct_res = [r for r in results if r.model_key == mk and r.chain_type == ct]
            c = sum(1 for r in ct_res if r.correct)
            t = len(ct_res)
            print(f"    {mk:15s}: {c}/{t} = {c/t:.0%}" if t else f"    {mk:15s}: no data")

    # Save
    output = {
        "experiment": "composition_depth",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "models": MODELS,
        "analysis": analysis,
    }

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nResults saved to {output_path}")

    return output


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    api_key_file = os.path.expanduser(
        "~/.openclaw/workspace/.credentials/groq-api-key.txt")

    with open(api_key_file) as f:
        api_key = f.read().strip()

    client = GroqClient(api_key)

    output_path = os.path.join(os.path.dirname(__file__), "composition-results.json")
    run_experiment(client, output_path)


if __name__ == "__main__":
    main()
