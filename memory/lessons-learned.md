# Lessons Learned — Forgemaster ⚒️

> Distilled from 2 nights of autonomous work (2026-04-24/25, 2026-04-25/26).
> Raw logs → `memory/2026-04-2*.md`. This is the permanent version.

---

## 1. Garbage Collection Strategy

**Problem:** /tmp grew to 5.3GB from experiment artifacts, compiled targets, and batch scripts.

**Lesson:** GC in three layers:
1. **Build artifacts** (`target/`) — delete immediately after publish. Never keep compiled binaries.
2. **Source archives** — copy to `memory/gpu-experiments/{name}/` then delete from /tmp. One canonical location.
3. **Batch scripts** — keep only last 3. Older ones are in git history.
4. **Published crate dirs** — source is on crates.io + archived in memory/. Nuke from /tmp.

**Result:** 5.3GB → 146MB. Target: keep /tmp under 200MB.

**GC schedule:** Run at start of each shift. Check with `du -sh /tmp/`.

---

## 2. Rate Limiting is Real (Not Transient)

**Problem:** PLATO API has a hard 60 req/min limit. First 57 batches used 0.15-0.2s sleep, which was fine for ~47-tile batches (9.4s < 60s window). But batch 60 (38 tiles) hit the limit because previous batch had JUST finished.

**Lesson:**
- 60 tiles/min = 1 tile/sec maximum sustained rate.
- 0.2s sleep = max 5 tiles/10s = 30 tiles/minute (safe margin).
- **Never run two batch scripts back-to-back.** Always wait 60+ seconds between batches.
- When rate limited, the script continues (subsequent tiles get 403'd too). Better to detect and sleep.

**Fix:** Add rate-limit detection to submit_tile:
```bash
if echo "$response" | grep -q "Rate limited"; then
    echo "[RATE LIMITED — sleeping 60s]"
    sleep 60
    # Retry
fi
```

---

## 3. Tool Agent OOM Patterns

**Pattern observed across 3+ nights:**

| Agent | Task | Result | Lesson |
|-------|------|--------|--------|
| Kimi | Rust benchmark | OOM (signal 15) | Keep prompts under 100 words. Use --quiet. |
| Kimi | Benchmark suite | OOM (signal 15) | Don't chain multiple subtasks in one prompt. |
| Kimi | Angular NN v0.2 | OOM (signal 15) | Break into: generate code, then compile, then analyze. |
| Claude Code | CUDA kernel v1 | SUCCESS | Architecture/planning is Claude's strength. |
| Claude Code | WASM design+impl | SUCCESS | Complex systems design. |
| Claude Code | SIMD snap | SUCCESS | Low-level optimization. |
| Direct writing | ALL benchmarks | SUCCESS | Always faster than delegating. |

**Lesson:** Write code directly. Use Claude for architecture/design docs. Use Kimi only for single-file implementations under 200 lines. Never delegate benchmark code — it's straightforward enough to write faster than the OOM-retry cycle.

---

## 4. crates.io Publishing Checklist

Learned from publishing 12 crates:

1. **Max 5 keywords** — error is silent until upload fails.
2. **No git dependencies** — `path = "..."` or git URLs in Cargo.toml will be rejected.
3. **Edition 2021 only** — rustc 1.95.0 on eileen doesn't support edition2024.
4. **Categories matter** — "mathematics" and "development-tools" are the most relevant for CT crates.
5. **README is the storefront** — badges, quick start, API table = professional.
6. **Version bump required** — can't re-upload same version. Ever.
7. **Test before publish** — `cargo publish --dry-run` catches most issues.

**Template crate structure:**
```
Cargo.toml  (5 keywords, 1-2 categories, MIT license)
README.md   (badges, description, install, quick start, license)
src/lib.rs  (modular, documented, 8+ tests)
LICENSE     (MIT)
```

---

## 5. PyPI Publishing Checklist

Learned from publishing 48 packages:

1. **Token in `~/.pypirc`** — `[pypi]` section with `token = pypi-AgEIcHlwaS5vcmc...`
2. **`pyproject.toml` only** — setup.py is deprecated. Use build system = hatchling.
3. **Name conflicts** — check `pip search` (or just try `twine upload`). `git-agent` was taken → published as `cocapn-git-agent`.
4. **File hash reuse** — can't re-upload same filename. Must bump version.
5. **Zero-dependency is best** — fleet packages are all pure Python with no deps.
6. **Batch publish** — script the whole thing. Don't publish one-by-one interactively.

---

## 6. Git Workflow Patterns

**The rebase dance** (every push):
```bash
git stash && git pull --rebase origin master && git stash pop; git push origin master
git stash && git pull --rebase forgemaster master && git stash pop; git push forgemaster master
```

**Stash pop conflicts with `.keeper/`:** Exit code 1 is non-fatal. The `.keeper/` files get modified by external processes (Oracle1, keeper scripts). Just ignore the exit code.

**Commit message format:** `[I2I:TYPE] summary` — TYPE is TILE, PUBLISH, EXPERIMENT, GC, DOC.

**Push cadence:** Every 30 min minimum. Never accumulate more than 2-3 unpushed commits.

---

## 7. PLATO Content Strategy

**What works:**
- Constraint theory framing for every domain (snap, deadband, drift, holonomy, MultiManifold)
- Fleet analogy paragraph at the end of every tile
- 5-point numbered lists with concrete examples
- Cross-domain linking (referencing other rooms)

**What doesn't:**
- Special characters in JSON (backticks, unescaped quotes) → HTTP 403 injection detection
- Tiles without fleet context feel disconnected from PLATO's mission
- Very short tiles (<200 chars answer) don't add value

**Room deepening > room creation:** PLATO had 581 rooms but many with 1-3 tiles. Deepening a room to 5+ tiles is more valuable than creating a new 1-tile room.

**Domain layering (GSM pattern):**
1. Concept (what is it?)
2. Mechanics (how does it work?)
3. Implementation (code/tools)
4. Optimization (benchmarks/performance)
5. Research (open questions/future work)

---

## 8. Experiment Documentation Pattern

**Every experiment gets:**
1. Source code → `memory/gpu-experiments/{name}/`
2. Results → inline in the session summary
3. Key insight → one sentence summarizing what we learned
4. Reproducibility → how to run it again

**Benchmark results format** (ASCII box table):
```
┌──────────────┬────────────┬──────────┐
│ Strategy     │ qps        │ Speedup  │
├──────────────┼────────────┼──────────┤
│ binary search│ 19.1M      │ 269.5x   │
│ brute force  │ 70.9K      │ 1.0x     │
└──────────────┴────────────┴──────────┘
```

**Headline numbers to remember:**
- Python 1229x (binary search, max_c=50000)
- Rust 316x (binary search, max_c=50000, full-circle)
- CUDA 550x (nvcc -O3, host code, max_c=50000)
- SIMD 4-6x (f32x8 wide)
- KD-tree 3.6x (release build)
- Float drift: 0.00e+00 (zero)
- Holonomy: 0.012-0.213 rad (bounded)

---

## 9. Context Window Management

**The 66% reduction** (15.4KB → 5.2KB) was the single highest-impact decision of the night shift. More thinking budget = better tile quality, better experiments, fewer errors.

**Pattern:**
- MEMORY.md → curated essentials only (identity, blockers, key numbers)
- references/ → detailed docs, loaded on-demand via `read()`
- TOOLS.md → agent priority and one-liners
- HEARTBEAT.md → task queue, nothing else
- Daily notes → `memory/YYYY-MM-DD.md`, rotate old ones

**Anti-pattern:** Loading reference files into the summary/context. They should stay in references/ and be read only when needed.

---

## 10. Autonomous Operation Protocol

**What "go all night" actually means:**
1. Check forge-watch.json first — stale=true → start immediately.
2. Work in 30-min cycles: produce tiles, commit, push.
3. Don't ask permission for internal actions (file edits, git pushes, tile submissions).
4. DO ask for external actions (emails, tweets, API calls outside PLATO).
5. If tools fail, write directly. Kimi/Claude are conveniences, not dependencies.
6. GC at the start of each shift. /tmp under 200MB.
7. Distill lessons into `memory/lessons-learned.md` when you discover something new.
8. Update HEARTBEAT.md as tasks complete — it's the task queue, not a wishlist.

---

## Open Questions for Future Shifts

1. **Angular KD-tree** — can we beat 3.6x by exploiting the circular topology?
2. **GPU access** — WSL2 has CUDA toolkit but no runtime GPU. When will passthrough work?
3. **FLUX VM tests** — the bytecode VM has 0 tests. Needs at least basic ones.
4. **Constraint-theory Python v0.3.0** — v0.2.0 exists, needs bump with new features.
5. **PLATO room coverage** — 581 rooms, ~400 with <5 tiles. Deepening strategy needed.
6. **Matrix send** — still broken. Needs Oracle1 gateway restart.

---

*Last updated: 2026-04-26 13:20 AKDT*
