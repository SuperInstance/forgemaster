#!/usr/bin/env python3
"""Run all Platonic Snap experiments."""
import subprocess
import sys
import time

experiments = [
    ("Experiment 1: 3D Snap Topology", "experiment1_snap_topology.py"),
    ("Experiment 2: Tensor Consistency", "experiment2_tensor.py"),
    ("Experiment 3: Constraint H¹ by ADE", "experiment3_h1.py"),
    ("Experiment 4: Eisenstein × φ Incompatibility", "experiment4_incompatibility.py"),
]

results = {}
for name, script in experiments:
    print(f"\n{'='*60}")
    print(f"Running: {name}")
    print(f"{'='*60}")
    t0 = time.time()
    proc = subprocess.run(
        [sys.executable, script],
        capture_output=True,
        text=True,
        cwd="/home/phoenix/.openclaw/workspace/experiments/platonic-snap",
    )
    elapsed = time.time() - t0
    print(proc.stdout)
    if proc.returncode != 0:
        print(f"ERROR: {proc.stderr}")
        results[name] = f"FAILED ({elapsed:.1f}s)"
    else:
        results[name] = f"OK ({elapsed:.1f}s)"

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
for name, status in results.items():
    print(f"  {name}: {status}")
