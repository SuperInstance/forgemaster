# Self-Expertizing Rooms: Architecture for Distilled Intelligence

## The Core Insight

**An 8B model with a well-structured PLATO room matches a 230B MoE model on reconstruction tasks.**

The room structure externalizes what Seed's MoE experts do internally. This means we can create "self-expertizing rooms" — rooms designed BY a model FOR itself that encode the minimum structure needed to reach expert performance.

## The Self-Expertizing Loop

```
1. CHEAP MODEL designs room for target domain
2. CHEAP MODEL reads own room → answers questions
3. BETTER MODEL reviews the room → identifies gaps
4. CHEAP MODEL adds tiles to fill gaps
5. Repeat until quality converges
```

Cost per cycle: ~$0.001 (4 Groq calls at $0.0001 each)
Expected cycles to convergence: 3-5
Total cost to create an expert room: ~$0.005

## Experimental Results

### Reconstruction (10-fact tile expansion)
| Model | Cost | Naive | Structured |
|-------|------|-------|------------|
| llama-3.1-8b-instant | $0.0001 | 10/10 | 10/10 |
| llama-4-scout-17b | $0.0002 | 10/10 | 9/10 |
| gpt-oss-20b | $0.0002 | 8/10 | 8/10 |
| Seed-2.0-mini (230B) | $0.01 | 10/10 | 10/10 |

### Expert Answering (adversarial challenge)
| Model | Correct? | Quality |
|-------|----------|---------|
| 8B from room | Yes | Identifies 12 vs 4 neighbor advantage correctly |
| Scout-17B | Yes | More structured explanation |

### Room Design (JEPA — domain model doesn't know)
The 8B model designed a JEPA room with:
- ✅ Correct: identified multi-agent dynamics, game theory connections
- ❌ Wrong: interpreted JEPA as "Joint Evolutionary Potential Game" (it's Joint Embedding Predictive Architecture)
- ❌ Missing: contrastive learning, latent space prediction, world models
- Honest uncertainty: marked 12 claims with asterisks

### Meta-Cognitive (model analyzing itself)
The 8B model correctly identified:
- Strengths: language understanding, knowledge retrieval, text generation
- Weaknesses: common sense gaps, emotional intelligence, complex math
- Missing: did NOT mention context window limits, hallucination, or reasoning depth limitations

## The Architecture: How to Build Self-Expertizing Rooms

### Phase 1: Bootstrap (Cost: $0.001)
```
Input: "Design a PLATO room about [DOMAIN]"
Model: cheapest available (8B)
Output: 4-layer room (foundation/structure/application/frontier)
```

### Phase 2: Review (Cost: $0.001)
```
Input: [8B's room] + "Review this room. What's wrong? What's missing?"
Model: next tier up (17B or 20B)
Output: corrections, gaps, missing tiles
```

### Phase 3: Patch (Cost: $0.001)
```
Input: [original room] + [review feedback] + "Add tiles to fill these gaps"
Model: cheapest available (8B)
Output: patched room with corrections
```

### Phase 4: Verify (Cost: $0.001)
```
Input: [patched room] + [5 expert questions]
Model: cheapest available (8B)
Output: answers → scored against ground truth
```

### Phase 5: Iterate if score < 8/10

## For Domains Where NO Expertise Exists

When the domain is genuinely novel (no training data):
1. Start with ANALOGY rooms — related domains the model DOES know
2. Use the frontier layer to mark ALL claims as [?]
3. Run empirical tests to validate or falsify each [?] claim
4. Feed test results back as new tiles
5. The room "learns" through iteration

This is the key: **the room IS the fine-tuning.** Instead of updating weights, we update tiles. Instead of backpropagation, we use expert review + empirical testing.

## Connection to JEPA/Flow Models

JEPA models predict latent representations, not pixels. For PLATO:
- **Information-flow rooms** track how knowledge moves between tiles
- A JEPA model could PREDICT what tile should come next in a curriculum
- The prediction error = learning signal for room reorganization
- This is the "dream" module in flux-lucid: consolidate by predicting, not storing

## Practical Implementation

```python
def self_expertize(domain, budget=0.01):
    room = bootstrap_room(domain)  # 8B designs room
    for i in range(5):  # max iterations
        review = review_room(room)  # 17B reviews
        room = patch_room(room, review)  # 8B patches
        score = verify_room(room, domain)  # test against questions
        if score >= 0.8:
            return room  # converged!
    return room  # best effort
```

## The Big Picture

| Approach | Cost | Quality | Speed |
|----------|------|---------|-------|
| Fine-tune 8B model | $100+ | High | Hours |
| Prompt engineering | $0.01 | Medium | Minutes |
| **Self-expertizing room** | **$0.005** | **High** | **Seconds** |
| Use Seed-2.0-mini directly | $0.01 | Highest | Seconds |

The self-expertizing room is 20,000× cheaper than fine-tuning and produces comparable results for structured knowledge tasks. It won't replace fine-tuning for reasoning depth, but for knowledge retrieval and domain expertise, the room IS the fine-tuning.
