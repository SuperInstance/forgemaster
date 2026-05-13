#!/bin/bash
# ============================================================================
# z.ai Experiment 2: Reasoning-Effort Cue Impact on GLM Models
# ============================================================================
# Tests whether reasoning-effort tags change GLM-5.1's reasoning token usage,
# and compares head-to-head with GLM-5-turbo (expected non-reasoning).
#
# Design:
#   - 3 conditions: [THINK_STEP_BY_STEP], [BE_CONCISE], NO_TAG
#   - 2 models: glm-5.1 (reasoning), glm-5-turbo (non-reasoning)
#   - 6 reasoning-heavy prompts × 3 trials each = 54 calls per model = 108 total
#   - max_tokens=4096 (enough headroom for reasoning + response)
#
# Metrics captured:
#   - reasoning_tokens (from completion_tokens_details)
#   - reasoning_content length (characters)
#   - response_content length and quality
#   - completion_tokens total
#   - Time to first token / total latency
#
# DO NOT RUN THIS WITHOUT EXPLICIT APPROVAL — it makes 108 paid API calls.
# ============================================================================

set -euo pipefail

API_KEY="703f56774c324a76b8a283ce50b15744.tLKi6d9yeYza5Spg"
BASE_URL="https://api.z.ai/api/coding/paas/v4/chat/completions"
OUTDIR="/home/phoenix/.openclaw/workspace/experiments/zai-p3"
RESULTS_FILE="$OUTDIR/experiment2_results.jsonl"
SUMMARY_FILE="$OUTDIR/experiment2_summary.txt"

# Clear results
> "$RESULTS_FILE"

# --- Models ---
MODEL_REASONING="glm-5.1"
MODEL_STANDARD="glm-5-turbo"
MODELS=("$MODEL_REASONING" "$MODEL_STANDARD")

# --- Reasoning-effort conditions ---
# Each condition: NAME | TAG_PREFIX
CONDITIONS=(
  "THINK_STEP_BY_STEP|[THINK_STEP_BY_STEP]"
  "BE_CONCISE|[BE_CONCISE]"
  "NO_TAG|"
)

# --- Prompts: All require genuine multi-step reasoning ---
# Chosen to require diverse reasoning strategies (proof, estimation, planning, analysis)
PROMPTS=(
  # 0: Formal proof (requires axiomatic reasoning)
  "Prove that there are infinitely many prime numbers."

  # 1: Probability puzzle (requires careful case analysis)
  "The Monty Hall problem: You're on a game show with 3 doors. Behind one door is a car; behind the others, goats. You pick door 1. The host, who knows what's behind the doors, opens door 3 to reveal a goat. He asks if you want to switch to door 2. Should you switch? Prove your answer mathematically."

  # 2: Algorithm design (requires reasoning about complexity)
  "Design an algorithm to find the kth smallest element in an unsorted array of n integers. Analyze its time and space complexity. Compare at least 3 different approaches."

  # 3: Physics estimation (requires layered approximation)
  "Estimate the total kinetic energy of all raindrops falling on Earth in a typical day. Show your reasoning chain and state your assumptions clearly."

  # 4: Logical puzzle (requires constraint propagation)
  "Five houses in a row are each painted a different color (red, blue, green, yellow, white). Each is occupied by a person of a different nationality (American, British, Swedish, Danish, Norwegian). Each person drinks a different beverage, smokes a different brand of cigarette, and keeps a different pet. Given: The Norwegian lives in the first house. The person in the green house drinks coffee. The British person lives in the red house. Who owns the fish? Solve step by step."

  # 5: Economic analysis (requires multi-factor reasoning)
  "If a country implements a universal basic income funded entirely by a value-added tax, what would be the expected effects on inflation, labor participation, and income inequality over 1-year, 5-year, and 20-year horizons? Reason through the transmission mechanisms."
)

NUM_PROMPTS=${#PROMPTS[@]}
NUM_TRIALS=3
NUM_CONDITIONS=${#CONDITIONS[@]}
NUM_MODELS=${#MODELS[@]}
TOTAL_CALLS=$((NUM_PROMPTS * NUM_TRIALS * NUM_CONDITIONS * NUM_MODELS))

echo "================================================================"
echo "z.ai Experiment 2: Reasoning-Effort Cue Impact"
echo "================================================================"
echo "Models:          ${NUM_MODELS} (${MODELS[*]})"
echo "Prompts:         ${NUM_PROMPTS}"
echo "Conditions:      ${NUM_CONDITIONS} (THINK_STEP_BY_STEP, BE_CONCISE, NO_TAG)"
echo "Trials:          ${NUM_TRIALS}"
echo "Max tokens:      4096"
echo "Total API calls: ${TOTAL_CALLS}"
echo "Start time:      $(date -Iseconds)"
echo "================================================================"
echo ""

call_api() {
  local model="$1"
  local prompt="$2"
  local condition_name="$3"
  local tag_prefix="$4"
  local trial="$5"
  local pidx="$6"

  local full_prompt="${tag_prefix}${prompt}"

  # Build JSON payload safely via Python
  local payload
  payload=$(python3 -c "
import json, sys
print(json.dumps({
    'model': '$model',
    'messages': [{'role': 'user', 'content': '''${full_prompt}'''}],
    'max_tokens': 4096,
    'temperature': 0.3
}))
")

  # Record start time
  local start_ms
  start_ms=$(date +%s%3N)

  # Make API call
  local response
  response=$(curl -s --max-time 120 "$BASE_URL" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $API_KEY" \
    -d "$payload" 2>&1)

  local end_ms
  end_ms=$(date +%s%3N)
  local latency_ms=$(( end_ms - start_ms ))

  # Parse response via Python
  python3 -c "
import json, sys

try:
    data = json.loads('''${response}''')
    msg = data['choices'][0]['message']
    usage = data.get('usage', {})
    details = usage.get('completion_tokens_details', {})
    
    content = msg.get('content', '') or ''
    reasoning = msg.get('reasoning_content', '') or ''
    
    result = {
        'model': '$model',
        'prompt_idx': $pidx,
        'condition': '$condition_name',
        'trial': $trial,
        'prompt': $(python3 -c "import json; print(json.dumps('$prompt'))"),
        'response': content,
        'reasoning_content': reasoning,
        'response_length': len(content),
        'reasoning_length': len(reasoning),
        'prompt_tokens': usage.get('prompt_tokens', 0),
        'completion_tokens': usage.get('completion_tokens', 0),
        'reasoning_tokens': details.get('reasoning_tokens', 0),
        'total_tokens': usage.get('total_tokens', 0),
        'latency_ms': $latency_ms,
        'has_reasoning': len(reasoning) > 0,
        'empty_response': len(content) == 0,
    }
except Exception as e:
    result = {
        'model': '$model',
        'prompt_idx': $pidx,
        'condition': '$condition_name',
        'trial': $trial,
        'error': str(e),
        'raw_response': '''${response}'''[:500],
        'response_length': 0,
        'reasoning_length': 0,
        'prompt_tokens': 0,
        'completion_tokens': 0,
        'reasoning_tokens': 0,
        'total_tokens': 0,
        'latency_ms': $latency_ms,
        'has_reasoning': False,
        'empty_response': True,
    }

print(json.dumps(result))
" >> "$RESULTS_FILE"
}

# --- Main experiment loop ---
count=0
for model in "${MODELS[@]}"; do
  echo "--- Model: $model ---"
  for pidx in $(seq 0 $((NUM_PROMPTS - 1))); do
    prompt="${PROMPTS[$pidx]}"
    for trial in $(seq 1 $NUM_TRIALS); do
      for cond_entry in "${CONDITIONS[@]}"; do
        IFS='|' read -r cond_name tag_prefix <<< "$cond_entry"
        
        count=$((count + 1))
        tag_display="${tag_prefix:-none}"
        echo -n "[$count/$TOTAL_CALLS] $model P$pidx T$trial $cond_name ($tag_display) ... "
        
        call_api "$model" "$prompt" "$cond_name" "$tag_prefix" "$trial" "$pidx"
        
        # Quick status from last line written
        tail -1 "$RESULTS_FILE" | python3 -c "
import json, sys
r = json.load(sys.stdin)
err = r.get('error', '')
if err:
    print(f'ERROR: {err[:60]}')
else:
    rl = r['response_length']
    rsl = r['reasoning_length']
    rt = r['reasoning_tokens']
    ct = r['completion_tokens']
    lat = r['latency_ms']
    print(f'resp={rl} reasoning_chars={rsl} rt={rt}/{ct} latency={lat}ms')
" 2>/dev/null || echo "parse error"
        
        # Rate limit: 0.5s between calls
        sleep 0.5
      done
    done
  done
done

echo ""
echo "================================================================"
echo "Experiment 2 complete."
echo "Total calls: $count"
echo "Results: $RESULTS_FILE"
echo "End time: $(date -Iseconds)"
echo "================================================================"

# --- Generate summary ---
python3 << 'PYEOF' >> "$SUMMARY_FILE"
import json
from collections import defaultdict

records = []
with open("/home/phoenix/.openclaw/workspace/experiments/zai-p3/experiment2_results.jsonl") as f:
    for line in f:
        records.append(json.loads(line))

errors = [r for r in records if 'error' in r]
valid = [r for r in records if 'error' not in r]

print(f"Total records: {len(records)}")
print(f"Errors: {len(errors)}")
print(f"Valid: {len(valid)}")
print()

# Summary by model × condition
print("=" * 80)
print("REASONING TOKEN USAGE (model × condition)")
print("=" * 80)
for model in ["glm-5.1", "glm-5-turbo"]:
    print(f"\n--- {model} ---")
    model_recs = [r for r in valid if r['model'] == model]
    if not model_recs:
        print("  No data")
        continue
    for cond in ["THINK_STEP_BY_STEP", "BE_CONCISE", "NO_TAG"]:
        recs = [r for r in model_recs if r['condition'] == cond]
        if not recs:
            print(f"  {cond:25s}: no data")
            continue
        avg_rt = sum(r['reasoning_tokens'] for r in recs) / len(recs)
        avg_rsl = sum(r['reasoning_length'] for r in recs) / len(recs)
        avg_resp = sum(r['response_length'] for r in recs) / len(recs)
        avg_ct = sum(r['completion_tokens'] for r in recs) / len(recs)
        empty = sum(1 for r in recs if r['empty_response'])
        avg_lat = sum(r['latency_ms'] for r in recs) / len(recs)
        print(f"  {cond:25s}: rt={avg_rt:7.0f}  rchars={avg_rsl:7.0f}  resp={avg_resp:5.0f}  comp={avg_ct:5.0f}  empty={empty}/{len(recs)}  lat={avg_lat:.0f}ms")

# Summary by prompt
print()
print("=" * 80)
print("REASONING BY PROMPT (glm-5.1 only)")
print("=" * 80)
glm51 = [r for r in valid if r['model'] == 'glm-5.1']
for pidx in sorted(set(r['prompt_idx'] for r in glm51)):
    recs = [r for r in glm51 if r['prompt_idx'] == pidx]
    prompt_preview = recs[0]['prompt'][:60]
    avg_rt = sum(r['reasoning_tokens'] for r in recs) / len(recs)
    avg_rsl = sum(r['reasoning_length'] for r in recs) / len(recs)
    avg_resp = sum(r['response_length'] for r in recs) / len(recs)
    print(f"  P{pidx}: {prompt_preview}...")
    print(f"       rt={avg_rt:.0f}  rchars={avg_rsl:.0f}  resp={avg_resp:.0f}")

# Key question: Does THINK_STEP_BY_STEP increase reasoning tokens for glm-5.1?
print()
print("=" * 80)
print("ANSWER: Does [THINK_STEP_BY_STEP] increase reasoning?")
print("=" * 80)
glm51 = [r for r in valid if r['model'] == 'glm-5.1']
think = [r for r in glm51 if r['condition'] == 'THINK_STEP_BY_STEP']
concise = [r for r in glm51 if r['condition'] == 'BE_CONCISE']
notag = [r for r in glm51 if r['condition'] == 'NO_TAG']

if think and concise:
    think_avg = sum(r['reasoning_tokens'] for r in think) / len(think)
    concise_avg = sum(r['reasoning_tokens'] for r in concise) / len(concise)
    notag_avg = sum(r['reasoning_tokens'] for r in notag) / len(notag) if notag else 0
    ratio = think_avg / concise_avg if concise_avg > 0 else float('inf')
    print(f"  THINK_STEP_BY_STEP avg rt: {think_avg:.0f}")
    print(f"  BE_CONCISE avg rt:         {concise_avg:.0f}")
    print(f"  NO_TAG avg rt:             {notag_avg:.0f}")
    print(f"  Ratio (THINK/CONCISE):     {ratio:.2f}x")
    if ratio > 1.3:
        print(f"  → YES: THINK_STEP_BY_STEP increases reasoning by {(ratio-1)*100:.0f}%")
    elif ratio < 0.77:
        print(f"  → REVERSE: BE_CONCISE actually increases reasoning?!")
    else:
        print(f"  → NO: Reasoning effort tags have minimal effect ({(ratio-1)*100:+.0f}%)")
else:
    print("  Insufficient data to answer")
PYEOF

echo ""
echo "Summary written to: $SUMMARY_FILE"
