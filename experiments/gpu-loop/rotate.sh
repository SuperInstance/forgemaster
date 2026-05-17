#!/bin/bash
# GPU Constraint Experiment Rotation Engine
# Models cycle: GLM-5.1 → Seed-2.0-mini → Nemotron-3-Nano-30B → repeat
# Each model: 10 min experiments → 5 min analyze+craft → next model starts

set -euo pipefail

BASE="/home/phoenix/.openclaw/workspace/experiments/gpu-loop"
CYCLE=0
MODELS=("glm-5.1" "seed-2.0-mini" "nemotron-30b")
MODEL_IDX=0

# Load state if exists
if [ -f "$BASE/state.json" ]; then
    CYCLE=$(python3 -c "import json; print(json.load(open('$BASE/state.json'))['cycle'])")
    MODEL_IDX=$(python3 -c "import json; print(json.load(open('$BASE/state.json'))['model_idx'])")
fi

mkdir -p "$BASE/cycle-$(printf '%03d' $CYCLE)"

echo "=== GPU Loop Starting ==="
echo "Cycle: $CYCLE | Model: ${MODELS[$MODEL_IDX]}"

# Save state
python3 -c "
import json
json.dump({'cycle': $CYCLE, 'model_idx': $MODEL_IDX}, open('$BASE/state.json', 'w'))
"

echo "Cycle $CYCLE ready for model ${MODELS[$MODEL_IDX]}"
echo "Next: spawn analyzer with this model to run experiments"
