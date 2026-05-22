//! Sunset and inheritance protocol for fleet clock agents.
//!
//! Sunset: graceful departure from the clock network.
//! Inheritance: transfer of clock state to a designated successor.

use crate::fraction_clock::Fraction;

extern crate alloc;
use alloc::string::String;
use alloc::vec::Vec;

/// Agent status in the fleet clock network.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum AgentStatus {
    /// Agent is active and participating in sync.
    Active,
    /// Agent is shutting down gracefully (sunset in progress).
    Sunsetting,
    /// Agent has left the network.
    Sunset,
    /// Agent inherited state from a predecessor.
    Inherited,
}

/// Sunset configuration.
#[derive(Clone, Debug)]
pub struct SunsetConfig {
    /// Grace period in ticks before final departure.
    pub grace_period_ticks: u64,
    /// Whether to broadcast final state before leaving.
    pub broadcast_final_state: bool,
}

impl Default for SunsetConfig {
    fn default() -> Self {
        SunsetConfig {
            grace_period_ticks: 10,
            broadcast_final_state: true,
        }
    }
}

/// Inheritance payload: state transferred from predecessor to successor.
#[derive(Clone, Debug)]
pub struct Inheritance {
    /// Predecessor agent ID.
    pub predecessor_id: String,
    /// Clock offset at time of transfer.
    pub offset: Fraction,
    /// Clock drift rate estimate.
    pub drift_rate: Fraction,
    /// Last known topology version.
    pub topology_version: u64,
    /// Timestamp of inheritance (in predecessor's ticks).
    pub timestamp: Fraction,
}

impl Inheritance {
    /// Create a new inheritance payload.
    pub fn new(
        predecessor_id: String,
        offset: Fraction,
        drift_rate: Fraction,
        topology_version: u64,
        timestamp: Fraction,
    ) -> Self {
        Inheritance {
            predecessor_id,
            offset,
            drift_rate,
            topology_version,
            timestamp,
        }
    }

    /// Validate that this inheritance is from a credible predecessor.
    pub fn is_valid(&self) -> bool {
        !self.predecessor_id.is_empty() && self.timestamp >= Fraction::ZERO
    }
}

/// Sunset state machine for an agent.
#[derive(Clone, Debug)]
pub struct SunsetMachine {
    /// Current status.
    pub status: AgentStatus,
    /// Configuration.
    pub config: SunsetConfig,
    /// Ticks remaining in grace period.
    pub ticks_remaining: u64,
    /// Designated successor (if any).
    pub successor_id: Option<String>,
    /// Pending inheritance (received from predecessor).
    pub pending_inheritance: Option<Inheritance>,
}

impl SunsetMachine {
    /// Create a new sunset machine in Active state.
    pub fn new(config: SunsetConfig) -> Self {
        SunsetMachine {
            status: AgentStatus::Active,
            config,
            ticks_remaining: 0,
            successor_id: None,
            pending_inheritance: None,
        }
    }

    /// Initiate sunset procedure.
    ///
    /// Returns true if sunset was initiated, false if already sunsetting/sunset.
    pub fn begin_sunset(&mut self, successor_id: Option<String>) -> bool {
        match self.status {
            AgentStatus::Active | AgentStatus::Inherited => {
                self.status = AgentStatus::Sunsetting;
                self.ticks_remaining = self.config.grace_period_ticks;
                self.successor_id = successor_id;
                true
            }
            _ => false,
        }
    }

    /// Tick the sunset timer. Returns true when sunset is complete.
    pub fn tick(&mut self) -> bool {
        if self.status != AgentStatus::Sunsetting {
            return false;
        }
        if self.ticks_remaining > 0 {
            self.ticks_remaining -= 1;
        }
        if self.ticks_remaining == 0 {
            self.status = AgentStatus::Sunset;
            return true;
        }
        false
    }

    /// Receive an inheritance from a predecessor.
    pub fn receive_inheritance(&mut self, inheritance: Inheritance) -> bool {
        if !inheritance.is_valid() {
            return false;
        }
        self.pending_inheritance = Some(inheritance);
        self.status = AgentStatus::Inherited;
        true
    }

    /// Apply the pending inheritance, consuming it.
    pub fn apply_inheritance(&mut self) -> Option<&Inheritance> {
        if self.pending_inheritance.is_some() {
            self.status = AgentStatus::Active;
            self.pending_inheritance.as_ref()
        } else {
            None
        }
    }

    /// Check if the agent is still operational (Active or Inherited).
    pub fn is_operational(&self) -> bool {
        matches!(self.status, AgentStatus::Active | AgentStatus::Inherited)
    }

    /// Generate the inheritance payload to pass to a successor.
    pub fn create_inheritance(
        &self,
        agent_id: &str,
        offset: Fraction,
        drift_rate: Fraction,
        topo_version: u64,
        timestamp: Fraction,
    ) -> Option<Inheritance> {
        if self.status != AgentStatus::Sunsetting {
            return None;
        }
        Some(Inheritance::new(
            agent_id.to_string(),
            offset,
            drift_rate,
            topo_version,
            timestamp,
        ))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sunset_flow() {
        let config = SunsetConfig {
            grace_period_ticks: 3,
            broadcast_final_state: true,
        };
        let mut sm = SunsetMachine::new(config);
        assert!(sm.is_operational());

        sm.begin_sunset(Some("successor".to_string()));
        assert_eq!(sm.status, AgentStatus::Sunsetting);
        assert!(sm.is_operational() == false);

        assert!(!sm.tick()); // 2 remaining
        assert!(!sm.tick()); // 1 remaining
        assert!(sm.tick());  // complete
        assert_eq!(sm.status, AgentStatus::Sunset);
    }

    #[test]
    fn test_inheritance() {
        let config = SunsetConfig::default();
        let mut sm = SunsetMachine::new(config);

        let inh = Inheritance::new(
            "predecessor".to_string(),
            Fraction::new(5, 1),
            Fraction::new(1, 100),
            1,
            Fraction::new(1000, 1),
        );

        assert!(sm.receive_inheritance(inh));
        assert_eq!(sm.status, AgentStatus::Inherited);
        assert!(sm.apply_inheritance().is_some());
        assert_eq!(sm.status, AgentStatus::Active);
    }

    #[test]
    fn test_invalid_inheritance() {
        let config = SunsetConfig::default();
        let mut sm = SunsetMachine::new(config);

        let bad = Inheritance::new(
            "".to_string(), // empty predecessor
            Fraction::ZERO,
            Fraction::ZERO,
            0,
            Fraction::ZERO,
        );
        assert!(!sm.receive_inheritance(bad));
    }
}
