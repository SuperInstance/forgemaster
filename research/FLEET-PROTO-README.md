# superinstance-fleet-proto ⚒️

**Shared PLATO client and I2I message protocol for the SuperInstance fleet.**

This crate provides the internal communication infrastructure that every fleet agent needs:

- **PLATO client** — REST-based knowledge base read/write
- **I2I messages** — Agent-to-agent typed communication with `.i2i` bottle files
- **FleetAgent trait** — Standard agent interface for capability-based dispatch
- **Well-known rooms** — Canonical PLATO room path constants

## Why a shared crate?

Without this crate, every new agent reimplements:
- The PLATO HTTP client (headers, error handling, URL construction)
- The I2I message format ("is it `[I2I:TYPE] scope: body` or `scope: [I2I] body`?")
- The bottle file format (how does the fleet parse deliverables?)

One shared crate eliminates all of that. New agents just add `superinstance-fleet-proto` as a dependency and get PLATO + I2I for free.

## Quick Start

```rust
use superinstance_fleet_proto::plato::PlatoClient;
use superinstance_fleet_proto::i2i::I2iMessage;
use superinstance_fleet_proto::rooms;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // 1. Write to PLATO
    let plato = PlatoClient::new("http://147.224.38.131:8847");
    plato.write(rooms::depgraph::SNAPSHOTS, &serde_json::json!({
        "node_count": 42,
        "edge_count": 128,
    })).await?;

    // 2. Send an I2I message
    let msg = I2iMessage::deliverable("depgraph", "42 nodes scanned, 128 edges found");
    println!("{}", msg.format());
    // → [I2I:DELIVERABLE] depgraph — 42 nodes scanned, 128 edges found

    // 3. Save as bottle file
    msg.to_file("deliverable.i2i".as_ref())?;

    Ok(())
}
```

## Modules

| Module | Description |
|---|---|
| [`plato`](src/plato.rs) | `PlatoClient` — HTTP client for PLATO knowledge base |
| [`i2i`](src/i2i.rs) | `I2iMessage` — typed, scoped agent-to-agent messages |
| [`rooms`](src/rooms.rs) | Well-known PLATO room paths (constants) |
| [`agent`](src/agent.rs) | `FleetAgent` trait + `AgentRequest`/`AgentResponse` types |
| [`errors`](src/errors.rs) | `FleetProtoError` — unified error type |

## PLATO Room Structure

The fleet uses a hierarchical room layout:

```
depgraph/
├── snapshots/        — Full graph snapshots by date
├── checks/latest     — Latest check results
├── impact/           — Per-dependency impact reports
└── fleet-overview/   — Cross-repo dependency heatmap

forgemaster/
├── session/          — Current session state
├── deliverables/     — Milestone records
└── blockers/         — Issues needing human attention

fleet/
├── ops/              — Operational status
├── progress/         — Cross-agent progress tracking
└── review/           — Review requests and approvals
```

## I2I Message Format

```
[I2I:TYPE] scope — body
```

| Type | Constant | Purpose |
|---|---|---|
| `INFO` | `MSG_INFO` | General informational broadcast |
| `DELIVERABLE` | `MSG_DELIVERABLE` | Completed deliverable notification |
| `BLOCKER` | `MSG_BLOCKER` | Blocker requiring human intervention |
| `COORDINATION` | `MSG_COORDINATION` | Cross-agent coordination |

Bottle files (`.i2i`) are git-friendly text files containing both the human-readable format and full JSON serialization.

## FleetAgent Trait

```rust
pub trait FleetAgent: Send + Sync {
    fn agent_id(&self) -> &str;
    fn channel(&self) -> &str;
    fn capabilities(&self) -> &[&str];
    async fn handle(&mut self, req: AgentRequest) -> AgentResponse;
}
```

Implement this trait to make any agent compatible with fleet coordination. Built-in support for capability-based dispatch, request validation, and automatic I2I message generation from responses.

## License

MIT — see [LICENSE](LICENSE) for details.
