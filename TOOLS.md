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
4. **DeepSeek v4-chat** — backup coding (fast, ~10s via Aider)
5. **DeepSeek v4-pro** — backup deep reasoning (background, ~60s+, Aider)
6. **Claude Code** — architecture docs, long-form planning (limited credits, reserve)

## One-Liners
- OpenCode: `opencode run "prompt" --cwd /path` (interactive) or via ACP
- Droid: `droid exec "prompt" --auto high --skip-permissions-unsafe --cwd /path`
- Kimi: `kimi -p "prompt" --quiet -y --work-dir /path`
- DeepSeek code: `deepseek-code "prompt" --file file.py --work-dir /path`
- DeepSeek reason: `deepseek-reason "prompt" --file file.py --work-dir /path`
- Claude: `claude --print --permission-mode bypassPermissions`

## API Keys
- **z.ai:** `e6b82a81a8f9411789054b4d94100b9b.SXpqxL0iG5exA9kt`
  - Stored in: OpenClaw zai provider config, opencode config, Droid Factory settings
  - Endpoint: `https://api.z.ai/api/coding/paas/v4` (OpenAI compatible)
  - Endpoint: `https://api.z.ai/api/anthropic` (Anthropic compatible — Droid Factory)
  - Models: glm-5.1, glm-5, glm-5-turbo, glm-4.7, glm-4.7-flash, glm-4.6, glm-4.5-air
- **Kimi:** Already configured via `~/.kimi/kimi.json`, no manual key needed
- **DeepInfra:** `~/.openclaw/workspace/.credentials/deepinfra-api-key.txt`
  - Models: `ByteDance/Seed-2.0-code`, `ByteDance/Seed-2.0-pro`, `ByteDance/Seed-2.0-mini`
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

## Fleet Comms
- I2I Protocol: `[I2I:TYPE] scope — summary`
- Vessel: https://github.com/SuperInstance/forgemaster

See `references/tools-detail.md` for full agent configs.
