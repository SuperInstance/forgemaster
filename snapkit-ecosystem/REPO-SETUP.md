# SnapKit Repository Setup Guide

This document describes how to create and configure the 7 GitHub repositories for the SnapKit ecosystem.

## Repository Overview

| # | Repo Name | Contents | Registry |
|---|-----------|----------|----------|
| 1 | `snapkit-python` | Python package (snapkit/) | PyPI |
| 2 | `snapkit-rust` | Rust crate | crates.io |
| 3 | `snapkit-js` | TypeScript/JS package | npm |
| 4 | `snapkit-c` | C library | GitHub releases |
| 5 | `snapkit-cuda` | CUDA library | GitHub releases |
| 6 | `snapkit-fortran` | Fortran module | fpm registry |
| 7 | `snapkit-ecosystem` | Cross-repo README, setup docs, CI templates | — |

---

## 1. Create the Repositories

For each repo, create via `gh` CLI or GitHub web UI:

```bash
# Clone first, then create remote
cd /path/to/repo

# Create GitHub repo
gh repo create SuperInstance/snapkit-python \
    --public \
    --description "Tolerance-compressed attention allocation — Python implementation" \
    --homepage "https://pypi.org/project/snapkit/" \
    --license MIT \
    --gitignore Python

# Set as remote
git remote add origin git@github.com:SuperInstance/snapkit-python.git
git push -u origin main
```

Repeat for all 7 repos with appropriate descriptions:

| Repo | Description | Gitignore |
|------|-------------|-----------|
| `snapkit-python` | "Tolerance-compressed attention allocation — Python implementation" | Python |
| `snapkit-rust` | "Tolerance-compressed attention allocation — Rust crate" | Rust |
| `snapkit-js` | "Tolerance-compressed attention allocation — TypeScript/JS package" | Node |
| `snapkit-c` | "Tolerance-compressed attention allocation — C library" | C |
| `snapkit-cuda` | "Tolerance-compressed attention allocation — CUDA kernel library" | CUDA |
| `snapkit-fortran` | "Tolerance-compressed attention allocation — Fortran 2008 module" | Fortran |
| `snapkit-ecosystem` | "SnapKit ecosystem — cross-repo documentation and setup" | — |

---

## 2. Files Per Repo

### snapkit-python
```
snapkit-python/
├── pyproject.toml       # Build config, project metadata
├── setup.cfg            # Fallback build config
├── MANIFEST.in          # Package manifest
├── README.md            # Documentation
├── LICENSE              # MIT
├── .gitignore           # Python gitignore
├── snapkit/             # Package source
│   ├── __init__.py
│   ├── snap.py
│   ├── delta.py
│   ├── attention.py
│   ├── scripts.py
│   ├── learning.py
│   ├── topology.py
│   ├── cohomology.py
│   ├── adversarial.py
│   ├── crossdomain.py
│   ├── streaming.py
│   ├── visualization.py
│   ├── integration.py
│   ├── serial.py
│   ├── pipeline.py
│   └── cli.py
├── tests/
│   ├── test_core.py
│   └── test_advanced.py
└── examples/
    ├── example_poker.py
    ├── example_learning.py
    └── example_streaming.py
```

### snapkit-rust
```
snapkit-rust/
├── Cargo.toml
├── Cargo.lock
├── README.md
├── LICENSE-MIT
├── LICENSE-APACHE
├── .gitignore
├── src/
│   ├── lib.rs
│   ├── snap.rs
│   ├── delta.rs
│   ├── attention.rs
│   ├── scripts.rs
│   ├── learning.rs
│   ├── topology.rs
│   ├── eisenstein.rs
│   ├── adversarial.rs
│   ├── streaming.rs
│   └── pipeline.rs
├── tests/
├── benches/
│   └── snap_bench.rs
└── examples/
    ├── poker.rs
    ├── rubik.rs
    ├── monitoring.rs
    └── learning.rs
```

### snapkit-js
```
snapkit-js/
├── package.json
├── tsconfig.json
├── README.md
├── LICENSE
├── .gitignore
├── src/
│   ├── index.ts
│   ├── snap.ts
│   ├── delta.ts
│   ├── attention.ts
│   ├── scripts.ts
│   ├── learning.ts
│   ├── topology.ts
│   ├── eisenstein.ts
│   ├── adversarial.ts
│   ├── streaming.ts
│   ├── pipeline.ts
│   ├── visualization.ts
│   └── types.ts
├── dist/              # Build output (committed for npm)
├── test/
└── examples/
```

### snapkit-c
```
snapkit-c/
├── Makefile
├── README.md
├── LICENSE
├── snapkit.pc.in
├── snapkit-config.cmake.in
├── .gitignore
├── include/snapkit/
│   ├── snapkit.h
│   └── snapkit_internal.h
├── src/
│   ├── core_ade.c
│   ├── core_delta.c
│   ├── core_eisenstein.c
│   ├── core_eisenstein_optimal.c
│   └── core_snap.c
├── tests/
│   ├── test_snapkit.c
│   └── bench_snapkit.c
└── examples/
    ├── example_eisenstein.c
    └── example_delta.c
```

### snapkit-cuda
```
snapkit-cuda/
├── Makefile
├── README.md
├── LICENSE
├── .gitignore
├── include/snapkit_cuda/
│   ├── snapkit_cuda.h
│   ├── eisenstein_snap.cuh
│   ├── eisenstein_snap_optimal.cuh
│   ├── batch_snap.cuh
│   ├── delta_detect.cuh
│   ├── attention.cuh
│   ├── topology.cuh
│   └── reduce.cuh
├── src/
│   ├── eisenstein_snap.cu
│   ├── batch_snap.cu
│   ├── delta_detect.cu
│   ├── attention.cu
│   ├── topology.cu
│   ├── reduce.cu
│   └── snapkit_cuda.cu
├── kernels/
│   ├── eisenstein_snap_kernel.cuh
│   ├── delta_threshold_kernel.cuh
│   ├── attention_weight_kernel.cuh
│   └── topology_snap_kernel.cuh
├── ptx/
│   ├── eisenstein_snap.ptx
│   └── eisenstein_snap_sm89.ptx
├── tests/
├── benches/
├── examples/
└── docs/
```

### snapkit-fortran
```
snapkit-fortran/
├── fpm.toml
├── Makefile
├── README.md
├── LICENSE
├── .gitignore
├── src/
│   ├── snapkit.f90
│   ├── snap.f90
│   ├── delta.f90
│   ├── attention.f90
│   ├── scripts.f90
│   ├── learning.f90
│   ├── topology.f90
│   ├── eisenstein.f90
│   └── visualization.f90
├── app/
│   ├── demo_poker.f90
│   ├── demo_learning.f90
│   └── benchmark.f90
└── test/
    ├── test_snap.f90
    ├── test_delta.f90
    ├── test_attention.f90
    ├── test_eisenstein.f90
    ├── test_topology.f90
    └── run_all.f90
```

### snapkit-ecosystem
```
snapkit-ecosystem/
├── README.md       # Cross-repo documentation
├── REPO-SETUP.md   # This file
└── .github/
    └── workflows/
        └── ci.yml  # Shared CI template
```

---

## 3. Branch Protection

For all 7 repos, enable these branch protection rules on `main`:

| Setting | Value |
|---------|-------|
| Require pull request before merging | ✅ |
| Require approvals | 1 |
| Dismiss stale reviews | ✅ |
| Require status checks | ✅ (CI must pass) |
| Require branches up to date | ✅ |
| Include administrators | ✅ (recommended) |
| Allow force pushes | ❌ |
| Allow deletions | ❌ |

```bash
# Set branch protection for a repo (requires admin access)
gh api repos/SuperInstance/snapkit-python/branches/main/protection \
    --method PUT \
    --field required_status_checks='{"checks":[{"context":"continuous-integration"}]}' \
    --field enforce_admins=true \
    --field required_pull_request_reviews='{"required_approving_review_count":1}' \
    --field restrictions=null
```

---

## 4. CI/CD Recommendations

### Python (PyPI publish)

`.github/workflows/pypi.yml`:
```yaml
name: Publish to PyPI
on:
  release:
    types: [published]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m pip install build twine
      - run: python -m build
      - run: python -m twine upload dist/* --skip-existing
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
```

### Rust (crates.io publish)

`.github/workflows/crates.yml`:
```yaml
name: Publish to crates.io
on:
  release:
    types: [published]
jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions-rust-lang/setup-rust-toolchain@v1
      - run: cargo publish --token ${{ secrets.CRATES_IO_TOKEN }}
```

### TypeScript (npm publish)

`.github/workflows/npm.yml`:
```yaml
name: Publish to npm
on:
  release:
    types: [published]
jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          registry-url: 'https://registry.npmjs.org'
      - run: npm ci
      - run: npm run build
      - run: npm publish
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

### C/CUDA/Fortran (GitHub releases)

`.github/workflows/release.yml`:
```yaml
name: Build and Release
on:
  release:
    types: [published]
jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build
        run: make clean && make
      - name: Upload artifacts
        uses: actions/upload-release-asset@v1
        with:
          upload_url: ${{ github.event.release.upload_url }}
          asset_path: ./build/
          asset_name: snapkit-release.tar.gz
          asset_content_type: application/gzip
```

### Shared CI (all repos)

Every repo should have basic CI:

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build
        run: make  # or cargo build, npm run build, pip install -e .
      - name: Test
        run: make test  # or cargo test, npm test, python -m pytest
```

---

## 5. Post-Creation Checklist

- [ ] All 7 repos created and pushed
- [ ] Branch protection enabled on `main`
- [ ] CI passing on all repos
- [ ] Python: `twine check dist/*` passes
- [ ] Rust: `cargo package --list` validates packaging
- [ ] JS: `npm pack --dry-run` shows correct files
- [ ] C: `make clean all test` completes successfully
- [ ] All READMEs render properly on GitHub
- [ ] Cross-repo links in ecosystem README point to actual repos
- [ ] API tokens stored in GitHub Secrets:
  - `PYPI_API_TOKEN` — for snapkit-python
  - `CRATES_IO_TOKEN` — for snapkit-rust
  - `NPM_TOKEN` — for snapkit-js

---

## 6. Domain & Registration

### PyPI
```bash
# Register: https://pypi.org/manage/projects/
# Then:
python -m twine upload dist/*
```

### crates.io
```bash
# Register: https://crates.io/me
cargo login $CRATES_IO_TOKEN
cargo publish
```

### npm
```bash
# Register: https://www.npmjs.com/settings/tokens
npm login
npm publish --access public
```

### fpm registry
Submit a PR to: https://github.com/fortran-lang/fpm-registry
Add `snapkit` to the registry database.

---

*Built for the Cocapn fleet. Ship it.*
