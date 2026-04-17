#!/usr/bin/env bash
# Claude Code hook for Buddy companion
# Usage: put this path in ~/.claude/settings.json under hooks.PostToolUse
#
# Env vars Claude Code provides:
#   CLAUDE_TOOL_NAME     — tool that was used
#   CLAUDE_TOOL_APPROVED — "true" or "false" (if approval prompt was shown)
#   CLAUDE_SESSION_TOKENS — cumulative tokens for current session (if available)

BUDDY_URL="${BUDDY_URL:-http://172.20.10.2:8080}"

# Approved → POST /approve
# Denied  → POST /deny
if [ "$CLAUDE_TOOL_APPROVED" = "true" ]; then
  curl -s -m 2 -X POST "$BUDDY_URL/approve" > /dev/null 2>&1 &
elif [ "$CLAUDE_TOOL_APPROVED" = "false" ]; then
  curl -s -m 2 -X POST "$BUDDY_URL/deny" > /dev/null 2>&1 &
fi

# Token count
if [ -n "$CLAUDE_SESSION_TOKENS" ]; then
  curl -s -m 2 -X POST "$BUDDY_URL/tokens" \
    -H "Content-Type: application/json" \
    -d "{\"count\": $CLAUDE_SESSION_TOKENS}" > /dev/null 2>&1 &
fi

exit 0
