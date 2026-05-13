#!/bin/bash
# Seed-2.0-mini reconstruction test
API_KEY=$(cat ~/.openclaw/workspace/.credentials/deepinfra-api-key.txt)
ENDPOINT="https://api.deepinfra.com/v1/openai/chat/completions"
MODEL="ByteDance/Seed-2.0-mini"
OUTDIR="/home/phoenix/.openclaw/workspace/baton-experiments/seed-recon-real"

# Helper: call Seed-2.0-mini
reconstruct() {
    local tile_num=$1
    local run=$2
    local tile_content="$3"
    
    local payload=$(jq -n \
        --arg model "$MODEL" \
        --arg prompt "Expand this compressed knowledge tile into a complete technical document. Restore all specific facts, numbers, names, and technical details. Do not add fabricated information — only expand what is explicitly present in the tile.\n\nTILE:\n$tile_content" \
        '{
            model: $model,
            messages: [{role: "user", content: $prompt}],
            temperature: 1.0,
            max_tokens: 2048
        }')
    
    echo "=== Tile $tile_num, Run $run ===" >&2
    curl -s "$ENDPOINT" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d "$payload" | jq -r '.choices[0].message.content // "ERROR: " + (.error.message // "unknown")' > "$OUTDIR/recon_tile${tile_num}_run${run}.txt"
    echo "Done: tile $tile_num run $run" >&2
}

export -f reconstruct
export API_KEY ENDPOINT MODEL OUTDIR

# Tile 1: Ground Truth Audit
T1='[TILE:GROUND-TRUTH-AUDIT]
Domain: Neural-PLATO ground truth verification experiment
Scope: 34 claims across 4 tiers of evidence strength
Key: Tier1=proven-by-code(23 claims), Tier2=standard-math(6), Tier3=partial-verify(2), Tier4=speculative(3)
Results: Fibonacci-word thick:thin→1/φ(n=10000,delta=0.000034), matching-rules 99.19%@n=10000, 3-coloring verified 40×40, golden-twist aperiodic 0-repeats@10000, Boltzmann entropy T=1.0=1.93 vs T=0.1=0.002, 2D captures 2.54% of 64D energy, snap-errors 100% localized(849/849)
Negatives: golden NOT special for compression(Q1), 3-coloring no retrieval help(Q8), locality after quantization FAILS(C9)
Baton-results: temp=1.0 optimal 100%@$0.01, split=3 optimal(75%), amnesia-cliff at 10%→0%
Tier3-gap: tile-type classification by perpendicular-space position needs fixing, thick:thin ratio ≈ φ not yet verified properly
Ground-truth-ratio: 85%(29/34), 5 unfounded = 6 trusted-theorems + 2 partial + 3 speculative labeled'

# Tile 2: Penrose Memory
T2='[TILE:PENROSE-MEMORY]
Domain: Rust+Python crate for aperiodic memory palace using Penrose tiling
Core-pipeline: embed→2D-Penrose-coords(golden-ratio-hash)→store-tiles→dead-reckon-recall→navigate-by-distance+heading→consolidate(golden-hierarchy φ^k)
Fibonacci-word: determines thick:thin tile bits(ratio→1/φ), matching-rules verify valid positions, 3-coloring enables sharding
API-Rust: new(dim), store(&[f64],u64)→tile_id, recall(&[f64],steps)→Vec<RecallResult>, navigate(id,dist,heading)→Vec<u64>, consolidate(), len()
API-Python: __init__(embedding_dim=1536), store(text,embedding)→int, recall(query_embedding,max_steps=5)→list, navigate(tile_id,distance,heading)→list, consolidate()→int
RecallResult-fields: tile_id, confidence, distance
Default-embedding-dim: 1536
Tests: Rust=15(roundtrip,aperiodicity,Fibonacci-ratio,3-coloring,consolidation,navigation,large-embeddings,confidence-decay), Python=10
License: MIT, version 0.1.0'

# Tile 3: FLUX ISA Opcodes
T3='[TILE:FLUX-ISA-OPCODES]
Domain: Virtual machine instruction set for constraint-theory operations
Enum: FluxOpcode repr(u8), derives(Debug,Clone,Copy,PartialEq,Eq,Hash)
Categories: ARITHMETIC(0x01-0x05: Add/Sub/Mul/Div/Mod), CONSTRAINT(0x10-0x13: Assert/Check/Validate/Reject), FLOW(0x20-0x24: Jump/Branch/Call/Return/Halt), MEMORY(0x30-0x34: Load/Store/Push/Pop/Swap), CONVERT(0x40-0x43: Snap/Quantize/Cast/Promote), LOGIC(0x50-0x53: And/Or/Not/Xor), COMPARE(0x60-0x65: Eq/Neq/Lt/Gt/Lte/Gte)
INT8-SAT(FLUX-X): SatAdd=0x28,SatSub=0x29,Clip=0x2A,Mad=0x2B,Popcnt=0x2C,Ctz=0x2D,Pabs=0x2E,Pmin=0x2F
GALOIS-ADJUNCTIONS(0x80-0x87): XorInvert(self-adjoint),Clamp(reflective-subcategory),Bloom/BloomQ(Heyting-algebra),FloorQ(left-adjoint),CeilQ(right-adjoint),Align(tolerance-set),Holonomy(cycle-check)
CROSS-DOMAIN(0x88-0x8F): Tdqkr(Tucker-top-k),Amnesia(Ebbinghaus-decay),Shadow(negative-space),Phase(transition),Couple(strength),Federate(distributed-merge),Bearing(dodecet),Depth(sonar)
PROJECTION(0x90-0x95): Project,Reconstruct,Window,Residue,Nasty,SnapHigh'

# Tile 4: Eisenstein / Dodecet Encoder
T4='[TILE:EISENSTEIN-DODECET]
Domain: Eisenstein integer constraint module for dodecet 12-bit state encoding
Dodecet-layout: 12-bits=3-nibbles, nibble2(11-8)=constraint-level(0=on-snap,15=at-ρ), nibble1(7-4)=direction-in-cell(0-15=22.5°azimuth), nibble0(3-0)=chirality+chamber(0-2:chamber0-5, bit3:safe/crit 0.70=crit)
Math: A₂-lattice, covering-radius ρ=1/√3≈0.5774, Voronoi-cell-area=√3/2, ω=e^(2πi/3)=-½+i√3/2, Weyl-group S₃ order=6
Weyl-chambers: 6 permutations of(0,1,2), chambers[0,2,5]=even-parity(rotations), chambers[1,3,4]=odd-parity(reflections)
Safe-threshold: ρ/2 (below=safe, above=critical), constraint-level 70%≥8(right-skewed)
SnapResult: dodecet(u16), snap_a/snap_b(i32), error(f64), error_normalized[0,1], error_level(u8), angle_level(u8), chamber(u8 0-5), parity(i8 ±1), is_safe(bool)
Hex-format: 3-char hex string, e.g. 0x{:03X}
Usage: EisensteinConstraint::new().snap(x,y)→SnapResult'

# Tile 5: Lighthouse Runtime
T5='[TILE:LIGHTHOUSE-RUNTIME]
Domain: PLATO agent room system for model orchestration
Metaphor: "lighthouse doesn\'t sail ships, shows where rocks are"
Pipeline: orient(task)→pick-cheapest-model→create-room, relay(room,seeds)→seed-first-then-agent-runs, gate(output)→credential/overclaim/external-checks
Filesystem: state/agents/{room_id}/ with state.json, tiles/, bottles/, log/, seeds/
Model-costs(rel/1K-queries): claude=50, glm=5, seed=0.1, deepseek=0.2, hermes=0.15
Task→model: synthesis/critique/big_idea→claude, architecture/complex_code/orchestration→glm, discovery/exploration/variation→seed, drafting→seed+deepseek, documentation/research→deepseek, adversarial/second_opinion→hermes
OpenClaw-models: claude=anthropic/claude-sonnet-4-20250514, glm=zai/glm-5.1, seed=deepinfra/ByteDance/Seed-2.0-mini, deepseek=deepseek/deepseek-chat, hermes=deepinfra/NousResearch/Hermes-3-Llama-3.1-70B
AgentStatus-enum: orienting→seeding→running→paused→complete→failed
PLATO_URL: http://147.224.38.131:8847'

echo "Starting 15 reconstructions..."

# Run all 15 in parallel (5 tiles × 3 runs each)
for t in 1 2 3 4 5; do
    var="T$t"
    tile="${!var}"
    for r in 1 2 3; do
        reconstruct $t $r "$tile" &
    done
done

wait
echo "All 15 reconstructions complete."
