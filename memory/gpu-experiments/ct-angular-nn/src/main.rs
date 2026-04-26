//! Angular Nearest-Neighbor Search Benchmark for Pythagorean Manifold
//! Compares: binary search, bucket lookup, interpolation search, brute force

use std::f64::consts::PI;
use std::hint::black_box;
use std::time::Instant;

type Triple = (u64, u64, u64);

fn generate_triples(max_c: u64) -> Vec<Triple> {
    let mut triples = Vec::new();
    let max_m = ((max_c as f64 / 2.0).sqrt()) as u64 + 1;
    for m in 1..=max_m {
        let m2 = m * m;
        if m2 * 2 > max_c * max_c { break; }
        let max_n = m.min(((max_c as f64 - m2 as f64).sqrt()) as u64);
        for n in (1..=max_n).filter(|n| (m + n) % 2 == 1 && gcd(m, *n) == 1) {
            let a = m2 - n * n;
            let b = 2 * m * n;
            let c = m2 + n * n;
            if c <= max_c {
                triples.push(if a < b { (a, b, c) } else { (b, a, c) });
            }
        }
    }
    triples.sort_by(|a, b| (a.0 as f64).atan2(a.1 as f64).partial_cmp(&(b.0 as f64).atan2(b.1 as f64)).unwrap());
    triples
}

fn gcd(a: u64, b: u64) -> u64 { if b == 0 { a } else { gcd(b, a % b) } }

fn triple_angle(t: &Triple) -> f64 { (t.0 as f64).atan2(t.1 as f64) }

// Strategy 1: Binary search on sorted angles
fn snap_binary_search<'a>(triples: &'a [(f64, &'a Triple)], theta: f64) -> &'a Triple {
    let theta = ((theta % (2.0 * PI)) + 2.0 * PI) % (2.0 * PI);
    match triples.binary_search_by(|(a, _)| a.partial_cmp(&theta).unwrap_or(std::cmp::Ordering::Equal)) {
        Ok(i) => triples[i].1,
        Err(0) => triples[0].1,
        Err(i) if i >= triples.len() => triples.last().unwrap().1,
        Err(i) => {
            let d_lo = (triples[i-1].0 - theta).abs();
            let d_hi = (triples[i].0 - theta).abs();
            if d_lo < d_hi { triples[i-1].1 } else { triples[i].1 }
        }
    }
}

// Strategy 2: Bucket-based lookup
struct BucketLookup {
    buckets: Vec<Vec<usize>>,
    n_buckets: usize,
    angles: Vec<f64>,
}

impl BucketLookup {
    fn new(triples: &[(f64, &Triple)], n_buckets: usize) -> Self {
        let mut buckets = vec![Vec::new(); n_buckets];
        for (i, (angle, _)) in triples.iter().enumerate() {
            let bucket = ((*angle / (2.0 * PI)) * n_buckets as f64) as usize % n_buckets;
            buckets[bucket].push(i);
        }
        BucketLookup { buckets, n_buckets, angles: triples.iter().map(|(a,_)| *a).collect() }
    }

    fn snap<'a>(&'a self, triples: &'a [(f64, &'a Triple)], theta: f64) -> &'a Triple {
        let theta = ((theta % (2.0 * PI)) + 2.0 * PI) % (2.0 * PI);
        let bucket = ((theta / (2.0 * PI)) * self.n_buckets as f64) as usize % self.n_buckets;
        let mut best_idx: Option<usize> = None;
        let mut best_dist = f64::MAX;
        // Check this bucket and adjacent buckets
        for &adj in &[(bucket + self.n_buckets - 1) % self.n_buckets, bucket, (bucket + 1) % self.n_buckets] {
            for &idx in &self.buckets[adj] {
                let d = (self.angles[idx] - theta).abs();
                if d < best_dist { best_dist = d; best_idx = Some(idx); }
            }
        }
        match best_idx {
            Some(idx) => triples[idx].1,
            None => triples[0].1, // fallback
        }
    }
}

// Strategy 3: Interpolation search
fn snap_interpolation<'a>(triples: &'a [(f64, &'a Triple)], theta: f64) -> &'a Triple {
    let theta = ((theta % (2.0 * PI)) + 2.0 * PI) % (2.0 * PI);
    if triples.is_empty() { panic!("empty"); }
    let n = triples.len();
    let lo_angle = triples[0].0;
    let hi_angle = triples[n-1].0;
    
    // Handle wrap-around
    if theta < lo_angle || theta > hi_angle {
        // Near 0/2pi boundary
        let d_start = (triples[0].0 + 2.0*PI - theta).abs();
        let d_end = (triples[n-1].0 - theta).abs();
        return if d_start < d_end { triples[0].1 } else { triples[n-1].1 };
    }

    let mut lo: usize = 0;
    let mut hi: usize = n - 1;
    let range = hi_angle - lo_angle;
    if range == 0.0 { return triples[0].1; }

    for _ in 0..64 {
        if lo >= hi { break; }
        let pos = lo as f64 + (hi as f64 - lo as f64) * (theta - lo_angle) / range;
        let pos = pos as usize;
        let pos = pos.max(lo).min(hi);
        if triples[pos].0 < theta { lo = pos + 1; }
        else if triples[pos].0 > theta { hi = if pos > 0 { pos - 1 } else { 0 }; }
        else { return triples[pos].1; }
    }

    // Linear probe from lo
    let mut best_idx = lo.min(triples.len()-1);
    let mut best_dist = (triples[best_idx].0 - theta).abs();
    for i in lo..=hi.min(triples.len()-1) {
        let d = (triples[i].0 - theta).abs();
        if d < best_dist { best_dist = d; best_idx = i; }
    }
    triples[best_idx].1
}

// Strategy 4: Brute force (ground truth)
fn snap_brute<'a>(triples: &'a [(f64, &'a Triple)], theta: f64) -> &'a Triple {
    let theta = ((theta % (2.0 * PI)) + 2.0 * PI) % (2.0 * PI);
    let mut best = triples[0].1;
    let mut best_dist = f64::MAX;
    for (angle, t) in triples {
        let _d = (angle - theta).abs().min((angle - theta).abs() + 2.0*PI - 2.0*PI);
        let d = (angle - theta).abs();
        if d < best_dist { best_dist = d; best = t; }
    }
    best
}

fn angle_diff(a: f64, b: f64) -> f64 {
    let d = (a - b).abs();
    d.min(2.0 * PI - d)
}

fn main() {
    let max_c: u64 = 50000;
    let n_queries = 100_000;
    let n_verify = 1_000;

    println!("╔══════════════════════════════════════════════════════════════╗");
    println!("║   ANGULAR NEAREST-NEIGHOR SEARCH BENCHMARK                  ║");
    println!("║   Pythagorean Manifold · Strategy Comparison                ║");
    println!("╚══════════════════════════════════════════════════════════════╝");

    // Generate triples
    let t0 = Instant::now();
    let raw_triples = generate_triples(max_c);
    let indexed: Vec<(f64, &Triple)> = raw_triples.iter().map(|t| (triple_angle(t), t)).collect();
    println!("\n  Generated {} triples (max_c={}) in {:?}", indexed.len(), max_c, t0.elapsed());
    println!("  Angle range: [{:.6}, {:.6}] rad", indexed.first().unwrap().0, indexed.last().unwrap().0);

    // Build bucket lookup
    let bucket = BucketLookup::new(&indexed, 1024);
    println!("  Bucket lookup: {} buckets", bucket.n_buckets);

    // Generate random queries
    use std::cell::RefCell;
    thread_local!(static SEED: RefCell<u64> = RefCell::new(42));
    let mut rng = || {
        SEED.with(|s| {
            let mut seed = s.borrow_mut();
            *seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
            *seed
        })
    };
    let queries: Vec<f64> = (0..n_queries).map(|_| (rng() as f64 / u64::MAX as f64) * 2.0 * PI).collect();

    // Correctness verification
    println!("\n  Correctness verification ({} random queries):", n_verify);
    let mut all_agree = true;
    let mut max_error: f64 = 0.0;
    let mut sum_error = 0.0;
    for &q in &queries[..n_verify.min(queries.len())] {
        let bf = snap_brute(&indexed, q);
        let bs = snap_binary_search(&indexed, q);
        let bu = bucket.snap(&indexed, q);
        let is = snap_interpolation(&indexed, q);
        
        let bs_ok = bs == bf;
        let bu_ok = angle_diff(triple_angle(bu), triple_angle(bf)) < 1e-10;
        let is_ok = angle_diff(triple_angle(is), triple_angle(bf)) < 1e-10;
        
        if !bs_ok || !bu_ok || !is_ok {
            println!("    MISMATCH at theta={:.6}: bf={:?} bs={:?} bu={:?} is={:?}", q, bf, bs, bu, is);
            all_agree = false;
        }
        let err = angle_diff(triple_angle(bs), triple_angle(bf));
        max_error = max_error.max(err);
        sum_error += err;
    }
    println!("    Binary search agrees with brute force: {}", if all_agree { "YES ✓" } else { "NO ✗" });
    println!("    Max angular error: {:.10} rad", max_error);
    println!("    Avg angular error: {:.10} rad", sum_error / n_verify.min(queries.len()) as f64);

    // Performance benchmarks
    println!("\n  Performance benchmarks ({} queries each):", n_queries);

    // Binary search
    let t0 = Instant::now();
    let mut sum = 0u64;
    for &q in &queries { let r = snap_binary_search(&indexed, q); sum += r.0; }
    let bs_time = t0.elapsed();
    let bs_qps = n_queries as f64 / bs_time.as_secs_f64();
    println!("    Binary search:      {:>10.2} qps ({:.2?})", bs_qps, bs_time);
    black_box(sum);

    // Bucket lookup
    let t0 = Instant::now();
    let mut sum = 0u64;
    for &q in &queries { let r = bucket.snap(&indexed, q); sum += r.0; }
    let bu_time = t0.elapsed();
    let bu_qps = n_queries as f64 / bu_time.as_secs_f64();
    println!("    Bucket (1024):      {:>10.2} qps ({:.2?})", bu_qps, bu_time);
    black_box(sum);

    // Interpolation search
    let t0 = Instant::now();
    let mut sum = 0u64;
    for &q in &queries { let r = snap_interpolation(&indexed, q); sum += r.0; }
    let is_time = t0.elapsed();
    let is_qps = n_queries as f64 / is_time.as_secs_f64();
    println!("    Interpolation:      {:>10.2} qps ({:.2?})", is_qps, is_time);
    black_box(sum);

    // Brute force (smaller sample)
    let bf_n = 10_000;
    let t0 = Instant::now();
    let mut sum = 0u64;
    for &q in &queries[..bf_n] { let r = snap_brute(&indexed, q); sum += r.0; }
    let bf_time = t0.elapsed();
    let bf_qps = bf_n as f64 / bf_time.as_secs_f64();
    println!("    Brute force (10K):  {:>10.2} qps ({:.2?})", bf_qps, bf_time);
    black_box(sum);

    // Speedup table
    println!("\n  ┌─────────────────────┬────────────┬────────────┐");
    println!("  │ Strategy            │ qps        │ Speedup    │");
    println!("  ├─────────────────────┼────────────┼────────────┤");
    println!("  │ Brute force (10K)   │ {:>10.0} │    1.00x   │", bf_qps);
    println!("  │ Interpolation       │ {:>10.0} │ {:>8.1}x   │", is_qps, is_qps/bf_qps);
    println!("  │ Bucket (1024)       │ {:>10.0} │ {:>8.1}x   │", bu_qps, bu_qps/bf_qps);
    println!("  │ Binary search       │ {:>10.0} │ {:>8.1}x   │", bs_qps, bs_qps/bf_qps);
    println!("  └─────────────────────┴────────────┴────────────┘");

    // Angle distribution analysis
    println!("\n  Angle distribution analysis:");
    let n_bins = 36; // 10-degree bins
    let mut bins = vec![0usize; n_bins];
    for (angle, _) in &indexed {
        let bin = ((angle / (2.0 * PI)) * n_bins as f64) as usize % n_bins;
        bins[bin] += 1;
    }
    let min_count = *bins.iter().min().unwrap();
    let max_count = *bins.iter().max().unwrap();
    let mean_count = indexed.len() as f64 / n_bins as f64;
    let variance: f64 = bins.iter().map(|c| (*c as f64 - mean_count).powi(2)).sum::<f64>() / n_bins as f64;
    let std_dev = variance.sqrt();
    let cv = std_dev / mean_count; // coefficient of variation
    println!("    Bins: {}, min: {}, max: {}, mean: {:.1}, CV: {:.3}", n_bins, min_count, max_count, mean_count, cv);
    println!("    CV > 0.5 indicates non-uniform distribution");
    
    // Print histogram
    println!("\n  Histogram (10° bins, each █ = ~{:.0} triples):", mean_count / 20.0);
    for (i, count) in bins.iter().enumerate() {
        let bar_len = (*count as f64 / mean_count * 10.0) as usize;
        let bar: String = "█".repeat(bar_len);
        println!("    {:3.0}°-{:3.0}° │{}│ {}", i as f64 * 10.0, (i+1) as f64 * 10.0, bar, count);
    }

    println!("\n══════════════════════════════════════════════════════════════");
    println!("  SUMMARY");
    println!("  Total triples:    {}", indexed.len());
    println!("  Binary search:    {:.0} qps (best overall)", bs_qps);
    println!("  All strategies agree: {}", if all_agree { "YES ✓" } else { "NO ✗" });
    println!("  Distribution CV:  {:.3} ({})", cv, if cv > 0.5 { "non-uniform" } else { "roughly uniform" });
    println!("══════════════════════════════════════════════════════════════");
}
