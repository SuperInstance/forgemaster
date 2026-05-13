#!/usr/bin/env python3
"""
workshop.py — Non-thinking models show their work as auditable JSON.

Pipeline:
  1. FORK: Generate N competing reconstructions (show work as JSON)
  2. RUN: Execute validation code from each reconstruction
  3. SCORE: Backtest facts against ground truth
  4. ANALYZE: 4D analysis (cost, quality, speed, coverage)
  5. FEED: Patterns feed back into room design for better zero-shot

The key insight: thinking models hide reasoning in opaque tokens.
Non-thinking models + forced JSON = transparent, auditable, backtestable.
"""
import json, time, os, sys, subprocess, traceback
import urllib.request

DI_KEY = open(os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")).read().strip()
GROQ_KEY = open(os.path.expanduser("~/.openclaw/workspace/.credentials/groq-api-key.txt")).read().strip()

PROVIDERS = {
    "groq": ("https://api.groq.com/openai/v1/chat/completions", GROQ_KEY),
    "deepinfra": ("https://api.deepinfra.com/v1/openai/chat/completions", DI_KEY),
}

MODELS = {
    "seed": ("ByteDance/Seed-2.0-mini", "deepinfra"),
    "hermes": ("NousResearch/Hermes-3-Llama-3.1-70B", "deepinfra"),
    "qwen235": ("Qwen/Qwen3-235B-A22B-Instruct-2507", "deepinfra"),
    "8b": ("llama-3.1-8b-instant", "groq"),
}

def call(model_key, prompt, temp=1.0, maxt=1500):
    model_name, provider = MODELS[model_key]
    endpoint, key = PROVIDERS[provider]
    payload = json.dumps({"model": model_name, "temperature": temp,
        "max_tokens": maxt,
        "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(endpoint, data=payload, headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
            latency = (time.time() - t0) * 1000
            content = data['choices'][0]['message'].get('content', '')
            reasoning = data['choices'][0]['message'].get('reasoning_content', '')
            tokens = data.get('usage', {}).get('total_tokens', 0)
            return {"content": content, "reasoning": reasoning, "tokens": tokens,
                    "latency_ms": latency, "model": model_name}
    except Exception as e:
        return {"error": str(e), "model": model_name}

# ─── STEP 1: FORK — Generate competing reconstructions ───────────────

FORK_PROMPT = """You are a workshop. Generate {n} COMPETING reconstructions of this tile.
For each, show reasoning as structured JSON.

TILE: {tile}

Output ONLY valid JSON:
{{"reconstructions": [
  {{
    "approach": "short name",
    "confidence": 0.0-1.0,
    "facts_recovered": ["fact1", "fact2", ...],
    "facts_uncertain": ["?maybe_fact", ...],
    "facts_missed": ["missed_fact", ...],
    "reasoning": "why this approach works",
    "validation_code": "python3 code that checks the facts"
  }}
]}}

Rules:
- Each approach must be DIFFERENT (literal, creative, systematic, etc.)
- confidence must reflect genuine certainty
- Mark guesses in facts_uncertain with ? prefix
- Include runnable validation code
- Be brutally honest about what you DON'T know"""

def fork(tile, model_key="seed", n=3):
    """Generate n competing reconstructions."""
    prompt = FORK_PROMPT.format(n=n, tile=tile)
    result = call(model_key, prompt, temp=1.0, maxt=2000)
    if "error" in result:
        return {"error": result["error"]}
    
    content = result["content"]
    # Extract JSON from response
    try:
        start = content.index('{')
        end = content.rindex('}') + 1
        parsed = json.loads(content[start:end])
    except (ValueError, json.JSONDecodeError):
        parsed = {"raw": content}
    
    return {
        "model": result["model"],
        "tokens": result["tokens"],
        "latency_ms": result["latency_ms"],
        "reconstructions": parsed.get("reconstructions", []),
        "raw": content if "reconstructions" not in parsed else None,
    }

# ─── STEP 2: RUN — Execute validation code ───────────────────────────

def run_validation(code_snippet):
    """Safely execute validation code and return result."""
    if not code_snippet or not code_snippet.strip():
        return {"passed": None, "output": "No validation code provided"}
    
    # Strip markdown code fences
    code = code_snippet.replace("```python", "").replace("```", "").strip()
    
    try:
        result = subprocess.run(
            ["python3", "-c", code],
            capture_output=True, text=True, timeout=10)
        return {
            "passed": result.returncode == 0,
            "output": (result.stdout + result.stderr)[:500],
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"passed": False, "output": "Validation timed out"}
    except Exception as e:
        return {"passed": False, "output": str(e)}

# ─── STEP 3: SCORE — Backtest against ground truth ──────────────────

def score_reconstruction(reconstruction, ground_truth_facts):
    """Score a reconstruction against known ground truth."""
    recovered = reconstruction.get("facts_recovered", [])
    uncertain = reconstruction.get("facts_uncertain", [])
    missed = reconstruction.get("facts_missed", [])
    
    all_claimed = [f.lstrip("?") for f in recovered + uncertain]
    
    hits = 0
    for gt in ground_truth_facts:
        gt_lower = gt.lower()
        if any(gt_lower in f.lower() for f in all_claimed):
            hits += 1
    
    return {
        "ground_truth_count": len(ground_truth_facts),
        "hits": hits,
        "recall": hits / len(ground_truth_facts) if ground_truth_facts else 0,
        "claimed_count": len(all_claimed),
        "uncertain_count": len(uncertain),
        "confidence": reconstruction.get("confidence", 0),
    }

# ─── STEP 4: ANALYZE — 4D analysis ──────────────────────────────────

def analyze_4d(results, ground_truth):
    """4D analysis: cost, quality, speed, coverage."""
    analysis = {
        "models_tested": [],
        "best_by_cost": None,
        "best_by_quality": None,
        "best_by_speed": None,
        "best_by_coverage": None,
        "recommendations": [],
    }
    
    for r in results:
        if "error" in r:
            continue
        
        model = r["model"]
        reconstructions = r.get("reconstructions", [])
        if not reconstructions:
            continue
        
        # Score each reconstruction
        scores = [score_reconstruction(rec, ground_truth) for rec in reconstructions]
        best_score = max(scores, key=lambda s: s["recall"]) if scores else {"recall": 0}
        
        model_analysis = {
            "model": model,
            "tokens": r.get("tokens", 0),
            "latency_ms": r.get("latency_ms", 0),
            "n_reconstructions": len(reconstructions),
            "best_recall": best_score["recall"],
            "best_confidence": best_score["confidence"],
            "avg_confidence": sum(rec.get("confidence",0) for rec in reconstructions) / len(reconstructions),
            "total_uncertain": sum(len(rec.get("facts_uncertain",[])) for rec in reconstructions),
        }
        analysis["models_tested"].append(model_analysis)
    
    if not analysis["models_tested"]:
        return analysis
    
    # Rank by each dimension
    analysis["best_by_cost"] = min(analysis["models_tested"], 
        key=lambda m: m["tokens"])["model"]
    analysis["best_by_quality"] = max(analysis["models_tested"], 
        key=lambda m: m["best_recall"])["model"]
    analysis["best_by_speed"] = min(analysis["models_tested"], 
        key=lambda m: m["latency_ms"])["model"]
    analysis["best_by_coverage"] = max(analysis["models_tested"], 
        key=lambda m: m["n_reconstructions"])["model"]
    
    # Generate recommendations
    for m in analysis["models_tested"]:
        if m["total_uncertain"] > 0:
            analysis["recommendations"].append(
                f"{m['model']}: {m['total_uncertain']} uncertain facts → add these to room as hints")
        if m["best_recall"] < 1.0:
            analysis["recommendations"].append(
                f"{m['model']}: {m['best_recall']:.0%} recall → room needs more context for missed facts")
    
    return analysis

# ─── STEP 5: FEED — Generate room improvements ───────────────────────

def feed_back(analysis, tile):
    """Generate room improvements from analysis."""
    uncertain_facts = set()
    for r in analysis.get("models_tested", []):
        # Find uncertain facts from the raw results
        pass  # Will be populated from actual data
    
    prompt = f"""Based on this workshop analysis:
{json.dumps(analysis, indent=2)}

Original tile: {tile}

Generate a room improvement patch. For each uncertain or missed fact:
1. Write a 1-2 sentence expansion hint
2. Rate how critical it is (1-5)
3. Suggest where it goes (foundation/structure/application)

Output JSON:
{{"patches": [{{"fact": "...", "hint": "...", "criticality": 1-5, "layer": "..."}}]}}"""
    
    result = call("seed", prompt, temp=0.5, maxt=800)
    if "error" in result:
        return {"error": result["error"]}
    
    content = result["content"]
    try:
        start = content.index('{')
        end = content.rindex('}') + 1
        return json.loads(content[start:end])
    except:
        return {"raw": content}

# ─── Full Pipeline ────────────────────────────────────────────────────

def workshop(tile, ground_truth, models=None):
    """Run the full workshop pipeline."""
    if models is None:
        models = ["seed", "hermes", "qwen235"]
    
    print(f"{'='*70}", flush=True)
    print(f"WORKSHOP: {tile[:60]}...", flush=True)
    print(f"Ground truth: {len(ground_truth)} facts", flush=True)
    print(f"Models: {', '.join(models)}", flush=True)
    print(f"{'='*70}\n", flush=True)
    
    # Step 1: Fork
    print("STEP 1: FORK — Generating competing reconstructions...", flush=True)
    fork_results = []
    for model_key in models:
        print(f"  Forking {model_key}...", flush=True)
        sys.stdout.flush()
        result = fork(tile, model_key, n=3)
        fork_results.append(result)
        if "error" in result:
            print(f"    ERROR: {result['error']}", flush=True)
        else:
            n_recs = len(result.get("reconstructions", []))
            print(f"    {n_recs} reconstructions, {result['tokens']} tokens, {result['latency_ms']:.0f}ms", flush=True)
        sys.stdout.flush()
        time.sleep(1)
    
    # Step 2: Run validation
    print("\nSTEP 2: RUN — Executing validation code...")
    for result in fork_results:
        if "error" in result:
            continue
        for i, rec in enumerate(result.get("reconstructions", [])):
            code = rec.get("validation_code", "")
            val = run_validation(code)
            rec["validation"] = val
            status = "✅" if val["passed"] else "❌" if val["passed"] is False else "⏭️"
            print(f"  {result['model']} rec[{i}]: {status} {val['output'][:60]}")
    
    # Step 3: Score
    print("\nSTEP 3: SCORE — Backtesting against ground truth...")
    for result in fork_results:
        if "error" in result:
            continue
        for i, rec in enumerate(result.get("reconstructions", [])):
            score = score_reconstruction(rec, ground_truth)
            rec["score"] = score
            print(f"  {result['model']} rec[{i}]: recall={score['recall']:.0%} conf={score['confidence']:.2f} uncertain={score['uncertain_count']}")
    
    # Step 4: Analyze
    print("\nSTEP 4: ANALYZE — 4D analysis...")
    analysis = analyze_4d(fork_results, ground_truth)
    print(f"  Best cost: {analysis.get('best_by_cost','?')}")
    print(f"  Best quality: {analysis.get('best_by_quality','?')}")
    print(f"  Best speed: {analysis.get('best_by_speed','?')}")
    print(f"  Best coverage: {analysis.get('best_by_coverage','?')}")
    for rec in analysis.get("recommendations", []):
        print(f"  📌 {rec}")
    
    # Step 5: Feed
    print("\nSTEP 5: FEED — Generating room improvements...")
    patches = feed_back(analysis, tile)
    if "patches" in patches:
        for p in patches["patches"]:
            print(f"  [{p.get('layer','?')}] ({p.get('criticality','?')}/5) {p.get('fact','?')}")
            print(f"    → {p.get('hint','?')}")
    
    # Save everything
    output = {
        "tile": tile,
        "ground_truth": ground_truth,
        "fork_results": fork_results,
        "analysis": analysis,
        "patches": patches,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    
    outpath = os.path.expanduser("~/.openclaw/workspace/papers/workshop-results.json")
    with open(outpath, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nSaved to {outpath}")
    
    return output

# ─── CLI ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    TILE = "Penrose P3 tiling, 5D cut-and-project, golden-ratio hash vertex IDs, Fibonacci word encoding, dead-reckoning navigation, deflation consolidation, 3-color baton sharding, C9 locality failure, PCA projection 1.7x better than golden for neighbor preservation, 56% recall@20 end-to-end, 230B/23B MoE Seed integration"
    
    GROUND_TRUTH = [
        "Penrose P3 tiling",
        "5D cut-and-project",
        "golden-ratio hash vertex IDs",
        "Fibonacci word encoding",
        "dead-reckoning navigation",
        "deflation consolidation",
        "3-color baton sharding",
        "C9 locality failure",
        "PCA 1.7x better than golden",
        "230B/23B MoE Seed integration",
    ]
    
    workshop(TILE, GROUND_TRUTH, models=["seed", "hermes", "qwen235"])
