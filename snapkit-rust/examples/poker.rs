/// Poker Attention Engine Demo
///
/// Demonstrates multi-stream delta detection for a poker scenario:
/// - Card values (uniform randomness)
/// - Player behavior (categorical)
/// - Betting patterns (directional)
/// - Emotional state detection
///
/// Usage: cargo run --example poker

use snapkit::{DeltaDetector, SnapFunction, SnapTopology};

fn main() {
    println!("=== Poker Attention Engine ===");
    println!("Modeling a poker player's multi-stream snap functions\n");

    // Set up three streams with different topologies
    let mut detector = DeltaDetector::new();

    // Stream 1: Card values — tight tolerance, uniform topology
    detector.add_stream(
        "cards",
        SnapFunction::<f64>::builder()
            .tolerance(0.15)
            .topology(SnapTopology::Uniform)
            .build(),
    );

    // Stream 2: Player behavior — tighter tolerance for behavioral tells
    detector.add_stream(
        "behavior",
        SnapFunction::<f64>::builder()
            .tolerance(0.05)
            .topology(SnapTopology::Categorical)
            .build(),
    );

    // Stream 3: Betting patterns — directional
    detector.add_stream(
        "betting",
        SnapFunction::<f64>::builder()
            .tolerance(0.1)
            .topology(SnapTopology::Octahedral)
            .build(),
    );

    // Simulate a hand of poker
    let observations = vec![
        ("cards", 0.05),     // Expected card (small delta)
        ("behavior", 0.02),  // Normal behavior
        ("betting", 0.08),   // Standard bet
        ("cards", 0.03),     // Another expected card
        ("behavior", 0.3),   // TELL! Player twitched
        ("betting", 0.5),    // BIG RAISE
        ("cards", 0.4),      // River card - improved?
        ("behavior", 0.04),  // Back to normal
        ("betting", 0.1),    // Call
    ];

    println!("Round  | Stream    | Value  | Status  | Severity");
    println!("-------|-----------|--------|---------|----------");

    for (i, &(stream, value)) in observations.iter().enumerate() {
        if let Some(delta) = detector.observe(stream, value) {
            let status = if delta.exceeds_tolerance() {
                "⚠ DELTA"
            } else {
                "✓ SNAP "
            };
            println!(
                "Hand {} | {:<9} | {:.3} | {} | {:?}",
                i / 3 + 1,
                stream,
                value,
                status,
                delta.severity
            );
        }
    }

    // Show prioritized deltas
    println!("\n--- Prioritized Attention Allocation ---");
    let prioritized = detector.prioritize(3);
    for (i, delta) in prioritized.iter().enumerate() {
        println!(
            "{}. Stream '{}': weight={:.3}, severity={:?}",
            i + 1,
            delta.stream_id,
            delta.attention_weight,
            delta.severity
        );
    }

    // Show stream statistics
    println!("\n--- Stream Statistics ---");
    for sid in &["cards", "behavior", "betting"] {
        if let Some(stream) = detector.get_stream(sid) {
            println!(
                "{}: {} obs, {} deltas, rate={:.1}%",
                sid,
                stream.total_observations(),
                stream.delta_count(),
                stream.delta_rate() * 100.0
            );
        }
    }
}
