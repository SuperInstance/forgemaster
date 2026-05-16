# TOOLS.md — Quick Reference

## Architecture: Forgemaster Orchestrates Coding Agents

```
Forgemaster (GLM-5.1 via z.ai)
  ├── Claude Code (claude — best for boilerplate, architecture docs)
  ├── OpenCode (z.ai GLM — paid plan)
  ├── Droid Factory (z.ai GLM — paid plan)
  └── Kimi CLI (kimi — paid plan)
```

I (Forgemaster) am the **orchestrator**. I run on `GLM-5.1` and delegate coding work to agents below.

**Claude Code**: Good for CLI boilerplate (470-line CLI in one pass). Times out on novel math. Use `--print --permission-mode bypassPermissions`.

## Agent Priority (Delegation Order)
1. **OpenCode** (`opencode`) — z.ai GLM models (paid plan), best for complex coding tasks
2. **Droid Factory** (`droid`) — z.ai GLM models (paid plan), good for autonomous coding missions
3. **Kimi CLI** (`kimi`) — kimi coding plan (paid plan), good for focused code modules
4. **Seed-2.0-mini** (DeepInfra) — PRIMARY FAILBACK. Cheap, fast, surprisingly good at code. Use when z.ai/kimi/claude hit limits.
5. **Seed-2.0-code** (DeepInfra) — Good for focused code generation tasks
6. **DeepSeek v4-chat** — backup coding (fast, ~10s via Aider)
7. **DeepSeek v4-pro** — backup deep reasoning (background, ~60s+, Aider)
8. **Claude Code** — architecture docs, long-form planning (limited credits, reserve)

## One-Liners
- OpenCode: `opencode run "prompt" --cwd /path` (interactive) or via ACP
- Droid: `droid exec "prompt" --auto high --skip-permissions-unsafe --cwd /path`
- Kimi: `kimi -p "prompt" --quiet -y --work-dir /path`
- Seed-2.0-mini: `curl -s https://api.deepinfra.com/v1/openai/chat/completions -H "Authorization: Bearer $DEEPINFRA_KEY" -d '{"model":"ByteDance/Seed-2.0-mini",...}'` — PRIMARY FAILBACK
- Seed-2.0-code: Same endpoint, model `ByteDance/Seed-2.0-code`
- DeepSeek code: `deepseek-code "prompt" --file file.py --work-dir /path`
- DeepSeek reason: `deepseek-reason "prompt" --file file.py --work-dir /path`
- Claude: `claude --print --permission-mode bypassPermissions`

## Seed-2.0-mini Failback Protocol
When z.ai (GLM-5.1) or other providers hit rate limits:
1. Switch to Seed-2.0-mini via DeepInfra API
2. Use for: code generation, file writing, research, documentation, creative content
3. Model ID: `ByteDance/Seed-2.0-mini` (general) or `ByteDance/Seed-2.0-code` (code-focused)
4. Endpoint: `https://api.deepinfra.com/v1/openai/chat/completions`
5. Key: `~/.openclaw/workspace/.credentials/deepinfra-api-key.txt`
6. Cost: Very cheap (~$0.01-0.05/query)
7. Quality: Surprisingly good — builds working code, docs, configs
8. Use in subagents: Pass DEEPINFRA_KEY env var to spawned agents

## API Keys
- **z.ai:** `[ZAI_KEY]`
  - Stored in: OpenClaw zai provider config, opencode config, Droid Factory settings
  - Endpoint: `https://api.z.ai/api/coding/paas/v4` (OpenAI compatible)
  - Endpoint: `https://api.z.ai/api/anthropic` (Anthropic compatible — Droid Factory)
  - Models: glm-5.1, glm-5, glm-5-turbo, glm-4.7, glm-4.7-flash, glm-4.6, glm-4.5-air
- **Kimi:** Already configured via `~/.kimi/kimi.json`, no manual key needed
- **DeepInfra:** `~/.openclaw/workspace/.credentials/deepinfra-api-key.txt`
  - Models: `ByteDance/Seed-2.0-code`, `ByteDance/Seed-2.0-pro`, `ByteDance/Seed-2.0-mini`, `NousResearch/Hermes-3-Llama-3.1-405B`, `NousResearch/Hermes-3-Llama-3.1-70B`, `Qwen/Qwen3.6-35B-A3B`, `Qwen/Qwen3.5-397B-A17B`, `Qwen/Qwen3-235B-A22B-Instruct-2507`
  - Endpoint: `https://api.deepinfra.com/v1/openai`
- **DeepSeek:** `~/.openclaw/workspace/.credentials/deepseek-api-key.txt`
  - Models: `deepseek-chat` (fast), `deepseek-reasoner` (slow)
  - Endpoint: `https://api.deepseek.com/v1`

## Agent Wrappers (Backup/Secondary — use only when z.ai/kimi unavailable)
All use Aider with isolated temp dirs (no repo-map overhead).
Files are copied to temp, edited by agent, then copied back.
- `seed-code` — Seed-2.0-code, coding specialist (DeepInfra)
- `seed-pro` — Seed-2.0-pro, heavy reasoning (DeepInfra)
- `seed-mini` — Seed-2.0-mini, cheap and fast (DeepInfra)
- `deepseek-code` — DeepSeek v4-chat, fast coding
- `deepseek-reason` — DeepSeek v4-pro/reasoner, deep reasoning
- Aider config: `~/.aider.deepseek.yml`

## OOM Rules
- Max 2 concurrent `cargo check/build`
- Serialize Rust builds, clean target/ between them
- Kimi: ~100 words max, `--quiet` mode
- DeepSeek v4-pro: use `deepseek-reason` (background), NOT curl (timeout kills)

## Key Constraints
- **rustc 1.75.0** — pin uuid≤1.4.1, no edition2024
- **No GROQ_API_KEY** — Groq agents unavailable
- **No OPENAI_API_KEY** — Codex unavailable

## PLATO Training Rooms (SuperInstance/plato-training)

The main build. Micro models for ensigns, deployable to any hardware at the click of a button.

```
plato_training/
  ├── types.py          — TrainingTile, TileLifecycle, LamportClock
  ├── adapters/lora.py  — LoRALayer with save/load
  ├── rooms/            — LoRAFactory room
  ├── store.py          — LocalTileStore (content-addressed)
  ├── throttle.py       — Fleet-aware training throttle
  ├── pytorch_room.py   — PyTorchRoom (LoRA + throttle)
  ├── tensorflow_room.py — TensorFlowRoom (Keras + throttle)
  ├── spline.py         — SplineLinear (Eisenstein lattice weights, NOVEL)
  ├── micro_models.py   — 8 room tasks + training pipeline
  ├── hardware.py       — 8 hardware targets + deploy pipeline
  ├── cli.py            — plato-train CLI (470 lines)
  └── tests/            — 69 tests passing
```

**One function:** `deploy_micro("drift-detect", target="npu")`
**Fleet deploy:** `deploy_fleet()` — all 48 task×target combos
**Fleet results:** drift-detect 100% on 5/6 targets, anomaly-flag 93% on NPU

### Key Results
- SplineLinear: 20× compression on drift-detect at SAME accuracy
- NPU quantization: maintains 100% on drift-detect and intent-detect
- Sub-millisecond inference across all CPU targets
- LoRA struggles on synthetic data (expected — needs real data)

### Architecture (3 layers)
1. Room Protocol: tiles, lifecycle, throttle, Lamport clocks
2. Engine Rooms: PyTorch/TF + micro models
3. Tensor-Spline: Eisenstein lattice weight parameterization

### Variant Selection (auto)
- cpu-tiny → spline (compression required)
- npu → dense + INT8 quantize
- gpu → lora
- default → dense

### Priority: Build the system, not posts
- Scale SplineLinear for high-dim tasks
- Real data pipelines for micro models
- Wire micro models into PLATO rooms
- GPT-2 / small transformer training runs

### Modular Architecture (4 independent repos)
| Repo | What | Tests |
|------|------|-------|
| SuperInstance/plato-types | Tile lifecycle, Lamport clocks | 10 |
| SuperInstance/tensor-spline | SplineLinear, LowRank, Hierarchical | 57 |
| SuperInstance/plato-data | CSV/JSONL/PLATO/fleet data loading | 10 |
| SuperInstance/plato-training | Micro models, hardware deploy, rooms | 116 |

Each independently installable. plato-training orchestrates.
- **Repo:** https://github.com/SuperInstance/casting-call
- **What:** Which model plays which role — fleet-wide model capability database
- **Agents consult this before choosing which model to cast into which shell**
- Includes: roster (11+ models), role taxonomy, failure modes, adversarial pairs, pipeline patterns
- 685 lines of evaluation data from real production work (May 3-7, 2026)

## I2I Protocol
- Instance-to-instance: no Python imports between repos, just tiles
- 5 tile schemas: model, data, compression, benchmark, deploy
- Collective inference: predict → listen → compare → gap → learn → share
- Focus scoring: confidence × delta = "how sure × how wrong"
- "The glitches ARE the research agenda. The gaps ARE the work."

## Fleet Comms
- I2I Protocol: `[I2I:TYPE] scope — summary`
- Vessel: https://github.com/SuperInstance/forgemaster

See `references/tools-detail.md` for full agent configs.

## Claude Code Timeout + Effort Rules

**Settings:** `effortLevel: high` (set in ~/.claude/settings.json)

**Model selection:**
- `claude --model opus` — for the hardest architectural/theoretical work
- `claude --model sonnet` — default for code generation, good balance
- Default (sonnet) is fine for most tasks

**Timeout protocol:**
- **Simple generation** (README, docs): `timeout 300 claude --print`
- **Architecture design** (API specs, system design): `timeout 600 claude --print`
- **Deep analysis** (comparative analysis, strategic docs): `timeout 900 claude --print`
- **Complex multi-file generation** (full packages, integrations): `timeout 1200 claude --print`
- **Highest level work** (ARCHITECTURE.md, theory synthesis): `timeout 1800 claude --model opus --print`
- **Max think** (when challenged, novel synthesis): `timeout 2400 claude --model opus --print`
- **Absolute max**: 2400s (40 min) — only for world-class output on novel problems
- **Rule of thumb**: If Opus timed out at X, retry at 3X

**Effort flags:**
- `--effort-level high` — per-invocation override for hard problems
- Settings already at `high` — Claude thinks longer before responding

**When to use Claude Code (vs GLM-5.1 subagents):**
- Architecture documents that need to synthesize MANY files
- Deep analysis requiring reading + reasoning about the whole system
- Novel theoretical synthesis that benefits from extended thinking
- When GLM-5.1 agents keep failing on the same problem

**Claude Code pattern for highest-level work:**
```bash
timeout 2400 claude --model opus --print --permission-mode bypassPermissions << 'PROMPT'
[Read these files first, then synthesize]
PROMPT
```

**Key: don't feed Claude too many files at once.** Read 5-10 max, or it OOMs.
For large synthesis, read files in the prompt via shell commands, not all at once.

## Fleet Model Routing (Updated 2026-05-15)

### z.ai (PAID PLAN — use heavily)

| Model | Best For | Stage | Notes |
|-------|----------|:-----:|-------|
| **glm-5.1** | Code generation, architecture, boilerplate, planning | 3 | Thinking model — reasoning in reasoning_content, content often empty. Pre-compute arithmetic before sending. |
| **glm-5-turbo** | Content tasks, non-reasoning generation, summaries | 3 | Non-thinking, faster. Same vocabulary wall. Pre-compute arithmetic. |
| **glm-4.7** | Lighter tasks, faster responses | 2-3 | Fallback when 5.x rate limited |
| **glm-4.7-flash** | Quick lookups, simple generation | 2 | Fastest, cheapest z.ai option |

### DeepInfra (PAY-PER-USE)

| Model | Best For | Stage | Cost |
|-------|----------|:-----:|------|
| **Seed-2.0-mini** | Domain computation, math reasoning, Stage 4 tasks | **4** | ~$0.01/query |
| **Seed-2.0-code** | Code + math combined tasks | **4** | ~$0.02/query |
| Hermes-70B | General generation, large context | 3 | Moderate |
| Qwen3-235B | Multi-step reasoning (with translation) | 3 | Moderate |
| Qwen3.6-35B | Cheap routing, fast | 2 | Cheap |

### Routing Rules

```
Code/architecture/docs → glm-5.1 (z.ai, paid plan)
Domain computation → Seed-2.0-mini (Stage 4, immune to vocabulary wall)
Reasoning about math → Seed-2.0-mini (only Stage 4 that answers correctly)
Content generation → glm-5-turbo (z.ai, paid plan)
Simple arithmetic on ANY model → fleet_translator.translate() first
```

### Key: z.ai is PAID — burn it for everything that doesn't need Stage 4
