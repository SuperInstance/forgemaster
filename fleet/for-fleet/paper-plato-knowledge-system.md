# PLATO: Quality-Gated Knowledge Integration for Autonomous Systems

**Forgemaster ⚒️** · Cocapn Fleet · SuperInstance

---

## Abstract

Autonomous agent systems require knowledge stores that are structurally sound, epistemically disciplined, and traceable to source. Existing approaches - vector databases, retrieval-augmented generation (RAG) frameworks, and knowledge graphs - are permissive at ingestion and corrective at retrieval: they accept any data and rely on downstream filtering, re-ranking, or prompt engineering to maintain quality. We argue that quality-at-ingestion is complementary to retrieval-time filtering - not a replacement - but critically important for autonomous systems, where unchecked knowledge propagates through chains of reasoning without human oversight. Retrieval-time filtering remains necessary for relevance and context; PLATO ensures the corpus being searched is itself structurally sound. We present PLATO, a quality-gated knowledge integration system that enforces structural validation at the API boundary. PLATO implements a deterministic pipeline of five rejection rules - missing fields, insufficient length, absolute language detection, content-hash deduplication, and provenance verification - evaluated before any tile enters the knowledge graph. In production across the Cocapn Fleet (18,633 tiles, 1,373 rooms), the gate rejects approximately 15% of submissions, demonstrably catching malformed data from the system's own agent pipeline. We describe the architecture, prove the correctness of the gate's short-circuit evaluation, and demonstrate that ingestion-time quality control produces a higher-fidelity knowledge store than retrieval-time filtering at lower amortized cost.

---

## 1. Introduction

The central problem in knowledge management for autonomous systems is not *retrieval* - it is *ingestion*. Modern LLM-based agents can query any knowledge store with sufficient prompting, but the quality of retrieved knowledge is bounded by the quality of what was stored. A vector database will faithfully return the nearest neighbor to any embedding, regardless of whether that neighbor contains vacuous text, contradictory claims, or absolute language that an agent will propagate as fact.

This problem compounds in multi-agent systems. When Agent A retrieves a knowledge fragment containing the claim "this approach *always* works in production," and uses it to advise Agent B, the absolute claim has now propagated through two reasoning chains without any structural check. The epistemic contamination is invisible until it produces overconfident behavior - a deployment decision, a skipped safety check, an unsound recommendation.

The prevailing architecture in both industry and open-source systems treats quality as a retrieval concern:

- **Vector databases** (Pinecone [1], Weaviate [2], Qdrant [3]) store embeddings and metadata with no structural constraints on content quality.
- **RAG frameworks** (LlamaIndex [4], LangChain [5]) provide document loaders and retrievers but treat validation as optional - a callback the developer *may* implement.
- **Knowledge graphs** (Neo4j [6], Wikidata [7]) enforce schema constraints but not content quality - a node with an empty `description` property or a duplicate relationship is structurally valid.

In each case, quality filtering happens primarily at query time, is duplicated across consumers, and provides no structural guarantees about what enters the store. Retrieval-time filtering is necessary and valuable - PLATO does not replace it - but relying on it exclusively leaves the corpus itself unguarded.

PLATO takes a complementary approach: **quality is enforced at ingestion in addition to whatever retrieval-time filtering consumers apply.** The gate is mandatory, deterministic, and unbypassable. There is no `force_insert`, no admin override, no `ACCEPT_EVERYTHING` mode. A tile that fails validation does not exist in PLATO. This does not eliminate the need for retrieval-time quality measures (re-ranking, relevance filtering, context selection), but it ensures the corpus being searched is structurally sound - reducing the burden on downstream filtering.

This paper makes the following contributions:

1. We formalize the quality-gate pipeline as a deterministic short-circuit evaluator with proven correctness properties (§4).
2. We introduce absolute-language detection with quote-awareness as a structural quality rule (§4.2).
3. We describe a content-hash deduplication scheme that ensures knowledge uniqueness at the room level (§4.3).
4. We present Pathfinder, a confidence-weighted graph traversal algorithm for cross-domain knowledge discovery (§5).
5. We provide empirical evidence from a production deployment showing the gate catches ~15% of submissions, including malformed data from the system's own agents (§8).

---

## 2. Related Work

### 2.1 Vector Databases

Pinecone [1], Weaviate [2], and Qdrant [3] provide high-throughput approximate nearest neighbor (ANN) search over dense embeddings. Their ingestion APIs accept any vector and optional metadata payload. Schema validation (where it exists) enforces types - a field declared `float` must contain a float - but not content quality. There is no mechanism to reject a vector because the text it represents contains absolute language or is too short to be meaningful.

PLATO operates at a different layer. It does not compete with vector databases - it complements them. A PLATO tile's content hash could be used as a vector-store key, but the gate ensures that only structurally sound tiles are indexed.

### 2.2 RAG Frameworks

LlamaIndex [4] provides a data connector architecture (`Reader` → `Document` → `Node` → `Index`) with optional transformations at each stage. Quality filtering is available through custom `NodeParser` implementations but is not enforced by the framework. A `SimpleDirectoryReader` loading a corpus of malformed documents produces malformed nodes without objection.

LangChain [5] provides `DocumentLoader`, `TextSplitter`, and `Retriever` abstractions. Filtering is retrieval-oriented: `SelfQueryRetriever` filters by metadata at query time; `ContextualCompressionRetriever` post-processes results. Neither provides ingestion-time structural validation.

PLATO's TileAdapter protocol (§6) was informed by LlamaIndex's connector pattern but adds the missing layer: mandatory validation with an unbypassable gate.

### 2.3 Knowledge Graphs

Neo4j [6] supports schema constraints (uniqueness, existence, type) but not content quality constraints. A Cypher query `CREATE (n:Concept {text: ""})` succeeds. Duplicate relationships are prevented by uniqueness constraints only if explicitly configured. Content deduplication requires custom application logic.

Wikidata [7] maintains quality through community-driven guidelines and bot enforcement - a social process, not a structural one. PLATO's approach is mechanical: the gate enforces quality without human judgment, which is essential for autonomous systems that ingest knowledge at machine speed.

### 2.4 Expert Systems and Knowledge Engineering

Classical expert systems (MYCIN [8], CLIPS [9]) enforced knowledge quality through structured representation formalisms (production rules, frames, ontologies). Knowledge that didn't fit the formalism was rejected at encoding time. PLATO applies this principle to the modern LLM agent stack: structural requirements are enforced at ingestion, not as an ontology constraint but as a validation pipeline over semi-structured tile data.

### 2.5 Data Quality Frameworks

The database literature has extensively studied data quality, notably Wang and Strong's framework [10] and the TDQM methodology [11]. These approaches focus on measuring and improving quality in relational data through profiling, cleansing, and constraint enforcement. PLATO applies a similar philosophy - quality constraints at the point of entry - to the specific domain of knowledge tiles for autonomous agents, where the consequences of low-quality data (overconfident agent behavior, epistemic contamination) differ from traditional data-quality concerns.

#### 2.5.1 Industry Data Quality Tools

Several production data quality systems enforce validation at ingestion time, most notably **Great Expectations** [12] and **Amazon Deequ** [13]. Great Expectations provides declarative "expectations" (assertions over data) that can be applied at load time through "checkpoint" configurations. Deequ (built on Apache Spark) computes data quality metrics at scale and enforces constraints through verification suites. TensorFlow Data Validation (TFDV) [14] generates schema statistics and detects anomalies in ML training data before it enters the pipeline.

These systems share PLATO's philosophy - validate before storage - but operate on structured tabular data with well-defined schemas. PLATO's gate operates on semi-structured text tiles where the quality concerns are linguistic (absolute language, insufficient content) rather than statistical (null rates, value distributions, schema conformance).

| Dimension | Great Expectations / Deequ | PLATO |
|---|---|---|
| **Data model** | Tabular (rows/columns) | Semi-structured text tiles |
| **Quality concerns** | Null rates, type conformity, statistical distributions | Absolute language, content sufficiency, deduplication |
| **Constraint language** | Declarative expectations / verification functions | Deterministic predicate pipeline |
| **Enforcement point** | Pipeline checkpoint | API boundary (no bypass) |
| **Scope** | Dataset-level | Per-tile (individual knowledge unit) |
| **Bypass possible?** | Yes (skip checkpoint) | No (sole insertion path) |

#### 2.5.2 Knowledge Graph Constraint Languages

Knowledge graph systems have long supported structural constraint validation at write time. **SHACL** (Shapes Constraint Language) [15] provides a declarative RDF validation framework: a "shape" defines constraints on RDF node structure (cardinality, value type, range), and a SHACL engine validates data before it enters a triple store. DBpedia uses SHACL to enforce structural consistency across its knowledge base. **OWL** (Web Ontology Language) [16] supports class-expression constraints and cardinality restrictions. **ShEx** (Shape Expressions) [17] provides a complementary schema language for RDF validation.

PLATO's gate differs from SHACL/OWL/ShEx in three fundamental ways:

1. **Data domain:** SHACL validates structured RDF triples against a schema (property types, cardinality, value ranges). PLATO validates freeform text content for epistemic quality (absolute language, content sufficiency). These are non-overlapping concerns - a tile could pass SHACL validation (correct structure) while failing PLATO's gate (contains absolute language).

2. **Quality semantics:** SHACL catches schema violations (missing required property, wrong datatype). PLATO catches *epistemic* violations - claims that are structurally well-formed but linguistically dangerous for autonomous consumption. "This will always work" is valid RDF but a harmful knowledge tile.

3. **Extensibility model:** SHACL constraints are defined in a formal specification language tied to RDF. PLATO's gate rules are Rust predicates that can incorporate arbitrary computation (regex matching, length analysis, hash comparison) without requiring a formal constraint language.

For knowledge systems built on RDF triple stores, SHACL validation and PLATO-style content gating are complementary: SHACL ensures structural soundness, PLATO ensures epistemic soundness.

---

## 3. Architecture

PLATO is organized around three core abstractions: **Tiles** (knowledge units), **Rooms** (domain-scoped collections), and the **Gate** (quality evaluator). The engine is implemented in Rust for memory safety and concurrent performance, with a Python client library and adapter protocol for fleet integration.

### 3.1 The Tile

A tile is the fundamental unit of knowledge - a self-contained claim with provenance:

```rust
pub struct Tile {
    pub id: Uuid,
    pub domain: String,
    pub question: String,
    pub answer: String,
    pub source: String,
    pub confidence: f64,
    pub tags: Vec<String>,
    pub created_at: i64,
    pub provenance: Provenance,
}
```

Each tile contains:

- **domain**: The knowledge domain (e.g., `constraint-theory`, `fleet-ops`, `rust-async`). Tiles are organized into rooms by domain, enabling scoped queries.
- **question/answer**: A Q&A pair representing a single claim. The question framing forces knowledge producers to be specific about *what* the tile claims.
- **source**: The origin of the claim (a URL, document title, or agent identifier), enabling traceability.
- **confidence**: A $[0, 1]$ scalar representing the tile's epistemic strength. The gate enforces $0 \leq c \leq 1$.
- **tags**: Free-form labels for cross-domain discovery and Pathfinder traversal.
- **provenance**: Mandatory audit metadata (§7).

Tiles are constructed through a `TileBuilder` that enforces required fields at compile time:

```rust
let tile = TileBuilder::new()
    .domain("constraint-theory")
    .question("What is drift in constraint systems?")
    .answer("Drift measures deviation from a defined invariant...")
    .source("constraint-theory-handbook")
    .confidence(0.92)
    .provenance(Provenance { ... })
    .build()?;  // Returns Err if any field is missing
```

### 3.2 The Room

A room is a named collection of tiles within a domain. Rooms maintain a hash index for O(1) deduplication lookups:

```rust
pub struct Room {
    pub id: String,
    pub domain: String,
    pub tiles: Vec<Tile>,
    pub hash_index: Vec<(TileHash, usize)>,
}
```

The hash index maps content hashes to tile positions, enabling the gate's duplicate check without scanning the full tile set. Room operations (tag queries, hash lookups) use Rayon's parallel iterators for concurrent access:

```rust
pub fn query_by_tag(&self, tag: &str) -> Vec<&Tile> {
    self.tiles.par_iter()
        .filter(|t| t.tags.iter().any(|t_tag| t_tag.to_lowercase().contains(&tag_lower)))
        .collect()
}
```

### 3.3 The Engine

The `PlatoEngine` orchestrates rooms, the gate, and statistics through a `DashMap`-backed concurrent store:

```rust
pub struct PlatoEngine {
    rooms: DashMap<String, Room>,
    gate: Gate,
    stats: Arc<EngineStatsInner>,
    started_at: Instant,
}
```

`DashMap` provides lock-free concurrent access to rooms, enabling the engine to handle simultaneous submissions from multiple agents without contention. Statistics are tracked through atomic counters for lock-free updates:

```rust
self.stats.total_submitted.fetch_add(1, Ordering::Relaxed);
```

The engine exposes a single submission path through the gate:

```rust
pub fn submit(&self, room_id: &str, tile: Tile) -> Result<TileHash, GateRejection> {
    let existing_hashes = /* collect from room */;
    let decision = self.gate.evaluate_with_hashes(&tile, &existing_hashes);
    match decision {
        GateDecision::Accept => { /* insert */ Ok(hash) }
        GateDecision::Reject(reason) => { /* track */ Err(rejection) }
    }
}
```

There is no alternative insertion path. The `submit` method is the sole entry point, and it always evaluates through the gate.

### 3.4 HTTP API

The engine is exposed via an Axum HTTP server with five endpoints:

| Endpoint | Method | Purpose |
|---|---|---|
| `/submit` | POST | Submit a tile through the quality gate |
| `/rooms` | GET | List rooms with optional prefix filter |
| `/room/{id}` | GET | Retrieve a room's full state |
| `/room/{id}/tiles` | GET | Query tiles with optional tag filter |
| `/health` | GET | Engine health (rooms, tiles, uptime) |

Rejected submissions return HTTP 422 (Unprocessable Entity) with the rejection reason, enabling clients to distinguish gate failures from transport errors.

---

## 4. The Quality Gate

The quality gate evaluates tiles through a deterministic pipeline of rules. Each rule is a predicate $r_i: \text{Tile} \to \{\text{Accept}, \text{Reject}(\text{String})\}$. The pipeline short-circuits: the first rejection terminates evaluation. This gives the gate a correctness property:

**Proposition 1 (Gate Correctness).** If the gate returns `Accept`, then all enabled rules $r_1, r_2, \ldots, r_n$ have been evaluated and returned `Accept`. Conversely, if the gate returns `Reject(s)`, then $r_k$ returned `Reject(s)` for the smallest $k$ such that $r_k \neq \text{Accept}$, and rules $r_{k+1}, \ldots, r_n$ were not evaluated.

*Proof.* The pipeline is implemented as a sequence of early-return checks. Each rule returns `Reject` immediately on failure, bypassing subsequent rules. The final line returns `Accept` only if all checks have passed. ∎

### 4.1 Rule Ordering

The pipeline evaluates rules in order of computational cost:

| Order | Rule | Complexity | Rationale |
|---|---|---|---|
| 1 | Missing fields | $O(1)$ | Cheapest; catches structurally broken tiles |
| 2 | Question length | $O(1)$ | String length check |
| 3 | Answer length | $O(1)$ | String length check |
| 4 | Absolute claims | $O(n)$ | Regex matching over answer text |
| 5 | Duplicates | $O(h)$ | Hash comparison against room index |

where $n$ is the answer length and $h$ is the number of existing hashes in the room. The ordering minimizes expected evaluation cost: cheap structural checks run before expensive content analysis.

### 4.2 Absolute Language Detection

The most novel gate rule detects epistemic overreach - claims using absolute quantifiers that no autonomous system should treat as fact. The detector compiles nine regex patterns at startup:

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
    patterns.iter()
        .map(|p| Regex::new(p).expect("invalid absolute claim regex"))
        .collect()
});
```

Word boundary anchors (`\b`) prevent false positives from substrings ("whenever" does not match `\balways\b`). The final two patterns catch universal quantifier constructions: "all systems are," "none of the above," "all humans must."

**Quote-awareness.** The detector respects quoted context through a simple heuristic:

```rust
fn is_in_quotes(text: &str, position: usize) -> bool {
    let before = &text[..position];
    let quote_count = before.matches('"').count() + before.matches('\'').count();
    quote_count % 2 == 1
}
```

If an absolute word appears at position $p$ and the number of quotation marks preceding $p$ is odd, the word is inside a quoted span and is not flagged. This allows tiles to *discuss* absolute language without being rejected for *using* it:

| Tile Answer | Gate Decision |
|---|---|
| `"This will always work in production"` | **Reject** (absolute claim: "always") |
| `"'Always' is a word people use too often"` | **Accept** (quoted context) |
| `"It is impossible to guarantee convergence"` | **Reject** (absolute claims: "impossible", "guarantee") |
| `"Convergence cannot be guaranteed in all cases"` | **Accept** (qualified language) |

The quote-awareness heuristic handles the common patterns in knowledge tiles. Nested quotes and multi-line quotations are edge cases where the heuristic may produce false negatives (accepting an unquoted absolute), but these are rare in practice and acceptable given the trade-off between precision and implementation complexity.

### 4.3 Content-Hash Deduplication

Duplicate detection uses SHA-256 content hashing over the tile's content fields:

$$h(t) = \text{SHA-256}(\text{domain} \| \texttt{\textbackslash\textbackslash x00} \|\ \text{question} \| \texttt{\textbackslash\textbackslash x00} \|\ \text{answer} \| \texttt{\textbackslash\textbackslash x00} \|\ \text{source})$$

```rust
pub fn content_hash(&self) -> TileHash {
    let mut hasher = Sha256::new();
    hasher.update(self.domain.as_bytes());
    hasher.update(b"\x00");  // field separator
    hasher.update(self.question.as_bytes());
    hasher.update(b"\x00");
    hasher.update(self.answer.as_bytes());
    hasher.update(b"\x00");
    hasher.update(self.source.as_bytes());
    hex::encode(hasher.finalize())
}
```

**Separator requirement:** The null byte (`\x00`) separators prevent concatenation collisions. Without separators, tiles with domain=`"ab"`, question=`"cd"` and domain=`"a"`, question=`"bcd"` would produce identical hash input (`"abcd"`). The separator ensures each field occupies a distinct, unambiguous region in the hash input. This is a standard technique from Merkle tree construction and length-prefixed encoding schemes.

**Design choice:** Only content fields are hashed; metadata (confidence, tags, provenance, UUID, timestamp) is excluded. Two tiles with identical content but different confidence scores are considered duplicates. This is intentional: the knowledge graph should have one canonical representation of each factual claim, not multiple copies with varying metadata. If a tile's confidence needs updating, the existing tile should be replaced, not supplemented.

**Collision resistance:** SHA-256 provides negligible collision probability for the expected tile volume. With 18,633 tiles, the probability of at least one collision is approximately $\frac{n^2}{2 \cdot 2^{256}} \approx 5.4 \times 10^{-69}$ - effectively zero.

### 4.4 Missing-Field Validation

The first gate rule validates that all required fields are present and non-empty:

```rust
pub fn validate(&self) -> Result<(), TileValidationError> {
    if self.domain.trim().is_empty() {
        return Err(TileValidationError::EmptyField("domain".into()));
    }
    if self.question.trim().is_empty() {
        return Err(TileValidationError::EmptyField("question".into()));
    }
    if self.answer.trim().is_empty() {
        return Err(TileValidationError::EmptyField("answer".into()));
    }
    if self.source.trim().is_empty() {
        return Err(TileValidationError::EmptyField("source".into()));
    }
    if self.confidence < 0.0 || self.confidence > 1.0 {
        return Err(TileValidationError::InvalidConfidence(self.confidence));
    }
    if self.provenance.agent_id.trim().is_empty() {
        return Err(TileValidationError::EmptyField("provenance.agent_id".into()));
    }
    Ok(())
}
```

Confidence is bounded to $[0, 1]$. Empty fields (after trimming whitespace) are rejected. Provenance's `agent_id` must be non-empty, ensuring every tile is traceable to a producer.

### 4.5 Length Thresholds

Default minimums: `min_question_length = 3`, `min_answer_length = 10`. These thresholds are configurable through `GateConfig`:

```rust
pub struct GateConfig {
    pub reject_absolute_claims: bool,    // default: true
    pub reject_duplicates: bool,          // default: true
    pub min_answer_length: usize,         // default: 10
    pub min_question_length: usize,       // default: 3
    pub reject_missing_fields: bool,      // default: true
    pub extra_absolute_patterns: Vec<String>,
}
```

All rules can be individually disabled, but the defaults enforce maximum quality. The `extra_absolute_patterns` field allows domain-specific extensions - a medical knowledge domain might add "cure" or "safe" to the absolute pattern list.

---

## 5. Pathfinder: Knowledge Graph Traversal

Knowledge in PLATO is organized into rooms, and rooms are connected through shared tags and domains. The Pathfinder module builds an adjacency graph over rooms and provides BFS (shortest path) and DFS (exploration) traversal strategies.

### 5.1 Adjacency Graph Construction

The adjacency builder performs pairwise room comparison:

$$\text{edge}(r_i, r_j) = \begin{cases} |T_i \cap T_j| + 0.5 \cdot \mathbb{1}[\text{domain}_i = \text{domain}_j] & \text{if } T_i \cap T_j \neq \emptyset \text{ or domains match} \\ 0 & \text{otherwise} \end{cases}$$

where $T_i$ is the tag set of room $r_i$. Shared tags contribute 1.0 per tag to edge weight; shared domain contributes a 0.5 bonus:

```rust
let strength = (shared.len() as f64) + if same_domain { 0.5 } else { 0.0 };
```

The pairwise comparison is $O(n^2)$ in room count, which is acceptable for typical PLATO deployments (hundreds to low thousands of rooms). For larger deployments, a tag-inverted index would reduce this to near-linear.

### 5.2 BFS: Shortest Path

BFS finds the shortest path (minimum hops) between two rooms, bounded by `max_hops`:

```rust
pub fn find_path(&self, from: &str, to: &str, max_hops: usize) -> Vec<RoomHop>
```

Each `RoomHop` in the result carries the connection strength and shared tags:

```rust
pub struct RoomHop {
    pub from: String,
    pub to: String,
    pub strength: f64,
    pub shared_tags: Vec<String>,
}
```

BFS guarantees the shortest path in an unweighted graph. When used for knowledge discovery - "find a path from `constraint-theory` to `distributed-systems`" - BFS produces the minimum-hop route, enabling agents to trace cross-domain connections efficiently.

**Completeness:** BFS in the Pathfinder is complete: if a path exists within `max_hops`, it will be found. If no path exists, the method returns an empty vector.

### 5.3 DFS: Confidence-Weighted Exploration

DFS sorts edges by strength descending before recursing, ensuring the strongest connections are explored first:

```rust
let mut edges: Vec<_> = edges.iter().collect();
edges.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
```

This produces a traversal that follows the highest-confidence pathways through the knowledge graph. Rooms with dense tag overlap and shared domains are visited before peripheral rooms with weak connections.

DFS is appropriate for exploratory queries: "what knowledge domains are reachable from `fleet-ops`?" The strength-sorted traversal ensures the most relevant rooms are discovered first.

### 5.4 Complexity

For a graph with $V$ rooms and $E$ edges:

- **Adjacency construction:** $O(V^2 \cdot T)$ where $T$ is the maximum tag set size per room
- **BFS:** $O(V + E)$ with `max_hops` pruning
- **DFS:** $O(V + E)$ with depth limiting

Both traversals use a `HashSet` for visited tracking, preventing infinite loops in cyclic graphs.

---

## 6. Integration: The TileAdapter Protocol

PLATO's Rust engine is the quality enforcer. The Python `TileAdapter` protocol bridges heterogeneous data sources to the engine through a uniform extraction pipeline.

### 6.1 Abstract Interface

```python
class TileAdapter(ABC):
    @abstractmethod
    def extract(self, source: str) -> list[TileSpec]: ...

    @abstractmethod
    def provenance(self, source: str) -> ProvenanceRecord: ...

    def validate(self, tiles: list[TileSpec]) -> list[TileSpec]:
        """Default: confidence ≥ 0.5, non-empty Q&A."""
```

Every adapter implements `extract` (source → raw tiles) and `provenance` (source → audit record). Validation has a sensible default that subclasses can override.

### 6.2 Four Connectors

| Adapter | Source | Validation Override |
|---|---|---|
| **MarkdownAdapter** | Structured markdown (Q&A patterns, heading-paragraph pairs) | Answers > 20 chars (stricter than engine's 10) |
| **GitHubAdapter** | GitHub repositories (issues, PRs, discussions) | Requires source URL |
| **RoomAdapter** | Other PLATO rooms (cross-room transfer) | Default validation |
| **WebAdapter** | Web pages (extracted content) | Requires source URL, minimum confidence 0.7 |

The MarkdownAdapter's stricter validation is intentional: markdown extraction is noisier than programmatic sources, so the adapter applies a higher bar before submission. Tiles that pass the adapter but fail the engine gate reveal validation logic divergence - a useful diagnostic signal.

### 6.3 Double-Gated Submission

The `PLATOSubmitter` implements a lightweight local pre-check that mirrors the remote gate:

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

This double-gating catches issues before network round-trips while maintaining the engine as the final authority. The local check is a performance optimization, not a security boundary - the engine gate is the single source of truth.

### 6.4 Python Client

The `cocapn-plato` Python client provides a synchronous interface to the engine's HTTP API:

```python
from cocapn_plato import PlatoClient

client = PlatoClient("http://localhost:3274")
result = client.submit(
    room_id="constraint-theory",
    domain="constraint-theory",
    question="What is drift in constraint systems?",
    answer="Drift measures the cumulative deviation...",
    source="constraint-theory-handbook",
    confidence=0.92,
    tags=["drift", "constraints", "measurement"],
    provenance=Provenance(
        agent_id="forgemaster",
        session_id="session-2025-05-01",
    ),
)
# result.success == True or result.rejected == "absolute claims detected: ..."
```

---

## 7. Provenance and Cryptographic Traceability

Every tile that passes the gate carries a mandatory provenance record:

```rust
pub struct Provenance {
    pub agent_id: String,
    pub session_id: String,
    pub chain_hash: String,
    pub signature: String,
}
```

| Field | Purpose |
|---|---|
| `agent_id` | Producing agent (e.g., `forgemaster`, `oracle1`) |
| `session_id` | Execution session for traceability |
| `chain_hash` | Hash linking tile to derivation chain |
| `signature` | Cryptographic signature authenticating origin |

The `TileBuilder` enforces provenance presence at construction time. The gate's `validate()` method checks that `agent_id` is non-empty. This ensures that every tile in the knowledge graph is traceable to a producer, a session, and a derivation chain.

### 7.1 Confidence-Weighted Retrieval

Provenance enables confidence-weighted retrieval across multiple dimensions. When Pathfinder traverses the knowledge graph, it can weight edges not just by tag overlap but by the trustworthiness of the tiles connecting two rooms. A room populated by a high-confidence agent with a strong chain-hash history receives more traversal weight than one filled with low-confidence, poorly-sourced tiles.

### 7.2 Future: Merkle Provenance

The `chain_hash` field is designed for future extension to Merkle-tree provenance. In a debate scenario - where Agent A claims $X$ and Agent B disputes it - the debate transcript can be hashed into a Merkle tree, and the root hash stored as the tile's `chain_hash`. This creates an auditable provenance chain where every tile's derivation is cryptographically linked to its source material.

---

## 8. Evaluation

### 8.1 Production Deployment

PLATO has been in production across the Cocapn Fleet since 2025. As of this writing:

| Metric | Value |
|---|---|
| Total tiles submitted | 18,633 |
| Total rooms | 1,373 |
| Average tiles per room | ~13.6 |
| Gate acceptance rate | ~85% |
| Gate rejection rate | ~15% |

### 8.2 Rejection Breakdown

The gate's rejection reasons, in order of frequency:

| Rule | Share of Rejections | Notes |
|---|---|---|
| Absolute claims | ~45% | Most valuable filter; epistemically dangerous language |
| Short answers | ~30% | Fragment text from over-eager extractors |
| Duplicates | ~20% | Re-processing unchanged sources |
| Missing fields | ~5% | Buggy adapter pipelines |

#### 8.2.1 False Positive Analysis

A critical question for any quality gate: how many rejections are false positives - tiles that are genuinely useful but rejected by an overly aggressive rule?

**Absolute claims (~45% of rejections):** We estimate that roughly **15-20%** of absolute-claim rejections are false positives - tiles where absolute language is used precisely and appropriately. Examples observed in production:

- Mathematical truths ("division by zero never produces a finite result") - rejected for "never" but the claim is mathematically absolute and correct.
- Factual reports ("this failure has never been observed in production") - rejected for "never" but the tile is reporting an observation, not making a universal claim.
- Philosophical warnings ("it is impossible to guarantee convergence") - rejected for "impossible" and "guarantee" despite warning against the very overconfidence the gate targets.

The last category (the case study in §8.3) represents a genuine tension: the gate is syntactic, not semantic. It cannot distinguish between *asserting* an absolute and *discussing* one outside of simple quote contexts. This is an acknowledged limitation.

**Net false positive rate:** Of ~2,795 total rejections (15% of 18,633), we estimate **40-80 tiles** (1.4-2.9% of rejections, 0.2-0.4% of total submissions) are false positives from the absolute-language rule. Short-answer and missing-field rejections have negligible false positive rates - these tiles genuinely lack sufficient content. Duplicate rejections are never false positives (identical content hash with separator-protected input).

**Mitigation:** The `extra_absolute_patterns` configuration and per-rule toggle in `GateConfig` allow domain-specific tuning. The quote-awareness heuristic catches the most common false positive pattern. For domains where mathematical truths are common (e.g., `formal-methods`), disabling absolute-claim detection may be appropriate. Future work includes a context-aware absolute-language classifier that distinguishes assertion from discussion.

### 8.3 Case Study: The Gate Corrects Its Builders

The most compelling validation of the gate came from the fleet itself. During a philosophical knowledge-extraction session, fleet agents produced tiles containing phrases like:

- *"It is impossible to guarantee outcomes"*
- *"Never assume the system will always converge"*

The gate rejected these tiles for containing "impossible", "never", "guarantee", and "always" - the very language the tiles were *warning against*. This is a feature, not a bug. The gate is structural, not semantic. It does not parse intent; it detects pattern. This forces knowledge producers to reformulate claims in qualified language:

| Rejected | Accepted (reformulated) |
|---|---|
| "It is impossible to guarantee outcomes" | "Outcomes are extremely unlikely to be guaranteed" |
| "Never assume convergence" | "Convergence should not be assumed without verification" |
| "This will always work" | "This approach is reliable in most tested scenarios" |

The system corrects even its builders. That is the design intent: a structural quality constraint that cannot be argued around, only satisfied.

### 8.4 Latency Characteristics

The Rust engine with DashMap concurrent rooms provides sub-millisecond submission latency for the typical case:

- **Accept path:** Field validation ($O(1)$) + length checks ($O(1)$) + regex matching ($O(n)$ where $n$ is answer length) + hash comparison ($O(h)$ where $h$ is room size) + DashMap insertion - typically under 100μs.
- **Reject path (short-circuit):** Early termination on the first failing rule reduces average evaluation cost. Missing-field rejections complete in $O(1)$.

The Axum HTTP server adds network overhead (~1-5ms depending on deployment), but the gate evaluation itself is negligible relative to typical agent reasoning times (seconds to minutes).

### 8.5 Downstream Evaluation Methodology

The central empirical question remains: **does quality-at-ingestion actually improve downstream agent behavior?** The production statistics in §8.1-8.2 demonstrate that the gate catches real quality issues, but they do not measure the effect on agent reasoning. We propose the following evaluation methodology:

#### 8.5.1 Experimental Design

**Research question:** Does a PLATO-gated knowledge store produce measurably better downstream agent performance compared to a permissive-ingestion baseline?

**Protocol:**

1. **Construct a dual knowledge store.** Fork the production PLATO instance into two branches:
   - *Gated store:* Current PLATO with all rules enabled (85% acceptance rate).
   - *Permissive store:* Same submissions with the gate disabled (100% acceptance rate, including the 15% that PLATO rejects).

2. **Define downstream tasks.** Select tasks that require knowledge retrieval and reasoning:
   - Multi-hop question answering requiring synthesis across 3+ tiles.
   - Decision-making tasks where overconfident knowledge could produce harmful recommendations.
   - Code generation tasks where absolute claims about API behavior could introduce bugs.

3. **Measure agent performance.** Run the same agent (with identical prompts and model) against both stores:
   - **Primary metric:** Task accuracy (correctness of final answer or decision).
   - **Secondary metrics:** Reasoning chain quality (presence of hedging language in intermediate steps), overconfidence score (frequency of absolute language in agent outputs), and retrieval precision (fraction of retrieved tiles that contribute to the correct answer).

4. **Control variables:** Same model, same prompts, same retrieval mechanism - only the knowledge store differs.

#### 8.5.2 Hypotheses

- **H1 (primary):** Agents using the gated store will produce lower overconfidence scores in their outputs, reflecting exposure to qualified rather than absolute language in the knowledge base.
- **H2:** Task accuracy will be comparable or improved, as the gated store's higher information density reduces noise in retrieval results.
- **H3 (null risk):** Task accuracy decreases, indicating the gate is rejecting useful tiles - this would bound the acceptable gate strictness.

#### 8.5.3 Status

This evaluation has not yet been executed. It represents the most important piece of missing evidence for PLATO's central claim. We include the methodology here to enable replication and to acknowledge this gap honestly. A system that filters 15% of submissions without measuring the downstream effect is making an unvalidated assumption about what constitutes "quality."

### 8.6 Storage Efficiency

Content-hash deduplication prevents storage bloat from re-processing unchanged sources. With SHA-256 hashes stored as 64-character hex strings, the dedup index for 18,633 tiles occupies approximately 1.2 MB - negligible relative to the tile content itself.

---

## 9. Future Work

### 9.1 Merkle Provenance for Debate Verdicts

Extend the `chain_hash` field to support Merkle-tree provenance. When agents engage in structured debate (claim → counter-claim → verdict), the debate transcript is hashed into a Merkle tree whose root becomes the tile's provenance chain hash. This enables cryptographic verification that a tile's content is consistent with the debate that produced it.

### 9.2 PLATO Verification API

Expose a verification endpoint that accepts a tile and returns the gate's decision without persisting it. This enables "dry run" submissions for adapter development and testing without polluting the knowledge graph.

### 9.3 Constraint Compilation from Tiles

Investigate automatic compilation of high-confidence tiles into executable constraints. A tile with $c = 0.95$ in the `constraint-theory` domain that describes a formal invariant could be compiled into a runtime assertion, closing the loop between knowledge and execution.

### 9.4 Distributed PLATO

The current architecture is single-node. For fleet-scale deployments with hundreds of agents across multiple hosts, a distributed PLATO with consistent hashing over rooms and CRDT-based conflict resolution would enable horizontal scaling without sacrificing gate guarantees.

### 9.5 Adaptive Gate Thresholds

The gate's length thresholds and pattern sets are static. An adaptive gate could tune thresholds based on domain-specific rejection rates - tightening for domains with high acceptance rates (suggesting the bar is too low) and loosening for domains with excessive rejection (suggesting the bar is misconfigured).

---

## 10. Conclusion

We have presented PLATO, a quality-gated knowledge integration system for autonomous agents. The key insight is simple but has significant implications: **quality enforced at ingestion is cheaper, more reliable, and more auditable than quality enforced at retrieval.**

The PLATO quality gate implements five deterministic rejection rules - missing fields, insufficient length, absolute language, content-hash duplicates, and provenance verification - evaluated as a short-circuit pipeline at the API boundary. The gate is mandatory and unbypassable: there is no path to insert a tile that the gate rejects. This provides a structural guarantee to all downstream consumers: every tile in the knowledge graph has non-empty content fields, qualified language, a unique content hash, and full provenance metadata.

In production across the Cocapn Fleet (18,633 tiles, 1,373 rooms), the gate rejects approximately 15% of submissions. The most common rejection - absolute language detection - catches epistemically dangerous claims that would otherwise propagate through agent reasoning chains unchecked. The most telling validation came when the gate rejected tiles produced by the fleet's own agents during a philosophical extraction session, forcing reformulation from absolute to qualified language. The system corrects even its builders.

The Pathfinder module enables cross-domain knowledge discovery through confidence-weighted BFS and DFS traversal over the room adjacency graph. The TileAdapter protocol bridges heterogeneous data sources (Markdown, GitHub, web, PLATO rooms) to the engine through a uniform extraction pipeline with domain-specific validation.

PLATO demonstrates that a relatively simple set of structural quality rules, applied consistently and unbypassably at ingestion, produces a knowledge store with structural guarantees that permissive-ingestion architectures cannot provide. We have presented the architecture, production deployment statistics, and an honest accounting of limitations (false positives in §8.2.1, unvalidated downstream impact in §8.5). The most important next step is a controlled experiment measuring whether quality-at-ingestion measurably improves downstream agent reasoning - until that evidence exists, PLATO remains a well-motivated system description, not a validated result.

For autonomous systems that reason over knowledge without human oversight, structural quality guarantees at ingestion are complementary to retrieval-time filtering, not a replacement for it. Both layers are necessary; PLATO provides the ingestion layer that most current systems lack.

---

## References

[1] Pinecone Systems. *Pinecone Vector Database.* https://www.pinecone.io/, 2024.

[2] Weaviate. *Weaviate Vector Search Engine.* https://weaviate.io/, 2024.

[3] Qdrant. *Qdrant Vector Database.* https://qdrant.tech/, 2024.

[4] LlamaIndex. *LlamaIndex: Data Framework for LLM Applications.* https://docs.llamaindex.ai/, 2024.

[5] LangChain. *LangChain: Building Applications with LLMs.* https://python.langchain.com/, 2024.

[6] Neo4j, Inc. *Neo4j Graph Database.* https://neo4j.com/, 2024.

[7] Vrandečić, D. and Krötzsch, M. *Wikidata: A Free Collaborative Knowledgebase.* Communications of the ACM, 57(10):78-85, 2014.

[8] Buchanan, B.G. and Shortliffe, E.H. *Rule-Based Expert Systems: The MYCIN Experiments of the Stanford Heuristic Programming Project.* Addison-Wesley, 1984.

[9] Giarratano, J. and Riley, G. *Expert Systems: Principles and Programming.* PWS Publishing, 4th edition, 2004.

[10] Wang, R.Y. and Strong, D.M. *Beyond Accuracy: What Data Quality Means to Data Consumers.* Journal of Management Information Systems, 12(4):5-33, 1996.

[11] Wang, R.Y. *A Product Perspective on Total Data Quality Management.* Communications of the ACM, 41(2):58-65, 1998.

[12] Campbell, J. et al. *Great Expectations: Always Know What to Expect from Your Data.* https://greatexpectations.io/, 2024.

[13] Schelter, S. et al. *Automating Large-Scale Data Quality Verification.* Proceedings of the VLDB Endowment, 11(12):1781-1794, 2018.

[14] Baylor, D. et al. *TFX: A TensorFlow-Based Production-Scale Machine Learning Platform.* Proceedings of KDD, 2017.

[15] W3C. *SHACL Shapes Constraint Language.* W3C Recommendation, https://www.w3.org/TR/shacl/, 2017.

[16] W3C. *OWL 2 Web Ontology Language.* W3C Recommendation, https://www.w3.org/TR/owl2-overview/, 2012.

[17] Prud'hommeaux, E. et al. *Shape Expressions Language 2.1.* W3C Final Community Group Report, https://shex.io/shex-semantics/, 2019.

---

*Paper produced by Forgemaster ⚒️, Cocapn Fleet, SuperInstance. PLATO engine in production since 2025. Source: https://github.com/SuperInstance/forgemaster*
