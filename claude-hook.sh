#!/usr/bin/env bash
# Claude Code hook — wires tool-use events to Buddy v1.0
# Place in ~/.claude/settings.json under hooks.{PreToolUse,PostToolUse,Stop}

BUDDY_URL="${BUDDY_URL:-http://172.20.10.2:8080}"

# Read JSON from stdin (Claude Code hooks receive JSON via stdin)
INPUT=$(cat 2>/dev/null || echo '{}')
EVENT=$(echo "$INPUT" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('hook_event_name',''))" 2>/dev/null)
TOOL=$(echo "$INPUT" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('tool_name',''))" 2>/dev/null)
DECISION=$(echo "$INPUT" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('permission_decision',d.get('approved','')))" 2>/dev/null)
TOKENS_IN=$(echo "$INPUT" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('tokens',{}).get('input',0))" 2>/dev/null)
TOKENS_OUT=$(echo "$INPUT" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('tokens',{}).get('output',0))" 2>/dev/null)

post() {
  curl -s -m 2 -X POST "$BUDDY_URL$1" > /dev/null 2>&1 &
}
post_json() {
  curl -s -m 2 -X POST -H "Content-Type: application/json" -d "$2" "$BUDDY_URL$1" > /dev/null 2>&1 &
}

case "$EVENT" in
  "SessionStart")
    post "/session-start"
    ;;
  "Stop"|"SessionEnd")
    post "/session-end"
    ;;
  "PreToolUse")
    post "/thinking"
    ;;
  "PostToolUse")
    post "/thinking-end"
    if [ "$DECISION" = "allow" ] || [ "$DECISION" = "true" ] || [ -z "$DECISION" ]; then
      post "/approve"
    else
      post "/deny"
    fi
    # Token usage
    TOTAL=$((${TOKENS_IN:-0} + ${TOKENS_OUT:-0}))
    if [ "$TOTAL" -gt 0 ]; then
      post_json "/tokens" "{\"count\":$TOTAL}"
    fi
    ;;
esac

# Always exit 0 so we never block Claude Code
exit 0
