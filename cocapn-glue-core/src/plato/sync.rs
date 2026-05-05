//! PLATO sync payload with generation-based delta sync.

use serde::{Serialize, Deserialize};
use alloc::vec::Vec;

/// Monotonically increasing generation ID for sync ordering.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub struct SyncGeneration(pub u64);

impl SyncGeneration {
    pub const ZERO: SyncGeneration = SyncGeneration(0);

    pub fn next(&self) -> SyncGeneration {
        SyncGeneration(self.0 + 1)
    }

    pub fn is_newer_than(&self, other: SyncGeneration) -> bool {
        self.0 > other.0
    }
}

/// PLATO sync payload variants.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum PlatoSyncPayload {
    /// Full snapshot of a PLATO room.
    Snapshot {
        room_id: Vec<u8>,
        generation: SyncGeneration,
        data: Vec<u8>,
    },
    /// Incremental delta from previous generation.
    Delta {
        room_id: Vec<u8>,
        from_gen: SyncGeneration,
        to_gen: SyncGeneration,
        patch: Vec<u8>,
    },
    /// Invalidation notice — stale data.
    Invalidate {
        room_id: Vec<u8>,
        generation: SyncGeneration,
    },
    /// Sync acknowledgement.
    SyncAck {
        room_id: Vec<u8>,
        generation: SyncGeneration,
    },
}

impl PlatoSyncPayload {
    /// Returns the room_id bytes for this payload.
    pub fn room_id(&self) -> &[u8] {
        match self {
            PlatoSyncPayload::Snapshot { room_id, .. } => room_id,
            PlatoSyncPayload::Delta { room_id, .. } => room_id,
            PlatoSyncPayload::Invalidate { room_id, .. } => room_id,
            PlatoSyncPayload::SyncAck { room_id, .. } => room_id,
        }
    }

    /// Returns the latest generation referenced by this payload.
    pub fn generation(&self) -> SyncGeneration {
        match self {
            PlatoSyncPayload::Snapshot { generation, .. } => *generation,
            PlatoSyncPayload::Delta { to_gen, .. } => *to_gen,
            PlatoSyncPayload::Invalidate { generation, .. } => *generation,
            PlatoSyncPayload::SyncAck { generation, .. } => *generation,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use alloc::vec;

    #[test]
    fn generation_ordering() {
        let g0 = SyncGeneration::ZERO;
        let g1 = g0.next();
        let g2 = g1.next();
        assert!(g2.is_newer_than(g1));
        assert!(g1.is_newer_than(g0));
        assert!(!g0.is_newer_than(g1));
    }

    #[test]
    fn payload_accessors() {
        let p = PlatoSyncPayload::Snapshot {
            room_id: vec![1, 2, 3],
            generation: SyncGeneration(5),
            data: vec![42],
        };
        assert_eq!(p.room_id(), &[1, 2, 3]);
        assert_eq!(p.generation(), SyncGeneration(5));
    }
}
