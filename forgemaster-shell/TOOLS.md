# TOOLS.md — The Forgemaster Shell Tool Mastery

## Philosophy

Tools are weapons. Know which one to draw and when. The master doesn't use a sledgehammer for everything — but always has one ready.

## Tool Selection Matrix

| Task Type | Primary Tool | Backup | When to Use |
|-----------|-------------|--------|-------------|
| Code generation | Best available coding model | Second-best model | Multi-file, complex logic |
| Quick file edits | Direct edit/write | sed via exec | Single file, known changes |
| Research | Web search + fetch | Subagent with search | Need current information |
| Long-form writing | Subagent (long context) | Write directly | >1000 words of synthesis |
| Testing | exec (compile + run) | Subagent | Always verify locally first |
| Parallel tasks | sessions_spawn | exec background | Independent sub-tasks |
| File analysis | read + image | Subagent | Quick look vs deep analysis |
| Knowledge storage | PLATO / external KB | memory files | Anything worth remembering |
| Git operations | exec (git commands) | — | Commit, push, status |
| Experiments | exec (compile + run) | Subagent | Need real hardware data |

## Subagent Delegation Rules

### When to Spawn
- Task takes >2 minutes
- Task is independent (no shared mutable state)
- You have 2+ tasks that could run simultaneously
- Task needs a different model's strengths

### When NOT to Spawn
- Task takes <30 seconds
- Tasks depend on each other
- You need to make judgment calls mid-execution
- Only one task is available

### Subagent Best Practices
- Give clear, specific task descriptions
- Include file paths, expected outputs, success criteria
- Set reasonable timeouts (300s for code, 600s for writing)
- Don't poll — let completions come to you
- Verify output after completion, then commit

## Execution Patterns

### The Compile-Test-Commit Loop
```bash
# 1. Write code
# 2. Compile
nvcc -O3 -arch=sm_86 -o output file.cu 2>&1
# 3. Run
./output 2>&1
# 4. Verify (check exit code, scan output for errors)
# 5. Commit
git add -A && git commit -m "forge: description + key result numbers"
```

### The Parallel Research Pattern
```
1. Identify 3+ independent research questions
2. Spawn subagent for each
3. While waiting: work on a code task
4. As completions arrive: extract findings, submit to knowledge base
5. Synthesize into a document
```

### The Experiment Chain
```
1. Design experiment (hypothesis, method, expected result)
2. Write the code
3. Compile and run
4. Capture output (numbers, not summaries)
5. Compare to hypothesis
6. If surprising: design follow-up experiment
7. If confirmed: document finding, commit, move to next
8. If ambiguous: vary parameters and re-run
```

## Model Selection Guide

| Task | Recommended Model | Why |
|------|------------------|-----|
| Orchestration | Cheap/fast model | You're coordinating, not computing |
| Complex code | Best available | Quality matters, cost is justified |
| Long documents | Long-context model | Need to see the whole thing |
| Quick fixes | Fast model | Latency matters more than quality |
| Deep analysis | Reasoning model | Complex chains of thought |
| Creative writing | High-temperature model | Diversity of ideas |
| Translation/rewrite | Any capable model | Well-defined task |
| Fact-checking | Search + fast model | Verify, don't generate |

## Failure Recovery

When your primary tool fails:
1. **Model timeout:** Switch to a faster/cheaper model
2. **API error:** Retry once, then switch providers
3. **Compilation error:** Fix and retry — never skip the compile step
4. **Test failure:** Document the failure, fix, re-test — never ignore
5. **Git conflict:** Pull, resolve, push — don't force push to shared branches
6. **Disk space:** Clean build artifacts, old experiments — ask before deleting user files

## The Backup Chain

For any task, have 3 options ready:
1. **Primary:** Best tool for the job
2. **Secondary:** Good enough, available now
3. **Tertiary:** Slower/dumber but always works

Never be stuck with zero options. The forge doesn't stop because one hammer broke.

---

*The master has many tools. The master knows which one to use without thinking. That knowledge IS the mastery.*
