# Commercial Aircraft FMS — Constraint Budget

| Constraint Category | Count | Type | Update Rate | Source |
|---------------------|-------|------|-------------|--------|
| Flight envelope (VMO, MMO, alpha) | 800 | Range (INT8) | 50 Hz | Air data + inertial |
| Navigation integrity (RNP, ANP) | 600 | Range (INT8) | 50 Hz | GNSS + IRS |
| Engine limits (N1, N2, EGT, EPR) | 1,200 | Range (INT8) | 50 Hz | FADEC ARINC 429 |
| Fuel system (imbalance, temp, qty) | 400 | Range (INT8) | 10 Hz | Fuel probes |
| Landing configuration (flaps, gear) | 300 | Enum/Range | 50 Hz | Proximity sensors |
| Terrain clearance (TAWS) | 500 | Range (INT8) | 5 Hz | Terrain database + GPS |
| TCAS resolution advisories | 200 | Enum | 1 Hz (event) | TCAS processor |
| Weight & balance (CG envelope) | 200 | Range (FP16-safe) | 10 Hz | Load sensors + fuel |
| Weather avoidance | 400 | Geofence | 10 Hz | Weather radar + SIGMET |
| ATC constraint compliance | 400 | Enum/Range | 5 Hz | CPDLC + FMS path |
| **TOTAL** | **5,000** | Mixed | 5-50 Hz | — |

Worst-case evaluation rate: 5,000 constraints × 50 Hz = 250,000 evaluations/sec. FPGA implementation targets 50M constraints/sec (200x headroom).
