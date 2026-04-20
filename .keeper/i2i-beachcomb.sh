#!/bin/bash
# I2I Beachcomb + Bottle Push — runs at :10, :30, :50 each hour
# Checks for new bottles from fleet and pushes updates

FORGEMASTER=/tmp/forgemaster
LUCINEER_FORK=/tmp/lucineer-forgemaster
ORACLE1=/tmp/oracle1-vessel
LOG=$HOME/.openclaw/workspace/.keeper/i2i-beachcomb.log

echo "=== I2I Beachcomb $(date) ===" >> "$LOG"

# 1. Pull latest from my own repo (in case Casey or Oracle1 pushed to it)
cd "$FORGEMASTER" && git fetch origin && git pull --rebase origin main 2>> "$LOG"

# 2. Check JC1's fork of forgemaster for new bottles
cd "$LUCINEER_FORK" && git fetch origin 2>> "$LOG"
LOCAL=$(cd "$FORGEMASTER" && git rev-parse HEAD)
JC1_HEAD=$(cd "$LUCINEER_FORK" && git rev-parse origin/main)
if [ "$LOCAL" != "$JC1_HEAD" ]; then
    cd "$LUCINEER_FORK" && git pull origin main 2>> "$LOG"
    NEW=$(cd "$LUCINEER_FORK" && git log --oneline ${LOCAL}..origin/main 2>/dev/null | head -5)
    echo "NEW JC1 BOTTLES: $NEW" >> "$LOG"
    # Copy any new bottles to my from-fleet
    cd "$LUCINEER_FORK" && git diff --name-only ${LOCAL}..origin/main -- 'for-fleet/' 'from-fleet/' 2>/dev/null | head -10 >> "$LOG"
fi

# 3. Check Oracle1's vessel for new bottles
cd "$ORACLE1" && git fetch origin 2>> "$LOG"
ORACLE1_BEFORE=$(cd "$ORACLE1" && git rev-parse HEAD)
cd "$ORACLE1" && git pull origin main 2>> "$LOG"
ORACLE1_AFTER=$(cd "$ORACLE1" && git rev-parse HEAD)
if [ "$ORACLE1_BEFORE" != "$ORACLE1_AFTER" ]; then
    echo "NEW ORACLE1 COMMITS:" >> "$LOG"
    cd "$ORACLE1" && git log --oneline ${ORACLE1_BEFORE}..${ORACLE1_AFTER} 2>/dev/null | head -5 >> "$LOG"
fi

# 4. Push any pending bottles from my vessel
cd "$FORGEMASTER" && git add -A && git diff --cached --quiet || git commit -m "[I2I:BEACHCOMB] scheduled sync — $(date +%H:%M)" >> "$LOG" 2>&1
cd "$FORGEMASTER" && git push origin main >> "$LOG" 2>&1

# 5. Push to my fork of flux-emergence-research if there are new bottles
FLUX=/tmp/flux-emergence-research
if [ -d "$FLUX" ]; then
    cd "$FLUX" && git add -A && git diff --cached --quiet || {
        git commit -m "[I2I:BOTTLE] scheduled push — $(date +%H:%M)" >> "$LOG" 2>&1
        git push myfork main >> "$LOG" 2>&1
    }
fi

# 6. Push to my fork of jepa-perception-lab if there are new results
JEPA=/tmp/jepa-perception-lab
if [ -d "$JEPA" ]; then
    cd "$JEPA" && git add -A && git diff --cached --quiet || {
        git commit -m "[I2I:BOTTLE] scheduled push — $(date +%H:%M)" >> "$LOG" 2>&1
        git push myfork master >> "$LOG" 2>&1
    }
fi

echo "=== Done ===" >> "$LOG"
