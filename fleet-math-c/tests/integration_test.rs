//! Integration test for fleet-math-c Rust FFI bindings.
//!
//! Verifies snap results, holonomy consistency, and batch operations.

use fleet_math_c::*;

fn rand_f32(seed: &mut u32, lo: f32, hi: f32) -> f32 {
    *seed ^= *seed << 13;
    *seed ^= *seed >> 17;
    *seed ^= *seed << 5;
    lo + (hi - lo) * (*seed % 10000) as f32 / 10000.0
}

#[test]
fn test_snap_100_points() {
    let mut seed = 42u32;
    for i in 0..100 {
        let x = rand_f32(&mut seed, -5.0, 5.0);
        let y = rand_f32(&mut seed, -5.0, 5.0);
        let r = snap(x, y);
        assert!(r.error >= 0.0, "Point {}: error must be non-negative, got {}", i, r.error);
        assert!(r.error < 1.0, "Point {}: error too large: {}", i, r.error);
        assert!(r.chamber <= 5, "Point {}: chamber must be 0-5, got {}", i, r.chamber);
    }
}

#[test]
fn test_batch_snap_matches_individual() {
    let mut seed = 99u32;
    let n = 50;
    let mut points = Vec::with_capacity(n * 2);
    for _ in 0..n {
        points.push(rand_f32(&mut seed, -5.0, 5.0));
        points.push(rand_f32(&mut seed, -5.0, 5.0));
    }

    let batch_results = batch_snap(&points);

    // Compare batch vs individual
    for i in 0..n {
        let individual = snap(points[2 * i], points[2 * i + 1]);
        let batch = &batch_results[i];
        assert!(
            (individual.error - batch.error).abs() < 1e-6,
            "Point {}: batch error {} != individual error {}",
            i, batch.error, individual.error
        );
        assert_eq!(individual.chamber, batch.chamber, "Point {} chamber mismatch", i);
        assert_eq!(individual.dodecet, batch.dodecet, "Point {} dodecet mismatch", i);
    }
}

#[test]
fn test_holonomy_4cycle() {
    let mut seed = 77u32;
    let mut all_results = Vec::new();

    // Generate 2500 groups of 4 = 10000 results total
    for _ in 0..2500 {
        let mut group = [snap(0.0, 0.0); 4];
        for g in group.iter_mut() {
            let x = rand_f32(&mut seed, -3.0, 3.0);
            let y = rand_f32(&mut seed, -3.0, 3.0);
            *g = snap(x, y);
        }
        all_results.push(group);
    }

    let mut consistent = 0usize;
    let mut total_holonomy = 0.0f64;
    let mut max_holonomy = 0.0f32;

    for group in &all_results {
        let h = holonomy_4cycle(group);
        assert!(h >= 0.0 && h <= 1.0, "Holonomy out of range: {}", h);
        total_holonomy += h as f64;
        if h > max_holonomy { max_holonomy = h; }
        if h < 0.1 { consistent += 1; }
    }

    let avg = total_holonomy / all_results.len() as f64;
    eprintln!(
        "Holonomy stats: avg={:.6}, max={:.6}, consistent(<0.1)={}/{}",
        avg, max_holonomy, consistent, all_results.len()
    );
    // At least some should be consistent
    assert!(consistent > 0, "Expected some consistent holonomy cycles");
}

#[test]
fn test_batch_holonomy() {
    let mut seed = 33u32;
    let n_cycles = 2500; // 2500 cycles * 4 = 10000 results
    let mut points = Vec::new();
    for _ in 0..(n_cycles * 4) {
        points.push(rand_f32(&mut seed, -3.0, 3.0));
        points.push(rand_f32(&mut seed, -3.0, 3.0));
    }

    let snap_results = batch_snap(&points);
    assert_eq!(snap_results.len(), n_cycles * 4);

    let holonomy = batch_holonomy(&snap_results);
    assert_eq!(holonomy.len(), n_cycles);

    for (i, &h) in holonomy.iter().enumerate() {
        assert!(h >= 0.0 && h <= 1.0, "Cycle {}: holonomy out of range: {}", i, h);
    }

    let avg = holonomy.iter().map(|&h| h as f64).sum::<f64>() / holonomy.len() as f64;
    let consistent = holonomy.iter().filter(|&&h| h < 0.1).count();
    eprintln!(
        "Batch holonomy: avg={:.6}, consistent(<0.1)={}/{}",
        avg, consistent, n_cycles
    );
}

#[test]
fn test_10000_random_snaps() {
    let mut seed = 2024u32;
    let total = 10_000;
    let mut max_error = 0.0f32;
    let mut sum_error = 0.0f64;

    for i in 0..total {
        let x = rand_f32(&mut seed, -10.0, 10.0);
        let y = rand_f32(&mut seed, -10.0, 10.0);
        let r = snap(x, y);
        assert!(r.error >= 0.0, "Snap {}: negative error", i);
        assert!(r.chamber <= 5, "Snap {}: invalid chamber {}", i, r.chamber);
        sum_error += r.error as f64;
        if r.error > max_error { max_error = r.error; }
    }

    let avg_error = sum_error / total as f64;
    eprintln!("10K snaps: avg_error={:.6}, max_error={:.6}", avg_error, max_error);
    assert!(max_error < 1.0, "Max error too high: {}", max_error);
}
