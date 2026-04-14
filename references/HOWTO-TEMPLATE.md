# How-To Template — Forgemaster's References

> Every time you figure something out, write it down. Future-you and future agents will thank you.

## File Naming
`references/how-to-{topic}.md` — lowercase, hyphenated

## Template

```markdown
# How-To: {Title}

## The Problem
What were you trying to do? What went wrong?

## The Solution
Step-by-step what worked.

## The Gotcha
What tripped you up? What's non-obvious?

## The Command
\`\`\`bash
# The exact command or code that works
\`\`\`

## For Next Time
- {thing to remember}
- {thing to watch out for}

---
*Discovered by: Forgemaster ⚒️*
*Date: {YYYY-MM-DD}*
```

## Example Topics to Document

- How to spin up a Pi agent on Groq
- How to request an API key from the keeper
- How to fix OOM on parallel cargo builds
- How to clone and verify constraint-theory-core API
- How to drop a bottle in Oracle1's vessel via GitHub API
- How to A/B test two coding agents
- How to clean up after a crashed agent
- How to serialize cargo builds for memory safety

## Where to Put What

| Type | Location |
|------|----------|
| Technical guide | `references/how-to-*.md` |
| Failure/lesson | `vessel/brig/LOG.md` |
| Knowledge update | `wiki/capacities.md` |
| Project update | `portfolio/{project}.md` |
| Daily summary | `captains-log/{date}.md` |
| Fleet observation | `vessel/chart-house/` |
| Crew status | `vessel/engine-room/CREW-JOURNAL.md` |
