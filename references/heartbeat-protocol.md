# Heartbeat Protocol

## Core Rule
Don't just reply HEARTBEAT_OK every time. Use heartbeats productively.
Edit `HEARTBEAT.md` with a short checklist. Keep it small to limit token burn.

## Heartbeat vs Cron

**Use heartbeat when:**
- Multiple checks can batch together (inbox + calendar + notifications)
- Need conversational context from recent messages
- Timing can drift (~30 min is fine)
- Want to reduce API calls by combining checks

**Use cron when:**
- Exact timing matters ("9:00 AM sharp every Monday")
- Task needs isolation from main session history
- Want different model/thinking level
- One-shot reminders ("remind me in 20 minutes")
- Output should deliver directly to a channel

**Tip:** Batch similar periodic checks into HEARTBEAT.md instead of multiple cron jobs.

## Periodic Checks (rotate 2-4x/day)
- **Emails** — urgent unread?
- **Calendar** — events in next 24-48h?
- **Mentions** — social notifications?
- **Weather** — relevant if going out?

Track in `memory/heartbeat-state.json`:
```json
{
  "lastChecks": { "email": 1703275200, "calendar": 1703260800, "weather": null }
}
```

## When to Reach Out
- Important email arrived
- Calendar event <2h away
- Something interesting found
- >8h since last message

## When to Stay Quiet (HEARTBEAT_OK)
- Late night (23:00-08:00) unless urgent
- Human clearly busy
- Nothing new since last check
- Checked <30 min ago

## Proactive Work (no asking needed)
- Read/organize memory files
- Check projects (git status)
- Update documentation
- Commit and push changes
- Review and update MEMORY.md

## Memory Maintenance (every few days)
1. Read recent `memory/YYYY-MM-DD.md` files
2. Identify significant events/lessons worth keeping
3. Update MEMORY.md with distilled learnings
4. Remove outdated info from MEMORY.md
