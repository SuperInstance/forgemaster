# MEP-Mobile: Multi-Device Acoustic Synchronization Protocol

## Overview

MEP-Mobile extends the Marine Echo Protocol (MEP) from our subsea stack to the air-acoustic domain. Two or more devices (phones, laptops, headsets) synchronize their clocks and coordinate chirp transmission to form a multi-element phased array.

## Clock Synchronization

### NTP Calibration (Coarse)

Each device runs an NTP client against a shared LAN time source before starting:

```
Device A → NTP query → Device B (or local router)
Device B → NTP query → same source
```

**Expected accuracy:** ±1-5ms over WiFi LAN (sufficient for coarse sync).

### Acoustic Handshake (Fine)

After NTP, devices perform an acoustic handshake to measure residual offset:

1. Device A emits a short sync pulse (1ms, 22kHz pure tone)
2. Both devices record arrival time (A: t_A_arrive, B: t_B_arrive)
3. Exchange timestamps
4. Time-of-flight: ToF = (t_B_arrive - t_A_arrive - t_A_tx) / 2
5. Clock offset = t_A_arrive - t_B_arrive - ToF
6. Repeat 5x, take median offset

**Expected accuracy:** ±0.1ms after acoustic handshake.

### Timing Budget

| Factor | Error | Impact on Range |
|--------|-------|-----------------|
| NTP only | ±5ms | ±1.7m |
| + acoustic handshake | ±0.1ms | ±3.4cm |
| + 96kHz sampling | ±10μs | ±3.4mm |

At 96kHz sampling (10.4μs/sample), our timing is fundamentally limited by sample clock jitter, not the sync protocol.

## Frame Format (MEP-Mobile)

Extended MEP header for air-acoustic transport. Packed binary, sent over UDP.

```
Offset  Size  Field            Description
──────  ────  ───────────────  ───────────────────────────────
0       1     version          Protocol version (0x01)
1       1     device_id        Source device ID
2       4     timestamp_ns     Device-local timestamp (monotonic clock ns)
6       2     chirp_id         Chirp sequence number (wraps at 65535)
8       2     chirp_type       0=chirp, 1=sync_pulse, 2=response
10      2     target_range_cm  Expected target range (cm, 0=unknown)
12      2     audio_len        Length of audio payload (bytes)
14      2     checksum         CRC-16 of header + payload (XMODEM)
16      N     audio_payload    Raw audio samples (PCM16 mono)
─────────────────────────────────────────────────────────
Total: 16 + N bytes
```

## Channel Combining Math

With 2 devices (A, B), each having 1 speaker and 1 microphone:

| Tx | Rx | Path Length | Usage |
|----|----|-------------|-------|
| A  | A  | 2×R_A       | Range to target from A |
| A  | B  | R_A + R_B   | Bistatic range sum |
| B  | A  | R_B + R_A   | Same (redundant, noise reduction) |
| B  | B  | 2×R_B       | Range to target from B |

**Triangulation:** With 2 baselines (A and B positions known), we solve for target position (x, y, z):

```
R_A = sqrt(x² + y² + z²)
R_B = sqrt((x - d)² + y² + z²)
```

where d = distance between devices. Given R_A from self-path and R_A+R_B from bistatic, both distances are determined → unique 3D position.

**Resolution improvement (2D → 3D):**
- Single phone: range + bearing → 2D (no elevation)
- Two phones: two range + two bearings → 3D (including height)

## Real-Time vs Batch Processing

### Real-Time Mode (Live Sleep Tracking)
- 10 chirps/sec per device
- On-device processing: matched filter + beamforming + breathing
- Off-device fusion: exchange range profiles every 1 second
- Latency: <200ms end-to-end

### Batch Mode (Post-Processing Analysis)
- Record raw audio + timestamps to file
- Post-process with full resolution (including phase-based breathing extraction)
- File format: WAV with metadata in RIFF chunks (device_id, chirp_timestamps)
- Useful for research: brute-force all possible sync offsets to find optimum

## Protocol Flow

```
Device A                     Device B
    │                           │
    ├── discovery (mDNS) ──────▶│
    │◀── discovery response ────┤
    │                           │
    ├── NTP sync ──────────────▶│
    │◀── NTP response ─────────┤
    │                           │
    ├── acoustic handshake ────▶│
    │◀── sync response ────────┤
    │                           │
    │  ─── sleep tracking ───  │
    │                           │
    ├── chirp (0xBEEF001) ─────▶│
    │◀── chirp response (0x0001)┤
    │    [both record locally]  │
    │                           │
    ├── exchange range profile ─▶│
    │◀── exchange range profile ─┤
    │                           │
    │  [fuse into 3D heatmap]  │
    │                           │
    ├── heartbeat (every 5s) ──▶│
    │◀── heartbeat ack ────────┤
    │                           │
```

## Failure Modes

| Failure | Fallback | User Impact |
|---------|----------|-------------|
| Device B battery dies | A continues solo | 2D -> 2D (reduced accuracy) |
| WiFi drops | Direct BLE (lower data rate) | Exchange range profiles less frequently |
| NTP unavailable | Device B's clock drifts | Gradual accuracy degradation over time |
| Acoustic handshake fails | NTP-only sync | ±1m range errors |
| Interference (TV, fan) | Frequency-hop to clear band | Minimal (automatic) |
