#!/bin/bash
# z.ai P3 Experiment: Domain Tag Routing
# Tests whether domain tags shift model's internal routing

API_KEY="703f56774c324a76b8a283ce50b15744.tLKi6d9yeYza5Spg"
BASE_URL="https://api.z.ai/api/coding/paas/v4/chat/completions"
MODEL="glm-5-turbo"
OUTDIR="/home/phoenix/.openclaw/workspace/experiments/zai-p3"
RESULTS_FILE="$OUTDIR/raw_results.jsonl"

> "$RESULTS_FILE"

# 10 prompts across 5 domains (2 per domain)
declare -a PROMPTS=(
  # Math (0-1)
  "What is the derivative of x^3 * sin(x)?"
  "Prove that the square root of 2 is irrational."
  # Physics (2-3)
  "Explain the uncertainty principle in quantum mechanics."
  "What is the relationship between voltage, current, and resistance?"
  # Coding (4-5)
  "Write a function to reverse a linked list in Python."
  "Explain the difference between TCP and UDP protocols."
  # Biology (6-7)
  "How does CRISPR gene editing work at the molecular level?"
  "What is the role of mitochondria in cellular energy production?"
  # History (8-9)
  "What caused the fall of the Roman Empire?"
  "Explain the significance of the Industrial Revolution."
)

declare -a DOMAINS=("MATHEMATICS" "PHYSICS" "COMPUTER_SCIENCE" "BIOLOGY" "HISTORY")
declare -a DOMAIN_MAP=(0 0 1 1 2 2 3 3 4 4)  # prompt index -> domain index

# Mismatched domain mapping (shift by 2)
declare -a MISMATCH_MAP=(2 2 3 3 4 4 0 0 1 1)

call_api() {
  local prompt="$1"
  local tag="$2"
  local trial="$3"
  local pidx="$4"
  local condition="$5"  # NOTAG, MATCHED, MISMATCHED
  
  local full_prompt="$prompt"
  if [ -n "$tag" ]; then
    full_prompt="[$tag] $prompt"
  fi

  # Escape for JSON
  local escaped_prompt=$(echo "$full_prompt" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read().strip()))")
  
  local response=$(curl -s --max-time 30 "$BASE_URL" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $API_KEY" \
    -d "{
      \"model\": \"$MODEL\",
      \"messages\": [{\"role\": \"user\", \"content\": $escaped_prompt}],
      \"max_tokens\": 1000,
      \"temperature\": 0.3
    }")
  
  # Extract response text and token count
  local content=$(echo "$response" | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    c=d['choices'][0]['message']['content']
    u=d.get('usage',{})
    print(json.dumps({'content':c,'prompt_tokens':u.get('prompt_tokens',0),'completion_tokens':u.get('completion_tokens',0),'total_tokens':u.get('total_tokens',0)}))
except Exception as e:
    print(json.dumps({'content':str(e),'prompt_tokens':0,'completion_tokens':0,'total_tokens':0}))
" 2>/dev/null)
  
  # Write result as JSONL
  python3 -c "
import json,sys
r = json.loads('''$content''')
result = {
    'prompt_idx': $pidx,
    'domain': '${DOMAINS[${DOMAIN_MAP[$pidx]}]}',
    'condition': '$condition',
    'tag': '$tag' if '$tag' else None,
    'trial': $trial,
    'prompt': '''$(echo "$prompt" | sed "s/'/'\\\\''/g")''',
    'response': r['content'],
    'prompt_tokens': r['prompt_tokens'],
    'completion_tokens': r['completion_tokens'],
    'total_tokens': r['total_tokens'],
    'response_length': len(r['content']),
}
print(json.dumps(result))
" >> "$RESULTS_FILE"
}

echo "Starting z.ai P3 experiment: 90 API calls (10 prompts × 3 conditions × 3 trials)"
echo "Start time: $(date -Iseconds)"

total=0
for pidx in $(seq 0 9); do
  prompt="${PROMPTS[$pidx]}"
  domain="${DOMAINS[${DOMAIN_MAP[$pidx]}]}"
  mismatch="${DOMAINS[${MISMATCH_MAP[$pidx]}]}"
  
  for trial in $(seq 1 3); do
    # Condition 1: NO TAG
    call_api "$prompt" "" "$trial" "$pidx" "NOTAG"
    total=$((total+1))
    echo "[$total/90] Prompt $pidx, NOTAG, trial $trial"
    
    # Condition 2: MATCHED TAG
    call_api "$prompt" "$domain" "$trial" "$pidx" "MATCHED"
    total=$((total+1))
    echo "[$total/90] Prompt $pidx, MATCHED ($domain), trial $trial"
    
    # Condition 3: MISMATCHED TAG
    call_api "$prompt" "$mismatch" "$trial" "$pidx" "MISMATCHED"
    total=$((total+1))
    echo "[$total/90] Prompt $pidx, MISMATCHED ($mismatch), trial $trial"
    
    # Small delay to avoid rate limits
    sleep 0.3
  done
done

echo "End time: $(date -Iseconds)"
echo "Total calls: $total"
echo "Results written to $RESULTS_FILE"
echo "Line count: $(wc -l < "$RESULTS_FILE")"
