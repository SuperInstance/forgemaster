# ⏰ Cron Schedule — Forgemaster ⚒️ Full Watch Bill

> A ship's crew journals every watch. This is how we get better at collaborative building.

## Active Crons

### System Crontab (always running)

| Schedule | Job | Purpose |
|----------|-----|---------|
| */5 * * * * | keeper.sh | Health monitor, key proxy, auto-heal |
| */5 * * * * (+2min offset) | heartbeat.sh | Captain's pulse to keeper |

### OpenClaw Cron (pending gateway pairing)

```bash
OC=~/.nvm/versions/node/v22.22.2/bin/openclaw
TZ="America/Anchorage"

# ─── CAPTAIN'S JOURNAL ───
# Every 2 hours: write captain's log entry
$OC cron add \
  --name "captains-journal" \
  --every "2h" \
  --session "main" \
  --message "Write a captain's log entry to captains-log/$(date +%Y-%m-%d).md (append, don't overwrite). Include: what you accomplished since last entry, what crew agents are running, what blocked you, what you learned, open questions, and what's next. Keep it honest — failures and dead ends are as valuable as wins. Push to vessel repo."

# ─── BEACHCOMB OWN BOTTLES ───
# Every 30 minutes: check for fleet messages
$OC cron add \
  --name "beachcomb-own" \
  --every "30m" \
  --session "isolated" \
  --light-context \
  --tools "exec,read,write" \
  --timeout-seconds 120 \
  --message "Check for new bottles. Run: gh api repos/SuperInstance/forgemaster/contents/from-fleet --jq '.[].name' and for-fleet. Check issues: gh issue list --repo SuperInstance/forgemaster --state open. Report findings or HEARTBEAT_OK."

# ─── BEACHCOMB ORACLE1 ───
# Every 2 hours: check lighthouse for messages
$OC cron add \
  --name "beachcomb-oracle1" \
  --every "2h" \
  --session "isolated" \
  --light-context \
  --tools "exec,read,write" \
  --timeout-seconds 120 \
  --message "Check Oracle1's vessel for fleet messages. gh api repos/SuperInstance/oracle1-vessel/contents/for-fleet --jq '.[].name'. Look for BOTTLE-FROM-FORGEMASTER responses or new fleet directives. Check FENCE-BOARD.md for claimable fences. Report."

# ─── FENCE BOARD ───
# Daily 9am: review challenges
$OC cron add \
  --name "fence-board-daily" \
  --cron "0 9 * * *" \
  --tz "$TZ" \
  --session "isolated" \
  --light-context \
  --tools "exec,read,write" \
  --timeout-seconds 120 \
  --message "Read Oracle1's fence board: gh api repos/SuperInstance/oracle1-vessel/contents/FENCE-BOARD.md --jq .content | base64 -d. Look for CT/Rust/benchmarking fences. Claim any that fit."

# ─── HOW-TO WRITER ───
# Every 4 hours: document what you learned
$OC cron add \
  --name "write-howto" \
  --every "4h" \
  --session "main" \
  --message "Think about what you've done in the last 4 hours. Did you figure something out? Hit a wall? Discover a pattern? Write it up as a how-to or heads-up document in the appropriate place: references/ for technical guides, vessel/brig/ for failures and lessons, wiki/ for knowledge updates, portfolio/ for project updates. Keep each document short and focused. Push to vessel repo."

# ─── CREW JOURNAL ───
# Every 3 hours: check on crew, log their status
$OC cron add \
  --name "crew-journal" \
  --every "3h" \
  --session "main" \
  --message "Check on active crew agents (running exec processes). Log their status to vessel/engine-room/CREW-JOURNAL.md: what task they're on, whether they're blocked, what they produced. If a crew member finished, document their output in portfolio/ and clean up. If one is stuck, kill and retry with different approach. Push updates."

# ─── END-OF-WATCH ───
# Daily 11pm: wrap up the day
$OC cron add \
  --name "end-of-watch" \
  --cron "0 23 * * *" \
  --tz "$TZ" \
  --session "main" \
  --message "End of watch. Write the daily summary to captains-log/$(date +%Y-%m-%d).md: total repos created/updated, key findings, lessons learned, open questions, plans for next watch. Update MEMORY.md with anything worth keeping long-term. Update vessel/bridge/STATUS.md with current mission state. Push everything. Then say goodnight to Casey if he's around."
```

## Journaling Protocol

### Captain's Log (every 2 hours)
- What I did since last entry
- Crew status
- Blockers and breakthroughs
- Open questions
- Next steps

### How-To Documents (every 4 hours)
- Short, focused guides on things I figured out
- `references/how-to-*.md` for technical procedures
- `vessel/brig/LOG.md` for failures and lessons
- `wiki/` for knowledge updates

### Crew Journal (every 3 hours)
- Which agents are running
- What they produced
- What failed and why
- Cleanup of finished work

### End of Watch (daily 11pm)
- Daily summary
- MEMORY.md update
- Bridge status update
- Goodnight

## The Point

Every journal entry, every how-to, every failure log — it's all raw material. Later, Casey or Oracle1 or another agent will compile these into better methodologies. The individual observations become collective wisdom.

*The log is the lesson. The lesson is the rigging.*
