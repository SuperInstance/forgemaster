#!/usr/bin/env bash
# run_all.sh — Run ALL ground truth tests
# Usage: ./run_all.sh [--quick]
#   --quick: skip brute-force optimality tests (takes ~30s instead of ~10min)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo "FLUX-FOLD GROUND TRUTH TEST SUITE"
echo "Forgemaster ⚒️ — Grounding theoretical imagination in data"
echo "============================================================"
echo ""

QUICK_FLAG=""
if [[ "${1:-}" == "--quick" ]]; then
    QUICK_FLAG="--skip-bruteforce"
    echo "[QUICK MODE] Skipping brute-force optimality tests"
    echo ""
fi

# Test 1: Snap Correctness
echo "================================"
echo "TEST 1: Snap Correctness"
echo "================================"
python3 test_snap_correctness.py $QUICK_FLAG --output results_snap.json
echo ""

# Test 2: Consensus Calibration
echo "================================"
echo "TEST 2: Consensus Calibration"
echo "================================"
python3 test_consensus_calibration.py
echo ""

# Test 3: Eisenstein Comparison
echo "================================"
echo "TEST 3: Eisenstein Comparison"
echo "================================"
python3 test_eisenstein_comparison.py
echo ""

# Test 4: Babai Comparison
echo "================================"
echo "TEST 4: Babai & Algorithm Comparison"
echo "================================"
python3 test_babai_comparison.py
echo ""

# Compile results.json
echo "================================"
echo "Compiling results.json"
echo "================================"
python3 -c "
import json, sys, os

snap_data = {}
consensus_data = {}
eisenstein_data = {}
babai_data = {}

# Load individual results
for fname, dest in [
    ('results_snap.json', snap_data),
    ('results_consensus.json', consensus_data),
    ('results_eisenstein.json', eisenstein_data),
    ('results_babai.json', babai_data),
]:
    if os.path.exists(fname):
        with open(fname) as f:
            dest.update(json.load(f))
    else:
        print(f'WARNING: {fname} not found')

# Compile unified results
results = {
    'metadata': {
        'suite': 'flux-fold-ground-truth',
        'author': 'Forgemaster',
        'date': '2026-05-14',
        'status': 'ground-truth'
    },
    'snap_correctness': snap_data.get('tests', {}),
    'consensus_calibration': consensus_data.get('tests', {}),
    'eisenstein_comparison': eisenstein_data.get('tests', {}),
    'babai_comparison': babai_data.get('tests', {}),
}

with open('results.json', 'w') as f:
    json.dump(results, f, indent=2, default=str)

print('results.json written')
"
echo ""
echo "============================================================"
echo "ALL TESTS COMPLETE"
echo "============================================================"
echo "View results: results.json"
