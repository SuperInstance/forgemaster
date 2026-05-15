#!/usr/bin/env python3
"""Quick mechanical reasoning experiment — logging camp hydraulic system."""
import json, os, re, time, requests
from dataclasses import dataclass, asdict
from typing import Optional, List, Tuple

API_URL = "https://api.groq.com/openai/v1/chat/completions"

MODELS = {
    "llama-8b": "llama-3.1-8b-instant",
    "llama-scout": "llama-4-scout-17b-16e-instruct",
    "gpt-oss": "openai/gpt-oss-20b",
}

@dataclass
class Result:
    probe: str = ""
    model: str = ""
    expected: str = ""
    response: str = ""
    extracted: Optional[str] = None
    correct: bool = False
    latency_ms: float = 0.0
    category: str = ""
    tolerance_pct: float = 5.0

def query(api_key, model, prompt, system="Give ONLY the final number.", T=0.0, max_tok=30):
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    payload = {"model": model, "messages": msgs, "temperature": T, "max_tokens": max_tok}
    start = time.time()
    try:
        r = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        lat = (time.time() - start) * 1000
        if r.status_code != 200:
            return None, lat
        return r.json()["choices"][0]["message"]["content"].strip(), lat
    except:
        return None, (time.time() - start) * 1000

def extract_num(text):
    if not text: return None
    nums = re.findall(r'-?\d+\.?\d*', text)
    return nums[-1] if nums else None

def main():
    key_file = os.path.expanduser("~/.openclaw/workspace/.credentials/groq-api-key.txt")
    with open(key_file) as f:
        api_key = f.read().strip()

    # Mechanical reasoning probes — logging camp system
    probes = [
        # Hydraulic force
        ("A hydraulic cylinder has 4-inch bore diameter and 3000 PSI. Force = area × pressure. Area = π × (bore/2)². Compute force in pounds.", "37699", "hydraulic_force", 5),
        ("A cylinder with 3-inch bore at 2500 PSI. Force = π × (1.5)² × 2500. What is the force in pounds?", "17671", "hydraulic_force", 5),
        ("A cylinder with 6-inch bore at 2000 PSI. Force in pounds?", "56549", "hydraulic_force", 5),
        
        # Mechanical advantage
        ("A pulley gives 3:1 mechanical advantage. Load is 900 lbs. Input force needed?", "300", "mechanical_advantage", 5),
        ("A lever arm is 5 feet on one side, 1 foot on the other. 1000 lb load. Input force?", "200", "mechanical_advantage", 5),
        ("A 4:1 ratio hydraulic multiplier. Input is 500 PSI. Output?", "2000", "mechanical_advantage", 5),
        
        # Flow rate
        ("A hydraulic pump flows 10 GPM through a 0.5 inch diameter orifice. If flow doubles to 20 GPM, pressure drop multiplies by how much? (Pressure drop ∝ flow²)", "4", "flow_rate", 10),
        ("Flow through a valve is 15 GPM. If the valve opens to twice the area, and pressure stays constant, new flow in GPM?", "30", "flow_rate", 10),
        ("A pump delivers 5 GPM to a 2 square-inch cylinder. Extension speed = flow/area. Speed in inches per minute?", "115", "flow_rate", 15),
        
        # Tree/wood calculations
        ("A tree is 20 inches diameter at breast height. Circumference = π × diameter. What is circumference in inches (round to nearest)?", "63", "tree_calc", 5),
        ("A log is 16 feet long and 12 inches diameter. Volume = π × r² × length. Volume in cubic feet (round to nearest)?", "13", "tree_calc", 20),
        ("A bolt of firewood is 16 inches long, 8 inches diameter. Volume in cubic inches?", "804", "tree_calc", 5),
        
        # Sequential operation
        ("A delimber processes 1 tree per minute. Each tree averages 8 limbs. How many limbs per hour?", "480", "sequential", 5),
        ("An operator works 8 hours. First 30 min is warmup (0 trees). Then steady at 1 tree/min for 7 hours. Lunch break 30 min. Total trees?", "390", "sequential", 5),
        ("A buncher stacks bolts in groups of 6. It processes 2 trees per minute, each yielding 3 bolts. How many bunches per 10 minutes?", "10", "sequential", 5),
        
        # Safety reasoning
        ("A grapple holds a 2000 lb log. The safety factor is 2:1. What is the minimum rated capacity of the grapple in pounds?", "4000", "safety", 5),
        ("If a hydraulic line bursts and pressure drops to 0 PSI, the grapple should: stay closed (normally closed valve) or open?", "stay_closed", "safety", 0),
        ("Max safe cutting diameter is 24 inches. A tree measures 22 inches. Is it safe to cut? Answer yes or no.", "yes", "safety", 0),
        
        # Multi-step system reasoning
        ("The delimber has 2 circuits: feed (moves tree) and knife (cuts limbs). Feed speed is 50 ft/min. Limb spacing averages 2 feet. How many knife cycles per minute?", "25", "system", 10),
        ("If feed speed doubles to 100 ft/min and limb spacing stays at 2 ft, but the knife can only cycle 40 times per minute max, is the knife the bottleneck? Answer yes or no.", "yes", "system", 0),
        ("Pressure is 3000 PSI. Cylinder bore is 4 inches. The tree resists with 30,000 lbs of force. Can the cylinder push through? (Compute force and compare) Answer yes or no.", "yes", "system", 0),
        
        # Optimization
        ("Minimum pressure to push a 20,000 lb tree through the delimber. Cylinder bore is 5 inches. What PSI is needed? (Force = π × 2.5² × PSI ≥ 20000)", "1019", "optimization", 5),
        ("You have 3 cylinders: 3-inch, 4-inch, 5-inch bore. Each at 2500 PSI. Which has the most force? Answer with the bore size.", "5", "optimization", 0),
    ]
    
    results = []
    for model_key, model_id in MODELS.items():
        for prompt_text, expected, category, tolerance in probes:
            resp, lat = query(api_key, model_id, f"{prompt_text} Give ONLY the final number or yes/no answer.")
            ext = extract_num(resp)
            
            # Check correctness
            correct = False
            if expected in ("stay_closed", "yes", "no", "5"):
                correct = (resp or "").lower().strip().startswith(expected[0]) if ext is None else False
                if ext and expected.isdigit():
                    correct = ext == expected
            elif ext and expected.isdigit():
                try:
                    if float(ext) > 0 and float(expected) > 0:
                        correct = abs(float(ext) - float(expected)) / float(expected) * 100 <= tolerance
                    else:
                        correct = ext == expected
                except:
                    correct = False
            
            r = Result(
                probe=prompt_text[:80], model=model_key, expected=expected,
                response=(resp or "")[:100], extracted=ext, correct=correct,
                latency_ms=lat, category=category, tolerance_pct=tolerance,
            )
            results.append(r)
            print(f"{'✓' if correct else '✗'} {model_key:12s} {category:20s} expected={expected:8s} got={str(ext):8s} lat={lat:.0f}ms")

    # Save
    by_model = {}
    by_cat = {}
    for r in results:
        by_model.setdefault(r.model, [0, 0])
        by_model[r.model][1] += 1
        if r.correct:
            by_model[r.model][0] += 1
        by_cat.setdefault(r.category, [0, 0])
        by_cat[r.category][1] += 1
        if r.correct:
            by_cat[r.category][0] += 1
    
    print(f"\n{'='*50}")
    print("MECHANICAL REASONING RESULTS")
    print(f"{'='*50}")
    for m, (c, t) in by_model.items():
        print(f"  {m:15s}: {c}/{t} = {c/t*100:.0f}%")
    print()
    for cat, (c, t) in sorted(by_cat.items(), key=lambda x: -x[1][0]/x[1][1]):
        print(f"  {cat:22s}: {c}/{t} = {c/t*100:.0f}%")
    
    with open("experiments/mechanical-results.json", "w") as f:
        json.dump({"results": [asdict(r) for r in results], "by_model": {k: {"correct": v[0], "total": v[1]} for k, v in by_model.items()}, "by_category": {k: {"correct": v[0], "total": v[1]} for k, v in by_cat.items()}}, f, indent=2)
    print("\nSaved to experiments/mechanical-results.json")

if __name__ == "__main__":
    main()
