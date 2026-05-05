//! # CT Bench — Reproducible Constraint Theory Benchmarks
//!
//! Standardized workloads for snap, holonomy, deadband, and distribution
//! measurement. Anyone with `cargo bench` can reproduce our numbers.

use std::f64::consts::TAU;

/// Benchmark configuration.
#[derive(Debug, Clone)]
pub struct BenchConfig {
    pub max_c: u64,
    pub n_queries: usize,
    pub n_holonomy_steps: usize,
}

impl Default for BenchConfig {
    fn default() -> Self { BenchConfig { max_c: 50_000, n_queries: 100_000, n_holonomy_steps: 10_000 } }
}

impl BenchConfig {
    pub fn quick() -> Self { BenchConfig { max_c: 1_000, n_queries: 10_000, n_holonomy_steps: 1_000 } }
    pub fn full() -> Self { BenchConfig { max_c: 100_000, n_queries: 1_000_000, n_holonomy_steps: 100_000 } }
}

/// Result of a single benchmark run.
#[derive(Debug, Clone)]
pub struct BenchResult {
    pub name: String,
    pub n_queries: usize,
    pub elapsed_ns: u64,
    pub qps: f64,
    pub max_c: u64,
    pub extra: std::collections::HashMap<String, f64>,
}

impl BenchResult {
    pub fn new(name: &str, n: usize, elapsed_ns: u64, max_c: u64) -> Self {
        let qps = if elapsed_ns > 0 { n as f64 / (elapsed_ns as f64 / 1e9) } else { 0.0 };
        BenchResult { name: name.into(), n_queries: n, elapsed_ns, qps, max_c, extra: std::collections::HashMap::new() }
    }
}

/// Angular distance on [0, 2pi).
#[inline]
pub fn angular_dist(a: f64, b: f64) -> f64 {
    let d = (a - b).abs();
    d.min(TAU - d)
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

fn gcd(a: u64, b: u64) -> u64 { if b == 0 { a } else { gcd(b, a % b) } }

/// Brute-force nearest triple. O(n) per query.
pub fn snap_brute(triples: &[(f64, usize)], theta: f64) -> usize {
    let a = ((theta % TAU) + TAU) % TAU;
    let mut best = 0;
    let mut best_d = f64::MAX;
    for (i, &(angle, _)) in triples.iter().enumerate() {
        let d = angular_dist(a, angle);
        if d < best_d { best_d = d; best = i; }
    }
    best
}

/// Build sorted angle array from raw triples.
pub fn build_angle_array(raw: &[(i64, i64, u64)]) -> Vec<(f64, usize)> {
    let mut arr: Vec<(f64, usize)> = raw.iter().enumerate()
        .map(|(i, &(a, b, _))| ((a as f64).atan2(b as f64), i))
        .collect();
    arr.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(std::cmp::Ordering::Equal));
    arr
}

/// Binary search snap. O(log n) per query.
pub fn snap_binary(sorted: &[(f64, usize)], theta: f64) -> usize {
    if sorted.is_empty() { return 0; }
    let a = ((theta % TAU) + TAU) % TAU;
    match sorted.binary_search_by(|(angle, _)| angle.partial_cmp(&a).unwrap_or(std::cmp::Ordering::Equal)) {
        Ok(i) => i,
        Err(0) => 0,
        Err(i) if i >= sorted.len() => {
            let d_last = angular_dist(a, sorted.last().unwrap().0);
            let d_first = angular_dist(a, sorted[0].0);
            if d_last <= d_first { sorted.len() - 1 } else { 0 }
        }
        Err(i) => {
            let d_lo = angular_dist(a, sorted[i - 1].0);
            let d_hi = angular_dist(a, sorted[i].0);
            if d_lo <= d_hi { i - 1 } else { i }
        }
    }
}

/// Run snap benchmark. Returns (binary_search_result, brute_force_result).
pub fn bench_snap(config: &BenchConfig) -> (BenchResult, BenchResult) {
    let raw = generate_triples(config.max_c);
    let sorted = build_angle_array(&raw);
    let step = TAU / config.n_queries as f64;
    
    // Binary search
    let start = std::time::Instant::now();
    let mut sum = 0u64;
    for i in 0..config.n_queries {
        let idx = snap_binary(&sorted, i as f64 * step);
        sum = sum.wrapping_add(idx as u64);
    }
    let bs_elapsed = start.elapsed().as_nanos() as u64;
    std::hint::black_box(sum);
    
    // Brute force
    let start = std::time::Instant::now();
    let mut sum = 0u64;
    for i in 0..config.n_queries {
        let idx = snap_brute(&sorted, i as f64 * step);
        sum = sum.wrapping_add(idx as u64);
    }
    let bf_elapsed = start.elapsed().as_nanos() as u64;
    std::hint::black_box(sum);
    
    let speedup = if bf_elapsed > 0 { bf_elapsed as f64 / bs_elapsed.max(1) as f64 } else { 0.0 };
    
    let mut bs = BenchResult::new("binary_search", config.n_queries, bs_elapsed, config.max_c);
    let mut bf = BenchResult::new("brute_force", config.n_queries, bf_elapsed, config.max_c);
    bs.extra.insert("speedup".into(), speedup);
    bf.extra.insert("speedup".into(), 1.0);
    (bs, bf)
}

/// Verify correctness: binary search vs brute force.
pub fn verify_snap(config: &BenchConfig) -> VerificationReport {
    let raw = generate_triples(config.max_c);
    let sorted = build_angle_array(&raw);
    let step = TAU / config.n_queries as f64;
    let mut agree = 0usize;
    
    for i in 0..config.n_queries {
        let theta = i as f64 * step;
        if snap_binary(&sorted, theta) == snap_brute(&sorted, theta) {
            agree += 1;
        }
    }
    
    VerificationReport {
        n_queries: config.n_queries,
        n_agree: agree,
        n_triples: sorted.len(),
        max_c: config.max_c,
        agreement_rate: agree as f64 / config.n_queries as f64,
    }
}

#[derive(Debug, Clone)]
pub struct VerificationReport {
    pub n_queries: usize,
    pub n_agree: usize,
    pub n_triples: usize,
    pub max_c: u64,
    pub agreement_rate: f64,
}

/// Holonomy measurement: random walk on the sorted angle array.
pub fn bench_holonomy(config: &BenchConfig) -> BenchResult {
    let raw = generate_triples(config.max_c);
    let sorted = build_angle_array(&raw);
    let n = sorted.len();
    if n == 0 { return BenchResult::new("holonomy", 0, 0, config.max_c); }
    
    let start = std::time::Instant::now();
    let mut pos = 0usize;
    let mut max_disp = 0.0f64;
    let mut rng_state: u64 = 42;
    
    for _ in 0..config.n_holonomy_steps {
        rng_state = rng_state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        let step = (rng_state >> 33) as usize % (n / 10).max(1);
        let forward = (rng_state & 1) == 0;
        pos = if forward { (pos + step) % n } else { (pos + n - step) % n };
        
        let disp = angular_dist(sorted[pos].0, sorted[0].0);
        max_disp = max_disp.max(disp);
    }
    let elapsed = start.elapsed().as_nanos() as u64;
    
    let mut result = BenchResult::new("holonomy", config.n_holonomy_steps, elapsed, config.max_c);
    result.extra.insert("max_displacement_rad".into(), max_disp);
    result.extra.insert("n_triples".into(), n as f64);
    result
}

/// Render results as a comparison table.
pub fn format_comparison(results: &[BenchResult]) -> String {
    let mut out = String::new();
    out.push_str("┌───────────────────┬─────────────┬────────────┬───────────┐\n");
    out.push_str("│ Strategy          │ qps         │ ns/query   │ Speedup   │\n");
    out.push_str("├───────────────────┼─────────────┼────────────┼───────────┤\n");
    let base_qps = results.last().map(|r| r.qps).unwrap_or(1.0);
    for r in results {
        let ns = if r.n_queries > 0 { r.elapsed_ns as f64 / r.n_queries as f64 } else { 0.0 };
        let speedup = r.extra.get("speedup").copied().unwrap_or(r.qps / base_qps.max(1.0));
        out.push_str(&format!("│ {:<17} │ {:>11.0} │ {:>10.0} │ {:>7.1}x   │\n", r.name, r.qps, ns, speedup));
    }
    out.push_str("└───────────────────┴─────────────┴────────────┴───────────┘\n");
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_generate_triples() {
        let t = generate_triples(10);
        assert!(t.contains(&(3, 4, 5)));
    }
    
    #[test]
    fn test_angular_dist() {
        assert!((angular_dist(0.0, 0.0)).abs() < 1e-10);
        assert!((angular_dist(0.0, TAU - 0.01) - 0.01).abs() < 1e-10);
    }
    
    #[test]
    fn test_build_angle_array_sorted() {
        let raw = generate_triples(100);
        let arr = build_angle_array(&raw);
        for i in 1..arr.len() {
            assert!(arr[i].0 >= arr[i - 1].0);
        }
    }
    
    #[test]
    fn test_snap_binary_matches_brute() {
        let raw = generate_triples(5000);
        let sorted = build_angle_array(&raw);
        for i in 0..1000 {
            let theta = i as f64 / 1000.0 * TAU;
            assert_eq!(snap_binary(&sorted, theta), snap_brute(&sorted, theta));
        }
    }
    
    #[test]
    fn test_bench_snap_runs() {
        let config = BenchConfig::quick();
        let (bs, bf) = bench_snap(&config);
        assert!(bs.qps > 0.0);
        assert!(bf.qps > 0.0);
        assert!(bs.qps > bf.qps); // binary should be faster
    }
    
    #[test]
    fn test_verify_100_percent() {
        let config = BenchConfig { max_c: 5000, n_queries: 10000, ..Default::default() };
        let report = verify_snap(&config);
        assert_eq!(report.agreement_rate, 1.0);
    }
    
    #[test]
    fn test_holonomy_runs() {
        let config = BenchConfig::quick();
        let result = bench_holonomy(&config);
        assert!(result.qps > 0.0);
        let disp = result.extra.get("max_displacement_rad").copied().unwrap_or(999.0);
        assert!(disp < TAU); // displacement should be less than full circle
    }
    
    #[test]
    fn test_format_comparison() {
        let results = vec![
            BenchResult::new("binary", 1000, 100_000, 1000),
            BenchResult::new("brute", 1000, 1_000_000, 1000),
        ];
        let table = format_comparison(&results);
        assert!(table.contains("binary"));
        assert!(table.contains("brute"));
    }
}
