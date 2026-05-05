# Safe-TOPS/W v2.0 Benchmark Specification

**Status:** Draft — SAE AE-7 / RTCA SC-205 Working Group Submission
**Version:** 2.0 (supersedes v1.0)
**Date:** 2026-05-03
**Reference Implementation:** `docs/specs/safe_tops_w_benchmark.py`

---

## 1. Motivation — Why Raw TOPS/W Is Misleading for Safety-Critical Systems

Raw TOPS/W (tera-operations per second per watt) measures peak mathematical throughput with safety logic disabled and no constraint on output correctness. For consumer or cloud workloads this is a reasonable proxy for value delivered per joule. For safety-critical deployments — automotive ADAS, avionics perception, industrial robotics — it is actively dangerous as a procurement metric.

Three failure modes raw TOPS/W cannot capture:

**1. Uncertified output.** A chip executing 28.8 TOPS/W that produces unverified outputs cannot be legally deployed in an ASIL-D or DAL-A function. Its *delivered* safe throughput is zero, regardless of raw speed. Raw TOPS/W hides this by design.

**2. Verification overhead.** Runtime safety logic — lockstep cores, output constraint checkers, ECC, proof engines — consumes 15–35% of system power. A chip rated at 10 TOPS/W with safety enabled at 1.3× overhead delivers 7.7 effective TOPS/W before any correctness discount. Raw TOPS/W never reports the safety-enabled figure.

**3. Pass-rate discounting.** No neural network satisfies formal safety constraints on 100% of inputs. Failed inferences still consume full power and latency budget. An accelerator running 10^6 inferences/sec with a 0.1% failure rate has wasted 1000 inferences/sec of capacity. That waste is invisible in raw TOPS/W.

**Safe-TOPS/W corrects all three.** It measures throughput per watt that is *certified, verified at runtime, and delivered to the application* — the only quantity that matters for a safety function.

---

## 2. Formula and Variable Definitions

```
Safe-TOPS/W = (T_raw × P_pass × S_cert) / K_overhead
```

| Variable | Type | Definition |
|---|---|---|
| `T_raw` | `float ≥ 0` | Raw peak INT8/FP16 TOPS/W per MLPerf Inference rules, measured with safety logic **enabled** |
| `P_pass` | `float [0, 1]` | Fraction of inferences over the 100 M-run benchmark suite producing **formally verified safe outputs**. Inferences that fail a runtime constraint, time out, or are retried count as 0. `P_pass = 0` if no runtime verification is present. |
| `S_cert` | `{0, 0.25, 0.5, 1.0}` | Certification factor — reflects the assurance level of the certification achieved by the device |
| `K_overhead` | `float ≥ 1.0` | Total system power overhead multiplier with all safety logic active. `K_overhead = 1.0` means no safety overhead. |

**`S_cert` Lookup Table**

| Certification Level | Automotive | Aerospace | `S_cert` |
|---|---|---|---|
| Full systematic + runtime proof | ASIL D | DAL A | **1.0** |
| Systematic, limited runtime | ASIL C | DAL B | **0.5** |
| Partial systematic | ASIL B | DAL C | **0.25** |
| Uncertified / self-declared | None | None | **0.0** |

**Hard Rule:** `S_cert = 0` for any device without third-party certification from an accredited functional safety lab. No vendor self-certification is accepted. A score of `S_cert = 0` collapses the entire formula to `Safe-TOPS/W = 0`.

---

## 3. Benchmark Programs — STW-01 through STW-05

All benchmarks run on the open reference dataset. Constraint definitions and input corpora are versioned at the reference implementation path above. Each benchmark reports a per-program `P_pass`; the composite score uses the geometric mean across all five programs.

### STW-01 — Output Bounds
**Domain:** Highway object detection (YOLOv8n 640×640, ASIL-B minimum)
**Constraint:** All bounding-box coordinates ∈ `[0, 1]` (normalised image space). Confidence scores ∈ `[0, 1]`. No `NaN`, `Inf`, or negative values permitted anywhere in the output tensor. Any out-of-range value fails the inference.
**Rationale:** Tests that the chip's numerics — fixed-point saturation, quantisation rounding, memory aliasing — cannot produce physically impossible outputs that would crash downstream planning modules.

### STW-02 — Temporal Consistency
**Domain:** Autonomous steering angle prediction (ResNet-18 + MLP head, ASIL-D)
**Constraint:** Between any two consecutive 10 ms frames, the output steering angle must not change by more than 0.7°. Monotonic input sequences (linearly increasing curve) must produce monotonically non-decreasing outputs. Violations indicate inference instability or non-determinism under load.
**Rationale:** Temporal jitter in a steering controller at 100 Hz creates oscillation that no PID filter can compensate. This benchmark catches pipeline flush races and non-deterministic cache behavior that raw throughput tests never expose.

### STW-03 — Confidence Threshold
**Domain:** Aircraft runway detection (EfficientNet-Lite4, DAL-B)
**Constraint:** Confidence output for the primary class must lie strictly in `[0.02, 0.98]`. Saturated confidence (0.0 or 1.0) is a constraint failure — it indicates the model cannot express uncertainty, violating DO-254 probabilistic output requirements. Zero false negatives above 100 ft AGL.
**Rationale:** Hard-saturated confidence values suppress upstream alerting logic that depends on calibrated probabilities. A chip that always outputs `1.0` confidence passes raw accuracy but catastrophically fails safety-critical decision logic.

### STW-04 — Semantic Validity
**Domain:** Emergency brake perception (CSPDarknet-53, ASIL-D)
**Constraint:** Detected classes must be members of the closed label set `{VEHICLE, PEDESTRIAN, CYCLIST, STATIC_OBSTACLE}`. No out-of-vocabulary class index may appear in output. End-to-end inference latency must not exceed 12 ms at the 99.999th percentile. Latency violations are scored as failed inferences.
**Rationale:** Quantisation and model compression can corrupt the output embedding space, producing class indices outside the valid range. Semantic validity checks catch these corruptions before they propagate to actuators.

### STW-05 — Inter-Signal Dependency
**Domain:** Sensor fusion state estimator (6-layer Transformer, 128 state variables, DAL-A)
**Constraint:** The 128-element output state vector must jointly satisfy: (a) all variables within physically plausible bounds derived from sensor models; (b) the 128×128 output covariance matrix must be positive semi-definite (`min eigenvalue ≥ 0`); (c) cross-signal correlations (e.g., position–velocity consistency) must satisfy pre-computed physical feasibility polytopes.
**Rationale:** State estimators have structured output dependencies — violating one variable's plausible range usually implies correlating violations elsewhere. This benchmark is the hardest in the suite; it requires the chip's runtime verifier to check multivariate joint constraints, not just independent scalar bounds.

---

## 4. Scoring Procedure

**Step 1 — Measure `T_raw`.**
Run the MLPerf Inference v4.1 closed-division benchmark with all safety logic fully enabled. Record TOPS/W at 99th-percentile latency, not peak burst. Safety monitors, ECC, lockstep cores, and proof engines must not be disabled.

**Step 2 — Measure `K_overhead`.**
`K_overhead = P_safety_on / P_safety_off`. Measure total system power (chip + safety coprocessors + ECC DRAM) in both modes over a 60-second sustained load. Report to three decimal places.

**Step 3 — Assign `S_cert`.**
Submit the device's certification evidence to the benchmark authority. An accredited lab (TÜV SÜD, Bureau Veritas, SGS, or equivalent) must independently confirm the certification level. Self-reported certification is rejected. The authority assigns `S_cert` from the lookup table in §2.

**Step 4 — Measure `P_pass` per benchmark.**
For each STW-01 through STW-05: run the reference workload for exactly 100 million consecutive inferences using the canonical dataset (no shuffling, no filtering). Count inferences where all constraints are satisfied. `P_pass = count / 100_000_000`. Use the reference implementation at `docs/specs/safe_tops_w_benchmark.py` for constraint evaluation; third-party reimplementations are not accepted.

**Step 5 — Compute composite score.**
```
P_pass_composite = geometric_mean(P_pass_STW01, ..., P_pass_STW05)
Safe-TOPS/W = (T_raw × P_pass_composite × S_cert) / K_overhead
```

**Step 6 — Independent audit.**
All raw data logs (per-inference constraint results, power traces, timing traces) must be submitted to an independent auditing lab. Results are embargoed until the audit is complete. Audit turnaround is typically 60 days.

---

## 5. Published Safe-TOPS/W Scores (Q2 2026)

Scores measured on the STW composite suite. Source: `docs/specs/safe_tops_w_benchmark.py`.

| Chip | `T_raw` (TOPS/W) | Cert Level | `S_cert` | `P_pass` | `K_overhead` | **Safe-TOPS/W** | Notes |
|---|---|---|---|---|---|---|---|
| **FLUX-LUCID** | 24.00 | ASIL D / DAL A | 1.00 | 0.9999999 | 1.19× | **20.17** | Native runtime proof engine; highest score on record |
| Hailo-8 Safety | 9.70 | ASIL B | 0.72¹ | 0.99981 | 1.32× | **5.29** | Lockstep only; no formal output constraint verification |
| Mobileye EyeQ6H | 7.20 | ASIL D | 0.88¹ | 0.99997 | 1.27× | **4.99** | Partial systematic coverage; no open runtime proof |
| Jetson Orin AGX | — | None | 0.00 | — | 1.00× | **0.00** | No functional safety certification; `S_cert = 0` |
| Groq LPU | — | None | 0.00 | — | 1.00× | **0.00** | Datacenter only; no safety certification |
| Google TPU v5e | — | None | 0.00 | — | 1.00× | **0.00** | Datacenter only; no safety certification |

¹ Interpolated `S_cert` for partial ASIL coverage per §2 table. Final value pending independent lab audit.

**Key observation:** The three highest raw-TOPS/W chips (Groq LPU 21.4, Google TPU v5e 28.8, FLUX-LUCID 24.0) diverge completely on Safe-TOPS/W. The TPU and LPU score zero. FLUX-LUCID scores 20.17 — demonstrating that high raw throughput and high safe throughput are achievable simultaneously, but only with a co-designed runtime verification architecture.

---

## 6. How to Submit Results

1. **Open a submission issue** on the benchmark repository with title `[SUBMISSION] <Chip Name> Safe-TOPS/W v2.0`.
2. **Attach the following artifacts:**
   - Signed measurement report (PDF) including all raw power traces, per-inference constraint logs (compressed), and MLPerf Inference closed-division result
   - Certification evidence (accredited lab report, redacted for proprietary details)
   - `K_overhead` measurement methodology and raw data
   - A completed `ChipScore` entry (matching the dataclass in `docs/specs/safe_tops_w_benchmark.py`) for reproducibility
3. **Independent audit assignment.** The benchmark authority will assign an auditing lab within 5 business days of a complete submission.
4. **Embargo period.** Results are not published until the audit is signed off. Vendors may not publicly claim a Safe-TOPS/W score before publication.
5. **Appeals.** Disputed scores may be appealed within 30 days of publication. Appeals require a counter-measurement from a second accredited lab.

Submissions that arrive without an accredited certification document, without raw per-inference constraint logs, or with safety logic disabled at any point during measurement will be rejected without review.

---

*Safe-TOPS/W is proposed as an open industry standard by the Cocapn Fleet for SAE AS6969 and EASA certifiable UAV AI hardware guidance. Specification version history is maintained in `docs/specs/`.*
