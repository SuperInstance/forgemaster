//! # plato-tile-dedup
//!
//! Near-duplicate tile detection for the PLATO knowledge graph.
//! Uses SimHash + LSH for fast approximate deduplication.

use std::collections::{HashMap, HashSet};

/// A SimHash fingerprint (64-bit).
pub type Fingerprint = u64;

/// Generate a SimHash fingerprint from text content.
pub fn simhash(text: &str) -> Fingerprint {
    let features: Vec<&str> = text.split_whitespace().collect();
    let mut v = [0i64; 64];
    
    for feature in &features {
        let h = hash_feature(feature);
        for i in 0..64 {
            if h & (1u64 << i) != 0 { v[i] += 1; } else { v[i] -= 1; }
        }
    }
    
    let mut fp = 0u64;
    for i in 0..64 {
        if v[i] > 0 { fp |= 1u64 << i; }
    }
    fp
}

fn hash_feature(s: &str) -> u64 {
    let mut h = 5381u64;
    for b in s.bytes() {
        h = h.wrapping_mul(33).wrapping_add(b as u64);
    }
    h
}

/// Hamming distance between two fingerprints.
pub fn hamming(a: Fingerprint, b: Fingerprint) -> u32 {
    (a ^ b).count_ones()
}

/// Check if two tiles are near-duplicates (Hamming distance <= threshold).
pub fn is_duplicate(a: Fingerprint, b: Fingerprint, threshold: u32) -> bool {
    hamming(a, b) <= threshold
}

/// Deduplication engine with LSH indexing.
pub struct DedupEngine {
    threshold: u32,
    index: HashMap<u32, Vec<Fingerprint>>, // bucket -> fingerprints
    seen: HashSet<Fingerprint>,
}

impl DedupEngine {
    pub fn new(threshold: u32) -> Self {
        DedupEngine { threshold, index: HashMap::new(), seen: HashSet::new() }
    }
    
    pub fn insert(&mut self, fp: Fingerprint) -> bool {
        if self.seen.contains(&fp) { return true; } // exact dup
        
        // Check LSH buckets
        for band in 0..4 {
            let bucket = (fp >> (band * 16)) & 0xFFFF;
            let bucket_key = bucket as u32;
            if let Some(fps) = self.index.get(&bucket_key) {
                for &other in fps {
                    if hamming(fp, other) <= self.threshold { return true; }
                }
            }
            self.index.entry(bucket_key).or_default().push(fp);
        }
        
        self.seen.insert(fp);
        false
    }
    
    pub fn len(&self) -> usize { self.seen.len() }
    pub fn is_empty(&self) -> bool { self.seen.is_empty() }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_simhash_deterministic() {
        let a = simhash("hello world");
        let b = simhash("hello world");
        assert_eq!(a, b);
    }
    
    #[test]
    fn test_simhash_different() {
        let a = simhash("hello world");
        let b = simhash("foo bar baz");
        assert_ne!(a, b);
    }
    
    #[test]
    fn test_hamming() {
        assert_eq!(hamming(0, 0), 0);
        assert_eq!(hamming(0xFFFF, 0), 16);
        assert_eq!(hamming(0xFF, 0x0F), 4);
    }
    
    #[test]
    fn test_is_duplicate() {
        let a = simhash("the quick brown fox");
        let b = simhash("the quick brown fox jumps");
        assert!(is_duplicate(a, a, 0)); // exact
        assert!(is_duplicate(a, b, 32)); // near-dup
    }
    
    #[test]
    fn test_dedup_engine() {
        let mut engine = DedupEngine::new(8);
        let fp1 = simhash("constraint theory snap function");
        let fp2 = simhash("constraint theory snap functions");
        let fp3 = simhash("quantum entanglement bell state");
        
        assert!(!engine.insert(fp1)); // new
        assert!(engine.insert(fp1));   // exact dup
        assert!(engine.insert(fp2));   // near-dup
        assert!(!engine.insert(fp3));  // new
        assert_eq!(engine.len(), 2);
    }
}
