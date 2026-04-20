# Routines — Forgemaster Operating Procedures

*Extracted from 5 days of operational logs. These are the refined patterns.*

## Build Discipline
- **Serialize cargo builds** — max 2 concurrent on 15GB RAM (3+ = OOM)
- **Write code in parallel, compile in serial** — Pi/Claude can generate simultaneously
- **rm -rf /tmp/<crate> immediately after push** — non-negotiable
- **Add .gitignore with "target/" before git init** — prevents 400MB binary artifacts
- **gh repo create --source=. --push** — cleaner than manual init + remote add

## Memory Management (Debrief Protocol)
- **free -h before installs >100MB** — need 3GB for <500MB, 5GB for >500MB
- **OpenClaw eats 1.8GB constant** — budget accordingly
- **Kill zombie pip processes** before retry: `pgrep -f 'pip3 install' | xargs kill -9`
- **Clear pip cache when >500MB**: `rm -rf ~/.cache/pip/`
- **/tmp danger zone: >2GB** — clean during heartbeats
- **8GB swap added** — safe to run 3-4 parallel builds now

## Publishing
- **crates.io rate limit**: 5 new crates per period (~1 hour cooldown)
- **Add metadata before publish**: license, repository, readme fields in Cargo.toml
- **Claude Code OOMs on batch publish** — use shell script + systemd timer instead
- **2-second delay between publishes** to avoid rate limit

## Cargo 1.75 Compatibility
- Cannot use `edition2024` crates
- Avoid: uuid, serde_yaml, thiserror v2, Tokio 1.40+
- **Inline modules > Cargo workspace** — workspace resolution breaks on 1.75
- Pin dependencies aggressively

## Borrow Checker Patterns
- **Capture fields before entry()** — `let x = self.field;` avoids E0502
- **&self vs &mut self** — read-only methods avoid interior mutability
- **emit() returns owned String** — avoids E0499/E0502 in test assertions
- **Separate mutable methods** — DeployPolicy.classify() is &self, DeployLedger.submit() is &mut self
- **Full rewrite > sed edits** for mangled files

## Claude Code Usage
- **Opus 4.7 for**: architecture, complex algorithms, reviews, cross-model analysis
- **Sonnet 4.6 for**: batch operations, metadata fixes, publish runs
- **Don't fire Claude Code for tasks already completed** — check file timestamps first
- **Claude Code OOMs at 15GB RAM** — it clones repos into /tmp
- **`--permission-mode bypassPermissions --print`** for non-interactive runs

## Fleet Communication
- **Daily bottles minimum** — even just status updates prevent communication gaps
- **Commit format**: `[I2I:TYPE] scope — summary` (em dash, imperative mood)
- **Message-in-a-bottle**: `for-fleet/` (outgoing) and `from-fleet/` (incoming) dirs
- **Beachcomb protocol**: ~30-min cadence, check for new forks/PRs/bottles
- **Bottle naming**: `BOTTLE-FROM-{AGENT}-TO-{TARGET}-{DATE}-{SUBJECT}.md`

## Constraint Theory Integration
- **snap() returns ([f32;2], f32)** — not Vec<f64> as docs suggest
- **new(density: usize)** — not new(tolerance: f64)
- **CT snap goes at MEASUREMENT boundary** — don't snap ground truth
- **880:1 seed-to-tile compression** — constraint theory concentrates information

## Scoring & Governance
- **Keyword gating**: <0.01 → score 0.0 (irrelevant tiles)
- **Deadband Protocol**: P0→P1→P2 strict priority, never skip
- **StateBridge coherence threshold**: <0.3 = P1, <0.1 = P0
- **Lock strength capped at 1.0**: `.min(1.0)`

## Tile Patterns
- **Dedup threshold 0.95** — nearly identical content; use 0.85 for merge
- **Jaccard with whole-word matching** — space-surround pattern for gates
- **TemporalValidity uses refreshed_at** — refresh() resets validity window
- **Ghost decay rate 0.96** — `1.0 * (1-0.96) = 0.04 < 0.05` threshold

## Git Patterns
- **branch -m master main** after every `gh repo create`
- **git push --force** for stale divergent branches
- **git filter-branch** to clean binary artifacts from history

## Kimi K2.5 Design
- **"Framework" not "OS"** for developer adoption
- **Pre-filled identity > blank template** — Kimi already IS Kimi
- **STOP AND DO checkpoints** — prevents batching everything
- **Banned words**: "robust", "holistic", "leverage", "seamless", "comprehensive"
