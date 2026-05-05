# Fleet Audit Checklist

## What This Skill Is
A systematic checklist for auditing fleet repos (both SuperInstance and Lucineer orgs). Identifies quality signals, integration points, and technical debt. Used to maintain standards across 1,400+ repos.

## When to Use It
- Auditing a new repo before adding to fleet
- Reviewing PRs to ensure they meet quality gates
- Checking existing repos for drift from standards
- Preparing refactoring plans for cross-org convergence

## How It Works

### Audit Phases
1. **Structure Scan** — Directory layout, README, Cargo.toml/requirements.txt
2. **Code Quality** — Tests, documentation, error handling
3. **Integration** — Fleet dependencies, I2I protocol usage
4. **Security** — Secrets, unsafe code, shell injection risks
5. **Documentation** — README completeness, inline docs, examples

### Checklist Items

#### Structure (5 items)
- [ ] `README.md` exists and is descriptive
- [ ] Cargo.toml / requirements.txt has valid metadata
- [ ] Source in `src/` or top-level for langs without src/
- [ ] Tests directory exists (integration tests)
- [ ] License file specified

#### Code Quality (7 items)
- [ ] Test coverage ≥ 20 tests for Rust, 10 tests for Python
- [ ] All public APIs have `///` doc comments
- [ ] Error handling: Result<T> or `anyhow::Result`, no panics
- [ ] No `unwrap()` calls in production code (tests okay)
- [ ] No `todo!()` or `unimplemented!()` without tracking issue
- [ ] Clippy warnings addressed (Rust)
- [ ] Type hints (Python) or explicit types (Rust)

#### Integration (5 items)
- [ ] Uses fleet crate dependencies (SuperInstance/) before crates.io
- [ ] Implements I2I protocol for communication
- [ ] Follows fleet tile format (plato-tile-spec)
- [ ] Follows fleet trust model (flux-trust / plato-trust-beacon)
- [ ] Uses fleet room convention (world/rooms/*.yaml)

#### Security (4 items)
- [ ] No hardcoded secrets (API keys, tokens, passwords)
- [ ] No `shell=True` in subprocess calls (Python)
- [ ] SQL injection protection (if database queries)
- [ ] Input validation on all external APIs

#### Documentation (4 items)
- [ ] README has usage example
- [ ] README lists fleet integration points
- [ ] Inline docs explain WHY, not just WHAT
- [ ] Changelog or version history

### Scoring

| Category | Max Score | Weight |
|-----------|------------|--------|
| Structure | 5 | 1.0 |
| Code Quality | 7 | 1.5 |
| Integration | 5 | 1.0 |
| Security | 4 | 2.0 |
| Documentation | 4 | 1.0 |

**Pass threshold:** 80% (23/25 points)
**Good:** 90%+ (22.5/25 points)
**Excellent:** 95%+ (23.75/25 points)

### Example Audit Score

**plato-tile-spec:** 25/25 (100%)
- ✅ Structure (5/5): README, src/, tests/, License
- ✅ Code Quality (10.5/7): 31 tests, docs, Result<T>, no unwrap()
- ✅ Integration (5/5): Canonical format, fleet-wide
- ✅ Security (8/4): No secrets, no injection
- ✅ Documentation (4/4): Examples, integration notes

**flux-instinct (before FM added tests):** 5/25 (20%)
- ❌ Tests (0/7): 0 tests
- ✅ Structure (3/5): README, src/, License
- ⚠️ Documentation (2/4): Minimal docs

### Using the Checklist

1. **Clone repo:** `gh repo clone Org/repo /tmp/audit/`
2. **Run through checklist:** Score each item
3. **Note exceptions:** Document why you scored X instead of Y
4. **Generate report:** Summary + recommendations
5. **Deliver via bottle:** Send to repo owner

## Examples

**JC1 Lucineer audit (2026-04-18):**
- 200 repos scanned
- 8 key repos deep-read
- 18 flux-rust crates audited (524 tests)
- Result: High code quality, tile format fragmentation, no CI/CD

**Super Z PR review (2026-04-18):**
- 10 PRs reviewed
- All closed "superseded by merged work on main"
- Finding: PR workflow is theater, code pushed directly then PRs filed as documentation

## Related Skills
- `fleet-crate-standard` — What good structure looks like
- `fleet-room-convention` — Integration points to check
- `fleet-bottle-protocol` — How to deliver audit report
