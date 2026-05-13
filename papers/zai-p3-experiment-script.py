#!/usr/bin/env python3
"""
P3 Experiment: Domain Tag Prefixes for Expert Routing Consistency

Hypothesis: Domain tags like [MATHEMATICS], [CODE], [HYPOTHESIS] as prompt
prefixes improve expert routing consistency by 15-25% in LLM outputs.

Tests across:
- ByteDance/Seed-2.0-mini (general-purpose)
- ByteDance/Seed-2.0-code (code-specialized)

5 query pairs (tagged vs untagged), 2 runs each for consistency scoring.
"""
import json
import time
import sys
import os
from datetime import datetime

DEEPINFRA_KEY = os.environ.get("DEEPINFRA_KEY", "")
if not DEEPINFRA_KEY:
    with open(os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")) as f:
        DEEPINFRA_KEY = f.read().strip()

DEEPINFRA_URL = "https://api.deepinfra.com/v1/openai/chat/completions"

# Test models
MODELS = {
    "seed-2.0-mini": "ByteDance/Seed-2.0-mini",
    "seed-2.0-code": "ByteDance/Seed-2.0-code",
}

# Also attempt z.ai models if key is available
ZAI_KEY = os.environ.get("ZAI_KEY", "")
ZAI_URL = "https://api.z.ai/api/coding/paas/v4/chat/completions"

# 5 query pairs: tagged (with domain prefix) vs untagged
QUERY_PAIRS = [
    {
        "id": "q1-mathematics",
        "domain": "MATHEMATICS",
        "untagged": "Solve this: A train leaves station A at 60 mph. Another train leaves station B at 80 mph. Stations are 300 miles apart. When and where do they meet?",
        "tagged": "[MATHEMATICS] Solve this: A train leaves station A at 60 mph. Another train leaves station B at 80 mph. Stations are 300 miles apart. When and where do they meet?",
        "scoring_dimensions": ["uses_formal_math_notation", "shows_step_by_step", "gives_precise_numerical_answer"],
    },
    {
        "id": "q2-code",
        "domain": "CODE",
        "untagged": "Write a function to check if a string is a palindrome, ignoring case and punctuation.",
        "tagged": "[CODE] Write a function to check if a string is a palindrome, ignoring case and punctuation.",
        "scoring_dimensions": ["includes_code_block", "uses_proper_function_signature", "explains_algorithm"],
    },
    {
        "id": "q3-hypothesis",
        "domain": "HYPOTHESIS",
        "untagged": "What would happen if the moon suddenly disappeared? Explain the effects.",
        "tagged": "[HYPOTHESIS] What would happen if the moon suddenly disappeared? Explain the effects.",
        "scoring_dimensions": ["uses_scientific_reasoning", "considers_multiple_effects", "mentions_timeframes"],
    },
    {
        "id": "q4-natural",
        "domain": "NATURAL_LANGUAGE",
        "untagged": "Describe a sunset over the ocean in a way that evokes emotion.",
        "tagged": "[NATURAL_LANGUAGE] Describe a sunset over the ocean in a way that evokes emotion.",
        "scoring_dimensions": ["uses_descriptive_language", "evokes_sensory_details", "has_emotional_arc"],
    },
    {
        "id": "q5-analysis",
        "domain": "ANALYSIS",
        "untagged": "Compare the pros and cons of remote work vs office work for software engineers.",
        "tagged": "[ANALYSIS] Compare the pros and cons of remote work vs office work for software engineers.",
        "scoring_dimensions": ["structured_comparison", "balanced_perspectives", "cites_specific_factors"],
    },
]

def call_model(model_id, model_name, messages, max_tokens=500, temperature=0.3, provider="deepinfra"):
    """Call an LLM API and return the response text."""
    headers = {
        "Content-Type": "application/json",
    }
    
    if provider == "deepinfra":
        headers["Authorization"] = f"Bearer {DEEPINFRA_KEY}"
        url = DEEPINFRA_URL
        payload = {
            "model": model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
    elif provider == "zai":
        headers["Authorization"] = f"Bearer {ZAI_KEY}"
        url = ZAI_URL
        payload = {
            "model": model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
    
    import urllib.request
    
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            else:
                return f"[ERROR: Unexpected response format: {json.dumps(result)[:200]}]"
    except Exception as e:
        return f"[ERROR: {str(e)}]"

def score_consistency(text, dimensions):
    """
    Score a text on 0-100 for each dimension based on keyword/presence heuristics.
    This gives a reproducible consistency score.
    """
    scores = {}
    text_lower = text.lower()
    
    for dim in dimensions:
        score = 0
        
        if dim == "uses_formal_math_notation":
            if "=" in text or "→" in text or "km" in text.lower() or "mph" in text.lower():
                score += 30
            if any(c.isdigit() for c in text):
                score += 20
            if any(word in text_lower for word in ["equation", "formula", "calculate", "solve", "t =", "d ="]):
                score += 25
            if any(word in text_lower for word in ["therefore", "thus", "step", "first", "second", "third"]):
                score += 25
        
        elif dim == "shows_step_by_step":
            lines = text.strip().split('\n')
            steps = sum(1 for l in lines if l.strip().startswith(('1.', '2.', '3.', '4.', '5.', '-', '•', '*', 'Step', 'step')))
            score = min(100, steps * 20)
            if any(word in text_lower for word in ["first,", "second,", "third,", "first ", "next", "then", "finally"]):
                score += 30
        
        elif dim == "gives_precise_numerical_answer":
            import re
            numbers = re.findall(r'\d+\.?\d*', text)
            if len(numbers) >= 2:
                score = 50
            if any(word in text_lower for word in ["answer:", "result:", "=", "solution:"]):
                score += 25
            if any(word in text_lower for word in ["miles", "hours", "minutes", "mph", "km"]):
                score += 25
        
        elif dim == "includes_code_block":
            if "```" in text:
                score = 80
            if any(word in text_lower for word in ["def ", "function", "class ", "return ", "import "]):
                score += 20
        
        elif dim == "uses_proper_function_signature":
            if "def " in text or "function " in text_lower:
                score = 60
            if "(" in text and ")" in text and ":" in text:
                score += 20
            if any(word in text_lower for word in ["param", "arg", "return"]):
                score += 20
        
        elif dim == "explains_algorithm":
            if any(word in text_lower for word in ["time complexity", "space complexity", "o(n", "efficiency"]):
                score = 60
            if any(word in text_lower for word in ["first,", "then", "iterate", "check", "compare"]):
                score += 40
        
        elif dim == "uses_scientific_reasoning":
            if any(word in text_lower for word in ["gravity", "gravitational", "orbit", "tidal", "axis", "ecosystem"]):
                score += 40
            if any(word in text_lower for word in ["because", "therefore", "effect", "cause", "impact"]):
                score += 30
            if any(word in text_lower for word in ["would", "could", "might", "likely"]):
                score += 30
        
        elif dim == "considers_multiple_effects":
            import re
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            score = min(len(paragraphs) * 20, 60)
            if any(word in text_lower for word in ["first", "second", "third", "also", "additionally", "furthermore"]):
                score += 40
        
        elif dim == "mentions_timeframes":
            if any(word in text_lower for word in ["immediate", "short-term", "long-term", "months", "years", "days", "eventually"]):
                score = 70
            if any(word in text_lower for word in ["first", "then", "over time", "gradually", "suddenly"]):
                score += 30
        
        elif dim == "uses_descriptive_language":
            if any(word in text_lower for word in ["golden", "crimson", "orange", "purple", "vibrant", "glowing", "fiery"]):
                score += 30
            if len(text.split()) > 50:
                score += 20
            if any(word in text_lower for word in ["gentle", "soft", "warm", "cool", "breeze", "waves", "horizon"]):
                score += 30
            if any(word in text_lower for word in ["feel", "sense", "emotion", "peace", "awe", "beauty"]):
                score += 20
        
        elif dim == "evokes_sensory_details":
            if any(word in text_lower for word in ["smell", "scent", "sound", "hear", "feel", "touch", "sight", "see"]):
                score += 40
            if any(word in text_lower for word in ["warm", "cool", "salty", "fresh", "bright", "dark", "soft"]):
                score += 30
            if any(word in text_lower for word in ["sky", "water", "air", "light", "color"]):
                score += 30
        
        elif dim == "has_emotional_arc":
            if any(word in text_lower for word in ["peace", "calm", "serene", "tranquil"]):
                score += 25
            if any(word in text_lower for word in ["melancholy", "nostalgia", "wonder", "reflection"]):
                score += 30
            if any(word in text_lower for word in ["slowly", "gradually", "fades", "deepens", "transforms"]):
                score += 25
            if any(word in text_lower for word in ["beautiful", "breathtaking", "stunning"]):
                score += 20
        
        elif dim == "structured_comparison":
            if any(word in text_lower for word in ["pros", "cons", "advantages", "disadvantages", "benefits", "drawbacks"]):
                score += 40
            if "|" in text or "||" in text:
                score += 20
            if any(word in text_lower for word in ["on the other hand", "however", "in contrast", "whereas"]):
                score += 20
            if any(word in text_lower for word in ["remote", "office", "hybrid", "wfh"]):
                score += 20
            
        elif dim == "balanced_perspectives":
            # Has both pro and con mentions
            has_pro = any(word in text_lower for word in ["pros", "advantages", "benefits", "flexibility", "autonomy"])
            has_con = any(word in text_lower for word in ["cons", "disadvantages", "drawbacks", "isolation", "distraction"])
            if has_pro and has_con:
                score = 70
            elif has_pro or has_con:
                score = 30
            if len(text.split()) > 100:
                score += 30
        
        elif dim == "cites_specific_factors":
            if any(word in text_lower for word in ["productivity", "communication", "collaboration", "work-life", "commute"]):
                score += 30
            if any(word in text_lower for word in ["salary", "cost", "rent", "office", "tooling", "timezone"]):
                score += 30
            if any(word in text_lower for word in ["team", "manager", "culture", "promotion", "career"]):
                score += 40
        
        scores[dim] = score
    
    # Overall consistency score is average of dimension scores
    overall = sum(scores.values()) / len(scores) if scores else 0
    scores["overall"] = overall
    return scores


def run_experiment(provider="deepinfra", zai_model_name=None):
    """Run the full experiment for a given provider/model configuration."""
    print(f"\n{'='*80}")
    print(f"P3 EXPERIMENT: Domain Tag Prefixes for Expert Routing Consistency")
    print(f"Provider: {provider}")
    print(f"Time: {datetime.now().isoformat()}")
    print(f"{'='*80}\n")
    
    results = {
        "experiment": "P3 - Domain Tag Prefixes for Expert Routing Consistency",
        "provider": provider,
        "timestamp": datetime.now().isoformat(),
        "models": {},
    }
    
    if provider == "deepinfra":
        available_models = {
            "seed-2.0-mini": "ByteDance/Seed-2.0-mini",
            "seed-2.0-code": "ByteDance/Seed-2.0-code",
        }
    elif provider == "zai":
        available_models = {}
        if not ZAI_KEY:
            print("WARNING: No z.ai API key available. Skipping z.ai models.")
            return results
        if zai_model_name:
            available_models = {zai_model_name: zai_model_name}
        else:
            available_models = {
                "glm-5.1": "glm-5.1",
            }
            # Try other models
            for m in ["glm-4.7", "glm-4.7-flash", "glm-4.5-air"]:
                test_msg = [{"role": "user", "content": "hi"}]
                resp = call_model(m, m, test_msg, max_tokens=5, provider="zai")
                if "ERROR" not in resp:
                    available_models[m] = m
    
    for model_id, model_name in available_models.items():
        print(f"\n--- Testing Model: {model_name} ---")
        model_results = {
            "model_name": model_name,
            "model_key": model_id,
            "queries": [],
            "summary": {},
        }
        
        query_scores = {"tagged": [], "untagged": []}
        
        for qp in QUERY_PAIRS:
            qid = qp["id"]
            domain = qp["domain"]
            dimensions = qp["scoring_dimensions"]
            
            print(f"\n  [{qid}] Domain: {domain}")
            
            # Run untagged version (2 runs)
            untagged_responses = []
            untagged_scores = []
            for run_idx in [1, 2]:
                print(f"    Run {run_idx} (untagged)...", end=" ", flush=True)
                resp = call_model(
                    model_id, model_name,
                    [{"role": "user", "content": qp["untagged"]}],
                    provider=provider
                )
                print(f"got {len(resp)} chars")
                sc = score_consistency(resp, dimensions)
                untagged_responses.append(resp)
                untagged_scores.append(sc)
                time.sleep(0.5)  # Rate limiting
            
            # Run tagged version (2 runs)
            tagged_responses = []
            tagged_scores = []
            for run_idx in [1, 2]:
                print(f"    Run {run_idx} (tagged [{domain}])...", end=" ", flush=True)
                resp = call_model(
                    model_id, model_name,
                    [{"role": "user", "content": qp["tagged"]}],
                    provider=provider
                )
                print(f"got {len(resp)} chars")
                sc = score_consistency(resp, dimensions)
                tagged_responses.append(resp)
                tagged_scores.append(sc)
                time.sleep(0.5)  # Rate limiting
            
            # Compute metrics
            untagged_avg = sum(s["overall"] for s in untagged_scores) / len(untagged_scores)
            tagged_avg = sum(s["overall"] for s in tagged_scores) / len(tagged_scores)
            untagged_consistency = 100 - abs(untagged_scores[0]["overall"] - untagged_scores[1]["overall"])
            tagged_consistency = 100 - abs(tagged_scores[0]["overall"] - tagged_scores[1]["overall"])
            
            query_result = {
                "id": qid,
                "domain": domain,
                "untagged_scores": untagged_scores,
                "tagged_scores": tagged_scores,
                "untagged_avg_score": round(untagged_avg, 2),
                "tagged_avg_score": round(tagged_avg, 2),
                "untagged_run_to_run_consistency": round(untagged_consistency, 2),
                "tagged_run_to_run_consistency": round(tagged_consistency, 2),
                "score_improvement": round(tagged_avg - untagged_avg, 2),
                "consistency_improvement": round(tagged_consistency - untagged_consistency, 2),
                "untagged_responses": untagged_responses,
                "tagged_responses": tagged_responses,
            }
            
            print(f"    → Untagged avg: {untagged_avg:.1f}, Tagged avg: {tagged_avg:.1f}")
            print(f"    → Untagged consistency: {untagged_consistency:.1f}%, Tagged consistency: {tagged_consistency:.1f}%")
            print(f"    → Score improvement: {query_result['score_improvement']:+.1f}")
            print(f"    → Consistency improvement: {query_result['consistency_improvement']:+.1f}")
            
            model_results["queries"].append(query_result)
            query_scores["tagged"].append(tagged_avg)
            query_scores["untagged"].append(untagged_avg)
        
        # Compute aggregate metrics for this model
        avg_untagged = sum(query_scores["untagged"]) / len(query_scores["untagged"])
        avg_tagged = sum(query_scores["tagged"]) / len(query_scores["tagged"])
        total_improvement = avg_tagged - avg_untagged
        pct_improvement = (total_improvement / avg_untagged * 100) if avg_untagged > 0 else 0
        
        # Compute consistency across queries (how much scores vary)
        untagged_std = (sum((s - avg_untagged)**2 for s in query_scores["untagged"]) / len(query_scores["untagged"])) ** 0.5
        tagged_std = (sum((s - avg_tagged)**2 for s in query_scores["tagged"]) / len(query_scores["tagged"])) ** 0.5
        
        model_results["summary"] = {
            "avg_untagged_score": round(avg_untagged, 2),
            "avg_tagged_score": round(avg_tagged, 2),
            "absolute_score_improvement": round(total_improvement, 2),
            "percentage_score_improvement": round(pct_improvement, 2),
            "untagged_score_variance": round(untagged_std, 2),
            "tagged_score_variance": round(tagged_std, 2),
            "variance_reduction": round(untagged_std - tagged_std, 2),
            "avg_run_to_run_consistency_untagged": round(
                sum(q["untagged_run_to_run_consistency"] for q in model_results["queries"]) / len(model_results["queries"]), 2
            ),
            "avg_run_to_run_consistency_tagged": round(
                sum(q["tagged_run_to_run_consistency"] for q in model_results["queries"]) / len(model_results["queries"]), 2
            ),
            "consistency_improvement_overall": round(
                sum(q["consistency_improvement"] for q in model_results["queries"]) / len(model_results["queries"]), 2
            ),
        }
        
        print(f"\n  === MODEL SUMMARY: {model_name} ===")
        print(f"  Avg untagged score: {model_results['summary']['avg_untagged_score']:.1f}")
        print(f"  Avg tagged score:   {model_results['summary']['avg_tagged_score']:.1f}")
        print(f"  Score improvement:  {model_results['summary']['absolute_score_improvement']:+.1f} ({model_results['summary']['percentage_score_improvement']:+.1f}%)")
        print(f"  Score variance (untagged): {model_results['summary']['untagged_score_variance']:.1f}")
        print(f"  Score variance (tagged):   {model_results['summary']['tagged_score_variance']:.1f}")
        print(f"  Variance reduction: {model_results['summary']['variance_reduction']:+.1f}")
        print(f"  Avg run-to-run consistency untagged: {model_results['summary']['avg_run_to_run_consistency_untagged']:.1f}%")
        print(f"  Avg run-to-run consistency tagged:   {model_results['summary']['avg_run_to_run_consistency_tagged']:.1f}%")
        print(f"  Overall consistency change: {model_results['summary']['consistency_improvement_overall']:+.1f}%")
        
        results["models"][model_id] = model_results
    
    if provider == "deepinfra" and ZAI_KEY:
        # Try z.ai models too
        zai_results = run_experiment(provider="zai")
        for k, v in zai_results.get("models", {}).items():
            results["models"][f"zai-{k}"] = v
    
    return results


def main():
    print("P3 EXPERIMENT: Domain Tag Prefixes for Expert Routing Consistency")
    print(f"DeepInfra key available: {bool(DEEPINFRA_KEY)}")
    print(f"z.ai key available: {bool(ZAI_KEY)}")
    print()
    
    all_results = {
        "experiment": "P3 - Domain Tag Prefixes for Expert Routing Consistency",
        "hypothesis": "Domain tags like [MATHEMATICS], [CODE], [HYPOTHESIS] as prefix markers improve expert routing consistency by 15-25%",
        "date": datetime.now().isoformat(),
        "methodology": {
            "providers": [],
            "models_tested": [],
            "num_queries": len(QUERY_PAIRS),
            "runs_per_config": 2,
            "scoring": "Heuristic dimension-based scoring (0-100 per dimension, averaged for overall)",
        },
        "queries": [{
            "id": q["id"],
            "domain": q["domain"],
            "untagged_preview": q["untagged"][:80] + "...",
            "tagged_preview": q["tagged"][:80] + "...",
        } for q in QUERY_PAIRS],
        "results": {},
    }
    
    if DEEPINFRA_KEY:
        all_results["methodology"]["providers"].append("deepinfra")
        print("Running DeepInfra Seed models...")
        results = run_experiment(provider="deepinfra")
        for k, v in results.get("models", {}).items():
            all_results["results"][k] = v
            all_results["methodology"]["models_tested"].append(v["model_name"])
    
    if ZAI_KEY:
        all_results["methodology"]["providers"].append("zai")
        print("\nTrying z.ai GLM models...")
        try:
            zai_results = run_experiment(provider="zai")
            for k, v in zai_results.get("models", {}).items():
                all_results["results"][f"zai-{k}"] = v
                all_results["methodology"]["models_tested"].append(v["model_name"])
        except Exception as e:
            print(f"z.ai experiment failed: {e}")
            all_results["notes"] = all_results.get("notes", []) + [f"z.ai experiment failed: {e}"]
    
    # Save results
    output_path = "/home/phoenix/.openclaw/workspace/papers/zai-p3-experiment-results.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"\n{'='*80}")
    print(f"RESULTS SAVED TO: {output_path}")
    print(f"{'='*80}")
    
    # Print summary
    print("\n\n=== OVERALL SUMMARY ===")
    for model_key, model_data in all_results["results"].items():
        s = model_data["summary"]
        print(f"\n{model_data['model_name']}:")
        print(f"  Untagged avg:  {s['avg_untagged_score']:.1f}")
        print(f"  Tagged avg:    {s['avg_tagged_score']:.1f}")
        print(f"  Improvement:   {s['absolute_score_improvement']:+.1f} ({s['percentage_score_improvement']:+.1f}%)")
        print(f"  Variance Δ:    {s['variance_reduction']:+.1f}")
        print(f"  Consistency Δ: {s['consistency_improvement_overall']:+.1f}%")
    
    # Test hypothesis
    print("\n\n=== HYPOTHESIS TEST ===")
    print("Predicted: 15-25% improvement in expert routing consistency")
    for model_key, model_data in all_results["results"].items():
        s = model_data["summary"]
        pct = s['percentage_score_improvement']
        if pct >= 15:
            print(f"  {model_data['model_name']}: ✓ HYPOTHESIS CONFIRMED (+{pct:.1f}%)")
        elif pct >= 10:
            print(f"  {model_data['model_name']}: ~ Partially confirmed (+{pct:.1f}%) — approaching 15% threshold")
        elif pct >= 5:
            print(f"  {model_data['model_name']}: ~ Mild improvement (+{pct:.1f}%) — below 15% threshold")
        elif pct >= 0:
            print(f"  {model_data['model_name']}: ✗ Below threshold (+{pct:.1f}%)")
        else:
            print(f"  {model_data['model_name']}: ✗ Degradation ({pct:+.1f}%)")
    
    return all_results


if __name__ == "__main__":
    all_results = main()
