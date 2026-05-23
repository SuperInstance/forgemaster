//! Postcard serialization helpers (no_std compatible).

use crate::wire::WireMessage;
use alloc::vec::Vec;

/// Serialize a WireMessage to bytes via Postcard.
pub fn serialize_message(msg: &WireMessage) -> Result<Vec<u8>, postcard::Error> {
    postcard::to_allocvec(msg)
}

/// Deserialize a WireMessage from bytes via Postcard.
pub fn deserialize_message(bytes: &[u8]) -> Result<WireMessage, postcard::Error> {
    postcard::from_bytes(bytes)
}

// Fixed-size serialization removed due to postcard/heapless version conflict.
// Use serialize_message() with alloc::vec::Vec instead.

#[cfg(test)]
mod tests {
    use super::*;
    use crate::wire::{TierId, Handshake, WireError};
    use alloc::vec;

    #[test]
    fn roundtrip_handshake() {
        let hs = WireMessage::Handshake(Handshake {
            sender: TierId::from_pid_timestamp(42, 1000),
            capabilities: 0b101,
            protocol_version: 1,
        });
        let bytes = serialize_message(&hs).unwrap();
        let back: WireMessage = deserialize_message(&bytes).unwrap();
        assert_eq!(hs, back);
    }

    #[test]
    fn roundtrip_error() {
        let err = WireMessage::Error(WireError::BufferOverflow);
        let bytes = serialize_message(&err).unwrap();
        let back: WireMessage = deserialize_message(&bytes).unwrap();
        assert_eq!(err, back);
    }
}
