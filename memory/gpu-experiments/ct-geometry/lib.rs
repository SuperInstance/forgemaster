//! # ct-geometry — Geometric Structures on the Pythagorean Manifold
//!
//! Delaunay-like triangulation, neighborhood graphs, Voronoi cells,
//! and geometric operations on the S1 manifold of Pythagorean triple angles.

const TAU: f64 = 6.283185307179586;

/// A point on the unit circle (angle only, radius = c/hypotenuse).
#[derive(Debug, Clone, Copy)]
pub struct CirclePoint {
    pub angle: f64,
    pub a: i64,
    pub b: i64,
    pub c: i64,
}

impl CirclePoint {
    pub fn new(angle: f64, a: i64, b: i64, c: i64) -> Self {
        CirclePoint { angle: ((angle % TAU) + TAU) % TAU, a, b, c }
    }
    
    /// Cartesian coordinates on unit circle.
    pub fn xy(&self) -> (f64, f64) {
        (self.angle.cos(), self.angle.sin())
    }
    
    /// Scaled Cartesian coordinates (radius = c).
    pub fn xy_scaled(&self) -> (f64, f64) {
        let r = self.c as f64;
        (r * self.angle.cos(), r * self.angle.sin())
    }
    
    pub fn is_pythagorean(&self) -> bool {
        self.a * self.a + self.b * self.b == self.c * self.c
    }
}

/// Angular distance on [0, 2pi).
pub fn angular_distance(a: f64, b: f64) -> f64 {
    let d = (a - b).abs();
    d.min(TAU - d)
}

/// Find k nearest neighbors by angle on the manifold.
pub fn knn(query: f64, points: &[CirclePoint], k: usize) -> Vec<usize> {
    let mut dists: Vec<(f64, usize)> = points.iter().enumerate()
        .map(|(i, p)| (angular_distance(query, p.angle), i))
        .collect();
    dists.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(std::cmp::Ordering::Equal));
    dists.truncate(k);
    dists.into_iter().map(|(_, i)| i).collect()
}

/// Build a neighborhood graph: each point connected to its k nearest neighbors.
pub fn neighborhood_graph(points: &[CirclePoint], k: usize) -> Vec<Vec<usize>> {
    points.iter().enumerate().map(|(i, p)| {
        knn(p.angle, points, k + 1).into_iter().filter(|&j| j != i).collect()
    }).collect()
}

/// Delaunay-like triangulation on S1: connect each point to its 2 nearest neighbors.
/// Returns edges as (i, j) pairs.
pub fn triangulate(points: &[CirclePoint]) -> Vec<(usize, usize)> {
    let mut edges = Vec::new();
    let adj = neighborhood_graph(points, 2);
    for (i, neighbors) in adj.iter().enumerate() {
        for &j in neighbors {
            let edge = if i < j { (i, j) } else { (j, i) };
            if !edges.contains(&edge) {
                edges.push(edge);
            }
        }
    }
    edges
}

/// Compute Voronoi cell boundaries: for each point, the angular extent
/// of its nearest-neighbor region.
pub fn voronoi_cells(points: &[CirclePoint]) -> Vec<(f64, f64)> {
    if points.is_empty() { return vec![]; }
    let n = points.len();
    if n == 1 { return vec![(0.0, TAU)]; }
    
    let mut sorted: Vec<f64> = points.iter().map(|p| p.angle).collect();
    sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    
    let mut cells = Vec::with_capacity(n);
    for i in 0..n {
        let prev = if i == 0 { sorted[n - 1] - TAU } else { sorted[i - 1] };
        let next = if i == n - 1 { sorted[0] + TAU } else { sorted[i + 1] };
        let lo = (sorted[i] + prev) / 2.0;
        let hi = (sorted[i] + next) / 2.0;
        cells.push((lo, hi));
    }
    cells
}

/// Voronoi cell width (angular extent) for each point.
pub fn cell_widths(points: &[CirclePoint]) -> Vec<f64> {
    voronoi_cells(points).into_iter()
        .map(|(lo, hi)| angular_distance(lo, hi))
        .collect()
}

/// Compute manifold curvature at a point: ratio of actual triple density
/// to uniform density. Values > 1 = denser than uniform, < 1 = sparser.
pub fn curvature(points: &[CirclePoint], index: usize) -> f64 {
    if points.is_empty() || index >= points.len() { return 1.0; }
    let widths = cell_widths(points);
    let avg_width = TAU / points.len() as f64;
    if avg_width == 0.0 { return 1.0; }
    widths[index] / avg_width
}

/// Generate circle points from Pythagorean triples.
pub fn generate_circle_points(max_c: i64) -> Vec<CirclePoint> {
    let mut points = Vec::new();
    let max_m = ((max_c as f64) / 1.41421356) as i64 + 1;
    
    for m in 2..=max_m {
        for n in 1..m {
            if (m + n) % 2 == 0 { continue; }
            if gcd(m, n) != 1 { continue; }
            let a = m * m - n * n;
            let b = 2 * m * n;
            let c = m * m + n * n;
            if c > max_c { break; }
            for &sa in &[1i64, -1] {
                for &sb in &[1i64, -1] {
                    let ang1 = ((sa * a) as f64).atan2((sb * b) as f64);
                    points.push(CirclePoint::new(ang1, sa * a, sb * b, c));
                    let ang2 = ((sa * b) as f64).atan2((sb * a) as f64);
                    points.push(CirclePoint::new(ang2, sa * b, sb * a, c));
                }
            }
        }
    }
    points
}

fn gcd(a: i64, b: i64) -> i64 {
    if b == 0 { a.abs() } else { gcd(b, a % b) }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    fn sample_points() -> Vec<CirclePoint> {
        vec![
            CirclePoint::new(0.0, 3, 4, 5),
            CirclePoint::new(1.0, 5, 12, 13),
            CirclePoint::new(2.0, 8, 15, 17),
            CirclePoint::new(3.0, 7, 24, 25),
            CirclePoint::new(4.0, 20, 21, 29),
            CirclePoint::new(5.0, 12, 35, 37),
        ]
    }
    
    #[test]
    fn test_circle_point_xy() {
        let p = CirclePoint::new(0.0, 3, 4, 5);
        let (x, y) = p.xy();
        assert!((x - 1.0).abs() < 1e-10);
        assert!(y.abs() < 1e-10);
    }
    
    #[test]
    fn test_circle_point_is_pythagorean() {
        let p = CirclePoint::new(1.0, 3, 4, 5);
        assert!(p.is_pythagorean());
    }
    
    #[test]
    fn test_knn() {
        let pts = sample_points();
        let neighbors = knn(0.5, &pts, 2);
        assert_eq!(neighbors.len(), 2);
        assert!(neighbors.contains(&0)); // closest to 0.5
    }
    
    #[test]
    fn test_neighborhood_graph() {
        let pts = sample_points();
        let graph = neighborhood_graph(&pts, 2);
        assert_eq!(graph.len(), 6);
        for neighbors in &graph {
            assert_eq!(neighbors.len(), 2);
        }
    }
    
    #[test]
    fn test_triangulate() {
        let pts = sample_points();
        let edges = triangulate(&pts);
        assert!(!edges.is_empty());
        // Each edge should be unique
        let mut sorted_edges: Vec<_> = edges.iter().map(|&(a,b)| if a<b{(a,b)}else{(b,a)}).collect();
        sorted_edges.sort();
        sorted_edges.dedup();
        assert_eq!(sorted_edges.len(), edges.len());
    }
    
    #[test]
    fn test_voronoi_cells() {
        let pts = sample_points();
        let cells = voronoi_cells(&pts);
        assert_eq!(cells.len(), 6);
        for (lo, hi) in &cells {
            assert!(hi > lo);
        }
    }
    
    #[test]
    fn test_cell_widths() {
        let pts = sample_points();
        let widths = cell_widths(&pts);
        assert_eq!(widths.len(), 6);
        for w in &widths {
            assert!(*w > 0.0);
            assert!(*w <= TAU);
        }
    }
    
    #[test]
    fn test_curvature() {
        let pts = sample_points();
        for i in 0..pts.len() {
            let k = curvature(&pts, i);
            assert!(k > 0.0);
        }
    }
    
    #[test]
    fn test_generate_circle_points() {
        let pts = generate_circle_points(100);
        assert!(pts.len() > 20);
        for p in &pts {
            assert!(p.is_pythagorean());
            assert!(p.c <= 100);
        }
    }
    
    #[test]
    fn test_angular_distance() {
        assert!(angular_distance(0.0, 0.0) < 1e-10);
        assert!((angular_distance(0.0, TAU - 0.01) - 0.01).abs() < 1e-10);
    }
}
