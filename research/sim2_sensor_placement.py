"""
Sim 2: Optimal Sensor Placement
Compare strategies for placing N sensors to minimize max snap error.
"""
import numpy as np

np.random.seed(42)

DOMAIN_SIZE = 10.0
QUERY_POINTS = 10000

def snap_to_nearest(points, sensors):
    """For each point, find distance to nearest sensor (= snap error)."""
    # Vectorized: compute all distances
    # points: (N, 2), sensors: (M, 2)
    diff = points[:, np.newaxis, :] - sensors[np.newaxis, :, :]  # (N, M, 2)
    dists = np.sqrt(np.sum(diff**2, axis=2))  # (N, M)
    return np.min(dists, axis=1)  # (N,)

def grid_placement(n, size):
    """Grid placement: n sensors in sqrt(n) x sqrt(n) grid."""
    side = int(np.sqrt(n))
    if side * side != n:
        # Not a perfect square, adjust
        side = int(np.ceil(np.sqrt(n)))
    spacing = size / (side + 1)
    xs = np.arange(1, side + 1) * spacing
    ys = np.arange(1, side + 1) * spacing
    xx, yy = np.meshgrid(xs, ys)
    pts = np.column_stack([xx.ravel(), yy.ravel()])[:n]
    return pts

def random_placement(n, size):
    """Random placement."""
    return np.random.uniform(0, size, (n, 2))

def centroid_placement(n, size):
    """Place at Voronoi cell centers of a grid (i.e., offset grid)."""
    side = int(np.ceil(np.sqrt(n)))
    spacing = size / (side + 1)
    xs = np.arange(1, side + 1) * spacing - spacing / 2
    ys = np.arange(1, side + 1) * spacing - spacing / 2
    xx, yy = np.meshgrid(xs, ys)
    pts = np.column_stack([xx.ravel(), yy.ravel()])
    pts = pts[(pts[:, 0] >= 0) & (pts[:, 0] <= size) & 
              (pts[:, 1] >= 0) & (pts[:, 1] <= size)]
    return pts[:n] if len(pts) >= n else np.vstack([pts, random_placement(n - len(pts), size)])

def boundary_placement(n, size):
    """Place sensors preferentially near domain boundaries."""
    pts = []
    # Half on boundary region, half random
    n_boundary = n // 2
    n_interior = n - n_boundary
    
    # Boundary sensors: sample near edges
    for _ in range(n_boundary):
        edge = np.random.randint(4)
        if edge == 0:  # left
            pts.append([np.random.uniform(0, size * 0.1), np.random.uniform(0, size)])
        elif edge == 1:  # right
            pts.append([np.random.uniform(size * 0.9, size), np.random.uniform(0, size)])
        elif edge == 2:  # bottom
            pts.append([np.random.uniform(0, size), np.random.uniform(0, size * 0.1)])
        else:  # top
            pts.append([np.random.uniform(0, size), np.random.uniform(size * 0.9, size)])
    
    # Interior: random
    for _ in range(n_interior):
        pts.append(np.random.uniform(0, size, 2))
    
    return np.array(pts[:n])

def greedy_placement(n, size, n_sample=5000):
    """Greedy: place each sensor where current max error is highest."""
    sensors = np.empty((0, 2))
    sample_points = np.random.uniform(0, size, (n_sample, 2))
    
    for i in range(n):
        if len(sensors) == 0:
            # First sensor at center
            new_sensor = np.array([[size / 2, size / 2]])
        else:
            errors = snap_to_nearest(sample_points, sensors)
            # Place at point with highest error
            worst_idx = np.argmax(errors)
            new_sensor = sample_points[worst_idx:worst_idx+1]
            # Remove nearby sample points to avoid clustering
            dists_to_new = np.sqrt(np.sum((sample_points - new_sensor)**2, axis=1))
            sample_points = sample_points[dists_to_new > size / (2 * np.sqrt(n))]
            if len(sample_points) < 100:
                sample_points = np.random.uniform(0, size, (n_sample, 2))
        
        sensors = np.vstack([sensors, new_sensor])
    
    return sensors

print("=" * 70)
print("SIM 2: OPTIMAL SENSOR PLACEMENT")
print("=" * 70)
print(f"Domain: {DOMAIN_SIZE}×{DOMAIN_SIZE}, Query points: {QUERY_POINTS}")
print()

strategies = {
    'Grid': grid_placement,
    'Centroid (offset)': centroid_placement,
    'Boundary-aware': boundary_placement,
    'Random': random_placement,
    'Greedy (max-error)': greedy_placement,
}

Ns = [4, 9, 16, 25, 36]

print(f"{'Strategy':<22} {'N=4':>12} {'N=9':>12} {'N=16':>12} {'N=25':>12} {'N=36':>12} {'Average':>12}")
print("-" * 94)

query_pts = np.random.uniform(0, DOMAIN_SIZE, (QUERY_POINTS, 2))

strategy_avgs = {}
for sname, sfn in strategies.items():
    row = []
    for n in Ns:
        sensors = sfn(n, DOMAIN_SIZE)
        errors = snap_to_nearest(query_pts, sensors)
        max_err = np.max(errors)
        row.append(max_err)
    avg = np.mean(row)
    strategy_avgs[sname] = avg
    row_str = " ".join(f"{v:>12.3f}" for v in row)
    print(f"{sname:<22} {row_str} {avg:>12.3f}")

print()
print("RANKING (by average max error, lower is better):")
for rank, (sname, avg) in enumerate(sorted(strategy_avgs.items(), key=lambda x: x[1]), 1):
    print(f"  {rank}. {sname}: {avg:.3f}")
