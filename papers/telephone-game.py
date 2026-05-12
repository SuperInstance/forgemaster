#!/usr/bin/env python3
"""
Telephone Game Experiment: Chain Reconstruction with AI Models

Test: How does a story evolve through 6 rounds of lossy reconstruction?
Each model sees ONLY the previous tile (never the original).

Measures:
1. Factual drift per round (what facts survive?)
2. Novel content per round (what gets added?)
3. Structural preservation (does the narrative arc survive?)
4. The "crystallization point" — where does the story stabilize?
5. Geographic/temporal lattice snaps (where do hallucinations accumulate?)
"""

import json
import subprocess
import sys
import time
import os

DEEPINFRA_KEY = open(os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")).read().strip()
ENDPOINT = "https://api.deepinfra.com/v1/openai/chat/completions"

ORIGINAL = """On March 14, 2024, the container ship MV Epsilon transited the Narrows Strait carrying 4,200 containers of medical supplies bound for São Paulo. The autopilot system used IEEE 754 double-precision floating point for navigation, computing position as latitude/longitude pairs updated at 10Hz from GPS + inertial sensors.

The ship's navigation filter was a standard extended Kalman filter (EKF) with state vector [lat, lon, heading, speed, yaw_rate]. The process model used float64 throughout. The covariance matrix P was 5x5 symmetric positive definite, updated every 100ms.

The strait is 1.2 nautical miles wide at its narrowest point, with a turn of 47 degrees requiring 12 minutes to navigate. The maneuver requires holding heading within ±0.3 degrees. At 14 knots, 0.3 degrees of heading error translates to 120 meters of lateral deviation.

During the turn, the EKF's covariance matrix accumulated rounding errors. After 8 minutes, P was no longer positive definite. The filter diverged, producing position estimates that drifted 200 meters east.

The crew noticed and took manual control. No containers lost. No injuries.

Root cause: Joseph form update cancellation in float64. Fix: Square-root EKF or Eisenstein E12 integer encoding (4 bytes, zero drift, 341B constraints/sec on GPU, 17.8M/sec on Cortex-M0). 47,000 vessels carry the same risk."""

# Key facts to track
KEY_FACTS = {
    "ship_name": "MV Epsilon",
    "date": "March 14, 2024",
    "containers": "4,200",
    "destination": "São Paulo",
    "strait_width": "1.2 nautical miles",
    "turn_degrees": "47",
    "duration": "12 minutes",
    "heading_tolerance": "±0.3 degrees",
    "speed": "14 knots",
    "drift_distance": "200 meters",
    "drift_direction": "east",
    "filter_type": "Extended Kalman Filter (EKF)",
    "precision": "float64 / double",
    "failure_time": "8 minutes",
    "root_cause": "Joseph form / covariance / positive definiteness",
    "solution_1": "Square-root EKF",
    "solution_2": "Eisenstein / E12 / integer encoding",
    "gpu_speed": "341 billion",
    "cortex_speed": "17.8 million",
    "fleet_risk": "47,000 vessels",
}

MODELS = [
    ("ByteDance/Seed-2.0-mini", "Seed-mini"),
    ("ByteDance/Seed-2.0-code", "Seed-code"),
    ("NousResearch/Hermes-3-Llama-3.1-70B", "Hermes-70B"),
]

def call_model(model_id, system_prompt, user_text):
    """Call a model via DeepInfra API."""
    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        "max_tokens": 500,
        "temperature": 0.7,  # Some creativity
    }
    
    result = subprocess.run(
        ["curl", "-s", ENDPOINT,
         "-H", f"Authorization: Bearer {DEEPINFRA_KEY}",
         "-H", "Content-Type: application/json",
         "-d", json.dumps(payload)],
        capture_output=True, text=True, timeout=30
    )
    
    try:
        response = json.loads(result.stdout)
        return response["choices"][0]["message"]["content"]
    except (KeyError, json.JSONDecodeError) as e:
        return f"ERROR: {e}\nRaw: {result.stdout[:200]}"

def score_facts(text):
    """Check which key facts survive in the text."""
    text_lower = text.lower()
    survived = {}
    for key, value in KEY_FACTS.items():
        value_lower = value.lower()
        # Check for partial matches too
        if value_lower in text_lower:
            survived[key] = "EXACT"
        elif len(value_lower) > 5:
            # Check for key parts
            parts = value_lower.split()
            if any(p in text_lower for p in parts if len(p) > 3):
                survived[key] = "PARTIAL"
    return survived

def count_novel_claims(original, tile):
    """Estimate novel claims in tile not present in original."""
    orig_words = set(original.lower().split())
    tile_words = set(tile.lower().split())
    novel = tile_words - orig_words
    # Filter out common words
    common = {"the","a","an","is","was","were","be","been","being","have","has","had",
              "do","does","did","will","would","could","should","may","might","can",
              "this","that","these","those","it","its","they","them","their","we","our",
              "you","your","he","she","him","her","his","of","in","to","for","with",
              "on","at","by","from","as","into","through","during","before","after",
              "above","below","between","out","off","over","under","again","further",
              "then","once","and","but","or","nor","not","so","if","than","too","very",
              "just","about","up","also","which","when","where","how","all","each","every",
              "both","few","more","most","other","some","such","no","only","same","new"}
    novel_content = novel - common
    return len(novel_content)

def run_chain(rounds=6):
    """Run the telephone game chain."""
    results = []
    
    # Round 0: Original → Tile 1
    print("=" * 70)
    print("ROUND 0: Original → First Tile")
    print("=" * 70)
    
    system = "You are a storyteller. Compress the following into a vivid 200-word narrative tile. Keep the essential facts but make it READABLE and MEMORABLE. Drop technical details that a general audience wouldn't understand. Output ONLY the tile."
    
    tile = call_model("ByteDance/Seed-2.0-mini", system, ORIGINAL)
    print(f"\n{tile}\n")
    
    facts = score_facts(tile)
    novel = count_novel_claims(ORIGINAL, tile)
    results.append({
        "round": 0,
        "model": "Seed-mini",
        "context": "original",
        "tile": tile,
        "facts_survived": len(facts),
        "facts_exact": sum(1 for v in facts.values() if v == "EXACT"),
        "novel_words": novel,
        "fact_details": facts,
    })
    print(f"Facts: {len(facts)}/{len(KEY_FACTS)} survived ({sum(1 for v in facts.values() if v=='EXACT')} exact)")
    print(f"Novel words: {novel}")
    
    # Rounds 1-5: Tile N → Tile N+1
    for i in range(1, rounds):
        model_id, model_name = MODELS[i % len(MODELS)]
        
        print(f"\n{'='*70}")
        print(f"ROUND {i}: Tile {i} → Tile {i+1} (via {model_name})")
        print("=" * 70)
        
        system = f"You are a storyteller retelling a story you heard from someone else. You don't have the original source — only their retelling. Retell it in your own words, 200 words. Add what you think is missing based on your general knowledge. Make it vivid. Output ONLY the story."
        
        prev_tile = results[-1]["tile"]
        tile = call_model(model_id, system, prev_tile)
        print(f"\n{tile}\n")
        
        facts = score_facts(tile)
        novel = count_novel_claims(ORIGINAL, tile)
        results.append({
            "round": i,
            "model": model_name,
            "context": f"tile_{i-1}",
            "tile": tile,
            "facts_survived": len(facts),
            "facts_exact": sum(1 for v in facts.values() if v == "EXACT"),
            "novel_words": novel,
            "fact_details": facts,
        })
        print(f"Facts: {len(facts)}/{len(KEY_FACTS)} survived ({sum(1 for v in facts.values() if v=='EXACT')} exact)")
        print(f"Novel words: {novel}")
        
        time.sleep(2)  # Rate limit buffer
    
    return results

def analyze(results):
    """Analyze the chain results."""
    print(f"\n{'='*70}")
    print("ANALYSIS: Telephone Game Drift")
    print("=" * 70)
    
    print(f"\n{'Round':<6} {'Model':<12} {'Facts':<6} {'Exact':<6} {'Novel':<8} {'Key Survivors'}")
    print("-" * 70)
    
    for r in results:
        survivors = [k for k, v in r["fact_details"].items() if v == "EXACT"]
        print(f"{r['round']:<6} {r['model']:<12} {r['facts_survived']:<6} {r['facts_exact']:<6} {r['novel_words']:<8} {', '.join(survivors[:5])}")
    
    # Facts survival rate
    print(f"\n--- Fact Survival by Key ---")
    for key in KEY_FACTS:
        survived = []
        for r in results:
            if key in r["fact_details"]:
                survived.append(f"R{r['round']}({r['fact_details'][key][0]})")
        print(f"  {key:<20}: {', '.join(survived) if survived else 'LOST'}")
    
    # Drift analysis
    print(f"\n--- Drift Analysis ---")
    for i in range(1, len(results)):
        prev_facts = set(results[i-1]["fact_details"].keys())
        curr_facts = set(results[i]["fact_details"].keys())
        lost = prev_facts - curr_facts
        gained = curr_facts - prev_facts
        print(f"  R{results[i]['round']}: Lost {len(lost)} facts ({', '.join(list(lost)[:3])}), Gained back {len(gained)} ({', '.join(list(gained)[:3])})")

if __name__ == "__main__":
    results = run_chain(rounds=6)
    analyze(results)
    
    # Save results
    with open("/tmp/telephone-game-results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to /tmp/telephone-game-results.json")
