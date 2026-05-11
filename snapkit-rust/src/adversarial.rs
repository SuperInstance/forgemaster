//! Adversarial snap — fake delta detection and camouflage.
//!
//! In adversarial settings (poker, blackjack, negotiation), agents actively
//! generate fake deltas to jam each other's snap functions. This module
//! provides tools for detecting fake deltas and generating camouflage signals.
//!
//! "The game isn't in the cards. The game is in the space between minds —
//! where each intelligence tries to out-fake the other's delta detection."
//! — SNAPS-AS-ATTENTION.md

use crate::delta::{Delta, DeltaSeverity};

/// Classification of a delta: real signal or adversary-generated noise.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum DeltaAuthenticity {
    /// Likely a real signal worth attending to.
    Authentic,
    /// Possibly an adversary-generated fake delta.
    Suspicious,
    /// Almost certainly a manufactured delta.
    Manufactured,
}

/// Result of fake delta detection.
#[derive(Debug, Clone)]
pub struct FakeDeltaReport {
    /// The delta being analyzed.
    pub delta: Delta,
    /// Estimated authenticity.
    pub authenticity: DeltaAuthenticity,
    /// Confidence in the assessment [0..1].
    pub confidence: f64,
    /// Suspiciousness score [0..1] — higher = more likely fake.
    pub suspiciousness: f64,
    /// Reasons for this assessment.
    pub indicators: Vec<String>,
}

/// Detects fake deltas by analyzing patterns across multiple streams.
///
/// Uses the following heuristics:
/// - **Consistency check**: Does this delta correlate with known patterns?
/// - **Temporal coherence**: Does the delta persist or is it an instant blip?
/// - **Cross-stream correlation**: Does this delta make sense across streams?
/// - **Statistical anomaly**: Is the delta's magnitude anomalous for this stream?
///
/// # Examples
///
/// ```
/// use snapkit::{FakeDeltaDetector, Delta, DeltaSeverity, SnapFunction};
///
/// let detector = FakeDeltaDetector::new(0.7);
///
/// let delta = Delta {
///     value: 5.0,
///     expected: 0.0,
///     magnitude: 5.0,
///     tolerance: 0.1,
///     severity: DeltaSeverity::Critical,
///     timestamp: 1,
///     stream_id: "test".to_string(),
///     attention_weight: 10.0,
/// };
///
/// let report = detector.analyze(&delta, &[]);
/// // A single isolated critical delta with no context is suspicious
/// assert_eq!(report.suspiciousness > 0.5, true);
/// ```
pub struct FakeDeltaDetector {
    /// Threshold above which a delta is flagged as suspicious [0..1].
    threshold: f64,
    /// History of deltas per stream for pattern analysis.
    history: Vec<Delta>,
}

impl FakeDeltaDetector {
    /// Create a new fake delta detector.
    pub fn new(threshold: f64) -> Self {
        Self {
            threshold: threshold.clamp(0.0, 1.0),
            history: Vec::new(),
        }
    }

    /// Analyze a delta for authenticity.
    ///
    /// `context_deltas` are recent deltas from OTHER streams that provide
    /// cross-stream context for the analysis.
    pub fn analyze(&self, delta: &Delta, context_deltas: &[&Delta]) -> FakeDeltaReport {
        let mut indicators = Vec::new();
        let mut suspiciousness = 0.0_f64;

        // 1. Magnitude check: extremely large deltas without buildup are suspicious
        let magnitude_ratio = delta.magnitude / delta.tolerance.max(0.001);
        if magnitude_ratio > 10.0 {
            suspiciousness += 0.3;
            indicators.push("extreme magnitude ratio".to_string());
        }

        // 2. Timestamp isolation: delta with no nearby observations
        let has_nearby = self
            .history
            .iter()
            .rev()
            .take(5)
            .any(|h| h.stream_id == delta.stream_id);
        if !has_nearby && !self.history.is_empty() {
            suspiciousness += 0.2;
            indicators.push("isolated from recent history".to_string());
        }

        // 3. Cross-stream consistency: if every stream shows a delta, it's more suspicious
        if !context_deltas.is_empty() {
            let all_deltas = context_deltas
                .iter()
                .filter(|d| d.exceeds_tolerance())
                .count();
            let ratio = all_deltas as f64 / context_deltas.len() as f64;
            if ratio > 0.8 {
                suspiciousness += 0.15;
                indicators.push("multi-stream anomaly".to_string());
            }
        }

        // 4. Severity spike: jumping from None/Nothing to Critical without Medium
        if delta.severity == DeltaSeverity::Critical {
            let recent_severities: Vec<DeltaSeverity> = self
                .history
                .iter()
                .rev()
                .take(3)
                .map(|h| h.severity)
                .collect();
            if recent_severities.iter().all(|s| *s == DeltaSeverity::None) {
                suspiciousness += 0.25;
                indicators.push("severity spike without buildup".to_string());
            }
        }

        // 5. Attention weight: abnormally high weight is suspicious
        if delta.attention_weight > 8.0 {
            suspiciousness += 0.1;
            indicators.push("abnormally high attention weight".to_string());
        }

        let authenticity = if suspiciousness >= self.threshold {
            DeltaAuthenticity::Suspicious
        } else if suspiciousness >= 0.8 {
            DeltaAuthenticity::Manufactured
        } else {
            DeltaAuthenticity::Authentic
        };

        FakeDeltaReport {
            delta: delta.clone(),
            authenticity,
            confidence: 1.0 - suspiciousness.clamp(0.0, 1.0),
            suspiciousness: suspiciousness.clamp(0.0, 1.0),
            indicators,
        }
    }

    /// Record a delta in the detector's history for pattern analysis.
    pub fn record(&mut self, delta: Delta) {
        self.history.push(delta);
    }

    /// Set the suspicion threshold.
    pub fn set_threshold(&mut self, threshold: f64) {
        self.threshold = threshold.clamp(0.0, 1.0);
    }

    /// Clear history.
    pub fn clear_history(&mut self) {
        self.history.clear();
    }
}

/// Generates camouflage signals to mask authentic deltas.
///
/// In adversarial settings (poker, negotiation), you may want to
/// generate noise to make it harder for adversaries to read your
/// authentic deltas.
///
/// # Examples
///
/// ```
/// use snapkit::{CamouflageGenerator};
///
/// let mut gen = CamouflageGenerator::new(0.3);
/// let noise = gen.generate_noise(5);
/// assert_eq!(noise.len(), 5);
/// ```
pub struct CamouflageGenerator {
    /// Noise amplitude as fraction of expected stream tolerance.
    amplitude: f64,
}

impl CamouflageGenerator {
    /// Create a new camouflage generator.
    ///
    /// `amplitude` controls how much noise to inject (0 = none, 1 = maximum).
    pub fn new(amplitude: f64) -> Self {
        Self {
            amplitude: amplitude.clamp(0.0, 1.0),
        }
    }

    /// Generate noise values to inject into a stream.
    ///
    /// Returns `n` noise values that look like authentic deltas but are
    /// actually manufactured to confuse adversarial delta detectors.
    pub fn generate_noise(&self, n: usize) -> Vec<f64> {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};

        let mut noise = Vec::with_capacity(n);
        for i in 0..n {
            // Deterministic noise from index — looks "real" but is reproducible
            let mut hasher = DefaultHasher::new();
            i.hash(&mut hasher);
            let h = hasher.finish();
            let normalized = (h as f64 / u64::MAX as f64) * 2.0 - 1.0;
            noise.push(normalized * self.amplitude);
        }
        noise
    }

    /// Apply camouflage noise to a real value.
    ///
    /// Returns the value with noise added, simulating a camouflaged signal.
    pub fn apply_camouflage(&self, value: f64, index: usize) -> f64 {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};

        let mut hasher = DefaultHasher::new();
        index.hash(&mut hasher);
        value.to_bits().hash(&mut hasher);
        let h = hasher.finish();
        let normalized = (h as f64 / u64::MAX as f64) * 2.0 - 1.0;
        value + normalized * self.amplitude
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_delta(stream_id: &str, magnitude: f64, severity: DeltaSeverity) -> Delta {
        Delta {
            value: magnitude,
            expected: 0.0,
            magnitude,
            tolerance: 0.1,
            severity,
            timestamp: 1,
            stream_id: stream_id.to_string(),
            attention_weight: magnitude.min(10.0),
        }
    }

    #[test]
    fn test_fake_delta_detector_authentic() {
        let detector = FakeDeltaDetector::new(0.7);
        let delta = make_delta("stream1", 0.5, DeltaSeverity::Medium);
        let report = detector.analyze(&delta, &[]);
        assert_eq!(report.authenticity, DeltaAuthenticity::Authentic);
    }

    #[test]
    fn test_fake_delta_detector_suspicious() {
        let detector = FakeDeltaDetector::new(0.3);
        // Extreme magnitude + no history = suspicious
        let delta = make_delta("stream1", 5.0, DeltaSeverity::Critical);
        let report = detector.analyze(&delta, &[]);
        assert_eq!(report.authenticity, DeltaAuthenticity::Suspicious);
    }

    #[test]
    fn test_fake_delta_detector_multi_stream() {
        let detector = FakeDeltaDetector::new(0.5);
        let delta = make_delta("stream1", 5.0, DeltaSeverity::Critical);

        // All context streams also show deltas = more suspicious
        let d2 = make_delta("s2", 4.0, DeltaSeverity::Critical);
        let d3 = make_delta("s3", 3.0, DeltaSeverity::High);
        let d4 = make_delta("s4", 5.0, DeltaSeverity::Critical);

        let context = vec![&d2, &d3, &d4];

        let report = detector.analyze(&delta, &context);
        assert_eq!(report.authenticity, DeltaAuthenticity::Suspicious);
    }

    #[test]
    fn test_fake_delta_indicators() {
        let detector = FakeDeltaDetector::new(0.3);
        let delta = make_delta("stream1", 5.0, DeltaSeverity::Critical);
        let report = detector.analyze(&delta, &[]);
        assert!(!report.indicators.is_empty());
    }

    #[test]
    fn test_camouflage_generate_noise() {
        let gen = CamouflageGenerator::new(0.3);
        let noise = gen.generate_noise(10);
        assert_eq!(noise.len(), 10);
        // All noise values should be within amplitude
        for n in &noise {
            assert!((*n).abs() <= 0.3);
        }
    }

    #[test]
    fn test_camouflage_apply() {
        let gen = CamouflageGenerator::new(0.5);
        let camouflaged = gen.apply_camouflage(1.0, 42);
        assert!(camouflaged != 1.0); // should have added noise
        assert!((camouflaged - 1.0).abs() <= 0.5); // within amplitude
    }

    #[test]
    fn test_delta_authenticity_order() {
        // Just verify the enum ordering makes sense
        assert_ne!(DeltaAuthenticity::Authentic as u8, DeltaAuthenticity::Manufactured as u8);
    }

    #[test]
    fn test_threshold_clamping() {
        let detector = FakeDeltaDetector::new(2.0); // > 1.0
        assert!(detector.threshold <= 1.0);

        let detector = FakeDeltaDetector::new(-0.5); // < 0.0
        assert!(detector.threshold >= 0.0);
    }
}
