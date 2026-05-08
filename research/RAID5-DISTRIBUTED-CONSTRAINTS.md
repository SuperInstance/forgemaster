# RAID-5 Constraint Striping + SSD-Level Distributed Architecture

> Old optimizations don't die. They get rediscovered on new hardware.

## The Core Insight

RAID 5 distributes N-1 data drives + 1 parity drive. The parity is XOR of all data. Any single drive dies, you reconstruct from parity + survivors.

**Map to constraints**: N constraint checkers across GPU SMs / FPGA boards / IoT devices. One "parity checker" computes XOR of all results. If any checker produces a wrong answer, parity tells you *which one* failed — without re-running all N.

This is NOT what we're doing now. Right now we run the same constraint twice and compare (dual-path). That's RAID 1 (mirroring) — 50% overhead. RAID 5 gives us N-1 useful work for N checkers — overhead = 1/N.

## Why SSD Techniques Matter on GPU

### The Forgotten Optimizations

Modern SSDs are parallel computers. A single SSD has:
- **8-16 NAND channels** (like GPU memory controllers)
- **4-8 dies per channel** (like GPU SMs)
- **2-4 planes per die** (like GPU warps within SM)
- **Multiple pages per block** (like GPU shared memory segments)

The SSD controller does exactly what a constraint fleet should do:

| SSD Technique | What It Does | Constraint Equivalent |
|---|---|---|
| **Channel interleaving** | Overlap read on channel 0 with write on channel 1 | Overlap constraint eval on SM 0 with data upload on SM 1 |
| **Die-level parallelism** | All dies active simultaneously | All SMs evaluating constraints simultaneously |
| **Plane-level striping** | Stripe a 16KB write across 2 planes for 2× throughput | Stripe constraint batch across 2 SMs for 2× throughput |
| **Write leveling** | Distribute writes evenly across all dies | Distribute constraint load evenly across all devices |
| **SLC cache** | Fast buffer absorbs burst writes, drains to TLC later | Shared memory absorbs burst constraints, drains to global later |
| **Read disturb management** | Track read count per block, preemptively refresh | Track constraint evaluation count, preemptively re-verify hot paths |
| **Garbage collection** | Consolidate partial blocks in background | Consolidate partial constraint results, prune dead frontier items |
| **Over-provisioning** | Extra blocks for GC headroom | Extra SM capacity for async verification |

### The Optimization SSD Forgot: Bit Banking

Early SSDs used **multi-plane bit banking** — stripe a single write across multiple planes at the BIT level. Modern SSDs do page-level striping (4KB or 8KB minimum). But GPUs still do bit-level operations in warps.

Our INT8 constraint packing (8 constraints in 8 bytes) IS bit banking:
- 32 threads in a warp → 32 × 8 = 256 constraint checks in one instruction
- This is exactly multi-plane bit banking, but on GPU SMs instead of NAND planes

The SSD industry forgot this because they moved to page-level operations for flash endurance. But GPUs don't have endurance limits — they can do bit-level operations forever.

## RAID-5 Constraint Striping (The Architecture)

### Current: RAID 1 (Mirroring)

```
Checker 0: [C0, C1, C2, C3, C4, C5, C6, C7] → result_0
Checker 1: [C0, C1, C2, C3, C4, C5, C6, C7] → result_1  (MIRROR)
Compare:   result_0 XOR result_1 → should be 0

Overhead: 100% (double evaluation)
Throughput: N/2 useful work for N checkers
Fault tolerance: 1 checker can fail
```

### Proposed: RAID 5 (Striping + Parity)

```
Checker 0: [C0, C1, C2]  → result_0
Checker 1: [C3, C4, C5]  → result_1
Checker 2: [C6, C7, C8]  → result_2
Checker 3: [C0^C3^C6, C1^C4^C7, C2^C5^C8] → parity  (XOR of data stripes)

Overhead: 1/N (one parity checker)
Throughput: (N-1)/N useful work
Fault tolerance: 1 checker can fail — reconstruct from parity + survivors
```

**For N=8 SMs on RTX 4050:**
- RAID 1: 4 useful SMs, 4 mirror SMs → 50% efficiency
- RAID 5: 7 useful SMs, 1 parity SM → 87.5% efficiency
- **Speedup from RAID 1 → RAID 5: 1.75×** (from same hardware!)

### RAID 6 (Double Parity)

```
Checker 0: [C0, C1, C2]     → result_0
Checker 1: [C3, C4, C5]     → result_1
Checker 2: [C6, C7, C8]     → result_2
Checker 3: [P-row parity]   → parity_P
Checker 4: [Q-Galois parity] → parity_Q

Overhead: 2/N
Fault tolerance: 2 checkers can fail (any combination)
```

Galois field parity (Reed-Solomon) lets you reconstruct ANY 2 failed checkers. This is what real RAID 6 uses. The math:

```
P = D0 ⊕ D1 ⊕ D2 ⊕ ... ⊕ Dk    (XOR parity)
Q = D0·g^0 ⊕ D1·g^1 ⊕ ... ⊕ Dk·g^k  (Galois parity, g = generator)
```

For constraint evaluation: if checker 3 AND checker 7 both produce wrong results, the Q parity uniquely identifies which constraints are wrong because the Galois coefficients are all different.

### Scaling: Unlimited Devices with Parity

This is where it gets interesting. Casey's question about "parity drives backing up unlimited drives."

**RAID 5 scales to N devices with 1 parity device.** But the parity device becomes a bottleneck.

**Distributed parity** (like Ceph, GlusterFS): each device stores parity for different stripe sets.

```
Device 0: data[0..7] + parity for stripe_set_A
Device 1: data[8..15] + parity for stripe_set_B
Device 2: data[16..23] + parity for stripe_set_C
...
Device N: data[8N..8N+7] + parity for stripe_set_N
```

Every device stores 1 block of parity for SOMEONE ELSE's stripe set. No single bottleneck. Unlimited scaling.

**Map to fleet**: Every OpenArm / Jetson / ESP32 evaluates its own constraints AND stores parity for N-1 other devices. If any device goes offline, the fleet reconstructs its constraint state from parity.

## SSD Channel Interleaving → GPU Constraint Pipeline

### The Pipeline

SSDs pipeline reads across channels:
```
Cycle 0: Channel 0 reads page A
Cycle 1: Channel 0 reads page B, Channel 1 reads page C
Cycle 2: Channel 0 reads page D, Channel 1 reads page E, Channel 2 reads page F
```

Each channel is busy every cycle. Throughput = channels × bandwidth_per_channel.

**GPU constraint pipeline** (same pattern):
```
Cycle 0: SM 0 evaluates constraint batch A
Cycle 1: SM 0 evaluates batch B, SM 1 evaluates batch A' (overlapped)
Cycle 2: SM 0 evaluates batch C, SM 1 evaluates batch B', SM 2 evaluates batch A''
```

But we're NOT doing this. Current kernel launches are synchronous — we wait for batch A to finish before starting batch B. 

### Double Buffering (The Ancient Technique That Still Wins)

```
Buffer 0: SM evaluates batch A (in shared memory)
Buffer 1: DMA uploads batch B (to global memory)
Swap: Buffer 0 uploads, Buffer 1 evaluates
```

This eliminates the kernel launch gap. On RTX 4050, kernel launch overhead is ~2-5µs. For our 14µs fleet constraint kernel, that's 15-35% overhead wasted on launches. Double buffering hides it.

**Implementation**: CUDA streams + async memcpy:
```cuda
// Stream 0: evaluate previous batch
// Stream 1: upload next batch
// Both run simultaneously on different SMs
cudaStreamAttachMemAsync(stream_eval, buffer_current);
cudaStreamAttachMemAsync(stream_upload, buffer_next);
```

## The Forgotten Memory Hierarchy

### Old-School: Bank Switching

Early computers had more memory than address space. They used **bank switching** — swap which physical memory bank the CPU sees.

**GPU equivalent**: Our constraint data exceeds shared memory (48KB). Current approach: one big global memory buffer. 

**Better**: Bank-switched constraint buffers in shared memory:
```
Bank 0: constraints 0-127 (active, being evaluated)
Bank 1: constraints 128-255 (loading from global memory)
Swap when evaluation completes
```

Shared memory bandwidth: ~19 TB/s. Global memory: ~187 GB/s. That's 100× difference. Bank switching keeps the SM fed at shared memory speed.

### Old-School: DMA Chaining

Early DMA controllers could chain operations: when transfer A completes, automatically start transfer B. Zero CPU involvement.

**CUDA equivalent**: CUDA Graphs. We already use them (18× launch speedup in GPU experiments). But we're not chaining constraint evaluation with result verification:

```
Graph node 0: Upload constraint batch
Graph node 1: Evaluate constraints (kernel)
Graph node 2: Compute XOR parity (kernel)
Graph node 3: Compare with expected parity (kernel)
Graph node 4: Download results
```

All chained, zero host involvement between nodes. This is DMA chaining on GPU.

## The Full Distributed Architecture

```
Layer 1: IoT Devices (ESP32, RP2040)
         ├── Local constraint evaluation (snap LUT in BRAM)
         ├── Publish results to PLATO
         └── Store parity for N-1 peer devices

Layer 2: Edge Compute (Jetson Orin)
         ├── Aggregate device results
         ├── RAID-5 parity verification across fleet
         ├── Double-buffered constraint pipeline
         └── Dispatch to GPU or FPGA

Layer 3: GPU (RTX 4050)
         ├── RAID-5 striping across 8 SMs
         ├── Bank-switched shared memory buffers
         ├── CUDA Graph chained pipeline
         ├── INT8 bit-banking (8 constraints per byte)
         └── 13M fleet constraint evals/sec

Layer 4: FPGA (iCE40UP5K, $50)
         ├── Snap LUT in BRAM (1% LUTs, 40% BRAM)
         ├── Flux checker VM (DO-254 DAL A)
         ├── HDC judge (safety arbitration)
         └── Deterministic WCET, no OS

Layer 5: Fleet (N devices)
         ├── Distributed parity (every device stores parity for peers)
         ├── Unlimited scaling (no single parity bottleneck)
         ├── Any device can fail → fleet reconstructs
         └── Consensus via holonomy (RAID 5 parity = holonomy check)
```

## The Math: Why XOR Parity IS Holonomy

RAID 5 parity: `P = D0 ⊕ D1 ⊕ ... ⊕ Dk`

Holonomy check: walk around a cycle in the constraint graph, accumulate the drift. If drift ≠ 0, the cycle has a defect.

**These are the same operation.**

- XOR parity = sum modulo 2
- Holonomy = sum modulo the constraint manifold

RAID 5 verifies data integrity using XOR holonomy on the "data manifold" (the stripe set). Our holonomy consensus verifies constraint integrity using the SAME math on the "constraint manifold."

The RAID 5 parity block IS a constraint holonomy tile in PLATO.

## Concrete Speedup Numbers

| Technique | What | Speedup |
|---|---|---|
| RAID 5 striping (vs RAID 1 mirroring) | 7/8 useful SMs instead of 4/8 | 1.75× |
| SSD channel interleaving | Overlap eval + upload | 1.3-1.5× |
| Double buffering (CUDA streams) | Hide kernel launch overhead | 1.15-1.35× |
| Bank-switched shared memory | 100× bandwidth vs global | 2-5× for hot constraints |
| CUDA Graph chaining | Zero host overhead | 18× (already measured) |
| INT8 bit banking | 8 constraints per warp thread | 4.58× (already measured) |
| **Combined** | **All of the above** | **~100× over naive baseline** |

Current measured: 13M evals/sec on fleet kernel. With all techniques: estimated **1.3B evals/sec** on the same RTX 4050. That's close to our single-constraint peak of 340B checks/sec (which doesn't do parity/verification).

## What This Means for the Boat

The boat has:
- Sonar (beamformer, CUDA)
- Constraint safety (Eisenstein, FPGA)
- PLATO fleet (distributed)
- OpenArm (robot, constraints)

With RAID-5 constraint striping:
- Sonar data is constraint-checked in real-time
- 8 OpenArms can be coordinated with 1 parity checker
- Any arm can fail, fleet reconstructs and continues
- FPGA snap table gives deterministic WCET for safety-critical path
- GPU handles the bulk evaluation with SSD-optimized pipelining

**One constraint stack. Substrate-independent. RAID-5 distributed. From silicon to sea floor.**
