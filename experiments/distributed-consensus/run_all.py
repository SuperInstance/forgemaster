#!/usr/bin/env python3
"""Run all distributed consensus experiments."""

import asyncio
import json
import sys
import os
import time

# Ensure we're in the right directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from experiment1_h1_detection import run_experiment as run_exp1
from experiment2_gossip_holonomy import run_experiment as run_exp2
from experiment3_crdt_precision import run_experiment as run_exp3


async def main():
    start = time.time()
    all_results = {}
    
    print("🔬 DISTRIBUTED CONSENSUS EXPERIMENTS")
    print("Testing constraint theory math on real distributed systems problems")
    print()
    
    # Experiment 1
    try:
        r1 = await run_exp1()
        all_results['experiment1'] = r1
    except Exception as e:
        print(f"\n❌ Experiment 1 failed: {e}")
        import traceback
        traceback.print_exc()
        all_results['experiment1'] = {'error': str(e)}
    
    print("\n\n")
    
    # Experiment 2
    try:
        r2 = await run_exp2()
        all_results['experiment2'] = r2
    except Exception as e:
        print(f"\n❌ Experiment 2 failed: {e}")
        import traceback
        traceback.print_exc()
        all_results['experiment2'] = {'error': str(e)}
    
    print("\n\n")
    
    # Experiment 3
    try:
        r3 = await run_exp3()
        all_results['experiment3'] = r3
    except Exception as e:
        print(f"\n❌ Experiment 3 failed: {e}")
        import traceback
        traceback.print_exc()
        all_results['experiment3'] = {'error': str(e)}
    
    elapsed = time.time() - start
    
    # Final summary
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    
    for name, result in all_results.items():
        if 'error' in result:
            print(f"  {name}: ❌ FAILED ({result['error']})")
        elif 'verdict' in result:
            print(f"  {name}: {result.get('verdict', 'UNKNOWN')}")
        else:
            print(f"  {name}: ✅ COMPLETED")
    
    print(f"\n  Total time: {elapsed:.1f}s")
    
    # Save combined results
    with open('results/all_experiments.json', 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"\n  All results saved to results/")


if __name__ == '__main__':
    asyncio.run(main())
