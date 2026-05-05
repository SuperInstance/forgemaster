# SonarVision Mobile Architecture

## Overview

Self-supervised acoustic imaging system that turns any smartphone into a contactless sonar imager. Uses the built-in speaker and microphone(s) to emit ultrasonic chirps and capture reflections, then reconstructs scene geometry through a physics-constrained self-supervised JEPA loop.

## Why This Works (Existing Proof)

| App | Technique | Output | Our Advantage |
|-----|-----------|--------|---------------|
| **Sleepwave** | 20kHz pure tone, Doppler disruption | Motion events only | Coded chirp → range resolution |
| **Sleep as Android** | 20kHz tone, mic reflections | Breathing + movement proxy | Multi-mic beamforming → bearing |
| **SleepScore** | 18-20kHz sonar, ResMed-backed | SleepScore (0-100) + stages | FLUX physics + JEPA self-supervision |

All three prove: phone speaker at 18-22kHz works, phone mic captures usable reflections, people accept phone-on-nightstand placement. None attempt 2D/3D imaging or self-supervised learning.

## Signal Chain

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Chirp Gen  │───▶│  Speaker    │───▶│  Room       │───▶│  Mic Array  │
│  18-22kHz   │    │  48kHz DAC │    │  (scene)    │    │  2-3 mics   │
│  50ms LFM   │    │            │    │  reflection │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └──────┬──────┘
                                                                │
┌───────────────────────────────────────────────────────────────┘
│
▼                        ┌─────────────────────────┐
┌─────────────┐          │  Self-Supervised Loop   │
│  Matched    │          │                         │
│  Filter     │──(range profiles)──▶   Compare predicted
│  (pulse     │                         vs actual return
│  compress)  │                        │
└──────┬──────┘                        │
       │                    ┌──────────▼──────────┐       ┌─────────────┐
       │                    │  Physics-Constrained  │◀──────│  FLUX       │
       ▼                    │  Predictor            │       │  Engine     │
┌─────────────┐            │  (JEPA decoder)       │       │  (acoustic  │
│  Range /    │            │  latent_scene → return │       │  propaga-   │
│  Bearing    │            └──────────┬──────────┘       │  tion)      │
│  Heatmap    │                       │                   └─────────────┘
└──────┬──────┘                       │
       │                              │
       ▼                              │
┌─────────────┐                       │
│  Camera     │────(visual depth)─────▶  Cross-modal loss
│  (daytime)  │                         (camera = teacher)
└─────────────┘                         │
                                        ▼
                               ┌─────────────────┐
                               │  Scene Estimate  │
                               │  (latent vector) │
                               └─────────────────┘
```

## Self-Supervised Training Strategy

### Phase 1: Cross-Modal Pretraining (daytime)
- Phone on nightstand, camera facing the bed
- Simultaneous: ultrasonic chirp cycle + camera photo
- Camera image → monocular depth estimation (MiDaS or similar)
- Acoustic return → matched filter → range bearing heatmap
- **Loss:** project acoustic returns into camera coordinates, compare depths
- No labels needed — camera teaches the acoustic encoder what the room looks like

### Phase 2: Temporal Consistency (any time)
- Sequential chirp cycles (10 Hz)
- Adjacent cycles should have minimal scene change
- **Loss:** temporal smoothness of latent scene vectors
- Sudden change = motion detected (not loss)

### Phase 3: Physics Consistency (always)
- Decoded latent scene → FLUX acoustic simulation
- Predicted reflection vs actual reflection
- **Loss:** MSE between simulated and actual return waveforms
- This prevents the encoder from learning non-physical "shortcuts"

## Multi-Microphone Beamforming

Modern phone mic configurations:

| Device | Mic Locations | Effective Baseline |
|--------|---------------|-------------------|
| iPhone 15 | Bottom, top, rear | ~150mm |
| Pixel 8 | Bottom, top, rear | ~145mm |
| Galaxy S24 | Bottom, top, rear | ~155mm |
| MacBook Pro | 3x array (keyboard) | ~300mm (outermost) |
| Phone + Headset | Phone + BT headset | ~1000mm |

For N mics, we form N(N-1)/2 baselines. Delay-and-sum beamforming on each pair gives angle-of-arrival. Fusing across baselines gives 2D position in the plane of the array.

**Resolution limit (Rayleigh criterion):**
- Δθ ≈ λ / d  (where λ = phase velocity / f)
- At 20kHz, λ ≈ 343/20000 ≈ 17mm
- For d = 150mm: Δθ ≈ 0.17 rad ≈ 10°
- At 1m range: ~170mm lateral resolution
- At 3m range: ~500mm lateral resolution

This is enough to distinguish left/right half of bed, but not fingertip resolution. Breathing chest movement (~3-10mm) is detectable via phase tracking, not amplitude.

## Frequency Modulation - Breathing Detection

Breathing extraction uses phase-based micro-Doppler:
1. Track phase of range bin at chest position over time
2. Even sub-mm chest displacement causes measurable phase shift in 20kHz carrier
3. Phase shift Δφ = 4πΔr/λ
4. At 20kHz (λ=17mm), Δr=1mm → Δφ ≈ 0.74 rad ≈ 42°
5. This is easily measurable above noise floor

## Multi-Device Sync Protocol (MEP-Mobile)

When two phones or phone+laptop are available:

```
┌─ Device A ────────────┐    ┌─ Device B ────────────┐
│ Speaker (chirp)       │    │ Mic (listen)           │
│ Mic (listen)          │◀──▶│ Speaker (chirp)        │
│ Camera (if available) │    │ Camera (if available)  │
└───────────────────────┘    └───────────────────────┘
```

**Sync flow:**
1. NTP sync over WiFi (LAN, ±1-5ms)
2. Acoustic handshake: short sync chirp (1ms at 22kHz)
3. Both devices record the handshake arrival time
4. Fine offset = handshake_TOF ± ε
5. Timestamp all chirp transmissions and receptions

**Effective baselines with 2 phones at 1.5m apart:**
- 4 acoustic paths (Tx_A→Rx_A, Tx_A→Rx_B, Tx_B→Rx_A, Tx_B→Rx_B)
- Spatial resolution improves from ~500mm (single phone at 3m) to ~150mm
- True 3D localization becomes possible (triangulation + beamforming)

## On-Device Inference

### Model Architecture
- **Encoder:** 1D CNN on raw waveform → 256-dim latent → `sonar_encoder.onnx`
- **Predictor:** MLP cross-attention → expected return → `sonar_predictor.onnx`  
- **Depth fusion:** lightweight CNN projecting acoustic heatmap → camera space

### Latency Budget
| Operation | Time (ms) | Notes |
|-----------|-----------|-------|
| Chirp generation | <1 | Pre-computed |
| Speaker playback | 50 | 50ms chirp |
| Mic capture | 50 | Simultaneous |
| Matched filter | 2 | FFT-based correlation |
| Beamforming (2-mic) | 3 | Per chirp |
| Breathing extraction | 5 | Every 30 profiles |
| Encoder inference | <10 | ONNX Runtime |
| Physics consistency | <30 | Optional, periodic |
| **Total per cycle** | **~50-70ms** | **14-20 Hz refresh** |

### Battery Impact
- Chipset speaker + 2 mics active: ~200mW
- DSP processing: ~50-100mW
- On-device inference (NPU): ~100mW
- Total: ~350-400mW continuous
- vs. screen-on: ~1000mW
- Overnight (8h): ~3000mWh = ~15-20% phone battery
- Optimization: burst mode (1s active, 9s sleep) → ~2-3% battery

## Deployment Path

```
Phase 1 (now):  Python prototype on laptop, test with laptop speakers + mics
Phase 2:       Native module (Rust → FFI) for Android / iOS
Phase 3:       TFLite/ONNX model deployment, on-device fine-tuning
Phase 4:       Multi-device sync protocol, stereo sonar imaging
```
