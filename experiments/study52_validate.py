#!/usr/bin/env python3
"""
Study 52: Fleet Router API Validation with Live Model Calls
============================================================
Phase A: Router accuracy (20 computations across 4 difficulty tiers)
Phase B: Translation quality audit (bare vs translated on Tier 2)
Phase C: Downgrade testing (Tier 1 unavailable → Tier 2)
"""

import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone

# Add workspace to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fleet_router_api import (
    ModelRegistry, ModelTierEnum, CriticalAngleRouter, RoutingStats,
    DEFAULT_MODELS, TIER_ACCURACY, PREFERRED_ORDER, create_app,
)
from fleet_translator_v2 import (
    FleetRouter, ModelStage, translate, translate_for_stage,
    NotationNormalizer, ActivationKeyEngineer, KNOWN_STAGES,
)

# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

DEEPINFRA_KEY = open(os.path.expanduser(
    "~/.openclaw/workspace/.credentials/deepinfra-api-key.txt"
)).read().strip()

OLLAMA_URL = "http://localhost:11434/api/chat"
DEEPINFRA_URL = "https://api.deepinfra.com/v1/openai/chat/completions"

def call_ollama(model: str, prompt: str, timeout: int = 60) -> dict:
    """Call a local Ollama model."""
    import requests
    resp = requests.post(OLLAMA_URL, json={
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.0, "num_predict": 256},
    }, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    content = data.get("message", {}).get("content", "")
    eval_count = data.get("eval_count", 0)
    return {"content": content.strip(), "tokens": eval_count, "model": model}

def call_deepinfra(model: str, prompt: str, timeout: int = 60) -> dict:
    """Call a DeepInfra model."""
    import requests
    resp = requests.post(DEEPINFRA_URL, json={
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": 256,
    }, headers={
        "Authorization": f"Bearer {DEEPINFRA_KEY}",
        "Content-Type": "application/json",
    }, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"].strip()
    usage = data.get("usage", {})
    return {
        "content": content,
        "tokens": usage.get("completion_tokens", 0),
        "model": model,
    }

def call_model(model_id: str, prompt: str, timeout: int = 60) -> dict:
    """Dispatch to correct API based on model ID."""
    if ":" in model_id and "/" not in model_id:
        # Ollama local model (e.g., "gemma3:1b")
        return call_ollama(model_id, prompt, timeout)
    else:
        # DeepInfra model
        return call_deepinfra(model_id, prompt, timeout)

# ---------------------------------------------------------------------------
# Correct answers
# ---------------------------------------------------------------------------

def eisenstein_norm(a, b):
    return a*a - a*b + b*b

def mobius(n):
    """Möbius function."""
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

def legendre(a, p):
    """Legendre symbol."""
    import math
    a_mod = a % p
    if a_mod == 0:
        return 0
    result = pow(a_mod, (p - 1) // 2, p)
    return result if result <= 1 else -1

def modular_inverse(a, m):
    import math
    if math.gcd(a, m) != 1:
        return None
    return pow(a, -1, m)

def extract_number(text: str):
    """Try to extract a numeric answer from model output."""
    import re
    # Look for final number patterns
    text = text.strip()
    # Look for "answer is X" or "= X" patterns
    patterns = [
        r'(?:answer|result|value|output)\s*(?:is|=|:)\s*(-?\d+(?:\.\d+)?)',
        r'=\s*(-?\d+(?:\.\d+)?)\s*(?:\.|$)',
        r'(-?\d+(?:\.\d+)?)\s*(?:\.|$)',
    ]
    for pat in patterns:
        matches = re.findall(pat, text, re.IGNORECASE)
        if matches:
            last = matches[-1]
            try:
                return float(last) if '.' in last else int(last)
            except:
                continue
    # Last resort: find last number in text
    numbers = re.findall(r'-?\d+(?:\.\d+)?', text)
    if numbers:
        last = numbers[-1]
        try:
            return float(last) if '.' in last else int(last)
        except:
            pass
    return None

def score_answer(expected, got_text: str, tolerance: float = 0.01) -> str:
    """Score answer as correct/incorrect/partial."""
    if expected is None:
        return "skip"
    got = extract_number(got_text)
    if got is None:
        return "incorrect"  # no number found
    if isinstance(expected, float):
        if abs(got - expected) <= tolerance:
            return "correct"
    else:
        if got == expected:
            return "correct"
    # Check if the number appears anywhere in text
    if str(expected) in got_text:
        return "partial"
    return "incorrect"

# ---------------------------------------------------------------------------
# Phase A: Router Accuracy Validation
# ---------------------------------------------------------------------------

def phase_a():
    """20 computations: 5 per difficulty tier."""
    print("\n" + "="*70)
    print("PHASE A: Router Accuracy Validation (20 computations)")
    print("="*70)

    # Set up router
    registry = ModelRegistry()
    stats = RoutingStats()
    for model_id, tier in DEFAULT_MODELS.items():
        registry.register(model_id, tier)
    router = CriticalAngleRouter(registry, stats)

    # Define test computations
    tests = [
        # --- Simple arithmetic (should route to Tier 1) ---
        {"name": "simple_eisenstein_1", "task_type": "eisenstein_norm",
         "params": {"a": 2, "b": 3}, "expected": eisenstein_norm(2, 3)},
        {"name": "simple_eisenstein_2", "task_type": "eisenstein_norm",
         "params": {"a": 5, "b": 7}, "expected": eisenstein_norm(5, 7)},
        {"name": "simple_eisenstein_3", "task_type": "eisenstein_norm",
         "params": {"a": 1, "b": 1}, "expected": eisenstein_norm(1, 1)},
        {"name": "simple_eisenstein_4", "task_type": "eisenstein_norm",
         "params": {"a": 0, "b": 4}, "expected": eisenstein_norm(0, 4)},
        {"name": "simple_eisenstein_5", "task_type": "eisenstein_norm",
         "params": {"a": 10, "b": 3}, "expected": eisenstein_norm(10, 3)},

        # --- Domain-labeled arithmetic (should translate + route) ---
        {"name": "labeled_mobius_1", "task_type": "mobius",
         "params": {"n": 30}, "expected": mobius(30)},
        {"name": "labeled_mobius_2", "task_type": "mobius",
         "params": {"n": 7}, "expected": mobius(7)},
        {"name": "labeled_legendre_1", "task_type": "legendre",
         "params": {"a": 2, "p": 7}, "expected": legendre(2, 7)},
        {"name": "labeled_legendre_2", "task_type": "legendre",
         "params": {"a": 3, "p": 11}, "expected": legendre(3, 11)},
        {"name": "labeled_modinv_1", "task_type": "modular_inverse",
         "params": {"a": 3, "m": 7}, "expected": modular_inverse(3, 7)},

        # --- Multi-step reasoning (should route to Tier 2) ---
        {"name": "multi_mobius_1", "task_type": "mobius",
         "params": {"n": 210}, "expected": mobius(210)},
        {"name": "multi_legendre_1", "task_type": "legendre",
         "params": {"a": 5, "p": 13}, "expected": legendre(5, 13)},
        {"name": "multi_modinv_2", "task_type": "modular_inverse",
         "params": {"a": 7, "m": 11}, "expected": modular_inverse(7, 11)},
        {"name": "multi_mobius_2", "task_type": "mobius",
         "params": {"n": 105}, "expected": mobius(105)},
        {"name": "multi_legendre_2", "task_type": "legendre",
         "params": {"a": 6, "p": 17}, "expected": legendre(6, 17)},

        # --- Hard / edge cases (test downgrade logic) ---
        {"name": "hard_mobius_prime_sq", "task_type": "mobius",
         "params": {"n": 4}, "expected": mobius(4)},
        {"name": "hard_mobius_large", "task_type": "mobius",
         "params": {"n": 2310}, "expected": mobius(2310)},
        {"name": "hard_legendre_0", "task_type": "legendre",
         "params": {"a": 7, "p": 7}, "expected": legendre(7, 7)},
        {"name": "hard_modinv_no", "task_type": "modular_inverse",
         "params": {"a": 2, "m": 4}, "expected": None},  # no inverse
        {"name": "hard_eisenstein_neg", "task_type": "eisenstein_norm",
         "params": {"a": -3, "b": 5}, "expected": eisenstein_norm(-3, 5)},
    ]

    results = []
    models_to_test = [
        "ByteDance/Seed-2.0-mini",       # Tier 1, DeepInfra
        "NousResearch/Hermes-3-Llama-3.1-70B",  # Tier 2, DeepInfra
        "gemma3:1b",                       # Tier 1, Ollama local
        "qwen3:0.6b",                      # Tier 3 (incompetent), Ollama local
    ]

    for test in tests:
        print(f"\n--- {test['name']} ---")
        print(f"  Task: {test['task_type']} | Params: {test['params']} | Expected: {test['expected']}")

        # Route through the router
        routing = router.route_request(test["task_type"], test["params"])
        print(f"  Routed: model={routing.get('model_id')} tier={routing.get('tier')} "
              f"reason={routing.get('routing_reason','')[:80]}")

        # Execute on multiple models
        for model_id in models_to_test:
            # Determine tier for this model
            entry = registry.get(model_id)
            tier = entry.tier if entry else ModelTierEnum.TIER_3_INCOMPETENT

            # Translate for this model's tier
            translated = router._translate(test["task_type"], test["params"], tier)

            print(f"  [{model_id}] tier={tier.value} prompt=\"{translated[:80]}...\"")

            try:
                t0 = time.time()
                response = call_model(model_id, translated, timeout=45)
                latency = time.time() - t0
                answer_text = response["content"]
                tokens = response.get("tokens", 0)

                # Score
                score = score_answer(test["expected"], answer_text)

                result = {
                    "test_name": test["name"],
                    "task_type": test["task_type"],
                    "params": test["params"],
                    "expected": test["expected"],
                    "model_id": model_id,
                    "tier": tier.value,
                    "translated_prompt": translated,
                    "response": answer_text[:500],
                    "score": score,
                    "latency_s": round(latency, 2),
                    "tokens": tokens,
                    "routed_model": routing.get("model_id"),
                    "routed_tier": routing.get("tier"),
                }
                results.append(result)
                print(f"    → {score} | {latency:.2f}s | answer: {answer_text[:100]}")

            except Exception as e:
                print(f"    → ERROR: {e}")
                results.append({
                    "test_name": test["name"],
                    "task_type": test["task_type"],
                    "params": test["params"],
                    "expected": test["expected"],
                    "model_id": model_id,
                    "tier": tier.value if entry else 3,
                    "translated_prompt": translated,
                    "response": None,
                    "score": "error",
                    "error": str(e),
                    "latency_s": None,
                    "tokens": None,
                    "routed_model": routing.get("model_id"),
                    "routed_tier": routing.get("tier"),
                })

    return results

# ---------------------------------------------------------------------------
# Phase B: Translation Quality Audit
# ---------------------------------------------------------------------------

def phase_b():
    """Compare bare vs translated prompts on Tier 2 models."""
    print("\n" + "="*70)
    print("PHASE B: Translation Quality Audit (bare vs translated)")
    print("="*70)

    tests = [
        {"task_type": "eisenstein_norm", "params": {"a": 3, "b": 5}, "expected": eisenstein_norm(3, 5)},
        {"task_type": "mobius", "params": {"n": 30}, "expected": mobius(30)},
        {"task_type": "legendre", "params": {"a": 2, "p": 7}, "expected": legendre(2, 7)},
        {"task_type": "eisenstein_norm", "params": {"a": 7, "b": 4}, "expected": eisenstein_norm(7, 4)},
        {"task_type": "mobius", "params": {"n": 105}, "expected": mobius(105)},
        {"task_type": "legendre", "params": {"a": 5, "p": 13}, "expected": legendre(5, 13)},
        {"task_type": "modular_inverse", "params": {"a": 7, "m": 11}, "expected": modular_inverse(7, 11)},
        {"task_type": "eisenstein_norm", "params": {"a": -2, "b": 6}, "expected": eisenstein_norm(-2, 6)},
        {"task_type": "mobius", "params": {"n": 210}, "expected": mobius(210)},
        {"task_type": "legendre", "params": {"a": 3, "p": 11}, "expected": legendre(3, 11)},
    ]

    tier2_models = ["NousResearch/Hermes-3-Llama-3.1-70B"]

    results = []
    for test in tests:
        print(f"\n--- {test['task_type']} {test['params']} (expected={test['expected']}) ---")

        # Build bare prompt (no activation key, no normalization)
        bare_dispatch = {
            "eisenstein_norm": f"Compute the Eisenstein norm of (a={test['params']['a']}, b={test['params']['b']}).",
            "mobius": f"Compute the Möbius function μ({test['params']['n']}).",
            "legendre": f"Compute the Legendre symbol ({test['params']['a']}|{test['params']['p']}).",
            "modular_inverse": f"Find the modular inverse of {test['params']['a']} mod {test['params']['m']}.",
        }
        bare_prompt = bare_dispatch.get(test["task_type"], str(test["params"]))

        # Build translated prompt (Tier 2 scaffolding)
        translated_prompt = translate(test["task_type"], test["params"], ModelStage.CAPABLE)

        print(f"  BARE:       \"{bare_prompt[:80]}\"")
        print(f"  TRANSLATED: \"{translated_prompt[:80]}\"")

        for model_id in tier2_models:
            for label, prompt in [("bare", bare_prompt), ("translated", translated_prompt)]:
                try:
                    t0 = time.time()
                    response = call_model(model_id, prompt, timeout=45)
                    latency = time.time() - t0
                    answer_text = response["content"]
                    score = score_answer(test["expected"], answer_text)

                    result = {
                        "task_type": test["task_type"],
                        "params": test["params"],
                        "expected": test["expected"],
                        "model_id": model_id,
                        "prompt_type": label,
                        "prompt": prompt,
                        "response": answer_text[:500],
                        "score": score,
                        "latency_s": round(latency, 2),
                    }
                    results.append(result)
                    print(f"    [{label}] → {score} | {latency:.2f}s | {answer_text[:80]}")

                except Exception as e:
                    print(f"    [{label}] → ERROR: {e}")
                    results.append({
                        "task_type": test["task_type"],
                        "params": test["params"],
                        "expected": test["expected"],
                        "model_id": model_id,
                        "prompt_type": label,
                        "prompt": prompt,
                        "response": None,
                        "score": "error",
                        "error": str(e),
                        "latency_s": None,
                    })

    return results

# ---------------------------------------------------------------------------
# Phase C: Downgrade Testing
# ---------------------------------------------------------------------------

def phase_c():
    """Test downgrade: Tier 1 unavailable → should fall to Tier 2 with translation."""
    print("\n" + "="*70)
    print("PHASE C: Downgrade Testing (Tier 1 unavailable)")
    print("="*70)

    # Set up router with Tier 1 unavailable
    registry = ModelRegistry()
    stats = RoutingStats()
    for model_id, tier in DEFAULT_MODELS.items():
        available = tier != ModelTierEnum.TIER_1_DIRECT  # Tier 1 = unavailable
        registry.register(model_id, tier, available=available)
    router = CriticalAngleRouter(registry, stats)

    tests = [
        {"task_type": "eisenstein_norm", "params": {"a": 3, "b": 5}, "expected": eisenstein_norm(3, 5)},
        {"task_type": "mobius", "params": {"n": 30}, "expected": mobius(30)},
        {"task_type": "legendre", "params": {"a": 2, "p": 7}, "expected": legendre(2, 7)},
        {"task_type": "eisenstein_norm", "params": {"a": 7, "b": 2}, "expected": eisenstein_norm(7, 2)},
        {"task_type": "mobius", "params": {"n": 105}, "expected": mobius(105)},
        {"task_type": "modular_inverse", "params": {"a": 5, "m": 7}, "expected": modular_inverse(5, 7)},
        {"task_type": "legendre", "params": {"a": 3, "p": 11}, "expected": legendre(3, 11)},
        {"task_type": "eisenstein_norm", "params": {"a": -1, "b": 4}, "expected": eisenstein_norm(-1, 4)},
        {"task_type": "mobius", "params": {"n": 210}, "expected": mobius(210)},
        {"task_type": "legendre", "params": {"a": 5, "p": 13}, "expected": legendre(5, 13)},
    ]

    results = []
    for test in tests:
        print(f"\n--- {test['task_type']} {test['params']} (expected={test['expected']}) ---")

        # Route with Tier 1 unavailable
        routing = router.route_request(test["task_type"], test["params"])
        model_id = routing.get("model_id")
        tier = routing.get("tier")
        downgraded = routing.get("downgraded", False)
        prompt = routing.get("translated_prompt", "")

        print(f"  Routed: model={model_id} tier={tier} downgraded={downgraded}")
        print(f"  Reason: {routing.get('routing_reason','')[:80]}")

        if not model_id or routing.get("rejected"):
            results.append({
                "task_type": test["task_type"],
                "params": test["params"],
                "expected": test["expected"],
                "model_id": None,
                "tier": tier,
                "downgraded": downgraded,
                "score": "rejected",
                "routing_reason": routing.get("routing_reason"),
            })
            continue

        # Execute the call
        try:
            t0 = time.time()
            response = call_model(model_id, prompt, timeout=45)
            latency = time.time() - t0
            answer_text = response["content"]
            score = score_answer(test["expected"], answer_text)

            result = {
                "task_type": test["task_type"],
                "params": test["params"],
                "expected": test["expected"],
                "model_id": model_id,
                "tier": tier,
                "translated_prompt": prompt,
                "response": answer_text[:500],
                "score": score,
                "latency_s": round(latency, 2),
                "downgraded": downgraded,
                "routing_reason": routing.get("routing_reason"),
            }
            results.append(result)
            print(f"  → {score} | {latency:.2f}s | {answer_text[:80]}")

        except Exception as e:
            print(f"  → ERROR: {e}")
            results.append({
                "task_type": test["task_type"],
                "params": test["params"],
                "expected": test["expected"],
                "model_id": model_id,
                "tier": tier,
                "translated_prompt": prompt,
                "response": None,
                "score": "error",
                "error": str(e),
                "latency_s": None,
                "downgraded": downgraded,
                "routing_reason": routing.get("routing_reason"),
            })

    return results

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("="*70)
    print("STUDY 52: Fleet Router API Validation")
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    print("="*70)

    all_results = {"phase_a": [], "phase_b": [], "phase_c": []}

    try:
        all_results["phase_a"] = phase_a()
    except Exception as e:
        print(f"\n⚠️ Phase A failed: {e}")
        traceback.print_exc()

    try:
        all_results["phase_b"] = phase_b()
    except Exception as e:
        print(f"\n⚠️ Phase B failed: {e}")
        traceback.print_exc()

    try:
        all_results["phase_c"] = phase_c()
    except Exception as e:
        print(f"\n⚠️ Phase C failed: {e}")
        traceback.print_exc()

    # Save JSON
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "study52_routing_validation.json")
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\n✅ Results saved to {out_path}")

    # Generate summary
    generate_report(all_results)

def generate_report(data):
    """Generate the markdown report."""
    report_lines = [
        "# Study 52: Fleet Router API Validation",
        f"\n**Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "\n## Phase A: Router Accuracy (20 computations × 4 models)",
    ]

    phase_a = data.get("phase_a", [])
    if phase_a:
        # Group by model
        by_model = {}
        for r in phase_a:
            mid = r.get("model_id", "unknown")
            if mid not in by_model:
                by_model[mid] = {"correct": 0, "partial": 0, "incorrect": 0, "error": 0, "skip": 0, "total": 0, "latencies": []}
            by_model[mid]["total"] += 1
            score = r.get("score", "error")
            if score in by_model[mid]:
                by_model[mid][score] += 1
            if r.get("latency_s"):
                by_model[mid]["latencies"].append(r["latency_s"])

        report_lines.append("\n| Model | Tier | Total | Correct | Partial | Incorrect | Error | Avg Latency |")
        report_lines.append("|-------|------|-------|---------|---------|-----------|-------|-------------|")
        for mid, counts in sorted(by_model.items()):
            avg_lat = sum(counts["latencies"]) / len(counts["latencies"]) if counts["latencies"] else 0
            report_lines.append(
                f"| {mid} | {phase_a[0].get('tier', '?')} | {counts['total']} | "
                f"{counts['correct']} | {counts['partial']} | {counts['incorrect']} | "
                f"{counts['error']} | {avg_lat:.2f}s |"
            )

        # Routing accuracy: how often did the router pick the right tier?
        correct_routes = sum(1 for r in phase_a if r.get("routed_model") and not r.get("error"))
        report_lines.append(f"\n**Router routing accuracy:** {correct_routes}/{len(phase_a)} successful routes")

        # Per-tier accuracy
        by_tier = {}
        for r in phase_a:
            tier = r.get("tier", "?")
            if tier not in by_tier:
                by_tier[tier] = {"correct": 0, "total": 0}
            by_tier[tier]["total"] += 1
            if r.get("score") == "correct":
                by_tier[tier]["correct"] += 1

        report_lines.append("\n### Accuracy by Tier")
        report_lines.append("\n| Tier | Correct | Total | Accuracy |")
        report_lines.append("|------|---------|-------|----------|")
        for tier in sorted(by_tier.keys()):
            t = by_tier[tier]
            acc = t["correct"] / t["total"] * 100 if t["total"] else 0
            report_lines.append(f"| {tier} | {t['correct']} | {t['total']} | {acc:.1f}% |")

    # Phase B
    report_lines.append("\n## Phase B: Translation Quality Audit (bare vs translated on Tier 2)")
    phase_b = data.get("phase_b", [])
    if phase_b:
        bare_scores = {"correct": 0, "incorrect": 0, "partial": 0, "error": 0, "total": 0}
        trans_scores = {"correct": 0, "incorrect": 0, "partial": 0, "error": 0, "total": 0}
        for r in phase_b:
            target = bare_scores if r.get("prompt_type") == "bare" else trans_scores
            target["total"] += 1
            score = r.get("score", "error")
            if score in target:
                target[score] += 1

        report_lines.append("\n| Prompt Type | Total | Correct | Partial | Incorrect | Error | Accuracy |")
        report_lines.append("|-------------|-------|---------|---------|-----------|-------|----------|")
        for label, scores in [("Bare", bare_scores), ("Translated", trans_scores)]:
            acc = scores["correct"] / scores["total"] * 100 if scores["total"] else 0
            report_lines.append(
                f"| {label} | {scores['total']} | {scores['correct']} | {scores['partial']} | "
                f"{scores['incorrect']} | {scores['error']} | {acc:.1f}% |"
            )

        delta = (trans_scores["correct"] / max(trans_scores["total"], 1) -
                 bare_scores["correct"] / max(bare_scores["total"], 1)) * 100
        report_lines.append(f"\n**Translation impact:** {delta:+.1f}% accuracy change")

        # Per-task breakdown
        by_task = {}
        for r in phase_b:
            tt = r.get("task_type", "?")
            pt = r.get("prompt_type", "?")
            if tt not in by_task:
                by_task[tt] = {"bare": [], "translated": []}
            by_task[tt][pt].append(r.get("score"))

        report_lines.append("\n### Per-Task Breakdown")
        for tt, scores in by_task.items():
            bare_acc = sum(1 for s in scores.get("bare", []) if s == "correct")
            trans_acc = sum(1 for s in scores.get("translated", []) if s == "correct")
            report_lines.append(f"- **{tt}:** bare={bare_acc}/{len(scores.get('bare',[]))} translated={trans_acc}/{len(scores.get('translated',[]))}")

    # Phase C
    report_lines.append("\n## Phase C: Downgrade Testing (Tier 1 unavailable)")
    phase_c = data.get("phase_c", [])
    if phase_c:
        downgraded_count = sum(1 for r in phase_c if r.get("downgraded"))
        correct_count = sum(1 for r in phase_c if r.get("score") == "correct")
        rejected_count = sum(1 for r in phase_c if r.get("score") == "rejected")
        error_count = sum(1 for r in phase_c if r.get("score") == "error")

        report_lines.append(f"\n- **Total tests:** {len(phase_c)}")
        report_lines.append(f"- **Downgraded:** {downgraded_count}")
        report_lines.append(f"- **Correct after downgrade:** {correct_count}")
        report_lines.append(f"- **Rejected (no model):** {rejected_count}")
        report_lines.append(f"- **Errors:** {error_count}")

        downgrade_acc = correct_count / len(phase_c) * 100 if phase_c else 0
        report_lines.append(f"- **Downgrade accuracy:** {downgrade_acc:.1f}%")

        report_lines.append("\n### Downgrade Routing Details")
        report_lines.append("\n| Task | Routed Model | Tier | Downgraded | Score |")
        report_lines.append("|------|-------------|------|------------|-------|")
        for r in phase_c:
            report_lines.append(
                f"| {r.get('task_type','?')} | {r.get('model_id','none')} | {r.get('tier','?')} | "
                f"{'Yes' if r.get('downgraded') else 'No'} | {r.get('score','?')} |"
            )

    # Recommendations
    report_lines.append("\n## Recommendations")
    report_lines.append("\n*(Generated after data collection — see full JSON for raw results)*")

    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "STUDY-52-ROUTING-VALIDATION.md")
    with open(report_path, "w") as f:
        f.write("\n".join(report_lines))
    print(f"✅ Report saved to {report_path}")

if __name__ == "__main__":
    main()
