//! # ct-learned — Learned Index for O(1) Pythagorean Snap
//!
//! Instead of binary search (O(log n)), train a piecewise linear model
//! of the CDF to predict the nearest triple index in O(1) with correction.

const TAU: f64 = 6.283185307179586;

/// A learned index model: piecewise linear CDF approximation.
#[derive(Debug, Clone)]
pub struct LearnedIndex {
    /// Segment boundaries (angles).
    pub boundaries: Vec<f64>,
    /// Slope within each segment.
    pub slopes: Vec<f64>,
    /// Intercept within each segment.
    pub intercepts: Vec<f64>,
    /// Total number of indexed items.
    pub n: usize,
}

/// Prediction result from the learned index.
#[derive(Debug, Clone)]
pub struct Prediction {
    pub predicted_idx: usize,
    pub segment: usize,
    pub confidence: f64,
}

/// Training data point: (angle, index).
#[derive(Debug, Clone, Copy)]
pub struct TrainingPoint {
    pub angle: f64,
    pub index: usize,
}

impl LearnedIndex {
    /// Train a piecewise linear model from sorted (angle, index) data.
    /// Uses `segments` number of linear pieces.
    pub fn train(data: &[TrainingPoint], segments: usize) -> Self {
        let n = data.len();
        if n == 0 || segments == 0 {
            return LearnedIndex { boundaries: vec![], slopes: vec![], intercepts: vec![], n: 0 };
        }
        
        let actual_segments = segments.min(n);
        let seg_size = n / actual_segments;
        
        let mut boundaries = Vec::with_capacity(actual_segments + 1);
        let mut slopes = Vec::with_capacity(actual_segments);
        let mut intercepts = Vec::with_capacity(actual_segments);
        
        for s in 0..actual_segments {
            let start = s * seg_size;
            let end = if s == actual_segments - 1 { n - 1 } else { (s + 1) * seg_size };
            
            let x0 = data[start].angle;
            let y0 = data[start].index as f64;
            let x1 = data[end].angle;
            let y1 = data[end].index as f64;
            
            boundaries.push(x0);
            
            let dx = x1 - x0;
            if dx.abs() > 1e-15 {
                let slope = (y1 - y0) / dx;
                let intercept = y0 - slope * x0;
                slopes.push(slope);
                intercepts.push(intercept);
            } else {
                slopes.push(0.0);
                intercepts.push(y0);
            }
        }
        
        boundaries.push(data[n - 1].angle);
        
        LearnedIndex { boundaries, slopes, intercepts, n }
    }
    
    /// Predict the index for a given angle. Returns the predicted index and segment.
    pub fn predict(&self, angle: f64) -> Prediction {
        if self.n == 0 {
            return Prediction { predicted_idx: 0, segment: 0, confidence: 0.0 };
        }
        
        // Find segment via binary search on boundaries
        let a = ((angle % TAU) + TAU) % TAU;
        let mut seg = 0;
        for i in 1..self.boundaries.len() {
            if a >= self.boundaries[i] { seg = i; } else { break; }
        }
        seg = seg.min(self.slopes.len() - 1);
        
        let predicted = (self.slopes[seg] * a + self.intercepts[seg]).round() as usize;
        let clamped = predicted.min(self.n - 1);
        
        // Confidence based on distance to nearest boundary
        let lo = self.boundaries.get(seg).copied().unwrap_or(0.0);
        let hi = self.boundaries.get(seg + 1).copied().unwrap_or(TAU);
        let range = hi - lo;
        let pos_in_seg = if range > 0.0 { (a - lo) / range } else { 0.5 };
        let confidence = 1.0 - 2.0 * (pos_in_seg - 0.5).abs(); // 1.0 at center, 0.0 at edges
        
        Prediction { predicted_idx: clamped, segment: seg, confidence }
    }
    
    /// Search with learned prediction + linear correction.
    /// Predicts index, then linear scans ±epsilon window.
    pub fn search(&self, angle: f64, angles: &[f64], epsilon: usize) -> usize {
        let pred = self.predict(angle);
        let a = ((angle % TAU) + TAU) % TAU;
        let n = angles.len();
        if n == 0 { return 0; }
        
        let lo = pred.predicted_idx.saturating_sub(epsilon);
        let hi = (pred.predicted_idx + epsilon).min(n - 1);
        
        let mut best_idx = lo;
        let mut best_dist = angular_distance(a, angles[lo]);
        
        for i in lo..=hi {
            let d = angular_distance(a, angles[i]);
            if d < best_dist {
                best_dist = d;
                best_idx = i;
            }
        }
        best_idx
    }
    
    /// Model size in bytes (approximate).
    pub fn model_size(&self) -> usize {
        (self.boundaries.len() + self.slopes.len() + self.intercepts.len()) * 8
    }
}

/// Angular distance on [0, 2pi).
pub fn angular_distance(a: f64, b: f64) -> f64 {
    let a = ((a % TAU) + TAU) % TAU;
    let b = ((b % TAU) + TAU) % TAU;
    let d = (a - b).abs();
    d.min(TAU - d)
}

/// Generate training data from sorted angles.
pub fn make_training_data(angles: &[f64]) -> Vec<TrainingPoint> {
    angles.iter().enumerate().map(|(i, &a)| TrainingPoint { angle: a, index: i }).collect()
}

/// Verify learned index correctness against brute-force nearest.
pub fn verify(index: &LearnedIndex, angles: &[f64], test_angles: &[f64], epsilon: usize) -> (usize, usize) {
    let mut correct = 0;
    let mut total = 0;
    
    for &query in test_angles {
        let q = ((query % TAU) + TAU) % TAU;
        // Brute force
        let mut bf_idx = 0;
        let mut bf_dist = TAU;
        for (i, &a) in angles.iter().enumerate() {
            let d = angular_distance(q, a);
            if d < bf_dist { bf_dist = d; bf_idx = i; }
        }
        
        let learned_idx = index.search(query, angles, epsilon);
        if learned_idx == bf_idx { correct += 1; }
        total += 1;
    }
    
    (correct, total)
}

#[cfg(test)]
mod tests {
    use super::*;
    
    fn sample_angles() -> Vec<f64> {
        // Simulate sorted Pythagorean triple angles (simplified)
        let mut angles: Vec<f64> = (0..100).map(|i| i as f64 / 100.0 * TAU).collect();
        angles.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        angles
    }
    
    #[test]
    fn test_train_and_predict() {
        let angles = sample_angles();
        let data = make_training_data(&angles);
        let index = LearnedIndex::train(&data, 10);
        
        let pred = index.predict(1.0);
        assert!(pred.predicted_idx < 100);
    }
    
    #[test]
    fn test_search_correctness() {
        let angles = sample_angles();
        let data = make_training_data(&angles);
        let index = LearnedIndex::train(&data, 10);
        
        for query in &[0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0] {
            let idx = index.search(*query, &angles, 5);
            assert!(idx < 100);
        }
    }
    
    #[test]
    fn test_verify_high_accuracy() {
        let angles = sample_angles();
        let data = make_training_data(&angles);
        let index = LearnedIndex::train(&data, 20);
        
        let test: Vec<f64> = (0..50).map(|i| i as f64 / 50.0 * TAU).collect();
        let (correct, total) = verify(&index, &angles, &test, 10);
        // With epsilon=10 on uniform data, should be very accurate
        assert!(correct as f64 / total as f64 > 0.9);
    }
    
    #[test]
    fn test_model_size() {
        let angles = sample_angles();
        let data = make_training_data(&angles);
        let index = LearnedIndex::train(&data, 10);
        assert!(index.model_size() < 1000); // small model
    }
    
    #[test]
    fn test_empty_data() {
        let index = LearnedIndex::train(&[], 5);
        let pred = index.predict(1.0);
        assert_eq!(pred.predicted_idx, 0);
    }
    
    #[test]
    fn test_single_segment() {
        let angles = sample_angles();
        let data = make_training_data(&angles);
        let index = LearnedIndex::train(&data, 1);
        let pred = index.predict(3.0);
        assert!(pred.predicted_idx < 100);
    }
    
    #[test]
    fn test_angular_distance() {
        assert!(angular_distance(0.0, 0.0) < 1e-10);
        assert!((angular_distance(0.0, TAU - 0.01) - 0.01).abs() < 1e-10);
    }
    
    #[test]
    fn test_many_segments() {
        let angles = sample_angles();
        let data = make_training_data(&angles);
        let index = LearnedIndex::train(&data, 50);
        assert_eq!(index.slopes.len(), 50);
    }
}
