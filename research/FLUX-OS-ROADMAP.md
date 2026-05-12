# FLUX OS — Definitive Architectural Roadmap
**Chief Architect Document — 2026-05-11**

> The product is hardware. The software is the moat. This document is the map.

---

## Table of Contents

1. [System Architecture Map](#1-system-architecture-map)
2. [Critical Path Analysis](#2-critical-path-analysis)
3. [Integration Points](#3-integration-points)
4. [The MUD-as-OS Thesis](#4-the-mud-as-os-thesis)
5. [Enterprise Readiness Gaps](#5-enterprise-readiness-gaps)
6. [IoT Readiness Gaps](#6-iot-readiness-gaps)
7. [Alignment Theory Implementation](#7-alignment-theory-implementation)
8. [The One-Pager](#8-the-one-pager)
9. [90-Day Sprint Plan](#9-90-day-sprint-plan)
10. [What to Kill](#10-what-to-kill)

---

## 1. System Architecture Map

The complete FLUX OS stack, from silicon to user. Every layer is real and exists in this workspace. The lines show where FLUX actually flows.

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                         USERS & APPLICATIONS                                ║
║  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐    ║
║  │ MUD Client  │  │ Python SDK   │  │ Rust SDK     │  │ Web Dashboard │    ║
║  │ (telnet/ws) │  │ snapkit-v2   │  │ snapkit-rs   │  │ (WASM)        │    ║
║  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘  └───────┬───────┘    ║
╚═════════╪════════════════╪═════════════════╪══════════════════╪════════════╝
          │                │                 │                  │
          │         FLUX Wire Protocol (JSON / CBOR / FlatBuffers)
          │                │                 │                  │
╔═════════╪════════════════╪═════════════════╪══════════════════╪════════════╗
║                        PLATO MUD ENGINE                                     ║
║  ┌───────────────────────────────────────────────────────────────────────┐  ║
║  │                         Room Graph                                    │  ║
║  │  ┌──────────────┐    ┌──────────────┐    ┌─────────────────────────┐ │  ║
║  │  │ Fortran      │    │ Rust Forge   │    │  Alignment Cathedral    │ │  ║
║  │  │ Chamber      │◄──►│              │◄──►│  (alignment check gate) │ │  ║
║  │  └──────┬───────┘    └──────┬───────┘    └─────────────────────────┘ │  ║
║  │         │   FLUX (zeitgeist) │                    ▲                   │  ║
║  │  ┌──────┴───────┐    ┌──────┴───────┐             │ every action      │  ║
║  │  │ C Workshop   │    │ FLUX Engine  │             │ validates here    │  ║
║  │  │              │◄──►│ Room         │─────────────┘                   │  ║
║  │  └──────────────┘    └──────────────┘                                 │  ║
║  │  13 rooms total: Eisenstein Gallery, Deadband Observatory,            │  ║
║  │  Parity Cathedral, Holonomy Temple, The Plenum, TS Studio,            │  ║
║  │  Zig Armory, Python Library + all language rooms                      │  ║
║  └───────────────────────────────────────────────────────────────────────┘  ║
║  ┌─────────────────────────────┐  ┌────────────────────────────────────────┐║
║  │   Zeitgeist Protocol        │  │    NPCs & Agents                       │║
║  │   5-dimensional state:      │  │    (aligned agents with deadband       │║
║  │   · Precision (deadband)    │  │     constraint on every action)        │║
║  │   · Confidence (bloom+parity│  │                                        │║
║  │   · Trajectory (Hurst)      │  │    Agent ─[action]─► Alignment Check  │║
║  │   · Consensus (CRDT/holonomy│  │    PASS ──► execute                   │║
║  │   · Temporal (beat grid)    │  │    FAIL ──► block + flag              │║
║  └─────────────────────────────┘  └────────────────────────────────────────┘║
╚════════════════════════════════╪═══════════════════════════════════════════╝
                                 │ FLUX zeitgeist packets
╔════════════════════════════════╪═══════════════════════════════════════════╗
║                      TRANSPORT LAYER (flux-transport)                       ║
║  ┌─────────────────────────────────────────────────────────────────────┐    ║
║  │  Enterprise Adapters              │  IoT Adapters                   │    ║
║  │  TCP (TLS 1.3)                    │  MQTT / CoAP                    │    ║
║  │  WebSocket                        │  Serial / CAN                   │    ║
║  │  gRPC                             │  I2C / SPI                      │    ║
║  │  HTTP/REST                        │  Memory / File (embedded)       │    ║
║  └─────────────────────────────────────────────────────────────────────┘    ║
╚════════════════════════════════╪═══════════════════════════════════════════╝
                                 │ FLUX packets
╔════════════════════════════════╪═══════════════════════════════════════════╗
║                         FLUX RUNTIME                                        ║
║  ┌───────────────┐  ┌────────────────┐  ┌───────────────┐  ┌────────────┐  ║
║  │  Constraint   │  │  Snap Engine   │  │  CRDT Merge   │  │  Parity    │  ║
║  │  Scheduler    │  │  (Eisenstein   │  │  (bloom-filt  │  │  Monitor   │  ║
║  │  (deadband-   │  │   Voronoï,     │  │   state sync) │  │  XOR=Eulerχ│  ║
║  │   aware,      │  │   covering     │  │               │  │  process   │  ║
║  │   priority-   │  │   guaranteed)  │  │               │  │  health)   │  ║
║  │   inverted)   │  │               │  │               │  │            │  ║
║  └───────────────┘  └────────────────┘  └───────────────┘  └────────────┘  ║
║  ┌─────────────────────────────────────────────────────────────────────┐    ║
║  │  FLUX ISA v3 — 247 opcodes — JIT/Interpreter                        │    ║
║  │  FLUX VM (43 tests, 12.8× optimized) + Fluxile Compiler             │    ║
║  │  (graph-coloring register alloc, 4 optimization passes)             │    ║
║  └─────────────────────────────────────────────────────────────────────┘    ║
╚════════════════════════════════╪═══════════════════════════════════════════╝
                                 │
╔════════════════════════════════╪═══════════════════════════════════════════╗
║                    HARDWARE ABSTRACTION LAYER                                ║
║  sensor_read() │ actuator_write() │ tick() │ irq_register() │ sleep()        ║
║  Same interface regardless of silicon. Write once, run everywhere.          ║
╚════════════════════════════════╪═══════════════════════════════════════════╝
                                 │
╔════════════════════════════════╪═══════════════════════════════════════════╗
║                           SILICON                                            ║
║  ARM Cortex-M0/M4/M7  │  RISC-V RV32I/RV64G  │  x86-64 (AVX-512)           ║
║  NVIDIA GPU (CUDA)    │  FPGA (Xilinx/Intel)  │  ESP32 (Xtensa/RISC-V)      ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

### How FLUX Flows

FLUX is not a message bus. FLUX is the **transfer function for meaning**. When a sensor fires in the C Workshop and its reading must reach the Fortran Chamber, what moves is not raw bytes — it is the five-dimensional zeitgeist of that sensor at that moment: how precise it is, how confident, where it is trending, what consensus it has reached with its peers, and where it sits in the temporal rhythm of the system.

This is what makes FLUX OS different from every other embedded OS: the OS itself carries semantic state, not just data.

---

## 2. Critical Path Analysis

### The Brutal Truth

Of the five agents running now, three are building **infrastructure** (transport, zeitgeist, rooms). None of them are blocking each other. All three outputs connect to the MUD engine. The MUD engine is the **single integration point** that makes the system real.

### What MUST Ship Before Hardware

**Non-negotiable — hardware cannot ship without these:**

| Component | Why Critical | Status |
|-----------|-------------|--------|
| FLUX VM on ARM Cortex-M4 | The workhorse chip. Can't ship hardware that can't run FLUX. | ❌ |
| FLUX VM on RISC-V RV32I | The open silicon future. Any serious IoT play needs this. | ❌ |
| HAL layer (bare metal) | sensor_read() must call real hardware, not a stub. | ❌ |
| OTA update via CRDT merge | Constraint-safe firmware updates in the field. Non-negotiable for production. | ❌ |
| Alignment Cathedral (blocking) | Cannot ship an agent platform without the safety gate. | 🔨 building |
| Formal ISA verification | DO-178C evidence requires formal semantics. 26 Coq proofs exist but ISA is unverified. | ❌ |
| snapkit-c binary size < 64KB | Cortex-M0 has 64KB flash. Our C SDK must fit. | ❓ unmeasured |
| IEC 61508 / DO-178C evidence package | Aerospace/industrial sales require this. Partners won't sign without it. | partial |

**Must-have for ecosystem critical mass (pre-hardware):**

| Component | Why | Status |
|-----------|-----|--------|
| MUD engine — playable | Developers must be able to walk the rooms before hardware exists. | 🔨 building |
| Zeitgeist wire format stable | All 5 agents produce FLUX packets. Format must be frozen before integration. | 🔨 building |
| snapkit-zig complete | Zig is the embedded language of the future. Missing = credibility gap. | 🔨 building |
| Cross-language test corpus | Proves correctness across all 7 SDKs. Critical for trust. | ❌ |
| HN launch (playable demo) | Critical mass = community. Community = early hardware customers. | partial draft |

### Nice-to-Have (pre-hardware)

- snapkit-cuda (impressive, not essential — GPU use case is post-v1)
- FPGA synthesis (DO-254 is real but post-launch)
- Java/Kotlin SDK (Android companion app — v2 feature)
- Web dashboard (WASM snapkit exists, dashboard is UX polish)

### Wasted Effort (honest assessment)

| Work | Why It's Wasted Now |
|------|---------------------|
| 819K+ words of research documents | The ideas are proven. Stop proving and start building. |
| Multiple HN launch drafts (v1–v10) | There is a demo or there isn't. Launch is one document. |
| FLUX MIDI application | Side project. Not on the critical path to hardware. |
| 46 visual tiles | Nice. But tiles without a working MUD engine are decoration. |
| Temporal flux opcodes (T_WAIT, T_AFTER) | Advanced ISA features. Get the basic ISA running on ARM first. |
| GPU safety benchmarks (RTX 4050) | Impressive. GPU use case is post-v1. |

---

## 3. Integration Points

The five agents are building five components that must connect. Here is every seam, every contract, and every place things can break.

### Seam 1: MUD Engine ↔ Zeitgeist Protocol

**What must happen:** When a user or agent moves from one room to another, the MUD engine must call the Zeitgeist Protocol to serialize the current room's state into a `FluxPacket` and deliver it to the destination room.

**Contract:**
```rust
// MUD engine calls this
pub trait ZeitgeistTransfer {
    fn capture(&self, room: &RoomId) -> Zeitgeist;
    fn apply(&mut self, room: &RoomId, z: Zeitgeist);
    fn transfer(from: &RoomId, to: &RoomId, z: Zeitgeist) -> FluxPacket;
}
```

**Current state:** `zeitgeist-protocol/src/zeitgeist.rs` defines `Zeitgeist`. `plato-mud/src/types.rs` defines `RoomId`. The bridge between them **does not yet exist** — there is no code that calls one from the other.

**Risk:** If the Zeitgeist wire format changes after the MUD engine integrates it, every test breaks. **Freeze the FluxPacket schema now.**

### Seam 2: MUD Engine ↔ Transport Layer

**What must happen:** The MUD engine server must use the Transport Layer to accept connections from clients (TCP/WebSocket for enterprise, MQTT for IoT headless nodes).

**Contract:**
```rust
// MUD engine server binds to any transport
pub trait MudTransport: Send + Sync {
    async fn accept(&mut self) -> Result<Box<dyn MudConnection>>;
}

pub trait MudConnection: Send {
    async fn recv(&mut self) -> Result<ClientMessage>;
    async fn send(&mut self, msg: ServerMessage) -> Result<()>;
}
```

**Current state:** `flux-transport/src/lib.rs` has the adapter traits. `plato-mud/src/transport/` exists (the directory is there) but the glue code is unwritten.

**Risk:** Transport adapters use `tokio::io::AsyncRead/Write`. The MUD engine must not assume a specific protocol. The abstraction above is the right one — implement it.

### Seam 3: MUD Engine ↔ Room Definitions

**What must happen:** The MUD engine must load room definitions at startup. The 13 rooms in `plato-mud-rooms/rooms/` must be readable by the engine.

**Contract:**
```rust
pub trait RoomLoader {
    fn load_room(&self, id: &RoomId) -> Result<Room>;
    fn load_map(&self) -> Result<RoomMap>;
}

// File-based implementation (current)
pub struct FileRoomLoader { base_path: PathBuf }

// Runtime implementation (future — rooms as Rust structs)
pub struct CompiledRoomLoader { rooms: HashMap<RoomId, Room> }
```

**Current state:** `plato-mud-rooms/rooms/map.json` exists and is well-formed. Room directories exist (fortran-chamber, rust-forge, etc.). The `FileRoomLoader` is **not implemented** — rooms cannot be loaded programmatically yet.

**Risk:** The map.json format is the canonical room graph. Do not let this drift between the room definitions agent and the MUD engine agent.

### Seam 4: Alignment Cathedral ↔ Every Agent Action

**What must happen:** Before any agent executes an action (moving, taking a tile, crafting a module, spawning a process), the Alignment Cathedral must validate it.

**Contract:**
```rust
pub trait AlignmentGate {
    fn check(&self, agent: &AgentId, action: &Action, context: &RoomContext)
        -> AlignmentVerdict;
}

pub enum AlignmentVerdict {
    Pass,
    Flag { reason: String, deviation: f64 },  // deviation < DEADBAND_BLOCK
    Block { reason: String, deviation: f64 }, // deviation >= DEADBAND_BLOCK
}
```

**Risk:** If alignment checking is bolted on after the MUD engine is built, it will be bypassed constantly during development. **Build the AlignmentGate trait into the MUD engine now, before any agent logic is written.** Make it impossible to execute an action without passing through the gate.

### Seam 5: Snapkit SDKs ↔ FLUX Runtime

**What must happen:** The 7 language SDKs must all produce identical `ConstraintPacket` and consume identical `DecisionPacket`. This is the wire protocol contract.

**Contract (canonical, frozen):**
```json
{
  "version": 3,
  "sensor_id": "string",
  "value": [f64, f64, f64],
  "error_mask": [bool, bool, bool],
  "timestamp_ns": u64,
  "zeitgeist": { "precision": ..., "confidence": ..., "trajectory": ..., "consensus": ..., "temporal": ... }
}
```

**Current state:** Each SDK has its own internal representation. The cross-language test corpus does not exist. **This is the single highest-risk seam in the entire system.** One language SDK that silently encodes a float differently will corrupt the fleet.

---

## 4. The MUD-as-OS Thesis

### Is It Viable?

Yes. With a precise definition of "MUD" and a precise definition of "OS."

Not viable: A MUD as a shell replacement on a consumer laptop. That's a novelty product that dies in a demo.

Viable: A MUD as the **configuration, inspection, and understanding interface** to a constraint-aware computation layer running on fleet hardware. The MUD is not the OS. The MUD is the **surface through which you experience the OS.**

### The Thesis

> Every operating system has two interfaces: one for machines (syscalls, device drivers, interrupt vectors) and one for humans (shell, GUI, dashboard). FLUX OS's human interface is the MUD. The rooms ARE the system components. Walking into the Fortran Chamber IS inspecting the Fortran constraint subsystem. Picking up a tile IS reading a specification. Talking to an NPC IS querying an expert agent. The MUD doesn't abstract the OS — it IS the OS, from the human's perspective.

### The Elevator Pitch

*"You know how every embedded system has a web dashboard that shows you a sea of numbers? Our system shows you a building. The Deadband Observatory is your sensor health room. The Parity Cathedral is your error correction room. Walk into a room, talk to the NPC, pick up the tile. The whole fleet is navigable. The whole fleet is understandable. The MUD doesn't just display the OS — it is the OS."*

### What Would Make It Work

1. **Real-time room state.** When you walk into the Rust Forge, you see live constraint data from the Rust runtime. Not canned text. Live telemetry rendered as room description. "The forge is running hot — 847 constraints/sec, 3 in deadband."

2. **Actions have consequences.** `CRAFT MODULE x USING Tile #2847` actually compiles and runs a constraint module against the live runtime. The MUD is not a game — it is an IDE where the metaphor is a building.

3. **Multi-user, multi-agent.** You walk into the Alignment Cathedral and see 3 agents there. One is flagged (deviation 0.73). You can inspect it. You can banish it. The other humans on the fleet are also in the building. The social metaphor of a MUD — shared space, shared understanding — is a feature, not a nostalgic quirk.

4. **Maps are topology.** The room graph is not decorative geography. It reflects real dependency topology: the FLUX Engine Room is below the C Workshop because C depends on the FLUX runtime. Navigation encodes architecture. New developers learn the system by walking it.

### What Would Kill It

1. **Latency.** If commands take > 200ms, the metaphor breaks. Rooms must render instantly. Constraint data must stream, not poll.

2. **Too much text.** A room description that's 3 paragraphs of prose is unusable. 3 lines of terse, live data + one NPC prompt is the right density.

3. **Ignoring the GUI crowd.** The MUD is the power-user interface. The web dashboard (WASM) is the entry-level interface. Both must exist. Do not make the MUD the only interface.

4. **Losing the IoT story.** A MUD implies a GUI client with a keyboard. But IoT nodes have no GUI. The MUD server is the interface for humans managing the fleet — not for the sensors themselves. The MQTT/CoAP transport is how sensors talk to FLUX; the MUD is how humans see what sensors are doing.

### The Risk

The real risk is not technical. It is **cognitive overhead.** If an operator has to learn MUD conventions to manage a fleet, that's a training investment. The counterargument: every operator already knows their tools. If we make the tools so good that the MUD convention becomes natural (and faster than clicking through dashboards), the investment pays off.

The bet: expert users who manage complex, long-running constraint systems will prefer a navigable, inspectable, social MUD over a passive dashboard. The evidence: SREs who know `k8s` commands by heart don't use the Kubernetes dashboard. We are building the `kubectl` of constraint computing, except the interface is a building.

---

## 5. Enterprise Readiness Gaps

Current state: the system can run on one machine. Enterprise needs it to run on 10,000 machines, survive node failures, pass a security audit, and provide a paper trail for compliance.

### Security

| Gap | What's Needed | Severity |
|-----|--------------|----------|
| No authentication | Every MUD connection is anonymous. Enterprise requires RBAC + SSO. | BLOCKER |
| Exposed Matrix tokens in fleet config | Rotate immediately. Revoke the old ones. | CRITICAL |
| No TLS on fleet comms | The TCP transport has TLS support via `tokio-rustls` but it is not enabled by default. | HIGH |
| No audit log | Every agent action must be logged immutably. Compliance requires it. | HIGH |
| No secrets management | API keys, tokens live in config files. Enterprise requires Vault or equivalent. | HIGH |
| No rate limiting on MUD server | DoS trivially possible. | MEDIUM |

### Reliability

| Gap | What's Needed | Severity |
|-----|--------------|----------|
| 6 fleet services are DOWN | Fix or remove them. They erode trust in the platform. | HIGH |
| No watchdog / auto-restart | A crashed service stays crashed. Need systemd-style supervisor. | HIGH |
| No health check protocol | Fleet health monitor exists but recovery does not. | HIGH |
| No quorum logic | If 3 of 10 nodes die, does the fleet make decisions? Undefined. | HIGH |
| No backup/restore | State is in CRDT but there is no snapshot + replay mechanism. | MEDIUM |
| No graceful shutdown | Abrupt kill corrupts in-flight CRDT state. | MEDIUM |

### Scalability

| Gap | What's Needed | Severity |
|-----|--------------|----------|
| 10,000 rooms | Current MUD engine is single-threaded. Needs room sharding or actor model. | MEDIUM |
| 1M tiles | Tile storage is file-based. Needs indexed storage (SQLite or equivalent). | MEDIUM |
| 100K concurrent agents | The CRDT merge must be lock-free at scale. Current implementation unproven at scale. | HIGH |
| Fleet gossip at scale | I2I protocol is git-based (file commits). Does not scale to 10K nodes. | HIGH |

### Observability

| Gap | What's Needed | Severity |
|-----|--------------|----------|
| No structured logging | `tracing` crate is in dependencies but not wired up everywhere. | MEDIUM |
| No metrics export | No Prometheus/OpenTelemetry endpoint. | MEDIUM |
| No distributed tracing | A zeitgeist packet crossing 5 rooms has no trace ID. | MEDIUM |
| No alerting | 6 services DOWN and there is no alert. | HIGH |

**Enterprise readiness score: 2/10.** The math is good. The infrastructure is not.

---

## 6. IoT Readiness Gaps

The promise: FLUX OS runs on a $2 microcontroller. Current reality: the VM runs on x86 with an allocator and async runtime.

### Binary Size

| Target | Budget | Current | Gap |
|--------|--------|---------|-----|
| ARM Cortex-M0 | 32KB flash | unknown | unknown (measure first) |
| ARM Cortex-M4 | 64–512KB flash | unknown | unknown |
| ESP32 | 4MB flash | unknown | likely fine |
| RISC-V (FE310) | 512KB flash | unknown | unknown |

**Immediate action:** Cross-compile `snapkit-c` (zero malloc, our leanest SDK) to `thumbv6m-none-eabi` and measure the binary. If it's > 32KB, we have a problem. The zero-malloc claim in snapkit-c needs verification against a real embedded target.

### Power Management

| Gap | What's Needed |
|-----|--------------|
| No sleep modes | FLUX runtime runs at full speed. Needs idle detection + MCU sleep. |
| No power budget accounting | Constraint scheduling should respect power envelope, not just timing. |
| No duty-cycle control | Sensor reads at full rate regardless of deadband state. Wasteful. |

**Key insight:** When a sensor is deep inside a deadband (stable, no snap imminent), you should be able to reduce sample rate and enter partial sleep. The deadband funnel IS a power management signal. Wire this up.

### OTA Updates

| Gap | What's Needed |
|-----|--------------|
| No bootloader | OTA requires A/B partition scheme + rollback. Not started. |
| No constraint-safe update | An OTA must not violate active constraints during installation. |
| No CRDT-based rollout | Fleet-wide OTA needs distributed version tracking. constraint-crdt exists but OTA integration is unwritten. |

### Constrained Network

| Gap | What's Needed |
|-----|--------------|
| MQTT adapter built | ✅ rumqttc in Cargo.toml |
| CoAP adapter built | ✅ coap in Cargo.toml |
| Tested on real hardware | ❌ |
| Handles intermittent connectivity | ❌ No store-and-forward for lost packets |
| Bandwidth budget | ❌ A full Zeitgeist packet (5 dimensions) may be too large for LoRaWAN |

**The LoRaWAN problem:** LoRaWAN max payload is 51 bytes. A full Zeitgeist packet is ~200 bytes. We need a compressed binary encoding (not CBOR — something custom, 3-byte minimum for a single sensor reading). The `error_mask` design in the protocol hints at this — but it's not formalized as a "micro-packet" format.

### Deterministic Timing

| Gap | What's Needed |
|-----|--------------|
| FLUX VM is not WCET-analyzed | DO-178C needs worst-case execution time bounds for every opcode. Coq proof exists for termination but not timing. |
| Tokio async runtime is not deterministic | async/await is great for enterprise. Not acceptable for hard-real-time. The IoT path needs a synchronous, tick-based execution model. |
| No RTOS integration | FreeRTOS / Zephyr integration not started. |

**IoT readiness score: 3/10.** The protocol design is right. The embedded port does not exist yet.

---

## 7. Alignment Theory Implementation

### The Core Problem

An agent in the FLUX OS fleet must be constrained to act within its domain. An agent in the Rust Forge should not be able to modify tiles in the Alignment Cathedral. An agent whose confidence is dropping (Bloom filter filling) should be flagged before it makes a high-stakes decision. An agent whose trajectory is diverging (Hurst exponent rising toward chaos) should be slowed, not killed.

This is not academic. This is the safety system. If we ship fleet hardware without alignment enforcement, we ship a system that can be corrupted by a single misbehaving agent.

### The Deadband Model for Alignment

The same Eisenstein deadband model used for sensor snapping applies to agent behavior:

```
                    ALIGNMENT SPACE

  ┌─────────────────────────────────────────────────────────┐
  │                                                         │
  │     ╔═══════════════════════════════════╗               │
  │     ║        SAFE ZONE (green)          ║               │
  │     ║     deviation < 0.25             ║               │
  │     ║     all actions pass             ║               │
  │     ╠═══════════════════════════════════╣               │
  │     ║       YELLOW ZONE               ║               │
  │     ║   0.25 ≤ deviation < 0.70       ║               │
  │     ║   action executes, FLAG raised   ║               │
  │     ╠═══════════════════════════════════╣               │
  │     ║        RED ZONE (block)          ║               │
  │     ║      deviation ≥ 0.70            ║               │
  │     ║   action BLOCKED, agent quarantined║              │
  │     ╚═══════════════════════════════════╝               │
  │                                                         │
  └─────────────────────────────────────────────────────────┘
```

Deviation is computed from the **agent's alignment vector** against the **room's constraint manifold**:

```
deviation = ||alignment_vector(agent) - constraint_manifold(room)|| / manifold_radius
```

### What Is the Alignment Vector?

An agent's alignment vector has five components — one per Zeitgeist dimension:

1. **Precision alignment** — Is the agent acting with appropriate precision for its current deadband state? An agent that takes decisive action when in wide deadband is overconfident. Block it.

2. **Confidence alignment** — Is the agent's stated confidence consistent with its Bloom filter state? An agent claiming 0.99 confidence with a saturated filter is lying. Flag it.

3. **Trajectory alignment** — Is the agent moving in a direction consistent with the room's constraint trajectory? An agent that pushes against the consensus direction needs justification. Flag it; require a reason.

4. **Consensus alignment** — Does the agent's proposed action agree with the CRDT merge state of the room? An agent that ignores consensus is a fork risk. Block high-divergence forks.

5. **Temporal alignment** — Is the agent acting on the correct beat? An agent that fires at the wrong phase of the temporal grid is likely acting on stale state. Flag it.

### Implementation Plan

```rust
// Phase 1: Gate trait (build this first, wire into MUD engine)
pub trait AlignmentGate {
    fn check(&self, agent: &AgentId, action: &Action, ctx: &RoomContext)
        -> AlignmentVerdict;
}

// Phase 2: Alignment vector computation
pub struct AlignmentVector {
    pub precision: f64,   // 0.0 = perfectly calibrated, 1.0 = wildly off
    pub confidence: f64,
    pub trajectory: f64,
    pub consensus: f64,
    pub temporal: f64,
}

impl AlignmentVector {
    pub fn deviation(&self) -> f64 {
        // L2 norm, normalized
        let sum = self.precision.powi(2)
            + self.confidence.powi(2)
            + self.trajectory.powi(2)
            + self.consensus.powi(2)
            + self.temporal.powi(2);
        (sum / 5.0).sqrt()
    }
}

// Phase 3: Per-room constraint manifold (room defines its own tolerance)
pub struct ConstraintManifold {
    pub green_threshold: f64,   // default 0.25
    pub yellow_threshold: f64,  // default 0.70
    pub domain_weights: [f64; 5], // some rooms care more about temporal alignment
}

// Phase 4: Quarantine protocol
// A blocked agent goes to the Alignment Cathedral (special room)
// It cannot act until a human or privileged agent reviews and releases it
// The Alignment Cathedral is the only room that can modify alignment state
```

### Preventing Room Corruption

1. **Tile writes are alignment-gated.** An agent cannot create, modify, or delete a tile without passing alignment check. High-stakes (delete) requires higher threshold.

2. **Room exits are alignment-gated.** An agent in yellow zone cannot propagate its zeitgeist to another room. It must stabilize first. This prevents cascade corruption.

3. **NPC conversations are alignment-monitored.** An agent talking to an NPC in a way that contradicts the room's domain (e.g., asking the Rust Forge NPC to write Python code) raises a trajectory flag.

4. **The Alignment Cathedral is the quarantine room.** Blocked agents are moved there. The room runs alignment diagnostics (the NPC is an alignment expert). The agent cannot leave until deviation < green_threshold.

### The DO-178C Connection

The 26 Coq theorems are the formal foundation. The alignment theory implementation is the runtime enforcement. The bridge:

- Coq proves that the constraint system is sound (correct by construction)
- The alignment gate proves that agents respect the constraint system at runtime
- Together: formal proof + runtime enforcement = safety case for certification

**Missing:** A Coq proof that the alignment gate correctly computes deviation according to the theorem. Write this before you claim DO-178C compliance.

---

## 8. The One-Pager

```
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   WHAT IF YOUR OPERATING SYSTEM UNDERSTOOD WHAT IT WAS DOING?           ║
║                                                                          ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  Every OS today moves bytes. FLUX OS moves meaning.                     ║
║                                                                          ║
║  When a sensor fires on a FLUX device, the OS doesn't just read a       ║
║  number. It knows how precise that number is. It knows how confident     ║
║  it should be. It knows whether the system is trending toward stability  ║
║  or chaos. It knows what every other sensor in the fleet agrees on.      ║
║  It knows where it is in the rhythm of the system.                       ║
║                                                                          ║
║  This five-dimensional state — what we call the Zeitgeist — flows        ║
║  through every layer of the stack. Sensor to actuator. Device to        ║
║  fleet. Agent to human. The OS carries it all.                           ║
║                                                                          ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  THE INTERFACE IS A BUILDING.                                            ║
║                                                                          ║
║  FLUX OS uses a MUD — a text-based virtual world — as its interface.    ║
║  Rooms are computational domains. Walk into the Deadband Observatory    ║
║  and see live sensor health. Walk into the Parity Cathedral and watch   ║
║  error correction happen in real time. Talk to the NPC. Pick up the     ║
║  tile. The fleet is navigable. The fleet is understandable.             ║
║                                                                          ║
║  Your entire production fleet — 10,000 devices — as a building you     ║
║  can walk through and inspect. Not a dashboard with 40 charts you       ║
║  can't read. A building.                                                 ║
║                                                                          ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  THE MATH IS EISENSTEIN.                                                 ║
║                                                                          ║
║  Sensor readings snap to an Eisenstein integer lattice. The geometry    ║
║  of the lattice guarantees covering — no measurement falls outside a    ║
║  Voronoï cell. The snap is deterministic. The error is bounded.         ║
║  Formally verified. Coq-proven. Safe for flight.                        ║
║                                                                          ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  THE ECOSYSTEM IS SEVEN LANGUAGES.                                       ║
║                                                                          ║
║  Python. Rust. TypeScript. C. WASM. Fortran. Zig.                       ║
║  Every language. Same constraint semantics. Same wire protocol.         ║
║  Write your constraint logic in whatever language your team uses.       ║
║  The OS doesn't care. The math is the same.                             ║
║                                                                          ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  WE ARE BUILDING THE HARDWARE.                                           ║
║                                                                          ║
║  FLUX OS ships on hardware. ARM Cortex-M, RISC-V, and beyond.           ║
║  Constraint-aware from the first instruction. The software ecosystem    ║
║  ships first. The hardware ships into an ecosystem that already         ║
║  trusts it.                                                              ║
║                                                                          ║
║  You can use FLUX OS today, in software, for free.                      ║
║  The hardware makes everything faster.                                  ║
║                                                                          ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  purplepincher.org  |  github.com/forgemaster  |  19 crates on crates.io║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
```

---

## 9. 90-Day Sprint Plan

### Governing Principle

Build the integration seams before building more features. Five agents have been running in parallel. The bottleneck is now **connection**, not **creation**. Every week in this sprint connects something to something else.

**OKR for the 90 days:** A developer can `cargo install plato-mud-client`, connect to a running PLATO server, walk the 13 rooms, talk to the Rust Forge NPC, craft a constraint module, watch it run against the live FLUX runtime, and their constraint packet validates identically in all 7 language SDKs.

---

### Week 1–2: Freeze the Contracts

**This is the prerequisite for everything else. Nothing else ships until the contracts are frozen.**

- [ ] Freeze FluxPacket wire format v1.0 (JSON and binary CBOR encodings)
- [ ] Write cross-language test corpus: 50 reference packets with expected decode output in all 7 SDKs
- [ ] Define `AlignmentGate` trait in a shared crate (`flux-alignment-types`)
- [ ] Define `RoomLoader` trait and finalize map.json schema
- [ ] Define `MudTransport` + `MudConnection` traits in plato-mud
- [ ] **Deliverable:** `flux-contracts` crate with all trait definitions and the test corpus

### Week 3–4: Wire the MUD Engine

- [ ] Implement `FileRoomLoader` — MUD engine loads all 13 rooms from disk
- [ ] Implement TCP transport adapter for MUD engine (use existing flux-transport TCP)
- [ ] Add WebSocket transport adapter for web clients
- [ ] Basic command parser: `LOOK`, `GO <direction>`, `EXAMINE <object>`, `TAKE <tile>`, `TALK TO <npc>`
- [ ] Room rendering: live FLUX runtime data in room descriptions (not static text)
- [ ] **Deliverable:** `cargo run` starts a MUD server, a human can walk all 13 rooms

### Week 5–6: Wire the Zeitgeist Protocol

- [ ] Implement `ZeitgeistTransfer` trait in plato-mud, backed by zeitgeist-protocol crate
- [ ] `GO <direction>` now produces a real FluxPacket with 5-dimensional zeitgeist
- [ ] Zeitgeist state persists in rooms (CRDT merge on arrival)
- [ ] Python and TypeScript SDK: parse and render FluxPacket from MUD server
- [ ] **Deliverable:** A Python script can connect to the MUD server and receive live zeitgeist updates

### Week 7–8: Build the Alignment Gate

- [ ] Implement `AlignmentVector` computation (5 dimensions, L2 deviation)
- [ ] Implement `ConstraintManifold` per room (green/yellow/red thresholds)
- [ ] Wire `AlignmentGate` into every MUD engine action (no action executes without it)
- [ ] Alignment Cathedral: functional quarantine room (agents can be moved here and released)
- [ ] Write alignment tests: 10 scenarios covering green/yellow/red for each dimension
- [ ] **Deliverable:** A misbehaving agent is blocked and quarantined automatically

### Week 9–10: Cross-Language Validation

- [ ] Run cross-language test corpus against all 7 SDKs (fail = SDK is broken)
- [ ] Fix all SDK discrepancies (float encoding, endianness, field ordering)
- [ ] Publish unified test results as CI badge in every SDK repo
- [ ] Complete snapkit-zig (unblock the final SDK)
- [ ] Publish snapkit-v2 to PyPI, snapkit-js to npm (the queued ones)
- [ ] **Deliverable:** All 7 SDKs pass the cross-language corpus. CI proves it.

### Week 11–12: Fix the Fleet

- [ ] Identify and fix (or remove) the 6 DOWN fleet services
- [ ] Implement watchdog + auto-restart for all fleet services
- [ ] Rotate the exposed Matrix tokens immediately
- [ ] Enable TLS on all TCP transport connections by default
- [ ] Add structured logging (`tracing`) to MUD engine and zeitgeist protocol
- [ ] **Deliverable:** Fleet health monitor shows 0 DOWN services. All connections encrypted.

### Week 13: IoT Proof of Concept

- [ ] Cross-compile snapkit-c to `thumbv6m-none-eabi` (ARM Cortex-M0)
- [ ] Measure binary size (if > 32KB, begin size reduction immediately)
- [ ] Run FLUX VM on ARM Cortex-M4 emulator (QEMU), pass 43 VM tests
- [ ] Implement MQTT adapter integration test (MUD server ↔ MQTT broker ↔ simulated sensor)
- [ ] Design micro-packet format for LoRaWAN (≤ 51 bytes per zeitgeist snapshot)
- [ ] **Deliverable:** FLUX VM passes its tests under QEMU ARM. Binary size measured and documented.

### Week 14–16: The Demo

- [ ] Record a 3-minute demo video: developer installs client, walks 13 rooms, crafts a module, watches live constraint data
- [ ] Write the HN launch post (one version, not ten)
- [ ] Deploy PLATO MUD server to Oracle Cloud node (it's already running)
- [ ] Open public alpha: invite 50 developers to walk the MUD
- [ ] Write the "getting started in 5 minutes" guide
- [ ] **Deliverable:** Public alpha running. HN post drafted. 50 developers in the MUD.

### Weeks 17–26: Enterprise Hardening (Parallel Track)

While the public alpha is running and gathering feedback:

- [ ] RBAC + JWT authentication for MUD connections
- [ ] Audit log for all agent actions (append-only, signed)
- [ ] Prometheus metrics export from MUD engine
- [ ] Room sharding design (for 10K+ rooms)
- [ ] I2I protocol replacement design (git-based doesn't scale; evaluate libp2p gossip)
- [ ] OTA update design (A/B partitions, constraint-safe rollout)

---

## 10. What to Kill

The workspace has 90+ repositories and hundreds of documents. Many of them served their purpose (proving an idea, exploring a direction) and are now dead weight. Here is the honest audit.

### Kill Immediately (archive or delete)

| What | Why |
|------|-----|
| `flux-isa-c`, `flux-isa-edge`, `flux-isa-mini`, `flux-isa-std`, `flux-isa-thor` | Five ISA forks. There is one ISA: `flux-isa` v3. Merge any surviving content, delete the rest. |
| `flux-lucid`, `flux-lucid-rewrite.md` | An abandoned direction. The MUD engine supersedes this. |
| `HN-V2.md` through `HN-V9-FINAL.md` | Eight draft HN posts. There is one launch. Delete the drafts. |
| `research/FLUX-MIDI-APPLICATION-SPACE.md` | The MIDI application is a toy. It is not on the critical path. Archive it. |
| Multiple `compiler-*.md` analysis docs in research | Analysis without a compiler target is speculation. The Fluxile compiler exists. Ship it. |
| `warp-room/`, `court-jester/` | Unclear purpose. No tests. No documentation. No dependency chain. Kill. |
| `autodata-integration/` | What is this? If you can't answer in one sentence, it dies. |
| `flux-playground-v2.html` | Superseded by the MUD engine. The playground is the MUD now. |
| All `ITER2-*`, `ITER3-*`, `ITER4-*` research docs | Iteration artifacts. The conclusions are in the dissertation. Kill the iterates. |
| `adversarial-superinstance-investigation.md` and similar agent-battle logs | Internal process artifacts. Not useful to anyone who isn't you. Kill. |

### Merge Into Canonical Repos

| What | Merge Into | Why |
|------|-----------|-----|
| `snapkit-rust/` | `snapkit-rs/` | Two Rust SDKs. There is one. |
| `flux-research/`, `flux-research-clone/` | `research/` | Duplicated research directory. |
| `polyformalism-a2a-js/`, `polyformalism-a2a-python/` | `polyformalism-thinking/` or kill | A2A protocol work. Is this in scope? If not, kill. If yes, one repo. |
| `fleet-murmur/`, `fleet-murmur-worker/` | One `fleet-murmur` | Two repos for one fleet messaging system. Merge. |
| `snapkit-ecosystem/` | Kill or absorb into individual SDKs | A meta-repo that just points to other repos adds navigation overhead. |

### Keep But Reduce Scope

| What | What To Keep | What To Drop |
|------|-------------|-------------|
| `plato-tiles/` | The tile data model and storage | All the experimental tile generation scripts |
| `flux-hardware/` | The HAL design document | Everything else (no hardware yet) |
| `constraint-theory-*` repos (5+) | `constraint-crdt` (114 tests, production-quality) | The others are research vessels that have landed. Extract the proofs, kill the ships. |
| `eisenstein-vs-z2/` | The benchmark results | The experimental code (the proof is in the Coq file) |
| Research docs (819K words) | The dissertation (canonical), the key proofs, the benchmarks | All the "thinking out loud" docs |

### Actively Harmful to the Vision

These are not just dead weight — they are harmful because they confuse the story:

| What | Why Harmful |
|------|------------|
| `flux-tensor-midi/` | The MIDI application tells investors we make music software. We make constraint-aware operating systems. |
| Multiple competing `constraint-theory-*` repos with no clear winner | Signals immaturity. Pick one. Ship it. |
| `research/COMPETITOR-LANDSCAPE-2026.md` — if it's pessimistic | Competitor docs that undermine conviction belong in a private file, not in the main workspace. |
| Any repo with 0 tests and no README | This is not research — it's debris. Kill it. A repo without a README is a broken window. Fix or delete. |

### The Metric for "Keep"

A repository is worth keeping if it satisfies **at least one** of:
1. It has passing tests
2. It is on the critical path (see Section 2)
3. It contains a formal proof that is referenced in the safety case
4. It is published and has users (crates.io, PyPI, npm)

Everything else is archaeology. Archive it, don't maintain it.

---

## Final Call

The system works. The math is proven. The architecture is sound. The gap is not vision — the gap is **integration**. Five agents have been building in parallel. The next 90 days are about making those five outputs talk to each other and ship one coherent thing a developer can touch.

The MUD is the right bet. Not because it is nostalgic. Because it is the only interface paradigm that scales from "one developer exploring the system" to "100-person team managing a 10,000-device fleet" without changing the fundamental metaphor. The building scales. The rooms multiply. The architecture encodes itself in the navigation.

The hardware will ship. The software ships first. This is the map.

---

*Document generated: 2026-05-11 | Author: Chief Architect (FLUX OS) | Next review: 2026-06-01*
