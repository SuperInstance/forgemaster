use sled::Db;

use crate::merkle::{Leaf, MerkleTree};

const TREES_TREE: &str = "merkle_trees";
const LEAVES_TREE: &str = "leaves";
const META_TREE: &str = "meta";
const CURRENT_LEAVES_KEY: &str = "current_leaves";

/// Sled-backed persistent store for Merkle trees.
pub struct ProvenanceStore {
    db: Db,
    batch_size: usize,
}

impl ProvenanceStore {
    pub fn new(db: Db, batch_size: usize) -> Self {
        Self { db, batch_size }
    }

    fn trees(&self) -> sled::Tree {
        self.db.open_tree(TREES_TREE).unwrap()
    }

    fn leaves(&self) -> sled::Tree {
        self.db.open_tree(LEAVES_TREE).unwrap()
    }

    fn meta(&self) -> sled::Tree {
        self.db.open_tree(META_TREE).unwrap()
    }

    /// Add a leaf and return its hash, the current tree root, tree size, and proof path.
    pub fn add_leaf(&self, leaf: Leaf) -> Result<AddLeafResult, String> {
        let leaf_hash = leaf.hash.clone();
        self.leaves().insert(&leaf_hash, serde_json::to_vec(&leaf).unwrap()).unwrap();

        // Append to current batch
        let mut current: Vec<Leaf> = self.get_current_leaves();
        current.push(leaf);
        let leaf_index = current.len() - 1;

        if current.len() >= self.batch_size {
            // Seal the tree
            let tree_index = self.next_tree_index();
            let tree = MerkleTree::build(tree_index, current.clone());
            self.store_tree(&tree);
            self.set_next_tree_index(tree_index + 1);
            self.clear_current_leaves();

            let proof = tree.proof(leaf_index).unwrap();
            let tree_size = tree.size();
            let merkle_root = tree.root;
            Ok(AddLeafResult {
                leaf_hash,
                merkle_root,
                tree_size,
                proof_path: proof.proof_path,
            })
        } else {
            // Not yet sealed — build an in-progress tree for proof
            let tree = MerkleTree::build(0, current.clone());
            self.set_current_leaves(&current);

            let proof = tree.proof(leaf_index).unwrap();
            let tree_size = tree.size();
            let merkle_root = tree.root;
            Ok(AddLeafResult {
                leaf_hash,
                merkle_root,
                tree_size,
                proof_path: proof.proof_path,
            })
        }
    }

    /// Look up a leaf by hash and verify it's in its tree.
    pub fn verify_leaf(&self, leaf_hash: &str) -> Option<VerifyResult> {
        let _leaf: Leaf = {
            let data = self.leaves().get(leaf_hash).ok()??;
            serde_json::from_slice(&data).ok()?
        };

        // Search all sealed trees for this leaf
        let tree_count = self.next_tree_index();
        for i in 0..tree_count {
            if let Some(tree) = self.load_tree(i) {
                for (idx, l) in tree.leaves.iter().enumerate() {
                    if l.hash == leaf_hash {
                        let proof = tree.proof(idx).unwrap();
                        return Some(VerifyResult {
                            valid: MerkleTree::verify_proof(&proof),
                            leaf_hash: leaf_hash.to_string(),
                            merkle_root: tree.root,
                            proof_path: proof.proof_path,
                        });
                    }
                }
            }
        }

        // Check current (unsealed) batch
        let current = self.get_current_leaves();
        for (idx, l) in current.iter().enumerate() {
            if l.hash == leaf_hash {
                let tree = MerkleTree::build(0, current);
                let proof = tree.proof(idx).unwrap();
                return Some(VerifyResult {
                    valid: MerkleTree::verify_proof(&proof),
                    leaf_hash: leaf_hash.to_string(),
                    merkle_root: tree.root,
                    proof_path: proof.proof_path,
                });
            }
        }

        None
    }

    /// Get the current Merkle root (from in-progress or last sealed tree).
    pub fn current_root(&self) -> String {
        let current = self.get_current_leaves();
        if !current.is_empty() {
            let tree = MerkleTree::build(0, current);
            return tree.root;
        }
        let tree_count = self.next_tree_index();
        if tree_count > 0 {
            if let Some(tree) = self.load_tree(tree_count - 1) {
                return tree.root;
            }
        }
        MerkleTree::empty(0).root
    }

    /// Get a sealed tree by index.
    pub fn get_tree(&self, index: u64) -> Option<MerkleTree> {
        self.load_tree(index)
    }

    /// Get stats.
    pub fn stats(&self) -> Stats {
        let total_leaves = self.leaves().len();
        let sealed_trees = self.next_tree_index();
        let db_size = self.db.size_on_disk().unwrap_or(0);
        Stats {
            total_leaves,
            sealed_trees,
            db_size_bytes: db_size as u64,
        }
    }

    // -- helpers --

    fn get_current_leaves(&self) -> Vec<Leaf> {
        self.meta()
            .get(CURRENT_LEAVES_KEY)
            .ok()
            .flatten()
            .and_then(|v| serde_json::from_slice(&v).ok())
            .unwrap_or_default()
    }

    fn set_current_leaves(&self, leaves: &[Leaf]) {
        self.meta()
            .insert(CURRENT_LEAVES_KEY, serde_json::to_vec(leaves).unwrap())
            .unwrap();
    }

    fn clear_current_leaves(&self) {
        self.meta().remove(CURRENT_LEAVES_KEY).unwrap();
    }

    fn next_tree_index(&self) -> u64 {
        self.meta()
            .get("next_tree_index")
            .ok()
            .flatten()
            .and_then(|v| serde_json::from_slice(&v).ok())
            .unwrap_or(0)
    }

    fn set_next_tree_index(&self, idx: u64) {
        self.meta()
            .insert("next_tree_index", serde_json::to_vec(&idx).unwrap())
            .unwrap();
    }

    fn store_tree(&self, tree: &MerkleTree) {
        let key = format!("tree_{}", tree.index);
        self.trees()
            .insert(key, serde_json::to_vec(tree).unwrap())
            .unwrap();
    }

    fn load_tree(&self, index: u64) -> Option<MerkleTree> {
        let key = format!("tree_{}", index);
        let data = self.trees().get(key).ok()??;
        serde_json::from_slice(&data).ok()
    }
}

#[derive(Debug, serde::Serialize)]
pub struct AddLeafResult {
    pub leaf_hash: String,
    pub merkle_root: String,
    pub tree_size: usize,
    pub proof_path: Vec<crate::merkle::ProofElement>,
}

#[derive(Debug, serde::Serialize)]
pub struct VerifyResult {
    pub valid: bool,
    pub leaf_hash: String,
    pub merkle_root: String,
    pub proof_path: Vec<crate::merkle::ProofElement>,
}

#[derive(Debug, serde::Serialize)]
pub struct Stats {
    pub total_leaves: usize,
    pub sealed_trees: u64,
    pub db_size_bytes: u64,
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::merkle::leaf::{LeafData, VerificationTrace};

    fn test_store() -> ProvenanceStore {
        let dir = tempfile::tempdir().unwrap();
        let db = sled::open(dir.path()).unwrap();
        ProvenanceStore::new(db, 4)
    }

    fn make_leaf(i: usize) -> Leaf {
        Leaf::new(LeafData::Verification(VerificationTrace {
            trace: vec![format!("step_{}", i)],
            domain: "test".into(),
            confidence: 0.99,
            source: "test".into(),
        }))
    }

    #[test]
    fn test_add_single_leaf() {
        let store = test_store();
        let leaf = make_leaf(0);
        let result = store.add_leaf(leaf).unwrap();
        assert!(result.leaf_hash.starts_with("sha256:"));
        assert!(result.merkle_root.starts_with("sha256:"));
        assert_eq!(result.tree_size, 1);
    }

    #[test]
    fn test_batch_seals_at_threshold() {
        let store = test_store(); // batch_size=4
        for i in 0..4 {
            let result = store.add_leaf(make_leaf(i)).unwrap();
            if i < 3 {
                assert!(result.tree_size < 4);
            } else {
                assert_eq!(result.tree_size, 4);
            }
        }
        // After sealing, next add starts fresh batch
        let result = store.add_leaf(make_leaf(4)).unwrap();
        assert_eq!(result.tree_size, 1);
    }

    #[test]
    fn test_verify_leaf_after_add() {
        let store = test_store();
        let leaf = make_leaf(42);
        let added = store.add_leaf(leaf).unwrap();
        let verify = store.verify_leaf(&added.leaf_hash).unwrap();
        assert!(verify.valid);
        assert_eq!(verify.leaf_hash, added.leaf_hash);
    }

    #[test]
    fn test_verify_nonexistent_leaf() {
        let store = test_store();
        assert!(store.verify_leaf("sha256:nope").is_none());
    }

    #[test]
    fn test_sealed_tree_retrievable() {
        let store = test_store(); // batch_size=4
        for i in 0..4 {
            store.add_leaf(make_leaf(i)).unwrap();
        }
        let tree = store.get_tree(0).unwrap();
        assert_eq!(tree.size(), 4);
        assert!(tree.root.starts_with("sha256:"));
    }

    #[test]
    fn test_stats() {
        let store = test_store();
        store.add_leaf(make_leaf(0)).unwrap();
        store.add_leaf(make_leaf(1)).unwrap();
        let stats = store.stats();
        assert_eq!(stats.total_leaves, 2);
        assert_eq!(stats.sealed_trees, 0);
    }
}
