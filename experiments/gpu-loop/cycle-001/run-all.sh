#!/bin/bash
cd /home/phoenix/.openclaw/workspace/experiments/gpu-loop/cycle-001
echo "=== CYCLE 001 — Seed-2.0-mini ==="
echo "Starting: $(date)"
echo ""

echo "--- EXP-1: Asymmetric Coupling ---"
python3 exp-1.py 2>&1
echo ""

echo "--- EXP-2: Sub-2-bit Regime ---"
python3 exp-2.py 2>&1
echo ""

echo "--- EXP-3: System Size Scaling ---"
python3 exp-3.py 2>&1
echo ""

echo "--- EXP-4: Architecture × Precision ---"
python3 exp-4.py 2>&1
echo ""

echo "--- EXP-5: C(precision) Functional Form ---"
python3 exp-5.py 2>&1
echo ""

echo "=== ALL EXPERIMENTS COMPLETE ==="
echo "Finished: $(date)"
