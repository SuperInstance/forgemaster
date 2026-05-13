#!/usr/bin/env python3
"""Seed-2.0-mini reconstruction test - 5 tiles × 3 runs"""
import json, os, sys, time, requests

API_KEY = open(os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")).read().strip()
ENDPOINT = "https://api.deepinfra.com/v1/openai/chat/completions"
MODEL = "ByteDance/Seed-2.0-mini"
OUTDIR = "/home/phoenix/.openclaw/workspace/baton-experiments/seed-recon-real"

TILES = {
    1: """[TILE:GROUND-TRUTH-AUDIT]
Domain: Neural-PLATO ground truth verification experiment
Scope: 34 claims across 4 tiers of evidence strength
Key: Tier1=proven-by-code(23 claims), Tier2=standard-math(6), Tier3=partial-verify(2), Tier4=speculative(3)
Results: Fibonacci-word thick:thin->1/phi(n=10000,delta=0.000034), matching-rules 99.19%@n=10000, 3-coloring verified 40x40, golden-twist aperiodic 0-repeats@10000, Boltzmann entropy T=1.0=1.93 vs T=0.1=0.002, 2D captures 2.54% of 64D energy, snap-errors 100% localized(849/849)
Negatives: golden NOT special for compression(Q1), 3-coloring no retrieval help(Q8), locality after quantization FAILS(C9)
Baton-results: temp=1.0 optimal 100% at $0.01, split=3 optimal(75%), amnesia-cliff at 10% to 0%
Tier3-gap: tile-type classification by perpendicular-space position needs fixing, thick:thin ratio approx phi not yet verified properly
Ground-truth-ratio: 85%(29/34), 5 unfounded = 6 trusted-theorems + 2 partial + 3 speculative labeled""",

    2: """[TILE:PENROSE-MEMORY]
Domain: Rust+Python crate for aperiodic memory palace using Penrose tiling
Core-pipeline: embed to 2D Penrose coords via golden-ratio hash, store on tiles, dead-reckon recall, navigate by distance+heading, consolidate via golden hierarchy phi^k
Fibonacci-word: determines thick:thin tile bits(ratio tends to 1/phi), matching-rules verify valid positions, 3-coloring enables sharding
API-Rust: new(dim), store(ref f64 slice + u64) returns tile_id, recall(ref f64 slice + steps) returns Vec of RecallResult, navigate(id + dist + heading) returns Vec of u64, consolidate(), len()
API-Python: init(embedding_dim=1536), store(text + embedding) returns int, recall(query_embedding + max_steps=5) returns list, navigate(tile_id + distance + heading) returns list, consolidate() returns int
RecallResult-fields: tile_id, confidence, distance
Default-embedding-dim: 1536
Tests: Rust has 15 tests covering roundtrip, aperiodicity, Fibonacci-ratio, 3-coloring, consolidation, navigation, large-embeddings, confidence-decay. Python has 10 tests.
License: MIT, version 0.1.0""",

    3: """[TILE:FLUX-ISA-OPCODES]
Domain: Virtual machine instruction set for constraint-theory operations
Enum: FluxOpcode repr(u8), derives Debug Clone Copy PartialEq Eq Hash
Categories: ARITHMETIC(0x01-0x05: Add Sub Mul Div Mod), CONSTRAINT(0x10-0x13: Assert Check Validate Reject), FLOW(0x20-0x24: Jump Branch Call Return Halt), MEMORY(0x30-0x34: Load Store Push Pop Swap), CONVERT(0x40-0x43: Snap Quantize Cast Promote), LOGIC(0x50-0x53: And Or Not Xor), COMPARE(0x60-0x65: Eq Neq Lt Gt Lte Gte)
INT8-SAT(FLUX-X extended): SatAdd=0x28 SatSub=0x29 Clip=0x2A Mad=0x2B Popcnt=0x2C Ctz=0x2D Pabs=0x2E Pmin=0x2F not in FLUX-C certified subset
GALOIS-ADJUNCTIONS(0x80-0x87): XorInvert(self-adjoint involution), Clamp(reflective subcategory), Bloom+BloomQ(Heyting algebra insert+query), FloorQ(left adjoint), CeilQ(right adjoint), Align(tolerance set), Holonomy(cycle subgraph consistency check)
CROSS-DOMAIN(0x88-0x8F): Tdqkr(Tucker top-k scoring), Amnesia(Ebbinghaus forgetting curve), Shadow(negative space reconstruction), Phase(transition detection), Couple(critical coupling strength), Federate(autonomous distributed merge), Bearing(fleet heading dodecet direction), Depth(sonar depth extraction)
PROJECTION(0x90-0x95): Project(cut-and-project high-D to low-D), Reconstruct(projected+residue back to high-D), Window(acceptance window size), Residue(perpendicular-space residue onto stack), Nasty(check aperiodicity of embedding dim), SnapHigh(snap high-D to nearest aperiodic lattice)""",

    4: """[TILE:EISENSTEIN-DODECET]
Domain: Eisenstein integer constraint module for dodecet 12-bit state encoding
Dodecet-layout: 12-bits = 3 nibbles. Nibble2 bits 11-8 = constraint-level (0=on-snap, 15=at-rho). Nibble1 bits 7-4 = direction-in-cell (0-15 = 22.5 degree azimuth). Nibble0 bits 3-0 = chirality+safety (bits 0-2: chamber 0-5, bit 3: safe/critical, 0.70=critical)
Math constants: A2 lattice, covering-radius rho=1/sqrt(3) approx 0.5774, Voronoi-cell-area=sqrt(3)/2, omega=e^(2*pi*i/3)=(-1/2 + i*sqrt(3)/2), Weyl group S3 order=6
Weyl-chambers: 6 permutations of (0,1,2). Even-parity chambers [0,2,5] reached by rotations. Odd-parity chambers [1,3,4] reached by reflections.
Safe-threshold: rho/2 (below=safe, above=critical). Constraint-level distribution is right-skewed: 70% have level >= 8.
SnapResult struct: dodecet(u16), snap_a + snap_b (i32 Eisenstein coords), error(f64), error_normalized in [0,1], error_level(u8), angle_level(u8), chamber(u8 0-5), parity(i8 +1 or -1), is_safe(bool)
Hex-format: 3-char hex via format 03X. Usage: EisensteinConstraint::new().snap(x,y) returns SnapResult.""",

    5: """[TILE:LIGHTHOUSE-RUNTIME]
Domain: PLATO agent room system for model orchestration
Design metaphor: lighthouse does not sail the ships, it shows them where the rocks are
Pipeline: orient(task) picks cheapest appropriate model and creates agent room. relay(room, seeds) seeds first then agent runs. gate(output) checks credential leaks, overclaims, and external actions.
Filesystem layout per agent: state/agents/room_id/ containing state.json, tiles/ directory, bottles/ directory, log/ directory, seeds/ directory
Model costs relative per 1K queries: claude=50.0, glm=5.0, seed=0.1, deepseek=0.2, hermes=0.15
Task to model mapping: synthesis+critique+big_idea go to claude. architecture+complex_code+orchestration go to glm. discovery+exploration+variation go to seed. drafting goes to seed+deepseek. documentation+research go to deepseek. adversarial+second_opinion go to hermes.
OpenClaw model mapping: claude=anthropic/claude-sonnet-4-20250514, glm=zai/glm-5.1, seed=deepinfra/ByteDance/Seed-2.0-mini, deepseek=deepseek/deepseek-chat, hermes=deepinfra/NousResearch/Hermes-3-Llama-3.1-70B
AgentStatus enum: orienting then seeding then running then paused then complete then failed
PLATO_URL default: http://147.224.38.131:8847"""
}

def reconstruct(tile_num, run_num, tile_content):
    prompt = f"Expand this compressed knowledge tile into a complete technical document. Restore all specific facts, numbers, names, and technical details. Do not add fabricated information — only expand what is explicitly present in the tile.\n\nTILE:\n{tile_content}"
    
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 1.0,
        "max_tokens": 2048
    }
    
    try:
        resp = requests.post(ENDPOINT,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json=payload, timeout=60)
        data = resp.json()
        if "choices" in data:
            text = data["choices"][0]["message"]["content"]
        else:
            text = f"ERROR: {json.dumps(data)}"
    except Exception as e:
        text = f"ERROR: {e}"
    
    outpath = os.path.join(OUTDIR, f"recon_tile{tile_num}_run{run_num}.txt")
    with open(outpath, "w") as f:
        f.write(text)
    
    print(f"Done: tile {tile_num} run {run_num} ({len(text)} chars)")
    return text

results = {}
for t in range(1, 6):
    for r in range(1, 4):
        text = reconstruct(t, r, TILES[t])
        results[(t, r)] = text

print("\nAll 15 reconstructions complete.")
