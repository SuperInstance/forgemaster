#!/usr/bin/env python3
"""
STRUCTURE VS SCALE EXPERIMENT
Can an 8B model with proper room structuring match or beat Seed-2.0-mini (230B/23B)?

Models: llama-3.1-8b-instant (Groq, ~1s response, essentially free)
         meta-llama/llama-4-scout-17b-16e-instruct (Groq)
         openai/gpt-oss-20b (Groq)
Baseline: ByteDance/Seed-2.0-mini (DeepInfra, 230B/23B MoE, $0.01)

Hypothesis: A well-structured PLATO room (curriculum ordering, domain tags,
self-reconstructing tiles) can make an 8B model perform comparably to Seed
on reconstruction tasks, because the structure externalizes what Seed's MoE
experts do internally.
"""
import json, time, urllib.request

GROQ_KEY = open("/home/phoenix/.openclaw/workspace/.credentials/groq-api-key.txt").read().strip()
GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

DEEPINFRA_KEY = open("/home/phoenix/.openclaw/workspace/.credentials/deepinfra-api-key.txt").read().strip()
DEEPINFRA_ENDPOINT = "https://api.deepinfra.com/v1/openai/chat/completions"

TILE = "Penrose P3 tiling, 5D cut-and-project, golden-ratio hash vertex IDs, Fibonacci word encoding, dead-reckoning navigation, deflation consolidation, 3-color baton sharding, C9 locality failure, PCA 1.7x better than golden, 56% recall@20, 230B/23B MoE Seed integration"

FACTS = ["penrose", "5d cut-and-project", "golden-ratio hash", "fibonacci word",
         "dead-reckoning", "deflation", "3-color baton", "C9 locality",
         "pca 1.7x", "230b/23b moe"]

def call_groq(model, messages, temperature=1.0, max_tokens=2000):
    payload = json.dumps({"model": model, "temperature": temperature,
        "max_tokens": max_tokens, "messages": messages}).encode()
    req = urllib.request.Request(GROQ_ENDPOINT, data=payload, headers={
        "Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
        return data['choices'][0]['message']['content'], data.get('usage',{}).get('total_tokens',0)

def call_deepinfra(model, messages, temperature=1.0, max_tokens=2000):
    payload = json.dumps({"model": model, "temperature": temperature,
        "max_tokens": max_tokens, "messages": messages}).encode()
    req = urllib.request.Request(DEEPINFRA_ENDPOINT, data=payload, headers={
        "Authorization": f"Bearer {DEEPINFRA_KEY}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
        return data['choices'][0]['message']['content'], data.get('usage',{}).get('total_tokens',0)

def score(text):
    t = text.lower()
    return sum(1 for f in FACTS if any(k in t for k in f.split()))

results = []

# ============================================================
# CONDITION 1: NAIVE — just the tile, no structure
# ============================================================
print("=== CONDITION 1: NAIVE (no structure) ===")
for model, provider in [
    ("llama-3.1-8b-instant", "groq"),
    ("meta-llama/llama-4-scout-17b-16e-instruct", "groq"),
    ("openai/gpt-oss-20b", "groq"),
    ("ByteDance/Seed-2.0-mini", "deepinfra"),
]:
    call_fn = call_groq if provider == "groq" else call_deepinfra
    for temp in [0.3, 1.0]:
        msgs = [{"role": "user", "content": f"Expand this compressed knowledge tile into a complete technical document: {TILE}"}]
    content, tokens = call_fn(model, msgs, temperature=temp)
        s = score(content)
        elapsed = "?"
        line = f"  {model:50s} t={temp} score={s}/10 tokens={tokens} chars={len(content)}"
        print(line)
        results.append({"condition": "naive", "model": model, "temp": temp, "score": s, "tokens": tokens, "chars": len(content)})
        time.sleep(0.5 if provider == "groq" else 2)

# ============================================================
# CONDITION 2: STRUCTURED — PLATO room with curriculum, tags, hints
# ============================================================
print("\n=== CONDITION 2: STRUCTURED (PLATO room format) ===")
STRUCTURED_PROMPT = """You are reading from a PLATO knowledge room: [DOMAIN: constraint-theory] [LEVEL: application] [CONFIDENCE: 0.92]

CURRICULUM CONTEXT:
- Prerequisites loaded: Eisenstein integers, Penrose geometry, PLATO architecture
- This tile is in the "application" layer (concrete implementations)
- Key terms are marked with [KEY] tags for precision

TILE CONTENT:
Penrose P3 tiling [KEY], 5D cut-and-project [KEY], golden-ratio hash vertex IDs [KEY], Fibonacci word encoding [KEY], dead-reckoning navigation [KEY], deflation consolidation [KEY], 3-color baton sharding [KEY], C9 locality failure [KEY], PCA projection 1.7x better than golden [KEY] for neighbor preservation, 56% recall@20 end-to-end [KEY], 230B/23B MoE [KEY] Seed integration

EXPANSION HINTS (reconstruction anchors):
- Penrose P3 = thick/thin rhombus tiling, 5-fold symmetry, aperiodic
- Cut-and-project = 5D lattice → perpendicular window → 2D projection
- Golden-ratio hash = Knuth multiplicative hash 0x9E3779B97F4A7C15
- Fibonacci word = deterministic thick:thin sequence → 1/φ ratio
- Dead reckoning = navigate by (distance, heading) from reference point
- Deflation = merge tiles at φ^k scale (dream consolidation)
- 3-coloring = baton shards (Built/Thought/Blocked), guaranteed no adjacents same
- C9 = locality after quantization FAILS (nearby memories snap to same tile)
- PCA = learned projection beats fixed golden ratio 1.7x for neighbors
- 230B/23B = MoE with 10:1 sparsity, AdaCoT adaptive reasoning

Expand this tile into a complete technical document preserving ALL key terms."""

for model, provider in [
    ("llama-3.1-8b-instant", "groq"),
    ("meta-llama/llama-4-scout-17b-16e-instruct", "groq"),
    ("openai/gpt-oss-20b", "groq"),
    ("ByteDance/Seed-2.0-mini", "deepinfra"),
]:
    call_fn = call_groq if provider == "groq" else call_deepinfra
    for temp in [0.3, 1.0]:
        content, tokens = call_fn(model, [
            {"role": "system", "content": "You are a PLATO tile expander. Preserve all [KEY] marked terms precisely."},
            {"role": "user", "content": STRUCTURED_PROMPT}
        ], temperature=temp)
        s = score(content)
        print(f"  {model:50s} t={temp} score={s}/10 tokens={tokens} chars={len(content)}")
        results.append({"condition": "structured", "model": model, "temp": temp, "score": s, "tokens": tokens, "chars": len(content)})
        time.sleep(0.5 if provider == "groq" else 2)

# ============================================================
# CONDITION 3: MULTI-ROOM — 3-room curriculum progression
# ============================================================
print("\n=== CONDITION 3: MULTI-ROOM (3-room curriculum) ===")
ROOM1 = "ROOM 1 [foundation]: Penrose P3 tiling has thick and thin rhombuses with 5-fold rotational symmetry. It's aperiodic — no translation maps it onto itself. Generated by cut-and-project from 5D lattice."
ROOM2 = "ROOM 2 [structure]: Fibonacci word encoding gives deterministic tile IDs. Golden-ratio hash (Knuth constant) creates unique vertex identifiers. Dead reckoning navigates by distance+heading. Deflation merges at φ^k scale."
ROOM3 = "ROOM 3 [application]: 3-coloring enables baton sharding. C9 locality fails after quantization. PCA projection 1.7x better than fixed golden for neighbors. 230B/23B MoE Seed with 10:1 sparsity and AdaCoT."

MULTI_PROMPT = f"""You are reading a PLATO curriculum in order. Each room builds on the previous.

{ROOM1}

{ROOM2}

{ROOM3}

Using ALL information from these 3 rooms, write a complete technical document about the Penrose Memory Palace system. Preserve every technical term precisely."""

for model, provider in [
    ("llama-3.1-8b-instant", "groq"),
    ("ByteDance/Seed-2.0-mini", "deepinfra"),
]:
    call_fn = call_groq if provider == "groq" else call_deepinfra
    content, tokens = call_fn(model, [
        {"role": "user", "content": MULTI_PROMPT}
    ], temperature=1.0)
    s = score(content)
    print(f"  {model:50s} score={s}/10 tokens={tokens} chars={len(content)}")
    results.append({"condition": "multi-room", "model": model, "temp": 1.0, "score": s, "tokens": tokens, "chars": len(content)})
    time.sleep(1)

# ============================================================
# SUMMARY
# ============================================================
print("\n" + "="*80)
print("STRUCTURE VS SCALE — CAN 8B + STRUCTURE MATCH 230B?")
print("="*80)

for r in sorted(results, key=lambda x: -x['score']):
    print(f"  {r['condition']:12s} {r['model']:50s} t={r.get('temp',1.0)} score={r['score']}/10")

# Key comparison
eightb_structured = [r for r in results if r['condition']=='structured' and '8b' in r['model'] and r['temp']==1.0]
seed_naive = [r for r in results if r['condition']=='naive' and 'Seed' in r['model'] and r['temp']==1.0]
eightb_naive = [r for r in results if r['condition']=='naive' and '8b' in r['model'] and r['temp']==1.0]

print(f"\n  8B naive:      {eightb_naive[0]['score'] if eightb_naive else '?'}/10")
print(f"  8B structured: {eightb_structured[0]['score'] if eightb_structured else '?'}/10")
print(f"  Seed naive:    {seed_naive[0]['score'] if seed_naive else '?'}/10")
if eightb_structured and seed_naive:
    delta = eightb_structured[0]['score'] - seed_naive[0]['score']
    print(f"  Gap (8B+struct - Seed naive): {delta:+d}")
    print(f"  Structure boost for 8B: {eightb_structured[0]['score'] - eightb_naive[0]['score']:+d}" if eightb_naive else "")

with open("/home/phoenix/.openclaw/workspace/papers/glm-stress-results/structure-vs-scale.json", "w") as f:
    json.dump(results, f, indent=2)
print("\nSaved to structure-vs-scale.json")
