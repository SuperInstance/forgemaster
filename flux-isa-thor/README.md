# flux-isa-thor ⚒️

**Heavyweight FLUX ISA runtime for GPU-class edge** — Jetson Thor / AGX Orin with CUDA, batch CSP solving, fleet coordination.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    flux-isa-thor                         │
├─────────────────────────────────────────────────────────┤
│  Axum HTTP Server                                        │
│  /compile /verify /execute /batch-solve /batch-sonar    │
│  /status /metrics /stream (WS)                          │
├─────────────────────────────────────────────────────────┤
│  5-Stage Pipeline: INGEST → VALIDATE → COMPILE →        │
│                    EXECUTE → COMMIT                     │
├──────────────┬──────────────┬───────────────────────────┤
│  ThorVM      │  CUDA Layer  │  Fleet Coordinator        │
│  43 opcodes  │  Batch CSP   │  I2I Protocol             │
│  Parallel    │  Batch Sonar │  Task Queue               │
│  Branch/Reduce│ GPU Dispatch │ Heartbeat                 │
├──────────────┴──────────────┴───────────────────────────┤
│  PLATO Client (HTTP + Cache + Pathfinder)               │
└─────────────────────────────────────────────────────────┘
```

## Opcodes

### Base ISA (35 opcodes)

| Range | Category | Opcodes |
|-------|----------|---------|
| 0x00–0x06 | Stack | NOP, PUSH, POP, DUP, SWAP, LOAD, STORE |
| 0x10–0x15 | Arithmetic | ADD, SUB, MUL, DIV, MOD, NEG |
| 0x20–0x22 | Logic | AND, OR, NOT |
| 0x30–0x35 | Comparison | EQ, NE, LT, LE, GT, GE |
| 0x40–0x45 | Control Flow | JMP, JZ, JNZ, CALL, RET, HALT |
| 0x50–0x54 | CSP | ASSERT, CONSTRAIN, PROPAGATE, SOLVE, VERIFY |
| 0x60–0x61 | I/O | PRINT, DEBUG |

### Thor Extensions (8 opcodes)

| Code | Opcode | Description |
|------|--------|-------------|
| 0x80 | PARALLEL_BRANCH | Fan-out to N parallel execution paths |
| 0x81 | REDUCE | Merge parallel results with reduction op |
| 0x82 | GPU_COMPILE | Compile current bytecode to CUDA kernel |
| 0x83 | BATCH_SOLVE | Solve N CSP instances on GPU |
| 0x84 | SONAR_BATCH | Batch sonar physics on GPU |
| 0x85 | TILE_COMMIT | Commit verified result to PLATO |
| 0x86 | PATHFIND | Traverse PLATO knowledge graph |
| 0x87 | EXTENDED_END | End of extended opcode sequence |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/compile` | Compile CSP spec to FLUX bytecodes |
| POST | `/verify` | Verify a claim (kill-shot endpoint) |
| POST | `/execute` | Execute FLUX bytecode |
| POST | `/batch-solve` | Batch CSP solve on GPU |
| POST | `/batch-sonar` | Batch sonar physics on GPU |
| GET | `/status` | Node status with GPU metrics |
| GET | `/metrics` | Prometheus metrics |
| WS | `/stream` | Live execution trace |

## Quick Start

```bash
# Build
cargo build --release

# Run with defaults
./target/release/flux-isa-thor

# Run with config file
./target/release/flux-isa-thor thor.toml

# Environment overrides
THOR_NODE_ID=thor-1 \
THOR_LISTEN_ADDR=0.0.0.0:8080 \
THOR_PLATO_URL=http://plato:3000 \
THOR_GPU_AVAILABLE=true \
THOR_GPU_MEMORY_MB=262144 \
./target/release/flux-isa-thor
```

## Configuration

```toml
node_id = "thor-1"
listen_addr = "0.0.0.0:8080"
plato_url = "http://plato:3000"
gpu_available = true
gpu_memory_mb = 262144
max_concurrent_kernels = 4
fleet_peers = ["http://thor-2:8080", "http://thor-3:8080"]
pipeline_channel_capacity = 1024
pipeline_batch_size = 64
pipeline_max_concurrent_execute = 8
checkpoint_interval_secs = 60
heartbeat_interval_secs = 30
plato_max_concurrent = 16
cache_max_entries = 100000
vm_max_stack = 65536
```

## CUDA Acceleration

The `GpuDispatcher` automatically routes work to GPU or CPU:

- **Small batches** (<256 items): CPU via Rayon parallelism
- **Large batches** (≥256 items): GPU via FFI to `libflux_cuda.so`

Production deployment requires:
1. NVIDIA CUDA toolkit 12.x
2. `libflux_cuda.so` in `LD_LIBRARY_PATH`
3. Sufficient GPU memory (256GB+ for Jetson Thor)

### Batch CSP Solver

Solves constraint satisfaction problems using backtracking with arc-consistency:
- CPU: Rayon parallel across all cores
- GPU: Batch 1M+ instances in a single kernel launch

### Batch Sonar Physics

Computes sound speed (Mackenzie equation) and absorption (Francois-Garrison):
- Validated against known oceanographic data
- Automatic CPU/GPU dispatch

## Fleet Coordination

### I2I Protocol

Instance-to-Instance messages for fleet coordination:

| Type | Purpose |
|------|---------|
| TASK | Task assignment to fleet nodes |
| STATUS | Heartbeat / status update |
| CHECKPOINT | Intermediate progress report |
| BLOCKER | Node needs help or input |
| DELIVERABLE | Completed work product |

### FleetCoordinator

- Priority-based task queue with deadline awareness
- Automatic task assignment to available nodes
- 30-second heartbeat broadcasts
- Result aggregation from multiple nodes

## PLATO Integration

- Async HTTP client with connection pooling
- Local in-memory tile cache (100K entries, LRU eviction)
- Background sync daemon (configurable interval)
- Pathfinder: BFS traversal of knowledge graph with confidence weighting
- Batch tile submission (1000+ tiles per API call)
- Gate-aware retry with softened language on rejection

## Pipeline

5-stage streaming pipeline with backpressure:

```
INGEST → VALIDATE → COMPILE → EXECUTE → COMMIT
  (ch)     (ch)       (ch)      (ch)     (counter)
```

- Bounded channels prevent memory blowout
- EXECUTE stage has semaphore-limited concurrency
- Metrics per stage: throughput, errors, latency
- Checkpoint for crash recovery

## Jetson Thor Deployment

```bash
# Cross-compile for aarch64
rustup target add aarch64-unknown-linux-gnu
cargo build --release --target aarch64-unknown-linux-gnu

# Deploy
scp target/aarch64-unknown-linux-gnu/release/flux-isa-thor thor:/usr/local/bin/
scp thor.toml thor:/etc/flux-isa-thor/

# systemd service
cat > /etc/systemd/system/flux-isa-thor.service << 'EOF'
[Unit]
Description=FLUX ISA Thor Runtime
After=network.target

[Service]
ExecStart=/usr/local/bin/flux-isa-thor /etc/flux-isa-thor/thor.toml
Restart=always
Environment=THOR_GPU_AVAILABLE=true
Environment=THOR_GPU_MEMORY_MB=262144

[Install]
WantedBy=multi-user.target
EOF
```

## Performance Tuning

| Parameter | Default | Jetson Thor | Data Center GPU |
|-----------|---------|-------------|-----------------|
| `pipeline_max_concurrent_execute` | 8 | 16 | 64 |
| `max_concurrent_kernels` | 4 | 8 | 16 |
| `pipeline_batch_size` | 64 | 256 | 1024 |
| `plato_max_concurrent` | 16 | 32 | 64 |
| `cache_max_entries` | 100K | 1M | 10M |

## Testing

```bash
# Run all tests
cargo test

# Run benchmarks
cargo bench

# Run with logging
RUST_LOG=flux_isa_thor=debug cargo test -- --nocapture
```

## License

Apache-2.0

## Author

Casey Digennaro — [SuperInstance](https://github.com/SuperInstance)
