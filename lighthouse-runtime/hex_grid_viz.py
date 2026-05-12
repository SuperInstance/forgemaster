#!/usr/bin/env python3
"""
Hex Grid Visualizer for Eisenstein Lattice Dodecet Encoding.

Snap floating-point (x,y) coordinates to the nearest Eisenstein lattice point
and visualize the dodecet sector coloring (6 Weyl chambers).

Usage:
    python hex_grid_viz.py --points "1.2,3.4 2.7,5.1" --output viz.png
    python hex_grid_viz.py --output viz.png  # random points
"""

import argparse
import math
import random
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import RegularPolygon
import numpy as np


# ---------------------------------------------------------------------------
# Eisenstein lattice math
# ---------------------------------------------------------------------------

# Basis vectors for Eisenstein integers:  e1 = (1, 0),  e2 = (-1/2, sqrt(3)/2)
E1 = np.array([1.0, 0.0])
E2 = np.array([-0.5, math.sqrt(3) / 2.0])

# Change-of-basis matrix  [e1 | e2]  (columns)
BASIS = np.column_stack([E1, E2])
BASIS_INV = np.linalg.inv(BASIS)


def snap_to_eisenstein(x: float, y: float):
    """Return (a, b, snap_x, snap_y, error) for the nearest Eisenstein lattice point."""
    coords = BASIS_INV @ np.array([x, y])
    a = int(round(coords[0]))
    b = int(round(coords[1]))
    snap = BASIS @ np.array([a, b], dtype=float)
    err = math.hypot(x - snap[0], y - snap[1])
    return a, b, float(snap[0]), float(snap[1]), err


def weyl_sector(x: float, y: float, snap_x: float, snap_y: float) -> int:
    """Return Weyl chamber sector 0-5 based on residual angle mod pi/3."""
    dx = x - snap_x
    dy = y - snap_y
    if abs(dx) < 1e-12 and abs(dy) < 1e-12:
        return 0
    angle = math.atan2(dy, dx)
    if angle < 0:
        angle += 2 * math.pi
    sector = int(angle / (math.pi / 3)) % 6
    return sector


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

SECTOR_COLORS = [
    "#e6194B",  # red
    "#3cb44b",  # green
    "#ffe119",  # yellow
    "#4363d8",  # blue
    "#f58231",  # orange
    "#911eb4",  # purple
]

SECTOR_LABELS = [
    "Sector 0 (0°-60°)",
    "Sector 1 (60°-120°)",
    "Sector 2 (120°-180°)",
    "Sector 3 (180°-240°)",
    "Sector 4 (240°-300°)",
    "Sector 5 (300°-360°)",
]


def hex_vertices(cx, cy, size=0.45):
    """Flat-top hexagon vertices."""
    angles = [math.radians(60 * i) for i in range(6)]
    return [(cx + size * math.cos(a), cy + size * math.sin(a)) for a in angles]


def parse_points(points_str: str):
    """Parse 'x1,y1 x2,y2 ...' into list of (x, y) tuples."""
    pts = []
    for tok in points_str.strip().split():
        parts = tok.split(",")
        if len(parts) != 2:
            raise ValueError(f"Bad point token: {tok!r}")
        pts.append((float(parts[0]), float(parts[1])))
    return pts


def random_points(n: int = 8):
    """Generate n random points in a reasonable range."""
    return [(random.uniform(-4, 4), random.uniform(-4, 4)) for _ in range(n)]


# ---------------------------------------------------------------------------
# Main visualization
# ---------------------------------------------------------------------------

def visualize(points, output_path="viz.png"):
    snappings = []
    for (x, y) in points:
        a, b, sx, sy, err = snap_to_eisenstein(x, y)
        sec = weyl_sector(x, y, sx, sy)
        snappings.append({
            "orig": (x, y),
            "a": a, "b": b,
            "snap": (sx, sy),
            "error": err,
            "sector": sec,
        })

    # Collect unique snap lattice points
    snap_set = {(s["a"], s["b"]) for s in snappings}
    # Also add nearby lattice points for context grid
    all_coords = [s["snap"] for s in snappings]
    if all_coords:
        xs = [c[0] for c in all_coords]
        ys = [c[1] for c in all_coords]
        coords_ab = [BASIS_INV @ np.array(c) for c in all_coords]
        min_a = int(math.floor(min(c[0] for c in coords_ab))) - 2
        max_a = int(math.ceil(max(c[0] for c in coords_ab))) + 2
        min_b = int(math.floor(min(c[1] for c in coords_ab))) - 2
        max_b = int(math.ceil(max(c[1] for c in coords_ab))) + 2
    else:
        min_a, max_a = -3, 3
        min_b, max_b = -3, 3

    # Build context lattice points
    context_lattice = set()
    for a in range(min_a, max_a + 1):
        for b in range(min_b, max_b + 1):
            context_lattice.add((a, b))

    fig, ax = plt.subplots(1, 1, figsize=(14, 12))
    ax.set_aspect("equal")

    # Draw background sector wedges centered on each snap point
    for s in snappings:
        sx, sy = s["snap"]
        sec = s["sector"]
        color = SECTOR_COLORS[sec]
        # Draw a faint wedge
        wedge = mpatches.Wedge(
            (sx, sy), 1.2, sec * 60, (sec + 1) * 60,
            facecolor=color, alpha=0.12, edgecolor="none",
        )
        ax.add_patch(wedge)

    # Draw context hexagons (faint gray)
    for (a, b) in context_lattice:
        pt = BASIS @ np.array([a, b], dtype=float)
        if (a, b) not in snap_set:
            hex_patch = RegularPolygon(
                pt, numVertices=6, radius=0.45, orientation=0,
                facecolor="#f0f0f0", edgecolor="#cccccc", linewidth=0.5,
            )
            ax.add_patch(hex_patch)

    # Draw snap hexagons with sector color
    for s in snappings:
        sx, sy = s["snap"]
        sec = s["sector"]
        color = SECTOR_COLORS[sec]
        hex_patch = RegularPolygon(
            (sx, sy), numVertices=6, radius=0.45, orientation=0,
            facecolor=color, alpha=0.35, edgecolor="black", linewidth=1.5,
        )
        ax.add_patch(hex_patch)

    # Draw connection lines (original → snap)
    for s in snappings:
        ox, oy = s["orig"]
        sx, sy = s["snap"]
        ax.plot([ox, sx], [oy, sy], color="gray", linewidth=1.0, linestyle="--", zorder=3)

    # Draw original points (red dots)
    for s in snappings:
        ox, oy = s["orig"]
        ax.plot(ox, oy, "o", color="red", markersize=7, zorder=5, markeredgecolor="darkred")

    # Draw snap points (blue dots on top of hexagons)
    for s in snappings:
        sx, sy = s["snap"]
        ax.plot(sx, sy, "o", color="blue", markersize=5, zorder=6, markeredgecolor="darkblue")

    # Annotate each snap with dodecet encoding
    for i, s in enumerate(snappings):
        sx, sy = s["snap"]
        label = f"({s['a']},{s['b']}) s{s['sector']} ε={s['error']:.3f}"
        # Offset annotation to avoid overlap with the point
        offset_x = 0.35 if (i % 2 == 0) else -0.35
        offset_y = 0.35 if (i % 3 == 0) else -0.25
        ax.annotate(
            label,
            xy=(sx, sy),
            xytext=(sx + offset_x, sy + offset_y),
            fontsize=7,
            fontfamily="monospace",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8, edgecolor="gray"),
            arrowprops=dict(arrowstyle="-", color="gray", lw=0.5),
            zorder=7,
        )

    # Legend
    legend_handles = [
        mpatches.Patch(color=SECTOR_COLORS[i], alpha=0.45, label=SECTOR_LABELS[i])
        for i in range(6)
    ]
    legend_handles.append(
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor="red",
                    markersize=8, label="Original point")
    )
    legend_handles.append(
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor="blue",
                    markersize=8, label="Snap target")
    )
    ax.legend(handles=legend_handles, loc="upper left", fontsize=8, framealpha=0.9)

    ax.set_title("Eisenstein Lattice Dodecet Encoding", fontsize=14, fontweight="bold")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(output_path, dpi=150)
    print(f"Saved visualization to {output_path}")

    # Print summary table
    print(f"\n{'Idx':>3}  {'Orig':>16}  {'Snap(a,b)':>10}  {'Snap(xy)':>16}  {'Sec':>3}  {'Error':>7}")
    print("-" * 70)
    for i, s in enumerate(snappings):
        ox, oy = s["orig"]
        sx, sy = s["snap"]
        print(
            f"{i:>3}  ({ox:+6.2f},{oy:+6.2f})  "
            f"({s['a']:>+3},{s['b']:>+3})    "
            f"({sx:+6.2f},{sy:+6.2f})  "
            f"{s['sector']:>3}  {s['error']:>7.4f}"
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Hex grid visualizer for Eisenstein lattice dodecet encoding."
    )
    parser.add_argument(
        "--points", type=str, default=None,
        help='Space-separated "x,y" pairs, e.g. "1.2,3.4 2.7,5.1"',
    )
    parser.add_argument(
        "--output", type=str, default="viz.png",
        help="Output image path (default: viz.png)",
    )
    parser.add_argument(
        "--n-random", type=int, default=8,
        help="Number of random points when --points is omitted (default: 8)",
    )
    args = parser.parse_args()

    if args.points:
        points = parse_points(args.points)
    else:
        random.seed(42)
        points = random_points(args.n_random)
        print(f"Using {args.n_random} random points (seed=42)")

    visualize(points, args.output)


if __name__ == "__main__":
    main()
