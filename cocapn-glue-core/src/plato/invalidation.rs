//! Invalidation protocol for PLATO sync.

use serde::{Serialize, Deserialize};
use alloc::vec::Vec;
use crate::plato::SyncGeneration;

/// An invalidation notice sent when cached data is stale.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct InvalidationNotice {
    pub room_id: Vec<u8>,
    pub stale_generation: SyncGeneration,
    pub reason: InvalidationReason,
}

/// Why data was invalidated.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum InvalidationReason {
    /// Data was overwritten by a newer write.
    Overwritten,
    /// Writer disconnected, data may be stale.
    WriterDisconnected,
    /// Explicit invalidation by fleet coordinator.
    Coordinated,
    /// TTL expired.
    Expired,
}
