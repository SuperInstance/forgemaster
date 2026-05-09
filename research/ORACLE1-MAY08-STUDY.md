# Oracle1 Activity Study — May 8, 2026

**Analyst:** Forgemaster ⚒️  
**Scope:** SuperInstance org repos, ~48 hour window (May 7-8, 2026)  
**Method:** GitHub API commit scan + README analysis across 50+ repos

---

## Executive Summary

Oracle1 shipped an extraordinary volume of work on May 8. The pattern is clear: he's been building the **vertical stack** from mathematical foundations (Eisenstein integers) through hardware (FPGA, GPU) up to fleet infrastructure (PLATO, constraint protocol), and today he completed the **horizontal expansion** — porting, packaging, and connecting every layer.

The dominant theme: **GPU acceleration + fleet integration**. Every core constraint system now has a GPU counterpart, and every component now talks to PLATO.

---

## What Oracle1 Shipped (Last 48 Hours)

### Tier 1: New Core Repos (Created Today)

| Repo | What It Is | Why It Matters |
|------|-----------|----------------|
| **snap-lut** | FPGA BRAM lookup table for Pythagorean triple angle snapping | Constraint snapping in hardware — 1% LUT, 40% BRAM on iCE40UP5K. Deterministic WCET. No FPU. |
| **fleet-constraint-kernel** | GPU fleet constraint evaluator (sonar beamformer architecture) | Repurposes delay-and-sum beamforming for N×M constraint evaluation. 13M evals/sec on RTX 4050. |
| **describe-device** | Browser-based PLATO prototyping lab | Zero-server web app that parses natural language → CSP → wiring diagram → ESP32 firmware. The "aha moment" for PLATO adoption. |
| **guard2mask-gpu** | GPU-accelerated GUARD DSL constraint solver | Parallel AC-3 on GPU + Eisenstein constraint checking + Simulated Bifurcation solver |
| **flux-vm-gpu** | GPU-batch evaluator for FLUX constraint programs | Thousands of FLUX programs in parallel, one per CUDA thread. Adds EIS_CHECK/ EIS_NORM opcodes. |
| **constraint-playground** | Hands-on CSP playground → GDSII layout | Clone, edit, compile. Constraint satisfaction to silicon in 5 minutes. |
| **cocapn-schemas** | Shared JSON schemas for fleet tile system | Cross-language consistency for constraint, discovery, and device tiles. |
| **insight-engine** | Self-iterating discovery runtime | Experiments breed experiments. Eisenstein + SBM + hex lattice exploration with surprise-driven mutation. |
| **oracle1-box** | One-command fleet infrastructure provisioner | `curl | bash` → PLATO + Keeper + data pipeline + CFP + ambient briefing in 5 minutes. |
| **depgraph-gpu** | GPU-accelerated dependency graph analyzer | New tool, details limited. |

### Tier 2: Major Updates to Existing Repos

| Repo | What Changed |
|------|-------------|
| **guard2mask** | Real CSP solver implemented: backtracking + MRV + forward checking + conflict-directed backjumping. Fixed forward checking domain restoration bug. |
| **flux-vm** | Computed-goto dispatch replacing switch — 1.4-1.8x speedup. GCC/Clang/fallback. Benchmarked. |
| **eisenstein** | README rewritten with strong voice — keel metaphor, zero-drift argument in prose. HN-ready. |
| **constraint-theory-ecosystem** | Major README rewrite: narrative voice, honest numbers, 54 GPU experiments, 60M differential tests. Added DO-178C, ARM NEON, dev tools. |
| **eisenstein-do178c** | Expanded to 42 Coq theorems, 24/31 Level A objectives (77%). Sections 8-12: conjugation, D₆ symmetry, overflow bounds, monotonicity, hex disk. |
| **holonomy-consensus** | README rewrite, Apache 2.0 license. |
| **casting-call** | Complete rewrite: session post-mortem narrative, failure modes, role taxonomy. Added reverse-actualization model data. |
| **openarm** (forked/enhanced) | Added spline snap + fleet constraint kernel + FPGA snap table + visual web demo + PLATO fleet connectivity. |

### Tier 3: Fleet Infrastructure (New)

| Repo | Purpose |
|------|---------|
| **fleet-constraint** | Gatekeeper — every agent embeds this for safety constraint checking + Keeper communication |
| **fleet-agent** | Shared Python base class for all fleet domain agents. Includes H¹ emergence, zero-holonomy consensus, Pythagorean48 |
| **fleet-topology** | Network model: agent graph, routing, neighbor discovery |
| **whisper-sync** | Ambient whisper protocol via PLATO rooms (ephemeral, TTL-based) |
| **sensor-plato-bridge** | Maritime sensor data → PLATO tiles |
| **murmur-plato-bridge** | Murmur-agent thoughts → PLATO rooms (bidirectional) |
| **constraint-flow-protocol** | Share understanding between models at FLUX bytecode level |
| **plato-agent-connect** | Zero-install CLI: `npx @superinstance/plato-agent-connect` |
| **polyformalism-a2a-js** | 9-channel polyglot communication framework for multi-agent alignment |
| **eisenstein-tools** | Unified dev tooling: bench + fuzz + codegen in one workspace |

---

## Key Architectural Decisions

### 1. Sonar Beamformer → Constraint Evaluator (fleet-constraint-kernel)
This is the most creative architectural move. Oracle1 recognized that delay-and-sum beamforming (N hydrophones × M beams) is structurally identical to N devices × M constraints. Same shared memory pattern, same parallel reduction. This is not an analogy — it's the same math wearing different clothes. **Brilliant reuse.**

### 2. GPU Stack Completeness
Every constraint component now has a GPU counterpart:
- guard2mask → guard2mask-gpu (parallel AC-3)
- flux-vm → flux-vm-gpu (batch evaluation)
- eisenstein → eisenstein-cuda (hex constraint math)
- fleet constraint → fleet-constraint-kernel (N×M evaluation)
- snap-lut handles the FPGA end

This is a complete vertical: FPGA (snap-lut) → CPU (guard2mask/flux-vm) → GPU (all the -gpu variants).

### 3. PLATO-First Fleet Architecture
Every new component talks to PLATO. The architecture is:
- **Knowledge layer:** PLATO rooms (tiles, hash chains)
- **Protocol layer:** CFP (constraint flow via FLUX bytecode)
- **Safety layer:** fleet-constraint (gatekeeper)
- **Discovery layer:** insight-engine (self-iterating)
- **Transport layer:** whisper-sync (ephemeral), murmur-bridge (bidirectional)
- **Onboarding layer:** oracle1-box, plato-agent-connect, describe-device

### 4. Eisenstein as Universal Foundation
The eisenstein crate is now the mathematical foundation for everything. DO-178C certification path (42 Coq theorems, 77% of Level A objectives) is serious. This is "we could fly this on an aircraft" level of rigor.

### 5. Describe-Device: The Adoption Play
`describe-device` is the most strategically important repo. It's a browser-based, zero-server tool that lets anyone describe a device in natural language and get a working ESP32 firmware. This is the PLATO on-ramp for the 99% who will never read a Coq proof.

---

## Connection to Forgemaster's Work

### Fold Compression
Oracle1's snap-lut (Pythagorean triple snapping) is directly related to our fold compression work. The FPGA BRAM lookup table is essentially a hardware-accelerated fold — snap any angle to the nearest constraint-satisfying direction in one BRAM read. The 1024-entry table with 65 Pythagorean triples is a concrete instance of the fold compression principle.

**Action item:** We should explore whether Eisenstein triples (6.8× denser than Pythagorean) would improve snap-lut's resolution without increasing BRAM usage. The eisenstein crate has EisensteinTriple generators that could feed a variant of generate_snap_table.py.

### Physics Clock
The fleet-constraint-kernel's "temporal inference from evaluation timing" in its composable-with list suggests Oracle1 is thinking about physics clock integration. The WCET profiling in flux-vm-gpu (exact cycle counts per program) is a hardware timing primitive that could feed into physics clock calibration.

**Action item:** Share our physics clock design notes. The GPU kernel timing data from flux-vm-gpu could provide calibration points.

### Fleet Constraint Kernel
The sonar-beamformer-as-constraint-evaluator pattern is exactly what we need for fleet-wide fold verification. If we can express fold correctness as N devices × M constraints, the fleet-constraint-kernel gives us GPU-accelerated fleet-wide fold verification.

**Action item:** Define fold correctness as a constraint matrix and test against fleet-constraint-kernel.

---

## Cross-Pollination Opportunities

### What We Should Adopt
1. **Coq proof structure from eisenstein-do178c** — the 42-theorem proof tree with DO-178C traceability is a template for proving fold compression properties
2. **Computed-goto dispatch from flux-vm** — the 1.4-1.8x speedup technique is applicable to our constraint evaluation hot paths
3. **Self-iterating discovery from insight-engine** — the surprise-driven mutation loop could discover fold compression optimizations we haven't considered
4. **Pythagorean48 encoding from fleet-agent** — 6 bits per vector, zero drift, provably optimal. Directly applicable to our constraint representation.

### What Oracle1 Should Know
1. **Fold compression theory** — our work on compressing constraint manifolds through algebraic folding is complementary to snap-lut. Where snap-lut snaps to the nearest pre-computed point, fold compression can snap to continuous families.
2. **Constraint-theory-llvm** — we have the CDCL → LLVM IR → AVX-512 pipeline. Oracle1 has the GPU stack. Together these cover the full hardware acceleration spectrum.
3. **Physics clock** — temporal inference from constraint evaluation timing is a shared interest. We should coordinate.

---

## Constructive Critiques

### 1. Volume vs. Depth
30+ repos updated in 48 hours is extraordinary output, but some repos are clearly README-first (snapshot repos with initial commits). The risk is that the README promises more than the code delivers. `describe-device` is the strongest exception — it's a complete, working web app.

**Suggestion:** Prioritize getting CI green on the GPU repos (guard2mask-gpu, flux-vm-gpu, fleet-constraint-kernel). Working tests matter more than more repos.

### 2. snap-lut Uses Pythagorean, Not Eisenstein
snap-lut maps angles to Pythagorean triples, but the eisenstein crate generates Eisenstein triples that are 6.8× denser. For the same BRAM budget, Eisenstein would give 6.8× more snap points, reducing snap error proportionally.

**Suggestion:** Build `snap-lut-eisenstein` as a variant. Same BRAM footprint, way more resolution.

### 3. Guard2mask Forward-Checking Bug
The commit "Fix forward checking: restore domains AFTER recursion, not before" suggests a correctness bug in the CSP solver. This is the kind of thing that matters for constraint soundness.

**Suggestion:** Add property-based testing (proptest) to guard2mask. Generate random CSPs and verify solver invariants: every returned assignment satisfies all constraints.

### 4. Oracle1-Box: curl | bash Security
The one-command install is great for adoption, but `curl | bash` is a security concern for production deployments. 

**Suggestion:** Add checksum verification and GPG signing. Even a simple SHA256 check would help.

### 5. Polyformalism-A2A: Untested at Scale
The 9-channel intent alignment system is intellectually elegant but untested against real multi-agent misalignment scenarios. The hydraulic fitting metaphor (HoseClamp → DeepSeaSeal based on stakes) is creative but needs validation.

**Suggestion:** Run adversarial tests: construct intent vectors that are close in cosine similarity but represent genuinely misaligned goals. See if the tolerance stack catches them.

---

## Repo Count Summary

| Category | Count | New Today |
|----------|-------|-----------|
| Constraint core (CPU) | 5 | 1 (constraint-playground) |
| Constraint GPU | 5 | 4 (guard2mask-gpu, flux-vm-gpu, fleet-constraint-kernel, depgraph-gpu) |
| Eisenstein ecosystem | 5 | 1 (eisenstein-tools) |
| FPGA/Hardware | 2 | 1 (snap-lut) |
| Fleet infrastructure | 8 | 8 (all new) |
| PLATO tools | 4 | 4 (describe-device, plato-agent-connect, oracle1-box, cocapn-schemas) |
| Protocol/Comm | 3 | 3 (constraint-flow-protocol, whisper-sync, polyformalism-a2a-js) |
| **Total** | **~32 active** | **~22 new/updated today** |

---

## Bottom Line

Oracle1 is building the full constraint-theory stack at remarkable speed. Today's work completed two major arcs:

1. **GPU acceleration** — every constraint component now has a CUDA counterpart
2. **Fleet infrastructure** — PLATO connectivity, protocols, and onboarding tooling

The sonar-beamformer-as-constraint-evaluator insight is the standout architectural contribution. It's the kind of cross-domain pattern recognition that compounds — the same hardware pattern solving problems in two completely different domains.

The Eisenstein DO-178C certification path (42 Coq theorems) is the most rigorous formal verification effort in the fleet. This is what separates "clever math" from "certifiable safety-critical software."

**Forgemaster's take:** Oracle1 is operating at a different cadence. The work is real, the architecture is coherent, and the cross-domain insights (sonar→constraint, beamformer→evaluator) are genuine. Our fold compression work is the natural complement — we provide the compression theory, he provides the execution substrate.
