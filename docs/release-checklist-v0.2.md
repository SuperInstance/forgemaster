# FLUX v0.2.0 Release Checklist

**Release date:** 2026-05-03
**Release manager:** _________________
**Status:** [ ] In progress  [ ] Complete

---

## 0. Prerequisites

- [ ] You are on a clean `master` branch with no uncommitted changes
- [ ] All PRs for v0.2.0 scope are merged
- [ ] crates.io account authenticated: `cargo login`
- [ ] npm account authenticated: `npm login` (scope `@superinstance`)
- [ ] GitHub CLI authenticated: `gh auth status`
- [ ] GPG signing key available (for git tags)

---

## 1. Pre-Release Quality Checks

Run all checks from the workspace root. Every box must be checked before proceeding.

### 1.1 Tests

```bash
# Core crates
cargo test -p flux-isa
cargo test -p flux-ast
cargo test -p flux-provenance
cargo test -p flux-bridge
cargo test -p guard2mask
cargo test -p guardc
cargo test -p flux-hdc
cargo test -p flux-verify-api
cargo test -p cocapn-glue-core
cargo test -p cocapn-cli

# Full workspace sweep (catches integration failures)
cargo test --workspace 2>&1 | tee /tmp/flux-test-output.txt
grep -E "FAILED|error" /tmp/flux-test-output.txt && echo "FAILURES PRESENT" || echo "All tests passed"
```

- [ ] All unit tests pass
- [ ] All integration tests pass (`guardc/tests/`, `cocapn-glue-core/tests/glue_test.rs`)
- [ ] No test output contains `FAILED` or `panicked`

### 1.2 Lint

```bash
# Run clippy at deny-warnings level for release quality
cargo clippy --workspace --all-targets --all-features -- -D warnings 2>&1 | tee /tmp/flux-clippy.txt
grep "^error" /tmp/flux-clippy.txt && echo "CLIPPY ERRORS" || echo "Clippy clean"
```

- [ ] Zero clippy errors
- [ ] Zero clippy warnings (or each suppressed warning has `#[allow(...)]` with a comment)

### 1.3 Security Audit

```bash
# Requires: cargo install cargo-audit
cargo audit 2>&1 | tee /tmp/flux-audit.txt
grep -E "error|warning" /tmp/flux-audit.txt
```

- [ ] Zero `cargo audit` errors (CVEs in direct dependencies block release)
- [ ] Any advisory warnings reviewed and documented in [§9 Known Issues](#9-known-issues-to-document)

### 1.4 Documentation Build

```bash
# Build docs for all public crates; treat warnings as errors
RUSTDOCFLAGS="-D warnings" cargo doc --workspace --no-deps 2>&1 | tee /tmp/flux-docs.txt
grep "^error" /tmp/flux-docs.txt && echo "DOC BUILD ERRORS" || echo "Docs built clean"

# Open locally to spot-check
cargo doc --workspace --no-deps --open
```

- [ ] Docs build with zero errors
- [ ] `flux-isa`: ISA opcodes and encoding tables documented
- [ ] `flux-ast`: all public types have rustdoc
- [ ] `guard2mask`: compiler pipeline documented with examples
- [ ] `guardc`: CLI usage documented in lib-level rustdoc
- [ ] `flux-bridge`: bridge protocol message types documented
- [ ] `flux-hdc`: HDC algorithm overview documented
- [ ] `flux-verify-api`: API endpoints documented (or link to OpenAPI spec)
- [ ] `flux-provenance`: Merkle proof structure documented
- [ ] `cocapn-cli`: terminal output formatting API documented
- [ ] `cocapn-glue-core`: wire protocol format documented with feature flags

### 1.5 Format Check

```bash
cargo fmt --all -- --check
```

- [ ] No formatting diffs (format before release if any found: `cargo fmt --all`)

### 1.6 Minimum Supported Rust Version (MSRV)

Per `flux-hdc/Cargo.toml`, MSRV is `1.75`. Verify no crate silently requires a newer version:

```bash
rustup install 1.75
rustup run 1.75 cargo check --workspace 2>&1 | grep "^error"
```

- [ ] All crates compile on Rust 1.75

---

## 2. Version Verification

Confirm every crate's `Cargo.toml` version matches the release manifest before publishing.

```bash
# Quick check — print name + version for all release crates
for crate in flux-isa flux-ast flux-provenance flux-bridge guard2mask guardc \
             flux-hdc flux-verify-api cocapn-cli cocapn-glue-core; do
  dir=$(find . -maxdepth 3 -name "Cargo.toml" | xargs grep -l "^name = \"$crate\"" 2>/dev/null | head -1 | xargs dirname)
  version=$(grep '^version' "$dir/Cargo.toml" | head -1 | awk -F'"' '{print $2}')
  echo "$crate  =>  $version"
done
```

Expected output:

| Crate | Expected Version |
|-------|-----------------|
| `flux-isa` | `0.1.1` |
| `flux-ast` | `0.1.1` |
| `flux-provenance` | `0.1.1` |
| `flux-bridge` | `0.1.1` |
| `guard2mask` | `0.1.3` |
| `guardc` | `0.1.0` |
| `flux-hdc` | `0.1.0` |
| `flux-verify-api` | `0.1.0` |
| `cocapn-cli` | `0.1.0` |
| `cocapn-glue-core` | `0.1.0` |

- [ ] All versions match the table above
- [ ] No crate references `path = "../foo"` that should instead reference the published version
- [ ] `guardc/Cargo.toml` references `flux-isa = "0.1"` (range covers 0.1.1 ✓)
- [ ] `ct-bridge-npm/package.json` version matches npm release target (`0.1.0`)

---

## 3. CHANGELOG Verification

```bash
cat CHANGELOG.md | head -60
```

- [ ] `## [0.2.0] - 2026-05-03` section exists
- [ ] All 10 release crates are mentioned (or their features/fixes are attributed)
- [ ] `### Added`, `### Changed`, `### Fixed`, `### Security` subsections are complete
- [ ] No placeholder text (`TODO`, `TBD`, `...`)
- [ ] Links at bottom of file point to correct diff URLs:
  ```
  [0.2.0]: https://github.com/SuperInstance/JetsonClaw1-vessel/compare/v0.1.0...v0.2.0
  ```
- [ ] `[0.1.0]` baseline link also present

---

## 4. crates.io Publish Order

**Critical:** publish in dependency order. A crate cannot be published until all its dependencies are live on crates.io. Wait ~30 seconds between publishes for the index to propagate.

### Tier 1 — No internal dependencies (publish first)

```bash
# flux-isa: foundational ISA definitions
cargo publish -p flux-isa --dry-run
cargo publish -p flux-isa
sleep 30
```
- [ ] `flux-isa 0.1.1` published

```bash
# flux-ast: pure AST types, no internal deps
cargo publish -p flux-ast --dry-run
cargo publish -p flux-ast
sleep 30
```
- [ ] `flux-ast 0.1.1` published

```bash
# cocapn-glue-core: wire protocol, no internal flux deps
cargo publish -p cocapn-glue-core --dry-run
cargo publish -p cocapn-glue-core
sleep 30
```
- [ ] `cocapn-glue-core 0.1.0` published

```bash
# flux-hdc: standalone HDC library (no_std compatible)
cargo publish -p flux-hdc --dry-run
cargo publish -p flux-hdc
sleep 30
```
- [ ] `flux-hdc 0.1.0` published

### Tier 2 — Depend on Tier 1

```bash
# guard2mask: depends on flux-isa
cargo publish -p guard2mask --dry-run
cargo publish -p guard2mask
sleep 30
```
- [ ] `guard2mask 0.1.3` published

```bash
# guardc: depends on flux-isa
cargo publish -p guardc --dry-run
cargo publish -p guardc
sleep 30
```
- [ ] `guardc 0.1.0` published

```bash
# flux-bridge: depends on flux-isa (bridge protocol)
cargo publish -p flux-bridge --dry-run
cargo publish -p flux-bridge
sleep 30
```
- [ ] `flux-bridge 0.1.1` published

### Tier 3 — Service and provenance layers

```bash
# flux-provenance: Merkle provenance service
cargo publish -p flux-provenance --dry-run
cargo publish -p flux-provenance
sleep 30
```
- [ ] `flux-provenance 0.1.1` published

```bash
# flux-verify-api: verification REST API
cargo publish -p flux-verify-api --dry-run
cargo publish -p flux-verify-api
sleep 30
```
- [ ] `flux-verify-api 0.1.0` published

### Tier 4 — CLI / presentation layer

```bash
# cocapn-cli: fleet CLI formatting (terminal-facing)
cargo publish -p cocapn-cli --dry-run
cargo publish -p cocapn-cli
sleep 30
```
- [ ] `cocapn-cli 0.1.0` published

### Post-publish index verification

```bash
# Verify all crates are live and at the correct version
for pkg in "flux-isa@0.1.1" "flux-ast@0.1.1" "guard2mask@0.1.3" "guardc@0.1.0" \
           "flux-bridge@0.1.1" "flux-hdc@0.1.0" "flux-verify-api@0.1.0" \
           "flux-provenance@0.1.1" "cocapn-cli@0.1.0" "cocapn-glue-core@0.1.0"; do
  name=$(echo $pkg | cut -d@ -f1)
  ver=$(echo $pkg | cut -d@ -f2)
  result=$(curl -s "https://crates.io/api/v1/crates/$name/$ver" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('version',{}).get('num','NOT FOUND'))")
  echo "$pkg => $result"
done
```

- [ ] All 10 crates visible on crates.io at correct versions

---

## 5. GitHub Release Creation

### 5.1 Tag

```bash
# Ensure working tree is clean
git status

# Create annotated tag
git tag -a v0.2.0 -m "FLUX v0.2.0 — constraint pipeline: ISA, AST, guard2mask, guardc, bridge, HDC, verify-api, provenance, cocapn fleet"

# Push tag (triggers CI if configured)
git push origin v0.2.0
```

- [ ] Tag `v0.2.0` created and pushed
- [ ] CI passes on the tagged commit

### 5.2 Release Notes

Extract the `[0.2.0]` section from CHANGELOG.md for the release body:

```bash
awk '/^## \[0\.2\.0\]/,/^## \[0\.1\.0\]/' CHANGELOG.md | head -n -1 > /tmp/release-notes-v0.2.0.md
cat /tmp/release-notes-v0.2.0.md
```

```bash
gh release create v0.2.0 \
  --title "FLUX v0.2.0" \
  --notes-file /tmp/release-notes-v0.2.0.md \
  --latest
```

- [ ] GitHub release created at `v0.2.0`
- [ ] Release is marked as "Latest release"
- [ ] Release notes accurately reflect CHANGELOG content

### 5.3 Release Artifacts (optional but recommended)

```bash
# Build release binaries for guardc and cocapn-cli
cargo build --release -p guardc
cargo build --release -p cocapn-cli

# Strip and upload
strip target/release/guardc
strip target/release/cocapn-cli

gh release upload v0.2.0 \
  target/release/guardc \
  target/release/cocapn-cli
```

- [ ] `guardc` binary uploaded (linux-x86_64)
- [ ] `cocapn-cli` binary uploaded (linux-x86_64)
- [ ] (Optional) cross-compiled aarch64 binaries uploaded

---

## 6. npm Package — ct-bridge-npm

```bash
cd ct-bridge-npm

# Verify package.json version
cat package.json | grep '"version"'

# Clean build
npm ci
npm run build

# Run tests
npm test

# Dry-run publish to check what will be uploaded
npm publish --dry-run --access public

# Publish
npm publish --access public
```

- [ ] `npm run build` succeeds with no TypeScript errors
- [ ] `npm test` passes
- [ ] `@superinstance/ct-bridge@0.1.0` published to npm
- [ ] Package visible at `https://www.npmjs.com/package/@superinstance/ct-bridge`
- [ ] `dist/index.js` and `dist/index.d.ts` present in published package

```bash
# Verify from npm registry
npm view @superinstance/ct-bridge version
```

- [ ] npm registry returns `0.1.0`

---

## 7. Post-Release Verification (Clean Slate)

Run these in a fresh temporary directory with no local workspace context to simulate what a new user experiences.

```bash
# Create isolated environment
mkdir /tmp/flux-release-verify && cd /tmp/flux-release-verify
```

### 7.1 Cargo install from crates.io

```bash
# Wait 5 minutes after publish for full CDN propagation, then:
cargo install guardc --version 0.1.0
guardc --version   # should print "guardc 0.1.0"
```

- [ ] `guardc` installs cleanly from crates.io

### 7.2 Dependency resolution smoke test

```bash
cat > /tmp/flux-release-verify/Cargo.toml << 'EOF'
[package]
name = "verify-flux-release"
version = "0.0.1"
edition = "2021"

[dependencies]
flux-isa = "0.1.1"
flux-ast = "0.1.1"
guard2mask = "0.1.3"
flux-bridge = "0.1.1"
flux-provenance = "0.1.1"
flux-hdc = "0.1.0"
flux-verify-api = "0.1.0"
cocapn-glue-core = "0.1.0"
cocapn-cli = "0.1.0"
EOF

mkdir src && echo 'fn main() {}' > src/main.rs
cargo build 2>&1
```

- [ ] All 10 crates resolve and compile from crates.io with no errors
- [ ] No yanked version warnings
- [ ] Dependency tree is clean: `cargo tree | grep flux`

### 7.3 npm install smoke test

```bash
cd /tmp && mkdir npm-verify && cd npm-verify
npm init -y
npm install @superinstance/ct-bridge@0.1.0
node -e "const b = require('@superinstance/ct-bridge'); console.log('ct-bridge loaded:', typeof b);"
```

- [ ] npm package installs without errors
- [ ] Package loads in Node.js

### 7.4 docs.rs build check

Visit `https://docs.rs/flux-isa/0.1.1/flux_isa/` after ~10 minutes (docs.rs builds asynchronously).

- [ ] `flux-isa` docs built successfully on docs.rs
- [ ] `flux-ast` docs built successfully on docs.rs
- [ ] `guard2mask` docs built successfully on docs.rs
- [ ] No docs.rs build failures (check build log for each crate)

---

## 8. Communication Checklist

### 8.1 Blog Post

- [ ] Draft written covering:
  - What FLUX v0.2.0 is (one-paragraph elevator pitch)
  - The 10 crates and what each does (with crates.io links)
  - Key technical highlights (ISA stack VM, GUARD→mask compiler, HDC matching, provenance Merkle)
  - Quick-start code snippet (install `guardc`, write a `.guard` file, compile it)
  - Link to CHANGELOG and GitHub release
- [ ] Blog post proofread for accuracy (versions, crate names)
- [ ] Blog post published

### 8.2 Social / Distribution

- [ ] **Discord** (`#releases` or equivalent): post release announcement with:
  - Version and date
  - 3-5 bullet highlights
  - Link to GitHub release
  - Link to blog post
- [ ] **X / Twitter**: short announcement tweet with `#Rust`, `#FormalVerification`, `#FLUX` hashtags and GitHub link
- [ ] **Reddit** (`r/rust` and/or `r/embeddedlinux`): post following subreddit rules for "Show and tell" or "Project" flairs
- [ ] **Hacker News** (`Show HN`): if appropriate for current traction stage
- [ ] **crates.io** crate descriptions: verify all 10 crates have up-to-date descriptions and keywords visible on their crates.io pages

### 8.3 Internal / Team

- [ ] Release notes shared with all contributors
- [ ] Any open issues that were fixed tagged with the `v0.2.0` milestone and closed
- [ ] GitHub milestone `v0.2.0` marked as closed

---

## 9. Known Issues to Document

Document these in the GitHub release notes and/or in a `KNOWN-ISSUES.md` at repo root.

| Issue | Affected Crate(s) | Severity | Workaround |
|-------|-------------------|----------|------------|
| `flux-hdc` no_std feature requires nightly for `core::simd` | `flux-hdc` | Low | Use `default-features = true` (std) until stabilized |
| `flux-verify-api` does not yet implement authentication | `flux-verify-api` | Medium | Run behind firewall / authenticated reverse proxy; do not expose publicly |
| `cocapn-cli` depends on ANSI escape codes; output unstyled on Windows cmd.exe | `cocapn-cli` | Low | Use Windows Terminal or WSL |
| `sled` 0.34 (used in `flux-provenance`) is in maintenance mode | `flux-provenance` | Low | Replacement with `redb` planned for v0.3.0 |
| `cargo audit` may flag `sled`-transitive dependency advisories | All (via `flux-provenance`) | Informational | Acknowledged; migration tracked in issue #___ |

_Add any additional issues discovered during release QA above._

---

## 10. Rollback Plan

If a critical defect is discovered post-publish:

### 10.1 Yank a crate version

Yanking prevents new projects from resolving the bad version, but does not break existing lock files.

```bash
# Yank a specific version (irreversible — coordinate with team first)
cargo yank --version 0.1.1 flux-isa

# Undo yank if yanked in error (within a short window)
cargo yank --undo --version 0.1.1 flux-isa
```

- Do NOT yank unless the defect is security-critical or data-corrupting
- Prefer publishing a `0.1.x` patch release instead of yanking

### 10.2 Patch release procedure

```bash
# 1. Create a hotfix branch
git checkout -b hotfix/v0.1.2-flux-isa v0.2.0

# 2. Fix the defect
# 3. Bump version in Cargo.toml (e.g., flux-isa 0.1.1 -> 0.1.2)
# 4. Update CHANGELOG with new patch section
# 5. Run full pre-release checklist (§1) on affected crates only
# 6. Publish only the affected crate(s)
cargo publish -p flux-isa

# 7. Create a patch GitHub release
gh release create v0.2.1 --title "FLUX v0.2.1 (patch)" --notes "Hotfix: ..."

# 8. Merge hotfix back to master
git checkout master && git merge hotfix/v0.1.2-flux-isa
```

### 10.3 Revert git tag (before users have pulled)

```bash
# Delete local and remote tag (only if release is brand-new and < 1 hour old)
git tag -d v0.2.0
git push origin :refs/tags/v0.2.0

# Delete GitHub release (leaves tag deleted state)
gh release delete v0.2.0 --yes
```

**Note:** Once a crate version is published to crates.io, it cannot be unpublished (only yanked). Yanking is the correct mitigation for a bad crate version; reverting git history is only for the source repo.

### 10.4 npm unpublish window

npm allows unpublish within 72 hours of first publish if the package has zero dependents:

```bash
npm unpublish @superinstance/ct-bridge@0.1.0
```

After 72 hours, contact npm support or publish a `0.1.1` patch.

---

## Release Sign-off

| Checkpoint | Owner | Signed off |
|-----------|-------|-----------|
| Pre-release checks (§1) | | |
| Version verification (§2) | | |
| CHANGELOG (§3) | | |
| crates.io publish (§4) | | |
| GitHub release (§5) | | |
| npm publish (§6) | | |
| Post-release verification (§7) | | |
| Communications sent (§8) | | |
| Known issues documented (§9) | | |

**Release complete:** [ ] Yes
**Date/time:** _________________
**Signed by:** _________________
