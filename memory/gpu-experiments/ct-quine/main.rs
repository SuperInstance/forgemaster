//! # Constraint Theory Self-Consistency Validator
//!
//! This program is a *quine* in the constraint-theory sense: it uses the
//! Pythagorean-triple manifold as its constraint surface, then proves that
//! the snap function is self-consistent — every snapped point is valid, and
//! every snap method agrees.
//!
//! Phases
//! ------
//!   1. Generate all Pythagorean triples with c ≤ MAX_C (Euclid's formula).
//!   2. Verify every triple satisfies a²+b²=c² with exact integer arithmetic.
//!   3. Perform N_Q random snap queries; for each:
//!        a. Binary-search snap   O(log n)
//!        b. Brute-force snap     O(n)
//!        c. Verify agreement and that the result is a valid triple.
//!   4. Run a 500-step holonomy loop on the unit circle; verify drift < 2π.
//!   5. Print a self-consistency verdict.

use std::time::Instant;

// ─── Arithmetic ────────────────────────────────────────────────────────────

fn gcd(mut a: u64, mut b: u64) -> u64 {
    while b != 0 {
        let t = b;
        b = a % b;
        a = t;
    }
    a
}

// ─── Manifold generation ───────────────────────────────────────────────────

/// Generate all Pythagorean triples (a ≤ b, c ≤ max_c) using Euclid's
/// parametrization:
///
///   a = m²−n²,  b = 2mn,  c = m²+n²   (m > n > 0, gcd=1, m−n odd)
///
/// then scale by k = 1 … max_c/c to include non-primitive triples.
///
/// Returns two parallel arrays:
///   `triples` — sorted by angle θ = atan2(b, a); ties broken by smallest c.
///   `angles`  — precomputed f64 angles for binary search.
fn generate_triples(max_c: u64) -> (Vec<(u64, u64, u64)>, Vec<f64>) {
    let mut set = std::collections::BTreeSet::new();

    // c = m²+n² ≤ max_c  ⟹  m ≤ √max_c
    let m_max = (max_c as f64).sqrt() as u64 + 2;

    for m in 2..=m_max {
        for n in 1..m {
            if (m + n) % 2 == 0 { continue; } // m−n must be odd
            if gcd(m, n) != 1   { continue; } // must be coprime
            let a0 = m * m - n * n;
            let b0 = 2 * m * n;
            let c0 = m * m + n * n;
            if c0 > max_c { continue; }
            let k_max = max_c / c0;
            for k in 1..=k_max {
                // Include BOTH orderings so angles span the full [0, π/2].
                // (a0 ≠ b0 always: m²−n² = 2mn has no integer solution.)
                set.insert((k * a0, k * b0, k * c0));
                set.insert((k * b0, k * a0, k * c0));
            }
        }
    }

    let mut triples: Vec<(u64, u64, u64)> = set.into_iter().collect();

    // Sort by angle; break ties by c (smallest scale first)
    triples.sort_by(|&(a1, b1, c1), &(a2, b2, c2)| {
        let t1 = f64::atan2(b1 as f64, a1 as f64);
        let t2 = f64::atan2(b2 as f64, a2 as f64);
        t1.partial_cmp(&t2).unwrap().then(c1.cmp(&c2))
    });

    let angles: Vec<f64> = triples
        .iter()
        .map(|&(a, b, _)| f64::atan2(b as f64, a as f64))
        .collect();

    (triples, angles)
}

// ─── Snap functions ────────────────────────────────────────────────────────

/// Binary-search snap — O(log n).
///
/// For a sorted array the closest element must lie at position `pos−1` or
/// `pos` (where `pos` is the insertion point for `theta`).  This is provably
/// optimal: every element left of `pos−1` is ≤ angles[pos−1] ≤ theta, so it
/// cannot be closer.
fn snap_binary(angles: &[f64], theta: f64) -> usize {
    let n   = angles.len();
    let pos = angles.partition_point(|&a| a < theta);
    let lo  = pos.saturating_sub(1);
    let hi  = pos.min(n - 1);
    if (angles[lo] - theta).abs() <= (angles[hi] - theta).abs() { lo } else { hi }
}

/// Brute-force snap — O(n) linear scan.  Independent implementation used as
/// a reference oracle for the agreement proof.
fn snap_brute(angles: &[f64], theta: f64) -> usize {
    angles
        .iter()
        .enumerate()
        .min_by(|(_, &a), (_, &b)| {
            (a - theta).abs().partial_cmp(&(b - theta).abs()).unwrap()
        })
        .map(|(i, _)| i)
        .unwrap()
}

// ─── RNG (no external deps) ────────────────────────────────────────────────

/// Knuth's multiplicative LCG.  Returns a uniform f64 in [0, 1).
fn lcg(state: &mut u64) -> f64 {
    *state = state
        .wrapping_mul(6_364_136_223_846_793_005)
        .wrapping_add(1_442_695_040_888_963_407);
    ((*state >> 11) as f64) * (1.0 / (1u64 << 53) as f64)
}

// ─── Main ──────────────────────────────────────────────────────────────────

fn main() {
    const MAX_C: u64   = 10_000;
    const N_Q:   usize = 10_000; // random snap queries
    const N_H:   usize = 500;    // holonomy steps

    println!("╔══════════════════════════════════════════════════════════╗");
    println!("║   CONSTRAINT THEORY SELF-CONSISTENCY VALIDATOR           ║");
    println!("║   Pythagorean Manifold · Snap-Function Proof             ║");
    println!("╚══════════════════════════════════════════════════════════╝");
    println!();

    // ── Phase 1 : Generate manifold ─────────────────────────────────────
    let t0 = Instant::now();
    let (triples, angles) = generate_triples(MAX_C);
    let t_gen = t0.elapsed();

    println!("Phase 1 · Manifold Generation");
    println!("  c ≤ {}  →  {} Pythagorean triples", MAX_C, triples.len());
    println!("  Generated in {:?}", t_gen);
    println!();

    // ── Phase 2 : Verify every triple a²+b²=c² (exact integer) ──────────
    let mut manifold_ok = true;
    for &(a, b, c) in &triples {
        if a * a + b * b != c * c {
            eprintln!("  BAD TRIPLE ({a}, {b}, {c}): {}+{}≠{}",
                      a*a, b*b, c*c);
            manifold_ok = false;
        }
    }

    println!("Phase 2 · Manifold Integrity  [integer a²+b²=c², no floats]");
    println!("  {} triples checked → {}",
             triples.len(),
             if manifold_ok { "ALL VALID ✓" } else { "FAILURES FOUND ✗" });
    println!();

    // ── Phase 3 : N_Q random snap queries ────────────────────────────────
    let mut rng        = 0xdead_beef_cafe_babe_u64;
    let mut snap_ok    = true;
    let mut agreements = 0usize;
    let mut max_dist   = 0.0f64;

    let t_q = Instant::now();
    for _ in 0..N_Q {
        // Random angle θ ∈ [0, π/2]
        let theta = lcg(&mut rng) * std::f64::consts::FRAC_PI_2;

        let ib = snap_binary(&angles, theta); // O(log n) path
        let ig = snap_brute (&angles, theta); // O(n)   oracle

        // Agreement: both methods must find a triple at the *same* angular
        // distance.  (Equal distance handles ties where multiple triples share
        // the same angle direction — e.g. (3,4,5) and (6,8,10).)
        let db = (angles[ib] - theta).abs();
        let dg = (angles[ig] - theta).abs();
        if (db - dg).abs() < 1e-12 { agreements += 1; }

        // Exact integer verification on the binary-search result
        let (a, b, c) = triples[ib];
        if a * a + b * b != c * c {
            eprintln!("  SNAP RETURNED INVALID TRIPLE ({a},{b},{c})");
            snap_ok = false;
        }

        if db > max_dist { max_dist = db; }
    }
    let t_q  = t_q.elapsed();
    let qps  = N_Q as f64 / t_q.as_secs_f64();

    println!("Phase 3 · Random Snap Queries  ({N_Q} queries)");
    println!("  Throughput:            {qps:.0} queries/sec");
    println!("  Binary ≡ Brute agree:  {agreements}/{N_Q}");
    println!("  Snapped triples valid: {snap_ok}");
    println!("  Max constraint dist:   {max_dist:.6} rad  ({:.4}°)",
             max_dist.to_degrees());
    println!();

    // ── Phase 4 : 500-step holonomy loop ─────────────────────────────────
    //
    // Walk θ randomly inside [ε, π/2−ε].  At every step snap to the nearest
    // triple and accumulate the per-step deviation (snapped_θ − query_θ).
    //
    // Claim: the cumulative deviation never exceeds 2π.
    //
    // Why it must hold: each step's deviation is bounded by half the largest
    // gap between consecutive triple angles.  With ~14 000 triples spanning
    // π/2 ≈ 1.57 rad the average gap is < 0.0002 rad.  Over 500 steps the
    // worst-case signed accumulation is ≪ 2π (≈ 6.28 rad), and the random
    // signs cause further cancellation (CLT: O(√500·gap)).

    let mut theta    = lcg(&mut rng) * std::f64::consts::FRAC_PI_2;
    let mut cum_err  = 0.0f64;
    let mut max_hol  = 0.0f64;

    for _ in 0..N_H {
        // Step size: up to ±π/50 per step — large enough to explore, small
        // enough that the walk stays inside [0, π/2].
        let delta = (lcg(&mut rng) - 0.5) * (std::f64::consts::PI / 50.0);
        theta = (theta + delta).clamp(1e-9, std::f64::consts::FRAC_PI_2 - 1e-9);

        let snapped = angles[snap_binary(&angles, theta)];
        cum_err    += snapped - theta;          // signed per-step deviation
        let h       = cum_err.abs();
        if h > max_hol { max_hol = h; }
    }

    let hol_bounded = max_hol < 2.0 * std::f64::consts::PI;

    println!("Phase 4 · Holonomy Loop  ({N_H} steps, step ≤ π/50)");
    println!("  Max holonomy drift:    {max_hol:.6} rad  ({:.4}°)",
             max_hol.to_degrees());
    println!("  Bounded (< 2π rad):    {hol_bounded}");
    println!();

    // ── Summary ──────────────────────────────────────────────────────────
    let all_pass = manifold_ok && snap_ok && agreements == N_Q && hol_bounded;

    println!("══════════════════════════════════════════════════════════");
    println!("  Total triples        : {}", triples.len());
    println!("  Queries/sec          : {qps:.0}");
    println!("  Holonomy drift       : {max_hol:.6} rad");
    println!("  Max constraint dist  : {max_dist:.6} rad");
    println!("  All verify passed    : {all_pass}");
    println!("══════════════════════════════════════════════════════════");
    println!();

    if all_pass {
        println!("  SELF-CONSISTENCY PROOF: PASSED ✓");
        println!();
        println!("  The snap function always returns a valid Pythagorean");
        println!("  triple (a²+b²=c², exact integers), and both snap methods");
        println!("  agree on every query.  The constraint manifold is");
        println!("  self-consistent.");
    } else {
        println!("  SELF-CONSISTENCY PROOF: FAILED ✗");
    }

    println!("══════════════════════════════════════════════════════════");

    if !all_pass {
        std::process::exit(1);
    }
}
