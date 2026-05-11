/// Real-Time Stream Monitoring Demo
///
/// Demonstrates delta detection on a synthetic data stream with periodic anomalies.
///
/// Usage: cargo run --example monitoring

use snapkit::{SnapFunction, SnapTopology};

fn generate_stream() -> Vec<f64> {
    let mut data = Vec::new();
    // Normal values around 0
    for i in 0..50 {
        let normal = (i as f64 * 0.02).sin() * 0.1; // gentle oscillation
        data.push(normal);
    }
    // Anomaly at position 20
    data[20] = 0.5;
    // Anomaly at position 35
    data[35] = 0.8;
    // Anomaly at position 42
    data[42] = 0.3;
    data
}

fn main() {
    println!("=== Real-Time Stream Monitor ===");
    println!("Monitoring synthetic data with 3 anomalies\n");

    let mut snap = SnapFunction::<f64>::builder()
        .tolerance(0.1)
        .topology(SnapTopology::Hexagonal)
        .build();

    let data = generate_stream();
    let mut delta_count = 0_u64;

    println!("Idx │ Value  │ Status   │ Delta   │ Tolerance");
    println!("────┼────────┼──────────┼─────────┼──────────");

    for (i, &value) in data.iter().enumerate() {
        let result = snap.observe(value);
        if result.is_delta() {
            delta_count += 1;
            println!(
                "{:3} │ {:.4} │ ⚠ DELTA │ {:.4} │ {:.3}",
                i, result.original, result.delta, result.tolerance
            );
        } else if i % 10 == 0 {
            println!(
                "{:3} │ {:.4} │ ✓ SNAP  │ {:.4} │ {:.3}",
                i, result.original, result.delta, result.tolerance
            );
        }
    }

    println!(
        "\nSummary: {} total observations, {} deltas detected",
        data.len(),
        delta_count
    );
    println!("Snap rate: {:.1}%", snap.snap_rate() * 100.0);
    println!("Calibration: {:.3}", snap.calibration());
}
