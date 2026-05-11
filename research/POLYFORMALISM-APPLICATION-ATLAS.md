# Polyformalism Application Atlas

**Forgemaster Research Report** · 2026-05-11  
**Status:** Honest assessment — not every domain is a fit  
**Core Tech:** polyformalism (13-language constraint library), Eisenstein lattice operations, constraint-theory snap/holonomy/merge, bloom semilattice CRDTs

---

## Executive Summary

Polyformalism gives us three weapons: **exact discrete constraint checking** (3.85B ops/s on AVX2), **Eisenstein lattice operations** (D6 symmetry, 1.15x hex packing density), and **bloom semilattice merge** (idempotent, commutative, associative — CRDT-grade). The question isn't whether these are cool math. It's whether they solve real problems that people pay money to solve.

This atlas maps 10 domains. Some are direct hits (aerospace, medical, robotics). Some are stretches (HFT, telecom). Some are honest misses we should skip. Priority rankings reflect both fit and revenue potential.

---

## 1. Aerospace / Avionics

### The Constraint Problem
DO-178C requires **traceable evidence** that every software requirement maps to verified code. Current tools (SCADE, Simulink) generate code from models but leave a gap: proving that *runtime constraints* (timing bounds, sensor ranges, actuator limits) hold under all operational conditions. Redundant flight control systems need **exact agreement** across channels — floating-point drift kills.

### How Polyformalism Applies
- **constraint_check** in 13 languages → generate certification artifacts directly from constraint specs
- **Eisenstein norm** provides exact integer arithmetic for sensor fusion bounds (no FP drift)
- **temporal snap** maps real-time deadlines to discrete lattice points — provable scheduling
- **Standards mapping already exists** (docs/standards-mapping.md: DO-178C, ISO 26262, IEC 61508, IEC 62304)
- AVX2 at 3.85B ops/s means constraint overhead is negligible even on legacy flight hardware

### State of the Art
- **ANSYS SCADE Suite** — model-based development, DO-178C certified, $50K+/seat
- **Esterel Technologies (now ANSYS)** — synchronous language compilers
- **LDRA** — static/dynamic analysis, DO-178B/C tool qualification
- **MathWorks Simulink/Stateflow** — de facto standard, generates C code
- **Wind River VxWorks** — RTOS with DO-178C certification evidence

### Competitive Advantage
Our edge isn't replacing SCADE — it's providing the **mathematical proof layer underneath**. When SCADE generates "check sensor value is between X and Y," we provide the discrete manifold that makes that check *exact and provable* at integer precision. No FP fuzziness in certification artifacts. That's a **certification cost reducer**, not a tool replacement.

### TAM
- DO-178C tool market: ~$800M globally (2025)
- Formal verification for safety-critical: ~$2.1B (growing 12% CAGR)
- Avionics software market: ~$15B

### Key Competitors
ANSYS SCADE, MathWorks, LDRA, Rapita Systems, AdaCore (SPARK/Ada)

### Implementation Complexity
**18-24 months** to DO-178C Tool Qualification Level 1 (TQL-1). The math is proven; the certification paperwork is the bottleneck.

### Priority: **9/10** — Our strongest fit. Standards mapping already written. Exact arithmetic + certification evidence is a real pain point.

---

## 2. Autonomous Vehicles

### The Constraint Problem
Perception pipelines have **no formal safety bounds**. A lidar point cloud gets processed through 15 neural network layers and nobody can prove the output is within tolerance. Motion planning generates trajectories that satisfy *soft* constraints (cost functions) but not *hard* constraints (physical impossibility). ISO 26262 requires ASIL-D evidence for safety-critical functions.

### How Polyformalism Applies
- **Intent-directed compilation** (from our paper stack) → compile perception constraints into runtime guards
- **Eisenstein lattice** for lidar point cloud alignment — lattice packing gives provable minimum-separation guarantees between detected objects
- **constraint_check** as runtime monitor on perception outputs (is this bounding box physically possible?)
- **Holonomy checking** — verify that sensor fusion doesn't accumulate angular drift over time
- **Temporal snap** for real-time deadline enforcement in planning loops

### State of the Art
- **Aptiv/Autonomous stuff** — custom C++ with ad-hoc bounds checking
- **NVIDIA DriveOS** — hardware + software stack, no formal constraint layer
- **Mobileye RSS** — Responsibility-Sensitive Safety model (mathematical but not discrete)
- **Waymo/Openpilot** — empirical testing, not formal verification
- **dSpace/Autonomous** — HIL simulation, no runtime constraint proving

### Competitive Advantage
RSS is the closest competitor (mathematical safety model). But RSS is *continuous* — it uses real arithmetic with epsilon tolerances. Our discrete lattice gives **exact** safety bounds. No "is 0.001 within tolerance?" debates. The AV industry is desperate for something certifiable and our approach is certifiable by construction.

### TAM
- ADAS/AV software market: ~$12B (2025), projected $35B (2030)
- ISO 26262 tool market: ~$1.5B
- AV safety validation: ~$3B (growing 25% CAGR)

### Key Competitors
Mobileye (RSS), NVIDIA (DriveOS), dSpace, TTTech (MotionWise), Parallel Domain (simulation)

### Implementation Complexity
**12-18 months** for perception constraint monitor. No certification required for initial product (tool, not safety element). Full ASIL-D qualification: 24-36 months.

### Priority: **8/10** — Strong fit, massive market, but longer sales cycle. The RSS-vs-discrete-lattice comparison paper alone would generate buzz.

---

## 3. Medical Devices

### The Constraint Problem
FDA 510(k) and de novo pathways require **safety cases** — structured arguments that a device is safe. Software-as-a-Medical-Device (SaMD) under IEC 62304 needs traceability from requirements through verification. Drug delivery pumps have killed people due to software errors (Therac-25, infusion pump recalls). Surgical robots need **workspace boundary enforcement** — the robot arm must never enter forbidden volumes.

### How Polyformalism Applies
- **constraint_check** generates verification artifacts directly from safety requirements
- **Eisenstein workspace bounds** for surgical robot joint limits — discrete lattice of valid configurations
- **OpenArm connection** — if Casey's fleet has any robotics work, constraint theory provides the safety envelope
- **Bloom merge** for multi-sensor medical monitoring — merge readings from different devices without drift
- **Standards mapping exists** — IEC 62304 coverage in our docs
- Drug delivery: volumetric constraints as integer arithmetic (no FP dosing errors)

### State of the Art
- **Medtronic** — proprietary safety systems, massive regulatory moat
- **Intuitive Surgical** — da Vinci system, custom safety controllers
- **LDRA/TÜV** — IEC 62304 tool qualification
- **MathWorks** — Simulink for medical device model-based design
- **Kinema (acquired)** — surgical robot safety

### Competitive Advantage
The FDA doesn't care about your framework. They care about **evidence**. Our approach generates evidence as a byproduct of the constraint system — every check produces an artifact. That reduces 510(k) preparation time and cost. For surgical robots specifically, Eisenstein lattice workspace bounds are novel — nobody else is doing discrete geometric safety envelopes.

### TAM
- Medical device software market: ~$8B (2025)
- Surgical robotics: ~$6B (growing 18% CAGR)
- FDA 510(k) consulting/services: ~$2B

### Key Competitors
Intuitive Surgical, Medtronic, J&J (Ottava), Stryker (Mako), LDRA, Jama Software (requirements traceability)

### Implementation Complexity
**24-36 months** for FDA-recognized tool qualification. The FDA path is slower than DO-178C because each device type needs separate validation.

### Priority: **7/10** — Real fit, but regulatory moats protect incumbents and slow adoption. Better as a consulting/service play than a product play initially.

---

## 4. Maritime / Oceanographic

### The Constraint Problem
Sonar beamforming requires **precise phase alignment** across hydrophone arrays. AUVs (Autonomous Underwater Vehicles) navigate by dead reckoning + acoustic positioning — both accumulate errors. Sensor fusion between IMU, DVL (Doppler Velocity Log), and acoustic positioning has no formal error bounds. The marine-gpu-edge project already exists in our stack.

### How Polyformalism Applies
- **Sonar beamforming** — Eisenstein lattice for phase alignment (beams are angular, lattice gives exact phase relationships)
- **AUV navigation** — constraint accumulation as lattice walk (holonomy measures drift)
- **Sensor fusion** — bloom merge for combining IMU/DVL/acoustic readings without floating-point accumulation
- **marine-gpu-edge** — already in our ecosystem, GPU acceleration of constraint operations
- **Temporal snap** for acoustic signal timing (sound speed in water varies with temperature/salinity)

### State of the Art
- **Kongsberg Maritime** — dominates AUV/sonar (HUGIN, REMUS)
- **Teledyne RD Instruments** — DVL sensors and processing
- **RESON/Teledyne** — multibeam sonar systems
- **WHOI/Scripps** — open-source acoustic processing tools
- **QPS (Quality Positioning Services)** — hydrographic software

### Competitive Advantage
Marine is a niche where **GPU-accelerated exact arithmetic** would be genuinely novel. Nobody is doing lattice-based sonar beamforming. The marine-gpu-edge connection gives us a real deployment story. However, the market is small and dominated by Kongsberg (Norwegian defense conglomerate).

### TAM
- Marine electronics market: ~$5B
- AUV/ROV market: ~$3B (growing 15% CAGR)
- Sonar processing software: ~$800M

### Key Competitors
Kongsberg, Teledyne, Thales (underwater systems), Atlas Elektronik, SAAB Seaeye

### Implementation Complexity
**6-12 months** for a sonar beamforming prototype. No certification required for research/oceanographic tools.

### Priority: **5/10** — Cool technical fit, small market, one dominant player. Worth a demo/paper but not a business.

---

## 5. Robotics / Manufacturing

### The Constraint Problem
6-DOF robot arms have **joint limits, workspace bounds, and singularity constraints** that must be enforced in real-time. Collaborative robots (cobots) need **proximity constraints** — stop within milliseconds if a human enters the safety zone. PLC safety interlocks are currently implemented as ad-hoc ladder logic with no formal guarantees. ISO 10218 / TS 15066 define safety requirements but leave implementation to integrators.

### How Polyformalism Applies
- **Eisenstein workspace bounds** — joint configurations map to a discrete lattice of valid positions
- **constraint_check at 3.85B ops/s** — overhead is zero for real-time safety enforcement
- **Bloom merge** for multi-robot coordination — merge occupancy grids without conflicts
- **Laman graph theory** (from our hex lattice work) — rigidity checking for multi-arm systems
- **Adaptive deadband** (ct-core-ext) — tolerance varies with speed/position automatically

### State of the Art
- **FANUC/ABB/KUKA** — proprietary safety controllers, high integration cost
- **Universal Robots** — collaborative robots with built-in safety (force limits)
- **ROS2/MoveIt2** — open-source planning, no formal safety guarantees
- **Pilz** — safety PLCs and safe robotics systems
- **Siemens Sinumerik** — CNC safety functions

### Competitive Advantage
MoveIt2 has **zero** formal safety guarantees. It uses sampling-based planners that are "probably fine." Our approach gives **provable** workspace bounds. For cobots specifically, TS 15066 requires speed/separation monitoring — our constraint system can check separation constraints deterministically, not probabilistically.

The Laman rigidity connection is genuinely novel. Nobody in robotics is using rigidity theory for multi-arm coordination.

### TAM
- Industrial robot controller market: ~$4B
- Collaborative robot market: ~$2B (growing 30% CAGR)
- Safety PLC market: ~$1.5B
- Robot safety systems: ~$800M

### Key Competitors
FANUC, ABB, KUKA, Universal Robots, Pilz, SICK (safety sensors), ROS2/MoveIt2

### Implementation Complexity
**6-12 months** for a ROS2 plugin that provides constraint-checked planning. **18-24 months** for ISO 10218 safety-certified version.

### Priority: **8/10** — Strong fit, growing market, open-source ecosystem (ROS2) makes distribution easy. The MoveIt2 plugin strategy is the wedge.

---

## 6. Finance / HFT

### The Constraint Problem
High-frequency trading requires **nanosecond timestamp alignment** across exchanges. Order books have **consistency constraints** (no negative positions, price-time priority). Risk limits must be checked in microseconds. All of this is currently done with floating-point arithmetic and ad-hoc checks.

### How Polyformalism Applies
- **Temporal snap** — align timestamps from different exchanges to a discrete lattice
- **Constraint checking** — exact integer arithmetic for risk limit verification (no FP rounding on money)
- **Bloom merge** — merge order book snapshots from different venues

### Honest Assessment
**This is a stretch.** HFT firms already have custom FPGA solutions that run at nanosecond latency. Our constraint_check at 3.85B ops/s is fast for software but glacial compared to hardware. The timestamp alignment problem is real but the solution is PTP (Precision Time Protocol) hardware, not lattice math. Risk limits are already done in fixed-point arithmetic (everyone knows not to use float for money).

### State of the Art
- **Exegy/Redline Trading** — FPGA-based ticker plants
- **Virtu Financial** — proprietary systems
- **Aerospike/Redis** — in-memory data stores
- **FIX protocol** — standard for order routing
- **Co-location services** — solve latency at the physical layer

### Competitive Advantage
Minimal. HFT is a hardware problem, not a math problem. The bloom merge for multi-venue order books is mildly interesting but not a differentiator.

### TAM
- Trading technology market: ~$10B
- Market data/infrastructure: ~$5B

### Key Competitors
Exegy, Redline, Exanet, Pico (Corvil), Vela Trading

### Implementation Complexity
**3-6 months** for a prototype, but nobody would buy it.

### Priority: **2/10** — Force-fit. The problem is hardware latency, not constraint theory. Skip.

---

## 7. Telecommunications

### The Constraint Problem
5G beam alignment requires precise phase relationships across antenna arrays (similar to sonar, but at GHz frequencies). Frequency allocation is a **packing problem** — fit maximum non-interfering channels into limited spectrum. Network synchronization (IEEE 1588 PTP) requires sub-microsecond alignment across distributed base stations.

### How Polyformalism Applies
- **Eisenstein lattice** for frequency packing — hex lattice is the optimal 2D packing, Eisenstein (its algebraic closure) might improve frequency allocation algorithms
- **Temporal snap** for network synchronization
- **Beam alignment** — phase constraints as lattice operations (same math as sonar beamforming)

### Honest Assessment
**Moderate fit, massive incumbent moat.** Qualcomm, Ericsson, and Huawei have armies of PhDs working on beamforming algorithms. They don't need our lattice math — they have custom DSP hardware. The frequency allocation angle is interesting academically but regulators (FCC, ITU) allocate spectrum politically, not mathematically. Network sync is already solved by PTP hardware.

### State of the Art
- **Qualcomm** — Snapdragon modem platforms, custom beamforming ASICs
- **Ericsson/Nokia/Huawei** — base station hardware + software
- **Texas Instruments** — RF beamforming ICs
- **Analog Devices** — software-defined radio platforms
- **MathWorks** — Phased Array System Toolbox

### Competitive Advantage
Novel angle on beamforming (Eisenstein lattice phase alignment) but the telecom industry is notoriously hard to penetrate. Standards bodies move slowly. Best angle might be an academic collaboration or patent play.

### TAM
- 5G infrastructure market: ~$80B
- Beamforming IC market: ~$3B
- Network synchronization: ~$1B

### Key Competitors
Qualcomm, Ericsson, Nokia, Huawei, Samsung, Analog Devices, Texas Instruments

### Implementation Complexity
**12-18 months** for a beamforming prototype, **years** to standards adoption.

### Priority: **3/10** — Interesting math but terrible go-to-market. Telecom is a relationship business with 10-year sales cycles.

---

## 8. Energy Grid

### The Constraint Problem
Renewable energy forecasting has **uncertainty constraints** — how much solar/wind will be available in the next hour? Grid frequency must stay within tight bounds (60Hz ±0.5Hz in the US). Load balancing across distributed generation sources is a real-time constraint satisfaction problem. NERC compliance requires evidence of constraint enforcement.

### How Polyformalism Applies
- **Temporal snap** — map generation forecasts to discrete time steps for scheduling
- **Constraint checking** — verify grid frequency stays within bounds across all scenarios
- **Bloom merge** — aggregate distributed generation/consumption data without coordination
- **Eisenstein lattice** — potentially for phasor measurement unit (PMU) alignment

### Honest Assessment
**Moderate fit.** Grid operators already have sophisticated energy management systems (EMS) from vendors like GE, Siemens, ABB. The constraint problems are real but already well-served. The bloom merge angle for distributed energy resource (DER) aggregation is interesting — as more solar/wind comes online, merging heterogeneous data sources without a central coordinator is a growing pain point.

### State of the Art
- **GE Vernova** — grid management software
- **Siemens Energy** — grid automation
- **ABB** — grid control systems
- **OSIsoft (AVEVA)** — PI System for real-time data
- **AutoGrid (acquired by Schneider)** — DER management

### Competitive Advantage
The DER aggregation angle is the most promising. As grids decentralize, bloom merge provides **coordination-free aggregation** of generation/consumption data. This is a real problem that current centralized EMS systems struggle with.

### TAM
- Grid automation market: ~$15B
- DER management: ~$3B (growing 20% CAGR)
- Energy forecasting: ~$1.5B

### Key Competitors
GE Vernova, Siemens Energy, ABB, Schneider Electric, AutoGrid, Smarter Grid Solutions

### Implementation Complexity
**12-18 months** for DER aggregation prototype. Grid operators are conservative — full deployment takes years.

### Priority: **4/10** — The DER aggregation angle is real but the market moves slowly. Better as a component in someone else's platform.

---

## 9. Distributed Systems

### The Constraint Problem
Consensus protocols (Raft, Paxos) require **agreement** among distributed nodes. CRDTs (Conflict-free Replicated Data Types) provide eventual consistency but have limited type expressiveness. Distributed lock timing is a coordination nightmare. Cross-datacenter replication has consistency/dimensionality tradeoffs (CAP theorem).

### How Polyformalism Applies
- **Holonomy** — measure the "angular deficit" of a distributed consensus round (did we come back to the same state?)
- **Bloom merge** — already proven as a CRDT merge operation (idempotent, commutative, associative)
- **Eisenstein lattice** — state space as a lattice structure for ordering distributed events
- **Constraint checking** — verify distributed invariants (no two nodes hold the same lock, bank balance never negative)

### Honest Assessment
**This is our second-strongest fit after aerospace.** The bloom semilattice is *literally* a CRDT merge operation — we proved it. Fleet CRDT convergence simulation showed 50 ticks to 100% across 20 nodes. The holonomy-as-consensus-measure idea is genuinely novel. The problem is that the distributed systems community has strong NIH syndrome and prefers Go/Rust libraries from CNCF projects.

### State of the Art
- **Redis/Valkey** — distributed locks
- **CockroachDB** — distributed SQL with Raft consensus
- **TiDB** — distributed database
- **Riak (Basho, defunct)** — CRDT pioneer
- **Automerge** — CRDT library for collaborative apps
- **Yjs** — CRDT for collaborative editing

### Competitive Advantage
Automerge and Yjs have CRDTs but only for specific data types (text, JSON, counters). Our bloom merge is a **general-purpose semilattice merge** that works on any constraint structure. The fleet simulation proves convergence. The holonomy metric for consensus health is novel — nobody else has a mathematical measure of "how healthy is my consensus round?"

### TAM
- Distributed database market: ~$25B
- Consensus/coordination services: ~$3B
- CRDT libraries: emerging market, ~$200M

### Key Competitors
Cockroach Labs, Redis Labs, Automerge (Martin Kleppmann), Yjs, Cloudflare (Durable Objects)

### Implementation Complexity
**3-6 months** for a Rust CRDT library based on bloom merge. **6-12 months** for production-grade distributed consensus plugin.

### Priority: **7/10** — Strong technical fit, but the market is crowded with well-funded competitors. Best as an open-source library play to build credibility.

---

## 10. Game Development

### The Constraint Problem
Multiplayer games need **state synchronization** across clients with different latencies. Physics engines have constraint solvers (Verlet integration, Jacobian methods) that are good but not provably correct. Network clock alignment is the same temporal sync problem we see everywhere. The Narrows demo (if it exists in fleet) would be a concrete demonstration.

### How Polyformalism Applies
- **Temporal snap** — align game state timestamps to a discrete tick lattice
- **Bloom merge** — merge state updates from multiple clients without central server
- **Constraint checking** — verify physics invariants (no tunneling, energy conservation)
- **Eisenstein lattice** — spatial partitioning for collision detection (lattice-structured spatial hash)

### Honest Assessment
**Low-moderate fit.** Game physics constraints are already well-solved by PhysX, Havok, and Bullet. Multiplayer sync is solved by deterministic lockstep (fighting games) or server-authoritative models (FPS games). The bloom merge for peer-to-peer state sync is interesting for indie games that can't afford dedicated servers, but this is a small niche.

The Narrows demo would be valuable as a **marketing tool** — "look, constraint theory makes multiplayer sync easy" — but not as a revenue generator.

### State of the Art
- **Unity/Unreal** — built-in multiplayer (Netcode for GameObjects, Unreal replication)
- **Photon Engine** — multiplayer backend
- **PlayFab (Microsoft)** — game services
- **Nakama (Heroic Labs)** — open-source game server
- **Riot/Valve custom engines** — proprietary deterministic lockstep

### Competitive Advantage
Minimal for AAA studios. Possible niche for indie P2P multiplayer games. Best value is as a demo/portfolio piece.

### TAM
- Game engine market: ~$4B
- Multiplayer backend services: ~$2B
- Indie game development tools: ~$500M

### Key Competitors
Unity, Epic (Unreal), Photon, Nakama, Mirror (Unity networking)

### Implementation Complexity
**3-6 months** for a multiplayer sync demo. **6-12 months** for a usable library.

### Priority: **3/10** — Good demo material, not a business. Games have the lowest willingness-to-pay for infrastructure tools.

---

## Summary Rankings

| # | Domain | Priority | Fit | TAM | Complexity | Verdict |
|---|---------|----------|-----|-----|------------|---------|
| 1 | **Aerospace/Avionics** | **9/10** | 🔥🔥🔥 | $15B | 18-24mo | **Pursue immediately.** Standards mapping exists. |
| 2 | **Robotics/Manufacturing** | **8/10** | 🔥🔥🔥 | $8B | 6-12mo | **Pursue.** ROS2 plugin as wedge. |
| 3 | **Autonomous Vehicles** | **8/10** | 🔥🔥 | $35B | 12-18mo | **Pursue.** Write the RSS-vs-lattice paper first. |
| 4 | **Distributed Systems** | **7/10** | 🔥🔥 | $25B | 3-6mo | **Open-source library play.** Credibility builder. |
| 5 | **Medical Devices** | **7/10** | 🔥🔥 | $16B | 24-36mo | **Consulting/service play.** Slow but lucrative. |
| 6 | **Maritime/Oceanographic** | **5/10** | 🔥 | $9B | 6-12mo | **Paper + demo.** Not a business. |
| 7 | **Energy Grid** | **4/10** | 🔥 | $19B | 12-18mo | **Component play.** DER aggregation niche. |
| 8 | **Telecommunications** | **3/10** | ⚡ | $80B | 12-18mo | **Skip.** Moats too thick. |
| 9 | **Game Development** | **3/10** | ⚡ | $6B | 3-6mo | **Demo only.** No revenue path. |
| 10 | **Finance/HFT** | **2/10** | ❌ | $15B | 3-6mo | **Skip.** Hardware problem, not math. |

---

## Recommended Strategy

### Phase 1: Prove It (Months 1-6)
1. **Aerospace POC** — Build a DO-178C constraint-checking plugin that generates certification artifacts. Show it to an avionics shop.
2. **ROS2 Constraint Plugin** — Open-source MoveIt2 plugin with Eisenstein workspace bounds. Gets us users and citations.
3. **CRDT Library** — Rust crate based on bloom merge. Publish on crates.io. Write a blog post about holonomy-as-consensus-health.
4. **Write the paper** — "Discrete Constraint Lattices for Safety-Critical Systems" targeting EMSOFT/LCTES.

### Phase 2: Revenue (Months 6-18)
1. **Avionics consulting** — Help shops reduce DO-178C certification costs using our tools
2. **Robotics safety certification** — ISO 10218 compliance tooling
3. **AV safety argument** — Approach AV companies with the lattice-vs-RSS comparison
4. **Medical device pilot** — Partner with a surgical robotics company on workspace bounds

### Phase 3: Platform (Months 18-36)
1. **Certified tool chain** — DO-178C TQL-1, IEC 62304, ISO 26262 tool qualification
2. **Cloud API** — Constraint checking as a service for distributed systems
3. **Hardware IP** — Eisenstein lattice operations as FPGA/ASIC IP blocks

---

## Honest Gaps

Things we're NOT good at (and should stop pretending):
- **Anything requiring sub-nanosecond latency** — That's hardware, not math
- **Markets dominated by 3 players** (Qualcomm, Kongsberg, etc.) — relationships beat algorithms
- **Consumer-facing products** — Nobody cares about provable constraints in their phone
- **Machine learning training** — Our constraint checking is for inference/verification, not gradient descent
- **General-purpose programming** — We're a domain-specific tool, not a language

---

*Research compiled by Forgemaster ⚒️ · Based on fleet knowledge base, constraint-theory-ecosystem docs, polyformalism benchmarks, and honest market assessment.*
