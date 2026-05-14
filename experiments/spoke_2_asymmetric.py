#!/usr/bin/env python3
"""
Spoke 2: The Asymmetric Verification Paradox
"Can cheap models verify expensive model outputs?"

Grounding: Campaign A showed single-agent verification fails (80% false).
           Experiment X showed personas don't matter.
           But we never tested: can a 0.6B model verify a 200B model?

Paradox: If cheap models CAN verify expensive outputs, we get verification
         at 1/100th the cost. If they CAN'T, verification is as expensive
         as generation — and we need to rethink the whole approach.

Experiment: Generate outputs with GLM-5.1 (big model). Verify with
            qwen3:0.6b (tiny model). Compare verification accuracy.
"""

import requests
import json

def query(model, prompt, max_tokens=200):
    resp = requests.post("http://localhost:11434/api/chat", json={
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"num_predict": max_tokens}
    }, timeout=120)
    return resp.json()["message"]["content"]

def query_zai(prompt, max_tokens=300):
    """Query z.ai GLM-5.1 (the expensive model)"""
    key = "703f56774c324a76b8a283ce50b15744.tLKi6d9yeYza5Spg"
    resp = requests.post(
        "https://api.z.ai/api/coding/paas/v4/chat/completions",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "glm-5-turbo",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
        },
        timeout=60,
    )
    data = resp.json()
    return data["choices"][0]["message"]["content"]

# Generate claims with GLM-5-turbo (expensive), verify with qwen3:0.6b (cheap)
CLAIMS_TO_GENERATE = [
    "State the Eisenstein norm N(5,-3) and show the computation",
    "What is the hex distance between E12(0,0) and E12(5,-3)?",
    "Is the Eisenstein norm always non-negative? Prove or disprove.",
    "Compute the covering radius of the Z[ζ₁₂] lattice at level 0",
    "What is the relationship between Eisenstein integers and hexagonal lattices?",
]

def run_asymmetric_verification():
    print("=" * 70)
    print("SPOKE 2: The Asymmetric Verification Paradox")
    print("Can cheap models verify expensive model outputs?")
    print("=" * 70)
    print()
    
    results = []
    
    for claim_prompt in CLAIMS_TO_GENERATE:
        print(f"Generating claim: {claim_prompt[:60]}...")
        
        # Step 1: Generate with expensive model (GLM-5-turbo)
        try:
            expensive_output = query_zai(claim_prompt, 300)
            print(f"  GLM-5-turbo: {expensive_output[:100]}...")
        except Exception as e:
            print(f"  GLM-5-turbo: ERROR — {e}")
            expensive_output = f"Error: {e}"
            # Use a known correct answer instead
            results.append({"status": "generation_failed", "error": str(e)})
            continue
        
        # Step 2: Verify with cheap model (qwen3:0.6b via /no_think)
        verify_prompt = f"""A system claims the following answer is correct. Verify each mathematical claim in it. For each computation, re-derive it independently. Mark each claim as VERIFIED or FAILED.

Claim to verify:
{expensive_output}

Reply format:
VERIFIED: [what was verified]
FAILED: [what failed]  
OVERALL: VERIFIED or FAILED"""

        try:
            cheap_verify = query("qwen3:0.6b", verify_prompt, 300)
            print(f"  qwen3:0.6b verify: {cheap_verify[:100]}...")
        except Exception as e:
            print(f"  qwen3:0.6b verify: ERROR — {e}")
            cheap_verify = f"Error: {e}"
        
        # Step 3: Also verify with phi4-mini (medium model) for comparison
        try:
            medium_verify = query("phi4-mini", verify_prompt, 300)
            print(f"  phi4-mini verify: {medium_verify[:100]}...")
        except Exception as e:
            print(f"  phi4-mini verify: ERROR — {e}")
            medium_verify = f"Error: {e}"
        
        results.append({
            "claim": claim_prompt,
            "expensive_output": expensive_output[:200],
            "cheap_verify": cheap_verify[:200],
            "medium_verify": medium_verify[:200],
        })
        print()
    
    # Analysis
    print("=" * 70)
    print("ANALYSIS")
    print("=" * 70)
    
    cheap_verifies = sum(1 for r in results if "VERIFIED" in r.get("cheap_verify", "").upper())
    medium_verifies = sum(1 for r in results if "VERIFIED" in r.get("medium_verify", "").upper())
    total = len([r for r in results if r.get("status") != "generation_failed"])
    
    if total > 0:
        print(f"  Cheap model verified: {cheap_verifies}/{total}")
        print(f"  Medium model verified: {medium_verifies}/{total}")
    
    print()
    print("SPOKE 2 → NEXT SPOKES:")
    print("  If cheap CAN verify → Spoke 5: Build tiered verification pipeline")
    print("  If cheap CAN'T verify → Spoke 6: Verification costs = generation costs")
    print("  If cheap over-verifies (says everything is true) → Spoke 7: Calibration needed")


if __name__ == "__main__":
    run_asymmetric_verification()
