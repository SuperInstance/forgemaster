# ct-geometry

Geometric structures on the Pythagorean manifold — triangulation, Voronoi cells, neighborhood graphs, curvature.

## What It Does

- `CirclePoint` — point on unit circle with triple metadata
- `knn()` — k nearest neighbors by angle
- `neighborhood_graph()` — each point connected to k nearest
- `triangulate()` — Delaunay-like triangulation on S1
- `voronoi_cells()` — angular extent of nearest-neighbor regions
- `curvature()` — local density ratio (dense vs sparse regions)

## Install

```toml
[dependencies]
ct-geometry = "0.1"
```

## Quick Start

```rust
use ct_geometry::{generate_circle_points, triangulate, curvature};

let points = generate_circle_points(50000);
let edges = triangulate(&points);
println!("Edges: {}", edges.len());
```

## License

MIT
