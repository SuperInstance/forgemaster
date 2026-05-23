use sha2::{Digest, Sha256};

use crate::api::response::TraceEntry;

/// Compute a Merkle-style hash of the entire trace.
/// Each entry is hashed, then the chain of hashes is hashed together.
pub fn hash_trace(trace: &[TraceEntry]) -> String {
    if trace.is_empty() {
        let mut hasher = Sha256::new();
        hasher.update(b"empty-trace");
        return hex::encode(hasher.finalize());
    }

    // Hash each entry individually
    let entry_hashes: Vec<String> = trace
        .iter()
        .enumerate()
        .map(|(i, entry)| {
            let mut hasher = Sha256::new();
            hasher.update(format!("{}:{}", i, entry.opcode).as_bytes());
            if let Some(v) = entry.value {
                hasher.update(format!(":v{}", v).as_bytes());
            }
            if let Some(r) = entry.result {
                hasher.update(format!(":r{}", r).as_bytes());
            }
            if let Some(e) = entry.expected {
                hasher.update(format!(":e{}", e).as_bytes());
            }
            if let Some(a) = entry.actual {
                hasher.update(format!(":a{}", a).as_bytes());
            }
            hasher.update(format!(":{}", entry.desc).as_bytes());
            hex::encode(hasher.finalize())
        })
        .collect();

    // Combine all entry hashes into a root hash
    let mut hasher = Sha256::new();
    for h in &entry_hashes {
        hasher.update(h.as_bytes());
    }
    hex::encode(hasher.finalize())
}

/// Verify that a trace matches a known proof hash.
pub fn verify_proof_hash(trace: &[TraceEntry], expected_hash: &str) -> bool {
    let computed = hash_trace(trace);
    computed == expected_hash || format!("sha256:{}", computed) == expected_hash
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_entry(opcode: &str, value: Option<f64>, result: Option<f64>, desc: &str) -> TraceEntry {
        TraceEntry {
            opcode: opcode.into(),
            value,
            result,
            expected: None,
            actual: None,
            desc: desc.into(),
        }
    }

    #[test]
    fn test_hash_deterministic() {
        let trace = vec![
            make_entry("LOAD", Some(200.0), None, "depth"),
            make_entry("LOAD", Some(50000.0), None, "frequency"),
        ];
        let h1 = hash_trace(&trace);
        let h2 = hash_trace(&trace);
        assert_eq!(h1, h2);
    }

    #[test]
    fn test_hash_changes_with_data() {
        let trace1 = vec![make_entry("LOAD", Some(200.0), None, "depth")];
        let trace2 = vec![make_entry("LOAD", Some(300.0), None, "depth")];
        assert_ne!(hash_trace(&trace1), hash_trace(&trace2));
    }

    #[test]
    fn test_empty_trace() {
        let h = hash_trace(&[]);
        assert!(!h.is_empty());
        assert_eq!(h.len(), 64); // SHA-256 hex = 64 chars
    }

    #[test]
    fn test_verify_proof_hash() {
        let trace = vec![make_entry("LOAD", Some(42.0), None, "answer")];
        let hash = hash_trace(&trace);
        assert!(verify_proof_hash(&trace, &hash));
        assert!(verify_proof_hash(&trace, &format!("sha256:{}", hash)));
        assert!(!verify_proof_hash(&trace, "wrong_hash"));
    }
}
