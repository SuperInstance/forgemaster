//! Integration tests for fleet-clock.

use fleet_clock::*;

// ── Fraction tests ──────────────────────────────────────────────────

#[test]
fn fraction_new_reduces() {
    let f = Fraction::new(6, 9);
    assert_eq!(f, Fraction::new(2, 3));
}

#[test]
fn fraction_add_sub_roundtrip() {
    let a = Fraction::new(1, 3);
    let b = Fraction::new(1, 6);
    let sum = a.add(b);
    assert_eq!(sum, Fraction::new(1, 2));
    let diff = sum.sub(b);
    assert_eq!(diff, a);
}

#[test]
fn fraction_ordering() {
    assert!(Fraction::new(1, 3) < Fraction::new(1, 2));
    assert!(Fraction::new(3, 4) > Fraction::new(2, 3));
    assert_eq!(Fraction::new(2, 4), Fraction::new(1, 2));
}

#[test]
fn fraction_to_f64() {
    let f = Fraction::new(1, 2);
    assert!((f.to_f64() - 0.5).abs() < 1e-10);
}

#[test]
fn fraction_zero_and_one() {
    assert_eq!(Fraction::ZERO, Fraction::new(0, 1));
    assert_eq!(Fraction::ONE, Fraction::new(1, 1));
}

// ── Laman topology tests ───────────────────────────────────────────

#[test]
fn laman_k3_edges() {
    let topo = LamanTopology::build(3);
    assert_eq!(topo.edges.len(), 3);
    assert!(topo.is_laman());
}

#[test]
fn laman_10_edges() {
    let topo = LamanTopology::build(10);
    assert_eq!(topo.edges.len(), 17); // 2*10 - 3
    assert!(topo.is_laman());
}

#[test]
fn laman_seeded_deterministic() {
    let t1 = LamanTopology::build_seeded(8, 42);
    let t2 = LamanTopology::build_seeded(8, 42);
    assert_eq!(t1.edges, t2.edges);
}

#[test]
fn laman_neighbors() {
    let topo = LamanTopology::build(4);
    let nbrs = topo.neighbors(3);
    assert!(nbrs.contains(&1));
    assert!(nbrs.contains(&2));
}

#[test]
fn laman_expected_edges() {
    assert_eq!(LamanTopology::expected_edges(5), 7);
    assert_eq!(LamanTopology::expected_edges(2), 1);
}

// ── PTP tests ───────────────────────────────────────────────────────

#[test]
fn ptp_offset_symmetric() {
    let t = Fraction::new(100, 1);
    let ex = PtpExchange::new(t, t.add(Fraction::new(5, 1)), t.add(Fraction::new(5, 1)), t.add(Fraction::new(10, 1)));
    assert_eq!(ex.offset(), Fraction::ZERO);
}

#[test]
fn ptp_offset_asymmetric() {
    let ex = PtpExchange::new(
        Fraction::new(0, 1),
        Fraction::new(10, 1),
        Fraction::new(10, 1),
        Fraction::new(12, 1),
    );
    let offset = ex.offset();
    assert_eq!(offset, Fraction::new(4, 1));
}

#[test]
fn ptp_estimator_median() {
    let mut est = PtpEstimator::new(PtpMode::OffsetEstimation);
    // Record 3 exchanges
    est.record(PtpExchange::new(
        Fraction::new(0, 1), Fraction::new(2, 1),
        Fraction::new(2, 1), Fraction::new(4, 1),
    ));
    est.record(PtpExchange::new(
        Fraction::new(0, 1), Fraction::new(6, 1),
        Fraction::new(6, 1), Fraction::new(8, 1),
    ));
    est.record(PtpExchange::new(
        Fraction::new(0, 1), Fraction::new(10, 1),
        Fraction::new(10, 1), Fraction::new(12, 1),
    ));
    let offset = est.estimated_offset();
    // Offsets: 0, 2, 4 → median = 2
    assert_eq!(offset, Fraction::new(2, 1));
}

#[test]
fn ptp_free_running_returns_zero() {
    let est = PtpEstimator::new(PtpMode::FreeRunning);
    assert_eq!(est.estimated_offset(), Fraction::ZERO);
}

// ── FleetClock integration tests ────────────────────────────────────

#[test]
fn clock_starts_and_ticks() {
    let config = FleetConfig::new("agent-1");
    let mut clock = FleetClock::new(config);
    clock.start();
    let t0 = clock.now();
    clock.tick();
    assert!(clock.now() > t0);
    assert_eq!(clock.tick_count(), 1);
}

#[test]
fn clock_custom_delta() {
    let config = FleetConfig::new("agent-2")
        .with_delta(Fraction::new(1, 4));
    let mut clock = FleetClock::new(config);
    clock.start();
    clock.tick();
    clock.tick();
    assert_eq!(clock.now(), Fraction::new(1, 2));
}

#[test]
fn clock_fleet_status() {
    let config = FleetConfig::new("agent-3");
    let mut clock = FleetClock::new(config);
    clock.start();
    clock.tick();
    let status = clock.fleet_status();
    assert_eq!(status.agent_id, "agent-3");
    assert_eq!(status.ticks, 1);
    assert_eq!(status.status, AgentStatus::Active);
}

#[test]
fn clock_sunset() {
    let config = FleetConfig::new("agent-4");
    let mut clock = FleetClock::new(config);
    clock.start();
    assert!(clock.sunset());
    assert!(!clock.is_operational());
}

#[test]
fn clock_stopped_does_not_tick() {
    let config = FleetConfig::new("agent-5");
    let mut clock = FleetClock::new(config);
    // Not started
    let t0 = clock.now();
    clock.tick();
    assert_eq!(clock.now(), t0);
}

#[test]
fn clock_with_ptp_correction() {
    let config = FleetConfig::new("agent-6")
        .with_ptp_mode(PtpMode::OffsetEstimation);
    let mut clock = FleetClock::new(config);
    clock.start();

    // Simulate PTP exchange showing we're 5 ticks ahead
    let ex = PtpExchange::new(
        Fraction::new(100, 1),
        Fraction::new(105, 1), // peer received at 105 (their clock)
        Fraction::new(105, 1),
        Fraction::new(108, 1), // we received reply at 108
    );
    clock.record_ptp(ex);
    // Offset should be applied
    let status = clock.fleet_status();
    assert!(status.ptp_exchanges > 0);
}

// ── Sunset / Inheritance tests ──────────────────────────────────────

#[test]
fn sunset_grace_period() {
    let mut sm = SunsetMachine::new(SunsetConfig {
        grace_period_ticks: 2,
        broadcast_final_state: false,
    });
    assert!(sm.begin_sunset(None));
    assert_eq!(sm.status, AgentStatus::Sunsetting);
    assert!(!sm.tick()); // 1 remaining
    assert!(sm.tick());  // complete
    assert_eq!(sm.status, AgentStatus::Sunset);
}

#[test]
fn inheritance_receive_and_apply() {
    let mut sm = SunsetMachine::new(SunsetConfig::default());
    let inh = Inheritance::new(
        "pred".to_string(),
        Fraction::new(3, 1),
        Fraction::new(1, 100),
        1,
        Fraction::new(500, 1),
    );
    assert!(sm.receive_inheritance(inh));
    assert_eq!(sm.status, AgentStatus::Inherited);
    let applied = sm.apply_inheritance();
    assert!(applied.is_some());
    assert_eq!(applied.unwrap().offset, Fraction::new(3, 1));
    assert_eq!(sm.status, AgentStatus::Active);
}

// ── Tensor-MIDI tests ───────────────────────────────────────────────

#[test]
fn tensor_midi_encode_decode() {
    let tm = TensorMidi::new();
    let ts = Fraction::new(42, 1);
    let encoded = tm.encode_tick(0x01, ts, b"test");
    let (sender, decoded_ts, payload) = tm.decode_tick(&encoded).unwrap();
    assert_eq!(sender, 0x01);
    assert_eq!(payload, b"test".to_vec());
}

#[test]
fn tensor_midi_bad_magic() {
    let tm = TensorMidi::new();
    let bad = vec![0x00, 0x00, 2, 0, 0, 0, 0, 0];
    let result = tm.decode_tick(&bad);
    assert!(result.is_err());
}

#[test]
fn tensor_midi_drift_tensor() {
    let tm = TensorMidi::new();
    let drifts = vec![
        Fraction::new(1, 1),
        Fraction::new(-3, 1),
        Fraction::new(0, 1),
    ];
    let tensor = tm.encode_drift_tensor(&drifts);
    assert_eq!(tensor.len(), 3);
    assert_eq!(tensor[0], 1);
    assert_eq!(tensor[1], -3);
}

// ── Spectral tests ──────────────────────────────────────────────────

#[test]
fn spectral_k3_algebraic_connectivity() {
    let topo = LamanTopology::build(3);
    let result = spectral_analysis(&topo);
    // K3 has algebraic connectivity = 3
    assert!((result.algebraic_connectivity - 3.0).abs() < 1.0);
    assert!(result.spectral_gap > 0.0);
}

#[test]
fn spectral_convergence_time_finite() {
    let topo = LamanTopology::build(5);
    let ct = convergence_time(&topo);
    assert!(ct.is_finite());
    assert!(ct > 0.0);
}
