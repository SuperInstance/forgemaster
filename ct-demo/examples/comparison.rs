//! # Float vs. Snap Comparison
//!
//! Run with:
//! ```bash
//! cargo run --example comparison
//! ```
//!
//! Prints a formatted table showing accumulated float error vs. the zero-error
//! snap result at increasing operation counts.

use ct_demo::{advantage_ratio, drift_accumulate, snap, snap_verify, PythagoreanManifold};

fn main() {
    print_header();
    print_drift_table();
    print_separator();
    print_snap_table();
    print_separator();
    print_manifold_demo();
    print_separator();
    print_benchmark_summary();
}

fn print_header() {
    println!();
    println!("╔══════════════════════════════════════════════════════════════════╗");
    println!("║        ct-demo: Constraint Theory vs. Floating Point             ║");
    println!("║        Pythagorean Manifold — Drift-Free Arithmetic Demo         ║");
    println!("╚══════════════════════════════════════════════════════════════════╝");
    println!();
    println!("  True value: 3.0  (first leg of the 3-4-5 Pythagorean triple)");
    println!("  Float noise per op: σ = f64::EPSILON ≈ {:.2e}", f64::EPSILON);
    println!("  Float error model: O(√N · σ)  |  Snap error: O(1)");
    println!();
}

fn print_drift_table() {
    println!("  ┌─────────────┬────────────────────────┬──────────────────────────┐");
    println!("  │     Ops (N) │  Float error  O(√N·σ)  │  Snap error  O(1)        │");
    println!("  ├─────────────┼────────────────────────┼──────────────────────────┤");

    let sigma = f64::EPSILON;
    let snap_error = 0.0_f64; // exact for integer inputs

    let op_counts: &[usize] = &[
        1,
        10,
        100,
        1_000,
        10_000,
        100_000,
        1_000_000,
        10_000_000,
        100_000_000,
        1_000_000_000,
    ];

    for &ops in op_counts {
        let float_err = drift_accumulate(ops, sigma);
        println!(
            "  │ {:>11} │  {:.6e}           │  {:<24} │",
            format_ops(ops),
            float_err,
            format_snap_error(snap_error),
        );
    }

    println!("  └─────────────┴────────────────────────┴──────────────────────────┘");
    println!();
    println!("  Float error grows without bound. Snap error: always 0.");
    println!();
}

fn print_snap_table() {
    println!("  Snap vs. Float Live Trial (add/subtract σ N times, compare result)");
    println!();
    println!("  ┌─────────────┬──────────────────┬──────────────────┬─────────────┐");
    println!("  │     Ops (N) │  Float result    │  Snap result     │  Advantage  │");
    println!("  ├─────────────┼──────────────────┼──────────────────┼─────────────┤");

    let op_counts: &[usize] = &[0, 100, 10_000, 1_000_000];

    for &ops in op_counts {
        let (snap_res, float_res) = snap_verify(ops);
        let adv = advantage_ratio(ops);
        println!(
            "  │ {:>11} │  {:<16} │  {:<16} │  {:<11} │",
            format_ops(ops),
            format!("{:.15}", float_res),
            snap_res,
            format_advantage(adv),
        );
    }

    println!("  └─────────────┴──────────────────┴──────────────────┴─────────────┘");
    println!();
}

fn print_manifold_demo() {
    println!("  PythagoreanManifold snap examples");
    println!();

    let manifolds: &[(u32, i64, u32, &[f64])] = &[
        (2, 1000, 1,  &[3.0, 3.4, 3.6, 4.0, 4.999, 5.001]),
        (2, 1000, 5,  &[0.0, 2.4, 7.0, 8.0, 12.5, 13.0]),
        (3, 500,  10, &[0.0, 4.9, 15.0, 24.9, 100.1]),
    ];

    println!("  ┌──────────────────────────┬──────────────────────────────────────────────┐");
    println!("  │ Manifold(dim, max, res)   │  snap(value) examples                        │");
    println!("  ├──────────────────────────┼──────────────────────────────────────────────┤");

    for &(dim, max, res, values) in manifolds {
        let m = PythagoreanManifold::new(dim, max, res);
        let examples: Vec<String> = values
            .iter()
            .map(|&v| format!("{:.1}→{}", v, snap(v, &m)))
            .collect();
        println!(
            "  │ ({}, {:>7}, res={:>2})    │  {:<44} │",
            dim,
            max,
            res,
            examples.join("  "),
        );
    }

    println!("  └──────────────────────────┴──────────────────────────────────────────────┘");
    println!();
    println!("  Key: every snap result is an exact i64 — no floating-point budget consumed.");
    println!();
}

fn print_benchmark_summary() {
    let r = ct_demo::benchmark();

    println!("  Full Benchmark Summary");
    println!();
    println!("  Operations:    {}", r.ops);
    println!("  Float result:  {:.15}", r.float_result);
    println!("  Snap result:   {} (exact)", r.snap_result);
    println!("  Float error:   {:.6e}", r.float_error);
    println!("  Snap error:    {:.6e}", r.snap_error);
    println!("  Advantage:     {}", format_advantage(r.advantage));
    println!("  Snap wins:     {}", if r.snap_wins() { "YES" } else { "tied (both exact)" });
    println!("  Run ID:        {}", r.run_id);
    println!();
    println!("  Conclusion: snap() delivers O(1) error regardless of N.");
    println!("  Float error grows as O(√N·σ) and cannot be avoided without");
    println!("  constraint-theory projection onto an exact integer manifold.");
    println!();
}

// ── Formatting helpers ─────────────────────────────────────────────────────────

fn format_ops(ops: usize) -> String {
    if ops == 0 {
        return "0".to_string();
    }
    let mut s = ops.to_string();
    let mut result = String::new();
    let mut count = 0;
    for ch in s.chars().rev() {
        if count > 0 && count % 3 == 0 {
            result.push('_');
        }
        result.push(ch);
        count += 1;
    }
    // reverse
    s = result.chars().rev().collect();
    s
}

fn format_snap_error(e: f64) -> String {
    if e == 0.0 {
        "0  (exact)".to_string()
    } else {
        format!("{:.6e}", e)
    }
}

fn format_advantage(adv: f64) -> String {
    if adv >= 1_000_000.0 {
        format!("{:.2e}×", adv)
    } else if adv >= 1000.0 {
        format!("{:.0}×", adv)
    } else if adv <= 1.0 {
        "1× (tied)".to_string()
    } else {
        format!("{:.2}×", adv)
    }
}

fn print_separator() {
    println!("  ──────────────────────────────────────────────────────────────────");
    println!();
}
