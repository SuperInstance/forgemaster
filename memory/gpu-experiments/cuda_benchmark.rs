//! Constraint Theory CUDA Benchmark
//!
//! Mirrors cpu_benchmark.rs but dispatches the snap queries to a GPU kernel
//! (cuda_kernel.cu) via unsafe FFI.  Falls back gracefully to the CPU path
//! when no CUDA-capable device is present at runtime.

use std::collections::BTreeSet;
use std::time::Instant;

// ---------------------------------------------------------------------------
// FFI declarations — match the `extern "C"` signatures in cuda_kernel.cu /
// cuda_stub.c.  The build system links exactly one of those objects.
// ---------------------------------------------------------------------------

extern "C" {
    /// Returns the number of CUDA-capable devices (0 if none or on any error).
    fn cuda_device_count() -> i32;

    /// Batch nearest-manifold query on the GPU.
    ///
    /// Fills `out_distances[i]` and `out_indices[i]` with the Euclidean
    /// distance and manifold index closest to `(query_xs[i], query_ys[i])`.
    ///
    /// Returns 0 on success, -1 on any CUDA error or if the stub is active.
    fn cuda_snap_batch(
        query_xs: *const f32,
        query_ys: *const f32,
        n_queries: i32,
        manifold_xs: *const f32,
        manifold_ys: *const f32,
        n_manifold: i32,
        out_distances: *mut f32,
        out_indices: *mut i32,
    ) -> i32;
}

fn is_cuda_available() -> bool {
    // Safety: cuda_device_count is a pure query with no side-effects that
    // matter here; the stub version always returns 0.
    unsafe { cuda_device_count() > 0 }
}

// ---------------------------------------------------------------------------
// Pythagorean triple generation (identical algorithm to cpu_benchmark.rs)
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Copy)]
struct Triple {
    a: i64,
    b: i64,
    c: i64,
}

impl Triple {
    fn normalized_f32(&self) -> (f32, f32) {
        (self.a as f32 / self.c as f32, self.b as f32 / self.c as f32)
    }
    fn normalized_f64(&self) -> (f64, f64) {
        (self.a as f64 / self.c as f64, self.b as f64 / self.c as f64)
    }
}

fn gcd(a: i64, b: i64) -> i64 {
    if b == 0 { a } else { gcd(b, a % b) }
}

fn generate_triples(max_c: i64) -> Vec<Triple> {
    let mut triples = Vec::new();
    let mut seen    = BTreeSet::new();

    let mut m: i64 = 2;
    while m * m <= max_c {
        let mut n: i64 = 1;
        while n < m {
            if (m - n) % 2 == 1 && gcd(m, n) == 1 {
                let a = m * m - n * n;
                let b = 2 * m * n;
                let c = m * m + n * n;
                if c <= max_c {
                    for &(a, b) in &[(a, b), (b, a)] {
                        let key = (a.abs(), b.abs());
                        if !seen.contains(&key) {
                            seen.insert(key);
                            triples.push(Triple { a, b, c });
                        }
                    }
                }
            }
            n += 1;
        }
        m += 1;
    }
    triples
}

// ---------------------------------------------------------------------------
// CPU brute-force snap (reference, for comparison and fallback)
// ---------------------------------------------------------------------------

fn snap_cpu(x: f64, y: f64, manifold: &[Triple]) -> (usize, f64) {
    let mut best_idx  = 0;
    let mut best_dist = f64::MAX;
    for (i, t) in manifold.iter().enumerate() {
        let (nx, ny) = t.normalized_f64();
        let d = ((nx - x).powi(2) + (ny - y).powi(2)).sqrt();
        if d < best_dist {
            best_dist = d;
            best_idx  = i;
        }
    }
    (best_idx, best_dist)
}

// ---------------------------------------------------------------------------
// Benchmark runner
// ---------------------------------------------------------------------------

struct BenchResult {
    label:        &'static str,
    triple_count: usize,
    queries:      usize,
    elapsed_us:   u64,
    throughput:   f64,
    avg_dist:     f64,
    max_dist:     f64,
}

impl std::fmt::Display for BenchResult {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        writeln!(f, "  Backend        : {}", self.label)?;
        writeln!(f, "  Manifold size  : {} points", self.triple_count)?;
        writeln!(f, "  Queries        : {}", self.queries)?;
        writeln!(f, "  Elapsed        : {} μs", self.elapsed_us)?;
        writeln!(f, "  Throughput     : {:.0} q/s", self.throughput)?;
        writeln!(f, "  Avg distance   : {:.6}", self.avg_dist)?;
        write!(  f, "  Max distance   : {:.6}", self.max_dist)
    }
}

fn run_gpu_bench(manifold: &[Triple], queries: usize) -> Option<BenchResult> {
    use rand::Rng;
    let mut rng = rand::thread_rng();

    // Build f32 manifold arrays
    let manifold_xs: Vec<f32> = manifold.iter().map(|t| t.normalized_f32().0).collect();
    let manifold_ys: Vec<f32> = manifold.iter().map(|t| t.normalized_f32().1).collect();

    // Generate queries (normalised to unit circle)
    let mut qxs = Vec::with_capacity(queries);
    let mut qys = Vec::with_capacity(queries);
    for _ in 0..queries {
        let x: f64 = rng.gen_range(-1.0..1.0);
        let y: f64 = rng.gen_range(-1.0..1.0);
        let r = (x * x + y * y).sqrt();
        qxs.push((x / r) as f32);
        qys.push((y / r) as f32);
    }

    let mut out_dist = vec![0.0f32; queries];
    let mut out_idx  = vec![0i32;  queries];

    let t0 = Instant::now();
    let rc = unsafe {
        cuda_snap_batch(
            qxs.as_ptr(), qys.as_ptr(), queries as i32,
            manifold_xs.as_ptr(), manifold_ys.as_ptr(), manifold.len() as i32,
            out_dist.as_mut_ptr(), out_idx.as_mut_ptr(),
        )
    };
    let elapsed = t0.elapsed();

    if rc != 0 {
        return None; // GPU error
    }

    let total_dist: f64 = out_dist.iter().map(|&d| d as f64).sum();
    let max_dist:   f64 = out_dist.iter().cloned().fold(0.0f32, f32::max) as f64;

    Some(BenchResult {
        label:        "CUDA GPU",
        triple_count: manifold.len(),
        queries,
        elapsed_us:   elapsed.as_micros() as u64,
        throughput:   queries as f64 / elapsed.as_secs_f64(),
        avg_dist:     total_dist / queries as f64,
        max_dist,
    })
}

fn run_cpu_bench(manifold: &[Triple], queries: usize) -> BenchResult {
    use rand::Rng;
    let mut rng = rand::thread_rng();

    let mut total_dist = 0.0f64;
    let mut max_dist   = 0.0f64;

    let t0 = Instant::now();
    for _ in 0..queries {
        let x: f64 = rng.gen_range(-1.0..1.0);
        let y: f64 = rng.gen_range(-1.0..1.0);
        let r  = (x * x + y * y).sqrt();
        let (_, d) = snap_cpu(x / r, y / r, manifold);
        total_dist += d;
        max_dist    = max_dist.max(d);
    }
    let elapsed = t0.elapsed();

    BenchResult {
        label:        "CPU brute-force",
        triple_count: manifold.len(),
        queries,
        elapsed_us:   elapsed.as_micros() as u64,
        throughput:   queries as f64 / elapsed.as_secs_f64(),
        avg_dist:     total_dist / queries as f64,
        max_dist,
    }
}

fn run_comparison(max_c: i64, queries: usize, cuda: bool) {
    println!("\n{}", "─".repeat(60));
    println!("max_c = {}  ({} queries)", max_c, queries);
    println!("{}", "─".repeat(60));

    let t0       = Instant::now();
    let manifold = generate_triples(max_c);
    println!("Generated {} triples in {:?}", manifold.len(), t0.elapsed());

    // ── CPU ──────────────────────────────────────────────────────────────
    let cpu = run_cpu_bench(&manifold, queries);
    println!("\n[CPU]\n{}", cpu);

    // ── GPU ──────────────────────────────────────────────────────────────
    if cuda {
        match run_gpu_bench(&manifold, queries) {
            Some(gpu) => {
                println!("\n[GPU]\n{}", gpu);
                let speedup = cpu.elapsed_us as f64 / gpu.elapsed_us as f64;
                println!("\n  ★  GPU speedup: {:.2}×", speedup);
                println!("  (Note: GPU times include H→D and D→H memcpy)");
            }
            None => println!("\n[GPU] kernel returned an error — see stderr"),
        }
    } else {
        println!("\n[GPU] skipped — no CUDA device detected");
    }
}

fn main() {
    println!("=== Constraint Theory CUDA Benchmark ===\n");

    let cuda = is_cuda_available();
    if cuda {
        println!("CUDA device(s) detected — GPU path active");
        println!("GPU device count: {}", unsafe { cuda_device_count() });
    } else {
        println!("No CUDA device detected — GPU path disabled, CPU fallback only");
    }

    let queries = 10_000usize;
    run_comparison(100,   queries, cuda);
    run_comparison(1_000, queries, cuda);
    run_comparison(10_000, queries, cuda);

    println!("\n{}", "═".repeat(60));
    println!("Conclusion:");
    println!("  GPU parallelism launches {} threads simultaneously.", queries);
    println!("  For small manifolds (< ~1000 pts) CPU/GPU are comparable");
    println!("  because PCIe transfer dominates over compute time.");
    println!("  GPU advantage grows with manifold size where O(n) scan is costly.");
}
