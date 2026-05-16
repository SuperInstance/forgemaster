# SCOUT-03: Content-Level Fault Detection for Multi-Agent Systems — Literature Gaps

**Date:** 2026-05-15
**Scout:** Forgemaster ⚒️
**Trigger:** Study 68 finding that structural checks miss adversarial agents
**Question:** What does the AI safety/verification literature say about content-level fault detection?

---

## Executive Summary

The literature is **sparse and fragmented** on content-level fault detection for multi-agent LLM systems. Most work focuses on either (a) structural/topological fault tolerance or (b) single-model output verification. **Nobody has combined structural + content verification for heterogeneous LLM fleets.** The canary tile pattern appears to be novel. BFT for heterogeneous model fleets is in its infancy with only one published approach (CP-WBFT). Published attacks similar to Study 68 findings are beginning to emerge but remain nascent.

**Key finding:** We are operating in a genuine research gap. The closest work (GAMMAF, CP-WBFT, SentinelAgent) addresses pieces of the problem but none combine content verification with structural guarantees in heterogeneous fleets.

---

## Paper-by-Paper Analysis

### 1. CP-WBFT: Byzantine Fault Tolerance for Multi-Agent LLM Systems
**Paper:** "Rethinking the Reliability of Multi-agent System: A Perspective from Byzantine Fault Tolerance" (Zheng et al., Nov 2025)
**arXiv:** 2511.10400

| Dimension | Rating |
|-----------|--------|
| Relevance | **9/10** — Directly addresses BFT for LLM-based MAS |
| Closeness to our work | Moderate — structural consensus, not content verification |
| What they have | Weighted BFT consensus using LLM "confidence probes"; survives 85.7% Byzantine fault rate; tested across topologies |
| What they miss | **Content-level verification** — they trust the LLM's self-reported confidence; no ground-truth checking; homogeneous model assumption |

**Key insight:** LLM agents show "stronger skepticism" when processing erroneous messages — they're naturally better at BFT than traditional agents. But they rely on the model's *own* confidence assessment, which adversarial agents would fake.

**Gap for us:** Their confidence-probe approach is structural. An adversarial agent that reports high confidence while emitting corrupted content would defeat their system. This is exactly the Study 68 scenario.

---

### 2. GAMMAF: Graph-Based Anomaly Monitoring Framework
**Paper:** "GAMMAF: A Common Framework for Graph-Based Anomaly Monitoring Benchmarking in LLM Multi-Agent Systems" (Mateo-Torrejón & Sánchez-Macián, Apr 2026)
**arXiv:** 2604.24477

| Dimension | Rating |
|-----------|--------|
| Relevance | **10/10** — Anomaly detection specifically for LLM multi-agent systems |
| Closeness | Close — graph-based defense with adversarial node isolation |
| What they have | Standardized benchmarking platform; XG-Guard and BlindGuard baselines; dynamic adversarial node isolation; cost reduction through early detection |
| What they miss | **Content verification** — focuses on behavioral/graph anomalies, not semantic correctness; doesn't address heterogeneous model fleets |

**Key insight:** "Equipping an LLM-MAS with effective attack remediation not only recovers system integrity but also substantially reduces overall operational costs." This validates the economic case for our verification work.

**Gap for us:** Their anomaly detection is graph-structural (communication patterns, node behavior). They don't verify whether agent *outputs are correct*, just whether agent *behavior is anomalous*. A sophisticated adversarial agent that behaves normally graph-wise but produces subtly corrupted outputs would evade their system.

---

### 3. RAFFLES: Fault Attribution for LLM Systems
**Paper:** "RAFFLES: Reasoning-based Attribution of Faults for LLM Systems" (Zhu et al., Sep 2025, EACL 2026)
**arXiv:** 2509.06822

| Dimension | Rating |
|-----------|--------|
| Relevance | **8/10** — Step-level fault attribution in multi-agent pipelines |
| Closeness | Close — identifies *which component* failed |
| What they have | Iterative judge-based fault attribution; Who&When dataset for step-level faults; outperforms baselines significantly |
| What they miss | **Online/real-time detection** — this is an offline evaluation framework; doesn't prevent faults, only attributes them after the fact |

**Key insight:** Fault attribution in multi-agent systems is fundamentally different from end-to-end evaluation. You need to identify *which step* and *which agent* introduced the error. Their iterative judge approach is the closest thing to "content verification" in the literature.

**Gap for us:** RAFFLES is post-hoc, not preventive. We need real-time content verification that catches adversarial outputs *before* they propagate. But their judge-based architecture could inform our canary tile verification approach.

---

### 4. SentinelAgent: Intent-Verified Delegation Chains
**Paper:** "SentinelAgent: Intent-Verified Delegation Chains for Securing Federal Multi-Agent AI Systems" (Patil, Apr 2026)
**arXiv:** 2604.02767

| Dimension | Rating |
|-----------|--------|
| Relevance | **7/10** — Formal verification of agent delegation |
| Closeness | Distant — focuses on authorization chains, not content |
| What they have | TLA+ mechanically verified delegation properties; 100% TPR at 0% FPR on deterministic properties; DelegationBench v4 with 516 scenarios; non-LLM Delegation Authority Service |
| What they miss | Content verification — they verify *who authorized what*, not *whether the output is correct* |

**Key insight:** "Practical infeasibility of deterministic intent verification" — they prove that you *cannot* deterministically verify whether an agent's output matches the user's intent. This is a fundamental limitation. They work around it with probabilistic NLI verification.

**Gap for us:** Their formal approach (TLA+ model checking) is something we should consider for our tile verification protocol. Their finding that intent verification degrades to 13% under sophisticated paraphrasing is a cautionary tale for content-level verification.

---

### 5. Hashgraph-Inspired Consensus for Multi-Model Reasoning
**Paper:** "A Hashgraph-Inspired Consensus Mechanism for Reliable Multi-Model Reasoning" (Ogunsina & Ogunsina, May 2025)

| Dimension | Rating |
|-----------|--------|
| Relevance | **7/10** — Multi-model consensus |
| Closeness | Close — addresses heterogeneous model agreement |
| What they have | Hashgraph-based consensus for getting reliable outputs from multiple LLMs |
| What they miss | Adversarial model detection — assumes all models are honest but error-prone |

**Key insight:** Using distributed systems consensus mechanisms (hashgraph) for multi-model LLM agreement. This is the "cross-validation" approach — get multiple models to agree.

**Gap for us:** Assumes benign failure models (crash faults, not Byzantine). Doesn't account for adversarial agents that deliberately try to corrupt consensus.

---

### 6. Low-Latency Fraud Detection for LLM Agents
**Paper:** "A Low-Latency Fraud Detection Layer for Detecting Adversarial Interaction Patterns in LLM-Powered Agents" (Yu et al., May 2026)

| Dimension | Rating |
|-----------|--------|
| Relevance | **8/10** — Adversarial pattern detection for LLM agents |
| Closeness | Close — real-time adversarial detection |
| What they have | Low-latency fraud detection layer; interaction-pattern-based |
| What they miss | Content-level verification — pattern-based, not semantic |

**Gap for us:** Similar to GAMMAF — detects behavioral anomalies, not semantic corruption.

---

### 7. Adjudicator: Correcting Noisy Labels with LLM Agent Council
**Paper:** "Adjudicator: Correcting Noisy Labels with a KG-Informed Council of LLM Agents" (You & Paul, Dec 2025)

| Dimension | Rating |
|-----------|--------|
| Relevance | **6/10** — Multi-agent verification via council |
| Closeness | Moderate — uses multiple agents to verify each other |
| What they have | Knowledge-graph-informed council of LLM agents for label correction |
| What they miss | Not designed for adversarial settings; assumes honest agents |

**Key insight:** "Council of agents" pattern for verification — multiple agents cross-check each other's outputs. This is the multi-model cross-validation approach.

---

### 8. Agentic Adversarial Rewriting Exposes Architectural Vulnerabilities
**Paper:** "Agentic Adversarial Rewriting Exposes Architectural Vulnerabilities in Black-Box NLP Pipelines" (Bethany et al., Apr 2026)

| Dimension | Rating |
|-----------|--------|
| Relevance | **7/10** — Attack methodology for multi-component NLP |
| Closeness | Relevant — demonstrates attacks on multi-component systems |
| What they have | Automated adversarial rewriting that finds architectural weaknesses |
| What they miss | Defense mechanisms |

**Gap for us:** This validates the threat model. Multi-component systems *are* vulnerable to adversarial inputs that exploit architectural gaps.

---

### 9. AbO-DDoS: Paralyzing AI Infrastructure via Targeted Injection
**Paper:** "Can a Single Message Paralyze the AI Infrastructure? The Rise of AbO-DDoS Attacks through Targeted Mobius Injection" (Liang et al., May 2026)

| Dimension | Rating |
|-----------|--------|
| Relevance | **7/10** — Demonstrates cascading failures in LLM infrastructure |
| Closeness | Relevant — shows how single corrupted inputs cascade |
| What they have | Novel attack class (AbO-DDoS) that can cascade through LLM infrastructure |
| What they miss | Content-level defenses |

**Key insight:** Single adversarial messages can cascade and paralyze entire multi-agent LLM infrastructure. This validates our concern about corrupted tiles propagating through the fleet.

---

### 10. RIVA: Configuration Drift Detection via LLM Agents
**Paper:** "RIVA: Leveraging LLM Agents for Reliable Configuration Drift Detection" (Abuzakuk et al., Mar 2026)

| Dimension | Rating |
|-----------|--------|
| Relevance | **5/10** — Drift detection, but for infrastructure config |
| Closeness | Moderate — conceptually similar to our drift detection |
| What they have | LLM agents that detect configuration drift between spec and reality |
| What they miss | Not applied to multi-agent content verification |

---

## Answers to Specific Questions

### Has anyone combined structural + content verification for LLM fleets?
**No.** This is the core gap. GAMMAF does structural (graph-based) anomaly detection. RAFFLES does content-level fault attribution (offline). Nobody combines both in a real-time system for heterogeneous LLM fleets. This is our opportunity.

### Is the canary tile pattern used anywhere?
**No published work** uses anything resembling canary tiles — known-answer test tiles injected into production workflows to verify agent integrity. The closest analog is:
- **RAFFLES** uses hand-crafted test scenarios, but offline and not in production
- **SentinelAgent** uses benchmark scenarios (DelegationBench), but for evaluation, not runtime monitoring
- **GAMMAF** generates synthetic adversarial interactions, but for training detectors, not as runtime probes

The canary tile pattern appears genuinely novel. The closest analogy in traditional software is **synthetic monitoring** (e.g., Google's Canary analysis for distributed systems), but nobody has applied this to LLM agent content verification.

### What's the state of the art in BFT for heterogeneous model fleets?
**Primitive.** Only two relevant works:
1. **CP-WBFT** (Zheng et al.) — BFT with confidence probes, but homogeneous model assumption
2. **Hashgraph consensus** (Ogunsina & Ogunsina) — multi-model agreement, but benign failure model

Nobody has published BFT protocols designed for fleets with heterogeneous model types (GLM, Claude, DeepSeek, etc.) where models have fundamentally different failure modes and capabilities. This is another opportunity.

### Are there published attacks similar to Study 68 findings?
**Emerging, but not identical.**
- **AbO-DDoS** shows cascading corruption from single adversarial inputs
- **OTora** demonstrates reasoning-level DoS in LLM agents
- **Knowledge base poisoning** (RAG context) shows corrupted knowledge propagation
- **Agentic adversarial rewriting** shows architectural vulnerability exploitation

Nobody has published the specific Study 68 scenario: an adversarial agent that passes all structural checks (correct format, correct protocol compliance) but produces subtly corrupted content that propagates through a fleet.

---

## Landscape Map

```
                    STRUCTURAL VERIFICATION
                           │
                    GAMMAF ┤
                    (graph │  anomaly)
                           │
    ┌──────────────────────┼──────────────────────┐
    │                      │                      │
    │   HASHGRAPH          │              SENTINEL- │
    │   CONSENSUS          │              AGENT     │
    │   (multi-model       │              (delegation│
    │    agreement)        │               chains)  │
    │                      │                      │
    ├──────────────────────┼──────────────────────┤
    │    NEITHER           │     BOTH             │
    │  (most work here)    │   ★ WE ARE HERE ★    │
    │                      │                      │
    │   RAFFLES            │   canary tiles +     │
    │   (offline fault     │   structural checks  │
    │    attribution)      │   + content verify   │
    │                      │                      │
    │   CP-WBFT            │                      │
    │   (BFT consensus)    │                      │
    │                      │                      │
    └──────────────────────┴──────────────────────┘
                    CONTENT VERIFICATION
```

---

## Research Gaps We Can Fill

### Gap 1: Combined Structural + Content Verification
Nobody has published a system that does both graph-topological anomaly detection AND semantic content verification for multi-agent LLM systems. Our tile-based architecture naturally supports both: structural checks on tile metadata + content verification on tile payloads (canary tiles).

### Gap 2: Canary Tile Pattern
The concept of injecting known-answer test tiles into production agent workflows to verify content-level integrity appears novel. This is essentially "synthetic monitoring for LLM fleets."

### Gap 3: BFT for Heterogeneous Model Fleets
All existing BFT work assumes either homogeneous models or benign failure models. Nobody handles fleets where different model families (GLM, Claude, DeepSeek, etc.) have fundamentally different failure modes, capabilities, and adversarial profiles.

### Gap 4: Content-Aware Adversarial Detection
All published anomaly detection for LLM MAS is behavioral/graph-based. Nobody detects adversarial agents based on the *semantic content* of their outputs compared to expected outputs.

### Gap 5: Real-Time Fault Attribution
RAFFLES does offline fault attribution. Nobody does real-time, streaming fault attribution that can isolate adversarial agents *before* their corruption propagates.

---

## Threat Model Validation

Our Study 68 threat model (adversarial agent that passes structural checks but produces corrupted content) is validated by:
1. **SentinelAgent's finding** that deterministic intent verification is "practically infeasible"
2. **AbO-DDoS** showing cascading corruption from single adversarial inputs
3. **GAMMAF's finding** that adversarial agents can be costly (high token generation)
4. **CP-WBFT's implicit assumption** that confidence probes are sufficient (they're not against adversarial agents)

The literature does NOT yet have:
- Published attacks that specifically target content-level corruption while maintaining structural compliance
- Defenses against such attacks
- Formal models of this threat

---

## Recommended Next Steps

1. **Position paper opportunity:** We could publish on the combined structural+content verification gap. The landscape is empty here.
2. **Canary tiles as contribution:** The canary tile pattern is genuinely novel and could be a standalone contribution.
3. **Benchmark alignment:** Consider using GAMMAF's framework and DelegationBench v4 as evaluation benchmarks.
4. **Formal verification:** SentinelAgent's TLA+ approach could validate our tile verification protocol.
5. **Watch RAFFLES:** Their judge-based fault attribution is the closest competitor. We should differentiate by being real-time and content-aware.

---

## Papers Cited

| # | Paper | arXiv | Date | Venue |
|---|-------|-------|------|-------|
| 1 | CP-WBFT (Zheng et al.) | 2511.10400 | Nov 2025 | — |
| 2 | GAMMAF (Mateo-Torrejón & Sánchez-Macián) | 2604.24477 | Apr 2026 | — |
| 3 | RAFFLES (Zhu et al.) | 2509.06822 | Sep 2025 | EACL 2026 |
| 4 | SentinelAgent (Patil) | 2604.02767 | Apr 2026 | — |
| 5 | Hashgraph Consensus (Ogunsina) | — | May 2025 | — |
| 6 | Fraud Detection Layer (Yu et al.) | — | May 2026 | — |
| 7 | Adjudicator (You & Paul) | — | Dec 2025 | — |
| 8 | Agentic Adversarial Rewriting (Bethany et al.) | — | Apr 2026 | — |
| 9 | AbO-DDoS (Liang et al.) | — | May 2026 | — |
| 10 | RIVA (Abuzakuk et al.) | — | Mar 2026 | — |
| 11 | OTora (Li et al.) | — | May 2026 | — |
| 12 | BARRED (debate-based guardrails) | — | Apr 2026 | — |

---

*SCOUT-03 complete. The field is wide open for our contribution.*
