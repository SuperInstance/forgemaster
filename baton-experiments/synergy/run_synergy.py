#!/usr/bin/env python3
"""
Baton Protocol: Small Model Synergy Experiments
Round-robin iterative experiments. Each round:
  1. Run experiment
  2. Score results  
  3. Generate hypotheses from findings
  4. Design next round to test those hypotheses

Only uses the smallest/cheapest models:
  - Seed-2.0-mini (~$0.01/query)
  - Qwen3.6-35B-A3B (~$0.01/query)
"""

import os, json, time, hashlib, urllib.request
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional

KEY = Path(os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")).read_text().strip()
URL = "https://api.deepinfra.com/v1/openai/chat/completions"
OUT = Path("/home/phoenix/.openclaw/workspace/baton-experiments/synergy")
OUT.mkdir(parents=True, exist_ok=True)

MODELS = {
    "seed": "ByteDance/Seed-2.0-mini",
    "qwen": "Qwen/Qwen3.6-35B-A3B",
}

SOURCE = Path("/home/phoenix/.openclaw/workspace/baton-experiments/linear-handoff-reconstruction.txt").read_text()

GROUND_TRUTH = [
    "6 Galois proof parts verified", "1.4M+ total constructive checks",
    "XOR self-adjoint involution", "INT8 reflective subcategory",
    "Bloom filter Heyting algebra", "floor/ceil adjoints",
    "intent alignment tolerance-set", "holonomy cycle/subgraph",
    "14 facts tracked in telephone game", "6 rounds of telephone",
    "MV Epsilon drifted 200 meters east", "Narrows Strait",
    "4,200 containers medical supplies", "47,000 vessels at risk",
    "Round 2 recovered a lost fact", "crystallization at Round 3-4",
    "6 immortal facts survived", "Lila Marquez invented by Round 1",
    "forgetting-as-feature thesis", "accuracy and utility inversely correlated",
    "Ebbinghaus curve is rate-distortion bound", "lighthouse runtime: orient/relay/gate",
    "first bootstrap: 5 seeds at $0.50", "hex grid visualizer built",
    "gate caught credential leaks", "tile-memory Python library",
    "memory-crystal Rust library", "41/41 tests in memory-crystal",
    "collective-recall-demo 33KB HTML", "bridge connects to PLATO",
    "6 fleet services down", "Oracle1 needs console access",
    "Matrix send broken", "210/210 dodecet-encoder tests",
    "snap() accuracy 63.9% to 99.4%", "17 crates on crates.io",
    "INT8 x8: 341B constraints/sec", "RTX 4050 memory-bound at 187 GB/s",
    "z.ai rate limits hit", "npm publish blocked",
]

def call(model_key: str, system: str, user: str, temp=0.7, max_tok=1500) -> str:
    payload = json.dumps({
        "model": MODELS[model_key],
        "messages": [{"role":"system","content":system},{"role":"user","content":user}],
        "temperature": temp, "max_tokens": max_tok,
    }).encode()
    req = urllib.request.Request(URL, data=payload,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            return json.loads(resp.read())["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[ERROR: {e}]"

def score(text: str) -> Dict:
    low = text.lower()
    found, missing = [], []
    for f in GROUND_TRUTH:
        terms = [t.lower() for t in f.split() if len(t) > 3]
        hits = sum(1 for t in terms if t in low)
        if hits >= max(len(terms)*0.5, 1):
            found.append(f)
        else:
            missing.append(f)
    novel = [w for w in set(low.split()) - set(SOURCE.lower().split()) if len(w) > 5]
    return {"found": len(found), "total": len(GROUND_TRUTH), "accuracy": len(found)/len(GROUND_TRUTH),
            "novel": len(novel), "len": len(text), "found_list": found, "missing_list": missing}

def save(name: str, data: Dict):
    (OUT / f"{name}.json").write_text(json.dumps(data, indent=2, default=str, ensure_ascii=False))

# ====================================================================
# EXPERIMENT RUNNER
# ====================================================================

def run_round(round_num: int, experiments: List[Dict]) -> Dict:
    """Run a round of experiments, return results + hypotheses."""
    print(f"\n{'='*70}")
    print(f"ROUND {round_num}")
    print(f"{'='*70}")
    
    results = []
    for exp in experiments:
        name = exp["name"]
        desc = exp["desc"]
        print(f"\n--- {name}: {desc} ---")
        
        # Run the experiment function
        output = exp["run"]()
        
        # Score
        if isinstance(output, str):
            s = score(output)
        elif isinstance(output, dict):
            main = output.get("final", output.get("remesh", output.get("revised", str(output))))
            s = score(main if isinstance(main, str) else str(main))
        else:
            s = score(str(output))
        
        s["name"] = name
        s["desc"] = desc
        print(f"  → {s['accuracy']:.1%} ({s['found']}/{s['total']}) | novel={s['novel']} | len={s['len']}")
        
        results.append({**s, "output": output})
        save(f"r{round_num}-{name}", {**s, "output": output})
    
    # Generate hypotheses for next round
    print(f"\n{'='*70}")
    print(f"ROUND {round_num} ANALYSIS")
    print(f"{'='*70}")
    for r in results:
        print(f"  {r['name']:<30} {r['accuracy']:.1%} ({r['found']}/{r['total']}) novel={r['novel']}")
    
    return {"round": round_num, "results": [{k:v for k,v in r.items() if k != "output"} for r in results]}

# ====================================================================
# ROUND 1: Baseline — All Small Models, Simple Roles
# ====================================================================

def round1():
    """Baseline: test each small model alone, then in 2-model synergy."""
    
    exps = []
    
    # 1a: Seed alone (control for small models)
    def seed_alone():
        return call("seed", "You are receiving a handoff from a previous agent. Summarize everything important.",
                    f"Handoff context:\n\n{SOURCE}", temp=0.3)
    exps.append({"name": "seed-alone", "desc": "Seed-2.0-mini alone, linear handoff", "run": seed_alone})
    
    # 1b: Qwen alone
    def qwen_alone():
        return call("qwen", "You are receiving a handoff from a previous agent. Summarize everything important.",
                    f"Handoff context:\n\n{SOURCE}", temp=0.3)
    exps.append({"name": "qwen-alone", "desc": "Qwen3.6-35B alone, linear handoff", "run": qwen_alone})
    
    # 1c: Seed encodes → Qwen decodes
    def seed_qwen():
        encoded = call("seed",
            "Extract the MOST IMPORTANT facts from this session. Bullet points only. No narrative.",
            f"Extract facts:\n\n{SOURCE}", temp=0.3)
        decoded = call("qwen",
            "You are receiving compressed notes from a previous agent. Reconstruct the full session context as best you can.",
            f"Compressed notes:\n\n{encoded}", temp=0.5)
        return decoded
    exps.append({"name": "seed-encode-qwen-decode", "desc": "Seed encodes → Qwen reconstructs", "run": seed_qwen})
    
    # 1d: Qwen encodes → Seed decodes
    def qwen_seed():
        encoded = call("qwen",
            "Extract the MOST IMPORTANT facts from this session. Bullet points only. No narrative.",
            f"Extract facts:\n\n{SOURCE}", temp=0.3)
        decoded = call("seed",
            "You are receiving compressed notes from a previous agent. Reconstruct the full session context as best you can.",
            f"Compressed notes:\n\n{encoded}", temp=0.5)
        return decoded
    exps.append({"name": "qwen-encode-seed-decode", "desc": "Qwen encodes → Seed reconstructs", "run": qwen_seed})
    
    # 1e: Both encode DIFFERENT aspects → one synthesizes
    def parallel_encode():
        tech = call("seed",
            "Extract ONLY concrete technical facts: numbers, file names, test results, APIs, errors.",
            f"Technical extraction:\n\n{SOURCE}", temp=0.3)
        abstract = call("qwen",
            "Extract ONLY abstract concepts: theories, decisions, reasoning, philosophy, narrative arc.",
            f"Abstract extraction:\n\n{SOURCE}", temp=0.5)
        synth = call("seed",
            "You have two compressed views of the same session. One is technical, one is abstract. Reconstruct the full picture.",
            f"TECHNICAL:\n{tech}\n\nABSTRACT:\n{abstract}", temp=0.5)
        return synth
    exps.append({"name": "parallel-encode-synth", "desc": "Seed→tech, Qwen→abstract, Seed synthesizes", "run": parallel_encode})
    
    return run_round(1, exps)

# ====================================================================
# ROUND 2: Designed from Round 1 hypotheses
# ====================================================================

def round2(r1_results):
    """Hypotheses from Round 1 guide this round's experiments."""
    
    # Hypothesis generator
    hypo = call("seed",
        "You are an experimental psychologist analyzing results. Given these experimental results, generate 3 specific testable hypotheses for the next round of experiments. Each hypothesis should be falsifiable and suggest a specific experiment.",
        f"Round 1 results:\n{json.dumps(r1_results, indent=2, default=str)[:2000]}\n\nGenerate 3 hypotheses for Round 2.",
        temp=0.8)
    
    print("\n--- HYPOTHESES FROM ROUND 1 ---")
    print(hypo)
    save("r2-hypotheses", {"hypotheses": hypo})
    
    # Based on typical Round 1 patterns, test:
    exps = []
    
    # 2a: Iterative refinement — encode/decode TWICE through different models
    def double_pass():
        first = call("seed",
            "Summarize this session, preserving all important details.",
            SOURCE, temp=0.3)
        second = call("qwen",
            "You received a summary of a session. Another agent will need to continue this work. Add any context you think is missing.",
            first, temp=0.5)
        third = call("seed",
            "Final handoff: reconstruct the most complete version of this session for the next agent.",
            second, temp=0.3)
        return third
    exps.append({"name": "double-pass", "desc": "Seed→Qwen→Seed triple pass", "run": double_pass})
    
    # 2b: Adversarial — one model challenges the other's reconstruction
    def adversarial():
        recon = call("seed",
            "Reconstruct this session for the next agent. Be comprehensive.",
            SOURCE, temp=0.3)
        critique = call("qwen",
            "You are an adversarial reviewer. Given the original and a reconstruction, list EVERYTHING the reconstruction got wrong or missed. Be harsh.",
            f"ORIGINAL:\n{SOURCE}\n\nRECONSTRUCTION:\n{recon}", temp=0.5)
        revised = call("seed",
            "You made a reconstruction. A critic found these issues. Fix them and produce a better reconstruction.",
            f"Your reconstruction:\n{recon}\n\nCritique:\n{critique}", temp=0.3)
        return revised
    exps.append({"name": "adversarial-refine", "desc": "Seed reconstructs → Qwen critiques → Seed revises", "run": adversarial})
    
    # 2c: Roleplay specialists — each model is a different "team member"
    def specialists():
        engineer = call("seed",
            "You are a Rust engineer. You only care about: code, tests, APIs, performance numbers, compilation. Extract EVERYTHING technical.",
            SOURCE, temp=0.3)
        researcher = call("qwen",
            "You are a research scientist. You only care about: theories, proofs, mathematical results, publications, insights. Extract EVERYTHING theoretical.",
            SOURCE, temp=0.3)
        ops = call("seed",
            "You are a DevOps engineer. You only care about: services, deployments, blockers, infrastructure, access. Extract EVERYTHING operational.",
            SOURCE, temp=0.3)
        combined = call("qwen",
            "Three specialists reported on the same session. Merge their reports into one complete handoff.",
            f"ENGINEER:\n{engineer}\n\nRESEARCHER:\n{researcher}\n\nOPS:\n{ops}", temp=0.3)
        return combined
    exps.append({"name": "roleplay-specialists", "desc": "Seed=engineer, Qwen=researcher, Seed=ops → Qwen merges", "run": specialists})
    
    # 2d: Minimal prompt — how much does prompt engineering matter for small models?
    def minimal():
        return call("seed", "Continue.", SOURCE, temp=0.3)
    exps.append({"name": "minimal-prompt", "desc": "Seed with just 'Continue.' as system prompt", "run": minimal})
    
    # 2e: Temperature sweep — same model, high vs low temp
    def hot_seed():
        return call("seed", "Reconstruct this session for the next agent.",
                    SOURCE, temp=1.2)
    exps.append({"name": "hot-seed", "desc": "Seed at temperature 1.2 (creative)", "run": hot_seed})
    
    return run_round(2, exps)

# ====================================================================
# ROUND 3: Designed from Rounds 1+2
# ====================================================================

def round3(r1_results, r2_results):
    """Final round testing the most promising configurations with refinements."""
    
    all_so_far = json.dumps({"r1": r1_results, "r2": r2_results}, default=str)[:3000]
    
    hypo = call("qwen",
        "You are an experimental psychologist. Given results from two rounds of baton protocol experiments, identify the single most important unanswered question and design ONE experiment to answer it.",
        f"All results so far:\n{all_so_far}\n\nWhat is the most important unanswered question? Design one experiment.",
        temp=0.7)
    
    print("\n--- ROUND 3 DESIGN RATIONALE ---")
    print(hypo)
    save("r3-rationale", {"rationale": hypo})
    
    exps = []
    
    # 3a: Best of R1/R2 combined — parallel encode + adversarial refinement
    def best_combined():
        tech = call("seed",
            "Extract concrete technical facts only: numbers, files, tests, APIs.",
            SOURCE, temp=0.3)
        theory = call("qwen",
            "Extract theoretical insights only: proofs, decisions, philosophy.",
            SOURCE, temp=0.3)
        blocks = call("seed",
            "Extract blockers and gaps only: errors, missing items, TODOs.",
            SOURCE, temp=0.3)
        merged = call("qwen",
            "Three views of the same session. Reconstruct completely.",
            f"TECHNICAL:\n{tech}\n\nTHEORY:\n{theory}\n\nBLOCKED:\n{blocks}", temp=0.3)
        critique = call("seed",
            "Harshly critique this reconstruction. What's missing or wrong?",
            f"ORIGINAL:\n{SOURCE}\n\nRECONSTRUCTION:\n{merged}", temp=0.5)
        final = call("qwen",
            "Final reconstruction incorporating critique.",
            f"DRAFT:\n{merged}\n\nCRITIQUE:\n{critique}", temp=0.3)
        return final
    exps.append({"name": "combined-best", "desc": "Parallel 3-way + adversarial critique + revision", "run": best_combined})
    
    # 3b: Telephone through small models — 4-hop chain
    def telephone_chain():
        current = SOURCE
        for i in range(4):
            model = "seed" if i % 2 == 0 else "qwen"
            current = call(model,
                f"You are Round {i+1} of a telephone game. Retell this session in your own words. Preserve facts but use your own framing.",
                current, temp=0.6)
            print(f"    telephone round {i+1} ({model}): {len(current)} chars")
        return current
    exps.append({"name": "telephone-4hop", "desc": "4-hop telephone: Seed→Qwen→Seed→Qwen", "run": telephone_chain})
    
    # 3c: The "Wise Advisor" — original points at gaps, doesn't correct
    def wise_advisor():
        # Agent reconstructs from partial
        partial = call("seed",
            "You have incomplete notes from a session. Do your best to reconstruct it.",
            f"Partial notes:\n{SOURCE[:800]}", temp=0.5)
        # Wise advisor points at gaps (not correcting, HINTING)
        hints = call("qwen",
            "You are a WISE advisor. You have the full session and an agent's partial reconstruction. Do NOT correct errors. Instead, give 5 SHORT hints about what they're missing. Like: 'Think about the test results' or 'Consider what was built'.",
            f"Full session:\n{SOURCE}\n\nAgent's reconstruction:\n{partial}", temp=0.5)
        # Agent tries again with hints
        revised = call("seed",
            "You made a partial reconstruction. A wise advisor gave you hints about what's missing. Try again.",
            f"Your first attempt:\n{partial}\n\nAdvisor hints:\n{hints}\n\nTry to reconstruct more completely.", temp=0.5)
        return revised
    exps.append({"name": "wise-advisor", "desc": "Partial recon → advisor hints → revised recon", "run": wise_advisor})
    
    # 3d: Cross-examination — two models interview each other
    def cross_exam():
        a1_knowledge = call("seed",
            "You attended the first half of a session (02:00-06:00). Describe what you saw.",
            SOURCE[:1100], temp=0.5)
        a2_knowledge = call("qwen",
            "You attended the second half of a session (06:00-10:00). Describe what you saw.",
            SOURCE[1100:], temp=0.5)
        interview = call("seed",
            "You attended the first half. Ask the second-half attendee 5 questions about what happened after you left.",
            f"Your knowledge (first half):\n{a1_knowledge}\n\nTheir knowledge (second half):\n{a2_knowledge}", temp=0.7)
        debrief = call("qwen",
            "Two agents who attended different halves of a session are debriefing. Write the complete combined handoff.",
            f"First half agent:\n{a1_knowledge}\n\nSecond half agent:\n{a2_knowledge}\n\nFirst half's questions:\n{interview}", temp=0.3)
        return debrief
    exps.append({"name": "cross-examination", "desc": "Split timeline, agents interview each other", "run": cross_exam})
    
    return run_round(3, exps)

# ====================================================================
# MAIN
# ====================================================================

def main():
    print("BATON PROTOCOL: SMALL MODEL SYNERGY")
    print("="*70)
    print(f"Models: {list(MODELS.keys())}")
    print(f"Source: {len(SOURCE)} chars | Ground truth: {len(GROUND_TRUTH)} facts")
    print(f"Output: {OUT}/")
    
    r1 = round1()
    r2 = round2(r1)
    r3 = round3(r1, r2)
    
    # Final comparative summary
    print(f"\n\n{'='*70}")
    print("FINAL COMPARATIVE RESULTS")
    print(f"{'='*70}")
    print(f"{'Round':<7} {'Experiment':<32} {'Accuracy':>9} {'Facts':>7} {'Novel':>7}")
    print("-"*70)
    for rd in [r1, r2, r3]:
        for r in rd["results"]:
            print(f"R{rd['round']:<6} {r['name']:<32} {r['accuracy']:>8.1%} {r['found']:>3}/{r['total']:<3} {r['novel']:>7}")
    
    # Save master summary
    save("summary-all", {"rounds": [r1, r2, r3]})

if __name__ == "__main__":
    main()
