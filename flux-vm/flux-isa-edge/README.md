# flux-isa-edge ⚒️

**Async FLUX ISA runtime for fleet edge nodes** — Jetson Xavier / AGX Orin with networking, PLATO sync, and sensor pipelines.

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  flux-isa-edge                   │
│                                                  │
│  ┌──────────┐  ┌──────────────┐  ┌───────────┐ │
│  │  Sensors  │→│  FLUX Pipeline │→│   PLATO    │ │
│  │ (sonar…)  │  │ (validate +   │  │  Client    │ │
│  └──────────┘  │  constraint)   │  │  + Cache   │ │
│                └──────────────┘  └─────┬─────┘ │
│                                         │       │
│  ┌──────────────────────────────────────┴───┐   │
│  │         Axum HTTP Server                 │   │
│  │  /execute  /validate  /status  /stream   │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │         Async VM (tokio)                  │   │
│  │  35 opcodes · cooperative yield · limits  │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

## FLUX ISA — 35 Opcodes

| Group | Opcodes |
|-------|---------|
| Stack | `PUSH`, `POP`, `DUP`, `SWAP`, `LOAD`, `STORE` |
| Arithmetic | `ADD`, `SUB`, `MUL`, `DIV`, `MOD`, `NEG` |
| Comparison | `EQ`, `NE`, `LT`, `LE`, `GT`, `GE` |
| Logic | `AND`, `OR`, `NOT` |
| Constraint | `VALIDATE`, `ASSERT`, `TOLERANCE`, `CLAMP` |
| Control | `JUMP`, `JUMP_IF`, `CALL`, `RET`, `HALT` |
| I/O | `INPUT`, `OUTPUT` |
| Extended | `SYNC`, `NOP` |

## Quick Start

```bash
# Build
cargo build --release

# Run with defaults (port 9090, PLATO at localhost:8080)
cargo run --release

# Configure via environment
FLUX_NODE_ID=edge-jetson-01 \
FLUX_PLATO_URL=http://plato.fleet:8080 \
FLUX_PORT=9090 \
cargo run --release
```

## API

### POST /execute
Execute FLUX bytecode on the async VM.

```json
{
  "bytecode": {
    "id": "uuid",
    "instructions": [
      {"opcode": "Push", "operand": 10.0},
      {"opcode": "Push", "operand": 20.0},
      {"opcode": "Add"},
      {"opcode": "Halt"}
    ]
  },
  "inputs": [],
  "limits": {"max_steps": 1000000, "max_time_secs": 30.0, "max_stack_depth": 1024}
}
```

### POST /validate
Validate a batch of values against [min, max] constraints.

### GET /status
Node status: uptime, tiles processed, constraint violations.

### GET /health
Health check endpoint.

### WebSocket /stream
Live sensor data stream.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `FLUX_NODE_ID` | `edge-{hostname}` | Node identifier |
| `FLUX_PLATO_URL` | `http://localhost:8080` | PLATO server URL |
| `FLUX_BIND_ADDR` | `0.0.0.0` | HTTP bind address |
| `FLUX_PORT` | `9090` | HTTP port |
| `FLUX_SYNC_INTERVAL` | `300` | PLATO sync interval (seconds) |
| `FLUX_MAX_STEPS` | `1000000` | VM execution step limit |
| `FLUX_MAX_TIME_SECS` | `30.0` | VM timeout per execution |
| `FLUX_MAX_STACK_DEPTH` | `1024` | Maximum stack depth |
| `FLUX_BATCH_SIZE` | `64` | Sensor readings per batch |
| `FLUX_VIOLATION_POLICY` | `log_and_continue` | `log_and_continue` or `halt` |

## Sensor Pipelines

### Built-in: Sonar
- **Mackenzie 1981** sound speed equation
- **Francois-Garrison 1982** absorption model
- Physical bounds validation compiled to FLUX bytecode at init
- Configurable depth, temperature, salinity, frequency

### Custom Sensors
Implement the `SensorSource` trait:

```rust
use flux_isa_edge::sensor::SensorSource;

struct MySensor;

impl SensorSource for MySensor {
    fn read_sensor_data(&mut self) -> Vec<f64> {
        // Read from hardware...
        vec![42.0]
    }
    fn sensor_name(&self) -> &str { "my-sensor" }
}
```

## Docker (Jetson)

```dockerfile
FROM dustynv/rust:latest
WORKDIR /app
COPY . .
RUN cargo build --release
EXPOSE 9090
CMD ["./target/release/flux-isa-edge"]
```

For Jetson with GPU acceleration, use the NVIDIA container runtime:

```bash
docker run --runtime=nvidia --gpus all -p 9090:9090 flux-isa-edge
```

## Fleet Integration

This edge node connects to the Cocapn fleet via PLATO:

1. **Startup**: Sync relevant rooms from PLATO to local cache
2. **Runtime**: Process sensor data through FLUX constraint pipelines
3. **Offline**: Operate from cache, queue tiles for later sync
4. **Reporting**: HTTP status endpoint for fleet dashboard

## Testing

```bash
cargo test    # 25 tests — opcodes, VM, sensors, pipeline, cache
cargo check   # Zero warnings with -D warnings
```

## License

Apache-2.0 — [SuperInstance](https://github.com/SuperInstance/forgemaster)
