//! # fleet-clock
//!
//! Anti-fragile PTP clock synchronization with Laman topology,
//! Fraction arithmetic, and Tensor-MIDI wire format.
//!
//! ## Quick Start
//!
//! ```rust
//! use fleet_clock::{FleetClock, FleetConfig, PtpMode, Fraction};
//!
//! let config = FleetConfig::new("my-agent")
//!     .with_delta(Fraction::new(1, 16))
//!     .with_ptp_mode(PtpMode::OffsetEstimation);
//!
//! let mut clock = FleetClock::new(config);
//! clock.start();
//! let now = clock.now();
//! let status = clock.fleet_status();
//! clock.sunset();
//! ```

#![cfg_attr(not(feature = "std"), no_std)]
#![allow(dead_code)]

extern crate alloc;

pub mod fraction_clock;
pub mod laman;
pub mod ptp;
pub mod spectral;
pub mod sunset;
pub mod tensor_midi;

// Re-exports
pub use fraction_clock::Fraction;
pub use laman::LamanTopology;
pub use ptp::{PtpEstimator, PtpExchange, PtpMode};
pub use spectral::{convergence_time, spectral_analysis, SpectralResult};
pub use sunset::{AgentStatus, Inheritance, SunsetConfig, SunsetMachine};
pub use tensor_midi::{MessageType, TensorMidi};

use alloc::string::{String, ToString};
use alloc::vec::Vec;

/// Configuration for a fleet clock instance.
#[derive(Clone, Debug)]
pub struct FleetConfig {
    /// Agent identifier.
    pub agent_id: String,
    /// Clock tick delta (resolution).
    pub delta: Fraction,
    /// PTP synchronization mode.
    pub ptp_mode: PtpMode,
    /// Initial clock offset.
    pub initial_offset: Fraction,
    /// Drift rate (fractional error per tick).
    pub drift_rate: Fraction,
    /// Maximum correction per sync round.
    pub max_correction: Fraction,
    /// Enable Tensor-MIDI encoding for wire messages.
    pub tensor_midi: bool,
}

impl FleetConfig {
    /// Create config with agent ID and sensible defaults.
    pub fn new(agent_id: &str) -> Self {
        FleetConfig {
            agent_id: agent_id.to_string(),
            delta: Fraction::new(1, 16),
            ptp_mode: PtpMode::OffsetEstimation,
            initial_offset: Fraction::ZERO,
            drift_rate: Fraction::ZERO,
            max_correction: Fraction::new(1, 100),
            tensor_midi: false,
        }
    }

    /// Set tick delta.
    pub fn with_delta(mut self, delta: Fraction) -> Self {
        self.delta = delta;
        self
    }

    /// Set PTP mode.
    pub fn with_ptp_mode(mut self, mode: PtpMode) -> Self {
        self.ptp_mode = mode;
        self
    }

    /// Set initial offset.
    pub fn with_offset(mut self, offset: Fraction) -> Self {
        self.initial_offset = offset;
        self
    }

    /// Set drift rate.
    pub fn with_drift_rate(mut self, rate: Fraction) -> Self {
        self.drift_rate = rate;
        self
    }

    /// Enable Tensor-MIDI encoding.
    pub fn with_tensor_midi(mut self) -> Self {
        self.tensor_midi = true;
        self
    }
}

/// Fleet clock status.
#[derive(Clone, Debug)]
pub struct FleetStatus {
    /// Agent ID.
    pub agent_id: String,
    /// Current clock time.
    pub time: Fraction,
    /// Current offset from PTP estimation.
    pub offset: Fraction,
    /// Estimated drift rate.
    pub drift: Fraction,
    /// Number of PTP exchanges recorded.
    pub ptp_exchanges: usize,
    /// Agent operational status.
    pub status: AgentStatus,
    /// Tick count since start.
    pub ticks: u64,
}

/// The main fleet clock.
///
/// Maintains local time as an exact Fraction, synchronizes with peers
/// via PTP offset estimation over a Laman topology.
#[derive(Clone, Debug)]
pub struct FleetClock {
    config: FleetConfig,
    /// Current local time as exact Fraction.
    local_time: Fraction,
    /// Accumulated PTP correction.
    ptp_offset: Fraction,
    /// PTP estimator.
    ptp_estimator: PtpEstimator,
    /// Sunset state machine.
    sunset: SunsetMachine,
    /// Tick counter.
    tick_count: u64,
    /// Whether the clock has been started.
    running: bool,
    /// Tensor-MIDI encoder (if enabled).
    midi_encoder: Option<TensorMidi>,
}

impl FleetClock {
    /// Create a new fleet clock with the given configuration.
    pub fn new(config: FleetConfig) -> Self {
        let ptp_estimator = PtpEstimator::new(config.ptp_mode);
        let sunset = SunsetMachine::new(SunsetConfig::default());
        let midi_encoder = if config.tensor_midi {
            Some(TensorMidi::new())
        } else {
            None
        };

        FleetClock {
            local_time: config.initial_offset,
            ptp_offset: Fraction::ZERO,
            ptp_estimator,
            sunset,
            tick_count: 0,
            running: false,
            config: config.clone(),
            midi_encoder,
        }
    }

    /// Start the clock.
    pub fn start(&mut self) {
        self.running = true;
    }

    /// Stop the clock.
    pub fn stop(&mut self) {
        self.running = false;
    }

    /// Advance by one tick.
    ///
    /// Returns the new time as a Fraction.
    pub fn tick(&mut self) -> Fraction {
        if !self.running {
            return self.local_time;
        }

        // Advance by delta + drift
        let advance = self.config.delta.add(self.config.drift_rate);
        self.local_time = self.local_time.add(advance);
        self.tick_count += 1;

        // Apply PTP correction
        self.local_time = self.local_time.add(self.ptp_offset);

        // Sunset tick
        self.sunset.tick();

        self.local_time
    }

    /// Get current time.
    pub fn now(&self) -> Fraction {
        self.local_time
    }

    /// Get current time as f64 (lossy).
    pub fn now_f64(&self) -> f64 {
        self.local_time.to_f64()
    }

    /// Record a PTP exchange and update offset estimate.
    pub fn record_ptp(&mut self, exchange: PtpExchange) {
        self.ptp_estimator.record(exchange);
        let new_offset = self.ptp_estimator.estimated_offset();

        // Clamp correction to max_correction
        let correction = new_offset.sub(self.ptp_offset);
        let abs_corr = if correction < Fraction::ZERO {
            correction.mul(Fraction::new(-1, 1))
        } else {
            correction
        };

        if abs_corr <= self.config.max_correction {
            self.ptp_offset = new_offset;
        } else if correction > Fraction::ZERO {
            self.ptp_offset = self.ptp_offset.add(self.config.max_correction);
        } else {
            self.ptp_offset = self.ptp_offset.sub(self.config.max_correction);
        }
    }

    /// Initiate sunset (graceful shutdown).
    pub fn sunset(&mut self) -> bool {
        self.sunset.begin_sunset(None)
    }

    /// Initiate sunset with a designated successor.
    pub fn sunset_with_successor(&mut self, successor_id: &str) -> bool {
        self.sunset.begin_sunset(Some(successor_id.to_string()))
    }

    /// Get the fleet status.
    pub fn fleet_status(&self) -> FleetStatus {
        FleetStatus {
            agent_id: self.config.agent_id.clone(),
            time: self.local_time,
            offset: self.ptp_offset,
            drift: self.config.drift_rate,
            ptp_exchanges: self.ptp_estimator.exchange_count(),
            status: self.sunset.status,
            ticks: self.tick_count,
        }
    }

    /// Get the agent ID.
    pub fn agent_id(&self) -> &str {
        &self.config.agent_id
    }

    /// Get the current tick count.
    pub fn tick_count(&self) -> u64 {
        self.tick_count
    }

    /// Check if the clock is running.
    pub fn is_running(&self) -> bool {
        self.running
    }

    /// Check if the agent is still operational.
    pub fn is_operational(&self) -> bool {
        self.sunset.is_operational()
    }

    /// Receive an inheritance from a predecessor.
    pub fn receive_inheritance(&mut self, inheritance: Inheritance) -> bool {
        if self.sunset.receive_inheritance(inheritance) {
            // Apply inherited offset
            if let Some(ref inh) = self.sunset.pending_inheritance {
                self.ptp_offset = inh.offset;
                self.config.drift_rate = inh.drift_rate;
            }
            self.sunset.apply_inheritance();
            true
        } else {
            false
        }
    }

    /// Encode current time as Tensor-MIDI (if enabled).
    pub fn encode_time_midi(&self) -> Option<Vec<u8>> {
        self.midi_encoder.as_ref().map(|enc| {
            enc.encode_tick(
                0, // self as sender
                self.local_time,
                &[],
            )
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_basic_clock() {
        let config = FleetConfig::new("test-agent");
        let mut clock = FleetClock::new(config);
        clock.start();

        let t0 = clock.now();
        clock.tick();
        let t1 = clock.now();
        assert!(t1 > t0);
    }

    #[test]
    fn test_delta_config() {
        let config = FleetConfig::new("test")
            .with_delta(Fraction::new(1, 4));
        let mut clock = FleetClock::new(config);
        clock.start();
        clock.tick();
        assert_eq!(clock.now(), Fraction::new(1, 4));
    }

    #[test]
    fn test_sunset() {
        let config = FleetConfig::new("test");
        let mut clock = FleetClock::new(config);
        clock.start();
        assert!(clock.sunset());
        assert!(!clock.is_operational());
    }

    #[test]
    fn test_no_tick_when_stopped() {
        let config = FleetConfig::new("test");
        let mut clock = FleetClock::new(config);
        // Not started
        let t0 = clock.now();
        clock.tick();
        assert_eq!(clock.now(), t0);
    }
}
