# Coding Agent Detail

## Architecture
```
Forgemaster (deepseek-v4-flash — cheap orchestrator)
  ├── OpenCode (z.ai GLM — paid plan, primary coding agent)
  ├── Droid Factory (z.ai GLM Anthropic — paid plan, missions)
  ├── Kimi CLI (kimi — paid plan, focused modules)
  └── [Backup] DeepSeek/DeepInfra via Aider wrappers
```

---

## 1. OpenCode (opencode) — z.ai GLM Coding Plan (PRIMARY)
- **Binary**: `/home/phoenix/.nvm/versions/node/v22.22.2/bin/opencode`
- **Config**: `~/.config/opencode/opencode.json` — has z.ai API key
- **Model**: `zai-coding-plan/glm-4.6` (default) or `zai-coding-plan/glm-4.5-air` (small)
- **Key**: `[ZAI_KEY]`
- **Endpoint**: `https://api.z.ai/api/coding/paas/v4` (OpenAI compatible)
- **Mode**: `opencode run "prompt" --cwd /path` (interactive TUI) or ACP server
- **ACP**: `opencode acp` starts ACP server for sessions_spawn `runtime: "acp"`
- **Best for**: Complex coding, refactoring, multi-file projects
- **Cost**: Paid (z.ai GLM coding plan — already paid for)
- **Provider Config**: `zai-coding-plan` with baseUrl + apiKey in opencode.json

### Usage
```bash
# Run a coding task
opencode run "Refactor the physics module to use Chen-Millero sound speed" --cwd /tmp/sv

# ACP mode (for OpenClaw sessions_spawn)
opencode acp --port 8080
```

---

## 2. Droid Factory (droid) — z.ai GLM via Anthropic API (PRIMARY)
- **Binary**: `/home/phoenix/.local/bin/droid`
- **Config**: `~/.factory/settings.json` — has z.ai Anthropic-compatible endpoint
- **Model**: Custom GLM-4.7 via z.ai Anthropic endpoint
- **Key**: `[ZAI_KEY]`
- **Endpoint**: `https://api.z.ai/api/anthropic` (Anthropic compatible)
- **Mode**: `droid exec "prompt" --auto high --skip-permissions-unsafe --cwd /path`
- **Also**: `--mission` mode for multi-agent orchestration
- **Best for**: Autonomous coding, multi-agent missions, code review
- **Cost**: Paid (z.ai GLM coding plan — already paid for)
- **Caution**: Default model is `claude-opus-4-7` — must use `--model glm-4.7` or set custom

### Usage
```bash
# Execute a coding task
droid exec "Implement Francois-Garrison absorption in physics.py" \
  --model glm-4.7 \
  --auto high \
  --skip-permissions-unsafe \
  --cwd /tmp/sv

# Multi-agent mission mode
droid exec "Build and test a CUDA kernel for sensor fusion" \
  --mission \
  --model glm-4.7 \
  --worker-model glm-4.7 \
  --auto high \
  --skip-permissions-unsafe \
  --cwd /tmp/marine-gpu-edge
```

---

## 3. Kimi CLI (kimi) — Kimi Coding Plan (PRIMARY)
- **Binary**: `/home/phoenix/.local/bin/kimi` v1.36.0
- **Config**: `~/.kimi/kimi.json`
- **Mode**: `kimi -p "prompt" --quiet -y --work-dir /path` (non-interactive)
- **Also**: `--print` (verbose), `--thinking` (extended reasoning)
- **Best for**: Production-quality code with type hints, docstrings, proper architecture
- **Proven**: Built 428-line GpuTrainer (Python), 316-line TileAPI (Rust, 10 tests)
- **Caution**: OOM-prone on <13GB free. Use `--quiet` mode. Sweet spot ~100 words.
- **Cost**: Paid (kimi coding plan — already paid for)

### Usage
```bash
kimi -p "Add a ThermoclineModel class to physics.py" --quiet -y --work-dir /tmp/sv
```

---

## 4. Claude Code (claude) — Premium, limited credits
- **Binary**: `/home/phoenix/.local/bin/claude` v2.1.86
- **Key**: Anthropic (session-based, limited budget)
- **Mode**: `--print --permission-mode bypassPermissions` (no PTY)
- **Best for**: Complex architecture, nuanced code, long-context reasoning
- **Cost**: $$$ — reserve for architecture only when z.ai not suitable

---

## 5. DeepSeek via Aider — Backup (pay-per-token)
- **Binary**: `/home/phoenix/.local/bin/aider` v0.86.2
- **Config**: `~/.aider.deepseek.yml`
- **Mode**: `--no-auto-commits --message "prompt"` non-interactive
- **Aider wrappers**: `deepseek-code` (v4-chat, fast) and `deepseek-reason` (v4-pro, deep reasoning)
- **Best for**: When z.ai/kimi unavailable, or cheap fast tasks
- **Cost**: Pay-per-token (DeepSeek API key)
- **Caution**: v4-pro requests can timeout — use background execution

### Agent Wrappers (in PATH)
```bash
deepseek-code "prompt" --file file.py --work-dir /path    # Fast: v4-chat
deepseek-reason "prompt" --file file.py --work-dir /path   # Deep: v4-pro
```

---

## 6. Seed Models via Aider — Backup (DeepInfra)
- **Key**: `~/.openclaw/workspace/.credentials/deepinfra-api-key.txt`
- **Models**: `ByteDance/Seed-2.0-code`, `ByteDance/Seed-2.0-pro`, `ByteDance/Seed-2.0-mini`
- **Endpoint**: `https://api.deepinfra.com/v1/openai`
- **Wrappers**: `seed-code`, `seed-pro`, `seed-mini` (all use Aider)

---

## 7. Pi (pi) — Fast, multi-provider (partially available)
- **Binary**: `/usr/lib/node_modules/openclaw/node_modules/.bin/pi`
- **Keys**:
  - GROQ_API_KEY (env) — ⚠️ NOT AVAILABLE
  - SILICONFLOW_API_KEY=sk-zrjkwnqutxuhjxrorvhmczyscfdoxkkqnnlghwpywoajecsj
- **Mode**: `-p "prompt"` non-interactive, `--provider groq --model llama-3.3-70b-versatile`
- **Also**: DeepInfra, ZAI, SiliconFlow (base URL https://api.siliconflow.com/v1)
- **Best for**: Fast code gen, boilerplate, tests, parallel batch (when SiliconFlow works)

---

## 8. Codex CLI (codex) — OpenAI
- **Binary**: `/usr/bin/codex` v0.120.0
- **Key**: ⚠️ Needs OPENAI_API_KEY (not set)
- **Mode**: `codex exec "prompt"` with PTY
- **Status**: Unavailable

---

## Orchestration Pattern

### Primary Path (preferred, in order)
1. **OpenCode** — most capable, best for complex multi-file tasks
2. **Droid** — best for autonomous missions, code review, multi-agent
3. **Kimi** — best for focused single-file modules, type-safe code
4. **DeepSeek/DeepInfra** — backup when paid plans unavailable

### Delegation Flow
```bash
# ForgeMaster receives task → decides which agent
opencode run "Task description" --cwd /path &
# or
droid exec "Task description" --model glm-4.7 --auto high --cwd /path &
# or
kimi -p "Task description" --quiet -y --work-dir /path &
wait  # collect results
```

### When to Use What
| Task Type | Agent | Why |
|---|---|---|
| Multi-file refactor | OpenCode | Best context management |
| Autonomous feature dev | Droid (mission mode) | Multi-agent, self-correcting |
| Focused code module | Kimi | Fast, type-safe, cheap compute |
| Architecture/planning | Claude Code | Long context, nuanced reasoning |
| Quick one-liner fix | Forgemaster direct | No round-trip needed |
