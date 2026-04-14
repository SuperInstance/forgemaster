# 📦 Cargo Hold — Below-Deck Equipment

> Tools that are installed and ready to load, but not currently running.

## Coding Agents

### Pi Coding Agent (Load: Free, Remote)
- **Binary**: `/usr/lib/node_modules/openclaw/node_modules/.bin/pi`
- **Provider**: Groq (LPU inference, unlimited)
- **Model**: `llama-3.3-70b-versatile`
- **Load command**: `pi -p "$TASK" --provider groq --model llama-3.3-70b-versatile`
- **Also available**: DeepInfra models via `--provider openai`
- **Best for**: Batch code gen, tests, boilerplate, parallel work

### Claude Code (Load: Expensive, Limited Tokens)
- **Binary**: `/home/phoenix/.local/bin/claude` v2.1.86
- **Mode**: `--print --permission-mode bypassPermissions` (no PTY)
- **Best for**: Architecture, complex reasoning, reviews
- **⚠️ Use sparingly** — limited budget

### Aider (Load: Free, Remote)
- **Binary**: `/home/phoenix/.local/bin/aider` v0.86.2
- **Provider**: Groq via `--model groq/llama-3.3-70b-versatile`
- **Mode**: `--no-auto-commits --message "prompt"`
- **Best for**: In-repo refactoring, multi-file edits

### Codex CLI (Load: Needs Key)
- **Binary**: `/usr/bin/codex` v0.120.0
- **Needs**: OPENAI_API_KEY (not configured)
- **Mode**: PTY required, `codex exec "prompt"`
- **Status**: ⚠️ Cannot use without key

## API Keys Available

| Key | Provider | Models | Cost |
|-----|----------|--------|------|
| GROQ_API_KEY | Groq | llama-3.3-70b, compound, gpt-oss-120b | Free |
| DEEPINFRA_API_KEY | DeepInfra | Seed 2.0, Nemotron, FLUX models | Pay-per-use |

## Load Procedures

### Light Load (1 Pi agent, ~0 local RAM)
```bash
PI=/usr/lib/node_modules/openclaw/node_modules/.bin/pi
cd /tmp/$WORK_DIR && git init
$PI -p "$TASK" --provider groq --model llama-3.3-70b-versatile
```

### Medium Load (2 Pi agents parallel, ~0 local RAM)
```bash
$PI -p "$TASK_A" --provider groq --model llama-3.3-70b-versatile &
$PI -p "$TASK_B" --provider groq --model llama-3.3-70b-versatile &
wait
```

### Heavy Load (1 Claude Code + 1 Pi)
```bash
claude --print --permission-mode bypassPermissions "$COMPLEX_TASK" &
pi -p "$SIMPLE_TASK" --provider groq --model llama-3.3-70b-versatile &
wait
```

### ⚠️ Overload Warning
- 3+ cargo builds = OOM kill on WSL2
- Always serialize: `cargo check` one at a time
- Clean `/tmp` between builds: `rm -rf /tmp/repo/target/`

## A/B Test Pattern
```bash
# Same task, two different models
pi -p "$TASK" --provider groq --model llama-3.3-70b-versatile > /tmp/result-a.txt &
pi -p "$TASK" --provider groq --model openai/gpt-oss-120b > /tmp/result-b.txt &
wait
diff /tmp/result-a.txt /tmp/result-b.txt
```
