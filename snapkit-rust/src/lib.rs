//! SnapKit — Tolerance-Compressed Attention Allocation Library ⚒️
//!
//! SnapKit implements the "Snaps as Attention" theory: a snap function
//! compresses information by mapping values within tolerance to the
//! nearest expected point. Only values outside tolerance ("deltas")
//! survive — they become the signals that demand attention.
//!
//! # Core Concepts
//!
//! - **SnapFunction**: The gatekeeper of attention. Values within tolerance
//!   are snapped to "expected" and ignored. Only deltas reach consciousness.
//!
//! - **DeltaDetector**: Monitors multiple streams for deltas. Each stream
//!   has its own snap function, tolerance, and topology.
//!
//! - **AttentionBudget**: Allocates finite cognitive resources to deltas
//!   proportional to their magnitude, actionability, and urgency.
//!
//! - **ScriptLibrary**: Stores learned patterns that execute automatically,
//!   freeing cognition for higher-level planning.
//!
//! - **EisensteinInt**: The Eisenstein integer lattice ℤ[ω] — the crown jewel.
//!   Provides the densest 2D packing with 6-fold symmetry and PID guarantee.
//!
//! - **LearningCycle**: Models the cycle of expertise — experience builds
//!   scripts, scripts free cognition, freed cognition handles novelty.
//!
//! - **Pipeline**: Composes multiple stages (snap, detect, allocate) into
//!   a single processing pipeline.
//!
//! - **FakeDeltaDetector**: Detects adversarial delta injection (poker,
//!   blackjack, negotiation settings).
//!
//! # Quick Start
//!
//! ```rust
//! use snapkit::{SnapFunction, SnapTopology};
//!
//! // Create a snap function with builder pattern
//! let mut snap = SnapFunction::<f64>::builder()
//!     .tolerance(0.1)
//!     .topology(SnapTopology::Hexagonal)
//!     .build();
//!
//! // Observe values — within tolerance snap, outside tolerance = delta
//! let result = snap.observe(0.05);
//! assert!(result.within_tolerance);
//!
//! let result = snap.observe(0.3);
//! assert!(result.is_delta());
//!
//! // Check calibration
//! println!("Snap rate: {:.2}%, Calibration: {:.2}",
//!     snap.snap_rate() * 100.0, snap.calibration());
//! ```
//!
//! # The Eisenstein Lattice (Crown Jewel)
//!
//! ```rust
//! use snapkit::{EisensteinInt, eisenstein_snap, eisenstein_distance};
//!
//! // Snap a point to the nearest Eisenstein integer
//! let nearest = eisenstein_snap((1.2, 0.7));
//! assert_eq!(nearest, EisensteinInt::new(1, 1));
//!
//! // Compute the norm: a² - ab + b² (multiplicative)
//! let e = EisensteinInt::new(3, 2);
//! assert_eq!(e.norm(), 7);  // 9 - 6 + 4 = 7
//! ```

pub mod adversarial;
pub mod attention;
pub mod delta;
pub mod eisenstein;
pub mod learning;
pub mod pipeline;
pub mod scripts;
pub mod snap;
pub mod streaming;
pub mod topology;

// Re-export the most commonly used types at the crate level.
pub use adversarial::{CamouflageGenerator, DeltaAuthenticity, FakeDeltaDetector, FakeDeltaReport};
pub use attention::{AllocationStrategy, AttentionAllocation, AttentionBudget};
pub use delta::{Delta, DeltaDetector, DeltaSeverity, DeltaStream};
pub use eisenstein::{
    eisenstein_distance, eisenstein_neighbors, eisenstein_snap, eisenstein_snap_batch, EisensteinInt,
};
pub use learning::{LearningCycle, LearningPhase, LearningState};
pub use pipeline::{Pipeline, PipelineResult, PipelineStage, PipelineStageResult};
pub use scripts::{Script, ScriptLibrary, ScriptMatch, ScriptStatus};
pub use snap::{SnapFunction, SnapFunctionBuilder, SnapResult};
pub use streaming::{process_stream, RingBuffer, StreamProcessor};
pub use topology::{recommend_topology, ADEData, ADE_SYSTEMS, SnapTopology};
