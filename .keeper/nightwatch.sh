#!/bin/bash
# Nightwatch — sends a keep-going nudge via openclaw CLI
OPENCLAW=/home/phoenix/.nvm/versions/node/v22.22.2/bin/openclaw
if [ -x "$OPENCLAW" ]; then
    $OPENCLAW cron list 2>/dev/null | grep -q nightwatch && echo "nightwatch cron active"
fi
