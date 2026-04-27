# 2026-04-27 — Marine GPU Edge Initiative

## Casey Directive (09:49 AKDT)
"Work more on novel and innovative GPU technology that would help our marine edge systems and integrating workstation and edge devices in distribution of computing. You and jetsonclaw1 are on a LAN. Can we do some amazing things that will translate later into better marine system management"

## Follow-up (09:51 AKDT)
"Use Claude Code and Kimi-cli for what they're good for"
"Create good memories for yourself and craft a great claude.md for your coder"

## What I Designed
1. CUDA sensor fusion kernels — NMEA parse, Kalman filter, sonar waterfall, nav constraints
2. Marine Edge Protocol (MEP) — 12-byte binary protocol for GPU offload between workstation↔edge
3. Constraint-aware scheduler — routes GPU tasks based on thermal/power/memory/precision constraints
4. Adaptive precision controller — runtime FP32/FP16/TF32 switching

## Hardware Verified
- CUDA 12.6 nvcc compiles successfully on eileen
- RTX 4050 Ada SM 8.9, Jetson Orin Nano SM 8.7
- jetsonclaw1 NOT reachable by hostname from eileen WSL2 — DNS resolution fails
- Need to figure out LAN connectivity (IP address, mDNS, or static hosts entry)

## Network Investigation
- eileen IP: 172.22.219.126/20 (WSL2 virtual network)
- DNS: 10.255.255.254 (times out)
- No tailscale CLI available in WSL
- Ping/SSH to jetsonclaw1 fails — hostname resolution broken
- Need Casey to provide jetsonclaw1 IP or check Windows host Tailscale

## Files Created
- `/tmp/marine-gpu-edge/src/marine_sensor_fusion.cu` — CUDA kernels (~16KB)
- `/tmp/marine-gpu-edge/src/mep_bridge.cpp` — MEP protocol + scheduler (~16KB)
- `/tmp/marine-gpu-edge/docs/ARCHITECTURE.md` — architecture doc
- `/tmp/marine-gpu-edge/CLAUDE.md` — coder instructions for Claude Code
- MEMORY.md updated with marine GPU initiative section

## Next Steps
1. Spin up Claude Code with CLAUDE.md to build out the project properly
2. Extract shared types into headers
3. Build CMakeLists.txt with cross-compilation
4. Add CUDA_CHECK macros and unit tests
5. Create benchmarks
6. Figure out jetsonclaw1 LAN connectivity
