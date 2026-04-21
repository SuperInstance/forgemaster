# 🦀 plato-soul-fingerprint

> *Every codebase leaves fingerprints. We measure them.*

Extract a **soul vector** from any git repository — a compressed mathematical representation of its coding identity. Part of the [PurplePincher](https://purplepincher.org) ecosystem.

## The Idea

When a hermit crab grows, it leaves nacre deposits on its shell. When a developer writes code, they leave **stylistic patterns** — function lengths, naming conventions, commit rhythms, documentation habits, dependency choices. These patterns form a fingerprint as unique as the coder who wrote them.

`plato-soul-fingerprint` extracts 63+ features across 6 dimensions, then compresses them via PCA into a low-dimensional **soul vector** — typically 10-12 numbers that capture the essence of a codebase's personality.

## What Makes Two Repos Similar?

The tool measures **cosine distance** between soul vectors. We tested it on 16 fleet repositories and found:

| Repo A | Repo B | Distance | Why? |
|--------|--------|----------|------|
| plato-tile-dedup | plato-tile-validate | 0.08 | Both thin, single-purpose tile crates built the same way |
| plato-tile-scorer | plato-tile-validate | 0.16 | Same tile ecosystem, different functions |
| plato-i2i-dcs | plato-room-engine | 0.34 | Both infrastructure crates, different domains |
| oracle1 (vessel) | plato-room-engine (crate) | 1.54 | Large vessel vs minimal crate — maximum soul distance |

**The closer the souls, the more similar the coding DNA.** This isn't about code duplication — it's about *style*, *structure*, and *approach*.

## Constraint Theory Mode

For fleets that value **exact geometry over floating-point approximation**, the CT quantization module snaps soul vectors to a Pythagorean coordinate grid:

```python
from plato_soul_fingerprint import snap_to_pythagorean, soul_hash

snapped = snap_to_pythagorean(soul_vector, density=100)
# Error: 0.56% relative — well within drift bounds

hash = soul_hash(snapped)
# soul_0f37c6b31fdb4ee6 — deterministic, reproducible across any machine
```

This enables **soul identity verification** — the same codebase always produces the same hash, regardless of floating-point differences between machines. The fleet's constraint theory research shows CT snap is 4% *faster* than float operations with 93.8% perfect idempotency. Soul vectors inherit these properties.

## Installation

```bash
pip install plato-soul-fingerprint
```

Requires: Python 3.8+, numpy

## Quick Start

```bash
# Extract a soul from a repo
plato-soul-fingerprint extract /path/to/repo

# Print its signature (compact personality description)
plato-soul-fingerprint signatures /path/to/souls/

# Distance between two repos
plato-soul-fingerprint distance /repo/a /repo/b

# Batch extract a directory of repos
plato-soul-fingerprint batch /directory/of/repos

# Compare two repos feature-by-feature
plato-soul-fingerprint compare /repo/a /repo/b

# Hierarchical clustering
plato-soul-fingerprint cluster /directory/of/souls/
```

## Python API

```python
from plato_soul_fingerprint import SoulExtractor
from plato_soul_fingerprint.analysis import soul_signature, soul_distance
from plato_soul_fingerprint.ct_quantize import snap_to_pythagorean, soul_hash

# Extract raw features (63+ dimensions)
extractor = SoulExtractor()
data = extractor.extract("/path/to/repo")

# Fit PCA across multiple repos
extractor.fit(["/repo1", "/repo2", "/repo3"])
transformed = extractor.transform(data)

# Get the soul signature
print(soul_signature(transformed))
# → "constraint-theory-core (rust, 44 commits) — heavily documented, self-contained"

# CT quantize for deterministic hashing
snapped = snap_to_pythagorean(transformed["pca_vector"])
print(soul_hash(snapped))
# → soul_7a3f2c9b1e0d4568
```

## Feature Dimensions

| Module | Features | What It Captures |
|--------|----------|------------------|
| **Temporal** | 30 | Commit frequency, burstiness, hourly patterns, batch vs incremental |
| **Stylistic** | 8 | Function length, naming conventions, doc comments, error handling, magic numbers |
| **Structural** | 7 | File type distribution, test ratio, doc ratio, directory depth, module cohesion |
| **Dependency** | 4 | Dependency count, dev dep ratio, freshness, ecosystem overlap |
| **Communication** | 7 | Commit message length, conventional commits, imperative verbs, emoji use |
| **Philosophical** | 4 | Vocabulary richness, metaphor density, architecture mentions, doc length |

**Languages:** Python, Rust, C, C++, CUDA (.cu/.cuh)

## Output Files

Each extraction produces:
- **`{repo}.soul.json`** — Machine-readable: metadata, 63+ raw features, PCA vector, variance info
- **`{repo}.soul.txt`** — Human-readable report with top features and PCA summary

## Fleet Integration

Part of the [PurplePincher](https://purplepincher.org) / PLATO ecosystem:

- 🦀 **Soul as shell geometry** — each codebase's personality is its shell pattern
- 🔮 **Operator diversity tracking** — different AI agents have different coding styles (signal, not noise)
- ⚓ **Constraint theory verified** — CT quantization eliminates floating-point drift
- 📊 **Temporal soul tracking** — extract at each git tag to plot personality evolution
- 🔍 **Anomaly detection** — flag repos whose soul diverges from fleet norms

## License

MIT

---

*"The shell is not a constraint; it is the crucible."* — CoCapn-Claw
