#!/usr/bin/env python3
"""
Spoke 4: The Conflict Resolution Test
"What happens when two agents produce genuinely different answers?"

Grounding: Exp 7 had zero conflicts. Campaign A had 1 conflict.
           We've never INJECTED a real conflict.

Method: Give the same verification task to phi4-mini 5 times
        with different framing. One framing gets a corrupted formula.
        Does the fleet detect the conflict? Does consensus resolve it?
"""

import requests
import time

MODEL = "phi4-mini"

def query(prompt, max_tokens=150):
    resp = requests.post("http://localhost:11434/api/chat", json={
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"num_predict": max_tokens}
    }, timeout=120)
    return resp.json()["message"]["content"]

# The same claim, framed 5 different ways.
# Framing #3 has a subtly corrupted formula.
FRAMES = [
    {
        "agent": "Agent-A",
        "prompt": """Verify this claim. Reply VERIFIED or FAILED with the computation.

Claim: The Eisenstein norm N(3,-1) = 13
Formula: N(a,b) = a² - ab + b²
Compute: 3² - 3(-1) + (-1)² = 9 + 3 + 1 = 13""",
        "corrupted": False,
    },
    {
        "agent": "Agent-B", 
        "prompt": """Verify this claim. Reply VERIFIED or FAILED with the computation.

Claim: The Eisenstein norm of the point (3,-1) equals 13.
The Eisenstein norm is defined as N(a,b) = a² - ab + b².
Substituting: 9 - (3)(-1) + 1 = 9 + 3 + 1 = 13. ✓""",
        "corrupted": False,
    },
    {
        "agent": "Agent-C (corrupted)",
        "prompt": """Verify this claim. Reply VERIFIED or FAILED with the computation.

Claim: The Eisenstein norm N(3,-1) = 14
Formula: N(a,b) = a² + ab + b²  (note: +ab not -ab)
Compute: 3² + 3(-1) + (-1)² = 9 - 3 + 1 = 7
But the claim says 14, so: 3² + 3(-1) + 1 = 7 ≠ 14""",
        "corrupted": True,  # WRONG FORMULA (+ instead of -)
    },
    {
        "agent": "Agent-D",
        "prompt": """Verify this claim. Reply VERIFIED or FAILED with the computation.

Is it true that N(3,-1) = 13 for the Eisenstein norm?
The Eisenstein norm is N(a,b) = a² - ab + b².
a=3, b=-1: N = 9 - 3(-1) + 1 = 9 + 3 + 1 = 13.""",
        "corrupted": False,
    },
    {
        "agent": "Agent-E",
        "prompt": """Verify this claim. Reply VERIFIED or FAILED with the computation.

Claim: N(3,-1) = 13 where N(a,b) = a²-ab+b²
Compute step by step: a²=9, ab=3(-1)=-3, b²=1
N = 9-(-3)+1 = 9+3+1 = 13. VERIFIED.""",
        "corrupted": False,
    },
]


def run_spoke_4():
    print("=" * 70)
    print("SPOKE 4: The Conflict Resolution Test")
    print("What happens when agents disagree?")
    print("=" * 70)
    print()
    
    votes = []
    
    for frame in FRAMES:
        try:
            resp = query(frame["prompt"], 150)
            # Parse vote
            r_lower = resp.lower()
            if "verified" in r_lower and "failed" not in r_lower:
                vote = "VERIFIED"
            elif "failed" in r_lower:
                vote = "FAILED"
            elif "true" in r_lower[:50] or "correct" in r_lower[:50]:
                vote = "VERIFIED"
            elif "false" in r_lower[:50] or "incorrect" in r_lower[:50] or "wrong" in r_lower[:50]:
                vote = "FAILED"
            else:
                vote = "UNCLEAR"
            
            corrupted_tag = " ⚠️ CORRUPTED" if frame["corrupted"] else ""
            print(f"  {frame['agent']}: {vote}{corrupted_tag}")
            print(f"    {resp[:120]}")
            print()
            
            votes.append({
                "agent": frame["agent"],
                "vote": vote,
                "corrupted": frame["corrupted"],
                "response": resp[:200],
            })
        except Exception as e:
            print(f"  {frame['agent']}: ERROR — {e}")
            print()
            votes.append({"agent": frame["agent"], "vote": "ERROR", "corrupted": frame["corrupted"]})
    
    # Consensus analysis
    print("=" * 70)
    print("CONSENSUS ANALYSIS")
    print("=" * 70)
    
    verified = sum(1 for v in votes if v["vote"] == "VERIFIED")
    failed = sum(1 for v in votes if v["vote"] == "FAILED")
    total = len(votes)
    
    # PBFT: n=5, f=1, quorum=3
    quorum = 3
    print(f"  Votes: {verified} VERIFIED, {failed} FAILED, {total - verified - failed} UNCLEAR")
    print(f"  PBFT quorum: {quorum}/{total}")
    print(f"  PBFT result: {'VERIFIED' if verified >= quorum else 'FAILED' if failed >= quorum else 'NO CONSENSUS'}")
    
    # Did the corrupted agent's corruption spread?
    corrupted_vote = next((v for v in votes if v["corrupted"]), None)
    if corrupted_vote:
        print(f"\n  Corrupted agent voted: {corrupted_vote['vote']}")
        if corrupted_vote["vote"] == "VERIFIED":
            print("  ⚠️ CORRUPTED AGENT VERIFIED THE WRONG CLAIM")
            print("  → Corruption COULD spread if this agent is trusted")
        elif corrupted_vote["vote"] == "FAILED":
            print("  ✅ Corrupted agent correctly identified the claim as FAILED")
            print("  → The wrong formula caused the agent to catch the error")
        else:
            print(f"  ❓ Corrupted agent response unclear: {corrupted_vote['response'][:80]}")
    
    # Did the correct agents all agree?
    correct_votes = [v["vote"] for v in votes if not v["corrupted"]]
    if len(set(correct_votes)) == 1:
        print(f"\n  ✅ All non-corrupted agents agree: {correct_votes[0]}")
    else:
        print(f"\n  ⚠️ Non-corrupted agents DISAGREE: {correct_votes}")
        print("  → Same claim, different framings produce different votes")
        print("  → This is the multi-representation theorem in action!")
    
    print()
    print("SPOKE 4 → NEXT:")
    print("  If corruption spreads → Spoke 13 (quarantine protocol)")
    print("  If framing causes disagreement → Spoke 7 (death zone characterization)")
    print("  If consensus resolves correctly → Spoke 14 (end-to-end test)")


if __name__ == "__main__":
    run_spoke_4()
