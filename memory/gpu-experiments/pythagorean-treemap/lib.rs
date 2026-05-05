//! # Pythagorean Treemap
//!
//! Hierarchical treemap visualization of Pythagorean triple density.
//! Maps the angular distribution of triples onto a space-filling tree.

/// A rectangular region in the treemap.
#[derive(Debug, Clone, Copy)]
pub struct Rect {
    pub x: f64,
    pub y: f64,
    pub w: f64,
    pub h: f64,
}

impl Rect {
    pub fn new(x: f64, y: f64, w: f64, h: f64) -> Self {
        Rect { x, y, w, h }
    }
    
    pub fn area(&self) -> f64 {
        self.w * self.h
    }
    
    pub fn split_horizontal(&self, ratio: f64) -> (Rect, Rect) {
        let split = self.w * ratio;
        (
            Rect::new(self.x, self.y, split, self.h),
            Rect::new(self.x + split, self.y, self.w - split, self.h),
        )
    }
    
    pub fn split_vertical(&self, ratio: f64) -> (Rect, Rect) {
        let split = self.h * ratio;
        (
            Rect::new(self.x, self.y, self.w, split),
            Rect::new(self.x, self.y + split, self.w, self.h - split),
        )
    }
}

/// A node in the treemap.
#[derive(Debug, Clone)]
pub struct TreemapNode {
    pub rect: Rect,
    pub value: f64,
    pub label: String,
    pub children: Vec<TreemapNode>,
}

impl TreemapNode {
    pub fn leaf(rect: Rect, value: f64, label: String) -> Self {
        TreemapNode { rect, value, label, children: vec![] }
    }
}

/// Angular density bin for triple distribution.
#[derive(Debug, Clone)]
pub struct DensityBin {
    pub angle_start: f64, // radians
    pub angle_end: f64,
    pub count: usize,
    pub density: f64,     // count / angular_width
}

/// Analyze the angular distribution of Pythagorean triples.
pub fn analyze_density(triples: &[(i64, i64, u64)], n_bins: usize) -> Vec<DensityBin> {
    let two_pi = std::f64::consts::TAU;
    let bin_width = two_pi / n_bins as f64;
    let mut bins = vec![DensityBin { angle_start: 0.0, angle_end: 0.0, count: 0, density: 0.0 }; n_bins];
    
    for (i, bin) in bins.iter_mut().enumerate() {
        bin.angle_start = i as f64 * bin_width;
        bin.angle_end = (i + 1) as f64 * bin_width;
    }
    
    for &(a, b, c) in triples {
        let angle = (a as f64).atan2(b as f64);
        let a = ((angle % two_pi) + two_pi) % two_pi;
        let idx = (a / bin_width) as usize % n_bins;
        bins[idx].count += 1;
    }
    
    for bin in &mut bins {
        bin.density = bin.count as f64 / bin_width;
    }
    
    bins
}

/// Build a squarified treemap from density bins.
/// Uses the squarified treemap algorithm for aspect ratios close to 1.
pub fn build_treemap(bins: &[DensityBin], canvas: Rect) -> TreemapNode {
    let total: f64 = bins.iter().map(|b| b.count as f64).sum();
    if total == 0.0 {
        return TreemapNode { rect: canvas, value: 0.0, label: "empty".into(), children: vec![] };
    }
    
    let mut sorted: Vec<(f64, usize)> = bins.iter().enumerate()
        .map(|(i, b)| (b.count as f64, i))
        .filter(|(v, _)| *v > 0.0)
        .collect();
    sorted.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal));
    
    let children = squarify(&sorted, canvas, total);
    TreemapNode { rect: canvas, value: total, label: "root".into(), children }
}

fn squarify(items: &[(f64, usize)], rect: Rect, total: f64) -> Vec<TreemapNode> {
    if items.is_empty() { return vec![]; }
    
    let mut result = vec![];
    let mut remaining = items.to_vec();
    let mut current_rect = rect;
    
    while !remaining.is_empty() {
        let short_side = current_rect.w.min(current_rect.h);
        if short_side <= 0.0 { break; }
        let mut row: Vec<(f64, usize)> = vec![];
        let mut row_sum = 0.0;
        let remaining_sum: f64 = remaining.iter().map(|(v, _)| *v).sum();
        
        for &(value, idx) in &remaining {
            let test_sum = row_sum + value;
            let test_ratio = if row.is_empty() { f64::INFINITY } else { worst_ratio(&row, test_sum, short_side) };
            let current_ratio = worst_ratio(&row, row_sum, short_side);
            
            if test_ratio <= current_ratio {
                row.push((value, idx));
                row_sum = test_sum;
            } else {
                break;
            }
        }
        
        let row_frac = if row_sum + remaining_sum - row_sum > 0.0 {
            row_sum / (row_sum + remaining_sum - row_sum)
        } else { 1.0 };
        
        let (row_rect, rest_rect) = if current_rect.w <= current_rect.h {
            current_rect.split_vertical(row_frac)
        } else {
            current_rect.split_horizontal(row_frac)
        };
        
        // Lay out items in row along the longer axis of row_rect
        let is_wide = row_rect.w >= row_rect.h;
        let mut offset = if is_wide { row_rect.x } else { row_rect.y };
        let row_len = if is_wide { row_rect.w } else { row_rect.h };
        
        for &(value, idx) in &row {
            let item_frac = value / row_sum;
            let item_len = row_len * item_frac;
            let item_rect = if is_wide {
                Rect::new(offset, row_rect.y, item_len, row_rect.h)
            } else {
                Rect::new(row_rect.x, offset, row_rect.w, item_len)
            };
            let label = format!("bin-{}", idx);
            result.push(TreemapNode::leaf(item_rect, value, label));
            offset += item_len;
        }
        
        remaining = remaining[row.len()..].to_vec();
        current_rect = rest_rect;
    }
    
    result
}

fn layout_row(row: &[(f64, usize)], rect: Rect, total_area: f64) {
    // Layout items proportionally along the longer axis
    if rect.w >= rect.h {
        let mut x = rect.x;
        for &(value, _) in row {
            let frac = value / total_area;
            let w = rect.w * frac;
            x += w;
        }
    }
}

fn worst_ratio(row: &[(f64, usize)], total_area: f64, short_side: f64) -> f64 {
    if row.is_empty() || total_area == 0.0 { return f64::INFINITY; }
    let s2 = short_side * short_side;
    let row_area = total_area;
    let max_val = row.iter().map(|(v, _)| *v).fold(0.0, f64::max);
    let min_val = row.iter().map(|(v, _)| *v).fold(f64::INFINITY, f64::min);
    
    let r1 = (s2 * max_val) / (row_area * row_area);
    let r2 = (row_area * row_area) / (s2 * min_val);
    r1.max(r2)
}

/// Generate all Pythagorean triples up to max_c (all 8 octants).
pub fn generate_triples(max_c: u64) -> Vec<(i64, i64, u64)> {
    let mut triples = Vec::new();
    let max_m = ((max_c as f64).sqrt() / std::f64::consts::SQRT_2) as u64 + 1;
    
    for m in 2..=max_m {
        for n in 1..m {
            if (m + n) % 2 == 0 { continue; }
            if gcd(m, n) != 1 { continue; }
            let a = m * m - n * n;
            let b = 2 * m * n;
            let c = m * m + n * n;
            if c > max_c { break; }
            // All 8 sign/reflection octants: (+-a, +-b, c)
            for &sa in &[1i64, -1] {
                for &sb in &[1i64, -1] {
                    triples.push((sa * a as i64, sb * b as i64, c));
                    triples.push((sa * b as i64, sb * a as i64, c));
                }
            }
        }
    }
    triples
}

fn gcd(a: u64, b: u64) -> u64 {
    if b == 0 { a } else { gcd(b, a % b) }
}

/// Render treemap as ASCII art.
pub fn render_ascii(node: &TreemapNode, width: usize, height: usize) -> String {
    let mut grid = vec![vec![' '; width]; height];
    render_node(node, &mut grid, width, height);
    let mut result = String::new();
    for row in &grid {
        result.push_str(&row.iter().collect::<String>());
        result.push('\n');
    }
    result
}

fn render_node(node: &TreemapNode, grid: &mut [Vec<char>], total_w: usize, total_h: usize) {
    // Scale from normalized [0,1] coords to grid coords
    let x0 = (node.rect.x * total_w as f64) as usize;
    let y0 = (node.rect.y * total_h as f64) as usize;
    let x1 = ((node.rect.x + node.rect.w) * total_w as f64).min(total_w as f64) as usize;
    let y1 = ((node.rect.y + node.rect.h) * total_h as f64).min(total_h as f64) as usize;
    
    let ch = if node.children.is_empty() && node.value > 0.0 { '#' } else { ' ' };
    
    for y in y0..y1.min(total_h) {
        for x in x0..x1.min(total_w) {
            grid[y][x] = ch;
        }
    }
    
    // Recurse into children
    for child in &node.children {
        render_node(child, grid, total_w, total_h);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::f64::consts::PI;
    
    #[test]
    fn test_rect_split_horizontal() {
        let r = Rect::new(0.0, 0.0, 100.0, 50.0);
        let (a, b) = r.split_horizontal(0.3);
        assert!((a.w - 30.0).abs() < 0.01);
        assert!((b.w - 70.0).abs() < 0.01);
    }
    
    #[test]
    fn test_rect_split_vertical() {
        let r = Rect::new(0.0, 0.0, 100.0, 50.0);
        let (a, b) = r.split_vertical(0.4);
        assert!((a.h - 20.0).abs() < 0.01);
        assert!((b.h - 30.0).abs() < 0.01);
    }
    
    #[test]
    fn test_generate_triples_basic() {
        let triples = generate_triples(10);
        assert!(triples.len() > 0);
        // (3,4,5) should be present
        assert!(triples.contains(&(3, 4, 5)));
    }
    
    #[test]
    fn test_analyze_density() {
        let triples = generate_triples(100);
        let bins = analyze_density(&triples, 18);
        assert_eq!(bins.len(), 18);
        let total: usize = bins.iter().map(|b| b.count).sum();
        assert_eq!(total, triples.len());
    }
    
    #[test]
    fn test_build_treemap() {
        let triples = generate_triples(100);
        let bins = analyze_density(&triples, 8);
        let canvas = Rect::new(0.0, 0.0, 1.0, 1.0);
        let tree = build_treemap(&bins, canvas);
        assert!(tree.value > 0.0);
        assert!(!tree.children.is_empty());
    }
    
    #[test]
    fn test_build_treemap_empty() {
        let bins = vec![DensityBin { angle_start: 0.0, angle_end: PI/4.0, count: 0, density: 0.0 }; 4];
        let canvas = Rect::new(0.0, 0.0, 1.0, 1.0);
        let tree = build_treemap(&bins, canvas);
        assert_eq!(tree.value, 0.0);
    }
    
    #[test]
    fn test_render_ascii() {
        let triples = generate_triples(50);
        let bins = analyze_density(&triples, 8);
        let canvas = Rect::new(0.0, 0.0, 1.0, 1.0);
        let tree = build_treemap(&bins, canvas);
        let ascii = render_ascii(&tree, 20, 10);
        assert!(ascii.contains('#'));
        assert!(ascii.len() > 0);
    }
    
    #[test]
    fn test_density_cv_low() {
        // Full-circle triples should be roughly uniform
        let triples = generate_triples(5000);
        let bins = analyze_density(&triples, 36);
        let mean = bins.iter().map(|b| b.count as f64).sum::<f64>() / bins.len() as f64;
        let var: f64 = bins.iter().map(|b| (b.count as f64 - mean).powi(2)).sum::<f64>() / bins.len() as f64;
        let cv = var.sqrt() / mean;
        assert!(cv < 0.3, "CV should be < 0.3 for full-circle, got {}", cv);
    }
}
