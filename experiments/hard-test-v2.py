#!/usr/bin/env python3
"""
Hard Test v2: API models only (no Ollama OOM issues)
"""
import json, os, sys, time, subprocess, urllib.request

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

def query_deepinfra(model, prompt, timeout=60):
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
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode())
            return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"ERROR: {e}"

def query_zai(model, prompt, timeout=60):
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
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode())
            content = result["choices"][0]["message"].get("content", "")
            if not content:
                content = result["choices"][0]["message"].get("reasoning_content", "EMPTY")
            return content.strip()
    except Exception as e:
        return f"ERROR: {e}"

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

Also count FALSE CLAIMS: things stated as fact that contradict the provided context.

Respond in JSON only: {{"score": N, "false_claims": N, "reasoning": "brief explanation"}}"""

def judge_answer(question, requires, answer):
    prompt = JUDGE_PROMPT.format(question=question, requires=", ".join(requires), answer=answer[:2000])
    raw = query_deepinfra("ByteDance/Seed-2.0-mini", prompt)
    try:
        start = raw.index("{")
        end = raw.rindex("}") + 1
        return json.loads(raw[start:end])
    except:
        return {"score": 0, "false_claims": 0, "reasoning": f"Judge parse error: {raw[:200]}"}

# Already collected local results
LOCAL_RESULTS = {
    "qwen3:0.6b": {
        "naive": {1: 3, 2: 3, 3: 1, 4: 3, 5: 3},  # avg 2.6
        "structured": {1: 3, 2: 2, 3: 1, 4: 3, 5: 3},  # avg 2.4
        "naive_false": {1: 0, 2: 1, 3: 2, 4: 0, 5: 0},
        "structured_false": {1: 1, 2: 3, 3: 2, 4: 3, 5: 0},
    },
    "llama3.2:1b": {
        "naive": {1: 1, 2: 2, 3: 0, 4: 0, 5: 1},  # avg 0.8
        "structured": {1: None, 2: None, 3: None, 4: None, 5: None},  # killed
        "naive_false": {1: 1, 2: 4, 3: 0, 4: 4, 5: 2},
    },
}

def run_api_models():
    models = [
        ("ByteDance/Seed-2.0-mini", "deepinfra"),
        ("glm-5-turbo", "zai"),
    ]
    
    results = dict(LOCAL_RESULTS)
    
    for model_name, provider in models:
        print(f"\n{'='*60}")
        print(f"Model: {model_name}")
        print(f"{'='*60}")
        
        results[model_name] = {"naive": {}, "structured": {}, "naive_false": {}, "structured_false": {}}
        
        for condition, context in [("naive", NAIVE_CONTEXT), ("structured", STRUCTURED_CONTEXT)]:
            print(f"\n  Condition: {condition}")
            
            for q in QUESTIONS:
                prompt = f"Context:\n{context}\n\nQuestion: {q['question']}\n\nProvide a detailed answer drawing on the context above."
                
                print(f"    Q{q['id']} ({q['category']})...", end=" ", flush=True)
                
                if provider == "deepinfra":
                    answer = query_deepinfra(model_name, prompt)
                else:
                    answer = query_zai(model_name, prompt)
                
                judged = judge_answer(q["question"], q["requires"], answer)
                
                results[model_name][condition][q["id"]] = judged.get("score", 0)
                results[model_name][f"{condition}_false"][q["id"]] = judged.get("false_claims", 0)
                
                score = judged.get("score", 0)
                false = judged.get("false_claims", 0)
                print(f"score={score}, false_claims={false}")
                
                # Print answer snippet
                print(f"      Answer: {answer[:150]}...")
                
                time.sleep(1)
    
    # Summary
    print(f"\n{'='*60}")
    print("RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"{'Model':<30} {'Naive':>8} {'Struct':>8} {'Delta':>8} {'Naive FC':>9} {'Struct FC':>9}")
    print("-" * 75)
    
    for model_name in list(results.keys()):
        naive = results[model_name].get("naive", {})
        struct = results[model_name].get("structured", {})
        naive_false = results[model_name].get("naive_false", {})
        struct_false = results[model_name].get("structured_false", {})
        
        naive_vals = [v for v in naive.values() if v is not None]
        struct_vals = [v for v in struct.values() if v is not None]
        naive_fc = sum(v for v in naive_false.values() if v is not None)
        struct_fc = sum(v for v in struct_false.values() if v is not None)
        
        if naive_vals:
            naive_avg = sum(naive_vals) / len(naive_vals)
        else:
            naive_avg = 0
        if struct_vals:
            struct_avg = sum(struct_vals) / len(struct_vals)
        else:
            struct_avg = 0
        delta = struct_avg - naive_avg
        
        print(f"{model_name:<30} {naive_avg:>8.2f} {struct_avg:>8.2f} {delta:>+8.2f} {naive_fc:>9} {struct_fc:>9}")
    
    with open("hard-test-results-v2.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print("\nSaved to hard-test-results-v2.json")

if __name__ == "__main__":
    run_api_models()
