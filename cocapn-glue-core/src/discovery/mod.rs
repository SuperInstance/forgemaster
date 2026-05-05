//! Fleet discovery — peers, capabilities, beacons.

mod peer;
mod capabilities;
mod beacon;

pub use peer::DiscoveredPeer;
pub use capabilities::{Capabilities, Capability};
pub use beacon::{Beacon, Discovery};
