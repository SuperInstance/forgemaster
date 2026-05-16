"""
STUDY 53 v2: GL(9) vs SO(3) — Intent-Correlated Transforms

The hypothesis: when transforms encode intent disagreement, GL(9) preserves
the holonomy-alignment correlation that SO(3) destroys by projecting away
6 of 9 CI facet dimensions.

Key design: each agent's transform is derived FROM its intent relative to
a shared reference. This creates a natural correlation between holonomy
deviation (transform disagreement) and alignment (intent disagreement).
"""
import json
import math
import random
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gl9_consensus import (
    GL9Matrix, GL9Agent, GL9HolonomyConsensus, IntentVector, pearson_correlation
)

# ─── SO(3) helpers ──────────────────────────────────────────────────

def mat3_mul(A, B):
    R = [[0]*3 for _ in range(3)]
    for i in range(3):
        for j in range(3):
            for k in range(3):
                R[i][j] += A[i][k] * B[k][j]
    return R

def mat3_identity():
    return [[1,0,0],[0,1,0],[0,0,1]]

def mat3_deviation(M):
    total = 0.0
    for i in range(3):
        for j in range(3):
            expected = 1.0 if i==j else 0.0
            total += (M[i][j] - expected)**2
    return math.sqrt(total)

def cosine_sim(a, b):
    dot = sum(x*y for x,y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(x*x for x in b))
    if na < 1e-12 or nb < 1e-12: return 0.0
    return dot / (na * nb)

def project_3d(v9):
    return v9[:3]


# ─── Intent-correlated transform generation ─────────────────────────

def intent_to_gl9_transform(intent, reference, noise_scale=0.1):
    """
    Build a GL(9) transform from intent relative to reference.
    The transform rotates dimensions where intent differs most from reference.
    This creates a natural coupling: intent divergence → transform deviation.
    """
    m = GL9Matrix.identity()
    diff = [intent[i] - reference[i] for i in range(9)]
    
    for a in range(9):
        for b in range(a+1, 9):
            # Angle proportional to the cross-difference
            angle = diff[a] * diff[b] * 3.0  # scale up for visibility
            if abs(angle) > 1e-10:
                rot = GL9Matrix.plane_rotation(a, b, angle)
                m = rot.multiply(m)
    
    # Add small noise for realism
    for i in range(9):
        m.data[i*9+i] += random.gauss(0, noise_scale * 0.1)
    
    return m

def gl9_to_so3(gl9):
    """Extract 3×3 from GL(9) top-left, Gram-Schmidt to rotation."""
    sub = [[gl9.data[i*9+j] for j in range(3)] for i in range(3)]
    # GS
    cols = [[sub[r][c] for r in range(3)] for c in range(3)]
    n0 = math.sqrt(sum(x*x for x in cols[0]))
    if n0 < 1e-12: return mat3_identity()
    u0 = [x/n0 for x in cols[0]]
    dot01 = sum(a*b for a,b in zip(u0, cols[1]))
    v1 = [cols[1][i] - dot01*u0[i] for i in range(3)]
    n1 = math.sqrt(sum(x*x for x in v1))
    if n1 < 1e-12: return mat3_identity()
    u1 = [x/n1 for x in v1]
    u2 = [
        u0[1]*u1[2] - u0[2]*u1[1],
        u0[2]*u1[0] - u0[0]*u1[2],
        u0[0]*u1[1] - u0[1]*u1[0],
    ]
    return [[u0[0],u1[0],u2[0]], [u0[1],u1[1],u2[1]], [u0[2],u1[2],u2[2]]]


# ─── Network generation ─────────────────────────────────────────────

def generate_correlated_network(num_agents, rng, fault_frac=0.0):
    """Generate agents where transforms encode intent disagreement."""
    ids = list(range(num_agents))
    
    # Shared reference intent
    ref = [rng.gauss(0, 1) for _ in range(9)]
    rn = math.sqrt(sum(x*x for x in ref))
    ref = [x/rn for x in ref]
    
    intents_9d = {}
    transforms_gl9 = {}
    transforms_so3 = {}
    
    faulty_ids = set()
    if fault_frac > 0:
        nf = max(1, int(num_agents * fault_frac))
        faulty_ids = set(rng.sample(ids, nf))
    
    for aid in ids:
        # Intent: reference + noise (more noise = more disagreement)
        noise_level = 0.5 if aid not in faulty_ids else 2.0
        intent = [ref[i] + rng.gauss(0, noise_level) for i in range(9)]
        n = math.sqrt(sum(x*x for x in intent))
        intent = [x/n for x in intent]
        intents_9d[aid] = intent
        
        # Transform derived from intent
        gl9 = intent_to_gl9_transform(intent, ref, noise_scale=0.05)
        if aid in faulty_ids:
            # Fault: extra large transform
            for _ in range(3):
                a, b = rng.sample(range(9), 2)
                rot = GL9Matrix.plane_rotation(a, b, rng.gauss(0, 1.5))
                gl9 = rot.multiply(gl9)
        
        transforms_gl9[aid] = gl9
        transforms_so3[aid] = gl9_to_so3(gl9)
    
    agents = {}
    for aid in ids:
        agents[aid] = GL9Agent(
            id=aid,
            intent=IntentVector(intents_9d[aid]),
            transform=transforms_gl9[aid],
            neighbors=[ids[(aid-1) % num_agents], ids[(aid+1) % num_agents]],
        )
    
    return agents, transforms_so3, intents_9d, ids, faulty_ids


# ─── Phase A: SO(3) correlation ─────────────────────────────────────

def phase_so3(n_trials, agent_range, rng):
    devs, aligns = [], []
    for _ in range(n_trials):
        na = rng.randint(*agent_range)
        agents, so3s, intents, ids, _ = generate_correlated_network(na, rng)
        
        # SO(3) ring holonomy
        prod = mat3_identity()
        for aid in ids:
            prod = mat3_mul(so3s[aid], prod)
        devs.append(mat3_deviation(prod))
        
        # 3D alignment
        i3d = {aid: project_3d(intents[aid]) for aid in ids}
        sim, cnt = 0.0, 0
        for i in range(len(ids)):
            for j in range(i+1, len(ids)):
                sim += cosine_sim(i3d[ids[i]], i3d[ids[j]])
                cnt += 1
        aligns.append(sim/cnt if cnt else 1.0)
    
    return {"r": pearson_correlation(devs, aligns), "n": n_trials}


# ─── Phase B: GL(9) correlation ─────────────────────────────────────

def phase_gl9(n_trials, agent_range, rng):
    devs, aligns = [], []
    for _ in range(n_trials):
        na = rng.randint(*agent_range)
        agents, so3s, intents, ids, _ = generate_correlated_network(na, rng)
        
        cons = GL9HolonomyConsensus(tolerance=1.5)
        for a in agents.values():
            cons.add_agent(a)
        res = cons.check_consensus()
        devs.append(res.deviation)
        aligns.append(res.alignment)
    
    return {"r": pearson_correlation(devs, aligns), "n": n_trials}


# ─── Phase C: Scaling ───────────────────────────────────────────────

def phase_scaling(sizes, trials, rng):
    results = []
    for sz in sizes:
        so3 = phase_so3(trials, (sz, sz), rng)
        gl9 = phase_gl9(trials, (sz, sz), rng)
        results.append({"size": sz, "so3_r": so3["r"], "gl9_r": gl9["r"]})
        print(f"  Size {sz:2d}: SO(3) r={so3['r']:+.4f}  GL(9) r={gl9['r']:+.4f}")
    return results


# ─── Phase D: Fault detection ───────────────────────────────────────

def phase_fault(n_trials, agent_range, rng, fault_frac=0.2):
    gl9_hit = 0
    gl9_fp = 0
    gl9_loc_correct = 0
    gl9_total_faulty = 0
    so3_hit = 0
    so3_fp = 0
    n_with_faults = 0
    
    for _ in range(n_trials):
        na = rng.randint(*agent_range)
        agents, so3s, intents, ids, faulty = generate_correlated_network(
            na, rng, fault_frac=fault_frac)
        
        if faulty:
            n_with_faults += 1
        gl9_total_faulty += len(faulty)
        
        # GL(9)
        cons = GL9HolonomyConsensus(tolerance=1.5)
        for a in agents.values():
            cons.add_agent(a)
        res = cons.check_consensus()
        
        found = set(res.faulty_agents)
        if faulty:
            if found & faulty:
                gl9_hit += 1
            gl9_loc_correct += len(found & faulty)
        gl9_fp += len(found - faulty)
        
        # SO(3)
        prod = mat3_identity()
        for aid in ids:
            prod = mat3_mul(so3s[aid], prod)
        so3_dev = mat3_deviation(prod)
        so3_thresh = 0.5  # scaled
        if so3_dev > so3_thresh:
            if faulty:
                so3_hit += 1
            else:
                so3_fp += 1
    
    return {
        "gl9_detect_rate": gl9_hit / n_with_faults if n_with_faults else 0,
        "gl9_localization_rate": gl9_loc_correct / gl9_total_faulty if gl9_total_faulty else 0,
        "gl9_false_positives": gl9_fp,
        "so3_detect_rate": so3_hit / n_with_faults if n_with_faults else 0,
        "so3_false_positives": so3_fp,
    }


# ─── Main ───────────────────────────────────────────────────────────

def main():
    SEED = 42
    print("=" * 60)
    print("STUDY 53 v2: GL(9) vs SO(3) — Intent-Correlated Transforms")
    print("=" * 60)
    
    results = {}
    
    # Phase A
    print("\n--- Phase A: SO(3) correlation ---")
    so3 = phase_so3(200, (5, 10), random.Random(SEED))
    print(f"  SO(3) r = {so3['r']:+.6f}")
    results["phase_a"] = so3
    
    # Phase B
    print("\n--- Phase B: GL(9) correlation ---")
    gl9 = phase_gl9(200, (5, 10), random.Random(SEED))
    print(f"  GL(9) r = {gl9['r']:+.6f}")
    results["phase_b"] = gl9
    
    # Phase C
    print("\n--- Phase C: Scaling ---")
    scaling = phase_scaling([3, 5, 7, 10, 15, 20], 50, random.Random(SEED))
    results["phase_c"] = scaling
    
    # Phase D
    print("\n--- Phase D: Fault detection ---")
    fault = phase_fault(200, (5, 15), random.Random(SEED))
    print(f"  GL(9) detect: {fault['gl9_detect_rate']:.1%}, "
          f"loc: {fault['gl9_localization_rate']:.1%}, "
          f"FP: {fault['gl9_false_positives']}")
    print(f"  SO(3) detect: {fault['so3_detect_rate']:.1%}, "
          f"FP: {fault['so3_false_positives']}")
    results["phase_d"] = fault
    
    # Summary
    delta = gl9['r'] - so3['r']
    print(f"\n{'='*60}")
    print(f"SO(3) r = {so3['r']:+.6f}")
    print(f"GL(9) r = {gl9['r']:+.6f}")
    print(f"Δr      = {delta:+.6f}")
    
    # Effect size interpretation
    if abs(delta) < 0.05:
        verdict = "NEGLIGIBLE — no significant difference between SO(3) and GL(9)"
    elif delta > 0.1:
        verdict = "STRONG — GL(9) significantly outperforms SO(3)"
    elif delta > 0:
        verdict = "MARGINAL — GL(9) slightly outperforms SO(3)"
    else:
        verdict = "REVERSED — SO(3) outperforms GL(9) (unexpected)"
    print(f"Verdict: {verdict}")
    
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "study53_gl9_results.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Saved: {out}")
    
    return results, so3, gl9, scaling, fault, verdict

if __name__ == "__main__":
    main()
