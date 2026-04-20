# MEMORY.md — Forgemaster ⚒️ Long-Term Memory

## Who I Am
- **Forgemaster** ⚒️ — Casey's constraint-theory specialist in the Cocapn fleet
- Running on eileen (WSL2) via OpenClaw, GLM-5.1
- My mission: make constraint theory undeniable through side-by-side proof repos

## Casey (Fleet Commander)
- Name: Casey Digennaro
- Timezone: America/Anchorage (AKDT)
- Runs SuperInstance org — 1,400+ repos, 9 AI agents
- Values shipping, direct communication, no fluff
- Wants the constraint-theory "HN moment" — a download that makes people go wow

## Fleet Structure
- **Oracle1 🔮** — Lighthouse Keeper, team leader, Oracle Cloud ARM
- **JetsonClaw1 ⚡** — Edge specialist, NVIDIA Jetson, C/CUDA
- **Babel 🌐** — Linguistics, multilingual FLUX
- **Super Z** — Quartermaster, fleet hygiene
- **Mechanic** — Fleet infrastructure
- I2I protocol: git-based messaging, `[I2I:TYPE] scope — summary` format
- Message-in-a-bottle: `for-fleet/`, `from-fleet/` folders
- Fence Board: Tom Sawyer Protocol for claiming challenges

## Constraint Theory Stack
- `constraint-theory-core` — Rust, crates.io, v1.0.1
- `constraint-theory-python` — PyO3 bindings
- `constraint-theory-web` — WASM, Cloudflare Pages demos
- Core: snap vectors to Pythagorean coordinates, quantize, verify holonomy
- Key insight: trade continuous precision for discrete exactness — zero drift, every machine

## JC1 (JetsonClaw1) — Deep Audit 2026-04-18
- 200 repos in Lucineer org. 524 tests across 18 flux-rust crates.
- **Code quality is high** — NaN guards, zero-external-dep pattern, consistent style
- **Key repos:** cudaclaw (44k lines Rust+CUDA), holodeck-c (C MUD, production), mycorrhizal-relay (elegant C routing), flux-runtime-c (85-opcode C VM)
- **Five Pillars Architecture** (ct-lab): Tiling, Assertions, Episodes, Anchors, Runtime — same as plato-kernel
- **Saltwater Principle:** distribute knowledge across repos, not centralize. Every piece in 3+ repos.
- **flux-instinct is a stub** (11 lines, 0 tests) — offered plato-instinct as replacement
- **Tile format fragmentation** still active — holodeck-c C structs, fleet-sim Python dicts, plato_core Python, plato-tile-spec Rust
- **JC1-JETSON-LESSONS.md** is the best documentation in the fleet. "Code is water, experience is the well."
- Full audit log: `memory/jc1-lucineer-audit-2026-04-18.md`
- Audit bottle delivered to JC1 vessel with 5 synergy offers

## Skill Extraction Candidates (from JC1 audit)
- `fleet-crate-standard` — Rust crate conventions (naming, structure, tests, deps)
- `fleet-bottle-protocol` — I2I bottle writing and delivery workflow
- `fleet-room-convention` — PLATO room repo structure and deployment
- `fleet-audit-checklist` — Repo audit framework (quality signals, synergy patterns)
- `fleet-trust-patterns` — Trust scoring patterns across fleet crates

## VM-Estate Architecture (2026-04-19)
- Casey's vision: each machine is a plot of land, intelligence grows on that land
- Add more plots = more intelligence (O(N²) via cross-pollination)
- Asymmetric training: different nodes train on different data → different adapters → shared cognition
- FM ↔ JC1 API: HTTP adapter exchange for flow-state-distributed thinking
- Self-distribution protocol: zero-config bootstrap for new Jetsons
- Day/night cycle: inference by day, QLoRA by night
- Adapter Market: Oracle1 validates (≥0.94), distributes fleet-wide
- Scaling: 1 node (50K steps/night) → 100 nodes (5M steps/night)
- Repo: SuperInstance/vm-estate
- JC1 onboarding bottle delivered: full forge stack docs + Jetson setup guide

## Forge Simulation Results
- distilgpt2 (82M params) on CPU — proven pipeline
- Run 1: 50 steps, loss 10.2→2.4 (76% reduction)
- Run 2: 200 steps, loss 10.4→0.93 (91% reduction, still converging)
- Speed: 0.6-1.7 steps/sec on CPU, projected 8-12/s on RTX 4050
- 1000-step run attempted but pip OOM on tokenization
- BLOCKED: CUDA torch install (pip OOM on 530MB download extraction)

## Neural Plato Stack (Complete)
- 68 crates, ~1,390+ tests across SuperInstance org
- Full pipeline: tracer → neural-kernel → casino → forge-daemon → trainer → adapter-store → inference-runtime → live-data → ranker
- "A model IS an OS. The forward pass IS the scheduler. Context window IS RAM. Special tokens ARE syscalls."
- Base model (7B Q4 = 3.5GB) + kernel adapter (100MB) + room adapters (50MB each)
- plato-tile-spec v2.0.0 tagged

## Constraint Theory Performance (from benchmarks)
- **CT snap is 4% faster than float** — 9,875 vs 9,433 Mvec/s on RTX 4050
- **93.8% perfectly idempotent** — worst-case drift 0.000112 (bounded, never growing)
- **Float drift: 29,666 after 1B ops** — CT snap bounded at 0.36
- **f32 destroys 45% of Pythagorean triples** above side=91 (77% by side=5000)
- **2,780 distinct Pythagorean directions** in 2D with sides < 1000 (11.4 bits)
- **CT snap does NOT commute with rotation** — snap AFTER rotation (max div 95.6)
- **Noise filtering**: CT + DCS improves by +1.5% over noisy DCS alone
- **Axis-aligned snap(1,0) and snap(0,1) = zero error** — perfect fixed points

## Lessons Learned

- **8GB swap added** — 3-4 parallel cargo builds now safe
- **GPU confirmed**: RTX 4050, 6141 MiB VRAM, Driver 591.74, CUDA 13.1 (Windows), nvcc 11.5 (WSL2)
- Max builds raised from 2 to 3-4
- **constraint-theory-core API differs from docs** — snap() is ([f32;2], f32), new(density: usize) not new(tolerance: f64)
- **Pi on Groq is free and fast** — use for batch code gen, save Claude for architecture
- **Pi sometimes fails** ("Failed to call a function") — retry or switch models
- **Casey's doctrine**: vessel = ship, hull = hardware limit, rigging = skills, crew = git-agents, MUD = shared abstraction
- **Captain's log after every watch** — continuity for the next session
- **A/B test crew** — redundant agents on critical tasks, compare outputs
- **Load light, unload clean** — only boot what you need, release when done
- **Sweep the shop floor** — `rm -rf /tmp/<crate>` immediately after every push. No exceptions. Debrief: memory/debrief-tmp-cleanup-2026-04-19.md
- **Check free -h before big installs** — need 3GB for <500MB, 5GB for >500MB. OpenClaw eats 1.8GB constant.
- **Kill zombie pip processes** — OOM-killed installs leave processes alive. `pgrep -f 'pip3 install' | xargs kill -9` before retry.
- **pip cache is not free** — grows without bound. Clear `~/.cache/pip/` when >500MB.
- **CUDA torch on eileen**: cu126 wheel installs (830MB DL), but needs libcudnn9-cuda-12 (482MB apt). Last blocker.
- **Claude Code credits reset** — use sparingly for highest-value connective work
- **crates.io rate limit** — 5 new crates per ~hour. Use systemd timer for batch retries with 2s delay.
- **Sonnet for batch, Opus for architecture** — Sonnet handles metadata/publish, Opus for design
- **Inline modules > Cargo workspace** — cargo 1.75 can't resolve complex workspace deps.
- **Knowledge-transfer docs are temporary** — distill into MEMORY.md, then delete. Don't accumulate.
- **Ticker logs (.keeper/ticker/) grow unbounded** — 2.2MB of raw gauge data. Need retention policy.
- **Inline modules > Cargo workspace** — cargo 1.75 can't resolve complex workspace deps. Copy APIs as inline modules.
- **&self vs &mut self** — flywheel components that mutate need interior mutability or separate mutable methods. DeployPolicy.classify() is read-only; use it directly instead of DeployLedger.submit().
- **Anchor search direction** — check both `anchor.contains(query)` AND `query.contains(anchor)` for natural language queries
- **ct-lab Tile Taxonomy is the best fleet research** — 8 categories of knowledge, especially NegativeSpace (worth 10x positive tiles)
- **Hypothesis gating: whole-word matching** — "overall" must not trigger "all" absolute gate. Space-surround the word.
- **Web research validates our approach** — AgentGit, RepuNet, Meta-Chunking all independently discovered patterns we already implement

## Night Build Session 2026-04-18→19
- **15 new crates built**, ~110 new tests, fleet at ~1,150+ tests
- **plato-kernel: 48→83 tests** — Claude Code Opus wired deadband+scoring+temporal
- **Oracle1 deployed 12 zeroclaws** — ~8,640 tiles overnight, PLATO server port 8847
- **Oracle1 exported 4 ensigns** — compressed knowledge from room training
- **JC1 last visible: 2026-04-17** — JIT v2 ghost-tiles attention weighting
- **Fleet tile count: ~11,000+** — target exceeded
- **5 crates on crates.io**: constraint-theory-core, plato-deadband, plato-tile-validate, plato-tile-scorer, plato-tile-dedup
- **15 more queued for crates.io** — rate-limited, scheduled retry
- **72+ PLATO crates**, ~1,680+ tests, 7 architectural layers
- **CCC (Cocapn-Claw)** — Kimi K2.5, third active fleet member, writing cocapn public READMEs
- **New crates**: plato-cli, plato-deadband, plato-room-nav, plato-tile-store, plato-room-runtime, plato-tile-encoder, plato-tile-dedup, plato-prompt-builder, plato-query-parser, plato-tile-import, plato-config, plato-tile-client
- **Fleet graph: 24 nodes, 24 edges**
- **systemd timer** used for Claude Code scheduling (openclaw cron blocked by pairing issue)
- **Bottles sent**: Oracle1 (deadband response + night shift), JC1 (cross-pollination + night shift)
