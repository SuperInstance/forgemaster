//! Bounded Drift Theorem — Experimental Verification in Rust
//!
//! THEOREM: For n Eisenstein snap ops each with error < ε, total holonomy ≤ nε.
//!
//! Two error models:
//!   Discrete:  snap returns random lattice point within ε of ideal
//!   Continuous: noise in disk(ε-R) then snap to nearest lattice (R=1/√3 ≈ 0.577)
//!               so true step error ≤ ε by construction.

use rand::Rng;
use rand::rngs::ThreadRng;
use std::f64::consts::PI;
use std::fs::File;
use std::io::Write;

fn voronoi_circumradius() -> f64 { 1.0 / 3.0_f64.sqrt() }

// ─── Eisenstein ──────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Copy)]
struct Eisenstein { a: f64, b: f64 }

impl Eisenstein {
    fn new(a: f64, b: f64) -> Self { Self { a, b } }
    fn to_complex(self) -> (f64, f64) {
        (self.a - 0.5 * self.b, (3.0_f64).sqrt() * 0.5 * self.b)
    }
    fn norm(self) -> f64 {
        let (x, y) = self.to_complex(); (x * x + y * y).sqrt()
    }
}

fn lattice_steps() -> [(i32, i32); 6] {
    [(1,0), (-1,1), (0,-1), (-1,0), (1,-1), (0,1)]
}

/// Generate a closed cycle efficiently.
///
/// Strategy: generate all n steps freely, then check if the net displacement
/// is 0. The default is to use the first free+close approach for small n,
/// and a Markov-chain approach for large n (bias steps toward closure).
///
/// Key insight: on the Eisenstein lattice, the 6 steps sum to 0, so any
/// random walk's net displacement is a 2D random walk with variance ~ n/3
/// in each coordinate. The probability of exact closure after n steps is
/// ~ 1/(πn/3) ≈ 3/(πn), so for n=1000, ~1/1000 walks are closed.
/// We use the 2-step closure method which works whenever the residual
/// (da, db) is representable as the sum of two primitive steps.
/// The set {step[i] + step[j] for i,j in 0..5} = all vectors with
/// |da| ≤ 2, |db| ≤ 2 where da + db ∈ {-2,-1,0,1,2}.
/// Unreachable residuals require 3+ steps.
fn random_cycle(n: usize, rng: &mut ThreadRng) -> Vec<usize> {
    if n <= 2 {
        // Trivial: must be all zeros, which only works if n=0
        // n=3: special case, generate and check
        return random_cycle_fallback(n, rng);
    }

    let steps = lattice_steps();

    // Precompute the 2-step closure table
    // Maps (da, db) -> [(i, j)] where steps[i] + steps[j] = (da, db)
    let mut close2: std::collections::HashMap<(i64,i64),Vec<(usize,usize)>> = std::collections::HashMap::new();
    for i in 0..6 { for j in 0..6 {
        let (d1,d2) = (steps[i].0 as i64 + steps[j].0 as i64, steps[i].1 as i64 + steps[j].1 as i64);
        close2.entry((d1,d2)).or_default().push((i,j));
    }}

    // Precompute the 3-step closure table
    let mut close3: std::collections::HashMap<(i64,i64),Vec<(usize,usize,usize)>> = std::collections::HashMap::new();
    for i in 0..6 { for j in 0..6 { for k in 0..6 {
        let d = (steps[i].0 as i64 + steps[j].0 as i64 + steps[k].0 as i64,
                 steps[i].1 as i64 + steps[j].1 as i64 + steps[k].1 as i64);
        close3.entry(d).or_default().push((i,j,k));
    }}}

    // Precompute the 4-step closure table
    let mut close4: std::collections::HashMap<(i64,i64),Vec<(usize,usize,usize,usize)>> = std::collections::HashMap::new();
    for i in 0..6 { for j in 0..6 { for k in 0..6 { for l in 0..6 {
        let d = (steps[i].0 as i64 + steps[j].0 as i64 + steps[k].0 as i64 + steps[l].0 as i64,
                 steps[i].1 as i64 + steps[j].1 as i64 + steps[k].1 as i64 + steps[l].1 as i64);
        close4.entry(d).or_default().push((i,j,k,l));
    }}}}

    // Determine how many steps to reserve for closure
    // 2 steps close most residuals; 3 or 4 cover everything
    let reserve = if n >= 6 { 4 } else { 2.max(n.saturating_sub(1)) };
    let free = n.saturating_sub(reserve);

    for _ in 0..1000 {
        let mut a: i64 = 0; let mut b: i64 = 0;
        let mut cycle = Vec::with_capacity(n);

        for _ in 0..free {
            let idx = rng.gen_range(0..6);
            cycle.push(idx);
            let (da, db) = steps[idx];
            a += da as i64; b += db as i64;
        }

        let residual = (-a, -b);

        if reserve == 2 {
            if let Some(closures) = close2.get(&residual) {
                let &(i, j) = &closures[rng.gen_range(0..closures.len())];
                cycle.push(i); cycle.push(j);
                return cycle;
            }
        } else if reserve == 3 {
            if let Some(closures) = close3.get(&residual) {
                let &(i,j,k) = &closures[rng.gen_range(0..closures.len())];
                cycle.push(i); cycle.push(j); cycle.push(k);
                return cycle;
            }
        } else if reserve >= 4 {
            if let Some(closures) = close4.get(&residual) {
                let &(i,j,k,l) = &closures[rng.gen_range(0..closures.len())];
                cycle.push(i); cycle.push(j); cycle.push(k); cycle.push(l);
                return cycle;
            }
            // Also try 2+2 combination
            if let Some(closures) = close4.get(&residual) {
                let &(i,j,k,l) = &closures[rng.gen_range(0..closures.len())];
                cycle.push(i); cycle.push(j); cycle.push(k); cycle.push(l);
                return cycle;
            }
        }
    }

    // Fallback
    random_cycle_fallback(n, rng)
}

fn random_cycle_fallback(n: usize, rng: &mut ThreadRng) -> Vec<usize> {
    let steps = lattice_steps();
    loop {
        let mut a: i64 = 0; let mut b: i64 = 0;
        let mut cycle = Vec::with_capacity(n);
        for _ in 0..n {
            let idx = rng.gen_range(0..6);
            cycle.push(idx);
            let (da, db) = steps[idx];
            a += da as i64; b += db as i64;
        }
        if a == 0 && b == 0 { return cycle; }
    }
}

// ─── Snap Functions ──────────────────────────────────────────────────────────

fn nearest_lattice(x: f64, y: f64) -> (i64, i64) {
    let b = (2.0 * y / 3.0_f64.sqrt()).round() as i64;
    let a = (x + 0.5 * 2.0 * y / 3.0_f64.sqrt()).round() as i64;
    let mut best = (a, b);
    let mut best_d2 = f64::INFINITY;
    for da in -1..=1 { for db in -1..=1 {
        let (lx, ly) = Eisenstein::new((a+da) as f64, (b+db) as f64).to_complex();
        let d2 = (x-lx)*(x-lx)+(y-ly)*(y-ly);
        if d2 < best_d2 { best_d2 = d2; best = (a+da, b+db); }
    }}
    best
}

/// Discrete error model: return random lattice point within ε of ideal point.
fn snap_discrete(ideal_a: f64, ideal_b: f64, epsilon: f64, rng: &mut ThreadRng) -> (i64, i64, f64) {
    if epsilon <= 0.0 {
        return (ideal_a.round() as i64, ideal_b.round() as i64, 0.0);
    }
    let (ix, iy) = Eisenstein::new(ideal_a, ideal_b).to_complex();
    let ci = (ideal_a.round() as i64, ideal_b.round() as i64);
    let sr = ((epsilon * 2.0).ceil() as i64).max(1);
    let mut cand: Vec<(i64,i64,f64)> = Vec::new();
    for da in -sr..=sr { for db in -sr..=sr {
        let (ca, cb) = (ci.0+da, ci.1+db);
        let (lx, ly) = Eisenstein::new(ca as f64, cb as f64).to_complex();
        let d = ((ix-lx)*(ix-lx)+(iy-ly)*(iy-ly)).sqrt();
        if d < epsilon { cand.push((ca, cb, d)); }
    }}
    if cand.is_empty() { (ci.0, ci.1, 0.0) } else { cand[rng.gen_range(0..cand.len())] }
}

/// Continuous noise model: noise in disk(ε-R) then snap to nearest lattice.
/// True error = distance from result lattice point to ideal ≤ ε by construction.
fn snap_continuous(ideal_a: f64, ideal_b: f64, epsilon: f64, rng: &mut ThreadRng) -> (i64, i64, f64) {
    let r = voronoi_circumradius();
    if epsilon <= r {
        return (ideal_a.round() as i64, ideal_b.round() as i64, 0.0);
    }
    let noise_radius = epsilon - r;
    let (ix, iy) = Eisenstein::new(ideal_a, ideal_b).to_complex();
    let angle = 2.0 * PI * rng.gen::<f64>();
    let mag = noise_radius * rng.gen::<f64>().sqrt();
    let (nx, ny) = (ix + mag * angle.cos(), iy + mag * angle.sin());
    let (a, b) = nearest_lattice(nx, ny);
    let (lx, ly) = Eisenstein::new(a as f64, b as f64).to_complex();
    let true_err = ((ix-lx)*(ix-lx)+(iy-ly)*(iy-ly)).sqrt();
    (a, b, true_err)
}

// ─── Cycle Walker ────────────────────────────────────────────────────────────

fn walk_cycle(steps: &[usize], epsilon: f64,
    snap_fn: fn(f64, f64, f64, &mut ThreadRng) -> (i64,i64,f64),
    rng: &mut ThreadRng) -> (f64, Vec<f64>)
{
    let mut a = 0.0f64; let mut b = 0.0f64;
    let mut errors = Vec::with_capacity(steps.len());
    for &si in steps {
        let s = lattice_steps()[si];
        let (ia, ib) = (a + s.0 as f64, b + s.1 as f64);
        let (sa, sb, e) = snap_fn(ia, ib, epsilon, rng);
        a = sa as f64; b = sb as f64;
        errors.push(e);
    }
    (Eisenstein::new(a, b).norm(), errors)
}

// ─── Test Runner ─────────────────────────────────────────────────────────────

#[derive(Debug, Clone)]
struct TestResult {
    model: String, n: usize, eps: f64, trials: usize,
    max_hol: f64, mean_hol: f64, min_hol: f64,
    bound: f64, violations: usize, tightness: f64,
}

fn run_test(model: &str, n: usize, eps: f64, trials: usize,
    snap_fn: fn(f64, f64, f64, &mut ThreadRng) -> (i64,i64,f64),
    rng: &mut ThreadRng) -> TestResult
{
    let bound = n as f64 * eps;
    let mut max_hol = 0.0; let mut sum_hol = 0.0;
    let mut min_hol = f64::INFINITY; let mut violations = 0;

    for _ in 0..trials {
        let cycle = random_cycle(n, rng);
        let (hol, _) = walk_cycle(&cycle, eps, snap_fn, rng);
        if hol > max_hol { max_hol = hol; }
        if hol < min_hol { min_hol = hol; }
        sum_hol += hol;
        if hol > bound + 1e-12 { violations += 1; }
    }

    TestResult {
        model: model.to_string(), n, eps, trials,
        max_hol, mean_hol: sum_hol / trials as f64, min_hol,
        bound, violations,
        tightness: if bound > 0.0 { max_hol / bound } else { 0.0 },
    }
}

// ─── Run Everything ──────────────────────────────────────────────────────────

fn run_all(rng: &mut ThreadRng) -> (Vec<TestResult>, Vec<TestResult>) {
    let n_vals = [3, 6, 10, 50, 100, 500, 1000];
    let eps_vals = [0.01, 0.05, 0.1, 0.3, 0.5, 0.6, 0.8, 1.0, 1.5, 2.0, 5.0, 10.0];
    let base = 5000;

    let mut disc = Vec::new(); let mut cont = Vec::new();

    for &n in &n_vals {
        for &eps in &eps_vals {
            let es = if eps < 1.0 { format!("{:.2}",eps) } else { format!("{:.0}",eps) };
            print!("  n={:4} ε={:>4}", n, es);

            let rd = run_test("discrete", n, eps, base, snap_discrete, rng);
            print!("  disc m={:.4} t={:.4} v={}", rd.max_hol, rd.tightness, rd.violations);
            disc.push(rd);

            let rc = run_test("continuous", n, eps, base, snap_continuous, rng);
            print!("  | cont m={:.4} t={:.4} v={}", rc.max_hol, rc.tightness, rc.violations);
            cont.push(rc);

            println!();
        }
    }
    (disc, cont)
}

// ─── Reporting ───────────────────────────────────────────────────────────────

fn write_json(disc: &[TestResult], cont: &[TestResult]) {
    let path = "/home/phoenix/.openclaw/workspace/experiments/bounded-drift/results.json";
    fn ser(rs: &[TestResult], ind: &str) -> String {
        let mut s = String::from("[\n");
        for (i, r) in rs.iter().enumerate() {
            s.push_str(&format!(
                "{}  {{\"n\":{},\"eps\":{},\"trials\":{},\"bound\":{:.10},\"max_hol\":{:.10},\"mean_hol\":{:.10},\"min_hol\":{:.10},\"violations\":{},\"tightness\":{:.6}}}",
                ind, r.n, r.eps, r.trials, r.bound, r.max_hol, r.mean_hol, r.min_hol, r.violations, r.tightness
            ));
            if i+1 < rs.len() { s.push(','); } s.push('\n');
        }
        s.push_str(&format!("{}]", ind)); s
    }
    let (d_ok, c_ok) = (
        disc.iter().all(|r| r.violations == 0),
        cont.iter().all(|r| r.violations == 0),
    );
    let json = format!(
        r#"{{"exp":"Bounded Drift","thm":"hol ≤ nε","ts":"2026-05-13T10:27:00-08:00","R":{},"r":0.5,"models":{{"discrete":{{"desc":"random lattice within ε","holds":{},"viol":{},"res":{}}},"continuous":{{"desc":"noise in disk(ε-R)+snap. True err ≤ ε.","holds":{},"viol":{},"res":{}}}}}}}"#,
        voronoi_circumradius(),
        d_ok, !d_ok, ser(&disc, "          "),
        c_ok, !c_ok, ser(&cont, "          "),
    );
    File::create(path).unwrap().write_all(json.as_bytes()).unwrap();
    println!("  → {}", path);
}

fn analyze(label: &str, results: &[TestResult]) {
    println!("\n═══ {} MODEL ═══", label);
    let viol: Vec<_> = results.iter().filter(|r| r.violations > 0).collect();
    if viol.is_empty() {
        println!("  ✓ THEOREM HOLDS for all (n, ε) pairs");
    } else {
        println!("  ✗ {} configs have violations:", viol.len());
        for v in &viol { println!("    n={} ε={} {}v/{}t", v.n, v.eps, v.violations, v.trials); }
    }

    println!("  Tightness (max_hol / nε) by ε:");
    for eps in [0.01, 0.05, 0.1, 0.3, 0.5, 0.6, 0.8, 1.0, 1.5, 2.0, 5.0, 10.0] {
        let es = if eps < 1.0 { format!("{:.2}",eps) } else { format!("{:.0}",eps) };
        print!("    ε={:>4}: ", es);
        for r in results.iter().filter(|r| (r.eps-eps).abs() < 1e-10) {
            print!("n={}:{:.4} ", r.n, r.tightness);
        }
        println!();
    }

    let max_t = results.iter().map(|r| r.tightness).fold(0.0, f64::max);
    println!("  Max tightness: {:.4}", max_t);

    // Is the true bound a function of n and ε that's tighter than nε?
    println!("  Tightness trend: as n increases, tightness tends to (const) or decays?");
    // Group by ε and check tightness trend across n
    for eps in [1.0, 2.0, 5.0, 10.0] {
        let eps_rs: Vec<_> = results.iter().filter(|r| (r.eps-eps).abs() < 1e-10).collect();
        if eps_rs.len() >= 3 {
            let ts: Vec<_> = eps_rs.iter().map(|r| format!("{}:{:.4}", r.n, r.tightness)).collect();
            println!("    ε={}: {}", eps, ts.join(" "));
        }
    }
}

fn main() {
    println!("╔══════════════════════════════════════════════════════════════╗");
    println!("║       Bounded Drift Theorem — Experimental Verification     ║");
    println!("╚══════════════════════════════════════════════════════════════╝");
    println!("Theorem: hol ≤ nε   Voronoi R={:.3}", voronoi_circumradius());
    println!();

    let mut rng = rand::thread_rng();
    let (disc, cont) = run_all(&mut rng);

    write_json(&disc, &cont);
    analyze("Discrete", &disc);
    analyze("Continuous", &cont);

    println!("\n═══ VERDICT ═══");
    let all_pass = disc.iter().all(|r| r.violations==0) && cont.iter().all(|r| r.violations==0);
    if all_pass {
        println!("  ✓ THEOREM CONFIRMED: Bounded Drift holds for all tested configs");
        println!("  ✓ 0 violations across {} configurations × 5000 trials each", disc.len() + cont.len());
    } else {
        println!("  ⚠ SEE VIOLATIONS ABOVE");
    }
    println!();
}
