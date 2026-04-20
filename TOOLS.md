# TOOLS.md - Forgemaster's Agent Toolkit

## Coding Agents Available

### 1. Claude Code (claude) — Premium, limited tokens
- **Binary**: `/home/phoenix/.local/bin/claude` v2.1.86
- **Key**: Anthropic (session-based, limited budget)
- **Mode**: `--print --permission-mode bypassPermissions` (no PTY needed)
- **Best for**: Complex architecture, nuanced code, long-context reasoning
- **Cost**: $$$ — use sparingly for high-value work

### 2. Pi Coding Agent (pi) — Fast, unlimited via Groq/SiliconFlow
- **Binary**: `/usr/lib/node_modules/openclaw/node_modules/.bin/pi`
- **Keys**: 
  - GROQ_API_KEY (env) — unlimited/fast
  - SILICONFLOW_API_KEY=sk-zrjkwnqutxuhjxrorvhmczyscfdoxkkqnnlghwpywoajecsj (added 2026-04-17)
- **Mode**: `-p "prompt"` for non-interactive, `--provider groq --model llama-3.3-70b-versatile`
- **Also supports**: DeepInfra (openai provider + base URL), ZAI, SiliconFlow (openai-compatible, base URL https://api.siliconflow.com/v1)
- **Valid SiliconFlow models**: stepfun-ai/Step-3.5-Flash, Qwen/Qwen3-VL-235B-A22B-Thinking, moonshotai/Kimi-K2.5, deepseek-ai/deepseek-chat, deepseek-ai/deepseek-reasoner
- **PTY**: Required for interactive mode
- **Best for**: Fast code gen, boilerplate, test writing, parallel batch work
- **Cost**: Free (Groq) / Pay-as-you-go (SiliconFlow) — scale with parallel runs

### 3. Aider — Git-native coding, multi-model
- **Binary**: `/home/phoenix/.local/bin/aider` v0.86.2
- **Key**: GROQ_API_KEY via `--model groq/llama-3.3-70b-versatile`
- **Mode**: `--no-auto-commits --message "prompt"` for non-interactive
- **Best for**: In-repo editing, refactoring, multi-file changes
- **Cost**: Free (Groq) — unlimited

### 4. Kimi CLI (kimi) — Moonshot AI, high-quality coding
- **Binary**: `/home/phoenix/.local/bin/kimi` v1.36.0
- **Mode**: `kimi -p "prompt" --quiet --work-dir /path` (non-interactive)
- **Also**: `--print` (verbose), `-y` (auto-approve), `--thinking` (extended reasoning)
- **Best for**: Production-quality code with type hints, docstrings, proper architecture
- **Proven**: Built 428-line GpuTrainer (Python), 316-line TileAPI (Rust, 10 tests)
- **Caution**: OOM-prone on <13GB free memory. Use `--quiet` mode to reduce memory. Works best with 13GB+ free.
- **Cost**: Free (Kimi account)

### 5. Codex CLI (codex) — OpenAI
- **Binary**: `/usr/bin/codex` v0.120.0
- **Key**: Needs OPENAI_API_KEY (not currently set)
- **Mode**: `codex exec "prompt"` with PTY
- **Best for**: General coding, autonomous multi-step
- **Cost**: $$ — needs key setup
- **Status**: ⚠️ No API key configured yet

## Parallel Execution Strategy

### OOM Prevention
- Max 2 agents building (`cargo check/build`) simultaneously on WSL2
- Serialize builds: write code in parallel, compile one at a time
- Clean target/ dirs between builds

## Tool Priority (Casey's Directive 2026-04-20)
1. **Kimi CLI** — quick, quality coding. First choice for implementation work.
2. **Claude Opus 4.7** — high planning, complex architecture. Use sparingly.
3. **Pi + Groq** — unlimited batch work, boilerplate, tests.
4. **Aider + Groq** — in-repo refactoring, multi-file edits.

### Recommended Agent Assignment
| Agent | Provider | Tokens | Use For |
|-------|----------|--------|--------|
| Kimi CLI | Moonshot | Free | **Primary coder** — quality + speed |
| Claude Opus 4.7 | Anthropic | Limited | Architecture, complex algorithms, reviews |
| Pi + Groq | Groq | Unlimited | Batch code gen, tests, boilerplate |
| Aider + Groq | Groq | Unlimited | In-repo refactoring, multi-file edits |
| Codex | OpenAI | TBD | Needs key — general coding |

### Example Parallel Pattern
```bash
# Fire 3 Pi agents at different tasks (all free, all fast)
pi -p "task 1" --provider groq --model llama-3.3-70b-versatile &
pi -p "task 2" --provider groq --model llama-3.3-70b-versatile &
pi -p "task 3" --provider groq --model llama-3.3-70b-versatile &
wait

# Then serialize: one cargo check at a time
cargo check --manifest-path /tmp/repo1/Cargo.toml
cargo check --manifest-path /tmp/repo2/Cargo.toml
```

## GPU Git-Agent Architecture (Thinking Out Loud)

The fleet concept of "git-agents" — autonomous coding entities that communicate via git commits — could leverage GPU acceleration:

1. **Batch Code Generation**: GPU-accelerated LLMs (via DeepInfra) generate multiple code solutions in parallel batches
2. **FLUX Bytecode Agents**: If we compile agent logic to FLUX bytecodes, we could run agent decision loops on the Jetson GPU via CUDA
3. **Constraint-Theory Coded Agents**: An agent whose internal state is maintained via PythagoreanManifold snapping — zero drift in long-running autonomous sessions
4. **Pi as GPU Agent**: Pi supports multiple providers — route to GPU-accelerated models (DeepInfra has GPU inference) for code generation, use cheap models for review/test

### Potential GPU Git-Agent Stack
```
DeepInfra GPU Models (Seed 2.0, Nemotron) → code generation
Groq LPU (llama-3.3-70b) → fast review/test
Jetson CUDA (FLUX bytecode) → agent logic execution
Constraint Theory → drift-free agent state management
```

## Fleet Communication
- **I2I Protocol**: `[I2I:TYPE] scope — summary` commit format
- **Pi**: OpenClaw embedded, accessed via `.bin/pi`
- **My vessel**: https://github.com/SuperInstance/forgemaster
