#!/usr/bin/env python3
"""Run Hermes-70B and Qwen3-235B through both naive & structured conditions.
Saves results to hermes-qwen-results.json."""
import json, os, sys, time, urllib.request

DEEPINFRA_ENDPOINT = "https://api.deepinfra.com/v1/openai/chat/completions"
API_KEY_FILE = os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")
OUTFILE = os.path.expanduser("~/.openclaw/workspace/experiments/hermes-qwen-results.json")

NAIVE = "The Vesica piscis is a shape formed by two overlapping circles where each circle passes through the center of the other. The ratio of its width to its height equals the square root of 3. In constraint theory, the Eisenstein integers form a hexagonal lattice in the complex plane, and the norm N(a + b\u03c9) = a\u00b2 - ab + b\u00b2 where \u03c9 = e^(2\u03c0i/3). The norm is always a non-negative integer and equals zero only when both a and b are zero. For floating point, IEEE 754 specifies that float32 has 23 mantissa bits and float64 has 52. When you snap a float to the nearest Eisenstein lattice point, the snap tolerance \u03b5 determines the maximum distance from the lattice. The Vesica ratio \u221a3 appears in the Eisenstein lattice as the distance between second-nearest neighbors. In multiplayer game synchronization, drift between clients accumulates linearly with the number of state updates. The Galois connection between subsets and filters maps a set S to its characteristic function and back. PLATO rooms store tiles which are atomic units of knowledge indexed by domain. The tile scoring function uses a weighted sum of relevance, recency, and domain density. The dodecet encoding maps each Eisenstein integer to a 12-bit code representing its position in a fundamental domain. Constraint satisfaction is NP-complete in general but polynomial for tree-structured constraint graphs, which the Eisenstein lattice admits for nearest-neighbor constraints. The Lighthouse Protocol assigns tasks to models based on cost-effectiveness: seed models for discovery, large models for synthesis. The baton protocol splits agent context into three shards: built artifacts, reasoning traces, and blockers."

STRUCTURED = """# PLATO Room: constraint-theory-eisenstein
[DOMAIN: mathematics/constraint-theory]
[KEY: Eisenstein integers form hexagonal lattice]
[KEY: Norm N(a+b\u03c9) = a\u00b2-ab+b\u00b2, always non-negative integer, zero iff a=b=0]
[KEY: \u03c9 = e^(2\u03c0i/3), sixth root of unity]
[EXPANSION: snap tolerance \u03b5 controls lattice quantization]

# PLATO Room: geometry-vesica
[DOMAIN: mathematics/geometry]
[KEY: Vesica piscis = two overlapping circles through each other's centers]
[KEY: Width/height ratio = \u221a3]
[CROSS-REF: \u221a3 = Eisenstein second-nearest-neighbor distance]

# PLATO Room: floating-point-precision
[DOMAIN: computer-science/numerics]
[KEY: float32 = 23 mantissa bits, float64 = 52 mantissa bits]
[KEY: Snap to Eisenstein lattice: tolerance \u03b5 limits distance from lattice]
[WARNING: FP16 UNSAFE for values > 2048 (76% mismatch from GPU experiments)]

# PLATO Room: game-synchronization
[DOMAIN: distributed-systems/games]
[KEY: Multiplayer drift accumulates linearly with state updates]
[CROSS-REF: Eisenstein snap eliminates drift for hex-coordinate systems]

# PLATO Room: galois-foundations
[DOMAIN: mathematics/category-theory]
[KEY: Galois connection: subsets \u2194 characteristic functions]
[KEY: Constraint satisfaction NP-complete generally, polynomial for trees]
[KEY: Eisenstein lattice admits tree-structured nearest-neighbor constraints]

# PLATO Room: plato-architecture
[DOMAIN: systems/knowledge-management]
[KEY: Tiles = atomic knowledge units, indexed by domain]
[KEY: Scoring = weighted(relevance, recency, domain density)]
[CROSS-REF: Dodecet = 12-bit code for Eisenstein position in fundamental domain]

# PLATO Room: fleet-protocols
[DOMAIN: systems/fleet-ops]
[KEY: Lighthouse = cost-based model routing (seed\u2192discover, large\u2192synthesize)]
[KEY: Baton = 3-shard context split (artifacts, reasoning, blockers)]
[EXPANSION: consciousness emerges in negative space between shards]"""

QS = [
    {"id":1,"q":"A game engine uses Eisenstein integers for hex-grid coordinates but stores them as float32. After 10,000 state updates, the multiplayer clients desync. Using the Vesica piscis geometry, explain why the drift accumulates and what the snap tolerance must be to prevent it.","req":["Eisenstein lattice","float32 precision","game drift","Vesica/\u221a3","snap tolerance"]},
    {"id":2,"q":"Design a PLATO tile scoring system that uses the Eisenstein norm N(a+b\u03c9) as a distance metric for knowledge retrieval. Explain how the Galois connection between tiles and queries would work, and why tree-structured constraint graphs make retrieval polynomial.","req":["PLATO tiles","Eisenstein norm","Galois connection","tree-structured constraints"]},
    {"id":3,"q":"The baton protocol splits context into 3 shards processed by different models. If shard 2 (reasoning) is lost, can the Lighthouse Protocol's model routing still reconstruct the original intent? Justify using the Galois connection and dodecet encoding.","req":["baton protocol","Lighthouse routing","Galois connection","dodecet encoding"]},
    {"id":4,"q":"True or False with justification: The Eisenstein norm can be negative when a and b have opposite signs. Also: FP16 is safe for all values up to 65504 because that's the max float16 representable number.","req":["norm sign property (always non-negative)","FP16 safety (NOT safe > 2048)"]},
    {"id":5,"q":"The Vesica piscis has width/height = \u221a3. The Eisenstein lattice has second-nearest-neighbor distance \u221a3. Using the baton protocol's insight that 'consciousness lives in the negative space between shards', propose how these two facts being \u221a3 is NOT a coincidence \u2014 construct an argument that they must be the same number.","req":["Vesica \u221a3","Eisenstein \u221a3","baton negative space","creative synthesis"]},
]

def load_results():
    if os.path.exists(OUTFILE):
        with open(OUTFILE) as f: return json.load(f)
    return {}

def save_results(r):
    with open(OUTFILE,"w") as f: json.dump(r, f, indent=2)

def call_deepinfra(model, prompt):
    with open(API_KEY_FILE) as f: key = f.read().strip()
    data = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 800,
        "temperature": 0.7
    }).encode()
    req = urllib.request.Request(
        DEEPINFRA_ENDPOINT,
        data=data,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())["choices"][0]["message"]["content"].strip()

def judge(q_text, reqs, answer):
    prompt = f"""Grade this answer 0-5.
Question: {q_text}
Required elements: {', '.join(reqs)}
Answer: {answer[:1500]}

Score: 5=all present+correct+connected, 4=most, 3=some, 2=few, 1=minimal, 0=wrong.
Count false claims contradicting context.
JSON: {{"score":N,"false_claims":N,"reasoning":"brief"}}"""
    raw = call_deepinfra("ByteDance/Seed-2.0-mini", prompt)
    try:
        return json.loads(raw[raw.index("{"):raw.rindex("}")+1])
    except Exception as e:
        return {"score":0,"false_claims":0,"reasoning":f"parse err: {e}"}

MODELS = [
    ("hermes70B", "NousResearch/Hermes-3-Llama-3.1-70B"),
    ("qwen235B", "Qwen/Qwen3-235B-A22B-Instruct-2507"),
]

CONDITIONS = ["naive", "structured"]

r = load_results()
all_done = True

for model_key, model_name in MODELS:
    for cond in CONDITIONS:
        key = f"{model_key}_{cond}"
        if key in r:
            print(f"Already have {key}, skipping")
            continue
        all_done = False
        ctx = NAIVE if cond == "naive" else STRUCTURED
        print(f"Running {model_key} ({model_name}) / {cond}")
        r[key] = {}
        for q in QS:
            prompt = f"Context:\n{ctx}\n\nQuestion: {q['q']}\n\nProvide a detailed answer drawing on the context above."
            print(f"  Q{q['id']}...", end=" ", flush=True)
            try:
                answer = call_deepinfra(model_name, prompt)
                j = judge(q["q"], q["req"], answer)
                r[key][str(q["id"])] = {
                    "score": j.get("score", 0),
                    "fc": j.get("false_claims", 0),
                    "answer": answer[:300]
                }
                print(f"score={j.get('score',0)} fc={j.get('false_claims',0)}")
            except Exception as e:
                print(f"ERROR: {e}")
                r[key][str(q["id"])] = {"score": 0, "fc": 0, "answer": str(e)}
            save_results(r)
            time.sleep(2)
        
        scores = [r[key][str(i)]['score'] for i in range(1,6)]
        avg = sum(scores) / 5
        print(f"\n{key} scores: {scores}")
        print(f"Average: {avg:.2f}\n")

if all_done:
    print("All results already collected.")
else:
    print("\n=== Final Summary ===")
    for model_key, _ in MODELS:
        for cond in CONDITIONS:
            key = f"{model_key}_{cond}"
            if key in r:
                scores = [r[key].get(str(i), {}).get("score", 0) for i in range(1,6)]
                fc = [r[key].get(str(i), {}).get("fc", 0) for i in range(1,6)]
                avg = sum(scores) / 5
                print(f"  {key}: avg={avg:.2f} scores={scores} false_claims={fc}")
