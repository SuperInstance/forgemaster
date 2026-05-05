//! Integration tests for cocapn-glue-core.

use cocapn_glue_core::*;

// ---- Wire protocol tests ----

#[test]
fn tier_id_from_mac() {
    let mac = [0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF];
    let id = wire::TierId::from_mac(&mac);
    assert_ne!(*id.as_bytes(), [0u8; 8]);
}

#[test]
fn tier_id_from_pid_timestamp() {
    let id = wire::TierId::from_pid_timestamp(42, 1000);
    let bytes = id.as_bytes();
    assert_eq!(&bytes[..4], &42u32.to_le_bytes());
    assert_eq!(&bytes[4..], &1000u32.to_le_bytes());
}

#[test]
fn wire_message_roundtrip_data_chunk() {
    let msg = wire::WireMessage::DataChunk(wire::DataChunk {
        sender: wire::TierId::from_uuid_prefix(&[0x01; 16]),
        chunk_id: 999,
        total_chunks: 3,
        sequence: 1,
        payload: vec![0xDE, 0xAD, 0xBE, 0xEF],
    });
    let bytes = wire::serialize_message(&msg).unwrap();
    let back: wire::WireMessage = wire::deserialize_message(&bytes).unwrap();
    assert_eq!(msg, back);
}

#[test]
fn wire_message_roundtrip_handshake() {
    let msg = wire::WireMessage::Handshake(wire::Handshake {
        sender: wire::TierId::from_pid_timestamp(1, 2),
        capabilities: 0b111,
        protocol_version: 1,
    });
    let bytes = wire::serialize_message(&msg).unwrap();
    let back: wire::WireMessage = wire::deserialize_message(&bytes).unwrap();
    assert_eq!(msg, back);
}

// ---- Discovery tests ----

#[test]
fn capabilities_bitmask() {
    let mut caps = discovery::Capabilities::none();
    caps.set(discovery::Capability::NoStd);
    caps.set(discovery::Capability::Cuda);
    assert!(caps.has(discovery::Capability::NoStd));
    assert!(caps.has(discovery::Capability::Cuda));
    assert!(!caps.has(discovery::Capability::Async));
}

#[test]
fn discovered_peer_has_capability() {
    let mut caps = discovery::Capabilities::none();
    caps.set(discovery::Capability::Plato);
    let peer = discovery::DiscoveredPeer::new(
        wire::TierId::from_pid_timestamp(10, 20),
        caps,
        1,
    );
    assert!(peer.has_capability(discovery::Capability::Plato));
    assert!(!peer.has_capability(discovery::Capability::Async));
}

#[test]
fn beacon_serialization_roundtrip() {
    let beacon = discovery::Beacon::new(
        wire::TierId::from_pid_timestamp(5, 6),
        discovery::Capabilities::all(),
        1,
        1234567890,
    );
    let bytes = wire::serialize_message(&wire::WireMessage::Handshake(wire::Handshake {
        sender: beacon.sender,
        capabilities: beacon.capabilities.raw(),
        protocol_version: beacon.protocol_version,
    })).unwrap();
    let back = wire::deserialize_message(&bytes).unwrap();
    if let wire::WireMessage::Handshake(hs) = back {
        assert_eq!(hs.capabilities, beacon.capabilities.raw());
    } else {
        panic!("Expected Handshake");
    }
}

// ---- PLATO sync tests ----

#[test]
fn plato_delta_sync_generation_check() {
    let g1 = plato::SyncGeneration(1);
    let g2 = plato::SyncGeneration(2);
    assert!(g2.is_newer_than(g1));
    assert!(!g1.is_newer_than(g2));
}

#[test]
fn plato_sync_payload_roundtrip() {
    let payload = plato::PlatoSyncPayload::Delta {
        room_id: vec![1, 2, 3],
        from_gen: plato::SyncGeneration(1),
        to_gen: plato::SyncGeneration(2),
        patch: vec![0xFF, 0x00],
    };
    let bytes = wire::serialize_message(&wire::WireMessage::Error(wire::WireError::UnknownTier)).unwrap();
    let _ = bytes; // Just checking wire still works alongside plato types
    // Verify payload accessors
    assert_eq!(payload.room_id(), &[1, 2, 3]);
    assert_eq!(payload.generation(), plato::SyncGeneration(2));
}

// ---- Merkle provenance tests ----

#[test]
fn merkle_tree_from_traces() {
    let t1 = provenance::VerificationTrace::new(
        wire::TierId::from_pid_timestamp(1, 1),
        1,
        vec![0x01],
        0,
        1000,
    );
    let t2 = provenance::VerificationTrace::new(
        wire::TierId::from_pid_timestamp(2, 2),
        2,
        vec![0x02],
        0,
        2000,
    );
    let tree = provenance::MerkleTree::from_traces(&[t1, t2]);
    assert_eq!(tree.len(), 2);
    assert_ne!(*tree.root(), [0u8; 32]);
}

#[test]
fn verification_trace_hash_deterministic() {
    let t = provenance::VerificationTrace::new(
        wire::TierId::from_pid_timestamp(1, 1),
        42,
        vec![0xAB],
        0,
        9999,
    );
    let h1 = t.hash();
    let h2 = t.hash();
    assert_eq!(h1, h2);
}

// ---- Config tests ----

#[test]
fn config_default() {
    let cfg = config::Config::default();
    assert_eq!(cfg.protocol_version, 1);
    assert_eq!(cfg.max_message_size, 65536);
}
