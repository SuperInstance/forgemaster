#!/bin/bash
set -euo pipefail

API_KEY="woKHPYOPyNkSUHFkkqAf90snZ1T9kqH7"
ENDPOINT="https://api.deepinfra.com/v1/openai/chat/completions"
OUTDIR="/home/phoenix/.openclaw/workspace/baton-experiments/cross-model-seeding"

call_api_qwen() {
  local temp="$1" prompt="$2" outfile="$3"
  local escaped_prompt=$(echo "$prompt" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')
  local payload="{\"model\":\"Qwen/Qwen3.6-35B-A3B\",\"messages\":[{\"role\":\"user\",\"content\":${escaped_prompt}}],\"temperature\":$temp,\"max_tokens\":4096}"
  
  echo "Calling Qwen at temp=$temp..."
  curl -s "$ENDPOINT" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d "$payload" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if 'choices' in data and data['choices'][0]['message']['content']:
    print(data['choices'][0]['message']['content'])
else:
    print('ERROR:', json.dumps(data))
" > "$outfile" 2>&1
  echo "  -> $outfile ($(wc -c < "$outfile") bytes)"
}

PROMPT1='Given the Penrose Memory Palace architecture (aperiodic coordinates for AI retrieval using Fibonacci words, cut-and-project from 5D to 2D, golden ratio hashing), generate 3 novel, falsifiable research questions that could reveal unexpected properties. For each question, explain why it is falsifiable and how you would test it in under 100 lines of Python.'

TILE='Eisenstein integers E₆ = ℤ[ω] where ω = e^(2πi/6) provide 12-fold rotational symmetry. snap(x,y) maps any (x,y) → nearest E₆ lattice point in O(1) via hex grid. Compared to Float32: zero cumulative drift over 1M operations. The dodecet (12-point neighborhood) encodes position with 4 bytes. Constraint checking: if snap(a) ⊕ snap(b) has weight > 2, operation is flagged. GPU benchmark: 341B constraints/sec on RTX 4050 with INT8 packing.'

PROMPT2="Reconstruct the FULL technical description from this compressed summary. Expand every abbreviation, explain every symbol, derive the full mathematical framework, and include implementation details that were compressed away.\n\nCompressed tile:\n$TILE"

# Experiment 1 & 2
call_api_qwen 1.0 "$PROMPT1" "$OUTDIR/exp1_qwen-35b_t1.0.txt"
call_api_qwen 1.0 "$PROMPT2" "$OUTDIR/exp2_qwen-35b_t1.0.txt"

# Experiment 3: temperature sweep
TEMPS=(0.3 0.7 1.0 1.3 1.5)
for t in "${TEMPS[@]}"; do
  call_api_qwen "$t" "$PROMPT2" "$OUTDIR/exp3_qwen-35b_t${t}.txt"
done

echo "=== Qwen experiments complete ==="
