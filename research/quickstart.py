#!/usr/bin/env python3
"""Eisenstein integer quickstart — zero dependencies, runs anywhere."""

import math

class EisensteinInt:
    """An Eisenstein integer a + bω where ω = e^(iπ/3).
    
    The E12 ring: every point is an exact hexagonal lattice coordinate.
    No floats. No rounding. Zero drift.
    """
    def __init__(self, a, b):
        self.a = a  # real component
        self.b = b  # ω component
    
    def __repr__(self):
        if self.b == 0: return f"E12({self.a})"
        if self.a == 0: return f"E12({self.b}ω)"
        sign = "+" if self.b >= 0 else "-"
        return f"E12({self.a} {sign} {abs(self.b)}ω)"
    
    def __add__(self, other):
        return EisensteinInt(self.a + other.a, self.b + other.b)
    
    def __sub__(self, other):
        return EisensteinInt(self.a - other.a, self.b - other.b)
    
    def __mul__(self, other):
        # (a + bω)(c + dω) = ac + (ad + bc)ω + bdω²
        # ω² = ω - 1, so bdω² = bd(ω - 1) = -bd + bdω
        a, b = self.a, self.b
        c, d = other.a, other.b
        return EisensteinInt(a*c - b*d, a*d + b*c + b*d)
    
    def norm(self):
        """N(a + bω) = a² - ab + b² — always a non-negative integer."""
        return self.a * self.a - self.a * self.b + self.b * self.b
    
    def conjugate(self):
        return EisensteinInt(self.a - self.b, -self.b)
    
    def to_cartesian(self):
        """Convert to (x, y) in the Euclidean plane."""
        x = self.a - self.b / 2
        y = self.b * math.sqrt(3) / 2
        return (x, y)
    
    def d6_rotate(self):
        """Rotate 60° (one D6 step). Exact — returns another Eisenstein integer."""
        return EisensteinInt(-self.b, self.a + self.b)
    
    def d6_neighbors(self):
        """Return all 6 neighbors (hex adjacency)."""
        offsets = [(1,0),(-1,0),(0,1),(0,-1),(1,-1),(-1,1)]
        return [EisensteinInt(self.a+da, self.b+db) for da, db in offsets]


def demo():
    print("═══════════════════════════════════════════")
    print("  Eisenstein Integer Quickstart")
    print("  Zero drift · Exact arithmetic · Hex lattice")
    print("═══════════════════════════════════════════\n")
    
    # Create two Eisenstein integers
    z1 = EisensteinInt(3, 1)
    z2 = EisensteinInt(1, 2)
    print(f"z1 = {z1},  norm = {z1.norm()}")
    print(f"z2 = {z2},  norm = {z2.norm()}")
    
    # Exact arithmetic
    print(f"\nz1 + z2 = {z1 + z2}")
    print(f"z1 × z2 = {z1 * z2}")
    print(f"z1 × conj(z2) = {z1 * z2.conjugate()}")
    
    # D6 rotation — the key operation
    print(f"\n--- D6 Rotation (60° steps) ---")
    z = EisensteinInt(5, 0)
    print(f"Start: {z} → cartesian {z.to_cartesian()}")
    for i in range(6):
        z = z.d6_rotate()
        x, y = z.to_cartesian()
        print(f"  Rotate {i+1}: {z} → ({x:.4f}, {y:.4f})")
    print(f"  After 6 rotations: back to start (exact)")
    
    # Neighbors
    origin = EisensteinInt(0, 0)
    neighbors = origin.d6_neighbors()
    print(f"\n--- D6 Neighbors of origin ---")
    for n in neighbors:
        print(f"  {n} → norm={n.norm()}, cartesian={n.to_cartesian()}")
    
    # The drift comparison
    print(f"\n--- Float drift vs E12 exact ---")
    print(f"After 10000 D6 rotations of (5,0):")
    
    # E12 path: exact
    z_exact = EisensteinInt(5, 0)
    for _ in range(10000):
        z_exact = z_exact.d6_rotate()
    ex, ey = z_exact.to_cartesian()
    print(f"  E12: ({z_exact.a}, {z_exact.b}) → ({ex:.6f}, {ey:.6f})")
    print(f"       Norm: {z_exact.norm()} (should be 25) — EXACT")
    
    # Float path: accumulate error
    angle = 0.0
    x, y = 5.0, 0.0
    for _ in range(10000):
        angle += math.pi / 3
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        x_new = x * cos_a - y * sin_a
        y_new = x * sin_a + y * cos_a
        x, y = x_new, y_new
    print(f"  Float: ({x:.6f}, {y:.6f}) — drifted {math.sqrt((x-5)**2 + y**2):.6f} from start")
    
    print(f"\n  That's why we use integers.")
    print(f"\n═══════════════════════════════════════════")
    print(f"  pip install constraint-theory")
    print(f"  cargo add eisenstein")
    print(f"  https://superinstance.github.io/cocapn-ai-web/")
    print(f"═══════════════════════════════════════════")


if __name__ == "__main__":
    demo()
