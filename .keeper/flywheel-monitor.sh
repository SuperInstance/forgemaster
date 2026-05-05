#!/bin/bash
# Flywheel Monitor — check status and log progress
# Run manually or on cron to monitor the autonomous research loop

FLYWHEEL_BASE=/tmp/forgemaster/flywheel
STATE=$FLYWHEEL_BASE/state.json
LOG=$FLYWHEEL_BASE/log.json

echo "=== FLYWHEEL STATUS $(date) ==="

if [ -f "$STATE" ]; then
    python3 -c "
import json
s = json.load(open('$STATE'))
print(f\"Completed: {s.get('completed', 0)} experiments\")
print(f\"Questions remaining: {s.get('questions_remaining', 0)}\")
print(f\"Last update: {s.get('last_update', 'never')}\")
"
else
    echo "No state file — flywheel not started yet"
fi

if [ -f "$LOG" ]; then
    python3 -c "
import json
log = json.load(open('$LOG'))
supported = sum(1 for l in log if l.get('verdict') == 'SUPPORTED')
falsified = sum(1 for l in log if l.get('verdict') == 'FALSIFIED')
inconclusive = len(log) - supported - falsified
print(f'Supported: {supported} | Falsified: {falsified} | Inconclusive: {inconclusive}')
print()
for l in log[-3:]:
    print(f\"  {l.get('verdict','?')}: {l.get('question','?')[:80]}\")
    if l.get('constraint'):
        print(f\"    → {l['constraint'][:100]}\")
"
fi

echo "=== END ==="
