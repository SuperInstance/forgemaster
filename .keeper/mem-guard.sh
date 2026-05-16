#!/bin/bash
# mem-guard.sh — Memory pressure emergency response
MEM_AVAIL=$(free -m | awk '/Mem:/ {print $7}')
if [ "$MEM_AVAIL" -lt 800 ]; then
    pgrep -f "pip3 install" | xargs kill -9 2>/dev/null
    pgrep -f "pip install" | xargs kill -9 2>/dev/null
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] MEMGUARD killed pip zombies (avail=${MEM_AVAIL}MB)" >> /home/phoenix/.openclaw/workspace/.keeper/mem-guard.log
fi
