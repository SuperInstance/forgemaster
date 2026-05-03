//! Beacon broadcast and discovery trait.

use serde::{Serialize, Deserialize};
use crate::wire::TierId;
use crate::discovery::Capabilities;

/// Beacon packet broadcast by peers for discovery.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Beacon {
    pub sender: TierId,
    pub capabilities: Capabilities,
    pub protocol_version: u16,
    pub timestamp: u64,
}

impl Beacon {
    pub fn new(sender: TierId, caps: Capabilities, version: u16, ts: u64) -> Self {
        Beacon { sender, capabilities: caps, protocol_version: version, timestamp: ts }
    }
}

/// Discovery trait — implement to integrate with your transport layer.
pub trait Discovery {
    type Error;
    /// Broadcast a beacon to the fleet.
    fn broadcast(&mut self, beacon: &Beacon) -> Result<(), Self::Error>;
    /// Listen for incoming beacons (blocking).
    fn listen(&mut self) -> Result<Beacon, Self::Error>;
}
