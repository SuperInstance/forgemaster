# Nuclear — Constraint Library (IEC 61513 / IEEE 603)

**Domain:** Nuclear I&C — PWR plant protection, reactor trip, ESFAS, process control
**Standard:** IEC 61513, IEEE 603
**Safety Integrity:** SIL 3 (<1e-7 dangerous failure probability per demand; 2oo3 or 2oo4 architecture)
**INT8 Strategy:** FLUX INT8 x8 packing (341B peak, 90.2B sustained constraints/sec)
**Quantization:** `q = clamp(round((v - offset) / scale), 0, 255)` — logarithmic mapping for neutron flux
**Highest Update Rate:** 100 Hz (RCP vibration)
**Key Challenge:** Logarithmic power mapping across 10 decades while preserving sub-critical monitoring resolution
**Criticality:** Highest consequence domain — violation can lead to core damage, radioactive release, off-site consequences

---

## 1. Reactor Power — Neutron Flux (Linear)

| Field | Value |
|-------|-------|
| **Name** | `neutron_flux_linear` |
| **Min** | 0 % RTP |
| **Max** | 125 % RTP |
| **Update** | 10 Hz |
| **INT8 Mapping** | offset=0, scale=0.4902 %/bit → q=0 at 0%, q=204 at 100%, q=255 at 125%. Headroom reserved for trip setpoint |
| **Safety Rationale** | >100%: departure from nucleate boiling (DNB) risk. >120%: automatic reactor trip. |
| **Failure Mode** | Detector cable break (source range); negative rate trip on power reduction + FLUX positive flux validation. |

## 2. Reactor Power — Neutron Flux (Logarithmic)

| Field | Value |
|-------|-------|
| **Name** | `neutron_flux_log` |
| **Min** | -5.0 decades |
| **Max** | +0.3 decades |
| **Update** | 10 Hz |
| **INT8 Mapping** | offset=-5.0, scale=0.0212 decades/bit → q=0 at -5.0, q=236 at 0, q=255 at +0.3. Nonlinear: log10(power) mapping |
| **Safety Rationale** | Source range startup: 1e-4% to 1e-1%. Log power covers 10 decades; subcritical multiplication monitoring. |
| **Failure Mode** | Detector saturation at high power; automatic switch to linear power channel. |

## 3. Reactor Coolant Temperature — Hot Leg

| Field | Value |
|-------|-------|
| **Name** | `coolant_temp_hot_leg` |
| **Min** | 250 °C |
| **Max** | 350 °C |
| **Update** | 1 Hz |
| **INT8 Mapping** | offset=250, scale=0.3922 °C/bit → q=0 at 250°C, q=179 at 320°C (nominal), q=255 at 350°C |
| **Safety Rationale** | Hot leg ~320°C nominal. >343°C: high pressurizer temperature trip. >350°C: structural limits. |
| **Failure Mode** | Thermowell vibration fatigue; RTD redundancy: 3× per leg, 2oo3 voting. |

## 4. Reactor Coolant Temperature — Cold Leg

| Field | Value |
|-------|-------|
| **Name** | `coolant_temp_cold_leg` |
| **Min** | 250 °C |
| **Max** | 330 °C |
| **Update** | 1 Hz |
| **INT8 Mapping** | offset=250, scale=0.3137 °C/bit → q=0 at 250°C, q=128 at 290°C (nominal), q=255 at 330°C |
| **Safety Rationale** | Cold leg ~290°C nominal. ΔT (hot–cold) ~30°C measures core power. Sudden ΔT rise = voiding or boron dilution. |
| **Failure Mode** | Grid frequency transient causes pump speed change; FLUX must correlate with turbine/generator speed. |

## 5. Core ΔT (Temperature Rise)

| Field | Value |
|-------|-------|
| **Name** | `core_delta_t` |
| **Min** | 15 °C |
| **Max** | 65 °C |
| **Update** | 1 Hz |
| **INT8 Mapping** | offset=15, scale=0.1961 °C/bit → q=0 at 15°C, q=76 at 30°C, q=255 at 65°C |
| **Safety Rationale** | Core power calorimetric measure. ΔT low at constant flow = power reduction. ΔT high = overpower or flow reduction. |
| **Failure Mode** | Cold leg sensor drift hot; FLUX checks against heat balance from steam generator output. |

## 6. Pressurizer Pressure

| Field | Value |
|-------|-------|
| **Name** | `pressurizer_pressure` |
| **Min** | 120 bar |
| **Max** | 180 bar |
| **Update** | 10 Hz |
| **INT8 Mapping** | offset=120, scale=0.2353 bar/bit → q=0 at 120, q=128 at 150 (nominal), q=255 at 180 |
| **Safety Rationale** | Maintains coolant liquid state. Low pressure: boiling/voiding in core. High pressure: RCS boundary rupture. |
| **Failure Mode** | Pressure transmitter impulse line blockage; redundant pressure taps + periodic blowdown. |

## 7. Pressurizer Level

| Field | Value |
|-------|-------|
| **Name** | `pressurizer_level` |
| **Min** | 15 % |
| **Max** | 85 % |
| **Update** | 1 Hz |
| **INT8 Mapping** | offset=0, scale=0.3333 %/bit → q=45 at 15%, q=170 at 57%, q=255 at 85% |
| **Safety Rationale** | RCS inventory buffer. Low: loss of coolant accident (LOCA). High: water hammer / spray nozzle flooding. |
| **Failure Mode** | DP level instrument reference leg drain; FLUX compares with pressurizer weight + temperature compensation. |

## 8. Steam Generator Level — Narrow Range

| Field | Value |
|-------|-------|
| **Name** | `sg_level_narrow` |
| **Min** | 20 % |
| **Max** | 80 % |
| **Update** | 1 Hz |
| **INT8 Mapping** | offset=0, scale=0.3137 %/bit → q=64 at 20%, q=128 at 40%, q=255 at 80% |
| **Safety Rationale** | Level control for heat removal. Low: uncover tubes → tube overheating + rupture. High: carryover to turbine blades. |
| **Failure Mode** | Level swell during rapid depressurization (shrink/swell inverse response); feedwater control must anticipate. |

## 9. Steam Generator Pressure

| Field | Value |
|-------|-------|
| **Name** | `sg_pressure` |
| **Min** | 40 bar |
| **Max** | 85 bar |
| **Update** | 1 Hz |
| **INT8 Mapping** | offset=40, scale=0.1765 bar/bit → q=0 at 40, q=128 at 63, q=255 at 85 |
| **Safety Rationale** | Secondary side pressure. Safety valves lift at 87 bar. Low: turbine trip + loss of heat sink. |
| **Failure Mode** | Main steam line break; pressure drops → high reactor coolant ΔT → overpower trip + safety injection. |

## 10. Reactor Coolant Pump (RCP) Speed

| Field | Value |
|-------|-------|
| **Name** | `rcp_speed` |
| **Min** | 800 rpm |
| **Max** | 1200 rpm |
| **Update** | 10 Hz |
| **INT8 Mapping** | offset=800, scale=1.5686 rpm/bit → q=0 at 800, q=128 at 1000, q=255 at 1200 |
| **Safety Rationale** | 4-loop PWR: 4 RCPs at 1200 rpm. Coastdown on loss of power provides ~30 s of forced flow. Seal failure at overspeed. |
| **Failure Mode** | VFD fault; seal injection pressure must be maintained during coastdown. |

## 11. Reactor Coolant Pump (RCP) Vibration

| Field | Value |
|-------|-------|
| **Name** | `rcp_vibration` |
| **Min** | 0 mm/s |
| **Max** | 7.5 mm/s |
| **Update** | 100 Hz |
| **INT8 Mapping** | offset=0, scale=0.0294 mm/s/bit → q=0 at 0, q=153 at 4.5 (alarm), q=255 at 7.5 |
| **Safety Rationale** | Bearing degradation / shaft crack detection. >4.5 mm/s: alarm. >7.5 mm/s: automatic pump trip. |
| **Failure Mode** | Cavitation from low NPSH; FLUX correlates vibration with suction pressure + temperature. |

## 12. Control Rod Position — Bank D (Shutdown)

| Field | Value |
|-------|-------|
| **Name** | `rod_position_bank_d` |
| **Min** | 0 % |
| **Max** | 100 % |
| **Update** | 10 Hz |
| **INT8 Mapping** | offset=0, scale=0.3922 %/bit → q=0 at 0%, q=128 at 50%, q=255 at 100% |
| **Safety Rationale** | Full insertion (100%) = reactor subcritical. Withdrawal during startup only with flux rate monitoring. |
| **Failure Mode** | Rod drift (seal failure, hydraulic leak); FLUX checks rod position vs. demand + flux response. |

## 13. Control Rod Position — Bank A (Regulating)

| Field | Value |
|-------|-------|
| **Name** | `rod_position_bank_a` |
| **Min** | 0 % |
| **Max** | 100 % |
| **Update** | 10 Hz |
| **INT8 Mapping** | Same as Bank D |
| **Safety Rationale** | Regulating bank for load follow. Control band: 20–80%. Out of band = inappropriate control strategy. |
| **Failure Mode** | Rod step counter miscount; redundant LVDT (Linear Variable Differential Transformer) per rod. |

## 14. Boric Acid Concentration

| Field | Value |
|-------|-------|
| **Name** | `boron_concentration` |
| **Min** | 0 ppm |
| **Max** | 2500 ppm |
| **Update** | 0.1 Hz |
| **INT8 Mapping** | offset=0, scale=9.8039 ppm/bit → q=0 at 0, q=26 at 250, q=153 at 1500, q=255 at 2500 |
| **Safety Rationale** | Chemical shim for reactivity control. Dilution during dilution accident reduces shutdown margin. |
| **Failure Mode** | Makeup tank isolation valve leak; FLUX monitors boron mass balance vs. volume control tank level. |

## 15. Containment Pressure

| Field | Value |
|-------|-------|
| **Name** | `containment_pressure` |
| **Min** | 0 bar(g) |
| **Max** | 5.0 bar(g) |
| **Update** | 1 Hz |
| **INT8 Mapping** | offset=0, scale=0.0196 bar/bit → q=0 at 0, q=128 at 2.5, q=255 at 5.0 |
| **Safety Rationale** | Design basis accident: main steam line break or LOCA. Peak ~4.5 bar. Containment integrity prevents release. |
| **Failure Mode** | Containment isolation valve failure to close; FLUX auto-close signal + manual override capability. |

## 16. Containment Radiation — Gamma

| Field | Value |
|-------|-------|
| **Name** | `containment_gamma` |
| **Min** | 0 Gy/h |
| **Max** | 10,000 Gy/h |
| **Update** | 1 Hz |
| **INT8 Mapping** | offset=0, scale=39.2157 Gy/h/bit → q=0 at 0, q=3 at 100, q=26 at 1000, q=255 at 10,000 |
| **Safety Rationale** | Post-LOCA radiation level indicates fuel clad integrity. >100 Gy/h: fuel damage suspected. >1000: core melt. |
| **Failure Mode** | Detector saturation during severe accident; wide-range + high-range dual detector architecture. |

## 17. Steam Generator Tube Rupture (SGTR) — Activity

| Field | Value |
|-------|-------|
| **Name** | `sgtr_activity` |
| **Min** | 0 Bq/mL |
| **Max** | 100,000 Bq/mL |
| **Update** | 0.1 Hz |
| **INT8 Mapping** | offset=0, scale=392.1569 Bq/mL/bit → q=0 at 0, q=1 at 10, q=3 at 1000, q=255 at 100,000 |
| **Safety Rationale** | Primary-to-secondary leak detected by noble gas activity in steam line. >10 Bq/mL: alarm. >1000: SGTR isolation. |
| **Failure Mode** | Background radiation fluctuation; trend analysis (doubling time) more reliable than absolute threshold. |

## 18. Reactor Vessel Head Level (Flooding)

| Field | Value |
|-------|-------|
| **Name** | `vessel_head_level` |
| **Min** | 0 % |
| **Max** | 100 % |
| **Update** | 1 Hz |
| **INT8 Mapping** | offset=0, scale=0.3922 %/bit → q=0 at 0%, q=128 at 50%, q=255 at 100% |
| **Safety Rationale** | Cavity flooding for severe accident management (in-vessel retention). Level must cover core for external cooling. |
| **Failure Mode** | Debris blockage of sump; FLUX compares multiple level taps + pump suction pressure. |

## 19. Emergency Diesel Generator (EDG) Speed

| Field | Value |
|-------|-------|
| **Name** | `edg_speed` |
| **Min** | 0 rpm |
| **Max** | 900 rpm |
| **Update** | 50 Hz |
| **INT8 Mapping** | offset=0, scale=3.5294 rpm/bit → q=0 at 0, q=204 at 720 (60 Hz), q=255 at 900 |
| **Safety Rationale** | 4 kV safety power on loss of offsite power (LOOP). Underspeed = underfrequency loads trip. |
| **Failure Mode** | Fuel oil filter clog; FLUX monitors lube oil pressure + cooling water temp for pre-trip diagnostics. |

## 20. Emergency Diesel Generator (EDG) Voltage

| Field | Value |
|-------|-------|
| **Name** | `edg_voltage` |
| **Min** | 3.6 kV |
| **Max** | 4.4 kV |
| **Update** | 50 Hz |
| **INT8 Mapping** | offset=3600, scale=3.1373 V/bit → q=0 at 3.6 kV, q=128 at 4.0 kV, q=255 at 4.4 kV |
| **Safety Rationale** | 4 kV ±10% for safety loads. Undervoltage: motor starting torque insufficient. Overvoltage: insulation stress. |
| **Failure Mode** | AVR (Automatic Voltage Regulator) failure; manual excitation control backup. |

## 21. Safety Injection Flow Rate

| Field | Value |
|-------|-------|
| **Name** | `safety_injection_flow` |
| **Min** | 0 kg/s |
| **Max** | 500 kg/s |
| **Update** | 10 Hz |
| **INT8 Mapping** | offset=0, scale=1.9608 kg/s/bit → q=0 at 0, q=64 at 125, q=255 at 500 |
| **Safety Rationale** | SI pumps inject borated water on LOCA signal. 4 trains × 125 kg/s each. Must prove flow to core. |
| **Failure Mode** | Pump cavitation from low suction pressure; FLUX must throttle recirc flow to maintain NPSH. |

## 22. Residual Heat Removal (RHR) Flow

| Field | Value |
|-------|-------|
| **Name** | `rhr_flow` |
| **Min** | 0 kg/s |
| **Max** | 800 kg/s |
| **Update** | 1 Hz |
| **INT8 Mapping** | offset=0, scale=3.1373 kg/s/bit → q=0 at 0, q=80 at 250, q=255 at 800 |
| **Safety Rationale** | Post-shutdown decay heat removal. 1% of full power (~30 MW) must be rejected continuously for days. |
| **Failure Mode** | Heat exchanger tube fouling; FLUX monitors RHR inlet/outlet temperature differential. |

## 23. Containment Isolation Valve Position

| Field | Value |
|-------|-------|
| **Name** | `containment_isolation` |
| **Min** | 0 % (closed) |
| **Max** | 100 % (open) |
| **Update** | 1 Hz |
| **INT8 Mapping** | Binary: q<10 = closed, q>245 = open, 10–245 = indeterminate/alarm. Discrete 0/255 mapping |
| **Safety Rationale** | CIVs must close within 5 s of isolation signal. Partial closure = leakage path. Limit switch + torque switch. |
| **Failure Mode** | Valve motor burnout; FLUX uses torque switch signature to detect mechanical binding. |

## 24. Excore Neutron Detector — Current

| Field | Value |
|-------|-------|
| **Name** | `excore_detector_current` |
| **Min** | 1e-12 A |
| **Max** | 1e-3 A |
| **Update** | 10 Hz |
| **INT8 Mapping** | Logarithmic: `q = clamp(255 × (log10(I) + 12) / 9, 0, 255)`. q=0 at 1e-12, q=170 at 1e-6, q=255 at 1e-3 |
| **Safety Rationale** | Fission chambers and BF3 proportional counters span 9 decades. Source range: 1e-12 A. Power range: 1e-6 A. |
| **Failure Mode** | Cable insulation degradation increases leakage current; baseline offset compensation required. |

---

**Total Constraints:** 24
**SIL Rating:** SIL 3 — <1e-7 dangerous failure probability per demand; 2oo3 or 2oo4 voting architecture
**FP16 Disqualified:** 76% mismatch rate above 2048; all values natively INT8-safe
**Logarithmic Handling:** Neutron flux (log) and excore detector use log10-based INT8 mapping — unique to nuclear domain
