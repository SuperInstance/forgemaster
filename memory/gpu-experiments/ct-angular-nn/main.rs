//! Angular Nearest-Neighbor Search Benchmark v0.2
//! Full-circle Pythagorean manifold (all 8 octants)
//! Compares: binary search, bucket lookup, interpolation search, brute force

use std::f64::consts::PI;
use std::hint::black_box;
use std::time::Instant;

type Triple = (i64, i64, u64);

fn generate_triples_full(max_c: u64) -> Vec<Triple> {
    let mut base = Vec::new();
    let max_m = ((max_c as f64 / 2.0).sqrt()) as u64 + 1;
    for m in 1..=max_m {
        let m2 = m * m;
        if m2 * 2 > max_c * max_c { break; }
        let max_n = m.min(((max_c as f64 - m2 as f64).sqrt()) as u64);
        for n in (1..=max_n).filter(|n| (m + n) % 2 == 1 && gcd(m, *n) == 1) {
            let a = m2 - n * n;
            let b = 2 * m * n;
            let c = m2 + n * n;
            if c <= max_c { base.push((a as i64, b as i64, c)); }
        }
    }
    let mut all = Vec::with_capacity(base.len() * 8);
    for &(a, b, c) in &base {
        all.push((a, b, c)); all.push((b, a, c));
        all.push((-a, b, c)); all.push((-b, a, c));
        all.push((-a, -b, c)); all.push((-b, -a, c));
        all.push((a, -b, c)); all.push((b, -a, c));
    }
    all.sort_by(|a, b| triple_angle(a).partial_cmp(&triple_angle(b)).unwrap());
    all.dedup_by(|a, b| (triple_angle(a) - triple_angle(b)).abs() < 1e-15);
    all
}

fn gcd(a: u64, b: u64) -> u64 { if b == 0 { a } else { gcd(b, a % b) } }

fn triple_angle(t: &Triple) -> f64 {
    let angle = (t.1 as f64).atan2(t.0 as f64);
    if angle < 0.0 { angle + 2.0 * PI } else { angle }
}

fn angle_diff(a: f64, b: f64) -> f64 {
    let d = (a - b).abs();
    d.min(2.0 * PI - d)
}

// Store angles and indices separately to avoid lifetime hell
struct Manifold {
    angles: Vec<f64>,
    triples: Vec<Triple>,
}

impl Manifold {
    fn new(max_c: u64) -> Self {
        let raw = generate_triples_full(max_c);
        let angles: Vec<f64> = raw.iter().map(triple_angle).collect();
        Manifold { angles, triples: raw }
    }

    fn len(&self) -> usize { self.angles.len() }

    fn snap_binary(&self, theta: f64) -> usize {
        let theta = ((theta % (2.0 * PI)) + 2.0 * PI) % (2.0 * PI);
        match self.angles.binary_search_by(|a| a.partial_cmp(&theta).unwrap_or(std::cmp::Ordering::Equal)) {
            Ok(i) => i,
            Err(0) => 0,
            Err(i) if i >= self.angles.len() => self.angles.len() - 1,
            Err(i) => {
                if angle_diff(self.angles[i-1], theta) < angle_diff(self.angles[i], theta) { i-1 } else { i }
            }
        }
    }

    fn snap_brute(&self, theta: f64) -> usize {
        let theta = ((theta % (2.0 * PI)) + 2.0 * PI) % (2.0 * PI);
        let mut best = 0;
        let mut best_d = f64::MAX;
        for (i, a) in self.angles.iter().enumerate() {
            let d = angle_diff(*a, theta);
            if d < best_d { best_d = d; best = i; }
        }
        best
    }
}

struct BucketIndex {
    buckets: Vec<Vec<usize>>,
    n_buckets: usize,
}

impl BucketIndex {
    fn new(angles: &[f64], n_buckets: usize) -> Self {
        let mut buckets = vec![Vec::new(); n_buckets];
        for (i, angle) in angles.iter().enumerate() {
            let b = ((*angle / (2.0 * PI)) * n_buckets as f64) as usize % n_buckets;
            buckets[b].push(i);
        }
        BucketIndex { buckets, n_buckets }
    }

    fn snap(&self, m: &Manifold, theta: f64) -> usize {
        let theta = ((theta % (2.0 * PI)) + 2.0 * PI) % (2.0 * PI);
        let bucket = ((theta / (2.0 * PI)) * self.n_buckets as f64) as usize % self.n_buckets;
        let mut best_idx = 0usize;
        let mut best_dist = f64::MAX;
        for offset in -2i32..=2 {
            let adj = ((bucket as i32 + offset).rem_euclid(self.n_buckets as i32)) as usize;
            for &idx in &self.buckets[adj] {
                let d = angle_diff(m.angles[idx], theta);
                if d < best_dist { best_dist = d; best_idx = idx; }
            }
        }
        best_idx
    }
}

fn snap_interpolation(m: &Manifold, theta: f64) -> usize {
    let theta = ((theta % (2.0 * PI)) + 2.0 * PI) % (2.0 * PI);
    let n = m.angles.len();
    if n == 0 { return 0; }
    let lo_a = m.angles[0];
    let hi_a = m.angles[n - 1];
    let range = hi_a - lo_a;
    if range.abs() < 1e-12 { return 0; }
    let mut lo: usize = 0;
    let mut hi: usize = n - 1;
    for _ in 0..64 {
        if lo >= hi { break; }
        let pos = lo as f64 + (hi as f64 - lo as f64) * (theta - lo_a) / range;
        let pos = pos.max(lo as f64).min(hi as f64) as usize;
        if m.angles[pos] < theta { lo = pos + 1; }
        else if m.angles[pos] > theta { hi = pos.saturating_sub(1); }
        else { return pos; }
    }
    let mut best = lo.min(n - 1);
    let mut best_d = angle_diff(m.angles[best], theta);
    for i in lo..=hi.min(n - 1) {
        let d = angle_diff(m.angles[i], theta);
        if d < best_d { best_d = d; best = i; }
    }
    best
}

fn main() {
    let max_c: u64 = 50000;
    let n_queries: usize = 100_000;
    let n_verify: usize = 1_000;

    println!("╔══════════════════════════════════════════════════════════════╗");
    println!("║  ANGULAR NN SEARCH BENCHMARK v0.2 — Full Circle            ║");
    println!("║  Pythagorean Manifold · 8 Octants · Strategy Comparison    ║");
    println!("╚══════════════════════════════════════════════════════════════╝");

    let t0 = Instant::now();
    let m = Manifold::new(max_c);
    println!("\n  {} full-circle triples (max_c={}) in {:?}", m.len(), max_c, t0.elapsed());
    println!("  Angle range: [{:.6}, {:.6}] rad", m.angles[0], *m.angles.last().unwrap());

    let bucket = BucketIndex::new(&m.angles, 1024);

    // PRNG
    let mut seed: u64 = 42;
    let mut rng = || -> f64 { seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1); seed as f64 / u64::MAX as f64 };
    let queries: Vec<f64> = (0..n_queries).map(|_| rng() * 2.0 * PI).collect();

    // Correctness
    println!("\n  Correctness ({} queries):", n_verify);
    let mut mismatches = 0usize;
    let mut max_err = 0.0f64;
    for &q in &queries[..n_verify] {
        let bf = m.snap_brute(q);
        let bs = m.snap_binary(q);
        let bu = bucket.snap(&m, q);
        let is_val = snap_interpolation(&m, q);
        let bs_err = angle_diff(m.angles[bs], m.angles[bf]);
        let bu_err = angle_diff(m.angles[bu], m.angles[bf]);
        let is_err = angle_diff(m.angles[is_val], m.angles[bf]);
        max_err = max_err.max(bs_err);
        if bs != bf || bu != bf || is_val != bf {
            mismatches += 1;
            if mismatches <= 3 {
                println!("    MISMATCH theta={:.4}: bf={} bs={} bu_err={:.10} is_err={:.10}",
                         q, bf, bs, bu_err, is_err);
            }
        }
    }
    println!("    Mismatches: {}/{}", mismatches, n_verify);
    println!("    Binary search max error: {:.12} rad", max_err);

    // Benchmarks
    println!("\n  Performance ({} queries):", n_queries);

    let t0 = Instant::now();
    let mut s = 0u64;
    for &q in &queries { s += m.triples[m.snap_binary(q)].2; }
    let bs_t = t0.elapsed();
    let bs_qps = n_queries as f64 / bs_t.as_secs_f64();
    black_box(s);

    let t0 = Instant::now();
    let mut s = 0u64;
    for &q in &queries { s += m.triples[bucket.snap(&m, q)].2; }
    let bu_t = t0.elapsed();
    let bu_qps = n_queries as f64 / bu_t.as_secs_f64();
    black_box(s);

    let t0 = Instant::now();
    let mut s = 0u64;
    for &q in &queries { s += m.triples[snap_interpolation(&m, q)].2; }
    let is_t = t0.elapsed();
    let is_qps = n_queries as f64 / is_t.as_secs_f64();
    black_box(s);

    let bf_n = 10_000;
    let t0 = Instant::now();
    let mut s = 0u64;
    for &q in &queries[..bf_n] { s += m.triples[m.snap_brute(q)].2; }
    let bf_t = t0.elapsed();
    let bf_qps = bf_n as f64 / bf_t.as_secs_f64();
    black_box(s);

    println!("\n  ┌─────────────────────┬────────────┬────────────┐");
    println!("  │ Strategy            │ qps        │ Speedup    │");
    println!("  ├─────────────────────┼────────────┼────────────┤");
    println!("  │ Brute force (10K)   │ {:>10.0} │    1.00x   │", bf_qps);
    println!("  │ Interpolation       │ {:>10.0} │ {:>8.1}x   │", is_qps, is_qps/bf_qps);
    println!("  │ Bucket (1024)       │ {:>10.0} │ {:>8.1}x   │", bu_qps, bu_qps/bf_qps);
    println!("  │ Binary search       │ {:>10.0} │ {:>8.1}x   │", bs_qps, bs_qps/bf_qps);
    println!("  └─────────────────────┴────────────┴────────────┘");

    // Distribution
    println!("\n  Distribution (18 bins × 20°):");
    let n_bins = 18;
    let mut bins = vec![0usize; n_bins];
    for angle in &m.angles {
        let b = ((angle / (2.0 * PI)) * n_bins as f64) as usize % n_bins;
        bins[b] += 1;
    }
    let mean_b = m.angles.len() as f64 / n_bins as f64;
    let var: f64 = bins.iter().map(|c| (*c as f64 - mean_b).powi(2)).sum::<f64>() / n_bins as f64;
    let cv = var.sqrt() / mean_b;
    println!("    CV: {:.3} ({})", cv, if cv > 0.3 { "non-uniform" } else { "roughly uniform" });

    for (i, c) in bins.iter().enumerate() {
        let bar_len = (*c as f64 / mean_b * 12.0) as usize;
        let bar: String = "█".repeat(bar_len);
        println!("    {:>5.0}°-{:>5.0}° │{}│ {}", i as f64 * 20.0, (i+1) as f64 * 20.0, bar, c);
    }

    println!("\n════════════════════════════════════════════════════════════");
    println!("  {} triples | {}x speedup | CV={:.2} | mismatches={}",
             m.len(), bs_qps/bf_qps, cv, mismatches);
    println!("════════════════════════════════════════════════════════════");
}
