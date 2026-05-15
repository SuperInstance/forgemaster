#!/usr/bin/env python3
"""
spline_scaffold.py — Negative-Space Anchoring for Zero-Shot Guidance
=====================================================================

THE INSIGHT:
Once you've mapped what a model CANNOT do (the negative space),
the boundary defines the model. You don't need dense data.
You need ANCHOR POINTS of verified truth along the boundary.
The model splines between them.

THE PROCESS:
1. Ground truth map tells us WHERE the boundary is
   (e.g., llama-3.1-8b: perfect sub-expressions, fails combination)
   
2. The boundary IS the negative space — it's defined by what's NOT there
   (the model can't combine a², ab, b² into a²-ab+b²)
   
3. Anchor points are MINIMAL true facts placed AT the boundary
   ("a²=25, ab=-15, b²=9" — the pieces it CAN compute)
   
4. The model, given these anchors, walks the path it couldn't find alone
   (given the pieces, "combine: a² - ab + b² = 25 - (-15) + 9 = 49" ✅)

5. Over time, the model INTERNALIZES the boundary from the anchors
   (the scaffold becomes the skill — distillation through use)

This is NOT prompt engineering. It's BOUNDARY ENGINEERING.
We're not telling the model what to do. We're placing buoys
along the edge of what it can't do, and it navigates by them.

Author: Forgemaster ⚒️
"""

import requests, re, json, time
from pathlib import Path
from collections import defaultdict

KEY = open("/home/phoenix/.openclaw/workspace/.credentials/groq-api-key.txt").read().strip()
URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

def query(model, prompt, system="", temp=0.3, max_tokens=50):
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    r = requests.post(URL, headers={"Authorization": f"Bearer {KEY}"},
        json={"model": model, "messages": msgs,
              "temperature": temp, "max_tokens": max_tokens}, timeout=30)
    c = r.json()["choices"][0]["message"]["content"].strip()
    nums = re.findall(r"-?\d+", c)
    return int(nums[-1]) if nums else None, c


# ═══════════════════════════════════════════════════════════════
# STEP 1: The Ground Truth Boundary (from 454-query portrait)
# ═══════════════════════════════════════════════════════════════

BOUNDARY = {
    "model": "llama-3.1-8b-instant",
    "can_do": {
        "a+b": 1.0, "a-b": 1.0, "a*b": 1.0,
        "a²": 1.0, "b²": 1.0, "ab": 1.0, "-ab": 1.0,
        "a²+b²": 1.0, "a³+b": 1.0, "max(a,b)": 1.0,
    },
    "boundary": {
        "a²-ab": 0.33,       # can compute pieces, fails combination
        "-ab+b²": 0.67,      # slightly better
        "a²-ab+b²": 0.25,   # THE cliff
        "a²+2ab-b": 0.75,   # surprisingly ok
    },
    "cannot_do": {
        "2a²-3ab+b²": 0.0,
        "a³-a²b+ab²-b³": 0.0,
        "a²-2ab+b²": 0.0,
    },
    "fragility": {
        "temperature_0.0": 1.0,   # T=0.0: perfect
        "temperature_0.3": 0.20,  # T=0.3: broken
        "temperature_1.0": 0.0,   # T=1.0: destroyed
    }
}

# ═══════════════════════════════════════════════════════════════
# STEP 2: Generate Minimal Anchor Points
# ═══════════════════════════════════════════════════════════════

def generate_anchors(formula, a, b):
    """
    Given a formula the model CAN'T do, compute the anchor points
    it CAN do that sit along the boundary.
    
    The anchors are the sub-expressions the model computes correctly
    but can't combine. Place them as buoys.
    """
    anchors = {}
    
    # Level 0: raw inputs (always correct)
    anchors["a"] = a
    anchors["b"] = b
    
    # Level 1: single operations (always correct)
    anchors["a²"] = a * a
    anchors["b²"] = b * b
    anchors["ab"] = a * b
    anchors["-ab"] = -(a * b)
    anchors["a+b"] = a + b
    anchors["a-b"] = a - b
    
    # Level 2: two-operation combinations (boundary)
    anchors["a²+b²"] = a*a + b*b
    anchors["a²-ab"] = a*a - a*b
    anchors["-ab+b²"] = -(a*b) + b*b
    anchors["a²+ab"] = a*a + a*b
    
    # Level 3: the target — compute directly from formula components
    # We already have all sub-expressions, just combine them
    # Parse the formula into a simple expression using our anchors
    target_expr = formula
    target_expr = target_expr.replace("a²-ab+b²", f"{anchors['a²']}-{anchors['ab']}+{anchors['b²']}")
    target_expr = target_expr.replace("a²-2ab+b²", f"{anchors['a²']}-2*{anchors['ab']}+{anchors['b²']}")
    target_expr = target_expr.replace("2a²-3ab+b²", f"2*{anchors['a²']}-3*{anchors['ab']}+{anchors['b²']}")
    target_expr = target_expr.replace("a³-ab", f"{a**3}-{anchors['ab']}")
    target_expr = target_expr.replace(" ", "")
    try:
        anchors["target"] = eval(target_expr)
    except:
        # Manual computation for known formulas
        anchors["target"] = anchors['a²'] - anchors['ab'] + anchors['b²']  # default
    
    return anchors


def find_spline_path(anchors, formula):
    """
    Find the MINIMUM set of anchors needed to guide the model
    from what it CAN do to what it CAN'T.
    
    The spline path: start from known-correct, add one step at a time,
    each step only requiring combination of already-established truths.
    """
    # For a²-ab+b², the path is:
    # a=5, b=-3 (known)
    # → a²=25 (known, single op)
    # → b²=9 (known, single op)  
    # → ab=-15 (known, single op)
    # → a²-ab = 25-(-15) = 40 (boundary — needs scaffold)
    # → a²-ab+b² = 40+9 = 49 (target — needs scaffold)
    
    # General: decompose formula into binary tree, each node is an anchor
    
    # Simple parser for polynomial expressions
    # Returns the tree of operations
    target = anchors["target"]
    
    # The minimum anchors: sub-expressions that the model computes correctly
    # plus ONE combination step at the boundary
    
    # Strategy: provide all Level 1 (single ops) + the combination instruction
    min_anchors = {
        "a²": anchors["a²"],
        "b²": anchors["b²"],
        "ab": anchors["ab"],
    }
    
    return min_anchors, target


# ═══════════════════════════════════════════════════════════════
# STEP 3: Build Scaffolding Prompts (zero-shot with anchors)
# ═══════════════════════════════════════════════════════════════

def build_scaffold_prompt(formula, a, b, level=0):
    """
    Build progressively scaffolded prompts.
    Level 0: bare (no anchors)
    Level 1: sub-expression anchors (pieces)
    Level 2: pieces + combination instruction
    Level 3: pieces + worked combination (almost giving answer)
    """
    anchors = generate_anchors(formula, a, b)
    target = anchors["target"]
    
    if level == 0:
        # Bare — the model fails here
        return f"Compute {formula} where a={a} and b={b}.", target
    
    elif level == 1:
        # Provide computed sub-expressions as facts
        return (
            f"Given: a={a}, b={b}\n"
            f"Computed: a²={anchors['a²']}, b²={anchors['b²']}, ab={anchors['ab']}\n"
            f"Compute: {formula}"
        ), target
    
    elif level == 2:
        # Pieces + combination instruction
        return (
            f"Given: a={a}, b={b}\n"
            f"Step 1: a² = {anchors['a²']} ✓\n"
            f"Step 2: ab = {anchors['ab']} ✓\n"
            f"Step 3: b² = {anchors['b²']} ✓\n"
            f"Step 4: Combine using {formula} → a² - ab + b² = {anchors['a²']} - ({anchors['ab']}) + {anchors['b²']}\n"
            f"What is the final result?"
        ), target
    
    elif level == 3:
        # Almost giving the answer — just the final arithmetic
        partial = anchors["a²"] - anchors["ab"]
        return (
            f"a² - ab + b² where a={a}, b={b}\n"
            f"= {anchors['a²']} - ({anchors['ab']}) + {anchors['b²']}\n"
            f"= {partial} + {anchors['b²']}\n"
            f"= ?"
        ), target
    
    return f"Compute {formula} where a={a} and b={b}.", target


# ═══════════════════════════════════════════════════════════════
# STEP 4: Test Scaffolding Levels (THE SPLINE EXPERIMENT)
# ═══════════════════════════════════════════════════════════════

def run_spline_experiment():
    """
    Test each scaffolding level on the boundary task.
    The model CAN'T do it bare (level 0).
    How much scaffolding does it need to cross the boundary?
    """
    
    print("╔════════════════════════════════════════════════════════════╗", flush=True)
    print("║  SPLINE SCAFFOLD — Negative Space Anchoring               ║", flush=True)
    print("║  How few anchors does a model need to cross the boundary? ║", flush=True)
    print("╚════════════════════════════════════════════════════════════╝", flush=True)
    
    # The boundary tasks — formulas the model CAN'T do bare
    boundary_tasks = [
        ("a²-ab+b²", (3, 4, 13)),
        ("a²-ab+b²", (5, -3, 49)),
        ("a²-ab+b²", (-4, 3, 37)),
        ("a²-ab+b²", (7, 1, 43)),
        ("a²-2ab+b²", (3, 4, 1)),
        ("a²-2ab+b²", (5, -3, 49)),
        ("2a²-3ab+b²", (3, 4, 5)),
        ("a³-ab", (5, -3, 140)),
    ]
    
    print(f"\n{'Formula':<15s} {'(a,b)':<10s} {'L0':>4s} {'L1':>4s} {'L2':>4s} {'L3':>4s}  {'Scaffold needed'}", flush=True)
    print("-" * 70, flush=True)
    
    results = []
    
    for formula, (a, b, ans) in boundary_tasks:
        level_results = {}
        
        for level in range(4):
            prompt, target = build_scaffold_prompt(formula, a, b, level)
            correct = 0
            for _ in range(5):
                out, _ = query(MODEL, prompt, 
                    system="You are a precise arithmetic computer. Give ONLY the final number.",
                    temp=0.3, max_tokens=20)
                if out == ans:
                    correct += 1
                time.sleep(0.1)
            level_results[level] = correct / 5
        
        # Find minimum scaffold level that gets >80%
        min_level = None
        for level in range(4):
            if level_results[level] >= 0.8:
                min_level = level
                break
        
        l0 = f"{level_results[0]:.0%}" if level_results[0] > 0 else "—"
        l1 = f"{level_results[1]:.0%}" if level_results[1] > 0 else "—"
        l2 = f"{level_results[2]:.0%}" if level_results[2] > 0 else "—"
        l3 = f"{level_results[3]:.0%}" if level_results[3] > 0 else "—"
        
        scaffold = f"L{min_level}" if min_level is not None else "NONE"
        
        print(f"  {formula:<15s} ({a},{b})  {l0:>4s} {l1:>4s} {l2:>4s} {l3:>4s}  → {scaffold}", flush=True)
        results.append({"formula": formula, "a": a, "b": b, "ans": ans, 
                        "levels": level_results, "min_scaffold": min_level})
    
    # ═══════════════════════════════════════════════════════════
    # NOW: Test if the scaffold TRAINS the model
    # Give it scaffolded examples, then test BARE again
    # ═══════════════════════════════════════════════════════════
    
    print("\n\n━━━ SPLINE TRAINING TEST ━━━", flush=True)
    print("  After scaffolded examples, can the model do it BARE?", flush=True)
    
    # Give 3 scaffolded examples, then test bare on a new input
    training_examples = [
        ("a²-ab+b²", 3, 4, 13),
        ("a²-ab+b²", 5, -2, 39),
        ("a²-ab+b²", -4, 3, 37),
    ]
    
    # Build few-shot prompt with scaffolding
    few_shot = "Here are worked examples:\n\n"
    for formula, a, b, ans in training_examples:
        anchors = generate_anchors(formula, a, b)
        few_shot += (
            f"a={a}, b={b}\n"
            f"  a² = {anchors['a²']}\n"
            f"  ab = {anchors['ab']}\n"
            f"  b² = {anchors['b²']}\n"
            f"  {formula} = {anchors['a²']} - ({anchors['ab']}) + {anchors['b²']} = {ans}\n\n"
        )
    
    # Test on novel inputs (not in training set)
    test_cases = [
        (7, 1, 43),
        (-6, -5, 91),
        (5, -3, 49),
        (2, 8, 51),
        (-7, 2, 67),
    ]
    
    print(f"\n  {'After 3 scaffolded examples:':<40s}", flush=True)
    print(f"  {'(a,b)→ans':<15s} {'bare':>6s} {'scaffolded':>12s} {'few-shot':>10s}", flush=True)
    print(f"  {'-'*50}", flush=True)
    
    for a, b, ans in test_cases:
        # Bare (no help)
        bare_correct = 0
        for _ in range(5):
            out, _ = query(MODEL, f"Compute a²-ab+b² where a={a} and b={b}.", 
                system="You are a precise arithmetic computer. Give ONLY the final number.",
                temp=0.3, max_tokens=20)
            if out == ans: bare_correct += 1
            time.sleep(0.1)
        
        # Scaffolded (level 2)
        scaffold_correct = 0
        prompt, _ = build_scaffold_prompt("a²-ab+b²", a, b, level=2)
        for _ in range(5):
            out, _ = query(MODEL, prompt,
                system="You are a precise arithmetic computer. Give ONLY the final number.",
                temp=0.3, max_tokens=20)
            if out == ans: scaffold_correct += 1
            time.sleep(0.1)
        
        # Few-shot (3 examples in context)
        few_correct = 0
        few_prompt = few_shot + f"Now compute a²-ab+b² where a={a} and b={b}. Give ONLY the final number."
        for _ in range(5):
            out, _ = query(MODEL, few_prompt,
                system="You are a precise arithmetic computer. Give ONLY the final number.",
                temp=0.3, max_tokens=20)
            if out == ans: few_correct += 1
            time.sleep(0.1)
        
        print(f"  ({a},{b})→{ans:<5d} {bare_correct:>4d}/5 {scaffold_correct:>10d}/5 {few_correct:>8d}/5", flush=True)
    
    # ═══════════════════════════════════════════════════════════
    # CROSS-MODEL: Does the same scaffold work for other models?
    # ═══════════════════════════════════════════════════════════
    
    print("\n\n━━━ CROSS-MODEL SPLINE TEST ━━━", flush=True)
    print("  Does the same scaffold transfer to other models?", flush=True)
    
    other_models = ["llama-3.3-70b-versatile", "meta-llama/llama-4-scout-17b-16e-instruct"]
    test = (5, -3, 49)
    
    for model in other_models:
        short = model.split("/")[-1][:20]
        print(f"\n  {short}:", flush=True)
        
        for level in range(4):
            prompt, _ = build_scaffold_prompt("a²-ab+b²", test[0], test[1], level)
            correct = 0
            for _ in range(5):
                out, _ = query(model, prompt,
                    system="You are a precise arithmetic computer. Give ONLY the final number.",
                    temp=0.3, max_tokens=20)
                if out == test[2]: correct += 1
                time.sleep(0.15)
            print(f"    L{level}: {correct}/5", flush=True)
    
    # ═══════════════════════════════════════════════════════════
    # GENERATE: The Spline Tile (for PLATO retrieval)
    # ═══════════════════════════════════════════════════════════
    
    spline_tile = {
        "id": "spline-combination-boundary",
        "type": "spline",
        "trigger": "Model computes sub-expressions correctly but fails to combine them into final result",
        "boundary": "a², b², ab each 100% correct; a²-ab+b² only 25% correct",
        "anchor_points": [
            "a² = a*a (Level 1, always correct)",
            "b² = b*b (Level 1, always correct)", 
            "ab = a*b (Level 1, always correct)",
        ],
        "spline_path": "Provide Level 1 anchors → model combines correctly",
        "min_scaffold_level": "TBD (measuring now)",
        "confidence": 0.80,
        "evidence": ["GROUND-TRUTH-PORTRAIT.md: sub-expressions 100%, combination 25%"],
        "negative": "Only tested on arithmetic. Unknown if combination scaffolding transfers to code generation or reasoning.",
    }
    
    return results, spline_tile


if __name__ == "__main__":
    results, tile = run_spline_experiment()
    
    # Save
    outpath = Path("/home/phoenix/.openclaw/workspace/experiments/spline-results.json")
    with open(outpath, "w") as f:
        json.dump({"results": results, "tile": tile}, f, indent=2)
    print(f"\nSaved to {outpath}", flush=True)
