//! LearningCycle — experience → pattern → script → automation.
//!
//! Expertise follows a cyclic pattern: experience builds scripts, scripts
//! free cognition, freed cognition enables planning, planning handles
//! novelty, and novelty builds new scripts.
//!
//! "The mind oscillates between building scripts (thinking, slow) and
//! running scripts (automatic, fast), monitoring for deltas, and
//! rebuilding when deltas accumulate."

use crate::scripts::ScriptLibrary;
use crate::snap::SnapFunction;

/// Phases of the expertise learning cycle.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum LearningPhase {
    /// No scripts — everything is novel.
    DeltaFlood,
    /// Patterns emerging — rapid script creation.
    ScriptBurst,
    /// Most things snap to scripts — low cognitive load.
    SmoothRunning,
    /// Accumulated deltas — scripts failing.
    Disruption,
    /// Constructing new scripts from deltas.
    Rebuilding,
}

/// Current state of the learning cycle.
#[derive(Debug, Clone)]
pub struct LearningState {
    /// Current phase.
    pub phase: LearningPhase,
    /// Total experiences processed.
    pub total_experiences: u64,
    /// Number of scripts built (total).
    pub scripts_built: usize,
    /// Number of currently active scripts.
    pub scripts_active: usize,
    /// Cognitive load [0..1] — 0 = fully automated, 1 = full attention.
    pub cognitive_load: f64,
    /// Fraction of observations that snap to known patterns.
    pub snap_hit_rate: f64,
    /// Fraction of novel observations (deltas).
    pub delta_rate: f64,
    /// Number of phase transitions.
    pub phase_transitions: u64,
}

/// The learning cycle of expertise.
///
/// Models the four modes of expert cognition:
/// 1. Building scripts (attention-heavy, slow)
/// 2. Running scripts (automatic, attention-free)
/// 3. Monitoring for deltas (light attention)
/// 4. Rebuilding when deltas accumulate (back to building)
///
/// # Examples
///
/// ```
/// use snapkit::{LearningCycle, SnapFunction};
///
/// let snap = SnapFunction::<f64>::new();
/// let mut cycle = LearningCycle::new(snap);
///
/// for value in [0.05, 0.02, 0.3, 0.04, 0.08].iter() {
///     let state = cycle.experience(*value, None);
///     // state.phase tells us which learning phase we're in
/// }
///
/// assert_eq!(cycle.total_experiences(), 5);
/// ```
pub struct LearningCycle {
    snap: SnapFunction<f64>,
    library: ScriptLibrary,
    /// How many consecutive deltas before triggering disruption.
    novelty_threshold: u64,
    /// How many similar deltas before auto-creating a script.
    script_creation_threshold: usize,

    // Internal state
    total_experiences: u64,
    consecutive_deltas: u64,
    pending_deltas: Vec<PendingDelta>,
    phase: LearningPhase,
    phase_transitions: u64,
    states: Vec<LearningState>,
}

/// A delta awaiting script creation.
#[allow(dead_code)]
struct PendingDelta {
    value: f64,
    expected: f64,
    delta_magnitude: f64,
}

impl LearningCycle {
    /// Create a new learning cycle with the given snap function.
    pub fn new(snap: SnapFunction<f64>) -> Self {
        Self {
            snap,
            library: ScriptLibrary::new(0.85),
            novelty_threshold: 5,
            script_creation_threshold: 3,
            total_experiences: 0,
            consecutive_deltas: 0,
            pending_deltas: Vec::new(),
            phase: LearningPhase::DeltaFlood,
            phase_transitions: 0,
            states: Vec::new(),
        }
    }

    /// Set the novelty threshold (consecutive deltas before disruption).
    pub fn set_novelty_threshold(&mut self, threshold: u64) {
        self.novelty_threshold = threshold;
    }

    /// Set the script creation threshold (similar deltas before auto-creating).
    pub fn set_script_creation_threshold(&mut self, threshold: usize) {
        self.script_creation_threshold = threshold;
    }

    /// Process a new experience through the learning cycle.
    ///
    /// Returns the current `LearningState` after processing.
    pub fn experience(&mut self, observation: f64, _context: Option<&str>) -> LearningState {
        self.total_experiences += 1;

        // Step 1: Snap the observation
        let result = self.snap.observe(observation);

        // Step 2: Check for delta
        if result.is_delta() {
            self.consecutive_deltas += 1;
            self.pending_deltas.push(PendingDelta {
                value: observation,
                expected: self.snap.baseline(),
                delta_magnitude: result.delta,
            });
        } else {
            self.consecutive_deltas = 0;
        }

        // Step 3: Check for script match
        if self.library.active_scripts() > 0 {
            let obs_vec = vec![observation];
            let maybe_match = self.library.find_best_match(&obs_vec);
            if let Some(m) = maybe_match {
                if m.is_match {
                    self.consecutive_deltas = 0;
                    if let Some(script) = self.library.get_mut(&m.script_id) {
                        script.record_use(true, self.total_experiences);
                    }
                }
            }
        }

        // Step 4: Create scripts from accumulated deltas
        if self.pending_deltas.len() >= self.script_creation_threshold {
            self.create_script_from_deltas();
        }

        // Step 5: Update phase
        self.update_phase();

        // Record state
        let state = self.current_state();
        self.states.push(state.clone());
        state
    }

    fn create_script_from_deltas(&mut self) {
        if self.pending_deltas.is_empty() {
            return;
        }

        // Compute mean of pending deltas as the trigger pattern
        let sum: f64 = self.pending_deltas.iter().map(|d| d.value).sum();
        let mean = sum / self.pending_deltas.len() as f64;

        let trigger = vec![mean];
        let response = serde_json::json!({"action": "handle", "value": mean});

        self.library.learn(
            trigger,
            response,
            &format!("auto_script_{}", self.total_experiences),
            std::collections::HashMap::new(),
        );

        self.pending_deltas.clear();
    }

    fn update_phase(&mut self) {
        let old_phase = self.phase;
        let hit_rate = self.library.hit_rate();
        let active = self.library.active_scripts();

        self.phase = if self.consecutive_deltas >= self.novelty_threshold * 2 {
            LearningPhase::Rebuilding
        } else if self.consecutive_deltas >= self.novelty_threshold {
            LearningPhase::Disruption
        } else if active == 0 {
            LearningPhase::DeltaFlood
        } else if hit_rate > 0.7 {
            LearningPhase::SmoothRunning
        } else {
            LearningPhase::ScriptBurst
        };

        if self.phase != old_phase {
            self.phase_transitions += 1;
        }
    }

    fn compute_cognitive_load(&self) -> f64 {
        if self.total_experiences == 0 {
            return 1.0;
        }

        let delta_rate = self.snap.delta_rate();
        let script_coverage = self.library.hit_rate();

        // Combined: deltas that scripts don't cover
        let load = delta_rate * (1.0 - script_coverage);
        load.clamp(0.0, 1.0)
    }

    /// Get the current learning state.
    pub fn current_state(&self) -> LearningState {
        LearningState {
            phase: self.phase,
            total_experiences: self.total_experiences,
            scripts_built: self.library.total_scripts(),
            scripts_active: self.library.active_scripts(),
            cognitive_load: self.compute_cognitive_load(),
            snap_hit_rate: self.snap.snap_rate(),
            delta_rate: self.snap.delta_rate(),
            phase_transitions: self.phase_transitions,
        }
    }

    /// Total experiences processed.
    pub fn total_experiences(&self) -> u64 {
        self.total_experiences
    }

    /// Number of phase transitions so far.
    pub fn phase_transitions(&self) -> u64 {
        self.phase_transitions
    }

    /// Get a reference to the script library.
    pub fn library(&self) -> &ScriptLibrary {
        &self.library
    }

    /// Get a mutable reference to the script library.
    pub fn library_mut(&mut self) -> &mut ScriptLibrary {
        &mut self.library
    }

    /// Get a reference to the snap function.
    pub fn snap(&self) -> &SnapFunction<f64> {
        &self.snap
    }

    /// Get a mutable reference to the snap function.
    pub fn snap_mut(&mut self) -> &mut SnapFunction<f64> {
        &mut self.snap
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_learning_cycle_starts_in_delta_flood() {
        let snap = SnapFunction::<f64>::new();
        let cycle = LearningCycle::new(snap);
        assert_eq!(cycle.current_state().phase, LearningPhase::DeltaFlood);
    }

    #[test]
    fn test_learning_cycle_experience() {
        let snap = SnapFunction::<f64>::new();
        let mut cycle = LearningCycle::new(snap);

        // First experience should still be delta flood (no scripts yet)
        let state = cycle.experience(0.05, None);
        assert_eq!(state.phase, LearningPhase::DeltaFlood);
        assert_eq!(state.total_experiences, 1);
    }

    #[test]
    fn test_learning_cycle_script_creation() {
        let snap = SnapFunction::<f64>::new();
        let mut cycle = LearningCycle::new(snap);
        cycle.set_script_creation_threshold(2);

        // Two deltas should trigger script creation
        cycle.experience(0.3, None);
        cycle.experience(0.4, None);

        assert_eq!(cycle.library.active_scripts(), 1);
    }

    #[test]
    fn test_learning_cycle_smooth_running() {
        let mut snap = SnapFunction::<f64>::new();
        snap.set_tolerance(0.5); // wide tolerance
        let mut cycle = LearningCycle::new(snap);

        // Pre-add a script that matches our observations
        cycle.library_mut().learn(
            vec![0.05],
            serde_json::json!({"action": "ok"}),
            "match_script",
            std::collections::HashMap::new(),
        );

        // Several observations within tolerance should lead to smooth running
        for _ in 0..10 {
            cycle.experience(0.05, None);
        }

        assert_eq!(cycle.current_state().phase, LearningPhase::SmoothRunning);
    }

    #[test]
    fn test_learning_cycle_disruption() {
        let mut snap = SnapFunction::<f64>::new();
        snap.set_tolerance(0.01); // very tight — everything is a delta
        let mut cycle = LearningCycle::new(snap);
        cycle.set_novelty_threshold(3);

        // Several consecutive deltas should trigger disruption
        cycle.experience(0.3, None);
        cycle.experience(0.5, None);
        cycle.experience(0.7, None);

        assert_eq!(cycle.current_state().phase, LearningPhase::Disruption);
    }

    #[test]
    fn test_learning_cycle_rebuilding() {
        let mut snap = SnapFunction::<f64>::new();
        snap.set_tolerance(0.01);
        let mut cycle = LearningCycle::new(snap);
        cycle.set_novelty_threshold(3);
        // Don't auto-create scripts from deltas
        cycle.set_script_creation_threshold(usize::MAX);

        // 6 consecutive deltas (2x threshold) → Rebuilding
        for i in 0..6 {
            cycle.experience(0.3 + i as f64 * 0.1, None);
        }

        assert_eq!(cycle.current_state().phase, LearningPhase::Rebuilding);
    }

    #[test]
    fn test_cognitive_load() {
        let mut snap = SnapFunction::<f64>::new();
        snap.set_tolerance(0.01); // everything is a delta
        let mut cycle = LearningCycle::new(snap);

        // High delta rate → high cognitive load
        cycle.experience(1.0, None);
        let load = cycle.current_state().cognitive_load;
        assert!(load > 0.5);
    }

    #[test]
    fn test_phase_transitions_count() {
        let snap = SnapFunction::<f64>::new();
        let mut cycle = LearningCycle::new(snap);

        // Start: DeltaFlood
        // After learning some scripts and getting smooth: transitions happen
        cycle.experience(0.05, None);
        let initial = cycle.phase_transitions();

        // We transitioned internally from DeltaFlood → some other phase
        assert!(initial <= 1);
    }
}
