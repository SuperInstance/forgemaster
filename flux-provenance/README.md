# flux-provenance

Merkle provenance service for the Cocapn fleet. Every verification trace submitted generates a SHA-256 leaf hash, and leaves are batched into Merkle trees that serve as immutable trust anchors.

## Architecture

- **Merkle trees** batch leaves (default: 1000 per tree)
- **SHA-256** hashing throughout
- **Sled** embedded database for persistence
- **Axum** HTTP server with JSON API
- Trees are **append-only** — sealed trees are immutable

## API

| Endpoint | Method | Description |
|---|---|---|
| `/submit` | POST | Submit a verification trace |
| `/verify/:leaf_hash` | GET | Verify a leaf is in a tree |
| `/root` | GET | Current Merkle root |
| `/tree/:index` | GET | Get sealed tree by index |
| `/stats` | GET | Total leaves, trees, storage size |

### Submit

```json
POST /submit
{ "trace": ["step1", "step2"], "domain": "sonar", "confidence": 0.97, "source": "flux-verify-api" }

Response:
{ "leaf_hash": "sha256:abc...", "merkle_root": "sha256:def...", "tree_size": 47, "proof_path": [...] }
```

### Verify

```json
GET /verify/sha256:abc...

Response:
{ "valid": true, "leaf_hash": "sha256:abc...", "merkle_root": "sha256:def...", "proof_path": [...] }
```

## Configuration

| Env Var | Default | Description |
|---|---|---|
| `PROVENANCE_DB_PATH` | `provenance_db` | Sled database path |
| `PROVENANCE_BATCH_SIZE` | `1000` | Leaves per tree |
| `PROVENANCE_LISTEN_ADDR` | `0.0.0.0:3010` | Listen address |

## Running

```bash
cargo run
```

## Testing

```bash
cargo test
```

## Version

0.1.0
