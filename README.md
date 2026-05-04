# Cocapn FLUX — Formally Verified Constraint Checker

A formally verified constraint satisfaction engine with mathematical proofs in Coq, GPU-accelerated evaluation, and zero drift across 278M+ test cases.

## Metrics

| Metric | Value |
|--------|-------|
| Commits (tonight) | 306+ |
| Coq theorems | 16 |
| GPU evaluations | 278M+, 0 mismatches |
| Dissertation | 18,678 words, 8 chapters |
| Research papers | 5 |
| Published packages | 6 |

## Architecture

```
GUARD → guard2mask → FLUX-C → GPU / FPGA / CPU
```

- **GUARD** — Constraint specification language
- **guard2mask** — Translates guards to bitmasks
- **FLUX-C** — Core compiler (formally verified)
- **GPU/FPGA/CPU** — Multi-backend execution

## Repositories

| Repo | Description |
|------|-------------|
| [flux-compiler](https://github.com/SuperInstance/flux-compiler) | Core compiler (Coq-verified) |
| [flux-vm](https://github.com/SuperInstance/flux-vm) | Virtual machine runtime |
| [flux-hardware](https://github.com/SuperInstance/flux-hardware) | GPU/FPGA hardware backends |
| [flux-papers](https://github.com/SuperInstance/flux-papers) | Research papers |
| [flux-site](https://github.com/SuperInstance/flux-site) | Project website |
| [flux-hdc](https://github.com/SuperInstance/flux-hdc) | Hyperdimensional computing integration |
| [flux-docs](https://github.com/SuperInstance/flux-docs) | Documentation |

## Quick Start

```bash
pip install flux-constraint
```

## License

Apache 2.0
