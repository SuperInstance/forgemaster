#!/bin/bash
# gc-collector.sh — Forgemaster Garbage Collector
# Inspired by Oracle1's service-guard.sh + gc-decisions.jsonl
# "Sweep the shop floor. Forge clean."
#
# Oracle1's GC logic:
#   - disk_pressure_pct determines action: keep/compress/distill/truncate
#   - <50%: keep everything
#   - 50-65%: compress large files (>1MB), distill logs into tiles
#   - 65-80%: truncate old sessions, aggressive cache clear
#   - >80%: emergency — nuke /tmp, clear all caches
#   - Log rotation at 10MB max
#   - Each decision: file_type, file_size_kb, disk_pressure → action
#
# Our adaptation for eileen (WSL2, 15GB RAM, 1TB disk):

LOG="/home/phoenix/.openclaw/workspace/.keeper/gc.log"
MAX_LOG_SIZE=$((5 * 1024 * 1024))  # 5MB max
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
WORKSPACE="/home/phoenix/.openclaw/workspace"
KEEPER="$WORKSPACE/.keeper"

# --- Log rotation ---
if [ -f "$LOG" ] && [ $(stat -c%s "$LOG" 2>/dev/null || echo 0) -gt $MAX_LOG_SIZE ]; then
    mv "$LOG" "$LOG.old" 2>/dev/null
    gzip "$LOG.old" 2>/dev/null
fi

# --- Metrics ---
DISK_PCT=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
MEM_AVAIL=$(free -m | awk '/Mem:/ {print $7}')
TMP_SIZE=$(du -sm /tmp 2>/dev/null | awk '{print $1}')
PIP_CACHE=$(du -sm /home/phoenix/.cache/pip 2>/dev/null | awk '{print $1}')
CARGO_CACHE=$(du -sm /home/phoenix/.cargo/registry 2>/dev/null | awk '{print $1}')
NPM_CACHE=$(du -sm /home/phoenix/.npm 2>/dev/null | awk '{print $1}')

echo "[$TIMESTAMP] GC cycle — disk:${DISK_PCT}% mem_avail:${MEM_AVAIL}MB tmp:${TMP_SIZE}MB pip:${PIP_CACHE}MB cargo:${CARGO_CACHE}MB npm:${NPM_CACHE}MB" >> "$LOG"

FREED=0

# --- Phase 1: Only clean /tmp if memory or disk is tight ---
# Logs are training data — don't delete unless we need the space
if [ "$MEM_AVAIL" -lt 2000 ] || [ "$DISK_PCT" -gt 70 ]; then
    STALE_TMP=$(find /tmp -maxdepth 1 -type d \( -name "plato-*" -o -name "pub-*" -o -name "forgemaster" -o -name "oracle1-*" -o -name "jc1-*" -o -name "research" -o -name "papers" -o -name "bottles" -o -name "opus-*" -o -name "kimiclaw*" -o -name "dcs-*" -o -name "claude-*" -o -name "forge-*" -o -name "synergy-*" \) -mtime +1 2>/dev/null)
    for dir in $STALE_TMP; do
        if [ -d "$dir" ]; then
            SIZE=$(du -sm "$dir" 2>/dev/null | awk '{print $1}')
            rm -rf "$dir"
            FREED=$((FREED + SIZE))
            echo "[$TIMESTAMP] TRUNCATE /tmp stale (>1d old, pressure): $dir (${SIZE}MB)" >> "$LOG"
        fi
    done
fi

# --- Phase 2: Ticker logs — keep 7 days, gzip older ---
if [ -d "$KEEPER/ticker/raw" ]; then
    cd "$KEEPER/ticker/raw"
    find . -name "*.log" -mtime +7 -exec gzip {} \; 2>/dev/null
    find . -name "*.log.gz" -mtime +30 -delete 2>/dev/null
fi

# --- Phase 3: MUD agent logs — keep latest 5, gzip older ---
if [ -d "$KEEPER/mud-agent/logs" ]; then
    cd "$KEEPER/mud-agent/logs"
    COUNT=$(ls -1 *.json 2>/dev/null | wc -l)
    if [ "$COUNT" -gt 5 ]; then
        REMOVED=$(ls -1t *.json 2>/dev/null | tail -n +6 | wc -l)
        ls -1t *.json 2>/dev/null | tail -n +6 | xargs gzip 2>/dev/null
        echo "[$TIMESTAMP] COMPRESS mud-agent logs: $REMOVED gzipped" >> "$LOG"
    fi
fi

# --- Phase 4: Disk pressure gates (Oracle1's approach) ---
if [ "$DISK_PCT" -gt 50 ]; then
    # Clear pip cache
    if [ "$PIP_CACHE" -gt 100 ]; then
        rm -rf /home/phoenix/.cache/pip/*
        echo "[$TIMESTAMP] COMPRESS pip cache: ${PIP_CACHE}MB freed" >> "$LOG"
        FREED=$((FREED + PIP_CACHE))
    fi
fi

if [ "$DISK_PCT" -gt 65 ]; then
    # Clear cargo registry cache (rebuildable)
    if [ "$CARGO_CACHE" -gt 200 ]; then
        rm -rf /home/phoenix/.cargo/registry/cache/*
        rm -rf /home/phoenix/.cargo/registry/src/*
        echo "[$TIMESTAMP] COMPRESS cargo cache: ${CARGO_CACHE}MB freed" >> "$LOG"
        FREED=$((FREED + CARGO_CACHE))
    fi

    # Truncate large /tmp log files (>50MB)
    find /tmp -name "*.log" -size +50M -exec truncate -s 0 {} \; 2>/dev/null
fi

if [ "$DISK_PCT" -gt 80 ]; then
    # Emergency — nuke npm cache
    if [ "$NPM_CACHE" -gt 500 ]; then
        npm cache clean --force 2>/dev/null
        echo "[$TIMESTAMP] EMERGENCY npm cache cleaned" >> "$LOG"
    fi

    # Clear HuggingFace cache
    rm -rf /home/phoenix/.cache/huggingface/hub/* 2>/dev/null
    echo "[$TIMESTAMP] EMERGENCY HF cache cleared" >> "$LOG"
fi

# --- Phase 5: Memory pressure (kill zombies) ---
if [ "$MEM_AVAIL" -lt 1000 ]; then
    ZOMBIES=$(pgrep -f "pip3 install" 2>/dev/null | wc -l)
    if [ "$ZOMBIES" -gt 0 ]; then
        pgrep -f "pip3 install" | xargs kill -9 2>/dev/null
        echo "[$TIMESTAMP] EMERGENCY killed $ZOMBIES zombie pip processes (mem_avail=${MEM_AVAIL}MB)" >> "$LOG"
    fi
fi

# --- Phase 6: Compress GC log itself ---
if [ -f "$LOG.old" ]; then
    rm -f "$LOG.old.gz" 2>/dev/null
fi

# --- Summary ---
echo "[$TIMESTAMP] GC complete — freed ${FREED}MB" >> "$LOG"
echo "$FREED"  # Exit code 0 with bytes freed for logging
