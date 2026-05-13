#!/usr/bin/env python3
"""Hard Test v3: API models, 120s timeouts, no Ollama"""
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
    {"id":1, "cat":"cross-domain", "q":"A game engine uses Eisenstein integers for hex-grid coordinates but stores them as float32. After 10,000 state updates, the multiplayer clients desync. Using the Vesica piscis geometry, explain why the drift accumulates and what the snap tolerance must be to prevent it.", "req":["Eisenstein lattice","float32 precision","game drift","Vesica/√3","snap tolerance"]},
    {"id":2, "cat":"creative-synthesis", "q":"Design a PLATO tile scoring system that uses the Eisenstein norm N(a+bω) as a distance metric for knowledge retrieval. Explain how the Galois connection between tiles and queries would work, and why tree-structured constraint graphs make retrieval polynomial.", "req":["PLATO tiles","Eisenstein norm","Galois connection","tree-structured constraints"]},
    {"id":3, "cat":"adversarial", "q":"The baton protocol splits context into 3 shards processed by different models. If shard 2 (reasoning) is lost, can the Lighthouse Protocol's model routing still reconstruct the original intent? Justify using the Galois connection and dodecet encoding.", "req":["baton protocol","Lighthouse routing","Galois connection","dodecet encoding"]},
    {"id":4, "cat":"negation-trap", "q":"True or False with justification: The Eisenstein norm can be negative when a and b have opposite signs. Also: FP16 is safe for all values up to 65504 because that's the max float16 representable number.", "req":["norm sign property (always non-negative)","FP16 safety (NOT safe > 2048)"]},
    {"id":5, "cat":"cross-domain-creative", "q":"The Vesica piscis has width/height = √3. The Eisenstein lattice has second-nearest-neighbor distance √3. Using the baton protocol's insight that 'consciousness lives in the negative space between shards', propose how these two facts being √3 is NOT a coincidence — construct an argument that they must be the same number.", "req":["Vesica √3","Eisenstein √3","baton negative space","creative synthesis"]},
]

def call_deepinfra(model, prompt):
    kf = os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")
    with open(kf) as f: key = f.read().strip()
    data = json.dumps({"model":model,"messages":[{"role":"user","content":prompt}],"max_tokens":1024,"temperature":0.7}).encode()
    req = urllib.request.Request("https://api.deepinfra.com/v1/openai/chat/completions",data=data,headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())["choices"][0]["message"]["content"].strip()

def call_zai(model, prompt):
    r = subprocess.run(["openclaw","config","get","providers.zai.apiKey"],capture_output=True,text=True,timeout=10)
    key = r.stdout.strip()
    data = json.dumps({"model":model,"messages":[{"role":"user","content":prompt}],"max_tokens":1024,"temperature":0.7}).encode()
    req = urllib.request.Request("https://api.z.ai/api/coding/paas/v4/chat/completions",data=data,headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        r = json.loads(resp.read().decode())
        c = r["choices"][0]["message"].get("content","")
        if not c: c = r["choices"][0]["message"].get("reasoning_content","EMPTY")
        return c.strip()

def judge(q_text, reqs, answer):
    prompt = f"""Grade this answer 0-5.\nQuestion: {q_text}\nRequired elements: {', '.join(reqs)}\nAnswer: {answer[:2000]}\n\nScore: 5=all present+correct, 4=most, 3=some, 2=few, 1=minimal, 0=wrong.\nAlso count false claims (contradicting context).\nJSON only: {{"score":N,"false_claims":N,"reasoning":"brief"}}"""
    raw = call_deepinfra("ByteDance/Seed-2.0-mini", prompt)
    try:
        return json.loads(raw[raw.index("{"):raw.rindex("}")+1])
    except:
        return {"score":0,"false_claims":0,"reasoning":f"parse err: {raw[:150]}"}

# Previous local results
prev = {
    "qwen3:0.6b": {"naive":[3,3,1,3,3],"structured":[3,2,1,3,3],"naive_fc":[0,1,2,0,0],"struct_fc":[1,3,2,3,0]},
    "llama3.2:1b": {"naive":[1,2,0,0,1],"naive_fc":[1,4,0,4,2]},
}

results = {}
for model_name, caller in [("ByteDance/Seed-2.0-mini", call_deepinfra), ("glm-5-turbo", call_zai)]:
    print(f"\n{'='*60}\n{model_name}\n{'='*60}")
    results[model_name] = {"naive":{},"structured":{},"naive_fc":{},"struct_fc":{}}
    
    for cond, ctx in [("naive",NAIVE),("structured",STRUCTURED)]:
        print(f"  {cond}:")
        for q in QS:
            prompt = f"Context:\n{ctx}\n\nQuestion: {q['q']}\n\nProvide a detailed answer drawing on the context above."
            print(f"    Q{q['id']}...", end=" ", flush=True)
            try:
                answer = caller(model_name, prompt)
                j = judge(q["q"], q["req"], answer)
                results[model_name][cond][q["id"]] = j.get("score",0)
                results[model_name][f"{cond}_fc"][q["id"]] = j.get("false_claims",0)
                print(f"score={j.get('score',0)} fc={j.get('false_claims',0)}")
                print(f"      {answer[:120]}...")
            except Exception as e:
                print(f"ERROR: {e}")
                results[model_name][cond][q["id"]] = 0
            time.sleep(1)

# Summary with all models
print(f"\n{'='*60}\nFINAL RESULTS\n{'='*60}")
all_models = list(prev.keys()) + list(results.keys())
print(f"{'Model':<30} {'Naive':>6} {'Struct':>6} {'Δ':>6} {'N-FC':>5} {'S-FC':>5}")
print("-"*60)

for m in all_models:
    if m in prev:
        nv = prev[m]["naive"]
        sv = prev[m].get("structured",[])
        nfc = sum(prev[m].get("naive_fc",[]))
        sfc = sum(prev[m].get("struct_fc",[]))
    else:
        nv = list(results[m]["naive"].values())
        sv = list(results[m]["structured"].values())
        nfc = sum(results[m]["naive_fc"].values())
        sfc = sum(results[m]["struct_fc"].values())
    
    na = sum(nv)/len(nv) if nv else 0
    sa = sum(sv)/len(sv) if sv else 0
    d = sa - na
    print(f"{m:<30} {na:>6.2f} {sa:>6.2f} {d:>+6.2f} {nfc:>5} {sfc:>5}")

with open("hard-test-results-v3.json","w") as f:
    json.dump({"prev":prev,"api":results}, f, indent=2, default=str)
print("\nSaved hard-test-results-v3.json")
