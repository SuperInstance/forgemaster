use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

/// A verification trace submitted to the provenance service.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VerificationTrace {
    pub trace: Vec<String>,
    pub domain: String,
    pub confidence: f64,
    pub source: String,
}

/// A constraint verification leaf.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConstraintLeaf {
    pub constraint_id: String,
    pub status: String,
    pub evidence: Vec<String>,
}

/// The leaf data stored in the Merkle tree.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum LeafData {
    Verification(VerificationTrace),
    Constraint(ConstraintLeaf),
}

/// A leaf in the Merkle tree, with its computed hash.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Leaf {
    pub hash: String,
    pub data: LeafData,
}

impl Leaf {
    pub fn new(data: LeafData) -> Self {
        let hash = Self::compute_hash(&data);
        Self { hash, data }
    }

    fn compute_hash(data: &LeafData) -> String {
        let json = serde_json::to_string(data).unwrap_or_default();
        let mut hasher = Sha256::new();
        hasher.update(json.as_bytes());
        format!("sha256:{}", hex::encode(hasher.finalize()))
    }
}

/// Raw leaf hash for tree operations.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LeafHash(pub String);

impl LeafHash {
    pub fn as_str(&self) -> &str {
        &self.0
    }
}
