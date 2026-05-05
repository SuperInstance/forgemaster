use flux_provenance::merkle::*;
use flux_provenance::store::ProvenanceStore;

fn make_verification_leaf(i: usize) -> Leaf {
    Leaf::new(LeafData::Verification(VerificationTrace {
        trace: vec![format!("step_{}", i)],
        domain: format!("domain_{}", i % 3),
        confidence: 0.9 + (i as f64 * 0.01),
        source: "integration-test".into(),
    }))
}

fn make_constraint_leaf(i: usize) -> Leaf {
    Leaf::new(LeafData::Constraint(ConstraintLeaf {
        constraint_id: format!("c_{}", i),
        status: "satisfied".into(),
        evidence: vec![format!("evidence_{}", i)],
    }))
}

// --- Merkle tree tests ---

#[test]
fn test_single_leaf_tree() {
    let leaf = make_verification_leaf(0);
    let tree = MerkleTree::build(0, vec![leaf]);
    assert_eq!(tree.size(), 1);
    assert!(tree.root.starts_with("sha256:"));
    assert!(tree.root.len() > 10);
}

#[test]
fn test_proof_roundtrip_many_leaves() {
    let leaves: Vec<Leaf> = (0..16).map(make_verification_leaf).collect();
    let tree = MerkleTree::build(0, leaves);
    for i in 0..16 {
        let proof = tree.proof(i).unwrap();
        assert!(MerkleTree::verify_proof(&proof), "proof for leaf {} failed", i);
    }
}

#[test]
fn test_tampered_leaf_fails_verification() {
    let leaves: Vec<Leaf> = (0..8).map(make_verification_leaf).collect();
    let tree = MerkleTree::build(0, leaves);
    let mut proof = tree.proof(3).unwrap();
    proof.leaf_hash = "sha256:0000000000000000000000000000000000000000000000000000000000000000".into();
    assert!(!MerkleTree::verify_proof(&proof));
}

#[test]
fn test_deterministic_hashing() {
    let leaves1: Vec<Leaf> = (0..4).map(make_verification_leaf).collect();
    let leaves2: Vec<Leaf> = (0..4).map(make_verification_leaf).collect();
    let tree1 = MerkleTree::build(0, leaves1);
    let tree2 = MerkleTree::build(99, leaves2);
    assert_eq!(tree1.root, tree2.root);
}

#[test]
fn test_different_data_different_root() {
    let leaves_a: Vec<Leaf> = (0..4).map(make_verification_leaf).collect();
    let leaves_b: Vec<Leaf> = (4..8).map(make_verification_leaf).collect();
    let tree_a = MerkleTree::build(0, leaves_a);
    let tree_b = MerkleTree::build(0, leaves_b);
    assert_ne!(tree_a.root, tree_b.root);
}

// --- Store persistence tests ---

struct TestStore {
    store: ProvenanceStore,
    _dir: tempfile::TempDir,
}

impl std::ops::Deref for TestStore {
    type Target = ProvenanceStore;
    fn deref(&self) -> &Self::Target { &self.store }
}

fn test_store_with(batch_size: usize) -> TestStore {
    let dir = tempfile::tempdir().unwrap();
    let db = sled::open(dir.path()).unwrap();
    let store = ProvenanceStore::new(db, batch_size);
    TestStore { store, _dir: dir }
}


#[test]
fn test_add_and_verify_leaf() {
    let store = test_store_with(10);
    let leaf = make_verification_leaf(0);
    let result = store.add_leaf(leaf).unwrap();
    assert!(result.leaf_hash.starts_with("sha256:"));

    let verify = store.verify_leaf(&result.leaf_hash).unwrap();
    assert!(verify.valid);
}

#[test]
fn test_batch_sealing() {
    let store = test_store_with(3);
    let mut last_result = None;
    for i in 0..6 {
        last_result = Some(store.add_leaf(make_verification_leaf(i)).unwrap());
    }
    // After 6 leaves with batch=3, we should have 2 sealed trees
    let stats = store.stats();
    assert_eq!(stats.sealed_trees, 2);
    assert_eq!(stats.total_leaves, 6);
}

#[test]
fn test_verify_across_sealed_tree() {
    let store = test_store_with(3);
    let mut leaf_hashes = Vec::new();
    for i in 0..3 {
        let r = store.add_leaf(make_verification_leaf(i)).unwrap();
        leaf_hashes.push(r.leaf_hash);
    }
    // All 3 should be verifiable after sealing
    for hash in &leaf_hashes {
        let v = store.verify_leaf(hash).unwrap();
        assert!(v.valid);
    }
}

#[test]
fn test_tree_retrieval() {
    let store = test_store_with(3);
    for i in 0..3 {
        store.add_leaf(make_verification_leaf(i)).unwrap();
    }
    let tree = store.get_tree(0).unwrap();
    assert_eq!(tree.size(), 3);
    assert!(tree.root.starts_with("sha256:"));
}

#[test]
fn test_stats_accuracy() {
    let store = test_store_with(100);
    for i in 0..5 {
        store.add_leaf(make_verification_leaf(i)).unwrap();
    }
    let stats = store.stats();
    assert_eq!(stats.total_leaves, 5);
    assert_eq!(stats.sealed_trees, 0);
}

#[test]
fn test_current_root() {
    let store = test_store_with(100);
    let root_before = store.current_root();
    store.add_leaf(make_verification_leaf(0)).unwrap();
    let root_after = store.current_root();
    assert_ne!(root_before, root_after);
}

#[test]
fn test_mixed_leaf_types() {
    let store = test_store_with(4);
    store.add_leaf(make_verification_leaf(0)).unwrap();
    store.add_leaf(make_constraint_leaf(1)).unwrap();
    store.add_leaf(make_verification_leaf(2)).unwrap();
    store.add_leaf(make_constraint_leaf(3)).unwrap();
    let stats = store.stats();
    assert_eq!(stats.total_leaves, 4);
    assert_eq!(stats.sealed_trees, 1);
}

#[test]
fn test_proof_path_structure() {
    let leaves: Vec<Leaf> = (0..8).map(make_verification_leaf).collect();
    let tree = MerkleTree::build(0, leaves);
    let proof = tree.proof(0).unwrap();
    // For 8 leaves, proof path should have 3 elements (log2(8))
    assert_eq!(proof.proof_path.len(), 3);
}
