#!/usr/bin/env python3
"""
Visualize angular distribution of Pythagorean triples on the unit circle.
"""

import math
import os
from collections import defaultdict

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def gcd(a, b):
    """Compute GCD using Euclidean algorithm."""
    while b:
        a, b = b, a % b
    return a


def generate_triples(max_c):
    """Generate all Pythagorean triples with c <= max_c."""
    triples = set()
    # Euclid's formula for primitive triples
    m = 2
    while True:
        added = False
        for n in range(1, m):
            if (m - n) % 2 == 0:
                continue
            if gcd(m, n) != 1:
                continue
            a0 = m * m - n * n
            b0 = 2 * m * n
            c0 = m * m + n * n
            if c0 > max_c:
                break
            added = True
            # Generate multiples
            k = 1
            while k * c0 <= max_c:
                a = k * a0
                b = k * b0
                c = k * c0
                # Normalize: store with a <= b for consistent angle
                # Actually we want the actual angle, so keep signs/orientation
                # But for unit circle, (a,b,c) and (b,a,c) are different angles
                # We'll store both orderings? No, Euclid gives a0,b0 but a0 > b0 possible.
                # The angle is atan2(b,a) where b and a are legs.
                # We should consider both (a,b,c) as valid.
                triples.add((a, b, c))
                # Also the swapped version gives a different angle
                triples.add((b, a, c))
                k += 1
        if not added and m * m + 1 > max_c:
            break
        m += 1
    return list(triples)


def compute_angles(triples):
    """Compute angles (radians) for triples on unit circle."""
    angles = []
    for a, b, c in triples:
        if c == 0:
            continue
        # Angle from x-axis to point (a/c, b/c)
        angle = math.atan2(b, a)
        if angle < 0:
            angle += 2 * math.pi
        angles.append(angle)
    return sorted(angles)


def ks_statistic(angles):
    """Compute Kolmogorov-Smirnov statistic against uniform [0, 2π]."""
    n = len(angles)
    if n == 0:
        return 0.0
    max_diff = 0.0
    for i, x in enumerate(angles, start=1):
        empirical = i / n
        theoretical = x / (2 * math.pi)
        diff = abs(empirical - theoretical)
        if diff > max_diff:
            max_diff = diff
        # Also check left limit
        if i > 1:
            empirical_prev = (i - 1) / n
            diff_prev = abs(empirical_prev - theoretical)
            if diff_prev > max_diff:
                max_diff = diff_prev
    return max_diff


def mean_spacing(angles):
    """Compute mean spacing between consecutive angles."""
    if len(angles) < 2:
        return 0.0
    diffs = []
    for i in range(1, len(angles)):
        diffs.append(angles[i] - angles[i - 1])
    # Wrap-around
    diffs.append(2 * math.pi - angles[-1] + angles[0])
    return sum(diffs) / len(diffs)


def max_gap(angles):
    """Compute maximum gap between consecutive angles."""
    if len(angles) < 2:
        return 0.0
    max_g = 0.0
    for i in range(1, len(angles)):
        g = angles[i] - angles[i - 1]
        if g > max_g:
            max_g = g
    # Wrap-around
    g = 2 * math.pi - angles[-1] + angles[0]
    if g > max_g:
        max_g = g
    return max_g


def plot_histograms(results):
    """Subplot histograms of angle distribution for each max_c."""
    n = len(results)
    cols = 2
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(14, 4 * rows), squeeze=False)
    
    for idx, (max_c, angles) in enumerate(results.items()):
        ax = axes[idx // cols][idx % cols]
        n_bins = 72  # 5-degree bins
        counts, bins, patches = ax.hist(angles, bins=n_bins, range=(0, 2 * math.pi),
                                         color='steelblue', edgecolor='white', alpha=0.7,
                                         density=True, label='Observed')
        # Uniform reference
        uniform_height = 1.0 / (2 * math.pi)
        ax.axhline(uniform_height, color='crimson', linestyle='--', linewidth=1.5,
                   label='Uniform reference')
        ax.set_title(f'max_c = {max_c} ({len(angles)} triples)')
        ax.set_xlabel('Angle (radians)')
        ax.set_ylabel('Density')
        ax.set_xlim(0, 2 * math.pi)
        ax.legend(loc='upper right')
    
    # Hide unused subplots
    for idx in range(n, rows * cols):
        ax = axes[idx // cols][idx % cols]
        ax.axis('off')
    
    plt.tight_layout()
    path = '/tmp/ct-histogram/plots/histograms.png'
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"Saved: {path}")


def plot_density(results):
    """Plot constraint density (triples per degree) vs angle."""
    n = len(results)
    cols = 2
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(14, 4 * rows), squeeze=False)
    
    for idx, (max_c, angles) in enumerate(results.items()):
        ax = axes[idx // cols][idx % cols]
        # 360 bins (1 degree each)
        degree_bins = 360
        counts, bins, patches = ax.hist(angles, bins=degree_bins, range=(0, 2 * math.pi),
                                         color='darkgreen', edgecolor='none', alpha=0.7)
        bin_centers = [(bins[i] + bins[i + 1]) / 2 for i in range(len(bins) - 1)]
        ax.plot(bin_centers, counts, color='darkorange', linewidth=0.8)
        ax.set_title(f'Density vs Angle (max_c = {max_c})')
        ax.set_xlabel('Angle (radians)')
        ax.set_ylabel('Triples per degree')
        ax.set_xlim(0, 2 * math.pi)
    
    for idx in range(n, rows * cols):
        axes[idx // cols][idx % cols].axis('off')
    
    plt.tight_layout()
    path = '/tmp/ct-histogram/plots/density.png'
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"Saved: {path}")


def plot_nearest_neighbor(results):
    """Plot nearest-neighbor distance distribution."""
    n = len(results)
    cols = 2
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(14, 4 * rows), squeeze=False)
    
    for idx, (max_c, angles) in enumerate(results.items()):
        ax = axes[idx // cols][idx % cols]
        if len(angles) < 2:
            ax.text(0.5, 0.5, 'Not enough data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(f'max_c = {max_c}')
            continue
        diffs = []
        for i in range(1, len(angles)):
            diffs.append(angles[i] - angles[i - 1])
        # Wrap-around
        diffs.append(2 * math.pi - angles[-1] + angles[0])
        
        ax.hist(diffs, bins=50, color='purple', edgecolor='white', alpha=0.7, density=True)
        # Exponential-like reference for random points on circle (wrapped)
        # But we just show the distribution
        mean_d = sum(diffs) / len(diffs)
        ax.axvline(mean_d, color='gold', linestyle='--', linewidth=1.5, label=f'Mean = {mean_d:.4f}')
        ax.set_title(f'Nearest-neighbor spacing (max_c = {max_c})')
        ax.set_xlabel('Spacing (radians)')
        ax.set_ylabel('Density')
        ax.legend()
    
    for idx in range(n, rows * cols):
        axes[idx // cols][idx % cols].axis('off')
    
    plt.tight_layout()
    path = '/tmp/ct-histogram/plots/nearest_neighbor.png'
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"Saved: {path}")


def main():
    max_c_values = [100, 1000, 5000, 10000, 50000]
    os.makedirs('/tmp/ct-histogram/plots', exist_ok=True)
    
    results = {}
    summary = []
    
    for max_c in max_c_values:
        print(f"Processing max_c = {max_c} ...")
        triples = generate_triples(max_c)
        angles = compute_angles(triples)
        results[max_c] = angles
        
        ks = ks_statistic(angles)
        msp = mean_spacing(angles)
        mg = max_gap(angles)
        
        summary.append({
            'max_c': max_c,
            'num_triples': len(angles),
            'ks_stat': ks,
            'mean_spacing': msp,
            'max_gap': mg,
        })
    
    print("\nGenerating plots ...")
    plot_histograms(results)
    plot_density(results)
    plot_nearest_neighbor(results)
    
    print("\n" + "=" * 65)
    print(f"{'max_c':>10} {'num_triples':>12} {'KS stat':>12} {'mean_spacing':>14} {'max_gap':>12}")
    print("-" * 65)
    for row in summary:
        print(f"{row['max_c']:>10} {row['num_triples']:>12} {row['ks_stat']:>12.6f} "
              f"{row['mean_spacing']:>14.6f} {row['max_gap']:>12.6f}")
    print("=" * 65)


if __name__ == '__main__':
    main()
