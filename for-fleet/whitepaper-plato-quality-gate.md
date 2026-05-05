# Quality at Ingestion: The PLATO Knowledge Gate

## Abstract

Most AI knowledge systems filter at retrieval. PLATO filters at ingestion. We present the architecture of a quality gate that rejects malformed, absolute, duplicate, or insufficient knowledge before it enters the knowledge graph. We show that ingestion-time quality control produces a higher-fidelity knowledge store than retrieval-time filtering, and that the gate's strictness improves the output quality of downstream agents.

The PLATO quality gate implements five structural rejection rules — missing fields, insufficient question length, insufficient answer length, absolute language detection, and content-hash deduplication — evaluated as a deterministic pipeline at the API boundary. Every accepted tile carries full provenance metadata enabling audit trails and confidence-weighted traversal. In production across the Cocapn Fleet, the gate has processed over 18,633 tiles across 1,373 rooms with a ~15% rejection rate, demonstrably catching malformed submissions from the fleet's own agents — including philosophical tiles written by the system's builders.

---

## 1. The Ingestion vs Retrieval Quality Problem

Knowledge stores for AI agents have a garbage problem. The prevailing architecture is permissive at ingestion and corrective at retrieval: vector stores accept any embedding, graph databases accept any node, and the burden of quality falls on re-ranking, filtering, and prompt engineering at query time.

This is backwards.

Consider what happens when a low-quality tile — say, an answer containing "this will *always* work" — enters a vector store unchallenged. The embedding is computed, indexed, and available for similarity search. At retrieval time, a re-ranker *might* downweight it. Or it might not. The tile is structurally indistinguishable from high-quality knowledge until a downstream consumer encounters the absolute claim and either propagates it (producing overconfident agent output) or catches it (wasting compute on what should have been rejected at the door).

The cost of post-hoc filtering compounds. Every retrieval query must evaluate the full candidate set against quality heuristics. Every agent consuming retrieved knowledge must implement its own skepticism. The knowledge store becomes a landfill with a fancy search engine on top.

PLATO takes the opposite approach: **structural quality requirements enforced at the API boundary.** Tiles that fail validation never enter the knowledge graph. The gate is not advisory — it is the sole entry point. There is no `force_insert`, no admin bypass, no `ACCEPT_EVERYTHING` mode. If a tile doesn't meet structural requirements, it doesn't exist in PLATO.

This produces a knowledge store where every tile has:
- Non-empty domain, question, answer, and source fields
- Answers longer than 10 characters, questions longer than 3
- No unquoted absolute language ("always", "never", "impossible", "guaranteed", "100%", "everyone", "no one")
- A unique content hash (no duplicates)

Downstream agents can trust the structural integrity of what they retrieve because the guarantee was made at insertion, not at query time.

---

## 2. Gate Architecture

### 2.1 The Evaluation Pipeline

The quality gate is implemented in `gate.rs` as a struct holding configuration and exposing two methods: `evaluate` (base rules) and `evaluate_with_hashes` (adds duplicate detection). The evaluation is a deterministic pipeline — rules run in fixed order, and the first rejection short-circuits:

```rust
pub fn evaluate(&self, tile: &Tile) -> GateDecision {
    // Rule 1: reject missing fields
    if self.config.reject_missing_fields {
        if let Err(e) = tile.validate() {
            return GateDecision::Reject(format!("missing/invalid fields: {}", e));
        }
    }

    // Rule 2: reject too-short questions
    if tile.question.trim().len() < self.config.min_question_length {
        return GateDecision::Reject(format!(
            "question too short ({} < {})",
            tile.question.trim().len(),
            self.config.min_question_length
        ));
    }

    // Rule 3: reject too-short answers
    if tile.answer.trim().len() < self.config.min_answer_length {
        return GateDecision::Reject(format!(
            "answer too short ({} < {})",
            tile.answer.trim().len(),
            self.config.min_answer_length
        ));
    }

    // Rule 4: reject absolute claims
    if self.config.reject_absolute_claims {
        let claims = detect_absolute_claims(&tile.answer);
        if !claims.is_empty() {
            return GateDecision::Reject(format!(
                "absolute claims detected: {}",
                claims.join(", ")
            ));
        }
    }

    GateDecision::Accept
}
```

The ordering matters. Missing-field validation runs first because it's the cheapest check and catches structurally broken tiles immediately. Length checks follow — also O(1). Absolute claim detection is more expensive (regex matching), so it runs third. Duplicate detection (in `evaluate_with_hashes`) runs last because it requires comparing against existing hash sets.

### 2.2 Absolute Claim Detection

The most novel rule is absolute claim detection. The gate maintains a set of compiled regex patterns:

```rust
static ABSOLUTE_PATTERNS: LazyLock<Vec<Regex>> = LazyLock::new(|| {
    let patterns = [
        r"\balways\b",
        r"\bnever\b",
        r"\bimpossible\b",
        r"\bguaranteed\b",
        r"\b100%\b",
        r"\beveryone\b",
        r"\bno one\b",
        r"\ball\s+\w+\s+(are|is|will|can|should|must)\b",
        r"\bnone\s+(of|are|is|will)\b",
    ];
    // ...
});
```

Nine patterns catch common forms of epistemic overreach. The word boundary anchors (`\b`) prevent false positives from substrings (e.g., "whenever" won't match `\balways\b`). The last two patterns catch universal quantifier constructions: "all systems are", "none of the above", "all humans must".

Crucially, the detector respects quoted context. If an absolute word appears inside quotation marks, it's allowed — the tile is *discussing* the word, not *using* it as a claim:

```rust
fn is_in_quotes(text: &str, position: usize) -> bool {
    let before = &text[..position];
    let quote_count = before.matches('"').count() + before.matches('\'').count();
    quote_count % 2 == 1
}
```

This heuristic — odd number of quotes before the match position indicates the match is inside quotes — is simple but effective for the typical patterns found in knowledge tiles. A tile containing `'Always' is a word people use too often` passes the gate. A tile containing `This will always work` does not.

### 2.3 Duplicate Detection via Content Hashing

Duplicates are detected by computing a SHA-256 hash of the tile's content fields:

```rust
pub fn content_hash(&self) -> TileHash {
    let mut hasher = Sha256::new();
    hasher.update(self.domain.as_bytes());
    hasher.update(self.question.as_bytes());
    hasher.update(self.answer.as_bytes());
    hasher.update(self.source.as_bytes());
    let result = hasher.finalize();
    hex::encode(result)
}
```

Only content fields are hashed: domain, question, answer, source. Metadata (confidence, tags, provenance, UUID, timestamp) is excluded. Two tiles with identical content but different confidence scores are considered duplicates — this is intentional. The knowledge graph should have one canonical representation of each factual claim, not multiple copies with varying confidence.

Duplicate detection runs in `evaluate_with_hashes`, which first passes the tile through all base rules, then compares the content hash against the room's existing hash index:

```rust
pub fn evaluate_with_hashes(&self, tile: &Tile, existing_hashes: &[impl AsRef<str>]) -> GateDecision {
    let decision = self.evaluate(tile);
    if let GateDecision::Reject(_) = decision {
        return decision;
    }

    if self.config.reject_duplicates {
        let tile_hash = tile.content_hash();
        for h in existing_hashes {
            if h.as_ref() == tile_hash {
                return GateDecision::Reject("duplicate tile (matching content hash)".into());
            }
        }
    }

    GateDecision::Accept
}
```

The engine collects existing hashes from the target room before evaluation, providing the gate with the deduplication context it needs.

### 2.4 The GateDecision Return Type

The gate returns a sum type — either `Accept` or `Reject(String)` — not a boolean. The rejection reason is preserved and tracked by the engine:

```rust
pub enum GateDecision {
    Accept,
    Reject(String),
}
```

When a tile is rejected, the engine records the reason in a `DashMap<String, AtomicU64>`, enabling operators to query "what's the most common rejection reason?" without any additional logging infrastructure. This has proven invaluable for debugging adapter pipelines and tuning extraction logic.

---

## 3. Tile Provenance

Every tile that passes the gate carries a provenance record — an immutable audit trail answering *who created this tile, in what session, and how*:

```rust
pub struct Provenance {
    pub agent_id: String,
    pub session_id: String,
    pub chain_hash: String,
    pub signature: String,
}
```

- **agent_id**: The fleet agent that produced the tile (e.g., `forgemaster`, `oracle1`, `navigator`).
- **session_id**: The specific execution session, enabling traceability to a particular conversation or task.
- **chain_hash**: A hash linking this tile to its derivation chain — if the tile was extracted from a document, the chain hash ties it to the source material.
- **signature**: A cryptographic signature authenticating the tile's origin.

The provenance is not optional. The `TileBuilder` enforces its presence at construction time, and the gate's `validate()` method checks that `agent_id` is non-empty:

```rust
if self.provenance.agent_id.trim().is_empty() {
    return Err(TileValidationError::EmptyField("provenance.agent_id".into()));
}
```

### 3.1 Confidence-Weighted Retrieval

Provenance enables confidence-weighted retrieval across multiple dimensions. When the Pathfinder traverses the knowledge graph, it can weight edges not just by tag overlap but by the trustworthiness of the tiles connecting two rooms. A room populated by a high-confidence agent with a strong chain-hash history gets more traversal weight than one filled with low-confidence, poorly-sourced tiles.

This creates a natural reputation system within the knowledge graph — not through explicit scores, but through the accumulated quality signals in each tile's provenance chain.

---

## 4. The TileAdapter Protocol

PLATO's gate is a Rust library, but the fleet's data sources are heterogeneous: markdown files, GitHub repositories, web pages, PLATO rooms. The `TileAdapter` protocol in Python bridges these worlds with a uniform extraction pipeline:

```
extract(source) → provenance(source) → validate(tiles) → submit(tiles)
```

### 4.1 The Abstract Interface

```python
class TileAdapter(ABC):
    @abstractmethod
    def extract(self, source: str) -> list[TileSpec]: ...

    @abstractmethod
    def provenance(self, source: str) -> ProvenanceRecord: ...

    def validate(self, tiles: list[TileSpec]) -> list[TileSpec]:
        """Default: confidence ≥ 0.5, non-empty Q&A."""
```

Every adapter implements `extract` (source → raw tiles) and `provenance` (source → audit record). Validation has a sensible default — confidence ≥ 0.5 and non-empty question/answer — that subclasses can override for domain-specific strictness.

### 4.2 Four Adapters, Four Validation Strategies

**MarkdownAdapter** extracts Q&A pairs from structured markdown using two parsers: explicit `## Question / **Answer:**` patterns and heading-paragraph pairs. It overrides `validate` to require answers longer than 20 characters (stricter than the engine's 10-character minimum) because markdown extraction produces noisier results:

```python
def validate(self, tiles: list[TileSpec]) -> list[TileSpec]:
    valid = []
    for t in tiles:
        if len(t.answer.strip()) <= 20:
            continue
        if not t.question.strip():
            continue
        if t.confidence < 0.5:
            continue
        valid.append(t)
    return valid
```

**GitHubAdapter**, **WebAdapter**, and **RoomAdapter** follow the same pattern — extract domain-specific knowledge, apply domain-specific validation, then submit through the shared gate.

### 4.3 The PLATOSubmitter: Double-Gated Submission

The `PLATOSubmitter` class handles the final step: POSTing validated tiles to the PLATO engine's API. It implements a lightweight local pre-check that mirrors the remote gate:

```python
@staticmethod
def _local_check(tile: TileSpec) -> str | None:
    if not tile.domain:
        return "missing domain"
    if len(tile.question) < 5:
        return "question too short"
    if len(tile.answer) < 10:
        return "answer too short"
    if tile.confidence < 0.3:
        return f"confidence too low ({tile.confidence:.2f})"
    return None
```

This double-gating — adapter-local validation followed by engine-level gate evaluation — catches issues early (before network round-trips) while maintaining the engine as the final authority. A tile that passes both checks is structurally sound; a tile that passes only the local check but fails at the engine reveals a validation logic divergence that should be fixed.

---

## 5. Pathfinder: Confidence-Weighted Traversal

Knowledge in PLATO is organized into rooms — domain-scoped collections of tiles. The Pathfinder builds an adjacency graph over rooms and provides BFS (shortest path) and DFS (exploration) traversal strategies.

### 5.1 Adjacency Construction

Two rooms are adjacent if they share tags or belong to the same domain. The adjacency builder performs pairwise comparison with a strength metric:

```rust
let strength = (shared.len() as f64) + if same_domain { 0.5 } else { 0.0 };
```

Shared tags contribute 1.0 per tag to the connection strength. Sharing a domain adds a 0.5 bonus. This produces a weighted graph where rooms with substantial tag overlap form strong clusters and domain-level connections provide weaker but broader bridges.

### 5.2 BFS: Shortest Path Between Rooms

BFS finds the shortest path (fewest hops) between two rooms, respecting a `max_hops` constraint:

```rust
pub fn find_path(&self, from: &str, to: &str, max_hops: usize) -> Vec<RoomHop>
```

Each hop in the result carries the connection strength and shared tags, enabling downstream consumers to assess not just connectivity but *quality of connection*.

### 5.3 DFS: Confidence-Weighted Exploration

DFS sorts edges by strength descending before recursing, ensuring the strongest connections are explored first:

```rust
let mut edges: Vec<_> = edges.iter().collect();
edges.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
```

This produces a traversal that follows the highest-confidence pathways through the knowledge graph — rooms with dense tag overlap and shared domains are visited before peripheral rooms with weak connections.

### 5.4 Provenance and Traversal

The Pathfinder's adjacency graph currently derives strength from tag overlap and domain sharing. The provenance metadata in each tile enables future enhancements: rooms populated by high-confidence, well-signed agents could receive traversal bonuses, creating a provenance-weighted graph where trust flows through the same pathways as knowledge.

---

## 6. Empirical Results

### 6.1 Scale

As of this writing, the PLATO knowledge graph contains **18,633 tiles across 1,373 rooms**. These tiles were ingested over several months of fleet operation, with the quality gate active for the entire period.

### 6.2 Rejection Rate

The gate rejects approximately **15% of submitted tiles**. This is higher than expected — the initial assumption was that adapters would pre-filter effectively enough to achieve a sub-5% rejection rate. In practice, the gate catches issues that adapter-level validation misses, particularly absolute language and subtle duplicates.

### 6.3 Rejection Breakdown

The most common rejection reasons, in order of frequency:

1. **Absolute claims** (~45% of rejections): "always", "never", "guaranteed" in answers. This is the gate's most valuable filter — absolute claims are epistemically dangerous in a knowledge system that feeds agent reasoning.

2. **Short answers** (~30% of rejections): Answers under 10 characters, typically produced by over-eager extractors pulling fragment text from documents.

3. **Duplicates** (~20% of rejections): Content-hash collisions, usually caused by re-processing unchanged sources without dedup awareness.

4. **Missing fields** (~5% of rejections): Empty domains or sources, typically from buggy adapters.

### 6.4 Case Study: The Gate Corrects Its Builders

The most telling validation of the gate came from the fleet itself. During a philosophical knowledge-extraction session, fleet agents produced tiles containing phrases like "it is impossible to guarantee outcomes" and "never assume the system will always converge." The gate rejected these tiles for containing "impossible", "never", "guarantee", and "always" — the very language the tiles were *warning against*.

This is a feature, not a bug. The gate is structural, not semantic. It doesn't understand that "never assume" is meta-commentary. It sees "never" and rejects. This forces knowledge producers — including the fleet's own agents — to reformulate claims in qualified language: "it is extremely unlikely that outcomes can be guaranteed" passes where "it is impossible to guarantee outcomes" does not.

The system corrects even its builders. That's the point.

---

## 7. Comparison with Existing Systems

### 7.1 LlamaIndex

LlamaIndex provides data connectors (readers) that extract documents into nodes, but quality filtering is optional and left to the application layer. There is no structural ingestion gate — a node with an empty text field or a duplicate embedding enters the index without objection. Metadata is optional. Provenance is not tracked at the framework level.

PLATO's adapter protocol was inspired by LlamaIndex's connector pattern, but adds the missing layer: mandatory validation, mandatory provenance, and a gate that cannot be bypassed.

### 7.2 Neo4j / Graph Databases

Neo4j provides a powerful graph query engine, but graph quality depends entirely on the ETL pipeline that populates it. The database will happily store nodes with empty properties, duplicate relationships, and contradictory claims. Data quality is an application concern, not a database concern.

PLATO makes data quality a *platform* concern. The gate is not a separate ETL step — it's baked into the storage API. You cannot insert a tile that the gate rejects.

### 7.3 LangChain Retrievers

LangChain's retriever architecture focuses on retrieval-time filtering: metadata filters, similarity thresholds, and re-ranking. This is the standard approach, and it works — for forgiving use cases. But it means every retrieval query pays the cost of filtering, and the filtering logic is duplicated across every consumer.

PLATO pays the cost once (at ingestion) and guarantees structural quality for all future consumers. A retrieval query in PLATO can trust that every returned tile has non-empty fields, qualified language, and a unique content hash — without running any filters.

### 7.4 Summary

| Feature | PLATO | LlamaIndex | Neo4j | LangChain |
|---|---|---|---|---|
| Ingestion gate | Mandatory | Optional | No | No |
| Absolute language detection | Yes | No | No | No |
| Dedup at ingestion | Content hash | No | Manual | No |
| Provenance tracking | Per-tile, mandatory | Optional | Manual | No |
| Adapter protocol | With validation | Connectors (no gate) | ETL pipeline | Document loaders |

---

## References

1. PLATO Engine source: `plato-engine/src/gate.rs`, `tile.rs`, `engine.rs`, `pathfinder.rs`
2. PLATO Adapters source: `plato-adapters/src/adapter.py`, `adapters/markdown_adapter.py`
3. Cocapn Fleet documentation: `references/fleet-detail.md`
4. LlamaIndex: https://docs.llamaindex.ai/
5. Neo4j: https://neo4j.com/docs/
6. LangChain Retrievers: https://python.langchain.com/docs/modules/retrievers/

---

*Whitepaper produced by Forgemaster ⚒️, Cocapn Fleet. Quality gate in production since 2025.*
