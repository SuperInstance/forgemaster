#!/usr/bin/env python3
"""
Experiment 2: Dependency Graph vs Dependency Stream
Do agents need the FULL dependency graph upfront, or just "what finished last"?
"""
import requests, json, time, os

KEY = open(os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")).read().strip()
URL = "https://api.deepinfra.com/v1/openai/chat/completions"

def query(prompt, max_tokens=250):
    resp = requests.post(URL,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
        json={"model": "ByteDance/Seed-2.0-mini", 
              "messages": [{"role": "user", "content": prompt}],
              "max_tokens": max_tokens, "temperature": 0},
        timeout=60)
    return resp.json()["choices"][0]["message"]["content"]

# A 5-step verification chain
chain = [
    {"id": "T1", "task": "Compute the Eisenstein norm of (3,-1)", 
     "expected": "7", "output": "7"},
    {"id": "T2", "task": "Given norm=7, classify the Weyl sector for (3,-1)",
     "expected": "sector info", "output": "Weyl sector 3 (angle ≈ 300°)"},
    {"id": "T3", "task": "Given sector 3, what's the dominant frequency?",
     "expected": "frequency", "output": "e^{-i4π/3} branch, frequency component at 4π/3"},
    {"id": "T4", "task": "Given frequency 4π/3, what's the snap radius for this sector?",
     "expected": "radius", "output": "snap radius = sqrt(7/3) ≈ 1.53"},
    {"id": "T5", "task": "Given snap radius 1.53, can float32(0.499, 0.866) snap into this sector?",
     "expected": "yes/no with reasoning", "output": "No — distance ≈ 2.65 > 1.53, outside snap radius"},
]

# Mode A: Full graph — agent sees ALL 5 tasks and outputs
graph_prompt = """You have 5 tasks in a dependency chain. Here is the FULL plan:

"""
for t in chain:
    graph_prompt += f"[{t['id']}] {t['task']}\n  → Expected: {t['expected']}\n\n"

graph_prompt += """\nAll outputs from previous steps:
"""
for t in chain:
    graph_prompt += f"{t['id']} result: {t['output']}\n"

graph_prompt += "\nNow execute T5 (the final task). Show your reasoning."

# Mode B: Stream — agent only sees T4's output and T5's task
stream_prompt = f"""Previous step result:
{T4_output if 'T4_output' in dir() else chain[3]['output']}

Your task: {chain[4]['task']}

DONE WHEN: You state whether the point snaps in and explain why."""

# Mode C: JIT — agent sees T4 output + one-line summary of entire chain so far  
jit_prompt = f"""Chain summary: T1(norm=7)→T2(sector 3)→T3(freq 4π/3)→T4(radius 1.53)
Last result: {chain[3]['output']}

Your task: {chain[4]['task']}

DONE WHEN: State whether the point snaps and why."""

# Mode D: Full context + perspectives (our approach)
persp_prompt = f"""Chain: T1→T2→T3→T4→T5 (you are at T5)
Summary: Eisenstein point (3,-1) has norm 7, sector 3, frequency 4π/3, snap radius 1.53
Previous output: {chain[3]['output']}

DO: {chain[4]['task']}
NEED: snap radius from previous step, float32 coordinates, distance calculation
DONE WHEN: State snap/no-snap with numerical reasoning"""

modes = {
    "full_graph": {"name": "Full Dependency Graph", "prompt": graph_prompt},
    "stream": {"name": "Stream (prev output only)", "prompt": stream_prompt},
    "jit": {"name": "JIT (summary + prev output)", "prompt": jit_prompt},
    "perspectives": {"name": "Perspectives (JIT + DO/NEED)", "prompt": persp_prompt},
}

def score_t5(response):
    """Score 0-3 for correctness of T5 answer"""
    r = response.lower()
    score = 0
    # Correct answer: NO, distance > radius
    if "no" in r or "not" in r or "outside" in r or "does not" in r:
        score += 1  # Correct conclusion
    # Shows distance calculation
    if any(x in r for x in ["distance", "dist", "2.65", "1.53"]):
        score += 0.5  # Numerical reasoning
    # Correct comparison
    if any(x in r for x in ["greater", "larger", ">", "outside", "exceeds"]):
        score += 0.5  # Correct comparison
    # Understands snap mechanism
    if any(x in r for x in ["snap", "radius", "coverage"]):
        score += 0.5  # Mechanism understanding
    # Wrong answer penalty
    if "yes" in r and "snap" in r and "no" not in r:
        score -= 1
    return max(score, 0)

print("="*60)
print("EXPERIMENT 2: Dependency Graph vs Stream vs JIT vs Perspectives")
print("="*60)

results = {}
for key, mode in modes.items():
    print(f"\nTesting: {mode['name']}...", flush=True)
    try:
        start = time.time()
        response = query(mode["prompt"])
        elapsed = time.time() - start
        score = score_t5(response)
        tokens = len(response.split())
        results[key] = {"name": mode["name"], "score": score, "tokens": tokens, "time": round(elapsed, 2)}
        print(f"  Score: {score:.1f}/3 | Tokens: {tokens} | Time: {elapsed:.1f}s")
        print(f"  Response: {response[:150]}...")
    except Exception as e:
        results[key] = {"name": mode["name"], "error": str(e)}
        print(f"  ERROR: {e}")

# Summary
print(f"\n{'='*60}")
print(f"{'Mode':<30} {'Score':<8} {'Tokens':<8} {'Time':<8}")
print("-"*60)
for key, r in results.items():
    if "error" not in r:
        print(f"{r['name']:<30} {r['score']:<8.1f} {r['tokens']:<8} {r['time']:<8.2f}s")
    else:
        print(f"{r['name']:<30} ERROR")

winner = max((r for r in results.values() if "score" in r), key=lambda r: r["score"])
print(f"\nWinner: {winner['name']} (score={winner['score']:.1f})")

# Prompt size comparison
for key, mode in modes.items():
    print(f"  {results[key]['name']}: {len(mode['prompt'])} chars input")
