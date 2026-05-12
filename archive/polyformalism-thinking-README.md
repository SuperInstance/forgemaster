# Polyformalism: Multi-Formalism Creative Cognition ⚒️

**Core hypothesis:** Creativity requires switching between different formal systems. No single system — math, language, code, music, whatever — can produce all possible insights. Switch systems, and the gaps between them are where new things appear.

## The Short Version

Take a problem. Express it in 3+ fundamentally different formal systems. The *gaps between expressions* produce insights no single perspective can reach. We tested this across N=54 linguistic/cognitive architectures. The data supports it.

## Where the Proof Stands

### Proven
- Multi-formalism insight sets are provably larger than any single formalism (Theorem 1, formally proven)
- Linguistic modes produce **1.66x higher insight** than English control (p < 0.05)
- Thinking in a different language produces **1.59x higher insight** than translating (supports Sapir-Whorf influence, not determinism)
- Inverted-U confirmed: peak cognitive switching at round 5, decline at rounds 7-8

### Disproven (our own earlier claims)
- Non-decreasing returns: **Wrong.** Returns are *diminishing.*
- Convergence guarantee: **Wrong.** It's an empirical pattern, not a theorem.
- We published those corrections.

### Speculative (not yet proven)
- That the 7 principles are *necessary* (vs. sufficient but not minimal)
- That DMN↔ECN switching maps directly to model debate rounds (plausible, not proven)
- That 5 specific languages form a "complete cognitive set" (interesting, pending falsification)

## The Neuroscience Bit (Borrowed)

Chen et al. (2025, N=2,433) showed creative output is predicted by dynamic DMN↔ECN switching — not by raw intelligence. Moderate switching hits an inverted-U optimum. Polyformalism is an engineering approach to *operationalize* that switching.

We've mapped it to an architecture:
- **Generators** (DMN mode, high α) — produce divergent ideas
- **Evaluator** (ECN mode, low α) — scores novelty × adequacy
- **Salience Router** (middle α) — moves traffic between them
- **Synthesizer** (middle α) — cross-references surviving ideas

## Architecture (One Diagram)

```
Generator (α=0.7-0.8) → Salience Router (α=0.5-0.6) → Evaluator (α=0.3)
                                                              ↓
                                                       Synthesizer (α=0.5)
```

Stop when: agreement > 0.7, insight plateau, or 5 rounds elapsed.

## What We Actually Built

- **polyformalism-turbo-shell** — Creative cognition shell for agents, MCP server included
- **linguistic-polyformalism-shell** — Cross-linguistic thinking shell
- **polyformalism-languages** — Sapir-Whorf experiments across 14 languages

## Quick Start

```bash
# Install the creative cognition engine
git clone https://github.com/SuperInstance/polyformalism-turbo-shell

# Install the cross-linguistic thinking shell
git clone https://github.com/SuperInstance/linguistic-polyformalism-shell
```

Or just read [FRAMEWORK.md](FRAMEWORK.md) + [GUIDE.md](GUIDE.md) if you want the concepts without the code.

## Ecosystem

| Repo | What It Is | Status |
|------|-----------|--------|
| polyformalism-thinking | Core framework, research, neuroscience | ✅ Live |
| polyformalism-languages | Linguistic experiments, 14 languages | ✅ Live |
| polyformalism-turbo-shell | Agent creative cognition shell + MCP | ✅ Live |
| linguistic-polyformalism-shell | Cross-linguistic thinking shell + MCP | ✅ Live |

## License

Apache 2.0
