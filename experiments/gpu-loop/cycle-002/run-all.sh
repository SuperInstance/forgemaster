#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "========================================"
echo "GPU Loop Cycle 002 — Running All Experiments"
echo "Model: Nemotron-30B"
echo "Date: $(date)"
echo "========================================"

for exp in exp-1.py exp-2.py exp-3.py exp-4.py exp-5.py; do
    echo ""
    echo ">>> Running $exp"
    echo ">>> Started: $(date)"
    python3 "$exp" 2>&1 | tee "${exp%.py}_output.log"
    echo ">>> Finished: $(date)"
done

echo ""
echo "========================================"
echo "All experiments complete."
echo "========================================"
