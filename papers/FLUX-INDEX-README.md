# flux-index — Semantic Code Search, Zero Dependencies

> "Spring-load any repo into a searchable dart."

`flux-index` indexes any codebase into a local vector space. Search it semantically in milliseconds. No GPU. No API. No cloud. No telemetry. Pure local.

## Install

```bash
pip install flux-index
```

That's it. Zero external dependencies beyond Python 3.8+.

## Usage

```bash
# Index a repo (runs in ~1 second for most projects)
cd your-project
flux-index .

# Search it
flux-index search "where does authentication happen"
flux-index search "how is the database connection pool managed"
flux-index search "error handling for payment failures"

# Index multiple repos, search across all of them
flux-index ~/projects/api-server
flux-index ~/projects/web-client
flux-index ~/projects/shared-libs
flux-index search --all "cross-site request forgery protection"

# Get a map of the codebase
flux-index map
```

## How It Works

1. **Extract** — Parse every function, class, struct, and commit into "tiles"
2. **Embed** — Hash-based 64-dim embeddings with IDF weighting (no model download)
3. **Snap** — Eisenstein chamber quantization for sub-millisecond approximate search
4. **Store** — Single `.flux.fvt` file per repo (~1MB per 10K LOC)

The entire index for a 50K-line project is ~2MB. Loads in 5ms. Searches in 10ms.

## Why Not grep/ripgrep?

`grep` finds literal text. `flux-index` finds meaning.

```bash
$ grep -r "compression" .
# Returns every line containing the literal string "compression"

$ flux-index search "data compression and size reduction"
# Returns the SplineLinear class, the gzip middleware, the image optimizer
# — even though none of them contain the word "compression"
```

## Why Not Sourcegraph/Copilot?

Those send your code to a server. `flux-index` runs entirely local. Works offline. Works on proprietary code. Works on air-gapped machines. Zero telemetry.

## Why Not a Local LLM?

An LLM takes 10-30 seconds to answer and needs 8GB+ of RAM. `flux-index` answers in 10ms with 50MB of RAM. It's not a chatbot — it's a compass. It tells you *where to look*.

## Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Index 10K LOC | ~1s | One-time, saved to disk |
| Index 100K LOC | ~5s | One-time, saved to disk |
| Load index | ~5ms | 14K tiles into RAM |
| Semantic search | ~10ms | Python, 14K tiles |
| Semantic search (C) | ~0.1ms | AVX-512, 14K tiles |
| Chamber search (C) | ~0.05ms | Eisenstein quantization |

## Architecture

```
Source Code
    │
    ├─ .py → extract functions, classes
    ├─ .rs → extract fns, structs, impls
    ├─ .c/.h → extract functions
    ├─ .js/.ts → extract functions, classes
    ├─ .go → extract functions, types
    └─ git log → extract commit messages
         │
         ▼
    Tiles (function, class, commit, file)
         │
         ▼
    Character n-gram hashing → 64-dim embedding
    IDF weighting from corpus statistics
         │
         ▼
    .flux.fvt file (single file, portable)
         │
         ▼
    Search: embed query → cosine similarity → top-K
    Optional: Eisenstein chamber quantization for speed
```

## The Math (simplified)

Each tile becomes a 64-dimensional vector using character n-gram hashing:

```
function_name("authenticate_user") → ["aut", "uth", "the", "hen", ...] → hash each → 64-dim vector
```

IDF weighting learns which n-grams are discriminative (rare = informative).

Eisenstein chambers snap each vector to one of 12 chambers. Search checks only nearby chambers → 12× fewer comparisons.

This is the same Eisenstein lattice used in constraint theory for sensor snap, now applied to code search. One lattice, many applications.

## Cross-Repo Search

Index multiple repos, search across all of them:

```bash
$ flux-index search --all "how does the fleet coordinate"
# Searches across: plato-training, tensor-spline, dodecet-encoder, flux-lucid, ...
# Returns: collective.py (0.82), fleet_miner.py (0.78), lighthouse.rs (0.74)
```

## Language Support

| Language | Extracts | Status |
|----------|----------|--------|
| Python | Functions, classes, methods | ✅ |
| Rust | Functions, structs, enums, impls | ✅ |
| C/C++ | Functions, structs | ✅ |
| JavaScript/TypeScript | Functions, classes | ✅ |
| Go | Functions, types | Planned |
| Java | Methods, classes | Planned |
| Any | Whole-file fallback | ✅ |

## What This Is Not

- Not an LLM. It doesn't generate code. It finds code.
- Not a search engine. No web indexing. Local repos only.
- Not a code analysis tool. No AST, no type checking. Pure text + embeddings.
- Not a replacement for grep. Use grep for exact matches, flux-index for semantic matches.

## Open Source

MIT license. Single-file C header for SIMD acceleration. Python package for convenience.

```
flux-index/
├── flux_index/           # Python package
│   ├── __init__.py
│   ├── extractor.py      # Language-specific tile extraction
│   ├── embedder.py       # Character n-gram embeddings + IDF
│   ├── search.py         # Cosine similarity search
│   ├── chambers.py       # Eisenstein chamber quantization
│   └── cli.py            # CLI interface
├── flux_vector_search.h  # Single C header for SIMD acceleration
├── README.md
└── pyproject.toml
```

## The Vision

Every repo you've ever worked with, spring-loaded and searchable. Your entire hard drive of projects, cross-referenced semantically. No cloud. No API. No waiting.

`git clone` → `flux-index .` → search.

The developer tool that respects your code by keeping it local.

---

*"The lattice doesn't care what language you wrote in. It just knows what sounds like what."*
