---
name: effective-agent
description: How to be an effective AI agent — patterns, model hierarchy, parallelism, and shipping discipline. Based on 200+ commits in 24 hours.
version: 1.0.0
---

# How To Be An Effective Agent

Read this BEFORE starting work. These patterns work. Use them.

## The 7 Patterns

### 1. Seed Mini Barrage
Fire 5-10 parallel queries to cheap models. Collect in 30-90s. Commit. Move on.
- Model: `ByteDance/Seed-2.0-mini` via DeepInfra
- Cost: ~$0.02/query
- Use heredoc pattern: `python3 << 'PYEOF' ... PYEOF &`

### 2. Model Hierarchy
Cheap first. Escalate only when needed:
- Bulk creation → Seed-2.0-mini ($0.02)
- Code generation → Seed-2.0-code ($0.03)
- Deep analysis → Seed-2.0-pro ($0.05)
- Strategic → Qwen-397B ($0.10)
- Math/proofs → DeepSeek Reasoner ($0.10)
- Best overall → Claude Opus ($1-3, rate-limited)

### 3. Subagent Parallelism
Fire 5 subagents → `sessions_yield()` → collect → commit → repeat.
Max concurrent: 5 (system limit).

### 4. Commit Every 30 Minutes
`git add -A && git commit && git push`. Uncommitted = lost after compaction.

### 5. One Repo = One Idea
Extract monorepos into focused repos. `gh repo create` + push.

### 6. Deep Research as a Service
10 models × same question from different angles. Synthesize consensus. Gaps = insights.

### 7. File-First Thinking
Don't describe. Write the file. Every discussion should produce ≥1 file.

## What NOT To Do
- Don't poll in loops. `sessions_yield()` and wait.
- Don't block on one model. Switch when rate-limited.
- Don't write status updates. Write commits.
- Don't plan for 10 minutes what you can build in 5.
- Don't use expensive models for cheap tasks.

## Self-Assessment (Honest Gaps)
- Timeouts on queries >180s (use subagents)
- Rust builds can OOM (serialize cargo builds)
- Don't always retry timeouts with shorter prompts
- Sometimes fire 10 models when 3 would do
- Generate lots of files without pruning

## Full Reference
See `references/forgemaster-operating-system.md` for the complete document with code examples, cost breakdowns, and session stats template.
