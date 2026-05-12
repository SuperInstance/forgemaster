#!/usr/bin/env python3
"""Validate snapkit Python implementation against the test corpus."""

import json
import os
import sys

from snap_common import eisenstein_snap, snap_error


def main():
    corpus_path = "corpus/snap_corpus.json"
    if not os.path.exists(corpus_path):
        print(f"ERROR: {corpus_path} not found. Run generate_corpus.py first.")
        sys.exit(1)
    
    with open(corpus_path) as f:
        corpus = json.load(f)
    
    passed = 0
    failed = 0
    errors = []
    
    for case in corpus:
        x, y = case["input"]["x"], case["input"]["y"]
        exp_a, exp_b = case["expected"]["a"], case["expected"]["b"]
        
        a, b = eisenstein_snap(x, y)
        err = snap_error(x, y, a, b)
        
        ok = True
        if a != exp_a:
            errors.append(f"Case {case['id']}: a={a}, expected={exp_a}")
            ok = False
        if b != exp_b:
            errors.append(f"Case {case['id']}: b={b}, expected={exp_b}")
            ok = False
        if err > case["snap_error_max"] + 1e-10:
            errors.append(f"Case {case['id']}: snap_error={err} > max={case['snap_error_max']}")
            ok = False
        
        if ok:
            passed += 1
        else:
            failed += 1
    
    print(f"Results: {passed}/{len(corpus)} passed, {failed} failed")
    
    if errors:
        print("\nErrors:")
        for e in errors[:20]:
            print(f"  {e}")
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more")
        sys.exit(1)
    else:
        print("All cases passed ✓")


if __name__ == "__main__":
    main()
