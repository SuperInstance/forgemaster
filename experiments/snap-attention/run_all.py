#!/usr/bin/env python3
"""
Run all snap-attention simulators.
"""

import subprocess
import sys
import json
import time

simulators = [
    ('poker_sim.py', '🎰 Poker Attention Engine'),
    ('transfer_sim.py', '🔄 Cross-Domain Transfer'),
    ('rubik_sim.py', '🧊 Rubik\'s Cube Script Engine'),
    ('attention_budget_sim.py', '📡 Multi-Flavor Attention Budget'),
    ('learning_cycle_sim.py', '🧠 Delta-to-Script Learning Cycle'),
]

print("=" * 70)
print("  SNAP-AS-ATTENTION: Full Simulation Suite")
print("=" * 70)

results_summary = {}
total_start = time.time()

for script, label in simulators:
    print(f"\n{'─' * 70}")
    print(f"  Running: {label}")
    print(f"{'─' * 70}")
    
    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, script],
            capture_output=True,
            text=True,
            timeout=300,
        )
        elapsed = time.time() - start
        
        if result.returncode == 0:
            print(result.stdout)
            results_summary[label] = {'status': 'success', 'time': round(elapsed, 1)}
        else:
            print(f"  ❌ FAILED (exit {result.returncode})")
            print(f"  stderr: {result.stderr[:500]}")
            results_summary[label] = {'status': 'failed', 'error': result.stderr[:200]}
    except subprocess.TimeoutExpired:
        results_summary[label] = {'status': 'timeout'}
        print(f"  ⏱️ TIMEOUT")
    except Exception as e:
        results_summary[label] = {'status': 'error', 'error': str(e)}
        print(f"  ❌ ERROR: {e}")

total_elapsed = time.time() - total_start

print(f"\n{'=' * 70}")
print(f"  COMPLETE — {total_elapsed:.1f}s total")
print(f"{'=' * 70}")

for label, info in results_summary.items():
    status = '✅' if info['status'] == 'success' else '❌'
    t = f"{info['time']}s" if 'time' in info else info['status']
    print(f"  {status} {label}: {t}")

# Save master summary
with open('results_summary.json', 'w') as f:
    json.dump(results_summary, f, indent=2)
