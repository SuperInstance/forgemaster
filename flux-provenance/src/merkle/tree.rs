use sha2::{Digest, Sha256};

use super::leaf::Leaf;

/// A Merkle proof path element.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ProofElement {
    pub hash: String,
    pub side: Side,
}

#[derive(Debug, Clone, Copy, serde::Serialize, serde::Deserialize)]
pub enum Side {
    Left,
    Right,
}

/// A Merkle proof for a leaf.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct MerkleProof {
    pub leaf_hash: String,
    pub merkle_root: String,
    pub proof_path: Vec<ProofElement>,
}

/// An immutable Merkle tree built from a batch of leaves.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct MerkleTree {
    pub index: u64,
    pub leaves: Vec<Leaf>,
    pub root: String,
    /// Internal node hashes, level by level from bottom.
    nodes: Vec<Vec<String>>,
}

impl MerkleTree {
    /// Build a new Merkle tree from leaves.
    pub fn build(index: u64, leaves: Vec<Leaf>) -> Self {
        let hashes: Vec<String> = leaves.iter().map(|l| l.hash.clone()).collect();
        let (nodes, root) = build_tree(&hashes);
        Self {
            index,
            leaves,
            root,
            nodes,
        }
    }

    /// Build an empty tree (single sentinel node).
    pub fn empty(index: u64) -> Self {
        let root = hash_empty();
        Self {
            index,
            leaves: vec![],
            nodes: vec![],
            root,
        }
    }

    /// Generate a Merkle proof for a leaf at the given index.
    pub fn proof(&self, leaf_index: usize) -> Option<MerkleProof> {
        if leaf_index >= self.leaves.len() {
            return None;
        }

        let leaf_hash = self.leaves[leaf_index].hash.clone();
        let proof_path = build_proof(leaf_index, &self.nodes);

        Some(MerkleProof {
            leaf_hash,
            merkle_root: self.root.clone(),
            proof_path,
        })
    }

    /// Verify a proof against this tree's root.
    pub fn verify_proof(proof: &MerkleProof) -> bool {
        let mut current = proof.leaf_hash.clone();
        for elem in &proof.proof_path {
            current = match elem.side {
                Side::Left => hash_pair(&elem.hash, &current),
                Side::Right => hash_pair(&current, &elem.hash),
            };
        }
        current == proof.merkle_root
    }

    pub fn size(&self) -> usize {
        self.leaves.len()
    }
}

/// Build the tree, returning (nodes_per_level, root_hash).
fn build_tree(hashes: &[String]) -> (Vec<Vec<String>>, String) {
    if hashes.is_empty() {
        return (vec![], hash_empty());
    }

    let mut nodes = Vec::new();
    let mut current_level: Vec<String> = hashes.to_vec();

    while current_level.len() > 1 {
        let mut next_level = Vec::new();
        let pairs = current_level.chunks(2);
        for pair in pairs {
            let left = &pair[0];
            let right = if pair.len() > 1 {
                &pair[1]
            } else {
                // Odd node: duplicate
                &pair[0]
            };
            next_level.push(hash_pair(left, right));
        }
        nodes.push(current_level.clone());
        current_level = next_level;
    }

    (nodes, current_level[0].clone())
}

fn build_proof(index: usize, nodes: &[Vec<String>]) -> Vec<ProofElement> {
    let mut path = Vec::new();
    let mut idx = index;

    for level in nodes {
        if idx % 2 == 0 {
            // We're left; sibling is right (or self if odd-end)
            let sib = if idx + 1 < level.len() {
                level[idx + 1].clone()
            } else {
                level[idx].clone() // duplicated
            };
            path.push(ProofElement {
                hash: sib,
                side: Side::Right,
            });
        } else {
            // We're right; sibling is left
            path.push(ProofElement {
                hash: level[idx - 1].clone(),
                side: Side::Left,
            });
        }

        idx /= 2;
    }

    path
}

fn hash_pair(left: &str, right: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(left.as_bytes());
    hasher.update(right.as_bytes());
    format!("sha256:{}", hex::encode(hasher.finalize()))
}

fn hash_empty() -> String {
    let mut hasher = Sha256::new();
    hasher.update(b"");
    format!("sha256:{}", hex::encode(hasher.finalize()))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::merkle::leaf::{LeafData, VerificationTrace};

    fn make_leaf(i: usize) -> Leaf {
        Leaf::new(LeafData::Verification(VerificationTrace {
            trace: vec![format!("step_{}", i)],
            domain: "test".into(),
            confidence: 0.99,
            source: "test".into(),
        }))
    }

    #[test]
    fn test_tree_build_4_leaves() {
        let leaves: Vec<Leaf> = (0..4).map(make_leaf).collect();
        let tree = MerkleTree::build(0, leaves);
        assert!(tree.root.starts_with("sha256:"));
        assert_eq!(tree.size(), 4);
    }

    #[test]
    fn test_tree_build_1_leaf() {
        let leaves = vec![make_leaf(0)];
        let tree = MerkleTree::build(0, leaves);
        assert!(tree.root.starts_with("sha256:"));
        assert_eq!(tree.size(), 1);
    }

    #[test]
    fn test_tree_build_3_leaves_odd() {
        let leaves: Vec<Leaf> = (0..3).map(make_leaf).collect();
        let tree = MerkleTree::build(0, leaves);
        assert!(tree.root.starts_with("sha256:"));
        assert_eq!(tree.size(), 3);
    }

    #[test]
    fn test_proof_generation_and_verification() {
        let leaves: Vec<Leaf> = (0..4).map(make_leaf).collect();
        let tree = MerkleTree::build(0, leaves);

        for i in 0..4 {
            let proof = tree.proof(i).unwrap();
            assert_eq!(proof.leaf_hash, tree.leaves[i].hash);
            assert_eq!(proof.merkle_root, tree.root);
            assert!(MerkleTree::verify_proof(&proof));
        }
    }

    #[test]
    fn test_proof_invalid_leaf_hash() {
        let leaves: Vec<Leaf> = (0..4).map(make_leaf).collect();
        let tree = MerkleTree::build(0, leaves);
        let mut proof = tree.proof(0).unwrap();
        proof.leaf_hash = "sha256:deadbeef".into();
        assert!(!MerkleTree::verify_proof(&proof));
    }

    #[test]
    fn test_deterministic_root() {
        let leaves: Vec<Leaf> = (0..4).map(make_leaf).collect();
        let tree1 = MerkleTree::build(0, leaves.clone());
        let tree2 = MerkleTree::build(1, leaves);
        assert_eq!(tree1.root, tree2.root);
    }

    #[test]
    fn test_empty_tree() {
        let tree = MerkleTree::empty(0);
        assert!(tree.root.starts_with("sha256:"));
        assert_eq!(tree.size(), 0);
    }
}
