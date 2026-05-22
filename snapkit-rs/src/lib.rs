//! snapkit-rs: Snapshot toolkit for capturing, diffing, and restoring state.

use std::collections::BTreeMap;

/// A snapshot of key-value state at a point in time.
#[derive(Debug, Clone, PartialEq)]
pub struct Snapshot {
    pub label: String,
    pub data: BTreeMap<String, String>,
}

impl Snapshot {
    /// Capture a new snapshot with the given label and key-value pairs.
    pub fn capture(label: &str, data: BTreeMap<String, String>) -> Self {
        Self {
            label: label.to_string(),
            data,
        }
    }

    /// Diff this snapshot against another, returning keys that were added,
    /// removed, or changed.
    pub fn diff(&self, other: &Snapshot) -> DiffResult {
        let mut added = Vec::new();
        let mut removed = Vec::new();
        let mut changed = Vec::new();

        for (key, val) in &self.data {
            match other.data.get(key) {
                None => removed.push(key.clone()),
                Some(other_val) if val != other_val => {
                    changed.push(DiffEntry {
                        key: key.clone(),
                        from: val.clone(),
                        to: other_val.clone(),
                    });
                }
                _ => {}
            }
        }

        for key in other.data.keys() {
            if !self.data.contains_key(key) {
                added.push(key.clone());
            }
        }

        DiffResult {
            from_label: self.label.clone(),
            to_label: other.label.clone(),
            added,
            removed,
            changed,
        }
    }

    /// Produce a restored snapshot by applying `other`'s values on top of
    /// this snapshot, keeping any keys only in `self`.
    pub fn restore(&self, patch: &Snapshot) -> Snapshot {
        let mut merged = self.data.clone();
        for (k, v) in &patch.data {
            merged.insert(k.clone(), v.clone());
        }
        Snapshot {
            label: format!("{}+{}", self.label, patch.label),
            data: merged,
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct DiffEntry {
    pub key: String,
    pub from: String,
    pub to: String,
}

#[derive(Debug, Clone, PartialEq)]
pub struct DiffResult {
    pub from_label: String,
    pub to_label: String,
    pub added: Vec<String>,
    pub removed: Vec<String>,
    pub changed: Vec<DiffEntry>,
}

impl DiffResult {
    pub fn is_empty(&self) -> bool {
        self.added.is_empty() && self.removed.is_empty() && self.changed.is_empty()
    }
}
