/// Rubik's Cube Script Engine Demo
///
/// Demonstrates script matching for Rubik's cube algorithms.
/// Shows how patterns snap to known algorithms, freeing cognition.
///
/// Usage: cargo run --example rubik

use snapkit::{Script, ScriptLibrary, ScriptStatus};
use std::collections::HashMap;

fn main() {
    println!("=== Rubik's Cube Script Engine ===");
    println!("Demonstrating pattern→script snap matching\n");

    let mut library = ScriptLibrary::new(0.85);

    // Add some CFOP algorithm scripts
    let oll_scripts = vec![
        (
            "OLL-1",
            "Dot - Sune (R U R' U R U2 R')",
            vec![1.0, 0.9, 0.8, 0.7],
        ),
        (
            "OLL-2",
            "L shape - Bowtie (F R U R' U' F')",
            vec![0.6, 0.8, 0.9, 0.5],
        ),
        (
            "OLL-3",
            "T shape (R U R' U' R' F R F')",
            vec![0.7, 0.6, 0.8, 0.7],
        ),
    ];

    for (id, name, pattern) in oll_scripts {
        library.add_script(Script {
            id: id.to_string(),
            name: name.to_string(),
            trigger_pattern: pattern,
            response: serde_json::json!({"algorithm": name.to_string()}),
            context: HashMap::new(),
            match_threshold: 0.85,
            status: ScriptStatus::Active,
            use_count: 0,
            success_count: 0,
            fail_count: 0,
            last_used: 0,
            confidence: 1.0,
        });
    }

    println!("Registered {} OLL algorithms\n", library.active_scripts());

    // Simulate recognizing patterns from cube state observations
    let observations = vec![
        ("Dot pattern", vec![0.95, 0.88, 0.82, 0.72]),
        ("Random scramble", vec![0.3, 0.5, 0.7, 0.2]),
        ("L shape", vec![0.58, 0.82, 0.88, 0.52]),
        ("T shape", vec![0.72, 0.58, 0.78, 0.68]),
    ];

    for (name, obs) in observations {
        print!("Observing {:15} → ", name);
        if let Some(match_result) = library.find_best_match(&obs) {
            if match_result.is_match {
                let script = library.get(&match_result.script_id).unwrap();
                println!(
                    "MATCH (conf={:.2}): {}",
                    match_result.confidence, script.name
                );
            } else {
                println!(
                    "No match (best={:.2}): NEW PATTERN — learning required",
                    match_result.confidence
                );
                // Learn it as a new script
                library.learn(
                    obs,
                    serde_json::json!({"action": "new_algorithm", "name": name}),
                    &format!("learned_{}", name.replace(' ', "_")),
                    HashMap::new(),
                );
            }
        } else {
            println!("NO SCRIPTS YET");
        }
    }

    println!(
        "\nLibrary stats: {} total, {} active, hit rate={:.1}%",
        library.total_scripts(),
        library.active_scripts(),
        library.hit_rate() * 100.0
    );
}
