#!/usr/bin/env python3
"""EXPERIMENT 1: Calibration = Deadband? Multi-lattice test.

Claude's critique: "calibration = deadband is analogy, not theorem."
To test: simulate Oracle1's MeasurementTriangle on DIFFERENT lattices.
If calibration convergence rate correlates with covering radius, it's structural.
If not, it's just "both converge to zero" (trivial).

Prediction: if calibration=deadband, convergence rate ∝ 1/ρ.
"""
import math, random

OMEGA_REAL = -0.5
OMEGA_IMAG = math.sqrt(3)/2

def eisenstein_snap(x, y):
    a = round(x - y * OMEGA_REAL / OMEGA_IMAG)
    b = round(y / OMEGA_IMAG)
    best, best_d = None, float('inf')
    for da in range(-1,2):
        for db in range(-1,2):
            ca, cb = a+da, b+db
            cx, cy = ca + cb*OMEGA_REAL, cb*OMEGA_IMAG
            d = math.sqrt((x-cx)**2 + (y-cy)**2)
            if d < best_d: best, best_d = (ca,cb), d
    return best, best_d

def square_snap(x, y):
    """Square lattice Z^2 snap."""
    a, b = round(x), round(y)
    return (a,b), math.sqrt((x-a)**2 + (y-b)**2)

def triangular_snap_high(x, y):
    """A_2 lattice with doubled spacing (covering radius = 2/sqrt(3))."""
    a = round(x - y * OMEGA_REAL / OMEGA_IMAG)
    b = round(y / OMEGA_IMAG)
    best, best_d = None, float('inf')
    for da in range(-1,2):
        for db in range(-1,2):
            ca, cb = (a+da)*2, (b+db)*2  # doubled spacing
            cx, cy = ca + cb*OMEGA_REAL, cb*OMEGA_IMAG
            d = math.sqrt((x-cx)**2 + (y-cy)**2)
            if d < best_d: best, best_d = (ca,cb), d
    return best, best_d

def measurement_triangle_convergence(snap_fn, start_x, start_y, target_x, target_y, steps=100):
    """Simulate Oracle1's MeasurementTriangle: 3 measurements, compute residual, converge.
    
    The triangle takes 3 consecutive measurements of position.
    Residual = |m1 + m2 - m3| / max(|m1|,|m2|,|m3|).
    Calibration succeeds when residual < threshold.
    
    We simulate: at each step, take 3 noisy readings of distance to snap target,
    compute triangle residual, and move toward target if residual is low.
    """
    measurements = []
    convergence_steps = []
    x, y = start_x, start_y
    
    for step in range(steps):
        # Three noisy measurements of current position
        noise = 0.01
        m1 = (x + random.gauss(0, noise), y + random.gauss(0, noise))
        m2 = (x + random.gauss(0, noise), y + random.gauss(0, noise))
        m3 = (x + random.gauss(0, noise), y + random.gauss(0, noise))
        
        # Triangle residual (closure error)
        mx = max(abs(m1[0]), abs(m2[0]), abs(m3[0]))
        my = max(abs(m1[1]), abs(m2[1]), abs(m3[1]))
        residual_x = abs(m1[0] + m2[0] - 2*m3[0]) / max(mx, 0.001)
        residual_y = abs(m1[1] + m2[1] - 2*m3[1]) / max(my, 0.001)
        residual = (residual_x + residual_y) / 2
        
        # Snap the current position
        snap, snap_err = snap_fn(x, y)
        
        # Deadband funnel: exponential decay
        t = step / steps
        deadband = math.exp(-5 * t)  # exponential from ~1 to ~0.007
        
        convergence_steps.append({
            'step': step,
            'residual': residual,
            'snap_error': snap_err,
            'deadband': deadband,
            'correlation': residual * snap_err if snap_err > 0 else 0
        })
        
        # Move toward target
        dx, dy = target_x - x, target_y - y
        dist = math.sqrt(dx*dx + dy*dy)
        if dist > 0.001:
            x += dx / dist * 0.05
            y += dy / dist * 0.05
    
    return convergence_steps

# Run experiment on 3 lattices
random.seed(42)
N = 500  # trials per lattice

lattices = {
    'Eisenstein (ρ=1/√3≈0.577)': (eisenstein_snap, 1/math.sqrt(3)),
    'Square Z² (ρ=√2/2≈0.707)': (square_snap, math.sqrt(2)/2),
    'Wide Eisenstein (ρ=2/√3≈1.155)': (triangular_snap_high, 2/math.sqrt(3)),
}

print("=" * 90)
print("EXPERIMENT 1: Does calibration convergence rate correlate with covering radius?")
print("=" * 90)
print(f"Trials per lattice: {N}")
print()

for name, (snap_fn, rho) in lattices.items():
    # Generate random start points and their snap targets
    residual_sum = 0
    snap_err_sum = 0
    correlation = 0
    steps_to_half = []  # steps until snap_error < rho/2
    
    for _ in range(N):
        x = random.uniform(-3, 3)
        y = random.uniform(-3, 3)
        target, _ = snap_fn(x, y)
        tx = target[0] + target[1] * OMEGA_REAL if snap_fn != square_snap else target[0]
        ty = target[1] * OMEGA_IMAG if snap_fn != square_snap else target[1]
        
        steps = measurement_triangle_convergence(snap_fn, x, y, tx, ty, steps=80)
        
        # Measure correlation between residual and snap_error
        residuals = [s['residual'] for s in steps]
        snap_errs = [s['snap_error'] for s in steps]
        
        # Pearson correlation
        n = len(residuals)
        mean_r = sum(residuals)/n
        mean_e = sum(snap_errs)/n
        cov = sum((residuals[i]-mean_r)*(snap_errs[i]-mean_e) for i in range(n))
        var_r = sum((r-mean_r)**2 for r in residuals)
        var_e = sum((e-mean_e)**2 for e in snap_errs)
        if var_r > 0 and var_e > 0:
            corr = cov / math.sqrt(var_r * var_e)
        else:
            corr = 0
        
        correlation += corr
        residual_sum += mean_r
        snap_err_sum += mean_e
        
        # Steps until snap_error < rho/2
        for s in steps:
            if s['snap_error'] < rho/2:
                steps_to_half.append(s['step'])
                break
    
    mean_corr = correlation / N
    mean_residual = residual_sum / N
    mean_snap_err = snap_err_sum / N
    mean_steps = sum(steps_to_half) / len(steps_to_half) if steps_to_half else float('inf')
    
    print(f"  {name}")
    print(f"    Covering radius ρ = {rho:.4f}")
    print(f"    Mean triangle residual: {mean_residual:.6f}")
    print(f"    Mean snap error: {mean_snap_err:.6f}")
    print(f"    Residual-SnapError correlation: {mean_corr:.4f}")
    print(f"    Mean steps to ρ/2: {mean_steps:.1f}")
    print()

# KEY TEST: Does convergence rate scale with 1/ρ?
print("=" * 90)
print("KEY TEST: Does mean_steps_to_ρ/2 scale with ρ?")
print("If calibration=deadband, convergence rate ∝ 1/ρ")
print("Predicted ranking: Eisenstein fastest, Square middle, Wide slowest")
print("If ranking matches: structural connection (SURVIVES)")
print("If random: trivial convergence (DIES)")
