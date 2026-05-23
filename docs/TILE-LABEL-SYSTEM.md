# Tile Label System — Self-Validating Zero-Shot Retrieval

## Core Idea

**Descriptions are not metadata. They are the retrieval contract.**

When a tile is created, the author agent writes multiple "perspectives" — bite-sized summaries tuned for different retrieval contexts. These perspectives are then **automatically play-tested** by other agents to prove the tile is findable zero-shot. A tile isn't "done" until a stranger agent can find it.

---

## The Problem This Solves

Right now: Agent A writes a tile with content but no retrieval hook. Agent B needs that knowledge. Agent B searches PLATO and gets 200 results. Agent B reads all 200. Agent B burns tokens and time.

What should happen: Agent A writes a tile and attaches 3-5 perspectives. Agent B searches. The RIGHT tile surfaces immediately because one of the perspectives matches B's intent. The system has already PROVEN this works because a test agent successfully retrieved it.

---

## Architecture

### 1. Perspective Layer (Write-Time Computation)

Every tile gets a `perspectives` array. Each perspective is a **pre-calculated retrieval contract**:

```json
{
  "id": "tile-spline-linear-compression",
  "content": "...(full 4KB tile content)...",
  "perspectives": [
    {
      "label": "one-line",
      "text": "SplineLinear: 20× weight compression using Eisenstein lattice parameterization, same accuracy as dense",
      "audience": "agent-searching",
      "tokens": 16
    },
    {
      "label": "hover-card",
      "text": "SplineLinear replaces dense weight matrices with Eisenstein integer coordinates. Achieves 16K:1 compression on drift-detect task. Deployed in plato-training v0.5.0. Works best for: classification tasks on cpu-tiny targets where memory is constrained.",
      "audience": "agent-evaluating",
      "tokens": 42
    },
    {
      "label": "context-brief",
      "text": "For CPU-tiny hardware targets, SplineLinear uses Eisenstein lattice weight parameterization instead of dense matrices. The weights live in ℤ[ω] space (Eisenstein integers), getting 16K:1 compression. Benchmarked: 100% accuracy on drift-detect, 93% on anomaly-flag. Trade-off: harder to train (5× slower convergence) but inference is sub-millisecond. Use when: memory < 2MB, accuracy > 90%, inference < 1ms.",
      "audience": "agent-deciding",
      "tokens": 68
    },
    {
      "label": "technical-compact",
      "text": "E12→dense: θ = a + bω, W = Σ θᵢ·e^(2πi·sector(θᵢ)/6). Compress by storing (a,b) pairs instead of float64 weights. 3 int16 values per weight vs 1 float64. Norm preservation proven via Weyl sector coloring.",
      "audience": "agent-implementing",
      "tokens": 38
    },
    {
      "label": "why-not-alternative",
      "text": "Why not LoRA for tiny targets: LoRA adds rank-decomposition overhead (A×B matrices) which is MORE memory than the original for small models. SplineLinear is smaller at every scale below 1M parameters. LoRA wins above 1M params.",
      "audience": "agent-comparing",
      "tokens": 40
    }
  ],
  "retrieval_status": "earmark-agentic-beta-test"
}
```

### 2. Perspective Taxonomy

| Label | Purpose | Token Budget | When Used |
|-------|---------|-------------|-----------|
| `one-line` | Search indexing, result listing | ≤20 | Agent scanning results |
| `hover-card` | Quick evaluation, "should I read this?" | ≤50 | Agent evaluating relevance |
| `context-brief` | Decision support, "should I use this?" | ≤80 | Agent deciding action |
| `technical-compact` | Implementation guidance | ≤50 | Agent writing code |
| `why-not-alternative` | Comparison, negative space | ≤50 | Agent choosing between options |
| `error-signature` | "What goes wrong with this?" | ≤30 | Agent debugging |
| `prerequisite-map` | "What must I understand first?" | ≤40 | Agent learning |
| `fleet-relevance` | "Which agents care about this?" | ≤25 | Agent routing |

Not every tile needs all perspectives. **Minimum viable: `one-line` + `hover-card`.**

### 3. Audience-Aware Compression

Perspectives are tuned by audience, not just length:

```
agent-searching   → Keywords + result. "What IS this?"
agent-evaluating  → Scope + trade-offs. "Is this relevant?"
agent-deciding    → Actionable comparison. "Should I use this?"
agent-implementing → Technical detail. "How do I build this?"
agent-comparing   → Negative space. "Why NOT the alternatives?"
agent-debugging   → Failure modes. "What breaks?"
```

The same tile means different things to different agents at different moments. Pre-computing these saves every future reader from re-deriving context.

### 4. The Earmark System

```json
{
  "retrieval_status": "earmark-agentic-beta-test",
  "earmark": {
    "created_at": "2026-05-14T16:30:00Z",
    "created_by": "forgemaster",
    "perspectives_written": 4,
    "beta_tests_passed": 0,
    "beta_tests_needed": 3,
    "in_field_retrievals": 0
  }
}
```

**Lifecycle:**

```
earmark-agentic-beta-test          ← Tile created with perspectives
        │
        ▼
[Beta test: random agent tries to find this tile zero-shot]
        │
        ├─ FAIL → perspectives rewritten, retry
        │
        ▼
field-validated                    ← 3 successful beta retrievals OR 5 in-field retrievals
        │
        ▼
proven-retrievable                 ← Tag removed entirely. Tile is "done."
```

**Earmark rules:**
1. New tiles start as `earmark-agentic-beta-test`
2. When system has spare capacity (idle agent, low queue), it picks a random earmarked tile and runs a retrieval test
3. Test: give an agent the `one-line` perspective as a search query, see if it finds the tile in top-3 results
4. Pass 3 beta tests → upgrade to `field-validated`
5. Get 5 successful in-field retrievals (real agents actually used it) → tag removed entirely
6. If a tile FAILS 3 consecutive beta tests → alert author agent to rewrite perspectives

### 5. The Beta Test Protocol

```
┌─────────────────────────────────────────────────────┐
│ AGENTIC BETA TEST                                   │
│                                                     │
│ Tester: Any idle fleet agent                        │
│ Cost: ~$0.01-0.05 per test (cheap model is FINE)   │
│ Frequency: When capacity available                  │
│                                                     │
│ Step 1: Pick random earmarked tile                  │
│ Step 2: Extract one-line perspective                │
│ Step 3: Formulate 3 paraphrased queries:            │
│         - Direct: exact perspective text             │
│         - Natural: "how do I compress weights?"      │
│         - Oblique: "tiny model, low memory, fast"    │
│ Step 4: Search PLATO with each query                │
│ Step 5: Check if target tile in top-3 results        │
│ Step 6: Record pass/fail + which perspective worked  │
│ Step 7: Update earmark counters                     │
└─────────────────────────────────────────────────────┘
```

**Why cheap models for testing:** If a Qwen-0.6B can find the tile, a GLM-5.1 definitely can. Testing with cheap models proves robustness.

### 6. Perspective Regeneration

When a tile's content is updated (superseded by new version):

1. New tile inherits perspectives from old tile
2. New tile gets `earmark-agentic-beta-test` again
3. Old tile's perspectives get `superseded_by` pointer
4. The inherited perspectives are DIFFed against new content
5. If content change is small, perspectives auto-adjust
6. If content change is large, perspectives get `earmark-rewrite-needed`

---

## Implementation Sketch

### Storage in PLATO

Perspectives live in tile metadata, not separate objects:

```python
@dataclass
class Perspective:
    label: str           # "one-line", "hover-card", etc.
    text: str            # The actual description
    audience: str        # "agent-searching", "agent-deciding", etc.
    tokens: int          # Token count (for budget enforcement)
    language: str        # "en", "ja", "zh" (multilingual perspectives)
    created_by: str      # Agent who wrote it
    created_at: str      # Timestamp
    test_results: list   # Beta test pass/fail history

@dataclass  
class Tile:
    id: str
    content: str
    perspectives: list[Perspective]
    retrieval_status: str  # earmark | field-validated | proven | None
    earmark: dict          # Test counters and history
```

### Retrieval Enhancement

When an agent queries PLATO:

```python
def search(query: str, top_k: int = 5):
    # 1. Embed query
    q_emb = embed(query)
    
    # 2. Search BOTH tile content AND perspectives
    content_hits = vector_search(q_emb, field="content")
    perspective_hits = vector_search(q_emb, field="perspectives.text")
    
    # 3. Merge with perspective boost
    # Tiles with matching perspectives rank higher
    # because perspectives are PRE-CALCULATED for retrieval
    merged = merge_results(
        content_hits, weight=0.4,
        perspective_hits, weight=0.6  # Perspectives > raw content
    )
    
    # 4. Prefer proven-retrievable tiles
    # They've been tested and found findable
    merged.sort(key=lambda t: (
        t.retrieval_status == "proven-retrievable",  # Best
        t.retrieval_status == "field-validated",      # Good
        t.retrieval_status == "earmark-agentic-beta-test",  # Unproven
    ), reverse=True)
    
    return merged[:top_k]
```

### Beta Test Runner

```python
async def run_beta_test(tile: Tile, tester_model: str = "qwen3:0.6b"):
    """Run by idle fleet agents when capacity available."""
    
    one_line = next(p for p in tile.perspectives if p.label == "one-line")
    
    queries = [
        one_line.text,  # Direct match
        paraphrase_with(tester_model, one_line.text, "natural"),  
        paraphrase_with(tester_model, one_line.text, "oblique"),
    ]
    
    passes = 0
    for q in queries:
        results = search(q, top_k=3)
        if tile.id in [r.id for r in results]:
            passes += 1
    
    tile.earmark["beta_tests_passed"] += passes
    tile.earmark["beta_tests_needed"] -= 1
    
    if passes >= 2:  # 2/3 queries found it
        tile.earmark["test_history"].append({"passed": True, "queries": queries})
    else:
        tile.earmark["test_history"].append({"passed": False, "queries": queries})
    
    # Check for promotion
    consecutive_passes = count_consecutive_passes(tile.earmark["test_history"])
    if consecutive_passes >= 3:
        tile.retrieval_status = "field-validated"
    elif count_consecutive_fails(tile.earmark["test_history"]) >= 3:
        tile.retrieval_status = "earmark-rewrite-needed"
        alert_author(tile)
```

---

## The Flywheel

```
Agent writes tile + perspectives
         │
         ▼
   Earmarked for testing
         │
         ▼
Idle agent tests retrieval ──────── FAIL ──→ Perspectives rewritten
         │                                      │
      PASS (3×)                                 └──→ Re-earmarked
         │
         ▼
   Field-validated
         │
         ▼
Real agents retrieve in field (5×)
         │
         ▼
   Proven-retrievable (tag removed)
         │
         ▼
   Perspectives become training data
   for better perspective generation
```

**The training data angle:** Every successful retrieval teaches us what good perspectives look like. Over time, we can train a perspective generator that writes better descriptions automatically. The beta test failures are the training signal.

---

## What This Enables

1. **A2A Knowledge Transfer** — Agent A writes, Agent B finds, zero prior relationship
2. **Self-Healing Index** — Bad descriptions are detected and flagged automatically
3. **Capacity-Aware QA** — Testing happens when idle, doesn't block work
4. **Progressive Trust** — Tiles earn trust through proven retrievability
5. **Multilingual Perspectives** — Same tile, perspectives in multiple languages for international fleets
6. **Perspective Inheritance** — Superseded tiles pass perspectives to successors
7. **Zero-Shot as Default** — Every tile is optimized for "never seen this before" retrieval

## Relationship to Existing Systems

| Concept | PLATO Today | With Label System |
|---------|------------|-------------------|
| Tile description | Optional, freeform | Structured perspectives, mandatory |
| Retrieval quality | Unknown, hope for the best | Measured, tested, proven |
| Agent lookup | Keyword search on content | Perspective-optimized vector search |
| Quality assurance | Manual review | Automated beta testing |
| Supersession | Content chain only | Content chain + perspective inheritance |

---

*"The best documentation is the kind that proves itself useful before anyone reads the full doc."*
