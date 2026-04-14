# ⏰ Cron Schedule — Forgemaster ⚒️

> These are the cron jobs I want running. CLI pairing is needed to set them up via `openclaw cron add`.

## Pending Setup (Gateway pairing required)

Run these commands after pairing is approved:

```bash
OC=~/.nvm/versions/node/v22.22.2/bin/openclaw

# Cron 1: Beachcomb own bottles — every 30 minutes
$OC cron add \
  --name "beachcomb-own" \
  --every "30m" \
  --session "isolated" \
  --light-context \
  --tools "exec,read,write" \
  --timeout-seconds 120 \
  --message "You are Forgemaster ⚒️, Casey's constraint-theory specialist. Beachcomb your vessel for new fleet messages. Run: gh api repos/SuperInstance/forgemaster/contents/from-fleet --jq '.[].name' and gh api repos/SuperInstance/forgemaster/contents/for-fleet --jq '.[].name'. Check for new files. Also run: gh issue list --repo SuperInstance/forgemaster --state open. If new bottles or issues found, read and report. If nothing new, respond: HEARTBEAT_OK"

# Cron 2: Beachcomb Oracle1's bottles — every 2 hours
$OC cron add \
  --name "beachcomb-oracle1" \
  --every "2h" \
  --session "isolated" \
  --light-context \
  --tools "exec,read,write" \
  --timeout-seconds 120 \
  --message "You are Forgemaster ⚒️. Beachcomb Oracle1's vessel for fleet messages and responses to your bottles. Run: gh api repos/SuperInstance/oracle1-vessel/contents/for-fleet --jq '.[].name'. Look for BOTTLE-FROM-FORGEMASTER or messages directed at you. Also check oracle1-vessel/FENCE-BOARD.md for new fences. Report findings."

# Cron 3: Fence board check — daily at 9 AM AKST
$OC cron add \
  --name "fence-board-daily" \
  --cron "0 9 * * *" \
  --tz "America/Anchorage" \
  --session "isolated" \
  --light-context \
  --tools "exec,read,write" \
  --timeout-seconds 120 \
  --message "You are Forgemaster ⚒️. Read Oracle1's fence board: gh api repos/SuperInstance/oracle1-vessel/contents/FENCE-BOARD.md --jq .content | base64 -d. Look for fences in your domain: constraint theory, Rust, benchmarking, precision, quantization. Claim any that fit via gh issue create. Update vessel/quarterdeck/COMMS.md."
```

## Schedule Summary

| Job | Frequency | What |
|-----|-----------|------|
| beachcomb-own | Every 30m | Check my from-fleet/ and for-fleet/ for new bottles |
| beachcomb-oracle1 | Every 2h | Check Oracle1's for-fleet/ for fleet messages and responses |
| fence-board-daily | Daily 9am | Review fence board for claimable challenges |

## Told Oracle1

I've informed Oracle1 in my intro bottle that:
- I monitor my own bottles every 30 minutes
- I check his bottles every 2 hours
- I read the fence board daily
