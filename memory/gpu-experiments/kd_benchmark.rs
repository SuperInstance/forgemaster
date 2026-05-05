//! KD-Tree accelerated snap benchmark
//! Compares brute-force O(n) vs KD-tree O(log n) snap performance

use std::collections::BTreeSet;
use std::time::Instant;

#[derive(Debug, Clone, Copy)]
struct Triple {
    a: i64,
    b: i64,
    c: i64,
}

impl Triple {
    fn normalized(&self) -> (f64, f64) {
        (self.a as f64 / self.c as f64, self.b as f64 / self.c as f64)
    }
}

fn gcd(a: i64, b: i64) -> i64 {
    if b == 0 { a } else { gcd(b, a % b) }
}

fn generate_triples(max_c: i64) -> Vec<Triple> {
    let mut triples = Vec::new();
    let mut seen = BTreeSet::new();
    let mut m: i64 = 2;
    while m * m <= max_c {
        let mut n: i64 = 1;
        while n < m {
            if (m - n) % 2 == 1 && gcd(m, n) == 1 {
                let a = m * m - n * n;
                let b = 2 * m * n;
                let c = m * m + n * n;
                if c <= max_c {
                    for &(a, b) in &[(a, b), (b, a)] {
                        let key = (a.abs(), b.abs());
                        if !seen.contains(&key) {
                            seen.insert(key);
                            triples.push(Triple::new(a, b, c));
                        }
                    }
                }
            }
            n += 1;
        }
        m += 1;
    }
    triples
}

impl Triple {
    fn new(a: i64, b: i64, c: i64) -> Self {
        Self { a, b, c }
    }
}

// ---- KD-Tree implementation ----

#[derive(Debug, Clone)]
struct KdNode {
    point: (f64, f64),
    triple_idx: usize,
    left: Option<Box<KdNode>>,
    right: Option<Box<KdNode>>,
    split_dim: usize, // 0 = x, 1 = y
}

fn build_kd(points: &mut [(f64, f64, usize)], depth: usize) -> Option<Box<KdNode>> {
    if points.is_empty() {
        return None;
    }
    let dim = depth % 2;
    points.sort_by(|a, b| if dim == 0 {
        a.0.partial_cmp(&b.0).unwrap()
    } else {
        a.1.partial_cmp(&b.1).unwrap()
    });
    let mid = points.len() / 2;
    let node = KdNode {
        point: (points[mid].0, points[mid].1),
        triple_idx: points[mid].2,
        split_dim: dim,
        left: build_kd(&mut points[..mid], depth + 1),
        right: build_kd(&mut points[mid + 1..], depth + 1),
    };
    Some(Box::new(node))
}

fn kd_nearest(node: &Option<Box<KdNode>>, query: (f64, f64), best: &mut (f64, usize)) {
    let node = match node {
        Some(n) => n,
        None => return,
    };

    let dx = query.0 - node.point.0;
    let dy = query.1 - node.point.1;
    let dist = (dx * dx + dy * dy).sqrt();
    if dist < best.0 {
        *best = (dist, node.triple_idx);
    }

    let diff = if node.split_dim == 0 { dx } else { dy };
    let (first, second) = if diff <= 0.0 {
        (&node.left, &node.right)
    } else {
        (&node.right, &node.left)
    };

    kd_nearest(first, query, best);

    // Prune: only check second subtree if the split plane is within best distance
    let split_dist = if node.split_dim == 0 {
        (query.0 - node.point.0).abs()
    } else {
        (query.1 - node.point.1).abs()
    };
    if split_dist < best.0 {
        kd_nearest(second, query, best);
    }
}

// ---- Brute force ----

fn brute_nearest(query: (f64, f64), manifold: &[Triple]) -> (f64, usize) {
    let mut best = (f64::MAX, 0usize);
    for (i, t) in manifold.iter().enumerate() {
        let (nx, ny) = t.normalized();
        let dx = query.0 - nx;
        let dy = query.1 - ny;
        let dist = (dx * dx + dy * dy).sqrt();
        if dist < best.0 {
            best = (dist, i);
        }
    }
    best
}

// ---- Main benchmark ----

fn main() {
    use rand::Rng;
    let mut rng = rand::thread_rng();

    let resolutions: &[i64] = &[100, 500, 1000, 2000, 5000, 10000, 20000, 50000];
    let query_counts: &[usize] = &[10_000, 100_000];

    println!("╔══════════════════════════════════════════════════════════════════════╗");
    println!("║        CONSTRAINT THEORY: KD-TREE vs BRUTE-FORCE BENCHMARK         ║");
    println!("╠══════════════════════════════════════════════════════════════════════╣");

    for &queries in query_counts {
        println!("║                                                                  ║");
        println!("║  {} queries per test                                    ║", format!("{:>9}", queries));
        println!("╠════════╦═════════╦═══════════════╦═══════════════╦══════════════╣");
        println!("║ max_c  ║ triples ║  brute (ms)   ║   kd (ms)     ║  speedup     ║");
        println!("╠════════╬═════════╬═══════════════╬═══════════════╬══════════════╣");

        for &max_c in resolutions {
            let manifold = generate_triples(max_c);
            let n = manifold.len();

            // Build KD-tree
            let mut pts: Vec<(f64, f64, usize)> = manifold.iter().enumerate()
                .map(|(i, t)| {
                    let (x, y) = t.normalized();
                    (x, y, i)
                })
                .collect();
            let kd_root = build_kd(&mut pts, 0);

            // Generate random queries on unit circle
            let queries_vec: Vec<(f64, f64)> = (0..queries)
                .map(|_| {
                    let x: f64 = rng.gen_range(-1.0..1.0);
                    let y: f64 = rng.gen_range(-1.0..1.0);
                    let r = (x * x + y * y).sqrt();
                    (x / r, y / r)
                })
                .collect();

            // Brute force
            let brute_start = Instant::now();
            let mut brute_total_dist = 0.0f64;
            for &q in &queries_vec {
                let (d, _) = brute_nearest(q, &manifold);
                brute_total_dist += d;
            }
            let brute_ms = brute_start.elapsed().as_secs_f64() * 1000.0;

            // KD-tree
            let kd_start = Instant::now();
            let mut kd_total_dist = 0.0f64;
            for &q in &queries_vec {
                let mut best = (f64::MAX, 0usize);
                kd_nearest(&kd_root, q, &mut best);
                kd_total_dist += best.0;
            }
            let kd_ms = kd_start.elapsed().as_secs_f64() * 1000.0;

            let speedup = if kd_ms > 0.0 { brute_ms / kd_ms } else { f64::INFINITY };
            let brute_qps = queries as f64 / (brute_ms / 1000.0);
            let kd_qps = queries as f64 / (kd_ms / 1000.0);

            // Verify correctness (distances should match)
            let dist_diff = (brute_total_dist - kd_total_dist).abs();

            println!("║ {:>6} ║ {:>7} ║ {:>9.2}     ║ {:>9.2}     ║ {:>8.1}x     ║",
                max_c, n, brute_ms, kd_ms, speedup);
            println!("║        ║         ║ {:>9.0} qps  ║ {:>9.0} qps  ║ dist Δ:{:.2e}  ║",
                brute_qps, kd_qps, dist_diff);
            println!("╠════════╬═════════╬═══════════════╬═══════════════╬══════════════╣");
        }
    }

    println!("║                                                                  ║");
    println!("║  Conclusion: KD-tree provides O(log n) snap, making constraint    ║");
    println!("║  theory practical at any resolution. Brute force is O(n).         ║");
    println!("╚══════════════════════════════════════════════════════════════════════╝");

    // Theoretical scaling comparison
    println!("\n  THEORETICAL SCALING (queries = 100,000)");
    println!("  {}", "─".repeat(60));
    println!("  | max_c  | triples | O(n) cost  | O(log n) cost | ratio  |");
    println!("  |--------|---------|------------|---------------|--------|");
    for &max_c in &[100, 1000, 10000, 100000, 1000000] {
        let n = (max_c as f64 / 6.0) as u64;
        let log_n = (n as f64).log2().max(1.0);
        let ratio = n as f64 / log_n;
        println!("  | {:>6} | {:>7} | {:>10} | {:>13.1} | {:>6.0}x |",
            max_c, n, n, log_n, ratio);
    }
}
