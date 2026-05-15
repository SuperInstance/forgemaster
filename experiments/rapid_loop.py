#!/usr/bin/env python3
"""
Rapid Experimentation Engine — Groq-Powered
=============================================
Uses Groq's 26ms latency for fast iteration loops:
1. Decompose a research question into testable sub-questions
2. Design minimal experiments for each
3. Run them immediately (not batch — iterate)
4. Read results, generate NEW questions from what we learn
5. Repeat until convergence or novelty exhaustion

Each cycle takes ~2-5 seconds. A full wheel spoke in under a minute.

Author: Forgemaster ⚒️
"""

import requests, json, re, time, sys
from collections import defaultdict

GROQ_KEY = open("/home/phoenix/.openclaw/workspace/.credentials/groq-api-key.txt").read().strip()
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"  # Fast, clean content, good at math

# ─── CORE TOOLS ────────────────────────────────────────────────

def groq(prompt, system="You are a precise arithmetic computer. Give ONLY the final number.", temp=0.3):
    """Single Groq query. ~26ms."""
    r = requests.post(GROQ_URL,
        headers={"Authorization": f"Bearer {GROQ_KEY}"},
        json={"model": MODEL, "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ], "temperature": temp, "max_tokens": 50},
        timeout=30)
    content = r.json()["choices"][0]["message"]["content"].strip()
    nums = re.findall(r"-?\d+", content)
    return int(nums[-1]) if nums else None, content

def groq_batch(prompts, temp=0.3):
    """Run a batch of prompts, return results."""
    results = []
    for p in prompts:
        out, raw = groq(p, temp=temp)
        results.append((out, raw))
        time.sleep(0.1)
    return results

def classify_output(out, a, b, answer, intermediates=None):
    """Classify a single output against expected values."""
    if out is None: return "INVALID"
    if out == answer: return "CORRECT"
    # Echoes
    for name, val in [("a", a), ("b", b), ("a+b", a+b), ("a-b", a-b), ("-a", -a), ("-b", -b)]:
        if out == val: return f"ECHO-{name}"
    # Partials
    if intermediates:
        for name, val in intermediates.items():
            if out == val: return f"PARTIAL-{name}"
    # Near-miss
    if abs(out - answer) <= 2: return "NEAR"
    return "OTHER"

# ─── EXPERIMENT TEMPLATES ──────────────────────────────────────

def width_sweep(model, tasks_by_width, trials=5):
    """Test a model across dependency widths."""
    results = {}
    for width, task_list in tasks_by_width.items():
        counts = defaultdict(int)
        for task in task_list:
            for _ in range(trials):
                out, raw = groq(task["prompt"])
                cls = classify_output(out, task["a"], task["b"], task["answer"], task.get("intermediates"))
                counts[cls] += 1
        n = sum(counts.values())
        results[width] = {
            "correct": counts.get("CORRECT", 0) / n,
            "echo": sum(v for k, v in counts.items() if "ECHO" in k) / n,
            "partial": sum(v for k, v in counts.items() if "PARTIAL" in k) / n,
            "other": counts.get("OTHER", 0) / n,
        }
    return results

def rapid_probe(question, test_inputs):
    """Rapid probe: ask the same question type with varied inputs.
    Returns (correct_rate, residue_distribution, interesting_patterns)."""
    correct = 0
    residue = defaultdict(int)
    patterns = []
    
    for inp in test_inputs:
        prompt = question.format(**inp)
        out, raw = groq(prompt)
        cls = classify_output(out, inp.get("a",0), inp.get("b",0), inp["answer"], inp.get("intermediates"))
        residue[cls] += 1
        if out == inp["answer"]:
            correct += 1
        elif cls == "OTHER" and out is not None:
            patterns.append({"input": inp, "output": out, "expected": inp["answer"], "raw": raw[:60]})
    
    n = len(test_inputs)
    return {
        "correct_rate": correct / n if n > 0 else 0,
        "residue": dict(residue),
        "novel_patterns": patterns[:5],
        "n": n,
    }

# ─── THE RAPID LOOP ───────────────────────────────────────────

def design_experiments(finding_statement):
    """Use Groq to design experiments that test a finding."""
    prompt = f"""Given this research finding: "{finding_statement}"

Design 3 MINIMAL experiments to test, refine, or falsify this finding.
Each experiment should use a simple arithmetic task with specific inputs.
Format each as JSON:
{{"name": "...", "independent_var": "...", "task": "formula", "inputs": [{{"a": N, "b": M, "answer": N}}], "prediction": "what we expect"}}

Respond with ONLY the JSON array, no other text."""

    out, raw = groq(prompt, system="You are an experimental designer. Output ONLY valid JSON.", temp=0.7)
    
    # Try to parse JSON from response
    try:
        # Find JSON array in response
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    except:
        pass
    return []

def read_results(probe_results):
    """Interpret probe results and generate follow-up questions."""
    findings = []
    
    cr = probe_results["correct_rate"]
    residue = probe_results["residue"]
    
    if cr > 0.8:
        findings.append(f"HIGH accuracy ({cr:.0%}) — model handles this task confidently")
    elif cr > 0.4:
        findings.append(f"MODERATE accuracy ({cr:.0%}) — partial capability, worth decomposing")
    elif cr > 0.1:
        findings.append(f"LOW accuracy ({cr:.0%}) — model struggles, residue analysis valuable")
    else:
        findings.append(f"NEAR-ZERO accuracy ({cr:.0%}) — beyond model's capability boundary")
    
    if residue.get("ECHO-a", 0) + residue.get("ECHO-b", 0) > probe_results["n"] * 0.3:
        findings.append("High echo rate — model attending but not computing")
    
    if residue.get("OTHER", 0) > probe_results["n"] * 0.3:
        findings.append("High OTHER rate — structured errors worth analyzing")
        for p in probe_results.get("novel_patterns", []):
            findings.append(f"  Novel: input({p['input']}) → {p['output']} (expected {p['expected']})")
    
    return findings

def sound_for_rocks(known_vars, width_range=(1, 5)):
    """Systematically probe the dependency width space to find interesting rocks.
    
    A 'rock' is a (model, width, novelty) combination where the result is
    unexpected — higher or lower accuracy than the model predicts.
    """
    rocks = []
    
    print("\n🔍 SOUNDING FOR ROCKS", flush=True)
    print("=" * 60, flush=True)
    
    # Test novel operations at each width
    operations = [
        (1, "a+2b", lambda a,b: a+2*b, {}),
        (1, "3a-b", lambda a,b: 3*a-b, {}),
        (2, "a²+2b²", lambda a,b: a*a+2*b*b, {"a²": None, "2b²": None}),
        (2, "2ab+b", lambda a,b: 2*a*b+b, {}),
        (3, "a²-ab+2b²", lambda a,b: a*a-a*b+2*b*b, {}),
        (3, "2a²-3ab+b²", lambda a,b: 2*a*a-3*a*b+b*b, {}),
        (4, "a³+ab-b²", lambda a,b: a**3+a*b-b*b, {}),
    ]
    
    test_pairs = [(3,4), (5,-2), (-4,3), (7,1), (-6,-5)]
    
    for width, formula, fn, intermediates in operations:
        if width < width_range[0] or width > width_range[1]:
            continue
        
        correct = 0
        total = 0
        unexpected = []
        
        for a, b in test_pairs:
            ans = fn(a, b)
            # Compute intermediates for this specific (a,b)
            local_intermediates = {}
            for name, val_fn in intermediates.items():
                if callable(val_fn):
                    try: local_intermediates[name] = val_fn(a, b) if val_fn.__code__.co_argcount == 2 else val_fn
                    except: pass
                elif val_fn is None:
                    pass
            
            prompt = f"Compute {formula} where a={a} and b={b}. Give ONLY the number."
            out, raw = groq(prompt)
            cls = classify_output(out, a, b, ans, local_intermediates)
            total += 1
            
            if out == ans:
                correct += 1
            elif cls not in ("CORRECT",) and out is not None:
                unexpected.append({"formula": formula, "a": a, "b": b, "out": out, "expected": ans, "class": cls})
            
            time.sleep(0.1)
        
        rate = correct / total if total > 0 else 0
        
        # Rock detection: unexpected results
        is_rock = False
        if width >= 3 and rate > 0.4:
            is_rock = True  # Better than expected at high width
            rocks.append({"type": "HIGH_ROCK", "formula": formula, "width": width, "rate": rate})
        elif width <= 1 and rate < 0.6:
            is_rock = True  # Worse than expected at low width
            rocks.append({"type": "LOW_ROCK", "formula": formula, "width": width, "rate": rate})
        
        sym = "🪨" if is_rock else "  "
        print(f"  {sym} w={width} {formula:<15s} {correct}/{total} ({rate:.0%})", flush=True)
        
        for u in unexpected[:2]:
            print(f"     → ({u['a']},{u['b']})→{u['out']} expected {u['expected']} [{u['class']}]", flush=True)
    
    return rocks

def run_rapid_loop():
    """The main rapid experimentation loop."""
    
    print("=" * 60, flush=True)
    print("RAPID EXPERIMENTATION ENGINE — Groq-Powered", flush=True)
    print(f"Model: {MODEL} (~26ms/query)", flush=True)
    print("=" * 60, flush=True)
    
    # ─── PHASE 1: Verify known rocks ────────────────────────────
    print("\n📐 PHASE 1: Verify Known Rocks", flush=True)
    print("-" * 60, flush=True)
    
    known_rocks = [
        ("Width-1 familiar", "a²+b²", [(3,4,25),(5,-2,29),(-4,3,25),(7,1,50)]),
        ("Width-3 familiar", "a²-ab+b²", [(3,4,13),(5,-2,39),(-4,3,37),(7,1,43)]),
    ]
    
    for name, formula, cases in known_rocks:
        correct = 0
        for a, b, ans in cases:
            out, _ = groq(f"Compute {formula} where a={a} and b={b}. Give ONLY the number.")
            if out == ans: correct += 1
        print(f"  {name}: {correct}/{len(cases)}", flush=True)
    
    # ─── PHASE 2: Sound for NEW rocks ──────────────────────────
    print("\n\n📐 PHASE 2: Sound for New Rocks", flush=True)
    print("-" * 60, flush=True)
    
    rocks = sound_for_rocks(["training_coverage", "dependency_width", "n_heads"], width_range=(1, 4))
    
    if rocks:
        print(f"\n  🪨 Found {len(rocks)} rocks worth sounding:", flush=True)
        for r in rocks:
            print(f"     {r['type']}: {r['formula']} (width={r['width']}, rate={r['rate']:.0%})", flush=True)
    else:
        print(f"\n  No new rocks at this sweep.", flush=True)
    
    # ─── PHASE 3: Probe the most interesting rock ──────────────
    if rocks:
        best_rock = max(rocks, key=lambda r: abs(r["rate"] - 0.5))  # Most surprising
        print(f"\n\n🔬 PHASE 3: Deep Probe of {best_rock['formula']}", flush=True)
        print("-" * 60, flush=True)
        
        # Run 20 trials with varied inputs
        formula = best_rock["formula"]
        import random
        test_set = []
        for _ in range(20):
            a = random.randint(-10, 10)
            b = random.randint(-10, 10)
            if a == 0 and b == 0: continue
            # We need to compute the answer ourselves
            # Simple eval for arithmetic formulas
            try:
                ans = eval(formula.replace("²", "**2"), {"a": a, "b": b})
            except:
                continue
            test_set.append({"a": a, "b": b, "answer": ans})
        
        probe = rapid_probe(f"Compute {formula} where a={{a}} and b={{b}}. Give ONLY the number.", test_set)
        
        print(f"  Correct: {probe['correct_rate']:.0%} ({probe['n']} trials)", flush=True)
        print(f"  Residue: {probe['residue']}", flush=True)
        
        findings = read_results(probe)
        for f in findings:
            print(f"  → {f}", flush=True)
        
        # ─── PHASE 4: Generate follow-up experiments ────────────
        print(f"\n\n🎡 PHASE 4: Generate Follow-Up Experiments", flush=True)
        print("-" * 60, flush=True)
        
        finding_text = f"Model achieves {probe['correct_rate']:.0%} on {formula} (width={best_rock['width']}). Residue: {probe['residue']}"
        exps = design_experiments(finding_text)
        
        if exps:
            print(f"  Generated {len(exps)} experiments:", flush=True)
            for e in exps[:3]:
                name = e.get("name", "?")
                iv = e.get("independent_var", "?")
                pred = e.get("prediction", "?")[:60]
                print(f"    • {name}: vary {iv} — {pred}", flush=True)
        else:
            # Manual follow-up
            print("  Manual follow-ups:", flush=True)
            if probe["correct_rate"] > 0.5:
                print("    → Try width+1 version of this task — where does it break?", flush=True)
            else:
                print("    → Try width-1 version — is the boundary sharp?", flush=True)
            print("    → Try negative inputs specifically — sign handling?", flush=True)
            print("    → Try larger magnitude inputs (|a|,|b| > 10) — overflow?", flush=True)
    
    # ─── PHASE 5: Temperature sweep on boundary task ───────────
    print("\n\n🌡️ PHASE 5: Temperature Sweep", flush=True)
    print("-" * 60, flush=True)
    
    # Use the Eisenstein norm as boundary task
    a, b, ans = 5, -2, 39
    for temp in [0.0, 0.1, 0.3, 0.5, 0.7, 1.0, 1.5]:
        correct = 0
        for _ in range(5):
            out, _ = groq(f"Compute a²-ab+b² where a={a} and b={b}. Give ONLY the number.", temp=temp)
            if out == ans: correct += 1
        print(f"  T={temp:.1f}: {correct}/5 correct", flush=True)
    
    print("\n" + "=" * 60, flush=True)
    print("RAPID LOOP COMPLETE — cycle time: ~60 seconds", flush=True)
    print("Use findings to design next spoke of the Wheel.", flush=True)
    print("=" * 60, flush=True)


if __name__ == "__main__":
    run_rapid_loop()
