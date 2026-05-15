#!/usr/bin/env python3
"""
Piagetian Stage Irreversibility Test
=====================================
Hypothesis: AI cognitive stages are structurally necessary (like Piaget's).
You cannot skip stages. Fine-tuning a Stage 1 model directly on Stage 4 tasks
produces defective Stage 3, NOT Stage 4.

Experimental Design:
  Cell A (Control):    Stage 1 model → baseline tasks → establish floor
  Cell B (Direct Jump): Stage 1 model → Stage 4 few-shot prompts → test skipping
  Cell C (Staged):     Stage 1 model → Stage 2 → Stage 3 → Stage 4 sequential → test progressive

Models tested:
  qwen3:0.6b (Stage 1 baseline)
  qwen3:4b   (Stage 2-3 boundary)

Uses local Ollama at localhost:11434.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
OLLAMA_BASE = os.environ.get("OLLAMA_BASE", "http://localhost:11434")
RESULTS_DIR = Path(__file__).parent
RESULTS_FILE = RESULTS_DIR / "STAGE-IRREVERSIBILITY-RESULTS.md"

MODELS = ["qwen3:0.6b", "qwen3:4b"]
MAX_TOKENS = 1024
TEMPERATURE = 0.1  # Low for determinism
TIMEOUT_SEC = 60

# ---------------------------------------------------------------------------
# Stage definitions — prompts that characterize each cognitive stage
# ---------------------------------------------------------------------------

STAGE_2_PROMPTS = [
    {
        "role": "system",
        "content": (
            "You are learning basic mathematical notation. "
            "You can recognize simple symbols and their direct meanings."
        ),
    },
    {
        "role": "user",
        "content": "What does the symbol '+' mean in mathematics? What does '×' mean?",
    },
    {
        "role": "assistant",
        "content": (
            "The symbol '+' means addition — combining two quantities. "
            "The symbol '×' means multiplication — repeated addition. "
            "For example, 3 × 4 means adding 3 four times: 3 + 3 + 3 + 3 = 12."
        ),
    },
    {
        "role": "user",
        "content": "What does |x| (absolute value) mean?",
    },
    {
        "role": "assistant",
        "content": (
            "|x| means the absolute value of x — the distance from zero. "
            "|5| = 5, |-3| = 3. It always gives a non-negative result."
        ),
    },
]

STAGE_3_PROMPTS = [
    {
        "role": "system",
        "content": (
            "You can compose multiple mathematical operations and understand "
            "notation that combines several concepts. You translate between "
            "symbolic notation and natural language."
        ),
    },
    {
        "role": "user",
        "content": "Compute |3 + 4i| where i is the imaginary unit.",
    },
    {
        "role": "assistant",
        "content": (
            "The absolute value (modulus) of a complex number a + bi is "
            "√(a² + b²).\n"
            "So |3 + 4i| = √(3² + 4²) = √(9 + 16) = √25 = 5."
        ),
    },
    {
        "role": "user",
        "content": "Translate to natural language: ‖v‖ = √(v₁² + v₂² + v₃²)",
    },
    {
        "role": "assistant",
        "content": (
            "This says: the norm (length) of a 3-dimensional vector v "
            "equals the square root of the sum of the squares of its three components."
        ),
    },
]

STAGE_4_PROMPTS = [
    {
        "role": "system",
        "content": (
            "You are an expert mathematician. You understand advanced algebraic "
            "structures including lattices, norms, and abstract algebra. You can "
            "compute Eisenstein norms, work with lattice basis reduction, and "
            "perform multi-step symbolic reasoning."
        ),
    },
    {
        "role": "user",
        "content": (
            "The Eisenstein integers are numbers of the form a + bω where "
            "ω = e^(2πi/3) = (-1 + i√3)/2, and a, b are integers.\n\n"
            "The Eisenstein norm is N(a + bω) = a² - ab + b².\n\n"
            "Compute N(2 + 3ω)."
        ),
    },
    {
        "role": "assistant",
        "content": (
            "N(2 + 3ω) = a² - ab + b² where a = 2, b = 3.\n"
            "= 2² - 2·3 + 3²\n"
            "= 4 - 6 + 9\n"
            "= 7"
        ),
    },
    {
        "role": "user",
        "content": (
            "Now compute N(1 - 2ω) using the same formula N(a + bω) = a² - ab + b²."
        ),
    },
    {
        "role": "assistant",
        "content": (
            "N(1 - 2ω) = a² - ab + b² where a = 1, b = -2.\n"
            "= 1² - 1·(-2) + (-2)²\n"
            "= 1 + 2 + 4\n"
            "= 7"
        ),
    },
]

# ---------------------------------------------------------------------------
# Test tasks — what we actually evaluate
# ---------------------------------------------------------------------------

TEST_TASKS = [
    {
        "id": "eisenstein_1",
        "category": "eisenstein_norm",
        "stage": 4,
        "prompt": (
            "The Eisenstein norm is N(a + bω) = a² - ab + b² where ω = (-1 + i√3)/2.\n"
            "Compute N(3 + 1ω). Show your work."
        ),
        "correct_answer": "7",
        "scoring": "exact_numeric",
    },
    {
        "id": "eisenstein_2",
        "category": "eisenstein_norm",
        "stage": 4,
        "prompt": (
            "The Eisenstein norm is N(a + bω) = a² - ab + b² where ω = (-1 + i√3)/2.\n"
            "Compute N(4 + 2ω). Show your work."
        ),
        "correct_answer": "12",
        "scoring": "exact_numeric",
    },
    {
        "id": "notation_translation_1",
        "category": "notation_translation",
        "stage": 3,
        "prompt": (
            "Translate this mathematical expression into natural language:\n"
            "Σᵢ₌₁ⁿ xᵢ² / n"
        ),
        "correct_answer": "mean of squares",
        "scoring": "semantic",
        "keywords": ["mean", "average", "squares", "sum", "divided", "n"],
    },
    {
        "id": "notation_translation_2",
        "category": "notation_translation",
        "stage": 3,
        "prompt": (
            "Translate to natural language: ∃x ∈ ℝ : x² = 2"
        ),
        "correct_answer": "there exists a real number whose square is 2",
        "scoring": "semantic",
        "keywords": ["exists", "real", "square", "2"],
    },
    {
        "id": "multistep_arith_1",
        "category": "multistep_arithmetic",
        "stage": 3,
        "prompt": (
            "Compute step by step: (|−7| + 3²) × 2 − √49"
        ),
        "correct_answer": "28",
        "scoring": "exact_numeric",
    },
    {
        "id": "multistep_arith_2",
        "category": "multistep_arithmetic",
        "stage": 2,
        "prompt": (
            "What is 15 + 27 × 2? (Remember order of operations)"
        ),
        "correct_answer": "69",
        "scoring": "exact_numeric",
    },
    {
        "id": "eisenstein_3",
        "category": "eisenstein_norm",
        "stage": 4,
        "prompt": (
            "Eisenstein norm: N(a + bω) = a² - ab + b².\n"
            "Compute N(5 + 3ω). Show your work."
        ),
        "correct_answer": "19",
        "scoring": "exact_numeric",
    },
    {
        "id": "symbolic_composition_1",
        "category": "symbolic_composition",
        "stage": 4,
        "prompt": (
            "Given:\n"
            "  f(x) = |x - 3|\n"
            "  g(x) = x² + 1\n\n"
            "Compute g(f(-2)). Show each step."
        ),
        "correct_answer": "26",
        "scoring": "exact_numeric",
    },
]


# ---------------------------------------------------------------------------
# Ollama client
# ---------------------------------------------------------------------------

def call_ollama(model: str, messages: list[dict], temperature: float = TEMPERATURE) -> dict:
    """Call Ollama chat API and return parsed response."""
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "stream": False,
        "think": False,  # Disable qwen3 thinking tokens
        "options": {
            "num_predict": MAX_TOKENS,
            "temperature": temperature,
        },
    }).encode()

    req = urllib.request.Request(
        f"{OLLAMA_BASE}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        return {"error": f"HTTP {e.code}: {body[:200]}"}
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_response(task: dict, response_text: str) -> dict:
    """Score a single response against the expected answer."""
    text = response_text.strip().lower()
    task_id = task["id"]
    scoring = task["scoring"]

    if "error" in response_text.lower():
        return {"correct": False, "score": 0.0, "reason": "model error", "response": response_text[:300]}

    if scoring == "exact_numeric":
        correct = task["correct_answer"]
        # Check if the correct answer appears in the response
        found = correct in response_text
        # Also check for common computation patterns
        return {
            "correct": found,
            "score": 1.0 if found else 0.0,
            "expected": correct,
            "found_in_response": found,
            "response": response_text[:500],
        }

    elif scoring == "semantic":
        keywords = task.get("keywords", [])
        hits = sum(1 for kw in keywords if kw.lower() in text)
        total = len(keywords)
        ratio = hits / total if total > 0 else 0
        return {
            "correct": ratio >= 0.5,
            "score": ratio,
            "keywords_hit": hits,
            "keywords_total": total,
            "response": response_text[:500],
        }

    return {"correct": False, "score": 0.0, "reason": "unknown scoring method"}


# ---------------------------------------------------------------------------
# Experiment cells
# ---------------------------------------------------------------------------

def run_cell_a(model: str) -> list[dict]:
    """Cell A (Control): No few-shot — just the test questions."""
    results = []
    for task in TEST_TASKS:
        messages = [{"role": "user", "content": task["prompt"]}]
        resp = call_ollama(model, messages)
        response_text = resp.get("message", {}).get("content", "") or resp.get("error", "NO RESPONSE")
        scored = score_response(task, response_text)
        scored["cell"] = "A"
        scored["model"] = model
        scored["task_id"] = task["id"]
        scored["task_category"] = task["category"]
        scored["task_stage"] = task["stage"]
        results.append(scored)
        time.sleep(0.5)  # Gentle rate limiting
    return results


def run_cell_b(model: str) -> list[dict]:
    """Cell B (Direct Jump): Give Stage 4 few-shot, then test."""
    results = []
    for task in TEST_TASKS:
        messages = STAGE_4_PROMPTS + [{"role": "user", "content": task["prompt"]}]
        resp = call_ollama(model, messages)
        response_text = resp.get("message", {}).get("content", "") or resp.get("error", "NO RESPONSE")
        scored = score_response(task, response_text)
        scored["cell"] = "B"
        scored["model"] = model
        scored["task_id"] = task["id"]
        scored["task_category"] = task["category"]
        scored["task_stage"] = task["stage"]
        results.append(scored)
        time.sleep(0.5)
    return results


def run_cell_c(model: str) -> list[dict]:
    """Cell C (Staged): Stage 2 → Stage 3 → Stage 4 sequential, then test."""
    results = []
    for task in TEST_TASKS:
        messages = (
            STAGE_2_PROMPTS
            + STAGE_3_PROMPTS
            + STAGE_4_PROMPTS
            + [{"role": "user", "content": task["prompt"]}]
        )
        resp = call_ollama(model, messages)
        response_text = resp.get("message", {}).get("content", "") or resp.get("error", "NO RESPONSE")
        scored = score_response(task, response_text)
        scored["cell"] = "C"
        scored["model"] = model
        scored["task_id"] = task["id"]
        scored["task_category"] = task["category"]
        scored["task_stage"] = task["stage"]
        results.append(scored)
        time.sleep(0.5)
    return results


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze_results(all_results: list[dict]) -> dict:
    """Aggregate results by cell, model, and task category."""
    analysis: dict[str, Any] = {}

    for model in MODELS:
        analysis[model] = {}
        for cell in ["A", "B", "C"]:
            cell_results = [r for r in all_results if r["model"] == model and r["cell"] == cell]
            if not cell_results:
                continue

            total = len(cell_results)
            correct = sum(1 for r in cell_results if r["correct"])
            avg_score = sum(r["score"] for r in cell_results) / total

            # By category
            by_cat = {}
            for r in cell_results:
                cat = r["task_category"]
                if cat not in by_cat:
                    by_cat[cat] = {"total": 0, "correct": 0, "scores": []}
                by_cat[cat]["total"] += 1
                by_cat[cat]["correct"] += 1 if r["correct"] else 0
                by_cat[cat]["scores"].append(r["score"])

            # By stage
            by_stage = {}
            for r in cell_results:
                s = r["task_stage"]
                if s not in by_stage:
                    by_stage[s] = {"total": 0, "correct": 0}
                by_stage[s]["total"] += 1
                by_stage[s]["correct"] += 1 if r["correct"] else 0

            analysis[model][cell] = {
                "total": total,
                "correct": correct,
                "accuracy": correct / total if total > 0 else 0,
                "avg_score": avg_score,
                "by_category": by_cat,
                "by_stage": by_stage,
            }

    return analysis


def format_results_markdown(analysis: dict, all_results: list[dict]) -> str:
    """Format results as a markdown report."""
    lines = [
        "# Piagetian Stage Irreversibility Test — Results",
        "",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Models:** {', '.join(MODELS)}",
        f"**Test tasks:** {len(TEST_TASKS)}",
        f"**Cells:** A (Control), B (Direct Jump to Stage 4), C (Staged: 2→3→4)",
        "",
        "---",
        "",
        "## Summary",
        "",
    ]

    # Summary table per model
    for model in MODELS:
        if model not in analysis:
            continue
        lines.append(f"### {model}")
        lines.append("")
        lines.append("| Cell | Correct | Total | Accuracy | Avg Score |")
        lines.append("|------|---------|-------|----------|-----------|")
        for cell in ["A", "B", "C"]:
            if cell not in analysis[model]:
                continue
            d = analysis[model][cell]
            lines.append(
                f"| {cell} | {d['correct']} | {d['total']} | "
                f"{d['accuracy']:.1%} | {d['avg_score']:.3f} |"
            )
        lines.append("")

        # By category
        lines.append("**By Task Category:**")
        lines.append("")
        lines.append("| Category | Cell A | Cell B | Cell C |")
        lines.append("|----------|--------|--------|--------|")
        all_cats = set()
        for cell in ["A", "B", "C"]:
            if cell in analysis[model]:
                all_cats.update(analysis[model][cell]["by_category"].keys())
        for cat in sorted(all_cats):
            row = f"| {cat} |"
            for cell in ["A", "B", "C"]:
                if cell in analysis[model] and cat in analysis[model][cell]["by_category"]:
                    c = analysis[model][cell]["by_category"][cat]
                    row += f" {c['correct']}/{c['total']} |"
                else:
                    row += " — |"
            lines.append(row)
        lines.append("")

        # By stage
        lines.append("**By Required Stage:**")
        lines.append("")
        lines.append("| Stage | Cell A | Cell B | Cell C |")
        lines.append("|-------|--------|--------|--------|")
        for stage in [2, 3, 4]:
            row = f"| {stage} |"
            for cell in ["A", "B", "C"]:
                if cell in analysis[model] and stage in analysis[model][cell]["by_stage"]:
                    s = analysis[model][cell]["by_stage"][stage]
                    row += f" {s['correct']}/{s['total']} |"
                else:
                    row += " — |"
            lines.append(row)
        lines.append("")

    # Detailed responses
    lines.append("---")
    lines.append("")
    lines.append("## Detailed Responses (Sample)")
    lines.append("")

    # Show Eisenstein responses for each cell
    for model in MODELS:
        lines.append(f"### {model} — Eisenstein Responses")
        lines.append("")
        for cell in ["A", "B", "C"]:
            eis_results = [
                r for r in all_results
                if r["model"] == model and r["cell"] == cell and r["task_category"] == "eisenstein_norm"
            ]
            if eis_results:
                lines.append(f"**Cell {cell}:**")
                lines.append("```")
                for r in eis_results[:2]:  # First 2 only
                    lines.append(f"Task: {r['task_id']} | Expected: {r.get('expected', '?')} | Got: {'✓' if r['correct'] else '✗'}")
                    # Extract just the numeric answer portion
                    resp = r.get("response", "")[:300]
                    lines.append(resp)
                    lines.append("---")
                lines.append("```")
                lines.append("")

    # Analysis & Conclusion
    lines.append("---")
    lines.append("")
    lines.append("## Analysis")
    lines.append("")

    # Compute key comparison: Cell B vs Cell C for Stage 4 tasks
    for model in MODELS:
        if model not in analysis:
            continue
        lines.append(f"### {model}")
        lines.append("")

        cell_b = analysis[model].get("B", {})
        cell_c = analysis[model].get("C", {})

        b_stage4 = cell_b.get("by_stage", {}).get(4, {})
        c_stage4 = cell_c.get("by_stage", {}).get(4, {})

        b_s4_acc = b_stage4.get("correct", 0) / b_stage4.get("total", 1)
        c_s4_acc = c_stage4.get("correct", 0) / c_stage4.get("total", 1)

        if c_s4_acc > b_s4_acc:
            lines.append(
                f"**Staged (Cell C) outperforms Direct Jump (Cell B) on Stage 4 tasks:** "
                f"{c_s4_acc:.1%} vs {b_s4_acc:.1%}"
            )
            lines.append("→ Evidence SUPPORTS stage irreversibility hypothesis.")
        elif b_s4_acc > c_s4_acc:
            lines.append(
                f"**Direct Jump (Cell B) outperforms Staged (Cell C) on Stage 4 tasks:** "
                f"{b_s4_acc:.1%} vs {c_s4_acc:.1%}"
            )
            lines.append("→ Evidence AGAINST stage irreversibility hypothesis.")
        else:
            lines.append(
                f"**Both cells perform equally on Stage 4 tasks:** {b_s4_acc:.1%}"
            )
            lines.append("→ Inconclusive — may need more tasks or different prompting.")

        lines.append("")

    # Failure mode analysis
    lines.append("### Failure Modes")
    lines.append("")
    for model in MODELS:
        lines.append(f"**{model}:**")
        for cell in ["A", "B", "C"]:
            incorrect = [
                r for r in all_results
                if r["model"] == model and r["cell"] == cell and not r["correct"]
            ]
            if incorrect:
                lines.append(f"- Cell {cell}: {len(incorrect)} failures")
                for r in incorrect[:3]:
                    lines.append(
                        f"  - {r['task_id']}: expected={r.get('expected', r.get('keywords_total', '?'))}, "
                        f"score={r['score']:.2f}"
                    )
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Conclusion")
    lines.append("")
    lines.append("_To be filled after analysis of results._")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("PIAGETIAN STAGE IRREVERSIBILITY TEST")
    print("=" * 60)
    print(f"Time: {datetime.now().isoformat()}")
    print(f"Models: {MODELS}")
    print(f"Tasks: {len(TEST_TASKS)}")
    print(f"Cells: A (Control), B (Direct Jump), C (Staged)")
    print()

    all_results = []

    for model in MODELS:
        print(f"\n{'='*40}")
        print(f"Model: {model}")
        print(f"{'='*40}")

        # Cell A — Control
        print("\n[Cell A — Control (no few-shot)]")
        cell_a = run_cell_a(model)
        all_results.extend(cell_a)
        acc = sum(1 for r in cell_a if r["correct"]) / len(cell_a)
        print(f"  → Accuracy: {acc:.1%} ({sum(1 for r in cell_a if r['correct'])}/{len(cell_a)})")

        # Cell B — Direct Jump
        print("\n[Cell B — Direct Jump (Stage 4 few-shot)]")
        cell_b = run_cell_b(model)
        all_results.extend(cell_b)
        acc = sum(1 for r in cell_b if r["correct"]) / len(cell_b)
        print(f"  → Accuracy: {acc:.1%} ({sum(1 for r in cell_b if r['correct'])}/{len(cell_b)})")

        # Cell C — Staged
        print("\n[Cell C — Staged (2 → 3 → 4 sequential)]")
        cell_c = run_cell_c(model)
        all_results.extend(cell_c)
        acc = sum(1 for r in cell_c if r["correct"]) / len(cell_c)
        print(f"  → Accuracy: {acc:.1%} ({sum(1 for r in cell_c if r['correct'])}/{len(cell_c)})")

    # Analyze
    print("\n\nAnalyzing results...")
    analysis = analyze_results(all_results)

    # Format and save
    report = format_results_markdown(analysis, all_results)

    # Fill in conclusion
    conclusion_lines = []
    for model in MODELS:
        if model not in analysis:
            continue
        cell_b = analysis[model].get("B", {})
        cell_c = analysis[model].get("C", {})
        b_s4 = cell_b.get("by_stage", {}).get(4, {})
        c_s4 = cell_c.get("by_stage", {}).get(4, {})
        b_acc = b_s4.get("correct", 0) / b_s4.get("total", 1) if b_s4.get("total", 0) > 0 else 0
        c_acc = c_s4.get("correct", 0) / c_s4.get("total", 1) if c_s4.get("total", 0) > 0 else 0
        conclusion_lines.append(f"- **{model}**: Cell B (direct) = {b_acc:.1%}, Cell C (staged) = {c_acc:.1%}")

    conclusion = "\n".join(conclusion_lines)
    report = report.replace(
        "_To be filled after analysis of results._",
        conclusion,
    )

    RESULTS_FILE.write_text(report)
    print(f"\nResults saved to: {RESULTS_FILE}")

    # Also save raw JSON
    raw_file = RESULTS_DIR / "stage_irreversibility_raw.json"
    raw_file.write_text(json.dumps(all_results, indent=2))
    print(f"Raw data saved to: {raw_file}")

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for model in MODELS:
        if model not in analysis:
            continue
        print(f"\n{model}:")
        for cell in ["A", "B", "C"]:
            if cell in analysis[model]:
                d = analysis[model][cell]
                print(f"  Cell {cell}: {d['accuracy']:.1%} ({d['correct']}/{d['total']})")

    return all_results, analysis


if __name__ == "__main__":
    main()
