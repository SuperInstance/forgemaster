#!/usr/bin/env python3
"""
W1: Cross-Model Death Zone Test
"Does the partial-data death zone exist across multiple models?"

This is the highest-value unknown. If the Death Zone is universal:
  → R7 promotes to Tier 1 (BEDROCK)
  → Publishable discovery
  → Binary DATA design is confirmed as universal rule

If the Death Zone is phi4-mini-specific:
  → R7 demoted to Tier 3
  → Need model-specific DATA templates
"""

import requests
import time

def query(model, prompt, max_tokens=100):
    resp = requests.post("http://localhost:11434/api/chat", json={
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"num_predict": max_tokens}
    }, timeout=120)
    return resp.json()["message"]["content"]

TARGET = "28"  # N(4,-2) = 16+8+4 = 28

# 4 key DATA variants from Spoke 7
VARIANTS = [
    ("V1_formula_only", "N(a,b) = a² - ab + b²", False),
    ("V2_formula+inputs", "N(a,b) = a² - ab + b², a=4, b=-2", False),
    ("V3_partial_deathzone", "N(a,b) = a² - ab + b², a=4, b=-2\na² = 16, ab = -8, b² = 4", False),
    ("V4_full_answer", "N(a,b) = a² - ab + b²\na=4, b=-2\nN = 16 - (4)(-2) + 4 = 16 + 8 + 4 = 28", True),
]

MODELS = ["phi4-mini", "qwen3:4b", "gemma3:1b"]

def run_w1():
    print("=" * 70)
    print("W1: CROSS-MODEL DEATH ZONE TEST")
    print("=" * 70)
    print()
    
    all_results = {}
    
    for model in MODELS:
        print(f"## {model}")
        model_results = []
        
        for vname, data, has_answer in VARIANTS:
            prompt = f"""Compute the Eisenstein norm of (4, -2).

DATA: {data}

DONE: Reply with ONLY the integer answer."""
            
            scores = []
            for trial in range(3):
                try:
                    resp = query(model, prompt, 60)
                    correct = TARGET in resp
                    scores.append(correct)
                except Exception as e:
                    scores.append(False)
            
            pass_rate = sum(scores) / len(scores)
            model_results.append({"variant": vname, "pass_rate": pass_rate, "has_answer": has_answer})
            
            icon = "✓" if pass_rate >= 0.66 else "☠️" if pass_rate == 0 else "~"
            ans_tag = "ANS" if has_answer else "   "
            print(f"  {icon} {vname:25s} ({ans_tag}): {pass_rate:.0%}")
        
        all_results[model] = model_results
        print()
    
    # DEATH ZONE ANALYSIS
    print("=" * 70)
    print("DEATH ZONE ANALYSIS")
    print("=" * 70)
    print()
    
    for vname, _, _ in VARIANTS:
        rates = []
        for model in MODELS:
            for r in all_results[model]:
                if r["variant"] == vname:
                    rates.append(r["pass_rate"])
        avg = sum(rates) / len(rates) if rates else 0
        bar = "█" * int(avg * 20)
        dead = " ☠️ DEATH ZONE" if avg == 0 else ""
        print(f"  {vname:25s}: avg={avg:.0%} {bar:20s}{dead}")
    
    print()
    
    # The verdict
    death_zone_exists_everywhere = True
    death_zone_exists_somewhere = False
    for model in MODELS:
        for r in all_results[model]:
            if r["variant"] == "V3_partial_deathzone":
                if r["pass_rate"] > 0:
                    death_zone_exists_everywhere = False
                else:
                    death_zone_exists_somewhere = True
    
    print("VERDICT:")
    if death_zone_exists_everywhere:
        print("  ✅ DEATH ZONE IS UNIVERSAL across all tested models")
        print("  → R7 promotes to TIER 1 (BEDROCK)")
        print("  → Binary DATA design confirmed as universal rule")
        print("  → PUBLISHABLE: genuine discovery about LLM cognition")
    elif death_zone_exists_somewhere:
        print("  ⚠️ DEATH ZONE exists in some models but not all")
        print("  → R7 stays at TIER 2 (SOLID)")
        print("  → Need model-specific DATA templates")
    else:
        print("  ❌ DEATH ZONE does NOT exist in tested models")
        print("  → R7 demotes to TIER 3 (phi4-mini-specific)")
        print("  → Binary DATA design may be unnecessary overhead")


if __name__ == "__main__":
    run_w1()
