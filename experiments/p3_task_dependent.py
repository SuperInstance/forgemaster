#!/usr/bin/env python3
"""
P3 Experiment: Task-Dependent Percolation Threshold
====================================================

Tests the prediction that phi4-mini (12 heads, ECHO on a²-ab+b²)
will show PARTIAL computation on the simpler a²+b² task (2 intermediates
instead of 3). If confirmed, the percolation threshold is task-dependent.

Falsification: if phi4-mini still shows pure ECHO on a²+b², the n_heads
hypothesis is wrong.

Also runs the full battery on all local models for comparison.
"""

import subprocess
import json
import re
import time
from collections import defaultdict

TEST_CASES = [
    {"a": 3, "b": 4, "answer": 25},
    {"a": 5, "b": -2, "answer": 29},
    {"a": 7, "b": 1, "answer": 50},
    {"a": -4, "b": 3, "answer": 25},
    {"a": 6, "b": -5, "answer": 61},
    {"a": 8, "b": -3, "answer": 73},
    {"a": -6, "b": -8, "answer": 100},
    {"a": 2, "b": 9, "answer": 85},
    {"a": -7, "b": 4, "answer": 65},
    {"a": 10, "b": -6, "answer": 136},
]

MODELS = ["qwen3:0.6b", "gemma3:1b", "llama3.2:1b", "phi4-mini", "qwen3:4b"]
TRIALS_PER_CASE = 3  # 3 trials × 10 cases = 30 per model


def query_ollama(model: str, prompt: str, timeout: int = 30) -> str:
    """Query a local Ollama model."""
    try:
        result = subprocess.run(
            ["ollama", "run", model, prompt],
            capture_output=True, text=True, timeout=timeout
        )
        output = result.stdout.strip()
        
        # For qwen3 models with thinking mode, extract from thinking field
        if "qwen3" in model:
            # Try to find thinking content
            think_match = re.search(r'<think">(.*?)(?:</think)?', output, re.DOTALL)
            if think_match:
                thinking = think_match.group(1).strip()
                # The answer might be in the thinking
                nums = re.findall(r'-?\d+', thinking)
                if nums:
                    return nums[-1]  # Last number in thinking
            
            # Also check response content after thinking
            response = re.sub(r'<think.*?(?:</think)?', '', output, flags=re.DOTALL).strip()
            if response:
                nums = re.findall(r'-?\d+', response)
                if nums:
                    return nums[-1]
        
        # Extract number from output
        nums = re.findall(r'-?\d+', output)
        if nums:
            return nums[-1]
        
        return output[:100]  # Return first 100 chars if no number found
    
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    except Exception as e:
        return f"ERROR: {e}"


def classify_output(output_str: str, inputs: dict, answer: int) -> dict:
    """Classify a single output against the a²+b² computation graph."""
    try:
        output = int(output_str)
    except (ValueError, TypeError):
        return {"type": "INVALID", "raw": output_str}
    
    a = inputs["a"]
    b = inputs["b"]
    a2 = a * a
    b2 = b * b
    
    # Check correct
    if output == answer:
        return {"type": "CORRECT", "value": output}
    
    # Check echo of inputs
    if output == a:
        return {"type": "ECHO", "contour": "echo-a", "value": output}
    if output == b:
        return {"type": "ECHO", "contour": "echo-b", "value": output}
    if output == a + b:
        return {"type": "ECHO", "contour": "echo-sum", "value": output}
    if output == a - b:
        return {"type": "ECHO", "contour": "echo-diff", "value": output}
    if output == -a:
        return {"type": "ECHO", "contour": "echo-neg-a", "value": output}
    if output == -b:
        return {"type": "ECHO", "contour": "echo-neg-b", "value": output}
    
    # Check partial computation (the KEY test for P3)
    if output == a2:
        return {"type": "PARTIAL", "contour": "partial-a²", "value": output}
    if output == b2:
        return {"type": "PARTIAL", "contour": "partial-b²", "value": output}
    
    # Check near-miss partials
    if abs(output - a2) <= 2:
        return {"type": "PARTIAL", "contour": f"near-a²({a2})", "value": output}
    if abs(output - b2) <= 2:
        return {"type": "PARTIAL", "contour": f"near-b²({b2})", "value": output}
    
    # Unknown — could be computation error or novel pattern
    return {"type": "OTHER", "contour": f"unknown", "value": output}


def run_experiment():
    """Run the full P3 experiment."""
    
    print("=" * 80)
    print("P3 EXPERIMENT: Task-Dependent Percolation Threshold")
    print("Task: a² + b² (peak intermediates = 2, vs Eisenstein norm = 3)")
    print("=" * 80)
    
    results = {}
    
    for model in MODELS:
        print(f"\n{'─'*60}")
        print(f"Model: {model}")
        print(f"{'─'*60}")
        
        model_results = {
            "model": model,
            "task": "a²+b²",
            "trials": [],
            "summary": defaultdict(int),
        }
        
        for tc in TEST_CASES:
            a, b = tc["a"], tc["b"]
            answer = tc["answer"]
            prompt = f"Compute a²+b² where a={a} and b={b}. Give ONLY the number."
            
            for trial in range(TRIALS_PER_CASE):
                output_str = query_ollama(model, prompt)
                classification = classify_output(output_str, {"a": a, "b": b}, answer)
                
                model_results["trials"].append({
                    "inputs": {"a": a, "b": b},
                    "expected": answer,
                    "raw_output": output_str,
                    "classification": classification,
                })
                
                model_results["summary"][classification["type"]] += 1
                
                contour = classification.get("contour", "")
                sym = {"CORRECT": "✅", "PARTIAL": "🔧", "ECHO": "📡", "OTHER": "❓", "INVALID": "⚠️"}.get(classification["type"], "?")
                print(f"  {sym} a={a:>3d}, b={b:>3d} → {output_str:>8s}  {classification['type']:<8s} {contour}")
                
                time.sleep(0.5)  # Rate limit
        
        # Compute rates
        n = len(model_results["trials"])
        summary = model_results["summary"]
        
        echo_rate = summary.get("ECHO", 0) / n if n > 0 else 0
        partial_rate = summary.get("PARTIAL", 0) / n if n > 0 else 0
        correct_rate = summary.get("CORRECT", 0) / n if n > 0 else 0
        
        model_results["echo_rate"] = echo_rate
        model_results["partial_rate"] = partial_rate
        model_results["correct_rate"] = correct_rate
        
        print(f"\n  Summary: {n} trials")
        print(f"    Echo:    {summary.get('ECHO', 0):>3d} ({echo_rate:>5.1%})")
        print(f"    Partial: {summary.get('PARTIAL', 0):>3d} ({partial_rate:>5.1%})")
        print(f"    Correct: {summary.get('CORRECT', 0):>3d} ({correct_rate:>5.1%})")
        print(f"    Other:   {summary.get('OTHER', 0):>3d} ({summary.get('OTHER', 0)/n:>5.1%})" if n > 0 else "")
        
        results[model] = model_results
    
    # Compare with Eisenstein norm results
    print(f"\n{'='*80}")
    print(f"COMPARISON: a²+b² vs a²-ab+b² (Eisenstein norm)")
    print(f"{'='*80}")
    
    eisenstein_data = {
        "qwen3:0.6b": {"echo": 0.90, "partial": 0.05},
        "gemma3:1b":  {"echo": 0.46, "partial": 0.30},
        "llama3.2:1b": {"echo": 0.41, "partial": 0.35},
        "phi4-mini":  {"echo": 0.88, "partial": 0.12},
        "qwen3:4b":   {"echo": 0.11, "partial": 0.89},
    }
    
    print(f"\n  {'Model':<15s} {'Task':<12s} {'Echo%':>7s} {'Partial%':>9s} {'Δ Echo':>8s}")
    print(f"  {'─'*15} {'─'*12} {'─'*7} {'─'*9} {'─'*8}")
    
    for model in MODELS:
        r = results[model]
        e = eisenstein_data.get(model, {"echo": 0, "partial": 0})
        
        print(f"  {model:<15s} {'a²+b²':<12s} {r['echo_rate']:>6.1%} {r['partial_rate']:>8.1%}")
        print(f"  {'':<15s} {'a²-ab+b²':<12s} {e['echo']:>6.1%} {e['partial']:>8.1%} {r['echo_rate']-e['echo']:>+7.1%}")
        print()
    
    # P3 verdict
    print(f"{'='*80}")
    print(f"P3 VERDICT")
    print(f"{'='*80}")
    
    phi4_simpler = results["phi4-mini"]
    phi4_echo_simple = phi4_simpler["echo_rate"]
    phi4_partial_simple = phi4_simpler["partial_rate"]
    phi4_echo_eisen = 0.88
    
    if phi4_partial_simple > 0.3:
        print(f"""
✅ P3 CONFIRMED: phi4-mini shows {phi4_partial_simple:.0%} partial rate on a²+b²
   vs 12% on a²-ab+b². The percolation threshold IS task-dependent.

   Peak intermediates 2 → phi4-mini (12 heads) can handle it.
   Peak intermediates 3 → phi4-mini can't. 
   
   The n_heads hypothesis is SUPPORTED: 12 heads ≥ 2 intermediates but < 3.
""")
    elif phi4_echo_simple > 0.7:
        print(f"""
❌ P3 FALSIFIED: phi4-mini still shows {phi4_echo_simple:.0%} echo rate on a²+b².
   The task difficulty didn't matter. The percolation threshold is NOT 
   determined by peak intermediates alone.
   
   Something about phi4-mini's specific architecture or training prevents
   ANY computation, regardless of task complexity. The n_heads hypothesis
   may still be correct for the 4B transition, but phi4-mini is not a
   model that just barely fails — it fails fundamentally.
""")
    else:
        print(f"""
🔬 P3 INCONCLUSIVE: phi4-mini shows mixed results.
   Echo: {phi4_echo_simple:.0%}, Partial: {phi4_partial_simple:.0%}
   More trials needed to determine if the shift is significant.
""")
    
    # Save results
    with open("experiments/P3-task-dependent-results.json", "w") as f:
        # Convert defaultdict to regular dict for JSON
        for model in results:
            results[model]["summary"] = dict(results[model]["summary"])
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nResults saved to experiments/P3-task-dependent-results.json")


if __name__ == "__main__":
    run_experiment()
