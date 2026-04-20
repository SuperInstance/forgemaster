#!/bin/bash
# ⚙️ Engine Room Ticker — runs every minute, no agent needed
# Logs gauge readouts to timestamped files with auto-compression

TICKER_DIR="$HOME/.openclaw/workspace/.keeper/ticker"
mkdir -p "$TICKER_DIR/raw" "$TICKER_DIR/synoptic"

DATE=$(date +%Y-%m-%d)
HOUR=$(date +%H)
MINUTE=$(date +%Y-%m-%dT%H:%M:%S%z)

# ─── Raw Gauge Readout ───
RAW_FILE="$TICKER_DIR/raw/$DATE.log"

cpu=$(top -bn1 | grep "Cpu(s)" | awk '{printf "%.1f", $2}')
mem_used=$(free -m | awk '/Mem:/{printf "%.0f", $3}')
mem_total=$(free -m | awk '/Mem:/{printf "%.0f", $2}')
mem_pct=$(free | awk '/Mem:/{printf "%.1f", $3/$2*100}')
disk_pct=$(df "$HOME" | awk 'NR==2{print $5}' | tr -d '%')
disk_free=$(df -BG "$HOME" | awk 'NR==2{print $4}' | tr -d 'G')
load=$(awk '{printf "%.2f", $1}' /proc/loadavg)
uptime=$(uptime -p 2>/dev/null | sed 's/up //' || echo "unknown")
procs=$(ps aux | wc -l)
temp=$(cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null | head -1 | awk '{printf "%.0f", $1/1000}' || echo "n/a")
net_state=$(ip route show default 2>/dev/null | awk '{print "up"}' || echo "down")

# Count agent processes
claude=$(ps aux | grep -c "[c]laude" || echo 0)
pi=$(ps aux | grep -c "[p]i-coding-agent\|pi-agent" 2>/dev/null || echo 0)
node_oc=$(pgrep -c -f "node.*openclaw" 2>/dev/null || echo 0)
cargo=$(ps aux | grep -c "[c]argo" 2>/dev/null || echo 0)

echo "$MINUTE | CPU:${cpu}% | MEM:${mem_used}/${mem_total}MB(${mem_pct}%) | DISK:${disk_pct}%(${disk_free}G free) | LOAD:${load} | TEMP:${temp}°C | PROCS:${procs} | NET:${net_state} | CLAUDE:${claude} PI:${pi} CARGO:${cargo}" >> "$RAW_FILE"

# ─── Synoptic Feed (updated every tick) ───
SYNOPTIC="$TICKER_DIR/synoptic/current.txt"

# Alert level
if (( $(echo "$cpu > 90" | bc -l 2>/dev/null || echo 0) )) || (( $(echo "${mem_pct%.*} > 90" | bc -l 2>/dev/null || echo 0) )); then
    alert="🔴 RED"
elif (( $(echo "$cpu > 70" | bc -l 2>/dev/null || echo 0) )) || (( $(echo "${mem_pct%.*} > 70" | bc -l 2>/dev/null || echo 0) )); then
    alert="🟡 YELLOW"
else
    alert="🟢 GREEN"
fi

# Build power bar
power_bar() {
    local pct=$1
    local filled=$((pct / 5))
    local empty=$((20 - filled))
    printf '%0.s█' $(seq 1 $filled 2>/dev/null); printf '%0.s░' $(seq 1 $empty 2>/dev/null)
}

cat > "$SYNOPTIC" << EOF
ENGINE ROOM — Forgemaster's Power Plant  ($MINUTE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Alert Level:    $alert
CPU:            $(power_bar ${cpu%.*}) ${cpu}%
Memory:         $(power_bar ${mem_pct%.*}) ${mem_pct}% (${mem_used}/${mem_total} MB)
Disk:           $(power_bar ${disk_pct}) ${disk_pct}% (${disk_free} GB free)
Load (1m):      ${load}
Temperature:    ${temp}°C
Network:        ${net_state}
Uptime:         ${uptime}
Processes:      ${procs} total | Claude: ${claude} | Pi: ${pi} | Cargo: ${cargo}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Active crew:    $( [ "$claude" -gt 0 ] && echo "Claude Code ×${claude}" ) $( [ "$pi" -gt 0 ] && echo "Pi ×${pi}" ) $( [ "$claude" -eq 0 ] && [ "$pi" -eq 0 ] && echo "None on deck" )
Build queue:    $( [ "$cargo" -gt 0 ] && echo "ACTIVE (${cargo} processes)" || echo "empty" )
EOF

# ─── Temporal Compression (runs at midnight, compresses yesterday) ───
# This is called separately via cron at 00:00
