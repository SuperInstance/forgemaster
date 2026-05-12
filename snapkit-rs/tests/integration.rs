//! Integration tests for snapkit — matching the Python test suite.

use snapkit::*;

// ── Eisenstein integer tests ─────────────────────────────────────────

#[test]
fn test_eisenstein_new() {
    let e = EisensteinInt::new(3, -2);
    assert_eq!(e.a, 3);
    assert_eq!(e.b, -2);
}

#[test]
fn test_eisenstein_norm_squared() {
    // 3² - 3(-2) + (-2)² = 9 + 6 + 4 = 19
    let e = EisensteinInt::new(3, -2);
    assert_eq!(e.norm_squared(), 19);
}

#[test]
fn test_eisenstein_norm_squared_zero() {
    assert_eq!(EisensteinInt::new(0, 0).norm_squared(), 0);
}

#[test]
fn test_eisenstein_norm_squared_units() {
    for unit in EisensteinInt::UNITS.iter() {
        assert_eq!(unit.norm_squared(), 1, "Unit {:?} should have norm 1", unit);
    }
}

#[test]
fn test_eisenstein_to_cartesian() {
    // (1, 0) → (1, 0)
    let (x, y) = EisensteinInt::new(1, 0).to_cartesian();
    assert!((x - 1.0).abs() < 1e-10);
    assert!(y.abs() < 1e-10);

    // (0, 1) → (-0.5, √3/2)
    let (x, y) = EisensteinInt::new(0, 1).to_cartesian();
    assert!((x + 0.5).abs() < 1e-10);
    assert!((y - 0.8660254037844386).abs() < 1e-10);
}

#[test]
fn test_eisenstein_add() {
    let a = EisensteinInt::new(1, 2);
    let b = EisensteinInt::new(3, -1);
    let c = a + b;
    assert_eq!(c, EisensteinInt::new(4, 1));
}

#[test]
fn test_eisenstein_sub() {
    let a = EisensteinInt::new(5, 3);
    let b = EisensteinInt::new(2, 1);
    let c = a - b;
    assert_eq!(c, EisensteinInt::new(3, 2));
}

#[test]
fn test_eisenstein_mul() {
    // (1,1) * (1,-1) = (2, 1)
    let a = EisensteinInt::new(1, 1);
    let b = EisensteinInt::new(1, -1);
    let c = a * b;
    assert_eq!(c, EisensteinInt::new(2, 1));
}

#[test]
fn test_eisenstein_conjugate() {
    let e = EisensteinInt::new(3, -2);
    let conj = e.conjugate();
    assert_eq!(conj.a, 3 - (-2)); // 5
    assert_eq!(conj.b, -(-2)); // 2
}

#[test]
fn test_eisenstein_norm_multiplicativity() {
    // norm(a*b) == norm(a) * norm(b)
    let a = EisensteinInt::new(3, -2);
    let b = EisensteinInt::new(1, 4);
    assert_eq!((a * b).norm_squared(), a.norm_squared() * b.norm_squared());
}

// ── Naive snap tests ─────────────────────────────────────────────────

#[test]
fn test_naive_round_origin() {
    let e = eisenstein::eisenstein_round_naive(0.0, 0.0);
    assert_eq!(e, EisensteinInt::new(0, 0));
}

#[test]
fn test_naive_round_unit() {
    // (1, 0) should round to (1, 0)
    let e = eisenstein::eisenstein_round_naive(1.0, 0.0);
    assert_eq!(e, EisensteinInt::new(1, 0));
}

#[test]
fn test_naive_round_near_origin() {
    // Point very close to (0,0) should snap to (0,0)
    let e = eisenstein::eisenstein_round_naive(0.01, 0.01);
    assert_eq!(e, EisensteinInt::new(0, 0));
}

#[test]
fn test_eisenstein_snap_on_lattice() {
    let (nearest, dist, is_snap) = eisenstein::eisenstein_snap(1.0, 0.0, 0.5);
    assert_eq!(nearest, EisensteinInt::new(1, 0));
    assert!(dist < 1e-10);
    assert!(is_snap);
}

#[test]
fn test_eisenstein_snap_off_lattice() {
    let (nearest, dist, is_snap) = eisenstein::eisenstein_snap(1.3, 0.0, 0.5);
    // Should snap to nearest lattice point
    assert!(dist <= 0.5);
    assert!(is_snap);
}

#[test]
fn test_eisenstein_snap_batch() {
    let points = vec![(0.0, 0.0), (1.0, 0.0), (0.0, 0.9)];
    let results = eisenstein::eisenstein_snap_batch(&points, 0.5);
    assert_eq!(results.len(), 3);
    assert!(results[0].2); // on lattice
    assert!(results[1].2); // on lattice
}

// ── Voronoï snap tests ───────────────────────────────────────────────

#[test]
fn test_voronoi_origin() {
    let e = voronoi::eisenstein_round_voronoi(0.0, 0.0);
    assert_eq!(e, EisensteinInt::new(0, 0));
}

#[test]
fn test_voronoi_unit_directions() {
    // East → (1, 0)
    let e = voronoi::eisenstein_round_voronoi(1.0, 0.0);
    assert_eq!(e, EisensteinInt::new(1, 0));

    // ω direction → (0, 1)
    let (wx, wy) = EisensteinInt::new(0, 1).to_cartesian();
    let e = voronoi::eisenstein_round_voronoi(wx, wy);
    assert_eq!(e, EisensteinInt::new(0, 1));
}

#[test]
fn test_voronoi_snap_with_tolerance() {
    let (nearest, dist, is_snap) = voronoi::eisenstein_snap_voronoi(0.3, 0.2, 0.5);
    assert!(dist <= 0.5);
    assert!(is_snap);
}

#[test]
fn test_voronoi_batch() {
    let points = vec![(0.0, 0.0), (1.0, 0.0), (0.5, 0.866)];
    let results = voronoi::eisenstein_snap_voronoi_batch(&points);
    assert_eq!(results.len(), 3);
    assert_eq!(results[0], EisensteinInt::new(0, 0));
    assert_eq!(results[1], EisensteinInt::new(1, 0));
}

#[test]
fn test_covering_radius() {
    let max_dist = voronoi::verify_covering_radius(50);
    let inv_sqrt3 = 1.0 / 1.7320508156882472;
    assert!(
        max_dist <= inv_sqrt3 + 1e-10,
        "Max snap distance {} exceeds covering radius 1/√3 ≈ {}",
        max_dist,
        inv_sqrt3
    );
}

// ── Temporal snap tests ──────────────────────────────────────────────

#[test]
fn test_beat_grid_new() {
    let grid = temporal::BeatGrid::new(1.0, 0.0, 0.0);
    assert_eq!(grid.period, 1.0);
    assert_eq!(grid.phase, 0.0);
    assert_eq!(grid.t_start, 0.0);
}

#[test]
fn test_beat_grid_snap_on_beat() {
    let grid = temporal::BeatGrid::new(1.0, 0.0, 0.0);
    let result = grid.snap(2.0, 0.1);
    assert!(result.is_on_beat);
    assert_eq!(result.beat_index, 2);
    assert!(result.offset.abs() < 1e-10);
}

#[test]
fn test_beat_grid_snap_off_beat() {
    let grid = temporal::BeatGrid::new(1.0, 0.0, 0.0);
    let result = grid.snap(2.5, 0.1);
    assert!(!result.is_on_beat);
    assert!(result.offset.abs() - 0.5 < 0.01);
}

#[test]
fn test_beat_grid_snap_with_phase() {
    let grid = temporal::BeatGrid::new(1.0, 0.5, 0.0);
    let result = grid.snap(0.5, 0.1);
    assert!(result.is_on_beat);
    assert_eq!(result.beat_index, 0);
}

#[test]
fn test_beat_grid_beats_in_range() {
    let grid = temporal::BeatGrid::new(1.0, 0.0, 0.0);
    let beats = grid.beats_in_range(1.5, 4.5);
    assert_eq!(beats, vec![2.0, 3.0, 4.0]);
}

#[test]
fn test_beat_grid_snap_batch() {
    let grid = temporal::BeatGrid::new(1.0, 0.0, 0.0);
    let times = vec![0.0, 1.0, 2.0, 0.5];
    let results = grid.snap_batch(&times, 0.1);
    assert_eq!(results.len(), 4);
    assert!(results[0].is_on_beat);
    assert!(results[1].is_on_beat);
    assert!(results[2].is_on_beat);
    assert!(!results[3].is_on_beat);
}

#[test]
fn test_temporal_snap_t0_detection() {
    let grid = temporal::BeatGrid::new(1.0, 0.0, 0.0);
    let mut ts = temporal::TemporalSnap::new(grid, 0.1, 0.1, 3);

    // Feed values that create an inflection: going down then up, with small value at inflection
    let r1 = ts.observe(0.0, 0.5);
    assert!(!r1.is_t_minus_0);

    let r2 = ts.observe(1.0, 0.02);
    assert!(!r2.is_t_minus_0); // Only 2 observations

    let r3 = ts.observe(2.0, 0.03);
    // d1 = (0.02 - 0.5) / 1 = -0.48 (going down)
    // d2 = (0.03 - 0.02) / 1 = 0.01 (going up)
    // d1*d2 < 0 → sign change; |curr_val| = 0.03 < 0.1 threshold
    assert!(r3.is_t_minus_0);
}

#[test]
fn test_temporal_snap_reset() {
    let grid = temporal::BeatGrid::new(1.0, 0.0, 0.0);
    let mut ts = temporal::TemporalSnap::new(grid, 0.1, 0.1, 3);
    ts.observe(0.0, 1.0);
    ts.observe(1.0, 2.0);
    ts.reset();
    assert_eq!(ts.history().len(), 0);
}

// ── Spectral analysis tests ──────────────────────────────────────────

#[test]
fn test_entropy_uniform() {
    // Uniform distribution over 10 bins should have entropy ≈ log2(10) ≈ 3.32
    let data: Vec<f64> = (0..100).map(|i| i as f64).collect();
    let h = spectral::entropy(&data, 10);
    assert!(h > 3.0, "Entropy {} should be > 3.0 for uniform", h);
}

#[test]
fn test_entropy_constant() {
    let data = vec![5.0; 100];
    let h = spectral::entropy(&data, 10);
    assert_eq!(h, 0.0);
}

#[test]
fn test_entropy_single_element() {
    let data = vec![1.0];
    let h = spectral::entropy(&data, 10);
    assert_eq!(h, 0.0);
}

#[test]
fn test_autocorrelation_constant() {
    let data = vec![5.0; 20];
    let acf = spectral::autocorrelation(&data, None);
    assert_eq!(acf[0], 1.0);
    // All other lags should be 0 or very small for constant
    for &v in &acf[1..] {
        assert!(v.abs() < 1e-10);
    }
}

#[test]
fn test_autocorrelation_single_lag() {
    let data = vec![1.0, 2.0, 3.0, 4.0, 5.0];
    let acf = spectral::autocorrelation(&data, Some(2));
    assert_eq!(acf.len(), 3);
    assert!((acf[0] - 1.0).abs() < 1e-10);
}

#[test]
fn test_hurst_short_data() {
    let data = vec![1.0, 2.0, 3.0];
    let h = spectral::hurst_exponent(&data);
    assert_eq!(h, 0.5); // Default for insufficient data
}

#[test]
fn test_spectral_summary() {
    // Sine wave — should have some entropy, non-zero hurst
    let data: Vec<f64> = (0..200).map(|i| (i as f64 * 0.1).sin()).collect();
    let summary = spectral::spectral_summary(&data, 10, None);
    assert!(summary.entropy_bits > 0.0);
    assert!(summary.hurst >= 0.0 && summary.hurst <= 1.0);
}

#[test]
fn test_spectral_batch() {
    let data1: Vec<f64> = (0..50).map(|i| i as f64).collect();
    let data2: Vec<f64> = (0..50).map(|i| (i as f64 * 0.1).sin()).collect();
    let results = spectral::spectral_batch(&[&data1, &data2], 10, None);
    assert_eq!(results.len(), 2);
}

// ── Connectome tests ─────────────────────────────────────────────────

#[test]
fn test_connectome_coupled() {
    let mut tc = connectome::TemporalConnectome::new(0.3, 5, 10);
    // Perfectly correlated
    let a: Vec<f64> = (0..20).map(|i| i as f64).collect();
    let b: Vec<f64> = (0..20).map(|i| (i as f64) * 2.0).collect();
    tc.add_room(&a);
    tc.add_room(&b);
    let result = tc.analyze();
    assert_eq!(result.pairs.len(), 1);
    assert_eq!(result.pairs[0].coupling, CouplingType::Coupled);
    assert!(result.pairs[0].correlation > 0.9);
}

#[test]
fn test_connectome_anti_coupled() {
    let mut tc = connectome::TemporalConnectome::new(0.3, 5, 10);
    let a: Vec<f64> = (0..20).map(|i| i as f64).collect();
    let b: Vec<f64> = (0..20).map(|i| -(i as f64)).collect();
    tc.add_room(&a);
    tc.add_room(&b);
    let result = tc.analyze();
    assert_eq!(result.pairs.len(), 1);
    assert_eq!(result.pairs[0].coupling, CouplingType::AntiCoupled);
}

#[test]
fn test_connectome_uncoupled() {
    let mut tc = connectome::TemporalConnectome::new(0.8, 2, 10);
    let a: Vec<f64> = (0..20).map(|i| (i as f64).sin()).collect();
    let b: Vec<f64> = (0..20).map(|i| (i as f64 * 0.01 + 100.0).cos()).collect();
    tc.add_room(&a);
    tc.add_room(&b);
    let result = tc.analyze();
    // These should be uncoupled with high threshold
    assert_eq!(result.pairs[0].coupling, CouplingType::Uncoupled);
}

#[test]
fn test_connectome_insufficient_samples() {
    let mut tc = connectome::TemporalConnectome::new(0.3, 5, 100);
    tc.add_room(&[1.0, 2.0, 3.0]);
    tc.add_room(&[4.0, 5.0, 6.0]);
    let result = tc.analyze();
    assert_eq!(result.pairs[0].coupling, CouplingType::Uncoupled);
    assert_eq!(result.pairs[0].confidence, 0.0);
}

#[test]
fn test_connectome_three_rooms() {
    let mut tc = connectome::TemporalConnectome::new(0.3, 5, 10);
    let a: Vec<f64> = (0..20).map(|i| i as f64).collect();
    let b: Vec<f64> = (0..20).map(|i| i as f64 * 2.0).collect();
    let c: Vec<f64> = (0..20).map(|i| -(i as f64)).collect();
    tc.add_room(&a);
    tc.add_room(&b);
    tc.add_room(&c);
    let result = tc.analyze();
    assert_eq!(result.pairs.len(), 3); // C(3,2) = 3
    assert_eq!(result.num_rooms, 3);
}

#[test]
fn test_room_pair_is_significant() {
    let coupled = types::RoomPair {
        room_a: 0,
        room_b: 1,
        coupling: CouplingType::Coupled,
        correlation: 0.9,
        lag: 0,
        confidence: 0.8,
    };
    assert!(coupled.is_significant());

    let uncoupled = types::RoomPair {
        room_a: 0,
        room_b: 1,
        coupling: CouplingType::Uncoupled,
        correlation: 0.1,
        lag: 0,
        confidence: 0.05,
    };
    assert!(!uncoupled.is_significant());
}

#[test]
fn test_connectome_result_filters() {
    let mut tc = connectome::TemporalConnectome::new(0.3, 5, 10);
    let a: Vec<f64> = (0..20).map(|i| i as f64).collect();
    let b: Vec<f64> = (0..20).map(|i| i as f64 * 2.0).collect();
    let c: Vec<f64> = (0..20).map(|i| -(i as f64)).collect();
    tc.add_room(&a);
    tc.add_room(&b);
    tc.add_room(&c);
    let result = tc.analyze();

    // Room 0 and 1: correlated (a vs 2a) → coupled
    // Room 0 and 2: anti-correlated (a vs -a) → anti-coupled
    // Room 1 and 2: anti-correlated (2a vs -a) → anti-coupled
    assert_eq!(result.coupled().len(), 1);
    assert_eq!(result.anti_coupled().len(), 2);
    assert_eq!(result.significant().len(), 3);
}

// ── Distance test ────────────────────────────────────────────────────

#[test]
fn test_eisenstein_distance_same_point() {
    let d = eisenstein::eisenstein_distance(1.0, 0.0, 1.0, 0.0);
    assert!(d < 1e-10);
}

#[test]
fn test_eisenstein_distance_adjacent() {
    let d = eisenstein::eisenstein_distance(0.0, 0.0, 1.0, 0.0);
    assert!((d - 1.0).abs() < 1e-10);
}

// ── Display test ─────────────────────────────────────────────────────

#[test]
fn test_eisenstein_display() {
    let e = EisensteinInt::new(3, -2);
    let s = format!("{}", e);
    assert_eq!(s, "3+-2ω");
}

// ── Covering radius constant test ────────────────────────────────────

#[test]
fn test_covering_radius_constant() {
    // Just verify the constant is close to 1/sqrt(3)
    assert!((eisenstein::COVERING_RADIUS - 0.5773502691896257).abs() < 1e-15);
}
