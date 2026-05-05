#!/bin/bash
# ⚓ Brothers-Keeper — Forgemaster's Guardian Daemon
# Runs via system cron every 5 minutes
# Monitors: gateway health, heartbeat freshness, hardware resources
# Heals: restarts gateway, kills zombies, cleans disk
# Proxies: API keys for git-agents

set -euo pipefail

KEEPER_DIR="$HOME/.openclaw/workspace/.keeper"
HEARTBEAT="$KEEPER_DIR/heartbeat.json"
KEEPER_RESP="$KEEPER_DIR/keeper-response.json"
KEEPER_LOG="$KEEPER_DIR/keeper.log"
KEY_DIR="$KEEPER_DIR/keys"
STALE_THRESHOLD=900  # 15 minutes in seconds
GATEWAY_SERVICE="openclaw-gateway.service"

# ─── Logging ───
log() {
  echo "[$(date -Iseconds)] KEEPER: $*" | tee -a "$KEEPER_LOG"
}

# ─── Hardware Health Check ───
get_health() {
  local cpu mem_used mem_total disk_free load gateway_status gateway_pid

  cpu=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d. -f1)
  mem_used=$(free -g | awk '/Mem:/{print $3}')
  mem_total=$(free -g | awk '/Mem:/{print $2}')
  disk_free=$(df -BG "$HOME" | awk 'NR==2{print $4}' | tr -d 'G')
  load=$(awk '{print $1}' /proc/loadavg)

  if systemctl --user is-active --quiet "$GATEWAY_SERVICE" 2>/dev/null; then
    gateway_status="running"
    gateway_pid=$(systemctl --user show "$GATEWAY_SERVICE" --property=MainPID --value 2>/dev/null || echo "unknown")
  else
    gateway_status="stopped"
    gateway_pid="none"
  fi

  # Count active agent processes
  local claude_count pi_count node_count
  claude_count=$(pgrep -c -f "claude" 2>/dev/null || echo 0)
  pi_count=$(pgrep -c -f "pi-coding-agent\|pi-agent" 2>/dev/null || echo 0)
  node_count=$(pgrep -c -f "node.*openclaw" 2>/dev/null || echo 0)

  cat > "$KEEPER_RESP" << EOF
{
  "timestamp": "$(date -Iseconds)",
  "gateway": "$gateway_status",
  "gateway_pid": "$gateway_pid",
  "cpu_pct": $cpu,
  "mem_used_gb": $mem_used,
  "mem_total_gb": $mem_total,
  "disk_free_gb": $disk_free,
  "load_1m": $load,
  "active_processes": {
    "claude": $claude_count,
    "pi": $pi_count,
    "node_openclaw": $node_count
  },
  "actions_taken": [],
  "warnings": []
}
EOF
}

# ─── Gateway Health ───
check_gateway() {
  if ! systemctl --user is-active --quiet "$GATEWAY_SERVICE" 2>/dev/null; then
    log "WARN: Gateway is down. Attempting restart."
    systemctl --user restart "$GATEWAY_SERVICE" 2>/dev/null || true
    sleep 3
    if systemctl --user is-active --quiet "$GATEWAY_SERVICE" 2>/dev/null; then
      log "OK: Gateway restarted successfully."
    else
      log "CRITICAL: Gateway restart failed!"
    fi
  fi
}

# ─── Heartbeat Check (Brothers-Keeper Protocol) ───
check_heartbeat() {
  if [ ! -f "$HEARTBEAT" ]; then
    log "WARN: No heartbeat file found. Captain may not have started yet."
    return
  fi

  local hb_ts now diff
  hb_ts=$(python3 -c "
import json,sys
try:
  d=json.load(open('$HEARTBEAT'))
  print(d.get('timestamp',''))
except: print('')
" 2>/dev/null)

  if [ -z "$hb_ts" ]; then
    log "WARN: Could not parse heartbeat timestamp."
    return
  fi

  now=$(date +%s)
  hb_epoch=$(date -d "$hb_ts" +%s 2>/dev/null || echo 0)
  diff=$(( now - hb_epoch ))

  if [ "$diff" -gt "$STALE_THRESHOLD" ]; then
    log "WARN: Heartbeat stale (${diff}s old). Brothers-Keeper protocol activated."

    # Check for zombie processes
    local zombies
    zombies=$(ps aux | grep -c 'Z' 2>/dev/null || echo 0)
    if [ "$zombies" -gt 5 ]; then
      log "WARN: $zombies zombie processes detected."
    fi

    # Check if gateway is responding
    if systemctl --user is-active --quiet "$GATEWAY_SERVICE" 2>/dev/null; then
      log "INFO: Gateway running but captain silent. Gateway may need restart."
      # Don't auto-restart gateway if it's running — captain might just be between sessions
    else
      log "CRITICAL: Gateway down AND captain silent. Full restart."
      systemctl --user restart "$GATEWAY_SERVICE" 2>/dev/null || true
    fi

    # Check disk space
    local disk_pct
    disk_pct=$(df "$HOME" | awk 'NR==2{print $5}' | tr -d '%')
    if [ "$disk_pct" -gt 90 ]; then
      log "WARN: Disk at ${disk_pct}%. Cleaning /tmp and cargo cache."
      rm -rf /tmp/proof-*/target/ /tmp/*.log 2>/dev/null || true
      rm -rf "$HOME/.cargo/registry/cache"/*/*.gz 2>/dev/null || true
    fi
  fi
}

# ─── API Key Proxy ───
process_key_requests() {
  local req_file="$KEEPER_DIR/key-request.json"
  if [ ! -f "$req_file" ]; then
    return
  fi

  local requester provider ts
  requester=$(python3 -c "import json; print(json.load(open('$req_file')).get('requester','unknown'))" 2>/dev/null || echo "unknown")
  provider=$(python3 -c "import json; print(json.load(open('$req_file')).get('provider',''))" 2>/dev/null || echo "")
  ts=$(date +%s)

  local key_value=""
  case "$provider" in
    groq)
      key_value="${GROQ_API_KEY:-}"
      ;;
    deepinfra)
      key_value="${DEEPINFRA_API_KEY:-}"
      ;;
    *)
      log "WARN: Unknown provider '$provider' requested by '$requester'"
      rm -f "$req_file"
      return
      ;;
  esac

  if [ -n "$key_value" ]; then
    local key_file="$KEY_DIR/${provider}-${requester}-${ts}.key"
    echo "$key_value" > "$key_file"
    chmod 600 "$key_file"
    log "OK: Key for '$provider' issued to '$requester' (expires in 60s)"

    # Auto-delete after 60 seconds
    (sleep 60 && rm -f "$key_file") &
  else
    log "WARN: No key available for provider '$provider'"
  fi

  rm -f "$req_file"
}

# ─── Clean Expired Keys ───
clean_keys() {
  find "$KEY_DIR" -name "*.key" -mmin +5 -delete 2>/dev/null || true
}

# ─── Rotate Log ───
rotate_log() {
  if [ -f "$KEEPER_LOG" ] && [ "$(wc -l < "$KEEPER_LOG")" -gt 5000 ]; then
    tail -1000 "$KEEPER_LOG" > "$KEEPER_LOG.tmp"
    mv "$KEEPER_LOG.tmp" "$KEEPER_LOG"
    log "OK: Log rotated."
  fi
}

# ─── Main ───
log "--- Keeper cycle start ---"
check_gateway
check_heartbeat
get_health
process_key_requests
clean_keys
rotate_log
log "--- Keeper cycle end ---"
