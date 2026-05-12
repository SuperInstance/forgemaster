use flux_verify_api::compiler;
use flux_verify_api::engine::vm::FluxVm;
use flux_verify_api::provenance::merkle;

use axum::Router;
use std::sync::Arc;
use tokio::sync::Mutex;

// Helper to build a test app
fn test_app() -> Router {
    use flux_verify_api::api::routes::{self, AppState};
    use flux_verify_api::config::Config;
    let state = Arc::new(Mutex::new(AppState::new(Config::from_env())));
    routes::router().with_state(state)
}

// ── Sonar Domain Tests ──

#[test]
fn test_sonar_50khz_disproven() {
    // "A 50kHz sonar at 200m depth can detect a 10dB target at 5km"
    // This should be DISPROVEN — 50kHz has too much absorption at 5km
    let problem = compiler::parse_claim(
        "A 50kHz sonar at 200m depth can detect a 10dB target at 5km",
        "sonar",
    )
    .expect("should parse");

    assert_eq!(problem.domain, "sonar");
    assert_eq!(problem.variables.len(), 4);

    let bytecodes = compiler::compile(&problem);
    let mut vm = FluxVm::new();
    let trace = vm.execute(&bytecodes);
    let (verdict, confidence, counterexample) = vm.evaluate(&trace, &problem);

    assert_eq!(verdict, "DISPROVEN");
    assert!(confidence > 0.9);
    assert!(counterexample.is_some());
    let ce = counterexample.unwrap();
    assert!(ce["signal_excess_db"].as_f64().unwrap() < 0.0);
}

#[test]
fn test_sonar_1khz_proven() {
    // Low frequency sonar should be able to detect at moderate range
    let problem = compiler::parse_claim(
        "A 1kHz sonar at 100m depth can detect a 10dB target at 2km",
        "sonar",
    )
    .expect("should parse");

    let bytecodes = compiler::compile(&problem);
    let mut vm = FluxVm::new();
    let trace = vm.execute(&bytecodes);
    let (verdict, _confidence, counterexample) = vm.evaluate(&trace, &problem);

    // 1kHz at 2km should be PROVEN (low absorption)
    assert_eq!(verdict, "PROVEN");
    assert!(counterexample.is_none());
}

#[test]
fn test_sonar_trace_has_physics() {
    let problem = compiler::parse_claim(
        "A 10kHz sonar at 50m depth can detect a 15dB target at 1km",
        "sonar",
    )
    .expect("should parse");

    let bytecodes = compiler::compile(&problem);
    let mut vm = FluxVm::new();
    let trace = vm.execute(&bytecodes);

    let opcodes: Vec<&str> = trace.iter().map(|e| e.opcode.as_str()).collect();
    assert!(opcodes.contains(&"LOAD"), "trace should have LOAD ops");
    assert!(
        opcodes.contains(&"SONAR_SVP"),
        "trace should have SONAR_SVP"
    );
    assert!(
        opcodes.contains(&"SONAR_ABSORPTION"),
        "trace should have SONAR_ABSORPTION"
    );
    assert!(opcodes.contains(&"SONAR_TL"), "trace should have SONAR_TL");
    assert!(
        opcodes.contains(&"ASSERT_GT"),
        "trace should have ASSERT_GT"
    );
}

#[test]
fn test_sonar_mackenzie_velocity() {
    let problem = compiler::parse_claim(
        "A 5kHz sonar at 200m depth can detect a 10dB target at 3km",
        "sonar",
    )
    .expect("should parse");

    let bytecodes = compiler::compile(&problem);
    let mut vm = FluxVm::new();
    let trace = vm.execute(&bytecodes);

    // Find the SVP entry and check the result is reasonable
    let svp = trace
        .iter()
        .find(|e| e.opcode == "SONAR_SVP")
        .expect("should have SVP");
    let sv = svp.result.unwrap();
    assert!(
        sv > 1450.0 && sv < 1550.0,
        "Sound velocity {} should be ~1480-1520",
        sv
    );
}

// ── Thermal Domain Tests ──

#[test]
fn test_thermal_in_range() {
    let problem = compiler::parse_claim(
        "temperature 45°C is within safe range of 20°C to 80°C",
        "thermal",
    )
    .expect("should parse");

    let bytecodes = compiler::compile(&problem);
    let mut vm = FluxVm::new();
    let trace = vm.execute(&bytecodes);
    let (verdict, _confidence, counterexample) = vm.evaluate(&trace, &problem);

    assert_eq!(verdict, "PROVEN");
    assert!(counterexample.is_none());
}

#[test]
fn test_thermal_out_of_range() {
    let problem = compiler::parse_claim(
        "temperature 95°C is within safe range of 20°C to 80°C",
        "thermal",
    )
    .expect("should parse");

    let bytecodes = compiler::compile(&problem);
    let mut vm = FluxVm::new();
    let trace = vm.execute(&bytecodes);
    let (verdict, _confidence, counterexample) = vm.evaluate(&trace, &problem);

    assert_eq!(verdict, "DISPROVEN");
    assert!(counterexample.is_some());
}

// ── Generic Domain Tests ──

#[test]
fn test_generic_gt_proven() {
    let problem = compiler::parse_claim("10 is greater than 5", "generic").expect("should parse");
    let bytecodes = compiler::compile(&problem);
    let mut vm = FluxVm::new();
    let trace = vm.execute(&bytecodes);
    let (verdict, _, _) = vm.evaluate(&trace, &problem);
    assert_eq!(verdict, "PROVEN");
}

#[test]
fn test_generic_lt_disproven() {
    let problem = compiler::parse_claim("10 is less than 5", "generic").expect("should parse");
    let bytecodes = compiler::compile(&problem);
    let mut vm = FluxVm::new();
    let trace = vm.execute(&bytecodes);
    let (verdict, _, _) = vm.evaluate(&trace, &problem);
    assert_eq!(verdict, "DISPROVEN");
}

#[test]
fn test_generic_operator_direct() {
    let problem = compiler::parse_claim("100 > 50", "generic").expect("should parse");
    let bytecodes = compiler::compile(&problem);
    let mut vm = FluxVm::new();
    let trace = vm.execute(&bytecodes);
    let (verdict, _, _) = vm.evaluate(&trace, &problem);
    assert_eq!(verdict, "PROVEN");
}

// ── Merkle Provenance Tests ──

#[test]
fn test_merkle_deterministic() {
    let problem = compiler::parse_claim(
        "A 10kHz sonar at 100m depth can detect a 10dB target at 2km",
        "sonar",
    )
    .expect("should parse");

    let bytecodes = compiler::compile(&problem);

    let mut vm1 = FluxVm::new();
    let trace1 = vm1.execute(&bytecodes);

    let mut vm2 = FluxVm::new();
    let trace2 = vm2.execute(&bytecodes);

    let hash1 = merkle::hash_trace(&trace1);
    let hash2 = merkle::hash_trace(&trace2);
    assert_eq!(hash1, hash2, "Same inputs should produce same hash");
}

#[test]
fn test_merkle_different_claims() {
    let problem1 = compiler::parse_claim(
        "A 10kHz sonar at 100m depth can detect a 10dB target at 2km",
        "sonar",
    )
    .expect("should parse");
    let problem2 = compiler::parse_claim(
        "A 50kHz sonar at 200m depth can detect a 10dB target at 5km",
        "sonar",
    )
    .expect("should parse");

    let bc1 = compiler::compile(&problem1);
    let bc2 = compiler::compile(&problem2);

    let mut vm1 = FluxVm::new();
    let mut vm2 = FluxVm::new();
    let t1 = vm1.execute(&bc1);
    let t2 = vm2.execute(&bc2);

    assert_ne!(merkle::hash_trace(&t1), merkle::hash_trace(&t2));
}

#[test]
fn test_proof_hash_format() {
    let problem = compiler::parse_claim(
        "A 5kHz sonar at 50m depth can detect a 10dB target at 1km",
        "sonar",
    )
    .expect("should parse");

    let bytecodes = compiler::compile(&problem);
    let mut vm = FluxVm::new();
    let trace = vm.execute(&bytecodes);
    let hash = merkle::hash_trace(&trace);

    // SHA-256 hex should be 64 characters
    assert_eq!(hash.len(), 64);
    assert!(hash.chars().all(|c| c.is_ascii_hexdigit()));
}

// ── Parser Tests ──

#[test]
fn test_unknown_domain() {
    let result = compiler::parse_claim("test", "quantum");
    assert!(result.is_err());
    assert!(result.unwrap_err().contains("Unknown domain"));
}

#[test]
fn test_sonar_counterexample_fields() {
    let problem = compiler::parse_claim(
        "A 50kHz sonar at 200m depth can detect a 10dB target at 5km",
        "sonar",
    )
    .expect("should parse");

    let bytecodes = compiler::compile(&problem);
    let mut vm = FluxVm::new();
    let trace = vm.execute(&bytecodes);
    let (_, _, ce) = vm.evaluate(&trace, &problem);

    let ce = ce.unwrap();
    assert!(ce.get("depth_m").is_some());
    assert!(ce.get("frequency_hz").is_some());
    assert!(ce.get("range_m").is_some());
    assert!(ce.get("sound_velocity_ms").is_some());
    assert!(ce.get("transmission_loss_db").is_some());
    assert!(ce.get("signal_excess_db").is_some());
}
