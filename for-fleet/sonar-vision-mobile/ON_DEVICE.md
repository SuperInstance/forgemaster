# On-Device Inference Engine — SonarVision Mobile

## Model Architecture

### Encoder (Raw Waveform → Latent Scene)

```
Input: (N_samples,) float32 raw audio at 48kHz
  │
  ├─ 1D Conv: C_in=1, C_out=32, K=512, S=256  (100ms context)
  ├─ ReLU + BN
  ├─ 1D Conv: C=32→64, K=256, S=128
  ├─ ReLU + BN
  ├─ 1D Conv: C=64→128, K=128, S=64
  ├─ ReLU + BN
  ├─ Global Avg Pooling
  ├─ Dense: 128 → 256
  └─ Latent vector z ∈ ℝ²⁵⁶
```

**Size:** ~500K parameters. Suitable for NPU/GPU on any phone with ML accelerator.

**Format:** ONNX (cross-platform) or TFLite (Android-optimized).

### Predictor (Latent → Expected Return)

Cross-attention transformer decoder:

```
Input: z ∈ ℝ²⁵⁶ + noise
  │
  ├─ Positional encoding (time axis for output samples)
  ├─ Cross-attention: Q=positions, KV=z
  ├─ FFN: 256→512→256
  ├─ LayerNorm + Add
  ├─ Dense: 256 → N_samples
  └─ Predicted return waveform ∈ ℝᴺ
```

**Size:** ~200K parameters.

### Depth Fusion (Acoustic → Camera Space)

Lightweight projector:

```
Input: (N_angles × N_range_bins) heatmap
  │
  ├─ 2D Conv: C=1→16, K=3, S=1
  ├─ ReLU
  ├─ 2D Conv: C=16→1, K=3, S=1
  ├─ Sigmoid
  └─ Output: same shape, depth-normalized
```

**Size:** ~500 parameters (tiny — learned projection).

## Quantization Strategy

| Layer Type | Training Precision | Deployment Precision |
|------------|-------------------|---------------------|
| Encoder Conv | FP32 | INT8 (per-channel) |
| Encoder Dense | FP32 | INT8 (per-tensor) |
| Predictor cross-attn | FP32 | FP16 (attention degrades in INT8) |
| Depth fusion | FP32 | INT8 |
| Matched filter (DSP) | N/A | FP32 (on DSP, not ML accelerators) |

**Post-training quantization** using calibration dataset of recorded chirp returns.

**Expected accuracy loss:** < 2% after INT8 quantization (acoustic data is robust).

## Latency Budget

Target: on-device, mobile NPU, Qualcomm Hexagon or Apple Neural Engine.

| Pipeline Stage | Time (ms) | Processor |
|----------------|-----------|-----------|
| Chirp generation | <0.1 | Pre-computed table |
| Speaker playback | 50.0 | Audio HW (overlapped) |
| Mic capture | 50.0 | Audio HW |
| Matched filter (FFT) | 1.0 | DSP (Qualcomm ADSP) |
| Envelope detection | 0.5 | DSP |
| Peak detection | 0.1 | CPU |
| Encoder inference | 3.0 (INT8) / 5.0 (FP16) | NPU |
| Predictor inference | 2.0 (FP16) | NPU |
| Breathing extraction | 5.0 (every 30th profile) | CPU |
| Self-supervised loss | 10-30 (periodic, async) | CPU/NPU |
| **Pipeline total** | **~56ms** | **~18Hz** |

**Optimization:** The matched filter + encoder can pipeline: while next chirp is playing, process the previous chirp's return. Overlap halves effective latency to ~28ms (36Hz).

## On-Device Training

Fine-tuning the self-supervised loop requires gradient computation, which is heavier than inference.

### Training Schedule
- **Daytime supervised:** When camera is available (user is awake, phone on nightstand)
  - Full cross-modal loss with camera depth
  - 10-20 pairs per session = free training data
- **Nighttime self-supervised:** When camera is dark (user sleeping)
  - Physics consistency loss only (FLUX engine forward pass)
  - Temporal consistency loss (adjacent chirps should have similar scene)
  - No labels needed

### Training Latency (optional, background compute)
| Operation | Time | Frequency | Power |
|-----------|------|-----------|-------|
| Cross-modal loss | ~30ms | Per ~60s of daytime use | ~400mW |
| Physics consistency | ~50ms | Every 60s (nighttime) | ~400mW |
| Gradient update | ~100ms | After each batch of 4 | ~500mW |
| **Total training** | **~3s/day** | **Negligible** | |

## Memory Footprint (On-Device)

| Component | RAM | ROM |
|-----------|-----|-----|
| Encoder model (INT8) | 500KB | 500KB |
| Predictor model (FP16) | 400KB | 400KB |
| Depth fusion (INT8) | 1KB | 1KB |
| Audio ring buffer (1s) | 192KB | 0 |
| Range profile buffer (60s) | 120KB | 0 |
| Matched filter kernel | 4KB | 4KB |
| **Total** | **~1.2MB RAM** | **~900KB ROM** |

This fits comfortably in any modern smartphone. For comparison: a single Instagram story frame is ~2MB.

## Battery Impact

| Mode | Components Active | Power | Over 8h Sleep |
|------|-------------------|-------|---------------|
| Continuous | Speaker + mic + NPU | ~350mW | ~2,800mWh = 22% battery (3000mAh @ 4V) |
| Burst (1s on, 9s off) | Same, duty-cycled | ~85mW avg | ~680mWh = 5.7% battery |
| Ultra-low (1s on, 29s off) | Same, longer duty | ~40mW avg | ~272mWh = 2.3% battery |

**Recommendation:** Burst mode (10% duty cycle) provides 1 chirp per second → adequate for breathing tracking, 5-6% battery overnight. Burst mode also reduces thermal load on the speaker.

## Export Format

Model exported via ONNX for cross-platform deployment:

```bash
# Export from Python
import torch
import torch.onnx
from sonar_mobile_model import SonarEncoder

model = SonarEncoder()
dummy_input = torch.randn(1, 1, 2400)  # 50ms at 48kHz
torch.onnx.export(model, dummy_input, "sonar_encoder.onnx",
    input_names=["audio"],
    output_names=["latent"],
    dynamic_axes={"audio": {0: "batch_size"}},
)

# Convert to TFLite for Android
import tensorflow as tf
converter = tf.lite.TFLiteConverter.from_onnx("sonar_encoder.onnx")
converter.optimizations = [tf.lite.Optimize.DEFAULT]
converter.target_spec.supported_types = [tf.lite.constants.FLOAT16]
tflite_model = converter.convert()
open("sonar_encoder.tflite", "wb").write(tflite_model)
```

## Verification Tests

Before deployment, validate:
1. **Deterministic:** Same input → same output (±1% numerical tolerance)
2. **Quantized accuracy:** INT8 < 2% MSE degradation vs FP32
3. **Latency:** <60ms per pipeline run on target device
4. **Thermal:** No speaker damage after 8h continuous 20kHz output
5. **Privacy:** Zero data leaves the device (on-device inference only)
