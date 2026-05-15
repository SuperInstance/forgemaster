#!/usr/bin/env python3
"""Spreader-tool operation test: Seed-2.0-mini vs MiMo-V2.5

Tests models on the specific cognitive patterns needed for spreader-tool
operations in the logging camp:
1. Multi-step sequential reasoning (delimb → cut → bunch)
2. Conditional branching (if tree > X diameter, route to large delimber)
3. State tracking (how many bolts in current bunch)
4. Safety constraint checking (pressure limits, diameter limits)
5. Optimization (best sequence given constraints)

Uses DeepInfra cached-input pricing for cost efficiency.
"""
import json, os, re, time, requests
from dataclasses import dataclass, asdict
from typing import Optional, List, Tuple

API_URL = "https://api.deepinfra.com/v1/openai/chat/completions"
API_KEY_FILE = os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")

MODELS = {
    "seed-mini": "ByteDance/Seed-2.0-mini",
    "mimo": "XiaomiMiMo/MiMo-V2.5",
    "step-flash": "stepfun-ai/Step-3.5-Flash",
}

FIXED_SYSTEM = (
    "You are a calculator. Output the result number ONLY. No words. No explanation."
)

@dataclass
class Probe:
    id: str
    category: str
    prompt: str
    expected: str
    difficulty: str  # easy/medium/hard

@dataclass 
class Result:
    probe_id: str
    model: str
    expected: str
    response: str
    extracted: Optional[str]
    correct: bool
    latency_ms: float
    category: str
    difficulty: str

def query(model_id: str, prompt: str, api_key: str) -> Tuple[Optional[str], float]:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": FIXED_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "max_tokens": 100,
    }
    start = time.time()
    try:
        r = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        lat = (time.time() - start) * 1000
        if r.status_code != 200:
            return f"ERROR {r.status_code}", lat
        data = r.json()
        msg = data["choices"][0]["message"]
        # Reasoning models (MiMo, GLM-5.1) put answer in reasoning_content
        content = msg.get("content", "") or ""
        reasoning = msg.get("reasoning_content", "") or ""
        # Use content if non-empty, else fall back to reasoning_content
        return (content.strip() if content.strip() else reasoning.strip()), lat
    except Exception as e:
        return f"ERROR {e}", (time.time() - start) * 1000

def extract_num(text):
    if not text: return None
    nums = re.findall(r'-?\d+\.?\d*', text)
    return nums[-1] if nums else None

def main():
    with open(API_KEY_FILE) as f:
        api_key = f.read().strip()
    
    probes = [
        # 1. Sequential reasoning
        Probe("SEQ1", "sequential", 
              "A delimber processes trees in sequence: grab(5s), delimb(15s), cut(3s), bunch(2s). Total time for 1 tree in seconds?", 
              "25", "easy"),
        Probe("SEQ2", "sequential",
              "Same delimber. After processing 3 trees, total time in seconds?",
              "75", "easy"),
        Probe("SEQ3", "sequential",
              "Same delimber. After 10 trees, how many minutes total? (round to nearest)",
              "4", "medium"),
        Probe("SEQ4", "sequential",
              "Grab takes 5s, delimb takes 15s, but delimbing can START during grab (overlap 3s). New time per tree in seconds?",
              "20", "medium"),
        Probe("SEQ5", "sequential",
              "With 3s overlap between grab and delimb, and 2s overlap between delimb and cut, time per tree?",
              "18", "hard"),
        
        # 2. Conditional branching
        Probe("COND1", "conditional",
              "Trees under 12 inches go to small delimber (1/min). Trees 12-24 inches go to large delimber (0.5/min). You have 6 small trees and 4 large trees. Total minutes?",
              "14", "easy"),
        Probe("COND2", "conditional",
              "Small delimber handles 1 tree/min. Large handles 0.5/min. If you have 20 trees total and 60% are small, total minutes?",
              "24", "medium"),
        Probe("COND3", "conditional",
              "Max small delimber diameter is 12 inches. A tree is 11.5 inches. Which delimber? Answer small or large.",
              "small", "easy"),
        Probe("COND4", "conditional",
              "A tree tapers from 14 inches at base to 8 inches at top. The small delimber max is 12 inches. Can it process the WHOLE tree? Answer yes or no.",
              "no", "hard"),
        
        # 3. State tracking
        Probe("STATE1", "state_tracking",
              "Bunches hold 6 bolts. You've cut 4 bolts. How many more before the bunch is full?",
              "2", "easy"),
        Probe("STATE2", "state_tracking",
              "Bunches hold 6 bolts. First tree yields 3 bolts. Second tree yields 4 bolts. How many bolts in current bunch? How many overflow?",
              "6 overflow 1", "medium"),
        Probe("STATE3", "state_tracking",
              "3 bunches complete (18 bolts). Current bunch has 4 bolts. Next tree yields 5 bolts. How many bunches now? How many bolts in partial bunch?",
              "4 bunches 1 bolt", "hard"),
        
        # 4. Safety constraints
        Probe("SAFE1", "safety",
              "Max pressure is 3500 PSI. Current reading is 2800 PSI. Is it safe to increase by 800 PSI? Answer yes or no.",
              "no", "easy"),
        Probe("SAFE2", "safety",
              "The grapple force limit is 50000 lbs. Tree weight is 12000 lbs. Safety factor is 3. Is the grapple rated for this? Answer yes or no.",
              "yes", "medium"),
        Probe("SAFE3", "safety",
              "Emergency stop triggers when pressure exceeds 4000 PSI OR cylinder temperature exceeds 180F. Current: 3800 PSI, 175F. Is emergency stop active? Answer yes or no.",
              "no", "easy"),
        Probe("SAFE4", "safety",
              "The delimber knife cycles at 40/min max. Feed speed creates 25 limbs/min. Knife utilization percentage?",
              "63", "medium"),
        
        # 5. Optimization
        Probe("OPT1", "optimization",
              "Small delimber: 1 tree/min, cost $2/tree. Large delimber: 0.5 tree/min, cost $5/tree. You have 10 small trees and 5 large trees. Cheapest approach cost?",
              "45", "medium"),
        Probe("OPT2", "optimization",
              "Fuel consumption: idle=1gal/hr, processing=3gal/hr. 8hr shift: 1hr warmup(idle), 6hr processing, 1hr shutdown(idle). Total fuel?",
              "20", "medium"),
        Probe("OPT3", "optimization",
              "Two operators: A processes 8 trees/hr, B processes 12 trees/hr. Combined rate if they work different zones?",
              "20", "easy"),
        
        # 6. Hydraulic system reasoning
        Probe("HYD1", "hydraulic",
              "Main pump: 20 GPM. Circuit A needs 12 GPM, circuit B needs 8 GPM. Can both run simultaneously? Answer yes or no.",
              "yes", "easy"),
        Probe("HYD2", "hydraulic",
              "Main pump: 20 GPM. Priority valve sends 15 GPM to circuit A first. Remaining to B. Circuit B needs 10 GPM. Is B starved? Answer yes or no.",
              "yes", "medium"),
        Probe("HYD3", "hydraulic",
              "Pressure drop across a valve: 500 PSI at 10 GPM. At 20 GPM, pressure drop quadruples (flow² relationship). New pressure drop?",
              "2000", "hard"),
    ]
    
    results = []
    for model_key, model_id in MODELS.items():
        print(f"\n--- {model_key} ---")
        for probe in probes:
            resp, lat = query(model_id, probe.prompt, api_key)
            ext = extract_num(resp)
            
            # Check correctness
            correct = False
            if probe.expected.isdigit():
                correct = ext == probe.expected if ext else False
            elif probe.expected in ("yes", "no", "small", "large"):
                correct = (resp or "").lower().strip().startswith(probe.expected[0])
            else:
                # Complex expected like "6 overflow 1" - check key numbers
                exp_nums = re.findall(r'\d+', probe.expected)
                got_nums = re.findall(r'\d+', resp or "")
                correct = exp_nums == got_nums
            
            r = Result(
                probe_id=probe.id, model=model_key, expected=probe.expected,
                response=(resp or "")[:100], extracted=ext, correct=correct,
                latency_ms=lat, category=probe.category, difficulty=probe.difficulty,
            )
            results.append(r)
            sym = "✓" if correct else "✗"
            print(f"  {sym} {probe.id:6s} [{probe.difficulty:6s}] {probe.category:15s} expected={probe.expected:15s} got={str(ext) or resp[:20]:15s} lat={lat:.0f}ms", flush=True)
    
    # Summary
    print(f"\n{'='*60}")
    print("SPREADER-TOOL RESULTS")
    print(f"{'='*60}")
    for mk in MODELS:
        mr = [r for r in results if r.model == mk]
        c = sum(1 for r in mr if r.correct)
        t = len(mr)
        lats = [r.latency_ms for r in mr]
        print(f"  {mk:15s}: {c}/{t} = {c/t*100:.0f}% (avg lat: {sum(lats)/len(lats):.0f}ms)")
        
        # By category
        for cat in set(r.category for r in mr):
            cr = [r for r in mr if r.category == cat]
            cc = sum(1 for r in cr if r.correct)
            print(f"    {cat:20s}: {cc}/{len(cr)} = {cc/len(cr)*100:.0f}%")
    
    with open("experiments/spreader-tool-results.json", "w") as f:
        json.dump({"results": [asdict(r) for r in results]}, f, indent=2)
    print("\nSaved to experiments/spreader-tool-results.json")

if __name__ == "__main__":
    main()
