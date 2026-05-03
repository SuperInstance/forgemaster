//! # Below-C Benchmark: Bitmask vs General Solver
//!
//! Run with:
//! ```bash
//! cargo run --example bitmask_benchmark
//! ```

use ct_demo::solver::{bitmask_n_queens, n_queens, benchmark_nqueens, BitmaskDomain};

fn main() {
    println!();
    println!("╔══════════════════════════════════════════════════════════════════╗");
    println!("║        Below-C Benchmark: Bitmask Domains vs General Solver      ║");
    println!("║        Single-instruction domain ops vs heap-allocated Vecs       ║");
    println!("╚══════════════════════════════════════════════════════════════════╝");
    println!();

    demo_bitmask_operations();
    println!("  ──────────────────────────────────────────────────────────────────");
    println!();
    benchmark_queens();
    println!("  ──────────────────────────────────────────────────────────────────");
    println!();
    print_analysis();
}

fn demo_bitmask_operations() {
    println!("  ┌─ Bitmask Domain Operations ────────────────────────────────────┐");
    println!("  │                                                                │");

    let a = BitmaskDomain::range(0, 7);
    let b = BitmaskDomain::range(3, 10);
    println!("  │  A = range(0,7) = {} ({} values)                      │", a, a.cardinality());
    println!("  │  B = range(3,10) = {} ({} values)                  │", b, b.cardinality());

    let c = a.intersect(&b);
    println!("  │  A ∩ B = {} (AND: single instruction)            │", c);

    let u = a.union(&b);
    println!("  │  A ∪ B = {} (OR: single instruction)                     │", u);

    let r = a.remove(3);
    println!("  │  A - {{3}} = {} (ANDN: single instruction)                │", r);

    println!("  │  |A| = {} (POPCNT: single instruction)                         │", a.cardinality());
    println!("  │  min(A) = {:?}  max(A) = {:?} (TZCNT/LZCNT)                     │", a.min(), a.max());

    println!("  │                                                                │");
    println!("  │  Every domain operation is a single CPU instruction.           │");
    println!("  │  No allocations. No loops. No pointer chasing.                 │");
    println!("  │                                                                │");
    println!("  └────────────────────────────────────────────────────────────────┘");
}

fn benchmark_queens() {
    println!("  ┌─ N-Queens: Bitmask vs General Solver ──────────────────────────┐");
    println!("  │                                                                │");
    println!("  │  {:>3}  {:>12}  {:>12}  {:>8}  {:>10}        │",
        "N", "Bitmask(μs)", "General(μs)", "Solutions", "Speedup");
    println!("  │  {}", "─".repeat(60));

    for n in [4u32, 6, 8, 10, 12] {
        let (bitmask_us, general_us, count) = benchmark_nqueens(n);
        let speedup = if bitmask_us > 0 && general_us > 0 {
            format!("{:.1}×", general_us as f64 / bitmask_us as f64)
        } else if bitmask_us == 0 && general_us == 0 {
            "<1μs both".to_string()
        } else if bitmask_us == 0 {
            "∞".to_string()
        } else {
            format!("{:.1}×", general_us as f64 / bitmask_us as f64)
        };
        println!("  │  {:>3}  {:>12}  {:>12}  {:>8}  {:>10}        │",
            n,
            if bitmask_us == 0 { "<1".to_string() } else { bitmask_us.to_string() },
            if general_us == 0 { "<1".to_string() } else { general_us.to_string() },
            count,
            speedup,
        );
    }

    println!("  │                                                                │");
    println!("  │  Bitmask domains eliminate heap allocations from the            │");
    println!("  │  inner loop of backtracking search. Each domain operation       │");
    println!("  │  (intersect, remove, cardinality) is a single instruction.      │");
    println!("  │                                                                │");
    println!("  └────────────────────────────────────────────────────────────────┘");
}

fn print_analysis() {
    println!("  ┌─ Analysis: Why This Matters ───────────────────────────────────┐");
    println!("  │                                                                │");
    println!("  │  Phase 1 (done): Bitmask domains in software                   │");
    println!("  │    - Domain ops: heap allocation → single register op          │");
    println!("  │    - Backtracking: Vec copies → register shadow copy           │");
    println!("  │    - Measured speedup: see table above                         │");
    println!("  │                                                                │");
    println!("  │  Phase 2: FPGA constraint machine (paper designed)             │");
    println!("  │    - Domain bitmask → hardware register (64 flip-flops)        │");
    println!("  │    - Constraint check → parallel comparator network            │");
    println!("  │    - Backtracking → register banking (one cycle swap)          │");
    println!("  │    - Projected: 200ns/check at 0.5W                           │");
    println!("  │                                                                │");
    println!("  │  Phase 3: RISC-V custom extension (future)                     │");
    println!("  │    - DOMAIN_INTERSECT as a single CPU instruction              │");
    println!("  │    - BACKTRACK_SNAPSHOT / RESTORE as hardware primitives       │");
    println!("  │    - No OS, no cache, no branch prediction needed              │");
    println!("  │                                                                │");
    println!("  │  The constraint is the hardware. The hardware is the constraint│");
    println!("  │                                                                │");
    println!("  └────────────────────────────────────────────────────────────────┘");
    println!();
}
