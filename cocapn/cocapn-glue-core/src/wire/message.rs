//! WireMessage — the core envelope for all cross-tier communication.

use serde::{Serialize, Deserialize};
use crate::wire::TierId;

/// Buffer trait abstracting heap vs stack storage.
pub trait Buffer: AsRef<[u8]> + AsMut<[u8]> + Default + Clone {}
impl<const N: usize> Buffer for heapless::Vec<u8, N> {}
impl Buffer for alloc::vec::Vec<u8> {}

/// Handshake payload exchanged on connection establishment.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Handshake {
    pub sender: TierId,
    pub capabilities: u32,
    pub protocol_version: u16,
}

/// Data chunk with optional chunk metadata.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct DataChunk {
    pub sender: TierId,
    pub chunk_id: u64,
    pub total_chunks: u32,
    pub sequence: u32,
    pub payload: alloc::vec::Vec<u8>,
}

/// Acknowledgement.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Ack {
    pub receiver: TierId,
    pub chunk_id: u64,
    pub sequence: u32,
}

/// Wire-level error.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum WireError {
    UnknownTier,
    MalformedMessage,
    BufferOverflow,
    UnsupportedVersion(u16),
    TransportError(u32),
}

/// The unified wire message envelope.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum WireMessage {
    Handshake(Handshake),
    DataChunk(DataChunk),
    Ack(Ack),
    Error(WireError),
}
