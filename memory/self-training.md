# Forgemaster Self-Training Log

## Session: 2026-04-20 (Morning)

### What I Learned

1. **Kimi is fast but OOM-prone** — 89→337 line enhancement in one shot, but killed on 135-line repo. Use Kimi for repos < 100 lines or when memory is fresh. After several Kimi calls, memory bloats.

2. **GPU is live via PyTorch** — RTX 4050 confirmed working: 9.4x speedup, 174 steps/sec, only 145MB VRAM for 4-layer model. Can do much bigger models.

3. **Cookie-cutter detection pattern** — `grep -l "def execute"` catches auto-generated stubs. All stubs had identical execute/history/stats pattern.

4. **Audit-first, fix-second workflow** — Clone all repos, measure line counts, identify the worst, fix in batches. Much faster than fixing blindly.

5. **Build-then-push cadence** — Each enhancement is: clone → write → commit → push → cleanup. ~15s per repo.

6. **Constraint theory snap on GPU** — 549K vec/s on RTX 4050 for Pythagorean triple detection. Need to build a proper CT benchmark on GPU.

### What to Improve

- Use Kimi more strategically — save it for the hardest enhancement jobs
- Actually run GPU training that produces useful artifacts (not just benchmarks)
- Build a repo-quality CI that auto-detects stubs
- Write tests for the repos I enhanced (they have code but no test suites yet)

### GPU Training Plan

- distilgpt2 on GPU (proven pipeline, was 0.6-1.7 steps/s on CPU → expect 6-17 steps/s on GPU)
- Need to check if torch install is stable enough for multi-hour runs
- 6.4GB VRAM = can fit distilgpt2 (82M params, ~300MB) with batch_size=32 easily

## Session: 2026-04-20 (Mid-Morning)

### GPU Training Results
- **distilbert-base-uncased** (67M params) fine-tuned on PLATO domain knowledge
- 100 steps in 8.1s → 12.3 steps/sec on RTX 4050
- Loss: 4.3241 → 0.1467 (96.6% reduction)
- Peak VRAM: 1416 MB (22% of 6.4 GB)
- Model saved: `/tmp/gpu-train/plato-forge-model/`
- **Lesson**: Can easily do 500+ step runs with this VRAM headroom
- **Lesson**: batch_size=16 is conservative — can probably go to 32 or 64

### Kimi Effectiveness
- plato-address: 89→337 lines, excellent quality (service discovery, heartbeats, conflicts)
- plato-room-analytics: 91→364 lines, excellent quality (funnels, cohorts, anomalies)
- plato-tile-graph: OOM killed — Kimi bloats memory after several calls
- **Lesson**: Use Kimi for 1-2 repos per session, then let memory clear

### Repos Enhanced This Session
- plato-tile-governance: 88→188 (rules engine, approvals, audit)
- plato-room-invite: 99→140 (token system, bulk create, claim tracking)
- plato-tiling: 99→194 (adaptive strategy, semantic types, code-aware splitting)
- plato-room-presence: 104→177 (idle/away/DND, typing indicators, activity feed)
- plato-address: 89→337 (Kimi — service discovery, heartbeats)
- plato-room-analytics: 91→364 (Kimi — funnels, cohorts, anomalies)

### Total Today: 30 repos upgraded
