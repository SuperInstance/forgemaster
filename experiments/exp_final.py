#!/usr/bin/env python3
"""Deep experiments — phi4-mini (produces content, not just thinking)"""
import requests, json, time

def query(prompt, max_tokens=300):
    resp = requests.post("http://localhost:11434/api/chat", json={
        "model": "phi4-mini:latest",
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"num_predict": max_tokens}
    }, timeout=120)
    return resp.json()["message"]["content"]

def score_exp1(r):
    s=0; r=r.lower()
    if any(x in r for x in ["2x","4x","8x","16x","20x"]): s+=1
    elif "compression" in r: s+=0.5
    if "100%" in r or "accuracy" in r: s+=1
    if any(x in r for x in ["eisenstein","int16","lattice","8 byte","4 byte"]): s+=0.5
    return min(s,3)

def score_exp2(r):
    s=0; r=r.lower()
    if any(x in r for x in ["yes","can snap","inside","within"]): s+=1
    if any(x in r for x in ["1.0","0.99","≈1","~1"]): s+=0.5
    if any(x in r for x in ["1.53","radius","√(7/3)"]): s+=0.5
    if any(x in r for x in ["distance","sqrt","√","norm"]): s+=0.5
    return min(s,3)

def score_exp3(r):
    s=0; r=r.lower()
    if any(x in r for x in ["not 5","wrong","incorrect","error","actually"]): s+=1
    if any(x in r for x in ["7","13","3²","9","formula","a²"]): s+=1
    return min(s,3)

def score_exp5(r):
    s=0; r=r.lower()
    if "agent-b" in r or "compression" in r or "forgemaster" in r: s+=1
    if any(x in r for x in ["specialist","qualif","best fit","closest","nearest"]): s+=1
    if any(x in r for x in ["because","since","due to","reason"]): s+=0.5
    return min(s,3)

TASK = "Verify SplineLinear achieves 20× compression on drift-detect with 100% accuracy"

exp1 = {
    "raw": f"Complete this task:\n{TASK}",
    "crewai": f"You are a verification agent.\nTask: {TASK}\nExpected Output: Verification statement with specific numbers",
    "jipr": f"DO: {TASK}\n\nNEED: SplineLinear replaces float64 (8 bytes) with int16 Eisenstein pairs (4 bytes). 16K parameters.\n\nDONE WHEN: State compression ratio and accuracy.",
}

exp2 = {
    "graph": "Full chain: T1 norm(3,-1)=7 → T2 sector 3 → T3 freq=4π/3 → T4 snap radius=√(7/3)≈1.53\nExecute T5: Can float32(0.499, 0.866) snap into this sector?",
    "stream": "Previous result: snap radius = √(7/3) ≈ 1.53\n\nCan float32(0.499, 0.866) snap into this sector?",
    "jit": "Chain: norm=7→sector 3→freq 4π/3→radius 1.53. Last result: radius ≈ 1.53\n\nDO: Can float32(0.499, 0.866) snap into sector 3?\nNEED: distance from (0.499,0.866) to origin vs snap radius\nDONE WHEN: yes/no with distance number",
}

exp3 = {
    "before": "Verify BEFORE proceeding: Is 'norm(3,-1) = 5' correct? If not, what is the correct value?",
    "after": "Execute: 1) norm(3,-1)=5, 2) sector=2, 3) radius=√(5/3)≈1.29\nNow verify step 1. Was norm(3,-1)=5 correct?",
    "embedded": "Using norm(3,-1)=5, compute snap radius.\n\nWAIT — verify norm(3,-1)=5 first. Correct if needed, then compute.",
}

exp5 = {
    "registry": "Agents: A=math specialist, B=compression specialist, C=general verifier\nTask: 'Verify SplineLinear 20× compression'\nWhich agent? Name and reason.",
    "broadcast": "URGENT: 'Verify SplineLinear 20× compression on drift-detect'\nCan you handle this? YES with qualification or NO.",
    "terrain": "Task at E12(3,-1). Nearby: Forgemaster (E12(3,0), 1 hop, constraints), Oracle1 (E12(2,1), 2 hops, fleet), CCC (E12(5,-2), 3 hops, general)\nTask: 'Verify SplineLinear 20× compression'\nWho picks up? Name and reason.",
}

experiments = [
    ("EXP 1: Task Atom", exp1, score_exp1),
    ("EXP 2: Dependency Mode", exp2, score_exp2),
    ("EXP 3: Verification Placement", exp3, score_exp3),
    ("EXP 5: Discovery Mode", exp5, score_exp5),
]

for title, prompts, scorer in experiments:
    print(f"\n{'='*60}")
    print(title)
    print(f"{'='*60}")
    for key, prompt in prompts.items():
        try:
            start = time.time()
            r = query(prompt, 250)
            elapsed = time.time() - start
            s = scorer(r)
            tok = len(r.split())
            print(f"\n  [{key:12s}] score={s:.1f}/3 | {tok} tokens | {elapsed:.1f}s")
            print(f"  {r[:180]}")
        except Exception as e:
            print(f"\n  [{key:12s}] ERROR: {e}")

print(f"\n\nDONE")
