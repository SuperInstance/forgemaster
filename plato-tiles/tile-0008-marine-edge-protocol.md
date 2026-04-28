# Marine Edge Protocol (MEP)

**Core Concept:** Marine Edge Protocol is a lightweight binary protocol for workstation-to-edge GPU offload, designed for marine navigation systems with low-bandwidth, high-latency connections (satellite, cellular, RF links).

**Design Philosophy:**
- **Minimal Overhead:** 12-byte fixed header, no unnecessary metadata
- **Type Safety:** Strong typing prevents data corruption
- **Streaming:** Continuous data flow without explicit request/response pairing
- **Resilience:** Checksums, sequence numbers, retransmission support

**Message Structure:**

**Header (12 bytes):**
```
Offset | Size | Field
-------|------|--------------------
0      | 4    | Magic Number (0x4D45503A = "MEP:")
4      | 4    | Sequence Number (monotonic)
8      | 2    | Message Type (enum)
10     | 2    | Payload Length (0-65535)
```

**Message Types:**
- `0x0001`: NMEA_DATA (navigation sentences)
- `0x0002`: SONAR_FRAME (ping data)
- `0x0003`: KALMAN_STATE (state vector)
- `0x0004`: CONSTRAINT_UPDATE (safety bounds)
- `0x0005`: GPU_COMMAND (kernel launch request)
- `0x0006`: GPU_RESULT (computation output)
- `0x00FF`: ACK (acknowledgment)
- `0x00FE`: NACK (negative acknowledgment)

**Payload Formats:**

**NMEA_DATA:**
```
+0 uint16: sentence_count
+2 uint8[]: NMEA sentences (null-terminated)
```

**SONAR_FRAME:**
```
+0 uint32: timestamp_ms
+4 float32: frequency_hz
+8 float32: range_start_m
+12 float32: range_end_m
+16 uint16: sample_count
+18 float32[]: intensity_samples
```

**GPU_COMMAND:**
```
+0 uint8: kernel_id
+1 uint8: precision_mode (FP32/TF32/FP16)
+2 uint32: input_buffer_addr
+6 uint32: output_buffer_addr
+10 uint16: input_size
+12 uint16: output_size
```

**Connection Establishment:**
```
Client                          Server
  |                               |
  |--- SYN (Magic, Type=HELLO) -> |
  |                               |
  |<- SYN-ACK (Magic, ServerID) --|
  |                               |
  |--- ACK (ClientID) -----------> |
  |                               |
  |<=== ESTABLISHED =============>|
```

**Reliability Features:**
- **Sequence Numbers:** Detect lost or out-of-order messages
- **Checksums:** Simple XOR-16 for payload integrity
- **Retransmission:** NACK triggers resend
- **Flow Control:** Backpressure via window size

**GPU Offload Workflow:**
1. Workstation collects sensor data (NMEA, sonar)
2. Encode into MEP messages
3. Stream to Jetson edge device via TCP/UDP
4. Edge device decodes, launches CUDA kernels
5. GPU results encoded as MEP, streamed back
6. Workstation receives, applies to navigation display

**Constraint Enforcement:**
MEP carries constraint updates (e.g., "no-go zones") to edge GPU, which validates all computations against safety constraints before returning results.

**Provenance:** Forgemaster (protocol design)
**Chain:** MEP bridge test in marine-gpu-edge
