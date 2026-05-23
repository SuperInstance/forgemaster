//! Merkle tree over verification traces using SHA-256.

use sha2::{Sha256, Digest};
use alloc::vec::Vec;
use crate::provenance::VerificationTrace;

/// SHA-256 hash output.
pub type Hash = [u8; 32];

/// A simple binary Merkle tree over verification trace hashes.
#[derive(Clone, Debug)]
pub struct MerkleTree {
    leaves: Vec<Hash>,
    root: Hash,
}

impl MerkleTree {
    /// Build a Merkle tree from verification traces.
    pub fn from_traces(traces: &[VerificationTrace]) -> Self {
        let leaves: Vec<Hash> = traces.iter().map(|t| t.hash()).collect();
        let root = Self::compute_root(&leaves);
        MerkleTree { leaves, root }
    }

    /// Build from raw leaf hashes.
    pub fn from_hashes(hashes: Vec<Hash>) -> Self {
        let root = Self::compute_root(&hashes);
        MerkleTree { leaves: hashes, root }
    }

    /// Empty tree with a zero root.
    pub fn empty() -> Self {
        MerkleTree {
            leaves: Vec::new(),
            root: [0u8; 32],
        }
    }

    /// Return the Merkle root.
    pub fn root(&self) -> &Hash {
        &self.root
    }

    /// Number of leaves.
    pub fn len(&self) -> usize {
        self.leaves.len()
    }

    pub fn is_empty(&self) -> bool {
        self.leaves.is_empty()
    }

    /// Get a leaf hash by index.
    pub fn leaf(&self, index: usize) -> Option<&Hash> {
        self.leaves.get(index)
    }

    fn compute_root(leaves: &[Hash]) -> Hash {
        if leaves.is_empty() {
            return [0u8; 32];
        }
        if leaves.len() == 1 {
            return leaves[0];
        }

        let mut layer: Vec<Hash> = leaves.to_vec();
        while layer.len() > 1 {
            let mut next = Vec::new();
            let mut i = 0;
            while i < layer.len() {
                let left = layer[i];
                let right = if i + 1 < layer.len() { layer[i + 1] } else { left };
                next.push(hash_pair(&left, &right));
                i += 2;
            }
            layer = next;
        }
        layer[0]
    }
}

/// Hash a pair of nodes.
fn hash_pair(a: &Hash, b: &Hash) -> Hash {
    let mut hasher = Sha256::new();
    hasher.update(a);
    hasher.update(b);
    let result: [u8; 32] = hasher.finalize().into();
    result
}

#[cfg(test)]
mod tests {
    use super::*;
    use alloc::vec;

    #[test]
    fn empty_tree() {
        let tree = MerkleTree::empty();
        assert!(tree.is_empty());
        assert_eq!(*tree.root(), [0u8; 32]);
    }

    #[test]
    fn single_leaf() {
        let leaf = [0xAB; 32];
        let tree = MerkleTree::from_hashes(vec![leaf]);
        assert_eq!(tree.len(), 1);
        assert_eq!(*tree.root(), leaf);
    }

    #[test]
    fn two_leaves() {
        let a = [0xAA; 32];
        let b = [0xBB; 32];
        let tree = MerkleTree::from_hashes(vec![a, b]);
        assert_eq!(tree.len(), 2);
        assert_eq!(*tree.root(), hash_pair(&a, &b));
    }

    #[test]
    fn three_leaves_deterministic() {
        let a = [0x01; 32];
        let b = [0x02; 32];
        let c = [0x03; 32];
        let tree1 = MerkleTree::from_hashes(vec![a, b, c]);
        let tree2 = MerkleTree::from_hashes(vec![a, b, c]);
        assert_eq!(tree1.root(), tree2.root());
    }
}
