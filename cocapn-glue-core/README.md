# cocapn-glue-core

**Cross-tier wire protocol unifying all FLUX ISA packages.**

The #1 critical path crate for the Cocapn fleet — provides a unified wire protocol, fleet discovery, and PLATO sync mechanism that works across all 4 FLUX ISA tiers:

| Tier | Target | Notes |
|------|--------|-------|
| **Mini** | `thumbv6m-none-eabi` | Cortex-M0+, no heap, `heapless` only |
| **Std** | `x86_64` / `aarch64` | Full std, process-level |
| **Edge** | `aarch64` | UUID-based, networked |
| **Thor** | CUDA GPUs | GPU UUID prefix, heavy compute |

## Features

- **`#![no_std]` by default** — works on MCUs with `heapless`
- **`std`** — enables `Vec`, `Box`, LRU tile cache, env config
- **`async`** — async transport traits (implies `std`)
- **`cuda`** — CUDA capability flag
- **`plato`** — PLATO sync extensions (implies `std`)

## Wire Protocol

```rust
use cocapn_glue_core::wire::*;

let id = TierId::from_pid_timestamp(42, 1000);
let msg = WireMessage::Handshake(Handshake {
    sender: id,
    capabilities: 0b101,
    protocol_version: 1,
});

let bytes = serialize_message(&msg).unwrap();
let back: WireMessage = deserialize_message(&bytes).unwrap();
assert_eq!(msg, back);
```

## Fleet Discovery

```rust
use cocapn_glue_core::discovery::*;

let mut caps = Capabilities::none();
caps.set(Capability::NoStd);
caps.set(Capability::Cuda);

let peer = DiscoveredPeer::new(tier_id, caps, 1);
assert!(peer.has_capability(Capability::Cuda));
```

## PLATO Sync

Generation-based delta sync with monotonic IDs:

```rust
use cocapn_glue_core::plato::*;

let payload = PlatoSyncPayload::Delta {
    room_id: vec![1, 2, 3],
    from_gen: SyncGeneration(1),
    to_gen: SyncGeneration(2),
    patch: vec![0xFF],
};
```

## Merkle Provenance

```rust
use cocapn_glue_core::provenance::*;

let trace = VerificationTrace::new(tier_id, 1, vec![0xAB], 0, 1000);
let tree = MerkleTree::from_traces(&[trace]);
println!("Merkle root: {:?}", tree.root());
```

## Capability Bitmask

| Bit | Capability | Description |
|-----|-----------|-------------|
| 0 | `NO_STD` | Runs without std |
| 1 | `ASYNC` | Async transport |
| 2 | `CUDA` | GPU compute |
| 3 | `PLATO` | PLATO sync |
| 4 | `FFI` | Foreign function interface |
| 5 | `PYTHON` | Python bindings |

## Serialization

All serialization uses **Postcard** (no_std serde, compact binary). No bincode, no JSON.

## Configuration

Environment variables with `GLUE_` prefix (requires `std` feature):

| Variable | Default | Description |
|----------|---------|-------------|
| `GLUE_TIER_ID` | `[0;8]` | Hex-encoded 8-byte tier ID |
| `GLUE_PROTOCOL_VERSION` | `1` | Protocol version |
| `GLUE_MAX_MESSAGE_SIZE` | `65536` | Max wire message size |
| `GLUE_PLATO_SYNC_INTERVAL_MS` | `5000` | PLATO sync interval |
| `GLUE_BEACON_INTERVAL_MS` | `1000` | Beacon broadcast interval |

## Tests

```bash
cargo test                    # 22 tests (10 unit + 12 integration)
cargo test --features std     # Includes LRU cache tests
```

## License

MIT
