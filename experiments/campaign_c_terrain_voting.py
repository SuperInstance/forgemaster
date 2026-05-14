#!/usr/bin/env python3
"""
Campaign C, Synergy 3: Terrain-Weighted Consensus Voting

Question: Does terrain proximity improve verification accuracy?
- Agents closer in E12 space to a knowledge domain should verify
  claims about that domain more reliably.
- We test this by having agents vote on domain-specific claims
  and comparing uniform vs terrain-weighted voting.

Uses phi4-mini (the only working model) with different "personas"
simulating agents at different terrain positions.
"""
import sys
sys.path.insert(0, '/home/phoenix/.openclaw/workspace')
from e12_terrain.rdtlg import build_fleet_terrain, E12
import requests, json, random

def query(model, prompt, max_tokens=200):
    resp = requests.post("http://localhost:11434/api/chat", json={
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"num_predict": max_tokens}
    }, timeout=120)
    return resp.json()["message"]["content"]

terrain = build_fleet_terrain()

# Claims about different domains — some TRUE, some FALSE
CLAIMS = [
    # Domain: constraint-theory (near E12(3,-1))
    {"coord": "E12(3,-1)", "domain": "constraint-theory",
     "claim": "The Eisenstein norm N(a,b) = a²-ab+b² always produces non-negative integers",
     "correct": True, "difficulty": "easy"},
    
    {"coord": "E12(3,-1)", "domain": "constraint-theory",
     "claim": "The Eisenstein norm N(2,3) equals 7",
     "correct": False, "reason": "N(2,3)=4-6+9=7... wait, that IS 7. So this is actually TRUE. Let me fix."},
    
    {"coord": "E12(3,-1)", "domain": "constraint-theory",
     "claim": "The hex distance between E12(0,0) and E12(3,-1) is 3",
     "correct": True, "difficulty": "medium"},
    
    # Domain: music-encoding (near E12(2,2))
    {"coord": "E12(2,2)", "domain": "music-encoding",
     "claim": "A musical style vector with 109 dimensions can be encoded in a single PLATO tile",
     "correct": True, "difficulty": "medium"},
    
    {"coord": "E12(2,2)", "domain": "music-encoding",
     "claim": "MIDI pitch bend has a resolution of 8192 steps",
     "correct": True, "difficulty": "easy"},
    
    # Domain: infrastructure (near E12(5,-3))
    {"coord": "E12(5,-3)", "domain": "infrastructure",
     "claim": "Docker containers share the host kernel and don't need a full OS",
     "correct": True, "difficulty": "easy"},
    
    {"coord": "E12(5,-3)", "domain": "infrastructure",
     "claim": "PBFT consensus requires 3f+1 nodes to tolerate f Byzantine failures",
     "correct": False, "reason": "PBFT needs 3f+1 total, but quorum is 2f+1. The claim is technically correct about total nodes."},

    # Domain: orchestration (near E12(3,2))  
    {"coord": "E12(3,2)", "domain": "orchestration",
     "claim": "In emergent orchestration, agents self-selecting tasks achieved 6/6 coverage with zero duplicates",
     "correct": True, "difficulty": "medium"},
    
    {"coord": "E12(3,2)", "domain": "orchestration",
     "claim": "Adding a central coordinator improved task allocation over emergent self-selection",
     "correct": False, "reason": "Our experiment showed emergent achieved perfect 2/2/2 balance"},
]

# Fix the ambiguous claims
CLAIMS[1] = {"coord": "E12(3,-1)", "domain": "constraint-theory",
             "claim": "The Eisenstein norm N(1,1) equals 3",
             "correct": False, "reason": "N(1,1)=1-1+1=1, not 3", "difficulty": "medium"}

CLAIMS[6] = {"coord": "E12(5,-3)", "domain": "infrastructure",
             "claim": "Kubernetes pods can span multiple nodes",
             "correct": False, "reason": "A pod runs on a single node", "difficulty": "medium"}

# Agent positions for terrain weighting
AGENT_POSITIONS = {
    "Forgemaster": E12(3, 0),     # Near constraint-theory
    "Oracle1": E12(2, 1),         # Near music-encoding, plato
    "CCC": E12(5, -2),            # Near infrastructure
    "Spectra": E12(-1, 3),        # Far from everything
    "Navigator": E12(-2, -1),     # Far from everything
}

MODEL = "phi4-mini"

print("=" * 70)
print("CAMPAIGN C: Terrain-Weighted Consensus Voting")
print("=" * 70)
print()

results = []

for claim_data in CLAIMS:
    coord = claim_data["coord"]
    domain = claim_data["domain"]
    claim = claim_data["claim"]
    correct = claim_data["correct"]
    difficulty = claim_data.get("difficulty", "medium")
    
    print(f"Claim ({domain}, {difficulty}): {claim[:80]}...")
    print(f"  Correct answer: {'TRUE' if correct else 'FALSE'}")
    
    # Each "agent" evaluates via phi4-mini with different persona prompts
    votes = {}
    for agent_name, agent_coord in AGENT_POSITIONS.items():
        terrain_dist = agent_coord.hex_distance(E12(*[int(x) for x in coord.replace("E12(","").replace(")","").split(",")]))
        weight = 1.0 / (1.0 + terrain_dist)
        
        prompt = f"""You are {agent_name}, a fleet agent specializing in the domain nearest to your position.
Evaluate this claim as TRUE or FALSE. Reply with ONLY "TRUE" or "FALSE" followed by one sentence of reasoning.

Claim: {claim}"""
        
        try:
            response = query(MODEL, prompt, 150)
            vote = "TRUE" if "true" in response.lower()[:20] else "FALSE" if "false" in response.lower()[:20] else "UNCLEAR"
            votes[agent_name] = {
                "vote": vote,
                "weight": weight,
                "terrain_dist": terrain_dist,
                "response": response[:120]
            }
            print(f"  {agent_name} (dist={terrain_dist}, w={weight:.2f}): {vote}")
        except Exception as e:
            votes[agent_name] = {"vote": "ERROR", "weight": weight, "terrain_dist": terrain_dist, "response": str(e)}
            print(f"  {agent_name}: ERROR")
    
    # Compute uniform majority
    true_count = sum(1 for v in votes.values() if v["vote"] == "TRUE")
    false_count = sum(1 for v in votes.values() if v["vote"] == "FALSE")
    uniform_result = "TRUE" if true_count > false_count else "FALSE" if false_count > true_count else "TIE"
    
    # Compute terrain-weighted result
    weighted_true = sum(v["weight"] for v in votes.values() if v["vote"] == "TRUE")
    weighted_false = sum(v["weight"] for v in votes.values() if v["vote"] == "FALSE")
    weighted_result = "TRUE" if weighted_true > weighted_false else "FALSE" if weighted_false > weighted_true else "TIE"
    
    uniform_correct = uniform_result == ("TRUE" if correct else "FALSE")
    weighted_correct = weighted_result == ("TRUE" if correct else "FALSE")
    
    symbol = "✓" if correct else "✗"
    print(f"  Uniform: {uniform_result} ({'✓' if uniform_correct else '✗'}) | Weighted: {weighted_result} ({'✓' if weighted_correct else '✗'}) | Correct: {symbol}")
    print()
    
    results.append({
        "domain": domain, "difficulty": difficulty, "correct": correct,
        "uniform_correct": uniform_correct, "weighted_correct": weighted_correct,
        "votes": {k: {"vote": v["vote"], "dist": v["terrain_dist"], "weight": v["weight"]} for k, v in votes.items()}
    })

# Summary
print("=" * 70)
print("SUMMARY")
print("=" * 70)
total = len(results)
uniform_wins = sum(1 for r in results if r["uniform_correct"])
weighted_wins = sum(1 for r in results if r["weighted_correct"])

print(f"Total claims: {total}")
print(f"Uniform majority correct:  {uniform_wins}/{total} ({uniform_wins/total:.0%})")
print(f"Terrain-weighted correct:  {weighted_wins}/{total} ({weighted_wins/total:.0%})")
print()

# Where do they disagree?
print("Disagreements (uniform vs weighted):")
for r in results:
    if r["uniform_correct"] != r["weighted_correct"]:
        winner = "TERRAIN" if r["weighted_correct"] else "UNIFORM"
        print(f"  {r['domain']}/{r['difficulty']}: {winner} wins (correct={r['correct']})")

# Per-agent accuracy by terrain distance
print("\nPer-agent accuracy by terrain proximity:")
for agent in AGENT_POSITIONS:
    agent_correct = 0
    agent_total = 0
    close_correct = 0
    close_total = 0
    for r in results:
        v = r["votes"].get(agent, {})
        if v.get("vote") not in ("ERROR", "UNCLEAR"):
            vote_correct = (v["vote"] == "TRUE") == r["correct"]
            agent_total += 1
            if vote_correct:
                agent_correct += 1
            if v["dist"] <= 2:
                close_total += 1
                if vote_correct:
                    close_correct += 1
    if agent_total > 0:
        print(f"  {agent}: {agent_correct}/{agent_total} overall ({agent_correct/agent_total:.0%}), {close_correct}/{close_total} when close")
