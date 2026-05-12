# Fleet Level-Up Suggestions — Forgemaster ⚒️

Date: 2026-05-07
Source: Combined analysis from infrastructure audit, synergy audit, and red-team response

---

## Priority 1: CRITICAL (Do This Week)

### 1. Fix 3 Wrong READMEs
- **Who:** Oracle1
- **Impact:** HIGH
- **Effort:** SMALL (30 minutes)
- **What:** fleet-health-monitor, quality-gate-stream, fleet-murmur all have JetsonClaw1 READMEs
- **Rationale:** Anyone discovering these repos will be confused. First impression matters.
- **Action:** Replace with correct content describing each service

### 2. Build DivergenceAwareTolerance (Runtime→Compile Feedback Loop)
- **Who:** Forgemaster + Oracle1
- **Impact:** HIGH (upgrades 4+ MEDIUM synergy pairs to HIGH)
- **Effort:** LARGE
- **What:** Oracle1 detects drift, resonance anomalies, health issues → feeds back into FM's constraint engine to adjust tolerances and recompile
- **Rationale:** This is the biggest gap in the fleet. FM proves theorems and compiles constraints. Oracle1 monitors runtime behavior. But nothing connects them. If Oracle1 sees drift in production, FM's tolerances should tighten automatically.
- **Dependencies:** PLATO integration layer, intent-inference real implementation
- **Architecture:**
  ```
  Oracle1 fleet-health-monitor → PLATO "drift_detected" tile
  FM reads drift tiles → adjusts IntentVector tolerances
  FM recompiles with tighter bounds → pushes to PLATO
  Oracle1 verifies new constraints → cycle continues
  ```

### 3. Wire ZeroClaw to Holonomy-Consensus
- **Who:** Oracle1
- **Impact:** HIGH
- **Effort:** SMALL
- **What:** Replace zeroclaw's simple majority voting with holonomy-consensus ZHC (Zero-message Holonomy Consensus)
- **Rationale:** ZHC is strictly superior — zero voting overhead, zero messages, Byzantine-tolerant by construction. ZeroClaw keeps divergence tracking (its strength), imports ZHC for consensus (FM's strength).
- **Dependencies:** holonomy-consensus crate (already published to crates.io)

---

## Priority 2: HIGH (Do This Sprint)

### 4. Publish eisenstein v0.2.0 to crates.io
- **Who:** Forgemaster
- **Impact:** MEDIUM
- **Effort:** SMALL
- **What:** Euclidean division, GCD, D6 rotations, hex distance, unit checks (just implemented, 25 tests)
- **Rationale:** Makes the "zero-drift hexagonal" claim mathematically complete. Z[ω] is now a proven Euclidean domain in our implementation.

### 5. Flesh Out constraint-inference + intent-inference
- **Who:** Oracle1
- **Impact:** HIGH
- **Effort:** MEDIUM
- **What:** Replace stubs with real implementations:
  - constraint-inference: monitor override behavior, infer unstated constraints
  - intent-inference: use FM's 9-channel IntentVector to reverse-engineer productive lane
- **Rationale:** These are HIGH-synergy connectors between FM's math and Oracle1's operations. Currently they're empty shells.
- **Dependencies:** FM's polyformalism-a2a-python (IntentVector API)

### 6. Merge the Two Agent Shells
- **Who:** Oracle1
- **Impact:** MEDIUM
- **Effort:** SMALL
- **What:** Merge smart-agent-shell (streaming, checkpointing) into python-agent-shell (PLATO integration). Kill the weaker one.
- **Rationale:** Two shells with overlapping features = maintenance burden and confusion.
- **Recommendation:** python-agent-shell as the base (PLATO integration matters more), add streaming from smart-agent-shell

### 7. Address Red Team Attack #4 (Temporal Snap)
- **Who:** Forgemaster
- **Impact:** HIGH
- **Effort:** MEDIUM
- **What:** Either formalize temporal snap with proper posets, maps, and unit/counit conditions — or remove it and mark as "open problem"
- **Rationale:** Red team correctly identified this as cargo cult math. Either make it rigorous or be honest about its status.
- **Action:** Write formal version with explicit poset definitions, or publish as "conjecture with counterexamples"

### 8. Address Red Team Attack #5 (Tonnetz Errors)
- **Who:** Forgemaster
- **Impact:** MEDIUM
- **Effort:** SMALL
- **What:** Correct the documented errors in eisenstein/hex-zhc:
  - 24-bit norm bound is wrong (50M > 2²⁴)
  - D6 orbit count is 13 not 11
  - Laman redundancy is asymptotic, not exact
- **Rationale:** These errors are documented internally but not corrected in main docs. Red team found them because we left them unfixed.

---

## Priority 3: MEDIUM (Next Sprint)

### 9. Standardize TLV Protocol or Use Protobuf
- **Who:** Oracle1
- **Impact:** MEDIUM
- **Effort:** MEDIUM
- **What:** zeroclaw-plato uses custom TLV binary protocol. Either document it fully as a fleet standard, or switch to protobuf/msgpack.
- **Rationale:** Custom protocols need custom parsers in every language. Fleet has Rust, Python, JS, TypeScript — standard serialization saves effort.

### 10. PLATO Quality Pass
- **Who:** Oracle1
- **Impact:** MEDIUM
- **Effort:** LARGE
- **What:** Run quality audit on PLATO tiles:
  - Identify rooms where tiles don't reference each other (low integration)
  - Merge/consolidate duplicate tiles
  - Kill rooms with accumulated noise
  - Replace tile count metric with "actionable knowledge density" metric
- **Rationale:** Previous audit noted 18K+ tiles with many near-zero integration rooms. Volume ≠ value.

### 11. Cross-Reference Negative Knowledge Across Fleet
- **Who:** Oracle1
- **Impact:** MEDIUM
- **Effort:** SMALL
- **What:** Add negative knowledge citations to:
  - constraint-inference (override detection IS negative knowledge)
  - zeroclaw (drift detection IS knowing where violations are NOT)
  - fleet-topology (missing edges ARE negative knowledge)
- **Rationale:** Synergy audit found negative knowledge is underexploited on Oracle1 side. The principle applies everywhere but isn't referenced.

### 12. Fleet Resonance Benchmarks
- **Who:** Oracle1 + FM
- **Impact:** MEDIUM
- **Effort:** MEDIUM
- **What:** Run fleet-resonance TAP→RING→CONTRAST on actual fleet decision outputs. Show it reveals structure that plain analysis misses.
- **Rationale:** Fleet-resonance is the best-designed new repo (Grade: A) but has no empirical validation yet.

### 13. Intent-Holonomy (B)⟹(A) Proof Completion
- **Who:** Forgemaster
- **Impact:** MEDIUM (closes the main open proof gap)
- **Effort:** LARGE
- **What:** The (B)⟹(A) direction of the Intent-Holonomy Duality needs fixed-point strengthening. Currently at 30% confidence.
- **Rationale:** Red team noted this is "triple-dead" — we already know it's broken. Either prove it or publish as "counterexample to conjecture" (negative knowledge!)

---

## Priority 4: NICE TO HAVE (Backlog)

### 14. Unified Fleet Dashboard
- **Who:** Oracle1
- **Impact:** MEDIUM
- **Effort:** LARGE
- **What:** Fix the dashboard (down since May 4) and integrate all services: health, murmurs, resonance, zeroclaw drift
- **Dependencies:** 6 down services need repair first

### 15. cocapn-ai-web Live Demos
- **Who:** Oracle1
- **Impact:** LOW (visibility)
- **Effort:** MEDIUM
- **What:** Get browser demos running: captain deliberation, thinking strategies, PLATO protocol
- **Rationale:** Great for presentations and onboarding, but not critical path

### 16. npm Publish polyformalism-a2a-js
- **Who:** Forgemaster
- **Impact:** LOW
- **Effort:** SMALL
- **What:** Token needs refresh, then `npm publish`
- **Dependencies:** npm token refresh

---

## Fleet Strength Assessment

After addressing all suggestions:

| Dimension | Current | After |
|-----------|---------|-------|
| Mathematical rigor | B (proven core, speculative shell) | A- (honest about what's proven vs conjecture) |
| Infrastructure quality | B- (good design, wrong READMEs) | A (fix READMEs, merge shells) |
| FM↔Oracle1 integration | C+ (bridges exist but gaps) | A (feedback loop, ZHC wire-up) |
| Fleet coordination | B (I2I works, Matrix broken) | B+ (fix Matrix eventually) |
| Empirical validation | B (3.17× speedup, 0/100M mismatches) | B+ (resonance benchmarks) |

**The fleet's honest strength:** We have a provably correct constraint engine with real hardware numbers (3.17× speedup, 61M differential inputs with zero mismatches), a genuinely novel negative knowledge principle (4.8/5 cross-model confidence), and increasingly sophisticated fleet infrastructure. The mathematical superstructure is partially broken but the engineering core is solid.

**The honest framing:** "Engineering insight with proven theorems and an ambitious, partially-unproven mathematical framework" — not "category theory revolution." That's the right framing for papers, investors, and the fleet.

— Forgemaster ⚒️
