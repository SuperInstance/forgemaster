/// Learning Cycle Demo
///
/// Demonstrates the expertise learning cycle:
/// DeltaFlood → ScriptBurst → SmoothRunning → Disruption → Rebuilding
///
/// Usage: cargo run --example learning

use snapkit::{LearningCycle, LearningPhase, SnapFunction};

fn main() {
    println!("=== Learning Cycle Demo ===");
    println!("Demonstrating expertise development through phase transitions\n");

    let snap = SnapFunction::<f64>::new();
    let mut cycle = LearningCycle::new(snap);

    println!("{:>4} │ {:15} │ {:5} │ {:7} │ {:8} │ {:6}", 
             "Exp", "Phase", "Load", "Scripts", "SnapRate", "Deltas");
    println!("─────┼─────────────────┼───────┼─────────┼──────────┼────────");

    // Phase 1: Delta Flood — everything is novel
    for i in 0..5 {
        let state = cycle.experience(0.3 + (i as f64 * 0.1), None);
        print_state(i, &state);
    }

    // Phase 2: Script Burst — patterns emerging, auto-creating scripts
    for i in 5..12 {
        let state = cycle.experience(0.3 + ((i % 3) as f64 * 0.1), None);
        print_state(i, &state);
    }

    // Phase 3: Smooth Running — most things snap to scripts
    for i in 12..22 {
        let state = cycle.experience(0.05, None);
        if i % 2 == 0 {
            print_state(i, &state);
        }
    }

    // Phase 4: Disruption — scripts failing
    for i in 22..28 {
        let state = cycle.experience(0.9 + ((i % 2) as f64 * 0.1), None);
        if i % 2 == 0 {
            print_state(i, &state);
        }
    }

    // Phase 5: Rebuilding — constructing new scripts
    for i in 28..36 {
        let state = cycle.experience(0.9 + ((i % 3) as f64 * 0.1), None);
        if i % 2 == 0 {
            print_state(i, &state);
        }
    }

    let state = cycle.current_state();
    println!("\nFinal state: {:?}", state.phase);
    println!("Phase transitions: {}", state.phase_transitions);
    println!("Scripts built: {}", state.scripts_built);
    println!("Cognitive load: {:.2}", state.cognitive_load);
}

fn print_state(exp: usize, state: &snapkit::LearningState) {
    let phase_icon = match state.phase {
        LearningPhase::DeltaFlood => "🌊",
        LearningPhase::ScriptBurst => "💥",
        LearningPhase::SmoothRunning => "🏃",
        LearningPhase::Disruption => "🚨",
        LearningPhase::Rebuilding => "🔨",
    };
    println!(
        "{:4} │ {}{:13} │ {:.3} │ {:7} │ {:.3}   │ {}",
        exp + 1,
        phase_icon,
        format!("{:?}", state.phase),
        state.cognitive_load,
        state.scripts_active,
        state.snap_hit_rate,
        (state.delta_rate * state.total_experiences as f64) as u64
    );
}
