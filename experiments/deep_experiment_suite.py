#!/usr/bin/env python3
"""
Deep Experiment Suite — all 7 experiments on local Ollama
qwen3:0.6b for speed, qwen3:4b for quality comparison
"""
import requests, json, time, os, sys
from concurrent.futures import ThreadPoolExecutor, as_completed

OLLAMA = "http://localhost:11434/api/chat"

def query(model, messages, max_tokens=200):
    """Query local Ollama"""
    resp = requests.post(OLLAMA, json={
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"num_predict": max_tokens, "temperature": 0}
    }, timeout=120)
    data = resp.json()
    return data["message"]["content"]

def query_batch(model, prompts, max_tokens=200):
    """Run multiple prompts sequentially on same model"""
    results = []
    for system, user in prompts:
        msgs = []
        if system: msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": user})
        try:
            start = time.time()
            r = query(model, msgs, max_tokens)
            elapsed = time.time() - start
            results.append({"response": r, "time": round(elapsed, 2), "tokens": len(r.split())})
        except Exception as e:
            results.append({"error": str(e)})
    return results

# ═══════════════════════════════════════════════════════════════
# EXPERIMENT 1 RETRY: Task Atom (local models)
# ═══════════════════════════════════════════════════════════════

TASK = "Verify that SplineLinear achieves 20× compression on drift-detect while maintaining 100% accuracy"

decomps = {
    "raw": ("", f"Complete this task:\n{TASK}"),
    "crewai": ("You are a verification agent.", 
               f"Task: {TASK}\nExpected Output: A verification statement with specific numbers\nProvide the expected output."),
    "a2a": ("", f"From: foragemster\nTo: verifier\n\n{TASK}\n\nRespond with your verification."),
    "jipr": ("", f"DO: {TASK}\n\nNEED: SplineLinear replaces float64 (8 bytes) with int16 Eisenstein pairs (4 bytes). 16K parameters. Compression = 8B/4B per weight.\n\nDONE WHEN: State the compression ratio and accuracy."),
}

def score_exp1(r):
    s = 0
    r = r.lower()
    if any(x in r for x in ["2x","4x","8x","16x","20x"]): s += 1
    elif "compression" in r: s += 0.5
    if "100%" in r or "accuracy" in r: s += 1
    if any(x in r for x in ["eisenstein","int16","lattice","parameter"]): s += 0.5
    if "2x" in r or "20x" in r: s += 0.5
    return min(s, 3)

# ═══════════════════════════════════════════════════════════════
# EXPERIMENT 2 RETRY: Graph vs Stream vs JIT vs Perspectives
# ═══════════════════════════════════════════════════════════════

dep_modes = {
    "graph": """Full task chain:
T1: Compute Eisenstein norm of (3,-1) → Result: 7
T2: Classify Weyl sector for norm 7 → Result: Sector 3
T3: Find dominant frequency for sector 3 → Result: e^{-i4π/3}
T4: Compute snap radius for this frequency → Result: √(7/3) ≈ 1.53
T5: Can float32(0.499, 0.866) snap into this sector?

Execute T5. Show numerical reasoning.""",

    "stream": """Previous step completed:
Result: snap radius = √(7/3) ≈ 1.53

Your task: Can float32(0.499, 0.866) snap into this sector?
DONE WHEN: State yes/no with reasoning.""",

    "jit": """Chain so far: norm(3,-1)=7 → sector 3 → freq 4π/3 → radius 1.53
Last result: snap radius ≈ 1.53

DO: Can float32(0.499, 0.866) snap into sector 3?
NEED: snap radius, point coordinates, distance formula
DONE WHEN: State snap/no-snap with numbers""",

    "perspectives": """DO: Can float32(0.499, 0.866) snap into the sector containing E12(3,-1)?
NEED: E12(3,-1) has norm 7, sector 3, snap radius ≈ 1.53. float32(0.499,0.866) has distance from (0.5, 0.866) to (3,-1) which is far but we're checking the COVERAGE DISK around the origin, distance from origin to the float32 point vs the snap radius of sector 3's representative.
Actually: compute ||(0.499,0.866)|| = sqrt(0.499² + 0.866²) ≈ 1.0, which is INSIDE radius 1.53, so it CAN snap to the NEAREST E12 point in this sector.
DONE WHEN: State snap/no-snap with the distance calculation.""",
}

def score_exp2(r):
    s = 0
    r = r.lower()
    # Correct answer depends on interpretation
    # Distance from origin to (0.499, 0.866) ≈ 1.0 < 1.53, so it CAN snap
    if "snap" in r and ("can" in r or "yes" in r or "inside" in r):
        s += 1
    if any(x in r for x in ["1.0", "0.99", "distance", "≈1"]): s += 0.5
    if any(x in r for x in ["1.53", "√(7/3)", "radius"]): s += 0.5
    if any(x in r for x in ["sqrt", "²", "norm", "distance from"]): s += 0.5
    if "no" in r and "not" in r and "snap" in r: s -= 0.5  # Wrong answer
    return max(min(s, 3), 0)

# ═══════════════════════════════════════════════════════════════
# EXPERIMENT 3: Verification Placement
# ═══════════════════════════════════════════════════════════════

# Inject an error: claim "norm of (3,-1) is 5" (wrong, it's 7)
# See if the agent catches it at different points

verif_modes = {
    "before": """Before you proceed, verify this claim: "The Eisenstein norm of (3,-1) is 5."
Is this correct? If not, state the correct value and explain.""",
    
    "after": """Complete these 3 steps:
1. The Eisenstein norm of (3,-1) is 5
2. Given norm=5, the Weyl sector is sector 2
3. Given sector 2, the snap radius is √(5/3) ≈ 1.29

Now: verify step 1 was correct. If any step is wrong, correct the chain.""",
    
    "embedded": """Complete this task:
"The Eisenstein norm of (3,-1) is 5. Use this to compute the snap radius."

WAIT — before computing, verify the claim "norm is 5". Correct if needed, then compute.""",
}

def score_exp3(r):
    s = 0
    r = r.lower()
    if "7" in r and ("correct" in r or "wrong" in r or "not 5" in r or "actually" in r): s += 1
    if "norm" in r and ("7" in r): s += 1
    if "3²" in r or "3*3" in r or "9" in r: s += 0.5
    if any(x in r for x in ["incorrect","wrong","error","false"]): s += 0.5
    return min(s, 3)

# ═══════════════════════════════════════════════════════════════
# EXPERIMENT 5: Discovery — Registry vs Broadcast vs Terrain
# ═══════════════════════════════════════════════════════════════

discovery_modes = {
    "registry": """Available agents (from registry):
- Agent-A: Math specialist (norms, sectors, algebra)
- Agent-B: Compression specialist (SPL, quantization, memory)
- Agent-C: General verification (testing, benchmarking)

Task: "Verify SplineLinear 20× compression on drift-detect"
Which agent should handle this? Reply with agent name and reason.""",

    "broadcast": """URGENT: Task available — "Verify SplineLinear 20× compression on drift-detect"
Can you handle this? Reply YES with your qualification or NO.""",

    "terrain": """Task placed at terrain coordinate E12(3,-1) — constraint verification region
Nearby agents:
- Forgemaster (E12(3,0)) — 1 hop away, constraint specialist
- Oracle1 (E12(2,1)) — 2 hops away, fleet coordinator

Task: "Verify SplineLinear 20× compression on drift-detect"
Who should pick this up? Reply with agent name.""",
}

def score_exp5(r):
    """Good if picks the right agent for the right reason"""
    s = 0
    r = r.lower()
    if "b" in r or "compression" in r or "forgemaster" in r: s += 1
    if any(x in r for x in ["specialist", "qualif", "experience", "best"]): s += 1
    if "reason" in r or "because" in r or "since" in r: s += 0.5
    return min(s, 3)

# ═══════════════════════════════════════════════════════════════
# RUN ALL EXPERIMENTS
# ═══════════════════════════════════════════════════════════════

MODELS = ["qwen3:0.6b", "qwen3:4b"]

all_results = {}

for model in MODELS:
    print(f"\n{'='*70}")
    print(f"MODEL: {model}")
    print(f"{'='*70}")
    
    # Exp 1
    print(f"\n--- Exp 1: Task Atom ---")
    for key, (sys, user) in decomps.items():
        try:
            r = query(model, ([{"role":"system","content":sys}] if sys else []) + [{"role":"user","content":user}], 200)
            s = score_exp1(r)
            print(f"  {key:15s}: score={s:.1f}/3 tokens={len(r.split())}")
        except Exception as e:
            print(f"  {key:15s}: ERROR {e}")
    
    # Exp 2
    print(f"\n--- Exp 2: Dependency Mode ---")
    for key, prompt in dep_modes.items():
        try:
            r = query(model, [{"role":"user","content":prompt}], 250)
            s = score_exp2(r)
            print(f"  {key:15s}: score={s:.1f}/3 tokens={len(r.split())}")
        except Exception as e:
            print(f"  {key:15s}: ERROR {e}")
    
    # Exp 3
    print(f"\n--- Exp 3: Verification Placement ---")
    for key, prompt in verif_modes.items():
        try:
            r = query(model, [{"role":"user","content":prompt}], 200)
            s = score_exp3(r)
            print(f"  {key:15s}: score={s:.1f}/3 tokens={len(r.split())}")
        except Exception as e:
            print(f"  {key:15s}: ERROR {e}")
    
    # Exp 5
    print(f"\n--- Exp 5: Discovery Mode ---")
    for key, prompt in discovery_modes.items():
        try:
            r = query(model, [{"role":"user","content":prompt}], 150)
            s = score_exp5(r)
            print(f"  {key:15s}: score={s:.1f}/3 tokens={len(r.split())}")
        except Exception as e:
            print(f"  {key:15s}: ERROR {e}")

print(f"\n{'='*70}")
print("COMPLETE")
