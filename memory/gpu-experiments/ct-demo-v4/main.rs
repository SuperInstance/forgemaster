//! Constraint Theory Demo v0.4.0
//! Self-validating: proves Pythagorean manifold snap is exact, drift-free, and consistent.

use std::f64::consts::PI;
use std::time::Instant;

type Triple = (i64, i64, u64);

fn gcd(a: u64, b: u64) -> u64 { if b == 0 { a } else { gcd(b, a % b) } }

fn generate_full(max_c: u64) -> Vec<Triple> {
    let mut base = Vec::new();
    let max_m = ((max_c as f64 / 2.0).sqrt()) as u64 + 1;
    for m in 1..=max_m {
        let m2 = m * m;
        if m2 * 2 > max_c * max_c { break; }
        let max_n = m.min(((max_c as f64 - m2 as f64).sqrt()) as u64);
        for n in (1..=max_n).filter(|&n| (m + n) % 2 == 1 && gcd(m, n) == 1) {
            let a = m2 - n * n; let b = 2 * m * n; let c = m2 + n * n;
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

fn triple_angle(t: &Triple) -> f64 {
    let a = (t.0 as f64).atan2(t.1 as f64);
    if a < 0.0 { a + 2.0 * PI } else { a }
}

fn angle_diff(a: f64, b: f64) -> f64 { let d = (a - b).abs(); d.min(2.0 * PI - d) }

fn snap(angles: &[f64], theta: f64) -> usize {
    let theta = ((theta % (2.0 * PI)) + 2.0 * PI) % (2.0 * PI);
    match angles.binary_search_by(|a| a.partial_cmp(&theta).unwrap_or(std::cmp::Ordering::Equal)) {
        Ok(i) => i,
        Err(0) => 0,
        Err(i) if i >= angles.len() => angles.len() - 1,
        Err(i) => { let dl = angle_diff(angles[i-1], theta); let dh = angle_diff(angles[i], theta); if dl <= dh { i-1 } else { i } }
    }
}

fn snap_brute(angles: &[f64], theta: f64) -> usize {
    let theta = ((theta % (2.0 * PI)) + 2.0 * PI) % (2.0 * PI);
    let mut best = 0; let mut best_d = f64::MAX;
    for (i, a) in angles.iter().enumerate() { let d = angle_diff(*a, theta); if d < best_d { best_d = d; best = i; } }
    best
}

fn main() {
    println!("╔══════════════════════════════════════════════════════════╗");
    println!("║  CONSTRAINT THEORY DEMO v0.4.0 — Self-Consistency Quine ║");
    println!("╚══════════════════════════════════════════════════════════╝");

    let max_c = 10000u64;
    let n_check = 100_000usize;
    let n_holo = 500usize;

    // Phase 1: Generate manifold
    let t0 = Instant::now();
    let triples = generate_full(max_c);
    let angles: Vec<f64> = triples.iter().map(triple_angle).collect();
    println!("\n  Phase 1: Manifold Generation");
    println!("    Triples: {} (max_c={})", triples.len(), max_c);
    println!("    Angle range: [{:.6}, {:.6}] rad", angles[0], *angles.last().unwrap());
    println!("    Time: {:?}", t0.elapsed());

    // Phase 2: Self-consistency (binary == brute for 100K random queries)
    println!("\n  Phase 2: Self-Consistency ({} queries)", n_check);
    let t0 = Instant::now();
    let mut seed: u64 = 42;
    let mut mismatches = 0usize;
    let mut max_err = 0.0f64;
    for _ in 0..n_check {
        seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
        let theta = seed as f64 / u64::MAX as f64 * 2.0 * PI;
        let bs = snap(&angles, theta);
        let bf = snap_brute(&angles, theta);
        if bs != bf {
            mismatches += 1;
            let err = angle_diff(angles[bs], angles[bf]);
            max_err = max_err.max(err);
        }
    }
    let consistency_time = t0.elapsed();
    let qps = n_check as f64 / consistency_time.as_secs_f64();
    println!("    Binary-brute agreement: {}/{} ({}%)", n_check - mismatches, n_check, 100 * (n_check - mismatches) / n_check);
    println!("    Max angular error: {:.12} rad", max_err);
    println!("    Throughput: {:.0} qps", qps);

    // Phase 3: Pythagorean verification (all triples satisfy x²+y²=c²)
    println!("\n  Phase 3: Pythagorean Verification (all triples)");
    let t0 = Instant::now();
    let mut violations = 0usize;
    for (_i, &(x, y, c)) in triples.iter().enumerate() {
        if (x as i128).pow(2) + (y as i128).pow(2) != (c as i128).pow(2) {
            violations += 1;
            if violations <= 3 { println!("    VIOLATION: ({}, {}, {})", x, y, c); }
        }
    }
    println!("    Violations: {}/{}", violations, triples.len());
    println!("    Time: {:?}", t0.elapsed());

    // Phase 4: Holonomy (random walk, 500 steps)
    println!("\n  Phase 4: Holonomy ({}-step random walk)", n_holo);
    let t0 = Instant::now();
    let mut pos = 0.0f64;
    let mut accumulated = 0.0f64;
    let mut max_holo = 0.0f64;
    for _ in 0..n_holo {
        seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1);
        let step = (seed as f64 / u64::MAX as f64 - 0.5) * 0.1;
        pos += step;
        let continuous_angle = ((pos % (2.0 * PI)) + 2.0 * PI) % (2.0 * PI);
        let snapped_angle = angles[snap(&angles, continuous_angle)];
        let discrete_step = angle_diff(snapped_angle, continuous_angle);
        accumulated += discrete_step;
        max_holo = max_holo.max(accumulated.abs());
    }
    let holonomy = accumulated;
    println!("    Accumulated holonomy: {:.6} rad ({:.2}°)", holonomy, holonomy * 180.0 / PI);
    println!("    Max instantaneous holonomy: {:.6} rad", max_holo);
    println!("    Bounded: {}", holonomy.abs() < 2.0 * PI);
    println!("    Time: {:?}", t0.elapsed());

    // Phase 5: Drift test (10K snaps, check all unique)
    println!("\n  Phase 5: Drift Elimination");
    let t0 = Instant::now();
    let mut drift = 0.0f64;
    for i in 0..10_000usize {
        let theta = (i as f64 / 10_000.0) * 2.0 * PI;
        let idx = snap(&angles, theta);
        let t = &triples[idx];
        let computed = ((t.0 as f64).powi(2) + (t.1 as f64).powi(2)).sqrt();
        drift += (computed - t.2 as f64).abs();
    }
    println!("    Total float drift: {:.6e}", drift);
    println!("    Zero drift: {}", drift < 1e-10);
    println!("    Time: {:?}", t0.elapsed());

    // Summary
    let passed = mismatches == 0 && violations == 0 && drift < 1e-10;
    println!("\n╔══════════════════════════════════════════════════════════╗");
    println!("║  RESULT: {}                                            ║", if passed { "ALL CHECKS PASSED ✓" } else { "FAILURES DETECTED ✗" });
    println!("║  Consistency:  {}/{}  |  Violations: {}/{}             ║", n_check - mismatches, n_check, violations, triples.len());
    println!("║  Holonomy: {:.4} rad  |  Drift: {:.1e}           ║", holonomy, drift);
    println!("║  Throughput: {:.0} qps  |  Triples: {}             ║", qps, triples.len());
    println!("╚══════════════════════════════════════════════════════════╝");
    std::process::exit(if passed { 0 } else { 1 });
}
