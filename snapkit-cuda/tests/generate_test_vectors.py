#!/usr/bin/env python3
"""
generate_test_vectors.py — Generate test vectors for SnapKit CUDA validation.

Generates:
- 1000 Eisenstein (A₂) test vectors
- 500 A₃ (tetrahedral) test vectors  
- 200 D₄ (triality) test vectors
- 100 E₈ (exceptional) test vectors
- 50 edge cases

Output: JSON file with input/output pairs for cross-validation.
"""

import json
import math
import random
import os

# ======================================================================
# Constants (must match CUDA code)
# ======================================================================
SQRT3 = 1.7320508075688772
HALF_SQRT3 = 0.8660254037844386
INV_SQRT3 = 0.5773502691896258
TOLERANCE = 0.1

# ======================================================================
# Snap Functions (reference implementations)
# ======================================================================

def eisenstein_snap(x, y):
    """Snap (x,y) to Eisenstein lattice. Returns (a, b, delta)."""
    b = round(2.0 * y / SQRT3)
    a = round(x + b * 0.5)
    snap_x = a - b * 0.5
    snap_y = b * HALF_SQRT3
    delta = math.hypot(x - snap_x, y - snap_y)
    return a, b, delta, snap_x, snap_y


def snap_binary_1d(value):
    """A₁ binary snap."""
    snapped = 1.0 if value >= 0.0 else -1.0
    delta = abs(value - snapped)
    return snapped, delta


def snap_tetrahedral_3d(x, y, z):
    """A₃ tetrahedral snap."""
    dots = {
        0:  x + y + z,
        1:  x - y - z,
        2: -x + y - z,
        3: -x - y + z
    }
    best = max(dots, key=dots.get)
    norm = math.hypot(x, y, z)
    mag = max(norm, 1e-12)
    
    vertices = {
        0: ( mag * INV_SQRT3,  mag * INV_SQRT3,  mag * INV_SQRT3),
        1: ( mag * INV_SQRT3, -mag * INV_SQRT3, -mag * INV_SQRT3),
        2: (-mag * INV_SQRT3,  mag * INV_SQRT3, -mag * INV_SQRT3),
        3: (-mag * INV_SQRT3, -mag * INV_SQRT3,  mag * INV_SQRT3)
    }
    
    sx, sy, sz = vertices[best]
    delta = math.hypot(x - sx, y - sy, z - sz)
    return best, sx, sy, sz, delta


def snap_d4_4d(x, y, z, w):
    """D₄ triality snap."""
    a1, a2, a3, a4 = x - y, y - z, z - w, z + w
    r1, r2, r3, r4 = round(a1), round(a2), round(a3), round(a4)
    
    parity = (r1 + r4) & 1
    if parity:
        e1, e2, e3, e4 = a1 - r1, a2 - r2, a3 - r3, a4 - r4
        errors = [abs(e1), abs(e2), abs(e3), abs(e4)]
        min_idx = errors.index(min(errors))
        adjust = [0, 0, 0, 0]
        adjust[min_idx] = 1 if [e1, e2, e3, e4][min_idx] > 0 else -1
        r1 += adjust[0]; r2 += adjust[1]; r3 += adjust[2]; r4 += adjust[3]
    
    sx = (r1 + r2 + r3 + r4) * 0.5
    sy = (-r1 + r2 + r3 + r4) * 0.5
    sz = (-r2 + r3 + r4) * 0.5
    sw = (-r3 + r4) * 0.5
    
    delta = math.sqrt((x - sx)**2 + (y - sy)**2 + (z - sz)**2 + (w - sw)**2)
    return (sx, sy, sz, sw), delta, (r1, r2, r3, r4)


def snap_e8_8d(vals):
    """E₈ exceptional snap."""
    int_candidate = []
    half_candidate = []
    int_dist2 = 0.0
    half_dist2 = 0.0
    
    for v in vals:
        r1 = round(v)
        int_candidate.append(r1)
        d1 = v - r1
        int_dist2 += d1 * d1
        
        vh = v - 0.5
        r2 = round(vh)
        half_candidate.append(r2 + 1)
        d2 = v - (r2 + 0.5)
        half_dist2 += d2 * d2
    
    int_sum = sum(int_candidate) & 1
    if int_sum:
        worst_idx = 0
        worst_err = 0.0
        for i in range(8):
            err = abs(vals[i] - int_candidate[i])
            if err > worst_err:
                worst_err = err
                worst_idx = i
        flipped = vals[worst_idx] - (int_candidate[worst_idx] + 1)
        alt = vals[worst_idx] - (int_candidate[worst_idx] - 1)
        int_dist2 -= worst_err * worst_err
        int_dist2 += min(flipped * flipped, alt * alt)
        int_candidate[worst_idx] += 1 if abs(flipped) < abs(alt) else -1
    
    if int_dist2 <= half_dist2:
        return list(int_candidate), math.sqrt(int_dist2), 'int'
    else:
        return list(half_candidate), math.sqrt(half_dist2), 'half'


# ======================================================================
# Vector Generators
# ======================================================================

def generate_eisenstein_vectors(count=1000):
    """Generate Eisenstein (A₂) test vectors."""
    vectors = []
    random.seed(1001)
    
    # Lattice points (random)
    for _ in range(count // 3):
        a = random.randint(-50, 50)
        b = random.randint(-50, 50)
        snap_x = a - b * 0.5
        snap_y = b * HALF_SQRT3
        vectors.append({
            'type': 'A₂',
            'input': [float(snap_x), float(snap_y)],
            'expected': [a, b, 0.0],
            'label': f'lattice_point_a{a}_b{b}'
        })
    
    # Points near lattice points (with noise)
    for _ in range(count // 3):
        a = random.randint(-20, 20)
        b = random.randint(-20, 20)
        snap_x = a - b * 0.5
        snap_y = b * HALF_SQRT3
        noise_x = random.uniform(-0.5, 0.5)
        noise_y = random.uniform(-0.5, 0.5)
        x = snap_x + noise_x
        y = snap_y + noise_y
        snap_a, snap_b, delta, sx, sy = eisenstein_snap(x, y)
        vectors.append({
            'type': 'A₂',
            'input': [x, y],
            'expected': [snap_a, snap_b, delta],
            'snapped_coords': [sx, sy],
            'label': f'noisy_{a}_{b}_{noise_x:.3f}_{noise_y:.3f}'
        })
    
    # Random points
    for _ in range(count - 2 * (count // 3)):
        x = random.uniform(-100, 100)
        y = random.uniform(-100, 100)
        snap_a, snap_b, delta, sx, sy = eisenstein_snap(x, y)
        vectors.append({
            'type': 'A₂',
            'input': [x, y],
            'expected': [snap_a, snap_b, delta],
            'snapped_coords': [sx, sy],
            'label': f'random_{x:.3f}_{y:.3f}'
        })
    
    return vectors[:count]


def generate_a3_vectors(count=500):
    """Generate A₃ (tetrahedral) test vectors."""
    vectors = []
    random.seed(1002)
    
    # Points at tetrahedron vertices
    inv_s3 = INV_SQRT3
    vertices = [
        (1*inv_s3, 1*inv_s3, 1*inv_s3),
        (1*inv_s3, -1*inv_s3, -1*inv_s3),
        (-1*inv_s3, 1*inv_s3, -1*inv_s3),
        (-1*inv_s3, -1*inv_s3, 1*inv_s3),
    ]
    
    for idx, (vx, vy, vz) in enumerate(vertices):
        for scale in [1.0, 2.0, 5.0]:
            best, sx, sy, sz, delta = snap_tetrahedral_3d(
                scale * vx, scale * vy, scale * vz
            )
            vectors.append({
                'type': 'A₃',
                'input': [scale * vx, scale * vy, scale * vz],
                'expected': [best, sx, sy, sz, delta],
                'label': f'vertex_{idx}_scale_{scale}'
            })
    
    # Points near vertices with noise
    for _ in range(count // 3):
        vx, vy, vz = random.choice(vertices)
        scale = random.uniform(0.5, 5.0)
        noise = random.uniform(-0.3, 0.3)
        x = scale * vx + noise
        y = scale * vy + noise
        z = scale * vz + noise
        best, sx, sy, sz, delta = snap_tetrahedral_3d(x, y, z)
        vectors.append({
            'type': 'A₃',
            'input': [x, y, z],
            'expected': [best, sx, sy, sz, delta],
            'label': f'noisy_vertex_{noise:.3f}'
        })
    
    # Random 3D points
    for _ in range(count - len(vertices)*3 - count // 3):
        x = random.uniform(-5, 5)
        y = random.uniform(-5, 5)
        z = random.uniform(-5, 5)
        best, sx, sy, sz, delta = snap_tetrahedral_3d(x, y, z)
        vectors.append({
            'type': 'A₃',
            'input': [x, y, z],
            'expected': [best, sx, sy, sz, delta],
            'label': f'random3d_{x:.3f}_{y:.3f}_{z:.3f}'
        })
    
    return vectors[:count]


def generate_d4_vectors(count=200):
    """Generate D₄ (triality) test vectors."""
    vectors = []
    random.seed(1003)
    
    # Known D₄ root vectors
    d4_roots = [
        (1, 1, 0, 0), (1, -1, 0, 0), (-1, 1, 0, 0), (-1, -1, 0, 0),
        (1, 0, 1, 0), (1, 0, -1, 0), (-1, 0, 1, 0), (-1, 0, -1, 0),
        (1, 0, 0, 1), (1, 0, 0, -1), (-1, 0, 0, 1), (-1, 0, 0, -1),
        (0, 1, 1, 0), (0, 1, -1, 0), (0, -1, 1, 0), (0, -1, -1, 0),
        (0, 1, 0, 1), (0, 1, 0, -1), (0, -1, 0, 1), (0, -1, 0, -1),
        (0, 0, 1, 1), (0, 0, 1, -1), (0, 0, -1, 1), (0, 0, -1, -1),
    ]
    
    for root in d4_roots[:10]:
        for scale in [1.0, 2.5]:
            x, y, z, w = [scale * v for v in root]
            snapped, delta, roots = snap_d4_4d(x, y, z, w)
            vectors.append({
                'type': 'D₄',
                'input': [x, y, z, w],
                'expected': [*snapped, delta],
                'roots': roots,
                'label': f'root_{root}_scale_{scale}'
            })
    
    # Noisy roots
    for _ in range(count // 2):
        root = random.choice(d4_roots)
        scale = random.uniform(0.5, 3.0)
        noise = random.uniform(-0.2, 0.2)
        x = scale * root[0] + noise
        y = scale * root[1] + noise
        z = scale * root[2] + noise
        w = scale * root[3] + noise
        snapped, delta, roots = snap_d4_4d(x, y, z, w)
        vectors.append({
            'type': 'D₄',
            'input': [x, y, z, w],
            'expected': [*snapped, delta],
            'roots': roots,
            'label': f'noisy_root_{noise:.3f}'
        })
    
    # Random
    for _ in range(count - 10 - count // 2):
        x, y, z, w = [random.uniform(-3, 3) for _ in range(4)]
        snapped, delta, roots = snap_d4_4d(x, y, z, w)
        vectors.append({
            'type': 'D₄',
            'input': [x, y, z, w],
            'expected': [*snapped, delta],
            'roots': roots,
            'label': f'random4d_{x:.3f}_{y:.3f}_{z:.3f}_{w:.3f}'
        })
    
    return vectors[:count]


def generate_e8_vectors(count=100):
    """Generate E₈ (exceptional) test vectors."""
    vectors = []
    random.seed(1004)
    
    # E₈ roots: (±1, ±1, 0, 0, 0, 0, 0, 0) permutations
    e8_type1_roots = []
    for i in range(8):
        for j in range(i+1, 8):
            for s1 in [-1, 1]:
                for s2 in [-1, 1]:
                    vec = [0]*8
                    vec[i] = s1
                    vec[j] = s2
                    e8_type1_roots.append(vec)
    
    sample_type1 = random.sample(e8_type1_roots, min(20, len(e8_type1_roots)))
    
    for root in sample_type1:
        for scale in [1.0, 3.0]:
            vec = [scale * v for v in root]
            snapped, delta, mode = snap_e8_8d(vec)
            vectors.append({
                'type': 'E₈',
                'input': vec,
                'expected': [*snapped, delta],
                'chosen_mode': mode,
                'label': f'root_type1_{root}_scale_{scale}'
            })
    
    # E₈ roots of second type: (±½, ±½, ..., ±½) with even minus signs
    for _ in range(count // 3):
        signs = [random.choice([-0.5, 0.5]) for _ in range(8)]
        # Ensure even number of minus signs
        neg_count = sum(1 for s in signs if s < 0)
        if neg_count % 2 != 0:
            signs[0] *= -1  # flip first sign
        snapped, delta, mode = snap_e8_8d(signs)
        vectors.append({
            'type': 'E₈',
            'input': signs,
            'expected': [*snapped, delta],
            'chosen_mode': mode,
            'label': f'root_type2_{signs}'
        })
    
    # Random
    for _ in range(count - 20 - count // 3):
        vec = [random.uniform(-3, 3) for _ in range(8)]
        snapped, delta, mode = snap_e8_8d(vec)
        vectors.append({
            'type': 'E₈',
            'input': vec,
            'expected': [*snapped, delta],
            'chosen_mode': mode,
            'label': f'random8d_{random.randint(0,9999):04d}'
        })
    
    return vectors[:count]


def generate_edge_cases(count=50):
    """Generate edge case test vectors."""
    vectors = []
    
    # Origin
    vectors.append({
        'type': 'EDGE',
        'input': [0.0, 0.0],
        'expected': [0, 0, 0.0],
        'label': 'origin',
        'category': 'trivial'
    })
    
    # Points on lattice rows
    for i, x in enumerate([0.5, -0.5, 1.5, -1.5, 3.0]):
        y = 0.0
        a, b, delta, sx, sy = eisenstein_snap(x, y)
        vectors.append({
            'type': 'EDGE',
            'input': [x, y],
            'expected': [a, b, delta],
            'snapped_coords': [sx, sy],
            'label': f'on_x_row_{x}',
            'category': 'row_aligned'
        })
    
    # Very large values
    for exp in [3, 4, 5, 6]:
        x = 10**exp
        y = 0.0
        a, b, delta, sx, sy = eisenstein_snap(x, y)
        vectors.append({
            'type': 'EDGE',
            'input': [x, y],
            'expected': [a, b, delta],
            'snapped_coords': [sx, sy],
            'label': f'large_x_{exp}',
            'category': 'large'
        })
    
    for exp in [3, 4]:
        x = 0.0
        y = 10**exp
        a, b, delta, sx, sy = eisenstein_snap(x, y)
        vectors.append({
            'type': 'EDGE',
            'input': [x, y],
            'expected': [a, b, delta],
            'snapped_coords': [sx, sy],
            'label': f'large_y_{exp}',
            'category': 'large'
        })
    
    # Negative values
    for x, y in [(-1.0, 0.0), (0.0, -1.0), (-3.14, -2.72), (-0.001, 0.001)]:
        a, b, delta, sx, sy = eisenstein_snap(x, y)
        vectors.append({
            'type': 'EDGE',
            'input': [x, y],
            'expected': [a, b, delta],
            'snapped_coords': [sx, sy],
            'label': f'negative_{x:.3f}_{y:.3f}',
            'category': 'negative'
        })
    
    # Near-zero
    for exp in range(1, 9):
        x = 10**-exp
        y = 0.0
        a, b, delta, sx, sy = eisenstein_snap(x, y)
        vectors.append({
            'type': 'EDGE',
            'input': [x, y],
            'expected': [a, b, delta],
            'snapped_coords': [sx, sy],
            'label': f'near_zero_1e{exp}',
            'category': 'near_zero'
        })
    
    # Pi/E-based
    for x, y in [(math.pi, math.e), (math.pi, 0), (0, math.e), 
                  (-math.pi, -math.e), (math.pi/2, math.e/2)]:
        a, b, delta, sx, sy = eisenstein_snap(x, y)
        vectors.append({
            'type': 'EDGE',
            'input': [x, y],
            'expected': [a, b, delta],
            'snapped_coords': [sx, sy],
            'label': f'pi_e_{x:.3f}_{y:.3f}',
            'category': 'transcendental'
        })
    
    # Values that cause round-to-nearest-even tie-breaking
    # round(1.5) = 2 (even), round(2.5) = 2 (even)
    # b = round(2y/√3) — pick y so that b_f is exactly .5
    # We need 2y/√3 = n.5 for some integer n
    # y = n.5 * √3 / 2
    for n in [1, 3, 5, 7]:
        y = (n + 0.5) * SQRT3 / 2.0
        x = 0.0
        a, b, delta, sx, sy = eisenstein_snap(x, y)
        vectors.append({
            'type': 'EDGE',
            'input': [x, y],
            'expected': [a, b, delta],
            'snapped_coords': [sx, sy],
            'label': f'tie_breaker_b_{n}_half',
            'category': 'rounding_ties'
        })
    
    # Fill remaining with random edge vectors
    random.seed(1005)
    remaining = count - len(vectors)
    for _ in range(remaining):
        x = random.uniform(-1, 1)
        y = random.uniform(-1, 1)
        a, b, delta, sx, sy = eisenstein_snap(x, y)
        vectors.append({
            'type': 'EDGE',
            'input': [x, y],
            'expected': [a, b, delta],
            'snapped_coords': [sx, sy],
            'label': f'random_edge_{random.randint(0,9999):04d}',
            'category': 'random_edge'
        })
    
    return vectors[:count]


# ======================================================================
# Main
# ======================================================================

def main():
    output_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("Generating test vectors...")
    
    generators = [
        ('eisenstein', generate_eisenstein_vectors, 1000),
        ('a3_tetrahedral', generate_a3_vectors, 500),
        ('d4_triality', generate_d4_vectors, 200),
        ('e8_exceptional', generate_e8_vectors, 100),
        ('edge_cases', generate_edge_cases, 50),
    ]
    
    all_vectors = {}
    total_vectors = 0
    
    for name, generator, count in generators:
        print(f"  {name}: generating {count} vectors...", end=' ')
        vectors = generator(count)
        all_vectors[name] = vectors
        print(f"{len(vectors)} generated")
        total_vectors += len(vectors)
    
    # Save combined output
    output_path = os.path.join(output_dir, 'snapkit_test_vectors.json')
    with open(output_path, 'w') as f:
        json.dump({
            'metadata': {
                'description': 'SnapKit CUDA test vectors for cross-validation',
                'total_vectors': total_vectors,
                'topologies': list(all_vectors.keys()),
            },
            'vectors': all_vectors
        }, f, indent=2)
    
    print(f"\nTotal vectors: {total_vectors}")
    print(f"Saved to: {output_path}")
    
    # Also save per-topology files
    for name, vectors in all_vectors.items():
        per_path = os.path.join(output_dir, f'vectors_{name}.json')
        with open(per_path, 'w') as f:
            json.dump(vectors, f, indent=2)
        print(f"  (also saved {name}: {per_path})")
    
    return 0


if __name__ == '__main__':
    main()
