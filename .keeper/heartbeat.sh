#!/bin/bash
# 💓 Forgemaster Heartbeat — written by the captain every 5 minutes
# Called via system cron or HEARTBEAT.md hook

KEEPER_DIR="$HOME/.openclaw/workspace/.keeper"
HEARTBEAT="$KEEPER_DIR/heartbeat.json"

mkdir -p "$KEEPER_DIR"

# Gather quick stats
crew_running=$(ps aux | grep -cE 'claude|pi-coding|aider' 2>/dev/null || echo 0)
proofs_done=$(ls -d /tmp/proof-*/src 2>/dev/null | wc -l)
disk_free=$(df -BG "$HOME" | awk 'NR==2{print $4}' | tr -d 'G')

cat > "$HEARTBEAT" << EOF
{
  "timestamp": "$(date -Iseconds)",
  "agent": "forgemaster",
  "status": "alive",
  "crew_active": $crew_running,
  "proofs_in_progress": $proofs_done,
  "disk_free_gb": $disk_free,
  "last_action": "$(tail -1 "$KEEPER_DIR/last-action.txt" 2>/dev/null || echo "heartbeat")",
  "message": "All hands on deck"
}
EOF
