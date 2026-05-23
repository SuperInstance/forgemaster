//! Discovered peer representation.

use serde::{Serialize, Deserialize};
use crate::wire::TierId;
use crate::discovery::{Capabilities, Capability};

/// A peer discovered via beacon broadcast.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct DiscoveredPeer {
    pub id: TierId,
    pub capabilities: Capabilities,
    pub protocol_version: u16,
}

impl DiscoveredPeer {
    pub fn new(id: TierId, caps: Capabilities, version: u16) -> Self {
        DiscoveredPeer {
            id,
            capabilities: caps,
            protocol_version: version,
        }
    }

    pub fn has_capability(&self, cap: Capability) -> bool {
        self.capabilities.has(cap)
    }
}
