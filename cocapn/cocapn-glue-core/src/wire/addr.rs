//! TierId — 8-byte fixed identifier for FLUX ISA tiers.
//!
//! - Mini: truncated MAC
//! - Std: PID + timestamp
//! - Edge: UUID prefix
//! - Thor: GPU UUID prefix

use serde::{Serialize, Deserialize};

/// 8-byte tier identifier. Fixed size, no heap.
#[derive(Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct TierId(pub [u8; 8]);

impl TierId {
    pub const BROADCAST: TierId = TierId([0xFF; 8]);
    pub const ZERO: TierId = TierId([0x00; 8]);

    pub fn from_bytes(b: &[u8; 8]) -> Self {
        TierId(*b)
    }

    pub fn from_mac(mac: &[u8; 6]) -> Self {
        let mut id = [0u8; 8];
        id[..6].copy_from_slice(mac);
        id[6] = mac[0] ^ mac[2];
        id[7] = mac[1] ^ mac[3] ^ mac[5];
        TierId(id)
    }

    pub fn from_pid_timestamp(pid: u32, ts: u32) -> Self {
        let mut id = [0u8; 8];
        id[..4].copy_from_slice(&pid.to_le_bytes());
        id[4..].copy_from_slice(&ts.to_le_bytes());
        TierId(id)
    }

    pub fn from_uuid_prefix(uuid: &[u8; 16]) -> Self {
        let mut id = [0u8; 8];
        id.copy_from_slice(&uuid[..8]);
        TierId(id)
    }

    pub fn as_bytes(&self) -> &[u8; 8] {
        &self.0
    }
}

impl core::fmt::Debug for TierId {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        write!(f, "TierId({:02x}{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}{:02x})",
            self.0[0], self.0[1], self.0[2], self.0[3],
            self.0[4], self.0[5], self.0[6], self.0[7])
    }
}
