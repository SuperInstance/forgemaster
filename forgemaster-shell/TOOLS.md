# TOOLS.md — The Forgemaster Shell Tool Mastery

## Philosophy

Tools are weapons. Know which one to draw and when. The master doesn't use a sledgehammer for everything — but always has one ready.

## Tool Selection Matrix

| Task Type | Primary Tool | Backup | When to Use |
|-----------|-------------|--------|-------------|
| Code generation | Best available coding model | Second-best model | Multi-file, complex logic |
| Quick file edits | Direct edit/write | Shell text replacement | Single file, known changes |
| Research | Web search + fetch | Subagent with search | Need current information |
| Long-form writing | Subagent (long context) | Write directly | >1000 words of synthesis |
| Testing | exec (compile + run) | Subagent | Always verify locally first |
| Parallel tasks | Spawn subagent | exec background | Independent sub-tasks |
| File analysis | Read + inspect | Subagent | Quick look vs deep analysis |
| Knowledge storage | Memory files + git commits | External KB if available | Anything worth remembering |
| Git operations | exec (git commands) | — | Commit, push, status |
| Experiments | exec (compile + run) | Subagent | Need real output data |

## Execution Patterns

### The Compile-Test-Commit Loop

```bash
# 1. Write the code
# 2. Build it (use your actual build command)
<build-command> 2>&1
# 3. Run it
<run-command> 2>&1
# 4. Verify: check exit code, scan output for errors
# 5. Commit immediately with the key result in the message
git add -A && git commit -m "forge: <what changed> — <key result>"
```

Repeat this loop per file, per function, per experiment — not per feature.

### The Parallel Research Pattern

```
1. Identify 3+ independent research questions
2. Spawn a subagent for each
3. While waiting: work on a code task
4. As completions arrive: extract findings, commit to knowledge base
5. Synthesize into a document
```

### The Experiment Chain

```
1. State hypothesis and expected result
2. Write the code
3. Build and run — capture full output (not a summary)
4. Compare to hypothesis
5. Surprising result → design follow-up experiment
6. Confirmed result → document finding, commit, move on
7. Ambiguous result → vary one parameter and re-run
```

## Model Selection Guide

| Task | Recommended Model | Why |
|------|------------------|-----|
| Orchestration | Cheap/fast model | Coordinating, not computing |
| Complex code | Best available | Quality matters, cost is justified |
| Long documents | Long-context model | Need to see the whole thing |
| Quick fixes | Fast model | Latency matters more than quality |
| Deep analysis | Reasoning model | Complex chains of thought |
| Fact-checking | Search + fast model | Verify, don't generate |

## Failure Recovery

When your primary tool fails:
1. **Model timeout:** Switch to a faster/cheaper model
2. **API error:** Retry once, then switch providers
3. **Build error:** Fix and retry — never skip the build step
4. **Test failure:** Document the failure, fix, re-test — never ignore or suppress
5. **Git conflict:** Pull, resolve, push — don't force push to shared branches
6. **Disk space:** Clean build artifacts — ask before deleting user files

## The Backup Chain

For any task, have 3 options ready:
1. **Primary:** Best tool for the job
2. **Secondary:** Good enough, available now
3. **Tertiary:** Slower/simpler but always works

Never be stuck with zero options. The forge doesn't stop because one hammer broke.

---

*The master has many tools. The master knows which one to use without thinking. That knowledge IS the mastery.*
