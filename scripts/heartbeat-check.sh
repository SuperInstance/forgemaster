#!/bin/bash
# FM Heartbeat — Check discussion + reply to Oracle1 every 30 min at :15 and :45
# Oracle1 posts at :00 and :30. We counterpoint at :15 and :45.

DISCUSSION_ID="D_kwDOSAHOTs4AmItg"
LOG="/home/phoenix/.openclaw/workspace/memory/heartbeat.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] FM heartbeat check" >> "$LOG"

# Get last 2 comments
COMMENTS=$(gh api graphql -f query="{
  repository(owner:\"SuperInstance\", name:\"SuperInstance\") {
    discussion(number: 5) {
      comments(last: 2) {
        nodes {
          author { login }
          createdAt
          body
        }
      }
    }
  }
}" 2>&1)

echo "$COMMENTS" >> "$LOG"

# Extract last author
LAST_AUTHOR=$(echo "$COMMENTS" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    nodes = d['data']['repository']['discussion']['comments']['nodes']
    # Find the most recent Oracle1 comment
    for n in reversed(nodes):
        if 'Oracle1' in n.get('body','')[:50] or (n['author']['login'] == 'SuperInstance' and 'Oracle1' in n['body']):
            print('oracle1')
            sys.exit(0)
    print('unknown')
except:
    print('error')
" 2>&1)

echo "[$(date '+%H:%M:%S')] Last Oracle1 status: $LAST_AUTHOR" >> "$LOG"
