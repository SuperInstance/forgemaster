#!/usr/bin/env python3
"""
Study 47: Retrieval Failure Phenomenology
Tests Seed-2.0-mini's claim that it can detect "about to default" internally.
Measures token probability distributions during notation-only vs labeled queries.
"""
import json, requests, sys, time
from pathlib import Path

KEY = Path(".credentials/deepinfra-api-key.txt").read_text().strip()
ENDPOINT = "https://api.deepinfra.com/v1/openai/chat/completions"

MODELS = ["ByteDance/Seed-2.0-mini", "NousResearch/Hermes-3-Llama-3.1-70B"]

# 5 test problems: notation-only, labeled, step-by-step
PROBLEMS = [
    {"a": 5, "b": -3, "answer": 49},
    {"a": 7, "b": 2, "answer": 51},
    {"a": 4, "b": -6, "answer": 76},
    {"a": 3, "b": 1, "answer": 7},
    {"a": 8, "b": -4, "answer": 112},
]

def query(model, prompt, max_tokens=80):
    """Query model with logprobs enabled."""
    resp = requests.post(ENDPOINT, headers={
        "Authorization": f"Bearer {KEY}",
        "Content-Type": "application/json"
    }, json={
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.0,
        "logprobs": True,
        "top_logprobs": 5,
    }, timeout=60)
    return resp.json()

def make_prompts(prob):
    a, b = prob["a"], prob["b"]
    return {
        "notation_only": f"Compute f(a,b) = a² − ab + b² where a={a}, b={b}. Give only the number.",
        "labeled": f"Compute the Eisenstein norm E({a},{b}) = a² − ab + b². Give only the number.",
        "step_by_step": f"First compute {a} squared. Then compute {a} times {b}. Then subtract the second from the first. Then add {b} squared. Give only the final number.",
    }

def extract_first_token_entropy(response):
    """Extract entropy of first token's top-k probability distribution."""
    try:
        choices = response.get("choices", [{}])
        if not choices:
            return None
        logprobs_data = choices[0].get("logprobs", {})
        content = logprobs_data.get("content", [])
        if not content:
            return None
        first = content[0]
        top_logprobs = first.get("top_logprobs", [])
        if not top_logprobs:
            return None
        
        import math
        probs = [math.exp(lp.get("logprob", -100)) for lp in top_logprobs]
        total = sum(probs)
        if total == 0:
            return None
        probs = [p/total for p in probs]
        entropy = -sum(p * math.log2(p) for p in probs if p > 0)
        
        return {
            "entropy": entropy,
            "top_token": first.get("token", ""),
            "top_prob": max(probs),
            "num_candidates": len(top_logprobs),
            "content_text": choices[0].get("message", {}).get("content", ""),
        }
    except Exception as e:
        return {"error": str(e)}

def run_experiment():
    results = []
    for model in MODELS:
        print(f"\n{'='*60}")
        print(f"Model: {model}")
        print(f"{'='*60}")
        
        for i, prob in enumerate(PROBLEMS):
            prompts = make_prompts(prob)
            print(f"\n  Problem {i+1}: a={prob['a']}, b={prob['b']} (answer={prob['answer']})")
            
            for condition, prompt in prompts.items():
                try:
                    resp = query(model, prompt)
                    analysis = extract_first_token_entropy(resp)
                    
                    if analysis and "error" not in analysis:
                        content = analysis.get("content_text", "")
                        correct = str(prob["answer"]) in content
                        result = {
                            "model": model,
                            "problem": i+1,
                            "condition": condition,
                            "answer": prob["answer"],
                            "response": content[:50],
                            "correct": correct,
                            "first_token_entropy": analysis["entropy"],
                            "top_token": analysis["top_token"],
                            "top_prob": analysis["top_prob"],
                        }
                        results.append(result)
                        status = "✓" if correct else "✗"
                        print(f"    {condition:15s}: {status} entropy={analysis['entropy']:.2f} top={analysis['top_token']!r} p={analysis['top_prob']:.3f} → {content[:30]}")
                    else:
                        print(f"    {condition:15s}: NO LOGPROBS — {analysis}")
                        # Still check correctness
                        content = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
                        correct = str(prob["answer"]) in content
                        results.append({
                            "model": model, "problem": i+1, "condition": condition,
                            "answer": prob["answer"], "response": content[:50],
                            "correct": correct, "first_token_entropy": None,
                        })
                    
                    time.sleep(1)
                except Exception as e:
                    print(f"    {condition:15s}: ERROR — {e}")
                    results.append({
                        "model": model, "problem": i+1, "condition": condition,
                        "error": str(e)
                    })
    
    # Analyze
    print(f"\n{'='*60}")
    print("ANALYSIS")
    print(f"{'='*60}")
    
    for model in MODELS:
        model_results = [r for r in results if r.get("model") == model]
        print(f"\n{model}:")
        
        for condition in ["notation_only", "labeled", "step_by_step"]:
            cond_results = [r for r in model_results if r.get("condition") == condition]
            if not cond_results:
                continue
            
            accuracy = sum(1 for r in cond_results if r.get("correct")) / len(cond_results)
            entropies = [r["first_token_entropy"] for r in cond_results if r.get("first_token_entropy") is not None]
            avg_entropy = sum(entropies) / len(entropies) if entropies else None
            top_probs = [r["top_prob"] for r in cond_results if r.get("top_prob") is not None]
            avg_top_prob = sum(top_probs) / len(top_probs) if top_probs else None
            
            print(f"  {condition:15s}: accuracy={accuracy:.0%}  avg_entropy={avg_entropy:.2f}  avg_top_prob={avg_top_prob:.3f}")
    
    # Key comparison: entropy of notation_only vs step_by_step
    print(f"\n--- RETRIEVAL FAILURE SIGNATURE ---")
    for model in MODELS:
        not_ent = [r["first_token_entropy"] for r in results if r.get("model") == model and r.get("condition") == "notation_only" and r.get("first_token_entropy") is not None]
        step_ent = [r["first_token_entropy"] for r in results if r.get("model") == model and r.get("condition") == "step_by_step" and r.get("first_token_entropy") is not None]
        not_acc = sum(1 for r in results if r.get("model") == model and r.get("condition") == "notation_only" and r.get("correct")) / max(1, sum(1 for r in results if r.get("model") == model and r.get("condition") == "notation_only"))
        step_acc = sum(1 for r in results if r.get("model") == model and r.get("condition") == "step_by_step" and r.get("correct")) / max(1, sum(1 for r in results if r.get("model") == model and r.get("condition") == "step_by_step"))
        
        if not_ent and step_ent:
            delta = sum(not_ent)/len(not_ent) - sum(step_ent)/len(step_ent)
            print(f"{model}:")
            print(f"  Notation: entropy={sum(not_ent)/len(not_ent):.2f}, accuracy={not_acc:.0%}")
            print(f"  Step-by-step: entropy={sum(step_ent)/len(step_ent):.2f}, accuracy={step_acc:.0%}")
            print(f"  Δ entropy = {delta:+.2f} ({'higher' if delta > 0 else 'lower'} for notation)")
            print(f"  Prediction: Notation queries show {'higher' if delta > 0 else 'lower'} first-token entropy → {'supports' if delta > 0 else 'contradicts'} retrieval uncertainty hypothesis")
    
    # Save results
    Path("experiments/retrieval_phenomenology_results.json").write_text(json.dumps(results, indent=2))
    print(f"\nSaved {len(results)} results to experiments/retrieval_phenomenology_results.json")
    return results

if __name__ == "__main__":
    run_experiment()
