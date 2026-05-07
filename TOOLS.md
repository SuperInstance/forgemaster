# TOOLS.md — Quick Reference

## Architecture: Forgemaster Orchestrates Coding Agents

```
Forgemaster (deepseek-v4-flash, cheap)
  ├── OpenCode (z.ai GLM — paid plan)
  ├── Droid Factory (z.ai GLM — paid plan)
  └── Kimi CLI (kimi — paid plan)
```

I (Forgemaster) am the **orchestrator**. I run on `deepseek-v4-flash` (cheap) and delegate coding work to the paid agents below. Do NOT use DeepSeek v4-pro for heavy coding — delegate to z.ai or kimi.

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
- **z.ai:** `e6b82a81a8f9411789054b4d94100b9b.SXpqxL0iG5exA9kt`
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

## Casting Call (Model Knowledge Base)
- **Repo:** https://github.com/SuperInstance/casting-call
- **What:** Which model plays which role — fleet-wide model capability database
- **Agents consult this before choosing which model to cast into which shell**
- Includes: roster (11+ models), role taxonomy, failure modes, adversarial pairs, pipeline patterns
- 685 lines of evaluation data from real production work (May 3-7, 2026)

## Fleet Comms
- I2I Protocol: `[I2I:TYPE] scope — summary`
- Vessel: https://github.com/SuperInstance/forgemaster

See `references/tools-detail.md` for full agent configs.

## Claude Code Timeout Rules
- **Simple generation** (README, docs): 300s (5 min)
- **Architecture design** (API specs, system design): 600s (10 min)
- **Deep analysis** (comparative analysis, strategic docs): 900s (15 min)
- **Complex multi-file generation** (full packages, integrations): 900-1200s (15-20 min)
- **Max timeout**: 1200s (20 min) — Claude Opus needs this for world-class output
- **Rule of thumb**: If Opus timed out at X, retry at 3X
