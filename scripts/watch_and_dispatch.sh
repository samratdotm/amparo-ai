#!/usr/bin/env bash
# Watches for the amparo-demo room to appear (created by an incoming SIP call)
# and immediately dispatches agent-py to handle it.
#
# Usage: run this in a second terminal alongside `uv run python src/agent.py dev`
#
# Why this exists:
#   The SIP dispatch rule routes calls to room "amparo-demo" but the LiveKit
#   CLI/SDK doesn't expose the agentDispatches proto field, so the rule can't
#   automatically wire the room to our worker. This script bridges that gap by
#   running lk dispatch create the moment the room appears.

ROOM="amparo-demo"
AGENT="agent-py"
POLL_INTERVAL=1

echo "======================================="
echo "  Amparo AI -- Call Dispatcher"
echo "  Watching for room: $ROOM"
echo "  Agent: $AGENT"
echo "======================================="
echo ""

dispatched=""

while true; do
    if lk room list 2>/dev/null | grep -q "$ROOM"; then
        if [ -z "$dispatched" ]; then
            echo "[$(date '+%H:%M:%S')] Room '$ROOM' detected -- dispatching $AGENT"
            lk dispatch create --room "$ROOM" --agent-name "$AGENT" 2>&1 || true
            dispatched="yes"
            echo "[$(date '+%H:%M:%S')] Done -- call is live"
        fi
    else
        if [ -n "$dispatched" ]; then
            echo "[$(date '+%H:%M:%S')] Room gone -- ready for next call"
            dispatched=""
        fi
    fi
    sleep "$POLL_INTERVAL"
done
