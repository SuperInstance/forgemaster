# DEMOS-FIX — Web Audit Fix Report
**Date:** 2026-05-17

## Findings

### ✅ All 10 demo pages are live and working (HTTP 200)
| Demo | Status |
|------|--------|
| demo-divergence-tolerance.html | 200 |
| demo-eisenstein-3d.html | 200 |
| demo-eisenstein.html | 200 |
| demo-fleet-murmur.html | 200 |
| demo-fleet-spread.html | 200 |
| demo-narrows.html | 200 |
| demo-plato-client.html | 200 |
| demo-playground.html | 200 |
| demo-voxel-v2.html | 200 |
| demo-voxel.html | 200 |

### 🔧 Fixed Issues (commit 26f0a80)

#### 1. Penrose Palace link → 404
- **Was:** `https://superinstance.github.io/penrose-memory-palace/` (404 — GH Pages never deployed)
- **Fixed:** → `https://github.com/SuperInstance/penrose-memory-palace-early-version` (repo link)
- Repo was renamed to `penrose-memory-palace-early-version`, no GH Pages configured

#### 2. Demo links using old domain
- **Was:** `superinstance.github.io/cocapn-ai-web/demo-*.html` (301 redirect)
- **Fixed:** → `plato.purplepincher.org/demo-*.html` (canonical, direct 200)

#### 3. Wiki nav broken links in history.html
- **Was:** Links to `architecture.html`, `fleet.html`, `philosophy.html` (don't exist)
- **Fixed:** Replaced with actual wiki pages: getting-started, technology, research, applications, glossary

### ⚠️ Remaining Issues (not fixed — need investigation)

#### Keel repo broken links
- `https://github.com/SuperInstance/keel/blob/main/RESEARCH-FINDINGS.md` → 404
- `https://github.com/SuperInstance/keel/blob/main/THE-BOAT-IS-THE-QUESTION.md` → 404
- `https://github.com/SuperInstance/keel/blob/main/UNIVERSAL-LAW.md` → 404
- These files may have been moved/renamed in the keel repo

#### crates.io → 404
- `https://crates.io` returns 404 via curl (likely just anti-bot, not actually broken in browser)

### Site Info
- **Domain:** plato.purplepincher.org
- **Pages source:** master branch, root `/`
- **Status:** built
