#!/usr/bin/env python3
"""
Run all snap-attention simulators with rich output.

Usage:
    python run_all.py              # run all with defaults
    python run_all.py --quick      # fast mode (reduced counts)
    python run_all.py --verbose    # show progress bars
    python run_all.py --html       # generate HTML reports for each
    python run_all.py --csv        # generate CSV exports for each
"""

import subprocess
import sys
import json
import time
import argparse

simulators = [
    ('poker_sim.py', '🎰 Poker Attention Engine', 'poker'),
    ('transfer_sim.py', '🔄 Cross-Domain Transfer', 'transfer'),
    ('rubik_sim.py', '🧊 Rubik\'s Cube Script Engine', 'rubik'),
    ('attention_budget_sim.py', '📡 Multi-Flavor Attention Budget', 'budget'),
    ('learning_cycle_sim.py', '🧠 Delta-to-Script Learning Cycle', 'learning'),
]

def run_all(quick=False, verbose=False, html=False, csv=False):
    print("=" * 70)
    print("  SNAP-AS-ATTENTION: Full Simulation Suite")
    print("=" * 70)
    
    results_summary = {}
    total_start = time.time()
    
    for script, label, tag in simulators:
        print(f"\n{'─' * 70}")
        print(f"  Running: {label}")
        print(f"{'─' * 70}")
        
        cmd = [sys.executable, script]
        if quick: cmd.append('--quick')
        if verbose: cmd.append('--verbose')
        if html: cmd.extend(['--html', f'report_{tag}.html'])
        if csv: cmd.extend(['--csv', f'results_{tag}.csv'])
        
        start = time.time()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            elapsed = time.time() - start
            
            if result.returncode == 0:
                # Print the simulator's own output (rich formatted)
                print(result.stdout)
                results_summary[label] = {'status': 'success', 'time': round(elapsed, 1)}
            else:
                print(f"  ❌ FAILED (exit {result.returncode})")
                if result.stderr: print(f"  stderr: {result.stderr[:500]}")
                results_summary[label] = {'status': 'failed', 'error': result.stderr[:200] if result.stderr else 'unknown'}
        except subprocess.TimeoutExpired:
            results_summary[label] = {'status': 'timeout'}
            print(f"  ⏱️ TIMEOUT")
        except Exception as e:
            results_summary[label] = {'status': 'error', 'error': str(e)}
            print(f"  ❌ ERROR: {e}")
    
    total_elapsed = time.time() - total_start
    
    # Summary
    print(f"\n{'═' * 70}")
    print(f"  SUITE COMPLETE — {total_elapsed:.1f}s total")
    print(f"{'═' * 70}")
    
    for label, info in results_summary.items():
        status = '✅' if info['status'] == 'success' else '❌'
        t = f"{info['time']}s" if 'time' in info else info['status']
        print(f"  {status} {label}: {t}")
    
    # Save master summary
    with open('results_summary.json', 'w') as f:
        json.dump(results_summary, f, indent=2)
    
    print(f"\n✅ Summary → results_summary.json")

def parse_args():
    parser = argparse.ArgumentParser(description="Run all snap-attention simulators")
    parser.add_argument('--quick', action='store_true', help='Fast mode (reduced counts)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show progress bars')
    parser.add_argument('--html', action='store_true', help='Generate HTML reports')
    parser.add_argument('--csv', action='store_true', help='Generate CSV exports')
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    run_all(quick=args.quick, verbose=args.verbose, html=args.html, csv=args.csv)
