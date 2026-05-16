#!/usr/bin/env python3
"""
experiments/tile_emergence.py — Tile Emergence Experiment
=========================================================

EXPERIMENT: Agents discover functions from scratch by accumulating tiles.

Give agents problems WITHOUT naming any functions. They must build tiles
that accumulate into a discovered function.

5 target functions (hidden from agents):
  - sort()    — ordering a list
  - max()     — finding the largest element
  - dedup()   — removing duplicates
  - reverse() — reversing a sequence
  - count_gt(x) — counting elements greater than x

For each function, a PLATO room starts empty. We feed input→output pairs
as tiles at increasing counts (10, 50, 100). After each batch, the agent
is asked to identify the pattern and write a function.

3 models tested: Seed-2.0-mini, Hermes-70B, Qwen3.6-35B

Phase 1: 5 functions × 3 models × 3 tile-counts = 45 trials
Phase 2 (optional): extend to 500, 1000 tile-counts

Results → experiments/TILE-EMERGENCE-RESULTS.md
"""

from __future__ import annotations

import json
import os
import random
import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add workspace to path for plato_room_ide imports
WORKSPACE = Path.home() / ".openclaw" / "workspace"
sys.path.insert(0, str(WORKSPACE))

from plato_room_ide import AgentRoom, ShellConfig, DEEPINFRA_ENDPOINT

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEEPINFRA_KEY_PATH = WORKSPACE / ".credentials" / "deepinfra-api-key.txt"
RESULTS_PATH = WORKSPACE / "experiments" / "TILE-EMERGENCE-RESULTS.md"
API_TIMEOUT = 25  # seconds, as specified

MODELS = {
    "Seed-2.0-mini": "ByteDance/Seed-2.0-mini",
    "Hermes-70B": "NousResearch/Hermes-3-Llama-3.1-70B",
    "Qwen3.6-35B": "Qwen/Qwen3.6-35B-A3B",
}

TILE_COUNTS = [10, 50, 100]
RANDOM_SEED = 42

# ---------------------------------------------------------------------------
# Target Functions (hidden from agents)
# ---------------------------------------------------------------------------

def generate_sort_pairs(n: int) -> List[Tuple[list, list]]:
    """Input: unsorted list → Output: sorted list."""
    random.seed(RANDOM_SEED + 1)
    pairs = []
    for _ in range(n):
        length = random.randint(3, 8)
        inp = random.choices(range(1, 50), k=length)
        out = sorted(inp)
        pairs.append((inp, out))
    return pairs

def generate_max_pairs(n: int) -> List[Tuple[list, Any]]:
    """Input: list → Output: max element."""
    random.seed(RANDOM_SEED + 2)
    pairs = []
    for _ in range(n):
        length = random.randint(3, 8)
        inp = random.choices(range(1, 50), k=length)
        out = max(inp)
        pairs.append((inp, out))
    return pairs

def generate_dedup_pairs(n: int) -> List[Tuple[list, list]]:
    """Input: list with dupes → Output: list without dupes (preserve order)."""
    random.seed(RANDOM_SEED + 3)
    pairs = []
    for _ in range(n):
        length = random.randint(4, 10)
        inp = random.choices(range(1, 15), k=length)
        seen = set()
        out = []
        for x in inp:
            if x not in seen:
                seen.add(x)
                out.append(x)
        pairs.append((inp, out))
    return pairs

def generate_reverse_pairs(n: int) -> List[Tuple[list, list]]:
    """Input: list → Output: reversed list."""
    random.seed(RANDOM_SEED + 4)
    pairs = []
    for _ in range(n):
        length = random.randint(3, 8)
        inp = random.choices(range(1, 50), k=length)
        out = list(reversed(inp))
        pairs.append((inp, out))
    return pairs

def generate_count_gt_pairs(n: int) -> List[Tuple[list, int]]:
    """Input: (list, threshold) → Output: count of elements > threshold."""
    random.seed(RANDOM_SEED + 5)
    pairs = []
    for _ in range(n):
        length = random.randint(3, 8)
        lst = random.choices(range(1, 50), k=length)
        threshold = random.randint(5, 30)
        out = sum(1 for x in lst if x > threshold)
        pairs.append(((lst, threshold), out))
    return pairs


TARGET_FUNCTIONS = {
    "fn-alpha": generate_sort_pairs,
    "fn-beta": generate_max_pairs,
    "fn-gamma": generate_dedup_pairs,
    "fn-delta": generate_reverse_pairs,
    "fn-epsilon": generate_count_gt_pairs,
}

# Ground-truth names for scoring
GROUND_TRUTH = {
    "fn-alpha": "sort",
    "fn-beta": "max",
    "fn-gamma": "dedup",
    "fn-delta": "reverse",
    "fn-epsilon": "count_gt",
}

# ---------------------------------------------------------------------------
# API Call Helper
# ---------------------------------------------------------------------------

def load_api_key() -> str:
    return DEEPINFRA_KEY_PATH.read_text().strip()

def call_model(
    model_id: str,
    messages: List[Dict[str, str]],
    api_key: str,
    max_tokens: int = 2048,
    temperature: float = 0.3,
) -> Tuple[str, int, int]:
    """Call DeepInfra API. Returns (response_text, prompt_tokens, completion_tokens)."""
    payload = json.dumps({
        "model": model_id,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode()

    req = urllib.request.Request(
        DEEPINFRA_ENDPOINT,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=API_TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            return content, prompt_tokens, completion_tokens
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        return f"[HTTP {e.code}: {body[:200]}]", 0, 0
    except Exception as e:
        return f"[Error: {type(e).__name__}: {e}]", 0, 0

# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_response(response: str, fn_id: str) -> Dict[str, Any]:
    """Score a model's response for correctness.

    Returns dict with:
      - correct: bool — did the agent identify the right function?
      - partial: bool — did it get close but not exact?
      - has_code: bool — did it write actual code?
      - confidence: float 0-1 — how confident in the discovery
      - raw_score: float — composite score
    """
    resp_lower = response.lower()
    truth = GROUND_TRUTH[fn_id]

    # Check for correct identification
    correct = False
    partial = False
    has_code = "def " in response or "function" in resp_lower or "=>" in response or "->" in response

    # Sort detection
    if truth == "sort":
        if any(w in resp_lower for w in ["sort", "sorted", "ordering", "order by", "ascending", "non-decreasing"]):
            correct = True
        elif any(w in resp_lower for w in ["arrange", "organize", "sequence"]):
            partial = True

    # Max detection
    elif truth == "max":
        if any(w in resp_lower for w in ["maximum", "max", "largest", "biggest", "greatest"]):
            correct = True
        elif any(w in resp_lower for w in ["highest", "top"]):
            partial = True

    # Dedup detection
    elif truth == "dedup":
        if any(w in resp_lower for w in ["duplicate", "dedup", "unique", "distinct", "remove duplicate", "no repeats"]):
            correct = True
        elif any(w in resp_lower for w in ["filter", "set", "one of each"]):
            partial = True

    # Reverse detection
    elif truth == "reverse":
        if any(w in resp_lower for w in ["reverse", "backwards", "backward", "opposite order", "flip"]):
            correct = True
        elif any(w in resp_lower for w in ["mirror", "end to beginning"]):
            partial = True

    # Count_gt detection
    elif truth == "count_gt":
        if any(w in resp_lower for w in ["count", "greater than", "more than", "above", "exceed", "larger than", "elements >"]):
            correct = True
        elif any(w in resp_lower for w in ["threshold", "filter and count", "how many"]):
            partial = True

    # Composite confidence
    raw_score = 0.0
    if correct:
        raw_score += 0.6
    if partial:
        raw_score += 0.3
    if has_code:
        raw_score += 0.2
    if correct and has_code:
        raw_score += 0.2  # bonus for both identifying AND coding

    confidence = min(1.0, raw_score)

    return {
        "correct": correct,
        "partial": partial,
        "has_code": has_code,
        "confidence": confidence,
        "raw_score": raw_score,
    }

# ---------------------------------------------------------------------------
# Trial Runner
# ---------------------------------------------------------------------------

@dataclass
class TrialResult:
    """Result of a single trial (function × model × tile_count)."""
    fn_id: str
    model_name: str
    tile_count: int
    response: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    score: Dict[str, Any] = field(default_factory=dict)
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def format_pairs_as_tiles(pairs: list, fn_id: str) -> str:
    """Format input→output pairs as tile data for the agent."""
    lines = ["Here are input→output observations:\n"]
    for i, (inp, out) in enumerate(pairs):
        lines.append(f"  Input:  {inp}")
        lines.append(f"  Output: {out}")
        lines.append("")
    return "\n".join(lines)


def format_count_gt_pairs(pairs: list) -> str:
    """Special formatting for count_gt which has (list, threshold) input."""
    lines = ["Here are input→output observations:\n"]
    for i, ((lst, threshold), out) in enumerate(pairs):
        lines.append(f"  Input:  (list={lst}, threshold={threshold})")
        lines.append(f"  Output: {out}")
        lines.append("")
    return "\n".join(lines)


SYSTEM_PROMPT = (
    "You are a pattern discovery agent in a PLATO room. "
    "You observe input→output pairs and try to discover the underlying function. "
    "You must write a Python function that maps inputs to outputs. "
    "Be precise and concise. First describe the pattern you see, then write the code."
)

DISCOVERY_PROMPT = (
    "Based on the input→output pairs above, what pattern do you see? "
    "Write a single Python function `f(input) -> output` that maps inputs to outputs. "
    "Explain your reasoning, then provide the function definition."
)


def run_trial(
    fn_id: str,
    model_name: str,
    model_id: str,
    tile_count: int,
    api_key: str,
) -> TrialResult:
    """Run a single trial: feed tiles to agent, ask for discovery, score result."""
    result = TrialResult(fn_id=fn_id, model_name=model_name, tile_count=tile_count)

    # Generate pairs
    gen_fn = TARGET_FUNCTIONS[fn_id]
    pairs = gen_fn(tile_count)

    # Format tiles
    if fn_id == "fn-epsilon":
        tiles_text = format_count_gt_pairs(pairs)
    else:
        tiles_text = format_pairs_as_tiles(pairs, fn_id)

    # Build messages
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": tiles_text + "\n" + DISCOVERY_PROMPT},
    ]

    # Call model
    start = time.time()
    response, prompt_tok, comp_tok = call_model(model_id, messages, api_key)
    elapsed = (time.time() - start) * 1000

    result.response = response
    result.prompt_tokens = prompt_tok
    result.completion_tokens = comp_tok
    result.total_tokens = prompt_tok + comp_tok
    result.latency_ms = elapsed

    # Check for errors
    if response.startswith("[HTTP") or response.startswith("[Error"):
        result.error = response
        return result

    # Score
    result.score = score_response(response, fn_id)

    return result


# ---------------------------------------------------------------------------
# Main Experiment Runner
# ---------------------------------------------------------------------------

def run_experiment(phase1_only: bool = True):
    """Run the full tile emergence experiment."""
    api_key = load_api_key()
    all_results: List[TrialResult] = []

    tile_counts = [10, 50, 100]
    if not phase1_only:
        tile_counts.extend([500, 1000])

    total_trials = len(TARGET_FUNCTIONS) * len(MODELS) * len(tile_counts)
    trial_num = 0

    print(f"{'='*70}")
    print(f"  TILE EMERGENCE EXPERIMENT")
    print(f"  {len(TARGET_FUNCTIONS)} functions × {len(MODELS)} models × {len(tile_counts)} tile-counts")
    print(f"  Total trials: {total_trials}")
    print(f"{'='*70}")
    print()

    for fn_id in TARGET_FUNCTIONS:
        for model_name, model_id in MODELS.items():
            for tile_count in tile_counts:
                trial_num += 1
                print(f"[{trial_num}/{total_trials}] {fn_id} × {model_name} × {tile_count} tiles ... ", end="", flush=True)

                result = run_trial(fn_id, model_name, model_id, tile_count, api_key)
                all_results.append(result)

                # Print summary
                if result.error:
                    print(f"ERROR ({result.latency_ms:.0f}ms)")
                elif result.score.get("correct"):
                    print(f"✓ CORRECT (conf={result.score['confidence']:.2f}, {result.total_tokens}tok, {result.latency_ms:.0f}ms)")
                elif result.score.get("partial"):
                    print(f"~ PARTIAL (conf={result.score['confidence']:.2f}, {result.total_tokens}tok, {result.latency_ms:.0f}ms)")
                else:
                    print(f"✗ MISS ({result.total_tokens}tok, {result.latency_ms:.0f}ms)")

                # Rate limit pause
                time.sleep(0.5)

    return all_results


# ---------------------------------------------------------------------------
# Results Report Generator
# ---------------------------------------------------------------------------

def generate_report(results: List[TrialResult]) -> str:
    """Generate the TILE-EMERGENCE-RESULTS.md report."""
    lines = []
    lines.append("# Tile Emergence Experiment — Results")
    lines.append("")
    lines.append("_Agents discover functions from scratch by accumulating tiles._")
    lines.append("")
    lines.append(f"**Date:** {time.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Trials:** {len(results)}")
    lines.append(f"**Models:** {', '.join(MODELS.keys())}")
    lines.append(f"**Functions:** {', '.join(TARGET_FUNCTIONS.keys())}")
    lines.append(f"**Tile counts:** {TILE_COUNTS}")
    lines.append("")

    # ── Summary Table ──
    lines.append("## Summary")
    lines.append("")
    lines.append("| Function | Model | Tiles | Correct | Confidence | Tokens | Latency |")
    lines.append("|----------|-------|------:|:-------:|:----------:|-------:|--------:|")

    for r in results:
        if r.error:
            status = "⚠️ ERR"
            conf = "—"
        elif r.score.get("correct"):
            status = "✓ YES"
            conf = f"{r.score['confidence']:.2f}"
        elif r.score.get("partial"):
            status = "~ PART"
            conf = f"{r.score['confidence']:.2f}"
        else:
            status = "✗ NO"
            conf = f"{r.score['confidence']:.2f}"
        lines.append(f"| {r.fn_id} | {r.model_name} | {r.tile_count} | {status} | {conf} | {r.total_tokens} | {r.latency_ms:.0f}ms |")

    lines.append("")

    # ── Tile Threshold Analysis ──
    lines.append("## Tile Threshold Analysis")
    lines.append("")
    lines.append("Minimum tiles before correct function discovered (per function per model):")
    lines.append("")
    lines.append("| Function | Ground Truth | Seed-2.0-mini | Hermes-70B | Qwen3.6-35B |")
    lines.append("|----------|-------------|:------------:|:----------:|:-----------:|")

    for fn_id in TARGET_FUNCTIONS:
        truth = GROUND_TRUTH[fn_id]
        thresholds = {}
        for model_name in MODELS:
            # Find minimum tile_count where correct=True
            fn_model_results = [r for r in results if r.fn_id == fn_id and r.model_name == model_name and not r.error]
            threshold = "—"
            for tc in sorted(TILE_COUNTS):
                matching = [r for r in fn_model_results if r.tile_count == tc and r.score.get("correct")]
                if matching:
                    threshold = str(tc)
                    break
            thresholds[model_name] = threshold
        lines.append(f"| {fn_id} | `{truth}()` | {thresholds['Seed-2.0-mini']} | {thresholds['Hermes-70B']} | {thresholds['Qwen3.6-35B']} |")

    lines.append("")

    # ── Convergence Curves ──
    lines.append("## Convergence Curves")
    lines.append("")
    lines.append("Accuracy (confidence) vs number of tiles:")
    lines.append("")

    for fn_id in TARGET_FUNCTIONS:
        truth = GROUND_TRUTH[fn_id]
        lines.append(f"### {fn_id} (`{truth}()`)")
        lines.append("")
        lines.append("```")
        lines.append(f"{'Tiles':>6} | {'Seed-mini':>10} | {'Hermes-70B':>11} | {'Qwen3.6-35B':>12}")
        lines.append(f"{'─'*6}─┼─{'─'*10}─┼─{'─'*11}─┼─{'─'*12}")

        for tc in TILE_COUNTS:
            vals = []
            for model_name in MODELS:
                matching = [r for r in results if r.fn_id == fn_id and r.model_name == model_name and r.tile_count == tc and not r.error]
                if matching:
                    conf = matching[0].score.get("confidence", 0.0)
                    vals.append(f"{conf:>10.2f}")
                else:
                    vals.append(f"{'N/A':>10}")
            lines.append(f"{tc:>6} | {vals[0]} | {vals[1]} | {vals[2]}")

        lines.append("```")
        lines.append("")

    # ── Token Economy ──
    lines.append("## Token Economy")
    lines.append("")
    lines.append("Tokens spent at each resolution level:")
    lines.append("")
    lines.append("| Model | Tile Count | Avg Tokens | Avg Prompt | Avg Completion |")
    lines.append("|-------|:----------:|:----------:|:----------:|:--------------:|")

    for model_name in MODELS:
        for tc in TILE_COUNTS:
            subset = [r for r in results if r.model_name == model_name and r.tile_count == tc and not r.error]
            if subset:
                avg_total = sum(r.total_tokens for r in subset) / len(subset)
                avg_prompt = sum(r.prompt_tokens for r in subset) / len(subset)
                avg_comp = sum(r.completion_tokens for r in subset) / len(subset)
                lines.append(f"| {model_name} | {tc} | {avg_total:.0f} | {avg_prompt:.0f} | {avg_comp:.0f} |")

    lines.append("")

    # ── Model Comparison ──
    lines.append("## Model Comparison")
    lines.append("")

    for model_name in MODELS:
        subset = [r for r in results if r.model_name == model_name and not r.error]
        correct_count = sum(1 for r in subset if r.score.get("correct"))
        partial_count = sum(1 for r in subset if r.score.get("partial") and not r.score.get("correct"))
        miss_count = len(subset) - correct_count - partial_count
        avg_conf = sum(r.score.get("confidence", 0) for r in subset) / max(1, len(subset))
        avg_tokens = sum(r.total_tokens for r in subset) / max(1, len(subset))
        avg_latency = sum(r.latency_ms for r in subset) / max(1, len(subset))

        lines.append(f"### {model_name}")
        lines.append(f"- **Correct:** {correct_count}/{len(subset)} ({100*correct_count/max(1,len(subset)):.0f}%)")
        lines.append(f"- **Partial:** {partial_count}/{len(subset)}")
        lines.append(f"- **Miss:** {miss_count}/{len(subset)}")
        lines.append(f"- **Avg Confidence:** {avg_conf:.2f}")
        lines.append(f"- **Avg Tokens:** {avg_tokens:.0f}")
        lines.append(f"- **Avg Latency:** {avg_latency:.0f}ms")
        lines.append("")

    # ── Snap Quality ──
    lines.append("## Snap Quality Analysis")
    lines.append("")
    lines.append("How precise is the discovered function? (correct + has_code = best snap)")
    lines.append("")
    lines.append("| Function | Model | Tiles | Has Code | Snap Quality |")
    lines.append("|----------|-------|------:|:--------:|:------------:|")

    for r in results:
        if r.error:
            continue
        has_code = "✓" if r.score.get("has_code") else "✗"
        if r.score.get("correct") and r.score.get("has_code"):
            quality = "⭐ EXCELLENT"
        elif r.score.get("correct"):
            quality = "✓ Good"
        elif r.score.get("partial"):
            quality = "~ Partial"
        else:
            quality = "✗ Miss"
        lines.append(f"| {r.fn_id} | {r.model_name} | {r.tile_count} | {has_code} | {quality} |")

    lines.append("")

    # ── Key Findings ──
    lines.append("## Key Findings")
    lines.append("")

    # Compute which model performed best overall
    model_scores = {}
    for model_name in MODELS:
        subset = [r for r in results if r.model_name == model_name and not r.error]
        correct = sum(1 for r in subset if r.score.get("correct"))
        model_scores[model_name] = correct

    best_model = max(model_scores, key=model_scores.get)
    lines.append(f"1. **Best Model:** {best_model} ({model_scores[best_model]} correct discoveries)")

    # Which function was hardest
    fn_scores = {}
    for fn_id in TARGET_FUNCTIONS:
        subset = [r for r in results if r.fn_id == fn_id and not r.error]
        correct = sum(1 for r in subset if r.score.get("correct"))
        fn_scores[fn_id] = correct

    easiest = max(fn_scores, key=fn_scores.get)
    hardest = min(fn_scores, key=fn_scores.get)
    lines.append(f"2. **Easiest Function:** {easiest} (`{GROUND_TRUTH[easiest]}()`) — {fn_scores[easiest]} correct")
    lines.append(f"3. **Hardest Function:** {hardest} (`{GROUND_TRUTH[hardest]}()`) — {fn_scores[hardest]} correct")

    # Tile count effect
    tc_scores = {}
    for tc in TILE_COUNTS:
        subset = [r for r in results if r.tile_count == tc and not r.error]
        correct = sum(1 for r in subset if r.score.get("correct"))
        tc_scores[tc] = correct

    lines.append(f"4. **Tile Count Effect:** " + ", ".join(f"{tc} tiles → {tc_scores.get(tc, 0)} correct" for tc in TILE_COUNTS))

    # Average resolution tile threshold
    resolved = [r for r in results if r.score.get("correct") and not r.error]
    if resolved:
        avg_threshold = sum(r.tile_count for r in resolved) / len(resolved)
        min_threshold = min(r.tile_count for r in resolved)
        lines.append(f"5. **Average Resolution Threshold:** {avg_threshold:.0f} tiles (min: {min_threshold})")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Generated by `experiments/tile_emergence.py`*")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Tile Emergence Experiment")
    parser.add_argument("--full", action="store_true", help="Run full experiment (500, 1000 tiles)")
    parser.add_argument("--dry-run", action="store_true", help="Generate test pairs without calling API")
    parser.add_argument("--function", type=str, help="Run only this function ID (e.g., fn-alpha)")
    parser.add_argument("--model", type=str, help="Run only this model name (e.g., Seed-2.0-mini)")
    args = parser.parse_args()

    if args.dry_run:
        print("DRY RUN — generating test pairs without API calls\n")
        for fn_id, gen_fn in TARGET_FUNCTIONS.items():
            pairs = gen_fn(5)
            print(f"--- {fn_id} (truth: {GROUND_TRUTH[fn_id]}) ---")
            for inp, out in pairs[:3]:
                print(f"  {inp} → {out}")
            print()
        sys.exit(0)

    # Filter if specified
    if args.function:
        TARGET_FUNCTIONS_COPY = {k: v for k, v in TARGET_FUNCTIONS.items() if k == args.function}
        TARGET_FUNCTIONS.clear()
        TARGET_FUNCTIONS.update(TARGET_FUNCTIONS_COPY)

    if args.model:
        MODELS_COPY = {k: v for k, v in MODELS.items() if k == args.model}
        MODELS.clear()
        MODELS.update(MODELS_COPY)

    results = run_experiment(phase1_only=not args.full)

    # Generate report
    report = generate_report(results)
    RESULTS_PATH.write_text(report)
    print(f"\n\nReport written to {RESULTS_PATH}")
    print(f"Total trials: {len(results)}")
    correct = sum(1 for r in results if r.score.get("correct"))
    print(f"Correct discoveries: {correct}/{len(results)}")
