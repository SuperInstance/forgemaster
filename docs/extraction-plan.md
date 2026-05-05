# JetsonClaw1-vessel → Focused Repos Extraction Plan

## New Repo Map

### 1. `flux-compiler` — The constraint-to-native compiler
**What**: GUARD → LLVM IR → native code pipeline
**Contents**:
- `flux-hardware/compiler/` (fluxc.py, flux_llvm_backend.py)
- `guard2mask/` (GUARD parser + GUARD→FLUX compiler)
- `guardc/` (verified Rust compiler)
- `guard-dsl/` (DSL spec)
- `.github/workflows/metal-bake.yml`
**Why**: The compiler is the core product. It deserves its own repo.

### 2. `flux-vm` — The FLUX-C virtual machine
**What**: 50-opcode stack-based constraint VM
**Contents**:
- `flux-hardware/vm/flux_vm.rs` (55 tests)
- `flux-hardware/bridge/` (FLUX-C→FLUX-X bridge)
- `flux-ast/` (universal AST, 7 node types)
- `flux-isa/` (ISA definitions)
- `flux-isa-mini/`, `flux-isa-std/`, `flux-isa-edge/`, `flux-isa-thor/`
**Why**: The VM is the runtime. Separate from compiler.

### 3. `flux-hardware` — GPU/FPGA/CPU backends
**What**: CUDA, AVX-512, Fortran, Verilog, eBPF, WebGPU, Vulkan
**Contents**:
- `flux-hardware/cuda/` (5 CUDA kernels + differential tests)
- `flux-hardware/cpu/` (AVX-512, retro benchmarks, JIT)
- `flux-hardware/fortran/` (Fortran constraint kernel)
- `flux-hardware/rtl/` (SystemVerilog + Verilog HDC judge)
- `flux-hardware/ebpf/` (eBPF constraint firewall + loader)
- `flux-hardware/webgpu/` (WebGPU shader)
- `flux-hardware/vulkan/` (Vulkan compute)
- `flux-hardware/formal/` (SymbiYosys formal verification)
- `flux-hardware/coq/` (Coq proofs)
- `flux-hardware/fuzz/` (fuzzing)
**Why**: Hardware backends are distinct from the compiler/VM. Each could have its own CI.

### 4. `flux-hdc` — Hyperdimensional Computing library
**What**: 1024-bit hypervectors, semantic matching, SRAM baking
**Contents**:
- `flux-hardware/hdc/` (Python HDC + Rust crate skeleton)
- `flux-hardware/guard-examples/` (example .guard files)
**Why**: HDC is a research project that may grow independently.

### 5. `flux-site` — Web presence + PHP kit
**What**: cocapn.ai pages, playground, PHP integration kit
**Contents**:
- `flux-site/` (all of it — pages, php-kit, static)
- `Dockerfile`
**Why**: Oracle1 builds the sites but needs the kit. Separate repo for web work.

### 6. `flux-papers` — Academic papers + specs
**What**: EMSOFT paper, Safe-TOPS/W spec, GUARD grammar, benchmarks
**Contents**:
- `docs/papers/` (EMSOFT paper + related work)
- `docs/specs/` (Safe-TOPS/W, opcode reference, GUARD grammar)
- `docs/benchmarks-ascii.txt`
- `docs/man/fluxc.1`
**Why**: Papers have their own review cycle. Specs should be versioned separately.

### 7. `flux-tutorials` — Documentation and learning materials
**What**: Cookbooks, quickstarts, tutorials, runbooks
**Contents**:
- `docs/tutorials/` (quickstart, cookbook, GUARD tutorial, error guide)
- `docs/runbooks/` (fleet ops runbook)
- `docs/strategy/` (investor docs, certification roadmap, manifesto)
- `CONTRIBUTING.md`, `CONTRIBUTING-v2.md`
**Why**: Tutorials change fast. Don't pollute code repos.

### 8. `cocapn-fleet-docs` — I2I bottles + fleet coordination
**What**: Forgemaster's deliverables, I2I bottles, fleet coordination
**Contents**:
- `for-fleet/` (all I2I bottles, reports, research)
- `for-fleet/dashboard/`, `for-fleet/sonar-*`
- `docs/strategy/` (fleet strategy docs)
- `references/` (fleet detail, tools detail, etc.)
**Why**: Fleet docs are coordination artifacts, not code.

### 9. Existing repos (already separate)
- `SuperInstance/constraint-theory-core` — Rust library
- `SuperInstance/ct-demo` — Demo crate + CSP solver
- `SuperInstance/flux-isa` — ISA definitions (already exists)
- `SuperInstance/forgemaster` — Forgemaster's vessel
- `cocapn/fleet-knowledge` — PLATO tiles

### 10. Keep in JetsonClaw1-vessel (agent infrastructure)
- `memory/` — Session memory
- `references/` — Agent reference docs
- `skills/` — Agent skills
- `.credentials/` — API keys (NEVER move to public repo)
- `scripts/` — Heartbeat and utility scripts
- `HEARTBEAT.md`, `MEMORY.md`, `SOUL.md`, etc.
- `claude/`, `autodata-integration/` — Other agent workspaces

## Extraction Command Pattern

```bash
# For each new repo:
mkdir /tmp/flux-compiler
cd /tmp/flux-compiler
git init

# Copy files from vessel, preserving history via git-subtree or manual
# Simple approach: copy files, new git history
cp -r ~/workspace/flux-hardware/compiler/ ./
cp -r ~/workspace/guard2mask/ ./
cp -r ~/workspace/guardc/ ./
cp -r ~/workspace/guard-dsl/ ./

# Write focused README
# Add remote and push
gh repo create SuperInstance/flux-compiler --public
git remote add origin https://github.com/SuperInstance/flux-compiler.git
git add . && git commit -m "initial: extract from JetsonClaw1-vessel"
git push -u origin main
```

## Priority Order

1. **flux-compiler** — The product. Ship first.
2. **flux-vm** — The runtime. Ship second.
3. **flux-hardware** — GPU/CPU/FPGA backends.
4. **flux-papers** — EMSOFT paper needs its own home.
5. **flux-site** — Oracle1 needs this.
6. **flux-hdc** — Research, can wait.
7. **flux-tutorials** — Docs, can wait.
8. **cocapn-fleet-docs** — Coordination, can wait.
