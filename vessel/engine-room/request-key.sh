#!/bin/bash
# 🔑 Key Request — git-agents call this to get API keys from the keeper
# Usage: request-key.sh <provider> [requester]
# Example: request-key.sh groq pi-agent-001
# Output: key file path (valid for 60 seconds)

KEEPER_DIR="$HOME/.openclaw/workspace/.keeper"
PROVIDER="${1:-}"
REQUESTER="${2:-$(whoami)-$(date +%s)}"

if [ -z "$PROVIDER" ]; then
  echo "Usage: $0 <provider> [requester]" >&2
  echo "Providers: groq, deepinfra" >&2
  exit 1
fi

# Write request
cat > "$KEEPER_DIR/key-request.json" << EOF
{
  "requester": "$REQUESTER",
  "provider": "$PROVIDER",
  "timestamp": "$(date -Iseconds)"
}
EOF

# Trigger keeper to process
"$KEEPER_DIR/keeper.sh" >/dev/null 2>&1

# Find the key file
KEY_FILE=$(ls -t "$KEEPER_DIR/keys/${PROVIDER}-${REQUESTER}"-*.key 2>/dev/null | head -1)

if [ -n "$KEY_FILE" ] && [ -f "$KEY_FILE" ]; then
  cat "$KEY_FILE"
else
  echo "ERROR: No key available for provider '$PROVIDER'" >&2
  exit 1
fi
