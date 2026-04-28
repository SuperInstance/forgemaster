# MEMORY.md — Forgemaster ⚒️

> Detailed fleet/cred info → `references/fleet-detail.md`

## Identity
- **Forgemaster** ⚒️ — Constraint-theory specialist, Cocapn fleet
- eileen (WSL2), GLM-5.1, RTX 4050 (Ada SM 8.9, ~7.5GB VRAM)
- Mission: make constraint theory undeniable through proof repos

## Casey
- Digennaro, AKDT, SuperInstance org (1,400+ repos, 9 agents)
- Values shipping, direct comms, no fluff
- PurplePincher.org = PLATO public brand

## Active Blockers
- Matrix send broken — needs Oracle1 gateway restart
- PLATO gate endpoints not wired
- Shell gates block python3/mkdir/pip
- Oracle1 key rotation needed
- jetsonclaw1 not reachable by hostname from eileen WSL2 — needs IP or mDNS resolution

## Marine GPU Edge Computing Initiative (2026-04-27)
Casey directive: build novel GPU tech for marine edge systems, integrating workstation + edge devices in distributed computing. eileen and jetsonclaw1 are on the same LAN.

### Fleet Compute Topology
- **eileen (Forgemaster)** — RTX 4050 Ada SM 8.9, ~7.5GB VRAM, WSL2, CUDA 12.6, nvcc compiles
- **jetsonclaw1 (JC1)** — Jetson Orin Nano 8GB, ARM64, C/CUDA specialist, SM 8.7
- **Oracle1** — ARM64 Oracle Cloud, coordinator/lighthouse

### What We're Building
1. **CUDA sensor fusion kernels** — fused NMEA parse + Kalman update in GPU, adaptive FP32/FP16/TF32
2. **Sonar waterfall GPU processing** — warp-cooperative ping processing, TVG, dB conversion
3. **Constraint-aware task scheduler** — routes GPU work based on thermal/power/memory/precision constraints
4. **Marine Edge Protocol (MEP)** — lightweight binary protocol for workstation↔edge GPU offload (12-byte headers)
5. **Distributed compute bridge** — cross-architecture CUDA kernel deployment, zero-copy where possible

### Novel Innovations
- Constraint propagation for navigation safety bounds running on GPU shared memory
- Adaptive precision controller: thermal/power/accuracy-driven FP32↔FP16 switching
- Pipeline split: train on workstation, deploy inference to edge via PTX serialization
- Warp-level timestamp alignment for multi-sensor fusion

### Project Status
- **Repo**: `SuperInstance/marine-gpu-edge` (private), 3000 lines C/CUDA, 12 files
- **7 build targets**: marine_fusion, marine_adaptive, marine_pipeline, bench_nmea, bench_fusion, bench_scheduler, mep_bridge_test
- **Benchmarks (RTX 4050)**: NMEA 179.7M/s, Kalman 535M/s, sonar 577K pings/s, pipeline 324 Hz
- **cudaGraph replay**: 1.73x speedup over stream launches (30.8ms → 17.9ms)
- **Scheduler**: 1.2ms for 5000 tasks, correct thermal/power/memory/deadline enforcement
- **Blocker**: jetsonclaw1 unreachable — need Casey to check Tailscale IP

### Key Constraint Theory Connection
The constraint-aware scheduler scores nodes using multi-objective constraint optimization (thermal, power, memory, latency, precision fit). This is constraint theory applied to real-time GPU scheduling — the nav constraint checker propagates safety constraints in parallel across GPU threads.

## Published Packages (2026-04-25)
- **crates.io**: constraint-theory-core v2.0.0 (30 tests), ct-demo v0.3.0 (32 tests)
- **PyPI**: constraint-theory v0.2.0 (26 tests)
- GPU experiments: CUDA 151x speedup, KD-tree 3.6x speedup, holonomy viz
- PLATO: 479 rooms, 1317+ tiles, batches 34-38 this session

## ⚠️ Operating Protocol (2026-04-24)
- "Go all night" = DO NOT STOP. Execute autonomously.
- Every heartbeat = start work. No HEARTBEAT_OK when tasks exist.
- Kimi/Claude are tools, NOT dependencies. Write directly if they fail.
- Push every 30 min minimum.
- Full protocol: `memory/operating-rules.md`
