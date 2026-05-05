//! Integration tests for ct-demo.
//!
//! These tests exercise the public API end-to-end, verifying the core claim:
//! snap achieves O(1) error while float accumulates O(√N·σ) error.

use ct_demo::{
    advantage_ratio, benchmark, drift_accumulate, snap, snap_verify, BenchmarkResult,
    PythagoreanManifold,
};

// ── PythagoreanManifold ────────────────────────────────────────────────────────

#[test]
fn manifold_new_stores_fields() {
    let m = PythagoreanManifold::new(3, 250, 5);
    assert_eq!(m.dimension, 3);
    assert_eq!(m.max_coordinate, 250);
    assert_eq!(m.resolution, 5);
}

#[test]
fn manifold_default_is_sensible() {
    let m = PythagoreanManifold::default();
    assert!(m.dimension > 0);
    assert!(m.max_coordinate > 0);
    assert!(m.resolution > 0);
}

#[test]
#[should_panic(expected = "resolution must be non-zero")]
fn manifold_panics_on_zero_resolution() {
    let _ = PythagoreanManifold::new(2, 100, 0);
}

#[test]
fn manifold_grid_point_count_unit_resolution() {
    // With max=5, res=1: points are -5,-4,-3,-2,-1,0,1,2,3,4,5 = 11
    let m = PythagoreanManifold::new(2, 5, 1);
    assert_eq!(m.grid_point_count(), 11);
}

#[test]
fn manifold_grid_point_count_coarse_resolution() {
    // With max=10, res=5: points are -10,-5,0,5,10 = 5
    let m = PythagoreanManifold::new(2, 10, 5);
    assert_eq!(m.grid_point_count(), 5);
}

#[test]
fn manifold_id_contains_all_fields() {
    let m = PythagoreanManifold::new(3, 500, 10);
    let id = m.id();
    assert!(id.contains("3"), "id should contain dimension");
    assert!(id.contains("500"), "id should contain max_coordinate");
    assert!(id.contains("10"), "id should contain resolution");
}

// ── snap ───────────────────────────────────────────────────────────────────────

#[test]
fn snap_pythagorean_triple_legs() {
    let m = PythagoreanManifold::default();
    // Classic 3-4-5 triple
    assert_eq!(snap(3.0, &m), 3);
    assert_eq!(snap(4.0, &m), 4);
    assert_eq!(snap(5.0, &m), 5);
    // 5-12-13 triple
    assert_eq!(snap(5.0, &m), 5);
    assert_eq!(snap(12.0, &m), 12);
    assert_eq!(snap(13.0, &m), 13);
}

#[test]
fn snap_negative_values() {
    let m = PythagoreanManifold::default();
    assert_eq!(snap(-3.0, &m), -3);
    assert_eq!(snap(-3.4, &m), -3);
    assert_eq!(snap(-3.6, &m), -4);
}

#[test]
fn snap_zero() {
    let m = PythagoreanManifold::default();
    assert_eq!(snap(0.0, &m), 0);
    assert_eq!(snap(0.4, &m), 0);
    assert_eq!(snap(-0.4, &m), 0);
}

#[test]
fn snap_respects_resolution() {
    let m = PythagoreanManifold::new(2, 1000, 5);
    // Nearest multiple of 5
    assert_eq!(snap(0.0, &m), 0);
    assert_eq!(snap(2.0, &m), 0);   // closer to 0 than 5
    assert_eq!(snap(3.0, &m), 5);   // closer to 5
    assert_eq!(snap(7.0, &m), 5);   // closer to 5 than 10
    assert_eq!(snap(8.0, &m), 10);  // closer to 10
    assert_eq!(snap(100.0, &m), 100);
}

#[test]
fn snap_clamps_positive() {
    let m = PythagoreanManifold::new(2, 100, 1);
    assert_eq!(snap(99.4, &m), 99);
    assert_eq!(snap(100.0, &m), 100);
    assert_eq!(snap(100.4, &m), 100);
    assert_eq!(snap(200.0, &m), 100);
}

#[test]
fn snap_clamps_negative() {
    let m = PythagoreanManifold::new(2, 100, 1);
    assert_eq!(snap(-100.0, &m), -100);
    assert_eq!(snap(-200.0, &m), -100);
}

#[test]
fn snap_result_is_deterministic() {
    let m = PythagoreanManifold::default();
    let v = 7.777_f64;
    let first = snap(v, &m);
    let second = snap(v, &m);
    assert_eq!(first, second);
}

// ── drift_accumulate ──────────────────────────────────────────────────────────

#[test]
fn drift_zero_sigma_is_zero() {
    assert_eq!(drift_accumulate(1_000_000, 0.0), 0.0);
}

#[test]
fn drift_sqrt_n_scaling() {
    let sigma = 1.0;
    // 4x the ops → 2x the error
    let e1 = drift_accumulate(100, sigma);
    let e2 = drift_accumulate(400, sigma);
    let ratio = e2 / e1;
    assert!((ratio - 2.0).abs() < 1e-9, "expected ratio=2.0, got {ratio}");
}

#[test]
fn drift_grows_monotonically() {
    let sigma = 1e-10;
    let errors: Vec<f64> = (0..=6)
        .map(|i| drift_accumulate(10usize.pow(i), sigma))
        .collect();
    for window in errors.windows(2) {
        assert!(window[1] > window[0], "drift should grow: {:?}", window);
    }
}

// ── snap_verify ───────────────────────────────────────────────────────────────

#[test]
fn snap_verify_snap_constant_across_ops() {
    for ops in [0, 1, 100, 10_000, 1_000_000] {
        let (snap_result, _) = snap_verify(ops);
        assert_eq!(snap_result, 3, "snap should always be 3, failed at ops={ops}");
    }
}

#[test]
fn snap_verify_float_may_drift_at_large_n() {
    // At very large N, float is likely to have accumulated some error.
    // We don't assert exact drift (it's hardware-dependent), but we confirm
    // snap is always better or equal.
    let (snap_res, float_res) = snap_verify(1_000_000);
    let snap_err = (snap_res as f64 - 3.0).abs();
    let float_err = (float_res - 3.0).abs();
    assert!(
        snap_err <= float_err || snap_err == 0.0,
        "snap_err={snap_err} should be ≤ float_err={float_err}"
    );
}

// ── advantage_ratio ───────────────────────────────────────────────────────────

#[test]
fn advantage_ratio_at_zero_is_one() {
    assert_eq!(advantage_ratio(0), 1.0);
}

#[test]
fn advantage_ratio_is_positive() {
    for ops in [1, 100, 10_000, 1_000_000] {
        assert!(advantage_ratio(ops) > 0.0, "advantage should be positive at ops={ops}");
    }
}

#[test]
fn advantage_ratio_increases_with_n() {
    let a_small = advantage_ratio(100);
    let a_large = advantage_ratio(1_000_000);
    assert!(a_large > a_small, "advantage should grow: {a_small} → {a_large}");
}

// ── benchmark ─────────────────────────────────────────────────────────────────

#[test]
fn benchmark_snap_result_is_exact() {
    let r: BenchmarkResult = benchmark();
    assert_eq!(r.snap_result, 3, "snap should land on 3.0 exactly");
    assert_eq!(r.snap_error, 0.0, "snap error must be zero for integer input");
}

#[test]
fn benchmark_ops_count() {
    let r = benchmark();
    assert_eq!(r.ops, 1_000_000);
}

#[test]
fn benchmark_advantage_is_positive() {
    let r = benchmark();
    assert!(r.advantage >= 1.0, "advantage must be ≥ 1.0");
}

#[test]
fn benchmark_run_id_is_nonempty_uuid() {
    let r = benchmark();
    assert!(!r.run_id.is_empty());
    // UUID v4 format: 8-4-4-4-12 hex chars
    assert_eq!(r.run_id.len(), 36, "UUID should be 36 chars: {}", r.run_id);
    let parts: Vec<&str> = r.run_id.split('-').collect();
    assert_eq!(parts.len(), 5, "UUID should have 5 parts");
}

#[test]
fn benchmark_two_runs_have_different_ids() {
    let r1 = benchmark();
    let r2 = benchmark();
    assert_ne!(r1.run_id, r2.run_id, "each run should have a unique ID");
}

#[test]
fn benchmark_snap_wins_or_ties() {
    let r = benchmark();
    // snap_wins() returns true only if snap_error < float_error.
    // If float_error is also 0 (very rare), it's a tie — still fine.
    assert!(
        r.snap_wins() || r.snap_error == r.float_error,
        "snap should win or tie: snap_err={} float_err={}",
        r.snap_error,
        r.float_error
    );
}
