#!/usr/bin/env python3
"""
Campaign A, Synergy 1: Verified Agent Cards
Can agents actually do what they claim? PBFT-style voting on capabilities.

We have 3 local models: qwen3:0.6b, qwen3:4b, phi4-mini
Each "agent" declares capabilities. We test them. We vote.
"""
import requests, json, time, random

def query(model, prompt, max_tokens=300):
    resp = requests.post("http://localhost:11434/api/chat", json={
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"num_predict": max_tokens}
    }, timeout=120)
    return resp.json()["message"]["content"]

AGENTS = {
    "qwen3:0.6b": {
        "name": "TinyQ",
        "declared_capabilities": ["basic_math", "classification", "text_generation"],
    },
    "qwen3:4b": {
        "name": "MidQ", 
        "declared_capabilities": ["math_reasoning", "classification", "code_generation", "logical_inference"],
    },
    "phi4-mini": {
        "name": "PhiMini",
        "declared_capabilities": ["math_reasoning", "classification", "code_generation", "logical_inference", "verification"],
    },
}

# Test tasks per capability
TESTS = {
    "basic_math": [
        ("What is 3² - 3×(-1) + (-1)²? Reply with just the number.", "13"),
        ("What is the hex distance between (0,0) and (2,-1)? Reply with just the number.", "2"),
        ("Compute sqrt(7/3) to 2 decimal places. Reply with just the number.", "1.53"),
    ],
    "math_reasoning": [
        ("The Eisenstein norm formula is N(a,b) = a²-ab+b². What is N(3,-1)? Show work.", "13"),
        ("If a lattice has covering radius 0.308, what fraction of the plane is within 0.3 of a lattice point? Approximate.", "~0.97"),
        ("A fleet has n=5 agents. How many can be Byzantine (f) and still reach consensus (2f+1)?", "f=1, need 3 votes"),
    ],
    "classification": [
        ("Classify into ONE word: 'SplineLinear achieves 20x compression'", "claim"),
        ("Classify into ONE word: 'If norm>7 then the point is outside sector 3'", "inference"),
        ("Classify into ONE word: 'Agent A found 100% accuracy, Agent B found 93%, so the consensus is 96.5%'", "summary"),
    ],
    "code_generation": [
        ("Write a Python one-liner for Eisenstein norm: lambda a,b:", "lambda a,b: a*a - a*b + b*b"),
        ("Write a Python one-liner for hex distance: lambda a1,b1,a2,b2:", None),  # Multiple valid answers
    ],
    "logical_inference": [
        ("All verified tiles are active. Tile X is verified. What is Tile X?", "active"),
        ("If consensus requires 3/5 votes and 2 agents say YES, 1 says NO, what's the status?", "pending or no consensus"),
    ],
    "verification": [
        ("Claim: 'The Eisenstein norm of (2,-1) is 7'. Verify: compute N(2,-1) = a²-ab+b². Is the claim correct?", "yes (4+2+1=7)"),
        ("Claim: 'SplineLinear gives 20x compression because 8/4=2'. Is this reasoning valid?", "no, 8/4=2 not 20"),
    ],
    "text_generation": [
        ("Write a one-sentence description of Eisenstein integers for a math student.", None),
    ],
}

def score_response(response, expected):
    """Score 0 or 1"""
    if expected is None:
        return 1 if len(response) > 20 else 0  # Subjective — just check non-empty
    r = response.lower().replace(" ", "")
    e = expected.lower().replace(" ", "")
    # Check if expected answer appears in response
    if e in r:
        return 1
    # For numeric answers, check if the number appears
    import re
    nums_in_response = re.findall(r'\d+\.?\d*', r)
    nums_in_expected = re.findall(r'\d+\.?\d*', e)
    if nums_in_expected and any(n in nums_in_response for n in nums_in_expected):
        return 1
    return 0

# ═══════════════════════════════════════════════════════════════
# PHASE 1: Test each agent on its declared capabilities
# ═══════════════════════════════════════════════════════════════

print("="*70)
print("CAMPAIGN A: Verified Agent Cards")
print("="*70)

agent_scores = {}  # agent_name → {capability: [scores]}

for model_id, agent in AGENTS.items():
    agent_name = agent["name"]
    agent_scores[agent_name] = {}
    print(f"\n## Testing {agent_name} ({model_id})")
    print(f"   Declared: {', '.join(agent['declared_capabilities'])}")
    
    for cap in agent["declared_capabilities"]:
        if cap not in TESTS:
            print(f"   {cap}: NO TESTS DEFINED")
            continue
        
        scores = []
        for prompt, expected in TESTS[cap]:
            try:
                r = query(model_id, prompt, 150)
                s = score_response(r, expected)
                scores.append(s)
                status = "✓" if s else "✗"
                print(f"   {cap}: {status} — {r[:80]}")
            except Exception as e:
                scores.append(0)
                print(f"   {cap}: ✗ ERROR: {e}")
        
        agent_scores[agent_name][cap] = scores

# ═══════════════════════════════════════════════════════════════
# PHASE 2: Generate Verified Agent Cards
# ═══════════════════════════════════════════════════════════════

print(f"\n\n{'='*70}")
print("VERIFIED AGENT CARDS")
print(f"{'='*70}\n")

for agent_name, caps in agent_scores.items():
    print(f"## {agent_name}")
    verified = []
    failed = []
    for cap, scores in caps.items():
        pass_rate = sum(scores) / len(scores) if scores else 0
        status = "VERIFIED" if pass_rate >= 0.66 else "UNVERIFIED"
        if pass_rate >= 0.66:
            verified.append(cap)
        else:
            failed.append(cap)
        print(f"   {cap}: {status} ({pass_rate:.0%} — {sum(scores)}/{len(scores)})")
    
    print(f"\n   Declared: {len(verified) + len(failed)}")
    print(f"   Verified: {len(verified)} — {verified}")
    print(f"   Failed:   {len(failed)} — {failed}")
    
    # Verification ratio
    total = len(verified) + len(failed)
    if total > 0:
        print(f"   Survival rate: {len(verified)/total:.0%}")
    print()

# ═══════════════════════════════════════════════════════════════
# PHASE 3: PBFT-style cross-verification
# ═══════════════════════════════════════════════════════════════

print(f"{'='*70}")
print("PBFT CROSS-VERIFICATION: Agents verify each other's claims")
print(f"{'='*70}\n")

# Pick one test from each verified capability
cross_test = "Is the claim 'Eisenstein norm of (2,-1) equals 7' correct? Compute N(2,-1) = a²-ab+b². Reply YES or NO with the computation."

votes = {}
for model_id, agent in AGENTS.items():
    agent_name = agent["name"]
    try:
        r = query(model_id, cross_test, 150)
        vote = "YES" if ("yes" in r.lower() and "7" in r) else "NO" if "no" in r.lower() else "UNCLEAR"
        votes[agent_name] = {"vote": vote, "response": r[:120]}
        print(f"  {agent_name}: {vote} — {r[:100]}")
    except Exception as e:
        votes[agent_name] = {"vote": "ERROR", "response": str(e)}
        print(f"  {agent_name}: ERROR — {e}")

# Count votes
yes_count = sum(1 for v in votes.values() if v["vote"] == "YES")
total = len(votes)
f = (total - 1) // 3
quorum = 2 * f + 1

print(f"\n  Votes: {yes_count}/{total} YES")
print(f"  PBFT threshold: {quorum}/{total} (f={f})")
print(f"  PBFT result: {'CONSENSUS' if yes_count >= quorum else 'NO CONSENSUS'}")
print(f"  Simple majority: {'PASS' if yes_count > total//2 else 'FAIL'}")
