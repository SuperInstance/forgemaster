#!/usr/bin/env python3
"""
Campaign D, Synergy 5: FLUX-ISA as Universal Task Encoding

Question: Can mathematical intent encoded as FLUX bytecode be 
decoded and executed by agents? Compare FLUX vs natural language.

FLUX has 7 opcodes: FOLD, ROUND, RESIDUAL, MINIMUM, SNAP, ENCODE, DECODE
Each is 2 bytes (opcode + operand). A full task is 16 bytes max.

This tests whether compact mathematical representation can REPLACE
natural language for certain classes of fleet tasks.
"""

import requests, json, time

def query(model, prompt, max_tokens=200):
    resp = requests.post("http://localhost:11434/api/chat", json={
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"num_predict": max_tokens}
    }, timeout=120)
    return resp.json()["message"]["content"]

# FLUX opcodes
OPCODES = {
    "FOLD": 0x01,    # Fold value into lattice sector
    "ROUND": 0x02,   # Round to nearest Eisenstein integer
    "RESIDUAL": 0x03,# Compute residual (value - rounded)
    "MINIMUM": 0x04, # Find minimum in neighborhood
    "SNAP": 0x05,    # Snap to dodecet boundary
    "ENCODE": 0x06,  # Encode as FLUX bytecode
    "DECODE": 0x07,  # Decode FLUX bytecode
}

# 10 tasks — each expressed as both FLUX and natural language
TASKS = [
    {
        "name": "snap-to-lattice",
        "flux": "SNAP(3.7, -1.2) → find nearest Eisenstein integer",
        "flux_bytes": [0x05, 0x03, 0x05, 0x01],  # SNAP(3), SNAP(1) — approximate
        "natural": "Find the nearest Eisenstein integer to the point (3.7, -1.2). An Eisenstein integer is a pair (a,b) where a and b are integers. Use the norm N(a,b) = a² - ab + b² to find the closest.",
        "verify": lambda r: "4" in r and ("-1" in r or "-2" in r),  # E12(4,-1) or E12(4,-2)
        "difficulty": "easy",
    },
    {
        "name": "compute-norm",
        "flux": "FOLD(3,-1) → N(a,b) = a²-ab+b²",
        "flux_bytes": [0x01, 0x03, 0x01, 0x01],
        "natural": "Compute the Eisenstein norm N(3,-1) = a² - ab + b². Show the calculation.",
        "verify": lambda r: "13" in r,
        "difficulty": "easy",
    },
    {
        "name": "find-residual",
        "flux": "RESIDUAL((3.7,-1.2), SNAP) → (3.7, -1.2) - nearest_integer",
        "flux_bytes": [0x03, 0x03, 0x03, 0x01],
        "natural": "The point (3.7, -1.2) is snapped to the nearest Eisenstein integer. Find the residual (the difference between the original point and the snapped point).",
        "verify": lambda r: ("0.3" in r or "0.2" in r or "-0.2" in r),  # Some residual
        "difficulty": "medium",
    },
    {
        "name": "hex-distance",
        "flux": "MINIMUM(DIST((0,0),(3,-1))) → hop count",
        "flux_bytes": [0x04, 0x03, 0x04, 0x01],
        "natural": "Calculate the hex distance (hop count) between Eisenstein integers (0,0) and (3,-1). The hex distance is max(|da|, |db|, |da+db|).",
        "verify": lambda r: "3" in r,
        "difficulty": "easy",
    },
    {
        "name": "covering-radius",
        "flux": "ROUND(sector_check) → is (0.5, 0.3) within covering radius of nearest lattice point?",
        "flux_bytes": [0x02, 0x05, 0x02, 0x03],
        "natural": "The E12 lattice has covering radius 0.308. Is the point (0.5, 0.3) within the covering radius of its nearest lattice point? Compute the distance to the nearest Eisenstein integer and compare to 0.308.",
        "verify": lambda r: ("no" in r.lower() or "not" in r.lower() or "outside" in r.lower()),  # Distance > 0.308
        "difficulty": "hard",
    },
    {
        "name": "encode-coord",
        "flux": "ENCODE((3,-1)) → FLUX bytecode representation",
        "flux_bytes": [0x06, 0x03, 0x06, 0x01],
        "natural": "Encode the Eisenstein coordinate (3, -1) as a compact byte representation. Each coordinate is a signed byte (-128 to 127). Write the result as hexadecimal.",
        "verify": lambda r: ("03" in r.lower() or "ff" in r.lower() or "0x" in r.lower()),
        "difficulty": "easy",
    },
    {
        "name": "multi-step",
        "flux": "SNAP(2.8,1.3) → FOLD → ROUND → RESIDUAL",
        "flux_bytes": [0x05, 0x02, 0x01, 0x02, 0x02, 0x01, 0x03, 0x00],
        "natural": "Take the point (2.8, 1.3). Step 1: Snap it to the nearest Eisenstein integer. Step 2: Compute the norm of the result. Step 3: Round the norm to the nearest integer. Step 4: Compute the residual (difference from exact). Show each step.",
        "verify": lambda r: ("7" in r or "9" in r),  # N(3,1)=7 or N(3,2)=7 or N(2,1)=3
        "difficulty": "medium",
    },
    {
        "name": "decode-bytes",
        "flux": "DECODE([0x05, 0x03, 0x05, 0x01]) → interpret FLUX bytecode",
        "flux_bytes": [0x07, 0x00, 0x07, 0x00],
        "natural": "Decode this sequence of operations on Eisenstein integers: [SNAP(3), SNAP(1)]. What does this instruction sequence do? What is the mathematical result?",
        "verify": lambda r: ("snap" in r.lower() or "3" in r),  # Should mention SNAP or the value 3
        "difficulty": "hard",
    },
    {
        "name": "min-neighborhood",
        "flux": "MINIMUM(neighbors(3,-1)) → smallest norm neighbor",
        "flux_bytes": [0x04, 0x00, 0x04, 0x00],
        "natural": "Find the Eisenstein integer neighbor of (3,-1) with the smallest norm. The six neighbors are (4,-1), (2,-1), (3,0), (3,-2), (4,-2), (2,0). Compute N(a,b) = a²-ab+b² for each and find the minimum.",
        "verify": lambda r: ("3" in r),  # (2,0) has norm 4, (3,0) has norm 9, etc. Minimum might vary by computation
        "difficulty": "medium",
    },
    {
        "name": "classify-claim",
        "flux": "ROUND(claim_type) → classify: CAUSAL/INFERENCE/SUMMARY",
        "flux_bytes": [0x02, 0x00, 0x02, 0x00],
        "natural": "Classify this reasoning type: 'If the lattice spacing decreases, the covering radius must also decrease, because tighter packing covers more space.' Choose from: CAUSAL, INFERENCE, SUMMARY, or COMPARISON.",
        "verify": lambda r: any(w in r.upper() for w in ["CAUSAL", "INFERENCE"]),
        "difficulty": "medium",
    },
]

MODEL = "phi4-mini"

print("=" * 70)
print("CAMPAIGN D: FLUX-ISA vs Natural Language Task Encoding")
print("=" * 70)
print()

results = []

for task in TASKS:
    print(f"Task: {task['name']} ({task['difficulty']})")
    
    # FLUX version
    flux_prompt = f"""Execute this FLUX instruction:
{task['flux']}

FLUX opcodes: FOLD=fold into sector, ROUND=round to Eisenstein int, RESIDUAL=compute residual, MINIMUM=find minimum, SNAP=snap to lattice, ENCODE=encode bytes, DECODE=decode bytes.

Execute and show the result."""
    
    # Natural language version
    nat_prompt = task['natural']
    
    # Execute both
    try:
        flux_resp = query(MODEL, flux_prompt, 200)
        flux_success = task['verify'](flux_resp)
    except Exception as e:
        flux_resp = f"ERROR: {e}"
        flux_success = False
    
    try:
        nat_resp = query(MODEL, nat_prompt, 200)
        nat_success = task['verify'](nat_resp)
    except Exception as e:
        nat_resp = f"ERROR: {e}"
        nat_success = False
    
    flux_s = "✓" if flux_success else "✗"
    nat_s = "✓" if nat_success else "✗"
    
    print(f"  FLUX: {flux_s} — {flux_resp[:80]}")
    print(f"  NAT:  {nat_s} — {nat_resp[:80]}")
    print()
    
    results.append({
        "task": task['name'],
        "difficulty": task['difficulty'],
        "flux_success": flux_success,
        "nat_success": nat_success,
    })

# Summary
print("=" * 70)
print("SUMMARY")
print("=" * 70)
flux_total = sum(1 for r in results if r['flux_success'])
nat_total = sum(1 for r in results if r['nat_success'])
print(f"FLUX success:  {flux_total}/{len(results)} ({flux_total/len(results):.0%})")
print(f"Natural success: {nat_total}/{len(results)} ({nat_total/len(results):.0%})")
print()

# By difficulty
for diff in ['easy', 'medium', 'hard']:
    subset = [r for r in results if r['difficulty'] == diff]
    if subset:
        f = sum(1 for r in subset if r['flux_success'])
        n = sum(1 for r in subset if r['nat_success'])
        print(f"  {diff}: FLUX {f}/{len(subset)}, NAT {n}/{len(subset)}")

print()
print("Tasks where FLUX won:")
for r in results:
    if r['flux_success'] and not r['nat_success']:
        print(f"  {r['task']}")

print("Tasks where NAT won:")
for r in results:
    if r['nat_success'] and not r['flux_success']:
        print(f"  {r['task']}")
PYEOF