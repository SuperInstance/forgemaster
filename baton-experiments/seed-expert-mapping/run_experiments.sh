#!/bin/bash
# Seed 2.0 Mini Expert Pathway Mapping Experiment
# 10 categories × 3 trials × 3 reasoning efforts = 90 calls

API_KEY="${DEEPINFRA_KEY}"
ENDPOINT="https://api.deepinfra.com/v1/openai/chat/completions"
MODEL="ByteDance/Seed-2.0-mini"
OUTDIR="/home/phoenix/.openclaw/workspace/baton-experiments/seed-expert-mapping"
RAWDIR="$OUTDIR/raw"

mkdir -p "$RAWDIR"

# Define prompts (indexed by category number)
declare -A PROMPTS
PROMPTS[1]="Write a Rust function that computes snap(x,y) to the nearest Eisenstein lattice point. The Eisenstein integers are a + b*ω where ω = (-1 + i√3)/2. The function should take (x: f64, y: f64) and return the nearest Eisenstein integer as (i64, i64) representing coefficients (a, b)."
PROMPTS[2]="Prove that the Fibonacci word thick:thin ratio converges to 1/φ where φ = (1+√5)/2. The Fibonacci word is the fixed point of the morphism 0→01, 1→0. Show your work step by step."
PROMPTS[3]="Given experimental results from a Penrose Memory Palace system (where knowledge is encoded in Penrose tiling coordinates and reconstructed via temperature-based sampling), generate 3 novel falsifiable hypotheses about the relationship between aperiodic tilings and information storage density."
PROMPTS[4]="Expand this compressed knowledge tile: 'Penrose(P3):rhombus-thin(36°,144°)×rhombus-thick(72°,108°)|matching:Ammann-bars|inflate:τ-scaling|covering:Gummelt-single-decagon|covering%:10.7%overlap→exact-tile|substitution:7→7|edge-match:arrow+arrow-not|diffraction:bragg-peaks@5fold|entropy-config:0|pinwheel-dense:subgroup-Z[τ]→continuum-rotations'. Reconstruct the full technical explanation from this compressed representation."
PROMPTS[5]="Find the flaw in this argument: 'Since Penrose tilings are aperiodic, no finite patch can determine the tiling uniquely. Therefore, any encoding of information in Penrose coordinates is fundamentally lossy, because the reconstruction algorithm cannot distinguish between the exponentially many completions of any finite patch. This proves that Penrose-based memory systems have unbounded information loss.'"
PROMPTS[6]="Connect Penrose tilings to neural network attention mechanisms. Specifically: how do the self-similar hierarchy of Penrose tilings and the multi-head attention pattern in transformers share mathematical structure? What does this connection imply for designing more efficient attention mechanisms?"
PROMPTS[7]="Design a REST API for a Penrose-based memory store. The store encodes knowledge tiles as coordinates in a Penrose tiling, supports reconstruction with configurable temperature, and returns expanded knowledge from compressed tiles. Include endpoints, data models, error handling, and a sketch of the internal tiling engine."
PROMPTS[8]="Why does temperature 1.0 produce optimal reconstructions in a Penrose Memory Palace system, where lower temperatures produce rigid/collapsed outputs and higher temperatures produce noisy/chaotic ones? Explain the statistical mechanics analogy."
PROMPTS[9]="This Rust code has a bug. Find it: 'fn snap_to_eisenstein(x: f64, y: f64) -> (i64, i64) { let omega_x = -0.5; let omega_y = 3.0_f64.sqrt() / 2.0; let a = x.round() as i64; let b = (y / omega_y).round() as i64; (a, b) }'"
PROMPTS[10]="Analyze your own reasoning process in answering this question. What internal representations did you form? What shortcuts did you take? Where were you uncertain? How would you verify your answer if you had tools?"

declare -A CATNAMES
CATNAMES[1]="pure_code"
CATNAMES[2]="math_proof"
CATNAMES[3]="hypothesis_gen"
CATNAMES[4]="reconstruction"
CATNAMES[5]="adversarial"
CATNAMES[6]="cross_domain"
CATNAMES[7]="concrete_app"
CATNAMES[8]="abstract_reasoning"
CATNAMES[9]="error_analysis"
CATNAMES[10]="meta_cognitive"

EFFORTS=("default" "low" "high")

run_experiment() {
    local cat=$1
    local trial=$2
    local effort=$3
    local catname="${CATNAMES[$cat]}"
    local fname="${catname}_trial${trial}_${effort}"
    
    local effort_json=""
    if [ "$effort" != "default" ]; then
        effort_json=", \"reasoning_effort\": \"$effort\""
    fi
    
    local prompt="${PROMPTS[$cat]}"
    
    # Use a temp file for the JSON body to avoid escaping issues
    local tmpbody=$(mktemp)
    cat > "$tmpbody" << ENDJSON
{
  "model": "$MODEL",
  "messages": [{"role": "user", "content": $(printf '%s' "$prompt" | jq -Rs .)}],
  "temperature": 1.0,
  "max_tokens": 4096$effort_json
}
ENDJSON
    
    local result=$(curl -s -w "\n%{http_code}" "$ENDPOINT" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d @"$tmpbody" \
        --max-time 120)
    
    local http_code=$(echo "$result" | tail -1)
    local body=$(echo "$result" | sed '$d')
    
    # Save raw response
    echo "$body" > "$RAWDIR/${fname}.json"
    
    # Extract metrics
    local content=$(echo "$body" | jq -r '.choices[0].message.content // empty' 2>/dev/null)
    local usage=$(echo "$body" | jq -r '.usage.completion_tokens // "error"' 2>/dev/null)
    local total_tokens=$(echo "$body" | jq -r '.usage.total_tokens // "error"' 2>/dev/null)
    local prompt_tokens=$(echo "$body" | jq -r '.usage.prompt_tokens // "error"' 2>/dev/null)
    local finish_reason=$(echo "$body" | jq -r '.choices[0].finish_reason // "error"' 2>/dev/null)
    
    # Count self-corrections (heuristic: words like "actually", "wait", "correction", "let me revise", "I was wrong")
    local corrections=0
    if [ -n "$content" ]; then
        corrections=$(echo "$content" | grep -oiE '(actually|wait,|correction|let me revise|i was wrong|on second thought|however,|that.s not right|mistake)' | wc -l)
    fi
    
    # Response length
    local char_count=0
    local word_count=0
    if [ -n "$content" ]; then
        char_count=$(echo "$content" | wc -c)
        word_count=$(echo "$content" | wc -w)
    fi
    
    # Detect if response has code blocks
    local has_code="no"
    if echo "$content" | grep -q '```'; then
        has_code="yes"
    fi
    
    # Detect math notation
    local has_math="no"
    if echo "$content" | grep -qE '(\$|\\\\|∑|∫|→|φ|ω)'; then
        has_math="yes"
    fi
    
    # Detect structured output (numbered lists, headers)
    local has_structure="no"
    if echo "$content" | grep -qE '(^#{1,3} |^[0-9]+\.|^- )'; then
        has_structure="yes"
    fi
    
    rm -f "$tmpbody"
    
    # Output as JSON line
    jq -n \
        --arg category "$catname" \
        --argjson cat_num "$cat" \
        --argjson trial "$trial" \
        --arg effort "$effort" \
        --argjson completion_tokens "$usage" \
        --argjson total_tokens "$total_tokens" \
        --argjson prompt_tokens "$prompt_tokens" \
        --argjson char_count "$char_count" \
        --argjson word_count "$word_count" \
        --argjson corrections "$corrections" \
        --arg has_code "$has_code" \
        --arg has_math "$has_math" \
        --arg has_structure "$has_structure" \
        --arg finish_reason "$finish_reason" \
        --arg http_code "$http_code" \
        '{category: $category, cat_num: $cat_num, trial: $trial, effort: $effort, completion_tokens: $completion_tokens, total_tokens: $total_tokens, prompt_tokens: $prompt_tokens, char_count: $char_count, word_count: $word_count, corrections: $corrections, has_code: $has_code, has_math: $has_math, has_structure: $has_structure, finish_reason: $finish_reason, http_code: $http_code}' \
        >> "$OUTDIR/metrics.jsonl"
    
    echo "  ✓ $fname: tokens=$usage, chars=$char_count, corrections=$corrections, code=$has_code, math=$has_math, struct=$has_structure"
}

echo "=== Seed 2.0 Mini Expert Pathway Mapping ==="
echo "Starting at $(date)"
echo "" > "$OUTDIR/metrics.jsonl"

TOTAL=0
DONE=0
for cat in $(seq 1 10); do
    for effort in "${EFFORTS[@]}"; do
        ((TOTAL++))
    done
done
TOTAL=$((TOTAL * 3))  # 3 trials each
echo "Total experiments: $TOTAL"

for cat in $(seq 1 10); do
    catname="${CATNAMES[$cat]}"
    echo ""
    echo "--- Category $cat: $catname ---"
    for effort in "${EFFORTS[@]}"; do
        for trial in $(seq 1 3); do
            ((DONE++))
            echo "[$DONE/$TOTAL] ${catname}_t${trial}_${effort}..."
            run_experiment "$cat" "$trial" "$effort"
        done
    done
done

echo ""
echo "=== Complete: $DONE experiments at $(date) ==="
