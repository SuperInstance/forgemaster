use std::collections::BTreeSet;
use std::time::Instant;

#[derive(Clone)]
struct Triple {
    a: u64,
    b: u64,
    c: u64,
    angle: f64, // atan2(b, a) for unit circle position
}

fn generate_triples(max_c: u64) -> Vec<Triple> {
    let mut set = BTreeSet::new();
    let m_max = (max_c as f64).sqrt() as u64 + 2;
    for m in 2..m_max {
        for n in 1..m {
            if (m - n) % 2 == 1 && gcd(m, n) == 1 {
                let a = m * m - n * n;
                let b = 2 * m * n;
                let c = m * m + n * n;
                if c <= max_c {
                    set.insert((a, b, c));
                    set.insert((b, a, c));
                }
            }
        }
    }
    set.into_iter()
        .map(|(a, b, c)| {
            let angle = ((b as f64).atan2(a as f64) + std::f64::consts::TAU) % std::f64::consts::TAU;
            Triple { a, b, c, angle }
        })
        .collect()
}

fn gcd(a: u64, b: u64) -> u64 {
    let (mut a, mut b) = (a, b);
    while b != 0 {
        let t = b;
        b = a % b;
        a = t;
    }
    a
}

fn brute_snap(angle: f64, triples: &[Triple]) -> usize {
    let mut best = 0usize;
    let mut best_dist = f64::MAX;
    for (i, t) in triples.iter().enumerate() {
        let d = (angle - t.angle).abs().min(std::f64::consts::TAU - (angle - t.angle).abs());
        if d < best_dist {
            best_dist = d;
            best = i;
        }
    }
    best
}

fn bin_snap(angle: f64, triples: &[Triple]) -> usize {
    match triples.binary_search_by(|t| t.angle.partial_cmp(&angle).unwrap()) {
        Ok(i) => i,
        Err(i) => {
            let n = triples.len();
            let lo = if i > 0 { i - 1 } else { n - 1 };
            let hi = if i < n { i } else { 0 };
            let d_lo = (angle - triples[lo].angle).abs().min(std::f64::consts::TAU - (angle - triples[lo].angle).abs());
            let d_hi = (angle - triples[hi].angle).abs().min(std::f64::consts::TAU - (angle - triples[hi].angle).abs());
            if d_lo < d_hi { lo } else { hi }
        }
    }
}

fn main() {
    println!("=== Constraint Theory Rust Benchmark ===\n");
    println!("{:<10} {:>8} {:>16} {:>16} {:>8}", "max_c", "triples", "brute (qps)", "binary (qps)", "speedup");
    println!("{}", "-".repeat(62));

    let iters = 100_000u64;
    for &max_c in &[100u64, 1000, 10000, 50000] {
        let mut triples = generate_triples(max_c);
        triples.sort_by(|a, b| a.angle.partial_cmp(&b.angle).unwrap());
        let n = triples.len();

        let mut rng_state: u64 = 42;
        let queries: Vec<f64> = (0..iters)
            .map(|_| {
                rng_state = rng_state.wrapping_mul(6364136223846793005).wrapping_add(1);
                (rng_state >> 33) as f64 / u32::MAX as f64 * std::f64::consts::TAU
            })
            .collect();

        let t0 = Instant::now();
        let mut brute_sum = 0usize;
        for &q in &queries { brute_sum = brute_sum.wrapping_add(brute_snap(q, &triples)); }
        let brute_t = t0.elapsed().as_secs_f64();

        let t0 = Instant::now();
        let mut bin_sum = 0usize;
        for &q in &queries { bin_sum = bin_sum.wrapping_add(bin_snap(q, &triples)); }
        let bin_t = t0.elapsed().as_secs_f64();
        // Prevent optimization
        if brute_sum == usize::MAX { println!("impossible"); }
        if bin_sum == usize::MAX { println!("impossible"); }

        let brute_qps = iters as f64 / brute_t;
        let bin_qps = iters as f64 / bin_t;
        let speedup = brute_t / bin_t;
        println!("{:<10} {:>8} {:>16.0} {:>16.0} {:>7.1}x", max_c, n, brute_qps, bin_qps, speedup);
    }

    // Holonomy measurement
    println!("\n=== Holonomy: 1000-step random walk ===");
    let triples = generate_triples(10000);
    let n = triples.len();
    let mut angle = 0.0_f64;
    let mut rng_state: u64 = 42;
    for _ in 0..1000 {
        rng_state = rng_state.wrapping_mul(6364136223846793005).wrapping_add(1);
        let delta = ((rng_state >> 33) as f64 / u32::MAX as f64 - 0.5) * 0.2;
        angle = (angle + delta + std::f64::consts::TAU) % std::f64::consts::TAU;
        // snap to nearest triple
        let best = triples.iter().min_by(|a, b| {
            let da = (angle - a.angle).abs().min(std::f64::consts::TAU - (angle - a.angle).abs());
            let db = (angle - b.angle).abs().min(std::f64::consts::TAU - (angle - b.angle).abs());
            da.partial_cmp(&db).unwrap()
        }).unwrap();
        angle = best.angle;
    }
    println!("After 1000 steps on {} triples: final angle = {:.6} rad", n, angle);

    // Float drift
    println!("\n=== Float drift: 1M multiply/divide ===");
    let mut val: f64 = 1.0;
    for _ in 0..1_000_000 {
        val *= 1.0000001;
        val /= 1.0000001;
    }
    println!("After 1M mul/div by 1.0000001: error = {:.2e}", (val - 1.0).abs());
}
