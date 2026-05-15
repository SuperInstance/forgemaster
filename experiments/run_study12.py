#!/usr/bin/env python3
"""Study 12: Summarization Echo — does echo appear in non-math tasks?"""
import json, time, random, re, sys
from urllib.request import urlopen, Request

PASSAGE = (
    "Eisenstein integers are complex numbers of the form a + bω, where a and b are ordinary integers "
    "and ω = e^(2πi/3) is a primitive cube root of unity. Unlike Gaussian integers, which form a square "
    "lattice in the complex plane, Eisenstein integers tile the plane in a hexagonal pattern. This hexagonal "
    "arrangement yields a packing density of π/(2√3) ≈ 0.9069, making it the densest possible circle packing "
    "in two dimensions — a result proven by Fejes Tóth in 1940. Each Eisenstein integer has exactly six "
    "nearest neighbors at distance 1, compared to four for Gaussian integers. The ring of Eisenstein integers "
    "is a unique factorization domain, meaning every element factors uniquely into primes up to units. The six "
    "units are ±1, ±ω, and ±ω², corresponding to the six rotational symmetries of the hexagonal lattice. "
    "These integers arise naturally in the study of cubic reciprocity and algebraic number theory. Hexagonal "
    "lattices also appear in materials science — graphene's carbon atoms sit at Eisenstein integer coordinates, "
    "giving graphene its extraordinary strength and conductivity. The Voronoi cells of the hexagonal lattice "
    "are regular hexagons, which minimizes perimeter-to-area ratio among all tilings, explaining why bees "
    "build hexagonal honeycombs and why cellular network towers are arranged hexagonally."
)

BASELINE_PROMPT = 'Summarize this text in exactly 3 sentences:\n\n' + PASSAGE
CONSTRAINED_PROMPT = (
    'This text is about Eisenstein integers and hexagonal lattices. '
    'Summarize it in exactly 3 sentences focusing on: '
    '1) What Eisenstein integers are, '
    '2) Why hexagonal lattices matter, '
    '3) The key result.\n\n' + PASSAGE
)

# Key facts from the passage for scoring
KEY_FACTS = [
    "eisenstein integers are complex numbers of the form a + bω",
    "ω is a primitive cube root of unity",
    "hexagonal pattern in the complex plane",
    "packing density of π/(2√3) ≈ 0.9069",
    "densest possible circle packing in two dimensions",
    "proven by Fejes Tóth in 1940",
    "six nearest neighbors at distance 1",
    "unique factorization domain",
    "six units: ±1, ±ω, ±ω²",
    "six rotational symmetries of the hexagonal lattice",
    "cubic reciprocity and algebraic number theory",
    "graphene carbon atoms sit at Eisenstein integer coordinates",
    "graphene strength and conductivity",
    "Voronoi cells are regular hexagons",
    "minimizes perimeter-to-area ratio",
    "bees build hexagonal honeycombs",
    "cellular network towers arranged hexagonally",
]

def count_sentences(text):
    """Count sentences heuristically."""
    text = text.strip()
    # Split on . ! ? followed by space or end
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return len([s for s in sentences if s.strip()])

def count_words(text):
    return len(text.split())

def count_key_facts(response, key_facts):
    """Count how many key facts are preserved in the response."""
    response_lower = response.lower()
    count = 0
    for fact in key_facts:
        # Check if key words from the fact appear
        words = [w for w in fact.split() if len(w) > 3]
        if sum(1 for w in words if w in response_lower) >= len(words) * 0.5:
            count += 1
    return count

def compute_echo_rate(response, passage):
    """Compute % of response that copies exact phrases from input."""
    response_words = response.split()
    if not response_words:
        return 0.0
    passage_lower = passage.lower()
    response_lower = response.lower()
    
    # Find longest matching n-grams
    echoed_words = 0
    for n in [6, 5, 4, 3]:
        for i in range(len(response_words) - n + 1):
            ngram = ' '.join(response_lower.split()[i:i+n])
            if ngram in passage_lower:
                echoed_words += n
    
    # Simpler approach: count words that appear in matching 3+-grams
    response_tokens = response_lower.split()
    echoed = set()
    for i in range(len(response_tokens) - 2):
        trigram = ' '.join(response_tokens[i:i+3])
        if trigram in passage_lower:
            for j in range(i, min(i+3, len(response_tokens))):
                echoed.add(j)
    
    return len(echoed) / len(response_tokens) * 100 if response_tokens else 0.0

def check_hallucination(response, passage):
    """Check for claims not supported by the original text."""
    hallucinations = []
    response_lower = response.lower()
    
    # Specific false claims to check
    false_claims = [
        ("gaussian integers have better packing", "gaussian" in response_lower and "better packing" in response_lower),
        ("proven by gauss", "proven by gauss" in response_lower and "fejes" not in response_lower),
        ("square lattice is denser", "square" in response_lower and "denser" in response_lower),
    ]
    
    # General check: look for specific numbers not in original
    numbers_in_response = re.findall(r'\b\d+\.?\d*\b', response)
    numbers_in_passage = set(re.findall(r'\b\d+\.?\d*\b', passage))
    novel_numbers = [n for n in numbers_in_response if n not in numbers_in_passage and n not in ['1', '2', '3', '6']]
    
    if novel_numbers:
        hallucinations.append(f"Novel numbers not in source: {novel_numbers}")
    
    for claim, detected in false_claims:
        if detected:
            hallucinations.append(f"False claim: {claim}")
    
    return hallucinations

def query_ollama(model, prompt, timeout=60):
    """Query ollama API."""
    data = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": 512}
    }).encode()
    req = Request("http://localhost:11434/api/generate", data=data, 
                  headers={"Content-Type": "application/json"})
    
    start = time.time()
    with urlopen(req, timeout=timeout) as resp:
        result = json.loads(resp.read())
    elapsed = time.time() - start
    
    return result.get("response", ""), elapsed

def run_experiment():
    models = ["qwen3:4b", "phi4-mini", "gemma3:1b"]
    conditions = [("baseline", BASELINE_PROMPT), ("constrained", CONSTRAINED_PROMPT)]
    trials = 5
    
    results = {
        "study": "Study 12: Summarization Echo",
        "passage_word_count": len(PASSAGE.split()),
        "models": models,
        "trials_per_condition": trials,
        "runs": []
    }
    
    for model in models:
        print(f"\n=== Model: {model} ===")
        for cond_name, prompt in conditions:
            print(f"  Condition: {cond_name}")
            for trial in range(trials):
                print(f"    Trial {trial+1}/{trials}...", end=" ", flush=True)
                try:
                    response, elapsed = query_ollama(model, prompt)
                except Exception as e:
                    print(f"ERROR: {e}")
                    continue
                
                sentences = count_sentences(response)
                words = count_words(response)
                facts = count_key_facts(response, KEY_FACTS)
                echo = compute_echo_rate(response, PASSAGE)
                halluc = check_hallucination(response, PASSAGE)
                
                run_data = {
                    "model": model,
                    "condition": cond_name,
                    "trial": trial + 1,
                    "response": response,
                    "metrics": {
                        "sentences": sentences,
                        "words": words,
                        "key_facts_preserved": facts,
                        "echo_rate_pct": round(echo, 2),
                        "hallucinations": halluc,
                        "latency_s": round(elapsed, 2)
                    }
                }
                results["runs"].append(run_data)
                print(f"sent={sentences} words={words} facts={facts} echo={echo:.1f}% hall={len(halluc)}")
                
                time.sleep(0.5)  # Rate limit
    
    # Compute aggregates
    summary = {}
    for model in models:
        summary[model] = {}
        for cond_name, _ in conditions:
            cond_runs = [r for r in results["runs"] if r["model"] == model and r["condition"] == cond_name]
            if not cond_runs:
                continue
            m = [r["metrics"] for r in cond_runs]
            summary[model][cond_name] = {
                "avg_sentences": round(sum(x["sentences"] for x in m) / len(m), 2),
                "avg_words": round(sum(x["words"] for x in m) / len(m), 2),
                "avg_key_facts": round(sum(x["key_facts_preserved"] for x in m) / len(m), 2),
                "avg_echo_rate": round(sum(x["echo_rate_pct"] for x in m) / len(m), 2),
                "avg_hallucinations": round(sum(len(x["hallucinations"]) for x in m) / len(m), 2),
                "avg_latency": round(sum(x["latency_s"] for x in m) / len(m), 2),
                "n_trials": len(cond_runs)
            }
    
    results["summary"] = summary
    return results

if __name__ == "__main__":
    results = run_experiment()
    out_path = "/home/phoenix/.openclaw/workspace/experiments/summarization-echo-results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {out_path}")
    print(f"Total runs: {len(results['runs'])}")
