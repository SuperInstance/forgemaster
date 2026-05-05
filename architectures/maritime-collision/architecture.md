## Agent 7: Maritime Collision Avoidance System

**Domain:** Autonomous / unmanned surface vessel (USV) and manned ship navigation
**Architect:** Agent 7 (Maritime Systems & IMO Compliance)

### System Block Diagram

```
+------------------------------------------------------------------+
|              MARITIME COLLISION AVOIDANCE SYSTEM (MCAS)             |
|                    FLUX Constraint Engine                         |
+------------------------------------------------------------------+
|                                                                   |
|  +-------------------------------------------------------------+|
|  |                    PERCEPTION FUSION LAYER                   ||
|  |                                                              ||
|  |  +----------------+  +----------------+  +----------------+ ||
|  |  |   RADAR        |  |    AIS         |  |   EO/IR CAMERA | ||
|  |  |  (X-band, S-band)|  |  (VHF, Class A)|  |  (day/night)   | ||
|  |  |  ARPA tracking |  |  ship database |  |  horizon detection||
|  |  +--------+-------+  +--------+-------+  +--------+-------+ ||
|  |           |                  |                  |           ||
|  |           v                  v                  v           ||
|  |  +--------+-------+  +--------+-------+  +--------+-------+ ||
|  |  |   LiDAR        |  |   SONAR        |  |   WEATHER      | ||
|  |  |  (obstacle,    |  |  (bathymetry,  |  |  (wind, waves, | ||
|  |  |   coastline)    |  |  depth)         |  |  visibility)   | ||
|  |  +--------+-------+  +--------+-------+  +--------+-------+ ||
|  |           |                  |                  |           ||
|  |           v                  v                  v           ||
|  |  +---------------------------------------------------------+||
|  |  |    NVIDIA Jetson Orin NX (16GB) — FLUX Engine          |||
|  |  |    Constraint checking + path planning + COLREG reasoning |||
|  |  +---------------------------------------------------------+||
|  +-------------------------------------------------------------+|
|                                                                   |
|  +-------------------------------------------------------------+|
|  |                    NAVIGATION & CONTROL OUTPUT                 ||
|  |    Autopilot / DP  |  ECDIS display  |  VDR / black box   ||
|  +-------------------------------------------------------------+|
|                                                                   |
|  +-------------------------------------------------------------+|
|  |                    BACKUP AIS AUTONOMOUS CHANNEL               ||
|  |    Standalone AIS-based CPA/TCPA calculator (ARM Cortex-M4)   ||
|  |    Independent power, independent GPS, independent VHF       ||
|  +-------------------------------------------------------------+|
|                                                                   |
+------------------------------------------------------------------+
```

### Constraint Budget

| Constraint Category | Count | Type | Update Rate | Source |
|---------------------|-------|------|-------------|--------|
| CPA / TCPA limits (per target) | 1,800 | Range (INT8) | 10 Hz | Radar + AIS fusion |
| COLREG rule compliance (stand-on/give-way) | 600 | Enum/Boolean | 10 Hz | Relative motion + rules |
| Safe speed for conditions | 400 | Range (INT8) | 10 Hz | Weather + visibility |
| Depth contour clearance | 600 | Range (INT8) | 10 Hz | Sonar + ENC chart |
| Traffic separation scheme (TSS) | 400 | Geofence | 10 Hz | ENC + GPS |
| Restricted area / no-go zones | 300 | Geofence/Enum | 10 Hz | ENC + regulatory |
| Weather envelope (wind, wave, vis) | 200 | Range (INT8) | 10 Hz | Weather sensors + forecast |
| Maneuverability limits (turn radius, stopping) | 300 | Range (FP16-safe) | 10 Hz | Ship hydrodynamic model |
| Route waypoint adherence | 200 | Range (INT8) | 10 Hz | GPS + planned route |
| Man overboard / emergency hold | 300 | Boolean | 10 Hz | Manual + sensor triggers |
| **TOTAL** | **5,100** | Mixed | 10 Hz | — |

At 10 Hz with 5,100 constraints: 51,000 evaluations/sec. Jetson Orin NX (1024 CUDA cores, ~60B constraints/sec) provides **1,000,000x headroom**. This extreme margin supports high-resolution trajectory prediction (Monte Carlo simulation of 100 futures per cycle) and continuous self-diagnostics.

### Hardware Selection

**Primary: NVIDIA Jetson Orin NX (16 GB)**
- **GPU:** 1024 CUDA cores, INT8 x8 packing supported
- **CPU:** 8-core Cortex-A78AE
- **Memory:** 16 GB LPDDR5 (102 GB/s bandwidth)
- **TDP:** 15W-25W configurable
- **I/O:** Gigabit Ethernet, USB 3.2, M.2 for NVMe logging

**Justification:**
1. **Massive compute headroom:** 60B constraints/sec vs 51K needed. Allows real-time trajectory optimization ( Model Predictive Control) with 100-step horizon, evaluating thousands of candidate paths per control cycle.
2. **Marine environmental:** Orin NX available in conduction-cooled variants. -25C to +80C operating range with appropriate enclosure. Salt spray, humidity managed via IP67 sealed housing.
3. **AI perception:** CUDA supports radar tracking, camera-based horizon detection, and AIS fusion neural networks alongside FLUX constraint engine.
4. **Low power:** 15-25W enables continuous operation on ship's 24V DC without dedicated cooling. Solar/battery backup viable for USVs.

**Backup: Standalone AIS processor (NXP i.MX RT1170 dual-core Cortex-M7/M4)**
- Independent GPS + VHF AIS receiver
- Calculates CPA/TCPA independently of primary system
- Battery-backed, always on
- Triggers audible alarm if primary and backup disagree

### Latency Budget Breakdown

| Stage | Time | Cumulative | Notes |
|-------|------|------------|-------|
| Radar sweep (X-band, 12 rpm) | 5,000 ms | 5,000 ms | Full 360° scan, ARPA track update |
| AIS message reception (VHF TDMA) | 2,000 ms | 5,000 ms | Slot-based, worst-case 2s update |
| Sensor fusion + track association | 20 ms | 5,020 ms | Multi-hypothesis tracking |
| FLUX constraint execution (5.1K @ 10Hz) | 0.1 ms | 5,020 ms | GPU kernel, negligible |
| COLREG reasoning + path planning | 50 ms | 5,070 ms | Rule-based + optimization |
| Autopilot command generation | 10 ms | 5,080 ms | NMEA 0183/2000 to autopilot |
| Autopilot servo response | 500 ms | — | Hydraulic steering gear |
| **TOTAL (perception + decision)** | **~95 ms** | — | Meets COLREG "constant watch" requirement |
| **TOTAL (to rudder response)** | **< 1 s** | — | Meets safe stopping distance for 20 kt vessel |

Maritime collision avoidance is not microseconds-critical — ship dynamics are slow (hundreds of meters stopping distance, seconds to minutes for maneuvers). The constraint is **decision quality**, not latency. FLUX's throughput supports extensive "what-if" simulation before committing to maneuvers.

### Redundancy Strategy

**Architecture: Dual with independent AIS backup**

| Element | Implementation |
|---------|---------------|
| Primary | Jetson Orin NX — full perception + FLUX + path planning |
| Secondary | Identical Jetson Orin NX, cold standby, watchdog-activated |
| Backup | NXP i.MX RT1170 — standalone AIS CPA/TCPA calculator, independent GPS/VHF |
| Cross-check | Primary and backup must agree on "dangerous target" boolean within 5 seconds |
| Degraded | Loss of primary -> backup AIS provides basic collision warning; manual steering |
| Navigation | Independent GPS receiver (u-blox ZED-F9P) on each channel, plus ship's INS |
| Power | 24V ship's main + 24V emergency + battery backup (4 hours) |

**Rationale:** Maritime regulations (COLREG, SOLAS) do not require automated collision avoidance on manned vessels — human watchkeeping remains primary. The system is decision-support + autonomous backup. Dual-channel with independent AIS ensures no single point of failure can disable collision warnings. Cold standby acceptable because human operator provides continuity.

### Power Budget

| Component | Power (W) | Notes |
|-----------|-----------|-------|
| Jetson Orin NX (primary) | 20 | Full compute, 100% duty |
| Jetson Orin NX (secondary, standby) | 3 | Low-power monitor mode |
| NXP i.MX RT1170 (AIS backup) | 1 | Always on, battery-backed |
| Radar interface (X-band processor) | 15 | ARPA tracking, includes magnetron |
| AIS transponder (Class A) | 8 | Transmit + receive, VHF PA |
| EO/IR camera + processor | 8 | Day/night, image stabilization |
| Sonar / echosounder | 5 | Bathymetry, 200 kHz |
| Weather station (wind, temp, pressure) | 2 | Ultrasonic anemometer |
| Ethernet switch (marine grade) | 4 | Managed, NMEA 2000 gateway |
| GPS receiver (multi-band) x3 | 2 | u-blox ZED-F9P |
| Display / ECDIS interface | 10 | Bridge display, touch |
| Marine enclosure (IP67, conduction) | 5 | Sealed, fanless, thermal |
| DC-DC (24V -> 12V/5V/3.3V) | 4 | Efficiency losses |
| **TOTAL** | **87 W** | — |
| FLUX compute specifically | ~6 W | GPU kernel @ 15% utilization |

### Certification Path

| Standard | Level | Approach |
|----------|-------|----------|
| IEC 61508 | SIL 2 | Systematic capability SC2, HFT=1 |
| IEC 61924 | — | Maritime navigation and radiocommunication equipment |
| IMO MSC.1/Circ.1638 | — | Guidelines for autonomous ship trials (MASS) |
| SOLAS Ch V | — | Safety of navigation, bridge equipment |
| COLREG (72) | — | International Regulations for Preventing Collisions at Sea |
| DNV Rules for Classification | — | Autonomous and remotely operated vessels |

**FLUX-specific certification argument:**
- **COLREG formalization:** GUARD DSL can express COLREG rules (Rules 4-19) as explicit constraints. Formal proofs ensure rules are implemented exactly as written, not approximated by neural networks.
- **Explainability:** Every FLUX constraint violation has explicit cause (e.g., "CPA < 0.5 NM with target MMSI 123456789"). Supports incident investigation and liability determination.
- **Deterministic scheduling:** Fixed 10 Hz constraint cycle. Bridge crew can rely on consistent system behavior, not unpredictable AI inference times.

### Estimated Cost

| Cost Item | Amount (USD) |
|-----------|-------------|
| Jetson Orin NX x2 | $1,200 |
| NXP i.MX RT1170 + support | $300 |
| Radar interface / ARPA processor | $4,500 |
| AIS Class A transponder | $2,500 |
| EO/IR camera (marine stabilized) | $3,500 |
| Sonar / echosounder | $2,000 |
| Weather station | $800 |
| Marine Ethernet switch | $600 |
| GPS receivers x3 | $450 |
| Bridge display (marine sunlight) | $2,000 |
| IP67 enclosure + thermal | $1,200 |
| Cabling + marine connectors | $1,200 |
| BOM subtotal | **$20,250** |
| NRE (COLREG modeling, DNV classification) | $180,000 |
| Sea trials + validation | $120,000 |
| **Total per vessel (amortized NRE over 50 units)** | **$18,000** |
| Total at fleet volume (500 vessels) | **$12,000** |

---