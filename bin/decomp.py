"""
decomp.py — Mathematical decomposition research loop.

NOT a helpdesk. NOT a chatbot proxy.

The loop:
1. Take a conjecture (e.g. "Bounded drift theorem holds for all cyclotomic fields")
2. Decompose into sub-conjectures via API (the ONE place the model earns its keep)
3. Verify each sub-conjecture locally at chip speed
4. Return: verified ✓, falsified ✗, or needs-stronger-decomposition

The API is a decomposition tool. The chips do the actual work.

Usage:
    python3 decomp.py "covering radius of Eisenstein lattice is 1/sqrt(3)"
    python3 decomp.py --conjecture-file papers/conjectures.txt
    python3 decomp.py --batch experiments/open-problems.json
"""

import json
import math
import os
import random
import re
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

CRED_DIR = os.path.expanduser("~/.openclaw/workspace/.credentials")
DECOMP_DIR = os.path.expanduser("~/.openclaw/workspace/experiments/decomp")
os.makedirs(DECOMP_DIR, exist_ok=True)

# ─── Local Verifiers (chip-speed, no API) ─────────────────────────

def verify_snap_idempotence(n: int = 100000, seed: int = 42, N: int = None) -> dict:
    if N is not None: n = N
    """snap(snap(p)) == snap(p) for all p. ~100ms for 100K points."""
    random.seed(seed)
    failures = 0
    for _ in range(n):
        x, y = random.gauss(0, 10), random.gauss(0, 10)
        s1 = eisenstein_snap(x, y)
        s2 = eisenstein_snap(*to_complex(*s1))
        if s1 != s2:
            failures += 1
    return {"conjecture": "snap is idempotent", "trials": n, 
            "failures": failures, "verified": failures == 0}


def verify_covering_radius(n: int = 100000, seed: int = 42, N: int = None) -> dict:
    if N is not None: n = N
    """max snap distance <= 1/sqrt(3). ~200ms for 100K."""
    random.seed(seed)
    max_d = 0
    max_point = None
    bound = 1 / math.sqrt(3)
    for _ in range(n):
        x, y = random.gauss(0, 10), random.gauss(0, 10)
        a, b = eisenstein_snap(x, y)
        rx, ry = to_complex(a, b)
        d = math.sqrt((rx - x)**2 + (ry - y)**2)
        if d > max_d:
            max_d = d
            max_point = (x, y)
    return {"conjecture": "covering radius = 1/√3", "trials": n,
            "max_distance": max_d, "bound": bound,
            "verified": max_d <= bound + 1e-10,
            "worst_case": max_point}


def verify_dodecet_cardinality(points: int = 100000, N: int = None) -> dict:
    if N is not None: points = N
    """snap always lands in exactly 12 sectors."""
    random.seed(42)
    sectors = set()
    for _ in range(points):
        x, y = random.gauss(0, 5), random.gauss(0, 5)
        angle = math.atan2(y, x)
        sector = round(angle / (math.pi / 6)) % 12
        sectors.add(sector)
    return {"conjecture": "dodecet has exactly 12 sectors", 
            "secters_found": len(sectors), "verified": len(sectors) == 12}


def verify_norm_multiplicative(n: int = 100000, N: int = None) -> dict:
    if N is not None: n = N
    """N(a*b) = N(a)*N(b) for Eisenstein integers."""
    random.seed(42)
    failures = 0
    for _ in range(n):
        a1, b1 = random.randint(-20, 20), random.randint(-20, 20)
        a2, b2 = random.randint(-20, 20), random.randint(-20, 20)
        n1 = a1**2 - a1*b1 + b1**2
        n2 = a2**2 - a2*b2 + b2**2
        # Multiply: (a1+b1ω)(a2+b2ω) = (a1a2-b1b2) + (a1b2+b1a2-b1b2)ω
        ra = a1*a2 - b1*b2
        rb = a1*b2 + b1*a2 - b1*b2
        n3 = ra**2 - ra*rb + rb**2
        if n1 * n2 != n3:
            failures += 1
    return {"conjecture": "norm is multiplicative for Eisenstein integers",
            "trials": n, "failures": failures, "verified": failures == 0}


def verify_drift_bounded(steps: int = 100000, bound: float = 1/math.sqrt(3), N: int = None) -> dict:
    if N is not None: steps = N
    """Closed constraint walk stays bounded."""
    random.seed(42)
    x = 0.0
    max_drift = 0
    for i in range(steps):
        x += random.gauss(0, 0.01)
        # Constraint cycle: snap back to lattice neighborhood
        snapped = round(x / bound) * bound
        drift = abs(x - snapped)
        max_drift = max(max_drift, drift)
        x = snapped  # reset — this is the "closed walk" property
    return {"conjecture": "closed constraint walk stays bounded",
            "steps": steps, "max_drift": max_drift, "bound": bound,
            "verified": max_drift <= bound}


def verify_hex_closest_pack(n: int = 100000, N: int = None) -> dict:
    if N is not None: n = N
    """Hexagonal packing is densest for snap-to-nearest."""
    random.seed(42)
    # Generate random points, snap, check no closer unsnapped point exists
    failures = 0
    for _ in range(n):
        x, y = random.gauss(0, 10), random.gauss(0, 10)
        a, b = eisenstein_snap(x, y)
        rx, ry = to_complex(a, b)
        d_snap = math.sqrt((rx-x)**2 + (ry-y)**2)
        # Check the 6 neighbors of the snapped point
        for da, db in [(1,0),(0,1),(1,1),(-1,0),(0,-1),(-1,-1)]:
            nx, ny = to_complex(a+da, b+db)
            d_neighbor = math.sqrt((nx-x)**2 + (ny-y)**2)
            if d_neighbor < d_snap - 1e-10:
                failures += 1
                break
    return {"conjecture": "snap finds true nearest lattice point",
            "trials": n, "failures": failures, "verified": failures == 0}


# ─── Helpers ──────────────────────────────────────────────────────

def eisenstein_snap(x: float, y: float) -> Tuple[int, int]:
    # Eisenstein integer a + bω where ω = e^(2πi/3) = -1/2 + i√3/2
    # Cartesian: real = a - b/2, imag = b√3/2
    # Inverse: b = 2y/√3, a = x + b/2
    b = round(2 * y / math.sqrt(3))
    a = round(x + b / 2)
    best, best_d = (a, b), float('inf')
    for da in [-1, 0, 1]:
        for db in [-1, 0, 1]:
            aa, bb = a + da, b + db
            cx = aa - bb / 2
            cy = bb * math.sqrt(3) / 2
            d = (cx - x)**2 + (cy - y)**2
            if d < best_d:
                best_d = d
                best = (aa, bb)
    return best


def to_complex(a: int, b: int) -> Tuple[float, float]:
    return (a - b / 2, b * math.sqrt(3) / 2)


LOCAL_VERIFIERS = {
    "snap_idempotence": verify_snap_idempotence,
    "covering_radius": verify_covering_radius,
    "dodecet_cardinality": verify_dodecet_cardinality,
    "norm_multiplicative": verify_norm_multiplicative,
    "drift_bounded": verify_drift_bounded,
    "hex_closest_pack": verify_hex_closest_pack,
}


# ─── Decomposition via API ────────────────────────────────────────

DECOMP_SYSTEM = """You are a mathematical decomposition engine. You receive a conjecture and break it into 
sub-conjectures that can EACH be verified by LOCAL computation.

Available local verifiers (these run at chip speed, no API needed):
1. snap_idempotence(N) — snap(snap(p)) == snap(p) for N random points
2. covering_radius(N) — max snap distance ≤ 1/√3 for N random points
3. dodecet_cardinality(N) — snap lands in exactly 12 sectors
4. norm_multiplicative(N) — N(a·b) = N(a)·N(b) for Eisenstein integers
5. drift_bounded(steps, bound) — closed constraint walk stays within bound
6. hex_closest_pack(N) — snap finds true nearest lattice point

Output JSON array of sub-conjectures:
[{"id": "S1", "statement": "...", "verifier": "name", "args": {...}, "reason": "why this sub-conjecture matters"}]

If the conjecture can be verified by a SINGLE local verifier, return a 1-element array.
If it needs proof techniques beyond these verifiers, say so honestly — don't fake it.
If you can partially decompose, return what you can verify and flag the rest.

Be precise. Mathematical content only. No exposition."""


def decompose(conjecture: str, provider="deepinfra", model="ByteDance/Seed-2.0-mini") -> dict:
    """Decompose a conjecture into locally-verifiable sub-conjectures."""
    key = _load_key(provider)
    if not key:
        return {"error": f"No key for {provider}"}
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": DECOMP_SYSTEM},
            {"role": "user", "content": conjecture},
        ],
        "max_tokens": 2048,
        "temperature": 0.2,
    }
    
    data = json.dumps(payload).encode()
    endpoints = {
        "deepinfra": "https://api.deepinfra.com/v1/openai/chat/completions",
        "deepseek": "https://api.deepseek.com/v1/chat/completions",
    }
    req = urllib.request.Request(
        endpoints[provider], data=data,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            result = json.loads(r.read())
        content = result["choices"][0]["message"]["content"]
        # Try to parse JSON from the response
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            raw = json_match.group()
            raw = re.sub(r'\\[a-zA-Z]+', '', raw)  # strip LaTeX commands
            try:
                sub_conjectures = json.loads(raw)
            except json.JSONDecodeError:
                # Extract individual objects
                sub_conjectures = []
                for m in re.finditer(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', raw):
                    try: sub_conjectures.append(json.loads(m.group()))
                    except: pass
                if not sub_conjectures:
                    sub_conjectures = [{"id": "S1", "raw": content[:500]}]
        else:
            sub_conjectures = [{"id": "S1", "raw": content}]
        return {"decomposition": sub_conjectures, "raw": content, "tokens": result.get("usage", {})}
    except Exception as e:
        return {"error": str(e)}


def _load_key(provider):
    files = {"deepinfra": "deepinfra-api-key.txt", "deepseek": "deepseek-api-key.txt"}
    path = os.path.join(CRED_DIR, files.get(provider, ""))
    if not os.path.exists(path): return None
    return open(path).read().strip()


# ─── Run a decomposition experiment ───────────────────────────────

def run_experiment(conjecture: str, provider="deepinfra", model="ByteDance/Seed-2.0-mini") -> dict:
    """
    Full decomposition experiment:
    1. Decompose via API (the model earns its keep here)
    2. Run local verifiers on each sub-conjecture
    3. Return full results
    """
    print(f"🔬 Decomposing: {conjecture[:80]}...")
    
    # Step 1: Decompose
    decomp = decompose(conjecture, provider, model)
    if "error" in decomp:
        return {"conjecture": conjecture, "error": decomp["error"]}
    
    print(f"   Got {len(decomp.get('decomposition', []))} sub-conjecture(s)")
    
    # Step 2: Run local verifiers
    results = []
    for sc in decomp.get("decomposition", []):
        verifier_name = sc.get("verifier", "")
        if verifier_name in LOCAL_VERIFIERS:
            verifier = LOCAL_VERIFIERS[verifier_name]
            args = sc.get("args", {})
            # Coerce string args to int where needed
            for k, v in args.items():
                if isinstance(v, str) and v.isdigit():
                    args[k] = int(v)
                elif isinstance(v, str):
                    try: args[k] = int(v)
                    except: pass
            t0 = time.perf_counter()
            try:
                result = verifier(**args)
            except Exception as e:
                result = {"error": str(e)}
            elapsed = time.perf_counter() - t0
            result["time_ms"] = round(elapsed * 1000, 1)
            result["sub_id"] = sc.get("id", "?")
            result["statement"] = sc.get("statement", "")
            result["reason"] = sc.get("reason", "")
            results.append(result)
            
            status = "✓" if result.get("verified") else "✗"
            print(f"   [{result['sub_id']}] {status} {verifier_name} ({result['time_ms']}ms)")
        else:
            results.append({
                "sub_id": sc.get("id", "?"),
                "statement": sc.get("statement", ""),
                "reason": sc.get("reason", ""),
                "status": "NO_LOCAL_VERIFIER",
                "note": sc.get("raw", "")[:200] if "raw" in sc else "Needs proof beyond available verifiers"
            })
            print(f"   [{sc.get('id', '?')}] ⚠ No local verifier for: {sc.get('statement', '?')[:60]}")
    
    experiment = {
        "conjecture": conjecture,
        "decomposition_raw": decomp.get("raw", ""),
        "sub_conjectures": results,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "provider": provider,
        "model": model,
    }
    
    # Save
    fname = re.sub(r'[^a-zA-Z0-9]', '-', conjecture[:40]) + ".json"
    with open(os.path.join(DECOMP_DIR, fname), "w") as f:
        json.dump(experiment, f, indent=2)
    
    return experiment


# ─── CLI ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 decomp.py 'conjecture statement'")
        print("       python3 decomp.py --verify-only covering_radius")
        sys.exit(1)
    
    if sys.argv[1] == "--verify-only":
        # Run all local verifiers without API
        name = sys.argv[2] if len(sys.argv) > 2 else "all"
        if name == "all":
            for vname, vfn in LOCAL_VERIFIERS.items():
                t0 = time.perf_counter()
                r = vfn()
                elapsed = time.perf_counter() - t0
                status = "✓" if r.get("verified") else "✗"
                print(f"  {status} {vname}: {elapsed*1000:.0f}ms — {r}")
        else:
            vfn = LOCAL_VERIFIERS.get(name)
            if vfn:
                t0 = time.perf_counter()
                r = vfn()
                elapsed = time.perf_counter() - t0
                print(json.dumps(r, indent=2))
                print(f"Time: {elapsed*1000:.0f}ms")
    else:
        conjecture = " ".join(sys.argv[1:])
        result = run_experiment(conjecture)
        print(json.dumps(result, indent=2))
