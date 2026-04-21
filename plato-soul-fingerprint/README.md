# plato-soul-fingerprint

Extract a soul vector from a git repository — coding identity compression for the fleet.

Every codebase has a personality. `plato-soul-fingerprint` extracts 63+ features from a git repository's source code, commit history, dependency graph, and documentation, then compresses them into a low-dimensional "soul vector" via PCA. This vector captures the repo's coding identity — its style, structure, communication patterns, and philosophical orientation.

## What It Measures

**6 feature extraction modules, 63+ dimensions:**

| Module | Features | What It Captures |
|--------|----------|------------------|
| **Temporal** | 30 | Commit frequency, burstiness, hourly patterns, batch vs incremental |
| **Stylistic** | 8 | Function length, naming conventions, doc comments, error handling, magic numbers |
| **Structural** | 6+ | File type distribution, test ratio, doc ratio, directory depth, module cohesion |
| **Dependency** | 4 | Dependency count, dev dep ratio, freshness, overlap with reference set |
| **Communication** | 7 | Commit message length, conventional commits, imperative verbs, emoji, references |
| **Philosophical** | 4 | Vocabulary richness, metaphor density, architecture mentions, doc length |

**Languages supported:** Python, Rust, C/C++ (automatic detection).

## Installation

```bash
pip install plato-soul-fingerprint
```

## Quick Start

```bash
# Extract a soul from a single repo
plato-soul-fingerprint extract /path/to/repo

# Extract and fit PCA across multiple repos
plato-soul-fingerprint extract /path/to/repo --fit-repos /repo1,/repo2,/repo3

# Cosine distance between two repos
plato-soul-fingerprint distance repo_a repo_b

# Compare two repos feature-by-feature
plato-soul-fingerprint compare repo_a repo_b

# Human-readable report
plato-soul-fingerprint report /path/to/repo

# Batch extract all repos in a directory
plato-soul-fingerprint batch /directory/of/repos

# Print soul signatures (compact personality descriptions)
plato-soul-fingerprint signatures /directory/of/.soul.json/files

# Hierarchical clustering
plato-soul-fingerprint cluster /directory/of/.soul.json/files
```

## Python API

```python
from plato_soul_fingerprint import SoulExtractor
from plato_soul_fingerprint.analysis import (
    soul_distance, soul_compare, soul_signature,
    feature_importance, dendrogram_text, batch_extract
)

# Extract features
extractor = SoulExtractor()
data = extractor.extract("/path/to/repo")

# Fit PCA on multiple repos
extractor.fit(["/repo1", "/repo2", "/repo3"])
transformed = extractor.transform(data)

# Soul signature (human-readable personality)
print(soul_signature(transformed))
# → "constraint-theory-core (rust, 44 commits) — heavily documented, self-contained"

# Feature importance (what drives the PCA dimensions)
importance = feature_importance(
    all_data, extractor.pca.components_,
    extractor.pca.explained_variance_ratio_,
    extractor._feature_keys
)
```

## Output

Each extraction produces two files:

- **`{repo}.soul.json`** — Machine-readable: metadata, raw features (63+), PCA vector, PCA metadata
- **`{repo}.soul.txt`** — Human-readable report with top features and PCA vector

## How It Works

1. **Extract** 63+ raw features across 6 dimensions (temporal, stylistic, structural, dependency, communication, philosophical)
2. **Standardize** via z-score normalization
3. **Reduce** via PCA (covariance eigendecomposition) — typically 95% variance in 10-12 dimensions
4. **Output** both raw and compressed representations

The PCA reduction is critical: 63 raw features → ~11 dimensions captures 95% of variance across fleet repos. This means a repo's entire coding personality can be represented in a single short vector.

## Fleet Integration

This tool is part of the [PurplePincher](https://purplepincher.org) ecosystem — the freely-available PLATO ML Matrix. Soul vectors enable:

- **Agent identity compression** — compress a codebase's personality into a comparable fingerprint
- **Style anomaly detection** — flag repos whose soul diverges from fleet norms
- **Temporal soul tracking** — extract at each git tag to plot personality evolution
- **Federated soul averaging** — find the fleet's collective coding personality
- **Constraint theory integration** — soul vectors as points on a style manifold, quantizable via Pythagorean snapping

## License

MIT
