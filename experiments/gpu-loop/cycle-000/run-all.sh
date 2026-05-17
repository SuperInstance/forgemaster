#!/bin/bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
echo "=== GPU Loop Cycle 0 — Running All Experiments ==="
echo "Start: $(date)"

for exp in "$DIR"/exp-{1,2,3,4,5}.py; do
    echo ""
    echo "=== Running $(basename $exp) ==="
    python3 "$exp" 2>&1 || echo "FAILED: $exp"
    echo "=== Done $(basename $exp) ==="
done

echo ""
echo "All experiments complete: $(date)"
