# Seed-2.0-mini Architecture Deep Dive

> ByteDance's Seed 2.0 family — Pro, Lite, Mini, Code
> Research compiled: 2026-05-12

---

## Executive Summary

**Seed-2.0-mini is not an open-weight model and ByteDance does not publicly disclose its parameter count, MoE vs. dense architecture, or training methodology.** Unlike DeepSeek, Qwen, or Llama — which release detailed technical papers — ByteDance's Seed team publishes only a **model card** focused on benchmarks and use-case demonstrations. The core architectural questions (active params, total params, training data, tokenizer, alignment technique) are **not answered in any public source**.

What we *do* know is assembled below from the official Seed2.0 Model Card PDF, third-party API providers, and benchmark aggregation sites.

---

## 1. What Is Seed-2.0-mini?

Seed-2.0-mini is the smallest, cheapest, highest-throughput variant in ByteDance's second-generation foundation model family (released February 14, 2026). It powers the **Doubao** app (China's #1 AI chatbot, 155M weekly active users) and is available via Volcano Engine / BytePlus / third-party providers.

| Variant | Positioning | Price (Input/Output per 1M tokens) | Key Strength |
|---------|-------------|-------------------------------------|-------------|
| **Pro** | Frontier reasoning | $0.47 / $2.37 | AIME 2025: 98.3, Codeforces: 3020 |
| **Lite** | Balanced production | $0.09 / $0.53 | Near-Pro quality at 5x less cost |
| **Mini** | High-throughput batch | $0.03 / $0.31 | Fastest, cheapest, RPM=30K |
| **Code** | Software dev specialized | ~$0.47 / ~$2.37 | Tuned on 2x coding data |

---

## 2. Architecture — What's Known vs. Unknown

### Known (from public sources):

| Spec | Value | Source |
|------|-------|--------|
| **Model ID** | `seed-2-0-mini-260215` | API providers |
| **Architecture** | Distilled from Seed 2.0 Pro — "fewer attention heads, reduced layers" | AIMLAPI model page |
| **Context window** | 256K tokens (reported by most providers); 32K (reported by AIMLAPI) | Multiple sources; 256K consensus |
| **Max output** | 128K-131K tokens | API providers |
| **Input types** | Text, Image, Video | Official model card |
| **Output types** | Text | Official model card |
| **Multimodal support** | Yes (text + image + video input) | ByteDance official |
| **Reasoning effort** | 4-level: minimal / low / medium / high | Multiple providers |
| **Tool calling** | Supported | Multiple providers |
| **Throughput** | 1.5M tokens/min, 30K requests/min | APIYI |
| **Tokenizer type** | Listed as "Other" (custom ByteDance tokenizer) | OpenRouter |

### Unknown (not publicly disclosed):

| Question | Status |
|----------|--------|
| **MoE or dense?** | ❌ Not disclosed. ByteDance's earlier Doubao 1.5 series *may* use MoE (based on sparse activation terminology in a benchmark page), but **Seed 2.0's architecture is not publicly described**. |
| **Total / active parameter count** | ❌ Completely unknown. No official or leaked number exists anywhere. |
| **Number of layers / attention heads / hidden dim** | ❌ Not disclosed |
| **Training data composition & scale** | ❌ Not disclosed. PDF mentions "systematic ingestion of long-tail domain knowledge" but no specifics. |
| **Tokenizer vocabulary size** | ❌ Not disclosed. OpenRouter labels it "Other" (custom). |
| **Training methodology** | ❌ Not disclosed. No RLHF / DPO / Constitutional AI paper from the Seed team. |
| **Knowledge distillation specifics** | ❌ AIMLAPI says "heavily distilled version of Pro" — but no details on distillation technique, temperature, or data. |
| **Alignment technique** | ❌ Not disclosed |

---

## 3. The Distillation Hypothesis (from secondary sources)

**AIMLAPI's model page** (the only source with architectural claims) states:

> *"Seed 2.0 Mini is a heavily distilled version of the Pro model. The distillation process narrows the architecture, removing attention heads and reducing layer count, specifically to minimize inference latency and operating cost."*

Key architectural claims from AIMLAPI:
- **32K context window** (disagrees with the 256K reported by most other providers — may reflect early deployment or a specific deployment variant)
- Cloud-only deployment (Volcano Engine / BytePlus ModelArk)
- OpenAI API-compatible

**Important caveat:** AIMLAPI is a third-party API aggregator, not ByteDance. Their architectural claims should be treated as informed speculation unless corroborated by official sources.

The **256K context window** is the consensus from:
- APIYI (BytePlus partner): 256K input, 128K output
- Puter.js: 262K context
- OpenRouter: 256K
- Evolink review: Same family as Pro/Lite (256K)

---

## 4. Benchmark Performance (Mini)

| Benchmark | Score | Context |
|-----------|-------|---------|
| AIME 2025 | 87.0 | Math reasoning — competitive with models 5-10x its price |
| AIME 2026 | 86.7 | Latest annual math competition |
| GPQA Diamond | 79.0 | Graduate-level Q&A |
| MMLU-Pro | 83.6 | Professional knowledge |
| HMMT Feb | 70.0 | Harvard-MIT Math Tournament |
| MathVision | 78.1 | Visual math reasoning |
| Codeforces | 1644 | Competitive programming rating |
| LiveCodeBench v6 | 64.1 | Real-time coding eval |
| SWE-Bench Verified | 67.9 | Real-world software engineering |
| MMMU | 79.7 | Multimodal understanding |
| MMMU-Pro | 71.4 | Professional multimodal |
| VideoMME | 81.2 | Video content analysis |
| MotionBench | 64.4 | Motion perception |
| TempCompass | 83.7 | Temporal reasoning |
| BrowseComp | 48.1 | Web browsing understanding |
| Terminal Bench | 36.9 | Terminal operation |
| WideSearch | 37.7 | Breadth-first search |

**Key observation:** Mini's performance collapses on agentic tasks (BrowseComp: 48.1, WideSearch: 37.7, Terminal Bench: 36.9) compared to Lite (72.1, 74.5, 45.0) and Pro (77.3, 74.7, 55.8). This confirms Mini is designed for **execution-layer throughput**, not decision-making autonomy.

---

## 5. The 4-Level Reasoning Effort System

One of Seed-2.0-mini's unique features is its adjustable reasoning effort:

| Level | Behavior | Token Cost | Performance |
|-------|----------|------------|-------------|
| **minimal** | No chain-of-thought | ~1/10 of high | ~85% of high mode |
| **low** | Light reasoning | Moderate | ~90% of high mode |
| **medium** | Standard reasoning | Standard | ~95% of high mode |
| **high** | Full chain-of-thought | Full | 100% |

> From APIYI: *"In minimal mode, overall performance is about 85% of hi mode, but token consumption is only about 1/10. This means the Mini + minimal combo can cover a huge volume of tasks that don't need deep reasoning (like classification or formatting), while Mini + hi performs close to Lite's baseline."*

This is architecturally significant: the model appears to have been **trained with variable reasoning depth** baked in — possibly through a single model with controllable inference budget (similar to DeepSeek-R1's thinking tokens, but with explicit user control).

---

## 6. What We Know About the Seed 2.0 Family (from the Official Model Card PDF)

The 50+ page official PDF reveals important contextual information but **no architecture details**:

### Design Priorities (from Section 1)
1. **Robust Visual and Multimodal Understanding** — Strengthened visual reasoning with reduced hallucination
2. **Fast and Flexible Inference** — Three model sizes for performance/speed trade-offs
3. **Reliable Complex Instruction Execution** — Structured reasoning and constraint satisfaction as first-class requirements
4. **Real-world complexity** — Moving from Olympiad problems to research-level reasoning

### Training Implications (inferred, not stated)
- The PDF mentions "systematic ingestion of long-tail domain knowledge" — likely a curated training data strategy
- The model demonstrates strong **in-context learning** from long-form sources (Encyclo-K evaluation)
- The "4-level reasoning effort" suggests training with variable-length chain-of-thought, possibly through reinforcement learning
- Agentic coding capabilities (frontend-heavy) reflect real-world usage data from Doubao

### Evaluation Philosophy
The PDF frames evaluation around four dimensions:
1. **Science Discovery** — Scientific coding, research reasoning
2. **Vibe Coding** — End-to-end software engineering
3. **Context Learning** — Long-context integration
4. **Real-World Tasks** — Enterprise workflows

This is not a standard academic benchmark suite — it's ByteDance's own framework for tracking progress on real-world complexity. The PDF includes extensive case studies (FEAL cryptanalysis, FreeCAD operation, CapCut editing, quantum compiling, general relativity, computational chemistry) but **no architecture disclosures**.

---

## 7. Comparison: Seed-2.0-mini vs. Comparable Models

| Feature | Seed-2.0-mini | Qwen-2.5-7B | Llama-3.2-3B | GPT-4.1-mini |
|---------|---------------|-------------|--------------|-------------|
| **Architecture** | Unknown (distilled) | Dense Transformer | Dense Transformer | Unknown |
| **Parameters** | Unknown | 7B | 3B | Unknown |
| **Context** | 256K | 128K | 128K | 1M |
| **Open weights** | ❌ | ✅ | ✅ | ❌ |
| **MoE** | Possibly | ❌ | ❌ | Unknown |
| **Known training data** | ❌ | ✅ (18T tokens) | ✅ (15T tokens) | ❌ |
| **Tokenizer disclosed** | ❌ | ✅ (151k vocab) | ✅ (128k vocab) | ❌ |
| **Alignment** | Unknown | RLHF | RLHF | RLHF |
| **AIME 2025** | 87.0 | ~40 | ~15 | ~60 |
| **MMLU-Pro** | 83.6 | ~65 | ~35 | ~75 |

**Key insight:** Seed-2.0-mini punches far above its price point on benchmarks. If it has ~7B active parameters (speculation), it would be roughly **10-20x more efficient on a per-parameter MMLU-Pro basis** than comparable open models. This efficiency likely comes from one or more of:
1. **Knowledge distillation** from a much larger Pro variant
2. **MoE architecture** with sparse activation
3. **Superior training data** curation
4. **Custom tokenizer** optimized for the task distribution
5. **Variable reasoning** (the 4-level effort system)

---

## 8. Open Questions & Research Directions

1. **Why does it work so well at temp=1.0?** — This was observed in the original prompt. The 4-level reasoning effort system may explain this: if Mini was trained to produce calibrated outputs at high temperature, the reasoning effort parameter may act as a proxy for temperature-control during training.

2. **What is the distillation technique?** — If Mini truly is a distilled Pro, the technique could be:
   - Standard knowledge distillation (logit matching)
   - Progressive layer pruning + fine-tuning
   - Sparse MoE sub-selection from Pro's experts
   - Quantization-aware training at low precision

3. **Why does Mini lose so badly on agentic tasks?** — BrowseComp (48.1) vs. Lite (72.1) suggests the distillation process specifically pruned the agentic reasoning pathways, or the shorter training horizon used during distillation didn't cover multi-step agent trajectories.

4. **Is there a technical report coming?** — ByteDance has published tech reports for prior models (Seed1.6, Seed1.5-VL). The Seed2.0 model card says "This report presents our initial progress" — suggesting a more detailed technical paper may follow.

---

## 9. Sources

| Source | Type | What It Contains |
|--------|------|-----------------|
| Seed2.0 Model Card PDF (official) | Official | Benchmarks, use cases, design philosophy — NO architecture details |
| Volcengine / BytePlus | API provider | Model IDs, pricing, availability |
| APIYI (BytePlus partner) | Third-party reseller | Mini specs: 256K ctx, 4-level effort, RPM/TPM |
| AIMLAPI | Third-party aggregator | Claims 32K ctx, distilled arch, reduced heads/layers |
| Evolink.ai review | Third-party analysis | Family comparison, pricing tables, gap analysis |
| Puter.js | Third-party API | 262K context window, OpenAI-compatible |
| OpenRouter | Third-party API | Tokenizer: "Other", pricing, multimodal support |

## 10. Bottom Line

**Seed-2.0-mini's architecture is not publicly known.** ByteDance has intentionally kept architectural details proprietary — in contrast to DeepSeek, Qwen, and Meta's Llama families which publish detailed technical reports.

What is clear: Mini is a **distilled, high-throughput variant** of the Seed 2.0 family, optimized for cost-effective batch processing at scale. Its efficiency likely comes from a combination of knowledge distillation, a superior training data pipeline (leveraging Doubao's 155M weekly users), and ByteDance's internal infrastructure optimizations.

The adjustable 4-level reasoning effort system is a genuinely novel feature not seen in other models at this price point, and may represent a significant architectural innovation in controllable inference.
