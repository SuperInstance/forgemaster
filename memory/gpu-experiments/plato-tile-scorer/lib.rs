//! # plato-tile-scorer
//!
//! Multi-signal tile quality scoring for the PLATO knowledge graph.
//! Combines freshness, depth, breadth, and constraint-theory relevance.

/// A scored tile result.
#[derive(Debug, Clone)]
pub struct ScoredTile {
    pub tile_id: String,
    pub score: f64,
    pub signals: ScoreSignals,
}

/// Individual scoring signals.
#[derive(Debug, Clone, Default)]
pub struct ScoreSignals {
    pub depth: f64,       // 0-1: how detailed is the answer
    pub freshness: f64,   // 0-1: recency of content
    pub breadth: f64,     // 0-1: how many concepts covered
    pub ct_relevance: f64,// 0-1: constraint-theory relevance
}

/// Weighted scoring configuration.
#[derive(Debug, Clone)]
pub struct ScoreWeights {
    pub depth: f64,
    pub freshness: f64,
    pub breadth: f64,
    pub ct_relevance: f64,
}

impl Default for ScoreWeights {
    fn default() -> Self {
        ScoreWeights { depth: 0.35, freshness: 0.15, breadth: 0.25, ct_relevance: 0.25 }
    }
}

/// Score a tile given its signals and weights.
pub fn score_tile(tile_id: &str, signals: ScoreSignals, weights: &ScoreWeights) -> ScoredTile {
    let score = weights.depth * signals.depth
        + weights.freshness * signals.freshness
        + weights.breadth * signals.breadth
        + weights.ct_relevance * signals.ct_relevance;
    ScoredTile { tile_id: tile_id.to_string(), score, signals }
}

/// Score multiple tiles and return sorted by descending score.
pub fn score_and_rank(tiles: Vec<(&str, ScoreSignals)>, weights: &ScoreWeights) -> Vec<ScoredTile> {
    let mut scored: Vec<ScoredTile> = tiles.into_iter()
        .map(|(id, sig)| score_tile(id, sig, weights))
        .collect();
    scored.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal));
    scored
}

/// Estimate answer depth from text length and structure.
pub fn estimate_depth(answer: &str) -> f64 {
    let len = answer.len();
    let has_numbers = answer.chars().any(|c| c.is_ascii_digit());
    let has_structure = answer.contains('\n') || answer.contains('.');
    let mut score: f64 = 0.0;
    if len > 50 { score += 0.3; }
    if len > 200 { score += 0.2; }
    if len > 500 { score += 0.2; }
    if has_numbers { score += 0.15; }
    if has_structure { score += 0.15; }
    let result: f64 = score.min(1.0);
    result
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_score_tile() {
        let sig = ScoreSignals { depth: 0.8, freshness: 0.5, breadth: 0.7, ct_relevance: 0.9 };
        let weights = ScoreWeights::default();
        let scored = score_tile("test", sig, &weights);
        assert!(scored.score > 0.7);
    }
    
    #[test]
    fn test_score_and_rank() {
        let tiles = vec![
            ("low", ScoreSignals::default()),
            ("high", ScoreSignals { depth: 1.0, freshness: 1.0, breadth: 1.0, ct_relevance: 1.0 }),
            ("mid", ScoreSignals { depth: 0.5, freshness: 0.5, breadth: 0.5, ct_relevance: 0.5 }),
        ];
        let ranked = score_and_rank(tiles, &ScoreWeights::default());
        assert_eq!(ranked[0].tile_id, "high");
        assert_eq!(ranked[2].tile_id, "low");
    }
    
    #[test]
    fn test_estimate_depth() {
        let short = "yes";
        let medium = "The snap function finds the nearest Pythagorean triple for a given angle.";
        let long = "Constraint theory provides a framework for analyzing geometric constraints.\nIt uses 3 key principles.\nThe first is the snap function, which maps angles to triples.";
        
        assert!(estimate_depth(short) < estimate_depth(medium));
        assert!(estimate_depth(medium) < estimate_depth(long));
    }
}
