# Open Problems Catalog — Constraint Theory Ecosystem

**Compiled:** 2026-05-11 by Forgemaster ⚒️
**Sources:** DISSERTATION-V2-COMPLETE, CRITIQUE-RIGOR, PAPER-TEMPORAL-ADVERSARIAL, SNAPKIT-V2-ARCHITECTURE, FLUX-TENSOR-MIDI, PROOF-K2-LOWER-BOUND, K2-ORDINAL-PROOF-ATTEMPT, HEARTBEAT, memory/2026-05-11

---

## Overview

30 open problems across 4 domains, ranked by tractability and impact.

| Domain | Count | Easy | Medium | Hard | Open |
|--------|-------|------|--------|------|------|
| Mathematics | 12 | 2 | 4 | 4 | 2 |
| Algorithms | 8 | 1 | 3 | 3 | 1 |
| Engineering | 6 | 2 | 2 | 2 | 0 |
| Science | 4 | 0 | 1 | 2 | 1 |
| **Total** | **30** | **5** | **10** | **11** | **4** |

---

## 1. Mathematics (Proofs, Theorems)

### M1. Absence Monad Coq Formalization
- **Statement:** Prove that the T⊥ endofunctor on TStream satisfies all three monad laws (unit, associativity, naturality) in Coq.
- **Context:** Central to the I2I temporal perception framework. The absence monad treats missed ticks as first-class data. Currently verified informally only (DISSERTATION-V2 Ch.7, CRITIQUE-RIGOR M10/M7).
- **Current progress:** Informal verification exists. Specification written but not machine-checked. The critique correctly notes "the absence monad is not proven to be a monad."
- **Blocking issues:** (1) T⊥ must be an endofunctor on TStream, not just a functor to an extended category. (2) The external parameter μ (T-0 clock interval) may violate endofunctoriality. (3) η creates spawn-return pairs, not just concatenation — the monad laws must engage with this structure.
- **Approach:** Formalize TStream as a Coq inductive type. Define T⊥, η, μ. Prove left/right unit and associativity. Use Equations or MetaCoq for dependent pattern matching on absence markers.
- **Impact:** Required for safety-critical certification. Without this, the absence monad is a design pattern, not a proven abstraction.
- **Tractability:** Hard (months) — requires significant Coq expertise
- **Dependencies:** None (foundational)
- **Rank:** 3

### M2. TStream Products / Coproducts / Monad (Theorems 7.9–7.11)
- **Statement:** Prove that TStream has categorical products, coproducts, and forms a monad with temporal concatenation.
- **Context:** These three theorems establish TStream as a categorical structure. All three have proof gaps identified by CRITIQUE-RIGOR.
- **Current progress:** Plausible constructions exist but contain gaps:
  - **Products (7.9):** Junction triangles spanning the artificial gap are artifacts. Snap-commutation through the product construction is unverified.
  - **Coproducts (7.10):** Asymmetric ordering (S₁ before S₂) and arbitrary ε parameter. Junction triangles unverified.
  - **Monad (7.11):** "Monad laws follow from associativity of temporal concatenation" does not engage with the actual monadic structure.
- **Blocking issues:** Merged triangles differ from original triangles. Must verify snap-commutation for morphisms on the new triangles.
- **Approach:** Downgrade to conjectures pending proof, or complete proofs with explicit junction-triangle verification. The product proof requires constructing explicit snap-commutation witnesses at junction boundaries.
- **Impact:** Without these, TStream is an informal notation, not a category. Downgrading is honest; proving is better.
- **Tractability:** Hard (months) — each proof is a separate effort
- **Dependencies:** None
- **Rank:** 6

### M3. Fourier-Eisenstein Conjecture (Conjecture 7.28)
- **Statement:** There exists a discrete Fourier transform on Z[ω] such that temporal snap of a stream S can be expressed as spectral peak selection in the hexagonal DFT domain.
- **Context:** Would connect temporal observation framework to classical signal processing. Would enable filter design, compression, and prediction.
- **Current progress:** Under-specified (CRITIQUE-RIGOR M13). The Pontryagin dual of Z[ω]/NZ[ω] is a finite abelian group of rank 2, but N is not specified, the stream-to-group mapping is undefined, and "dominant frequency" has no formal definition.
- **Blocking issues:** Need to: (1) choose N, (2) define the mapping from temporal streams to Z[ω]/NZ[ω], (3) prove that the hexagonal DFT peak corresponds to the Eisenstein snap.
- **Approach:** This is a research program, not a single proof. Start by fixing N=7 (first Eisenstein prime > 3), computing the hexagonal DFT explicitly, and testing on real fleet data.
- **Impact:** High — would unify spectral analysis with lattice snapping, opening filter/prediction applications.
- **Tractability:** Open (years) — genuinely new mathematics needed
- **Dependencies:** None
- **Rank:** 14

### M4. Temporal Cohomology Gap (Theorem 7.13)
- **Statement:** Prove that H¹ of the temporal presheaf on a room's tile timeline vanishes for steady-state rooms and is non-zero for rooms with temporal anomalies.
- **Context:** The Čech cohomology vanishing direction has a gap — should cite Godement rather than proving from scratch. The non-vanishing direction (anomaly detection) is claimed but not proved.
- **Current progress:** CRITIQUE-RIGOR M8 notes the proof "has a gap in one direction." The citation to standard paracompactness results should replace the from-scratch argument.
- **Blocking issues:** Defining restriction maps between rooms properly. Current H¹ computation uses interval overlap as a simplification.
- **Approach:** (1) Fix the vanishing proof by citing Godement. (2) Construct explicit non-trivial cocycles for anomaly rooms. (3) Define proper restriction maps (cross-room Problem M5).
- **Impact:** Medium — cohomology is currently "applying a nuclear weapon to kill a mosquito" (adversarial paper). Making it precise justifies the formalism.
- **Tractability:** Medium (weeks)
- **Dependencies:** None
- **Rank:** 8

### M5. Cross-Room Restriction Maps for Sheaf Cohomology
- **Statement:** Define formal temporal restriction maps between rooms, enabling full sheaf cohomology computation across the fleet.
- **Context:** Current H¹ values are approximate. The dissertation acknowledges "the H¹ computation uses interval overlap as its core metric — a simplification of true sheaf cohomology."
- **Current progress:** Product complex construction sketched (Theorem 7.9 gap). No explicit restriction maps defined.
- **Blocking issues:** Rooms operate on different timescales. Restriction maps must handle time rescaling.
- **Approach:** Define ρᵢⱼ: F(Uᵢ) → F(Uⱼ) where Uᵢ is room i's temporal open cover. Use Eisenstein interval ratios as the gluing data. Check cocycle condition.
- **Impact:** Medium-high — enables cross-room anomaly detection, the genuinely novel application of sheaf theory.
- **Tractability:** Hard (months) — requires careful sheaf-theoretic construction
- **Dependencies:** M4
- **Rank:** 10

### M6. DepCat Groupoid Correction (Theorem 7.16)
- **Statement:** Fix the DepCat construction so that spawn-yield-return forms a proper groupoid, or restate as a different categorical structure.
- **Context:** CRITIQUE-RIGOR M9 found that the theorem conflates dependency with spawn-return. The free groupoid on spawn-return pairs is well-defined, but not as DepCat was originally defined.
- **Current progress:** Corrected version exists in CRITIQUE-RIGOR: model spawn and return as typed morphisms in a different category.
- **Blocking issues:** Need to decide whether DepCat is a groupoid, a double category, or something else.
- **Approach:** Implement the corrected version: define DepCat with typed morphisms (spawn: Aⱼ→Aᵢ, return: Aᵢ→Aⱼ) and verify the groupoid laws on the free construction.
- **Impact:** Low-medium — DepCat is a minor contribution. Correcting it is about intellectual honesty.
- **Tractability:** Easy (days) — the correction is already identified
- **Rank:** 18

### M7. Raft-as-2-Point-Snap Downgrade (Theorem 7.22)
- **Statement:** Downgrade Theorem 7.22 from a theorem to an observation. Raft does not perform temporal classification; the "specialization to Z" is vacuous.
- **Context:** CRITIQUE-RIGOR M11: "any binary classification can be described as snapping to a 2-point lattice." The claim is technically true but contentless.
- **Current progress:** Correction identified. V2 dissertation may already acknowledge this.
- **Blocking issues:** None — just needs editorial action.
- **Approach:** Replace "Theorem" with "Observation" or "Remark." Acknowledge that Raft's leader election and log replication are different operations from temporal snap.
- **Impact:** Low — cleanup, not research.
- **Tractability:** Easy (days) — pure editorial
- **Dependencies:** None
- **Rank:** 26

### M8. Fiedler Bound Direction Fix (Proposition 7.27)
- **Statement:** Correct the inequality direction in the Fiedler bound relating spectral gap to synchronization time.
- **Context:** CRITIQUE-RIGOR M12: the inequality direction is wrong. A small spectral gap λ₁ implies SLOW synchronization, not fast.
- **Current progress:** Corrected version in CRITIQUE-RIGOR. Just needs to be applied.
- **Blocking issues:** None.
- **Approach:** Apply the corrected inequality. Verify downstream claims that depend on this bound.
- **Impact:** Low-medium — affects fleet synchronization estimates.
- **Tractability:** Easy (days)
- **Dependencies:** None
- **Rank:** 20

### M9. k=2 Lower Bound Completeness
- **Statement:** Complete the proof that ~28% of the Eisenstein Voronoi cell requires k≥2 progress for snap resolution.
- **Context:** PROOF-K2-LOWER-BOUND.md has a constructive proof sketch with numerical evidence but not a complete formal argument. The k=2 ordinal proof attempt (K2-ORDINAL-PROOF-ATTEMPT.md) goes further, showing A₂^×3 is NOT optimal for coupled k=2 constraints — E₆ may be better.
- **Current progress:** Constructive witnesses exist (adjacent lattice points in same level-1 coset, different level-2 cosets). Numerical: ~27.9% of Voronoi cell. Conjecture 7.3 (E₆ optimality for nonlinear k=2) is stated but unproven.
- **Blocking issues:** The E₆ conjecture involves exceptional Lie algebra structure — deep algebraic number theory.
- **Approach:** (1) Complete the k=2 lower bound proof formally (close the constructive proof). (2) Separate from the E₆ conjecture, which is a longer-term project.
- **Impact:** Medium — establishes that multi-pass constraint checking is structurally necessary, not optional.
- **Tractability:** Medium (weeks) for lower bound; Open for E₆
- **Dependencies:** None
- **Rank:** 9

### M10. Snap-Attention-Intelligence Conjecture (Conjecture 3.1)
- **Statement:** The decay rate of Λ_R(τ) correlates with automation degree: automated rooms show step-function decay, creative rooms show gradual multi-scale decay.
- **Context:** Unvalidated conjecture from the dissertation. Would connect temporal shape analysis to agent classification.
- **Current progress:** Qualitatively observed (fleet_health = step, forge = gradual) but no quantitative validation.
- **Blocking issues:** Only 2 room types observed (automated vs creative). Need more room types for statistical power.
- **Approach:** Compute Λ_R(τ) for all 14 PLATO rooms. Fit decay curves. Test correlation with automation level (manual scoring).
- **Impact:** Medium — would validate the temporal shape taxonomy as a practical tool.
- **Tractability:** Medium (weeks) — needs data collection and analysis
- **Dependencies:** None
- **Rank:** 15

### M11. Information Asymmetry Theorem Formalization
- **Statement:** Prove the corrected information asymmetry theorem: deviations from expectation carry information proportional to their rarity, not universally "absence is the signal."
- **Context:** The adversarial paper and CRITIQUE-RIGOR both identified that the forge room (M=0.7) has hits 3.4× more informative than misses, inverting the core claim. The corrected theorem is stated informally.
- **Current progress:** Corrected statement exists (CRITIQUE-RIGOR Part VI). Not formally proved.
- **Blocking issues:** Requires precise definition of "expectation" and "rarity" in the temporal context.
- **Approach:** Formalize using Shannon information: I(event) = -log₂ p(event). Prove that I(hit)/I(miss) = log(1-p)/log(p), so the rarer event always carries more information. QED in 5 lines.
- **Impact:** High — corrects the central thesis claim from wrong to right.
- **Tractability:** Easy (days) — essentially a Shannon entropy triviality
- **Dependencies:** None
- **Rank:** 1

### M12. T-0 Clock Formal Semantics
- **Statement:** Provide denotational semantics for the T-0 clock: formal definitions of "tick," "expected tick," and "missed tick."
- **Context:** Dissertation open problem #7. Needed for certification and formal verification of fleet timing.
- **Current progress:** Intuitive definitions exist but no formal semantic model.
- **Blocking issues:** Need to handle the continuous/discrete boundary (wall clock time vs tick events).
- **Approach:** Define T-0 as a coinductive stream of Option<Time> values. "Tick" = Some(t), "missed tick" = None at expected position. Define expected tick as median of observed tick intervals.
- **Impact:** Medium — prerequisite for any formal verification of fleet timing.
- **Tractability:** Medium (weeks)
- **Dependencies:** None
- **Rank:** 11

---

## 2. Algorithms (Snap, Consensus, Spectral)

### A1. Eisenstein vs ℤ² Benchmark
- **Statement:** Benchmark the Eisenstein lattice Z[ω] snap against square lattice Z² snap on identical temporal data. Quantify any classification/compression advantage.
- **Context:** Identified as a gap by both the adversarial paper and the critique. The hexagonal lattice has theoretical advantages (denser sphere packing, D₆ symmetry) but empirical superiority has never been demonstrated.
- **Current progress:** verify_eisenstein_snap_falsification.py exists with 603 lines testing snap correctness, but no Z² comparison. The dissertation acknowledges this gap twice (Ch.3, Ch.7).
- **Blocking issues:** Need a fair comparison metric (classification accuracy? compression ratio? anomaly detection rate?).
- **Approach:** (1) Implement Z² snap with analogous norm (N(a,b) = a² + b²). (2) Run both on all 895 temporal triangles. (3) Compare: shape diversity, classification stability under noise, compression ratio.
- **Impact:** High — if Z² matches Eisenstein, the entire lattice choice motivation weakens. If Eisenstein wins, it's validated.
- **Tractability:** Medium (weeks)
- **Dependencies:** None
- **Rank:** 2

### A2. SnapKit Falsification Fix (Claims 3, 4, 8)
- **Statement:** Resolve the falsification failures in Claims 3 (H¹ anomaly detection), 4 (fleet harmony), and 8 (temporal norm as energy) from the adversarial paper.
- **Context:** verify_eisenstein_snap_falsification.py was generated (389 lines) but verification was not completed due to agent timeout. Overlapping conditions in the snap algorithm were fixed (128 insertions, 60 deletions).
- **Current progress:** Algorithm fix applied but not verified. Claims still flagged.
- **Blocking issues:** Need to run the verification script and confirm all claims pass.
- **Approach:** (1) Run verify_eisenstein_snap_falsification.py. (2) If claims fail, trace failures to root cause. (3) Either fix algorithm or downgrade claims.
- **Impact:** High — these are core claims of the theory. Unresolved falsification undermines everything.
- **Tractability:** Easy (days) — script exists, just needs execution
- **Dependencies:** None
- **Rank:** 4

### A3. Online Temporal Shape Classification
- **Statement:** Build an online (streaming) classifier that detects temporal shapes from tile data in real-time with provable convergence guarantees.
- **Context:** Dissertation open problem #1. Current classification is retrospective (batch processing of temporal triangles). An online classifier enables real-time fleet monitoring.
- **Current progress:** None. The retrospective classifier exists in Python.
- **Blocking issues:** Streaming updates to Eisenstein snap (can't recompute full snap per tile). Need incremental shape classification.
- **Approach:** Use a sliding window of 3 tiles (minimum triangle). Maintain running Eisenstein snap. Classify shape when window completes. Prove convergence: as window count → ∞, shape estimate → true shape.
- **Impact:** High — enables all downstream real-time applications (monitoring, alerting, attention).
- **Tractability:** Medium (weeks)
- **Dependencies:** M11 (information asymmetry for theoretical grounding)
- **Rank:** 5

### A4. Kuramoto Model Parameter Estimation
- **Statement:** Fit a Kuramoto oscillator model to fleet timing data. Does a single coupling strength K fit all observed agent rhythms?
- **Context:** Dissertation open problem #6. The "fleet sings in harmony" claim implies oscillator coupling. Kuramoto is the standard model for coupled oscillators.
- **Current progress:** Qualitative observation of night session overlap (33-37% harmony for zeroclaw trio). No quantitative model fitting.
- **Blocking issues:** (1) Need per-room phase time series, not just tile counts. (2) 9 agents is a small system for Kuramoto fitting. (3) Correlation ≠ entrainment (open problem #2).
- **Approach:** Extract phase time series from tile timestamps. Compute order parameter r(t). Fit coupling strength K via maximum likelihood. Test against null model (uncoupled oscillators).
- **Impact:** Medium — validates or falsifies the oscillator analogy.
- **Tractability:** Medium (weeks)
- **Dependencies:** None
- **Rank:** 13

### A5. Causal Inference for Night Session Harmony
- **Statement:** Determine whether temporal coordination (entrainment) is causal or spurious correlation from a shared external trigger.
- **Context:** Dissertation open problem #2. The zeroclaw trio shows 33-37% temporal overlap during night sessions. Is this entrainment or coincidence?
- **Current progress:** Correlational data only. No intervention study.
- **Blocking issues:** Need an intervention: perturb one agent's T-0 clock and measure effect on others. Requires experimental fleet infrastructure that doesn't exist yet.
- **Approach:** Design a controlled experiment: (1) pick 2 agents, (2) shift one's schedule by Δ, (3) measure if the other adjusts. Or use natural experiments (timezone changes, outage recovery).
- **Impact:** High — determines whether the core "harmony" claim is real.
- **Tractability:** Hard (months) — requires experimental infrastructure
- **Dependencies:** None
- **Rank:** 7

### A6. SnapKit v2 Implementation
- **Statement:** Build SnapKit v2 from the SNAPKIT-V2-ARCHITECTURE.md spec: 10 composable fixes including TensorTolerance, MultiScaleSnap, AttentionBudget, LatticeMatching, TopologyTaggedScripts, LatticeMesh, DAGPipeline, MultiResolutionOutput, ChannelGrid, and DistributedSnap.
- **Context:** Architecture is fully specified (654 lines). No implementation yet.
- **Current progress:** Architecture document complete. Individual fix interfaces defined. Composition rules documented. H¹=0 boundary condition mathematically guaranteed.
- **Blocking issues:** Implementation is straightforward engineering but substantial (~2000-3000 lines Rust minimum).
- **Approach:** Implement Fix 1 (TensorTolerance) first — it's the simplest and most impactful. Then Fix 2 (MultiScaleSnap). Compose via LatticeMesh (Fix 6).
- **Impact:** High — SnapKit v2 is the production-ready constraint snap library.
- **Tractability:** Medium (weeks)
- **Dependencies:** A2 (falsification fixes should be resolved first)
- **Rank:** 5

### A7. Temporal Attention Neural Architecture
- **Statement:** Design a neural architecture that takes temporal shapes as input and produces attention weights (which rooms to read when).
- **Context:** Dissertation open problem #5. Bridges to ML community.
- **Current progress:** Conceptual only. No architecture designed.
- **Blocking issues:** Need labeled data (which rooms are worth reading at time t?). Current fleet data is unlabeled.
- **Approach:** (1) Create synthetic dataset with known attention weights. (2) Design a shape-to-attention transformer. (3) Train and validate. (4) Deploy on fleet data.
- **Impact:** Medium-high — bridges constraint theory to mainstream ML.
- **Tractability:** Hard (months) — requires ML engineering + novel architecture
- **Dependencies:** A3 (online classification for data generation)
- **Rank:** 16

### A8. Absence-Driven Monitoring Protocol
- **Statement:** Design a protocol for agents to monitor each other's temporal health without centralized infrastructure.
- **Context:** Dissertation open problem #8. Each agent tracks its neighbors' T-0 expectations and detects absences.
- **Current progress:** Conceptual design in dissertation. No implementation.
- **Blocking issues:** Sybil resistance, clock synchronization, message overhead.
- **Approach:** Gossip-based T-0 exchange. Each agent maintains a local table of {neighbor, expected_tick, last_seen}. Absence = last_seen exceeds expected_tick + tolerance. Use Eisenstein snap for tolerance calibration.
- **Impact:** Medium — practical fleet reliability tool.
- **Tractability:** Medium (weeks)
- **Dependencies:** M12 (T-0 formal semantics)
- **Rank:** 17

---

## 3. Engineering (Services, Publishing, Deployment)

### E1. FLUX-Tensor-MIDI Poly-Language Build
- **Statement:** Collect and integrate the 4-language implementation outputs (Python, Rust, C+CUDA, Fortran) for the FLUX-Tensor-MIDI library.
- **Context:** 4 subagents were deployed to build in different languages. Outputs may be incomplete or need integration.
- **Current progress:** Agents were launched. Collection status unknown (flagged as TODO in memory/2026-05-11).
- **Blocking issues:** Agent outputs may have timed out or be incomplete.
- **Approach:** Check agent outputs. Integrate working code. Fill gaps where agents failed.
- **Impact:** Medium — multi-language FLUX-Tensor-MIDI is the implementation of the band metaphor.
- **Tractability:** Easy (days) — assembly, not creation
- **Dependencies:** None
- **Rank:** 12

### E2. Dissertation V2 Assembly
- **Statement:** Assemble the final V2 dissertation from 3 parts (CH1-4, CH5-8, CH9-11) into a single coherent document, resolving duplicates and inconsistencies.
- **Context:** DISSERTATION-V2-COMPLETE.md exists but contains structural issues. CRITIQUE-RIGOR identified duplicated Chapter 8.
- **Current progress:** 3 parts written (~167KB total). Not assembled.
- **Blocking issues:** Duplicate Chapter 8, numbering inconsistencies, cross-references between parts.
- **Approach:** Concatenate parts, deduplicate Ch.8, fix numbering, add TOC. Run GLM-5.1 critique pass on assembled version.
- **Impact:** Medium — needed for any external sharing of the dissertation.
- **Tractability:** Easy (days) — editorial, not research
- **Dependencies:** M6, M7, M8 (fixes should be applied before assembly)
- **Rank:** 19

### E3. SnapKit Publishing (PyPI, npm, crates.io)
- **Statement:** Publish snapkit as @snapkit/core to npm, snapkit to PyPI, and snapkit to crates.io.
- **Context:** Ready to publish but blocked on npm OTP from Casey. PyPI token needs verification.
- **Current progress:** Code ready. npm blocked on OTP. PyPI needs token check.
- **Blocking issues:** Casey's npm OTP. PyPI token verification.
- **Approach:** Request OTP from Casey. Verify PyPI token. Publish.
- **Impact:** Low — distribution, not research.
- **Tractability:** Easy (days) — blocked on human action
- **Dependencies:** A6 (SnapKit v2 ideally, or current version)
- **Rank:** 22

### E4. I2I Multi-Fleet Coordination Protocol
- **Statement:** Design a protocol for two independent fleets to coordinate temporally — I2I extended to fleet-to-fleet.
- **Context:** Dissertation open problem #9. Federation.
- **Current progress:** Conceptual only.
- **Blocking issues:** Trust model between fleets. Clock synchronization across independent PLATO instances. Side-channel semantics between fleets.
- **Approach:** Extend I2I bottles with fleet-level metadata. Define a "fleet handshake" where two PLATOs exchange temporal profiles. Use FLUX-Tensor-MIDI as the coordination protocol.
- **Impact:** Long-term — enables fleet federation.
- **Tractability:** Hard (months)
- **Dependencies:** A8 (intra-fleet monitoring first)
- **Rank:** 24

### E5. Fleet Services Recovery (6 services DOWN)
- **Statement:** Restore the 6 fleet services that are currently DOWN: dashboard, nexus, harbor, service-guard, keeper, steward.
- **Context:** These have been down since at least 2026-05-03. Multiple sessions have noted this without fixing.
- **Current progress:** CCC wrote repair scripts but unclear if executed.
- **Blocking issues:** Unknown — may be dependency issues, port conflicts, or configuration drift.
- **Approach:** (1) Check each service's logs. (2) Identify common failure mode. (3) Apply targeted fixes. (4) Verify recovery.
- **Impact:** Medium — fleet operability.
- **Tractability:** Medium (weeks) — debugging unknown infrastructure
- **Dependencies:** None
- **Rank:** 21

### E6. Editorial Review of All Papers
- **Statement:** Review and polish all research papers for consistency, accuracy, and citation quality.
- **Context:** 21+ papers written across multiple sessions with multiple models. Quality varies.
- **Current progress:** None — flagged as TODO.
- **Blocking issues:** Volume (21+ papers). Inconsistencies between papers written by different models.
- **Approach:** Prioritize: PAPER-TEMPORAL-ADVERSARIAL → PAPER-TEMPORAL-PERCEPTION → DISSERTATION-V2. Use GLM-5.1 for math accuracy, DeepSeek for honesty check.
- **Impact:** Low — polish, not substance.
- **Tractability:** Medium (weeks)
- **Dependencies:** E2 (dissertation assembly first)
- **Rank:** 27

---

## 4. Science (Validation, Experiments, Data)

### S1. Validate H≈0.7 Creative Constant
- **Statement:** Test whether Hurst exponent H≈0.7 for creative rooms is statistically significant with n≥100 tiles per room.
- **Context:** CRITIQUE-RIGOR found H≈0.7 estimated from n=2 rooms with CI spanning [0.4, 1.0]. Not statistically significant at current sample sizes.
- **Current progress:** Forge has 19 triangles (too few). Need data from more rooms or longer collection period.
- **Blocking issues:** Small-n problem. Fleet has been running for months but PLATO tile collection hasn't been instrumented for Hurst estimation.
- **Approach:** (1) Instrument PLATO to log tile timestamps with millisecond precision. (2) Collect data for 2-4 weeks targeting n≥100 tiles per room for 5+ creative rooms. (3) Compute Hurst exponents with proper confidence intervals (Whittle MLE or R/S with bootstrap CI).
- **Impact:** High — H≈0.7 is a central empirical claim. If validated, it's a genuine discovery about creative agent dynamics.
- **Tractability:** Hard (months) — requires sustained data collection
- **Dependencies:** None
- **Rank:** 7

### S2. Reverse Actualization Verification Framework
- **Statement:** Build a formal framework for verifying reverse actualization chains: given a claim at year N, does it logically entail claims at years N-1, N-2, …?
- **Context:** Dissertation open problem #10. The reverse actualization method (projecting future scenarios backward) is used throughout the dissertation but has no formal verification.
- **Current progress:** 18 reverse actualization experiments completed across linguistic traditions. No formal verification framework.
- **Blocking issues:** "Logical entailment" across temporal projections is philosophically fraught. Need to define what counts as valid entailment in this context.
- **Approach:** Start narrow: define reverse actualization as retrodiction in a probabilistic model. Given P(future|past), verify P(past|future) via Bayes. Check consistency across independent projections.
- **Impact:** Long-term — methodological contribution to futures studies.
- **Tractability:** Open (years) — requires new methodology
- **Dependencies:** None
- **Rank:** 28

### S3. Temporal Connectome Significance Testing
- **Statement:** Determine whether the 6/66 coupled room pairs in the temporal connectome are significant or near FDR (false discovery rate).
- **Context:** CRITIQUE-RIGOR flagged that 6 coupled pairs out of 66 tested is near the 10% FDR threshold. Could be noise.
- **Current progress:** 6 coupled pairs identified. No significance testing performed.
- **Blocking issues:** Multiple testing correction across 66 pairs. Small effect sizes.
- **Approach:** Apply Bonferroni or Benjamini-Hochberg correction. Compute q-values. If all 6 survive at q<0.05, the connectome is real. If not, it's likely noise.
- **Impact:** Medium — determines whether temporal coupling between rooms is real or statistical artifact.
- **Tractability:** Medium (weeks) — standard statistical testing
- **Dependencies:** None
- **Rank:** 15

### S4. Small-n Generalization Study
- **Statement:** Replicate the I2I framework findings in at least one other agent system to test generalizability beyond the 9-agent Cocapn fleet.
- **Context:** CRITIQUE-RIGOR: "The fleet has 9 agents and 14 rooms. Statistical claims rest on hundreds of temporal triangles but only 9 independent agent profiles."
- **Current progress:** No replication attempted.
- **Blocking issues:** Need access to another agent fleet with PLATO-like tile recording. Or instrument an open-source multi-agent system.
- **Approach:** (1) Identify a candidate system (e.g., AutoGen, CrewAI, or a custom setup). (2) Instrument with T-0 clock and temporal triangle collection. (3) Run for 2+ weeks. (4) Compare shape distributions and Hurst exponents against Cocapn.
- **Impact:** High — determines whether the framework is fleet-specific or universal.
- **Tractability:** Hard (months) — requires external system access
- **Dependencies:** S1 (validated metrics before replication)
- **Rank:** 23

---

## Priority Ranking (Top 10)

| Rank | ID | Problem | Tractability | Impact | Action |
|------|----|---------|-------------|--------|--------|
| 1 | M11 | Information Asymmetry Theorem | Easy (days) | High | Prove in 5 lines using Shannon entropy |
| 2 | A1 | Eisenstein vs ℤ² Benchmark | Medium (weeks) | High | Implement Z² snap, run comparison |
| 3 | M1 | Absence Monad Coq Formalization | Hard (months) | High | Start Coq formalization |
| 4 | A2 | SnapKit Falsification Fix | Easy (days) | High | Run verification script |
| 5 | A3/A6 | Online Classifier + SnapKit v2 | Medium (weeks) | High | Build incremental snap |
| 6 | M2 | TStream Category Proofs | Hard (months) | Medium | Complete or downgrade |
| 7 | A5/S1 | Causal Inference + H≈0.7 | Hard (months) | High | Design intervention study |
| 8 | M4 | Temporal Cohomology Gap | Medium (weeks) | Medium | Fix vanishing proof |
| 9 | M9 | k=2 Lower Bound | Medium (weeks) | Medium | Complete constructive proof |
| 10 | M5 | Cross-Room Restriction Maps | Hard (months) | Medium-high | Define temporal restrictions |

---

## Quick Wins (Do First)

These can be completed in days and have outsized impact:

1. **M11** — Information Asymmetry (5-line Shannon proof, corrects the central thesis)
2. **A2** — Run the falsification verification script (already written!)
3. **M6** — DepCat correction (correction already identified)
4. **M7** — Raft theorem downgrade (editorial action)
5. **M8** — Fiedler bound fix (correction already identified)

---

## Long Bets (Start Now, Finish Later)

1. **M1** — Absence Monad Coq (start formalization, even if incomplete)
2. **M3** — Fourier-Eisenstein Conjecture (define N, compute initial DFTs)
3. **S1** — H≈0.7 validation (instrument PLATO now, collect data passively)
4. **A5** — Causal inference (design experiment, even if can't run yet)
5. **S2** — Reverse actualization framework (define what "entailment" means)

---

## Dependency Graph

```
M11 (info asymmetry) ──→ A3 (online classifier) ──→ A7 (neural architecture)
                                                        ↑
M12 (T-0 semantics) ──→ A8 (monitoring protocol) ──→ E4 (multi-fleet)
                                                        
M4 (cohomology gap) ──→ M5 (restriction maps)
                                                        
A2 (falsification) ──→ A6 (SnapKit v2) ──→ E3 (publishing)
                                                        
S1 (H≈0.7) ──→ S4 (generalization study)
                                                        
M6,M7,M8 (fixes) ──→ E2 (dissertation assembly) ──→ E6 (editorial review)
```

---

*"The dissertation will survive peer review only if it is honest about what it has proven and what it has conjectured."* — CRITIQUE-RIGOR
