"""
Sim 3: Adaptive Bit Allocation
Compare uniform vs right-skew-optimized quantization for INT8 constraint checking.
"""
import numpy as np

np.random.seed(42)

N_ERRORS = 100000
A = np.sqrt(3) / 2  # Eisenstein cell area
rho = 1 / np.sqrt(3)  # covering radius
N_LEVELS = 256  # INT8

# Generate snap errors from right-skewed distribution: P(d < r) = pi*r^2/A
u = np.random.uniform(0, 1, N_ERRORS)
errors = np.sqrt(A * u / np.pi)

print("=" * 70)
print("SIM 3: ADAPTIVE BIT ALLOCATION")
print("=" * 70)
print(f"N errors: {N_ERRORS}, Quantization levels: {N_LEVELS}")
print(f"Error range: [{errors.min():.4f}, {errors.max():.4f}]")
print(f"Error mean: {errors.mean():.4f}, median: {np.median(errors):.4f}")
print(f"Error std: {errors.std():.4f}")
print()

# Strategy 1: Uniform quantization
def uniform_quantize(errors, n_levels, vmin, vmax):
    levels = np.linspace(vmin, vmax, n_levels)
    indices = np.clip(np.round((errors - vmin) / (vmax - vmin) * (n_levels - 1)), 0, n_levels - 1).astype(int)
    quantized = levels[indices]
    return quantized, levels

# Strategy 2: Quantile-based binning (equal probability mass per bin)
def quantile_quantize(errors, n_levels):
    percentiles = np.linspace(0, 100, n_levels)
    levels = np.percentile(errors, percentiles)
    # Assign each error to nearest level
    indices = np.searchsorted(levels, errors, side='right') - 1
    indices = np.clip(indices, 0, n_levels - 1)
    quantized = levels[indices]
    return quantized, levels

# Strategy 3: sqrt-scaled quantization (more levels near rho, fewer near 0)
def sqrt_quantize(errors, n_levels, vmin, vmax):
    # Transform: use sqrt spacing (concentrate levels near vmax)
    levels_transformed = np.linspace(np.sqrt(vmin), np.sqrt(vmax), n_levels)
    levels = levels_transformed ** 2
    indices = np.searchsorted(levels, errors, side='right') - 1
    indices = np.clip(indices, 0, n_levels - 1)
    quantized = levels[indices]
    return quantized, levels

# Strategy 4: Log-ish quantization (concentrate near 0 instead — for comparison)
def logish_quantize(errors, n_levels, vmin, vmax):
    eps = 1e-10
    levels_log = np.linspace(np.log(vmin + eps), np.log(vmax + eps), n_levels)
    levels = np.exp(levels_log)
    indices = np.searchsorted(levels, errors, side='right') - 1
    indices = np.clip(indices, 0, n_levels - 1)
    quantized = levels[indices]
    return quantized, levels

vmin, vmax = 0, rho

strategies = {
    'Uniform (evenly spaced)': lambda: uniform_quantize(errors, N_LEVELS, vmin, vmax),
    'Quantile (equal mass)': lambda: quantile_quantize(errors, N_LEVELS),
    'Sqrt-scaled (more near ρ)': lambda: sqrt_quantize(errors, N_LEVELS, vmin, vmax),
    'Log-scaled (more near 0)': lambda: logish_quantize(errors, N_LEVELS, vmin, vmax),
}

print(f"{'Strategy':<30} {'MSE':>12} {'RMSE':>12} {'Max Error':>12} {'Mean Abs':>12}")
print("-" * 80)

results = {}
for name, fn in strategies.items():
    quantized, levels = fn()
    mse = np.mean((errors - quantized) ** 2)
    rmse = np.sqrt(mse)
    max_err = np.max(np.abs(errors - quantized))
    mae = np.mean(np.abs(errors - quantized))
    results[name] = {'mse': mse, 'rmse': rmse, 'max_err': max_err, 'mae': mae}
    print(f"{name:<30} {mse:>12.6f} {rmse:>12.6f} {max_err:>12.6f} {mae:>12.6f}")

print()
print("LEVEL DISTRIBUTION ANALYSIS:")
print()
for name, fn in strategies.items():
    quantized, levels = fn()
    # Bin count per decile of error range
    deciles = np.linspace(0, rho, 11)
    counts = []
    for i in range(10):
        mask = (errors >= deciles[i]) & (errors < deciles[i+1])
        counts.append(np.sum(mask))
    print(f"  {name}: levels range [{levels[1]-levels[0]:.6f} ... {levels[-1]-levels[-2]:.6f}]")

print()
print("RANKING (by MSE, lower is better):")
for rank, (name, r) in enumerate(sorted(results.items(), key=lambda x: x[1]['mse']), 1):
    print(f"  {rank}. {name}: MSE={r['mse']:.6f}, RMSE={r['rmse']:.6f}")

print()
print("KEY INSIGHT:")
print("  The right-skewed distribution has most errors near 0, fewer near ρ.")
print("  Quantile binning puts equal mass in each bin, giving finer resolution")
print("  where most data lives (near 0). For right-skew data, this means")
print("  MORE levels near 0 and FEWER near ρ — opposite of the hypothesis!")
print("  The question is whether we want to minimize MSE (quantile wins)")
print("  or minimize max error (uniform or sqrt-scaled may win).")
