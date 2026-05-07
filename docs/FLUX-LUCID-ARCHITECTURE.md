# FLUX-LUCID Ecosystem Architecture
## Unified View — All Components, All Platforms, All Repos

---

## The Stack (Bottom to Top)

```
┌─────────────────────────────────────────────────────────────────┐
│                     APPLICATION LAYER                           │
│  polyformalism-turbo-shell (MCP, 6 tools)                      │
│  linguistic-polyformalism-shell (MCP, 5 tools)                 │
│  flux-verify-api (NL verification REST API)                    │
├─────────────────────────────────────────────────────────────────┤
│                  COMMUNICATION LAYER                            │
│  polyformalism-a2a (PyPI) — 9-channel polyglot framework       │
│  holonomy-consensus (crates.io) — GL(9) ZHC alignment          │
│  fleet-murmur (Oracle1) — resonance matching                   │
│  fleet-spread (Oracle1) — 5-specialist synthesis                │
│  fleet-coordinate (Oracle1) — ZHC/beam/emergence                │
├─────────────────────────────────────────────────────────────────┤
│                   COMPILATION LAYER                             │
│  constraint-theory-llvm (crates.io) — CDCL → LLVM IR → x86-64  │
│  constraint-theory-mlir — FLUX MLIR dialect (C++)              │
│  flux-vm (Oracle1) — 50 opcodes, 5 variants (mini/std/thor/…)  │
│  flux-ast — Abstract syntax tree for FLUX language              │
├─────────────────────────────────────────────────────────────────┤
│                     CORE LAYER                                  │
│  constraint-theory-core (crates.io) — CDCL solver, AC-3         │
│  constraint-theory (PyPI) — Python reference implementation     │
│  flux-constraint (PyPI) — INT8 saturated checking               │
│  flux-constraint (npm) — JS zero-dependency checking            │
│  constraint-theory-ecosystem — 42 language reference            │
├─────────────────────────────────────────────────────────────────┤
│                   INFRASTRUCTURE LAYER                          │
│  PLATO (1141 rooms) — persistent knowledge store                │
│  fleet-knowledge (GitHub) — shared fleet documentation          │
│  I2I Protocol — git-based inter-agent communication             │
│  ZHC tolerance 0.5 — alignment guarantee                        │
│  Pythagorean48 — 48-direction intent lattice (5.585 bits)       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Published Packages (14 total)

### crates.io (12 crates)

| Crate | Version | Description | Author |
|-------|---------|-------------|--------|
| `constraint-theory-llvm` | 0.1.1 | CDCL → LLVM IR → AVX-512 + direct x86-64 emission | FM |
| `holonomy-consensus` | 0.1.1 | GL(9) zero-holonomy consensus for fleet coordination | FM |
| `flux-isa` | 0.1.2 | FLUX instruction set architecture | Oracle1 |
| `flux-isa-mini` | 0.1.0 | Minimal ISA for embedded (STM32) | Oracle1 |
| `flux-isa-std` | 0.1.0 | Standard ISA with validation pipeline | Oracle1 |
| `flux-isa-thor` | 0.1.0 | GPU-accelerated ISA with CUDA | Oracle1 |
| `flux-isa-edge` | 0.1.0 | Edge computing ISA with sensor pipeline | Oracle1 |
| `flux-ast` | 0.1.1 | Abstract syntax tree for FLUX language | Oracle1 |
| `guard2mask` | 0.1.3 | GUARD DSL → INT8 constraint masks | Fleet |
| `flux-verify-api` | 0.1.1 | NL verification REST API | Fleet |
| `flux-hdc` | 0.1.0 | Hyperdimensional computing for constraint bloom | Fleet |
| `flux-provenance` | 0.1.1 | Constraint provenance tracking | Fleet |
| `flux-bridge` | 0.1.1 | Cross-language constraint bridge | Fleet |
| `guardc` | 0.1.0 | GUARD verified compiler CLI | Fleet |

### PyPI (3 packages)

| Package | Version | Description |
|---------|---------|-------------|
| `constraint-theory` | 1.0.1 | Python reference implementation |
| `flux-constraint` | 1.0.0 | INT8 saturated constraint checking |
| `polyformalism-a2a` | 0.1.0 | 9-channel polyglot communication framework |

### npm (BLOCKED — token expired)

| Package | Version | Status |
|---------|---------|--------|
| `@superinstance/flux-constraint` | 1.0.0 | Ready, needs npm token refresh |

---

## Repository Map (16 repos)

### Forgemaster's Repos (SuperInstance org)
1. **constraint-theory-llvm** — Pure Rust, CDCL → LLVM IR → AVX-512
2. **constraint-theory-ecosystem** — 42 language reference, CI, benchmarks
3. **constraint-theory-engine-cpp-lua** — C++20 core + LuaJIT bridge
4. **constraint-theory-rust-python** — Rust + PyO3 bindings
5. **constraint-theory-mojo** — Mojo frontend + Python fallback
6. **constraint-theory-mlir** — FLUX MLIR dialect (C++)
7. **polyformalism-thinking** — Core framework + A2A research
8. **polyformalism-languages** — Sapir-Whorf experiments
9. **polyformalism-turbo-shell** — Creative cognition MCP shell
10. **linguistic-polyformalism-shell** — Cross-linguistic thinking MCP shell

### Oracle1's Repos (cocapn org)
11. **holonomy-consensus** — ZHC core (Rust, GL(9))
12. **fleet-murmur** — Resonance matching (Python)
13. **fleet-spread** — 5-specialist synthesis (Rust)
14. **fleet-coordinate** — ZHC/beam/emergence coordination (Rust)
15. **fleet-homology** — Betti number computation (Rust)
16. **fleet-knowledge** — Shared fleet documentation

---

## The 9-Channel Model (C1-C9)

| # | Channel | Polyglot Question | Oracle1 Equivalent |
|---|---------|-------------------|-------------------|
| C1 | Boundary | What are we talking about? | murmur topic matching |
| C2 | Pattern | How do pieces connect? | spread synthesis |
| C3 | Process | What's happening over time? | beam convergence |
| C4 | Knowledge | How sure am I? | ZHC tolerance |
| C5 | Social | Who cares and why? | fleet graph edges |
| C6 | Deep Structure | What's really being said? | homology H¹ |
| C7 | Instrument | What tools are available? | PLATO queries |
| C8 | Paradigm | What model of thought? | P48 lattice direction |
| C9 | Stakes | What matters vs what doesn't? | constraint surface |

---

## Integration Points (FM ↔ Oracle1)

### What FM Built That Oracle1 Uses
- `polyformalism-a2a` intent profiles → fleet-murmur resonance input
- 9-channel flavor vectors → P48 lattice encoding (log₂(48) × 9 ≈ 50.3 bits)
- Navigation metaphors → ZHC tolerance interpretation

### What Oracle1 Built That FM Uses
- `holonomy-consensus` GL(9) module → A2A alignment guarantee
- `flux-vm` ISA variants → constraint execution on edge/embedded/GPU
- Direct x86-64 emitter → bypasses LLVM for raw AVX-512 performance
- P48 lattice → zero-drift intent encoding

### The Sheaf Cohomology Connection
Both programs solve H⁰(S) ≠ ∅:
- Oracle1: for coordination (beam equilibrium, ZHC consensus)
- Forgemaster: for intent (alignment loop convergence, A2A channels)

### The 3-Layer Architecture
```
LAYER 3: Semantic (A2A 9-channel, alignment loop, C9 Stakes)
LAYER 2: Trust+Intent (P48 × [0,5]⁹ lattice, zero-drift, 38ms)
LAYER 1: Topological (fleet graph, β₁ emergence, murmur transport, HDC bloom)
```

---

## Research Artifacts (This Session)

### Navigation Metaphor Series (5 papers, ~58KB)
1. SPLINES-IN-THE-ETHER.md — Anchors define the curve
2. FAIR-CURVE-FIRST.md — Intent defines the grid
3. ROCKS-ARENT-ON-CHART.md — Local knowledge required
4. DRAFT-DETERMINES-TRUTH.md — Deep enough for my keel
5. PHYSICAL-WORLD-SOLVED-THIS.md — 6 domains prove negative knowledge

### Reverse Actualization (5 domains, ~58KB)
- Glassblowing (Seed-2.0-pro) — accurate models are FORBIDDEN
- Pottery (Step-3.5-Flash) — squat effect is timescale-dependent
- Wildlife tracking (Qwen3-235B) — curve describable through embodiment
- Jazz (Qwen3.5-397B) — in art you GRIND against rocks
- Music composition (Hermes-405B) — confirmed all 5

### Underrepresented Traditions (5 perspectives, ~30KB)
- Yoruba, Swahili, Igbo, Inuktitut, ASL/Deaf
- 8 new dimensions discovered beyond 9-channel model
- No two traditions found same primary consideration

### Experimental Evidence (12 models, 6 cultural perspectives, 5 domains)
- 224KB raw experiment data
- Cross-validated by 12+ AI models
- Zero-shot validation from 6 cultural viewpoints

---

## Next: Refactoring Needed

1. **Unify encoding:** `polyformalism-a2a` encode.py uses heuristics; needs LLM-based encoder
2. **Wire GL(9) into fleet:** holonomy-consensus Rust → polyformalism-a2a Python bridge
3. **Tolerance-aware PLATO tiles:** Include tolerance metadata per channel in PLATO submissions
4. **npm publishing:** Needs token refresh from Casey
5. **flux-constraint Python/JS sync:** PyPI and npm versions need to share the same test vectors
6. **Oracle1's x86-64 emitter:** Should be exposed as a feature flag in constraint-theory-llvm
7. **Shell repos → npm packages:** polyformalism-turbo-shell and linguistic-polyformalism-shell should be installable via npm as MCP servers

---

*16 repos. 14 published crates. 3 PyPI packages. 12+ models. 11 domains. One ocean.*
