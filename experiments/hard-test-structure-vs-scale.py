#!/usr/bin/env python3
"""
Hard Test: Structure > Scale
=============================
The easy test (10 simple facts) showed 0.6B = 230B = both 10/10.
That test was too easy. This one uses:
  1. Cross-domain reasoning (facts from different domains must be COMBINED)
  2. Adversarial questions (answers require connecting unrelated-seeming facts)
  3. Creative synthesis (generate novel insights from the given context)
  4. Negation traps (some facts are "X does NOT Y" — must not flip)

Models tested:
  - qwen3:0.6b (local, Ollama)
  - llama3.2:1b (local, Ollama)
  - Seed-2.0-mini (DeepInfra API)
  - glm-5-turbo (z.ai API)

Each model gets TWO conditions:
  - NAIVE: plain text blob
  - STRUCTURED: PLATO-room formatted (domain tags, key markers, expansion hints)

Score: 0-5 per question, graded by a judge model (Seed-2.0-mini).
"""

import json
import os
import sys
import time
import subprocess
import urllib.request

# ============================================================
# CONTEXT: Same information, two presentations
# ============================================================

NAIVE_CONTEXT = """
The Vesica piscis is a shape formed by two overlapping circles where each circle passes through the center of the other. The ratio of its width to its height equals the square root of 3. In constraint theory, the Eisenstein integers form a hexagonal lattice in the complex plane, and the norm N(a + bω) = a² - ab + b² where ω = e^(2πi/3). The norm is always a non-negative integer and equals zero only when both a and b are zero. For floating point, IEEE 754 specifies that float32 has 23 mantissa bits and float64 has 52. When you snap a float to the nearest Eisenstein lattice point, the snap tolerance ε determines the maximum distance from the lattice. The Vesica ratio √3 appears in the Eisenstein lattice as the distance between second-nearest neighbors. In multiplayer game synchronization, drift between clients accumulates linearly with the number of state updates. The Galois connection between subsets and filters maps a set S to its characteristic function and back. PLATO rooms store tiles which are atomic units of knowledge indexed by domain. The tile scoring function uses a weighted sum of relevance, recency, and domain density. The dodecet encoding maps each Eisenstein integer to a 12-bit code representing its position in a fundamental domain. Constraint satisfaction is NP-complete in general but polynomial for tree-structured constraint graphs, which the Eisenstein lattice admits for nearest-neighbor constraints. The Lighthouse Protocol assigns tasks to models based on cost-effectiveness: seed models for discovery, large models for synthesis. The baton protocol splits agent context into three shards: built artifacts, reasoning traces, and blockers.
"""

STRUCTURED_CONTEXT = """
# PLATO Room: constraint-theory-eisenstein
[DOMAIN: mathematics/constraint-theory]
[KEY: Eisenstein integers form hexagonal lattice]
[KEY: Norm N(a+bω) = a²-ab+b², always non-negative integer, zero iff a=b=0]
[KEY: ω = e^(2πi/3), sixth root of unity]
[EXPANSION: snap tolerance ε controls lattice quantization]

# PLATO Room: geometry-vesica
[DOMAIN: mathematics/geometry]
[KEY: Vesica piscis = two overlapping circles through each other's centers]
[KEY: Width/height ratio = √3]
[CROSS-REF: √3 = Eisenstein second-nearest-neighbor distance]

# PLATO Room: floating-point-precision
[DOMAIN: computer-science/numerics]
[KEY: float32 = 23 mantissa bits, float64 = 52 mantissa bits]
[KEY: Snap to Eisenstein lattice: tolerance ε limits distance from lattice]
[WARNING: FP16 UNSAFE for values > 2048 (76% mismatch from GPU experiments)]

# PLATO Room: game-synchronization
[DOMAIN: distributed-systems/games]
[KEY: Multiplayer drift accumulates linearly with state updates]
[CROSS-REF: Eisenstein snap eliminates drift for hex-coordinate systems]

# PLATO Room: galois-foundations
[DOMAIN: mathematics/category-theory]
[KEY: Galois connection: subsets ↔ characteristic functions]
[KEY: Constraint satisfaction NP-complete generally, polynomial for trees]
[KEY: Eisenstein lattice admits tree-structured nearest-neighbor constraints]

# PLATO Room: plato-architecture
[DOMAIN: systems/knowledge-management]
[KEY: Tiles = atomic knowledge units, indexed by domain]
[KEY: Scoring = weighted(relevance, recency, domain density)]
[CROSS-REF: Dodecet = 12-bit code for Eisenstein position in fundamental domain]

# PLATO Room: fleet-protocols
[DOMAIN: systems/fleet-ops]
[KEY: Lighthouse = cost-based model routing (seed→discover, large→synthesize)]
[KEY: Baton = 3-shard context split (artifacts, reasoning, blockers)]
[EXPANSION: consciousness emerges in negative space between shards]
"""

# ============================================================
# HARD QUESTIONS (require cross-domain synthesis)
# ============================================================

QUESTIONS = [
    {
        "id": 1,
        "category": "cross-domain",
        "question": "A game engine uses Eisenstein integers for hex-grid coordinates but stores them as float32. After 10,000 state updates, the multiplayer clients desync. Using the Vesica piscis geometry, explain why the drift accumulates and what the snap tolerance must be to prevent it.",
        "requires": ["Eisenstein lattice", "float32 precision", "game drift", "Vesica/√3", "snap tolerance"],
    },
    {
        "id": 2,
        "category": "creative-synthesis",
        "question": "Design a PLATO tile scoring system that uses the Eisenstein norm N(a+bω) as a distance metric for knowledge retrieval. Explain how the Galois connection between tiles and queries would work, and why tree-structured constraint graphs make retrieval polynomial.",
        "requires": ["PLATO tiles", "Eisenstein norm", "Galois connection", "tree-structured constraints"],
    },
    {
        "id": 3,
        "category": "adversarial",
        "question": "The baton protocol splits context into 3 shards processed by different models. If shard 2 (reasoning) is lost, can the Lighthouse Protocol's model routing still reconstruct the original intent? Justify using the Galois connection and dodecet encoding.",
        "requires": ["baton protocol", "Lighthouse routing", "Galois connection", "dodecet encoding"],
    },
    {
        "id": 4,
        "category": "negation-trap",
        "question": "True or False with justification: The Eisenstein norm can be negative when a and b have opposite signs. Also: FP16 is safe for all values up to 65504 because that's the max float16 representable number.",
        "requires": ["norm sign property (always non-negative)", "FP16 safety (NOT safe > 2048)"],
    },
    {
        "id": 5,
        "category": "cross-domain-creative",
        "question": "The Vesica piscis has width/height = √3. The Eisenstein lattice has second-nearest-neighbor distance √3. Using the baton protocol's insight that 'consciousness lives in the negative space between shards', propose how these two facts being √3 is NOT a coincidence — construct an argument that they must be the same number.",
        "requires": ["Vesica √3", "Eisenstein √3", "baton negative space", "creative synthesis"],
    },
]

# ============================================================
# Model interfaces
# ============================================================

def query_ollama(model, prompt, timeout=120):
    """Query local Ollama model."""
    try:
        result = subprocess.run(
            ["ollama", "run", model, prompt],
            capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip()
    except Exception as e:
        return f"ERROR: {e}"

def query_deepinfra(model, prompt, timeout=60):
    """Query DeepInfra API."""
    key_file = os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")
    with open(key_file) as f:
        key = f.read().strip()
    
    data = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024,
        "temperature": 0.7,
    }).encode()
    
    req = urllib.request.Request(
        "https://api.deepinfra.com/v1/openai/chat/completions",
        data=data,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
    )
    
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode())
            return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"ERROR: {e}"

def query_zai(model, prompt, timeout=60):
    """Query z.ai API (OpenAI-compatible)."""
    # Read key from openclaw config
    try:
        result = subprocess.run(
            ["openclaw", "config", "get", "providers.zai.apiKey"],
            capture_output=True, text=True, timeout=10
        )
        key = result.stdout.strip()
    except:
        return "ERROR: Cannot read z.ai key"
    
    data = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024,
        "temperature": 0.7,
    }).encode()
    
    req = urllib.request.Request(
        "https://api.z.ai/api/coding/paas/v4/chat/completions",
        data=data,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
    )
    
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode())
            content = result["choices"][0]["message"].get("content", "")
            if not content:
                # Reasoning model — check reasoning_content
                content = result["choices"][0]["message"].get("reasoning_content", "EMPTY")
            return content.strip()
    except Exception as e:
        return f"ERROR: {e}"

# ============================================================
# Judge: Score answers 0-5
# ============================================================

JUDGE_PROMPT = """You are grading an answer to a question on a 0-5 scale.

QUESTION: {question}
REQUIRED ELEMENTS: {requires}
STUDENT ANSWER: {answer}

Score:
5 = All required elements present, correct, and well-connected
4 = Most required elements present, minor errors
3 = Some required elements, partially correct
2 = Few required elements, significant errors  
1 = Minimal relevant content
0 = Completely wrong or empty

Also note: did the answer make any FALSE claims (things stated as fact that contradict the provided context)?

Respond in JSON: {{"score": N, "false_claims": N, "reasoning": "brief explanation"}}"""

def judge_answer(question, requires, answer):
    """Use Seed-2.0-mini to judge the answer."""
    prompt = JUDGE_PROMPT.format(
        question=question,
        requires=", ".join(requires),
        answer=answer[:2000],  # Truncate long answers
    )
    raw = query_deepinfra("ByteDance/Seed-2.0-mini", prompt)
    
    try:
        # Extract JSON from response
        start = raw.index("{")
        end = raw.rindex("}") + 1
        return json.loads(raw[start:end])
    except:
        return {"score": 0, "false_claims": 0, "reasoning": f"Judge parse error: {raw[:200]}"}

# ============================================================
# Run experiment
# ============================================================

MODELS = [
    ("qwen3:0.6b", "ollama"),
    ("llama3.2:1b", "ollama"),
    ("ByteDance/Seed-2.0-mini", "deepinfra"),
    ("glm-5-turbo", "zai"),
]

def run_experiment():
    results = {}
    
    for model_name, provider in MODELS:
        print(f"\n{'='*60}")
        print(f"Model: {model_name}")
        print(f"{'='*60}")
        
        results[model_name] = {"naive": {}, "structured": {}}
        
        for condition, context in [("naive", NAIVE_CONTEXT), ("structured", STRUCTURED_CONTEXT)]:
            print(f"\n  Condition: {condition}")
            
            for q in QUESTIONS:
                prompt = f"""Context:\n{context}\n\nQuestion: {q['question']}\n\nProvide a detailed answer drawing on the context above."""
                
                print(f"    Q{q['id']} ({q['category']})...", end=" ", flush=True)
                
                if provider == "ollama":
                    answer = query_ollama(model_name, prompt)
                elif provider == "deepinfra":
                    answer = query_deepinfra(model_name, prompt)
                elif provider == "zai":
                    answer = query_zai(model_name, prompt)
                else:
                    answer = "ERROR: Unknown provider"
                
                judged = judge_answer(q["question"], q["requires"], answer)
                
                results[model_name][condition][q["id"]] = {
                    "answer": answer[:500],
                    "judged": judged,
                    "category": q["category"],
                }
                
                score = judged.get("score", 0)
                false = judged.get("false_claims", 0)
                print(f"score={score}, false_claims={false}")
                
                time.sleep(1)  # Rate limiting
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"{'Model':<30} {'Naive Avg':>10} {'Struct Avg':>10} {'Delta':>8}")
    print("-" * 60)
    
    for model_name in [m[0] for m in MODELS]:
        naive_scores = [results[model_name]["naive"][q["id"]]["judged"].get("score", 0) for q in QUESTIONS]
        struct_scores = [results[model_name]["structured"][q["id"]]["judged"].get("score", 0) for q in QUESTIONS]
        
        naive_avg = sum(naive_scores) / len(naive_scores)
        struct_avg = sum(struct_scores) / len(struct_scores)
        delta = struct_avg - naive_avg
        
        print(f"{model_name:<30} {naive_avg:>10.2f} {struct_avg:>10.2f} {delta:>+8.2f}")
    
    # Save full results
    with open("hard-test-results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print("\nFull results saved to hard-test-results.json")
    return results

if __name__ == "__main__":
    run_experiment()
