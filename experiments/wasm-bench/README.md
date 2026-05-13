# WASM + WebGPU Benchmarks

The actual constraint checking implementation lives at:
`/home/phoenix/.openclaw/workspace/constraint-wasm/`

This benchmark validates:
- **Eisenstein Snap**: Cartesian → Eisenstein integer lattice snapping
- **Dodecet Encode**: 12-element constraint state compression
- **3-Tier Constraint Check**: Local (Admit 432), Regional (Parity/Density), Global invariants

See `constraint-wasm/` for the full implementation with:
- `constraint.wat` — Hand-written WebAssembly Text
- `constraint.c` — C source (emcc or gcc compatible)
- `constraint_compute.wgsl` — WebGPU compute shaders
- `index.html` — Browser benchmark page (JS + WASM + WebGPU)
- `constraint.wasm` — Compiled binary (1397 bytes)
