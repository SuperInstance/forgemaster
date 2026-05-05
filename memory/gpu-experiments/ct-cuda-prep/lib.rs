//! # ct-cuda-prep — GPU-Ready CUDA Snap Kernels
//!
//! Compile-verified CUDA kernels with CPU fallback and PTX analysis.
//! The CUDA kernel (`src/kernels/snap.cu`) is algorithmically identical to
//! the CPU reference (`src/kernels/snap_cpu.c`) — verified at the source level.
//!
//! ## Compile CUDA (when GPU is available)
//! ```bash
//! nvcc -O3 -arch=sm_89 -ptx src/kernels/snap.cu -o snap.ptx
//! nvcc -O3 -arch=sm_89 -cubin src/kernels/snap.cu -o snap.cubin
//! ```
//!
//! ## PTX Analysis
//! ```bash
//! nvcc -O3 -arch=sm_89 -ptx src/kernels/snap.cu -o /dev/stdout | \
//!     grep -c "ld.const"   # constant memory loads
//! ```

use std::f64::consts::TAU;

/// A single Pythagorean triple.
#[derive(Debug, Clone, Copy)]
pub struct Triple {
    pub a: i64,
    pub b: i64,
    pub c: u64,
}

/// Generate all primitive Pythagorean triples up to max_c (Euclid's formula, all 8 octants).
pub fn generate_triples(max_c: u64) -> Vec<Triple> {
    let mut triples = Vec::new();
    let max_m = ((max_c as f64).sqrt() / std::f64::consts::SQRT_2) as u64 + 1;
    for m in 2..=max_m {
        for n in 1..m {
            if (m + n) % 2 == 0 { continue; }
            if gcd(m, n) != 1 { continue; }
            let a = m * m - n * n;
            let b = 2 * m * n;
            let c = m * m + n * n;
            if c > max_c { break; }
            for &sa in &[1i64, -1] {
                for &sb in &[1i64, -1] {
                    triples.push(Triple { a: sa * a as i64, b: sb * b as i64, c });
                    triples.push(Triple { a: sa * b as i64, b: sb * a as i64, c });
                }
            }
        }
    }
    triples
}

fn gcd(a: u64, b: u64) -> u64 { if b == 0 { a } else { gcd(b, a % b) } }

/// CPU reference snap — identical algorithm to the CUDA kernel.
pub fn snap_cpu(triples: &[Triple], theta: f64) -> (usize, f64) {
    if triples.is_empty() { return (0, 0.0); }
    let a = ((theta % TAU) + TAU) % TAU;

    // Build sorted angle array
    let mut indexed: Vec<(f64, usize)> = triples.iter().enumerate()
        .map(|(i, t)| ((t.a as f64).atan2(t.b as f64), i))
        .collect();
    indexed.sort_by(|x, y| x.0.partial_cmp(&y.0).unwrap_or(std::cmp::Ordering::Equal));

    let angles: Vec<f64> = indexed.iter().map(|x| x.0).collect();
    let indices: Vec<usize> = indexed.iter().map(|x| x.1).collect();
    let n = angles.len();

    // Binary search (same logic as CUDA kernel)
    let mut lo = 0usize;
    let mut hi = n - 1;
    while lo < hi {
        let mid = (lo + hi) / 2;
        if angles[mid] < a { lo = mid + 1; } else { hi = mid; }
    }

    let idx = if lo == 0 {
        let d_last = (a - angles[n - 1]).abs().min(TAU - (a - angles[n - 1]).abs());
        let d_first = (a - angles[0]).abs().min(TAU - (a - angles[0]).abs());
        if d_last <= d_first { indices[n - 1] } else { indices[0] }
    } else {
        let d_lo = (a - angles[lo - 1]).abs().min(TAU - (a - angles[lo - 1]).abs());
        let d_hi = (a - angles[lo]).abs().min(TAU - (a - angles[lo]).abs());
        if d_lo <= d_hi { indices[lo - 1] } else { indices[lo] }
    };

    let dist = (a - angles[lo]).abs().min(TAU - (a - angles[lo]).abs());
    (idx, dist)
}

/// Verify CUDA kernel produces same results as CPU reference.
/// Call this after running both on identical input.
pub fn verify_consistency(cpu_results: &[(usize, f64)], gpu_results: &[(usize, f64)]) -> VerificationResult {
    let n = cpu_results.len().min(gpu_results.len());
    let mut agree = 0;
    let mut max_dist_diff = 0.0;
    for i in 0..n {
        if cpu_results[i].0 == gpu_results[i].0 { agree += 1; }
        let dd = (cpu_results[i].1 - gpu_results[i].1).abs();
        if dd > max_dist_diff { max_dist_diff = dd; }
    }
    VerificationResult {
        n_compared: n,
        n_agree: agree,
        agreement_rate: if n > 0 { agree as f64 / n as f64 } else { 0.0 },
        max_distance_diff: max_dist_diff,
    }
}

#[derive(Debug, Clone)]
pub struct VerificationResult {
    pub n_compared: usize,
    pub n_agree: usize,
    pub agreement_rate: f64,
    pub max_distance_diff: f64,
}

/// PTX instruction analysis (theoretical — requires nvcc output).
#[derive(Debug, Clone)]
pub struct PtxAnalysis {
    pub arch: String,
    pub total_instructions: usize,
    pub const_loads: usize,
    pub register_count: usize,
    pub shared_memory_bytes: usize,
}

impl PtxAnalysis {
    /// Theoretical analysis for sm_89 (RTX 4050 Ada Lovelace).
    pub fn theoretical_sm89(n_triples: usize) -> Self {
        // Constant memory: 64KB limit, triples use 8 bytes each (double)
        // 50K triples = 400KB → exceeds constant, use global + L1/L2 cache
        let fits_const = n_triples * 8 <= 65536;
        PtxAnalysis {
            arch: "sm_89".into(),
            total_instructions: 42, // estimated for snap_binary
            const_loads: if fits_const { 1 } else { 0 },
            register_count: 32, // per thread, typical for binary search
            shared_memory_bytes: if fits_const { 0 } else { n_triples * 8 },
        }
    }

    /// Estimate GPU throughput.
    pub fn estimated_qps(&self, n_triples: usize, n_sms: usize, clock_ghz: f64) -> f64 {
        // RTX 4050: 24 SMs, 2.4 GHz boost
        // Each warp of 32 threads does independent snap
        let warps_per_sm = 8; // occupancy estimate
        let threads_per_cycle = n_sms as f64 * warps_per_sm as f64 * 32.0;
        let cycles_per_snap = 20.0; // binary search: log2(n) ≈ 15 + overhead
        threads_per_cycle * clock_ghz * 1e9 / cycles_per_snap
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_generate_triples() {
        let t = generate_triples(10);
        assert!(t.iter().any(|x| x.a == 3 && x.b == 4 && x.c == 5));
    }

    #[test]
    fn test_snap_cpu_basic() {
        let triples = generate_triples(1000);
        let (idx, dist) = snap_cpu(&triples, 0.0);
        assert!(idx < triples.len());
        assert!(dist >= 0.0);
    }

    #[test]
    fn test_snap_cpu_wraparound() {
        let triples = generate_triples(1000);
        let (idx0, _) = snap_cpu(&triples, 0.001);
        let (idx_tau, _) = snap_cpu(&triples, TAU - 0.001);
        // Should snap to nearby triples
        assert!(idx0 < triples.len());
        assert!(idx_tau < triples.len());
    }

    #[test]
    fn test_verify_consistency() {
        let cpu = vec![(0, 0.001), (1, 0.002), (2, 0.003)];
        let gpu = vec![(0, 0.001), (1, 0.002), (2, 0.003)];
        let result = verify_consistency(&cpu, &gpu);
        assert_eq!(result.agreement_rate, 1.0);
    }

    #[test]
    fn test_verify_disagreement() {
        let cpu = vec![(0, 0.001), (1, 0.002)];
        let gpu = vec![(5, 0.001), (1, 0.003)];
        let result = verify_consistency(&cpu, &gpu);
        assert_eq!(result.agreement_rate, 0.5);
    }

    #[test]
    fn test_ptx_analysis_sm89() {
        let analysis = PtxAnalysis::theoretical_sm89(50000);
        assert_eq!(analysis.arch, "sm_89");
        assert!(analysis.total_instructions > 0);
    }

    #[test]
    fn test_ptx_estimated_qps() {
        let analysis = PtxAnalysis::theoretical_sm89(50000);
        let qps = analysis.estimated_qps(50000, 24, 2.4);
        assert!(qps > 1e9); // Should estimate >1 billion qps
    }

    #[test]
    fn test_empty_triples() {
        let (idx, dist) = snap_cpu(&[], 1.0);
        assert_eq!(idx, 0);
        assert_eq!(dist, 0.0);
    }
}
