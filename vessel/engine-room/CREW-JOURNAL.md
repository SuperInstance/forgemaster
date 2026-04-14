# 📓 Crew Journal — Agent Status Log

> Checked every 3 hours. Each entry: who ran, what they did, what failed.

## 2026-04-14

### 09:30 — First Wave (Claude Code, 4 agents)
- **tide-crest**: Physics sim proof ✅ — compiled, pushed
- **faint-sable**: Vector search proof ✅ — compiled, pushed (later rebuilt by Pi after OOM)
- **ember-shell**: API reference ✅ — 855 lines, pushed
- **mild-ember**: Game sync proof ✅ — compiled, pushed
- **Lesson**: 4 parallel cargo builds = OOM. Max 2 concurrent.

### 10:30 — Second Wave (Pi/Groq, 2 agents)
- **quiet-prairie**: Vector search rebuild ✅ — compiled, pushed
- **nimble-canyon**: Signal processing ❌ — Pi failed "Failed to call a function". Complex prompt too much for llama-70b.
- **Lesson**: Pi handles well-scoped tasks. Complex multi-constraint → Claude.

### 11:00 — Third Wave (Pi/Groq, 3 agents for validation)
- **Rigidity validation**: ✅ compiled after Cargo.toml fix (Pi wrote unquoted name)
- **Bits validation**: ✅ compiled after flattening nested workspace mess
- **Holonomy validation**: ❌ Pi failed twice. Claude Code succeeded.
- **Lesson**: Pi generates Cargo.toml errors (unquoted strings, nested workspaces). Always verify and fix.

### Crew Notes
- Pi on Groq is reliable for simple code gen but struggles with:
  - Complex multi-constraint prompts
  - Proper TOML formatting
  - Avoiding nested directory structures
- Claude Code produces higher quality but costs tokens
- Best pattern: Pi for first draft, human review for TOML/API fixes, cargo check to verify
