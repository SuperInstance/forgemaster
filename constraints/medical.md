# Medical Devices — Constraint Library (IEC 62304 / ISO 14971)

**Domain:** Medical devices — infusion therapy, patient monitoring, anesthesia, defibrillation
**Standard:** IEC 62304, ISO 14971
**Device Class:** Class III (FDA 510(k)/PMA)
**INT8 Strategy:** FLUX INT8 x8 packing (341B peak, 90.2B sustained constraints/sec)
**Quantization:** `q = clamp(round((v - offset) / scale), 0, 255)` — nonlinear splits where noted
**Highest Update Rate:** 1000 Hz (pump motor, air-in-line, pacer output)
**Key Challenge:** Therapeutic index drugs (digoxin, insulin, heparin) where 2× error is lethal; quantization must preserve 0.1-unit resolution

---

## 1. Infusion Rate — Basal

| Field | Value |
|-------|-------|
| **Name** | `infusion_rate_basal` |
| **Min** | 0.1 mL/h |
| **Max** | 1200 mL/h |
| **Update** | 10 Hz |
| **INT8 Mapping** | offset=0, scale=4.7059 mL/h/bit → q=1 at ~4.7, q=255 at 1200. Nonlinear split: 0–10 mL/h uses expanded 0.1 mL/h/bit sub-range |
| **Safety Rationale** | Insulin underdose → hyperglycemia/diabetic coma; overdose → hypoglycemic seizure/death. PCA opioids: respiratory depression. |
| **Failure Mode** | Peristaltic tubing wear increases occlusion false-negative; flow sensor (ultrasonic) cross-check required. |

## 2. Infusion Rate — Bolus

| Field | Value |
|-------|-------|
| **Name** | `infusion_rate_bolus` |
| **Min** | 0 mL |
| **Max** | 50 mL |
| **Update** | 100 Hz |
| **INT8 Mapping** | offset=0, scale=0.1961 mL/bit → q=0 at 0, q=255 at 50 mL |
| **Safety Rationale** | Bolus volume limit prevents overdose from PCA button abuse or software bug. |
| **Failure Mode** | Stuck keypad causes repeated bolus requests; lockout timer (e.g., 10 min) + FLUX cumulative volume check. |

## 3. Occlusion Pressure

| Field | Value |
|-------|-------|
| **Name** | `occlusion_pressure` |
| **Min** | 0 mmHg |
| **Max** | 800 mmHg |
| **Update** | 100 Hz |
| **INT8 Mapping** | offset=0, scale=3.1373 mmHg/bit → q=0 at 0, q=159 at 500, q=255 at 800 |
| **Safety Rationale** | Distal occlusion (needle clot) causes upstream pressure rise; pump must alarm and stop before container rupture. Typical alarm: 300–500 mmHg. |
| **Failure Mode** | Proximal occlusion (bag spike clamped) indistinguishable from distal without upstream sensor; dual-pressure architecture. |

## 4. Heart Rate — ECG Derived

| Field | Value |
|-------|-------|
| **Name** | `heart_rate_ecg` |
| **Min** | 30 bpm |
| **Max** | 220 bpm |
| **Update** | 1 Hz |
| **INT8 Mapping** | offset=30, scale=0.7451 bpm/bit → q=0 at 30, q=27 at 50, q=161 at 150, q=255 at 220 |
| **Safety Rationale** | Bradycardia <50 bpm: syncope, cardiac arrest. Tachycardia >150 bpm: hemodynamic collapse, ventricular fibrillation threshold. |
| **Failure Mode** | EMI (MRI, diathermy) causes false high rate; common-mode rejection >80 dB required. |

## 5. Heart Rate — SpO2 Plethysmograph

| Field | Value |
|-------|-------|
| **Name** | `heart_rate_spo2` |
| **Min** | 30 bpm |
| **Max** | 220 bpm |
| **Update** | 1 Hz |
| **INT8 Mapping** | Same as ECG |
| **Safety Rationale** | Redundant HR source for arrhythmia detection. Perfusion index affects accuracy. |
| **Failure Mode** | Motion artifact during transport; FLUX flags if ECG/SpO2 discrepancy >20 bpm for >5 s. |

## 6. SpO2 (Oxygen Saturation)

| Field | Value |
|-------|-------|
| **Name** | `spo2` |
| **Min** | 70 % |
| **Max** | 100 % |
| **Update** | 1 Hz |
| **INT8 Mapping** | offset=70, scale=0.1176 %/bit → q=0 at 70%, q=170 at 90%, q=255 at 100% |
| **Safety Rationale** | Hypoxemia <90%: tissue hypoxia, organ damage. Critical threshold for ventilator adjustment or O2 therapy. |
| **Failure Mode** | CO poisoning falsely elevates SpO2 (carboxyhemoglobin read as oxyhemoglobin); ABG lab correlation required. |

## 7. Respiratory Rate

| Field | Value |
|-------|-------|
| **Name** | `respiratory_rate` |
| **Min** | 4 bpm |
| **Max** | 60 bpm |
| **Update** | 1 Hz |
| **INT8 Mapping** | offset=4, scale=0.2196 bpm/bit → q=0 at 4, q=105 at 27, q=255 at 60 |
| **Safety Rationale** | Apnea / respiratory arrest. Opioid-induced respiratory depression: rate drops before SpO2. Early warning. |
| **Failure Mode** | Impedance pneumography artifact from patient movement; ETCO2 capnography preferred for sedation. |

## 8. End-Tidal CO2 (ETCO2)

| Field | Value |
|-------|-------|
| **Name** | `etco2` |
| **Min** | 15 mmHg |
| **Max** | 60 mmHg |
| **Update** | 1 Hz |
| **INT8 Mapping** | offset=15, scale=0.1765 mmHg/bit → q=0 at 15, q=85 at 30, q=255 at 60 |
| **Safety Rationale** | Hypocapnia <30: cerebral vasoconstriction. Hypercapnia >50: respiratory acidosis, narcosis. Ventilator weaning metric. |
| **Failure Mode** | Sampling line condensation; water trap + heated line required. FLUX detects waveform flatline. |

## 9. Invasive Blood Pressure — Systolic

| Field | Value |
|-------|-------|
| **Name** | `ibp_systolic` |
| **Min** | 40 mmHg |
| **Max** | 280 mmHg |
| **Update** | 100 Hz |
| **INT8 Mapping** | offset=40, scale=0.9412 mmHg/bit → q=0 at 40, q=117 at 150, q=255 at 280 |
| **Safety Rationale** | Hypotension: shock, hemorrhage. Hypertension: stroke, myocardial strain. ICU continuous monitoring. |
| **Failure Mode** | Line disconnection reads atmospheric (0 mmHg relative); FLUX must detect damping coefficient change. |

## 10. Invasive Blood Pressure — Diastolic

| Field | Value |
|-------|-------|
| **Name** | `ibp_diastolic` |
| **Min** | 20 mmHg |
| **Max** | 160 mmHg |
| **Update** | 100 Hz |
| **INT8 Mapping** | offset=20, scale=0.5490 mmHg/bit → q=0 at 20, q=64 at 55, q=255 at 160 |
| **Safety Rationale** | Coronary perfusion pressure = diastolic – right-atrial pressure. <50 mmHg: myocardial ischemia. |
| **Failure Mode** | Catheter tip against vessel wall (whip artifact); flush test detects dynamic response. |

## 11. Invasive Blood Pressure — Mean Arterial

| Field | Value |
|-------|-------|
| **Name** | `ibp_map` |
| **Min** | 35 mmHg |
| **Max** | 160 mmHg |
| **Update** | 100 Hz |
| **INT8 Mapping** | offset=35, scale=0.4902 mmHg/bit → q=0 at 35, q=61 at 65, q=255 at 160 |
| **Safety Rationale** | MAP = DBP + 1/3(SBP–DBP). Organ perfusion target: 65–80 mmHg. Sepsis protocol target. |
| **Failure Mode** | Zeroing port left open to atmosphere; FLUX flags MAP <20 as implausible unless hemorrhage context. |

## 12. Non-Invasive BP — Systolic

| Field | Value |
|-------|-------|
| **Name** | `nibp_systolic` |
| **Min** | 60 mmHg |
| **Max** | 280 mmHg |
| **Update** | 0.1 Hz |
| **INT8 Mapping** | offset=60, scale=0.8627 mmHg/bit → q=0 at 60, q=104 at 150, q=255 at 280 |
| **Safety Rationale** | Oscillometric cuff measurement. Cuff too small → false high; too large → false low. |
| **Failure Mode** | Leaky cuff bladder; FLUX detects pressure decay during inflation phase. |

## 13. Non-Invasive BP — Diastolic

| Field | Value |
|-------|-------|
| **Name** | `nibp_diastolic` |
| **Min** | 40 mmHg |
| **Max** | 160 mmHg |
| **Update** | 0.1 Hz |
| **INT8 Mapping** | offset=40, scale=0.4706 mmHg/bit → q=0 at 40, q=32 at 55, q=255 at 160 |
| **Safety Rationale** | Paired with systolic. 5-minute auto-cycle balances patient comfort with monitoring fidelity. |
| **Failure Mode** | Patient movement during measurement; motion rejection algorithm flags invalid cycle. |

## 14. Temperature — Core

| Field | Value |
|-------|-------|
| **Name** | `temperature_core` |
| **Min** | 25 °C |
| **Max** | 45 °C |
| **Update** | 0.1 Hz |
| **INT8 Mapping** | offset=25, scale=0.0784 °C/bit → q=0 at 25°C, q=127 at 35°C, q=255 at 45°C |
| **Safety Rationale** | Hypothermia <35°C: coagulopathy, arrhythmia. Hyperthermia >40°C: heat stroke, enzyme denaturation. |
| **Failure Mode** | Esophageal probe migration into stomach; position verification by auscultation. |

## 15. Temperature — Skin

| Field | Value |
|-------|-------|
| **Name** | `temperature_skin` |
| **Min** | 20 °C |
| **Max** | 42 °C |
| **Update** | 0.1 Hz |
| **INT8 Mapping** | offset=20, scale=0.0863 °C/bit → q=0 at 20°C, q=116 at 30°C, q=255 at 42°C |
| **Safety Rationale** | Peripheral perfusion indicator. Shock: core-skin gradient >4°C. Infant incubator control. |
| **Failure Mode** | Sensor detached; FLUX detects sudden drop to ambient + flag "sensor off". |

## 16. Infusion Pump Motor Current

| Field | Value |
|-------|-------|
| **Name** | `pump_motor_current` |
| **Min** | 0 mA |
| **Max** | 800 mA |
| **Update** | 1000 Hz |
| **INT8 Mapping** | offset=0, scale=3.1373 mA/bit → q=0 at 0, q=64 at 200, q=255 at 800 |
| **Safety Rationale** | Motor current signature: normal flow vs. occlusion vs. air-in-line vs. empty container. Pattern recognition basis. |
| **Failure Mode** | Motor gearbox seizure; current rises but flow absent — FLUX must correlate current with flow sensor. |

## 17. Air-in-Line Sensor

| Field | Value |
|-------|-------|
| **Name** | `air_in_line` |
| **Min** | 0 µL |
| **Max** | 500 µL |
| **Update** | 1000 Hz |
| **INT8 Mapping** | offset=0, scale=1.9608 µL/bit → q=0 at 0, q=26 at 50 (alarm), q=102 at 200 (hard stop), q=255 at 500 |
| **Safety Rationale** | Vascular air embolism threshold: >100 µL/kg can be fatal. Alarm at 50 µL bubble; hard stop at 200 µL cumulative. |
| **Failure Mode** | Ultrasonic coupling gel dries; self-test with known bubble standard at maintenance. |

## 18. Drug Concentration — Insulin (U-100)

| Field | Value |
|-------|-------|
| **Name** | `insulin_concentration` |
| **Min** | 80 U/mL |
| **Max** | 120 U/mL |
| **Update** | 0.01 Hz |
| **INT8 Mapping** | offset=80, scale=0.1569 U/mL/bit → q=0 at 80, q=127 at 100, q=255 at 120 |
| **Safety Rationale** | U-100 = 100 units/mL. U-500 loaded by mistake → 5× overdose. Barcode verification + FLUX concentration range. |
| **Failure Mode** | Vial swap error; pharmacy scan + pump scan double-verify. |

## 19. Anesthetic Agent Concentration (MAC)

| Field | Value |
|-------|-------|
| **Name** | `anesthetic_mac` |
| **Min** | 0.0 MAC |
| **Max** | 2.0 MAC |
| **Update** | 1 Hz |
| **INT8 Mapping** | offset=0, scale=0.0078 MAC/bit → q=0 at 0, q=128 at 1.0, q=255 at 2.0 |
| **Safety Rationale** | MAC = 1.0 at 50% immobility. >1.3 MAC: cardiovascular depression. Awareness risk <0.4 MAC. |
| **Failure Mode** | Vaporizer tipped (transport position); liquid agent dumps into breathing circuit → overdose. |

## 20. PEEP (Positive End-Expiratory Pressure)

| Field | Value |
|-------|-------|
| **Name** | `peep` |
| **Min** | 0 cmH2O |
| **Max** | 25 cmH2O |
| **Update** | 100 Hz |
| **INT8 Mapping** | offset=0, scale=0.0980 cmH2O/bit → q=0 at 0, q=51 at 5, q=255 at 25 |
| **Safety Rationale** | Prevents alveolar collapse. >25 cmH2O: barotrauma, hemodynamic compromise. ARDS protocol: 5–15. |
| **Failure Mode** | Exhalation valve stuck closed; pressure relief valve at 40 cmH2O backup + FLUX alarm. |

## 21. Peak Inspiratory Pressure (PIP)

| Field | Value |
|-------|-------|
| **Name** | `pip` |
| **Min** | 5 cmH2O |
| **Max** | 60 cmH2O |
| **Update** | 100 Hz |
| **INT8 Mapping** | offset=5, scale=0.2157 cmH2O/bit → q=0 at 5, q=116 at 30, q=255 at 60 |
| **Safety Rationale** | Lung protective ventilation: <30 cmH2O. >40: pneumothorax risk. Bronchospasm / mucus plug causes rise. |
| **Failure Mode** | Ventilator circuit kink; FLUX checks PIP vs. PEEP differential (driving pressure). |

## 22. Tidal Volume (VT)

| Field | Value |
|-------|-------|
| **Name** | `tidal_volume` |
| **Min** | 200 mL |
| **Max** | 1200 mL |
| **Update** | 100 Hz |
| **INT8 Mapping** | offset=200, scale=3.9216 mL/bit → q=0 at 200, q=76 at 500, q=255 at 1200 |
| **Safety Rationale** | 6–8 mL/kg ideal body weight for lung protection. >10 mL/kg: volutrauma. |
| **Failure Mode** | Endotracheal tube cuff leak; exhaled volume < inhaled triggers FLUX disconnect alarm. |

## 23. FIO2 (Fraction Inspired Oxygen)

| Field | Value |
|-------|-------|
| **Name** | `fio2` |
| **Min** | 21 % |
| **Max** | 100 % |
| **Update** | 1 Hz |
| **INT8 Mapping** | offset=21, scale=0.3098 %/bit → q=0 at 21%, q=126 at 60%, q=255 at 100% |
| **Safety Rationale** | Premature infants: >60% FIO2 causes retinopathy of prematurity (ROP). Adults: hyperoxia generates free radicals. |
| **Failure Mode** | Oxygen supply pressure loss; FLUX auto-switch to air + alarm. Blender valve failure. |

## 24. Defibrillator Energy

| Field | Value |
|-------|-------|
| **Name** | `defib_energy` |
| **Min** | 0 J |
| **Max** | 360 J |
| **Update** | 10 Hz |
| **INT8 Mapping** | offset=0, scale=1.4118 J/bit → q=0 at 0, q=85 at 120, q=142 at 200, q=255 at 360 |
| **Safety Rationale** | Biphasic: 120–200 J typical. 360 J monophasic for refractory VF. Pediatric: 2–4 J/kg. Overdelivery: myocardial damage. |
| **Failure Mode** | Capacitor aging reduces delivered energy; charge-time monitor detects capacitance decay. |

## 25. Pacemaker Pulse Amplitude

| Field | Value |
|-------|-------|
| **Name** | `pacer_amplitude` |
| **Min** | 0 V |
| **Max** | 10 V |
| **Update** | 1000 Hz |
| **INT8 Mapping** | offset=0, scale=0.0392 V/bit → q=0 at 0, q=51 at 2.0, q=128 at 5.0, q=255 at 10 |
| **Safety Rationale** | Capture threshold: typically 1–3 V. Output programmed to 2× threshold for margin. >10 V: tissue damage / pain. |
| **Failure Mode** | Lead fracture → loss of capture; impedance monitoring + FLUX threshold verification. |

## 26. Pacemaker Pulse Width

| Field | Value |
|-------|-------|
| **Name** | `pacer_width` |
| **Min** | 0.1 ms |
| **Max** | 2.0 ms |
| **Update** | 1000 Hz |
| **INT8 Mapping** | offset=0.1, scale=0.0075 ms/bit → q=0 at 0.1, q=53 at 0.5, q=255 at 2.0 |
| **Safety Rationale** | Strength-duration curve: shorter pulses need higher amplitude. 0.5 ms typical. >2 ms: battery drain, tissue injury. |
| **Failure Mode** | Output capacitor short; pulse width collapses to near-zero → no capture. |

## 27. Patient Weight (Drug Dosing)

| Field | Value |
|-------|-------|
| **Name** | `patient_weight` |
| **Min** | 0.5 kg |
| **Max** | 250 kg |
| **Update** | 0.01 Hz |
| **INT8 Mapping** | offset=0.5, scale=0.9784 kg/bit → q=0 at 0.5, q=51 at 50, q=102 at 100, q=255 at 250 |
| **Safety Rationale** | Dose = mg/kg. Load cell on bed measures continuously for ICU. Wrong weight: 2× overdose possible. |
| **Failure Mode** | Patient supports themselves on side rails; weight artifact. Load cell tare drift. |

## 28. EEG Burst Suppression Ratio

| Field | Value |
|-------|-------|
| **Name** | `burst_suppression` |
| **Min** | 0 % |
| **Max** | 100 % |
| **Update** | 1 Hz |
| **INT8 Mapping** | offset=0, scale=0.3922 %/bit → q=0 at 0%, q=26 at 10%, q=102 at 40%, q=255 at 100% |
| **Safety Rationale** | General anesthesia depth: 0% = awake, 10–40% = adequate, >80% = burst suppression (too deep). Avoids awareness + overdose. |
| **Failure Mode** | Electrocautery interference; notch filter + burst detection algorithm validation. |

---

**Total Constraints:** 28
**SIL Rating:** FDA Class III — PMA with clinical trials; software is SOUP (Software of Unknown Provenance) audited
**FP16 Disqualified:** 76% mismatch rate above 2048; all values natively INT8-safe
