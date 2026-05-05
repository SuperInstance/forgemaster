# FLUX v0.4.0 Release Checklist

## Prerequisites
- [ ] You have maintainer access to the FLUX crates.io packages and GitHub repository
- [ ] All PRs and changes targeted for v0.4.0 are merged into the current release branch (or `main` for straight-to-release workflows)
- [ ] You have pulled the latest repository state and have no uncommitted local changes

---

## 1. Pre-release Validation
### Required Checks
- [ ] Run full test suite across all crates:
  ```bash
  cargo test --all --all-features --release
  ```
  Confirm all tests pass, flaky tests are resolved, and no test failures remain.
- [ ] Run performance benchmarks to capture baseline metrics:
  ```bash
  cargo bench --all
  ```
  Verify no critical performance regressions are introduced in this release.
- [ ] Update the `CHANGELOG.md`:
  - Add a dedicated v0.4.0 entry with the current release date
  - List all breaking changes, new features, bug fixes, and dependency updates
  - Reference all PRs and issues included in this release
  - Follow the [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format
- [ ] Bump version numbers across all workspace crates:
  Ensure `cargo-edit` is installed first: `cargo install cargo-edit`
  Use `cargo-set-version` to update all `Cargo.toml` files:
  ```bash
  cargo set-version --workspace v0.4.0
  ```
  - Verify all version references in documentation, examples, and scripts are updated
  - Commit the version bump with a standardized commit message:
    ```bash
    git commit -am "chore: bump version to v0.4.0"
    ```

---

## 2. Build & Lint Validation
### Required Checks
- [ ] Compile release builds for all crates:
  ```bash
  cargo build --release --all
  ```
  Confirm no compilation errors occur.
- [ ] Run dry-run publish to validate package metadata:
  ```bash
  cargo publish --dry-run --all
  ```
  Resolve any errors related to invalid versions, missing fields, or dependency issues.
- [ ] Run clippy lints with strict warnings:
  ```bash
  cargo clippy --all --all-features -- -D warnings
  ```
  Fix all lint warnings and errors before proceeding.
- [ ] Verify code formatting matches project standards:
  ```bash
  cargo fmt --all --check
  ```
  If any formatting issues are found, run `cargo fmt --all` and commit the changes.

---

## 3. Publish Release
### Required Checks
- [ ] Publish all crates to crates.io in **dependency order** (publish foundational crates first, e.g. `flux-core` before `flux-cli`):
  ```bash
  # Example order for a multi-crate workspace
  cargo publish --package flux-core
  cargo publish --package flux-utils
  cargo publish --package flux-cli
  ```
  Wait 10-15 minutes between publishes to allow crates.io to propagate package updates.
- [ ] Create an annotated git tag for the release:
  ```bash
  git tag -a v0.4.0 -m "FLUX v0.4.0 Release"
  ```
- [ ] Push the tag to the remote repository:
  ```bash
  git push origin v0.4.0
  ```
- [ ] Create a GitHub Release:
  1. Navigate to the [FLUX GitHub releases page](https://github.com/your-org/flux/releases)
  2. Click "Draft a new release"
  3. Select the `v0.4.0` tag
  4. Use auto-generated release notes or customize them to match the `CHANGELOG.md` entry
  5. Attach compiled release binaries (if applicable)
  6. Click "Publish release"

---

## 4. Post-release Tasks
### Required Checks
- [ ] Update project documentation:
  - Refresh the `README.md` to reflect the latest v0.4.0 version and new features
  - Build and deploy updated API documentation:
    ```bash
    cargo doc --all --no-deps --release
    ```
  - Sync the built docs to the project's hosted documentation site
- [ ] Announce the release across community channels:
  - Post to Twitter/X, Discord, Reddit, and official FLUX community forums
  - Include key release highlights and a link to the GitHub release page
- [ ] Update the official FLUX website:
  - Add the v0.4.0 release notes
  - Update download links and version badges to point to v0.4.0
- [ ] Notify existing users:
  - Send a newsletter to registered FLUX users
  - Post updates in user community groups and support channels
- [ ] Merge release commits back to the default branch (if using a dedicated release branch):
  Create a pull request to merge the release tag into `main` and merge it

---

> Save this file to `/home/phoenix/.openclaw/workspace/docs/runbooks/release-checklist.md`