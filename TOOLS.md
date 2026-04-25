# TOOLS.md — Quick Reference

## Agent Priority
1. **Kimi CLI** — primary coder, free, quality+speed
2. **Claude Code** — architecture only, limited credits
3. **Pi + SiliconFlow** — batch work, tests
4. **Aider** — in-repo refactoring (needs Groq key)

## One-Liners
- Kimi: `kimi -p "prompt" --quiet -y --work-dir /path`
- Claude: `claude --print --permission-mode bypassPermissions`
- Pi: `pi -p "prompt" --provider siliconflow --model deepseek-ai/deepseek-chat`

## OOM Rules
- Max 2 concurrent `cargo check/build`
- Serialize Rust builds, clean target/ between them
- Kimi: ~100 words max, `--quiet` mode

## Key Constraints
- **rustc 1.75.0** — pin uuid≤1.4.1, no edition2024
- **No GROQ_API_KEY** — Groq agents unavailable
- **No OPENAI_API_KEY** — Codex unavailable

## Fleet Comms
- I2I Protocol: `[I2I:TYPE] scope — summary`
- Vessel: https://github.com/SuperInstance/forgemaster

See `references/tools-detail.md` for full agent configs.
