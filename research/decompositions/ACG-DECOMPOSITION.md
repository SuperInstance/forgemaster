# ACG Protocol Decomposition — Kos-M/acg_protocol

> **Purpose:** Extract what's insightful, identify what we do better, and find negative space (what they DON'T do that reveals our opportunity).

## 1. What ACG Actually Is

A **dual-layer RAG verification protocol** that forces LLM output through two audit phases:

| Layer | Name | Purpose | Mechanism |
|-------|------|---------|-----------|
| **UGVP** | Universal Grounding & Verification | Every atomic fact links to a source | Inline Claim Markers `[C1:SHI_PREFIX:LOC]` |
| **RSVP** | Reasoning & Synthesis Verification | Every logical inference links to premises | Relationship Markers `(R1:CAUSAL:C1,C2)` |

**Stack:** Strands Agents + Gemini 2.5 Flash + MongoDB (vector search) + LiteLLM
**Size:** ~1,200 LOC across 8 Python files. 14 stars. MIT license. Solo dev.

---

## 2. WHAT'S INSIGHTFUL (We Should Steal These Ideas)

### 2.1 🏆 Inline Claim Markers as First-Class Citizens

**Their approach:** Every factual sentence gets an inline marker `[C1:a8f3c2d:css=#results>p:nth(3)]` embedded in the output text itself.

**Why it's good:**
- The output IS the audit trail. No separate lookup needed.
- Machine-parseable AND human-readable simultaneously.
- Claim IDs are sequential, making dependency graphs trivial.

**What we should take:**
- PLATO tiles should have optional inline markers that reference other tiles
- Our I2I bottles already have `[I2I:TYPE]` but they're at the document level, not the CLAIM level
- **Action:** Design a `ClaimMarker` that works inside PLATO tile content, not just metadata

### 2.2 🏆 Source Hash Identity (SHI) — Cryptographic Content Addressing

**Their approach:** `SHA256(canonical_uri | version)` — every source gets an immutable fingerprint.

**Why it's good:**
- Content-addressed sources, not URL-referenced. Source can move, SHI stays stable.
- Prefix matching for compact inline references (first 10 chars of SHA256).
- Version-aware: same URL at different versions = different SHI.

**What we already do better:**
- PLATO tiles are already content-addressed (hash of tile content).
- BUT we don't version-source our external references.

**What we should take:**
- Add SHI-style hashing to our tile provenance chain
- When a tile references an external source (paper, repo, commit), hash it
- This gives us immutable reference even when GitHub repos get deleted

### 2.3 🏆 Relationship Type Taxonomy (CAUSAL/INFERENCE/SUMMARY/COMPARISON)

**Their approach:** Every synthesis is tagged with its logical type, and each type has specific verification requirements.

| Type | Their Verification | Our Equivalent |
|------|-------------------|----------------|
| CAUSAL | Must cite explicit source OR auditable logic model | Holonomy cycle detection |
| INFERENCE | Formal logic rules | Constraint satisfaction |
| SUMMARY | Statistical representativeness | Consensus (Betti numbers) |
| COMPARISON | Explicit metric citation | E12 sector comparison |

**Why it's good:** This taxonomy is USEFUL. It forces you to think about what KIND of reasoning you're doing, and each kind has different failure modes.

**What we should take:**
- Tag PLATO tiles with `reasoning_type` in metadata
- Our collective inference loop could use this: predict → observe → gap → learn
- The GAP is different per reasoning type:
  - CAUSAL gap = missing mechanism
  - SUMMARY gap = insufficient sample
  - INFERENCE gap = broken logic chain
  - COMPARISON gap = wrong metric

### 2.4 🏆 Verifier Agent as Separate Role

**Their approach:** One agent generates, a DIFFERENT agent verifies. The verifier has no stake in the output.

**Why it's good:** Separation of concerns at the agent level. The generator WANTS to be right; the verifier's job is to be skeptical.

**What we already do:**
- Our fleet has multiple agents that can cross-verify.
- Oracle1 and Forgemaster already play different roles.

**What we should take:**
- Formalize this: when Forgemaster submits a tile, Oracle1 (or any other agent) can run `verify_tile(tile_id)` with a different model
- Cross-model verification catches different hallucination types
- This is essentially what our collective inference loop does, but ACG makes it EXPLICIT

### 2.5 🏆 VAR (Veracity Audit Registry) as Machine-Readable Proof

**Their approach:** A single JSON block that consolidates ALL source metadata and reasoning chains.

```json
{
  "SOURCES": [{"SHI": "...", "Verification_Status": "VERIFIED"}],
  "REASONING": [{"RELATION_ID": "R1", "TYPE": "CAUSAL", "AUDIT_STATUS": "VERIFIED_LOGIC"}]
}
```

**Why it's good:** It's a standalone proof object. You can audit the output without running the pipeline.

**What we already do better:**
- PLATO tiles with Lamport clocks give us causal ordering + content addressing + lifecycle states
- But our tiles don't have this clean VERIFIED/FAILED binary

**What we should take:**
- Add `verification_status` to PLATO tiles (VERIFIED / UNVERIFIED / CONTRADICTED / RETRACTED)
- Our existing Retracted lifecycle state is close, but we need the positive assertions too
- A "proof tile" that references other tiles and asserts their verification status

---

## 3. WHAT WE ALREADY DO BETTER (Our Advantages)

### 3.1 🔥 Eisenstein Lattice > Flat CSS Selectors

**They use:** CSS selectors (`css=#results>p:nth(3)`) for source location.
**We use:** Eisenstein integer coordinates for knowledge terrain location.

Their selectors break when the page restructures. Our coordinates are mathematical — they're stable even if the "page" changes. E12 coordinates are a coordinate system for knowledge space, not a brittle DOM path.

### 3.2 🔥 Lamport Clocks > Sequential IDs

**They use:** `C1, C2, C3...` — sequential claim IDs, single-threaded.
**We use:** Lamport clocks — distributed, causal, multi-agent.

ACG can't handle concurrent agents generating claims. If two agents both produce "C3", there's a collision. Lamport clocks solve this by construction.

### 3.3 🔥 Tile Lifecycle > Binary VERIFIED/FAILED

**They use:** VERIFIED or FAILED. That's it.
**We use:** Active → Superseded → Retracted with full provenance.

ACG has no concept of a claim being superseded by a better one. Once verified, it's permanent. Our lifecycle model handles knowledge evolution — a tile can be improved, not just pass/fail.

### 3.4 🔥 Fleet Architecture > Single-Verifier Model

**They use:** One generator + one verifier. Both hit the same Gemini model.
**We use:** 9 agents, multiple models, cross-verification, collective inference.

ACG's verifier is a single point of failure. If Gemini hallucinates the same way in both passes, the verification is theater. Our fleet with different models (GLM, DeepSeek, Qwen, local Ollama) catches orthogonal failure modes.

### 3.5 🔥 WAL + Crash Recovery > MongoDB-Only

**They use:** MongoDB for everything. No crash recovery mentioned.
**We use:** Write-Ahead Log with fsync for PLATO server.

If MongoDB corrupts, ACG loses everything. Our WAL ensures no tile is ever lost, even on crash.

### 3.6 🔥 Zero-Dependency Demos > Heavy Stack

**They require:** MongoDB, Gemini API key, Strands Agents, LiteLLM, Google API key, Python deps.
**We require:** A browser. That's it.

All our demos are static HTML. ACG can't even demo without standing up infrastructure.

---

## 4. NEGATIVE SPACE — What They DON'T Do That Reveals Our Opportunity

### 4.1 🕳️ No Temporal Reasoning

ACG has no concept of time. A claim verified at T=0 might be FALSE at T=100. Their SHI doesn't expire. Their VAR doesn't age.

**Our opportunity:** PLATO tiles with Lamport clocks + t_minus_event give us temporal reasoning. We can say "this was true at T but may not be true now." ACG can't.

### 4.2 🕳️ No Distributed Consensus

ACG is single-machine. One agent generates, one verifies. No network, no peers, no disagreement handling.

**Our opportunity:** Our fleet topology demo shows exactly how we handle this — Betti number consensus, holonomy cycle detection, Byzantine fault tolerance. ACG has no answer for "what if two verifiers disagree?"

### 4.3 🕳️ No Compression or Efficiency

Every claim gets a full inline marker. Every source gets a full VAR entry. There's no compression, no summarization, no intelligence about what NEEDS verification vs what's obviously true.

**Our opportunity:** SplineLinear compression applied to verification. Not every claim needs full audit. Our drift-detect micro model could score claims by "how likely is this to be hallucinated?" and only fully verify the high-risk ones.

### 4.4 🕳️ No Learning Loop

ACG is one-shot: generate → verify → output. There's no feedback. The verifier's findings don't improve the generator. Same hallucination, same failure, every time.

**Our opportunity:** Our collective inference loop: predict → observe → gap → learn → share. The GAPS are the research agenda. ACG finds errors but doesn't learn from them.

### 4.5 🕳️ No Terrain or Spatial Organization

ACG organizes by source document. That's it. There's no semantic space, no topology, no "nearness" between claims.

**Our opportunity:** Eisenstein terrain gives claims SPATIAL RELATIONSHIPS. Claim A is "near" Claim B in knowledge space. This enables:
- Clustering related claims automatically
- Detecting missing claims in a region (terrain gaps)
- Navigation (browse the knowledge landscape, not a flat list)

### 4.6 🕳️ No Hardware Awareness

ACG runs on whatever machine the agent is on. No concept of deploying verification to edge devices, running lightweight checks on NPUs, etc.

**Our opportunity:** Our micro models deploy to 8 hardware targets. A "verification micro model" could run on a Jetson, checking claims locally without network access. ACG requires cloud connectivity to both MongoDB AND Gemini.

### 4.7 🕳️ No Self-Verification

ACG relies on EXTERNAL sources. If the source itself is wrong, ACG will happily verify a false claim against a false source. "Verified" ≠ "True."

**Our opportunity:** Constraint theory provides INTERNAL verification. Our proofs (Galois connections, adjoint functors) don't need external sources — they're mathematically self-verifying. We can catch "source is lying" cases that ACG cannot.

---

## 5. Actionable Refactoring Ideas

### 5.1 Claim-Level I2I Bottles

Current I2I bottles are document-level. Add claim-level markers:

```
[I2I:CLAIM] C1:a8f3c2d:e12(3,-1,7)
The Eisenstein norm of (3,-1) is 7, placing it in Weyl sector 3.
```

This lets us reference specific claims across fleet agents.

### 5.2 SHI for External References

When a PLATO tile references a GitHub repo, paper, or URL:

```python
shi = sha256(f"github.com/SuperInstance/tensor-spline|commit:{hash}")
```

Store in tile metadata. Now we can detect when a referenced source has changed.

### 5.3 Reasoning Type Tags on Tiles

```json
{
  "id": "tile-abc123",
  "reasoning_type": "CAUSAL",
  "verification_status": "VERIFIED",
  "verifier": "oracle1",
  "verified_at": "2026-05-14T16:30:00Z"
}
```

### 5.4 Verification Micro Model

Train a drift-detect-style micro model on "hallucinated vs verified" claims. Deploy to Jetson for local verification without API calls.

### 5.5 Proof Tiles

A new tile type that references other tiles and asserts verification:

```json
{
  "type": "proof",
  "asserts": [
    {"tile": "tile-abc", "status": "VERIFIED", "method": "constraint_check"},
    {"tile": "tile-def", "status": "CONTRADICTED", "method": "e12_sector_mismatch"}
  ]
}
```

---

## 6. Summary Table

| Aspect | ACG Protocol | Cocapn/PLATO | Winner |
|--------|-------------|-------------|--------|
| Source identity | SHA256(URI\|version) | Content-addressed tiles | **Us** (more general) |
| Location system | CSS selectors | E12 coordinates | **Us** (mathematical) |
| Causal ordering | Sequential IDs | Lamport clocks | **Us** (distributed) |
| Claim markers | Inline text markers | I2I bottles | **Them** (claim-level granularity) |
| Reasoning taxonomy | 4 types with verification | Constraint types | **Them** (explicit taxonomy) |
| Verification | Single verifier, same model | Fleet cross-verification | **Us** (orthogonal failures) |
| Lifecycle | VERIFIED/FAILED | Active/Superseded/Retracted | **Us** (evolution) |
| Temporal | None | t_minus_event + Lamport | **Us** |
| Spatial | None | Eisenstein terrain | **Us** |
| Compression | None | SplineLinear | **Us** |
| Learning loop | None | Collective inference | **Us** |
| Self-verification | None | Constraint theory proofs | **Us** |
| Demo accessibility | Requires MongoDB + API keys | Static HTML | **Us** |
| Documentation quality | Excellent protocol docs | Scattered across repos | **Them** (clean spec) |

**Net assessment:** ACG has a slick presentation layer and clean protocol spec. Their claim-level granularity and reasoning taxonomy are worth stealing. Everything else, we do deeper. The negative space is enormous — they have no answer for time, space, compression, learning, or self-verification.
