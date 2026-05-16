//! Multi-dimensional state tensor.
//!
//! Dimensions: time, intent (FLUX), harmony, side-channels.

use alloc::string::String;
use alloc::vec::Vec;
use core::fmt;

#[cfg(feature = "serde")]
use serde::{Deserialize, Serialize};

/// Named dimension in the state tensor.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[cfg_attr(feature = "serde", derive(Serialize, Deserialize))]
pub enum TensorDimension {
    /// Temporal dimension (clock ticks, beats).
    Time,
    /// Intent dimension (FLUX vector state).
    Intent,
    /// Harmony dimension (correlation, Jaccard).
    Harmony,
    /// Side-channel dimension (nods, smiles, frowns).
    SideChannel,
}

/// A single scalar entry in the state tensor, tagged with its dimension and timestamp.
#[derive(Clone, Debug, PartialEq)]
#[cfg_attr(feature = "serde", derive(Serialize, Deserialize))]
pub struct TensorEntry {
    pub dimension: TensorDimension,
    pub key: String,
    pub value: f64,
    pub timestamp: f64,
}

/// Multi-dimensional state tensor for a room or ensemble.
///
/// Stores timestamped scalar values across four dimensions.
#[derive(Clone, Debug, Default)]
#[cfg_attr(feature = "serde", derive(Serialize, Deserialize))]
pub struct StateTensor {
    entries: Vec<TensorEntry>,
}

impl StateTensor {
    /// Create an empty tensor.
    pub fn new() -> Self {
        Self { entries: Vec::new() }
    }

    /// Push an entry into the tensor.
    pub fn push(&mut self, entry: TensorEntry) {
        self.entries.push(entry);
    }

    /// Number of entries.
    #[inline]
    pub fn len(&self) -> usize {
        self.entries.len()
    }

    /// Whether the tensor is empty.
    #[inline]
    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }

    /// Iterate over entries in a specific dimension.
    pub fn iter_dimension(&self, dim: TensorDimension) -> impl Iterator<Item = &TensorEntry> {
        self.entries.iter().filter(move |e| e.dimension == dim)
    }

    /// Latest entry for a given dimension + key, or `None`.
    pub fn latest(&self, dim: TensorDimension, key: &str) -> Option<&TensorEntry> {
        self.iter_dimension(dim)
            .filter(|e| e.key == key)
            .last()
    }

    /// All entries within a time range `[t0, t1]`.
    pub fn in_range(&self, t0: f64, t1: f64) -> Vec<&TensorEntry> {
        self.entries
            .iter()
            .filter(|e| e.timestamp >= t0 && e.timestamp <= t1)
            .collect()
    }

    /// Prune entries older than `t_cutoff`, returning the number removed.
    pub fn prune_before(&mut self, t_cutoff: f64) -> usize {
        let before = self.entries.len();
        self.entries.retain(|e| e.timestamp >= t_cutoff);
        before - self.entries.len()
    }
}

impl fmt::Display for StateTensor {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "Tensor({} entries)", self.entries.len())
    }
}
