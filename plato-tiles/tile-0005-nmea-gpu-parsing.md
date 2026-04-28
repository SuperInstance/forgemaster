# NMEA Sentence GPU Parsing

**Core Concept:** NMEA (National Marine Electronics Association) sentences are ASCII-encoded navigation data streams. GPU parsing achieves massive parallelism by processing multiple sentences concurrently across thousands of threads.

**NMEA Sentence Structure:**
```
$GPGGA,092750.000,5321.6802,N,00630.3372,W,1,8,1.03,61.7,M,55.2,M,,*76
$GPGLL,5321.6802,N,00630.3372,W,092750.000,A*4A
```
Format: `$<talker><sentence type>,<data>*<checksum>`

**Parsing Challenges:**
- Variable-length sentences (30-80 bytes typical)
- Comma-delimited fields
- Hex checksum validation
- Floating-point coordinate conversion (DDMM.MMMM → decimal degrees)
- Multiple concurrent streams (GPS, AIS, depth, wind, heading)

**GPU Parsing Strategy:**
- **Input Coalescing:** Load 32 bytes per warp into shared memory
- **Thread-Per-Character:** Each thread handles one character position
- **Field Boundary Detection:** Comma tracking via warp shuffle
- **Parallel Checksum:** XOR reduction across sentence
- **SIMD Conversion:** Float parsing using digit-by-digit expansion

**Optimization Techniques:**
- **Memory Alignment:** Pad input to 128-byte boundaries
- **Register Spilling:** Keep hot fields in registers
- **Warp Primitives:** Use `__ballot()` for comma positions
- **Prefetching:** Double-buffer next chunk while processing current

**Performance (RTX 4050):**
- 179.7M sentences/second peak
- ~5.5 ns per sentence
- 32 concurrent streams per kernel launch
- Memory bandwidth: ~350 GB/s (near theoretical 360 GB/s)

**Constraint Connection:**
Parsed NMEA feeds constraint-based navigation safety systems. Position, velocity, and heading constraints evaluated in real-time across GPU threads using constraint propagation.

**Integration with Kalman Filter:**
Parsed data streams directly into Kalman prediction step without CPU-GPU transfer, enabling end-to-end sensor fusion on GPU.

**Provenance:** Forgemaster (marine-gpu-edge benchmarks)
**Chain:** SuperInstance/marine-gpu-edge bench_nmea target
