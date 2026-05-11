//! DeltaDetector — tracking what exceeds attention tolerance.
//!
//! The delta detector monitors information streams and flags observations
//! that exceed snap tolerance. The felt delta IS the primary information
//! signal — not the calculated probability, but the qualitative shift from
//! "expected" to "unexpected."
//!
//! "The delta is the compass needle. It points attention toward the part
//! of the information landscape where thinking can make the most difference."

use crate::snap::SnapFunction;

/// How significant a delta is.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum DeltaSeverity {
    /// Within tolerance — no delta.
    None,
    /// Just outside tolerance.
    Low,
    /// Clearly exceeds tolerance.
    Medium,
    /// Far from expected.
    High,
    /// Extremely far — possible system failure.
    Critical,
}

/// A felt delta — information that exceeded snap tolerance.
///
/// The delta is not just a number. It encodes the qualitative quality
/// of "something changed" that can be patterned across domains.
#[derive(Debug, Clone, PartialEq)]
pub struct Delta {
    /// The observed value.
    pub value: f64,
    /// The expected (baseline) value.
    pub expected: f64,
    /// Absolute magnitude of the deviation.
    pub magnitude: f64,
    /// Current snap tolerance.
    pub tolerance: f64,
    /// Severity classification.
    pub severity: DeltaSeverity,
    /// Timestamp (observation counter) for ordering.
    pub timestamp: u64,
    /// Which stream this delta belongs to.
    pub stream_id: String,
    /// How much attention this delta merits [0..1].
    pub attention_weight: f64,
}

impl Delta {
    /// Returns true if this delta exceeds tolerance (is non-trivial).
    #[inline]
    pub fn exceeds_tolerance(&self) -> bool {
        self.severity != DeltaSeverity::None
    }
}

/// A stream of deltas from a single information source.
///
/// Each stream has its own snap function, tolerance, and topology.
/// Multiple streams model the multi-layer architecture of expert cognition
/// (e.g., poker: cards, behavior, betting, emotion, dynamics).
///
/// # Examples
///
/// ```
/// use snapkit::{DeltaStream, SnapFunction};
///
/// let snap = SnapFunction::<f64>::new();
/// let mut stream = DeltaStream::new("cards", snap);
///
/// let delta = stream.observe(0.05);
/// assert!(!delta.exceeds_tolerance()); // within tolerance
///
/// let delta = stream.observe(0.3);
/// assert!(delta.exceeds_tolerance()); // delta detected
/// ```
#[derive(Debug, Clone)]
pub struct DeltaStream {
    /// Identifier for this stream.
    pub stream_id: String,
    /// The snap function gating this stream.
    pub snap: SnapFunction<f64>,
    /// History of all deltas produced by this stream.
    deltas: Vec<Delta>,
    /// Tick counter for timestamps.
    tick: u64,
}

impl DeltaStream {
    /// Create a new delta stream.
    pub fn new(stream_id: &str, snap: SnapFunction<f64>) -> Self {
        Self {
            stream_id: stream_id.to_string(),
            snap,
            deltas: Vec::new(),
            tick: 0,
        }
    }

    /// Observe a value and produce a delta.
    pub fn observe(&mut self, value: f64) -> Delta {
        self.tick += 1;
        let result = self.snap.observe(value);

        let severity = classify_severity(result.delta, result.tolerance);
        let attention_weight = compute_attention_weight(result.delta, result.tolerance);

        let delta = Delta {
            value,
            expected: self.snap.baseline(),
            magnitude: result.delta,
            tolerance: result.tolerance,
            severity,
            timestamp: self.tick,
            stream_id: self.stream_id.clone(),
            attention_weight,
        };

        self.deltas.push(delta.clone());
        delta
    }

    /// Get the n most recent deltas.
    pub fn recent_deltas(&self, n: usize) -> &[Delta] {
        let len = self.deltas.len();
        if len <= n {
            &self.deltas
        } else {
            &self.deltas[len - n..]
        }
    }

    /// Get all deltas that exceed tolerance.
    pub fn nontrivial_deltas(&self) -> Vec<&Delta> {
        self.deltas.iter().filter(|d| d.exceeds_tolerance()).collect()
    }

    /// Total observations processed.
    pub fn total_observations(&self) -> u64 {
        self.tick
    }

    /// Number of nontrivial deltas detected.
    pub fn delta_count(&self) -> u64 {
        self.deltas.iter().filter(|d| d.exceeds_tolerance()).count() as u64
    }

    /// Rate of nontrivial deltas [0..1].
    pub fn delta_rate(&self) -> f64 {
        if self.tick == 0 {
            return 0.0;
        }
        self.delta_count() as f64 / self.tick as f64
    }
}

/// Multi-stream delta detector — the core of the attention allocation engine.
///
/// Monitors multiple information streams simultaneously, each with its own
/// snap function and tolerance. Deltas are ranked by attention weight to
/// determine which deserve cognitive resources.
///
/// # Examples
///
/// ```
/// use snapkit::{DeltaDetector, SnapFunction};
///
/// let mut detector = DeltaDetector::new();
///
/// detector.add_stream("cards", SnapFunction::<f64>::new());
/// detector.add_stream("behavior", SnapFunction::<f64>::new());
///
/// detector.observe("cards", 0.05);
/// detector.observe("behavior", 0.3);
///
/// let prioritized = detector.prioritize(3);
/// assert_eq!(prioritized.len(), 1); // only behavior is nontrivial
/// ```
#[derive(Debug, Clone)]
pub struct DeltaDetector {
    streams: std::collections::HashMap<String, DeltaStream>,
}

impl DeltaDetector {
    /// Create a new delta detector.
    pub fn new() -> Self {
        Self {
            streams: std::collections::HashMap::new(),
        }
    }

    /// Add an information stream to monitor.
    pub fn add_stream(&mut self, stream_id: &str, snap: SnapFunction<f64>) {
        let stream = DeltaStream::new(stream_id, snap);
        self.streams.insert(stream_id.to_string(), stream);
    }

    /// Remove a stream from monitoring.
    pub fn remove_stream(&mut self, stream_id: &str) -> bool {
        self.streams.remove(stream_id).is_some()
    }

    /// Observe a value on a specific stream.
    ///
    /// Returns `None` if the stream doesn't exist.
    pub fn observe(&mut self, stream_id: &str, value: f64) -> Option<Delta> {
        self.streams.get_mut(stream_id).map(|s| s.observe(value))
    }

    /// Observe values across multiple streams at once.
    ///
    /// Takes a slice of (stream_id, value) pairs.
    /// Returns a `Vec<(String, Delta)>` of results.
    pub fn observe_batch(&mut self, observations: &[(&str, f64)]) -> Vec<(String, Delta)> {
        observations
            .iter()
            .filter_map(|&(sid, val)| {
                self.observe(sid, val).map(|d| (sid.to_string(), d))
            })
            .collect()
    }

    /// Prioritize deltas by attention weight.
    ///
    /// Returns the top-k non-trivial deltas sorted by attention weight
    /// (descending). These are the deltas that DESERVE cognitive resources.
    pub fn prioritize(&self, top_k: usize) -> Vec<&Delta> {
        let mut all: Vec<&Delta> = self
            .streams
            .values()
            .flat_map(|s| s.deltas.iter().filter(|d| d.exceeds_tolerance()))
            .collect();

        all.sort_by(|a, b| {
            b.attention_weight
                .partial_cmp(&a.attention_weight)
                .unwrap_or(std::cmp::Ordering::Equal)
        });

        all.truncate(top_k);
        all
    }

    /// Get the most recent delta from each stream.
    pub fn current_deltas(&self) -> Vec<(&str, Option<&Delta>)> {
        self.streams
            .iter()
            .map(|(sid, s)| (sid.as_str(), s.deltas.last()))
            .collect()
    }

    /// Get a reference to a specific stream, if it exists.
    pub fn get_stream(&self, stream_id: &str) -> Option<&DeltaStream> {
        self.streams.get(stream_id)
    }

    /// Get a mutable reference to a specific stream, if it exists.
    pub fn get_stream_mut(&mut self, stream_id: &str) -> Option<&mut DeltaStream> {
        self.streams.get_mut(stream_id)
    }

    /// Number of streams being monitored.
    pub fn num_streams(&self) -> usize {
        self.streams.len()
    }

    /// Total deltas (all severities) across all streams.
    pub fn total_deltas(&self) -> usize {
        self.streams.values().map(|s| s.deltas.len()).sum()
    }

    /// Clear all delta history (keeps streams and their snap functions).
    pub fn clear_history(&mut self) {
        for stream in self.streams.values_mut() {
            stream.deltas.clear();
            stream.tick = 0;
        }
    }
}

impl Default for DeltaDetector {
    fn default() -> Self {
        Self::new()
    }
}

// --- Helpers ---

fn classify_severity(delta: f64, tolerance: f64) -> DeltaSeverity {
    if tolerance <= 0.0 {
        return if delta > 0.0 {
            DeltaSeverity::Critical
        } else {
            DeltaSeverity::None
        };
    }
    let ratio = delta / tolerance;
    if ratio <= 1.0 {
        DeltaSeverity::None
    } else if ratio <= 1.5 {
        DeltaSeverity::Low
    } else if ratio <= 3.0 {
        DeltaSeverity::Medium
    } else if ratio <= 5.0 {
        DeltaSeverity::High
    } else {
        DeltaSeverity::Critical
    }
}

/// Compute attention weight from magnitude and tolerance.
///
/// Attention weight = delta / tolerance (capped at 10.0).
/// A delta exactly at tolerance has weight 1.0.
fn compute_attention_weight(delta: f64, tolerance: f64) -> f64 {
    if tolerance <= 0.0 {
        return 10.0; // max attention
    }
    (delta / tolerance).min(10.0)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_delta_stream_within_tolerance() {
        let snap = SnapFunction::<f64>::new();
        let mut stream = DeltaStream::new("test", snap);
        let delta = stream.observe(0.05);
        assert_eq!(delta.severity, DeltaSeverity::None);
        assert!(!delta.exceeds_tolerance());
    }

    #[test]
    fn test_delta_stream_exceeds_tolerance() {
        let snap = SnapFunction::<f64>::new();
        let mut stream = DeltaStream::new("test", snap);
        let delta = stream.observe(0.3);
        assert_eq!(delta.severity, DeltaSeverity::Medium);
        assert!(delta.exceeds_tolerance());
    }

    #[test]
    fn test_delta_stream_severity_scale() {
        let mut snap = SnapFunction::<f64>::new();
        snap.set_tolerance(1.0);
        let mut stream = DeltaStream::new("test", snap);

        // ratio = 0.5 → None
        assert_eq!(stream.observe(0.5).severity, DeltaSeverity::None);
        // ratio = 1.2 → Low
        assert_eq!(stream.observe(1.2).severity, DeltaSeverity::Low);
        // ratio = 2.5 → Medium
        assert_eq!(stream.observe(2.5).severity, DeltaSeverity::Medium);
        // ratio = 4.0 → High
        assert_eq!(stream.observe(4.0).severity, DeltaSeverity::High);
        // ratio = 6.0 → Critical
        assert_eq!(stream.observe(6.0).severity, DeltaSeverity::Critical);
    }

    #[test]
    fn test_delta_detector() {
        let mut detector = DeltaDetector::new();

        detector.add_stream("cards", SnapFunction::<f64>::new());
        detector.add_stream("behavior", SnapFunction::<f64>::new());

        // Within tolerance for cards, delta for behavior
        detector.observe("cards", 0.05);
        detector.observe("behavior", 0.3);

        let prioritized = detector.prioritize(3);
        assert_eq!(prioritized.len(), 1);
        assert_eq!(prioritized[0].stream_id, "behavior");
    }

    #[test]
    fn test_delta_detector_empty() {
        let detector = DeltaDetector::new();
        assert_eq!(detector.num_streams(), 0);
        assert!(detector.prioritize(3).is_empty());
    }

    #[test]
    fn test_delta_detector_nonexistent_stream() {
        let mut detector = DeltaDetector::new();
        let delta = detector.observe("nonexistent", 1.0);
        assert!(delta.is_none());
    }

    #[test]
    fn test_recent_deltas() {
        let snap = SnapFunction::<f64>::new();
        let mut stream = DeltaStream::new("test", snap);

        stream.observe(0.05);
        stream.observe(0.08);
        stream.observe(0.3);

        let recent = stream.recent_deltas(2);
        assert_eq!(recent.len(), 2);
        assert!((recent[0].value - 0.08).abs() < 1e-10);
        assert!((recent[1].value - 0.3).abs() < 1e-10);
    }

    #[test]
    fn test_nontrivial_filter() {
        let snap = SnapFunction::<f64>::new();
        let mut stream = DeltaStream::new("test", snap);

        stream.observe(0.05); // snap
        stream.observe(0.3);  // delta
        stream.observe(0.02); // snap

        let nontrivial = stream.nontrivial_deltas();
        assert_eq!(nontrivial.len(), 1);
    }

    #[test]
    fn test_delta_rate() {
        let snap = SnapFunction::<f64>::new();
        let mut stream = DeltaStream::new("test", snap);

        stream.observe(0.05);
        stream.observe(0.02);
        stream.observe(0.3);

        assert!((stream.delta_rate() - 1.0 / 3.0).abs() < 1e-10);
    }

    #[test]
    fn test_observe_batch() {
        let mut detector = DeltaDetector::new();
        detector.add_stream("a", SnapFunction::<f64>::new());
        detector.add_stream("b", SnapFunction::<f64>::new());

        let results = detector.observe_batch(&[("a", 0.05), ("b", 0.3), ("a", 0.4)]);
        assert_eq!(results.len(), 3);
        // a's first observation is within tolerance
        assert!(!results[0].1.exceeds_tolerance());
        // b's observation is outside tolerance
        assert!(results[1].1.exceeds_tolerance());
    }
}
