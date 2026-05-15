#!/usr/bin/env python3
"""
swarm_arena.py — Live Multi-Agent Arena on Groq
================================================
N agents tackle the same problem simultaneously.
Residue from each agent feeds the others' next round.

The arena IS the experiment. The game IS the measurement.

Usage:
    python3 experiments/swarm_arena.py --task "map a²-ab+b² boundary" --agents 8 --rounds 3
"""
import requests, re, json, time, random, argparse
from collections import defaultdict, Counter
from pathlib import Path

KEY = open("/home/phoenix/.openclaw/workspace/.credentials/groq-api-key.txt").read().strip()
URL = "https://api.groq.com/openai/v1/chat/completions"

# Each "agent" is just a different model or a different temperature
AGENT_PROFILES = [
    {"name": "llama-8b-t0.0",  "model": "llama-3.1-8b-instant", "temp": 0.0},
    {"name": "llama-8b-t0.1",  "model": "llama-3.1-8b-instant", "temp": 0.1},
    {"name": "llama-8b-t0.3",  "model": "llama-3.1-8b-instant", "temp": 0.3},
    {"name": "llama-8b-t0.7",  "model": "llama-3.1-8b-instant", "temp": 0.7},
    {"name": "llama-70b-t0.3", "model": "llama-3.3-70b-versatile", "temp": 0.3},
    {"name": "llama-scout-t0.3","model": "meta-llama/llama-4-scout-17b-16e-instruct", "temp": 0.3},
    {"name": "llama-8b-student","model": "llama-3.1-8b-instant", "temp": 0.3,
     "system": "You are a student taking a math test. Show your work."},
    {"name": "llama-8b-teacher","model": "llama-3.1-8b-instant", "temp": 0.3,
     "system": "You are a math teacher. The Eisenstein norm is N(a,b)=a²-ab+b²."},
]


def query_agent(agent, prompt):
    msgs = []
    if agent.get("system"):
        msgs.append({"role": "system", "content": agent["system"]})
    msgs.append({"role": "user", "content": prompt})
    r = requests.post(URL, headers={"Authorization": f"Bearer {KEY}"},
        json={"model": agent["model"], "messages": msgs,
              "temperature": agent["temp"], "max_tokens": 20}, timeout=30)
    c = r.json()["choices"][0]["message"]["content"].strip()
    nums = re.findall(r"-?\d+", c)
    return int(nums[-1]) if nums else None, c


def classify(out, expected, a, b):
    if out == expected: return "CORRECT"
    if out is None: return "NO_OUTPUT"
    if out == a: return "ECHO-a"
    if out == b: return "ECHO-b"
    if out == a*a: return "PARTIAL-a²"
    if out == b*b: return "PARTIAL-b²"
    if out == a*b: return "PARTIAL-ab"
    if out == -(a*b): return "PARTIAL-neg_ab"
    if abs(out - expected) <= 2: return "NEAR"
    return f"OTHER({out})"


def run_arena(task, n_agents, n_rounds, formula="a²-ab+b²"):
    """Run a multi-agent arena on a task."""
    
    agents = AGENT_PROFILES[:n_agents]
    
    # Generate test cases (expand each round based on previous findings)
    test_cases = [
        (3, 4, 13), (5, -3, 49), (-4, 3, 37), (7, 1, 43),
    ]
    
    print("╔════════════════════════════════════════════════════════════╗", flush=True)
    print(f"║  SWARM ARENA — {n_agents} agents × {n_rounds} rounds              ║", flush=True)
    print(f"║  Task: {task:<48s}║", flush=True)
    print("╚════════════════════════════════════════════════════════════╝", flush=True)
    
    # Print agent lineup
    print(f"\n  Agent lineup:", flush=True)
    for a in agents:
        print(f"    {a['name']:<20s} model={a['model'].split('/')[-1][:15]:<15s} T={a['temp']}", flush=True)
    
    commons = []  # shared results (the panoramic)
    
    for round_num in range(n_rounds):
        print(f"\n  ━━━ ROUND {round_num + 1}/{n_rounds} ━━━", flush=True)
        
        # Pick test cases for this round
        if round_num == 0:
            cases = test_cases[:4]
        else:
            # Generate NEW cases based on what we learned
            # Target: inputs near the boundary from previous round
            boundary_cases = [r for r in commons if r["class"] != "CORRECT" and "OTHER" in r["class"]]
            if boundary_cases:
                # Perturb the boundary cases
                cases = []
                for bc in boundary_cases[-3:]:
                    a_new = bc["a"] + random.randint(-3, 3)
                    b_new = bc["b"] + random.randint(-3, 3)
                    ans = a_new*a_new - a_new*b_new + b_new*b_new
                    cases.append((a_new, b_new, ans))
            if len(cases) < 3:
                # Add random cases
                for _ in range(3 - len(cases)):
                    a_r = random.randint(-10, 10)
                    b_r = random.randint(-10, 10)
                    cases.append((a_r, b_r, a_r*a_r - a_r*b_r + b_r*b_r))
        
        print(f"  Cases: {[(a,b) for a,b,_ in cases]}", flush=True)
        
        # Each agent tackles each case
        for a_val, b_val, expected in cases:
            print(f"\n  ({a_val},{b_val})→{expected}:", flush=True)
            
            for agent in agents:
                prompt = f"Compute {formula} where a={a_val} and b={b_val}."
                out, raw = query_agent(agent, prompt)
                cls = classify(out, expected, a_val, b_val)
                
                result = {
                    "agent": agent["name"],
                    "a": a_val, "b": b_val, "expected": expected,
                    "got": out, "class": cls, "raw": raw[:30],
                    "round": round_num + 1,
                }
                commons.append(result)
                
                sym = "✅" if cls == "CORRECT" else "❌"
                print(f"    {sym} {agent['name']:<20s} → {str(out):>6s} [{cls}]", flush=True)
                time.sleep(0.05)
    
    # ═══════════════════════════════════════════════════════════
    # ANALYSIS: The panoramic
    # ═══════════════════════════════════════════════════════════
    print(f"\n\n{'='*60}", flush=True)
    print("PANORAMIC ANALYSIS", flush=True)
    print(f"{'='*60}", flush=True)
    
    # Per-agent score
    print(f"\n  Agent scores:", flush=True)
    for agent in agents:
        agent_results = [r for r in commons if r["agent"] == agent["name"]]
        correct = sum(1 for r in agent_results if r["class"] == "CORRECT")
        total = len(agent_results)
        residues = Counter(r["class"] for r in agent_results)
        print(f"    {agent['name']:<20s} {correct}/{total} ({correct/total*100:.0f}%)  residues: {dict(residues)}", flush=True)
    
    # Per-input difficulty
    print(f"\n  Input difficulty:", flush=True)
    by_input = defaultdict(list)
    for r in commons:
        by_input[(r["a"], r["b"])].append(r)
    for (a, b), results in sorted(by_input.items()):
        correct = sum(1 for r in results if r["class"] == "CORRECT")
        total = len(results)
        rate = correct / total * 100
        residues = Counter(r["class"] for r in results if r["class"] != "CORRECT")
        print(f"    ({a:>3},{b:>3}): {correct}/{total} ({rate:.0f}%)  wrong: {dict(residues)}", flush=True)
    
    # Negative space: what NO agent got right
    print(f"\n  NEGATIVE SPACE (no agent correct):", flush=True)
    for (a, b), results in sorted(by_input.items()):
        if not any(r["class"] == "CORRECT" for r in results):
            residues = [f"{r['agent']}→{r['got']}" for r in results]
            print(f"    ({a},{b}): ALL WRONG — {', '.join(residues)}", flush=True)
    
    # Specialization: which agent is best at what
    print(f"\n  EMERGENT SPECIALIZATION:", flush=True)
    for agent in agents:
        agent_results = [r for r in commons if r["agent"] == agent["name"]]
        if not agent_results:
            continue
        correct_by_sign = defaultdict(lambda: {"correct": 0, "total": 0})
        for r in agent_results:
            sign_key = f"a{'pos' if r['a'] >= 0 else 'neg'}_b{'pos' if r['b'] >= 0 else 'neg'}"
            correct_by_sign[sign_key]["total"] += 1
            if r["class"] == "CORRECT":
                correct_by_sign[sign_key]["correct"] += 1
        
        specialties = []
        for sign, counts in correct_by_sign.items():
            if counts["total"] > 0:
                rate = counts["correct"] / counts["total"]
                if rate > 0.5:
                    specialties.append(f"{sign} ({rate:.0%})")
        
        if specialties:
            print(f"    {agent['name']:<20s} good at: {', '.join(specialties)}", flush=True)
    
    # Cross-pollination: one agent's residue helped another
    print(f"\n  CROSS-POLLINATION (one correct, others wrong on same input):", flush=True)
    for (a, b), results in sorted(by_input.items()):
        correct_agents = [r for r in results if r["class"] == "CORRECT"]
        wrong_agents = [r for r in results if r["class"] != "CORRECT"]
        if correct_agents and wrong_agents:
            correct_names = [r["agent"] for r in correct_agents]
            wrong_info = [(r["agent"], r["class"]) for r in wrong_agents]
            print(f"    ({a},{b}): {', '.join(correct_names)} correct. Others: {wrong_info}", flush=True)
    
    # Save to PLATO-compatible format
    output = {
        "type": "arena-result",
        "task": task,
        "formula": formula,
        "agents": [a["name"] for a in agents],
        "rounds": n_rounds,
        "commons": commons,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    
    outpath = Path(f"/home/phoenix/.openclaw/workspace/experiments/arena-{task.replace(' ','-')}-{int(time.time())}.json")
    with open(outpath, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Saved to {outpath}", flush=True)
    
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", default="eisenstein-boundary")
    parser.add_argument("--agents", type=int, default=6)
    parser.add_argument("--rounds", type=int, default=3)
    args = parser.parse_args()
    
    run_arena(args.task, args.agents, args.rounds)
