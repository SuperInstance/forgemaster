//! ScriptLibrary — learned patterns that free cognition.
//!
//! Scripts are compressed, pre-learned sequences that can be executed
//! without conscious thought. When a pattern snaps to a known script,
//! cognition is freed for higher-level planning.
//!
//! "Knowledge is when to think and planning scripts that free the mind."
//! — SNAPS-AS-ATTENTION.md

use std::collections::HashMap;

/// Status of a script in the library.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum ScriptStatus {
    /// Newly created, not yet verified.
    Draft,
    /// Verified and in use.
    Active,
    /// Partially failing, needs update.
    Degraded,
    /// No longer used.
    Archived,
}

/// Result of matching an observation against the script library.
#[derive(Debug, Clone)]
pub struct ScriptMatch {
    /// ID of the matching script.
    pub script_id: String,
    /// How well the pattern matches [0..1].
    pub confidence: f64,
    /// Whether this is above the match threshold.
    pub is_match: bool,
    /// Euclidean distance from the trigger pattern.
    pub delta_from_template: f64,
}

impl ScriptMatch {
    fn new(script_id: String, confidence: f64, threshold: f64, delta: f64) -> Self {
        Self {
            is_match: confidence >= threshold,
            script_id,
            confidence,
            delta_from_template: delta,
        }
    }
}

/// A learned pattern that can be executed automatically.
///
/// Scripts are the "vocabulary" of expertise. They encode:
/// - A trigger pattern (what activates this script)
/// - A response (what the script does)
/// - A context (when this script is appropriate)
/// - Success/failure statistics (for monitoring)
///
/// Like speedcubing algorithms or poker basic strategy:
/// recognized automatically, executed without thinking.
#[derive(Debug, Clone)]
pub struct Script {
    /// Unique identifier.
    pub id: String,
    /// Human-readable name.
    pub name: String,
    /// The pattern that activates this script (as a flat Vec of coefficients).
    pub trigger_pattern: Vec<f64>,
    /// The pre-computed response (stored as a JSON-like map).
    pub response: serde_json::Value,
    /// Context metadata for the script.
    pub context: HashMap<String, String>,
    /// Minimum similarity to activate.
    pub match_threshold: f64,
    /// Current status.
    pub status: ScriptStatus,
    /// Number of times this script has been used.
    pub use_count: u64,
    /// Number of successful uses.
    pub success_count: u64,
    /// Number of failed uses.
    pub fail_count: u64,
    /// Timestamp of last use.
    pub last_used: u64,
    /// Current confidence in this script.
    pub confidence: f64,
}

impl Script {
    /// Check if an observation matches this script's trigger pattern.
    ///
    /// Uses cosine similarity between observation and trigger pattern.
    pub fn match_observation(&self, observation: &[f64]) -> ScriptMatch {
        if self.status != ScriptStatus::Active {
            return ScriptMatch::new(
                self.id.clone(),
                0.0,
                self.match_threshold,
                f64::INFINITY,
            );
        }

        if observation.len() != self.trigger_pattern.len() {
            return ScriptMatch::new(
                self.id.clone(),
                0.0,
                self.match_threshold,
                f64::INFINITY,
            );
        }

        // Cosine similarity
        let dot: f64 = observation
            .iter()
            .zip(self.trigger_pattern.iter())
            .map(|(a, b)| a * b)
            .sum();

        let norm_obs: f64 = observation.iter().map(|x| x * x).sum::<f64>().sqrt();
        let norm_tpl: f64 = self.trigger_pattern.iter().map(|x| x * x).sum::<f64>().sqrt();

        let similarity = if norm_obs == 0.0 || norm_tpl == 0.0 {
            0.0
        } else {
            dot / (norm_obs * norm_tpl)
        };

        // Convert similarity [-1, 1] to confidence [0, 1]
        let confidence = (similarity + 1.0) / 2.0;

        // Euclidean distance from template
        let delta: f64 = observation
            .iter()
            .zip(self.trigger_pattern.iter())
            .map(|(a, b)| (a - b).powi(2))
            .sum::<f64>()
            .sqrt();

        ScriptMatch::new(self.id.clone(), confidence, self.match_threshold, delta)
    }

    /// Record a use of this script.
    pub fn record_use(&mut self, success: bool, timestamp: u64) {
        self.use_count += 1;
        self.last_used = timestamp;
        if success {
            self.success_count += 1;
        } else {
            self.fail_count += 1;
        }
        self.update_confidence();
    }

    fn update_confidence(&mut self) {
        if self.use_count == 0 {
            self.confidence = 1.0;
            return;
        }
        let success_rate = self.success_count as f64 / self.use_count as f64;
        // Decay: weight by count, penalize failures
        self.confidence = success_rate * (self.success_count as f64 / self.use_count as f64).min(1.0);

        // Degrade if failing consistently
        if self.use_count > 5 && success_rate < 0.5 {
            self.status = ScriptStatus::Degraded;
        }
    }

    /// Success rate of this script [0..1].
    pub fn success_rate(&self) -> f64 {
        if self.use_count == 0 {
            return 1.0;
        }
        self.success_count as f64 / self.use_count as f64
    }
}

/// Library of learned scripts — the system's "muscle memory."
///
/// The script library stores pre-verified response sequences indexed
/// by their trigger patterns. When an observation snaps to a known
/// pattern, the corresponding script executes automatically, freeing
/// cognition for planning.
///
/// # Examples
///
/// ```
/// use snapkit::{ScriptLibrary, Script};
/// use std::collections::HashMap;
///
/// let mut library = ScriptLibrary::new(0.85);
///
/// // Add a script
/// library.add_script(Script {
///     id: "fold_weak_hand".to_string(),
///     name: "Fold weak hand out of position".to_string(),
///     trigger_pattern: vec![0.1, 0.2, 0.3],
///     response: serde_json::json!({"action": "fold"}),
///     context: HashMap::new(),
///     match_threshold: 0.85,
///     status: snapkit::ScriptStatus::Active,
///     use_count: 0,
///     success_count: 0,
///     fail_count: 0,
///     last_used: 0,
///     confidence: 1.0,
/// });
///
/// let match_result = library.find_best_match(&[0.12, 0.19, 0.31]);
/// assert!(match_result.is_some());
/// assert!(match_result.unwrap().is_match);
/// ```
#[derive(Debug, Clone)]
pub struct ScriptLibrary {
    /// Match threshold for script activation.
    pub match_threshold: f64,
    /// All scripts indexed by ID.
    scripts: HashMap<String, Script>,
    /// How many lookups found a match.
    hit_count: u64,
    /// How many lookups found no match.
    miss_count: u64,
    /// Tick counter for timestamps.
    tick: u64,
}

impl ScriptLibrary {
    /// Create a new script library with a given match threshold.
    pub fn new(match_threshold: f64) -> Self {
        Self {
            match_threshold,
            scripts: HashMap::new(),
            hit_count: 0,
            miss_count: 0,
            tick: 0,
        }
    }

    /// Add a script to the library.
    pub fn add_script(&mut self, mut script: Script) {
        script.match_threshold = self.match_threshold;
        self.scripts.insert(script.id.clone(), script);
    }

    /// Retrieve a script by ID.
    pub fn get(&self, script_id: &str) -> Option<&Script> {
        self.scripts.get(script_id)
    }

    /// Retrieve a mutable reference to a script by ID.
    pub fn get_mut(&mut self, script_id: &str) -> Option<&mut Script> {
        self.scripts.get_mut(script_id)
    }

    /// Find the best matching script for an observation.
    ///
    /// Returns `None` if no script matches above threshold.
    pub fn find_best_match(&mut self, observation: &[f64]) -> Option<ScriptMatch> {
        self.tick += 1;

        if self.scripts.is_empty() {
            self.miss_count += 1;
            return None;
        }

        let mut best_match: Option<ScriptMatch> = None;
        let mut best_confidence = 0.0;

        for script in self.scripts.values().filter(|s| s.status == ScriptStatus::Active) {
            let match_result = script.match_observation(observation);
            if match_result.confidence > best_confidence {
                best_confidence = match_result.confidence;
                best_match = Some(match_result);
            }
        }

        match best_match {
            Some(m) if m.is_match => {
                self.hit_count += 1;
                Some(m)
            }
            _ => {
                self.miss_count += 1;
                // Return the best match even if below threshold
                best_match
            }
        }
    }

    /// Find all scripts that match an observation above a loose threshold.
    pub fn find_all_matches(&self, observation: &[f64]) -> Vec<ScriptMatch> {
        let mut matches: Vec<ScriptMatch> = self
            .scripts
            .values()
            .filter(|s| s.status == ScriptStatus::Active)
            .map(|s| s.match_observation(observation))
            .filter(|m| m.confidence > 0.5) // Loose threshold
            .collect();

        matches.sort_by(|a, b| {
            b.confidence
                .partial_cmp(&a.confidence)
                .unwrap_or(std::cmp::Ordering::Equal)
        });
        matches
    }

    /// Learn a new script from a pattern-response pair.
    ///
    /// This is the "building" phase of the expertise cycle:
    /// a novel situation has been encountered, reasoned about,
    /// and the solution is cached as a script for future use.
    pub fn learn(
        &mut self,
        trigger_pattern: Vec<f64>,
        response: serde_json::Value,
        name: &str,
        context: HashMap<String, String>,
    ) -> String {
        // Generate a deterministic ID from the pattern
        let mut hasher = std::collections::hash_map::DefaultHasher::new();
        use std::hash::Hasher;
        for &val in &trigger_pattern {
            let bits = val.to_bits();
            hasher.write_u64(bits);
        }
        let hash = hasher.finish();
        let script_id = format!("script_{:016x}", hash);

        let script = Script {
            id: script_id.clone(),
            name: if name.is_empty() {
                format!("script_{:016x}", hash)
            } else {
                name.to_string()
            },
            trigger_pattern,
            response,
            context,
            match_threshold: self.match_threshold,
            status: ScriptStatus::Active,
            use_count: 0,
            success_count: 0,
            fail_count: 0,
            last_used: self.tick,
            confidence: 1.0,
        };

        self.add_script(script);
        script_id
    }

    /// Archive a script (don't delete — might need to rebuild).
    pub fn archive(&mut self, script_id: &str) -> bool {
        if let Some(script) = self.scripts.get_mut(script_id) {
            script.status = ScriptStatus::Archived;
            true
        } else {
            false
        }
    }

    /// Remove scripts that are failing consistently.
    pub fn prune(&mut self, min_uses: u64, min_success_rate: f64) {
        for script in self.scripts.values_mut() {
            if script.use_count >= min_uses && script.success_rate() < min_success_rate {
                script.status = ScriptStatus::Degraded;
            }
        }
    }

    /// Fraction of lookups that found a matching script [0..1].
    pub fn hit_rate(&self) -> f64 {
        let total = self.hit_count + self.miss_count;
        if total == 0 {
            return 0.0;
        }
        self.hit_count as f64 / total as f64
    }

    /// Number of active scripts.
    pub fn active_scripts(&self) -> usize {
        self.scripts
            .values()
            .filter(|s| s.status == ScriptStatus::Active)
            .count()
    }

    /// Total number of scripts (all statuses).
    pub fn total_scripts(&self) -> usize {
        self.scripts.len()
    }

    /// Total lookup attempts.
    pub fn total_lookups(&self) -> u64 {
        self.hit_count + self.miss_count
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_test_script(id: &str) -> Script {
        Script {
            id: id.to_string(),
            name: format!("test_script_{}", id),
            trigger_pattern: vec![1.0, 2.0, 3.0],
            response: serde_json::json!({"action": "test"}),
            context: HashMap::new(),
            match_threshold: 0.85,
            status: ScriptStatus::Active,
            use_count: 0,
            success_count: 0,
            fail_count: 0,
            last_used: 0,
            confidence: 1.0,
        }
    }

    #[test]
    fn test_script_match_exact() {
        let script = make_test_script("exact");
        let observation = vec![1.0, 2.0, 3.0];
        let match_result = script.match_observation(&observation);
        assert!(match_result.is_match);
        assert!((match_result.confidence - 1.0).abs() < 1e-10);
    }

    #[test]
    fn test_script_match_close() {
        let script = make_test_script("close");
        let observation = vec![1.1, 2.0, 2.9];
        let match_result = script.match_observation(&observation);
        assert!(match_result.is_match);
    }

    #[test]
    fn test_script_match_no_match() {
        let script = make_test_script("no_match");
        // Orthogonal vector — should not match
        let observation = vec![1.0, -2.0, 1.0]; // dot = 1-4+3 = 0
        let match_result = script.match_observation(&observation);
        assert!(!match_result.is_match);
    }

    #[test]
    fn test_script_degraded_doesnt_match() {
        let mut script = make_test_script("degraded");
        script.status = ScriptStatus::Degraded;
        let observation = vec![1.0, 2.0, 3.0];
        let match_result = script.match_observation(&observation);
        assert!(!match_result.is_match);
    }

    #[test]
    fn test_script_library() {
        let mut library = ScriptLibrary::new(0.85);
        library.add_script(make_test_script("s1"));
        library.add_script(make_test_script("s2"));

        let result = library.find_best_match(&[1.0, 2.0, 3.0]);
        assert!(result.is_some());
        assert!(result.unwrap().is_match);

        let result = library.find_best_match(&[1.0, -2.0, 1.0]);
        // Should still return the best match but with is_match = false
        assert!(result.is_some());
        assert!(!result.unwrap().is_match);
    }

    #[test]
    fn test_script_library_empty() {
        let mut library = ScriptLibrary::new(0.85);
        let result = library.find_best_match(&[1.0, 2.0, 3.0]);
        assert!(result.is_none());
    }

    #[test]
    fn test_script_library_hit_rate() {
        let mut library = ScriptLibrary::new(0.85);
        library.add_script(make_test_script("s1"));

        // Two lookups: hit + miss = 50% hit rate
        library.find_best_match(&[1.0, 2.0, 3.0]);
        library.find_best_match(&[1.0, -2.0, 1.0]);

        // 50% hit rate (one hit, one miss)
        assert!((library.hit_rate() - 0.5).abs() < 1e-10);
    }

    #[test]
    fn test_learn() {
        let mut library = ScriptLibrary::new(0.85);
        let id = library.learn(
            vec![0.5, 0.7, 0.9],
            serde_json::json!({"action": "learned"}),
            "learned_test",
            HashMap::new(),
        );

        assert!(library.get(&id).is_some());
        assert_eq!(library.active_scripts(), 1);
    }

    #[test]
    fn test_archive() {
        let mut library = ScriptLibrary::new(0.85);
        library.add_script(make_test_script("s1"));
        assert!(library.archive("s1"));
        assert_eq!(library.active_scripts(), 0);
    }

    #[test]
    fn test_prune() {
        let mut library = ScriptLibrary::new(0.85);
        library.add_script(make_test_script("s1"));

        // Simulate many failures
        let script = library.get_mut("s1").unwrap();
        for _ in 0..10 {
            script.record_use(false, 1);
        }

        library.prune(5, 0.3);
        assert!(library.get("s1").unwrap().status == ScriptStatus::Degraded);
    }

    #[test]
    fn test_success_rate() {
        let mut script = make_test_script("sr");
        assert!((script.success_rate() - 1.0).abs() < 1e-10);
        script.record_use(true, 1);
        script.record_use(false, 2);
        assert!((script.success_rate() - 0.5).abs() < 1e-10);
    }

    #[test]
    fn test_find_all_matches() {
        let mut library = ScriptLibrary::new(0.85);
        library.add_script(make_test_script("s1"));
        library.add_script(make_test_script("s2"));

        let matches = library.find_all_matches(&[1.0, 2.0, 3.0]);
        assert_eq!(matches.len(), 2);
        // Both should be sorted by confidence descending
        assert!(matches[0].confidence >= matches[1].confidence);
    }
}
