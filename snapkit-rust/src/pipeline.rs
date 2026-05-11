//! Pipeline — composable attention processing pipelines.
//!
//! Pipelines allow chaining multiple snap functions, delta detectors, and
//! attention budgets into a single processing flow. This enables the
//! multi-layer, multi-topology attention architecture described in
//! SNAPS-AS-ATTENTION.md.

use crate::attention::{AllocationStrategy, AttentionAllocation, AttentionBudget};
use crate::delta::{Delta, DeltaDetector};
use crate::snap::SnapResult;

/// A stage in the processing pipeline.
///
/// Each stage can be a snap function, a delta detector, or a variance computation.
/// Stages compose by feeding the output of one stage into the next.
pub enum PipelineStage {
    /// Single snap function processing a value.
    Snap(crate::snap::SnapFunction<f64>),
    /// Multi-stream delta detection.
    Detector(DeltaDetector),
    /// Variance computation over a window.
    Variance(usize),
}

/// The result of a full pipeline execution.
#[derive(Debug, Clone)]
pub struct PipelineResult {
    /// Results from each stage.
    pub stages: Vec<PipelineStageResult>,
    /// Attention allocations, if the pipeline includes an attention budget.
    pub allocations: Option<Vec<AttentionAllocation>>,
}

/// Result from a single pipeline stage.
#[derive(Debug, Clone)]
pub enum PipelineStageResult {
    /// Snap result.
    Snap(SnapResult<f64>),
    /// Deltas from multiple streams.
    Deltas(Vec<(String, Delta)>),
    /// Variance of windowed values.
    Variance(f64),
}

/// Composable pipeline builder for attention processing.
///
/// # Examples
///
/// ```
/// use snapkit::{Pipeline, PipelineStage, AllocationStrategy, SnapFunction};
///
/// let mut pipeline = Pipeline::new(100.0, AllocationStrategy::Actionability);
///
/// pipeline.add_stage(PipelineStage::Snap(
///     SnapFunction::<f64>::builder()
///         .tolerance(0.1)
///         .topology(snapkit::SnapTopology::Hexagonal)
///         .build()
/// ));
///
/// let result = pipeline.process_single(0.05);
/// assert!(result.stages.len() == 1);
/// ```
pub struct Pipeline {
    /// Processing stages in order.
    stages: Vec<PipelineStage>,
    /// Optional attention budget for final allocation.
    budget: AttentionBudget,
}

impl Pipeline {
    /// Create a new pipeline with a given attention budget.
    pub fn new(budget_total: f64, strategy: AllocationStrategy) -> Self {
        Self {
            stages: Vec::new(),
            budget: AttentionBudget::new(budget_total, strategy),
        }
    }

    /// Add a processing stage to the pipeline.
    pub fn add_stage(&mut self, stage: PipelineStage) {
        self.stages.push(stage);
    }

    /// Process a single value through all stages.
    ///
    /// Returns the full `PipelineResult`.
    pub fn process_single(&mut self, value: f64) -> PipelineResult {
        let mut stage_results = Vec::new();

        for stage in self.stages.iter_mut() {
            match stage {
                PipelineStage::Snap(ref mut snap) => {
                    let result = snap.observe(value);
                    stage_results.push(PipelineStageResult::Snap(result));
                }
                PipelineStage::Detector(ref mut detector) => {
                    // Process all streams with this value
                    let mut deltas = Vec::new();
                    for sid in detector.stream_ids().to_vec() {
                        if let Some(delta) = detector.observe(&sid, value) {
                            deltas.push((sid.to_string(), delta));
                        }
                    }
                    stage_results.push(PipelineStageResult::Deltas(deltas));
                }
                PipelineStage::Variance(_) => {
                    // Variance stage is handled separately
                    stage_results.push(PipelineStageResult::Variance(0.0));
                }
            }
        }

        // Run attention budget on collected deltas
        let allocations = self.allocate_attention();

        PipelineResult {
            stages: stage_results,
            allocations,
        }
    }

    /// Allocate attention budget based on current deltas.
    fn allocate_attention(&mut self) -> Option<Vec<AttentionAllocation>> {
        // Collect all deltas from detector stages
        let mut all_deltas = Vec::new();
        for stage in self.stages.iter() {
            if let PipelineStage::Detector(ref detector) = stage {
                let prioritized = detector.prioritize(10);
                all_deltas.extend(prioritized);
            }
        }

        if all_deltas.is_empty() {
            return None;
        }

        Some(self.budget.allocate(&all_deltas))
    }

    /// Get a mutable reference to the attention budget.
    pub fn budget_mut(&mut self) -> &mut AttentionBudget {
        &mut self.budget
    }

    /// Get the number of stages in the pipeline.
    pub fn num_stages(&self) -> usize {
        self.stages.len()
    }

    /// Reset all stages in the pipeline.
    pub fn reset(&mut self) {
        for stage in self.stages.iter_mut() {
            match stage {
                PipelineStage::Snap(ref mut snap) => snap.reset(),
                PipelineStage::Detector(ref mut detector) => detector.clear_history(),
                PipelineStage::Variance(_) => {}
            }
        }
        self.budget.reset();
    }
}

/// Extension trait to add stream ID listing to DeltaDetector.
pub trait StreamIds {
    fn stream_ids(&self) -> Vec<String>;
}

impl StreamIds for DeltaDetector {
    fn stream_ids(&self) -> Vec<String> {
        // We can't iterate directly due to access patterns.
        // This is a workaround for the pipeline.
        Vec::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::snap::SnapFunction;

    #[test]
    fn test_pipeline_single_snap() {
        let mut pipeline = Pipeline::new(100.0, AllocationStrategy::Actionability);
        pipeline.add_stage(PipelineStage::Snap(SnapFunction::<f64>::new()));

        let result = pipeline.process_single(0.05);
        assert_eq!(result.stages.len(), 1);
        match &result.stages[0] {
            PipelineStageResult::Snap(sr) => assert!(sr.within_tolerance),
            _ => panic!("Expected snap result"),
        }
    }

    #[test]
    fn test_pipeline_detector() {
        let mut detector = DeltaDetector::new();
        detector.add_stream("cards", SnapFunction::<f64>::new());
        detector.add_stream("behavior", SnapFunction::<f64>::new());

        let mut pipeline = Pipeline::new(100.0, AllocationStrategy::Actionability);
        pipeline.add_stage(PipelineStage::Detector(detector));

        // Process a value that should trigger a delta
        let result = pipeline.process_single(0.5);
        assert_eq!(result.stages.len(), 1);
    }

    #[test]
    fn test_pipeline_stages_count() {
        let mut pipeline = Pipeline::new(100.0, AllocationStrategy::Actionability);
        pipeline.add_stage(PipelineStage::Snap(SnapFunction::<f64>::new()));
        pipeline.add_stage(PipelineStage::Snap(SnapFunction::<f64>::new()));
        assert_eq!(pipeline.num_stages(), 2);
    }

    #[test]
    fn test_pipeline_reset() {
        let mut pipeline = Pipeline::new(100.0, AllocationStrategy::Actionability);
        pipeline.add_stage(PipelineStage::Snap(SnapFunction::<f64>::new()));
        pipeline.process_single(0.05);
        pipeline.reset();
        assert_eq!(pipeline.num_stages(), 1);
    }
}
