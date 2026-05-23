//! TUTOR-style hyperdimensional constraint matcher.

use crate::{Hypervector, hamming_similarity};
use thiserror::Error;

/// Error type for matcher operations.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Error)]
#[non_exhaustive]
pub enum MatcherError {
    /// No concepts stored in matcher.
    #[error("matcher contains no concepts")]
    NoConcepts,
    /// Top-k value is 0.
    #[error("top-k must be greater than 0")]
    InvalidTopK,
}

/// TUTOR-style hyperdimensional classifier/matcher.
/// Stores concepts as hypervectors (bundles of training examples) and matches queries
/// using Hamming similarity.
#[derive(Debug, Clone, Default)]
pub struct TUTORConstraintMatcher<K: Clone + PartialEq> {
    concepts: Vec<(K, Hypervector)>,
}

impl<K: Clone + PartialEq> TUTORConstraintMatcher<K> {
    /// Create a new empty matcher.
    #[inline]
    pub fn new() -> Self {
        Self { concepts: Vec::new() }
    }

    /// Add or update a concept with a pre-bundled hypervector.
    #[inline]
    pub fn add_concept(&mut self, id: K, hv: Hypervector) {
        if let Some((_, existing_hv)) = self.concepts.iter_mut().find(|(cid, _)| cid == &id) {
            *existing_hv = hv;
        } else {
            self.concepts.push((id, hv));
        }
    }

    /// Add an example to an existing concept (or create a new concept).
    /// Updates the concept's hypervector to be the majority bundle of all existing examples
    /// and the new example.
    pub fn add_example(&mut self, id: K, example_hv: Hypervector) {
        if let Some((_, existing_hv)) = self.concepts.iter_mut().find(|(cid, _)| cid == &id) {
            // Bundle existing concept (1 example) with new example
            *existing_hv = match majority_bundle(&[*existing_hv, example_hv]) {
                Ok(hv) => hv,
                Err(_) => example_hv,
            };
        } else {
            self.concepts.push((id, example_hv));
        }
    }

    /// Bundle all stored concepts into a single hypervector.
    /// Useful for compact storage or multi-concept queries.
    pub fn bundle_all(&self) -> Result<Hypervector, MatcherError> {
        if self.concepts.is_empty() {
            return Err(MatcherError::NoConcepts);
        }
        let hvs: Vec<Hypervector> = self.concepts.iter().map(|(_, hv)| *hv).collect();
        Ok(majority_bundle(&hvs)?)
    }

    /// Query the matcher for the top-k most similar concepts.
    /// Returns a vector of (concept_id, similarity) sorted by similarity descending.
    pub fn query(&self, query_hv: &Hypervector, top_k: usize) -> Result<Vec<(K, f64)>, MatcherError> {
        if self.concepts.is_empty() {
            return Err(MatcherError::NoConcepts);
        }
        if top_k == 0 {
            return Err(MatcherError::InvalidTopK);
        }

        // Calculate similarities
        let mut scores: Vec<(K, f64)> = self.concepts
            .iter()
            .map(|(id, hv)| (id.clone(), hamming_similarity(query_hv, hv)))
            .collect();

        // Sort by similarity descending
        scores.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(core::cmp::Ordering::Equal));

        // Take top-k
        Ok(scores.into_iter().take(top_k).collect())
    }

    /// Get the number of stored concepts.
    #[inline]
    pub fn len(&self) -> usize {
        self.concepts.len()
    }

    /// Check if the matcher is empty.
    #[inline]
    pub fn is_empty(&self) -> bool {
        self.concepts.is_empty()
    }
}

// Import for majority_bundle used in add_example
use crate::majority_bundle;

impl From<crate::OperationError> for MatcherError {
    fn from(_: crate::OperationError) -> Self {
        MatcherError::NoConcepts
    }
}