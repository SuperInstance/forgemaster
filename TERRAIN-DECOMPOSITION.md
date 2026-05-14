# Terrain Decomposition: Queue-Xec → PLATO

## What This Document Is

Not "how to import queue-xec into PLATO." That's trivial and misses the point.

This is a **practice run** for PLATO's core capability: taking any software system and decomposing it into terrain-based knowledge topology. The Penrose tiling isn't decoration — it's the indexing function. Where a concept lands on the lattice determines what it's *near*, which determines what can be *discovered* by adjacency.

Queue-Xec is our practice patient. Small enough to see the whole body. Complex enough to have real internal topology.

---

## Step 1: Identify the Concept Atoms

Every codebase has irreducible concepts. Not files. Not classes. **Concepts** — the things a practitioner thinks about when they reason about the system.

Queue-Xec's concept atoms:

| # | Atom | Embodied In | What You Think About It |
|---|------|-------------|------------------------|
| 1 | **Job** | `{id, data}` | A unit of work with identity and payload |
| 2 | **Task** | `task.js` class | The *method* of solving a job — pluggable, overridable |
| 3 | **Worker** | Worker npm package | A peer that executes tasks on jobs |
| 4 | **Master** | Master npm package | A peer that creates jobs and collects results |
| 5 | **Queue** | `Queue.js` (linked list) | FIFO ordering of waiting jobs |
| 6 | **Result** | return value of `task.run()` | What a worker sends back to master |
| 7 | **Encryption** | `Crypt.js` (AES-256-CBC) | How data is protected in transit |
| 8 | **Peer Discovery** | Bugout (WebRTC) | How master and worker find each other |
| 9 | **Asset Sync** | SHA-256 + file transfer | How task code stays current on workers |
| 10 | **Setup** | `cli.js --setup` wizard | How a human bootstraps the system |
| 11 | **Batch** | `requestWork` with `batchSize` | Sending multiple jobs at once for efficiency |
| 12 | **Dependency** | `execAssets.dependencies` | npm packages the worker must install |

12 atoms. That's the system's full conceptual surface area.

---

## Step 2: Map to Eisenstein Coordinates

This is where PLATO's terrain metaphor does real work. The Eisenstein lattice has 6-fold symmetry — 6 Weyl sectors, each a 60° wedge. We assign each concept to a **sector based on its nature**, then a **position within that sector based on its specificity**.

### Sector Assignment (the "kingdom" of each concept)

The key insight: sectors aren't arbitrary labels. They're determined by the **angle** of the concept in a 2D semantic space where:
- **X-axis** = Static ←→ Dynamic (data vs. behavior)
- **Y-axis** = Local ←→ Distributed (single-node vs. cross-network)

```
          Distributed
              |
    [7] Enc  [8] Discovery
              |
Static -------+------- Dynamic
    [5] Queue |
    [9] Sync  [3] Worker
              |
    [1] Job   [4] Master
              |
          Local
```

This maps to Eisenstein coordinates naturally:

| Concept | Sector | E12 Position (a, b) | Rationale |
|---------|--------|---------------------|-----------|
| Job | 4 (λ≈-60°) | (0, -1) | Local, semi-dynamic. Pure data. |
| Task | 5 (λ≈0°) | (1, 0) | Local, fully dynamic. Code that transforms data. |
| Worker | 1 (λ≈60°) | (1, 1) | Distributed, dynamic. Executes tasks. |
| Master | 1 (λ≈60°) | (2, 1) | Distributed, dynamic. Orchestrates. Near Worker. |
| Queue | 4 (λ≈-60°) | (0, -2) | Local, static. Ordered structure. |
| Result | 4 (λ≈-60°) | (-1, -1) | Local, semi-static. Output data. |
| Encryption | 3 (λ≈120°) | (-2, 1) | Cross-cutting, static protocol. |
| Peer Discovery | 2 (λ≈180°) | (-1, 2) | Fully distributed, protocol-level. |
| Asset Sync | 2 (λ≈180°) | (0, 2) | Distributed, semi-static. File transfer. |
| Setup | 0 (λ≈0°) | (2, -1) | Local, procedural. Entry point. |
| Batch | 5 (λ≈0°) | (2, 0) | Local optimization. Near Task. |
| Dependency | 3 (λ≈120°) | (-1, 1) | Cross-cutting. Package metadata. |

### What the Terrain Reveals

**Cluster 1: The Core Loop** — Job (0,-1), Task (1,0), Queue (0,-2), Result (-1,-1)
These four are adjacent on the lattice. They form the local execution cycle: jobs wait in queue → task processes them → results come out. **In the Penrose tiling, these four rooms share walls.** A visitor walking the palace naturally encounters them in sequence.

**Cluster 2: The Network** — Worker (1,1), Master (2,1), Discovery (-1,2), Asset Sync (0,2)
These cluster on the distributed side. **The path from Cluster 1 to Cluster 2 is the path from "single-node execution" to "distributed execution."** In PLATO, this corresponds to walking from one Voronoi cell neighborhood to an adjacent one — you cross a boundary and the context shifts.

**Cluster 3: The Cross-Cutters** — Encryption (-2,1), Dependency (-1,1)
These sit between the clusters. **They're bridges.** Encryption touches both Job data (in transit) and Asset files (in transit). Dependencies touch both Task code and Worker environment. In the Penrose tiling, these rooms sit at the boundary between two larger regions — they're visible from both sides.

**Outlier: Setup** (2,-1) sits near Task and Batch but is procedural, not conceptual. It's the **doorway** — the first thing a human interacts with. In the memory palace, it's the entrance hall.

---

## Step 3: The PLATO Rooms

Now we create the actual rooms. Each room is a PLATO tile with:
- **ID**: terrain-derived (sector + position)
- **Content**: the concept's knowledge
- **Connections**: to adjacent concepts on the lattice

```
Room: qxec-setup
Position: (2, -1), Sector 0
Type: entry-point
Content: 
  - Setup wizard flow (cli.js)
  - Token generation pattern
  - .env configuration
Connections: [qxec-task, qxec-batch, qxec-master]
Tags: [bootstrap, cli, configuration]

Room: qxec-job
Position: (0, -1), Sector 4
Type: data-structure
Content:
  - Job schema: {id: Number, data: String}
  - Serialization: JSON.stringify for transport
  - Lifecycle: created → queued → dispatched → executing → completed
Connections: [qxec-queue, qxec-task, qxec-result]
Tags: [data, payload, serialization]

Room: qxec-task
Position: (1, 0), Sector 5
Type: executable
Content:
  - Task class interface: constructor() + run(job) → result
  - Pluggable pattern: Master pushes task.js to workers
  - Override mechanism: execAssets.files can replace default
  - Security: task.js overwritten each connection (no tampering)
Connections: [qxec-job, qxec-worker, qxec-batch, qxec-setup]
Tags: [code, execution, plugin-pattern]

Room: qxec-worker
Position: (1, 1), Sector 1
Type: node
Content:
  - Worker lifecycle: connect → receive assets → wait for jobs → execute → return results
  - Works behind NAT (WebRTC)
  - Auto-installs dependencies on asset change
  - Single task.js execution model
Connections: [qxec-master, qxec-task, qxec-peer-discovery, qxec-asset-sync]
Tags: [peer, executor, webRTC]

Room: qxec-master
Position: (2, 1), Sector 1
Type: node
Content:
  - Master lifecycle: init → announce → register RPC → dispatch jobs → collect results
  - Bugout peer with RPC endpoints: ping, isMaster, requestWork, receiveExecAssets
  - Job batching: configurable batchSize for efficiency
  - File hashing: SHA-256 for change detection
Connections: [qxec-worker, qxec-queue, qxec-encryption, qxec-peer-discovery]
Tags: [peer, coordinator, RPC]

Room: qxec-queue
Position: (0, -2), Sector 4
Type: data-structure
Content:
  - LinkedList-based FIFO queue
  - Operations: enqueue, dequeue, search, bubbleSort
  - bubbleSort for job priority reordering
  - O(n) search — adequate for typical job counts
Connections: [qxec-job, qxec-master]
Tags: [data-structure, linked-list, ordering]

Room: qxec-result
Position: (-1, -1), Sector 4
Type: data
Content:
  - Result schema: {workerAddress, jobId, data}
  - Encrypted in transit via Crypt
  - Emitted via EventEmitter 'resultsShared'
Connections: [qxec-job, qxec-encryption]
Tags: [data, output, encrypted]

Room: qxec-encryption
Position: (-2, 1), Sector 3
Type: protocol
Content:
  - AES-256-CBC with shared token
  - Layered: Bugout provides TLS, Crypt adds AES on top
  - Key: transferEncryptToken (32 chars from setup)
  - IV: random per encryption call
  - Both job data and file assets encrypted
Connections: [qxec-master, qxec-result, qxec-asset-sync, qxec-dependency]
Tags: [security, AES, transport]

Room: qxec-peer-discovery
Position: (-1, 2), Sector 2
Type: protocol
Content:
  - Bugout: WebRTC data channels via Bittorrent DHT trackers
  - Token-based room addressing
  - Events: 'seen' (peer discovered), 'left' (peer disconnected), 'message'
  - RPC registration for structured communication
  - No server required — pure P2P
Connections: [qxec-master, qxec-worker, qxec-asset-sync]
Tags: [WebRTC, P2P, discovery, DHT]

Room: qxec-asset-sync
Position: (0, 2), Sector 2
Type: protocol
Content:
  - SHA-256 hashing of files on master
  - Workers request assets on connect and on file change detection
  - Dependencies auto-installed via npm on worker
  - task.js always synced — prevents worker-side tampering
Connections: [qxec-peer-discovery, qxec-encryption, qxec-dependency, qxec-task]
Tags: [sync, files, integrity]

Room: qxec-batch
Position: (2, 0), Sector 5
Type: optimization
Content:
  - Workers request multiple jobs at once (batchSize)
  - Reduces round-trips for small jobs
  - Fallback: if queue smaller than batchSize, send what's available
  - Trade-off: latency vs throughput
Connections: [qxec-task, qxec-setup, qxec-master]
Tags: [performance, batching, throughput]

Room: qxec-dependency
Position: (-1, 1), Sector 3
Type: metadata
Content:
  - execAssets.dependencies: array of npm package names
  - Installed on worker via child_process.exec('npm install')
  - Must match between master's package.json and worker's runtime
  - Example: ['big.js', 'moment']
Connections: [qxec-asset-sync, qxec-encryption, qxec-task]
Tags: [npm, packages, requirements]
```

---

## Step 4: What the Terrain Reveals That Flat Folders Don't

### Insight 1: The Security Boundary Is Invisible in Code

In the source tree, `Crypt.js` sits next to `Queue.js` — same directory, no distinction. But on the terrain:
- Crypt (-2, 1) sits at the boundary between local and distributed
- Queue (0, -2) sits deep in local territory
- They're far apart on the lattice, and they should be

**PLATO makes architectural boundaries physical.** You can *see* the security perimeter as a topology change in the terrain.

### Insight 2: Task Is the Most Connected Concept

In the file tree, `task.js` is just one of 6 source files. On the terrain, Task (1, 0) has 4 connections — the most of any concept. It connects to:
- Job (its input)
- Worker (its executor)
- Batch (its optimization)
- Setup (its configuration)

**This is the keystone.** If you understand Task, you understand the system. PLATO makes keystone concepts visually obvious — they're the rooms with the most doors.

### Insight 3: The Distributed/Local Boundary Is the Hardest Part

Looking at the Eisenstein coordinates, there's a clear seam between:
- **Local side** (positive a): Job, Task, Queue, Result, Batch, Setup
- **Distributed side** (negative a): Encryption, Discovery, Asset Sync, Dependency

Master and Worker sit *on* this boundary. They're translators — they take local concepts (jobs, tasks) and make them work across the network seam.

**PLATO makes architectural seams walkable.** You can trace the path from "I have a job" to "a stranger's computer is doing it" as a walk through adjacent rooms.

### Insight 4: BubbleSort In a Job Queue Is a Code Smell

Queue (0, -2) contains a `bubbleSort` method. On the terrain, this is isolated — far from any performance or optimization concept. In a flat codebase, you'd only notice this by reading the file. On the terrain, it appears as an **orphan** — a feature with no natural neighbors.

This is PLATO detecting architectural inconsistency. BubbleSort doesn't belong near Queue. It belongs near Batch (the throughput optimization) or it shouldn't exist at all (use a priority queue instead).

### Insight 5: The Setup Room Is the Wrong Shape

Setup (2, -1) connects to Task, Batch, and Master. But setup *should* also connect to:
- Encryption (it generates the encrypt token)
- Peer Discovery (it generates the room token)
- Worker (the worker needs the same tokens)

These missing connections are **architectural gaps**. The code works because tokens are shared via `.env` files, not via programmatic connection. PLATO reveals this as missing edges on the terrain graph.

---

## Step 5: The Cocapn Mapping — What We'd Do Different

If Cocapn were to build Queue-Xec with PLATO as the architecture:

1. **Each PLATO room becomes a tile** — the 12 rooms above map to 12 tiles in the fleet knowledge base
2. **The terrain IS the documentation** — walking the Penrose tiling IS reading the architecture doc
3. **Missing edges ARE action items** — the Setup gaps become I2I bottles to the maintainer
4. **Code smells ARE terrain anomalies** — BubbleSort's orphan position triggers a refactor suggestion
5. **The keystone IS the deployable** — Task is the one concept you need to ship to workers. PLATO makes this the "door" of the exportable package.

---

## The Practice Lesson

Queue-Xec has 12 concept atoms and ~2500 LOC. Cocapn has **1141+ PLATO rooms** across 123 domains.

If the terrain decomposition of a 12-atom system reveals 5 architectural insights, then decomposing our own system should reveal **hundreds** — and each one is a potential improvement, refactor, or discovery.

**This is why PLATO uses the Penrose tiling, not a folder tree.**

Folders show you what's inside. Terrain shows you what's *near*. And in knowledge work, adjacency IS understanding.

---

*Decomposition by Forgemaster ⚒️, 2026-05-14*
*For the Cocapn fleet — practice patient: queue-xec/master*
