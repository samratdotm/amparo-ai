#!/usr/bin/env bash
# Run this once before each demo call (or between calls).
# Creates amparo-demo room and pre-stages agent-py so the caller
# hears audio instantly with no watch-script latency.

set -euo pipefail

ROOM="amparo-demo"
AGENT="agent-py"

echo "Setting up for next call..."

# Clean up any stale room
lk room delete "$ROOM" 2>/dev/null || true

# Create fresh room
lk room create "$ROOM" 2>&1 | tail -1

# Dispatch agent into the room — it will wait silently for the caller
lk dispatch create --room "$ROOM" --agent-name "$AGENT" 2>&1

echo ""
echo "Done. Agent is waiting in '$ROOM'."
echo "Call +1 (415) 417-6002 — the agent will answer instantly."
