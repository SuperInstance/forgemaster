#!/usr/bin/env python3
"""Run one model at a time, save incrementally, avoid OOM."""
import json, os, sys, time, subprocess, urllib.request

NAIVE = "The Vesica piscis is a shape formed by two overlapping circles where each circle passes through the center of the other. The ratio of its width to its height equals the square root of 3. In constraint theory, the Eisenstein integers form a hexagonal lattice in the complex plane, and the norm N(a + bω) = a² - ab + b² where ω = e^(2πi/3). The norm is always a non-negative integer and equals zero only when both a and b are zero. For floating point, IEEE 754 specifies that float32 has 23 mantissa bits and float64 has 52. When you snap a float to the nearest Eisenstein lattice point, the snap tolerance ε determines the maximum distance from the lattice. The Vesica ratio √3 appears in the Eisenstein lattice as the distance between second-nearest neighbors. In multiplayer game synchronization, drift between clients accumulates linearly with the number of state updates. The Galois connection between subsets and filters maps a set S to its characteristic function and back. PLATO rooms store tiles which are atomic units of knowledge indexed by domain. The tile scoring function uses a weighted sum of relevance, recency, and domain density. The dodecet encoding maps each Eisenstein integer to a 12-bit code representing its position in a fundamental domain. Constraint satisfaction is NP-complete in general but polynomial for tree-structured constraint graphs, which the Eisenstein lattice admits for nearest-neighbor constraints. The Lighthouse Protocol assigns tasks to models based on cost-effectiveness: seed models for discovery, large models for synthesis. The baton protocol splits agent context into three shards: built artifacts, reasoning traces, and blockers."

STRUCTURED = """# PLATO Room: constraint-theory-eisenstein
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
[EXPANSION: consciousness emerges in negative space between shards]"""

QS = [
    {"id":1,"q":"A game engine uses Eisenstein integers for hex-grid coordinates but stores them as float32. After 10,000 state updates, the multiplayer clients desync. Using the Vesica piscis geometry, explain why the drift accumulates and what the snap tolerance must be to prevent it.","req":["Eisenstein lattice","float32 precision","game drift","Vesica/√3","snap tolerance"]},
    {"id":2,"q":"Design a PLATO tile scoring system that uses the Eisenstein norm N(a+bω) as a distance metric for knowledge retrieval. Explain how the Galois connection between tiles and queries would work, and why tree-structured constraint graphs make retrieval polynomial.","req":["PLATO tiles","Eisenstein norm","Galois connection","tree-structured constraints"]},
    {"id":3,"q":"The baton protocol splits context into 3 shards processed by different models. If shard 2 (reasoning) is lost, can the Lighthouse Protocol's model routing still reconstruct the original intent? Justify using the Galois connection and dodecet encoding.","req":["baton protocol","Lighthouse routing","Galois connection","dodecet encoding"]},
    {"id":4,"q":"True or False with justification: The Eisenstein norm can be negative when a and b have opposite signs. Also: FP16 is safe for all values up to 65504 because that's the max float16 representable number.","req":["norm sign property (always non-negative)","FP16 safety (NOT safe > 2048)"]},
    {"id":5,"q":"The Vesica piscis has width/height = √3. The Eisenstein lattice has second-nearest-neighbor distance √3. Using the baton protocol's insight that 'consciousness lives in the negative space between shards', propose how these two facts being √3 is NOT a coincidence — construct an argument that they must be the same number.","req":["Vesica √3","Eisenstein √3","baton negative space","creative synthesis"]},
]

OUTFILE = "hard-test-results-final.json"

def load_results():
    if os.path.exists(OUTFILE):
        with open(OUTFILE) as f: return json.load(f)
    return {}

def save_results(r):
    with open(OUTFILE,"w") as f: json.dump(r, f, indent=2)

def call_deepinfra(model, prompt):
    kf = os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")
    with open(kf) as f: key = f.read().strip()
    data = json.dumps({"model":model,"messages":[{"role":"user","content":prompt}],"max_tokens":800,"temperature":0.7}).encode()
    req = urllib.request.Request("https://api.deepinfra.com/v1/openai/chat/completions",data=data,headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())["choices"][0]["message"]["content"].strip()

ZAI_KEY = "703f56774c324a76b8a283ce50b15744.tLKi6d9yeYza5Spg"

def call_zai(model, prompt):
    data = json.dumps({"model":model,"messages":[{"role":"user","content":prompt}],"max_tokens":800,"temperature":0.7}).encode()
    req = urllib.request.Request("https://api.z.ai/api/coding/paas/v4/chat/completions",data=data,headers={"Authorization":f"Bearer {ZAI_KEY}","Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        r = json.loads(resp.read().decode())
        c = r["choices"][0]["message"].get("content","")
        if not c: c = r["choices"][0]["message"].get("reasoning_content","EMPTY")
        return c.strip()

def judge(q_text, reqs, answer):
    prompt = f"""Grade this answer 0-5.\nQuestion: {q_text}\nRequired elements: {', '.join(reqs)}\nAnswer: {answer[:1500]}\n\nScore: 5=all present+correct+connected, 4=most, 3=some, 2=few, 1=minimal, 0=wrong.\nCount false claims contradicting context.\nJSON: {{"score":N,"false_claims":N,"reasoning":"brief"}}"""
    raw = call_deepinfra("ByteDance/Seed-2.0-mini", prompt)
    try:
        return json.loads(raw[raw.index("{"):raw.rindex("}")+1])
    except:
        return {"score":0,"false_claims":0,"reasoning":f"parse err"}

# Get model/condition from args
# Usage: python3 hard-test-final.py <model_name> <naive|structured>
if len(sys.argv) != 3:
    print("Usage: python3 hard-test-final.py <model> <naive|structured>")
    print("Models: seed-mini, glm-5-turbo")
    sys.exit(1)

model_arg = sys.argv[1]
cond = sys.argv[2]

if model_arg == "seed-mini":
    model_name = "ByteDance/Seed-2.0-mini"
    caller = call_deepinfra
elif model_arg == "glm-5-turbo":
    model_name = "glm-5-turbo"
    caller = call_zai
else:
    print(f"Unknown model: {model_arg}")
    sys.exit(1)

ctx = NAIVE if cond == "naive" else STRUCTURED
r = load_results()
key = f"{model_arg}_{cond}"

if key in r:
    print(f"Already have {key}, skipping")
    sys.exit(0)

print(f"Running {model_name} / {cond}")
r[key] = {}

for q in QS:
    prompt = f"Context:\n{ctx}\n\nQuestion: {q['q']}\n\nProvide a detailed answer drawing on the context above."
    print(f"  Q{q['id']}...", end=" ", flush=True)
    try:
        answer = caller(model_name, prompt)
        j = judge(q["q"], q["req"], answer)
        r[key][str(q["id"])] = {"score": j.get("score",0), "fc": j.get("false_claims",0), "answer": answer[:300]}
        print(f"score={j.get('score',0)} fc={j.get('false_claims',0)}")
    except Exception as e:
        print(f"ERROR: {e}")
        r[key][str(q["id"])] = {"score": 0, "fc": 0, "answer": str(e)}
    save_results(r)
    time.sleep(2)

# Print partial summary
print(f"\n{key} scores: {[r[key][str(i)]['score'] for i in range(1,6)]}")
avg = sum(r[key][str(i)]['score'] for i in range(1,6)) / 5
print(f"Average: {avg:.2f}")
