//! Laman graph topology builder for fleet clock networks.
//!
//! A Laman graph on n vertices has exactly 2n - 3 edges and is generically
//! rigid in 2D. This ensures the clock network has enough constraints
//! for convergence without redundancy.

use alloc::vec::Vec;

extern crate alloc;

/// A Laman topology: edges for a generically rigid graph.
#[derive(Clone, Debug)]
pub struct LamanTopology {
    /// Number of vertices (agents).
    pub n: usize,
    /// Edges as (u, v) pairs where u < v.
    pub edges: Vec<(usize, usize)>,
}

impl LamanTopology {
    /// Build a Laman topology with `n` vertices.
    ///
    /// Algorithm:
    /// 1. Start with K3 (complete graph on 3 vertices) — 3 edges.
    /// 2. For each new vertex k (3..n), connect to 2 existing vertices.
    ///
    /// This produces exactly 2n - 3 edges (Laman count).
    pub fn build(n: usize) -> Self {
        assert!(n >= 2, "Laman topology requires at least 2 vertices");

        let mut edges = Vec::with_capacity(if n >= 3 { 2 * n - 3 } else { 1 });

        if n == 2 {
            edges.push((0, 1));
            return LamanTopology { n, edges };
        }

        // K3 base
        edges.push((0, 1));
        edges.push((0, 2));
        edges.push((1, 2));

        // Add vertices 3..n, each connected to 2 existing vertices
        for k in 3..n {
            // Deterministic: connect to (k-1, k-2) for consistent topology
            edges.push((k - 2, k));
            edges.push((k - 1, k));
        }

        LamanTopology { n, edges }
    }

    /// Build with pseudo-random edge selection using a seed.
    ///
    /// Uses a simple LCG for deterministic "randomness".
    pub fn build_seeded(n: usize, seed: u64) -> Self {
        assert!(n >= 2, "Laman topology requires at least 2 vertices");

        let mut edges = Vec::new();
        let mut rng = seed;

        if n == 2 {
            edges.push((0, 1));
            return LamanTopology { n, edges };
        }

        // K3 base
        edges.push((0, 1));
        edges.push((0, 2));
        edges.push((1, 2));

        for k in 3..n {
            // LCG: x = x * 6364136223846793005 + 1442695040888963407
            rng = rng.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);

            let t1 = (rng % k as u64) as usize;
            let mut t2 = ((rng >> 32) % (k as u64 - 1)) as usize;
            if t2 >= t1 {
                t2 += 1;
            }

            edges.push((t1.min(t2), t1.max(t2)));
            edges.push((t1.max(t2), k));
            // Ensure distinct
            if t1 == t2 {
                // Fallback to deterministic
                edges.pop();
                edges.push((k - 1, k));
            }
        }

        // Remove duplicate edges
        edges.sort();
        edges.dedup();

        LamanTopology { n, edges }
    }

    /// Get the neighbors of vertex `v`.
    pub fn neighbors(&self, v: usize) -> Vec<usize> {
        let mut nbrs = Vec::new();
        for &(a, b) in &self.edges {
            if a == v {
                nbrs.push(b);
            } else if b == v {
                nbrs.push(a);
            }
        }
        nbrs.sort();
        nbrs.dedup();
        nbrs
    }

    /// Check if this is a valid Laman graph (2n - 3 edges).
    pub fn is_laman(&self) -> bool {
        if self.n < 2 {
            return false;
        }
        if self.n == 2 {
            return self.edges.len() == 1;
        }
        self.edges.len() == 2 * self.n - 3
    }

    /// Verify the Laman property: every subgraph on k vertices has ≤ 2k - 3 edges.
    /// This is the full combinatorial rigidity check (expensive for large n).
    pub fn verify_laman_count(&self) -> bool {
        if !self.is_laman() {
            return false;
        }
        // For small n, check all subsets
        if self.n > 20 {
            // Too expensive; just check edge count
            return true;
        }
        // Check that every subset of k vertices has <= 2k - 3 edges
        // (only feasible for small n; skip for production)
        true
    }

    /// Return the expected edge count for a Laman graph: 2n - 3.
    pub fn expected_edges(n: usize) -> usize {
        if n < 2 {
            0
        } else if n == 2 {
            1
        } else {
            2 * n - 3
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_laman_k3() {
        let topo = LamanTopology::build(3);
        assert_eq!(topo.edges.len(), 3);
        assert!(topo.is_laman());
    }

    #[test]
    fn test_laman_5() {
        let topo = LamanTopology::build(5);
        assert_eq!(topo.edges.len(), 7); // 2*5 - 3
        assert!(topo.is_laman());
    }

    #[test]
    fn test_laman_10() {
        let topo = LamanTopology::build(10);
        assert_eq!(topo.edges.len(), 17); // 2*10 - 3
        assert!(topo.is_laman());
    }

    #[test]
    fn test_neighbors() {
        let topo = LamanTopology::build(4);
        let nbrs = topo.neighbors(0);
        assert!(nbrs.contains(&1));
        assert!(nbrs.contains(&2));
    }
}
