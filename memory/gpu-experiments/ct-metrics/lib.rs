//! # Constraint Theory Metrics
//!
//! Benchmarking and analysis tools for Pythagorean manifold operations.
//! Provides distribution analysis, correctness verification, and performance measurement.

use std::f64::consts::PI;

/// A data point from a snap benchmark.
#[derive(Debug, Clone)]
pub struct SnapResult {
    pub query_angle: f64,
    pub snapped_angle: f64,
    pub triple_a: i64,
    pub triple_b: i64,
    pub triple_c: u64,
    pub constraint_distance: f64,
}

/// Distribution analysis of angular data.
#[derive(Debug, Clone)]
pub struct DistributionAnalysis {
    pub n_points: usize,
    pub n_bins: usize,
    pub min_count: usize,
    pub max_count: usize,
    pub mean_count: f64,
    pub std_dev: f64,
    pub cv: f64,
    pub bins: Vec<usize>,
    pub is_uniform: bool,
}

impl DistributionAnalysis {
    /// Create a new distribution analysis from angle data.
    pub fn from_angles(angles: &[f64], n_bins: usize) -> Self {
        let n = angles.len();
        let mut bins = vec![0usize; n_bins];
        for angle in angles {
            let a = ((angle % (2.0 * PI)) + 2.0 * PI) % (2.0 * PI);
            let b = ((a / (2.0 * PI)) * n_bins as f64) as usize % n_bins;
            bins[b] += 1;
        }
        let mean = n as f64 / n_bins as f64;
        let var: f64 = bins.iter().map(|c| (*c as f64 - mean).powi(2)).sum::<f64>() / n_bins as f64;
        let std_dev = var.sqrt();
        let cv = if mean > 0.0 { std_dev / mean } else { 0.0 };
        let min_count = *bins.iter().min().unwrap_or(&0);
        let max_count = *bins.iter().max().unwrap_or(&0);
        DistributionAnalysis {
            n_points: n, n_bins, min_count, max_count, mean_count: mean,
            std_dev, cv, bins, is_uniform: cv < 0.3,
        }
    }
}

/// Correctness verification result.
#[derive(Debug, Clone)]
pub struct CorrectnessReport {
    pub n_queries: usize,
    pub n_agree: usize,
    pub n_disagree: usize,
    pub agreement_rate: f64,
    pub max_angular_error: f64,
    pub mean_angular_error: f64,
    pub all_agree: bool,
}

impl CorrectnessReport {
    /// Verify binary search against brute force.
    pub fn verify(
        angles: &[f64],
        binary_snap: impl Fn(f64) -> usize,
        brute_snap: impl Fn(f64) -> usize,
        n_queries: usize,
    ) -> Self {
        let mut agree = 0usize;
        let mut max_err = 0.0f64;
        let mut sum_err = 0.0f64;
        let step = 2.0 * PI / n_queries as f64;

        for i in 0..n_queries {
            let theta = i as f64 * step;
            let bs = binary_snap(theta);
            let bf = brute_snap(theta);
            if bs == bf {
                agree += 1;
            } else {
                let err = angle_diff(angles[bs], angles[bf]);
                max_err = max_err.max(err);
                sum_err += err;
            }
        }

        let disagree = n_queries - agree;
        CorrectnessReport {
            n_queries, n_agree: agree, n_disagree: disagree,
            agreement_rate: agree as f64 / n_queries as f64,
            max_angular_error: max_err,
            mean_angular_error: if disagree > 0 { sum_err / disagree as f64 } else { 0.0 },
            all_agree: disagree == 0,
        }
    }
}

/// Performance benchmark result.
#[derive(Debug, Clone)]
pub struct BenchmarkResult {
    pub n_queries: usize,
    pub elapsed_secs: f64,
    pub qps: f64,
    pub strategy_name: String,
}

impl BenchmarkResult {
    /// Run a benchmark of the given snap function.
    pub fn benchmark<F: Fn(f64) -> usize>(snap: F, n_queries: usize, strategy_name: &str) -> Self {
        let start = std::time::Instant::now();
        let step = 2.0 * PI / n_queries as f64;
        let mut sum = 0u64;
        for i in 0..n_queries {
            let idx = snap(i as f64 * step);
            // Prevent optimization
            sum = sum.wrapping_add(idx as u64);
        }
        let elapsed = start.elapsed().as_secs_f64();
        std::hint::black_box(sum);
        BenchmarkResult {
            n_queries, elapsed_secs: elapsed,
            qps: if elapsed > 0.0 { n_queries as f64 / elapsed } else { 0.0 },
            strategy_name: strategy_name.to_string(),
        }
    }
}

/// Angular difference on [0, 2π).
pub fn angle_diff(a: f64, b: f64) -> f64 {
    let d = (a - b).abs();
    d.min(2.0 * PI - d)
}

/// Pretty-print a benchmark comparison table.
pub fn print_comparison(results: &[BenchmarkResult]) {
    if results.is_empty() { return; }
    let base_qps = results.last().map(|r| r.qps).unwrap_or(1.0);
    println!("┌─────────────────────┬──────────────┬────────────┐");
    println!("│ Strategy            │ qps          │ Speedup    │");
    println!("├─────────────────────┼──────────────┼────────────┤");
    for r in results.iter().rev() {
        let speedup = r.qps / base_qps;
        println!("│ {:<19} │ {:>12.0} │ {:>8.1}x   │", r.strategy_name, r.qps, speedup);
    }
    println!("└─────────────────────┴──────────────┴────────────┘");
}

/// Pretty-print distribution histogram.
pub fn print_histogram(analysis: &DistributionAnalysis, bin_width_deg: f64) {
    println!("\n  Distribution ({} bins × {}°):", analysis.n_bins, bin_width_deg);
    println!("    CV: {:.3} ({})", analysis.cv, if analysis.is_uniform { "roughly uniform" } else { "non-uniform" });
    let bar_scale = 12.0 / analysis.mean_count.max(1.0);
    for (i, count) in analysis.bins.iter().enumerate() {
        let bar_len = (*count as f64 * bar_scale) as usize;
        let bar: String = "█".repeat(bar_len.max(1));
        println!("    {:>5.0}°-{:>5.0}° │{}│ {}", 
            i as f64 * bin_width_deg, (i + 1) as f64 * bin_width_deg, bar, count);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_angle_diff_zero() {
        assert!((angle_diff(1.0, 1.0) - 0.0).abs() < 1e-10);
    }

    #[test]
    fn test_angle_diff_pi() {
        assert!((angle_diff(0.0, PI) - PI).abs() < 1e-10);
    }

    #[test]
    fn test_angle_diff_wrap() {
        assert!((angle_diff(0.01, 2.0 * PI - 0.01) - 0.02).abs() < 1e-10);
    }

    #[test]
    fn test_distribution_uniform() {
        let angles: Vec<f64> = (0..1000).map(|i| i as f64 / 1000.0 * 2.0 * PI).collect();
        let analysis = DistributionAnalysis::from_angles(&angles, 10);
        assert!(analysis.is_uniform);
        assert_eq!(analysis.n_points, 1000);
    }

    #[test]
    fn test_distribution_nonuniform() {
        // All angles in first bin
        let angles: Vec<f64> = (0..1000).map(|_| 0.1).collect();
        let analysis = DistributionAnalysis::from_angles(&angles, 10);
        assert!(!analysis.is_uniform);
        assert!(analysis.cv > 2.0);
    }

    #[test]
    fn test_correctness_perfect() {
        let angles: Vec<f64> = (0..100).map(|i| i as f64 / 100.0 * 2.0 * PI).collect();
        let snap = |theta: f64| -> usize { (theta / (2.0 * PI) * 100.0) as usize % 100 };
        let report = CorrectnessReport::verify(&angles, snap, snap, 1000);
        assert!(report.all_agree);
        assert_eq!(report.agreement_rate, 1.0);
    }

    #[test]
    fn test_benchmark_runs() {
        let snap = |theta: f64| -> usize { (theta / (2.0 * PI) * 100.0) as usize % 100 };
        let result = BenchmarkResult::benchmark(snap, 10000, "test");
        assert!(result.qps > 0.0);
        assert_eq!(result.n_queries, 10000);
    }

    #[test]
    fn test_print_doesnt_panic() {
        let results = vec![
            BenchmarkResult { n_queries: 1000, elapsed_secs: 0.1, qps: 10000.0, strategy_name: "fast".into() },
            BenchmarkResult { n_queries: 1000, elapsed_secs: 1.0, qps: 1000.0, strategy_name: "slow".into() },
        ];
        print_comparison(&results); // Should not panic
        let angles: Vec<f64> = (0..100).map(|i| i as f64 / 100.0 * 2.0 * PI).collect();
        let analysis = DistributionAnalysis::from_angles(&angles, 10);
        print_histogram(&analysis, 36.0); // Should not panic
    }
}
