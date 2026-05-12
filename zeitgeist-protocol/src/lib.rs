//! Zeitgeist Protocol — FLUX transference specification and reference implementation
//!
//! The Zeitgeist is a CRDT semilattice capturing five dimensions of agent alignment:
//! - **Precision**: Deadband funnel state
//! - **Confidence**: Certainty via bloom filter + parity
//! - **Trajectory**: Trend via Hurst exponent
//! - **Consensus**: Cycle coherence with CRDT version vector
//! - **Temporal**: Beat grid rhythm coherence

pub mod packet;
pub mod zeitgeist;
pub mod precision;
pub mod confidence;
pub mod trajectory;
pub mod consensus;
pub mod temporal;
pub mod merge;

pub use packet::FluxPacket;
pub use zeitgeist::Zeitgeist;
pub use precision::PrecisionState;
pub use confidence::ConfidenceState;
pub use trajectory::TrajectoryState;
pub use consensus::ConsensusState;
pub use temporal::TemporalState;
