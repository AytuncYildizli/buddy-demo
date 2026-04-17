# core2-bridge — MCP server for Core2 Buddy

Exposes your physical M5Stack Core2 Buddy as an MCP toolset.
Claude (or any MCP-compatible agent) can now send notifications,
request physical confirmation, and ask the user multiple-choice questions —
all through the Core2 screen.

## Tools

### `core2_notify(topic, message, emoji, halo_color)`
Push a transient notification to the Buddy display.
Halo changes color briefly to: `blue` | `yellow` | `green` | `red`.

```python
core2_notify("deploy", "Pushed to prod 🚀", "🚀", "green")
```

### `core2_confirm(action, hold_seconds=2, ttl=15)`
Ask the user to physically hold the Core2 screen to confirm an action.
Returns `"confirmed"` or `"timeout"`.

```python
result = core2_confirm("drop production table", hold_seconds=3, ttl=20)
```

### `core2_ask(question, choices)`
Show a multiple-choice question on the Core2 screen.
Up to 4 choices; returns the chosen option text or `"timeout"`.

```python
answer = core2_ask("Deploy to which env?", ["staging", "prod", "cancel"])
```

---

## Installation

```bash
cd core2-bridge
pip install -r requirements.txt
```

Set the server URL if not using the default:
```bash
export BUDDY_URL=http://172.20.10.2:8080
```

## Running

```bash
python server.py
```

Or via MCP CLI:
```bash
mcp run server.py
```

---

## Registering in Claude Code (`~/.claude/mcp.json`)

Add the following entry to register core2-bridge as a local MCP server:

```json
{
  "mcpServers": {
    "core2-bridge": {
      "command": "python",
      "args": ["/path/to/buddy-demo/core2-bridge/server.py"],
      "env": {
        "BUDDY_URL": "http://172.20.10.2:8080"
      }
    }
  }
}
```

Replace `/path/to/buddy-demo` with your actual checkout path,
e.g. `/Users/aytunc/clawd/projects/buddy-demo`.

After saving, restart Claude Code. You should see `core2-bridge` in the
MCP tools list.

### Example: using uv (recommended for isolated env)

```json
{
  "mcpServers": {
    "core2-bridge": {
      "command": "uv",
      "args": [
        "run",
        "--with", "mcp[cli]",
        "--with", "requests",
        "/path/to/buddy-demo/core2-bridge/server.py"
      ],
      "env": {
        "BUDDY_URL": "http://172.20.10.2:8080"
      }
    }
  }
}
```

---

## Server endpoints required

The buddy `server.py` must be running with these additional endpoints
(added in the companion `server.py` update):

| Method | Path | Description |
|--------|------|-------------|
| POST | `/event` | Transient notification |
| POST | `/confirm/request` | Request physical hold-confirm |
| GET  | `/confirm/status?id=` | Poll confirm state |
| POST | `/confirm/ack` | Device ACKs confirmed |
| POST | `/ask` | Post multiple-choice question |
| GET  | `/ask/status?id=` | Poll answer state |
| POST | `/ask/answer` | Device posts selected answer |
