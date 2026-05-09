# Fleet Dependency Map v2 — 2026-05-08 Session C Update

> 11 new repos this session. All standalone. All composable. Zero forced dependencies.

## The Modular Stack (12 repos, grouped by layer)

```
═══ SILICON LAYER (FPGA + CUDA) ═══
                                     
  eisenstein-cuda ←───────────────── shared math header (.cuh)
     │          │                     
  snap-lut   snap-lut-eisenstein  ←── FPGA BRAM tables
  (Pythag)   (Eisenstein, 6.8×)      
                                     
═══ COMPUTE LAYER (GPU) ═══          
                                     
  fleet-constraint-kernel ←────────── N×M parallel evaluator (CUDA)
     │                                
     └── eisenstein-cuda ←─────────── uses shared header
                                     
═══ MATH LAYER (Python) ═══          
                                     
  physics-clock ───────────────────── temporal inference + reality parity
  fold-compression ────────────────── permutation group compression
  temporal-flux ───────────────────── 7 time-aware FLUX opcodes
                                     
═══ TYPES LAYER (Rust) ═══           
                                     
  fleet-proto-rs ←─────────────────── shared types + PLATO client
                                     
═══ VISUAL LAYER (Browser) ═══       
                                     
  constraint-demo ←─────────────────── physics clock + parity + fold + snap
                                     
═══ FORMAL LAYER (Proofs) ═══        
                                     
  fleet-formal-proofs ←────────────── AC-3, Laman, H¹, Py48, ZHC
                                     
═══════════════════════════════════
                                     
  All repos are STANDALONE.          
  Dependencies are NATURAL, not forced.
  Use one, use many, the synergy compounds.
```

## Cross-Repo Connections (What Enhances What)

| From | To | Enhancement |
|------|----|-------------|
| eisenstein-cuda | fleet-constraint-kernel | Constraint math for GPU evaluator |
| eisenstein-cuda | snap-lut-eisenstein | Same math, hardware version |
| physics-clock | temporal-flux | Temporal inference backend for T_WAIT/T_AFTER |
| physics-clock | fleet-constraint-kernel | eval_time_ns → temporal fingerprint |
| fold-compression | temporal-flux | T_FOLD opcode backend |
| fleet-proto-rs | fleet-constraint-kernel | Rust types for constraint results |
| fleet-proto-rs | physics-clock | ConstraintBatch has thermal_state_celsius |
| fleet-formal-proofs | fleet-constraint-kernel | Proves AC-3 soundness used by kernel |
| fleet-formal-proofs | fold-compression | Proves β₁ = compression ratio |
| snap-lut-eisenstein | constraint-demo | Visual comparison in Section 4 |
| constraint-demo | ALL | Visual proof that ties everything together |

## Oracle1 ↔ Forgemaster Repos

| Oracle1 | Forgemaster | Bridge |
|---------|-------------|--------|
| describe-device | constraint-demo | Both zero-dep browser demos |
| constraint-flow-protocol | temporal-flux | T_* opcodes extend FLUX ISA |
| guard2mask | fleet-formal-proofs | AC-3 completeness proof |
| guard2mask | snap-lut-eisenstein | CSP solutions → LUT configs |
| flux-vm | temporal-flux | Temporal opcodes for VM |
| fleet-constraint | fleet-proto-rs | Same types, Python vs Rust |
| oracle1-box | fleet-proto-rs | Infra uses shared types |
| bare-metal-plato | eisenstein-cuda | .cuh works on ESP32 |

## Session C Stats

- **11 repos created** (all public, all standalone)
- **4 research documents** (physics clock, time-aware AI, security, inception)
- **5 formal proofs** (AC-3, Laman, H¹, Pythagorean48, ZHC)
- **2 Oracle1 studies** (22 repos analyzed, cross-pollination mapped)
- **1 I2I bottle** (coordination plan sent)
- **1 browser demo** (constraint-demo, 750 lines, zero deps)
