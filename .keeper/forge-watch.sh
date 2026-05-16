#!/bin/bash
# 🔨 FORGE-WATCH — Activity Monitor for Forgemaster
# Runs every 5 minutes via cron
# If Forgemaster hasn't pushed to git in 45 minutes, this is a problem.
# Writes a file that the heartbeat system will see.

FORGE_DIR="$HOME/.openclaw/workspace"
KEEPER_DIR="$FORGE_DIR/.keeper"
WATCH_FILE="$KEEPER_DIR/forge-watch.json"
LOG="$KEEPER_DIR/forge-watch.log"

mkdir -p "$KEEPER_DIR"

# Check last git push time to fleet-knowledge
FK_DIR="/tmp/fleet-knowledge"
if [ -d "$FK_DIR/.git" ]; then
    LAST_PUSH=$(git -C "$FK_DIR" log -1 --format=%ct 2>/dev/null || echo 0)
    NOW=$(date +%s)
    AGE=$(( NOW - LAST_PUSH ))
    AGE_MIN=$(( AGE / 60 ))
else
    AGE_MIN=9999
fi

# Check last tile submission (chain growth) via PLATO API
CHAIN_NOW=$(curl -sf http://147.224.38.131:8847/rooms 2>/dev/null | python3 -c "
import sys, json
rooms = json.loads(sys.stdin.read())
total = sum(d.get('tile_count',0) for d in rooms.values())
print(total)
" 2>/dev/null || echo "error")

# Write status
cat > "$WATCH_FILE" << EOF
{
  "timestamp": "$(date -Iseconds)",
  "last_git_push_min_ago": $AGE_MIN,
  "plato_total_tiles": "$CHAIN_NOW",
  "stale": $([ $AGE_MIN -gt 45 ] && echo "true" || echo "false")
}
EOF

# Log
echo "[$(date -Iseconds)] WATCH: push_age=${AGE_MIN}min tiles=$CHAIN_NOW stale=$([ $AGE_MIN -gt 45 ] && echo YES || echo no)" >> "$LOG"

# If stale for more than 45 minutes, write an alert to HEARTBEAT.md
if [ $AGE_MIN -gt 45 ]; then
    echo "⚠️ ALERT: No git push in ${AGE_MIN} minutes. Forge may be stalled." >> "$KEEPER_DIR/forge-alert.txt"
fi

# Keep log from growing forever
tail -100 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
