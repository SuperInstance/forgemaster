#!/usr/bin/env python3
"""Piaget Stage Test — Phase 2: Recall & Transfer on Eisenstein Integers"""

import json, time, urllib.request, urllib.error, os, sys
from datetime import datetime

OLLAMA_URL = "http://localhost:11434/api/chat"
MODELS = ["qwen3:0.6b", "qwen3:4b", "gemma3:1b"]

# ── Questions ──────────────────────────────────────────────
QUESTIONS = [
    # Group A — Recall (formula NOT provided)
    {"id": 1, "group": "A", "q": "Is 7 an Eisenstein prime? Answer yes or no with one sentence of reasoning."},
    {"id": 2, "group": "A", "q": "What is the norm of the Eisenstein integer 3+2ω?"},
    {"id": 3, "group": "A", "q": "Find all Eisenstein integers with norm 7."},
    {"id": 4, "group": "A", "q": "Is the product of two Eisenstein primes always an Eisenstein prime?"},
    # Group B — Transfer
    {"id": 5, "group": "B", "q": "If N(α) = 13 and N(β) = 7, what is N(αβ)?"},
    {"id": 6, "group": "B", "q": "Is 1−ω a unit in the Eisenstein integers? Why?"},
    {"id": 7, "group": "B", "q": "How many Eisenstein integers have norm 3?"},
    {"id": 8, "group": "B", "q": "Which has more divisors in the Eisenstein integers: 7 or 13?"},
]

# ── Cell scaffolds ─────────────────────────────────────────
CELL_A_SYSTEM = "You are a helpful math assistant. Answer concisely."

CELL_B_SYSTEM = """You are a helpful math assistant. Think step by step.

Examples of step-by-step reasoning:
- To check if 17 is prime: try dividing by 2,3,5,7,11,13. None divide evenly, so 17 is prime.
- To find the GCD of 48 and 18: 48=18×2+12, 18=12×1+6, 12=6×2+0, so GCD=6.
- To count integers with norm ≤5 in Z[i]: check each Gaussian integer a+bi with |a|,|b|≤2, count those with a²+b²≤5.

Now answer the question step by step."""

CELL_C_SYSTEM = """You are a helpful math assistant. First, consider these warm-up facts about Eisenstein integers:
- Eisenstein integers are numbers of the form a+bω where ω = e^{2πi/3} = (-1+i√3)/2
- The norm is N(a+bω) = a² - ab + b²
- A rational prime p is an Eisenstein prime iff p ≡ 2 (mod 3), except 3 which is special (3 = -ω²(1-ω)²).

Now answer the question using these facts."""

CELLS = {
    "A": CELL_A_SYSTEM,
    "B": CELL_B_SYSTEM,
    "C": CELL_C_SYSTEM,
}

# ── Answer keys for scoring ────────────────────────────────
# Score 0=wrong, 1=partially correct, 2=fully correct
ANSWER_KEYS = {
    1: {
        "key_answer": "No, 7 is not an Eisenstein prime because 7 ≡ 1 (mod 3), so it factors as 7 = (2+3ω)(2+3ω̄) or similar. Equivalently, 7 = (3-ω)(3-ω²).",
        "must_contain": ["no", "not", "≡ 1", "1 (mod 3)", "factors", "factor"],
        "partial": ["no", "not"],
        "full": ["7", "≡ 1", "mod 3"],  # needs 7 and mod 3 reasoning
    },
    2: {
        "key_answer": "N(3+2ω) = 3² - 3·2 + 2² = 9 - 6 + 4 = 7.",
        "must_contain": ["7"],
        "partial": ["7"],
        "full_requires_computation": True,  # must show computation or get 7
    },
    3: {
        "key_answer": "The Eisenstein integers with norm 7 are the 12 associates of (3-ω) and (2+3ω) etc. Specifically: ±(3+ω), ±(3+2ω), ±(2+3ω), ±(1-3ω), and their rotations. There are exactly 12.",
        "must_contain": ["12"],
        "partial": ["3+2ω", "2+3ω", "3+ω", "2-ω", "3-ω"],
        "full": ["12"],
    },
    4: {
        "key_answer": "No. The product of two primes is composite by definition. E.g., 2 and 5 are Eisenstein primes (both ≡ 2 mod 3), but 2·5 = 10 is not prime.",
        "must_contain": ["no"],
        "partial": ["no"],
        "full": ["no", "product", "composite", "example", "10"],
    },
    5: {
        "key_answer": "N(αβ) = N(α)·N(β) = 13·7 = 91.",
        "must_contain": ["91"],
        "partial": ["91"],
        "full": ["91"],
    },
    6: {
        "key_answer": "Yes, 1-ω is a unit. N(1-ω) = 1² - 1·(-1) + (-1)² = 1+1+1 = 3... wait. Actually N(1-ω) = 1 - 1·(-1) + 1 = 3. Hmm, that's not 1. Actually 1-ω has norm 3, NOT a unit. The units are ±1, ±ω, ±ω². So 1-ω is NOT a unit.",
        "must_contain": ["not", "no"],
        "partial": ["unit", "norm"],
        "full": ["no", "not", "norm"],
    },
    7: {
        "key_answer": "0. There are no Eisenstein integers with norm 3... wait. N(1-ω) = 1²-1·(-1)+(-1)² = 3. And N(1+ω) = 1-1·1+1 = 1 (unit). Actually N(a+bω) = a²-ab+b² = 3. Solutions: (a,b) = (2,1): 4-2+1=3 ✓, (1,2): 1-2+4=3 ✓, (-1,-2): 1+2+4=7 ✗. With associates there are 6 Eisenstein integers with norm 3.",
        "must_contain": ["6"],
        "partial": ["6", "3", "2+ω"],
        "full": ["6"],
    },
    8: {
        "key_answer": "7 has more divisors. 7 ≡ 1 (mod 3) so it factors into two non-associate Eisenstein primes, giving more divisors. 13 ≡ 1 (mod 3) also factors, but 7 = π·π̄ with N(π)=7, while 13 = σ·σ̄ with N(σ)=13. Both factor similarly. Actually both are ≡ 1 mod 3 so both factor. They have the same number of divisors (up to associates). Wait — both factor as products of two non-units, so the divisor structure is the same. The answer is: they have the same number of divisors (up to associates), or equivalently 13 has more divisors if counting all Eisenstein integers that divide them.",
        "must_contain": ["7", "13"],
        "partial": ["7", "13", "same", "≡ 1", "mod 3"],
        "full": ["same", "≡ 1", "both"],
    },
}


def score_response(qid, response):
    """Score a response 0, 1, or 2."""
    r = response.lower()
    key = ANSWER_KEYS[qid]

    if qid == 1:
        # Must say no/not, and give mod 3 reasoning
        has_no = any(w in r for w in ["no", "not an eisenstein prime", "not prime"])
        has_mod3 = "mod 3" in r or "≡ 1" in r or "= 1 (mod" in r or "remainder 1" in r
        has_factors = "factor" in r or "composite" in r or "split" in r
        if has_no and (has_mod3 or has_factors):
            return 2
        elif has_no:
            return 1
        else:
            return 0

    elif qid == 2:
        # Must compute norm = 7
        has_7 = "7" in r.split() or "= 7" in r or "=7" in r or "is 7" in r or "equals 7" in r
        has_computation = "3²" in r or "9" in r or "a²" in r or "a^2" in r or "3**2" in r or "3*3" in r
        if has_7 and has_computation:
            return 2
        elif has_7:
            return 1
        else:
            return 0

    elif qid == 3:
        # Must find the integers and ideally say 12
        has_12 = "12" in r
        has_example = any(s in r for s in ["3+2ω", "3+2w", "2+3ω", "2+3w", "3+ω", "3+w", "2-ω", "2-w", "3-ω", "3-w"])
        if has_12 and has_example:
            return 2
        elif has_12:
            return 1
        elif has_example:
            return 1
        else:
            return 0

    elif qid == 4:
        # Must say no
        has_no = any(w in r for w in ["no", "not always", "never"])
        has_reason = any(w in r for w in ["product", "composite", "example", "10", "multiply", "not prime"])
        if has_no and has_reason:
            return 2
        elif has_no:
            return 1
        else:
            return 0

    elif qid == 5:
        # Must get 91
        has_91 = "91" in r
        has_mult = "13" in r and "7" in r
        if has_91 and has_mult:
            return 2
        elif has_91:
            return 2
        else:
            return 0

    elif qid == 6:
        # 1-ω has norm 3, so it's NOT a unit
        has_no = "no" in r or "not" in r or "isn't" in r or "is not" in r
        has_norm = "norm" in r and "3" in r
        has_units = "unit" in r
        if has_no and has_norm:
            return 2
        elif has_no or has_norm:
            return 1
        else:
            return 0

    elif qid == 7:
        # 6 Eisenstein integers have norm 3
        has_6 = "6" in r or "six" in r
        has_explanation = any(s in r for w in ["2+ω", "2+w", "2+1", "1+2"] for s in [w])
        if has_6:
            return 2
        elif has_explanation or "0" in r:
            return 1
        else:
            return 0

    elif qid == 8:
        # Both ≡ 1 mod 3, same number of divisors up to associates
        has_same = "same" in r or "equal" in r or "both" in r
        has_mod3 = "mod 3" in r or "≡ 1" in r
        has_both = "7" in r and "13" in r
        if has_same and has_mod3 and has_both:
            return 2
        elif has_same and has_both:
            return 1
        elif has_both:
            return 1
        else:
            return 0

    return 0


def query_ollama(model, system, user_msg, timeout=120):
    """Send a single query to Ollama and return the response text."""
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ],
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 512},
    }).encode()

    req = urllib.request.Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            return data.get("message", {}).get("content", "").strip()
    except Exception as e:
        return f"ERROR: {e}"


def main():
    results = []
    total = len(MODELS) * len(CELLS) * len(QUESTIONS)
    done = 0

    for model in MODELS:
        for cell_name, system in CELLS.items():
            for q in QUESTIONS:
                done += 1
                label = f"[{done}/{total}] {model} cell={cell_name} Q{q['id']}"
                print(f"{label} ...", flush=True)

                t0 = time.time()
                response = query_ollama(model, system, q["q"])
                elapsed = time.time() - t0

                score = score_response(q["id"], response)

                results.append({
                    "model": model,
                    "cell": cell_name,
                    "question_id": q["id"],
                    "group": q["group"],
                    "question": q["q"],
                    "response": response,
                    "score": score,
                    "elapsed_s": round(elapsed, 1),
                    "timestamp": datetime.now().isoformat(),
                })

                print(f"  score={score} ({elapsed:.1f}s)", flush=True)

                # Small delay to avoid overwhelming Ollama
                time.sleep(0.5)

    # ── Save raw JSON ──
    raw_path = "/home/phoenix/.openclaw/workspace/experiments/stage_irreversibility_phase2_raw.json"
    with open(raw_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nRaw results saved to {raw_path}")

    # ── Analysis ──
    summary = {}
    for model in MODELS:
        summary[model] = {}
        for cell in ["A", "B", "C"]:
            cell_results = [r for r in results if r["model"] == model and r["cell"] == cell]
            scores = [r["score"] for r in cell_results]
            group_a = [r["score"] for r in cell_results if r["group"] == "A"]
            group_b = [r["score"] for r in cell_results if r["group"] == "B"]
            summary[model][cell] = {
                "total": sum(scores),
                "max": len(scores) * 2,
                "pct": round(100 * sum(scores) / (len(scores) * 2), 1),
                "group_a_total": sum(group_a),
                "group_a_max": len(group_a) * 2,
                "group_b_total": sum(group_b),
                "group_b_max": len(group_b) * 2,
                "per_question": {r["question_id"]: r["score"] for r in cell_results},
            }

    # ── Generate markdown report ──
    md = f"""# Piaget Stage Test — Phase 2: Recall & Transfer (Eisenstein Integers)

**Date:** {datetime.now().strftime("%Y-%m-%d %H:%M")}
**Models:** {', '.join(MODELS)}
**Cells:** A (baseline), B (step-by-step few-shot), C (Eisenstein warm-up facts)
**Questions:** 8 (4 recall, 4 transfer) — formula NOT provided
**Scoring:** 0=wrong, 1=partial, 2=correct (max=16 per cell)

## Summary Scores

| Model | Cell A | Cell B | Cell C | A% | B% | C% |
|-------|--------|--------|--------|----|----|-----|
"""

    for model in MODELS:
        a = summary[model]["A"]
        b = summary[model]["B"]
        c = summary[model]["C"]
        md += f"| {model} | {a['total']}/{a['max']} | {b['total']}/{b['max']} | {c['total']}/{c['max']} | {a['pct']}% | {b['pct']}% | {c['pct']}% |\n"

    md += """
## Per-Model Detail

"""
    for model in MODELS:
        md += f"### {model}\n\n"
        md += "| Q | Group | Cell A | Cell B | Cell C |\n|---|-------|--------|--------|--------|\n"
        for q in QUESTIONS:
            qid = q["id"]
            scores_row = []
            for cell in ["A", "B", "C"]:
                s = summary[model][cell]["per_question"][qid]
                scores_row.append(str(s))
            md += f"| {qid} | {q['group']} | {' → '.join(scores_row[:1])} | {scores_row[1]} | {scores_row[2]} |\n"
        md += "\n"

    md += """## Group Comparison (Recall vs Transfer)

| Model | Cell | Recall (A) | Transfer (B) |
|-------|------|------------|--------------|
"""
    for model in MODELS:
        for cell in ["A", "B", "C"]:
            c = summary[model][cell]
            md += f"| {model} | {cell} | {c['group_a_total']}/{c['group_a_max']} | {c['group_b_total']}/{c['group_b_max']} |\n"

    # Stage classification
    md += """
## Stage Classification

| Model | Cell A | Cell B | Cell C | Overall Stage |
|-------|--------|--------|--------|---------------|
"""
    for model in MODELS:
        stages = []
        for cell in ["A", "B", "C"]:
            pct = summary[model][cell]["pct"]
            if pct >= 75:
                stages.append("S4")
            elif pct >= 50:
                stages.append("S3")
            elif pct >= 25:
                stages.append("S2")
            else:
                stages.append("S1")
        overall = max(stages)  # best performance
        md += f"| {model} | {stages[0]} | {stages[1]} | {stages[2]} | {overall} |\n"

    md += """
## Key Observations

### Phase 2 vs Phase 1
Phase 2 tests **recall** (knowing Eisenstein integer properties without being given formulas) vs Phase 1 which tested **computation** (applying given formulas). This distinguishes:
- **Stage 4**: Can recall domain facts AND apply them correctly
- **Stage 3**: Can apply scaffolding but lacks independent recall
- **Stage 2**: Partial recall, inconsistent application
- **Stage 1**: Cannot recall or apply domain-specific knowledge

### Expected Patterns
- **qwen3:0.6b (Stage 1)**: Near-zero scores across all cells — too small for domain recall
- **qwen3:4b (Stage 2-3)**: Cell C > Cell B > Cell A (scaffolding helps), moderate scores
- **gemma3:1b (Stage 1)**: Low scores, may show some improvement with Cell C

### Critical Test: Cell B vs Cell C
- Cell B gives general reasoning scaffolding → helps Stage 3+ (can reason if they know facts)
- Cell C gives domain facts → helps Stage 2+ (can apply if given the facts)
- **If Cell C >> Cell B**: Model is Stage 2 (needs domain knowledge, not reasoning help)
- **If Cell B >> Cell C**: Model is Stage 3 (can reason but domain knowledge is wrong)
- **If Cell B ≈ Cell C ≈ high**: Model is Stage 4 (has both reasoning and domain knowledge)

## Sample Responses
"""
    # Add a few interesting sample responses
    for model in MODELS:
        md += f"\n### {model} — Q5 (N(αβ)) Cell A\n"
        for r in results:
            if r["model"] == model and r["cell"] == "A" and r["question_id"] == 5:
                md += f"**Score: {r['score']}/2**\n> {r['response'][:300]}\n\n"
                break

        md += f"### {model} — Q1 (7 prime?) Cell C\n"
        for r in results:
            if r["model"] == model and r["cell"] == "C" and r["question_id"] == 1:
                md += f"**Score: {r['score']}/2**\n> {r['response'][:300]}\n\n"
                break

    report_path = "/home/phoenix/.openclaw/workspace/experiments/STAGE-IRREVERSIBILITY-PHASE2.md"
    with open(report_path, "w") as f:
        f.write(md)
    print(f"Report saved to {report_path}")

    # Print summary
    print("\n" + "="*60)
    print("QUICK SUMMARY")
    print("="*60)
    for model in MODELS:
        print(f"\n{model}:")
        for cell in ["A", "B", "C"]:
            c = summary[model][cell]
            print(f"  Cell {cell}: {c['total']}/{c['max']} ({c['pct']}%)")
            print(f"    Recall: {c['group_a_total']}/{c['group_a_max']}, Transfer: {c['group_b_total']}/{c['group_b_max']}")


if __name__ == "__main__":
    main()
