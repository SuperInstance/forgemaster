#!/bin/bash
# Seed-2.0-mini Ablation Study
API_KEY="woKHPYOPyNkSUHFkkqAf90snZ1T9kqH7"
ENDPOINT="https://api.deepinfra.com/v1/openai/chat/completions"
MODEL="ByteDance/Seed-2.0-mini"
OUTDIR="/home/phoenix/.openclaw/workspace/baton-experiments/seed-ablation"

# Source text facts (7 key facts):
# 1. aperiodic Penrose P3 tilings as spatial coords
# 2. golden-ratio hash index
# 3. dead reckoning navigation
# 4. Fibonacci word encoding
# 5. 5D cut-and-project
# 6. deflation consolidation
# 7. 3-color baton sharding
# 8. C9 locality failure (quantization)

# Actually 8 facts - let me re-read the task... it says "7 facts" but lists 8 items.
# I'll score all 8.

FACTS=("aperiodic" "golden.ratio hash" "dead reckoning" "Fibonacci" "5D cut.and.project" "deflation" "3.color baton" "C9 locality")

# Tile formats
FMT1='Penrose P3 tiling, aperiodic spatial coords, AI memory. Golden-ratio hash index. Dead reckoning nav. Fibonacci word IDs. 5D cut-and-project. Deflation consolidation. 3-color baton sharding. C9 locality fails.'
FMT2='Penrose P3 aperiodic memory spatial coords golden hash dead reckoning Fibonacci cut-project deflation 3-color baton C9 locality'
FMT3='{"name": "Penrose Memory Palace", "tiling": "P3", "nav": "dead_reckoning", "encoding": "Fibonacci", "dims": 5, "consolidation": "deflation", "sharding": "3-color baton", "limitation": "C9 locality"}'
FMT4='Imagine a palace where rooms never repeat. Penrose tilings make each room unique. You navigate by feel — distance and direction from where you stand. The Fibonacci sequence names each room. Cut from 5 dimensions to 2. When full, rooms merge by deflation. Three colors split the palace between agents. But rooms that should be neighbors sometimes become strangers — this is the C9 failure.'
FMT5='The Penrose Memory Palace uses aperiodic Penrose P3 tilings as spatial coordinates for AI memory retrieval.'

score_reconstruction() {
    local text="$1"
    local score=0
    
    # 1. aperiodic
    echo "$text" | grep -qi "aperiodic" && score=$((score + 1))
    # 2. golden-ratio hash
    echo "$text" | grep -qi "golden" && echo "$text" | grep -qi "hash" && score=$((score + 1))
    # 3. dead reckoning
    echo "$text" | grep -qi "dead.reckon" && score=$((score + 1))
    # 4. Fibonacci
    echo "$text" | grep -qi "fibonacci" && score=$((score + 1))
    # 5. 5D cut-and-project
    (echo "$text" | grep -qi "5.d\|five.dimensional\|5d") && (echo "$text" | grep -qi "cut.and.project\|projection") && score=$((score + 1))
    # 6. deflation
    echo "$text" | grep -qi "deflat" && score=$((score + 1))
    # 7. 3-color baton
    (echo "$text" | grep -qi "3.color\|three.color") && echo "$text" | grep -qi "baton\|shard" && score=$((score + 1))
    # 8. C9 locality
    echo "$text" | grep -qi "C9\|locality" && score=$((score + 1))
    
    echo $score
}

call_api() {
    local prompt="$1"
    local temp="$2"
    local response
    response=$(curl -s --max-time 60 "$ENDPOINT" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d "$(jq -n \
            --arg model "$MODEL" \
            --argjson temp "$temp" \
            --arg user "$prompt" \
            '{model: $model, temperature: $temp, max_tokens: 1024, messages: [{role: "user", content: $user}]}')")
    echo "$response" | jq -r '.choices[0].message.content // "ERROR: " + (tojson)'
}

echo "========================================="
echo "SEED-2.0-MINI ABLATION STUDY"
echo "========================================="
echo ""

# ==========================================
# EXPERIMENT A: Tile Format Ablation
# ==========================================
echo "=== EXPERIMENT A: Tile Format Ablation ==="
echo ""

declare -A FMTS
FMTS[1]="$FMT1"
FMTS[2]="$FMT2"
FMTS[3]="$FMT3"
FMTS[4]="$FMT4"
FMTS[5]="$FMT5"

FMT_NAMES=("minimal-maximal" "keyword-only" "structured-json" "narrative" "first-sentence-only")

PROMPT_A="Reconstruct the full technical description from this compressed summary. "

EXPA_FILE="$OUTDIR/exp_a_raw.txt"
> "$EXPA_FILE"

EXPA_RESULTS="$OUTDIR/exp_a_scores.txt"
> "$EXPA_RESULTS"

for i in 1 2 3 4 5; do
    echo "--- Format $i: ${FMT_NAMES[$((i-1))]} ---"
    echo "FORMAT $i: ${FMT_NAMES[$((i-1))]}" >> "$EXPA_FILE"
    
    tile="${FMTS[$i]}"
    prompt="${PROMPT_A}${tile}"
    
    result=$(call_api "$prompt" 1.0)
    score=$(score_reconstruction "$result")
    
    echo "Score: $score/8" | tee -a "$EXPA_RESULTS"
    echo "" >> "$EXPA_FILE"
    echo "Response:" >> "$EXPA_FILE"
    echo "$result" >> "$EXPA_FILE"
    echo "---" >> "$EXPA_FILE"
    echo "" >> "$EXPA_FILE"
    
    echo "$i ${FMT_NAMES[$((i-1))]} $score" >> "$EXPA_RESULTS"
    echo ""
done

echo ""
echo "========================================="
echo ""
echo "=== EXPERIMENT B: Temperature Sweep ==="
echo ""

EXPB_FILE="$OUTDIR/exp_b_raw.txt"
> "$EXPB_FILE"

EXPB_RESULTS="$OUTDIR/exp_b_scores.csv"
echo "temperature,trial,score" > "$EXPB_RESULTS"

TEMPS=(0.1 0.3 0.5 0.7 0.8 0.9 1.0 1.1 1.2 1.3 1.5 1.7 2.0)

for temp in "${TEMPS[@]}"; do
    echo "--- Temperature: $temp ---"
    for trial in 1 2 3; do
        prompt="${PROMPT_A}${FMT1}"
        result=$(call_api "$prompt" "$temp")
        score=$(score_reconstruction "$result")
        
        echo "  Trial $trial: $score/8"
        echo "$temp,$trial,$score" >> "$EXPB_RESULTS"
        
        echo "TEMP=$temp TRIAL=$trial SCORE=$score" >> "$EXPB_FILE"
        echo "$result" >> "$EXPB_FILE"
        echo "---" >> "$EXPB_FILE"
    done
    echo ""
done

echo ""
echo "========================================="
echo ""
echo "=== EXPERIMENT C: Prompt Sensitivity ==="
echo ""

EXPC_FILE="$OUTDIR/exp_c_raw.txt"
> "$EXPC_FILE"

EXPC_RESULTS="$OUTDIR/exp_c_scores.csv"
echo "prompt_id,prompt_name,trial,score" > "$EXPC_RESULTS"

PROMPT_C_NAMES=("reconstruct" "original-text" "expand-tile" "research-note" "decode-expand")
PROMPT_C=(
    "Reconstruct the full technical description from this compressed summary. ${FMT1}"
    "What was the original text that was compressed into this tile? Reconstruct it. ${FMT1}"
    "Expand this compressed knowledge tile into a complete technical document. ${FMT1}"
    "Based on this summary, write the full research note. ${FMT1}"
    "Decode and expand: ${FMT1}"
)

for pid in 0 1 2 3 4; do
    echo "--- Prompt $((pid+1)): ${PROMPT_C_NAMES[$pid]} ---"
    for trial in 1 2 3; do
        result=$(call_api "${PROMPT_C[$pid]}" 1.0)
        score=$(score_reconstruction "$result")
        
        echo "  Trial $trial: $score/8"
        echo "$((pid+1)),${PROMPT_C_NAMES[$pid]},$trial,$score" >> "$EXPC_RESULTS"
        
        echo "PROMPT=$((pid+1)) ${PROMPT_C_NAMES[$pid]} TRIAL=$trial SCORE=$score" >> "$EXPC_FILE"
        echo "$result" >> "$EXPC_FILE"
        echo "---" >> "$EXPC_FILE"
    done
    echo ""
done

echo ""
echo "========================================="
echo "All experiments complete. Generating analysis..."
echo "========================================="
