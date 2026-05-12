//! Zeitgeist Protocol — FLUX transference specification and reference implementation
//!
//! The Zeitgeist is a CRDT semilattice capturing five dimensions of agent alignment:
//! - **Precision**: Deadband funnel state
//! - **Confidence**: Certainty via bloom filter + parity
//! - **Trajectory**: Trend via Hurst exponent
//! - **Consensus**: Cycle coherence with CRDT version vector
//! - **Temporal**: Beat grid rhythm coherence

pub mod confidence;
pub mod consensus;
pub mod merge;
pub mod packet;
pub mod precision;
pub mod temporal;
pub mod trajectory;
pub mod zeitgeist;

pub use confidence::ConfidenceState;
pub use consensus::ConsensusState;
pub use packet::FluxPacket;
pub use precision::PrecisionState;
pub use temporal::TemporalState;
pub use trajectory::TrajectoryState;
pub use zeitgeist::Zeitgeist;
