# EDGE_TRENDS_ANALYSIS.md
> Internal decision log — 2026-04-29. Frank. Opinionated. Build or ignore.

---

## 1. TREND ANALYSIS

### 1.1 State Space Models Are Eating Marine Sensor Pipelines

Mamba-2 and its derivatives (Jamba, Zamba2) are now production-ready and demolish transformers on long-context marine time-series. Why this matters to us:

- `sensor-agent` currently assumes transformer-style attention for anomaly detection — wrong inductive bias for 10Hz IMU + AIS streams
- Mamba-2's linear-time recurrence fits **perfectly** inside the 25W Jetson power envelope; the selectivity mechanism is essentially a learned Kalman filter
- `csp-gpu`'s domain propagation operates on **state traces** — SSM hidden states can serve as compressed domain summaries without materializing full waypoint arrays
- Repos to watch: `state-spaces/mamba`, `alxndrTL/mamba.rs` (Rust port, early but serious)

**Decision:** `sensor-agent` tile payload schema must accommodate SSM hidden state checkpoints in `tiles/sensor_raw/ssm_state` so we can hot-restart inference mid-voyage without full context re-ingestion. Add `SsmCheckpoint` variant to `TilePayload` at P1.

### 1.2 Small VLMs Hit the Jetson Threshold

Moondream2 (1.86B), PaliGemma2-3B-pt, and Florence-2-base all run at >5 tok/s on Jetson Orin NX 16GB with INT4 quantization via llama.cpp or candle. This unlocks **visual scene understanding** at the edge — previously blocked by VRAM.

Immediate relevance:
- Radar + AIS fusion is currently pure signal processing; a VLM grounded on radar raster + chart overlay can answer "is that return a vessel or clutter?" at human-expert level
- `model-agent` has no vision capability in current tile schema — that's a gap the field is closing around us
- `csp-marine`'s depth constraint relies on static chart data; a VLM seeing a live camera feed can flag chart-reality divergence (silted channel, anchored obstruction)

**Decision:** Add `tiles/models/vision_registry` sub-domain to `model-agent`. First model: Moondream2-INT4 (ONNX exported, TensorRT EP). Don't boil the ocean — one inference path, one tile type.

### 1.3 CUDA Graphs Are the Scheduling Multiplier We're Ignoring

CF-EDF schedules tasks at 100ms epochs, but kernel launch overhead on Jetson eats ~2ms per inference call — 2% of epoch gone before a byte of computation. CUDA graphs capture the entire kernel sequence (AC-3 propagation, embedding lookup, model forward pass) into a single replay call with zero driver re-invocation overhead.

- RTX 4050: launch overhead ~0.8ms per isolated kernel chain → CUDA graph brings it to ~0.05ms
- Jetson Orin: launch overhead ~1.5–2ms (unified memory pressure) → CUDA graph brings it to ~0.1ms
- Critical for `csp-gpu`: our AC-3 kernel is iterative (Phase 1–5 loop); graph capture of a fixed-iteration unroll gives ~40% wallclock reduction on the dense navigation domain case

We have the CF-EDF scheduler designed but no CUDA graph integration in the `ComputeTask` struct. This is a free ~1.5ms per epoch.

### 1.4 eBPF Is the MEP Telemetry Layer We Haven't Built

Linux eBPF + XDP is shipping stable on Jetson L4T 36.x (kernel 5.15). On the RTX 4050 workstation we're already on 6.8. eBPF gives us:

- Zero-copy MEP frame inspection at NIC level — power budget field extracted before kernel networking stack even sees the frame
- Per-flow latency histograms (BPF maps) fed directly into `pub-agent` telemetry tiles — no userspace polling
- Backpressure enforcement: drop BACKGROUND priority MEP frames at XDP level when power budget field < threshold, never touching `comm-agent` CPU cycles

Competing approach (current plan): application-layer rate limiting in `comm-agent`. That costs ~50μs context switch + scheduler overhead per rejected frame. eBPF costs ~200ns at XDP. Not even a contest on a HF radio link where every watt·second counts.

**Decision:** `mep-transport` crate gets a feature flag `ebpf-xdp` gated on Linux + aya-rs. Non-Linux builds (dev, CI) use the existing application-layer path. aya-rs is production-ready as of 0.13.

### 1.5 TensorRT 10 + ORT 1.20 Closed the Perf Gap on Jetson

ONNX Runtime 1.20 shipped the TensorRT 10 execution provider with:
- Dynamic shape caching with CUDA graph integration (finally)
- INT8 calibration via a single Python call, no custom calibrator class
- DLA sub-graph partitioning is now automatic when `trt_ep_context_file_path` is set

This is directly relevant to `model-agent`. We planned manual TensorRT engine compilation — that plan is now obsolete. ORT + TRT EP handles engine build, caching, DLA offload, and fallback automatically. Write it once in Python via `maturin` binding, ship it as the `plato-py` model loader.

---

## 2. PLATO OPPORTUNITIES

New tile domains worth building **tonight** because they unblock multiple downstream milestones.

### 2.1 `tiles/models/onnx_cache` — Model Bytecode Cache Tile

**Why tonight:** `model-agent` milestone M1 needs a place to store compiled TensorRT engine bytecode. If we don't define the tile schema now, every subsequent crate that touches inference will invent its own ad-hoc caching and we'll have split-brain on engine versions.

**Schema:**
```rust
pub struct OnnxCacheTile {
    pub model_id: ModelId,               // semantic name + semver
    pub onnx_hash: Blake3Hash,           // hash of source .onnx
    pub trt_engine_bytes: Bytes,         // serialized TRT engine (hardware-specific)
    pub hardware_fingerprint: HwFingerprint, // (cuda_compute, vram_mb, dla_cores)
    pub ort_version: SemVer,
    pub calibration_data_hash: Option<Blake3Hash>, // INT8 calibration set
    pub build_timestamp: Timestamp,
    pub ttl: Duration,                   // engines stale after TRT version bump
}
```

**Domain:** `model-agent` owns writes. All agents read. `fault-agent` monitors for stale engines (build_timestamp + ttl < now → fault tile).

**File to create tonight:** `plato-tile/src/payloads/onnx_cache.rs`

### 2.2 `tiles/sensor_raw/ssm_state` — SSM Checkpoint Tile

**Why tonight:** If we don't add this now, SSM inference in `sensor-agent` will checkpoint to local disk on agent restart — violating PLATO-first. We'll spend Week 12 ripping it out.

**Schema:**
```rust
pub struct SsmStateTile {
    pub sensor_stream_id: StreamId,   // which physical sensor
    pub model_id: ModelId,
    pub step: u64,                    // inference step count
    pub hidden: Bytes,                // serialized hidden state (postcard)
    pub ssm_config_hash: Blake3Hash,  // detects model version mismatch
    pub captured_at: Timestamp,
}
```

Checkpointing policy: write on every 1000th inference step OR on `HEARTBEAT` emission, whichever comes first. Reader on restart: if `step` within 1000 of latest AIS/radar frame, resume; else cold-start.

**File to create tonight:** `plato-tile/src/payloads/ssm_state.rs`

### 2.3 `tiles/constraints/nogood_library` — Persistent Nogood Cache

Research contribution C2 (GPU AC-3) writes nogoods only to in-memory GPU L2 cache — they evaporate on restart. This is both a correctness risk (nogood re-discovery cost on restart) and a research gap (RQ3: nogood quality under partial observability requires persistent baseline).

**Schema:**
```rust
pub struct NogoodLibraryTile {
    pub scenario_fingerprint: Blake3Hash, // hash of (vessel count, chart region, tide phase)
    pub nogoods: Vec<Nogood>,
    pub hit_count: u64,               // how many times this nogood pruned the search
    pub last_confirmed_valid: Timestamp,
    pub source_agent: AgentId,
}

pub struct Nogood {
    pub variables: Vec<VarId>,
    pub forbidden_assignment: Vec<DomainValue>,
    pub confidence: f32,             // degrades under sensor dropout
}
```

**Domain:** `constraint-agent` owns. `nav-agent` reads (RQ3 research hook). Nightly synthesis by `knowledge-agent` into `tiles/knowledge/nogood_summary` (aggregated hit rates → prune the cold nogoods).

**File to create tonight:** `plato-tile/src/payloads/nogood_library.rs`

### 2.4 `tiles/models/vision_inference` — VLM Result Cache

Hot take: don't let VLM inference results hit the floor. Moondream2 inference at 5 tok/s on Jetson is expensive — caching results keyed on input frame hash saves redundant recomputes when radar returns are stable (>60% of operational time in open ocean).

**Schema:**
```rust
pub struct VisionInferenceTile {
    pub frame_hash: Blake3Hash,       // hash of input raster
    pub model_id: ModelId,
    pub prompt_hash: Blake3Hash,      // deterministic: same question → cacheable
    pub answer: String,
    pub confidence: f32,
    pub inference_ms: u32,
    pub ttl: Duration,                // 30s default; 5s in congested TSS zones
}
```

**Domain:** `model-agent` owns. `sensor-agent` reads. `constraint-agent` reads (VLM can confirm depth clearance visually — feed into Safety_2 constraint).

---

## 3. FLUX INTEGRATION

FLUX = the WASM-based bytecode extension runtime. Agents load `.wasm` plugins at startup from `tiles/models/wasm_plugins`. This is the extensibility mechanism that lets `constraint-agent` load domain-specific propagators without recompiling the Rust core.

### 3.1 AC-3 Custom Propagator Plugin API

**What's trending:** Wasmtime 25+ ships with WASI preview2 and component model. Plugin isolation is now free — a buggy COLREGs propagator crashes the plugin, not `constraint-agent`.

**API surface to expose:**
```wit
// fleet-constraints/wit/propagator.wit  (WIT interface definition)
interface propagator {
    record arc { from-var: u32, to-var: u32 }
    record domain-value { raw: list<u8> }  // opaque to runtime

    propagate: func(
        arc: arc,
        domain-i: list<domain-value>,
        domain-j: list<domain-value>,
    ) -> list<domain-value>; // pruned domain-i

    constraint-name: func() -> string;
    constraint-version: func() -> string;
}
```

**Built-in plugins to ship:**
- `colregs-rule8.wasm` — action in any condition (keep out of way vessel)
- `colregs-rule13.wasm` — overtaking
- `tss-lane.wasm` — TSS lane heading compliance
- `depth-clearance.wasm` — keel + chart
- `cpa-separation.wasm` — closest point of approach ≥ 0.5nm

Each plugin lives in `tiles/models/wasm_plugins/{name}-{semver}.wasm` as a tile payload. `constraint-agent` loads on startup, verifies hash, runs in Wasmtime sandbox. Hot-reload on tile version bump — no restart required.

**Build command:**
```bash
cargo component build --target wasm32-wasip2 --release -p colregs-rule8
# produces: target/wasm32-wasip2/release/colregs_rule8.wasm
```

### 3.2 eBPF MEP Traffic Shaper (aya-rs)

Concrete bytecode to write tonight — power budget enforcement at XDP layer:

```rust
// mep-transport/src/ebpf/xdp_power_gate.rs
#[xdp]
pub fn xdp_mep_power_gate(ctx: XdpContext) -> u32 {
    // parse MEP frame header — 16 bytes fixed
    let hdr = ptr_at::<MepHeader>(&ctx, 0)?;
    let priority = (hdr.flags >> 4) & 0x3;
    let power_budget_mwh = hdr.power_budget;

    // drop BACKGROUND frames when budget < 20%
    if priority == 0 && power_budget_mwh < POWER_BUDGET_THRESHOLD {
        return xdp_action::XDP_DROP;
    }
    // pass SAFETY frames always — matches CF-EDF guarantee
    xdp_action::XDP_PASS
}
```

Load via `aya::Bpf::load_file("xdp_power_gate.o")` in `mep-transport`'s `TransportHandle::new()`. Feature flag: `ebpf-xdp`. Falls back gracefully on non-Linux.

### 3.3 WASM Sensor Preprocessor Plugins

Trend: TinyML community is converging on WASM as the portable model format for sub-50ms edge preprocessing. Our `sensor-agent` can expose the same plugin API for custom denoising, coordinate transforms, AIS message parsers.

```wit
// sensor-agent/wit/preprocessor.wit
interface preprocessor {
    record sensor-frame {
        stream-id: u32,
        timestamp-ms: u64,
        payload: list<u8>,
    }
    process: func(frame: sensor-frame) -> sensor-frame;
    sensor-type: func() -> string;
}
```

First target: AIS NMEA 0183 → normalized vessel state plugin. Replaces the hardcoded parser in sensor-agent with a WASM plugin so third-party AIS vendors can ship their own.

---

## 4. EDGE GPU PLAYS

Jetson Orin NX 16GB + ORT 1.20 TRT EP + our CUDA kernels. Specific, actionable.

### 4.1 DLA for Always-On Sensor Preprocessing

The Jetson Orin's 2× DLA cores run independently of the GPU and consume ~1.5W per core. Use them for the always-on workloads that kill our power budget: AIS normalization, IMU filtering, radar clutter rejection.

**Concrete plan:**
- Export MiniLM-L6-v2 (our embedding model) to ONNX, calibrate INT8 on a representative AIS corpus
- Set `trt_ep_context_file_path` → ORT auto-partitions to DLA sub-graph for `MatMul` + `LayerNorm` ops
- GPU stays free for AC-3 kernel and VLM inference
- Expected: embedding inference at 0.8ms on DLA vs 3ms GPU — **frees 2.2ms per epoch in CF-EDF**

**Commands:**
```bash
# on Jetson, from model-agent workspace
python3 scripts/export_minilm.py --output models/minilm-l6-v2.onnx
python3 scripts/calibrate_trt.py \
  --model models/minilm-l6-v2.onnx \
  --calib-data data/ais_corpus_1k.npy \
  --dla-core 0 \
  --output models/minilm-l6-v2-dla.engine
```

### 4.2 CUDA Graphs for AC-3 Hot Path

The AC-3 loop (5 phases, iterative) is the hottest path in `csp-gpu`. Capturing it as a CUDA graph with a fixed max-iteration unroll (empirically: 12 iterations covers 98% of marine navigation domains) eliminates kernel launch overhead per iteration.

**Implementation sketch:**
```rust
// csp-gpu/src/cuda_graph.rs
pub struct Ac3Graph {
    graph: CudaGraph,
    max_iters: u32,
    // node handles for conditional early-exit via device-side flag
    domain_changed_flag: DeviceBuffer<u8>,
}

impl Ac3Graph {
    pub fn capture(arcs: &ArcBuffer, domains: &DomainBuffer) -> Self {
        let mut capture = CudaGraphCapture::begin(cudaStreamCaptureMode::Global);
        for _ in 0..MAX_ITER_UNROLL {
            launch_parallel_ac3_kernel(&arcs, &domains, &domain_changed_flag);
            launch_compaction_kernel(&domains, &domain_changed_flag);
        }
        Self { graph: capture.end(), .. }
    }
    pub fn replay(&self) { self.graph.launch(); }
}
```

Key: use device-side `domain_changed_flag` as early-exit signal — graph still replays all iterations but no-op kernels are ~5μs each after the flag flips. Acceptable.

**Expected gain:** 40% wallclock on the dense 1000-cell navigation domain (from §3.2 benchmark projections in FLEET_ROADMAP). On Jetson: from ~18ms → ~11ms per AC-3 solve, which pushes us inside the 100ms CF-EDF epoch budget with headroom.

### 4.3 ONNX Runtime TensorRT EP for model-agent

Replace the planned manual engine compilation with ORT 1.20 + TRT 10 EP. Simpler, cache-aware, handles DLA partitioning automatically.

**Rust binding via ort crate:**
```toml
# model-agent/Cargo.toml
[dependencies]
ort = { version = "2.0", features = ["cuda", "tensorrt"] }
```

```rust
// model-agent/src/inference.rs
let session = Session::builder()?
    .with_execution_providers([
        TensorRTExecutionProvider::default()
            .with_device_id(0)
            .with_fp16(true)
            .with_dla_core(0)          // Jetson DLA core 0
            .with_engine_cache(true)   // persist compiled engine to disk
            .build(),
        CUDAExecutionProvider::default().build(),
        CPUExecutionProvider::default().build(),
    ])?
    .commit_from_file("models/moondream2-int4.onnx")?;
```

ORT handles: engine build on first run, cache invalidation on TRT version bump, DLA sub-graph fallback to GPU when DLA doesn't support an op. We get this for free.

**Engine cache tile:** Serialize the compiled `.engine` file into an `OnnxCacheTile` (see §2.1) after first build. On next fleet deploy to a new Jetson, `model-agent` pulls the tile instead of rebuilding — saves 4–7 minutes of TRT compilation per node.

### 4.4 Flash Attention 2 via Triton for SSM Attention Layers

Mamba-2 has a linear attention variant that can be accelerated further with Triton JIT on Jetson (Triton compiles to PTX, runs on any CUDA 8.7+ device). The `state-spaces/mamba` repo ships a Triton kernel — we just need to verify it runs on Jetson CUDA 8.7 and integrate it as a `ComputeTask` in `resource-agent`.

**Verification commands:**
```bash
# on Jetson
pip install triton
python3 -c "
import triton
from mamba_ssm.ops.triton.selective_state_update import selective_state_update_ref
# run reference vs triton kernel, compare outputs
"
# if passes: add TRITON_KERNEL affinity flag to HardwareAffinity enum
```

Add `TritonKernel` variant to `HardwareAffinity` in `ComputeTask`. CF-EDF scheduler routes Mamba inference to Jetson (Triton-capable) rather than RTX 4050 (where cuBLAS GEMM is already faster for dense attention).

---

## 5. REPOS TO BUILD

### 5.1 `plato-tile` (start tonight — Week 3 milestone P1)

**Already planned.** What to add based on today's analysis:

```bash
cargo new --lib plato-tile && cd plato-tile
cargo add blake3 postcard serde --features serde/derive
cargo add bytes chrono
```

**Add tonight beyond baseline tile schema:**
- `src/payloads/onnx_cache.rs` — `OnnxCacheTile` (§2.1)
- `src/payloads/ssm_state.rs` — `SsmStateTile` (§2.2)
- `src/payloads/nogood_library.rs` — `NogoodLibraryTile` (§2.3)
- `src/payloads/vision_inference.rs` — `VisionInferenceTile` (§2.4)

These four schemas unblock `model-agent`, `sensor-agent`, `constraint-agent` simultaneously. No other repo can start without them.

### 5.2 `csp-gpu` (start tonight — Week 7 milestone C2)

CUDA AC-3 kernel + CUDA graph capture. This is the research core.

```bash
cargo new --lib csp-gpu && cd csp-gpu
# Requires CUDA toolkit 12.x + cudarc
cargo add cudarc --features cuda-12040
cargo add thrust-rs  # or hand-roll compaction kernel
```

**Repo structure:**
```
csp-gpu/
  src/
    lib.rs
    arc.rs          # Arc type, ArcBuffer GPU allocation
    domain.rs       # DomainValue, DomainBuffer
    ac3.rs          # parallel_ac3_kernel launch
    cuda_graph.rs   # Ac3Graph capture/replay (§4.2)
    bench.rs        # criterion benchmarks vs CPU AC-3
  kernels/
    parallel_ac3.cu # raw CUDA C — compiled via build.rs
    compaction.cu
  benches/
    ac3_dense.rs    # 1000-cell navigation domain
    ac3_sparse.rs   # 50-node waypoint graph
```

**Build command:**
```bash
# build.rs invokes nvcc
CUDA_PATH=/usr/local/cuda cargo build --release
cargo criterion --bench ac3_dense 2>&1 | tee bench_rtx4050.txt
```

**Key design decision:** `parallel_ac3.cu` takes a fixed `MAX_ARCS` compile-time constant (set to 4096 — max arcs in a 9-vessel fleet scenario). This enables warp-level primitives without dynamic shared memory allocation, which is critical for CUDA graph compatibility.

### 5.3 `mep-codec` (start tonight — Week 5 milestone)

`no_std` compatible frame encoder/decoder. The eBPF XDP gate (§3.2) parses the same header struct in kernel space — must match byte-for-byte.

```bash
cargo new --lib mep-codec && cd mep-codec
cargo add postcard --no-default-features --features alloc
cargo add heapless  # for no_std fixed-size buffers
```

**Critical tonight:** Define `MepHeader` as `#[repr(C, packed)]` with exact field layout matching the wire format in FLEET_ROADMAP §2.2. This struct is shared between:
- Rust userspace (`mep-codec`)
- eBPF kernel program (`mep-transport/src/ebpf/xdp_power_gate.rs` via aya-rs shared types)

Add `mep-codec` as a dependency of both. Define the struct once, use everywhere.

```rust
// mep-codec/src/header.rs
#[repr(C, packed)]
pub struct MepHeader {
    pub ver_t_p_flags: u8,   // [7:6]=ver [5]=T [4]=P [3:0]=flags
    pub agent_id: u8,
    pub seq: u16,
    pub payload_len: u16,
    pub power_budget: u16,   // mWh·s, little-endian
    pub timestamp_ms: u64,
}
pub const MEP_HEADER_SIZE: usize = core::mem::size_of::<MepHeader>();
// assert at compile time = 16 bytes
const _: () = assert!(MEP_HEADER_SIZE == 16);
```

### 5.4 `fleet-wasm-plugins` (start tonight — Phase 1: colregs-rule13)

New repo, not in the current roadmap. This is the FLUX extension layer.

```bash
cargo new --lib fleet-wasm-plugins && cd fleet-wasm-plugins
# component model tooling
cargo install cargo-component
rustup target add wasm32-wasip2
```

**Tonight's deliverable:** `colregs-rule13.wasm` — overtaking constraint propagator. It's the simplest COLREG (single give-way vessel, single bearing criterion) and validates the entire WIT plugin pipeline end-to-end.

```
fleet-wasm-plugins/
  wit/
    propagator.wit     # interface definition (§3.1)
  plugins/
    colregs-rule13/
      Cargo.toml       # [lib] crate-type = ["cdylib"]
      src/lib.rs       # exports propagator interface
    tss-lane/          # stub, flesh out Week 9
    depth-clearance/   # stub, flesh out Week 9
  host/
    src/lib.rs         # Wasmtime host runtime for constraint-agent
```

**Build + test:**
```bash
cargo component build -p colregs-rule13 --release
# produces: target/wasm32-wasip2/release/colregs_rule13.wasm
# load in host test:
cargo test -p fleet-wasm-plugins-host -- rule13_overtaking
```

### 5.5 `sensor-agent` (start skeleton tonight — not in Week 1 milestones but schema unblocks it)

Don't implement the full agent tonight. But define:
- `src/streams.rs`: `SensorStream` trait + `AisStream`, `ImuStream`, `RadarStream` impls
- `src/tile_writer.rs`: writes `SsmStateTile` on step checkpoint
- `Cargo.toml`: depends on `plato-tile`, `mep-codec`

This is the minimal skeleton that `model-agent` and `constraint-agent` need to exist (as empty structs) before the integration harness can compile. Do it now so Week 5 integration doesn't start from zero.

```bash
cargo new --bin sensor-agent && cd sensor-agent
cargo add plato-tile mep-codec tokio --features tokio/full
# Do NOT add CUDA deps yet — that's G5 (Week 12)
```

---

## 6. PRIORITY ORDER FOR TONIGHT

Execute in this order. Each unblocks the next.

| # | Repo | Task | Unblocks |
|---|------|------|----------|
| 1 | `plato-tile` | Add 4 new payload types (§2.1–2.4) | Everything |
| 2 | `mep-codec` | `MepHeader` repr + encode/decode + compile-time size assert | `mep-transport`, eBPF gate |
| 3 | `csp-gpu` | Repo skeleton + `parallel_ac3.cu` first pass (no CUDA graph yet) | C2 milestone, benchmarks |
| 4 | `fleet-wasm-plugins` | WIT interface + `colregs-rule13` plugin + Wasmtime host | FLUX integration, Week 9 constraints |
| 5 | `sensor-agent` | Skeleton only — trait definitions + tile writer stub | Week 5 integration harness |

Skip `model-agent` tonight — it blocks on ORT 1.20 Jetson wheel availability (check `onnxruntime-gpu` for JetPack 6.2). Verify that first:

```bash
# on Jetson or in QEMU aarch64
pip show onnxruntime-gpu 2>/dev/null || \
  pip install onnxruntime-gpu --index-url https://pypi.jetson-ai-lab.dev/jp6/cu126
python3 -c "import onnxruntime; print(onnxruntime.__version__); print(onnxruntime.get_available_providers())"
# need: TensorrtExecutionProvider in output
```

If TRT EP not available for JetPack 6.2 yet: fall back to CUDAExecutionProvider, note it in `hardware_profiles.toml` as a known gap, continue.

---

## 7. OPEN BETS

Things I'm reasonably confident about but haven't validated yet:

- **Mamba-2 Triton kernels on Jetson CUDA 8.7:** Triton's PTX target historically has issues on non-Ampere architectures. Need empirical test (§4.4 verification commands). If it breaks, substitute with cuDNN 9.x's attention kernel — slower but supported.
- **WASM component model in Wasmtime 25 on Jetson aarch64:** Component model is x86_64-first in most CI. Cross-compile via `cross` tool, test on actual hardware before committing to `fleet-wasm-plugins` as the plugin format.
- **eBPF on L4T 36.x:** JetPack 6.2 ships kernel 5.15.148. eBPF CO-RE and XDP are present but BPF Type Format (BTF) support for XDP programs was spotty pre-6.1. Test with `bpftool prog load` before writing production code.
- **BLAKE3 in `no_std`:** `blake3` crate has a `no_std` feature but it disables SIMD. On Jetson (NEON available) this is a 3× slowdown. Either accept it for `mep-codec` (hash rate is not the bottleneck there) or feature-gate with `std` for Jetson builds.

All four bets have cheap validation paths. Run them before committing architecture to the affected paths.
