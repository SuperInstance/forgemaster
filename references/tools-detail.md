# Coding Agent Details

## 1. Claude Code (claude) — Premium, limited
- **Binary**: `/home/phoenix/.local/bin/claude` v2.1.86
- **Key**: Anthropic (session-based, limited budget)
- **Mode**: `--print --permission-mode bypassPermissions` (no PTY)
- **Best for**: Complex architecture, nuanced code, long-context reasoning
- **Cost**: $$$ — reserve for architecture only

## 2. Pi (pi) — Fast, multi-provider
- **Binary**: `/usr/lib/node_modules/openclaw/node_modules/.bin/pi`
- **Keys**:
  - GROQ_API_KEY (env) — ⚠️ NOT AVAILABLE
  - SILICONFLOW_API_KEY=sk-zrjkwnqutxuhjxrorvhmczyscfdoxkkqnnlghwpywoajecsj
- **Mode**: `-p "prompt"` non-interactive, `--provider groq --model llama-3.3-70b-versatile`
- **Also**: DeepInfra, ZAI, SiliconFlow (base URL https://api.siliconflow.com/v1)
- **SiliconFlow models**: stepfun-ai/Step-3.5-Flash, Qwen/Qwen3-VL-235B-A22B-Thinking, moonshotai/Kimi-K2.5, deepseek-ai/deepseek-chat, deepseek-ai/deepseek-reasoner
- **PTY**: Required for interactive
- **Best for**: Fast code gen, boilerplate, tests, parallel batch

## 3. Aider — Git-native, multi-model
- **Binary**: `/home/phoenix/.local/bin/aider` v0.86.2
- **Mode**: `--no-auto-commits --message "prompt"` non-interactive
- **Best for**: In-repo editing, refactoring, multi-file changes
- **Cost**: Free (Groq) — but Groq unavailable

## 4. Kimi CLI (kimi) — Moonshot AI
- **Binary**: `/home/phoenix/.local/bin/kimi` v1.36.0
- **Mode**: `kimi -p "prompt" --quiet --work-dir /path` (non-interactive)
- **Also**: `--print` (verbose), `-y` (auto-approve), `--thinking` (extended reasoning)
- **Best for**: Production-quality code with type hints, docstrings, proper architecture
- **Proven**: Built 428-line GpuTrainer (Python), 316-line TileAPI (Rust, 10 tests)
- **Caution**: OOM-prone on <13GB free. Use `--quiet` mode. Sweet spot ~100 words.
- **Cost**: Free

## 5. Codex CLI (codex) — OpenAI
- **Binary**: `/usr/bin/codex` v0.120.0
- **Key**: ⚠️ Needs OPENAI_API_KEY (not set)
- **Mode**: `codex exec "prompt"` with PTY
- **Status**: Unavailable

## Parallel Pattern
```bash
# Write in parallel, compile serial
pi -p "task 1" --provider groq --model llama-3.3-70b-versatile &
pi -p "task 2" --provider groq --model llama-3.3-70b-versatile &
wait
# Then serialize builds (max 2 concurrent cargo operations)
cargo check --manifest-path /tmp/repo1/Cargo.toml
```

## GPU Git-Agent Architecture (Notes)
- DeepInfra GPU Models → code generation
- Groq LPU → fast review/test
- Jetson CUDA (FLUX bytecode) → agent logic execution
- Constraint Theory → drift-free agent state management
