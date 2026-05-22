//! Laplacian eigenvalue computation for convergence analysis.
//!
//! Computes the algebraic connectivity (second-smallest eigenvalue of the
//! graph Laplacian) which bounds the convergence rate of clock sync.
//! Uses libm for f64 math operations (no_std compatible).

use crate::laman::LamanTopology;
use crate::fraction_clock::Fraction;

extern crate alloc;
use alloc::vec::Vec;

/// Spectral analysis result for a topology.
#[derive(Clone, Debug)]
pub struct SpectralResult {
    /// All eigenvalues of the graph Laplacian (sorted ascending).
    pub eigenvalues: Vec<f64>,
    /// Algebraic connectivity (2nd smallest eigenvalue).
    pub algebraic_connectivity: f64,
    /// Spectral gap (λ_2 / λ_max ratio).
    pub spectral_gap: f64,
}

/// Compute the graph Laplacian as a dense matrix.
///
/// L = D - A where D is degree matrix and A is adjacency matrix.
fn laplacian_matrix(topo: &LamanTopology) -> Vec<Vec<f64>> {
    let n = topo.n;
    let mut lap = vec![vec![0.0f64; n]; n];

    // Degree and adjacency
    for &(u, v) in &topo.edges {
        lap[u][v] = -1.0;
        lap[v][u] = -1.0;
        lap[u][u] += 1.0;
        lap[v][v] += 1.0;
    }

    lap
}

/// Compute eigenvalues using the power method + deflation.
///
/// For small matrices (n ≤ ~30), this is sufficient.
/// Returns eigenvalues sorted ascending.
pub fn eigenvalues(topo: &LamanTopology) -> Vec<f64> {
    let n = topo.n;
    if n == 0 {
        return vec![];
    }
    if n == 1 {
        return vec![0.0];
    }

    let mat = laplacian_matrix(topo);
    let mut eigs = Vec::with_capacity(n);

    // Use Gershgorin + QR-like iteration for small matrices
    // For practical purposes, use Jacobi eigenvalue algorithm (rotations)
    // Simplified: use power iteration to find dominant, then deflate

    // Actually, let's use a simpler approach for small matrices:
    // compute characteristic polynomial coefficients and find roots
    // For a Laplacian, we know λ1 = 0.

    // Use the fact that for connected graphs, λ1 = 0 and others > 0.
    // Estimate remaining eigenvalues via Rayleigh quotient iteration.

    // Simplified approach: tridiagonalize then use QR
    let mut a = mat.clone();

    // Tridiagonalize via Householder reflections
    for k in 0..n.saturating_sub(2) {
        // Compute Householder vector for column k
        let mut x = vec![0.0; n];
        for i in (k + 1)..n {
            x[i] = a[i][k];
        }

        let norm_x = {
            let mut s = 0.0;
            for i in (k + 1)..n {
                s += x[i] * x[i];
            }
            libm::sqrt(s)
        };

        if norm_x < 1e-15 {
            continue;
        }

        let sign = if x[k + 1] >= 0.0 { 1.0 } else { -1.0 };
        x[k + 1] += sign * norm_x;

        let norm_v = {
            let mut s = 0.0;
            for i in (k + 1)..n {
                s += x[i] * x[i];
            }
            libm::sqrt(s)
        };

        if norm_v < 1e-15 {
            continue;
        }

        for i in (k + 1)..n {
            x[i] /= norm_v;
        }

        // Apply: A = (I - 2vv^T) A (I - 2vv^T)
        // P = I - 2vv^T
        // A' = PAP
        for j in 0..n {
            let mut dot = 0.0f64;
            for i in (k + 1)..n {
                dot += x[i] * a[i][j];
            }
            for i in (k + 1)..n {
                a[i][j] -= 2.0 * x[i] * dot;
            }
        }

        for i in 0..n {
            let mut dot = 0.0f64;
            for j in (k + 1)..n {
                dot += x[j] * a[i][j];
            }
            for j in (k + 1)..n {
                a[i][j] -= 2.0 * dot * x[j];
            }
        }
    }

    // Now apply QR iteration on the tridiagonal-ish matrix
    for _iter in 0..100 * n {
        // Shifted QR step
        let shift = a[n - 1][n - 1];
        for i in 0..n {
            a[i][i] -= shift;
        }

        // Gram-Schmidt QR
        let mut q = vec![vec![0.0f64; n]; n];
        let mut r = vec![vec![0.0f64; n]; n];

        for j in 0..n {
            for i in 0..n {
                q[i][j] = a[i][j];
            }
            for k in 0..j {
                let mut dot = 0.0;
                for i in 0..n {
                    dot += q[i][j] * q[i][k];
                }
                r[k][j] = dot;
                for i in 0..n {
                    q[i][j] -= dot * q[i][k];
                }
            }
            let mut norm = 0.0;
            for i in 0..n {
                norm += q[i][j] * q[i][j];
            }
            norm = libm::sqrt(norm);
            r[j][j] = norm;
            if norm > 1e-15 {
                for i in 0..n {
                    q[i][j] /= norm;
                }
            }
        }

        // A = RQ + shift*I
        for i in 0..n {
            for j in 0..n {
                a[i][j] = 0.0;
                for k in 0..n {
                    a[i][j] += r[i][k] * q[k][j];
                }
            }
            a[i][i] += shift;
        }
    }

    // Extract diagonal as eigenvalues
    for i in 0..n {
        eigs.push(a[i][i]);
    }

    // Sort ascending
    eigs.sort_by(|a, b| a.partial_cmp(b).unwrap_or(core::cmp::Ordering::Equal));

    // Clamp small negatives to 0 (numerical noise)
    for e in &mut eigs {
        if *e < 0.0 && *e > -1e-8 {
            *e = 0.0;
        }
    }

    eigs
}

/// Compute spectral analysis of a Laman topology.
pub fn spectral_analysis(topo: &LamanTopology) -> SpectralResult {
    let eigs = eigenvalues(topo);
    let n = eigs.len();

    let algebraic_connectivity = if n >= 2 { eigs[1] } else { 0.0 };
    let spectral_gap = if n >= 2 && eigs[n - 1] > 1e-15 {
        algebraic_connectivity / eigs[n - 1]
    } else {
        0.0
    };

    SpectralResult {
        eigenvalues: eigs,
        algebraic_connectivity,
        spectral_gap,
    }
}

/// Estimate convergence time for a Laman topology.
///
/// Convergence time ~ 1 / algebraic_connectivity.
pub fn convergence_time(topo: &LamanTopology) -> f64 {
    let result = spectral_analysis(topo);
    if result.algebraic_connectivity > 1e-15 {
        1.0 / result.algebraic_connectivity
    } else {
        f64::INFINITY
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_k3_eigenvalues() {
        let topo = LamanTopology::build(3);
        let eigs = eigenvalues(&topo);
        assert_eq!(eigs.len(), 3);
        // K3 Laplacian has eigenvalues 0, 3, 3
        assert!(eigs[0].abs() < 0.5); // ~0
        assert!((eigs[1] - 3.0).abs() < 0.5);
        assert!((eigs[2] - 3.0).abs() < 0.5);
    }

    #[test]
    fn test_algebraic_connectivity_positive() {
        let topo = LamanTopology::build(5);
        let result = spectral_analysis(&topo);
        assert!(result.algebraic_connectivity > 0.0);
    }

    #[test]
    fn test_spectral_gap() {
        let topo = LamanTopology::build(5);
        let result = spectral_analysis(&topo);
        assert!(result.spectral_gap > 0.0);
        assert!(result.spectral_gap <= 1.0);
    }
}
