"""Eisenstein Kernel Benchmark — Python"""
import time
import math
import random

random.seed(42)

def eisenstein_norm(a: int, b: int) -> int:
    """N(a + bw) = a^2 - a*b + b^2"""
    return a * a - a * b + b * b

def eisenstein_snap(x: float, y: float) -> tuple:
    """Snap (x,y) to nearest Eisenstein lattice point"""
    q = (2.0/3.0 * x - 1.0/3.0 * y)
    r = (2.0/3.0 * y)
    rq = round(q)
    rr = round(r)
    rs = round(-q - r)
    diff = abs(rq + rr + rs)
    if diff == 0:
        a, b = rq, rr
    elif diff == 2:
        if abs(rq - q) > abs(rr - r):
            rq = -rr - rs
        else:
            rr = -rq - rs
        a, b = rq, rr
    else:
        a, b = rq, rr
    return a, b

def eisenstein_distance(x: float, y: float, a: int, b: int) -> float:
    """Distance from (x,y) to lattice point (a, bw)"""
    px = a - 0.5 * b
    py = b * math.sqrt(3) / 2.0
    return math.sqrt((x - px)**2 + (y - py)**2)

def constraint_check(a: int, b: int, radius: float) -> bool:
    """Check if Eisenstein norm is within radius constraint"""
    norm = eisenstein_norm(a, b)
    return norm <= radius * radius

# Generate test data
N = 10_000_000
norm_inputs = [(random.randint(-1000, 1000), random.randint(-1000, 1000)) for _ in range(N)]
snap_inputs = [(random.uniform(-100, 100), random.uniform(-100, 100)) for _ in range(N)]
constraint_inputs = [(random.randint(-100, 100), random.randint(-100, 100), random.uniform(1, 50)) for _ in range(N)]

# Benchmark norm
start = time.perf_counter()
norm_sum = sum(eisenstein_norm(a, b) for a, b in norm_inputs)
norm_time = time.perf_counter() - start

# Benchmark snap
start = time.perf_counter()
snap_results = [eisenstein_snap(x, y) for x, y in snap_inputs]
snap_time = time.perf_counter() - start

# Benchmark constraint
start = time.perf_counter()
constraint_pass = sum(1 for a, b, r in constraint_inputs if constraint_check(a, b, r))
constraint_time = time.perf_counter() - start

print(f"Python Results (N={N:,}):")
print(f"  eisenstein_norm:  {norm_time:.3f}s  (sum={norm_sum})")
print(f"  eisenstein_snap:  {snap_time:.3f}s  (first={snap_results[0]})")
print(f"  constraint_check: {constraint_time:.3f}s  (pass={constraint_pass})")
print(f"  TOTAL: {norm_time + snap_time + constraint_time:.3f}s")
