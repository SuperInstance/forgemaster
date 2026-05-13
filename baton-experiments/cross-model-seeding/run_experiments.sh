#!/bin/bash
set -euo pipefail

API_KEY="${DEEPINFRA_KEY}"
ENDPOINT="https://api.deepinfra.com/v1/openai/chat/completions"
OUTDIR="/home/phoenix/.openclaw/workspace/baton-experiments/cross-model-seeding"

MODELS=("ByteDance/Seed-2.0-mini" "NousResearch/Hermes-3-Llama-3.1-70B" "Qwen/Qwen3.6-35B-A3B")
MODEL_SHORT=("seed-mini" "hermes-70b" "qwen-35b")

call_api() {
  local model="$1" temp="$2" prompt="$3" outfile="$4"
  
  # Escape prompt for JSON
  local escaped_prompt=$(echo "$prompt" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')
  
  local payload="{\"model\":\"$model\",\"messages\":[{\"role\":\"user\",\"content\":${escaped_prompt}}],\"temperature\":$temp,\"max_tokens\":2048}"
  
  echo "Calling $model at temp=$temp..."
  curl -s "$ENDPOINT" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d "$payload" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if 'choices' in data:
    print(data['choices'][0]['message']['content'])
else:
    print('ERROR:', json.dumps(data))
" > "$outfile" 2>&1
  echo "  -> $outfile ($(wc -c < "$outfile") bytes)"
}

# EXPERIMENT 1: Novel Question Generation
echo "=== EXPERIMENT 1: Novel Question Generation ==="
PROMPT1='Given the Penrose Memory Palace architecture (aperiodic coordinates for AI retrieval using Fibonacci words, cut-and-project from 5D to 2D, golden ratio hashing), generate 3 novel, falsifiable research questions that could reveal unexpected properties. For each question, explain why it is falsifiable and how you would test it in under 100 lines of Python.'

for i in 0 1 2; do
  call_api "${MODELS[$i]}" 1.0 "$PROMPT1" "$OUTDIR/exp1_${MODEL_SHORT[$i]}_t1.0.txt" &
done
wait
echo "Experiment 1 complete."

# EXPERIMENT 2: Reconstruction Accuracy
echo "=== EXPERIMENT 2: Reconstruction Accuracy ==="
TILE='Eisenstein integers E₆ = ℤ[ω] where ω = e^(2πi/6) provide 12-fold rotational symmetry. snap(x,y) maps any (x,y) → nearest E₆ lattice point in O(1) via hex grid. Compared to Float32: zero cumulative drift over 1M operations. The dodecet (12-point neighborhood) encodes position with 4 bytes. Constraint checking: if snap(a) ⊕ snap(b) has weight > 2, operation is flagged. GPU benchmark: 341B constraints/sec on RTX 4050 with INT8 packing.'

PROMPT2="Reconstruct the FULL technical description from this compressed summary. Expand every abbreviation, explain every symbol, derive the full mathematical framework, and include implementation details that were compressed away.\n\nCompressed tile:\n$TILE"

for i in 0 1 2; do
  call_api "${MODELS[$i]}" 1.0 "$PROMPT2" "$OUTDIR/exp2_${MODEL_SHORT[$i]}_t1.0.txt" &
done
wait
echo "Experiment 2 complete."

# EXPERIMENT 3: Temperature Sensitivity
echo "=== EXPERIMENT 3: Temperature Sensitivity ==="
TEMPS=(0.3 0.7 1.0 1.3 1.5)

for i in 0 1 2; do
  for t in "${TEMPS[@]}"; do
    call_api "${MODELS[$i]}" "$t" "$PROMPT2" "$OUTDIR/exp3_${MODEL_SHORT[$i]}_t${t}.txt" &
  done
  # Serialize per model to avoid rate limits
  wait
  echo "  ${MODEL_SHORT[$i]} temperature sweep complete."
done
echo "Experiment 3 complete."
echo "=== ALL EXPERIMENTS DONE ==="
