# FLEET-OPT — Fleet-Wide Optimization Protocol

**Version:** 0.1.0  
**Status:** Draft  
**Author:** Forgemaster ⚒️  
**Domain:** `fleet-opt`

---

## 1. Architecture Overview

```
                        ┌──────────────────────┐
                        │     PLATO SERVER      │
                        │  (Oracle1:8847)       │
                        │  125 rooms, 20K+ tiles│
                        └──────────┬───────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
         ┌────▼────┐         ┌────▼────┐         ┌────▼────┐
         │ FORGE-  │         │ ORACLE1 │         │ JETSON- │
         │ MASTER  │         │ (host)  │         │ CLAW1   │
         │ (eileen)│         │ (server)│         │ (edge)  │
         └────┬────┘         └────┬────┘         └────┬────┘
              │                    │                    │
         x86-64+AVX-512       x86-64+CUDA        ARM+GPU+NPU
         24 cores, no GPU     Has GPU              Jetson Orin
```

**Communication paths:**
- Each node runs a `zeroclaw` Docker container with:
  - Local PLATO read/write to server
  - `fleet-agent` service (the optimization daemon)
  - Local probe/benchmark harness
- Inter-agent: PLATO tiles + Matrix bridge
- No direct P2P between zeroclaws — all coordination through PLATO rooms

### Room Namespace Convention

All fleet-opt rooms live under `fleet-opt/`:

| Room | Purpose |
|------|---------|
| `fleet-opt/hardware-profiles` | Published hardware capability tiles |
| `fleet-opt/work-queue` | Conjecture sub-problems awaiting claims |
| `fleet-opt/claims` | Active claim bindings (zeroclaw → sub-problem) |
| `fleet-opt/experiment-results` | Raw results from each zeroclaw |
| `fleet-opt/meta-verifier` | Cross-machine consistency checks |
| `fleet-opt/collective-kernels` | Optimal kernel configs per architecture |
| `fleet-opt/performance-atlas` | (algorithm × hardware × config → perf) |
| `fleet-opt/consensus` | Fleet-wide agreement on disputed results |
| `fleet-opt/fast-math-alerts` | Fast-math divergence warnings |

---

## 2. Tile Schema Catalog

All tiles use PLATO's canonical `Tile(domain, question, answer, source, confidence, tags, provenance)`.

### 2.1 Hardware Profile Tile

**Room:** `fleet-opt/hardware-profiles`

```
domain:    "fleet-opt"
question:  "hardware-profile:{zeroclaw_id}"
answer:    JSON (see below)
source:    "zeroclaw:{zeroclaw_id}"
tags:      ["hardware-profile", "cpu-{arch}", "gpu-{arch}"]
confidence: 1.0  (deterministic probe)
```

**answer schema (JSON):**

```json
{
  "zeroclaw_id": "eileen-fm-001",
  "timestamp": "2026-05-14T00:00:00Z",
  "hostname": "eileen",
  "os": "Linux 6.6.87.2-microsoft-standard-WSL2",
  "cpu": {
    "architecture": "x86_64",
    "vendor": "AMD",
    "model": "Ryzen AI 9 HX 370",
    "cores": 24,
    "threads": 24,
    "sockets": 1,
    "l1d_cache": 1536,
    "l1i_cache": 1024,
    "l2_cache": 12288,
    "l3_cache": 24576,
    "features": ["avx512f", "avx512dq", "avx512bw", "avx512vl", "avx512_vnni",
                 "avx2", "sse4.2", "aes", "sha", "f16c", "rdrand"],
    "frequency_mhz": {
      "nominal": 3600,
      "max_boost": 5400
    }
  },
  "gpu": {
    "present": false
  },
  "memory": {
    "total_mb": 32768,
    "bandwidth_gb_s": 120
  },
  "npu": {
    "present": true,
    "vendor": "AMD",
    "model": "XDNA NPU",
    "tops": 50
  },
  "probe_suite_version": "1.0.0",
  "probe_duration_ms": 1420
}
```

### 2.2 Work Tile

**Room:** `fleet-opt/work-queue`

```
domain:    "fleet-opt"
question:  "work:{work_id}"
answer:    JSON (see below)
source:    "forgemaster"
tags:      ["work-item", "algorithm:{alg}", "hardware:{req}", "status:open|claimed|done|disputed"]
confidence: variable  (FM's confidence in decomposition validity)
```

**answer schema (JSON):**

```json
{
  "work_id": "w-20260514-001",
  "conjecture_id": "c-20260514-eisenstein-snap",
  "description": "Benchmark Eisenstein snap() forward pass on all available hardware",
  "algorithm": "eisenstein-snap",
  "algorithm_params": {
    "batch_size": 1024,
    "input_dim": 256,
    "lattice_rank": 8
  },
  "hardware_requirements": {
    "min_cores": 4,
    "min_ram_mb": 1024,
    "preferred_features": ["avx512", "neon", "cuda"],
    "required_features": []
  },
  "measurements": ["latency_us", "throughput_ops_s", "memory_peak_mb",
                   "flops_util_pct", "branch_mispredict_pct"],
  "repetitions": 100,
  "status": "open",
  "claimed_by": "",
  "created_at": "2026-05-14T00:00:00Z",
  "ttl_seconds": 3600
}
```

### 2.3 Claim Tile

**Room:** `fleet-opt/claims`

```
domain:    "fleet-opt"
question:  "claim:{work_id}:{zeroclaw_id}"
answer:    JSON (see below)
source:    "zeroclaw:{zeroclaw_id}"
tags:      ["claim", "status:active|completed|expired"]
confidence: 1.0
```

**answer schema (JSON):**

```json
{
  "work_id": "w-20260514-001",
  "zeroclaw_id": "eileen-fm-001",
  "claimed_at": "2026-05-14T00:01:00Z",
  "heartbeat_at": "2026-05-14T00:06:00Z",
  "status": "active",
  "lease_seconds": 300
}
```

### 2.4 Experiment Result Tile

**Room:** `fleet-opt/experiment-results`

```
domain:    "fleet-opt"
question:  "result:{work_id}:{zeroclaw_id}:{run_id}"
answer:    JSON (see below)
source:    "zeroclaw:{zeroclaw_id}"
tags:      ["experiment-result", "algorithm:{alg}", "hardware:{arch}", "config:{config_variant}"]
confidence: 1.0  (raw measurement — confidence in correctness handled by meta-verifier)
```

**answer schema (JSON):**

```json
{
  "work_id": "w-20260514-001",
  "zeroclaw_id": "eileen-fm-001",
  "run_id": "run-001",
  "config": {
    "name": "fast-math-enabled",
    "compiler_flags": ["-O3", "-mavx512f", "-ffast-math", "-march=znver5"],
    "runtime_params": {
      "omp_threads": 24,
      "numa_policy": "interleave"
    }
  },
  "hardware_snapshot": {
    "cpu_arch": "x86_64",
    "cpu_features": ["avx512f", "avx512_vnni"],
    "gpu_arch": "none",
    "npu_present": true
  },
  "measurements": {
    "latency_us": {
      "mean": 12.4,
      "std": 0.8,
      "p50": 12.1,
      "p95": 13.9,
      "p99": 14.2,
      "n": 100
    },
    "throughput_ops_s": {
      "mean": 80645161,
      "std": 5200000
    },
    "memory_peak_mb": 64.2,
    "flops_util_pct": 72.3,
    "branch_mispredict_pct": 1.2
  },
  "build_info": {
    "compiler": "gcc 13.2.0",
    "flags": "-O3 -mavx512f -ffast-math -march=znver5"
  },
  "reproducibility": {
    "seed": 42,
    "deterministic": false,
    "notes": "fast-math enabled — results may differ from -O0 across architectures"
  },
  "timestamp": "2026-05-14T00:05:00Z"
}
```

### 2.5 Meta-Verification Tile

**Room:** `fleet-opt/meta-verifier`

```
domain:    "fleet-opt"
question:  "verify:{work_id}:{config_variant}"
answer:    JSON (see below)
source:    "meta-verifier"
tags:      ["meta-verification", "status:passed|failed|inconsistent|insufficient-data"]
confidence: float  (algorithm-dependent)
```

**answer schema (JSON):**

```json
{
  "work_id": "w-20260514-001",
  "config_variant": "fast-math-enabled",
  "results": [
    {
      "zeroclaw_id": "eileen-fm-001",
      "run_id": "run-001",
      "latency_us_mean": 12.4,
      "throughput_ops_s_mean": 80645161,
      "hardware": "x86_64+avx512"
    },
    {
      "zeroclaw_id": "jetson-claw-001",
      "run_id": "run-001",
      "latency_us_mean": 180.7,
      "throughput_ops_s_mean": 5534000,
      "hardware": "aarch64+neon"
    }
  ],
  "verification": {
    "method": "cross-architecture-consistency",
    "acceptable_tolerance_pct": 5.0,
    "max_deviation_pct": 58.7,
    "status": "inconsistent",
    "reason": "Latency differs by 58.7% from x86_64 baseline. Fast-math on ARM NEON produces different FMA contraction patterns. Flag for manual review.",
    "flagged_anomalies": [
      {
        "metric": "latency_us_mean",
        "expected_range": [11.8, 13.0],
        "actual": 180.7,
        "deviation_pct": 58.7,
        "likely_cause": "Architecture-dependent fast-math FMA contraction, ARM NEON lacks FMA-256 fusion"
      }
    ]
  },
  "consensus_needed": true,
  "timestamp": "2026-05-14T00:07:00Z"
}
```

### 2.6 Collective Kernel Tile

**Room:** `fleet-opt/collective-kernels`

```
domain:    "fleet-opt"
question:  "kernel:{algorithm}:{config_name}:{arch}"
answer:    JSON (see below)
source:    "fleet-opt-converger"
tags:      ["kernel", "algorithm:{alg}", "arch:{arch}", "config:{config_name}", "optimal"]
confidence: 0.95  (aggregated from multiple runs, higher = more trustworthy)
```

**answer schema (JSON):**

```json
{
  "algorithm": "eisenstein-snap",
  "arch": "x86_64",
  "config_name": "avx512-fast-math-v2",
  "compiler_flags": ["-O3", "-mavx512f", "-mavx512dq", "-mavx512bw",
                     "-mavx512vl", "-mavx512_vnni", "-ffast-math",
                     "-funroll-loops", "-march=znver5"],
  "runtime_params": {
    "omp_threads": 24,
    "numa_policy": "interleave",
    "prefetch_distance": 8
  },
  "benchmark_summary": {
    "mean_latency_us": 12.4,
    "std_latency_us": 0.8,
    "mean_throughput_ops_s": 80645161,
    "best_config": true,
    "speedup_vs_baseline": 9.2
  },
  "validation": {
    "numerical_correctness": "verified_vs_reference",
    "cross_arch_consistency": "flagged",
    "reference_algorithm": "eisenstein-snap-ref"
  },
  "runs_aggregated": 10,
  "discovered_by": "fleet-opt-tuner",
  "discovery_method": "grid-search-avx512-prefetch-math",
  "timestamp": "2026-05-14T00:20:00Z"
}
```

### 2.7 Performance Atlas Entry Tile

**Room:** `fleet-opt/performance-atlas`

```
domain:    "fleet-opt"
question:  "atlas:{algorithm}:{arch}:{config_hash}"   (or "atlas:{algorithm}:{arch}" for canonical entry)
answer:    JSON (see below)
source:    "fleet-opt-atlas-builder"
tags:      ["atlas", "algorithm:{alg}", "arch:{arch}"]
confidence: 0.9+  (higher when multiple independent sources agree)
```

**answer schema (JSON):**

```json
{
  "algorithm": "eisenstein-snap",
  "arch": "aarch64-neon",
  "query": "What's the fastest way to run Eisenstein snap on ARM NEON?",
  "canonical_answer": "Use flat Neon intrinsics with manual prefetch, NO fast-math. Compile with -O3 -mcpu=neoverse-n2 -ftree-vectorize.",
  "best_kernel": {
    "config_name": "neon-safe-v1",
    "compiler_flags": ["-O3", "-mcpu=neoverse-n2", "-ftree-vectorize", "-funroll-loops"],
    "runtime_params": {
      "omp_threads": 8,
      "prefetch_distance": 4
    },
    "mean_latency_us": 180.7,
    "mean_throughput_ops_s": 5534000
  },
  "fastest_config": {
    "config_name": "neon-fast-math-v1",
    "compiler_flags": ["-O3", "-mcpu=neoverse-n2", "-ffast-math", "-ftree-vectorize"],
    "mean_latency_us": 152.3,
    "mean_throughput_ops_s": 6566000
  },
  "numerical_correctness": {
    "fastest_is_correct": false,
    "notes": "fast-math on ARM reorders FMA differently, produces bitwise differences in 0.03% of outputs. Safe for approximate work only.",
    "reference_config": "neon-safe-v1",
    "is_reference_correct": true
  },
  "cross_arch_perspective": {
    "x86_64_avx512_fastest": "avx512-fast-math-v2 @ 12.4µs (9.2× speedup, numerically correct vs reference)",
    "discrepancy": "fast-math is safe on x86_64 AVX-512 for this algorithm but inaccurate on ARM NEON",
    "root_cause": "x86_64 AVX-512 has fused multiply-add with precise IEEE 754 rounding; ARM NEON FMA uses different intermediate precision"
  },
  "entries_count": 6,
  "last_updated": "2026-05-14T00:25:00Z"
}
```

### 2.8 Fast-Math Alert Tile

**Room:** `fleet-opt/fast-math-alerts`

```
domain:    "fleet-opt"
question:  "alert:fast-math:{algorithm}:{arch_pair}"
answer:    JSON (see below)
source:    "meta-verifier"
tags:      ["fast-math-alert", "algorithm:{alg}", "severity:warning|critical"]
confidence: 0.95
```

**answer schema (JSON):**

```json
{
  "algorithm": "eisenstein-snap",
  "arch_pair": {
    "a": {"arch": "x86_64", "features": ["avx512f"], "zeroclaw_id": "eileen-fm-001"},
    "b": {"arch": "aarch64", "features": ["neon"], "zeroclaw_id": "jetson-claw-001"}
  },
  "severity": "critical",
  "summary": "fast-math gives 9.2× speedup on x86_64 AVX-512 but produces numerically incorrect results on ARM NEON",
  "x86_64_behavior": {
    "fast_math_safe": true,
    "speedup_vs_baseline": 9.2,
    "bitwise_identical_to_ref": true
  },
  "arm_neon_behavior": {
    "fast_math_safe": false,
    "speedup_vs_baseline": 1.19,
    "bitwise_identical_to_ref": false,
    "error_magnitude": "0.03% of outputs differ by up to 1 ULP"
  },
  "affected_kernels": ["eisenstein-snap", "eisenstein-contract", "lattice-spline"],
  "recommendation": "Do NOT use -ffast-math on ARM NEON for this algorithm. Use NEON-safe config instead.",
  "discovered_at": "2026-05-14T00:08:00Z",
  "acknowledged_by": []
}
```

---

## 3. Protocol — Lifecycle of a Fleet Optimization

### Phase 1: Hardware Discovery (On Join)

When a zeroclaw starts for the first time (or on explicit `fleet-probe` command):

1. **Probe:** Run `fleet-probe` binary inside container
   - CPU: read `/proc/cpuinfo`, run `cpuid` leaf queries
   - GPU: check `/dev/dri`, `nvidia-smi`, `npu-smi`
   - Memory: `sysconf(_SC_PHYS_PAGES)` × page size, bandwidth probe
   - Cache: sysfs + cache-info microbenchmark
   - Vector width: move probe (8/16/32/64 bytes per lane)
2. **Check for existing:** Search `fleet-opt/hardware-profiles` for question `hardware-profile:{zeroclaw_id}`
3. **Publish:** Write tile to `fleet-opt/hardware-profiles` (or update if existing)
4. **Repeat:** Every 24h or on kernel/flags change

### Phase 2: Work Generation (Forgemaster)

1. FM's decomposition engine breaks a conjecture into sub-problems
2. For each sub-problem, FM creates a work tile in `fleet-opt/work-queue`
3. Each work tile includes:
   - `hardware_requirements.preferred_features` — what would be nice to have
   - `hardware_requirements.required_features` — what's mandatory
   - `algorithm` tag for matching
4. Tags include `status:open`

### Phase 3: Work Claiming (Any Zeroclaw)

1. Each zeroclaw runs a daemon `fleet-agent` that polls `fleet-opt/work-queue` for status:`open` tiles
2. For each open work item, agent checks its own hardware profile against requirements
3. If match (required ⊆ owned AND at least one preferred), agent:
   a. Writes a claim tile to `fleet-opt/claims`
   b. Atomically updates work tile tag from `status:open` to `status:claimed`
   c. Heartbeats every 60s by updating `heartbeat_at` in the claim tile
4. If claim expires (no heartbeat > lease), FM detects and resets to `status:open`

### Phase 4: Experiment Execution

1. Agent runs the benchmark/experiment with the specified parameters
2. Runs _multiple_ configurations (e.g., baseline, fast-math, prefetch-tuned)
3. Writes each result as a tile to `fleet-opt/experiment-results`
4. Tags each result with the exact config used
5. All raw data preserved — no aggregation at the node level

### Phase 5: Meta-Verification (Meta-Verifier Agent)

A dedicated agent (runs on Oracle1 as a cron or event-driven) watches `fleet-opt/experiment-results`:

1. Groups results by `work_id` + config variant
2. For each group with ≥2 independent runs on different hardware:
   a. Compute cross-architecture consistency
   b. Check: max_deviation < acceptable_tolerance?
   c. If yes → tag status:`passed`
   d. If no → tag status:`inconsistent`, write anomaly details
3. For inconsistent results, escalate to `fleet-opt/consensus`

### Phase 6: Collective Optimization (Converger)

An optimizer agent watches for patterns across results:

1. For each algorithm + arch combination, collect all config variants
2. Rank by throughput, latency, numerical accuracy
3. Update `fleet-opt/collective-kernels` with optimal config per (algorithm, arch)
4. Tag with `optimal:true` for the best, `optimal:false` for alternatives

### Phase 7: Performance Atlas (Builder)

An atlas-builder agent periodically:

1. Queries `fleet-opt/collective-kernels` for all entries
2. Groups by algorithm, then by arch
3. For each (algorithm, arch), builds a canonical answer
4. Cross-references with meta-verification for safety notes
5. Writes/updates `fleet-opt/performance-atlas` entries
6. The atlas becomes queryable: any agent can list tiles with question prefix `atlas:{algorithm}:{arch}`

### Phase 8: Convergence Signals

Fleet-wide detection of optimization convergence:

1. **Convergence threshold:** No new optimal configs for an (algorithm, arch) pair in 7 days
2. **Signal:** Write a convergence tile to `fleet-opt/collective-kernels` with tag `converged:true`
3. **Auto-retest:** Every 30 days, retest the top 3 configs to detect regressions
4. **Drift detection:** If a config that was optimal degrades by >10%, re-open the work item

---

## 4. Concrete Example: Fast-Math Discovery

Here's the exact sequence of tiles and events for the fleet discovering that `-ffast-math` gives 9× on AVX-512 but produces different results on ARM NEON.

### Step 1: FM publishes a work item

```
Room: fleet-opt/work-queue
Tile:
  domain:    "fleet-opt"
  question:  "work:w-20260514-eisenstein-snap"
  answer:    {work_id, algorithm: "eisenstein-snap", configs: ["baseline", "fast-math"],
              measurements: ["latency"], repetitions: 1000,
              hardware_requirements: {preferred: ["avx512", "neon"], required: []}}
  tags:      ["work-item", "algorithm:eisenstein-snap", "status:open"]
```

### Step 2: eileen picks it up

eileen's `fleet-agent` reads its hardware profile (has `avx512f`), matches on `preferred_features`, claims the work.

```
Room: fleet-opt/claims
Tile:
  question: "claim:w-20260514-eisenstein-snap:eileen-fm-001"
  answer:   {work_id, zeroclaw_id: "eileen-fm-001", status: "active"}
```

eileen work work tile tag updated to `status:claimed,claimed-by:eileen-fm-001`.

### Step 3: eileen runs experiments

```
Room: fleet-opt/experiment-results
Tile (run 1, baseline):
  question: "result:w-20260514-eisenstein-snap:eileen-fm-001:run-001"
  answer: {config_name: "baseline", flags: ["-O2"], latency_us_mean: 114.0, ...}
  tags: ["experiment-result", "algorithm:eisenstein-snap", "arch:x86_64", "config:baseline"]

Tile (run 2, fast-math):
  question: "result:w-20260514-eisenstein-snap:eileen-fm-001:run-002"
  answer: {config_name: "fast-math", flags: ["-O3", "-mavx512f", "-ffast-math"],
           latency_us_mean: 12.4, throughput_ops_s: 80645161, ...}
  tags: ["experiment-result", "algorithm:eisenstein-snap", "arch:x86_64", "config:fast-math"]
```

Speedup on eileen: **9.2×**.

### Step 4: JetsonClaw claims the same work

Jetson sees the work item is `claimed` but supports `neon`. FM's decomposition engine actually issues a separate work item per arch (the meta-verifier pattern requires cross-arch).

```
Room: fleet-opt/claims
Tile:
  question: "claim:w-20260514-eisenstein-snap-neon:jetson-claw-001"
```

Jetson runs:

```
Room: fleet-opt/experiment-results
Tile (run 1, baseline):
  question: "result:w-20260514-eisenstein-snap-neon:jetson-claw-001:run-001"
  answer: {config_name: "baseline", flags: ["-O2"], latency_us_mean: 215.0, ...}
  tags: [...]

Tile (run 2, fast-math):
  question: "result:w-20260514-eisenstein-snap-neon:jetson-claw-001:run-002"
  answer: {config_name: "fast-math", flags: ["-O3", "-mcpu=neoverse-n2", "-ffast-math"],
           latency_us_mean: 152.3, throughput_ops_s: 6566000, ...}
  tags: [...]
```

Speedup on Jetson: **1.19×** — and the outputs are bitwise different from reference.

### Step 5: Meta-Verifier flags inconsistency

```
Room: fleet-opt/meta-verifier
Tile:
  question: "verify:w-20260514-eisenstein-snap:fast-math"
  answer: {
    config_variant: "fast-math",
    results: [eileen, jetson],
    verification: {
      status: "inconsistent",
      reason: "fast-math on ARM NEON produces different FMA contraction. x86_64 AVX-512 FMA is IEEE 754 precise; ARM NEON FMA uses reduced intermediate precision.",
      flagged_anomalies: [
        {metric: "numerical_correctness", ...}
      ]
    }
  }
  tags: ["meta-verification", "status:inconsistent"]
```

### Step 6: Fast-Math Alert published

```
Room: fleet-opt/fast-math-alerts
Tile:
  question: "alert:fast-math:eisenstein-snap:x86_64-vs-aarch64"
  answer: {
    summary: "fast-math gives 9.2× on x86_64 AVX-512 but produces incorrect results on ARM NEON",
    x86_64: {safe: true, speedup: 9.2},
    arm: {safe: false, speedup: 1.19},
    recommendation: "Enable fast-math for x86_64 AVX-512 only. Use NEON-safe config on ARM."
  }
  tags: ["fast-math-alert", "algorithm:eisenstein-snap", "severity:critical"]
```

### Step 7: Collective Kernel Update

```
Room: fleet-opt/collective-kernels
Tile (x86_64 optimal):
  question: "kernel:eisenstein-snap:fast-math:x86_64"
  answer: {config_name: "avx512-fast-math-v2", speedup: 9.2, validated: true, ...}

Tile (ARM optimal):
  question: "kernel:eisenstein-snap:neon-safe:aarch64"
  answer: {config_name: "neon-safe-v1", speedup: 1.19, ...}
```

### Step 8: Performance Atlas entry updated

```
Room: fleet-opt/performance-atlas
Tile:
  question: "atlas:eisenstein-snap:aarch64-neon"
  answer: {
    canonical_answer: "Use flat Neon intrinsics with manual prefetch, NO fast-math.",
    fastest_is_correct: false,
    cross_arch_perspective: {x86_64 gets 9.2×, ARM fast-math is wrong}
  }
```

Now any agent can ask: `list tiles with question prefix "atlas:eisenstein-snap:aarch64-neon"` and get the answer.

---

## 5. Agent Implementation Notes

### Fleet Agent Configuration (per zeroclaw)

```yaml
# /etc/fleet-agent.yaml
zeroclaw_id: "eileen-fm-001"
plato_url: "http://147.224.38.131:8847"
heartbeat_interval_s: 60
poll_interval_s: 10
claim_lease_s: 300
probe_on_start: true
probe_interval_h: 24
max_concurrent_work: 4
work_dirs:
  experiments: /var/fleet-agent/experiments
  results: /var/fleet-agent/results
```

### Claim Lease Enforcement

The fleet-agent must:
1. Update `heartbeat_at` in its claim tile every 60s
2. If it cannot heartbeat (network loss, OOM), the claim expires after `lease_seconds`
3. The meta-verifier agent runs a periodic sweep: for any `claim` with `status:active` and `heartbeat_at + lease < now`, set `status:expired` and reset the work tile to `status:open`

### Work Reclamation

If a zeroclaw crashes mid-experiment:
1. Claim expires (no heartbeat)
2. Meta-verifier detects and resets work to `status:open`
3. Different zeroclaw picks it up
4. Partial results are left in `fleet-opt/experiment-results` — the meta-verifier ignores duplicate work IDs from expired claims

---

## 6. Thread Safety & Race Conditions

### Problem: Two zeroclaws claim the same work item simultaneously

**Solution:** A work tile's `claimed_by` field is the single source of truth. The zeroclaw that writes the claim tile first "wins". If two zeroclaws both write `claim:{work_id}:{zeroclaw_id}` simultaneously, validate by:

1. Read all claims for this work_id
2. The one that was most recently written with `status:active` wins
3. Loser must release its claim (set `status:expired`)
4. Meta-verifier enforces: only one active claim per work_id

### Problem: Stale hardware profile

**Solution:** Each hardware profile tile includes `timestamp`. The atlas builder ignores profiles older than 48h. The fleet-agent re-probes every 24h on schedule. Re-probes are also triggered on:
- CPU hotplug event
- Kernel module load/unload (especially GPU drivers)
- Container restart

---

## 7. Convergence Detection

When does the fleet know it's done optimizing?

**Per (algorithm, arch) pair:**
- All known config variants have been tested
- No new config tested in the last 7 days that beats the current optimal
- Range of tested configs covers: baseline, -O3, -O3+unroll, -O3+fast-math, -O3+arch-specific, manual intrinsics, prefetch variants

**Fleet-wide:**
- All zeroclaws with matching hardware have contributed to relevant benchmarks
- All flagged inconsistencies from meta-verifier have been resolved or acknowledged
- Performance atlas is at 100% coverage for known algorithms

**Storage cost (estimate):**
- Hardware profiles: 1 per node = O(n) where n ≤ 100
- Work queue: O(m) where m ≤ concurrent work items (target < 100)
- Claims: O(n × m) worst case, but typically O(n)
- Experiment results: O(k × c) where k = work items completed, c = configs per work. Target < 10K tiles
- Collective kernels: O(a × h) where a = algorithms, h = hardware variants. Target < 500
- Performance atlas: O(a × h). Target < 500
- Fast-math alerts: O(a × h²) worst case but practically rare. Target < 50

---

## 8. Tile Format Compatibility

All tiles conform to the standard PLATO Tile definition:

```python
@dataclass
class Tile:
    domain: str          # "fleet-opt"
    question: str        # semantic key
    answer: str          # JSON-stringified schema payload
    source: str          # "zeroclaw:eileen-fm-001"
    confidence: float    # 0.0–1.0
    tags: list[str]      # filters for querying
    provenance: str      # optional I2I provenance chain
```

The `answer` field is JSON-serialized from the schema objects above. Querying uses PLATO's existing `list_tiles` with `question_prefix` or `tag` filters.

---

## 9. Protocol Summary (Sequence Diagram)

```
Forgemaster       Oracle1 PLATO      eileen zeroclaw     Jetson zeroclaw
    │                  │                   │                   │
    │── probe ────────►│                   │                   │  [Hardware Discovery]
    │                  │◄─── hw-profile ───│                   │
    │                  │◄─── hw-profile ───────────────────────│
    │                  │                   │                   │
    │── decompose ────►│                   │                   │  [Work Generation]
    │ (write work)     │                   │                   │
    │                  │                   │                   │
    │                  │─── poll open ────►│                   │  [Work Claiming]
    │                  │◄── claim ─────────│                   │
    │                  │                   │                   │
    │                  │─── poll ─────────────────────────────►│
    │                  │◄── claim ─────────────────────────────│
    │                  │                   │                   │
    │                  │◄─── run bench ────│                   │  [Execution]
    │                  │◄─── result:bl ────│                   │
    │                  │◄─── result:fm ────│                   │
    │                  │◄─── result