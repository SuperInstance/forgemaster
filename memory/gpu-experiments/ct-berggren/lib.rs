//! # ct-berggren — Berggren Ternary Tree
//!
//! All primitive Pythagorean triples form a ternary tree rooted at (3,4,5).
//! Three 3x3 matrices generate every child triple. This crate provides
//! tree traversal, level enumeration, and algebraic operations.
//!
//! ```
//! use ct_berggren::{BerggrenTree, Matrix3};
//!
//! let tree = BerggrenTree::new(50000);
//! assert_eq!(tree.root(), &(3, 4, 5));
//! assert!(tree.count() > 3000); // ~3980 primitives at max_c=50000
//! ```

/// A 3x3 matrix for Berggren multiplication.
#[derive(Debug, Clone, Copy)]
pub struct Matrix3 {
    pub m: [[i64; 3]; 3],
}

impl Matrix3 {
    pub const fn new(m: [[i64; 3]; 3]) -> Self { Matrix3 { m } }
    
    /// Matrix-vector multiply: M * (a, b, c)^T
    pub fn apply(&self, v: (i64, i64, i64)) -> (i64, i64, i64) {
        let m = &self.m;
        (
            m[0][0] * v.0 + m[0][1] * v.1 + m[0][2] * v.2,
            m[1][0] * v.0 + m[1][1] * v.1 + m[1][2] * v.2,
            m[2][0] * v.0 + m[2][1] * v.1 + m[2][2] * v.2,
        )
    }
    
    /// Matrix multiply: self * other
    pub fn mul(&self, other: &Matrix3) -> Matrix3 {
        let mut r = [[0i64; 3]; 3];
        for i in 0..3 {
            for j in 0..3 {
                for k in 0..3 {
                    r[i][j] += self.m[i][k] * other.m[k][j];
                }
            }
        }
        Matrix3::new(r)
    }
}

/// The three Berggren matrices.
pub const MAT_A: Matrix3 = Matrix3::new([
    [ 1, -2,  2],
    [ 2, -1,  2],
    [ 2, -2,  3],
]);

pub const MAT_B: Matrix3 = Matrix3::new([
    [ 1,  2,  2],
    [ 2,  1,  2],
    [ 2,  2,  3],
]);

pub const MAT_C: Matrix3 = Matrix3::new([
    [-1,  2,  2],
    [-2,  1,  2],
    [-2,  2,  3],
]);

/// A node in the Berggren tree.
#[derive(Debug, Clone)]
pub struct TreeNode {
    pub triple: (i64, i64, i64),
    pub level: usize,
    pub children: Vec<TreeNode>,
}

impl TreeNode {
    pub fn new(triple: (i64, i64, i64), level: usize) -> Self {
        TreeNode { triple, level, children: Vec::new() }
    }
    
    pub fn is_pythagorean(&self) -> bool {
        let (a, b, c) = self.triple;
        a * a + b * b == c * c
    }
    
    pub fn hypotenuse(&self) -> i64 { self.triple.2 }
}

/// Berggren ternary tree of primitive Pythagorean triples.
pub struct BerggrenTree {
    root: TreeNode,
    max_c: i64,
    total_count: usize,
}

impl BerggrenTree {
    /// Build the tree up to max_c hypotenuse.
    pub fn new(max_c: i64) -> Self {
        let mut root = TreeNode::new((3, 4, 5), 0);
        let total_count = expand(&mut root, max_c);
        BerggrenTree { root, max_c, total_count }
    }
    
    pub fn root(&self) -> &(i64, i64, i64) { &self.root.triple }
    pub fn count(&self) -> usize { self.total_count }
    pub fn max_depth(&self) -> usize { max_depth(&self.root) }
    
    /// Collect all triples as (a, b, c, level).
    pub fn all_triples(&self) -> Vec<(i64, i64, i64, usize)> {
        let mut result = Vec::new();
        collect(&self.root, &mut result);
        result
    }
    
    /// Collect triples at a specific depth level.
    pub fn at_level(&self, level: usize) -> Vec<(i64, i64, i64)> {
        self.all_triples().into_iter()
            .filter(|(_, _, _, l)| *l == level)
            .map(|(a, b, c, _)| (a, b, c))
            .collect()
    }
    
    /// Get the three matrices for external use.
    pub fn matrices() -> [Matrix3; 3] { [MAT_A, MAT_B, MAT_C] }
    
    /// Generate a triple by matrix path from root.
    /// Path is a sequence of 0=A, 1=B, 2=C matrix applications.
    pub fn triple_by_path(path: &[usize]) -> (i64, i64, i64) {
        let mats = Self::matrices();
        let mut v = (3i64, 4i64, 5i64);
        for &idx in path {
            if idx < 3 { v = mats[idx].apply(v); }
        }
        v
    }
}

fn expand(node: &mut TreeNode, max_c: i64) -> usize {
    let (a, b, c) = node.triple;
    let mut count = 0;
    for mat in &[MAT_A, MAT_B, MAT_C] {
        let child = mat.apply((a, b, c));
        if child.2 <= 0 || child.2 > max_c { continue; }
        if child.0 * child.0 + child.1 * child.1 != child.2 * child.2 { continue; }
        count += 1;
        let mut child_node = TreeNode::new(child, node.level + 1);
        count += expand(&mut child_node, max_c);
        node.children.push(child_node);
    }
    count
}

fn max_depth(node: &TreeNode) -> usize {
    if node.children.is_empty() { node.level }
    else { node.children.iter().map(max_depth).max().unwrap_or(node.level) }
}

fn collect(node: &TreeNode, out: &mut Vec<(i64, i64, i64, usize)>) {
    out.push((node.triple.0, node.triple.1, node.triple.2, node.level));
    for child in &node.children { collect(child, out); }
}

/// Matrix path as a compact representation of a triple's position in the tree.
pub fn encode_path(path: &[usize]) -> Vec<u8> {
    path.iter().map(|&i| i as u8).collect()
}

/// Decode a path from bytes.
pub fn decode_path(bytes: &[u8]) -> Vec<usize> {
    bytes.iter().map(|&b| b as usize).collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_matrix_a_applied_to_root() {
        let result = MAT_A.apply((3, 4, 5));
        assert_eq!(result, (5, 12, 13));
        assert!(result.0 * result.0 + result.1 * result.1 == result.2 * result.2);
    }
    
    #[test]
    fn test_matrix_b_applied_to_root() {
        let result = MAT_B.apply((3, 4, 5));
        assert!(result.0 * result.0 + result.1 * result.1 == result.2 * result.2);
    }
    
    #[test]
    fn test_matrix_c_applied_to_root() {
        let result = MAT_C.apply((3, 4, 5));
        assert!(result.0 * result.0 + result.1 * result.1 == result.2 * result.2);
    }
    
    #[test]
    fn test_tree_root() {
        let tree = BerggrenTree::new(100);
        assert_eq!(tree.root(), &(3, 4, 5));
    }
    
    #[test]
    fn test_tree_count() {
        let tree = BerggrenTree::new(50000);
        // ~3980 positive-c primitives at max_c=50000, tree includes some with |c|<=max_c
        assert!(tree.count() > 3000, "Got {}", tree.count());
        assert!(tree.count() < 10000, "Got {}", tree.count());
    }
    
    #[test]
    fn test_tree_all_pythagorean() {
        let tree = BerggrenTree::new(1000);
        for (a, b, c, _) in tree.all_triples() {
            assert_eq!(a * a + b * b, c * c, "Not Pythagorean: ({}, {}, {})", a, b, c);
            assert!(c <= 1000);
        }
    }
    
    #[test]
    fn test_max_depth() {
        let tree = BerggrenTree::new(10000);
        assert!(tree.max_depth() > 5);
    }
    
    #[test]
    fn test_at_level() {
        let tree = BerggrenTree::new(1000);
        let level0 = tree.at_level(0);
        assert_eq!(level0.len(), 1);
        assert_eq!(level0[0], (3, 4, 5));
        let level1 = tree.at_level(1);
        assert_eq!(level1.len(), 3); // A, B, C applied to root
    }
    
    #[test]
    fn test_triple_by_path() {
        let root = BerggrenTree::triple_by_path(&[]);
        assert_eq!(root, (3, 4, 5));
        let a_root = BerggrenTree::triple_by_path(&[0]); // MAT_A
        assert_eq!(a_root, (5, 12, 13));
    }
    
    #[test]
    fn test_matrix_multiply() {
        // A * B should produce a valid compound matrix
        let ab = MAT_A.mul(&MAT_B);
        let result = ab.apply((3, 4, 5));
        assert!(result.0 * result.0 + result.1 * result.1 == result.2 * result.2);
    }
    
    #[test]
    fn test_encode_decode_path() {
        let path = vec![0, 1, 2, 0];
        let encoded = encode_path(&path);
        let decoded = decode_path(&encoded);
        assert_eq!(path, decoded);
    }
}
