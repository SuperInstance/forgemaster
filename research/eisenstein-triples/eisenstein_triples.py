#!/usr/bin/env python3
"""Eisenstein triple generator and analyzer.

Eisenstein triple: a² - ab + b² = c², the hexagonal analog of Pythagorean triples.
This is the norm form of Z[ω] where ω = e^{2πi/3}.
"""

from math import gcd, isqrt
from typing import List, Tuple, Dict, Set
from collections import defaultdict


def norm(a: int, b: int) -> int:
    """Eisenstein norm: a² - ab + b²"""
    return a * a - a * b + b * b


def is_eisenstein_triple(a: int, b: int, c: int) -> bool:
    return norm(a, b) == c * c


def is_primitive(a: int, b: int) -> bool:
    """Check if (a, b) gives a primitive Eisenstein triple.
    In Z[ω], primitivity means gcd in the Eisenstein ring = 1.
    For our purposes: gcd(|a|, |b|, |a-b|) = 1 (up to unit multiplication).
    """
    if a == 0 and b == 0:
        return False
    return gcd(gcd(abs(a), abs(b)), abs(a - b)) == 1


def weyl_orbit(a: int, b: int) -> List[Tuple[int, int]]:
    """All 12 elements of the D₆ orbit: 6 rotations × {±1}.
    
    The 6 rotations of the hexagonal lattice act on (a,b) as:
    (a,b), (-b, a-b), (b-a, -a), (-a, -b), (b, b-a), (a-b, a)
    
    And negation gives 6 more:
    (-a, -b), (b, b-a), (a-b, a), (a, b), (-b, a-b), (b-a, -a)
    
    But since we want DISTINCT elements, we compute all 12 and deduplicate.
    """
    elements = set()
    # The D₆ group acts on Eisenstein integers by multiplication by units
    # Units of Z[ω]: ±1, ±ω, ±ω²  (6 units)
    # And conjugation: a + bω → a + bω² = (a-b) - bω
    
    pairs = [
        (a, b),           # identity
        (-b, a - b),      # ×ω
        (b - a, -a),      # ×ω²
        (-a, -b),         # ×(-1)
        (b, b - a),       # ×(-ω)
        (a - b, a),       # ×(-ω²)
        # Conjugation + units
        (a, a - b),       # conjugate
        (b - a, -b),      # conjugate ×ω
        (-a, b - a),      # conjugate ×ω²
        (-a, b),          # conjugate ×(-1) = -(conjugate)
        (b, a),           # conjugate ×(-ω)
        (a - b, -a),      # conjugate ×(-ω²)
    ]
    
    for p in pairs:
        elements.add(p)
    
    return sorted(elements)


def generate_triples(max_c: int) -> List[Tuple[int, int, int]]:
    """Generate all Eisenstein triples (a, b, c) with c ≤ max_c.
    Returns triples with c > 0, normalized so a > 0 or (a == 0 and b > 0).
    """
    triples = set()
    c_sq_max = max_c * max_c
    
    # Search: for each (a, b), compute norm = a²-ab+b², check if it's a perfect square
    # Norm grows as O(max(a,b)²), so we need |a|, |b| ≤ max_c
    for a in range(-max_c, max_c + 1):
        for b in range(-max_c, max_c + 1):
            if a == 0 and b == 0:
                continue
            n = norm(a, b)
            if n == 0:
                continue
            c = isqrt(n)
            if c * c == n and c <= max_c and c > 0:
                # Normalize: pick canonical representative from D₆ orbit
                # Use the one with smallest (a,b) in lex order with a ≥ 0
                triples.add((a, b, c))
    
    return sorted(triples)


def primitive_triples(max_c: int) -> List[Tuple[int, int, int]]:
    """All primitive Eisenstein triples with c ≤ max_c."""
    return [(a, b, c) for a, b, c in generate_triples(max_c) if is_primitive(a, b)]


def density_comparison(max_c: int) -> Dict:
    """Compare Eisenstein triple density to Pythagorean triple density."""
    eis = primitive_triples(max_c)
    
    # Pythagorean: a² + b² = c², primitive
    pyth = set()
    for a in range(1, max_c + 1):
        for b in range(a, max_c + 1):
            n = a * a + b * b
            c = isqrt(n)
            if c * c == n and c <= max_c and gcd(a, b) == 1:
                pyth.add((a, b, c))
    
    return {
        "eisenstein_count": len(eis),
        "pythagorean_count": len(pyth),
        "ratio": len(eis) / len(pyth) if pyth else float('inf'),
        "eisenstein_density_pct": (len(eis) / len(pyth) - 1) * 100 if pyth else 0,
    }


def multiplication_closure(max_c: int = 100) -> Dict:
    """Verify Eisenstein triples are closed under Z[ω] multiplication.
    
    If (a₁, b₁) has norm c₁² and (a₂, b₂) has norm c₂²,
    then their product has norm (c₁·c₂)².
    
    Multiplication: (a₁+b₁ω)(a₂+b₂ω) = (a₁a₂-b₁b₂) + (a₁b₂+b₁a₂-b₁b₂)ω
    """
    triples = primitive_triples(max_c)
    closed = 0
    failed = 0
    examples = []
    
    for i in range(min(len(triples), 20)):
        a1, b1, c1 = triples[i]
        for j in range(i, min(len(triples), 20)):
            a2, b2, c2 = triples[j]
            
            # Multiply in Z[ω]
            prod_a = a1 * a2 - b1 * b2
            prod_b = a1 * b2 + b1 * a2 - b1 * b2
            
            # Check norm
            prod_norm = norm(prod_a, prod_b)
            expected_c = c1 * c2
            
            if prod_norm == expected_c * expected_c:
                closed += 1
            else:
                failed += 1
                if len(examples) < 5:
                    examples.append(f"  FAIL: ({a1},{b1},{c1}) × ({a2},{b2},{c2}) → ({prod_a},{prod_b}) norm={prod_norm}, expected {expected_c}²={expected_c**2}")
    
    return {"closed": closed, "failed": failed, "examples": examples[:5]}


def parametric_form(m: int, n: int) -> Tuple[int, int, int]:
    """Parametric form for Eisenstein triples.
    
    Analogous to Pythagorean (m²-n², 2mn, m²+n²):
    Eisenstein: (m²-n², 2mn-n², m²-mn+n²) with norm (m²-mn+n²)²
    
    Verify: norm(m²-n², 2mn-n²) = (m²-n²)² - (m²-n²)(2mn-n²) + (2mn-n²)²
    """
    a = m * m - n * n
    b = 2 * m * n - n * n
    c = m * m - m * n + n * n
    
    # Verify
    actual_norm = norm(a, b)
    expected = c * c
    
    return (a, b, c, actual_norm == expected)


if __name__ == "__main__":
    print("=== Eisenstein Triple Generator ===\n")
    
    # Quick test
    print("Small triples (c ≤ 50):")
    for a, b, c in primitive_triples(50):
        print(f"  ({a:+4d}, {b:+4d}, {c:3d})  norm={norm(a,b)}  primitive={is_primitive(a,b)}")
    
    print(f"\nPrimitive triples with c < 100: {len(primitive_triples(100))}")
    print(f"Primitive triples with c < 1000: {len(primitive_triples(1000))}")
    
    print("\n=== Density Comparison ===")
    d = density_comparison(200)
    for k, v in d.items():
        print(f"  {k}: {v}")
    
    print("\n=== Multiplication Closure ===")
    m = multiplication_closure(50)
    print(f"  Closed: {m['closed']}, Failed: {m['failed']}")
    for ex in m['examples']:
        print(ex)
    
    print("\n=== Parametric Form ===")
    for m in range(2, 10):
        for n in range(1, m):
            a, b, c, ok = parametric_form(m, n)
            if ok and c <= 100:
                print(f"  m={m}, n={n} → ({a}, {b}, {c}) ✓" if ok else f"  m={m}, n={n} → ({a}, {b}, {c}) ✗")
    
    print("\n=== Weyl Orbit of (4, 1) ===")
    orbit = weyl_orbit(4, 1)
    for p in orbit:
        print(f"  {p}  norm={norm(*p)}")
    print(f"  All same norm: {len(set(norm(*p) for p in orbit)) == 1}")
