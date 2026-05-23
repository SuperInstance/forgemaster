# WASM Deploy Status — Escalation Gate

**Date:** 2026-05-17 | **Status:** ✅ Export verified, WASM-ready

## Model: Escalation Gate

| Property | Value |
|----------|-------|
| Parameters | 737 |
| Weight bytes | 2,948 |
| ONNX file | 1,554 bytes |
| TorchScript file | 12,929 bytes |
| Architecture | Linear(5→32)→ReLU→Linear(32→16)→ReLU→Linear(16→1)→Sigmoid |
| Accuracy | 81% |
| Recall | 57.1% |
| False positive rate | 9.2% |

## Input/Output

```
Input:  float32[5] = [confidence, tile_count, drift_rate, anomaly_score, density]
Output: float32    = escalation probability (0-1)
```

## Export Formats Verified

| Format | File | Size | Status |
|--------|------|------|--------|
| TorchScript | `escalation_gate.pt` | 12.6 KB | ✅ Roundtrip verified |
| ONNX (opset 14) | `escalation_gate.onnx` | 1.5 KB | ✅ ONNX validation PASS |
| NumPy weights | `escalation_gate_weights.npz` | 4.4 KB | ✅ Loadable |
| C header | `escalation_gate_weights.h` | 11.2 KB | ✅ Bare-metal embeddable |
| Pure JS engine | `escalation_gate.js` | 2.7 KB | ✅ No dependencies |

## WASM Deployment Paths

### Path 1: onnxruntime-wasm (Recommended for browser)
```bash
npm install onnxruntime-web
# Load escalation_gate.onnx (1.5KB) — runs in browser
```
- Smallest artifact: 1.5KB ONNX model
- Runtime: ~2MB onnxruntime-wasm library
- Latency: sub-millisecond

### Path 2: Pure JavaScript (Lightest)
- Use `escalation_gate.js` — no dependencies, 737 params
- 3 matrix multiplications + 2 ReLU + 1 sigmoid
- Total compute: 5×32 + 32×16 + 16×1 = 593 multiply-adds
- Latency: <1μs on modern JS engines
- **This IS effectively WASM-speed already** — the model is so small that JS overhead is negligible

### Path 3: C/Rust → WASM (Embedded/Native)
- Embed weights via `escalation_gate_weights.h` (C) or load .npz
- Compile with `-O3 -msimd128` for WASM SIMD
- Binary size: ~5-10KB including weights
- Latency: <100ns

## Inference Latency Estimates

| Target | Estimated Latency | Method |
|--------|-------------------|--------|
| Browser (JS) | <1μs | Pure matmul, no overhead |
| Node.js | <1μs | Same |
| WASM (C/Rust) | <100ns | Compiled, SIMD |
| Embedded (ARM M0) | <10μs | No FPU needed, soft float OK |
| NPU | N/A | Too small — CPU is faster |

## File Inventory

```
experiments/wasm-deploy/
├── export_escalation_gate.py      — Export script (TorchScript + ONNX + weights)
├── escalation_gate_inference.py   — Pure numpy inference engine (reference)
├── escalation_gate.js             — Pure JS inference engine (browser-ready)
├── escalation_gate.pt             — TorchScript model (12.6KB)
├── escalation_gate.onnx           — ONNX model (1.5KB)
├── escalation_gate_weights.npz    — Raw numpy weights (4.4KB)
└── escalation_gate_weights.h      — C header with embedded weights (11.2KB)
```

## Key Insight

**The escalation gate is so small (737 params, 1.5KB ONNX) that "WASM deployment" is almost trivial.** A pure JavaScript implementation with no framework dependencies runs in microseconds. The ONNX path adds safety/validation but the model is small enough that direct matmul in any language works perfectly.

The real value of WASM deployment isn't performance (CPU is already instant) — it's **portability**. The same 1.5KB model runs identically in:
- PLATO rooms (Python)
- Browser dashboards (JS/ONNX)
- Edge devices (C/WASM)
- Cloud workers (any runtime)

## Next Steps

1. **Train with real data** — current weights are synthetic, need real room telemetry
2. **Tune threshold** — lower from 0.5 to improve recall (currently 57.1%)
3. **Wire into PLATO** — add escalation gate to room runtime as default
4. **Bundle with traceable model** — 737 (gate) + 1037 (room model) = 1774 params total, 7KB system
5. **onnxruntime-wasm demo** — actual browser PoC loading the ONNX model
