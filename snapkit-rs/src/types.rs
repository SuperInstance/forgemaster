//! Shared types for snapkit modules.

use core::fmt;

/// Result of a temporal snap operation.
#[derive(Debug, Clone, Copy)]
pub struct TemporalResult {
    pub original_time: f64,
    pub snapped_time: f64,
    pub offset: f64,
    pub is_on_beat: bool,
    pub is_t_minus_0: bool,
    pub beat_index: i64,
    pub beat_phase: f64,
}

/// Summary of spectral analysis on a signal.
#[derive(Debug, Clone, Copy)]
pub struct SpectralSummary {
    /// Shannon entropy in bits.
    pub entropy_bits: f64,
    /// Hurst exponent via R/S analysis.
    pub hurst: f64,
    /// Autocorrelation at lag 1.
    pub autocorr_lag1: f64,
    /// Lag at which autocorrelation first drops below 1/e.
    pub autocorr_decay: f64,
    /// True if signal appears stationary (0.4 ≤ H ≤ 0.6, |lag1| < 0.3).
    pub is_stationary: bool,
}

/// Type of coupling between two temporal signals.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CouplingType {
    Coupled,
    AntiCoupled,
    Uncoupled,
}

impl fmt::Display for CouplingType {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            CouplingType::Coupled => write!(f, "coupled"),
            CouplingType::AntiCoupled => write!(f, "anti_coupled"),
            CouplingType::Uncoupled => write!(f, "uncoupled"),
        }
    }
}

/// A pair of rooms with their coupling information.
#[derive(Debug, Clone)]
pub struct RoomPair {
    pub room_a: usize,
    pub room_b: usize,
    pub coupling: CouplingType,
    pub correlation: f64,
    pub lag: i32,
    pub confidence: f64,
}

impl RoomPair {
    /// True if the coupling is significant (coupled or anti-coupled).
    pub fn is_significant(&self) -> bool {
        self.coupling != CouplingType::Uncoupled
    }
}

/// Result of connectome analysis.
#[derive(Debug, Clone)]
pub struct ConnectomeResult {
    pub pairs: alloc::vec::Vec<RoomPair>,
    pub num_rooms: usize,
}

impl ConnectomeResult {
    /// Return only coupled pairs.
    pub fn coupled(&self) -> alloc::vec::Vec<&RoomPair> {
        self.pairs.iter().filter(|p| p.coupling == CouplingType::Coupled).collect()
    }

    /// Return only anti-coupled pairs.
    pub fn anti_coupled(&self) -> alloc::vec::Vec<&RoomPair> {
        self.pairs.iter().filter(|p| p.coupling == CouplingType::AntiCoupled).collect()
    }

    /// Return all significant pairs.
    pub fn significant(&self) -> alloc::vec::Vec<&RoomPair> {
        self.pairs.iter().filter(|p| p.is_significant()).collect()
    }
}

extern crate alloc;
