#!/usr/bin/env python3
"""Buddy server v2.0 — Physical reactivity + breathing + events + MCP bridge support."""
import json
import time
import uuid
from collections import deque
from flask import Flask, jsonify, request, Response

app = Flask(__name__)

state = {
    "approved": 0, "denied": 0, "tokens": 0, "today": 0,
    "mood": 5, "energy": 5, "level": 0, "napped": "0h00m",
    "last_activity": time.time(), "last_feed": time.time(),
    "day_start": time.time(),
    
    # v1.0: event + breathing
    "last_event": "", "last_event_time": 0,
    "thinking": False,
    "burn_rate": 0,  # tokens/sec

    # v2.0: MCP bridge support
    "events": [],            # list of recent events (max 5)
    "halo_override": None,   # color string or None
    "halo_override_until": 0,
    "confirm_pending": {},   # {id: {action, hold_seconds, ttl, status, created_at, hold_start_time, hold_progress}}
    "ask_pending": {},       # {id: {question, choices, ttl, status, selected_index, created_at}}
    "tea_mode_until": 0,
}

# Token samples for burn rate calc (last 30s)
token_samples = deque(maxlen=60)  # (timestamp, cumulative_tokens)

def fire_event(name):
    state["last_event"] = name
    state["last_event_time"] = time.time()
    state["last_activity"] = time.time()

def recalc():
    now = time.time()
    hunger_elapsed = now - state["last_feed"]
    state["energy"] = max(0, 5 - int(hunger_elapsed / 30))
    
    total = state["approved"] + state["denied"]
    if total > 0:
        ratio = state["approved"] / total
        state["mood"] = max(1, min(5, int(ratio * 5)))
    else:
        state["mood"] = 5
    
    state["level"] = min(99, state["approved"] // 5)
    
    idle = int(now - state["last_activity"])
    state["napped"] = f"{idle//3600}h{(idle%3600)//60:02d}m"
    
    # Burn rate: tokens in last 10s
    cutoff = now - 10
    recent = [s for s in token_samples if s[0] >= cutoff]
    if len(recent) >= 2:
        dt = recent[-1][0] - recent[0][0]
        dtok = recent[-1][1] - recent[0][1]
        state["burn_rate"] = int(dtok / dt) if dt > 0 else 0
    else:
        state["burn_rate"] = 0
    
    # Clear stale event
    if now - state["last_event_time"] > 3:
        state["last_event"] = ""
    
    # Clear stale thinking
    if state["thinking"] and now - state["last_event_time"] > 15:
        state["thinking"] = False
    
    if now - state["day_start"] > 86400:
        state["today"] = 0
        state["day_start"] = now

@app.route("/state")
def get_state():
    recalc()
    now = time.time()

    # Compute active event (most recent non-expired)
    active_event = None
    for evt in reversed(state["events"]):
        if now < evt["expires_at"]:
            active_event = evt
            break

    # Compute active confirm (oldest pending non-expired)
    active_confirm = None
    for cid, entry in state["confirm_pending"].items():
        if entry["status"] == "pending" and now < entry["expires_at"]:
            active_confirm = {"id": cid, **entry}
            break

    # Compute active ask
    active_ask = None
    for aid, entry in state["ask_pending"].items():
        if entry["status"] == "pending" and now < entry["expires_at"]:
            active_ask = {"id": aid, **entry}
            break

    # Halo override
    halo_override = None
    if state["halo_override"] and now < state["halo_override_until"]:
        halo_override = state["halo_override"]

    # Tea active
    tea_active = now < state["tea_mode_until"]

    out = {k: v for k, v in state.items()
           if k not in (
               "last_activity", "last_feed", "day_start", "last_event_time",
               "halo_override_until", "confirm_pending", "ask_pending",
           )}
    out["tea_active"] = tea_active
    out["halo_override"] = halo_override
    out["active_event"] = active_event
    out["active_confirm"] = active_confirm
    out["active_ask"] = active_ask
    return jsonify(out)

@app.route("/approve", methods=["POST", "GET"])
def approve():
    state["approved"] += 1
    state["today"] += 1
    fire_event("approve")
    return jsonify({"ok": True, "approved": state["approved"]})

@app.route("/deny", methods=["POST", "GET"])
def deny():
    state["denied"] += 1
    state["today"] += 1
    fire_event("deny")
    return jsonify({"ok": True, "denied": state["denied"]})

@app.route("/tokens", methods=["POST"])
def tokens():
    data = request.get_json(silent=True) or {}
    if "set" in data:
        state["tokens"] = data["set"]
    else:
        state["tokens"] += data.get("count", 100)
    
    token_samples.append((time.time(), state["tokens"]))
    state["last_activity"] = time.time()
    return jsonify({"ok": True, "tokens": state["tokens"]})

@app.route("/session-start", methods=["POST", "GET"])
def session_start():
    fire_event("session_start")
    state["thinking"] = False
    return jsonify({"ok": True})

@app.route("/session-end", methods=["POST", "GET"])
def session_end():
    fire_event("session_end")
    state["thinking"] = False
    return jsonify({"ok": True})

@app.route("/thinking", methods=["POST", "GET"])
def thinking():
    state["thinking"] = True
    fire_event("thinking")
    return jsonify({"ok": True})

@app.route("/thinking-end", methods=["POST", "GET"])
def thinking_end():
    state["thinking"] = False
    fire_event("thinking_end")
    return jsonify({"ok": True})

@app.route("/feed", methods=["POST", "GET"])
def feed():
    state["last_feed"] = time.time()
    state["last_activity"] = time.time()
    return jsonify({"ok": True})

@app.route("/pet", methods=["POST", "GET"])
def pet():
    state["mood"] = min(5, state["mood"] + 1)
    state["last_activity"] = time.time()
    return jsonify({"ok": True})

@app.route("/reset", methods=["POST", "GET"])
def reset():
    state.update({
        "approved": 0, "denied": 0, "tokens": 0, "today": 0,
        "mood": 5, "energy": 5, "level": 0, "napped": "0h00m",
        "last_activity": time.time(), "last_feed": time.time(),
        "day_start": time.time(), "last_event": "",
        "thinking": False, "burn_rate": 0,
        "events": [], "halo_override": None, "halo_override_until": 0,
        "confirm_pending": {}, "ask_pending": {}, "tea_mode_until": 0,
    })
    token_samples.clear()
    return jsonify({"ok": True})


# =============================================================================
# v2.0 MCP Bridge Endpoints
# =============================================================================

@app.route("/event", methods=["POST"])
def post_event():
    """Push a transient notification/event. Used by MCP bridge and auth-halo."""
    data = request.get_json(silent=True) or {}
    topic       = data.get("topic", "")
    message     = data.get("message", "")
    emoji       = data.get("emoji", "📢")
    halo_color  = data.get("halo_color", "blue")
    ttl_seconds = int(data.get("ttl_seconds", 5))

    now = time.time()
    evt = {
        "topic": topic,
        "message": message,
        "emoji": emoji,
        "halo_color": halo_color,
        "ttl": ttl_seconds,
        "created_at": now,
        "expires_at": now + ttl_seconds,
    }
    state["events"].append(evt)
    # Keep only last 5
    state["events"] = state["events"][-5:]

    # Apply halo override
    state["halo_override"] = halo_color
    state["halo_override_until"] = now + ttl_seconds

    fire_event(f"event:{topic}")
    return jsonify({"ok": True})


@app.route("/confirm/request", methods=["POST"])
def confirm_request():
    """Request physical hold-to-confirm from user."""
    data = request.get_json(silent=True) or {}
    action       = data.get("action", "confirm")
    hold_seconds = float(data.get("hold_seconds", 2))
    ttl          = float(data.get("ttl", 15))

    request_id = str(uuid.uuid4())
    now = time.time()
    state["confirm_pending"][request_id] = {
        "action": action,
        "hold_seconds": hold_seconds,
        "ttl": ttl,
        "status": "pending",
        "created_at": now,
        "expires_at": now + ttl,
        "hold_start_time": None,
        "hold_accumulated": 0.0,
        "hold_progress": 0.0,
    }
    fire_event("confirm_request")
    return jsonify({"ok": True, "request_id": request_id})


@app.route("/confirm/status/<confirm_id>", methods=["GET"])
def confirm_status(confirm_id):
    """Poll confirm status. Also accepts ?id= query param for compat."""
    confirm_id = confirm_id or request.args.get("id", "")
    entry = state["confirm_pending"].get(confirm_id)
    if not entry:
        return jsonify({"error": "not found"}), 404

    now = time.time()
    # Auto-expire
    if entry["status"] == "pending" and now > entry["expires_at"]:
        entry["status"] = "timeout"

    # Update hold progress if currently holding
    if entry["hold_start_time"] is not None and entry["status"] == "pending":
        elapsed = now - entry["hold_start_time"] + entry["hold_accumulated"]
        progress = min(1.0, elapsed / entry["hold_seconds"])
        entry["hold_progress"] = progress
        if progress >= 1.0:
            entry["status"] = "confirmed"
            entry["hold_start_time"] = None

    return jsonify({
        "status": entry["status"],
        "state": entry["status"],  # alias for core2-bridge compat
        "hold_progress": entry["hold_progress"],
    })


@app.route("/confirm/ack/<confirm_id>", methods=["POST"])
def confirm_ack(confirm_id):
    """Firmware calls this on hold_start / hold_release / deny."""
    data = request.get_json(silent=True) or {}
    action = data.get("action", "")
    entry = state["confirm_pending"].get(confirm_id)
    if not entry:
        return jsonify({"error": "not found"}), 404

    now = time.time()
    if action == "hold_start":
        entry["hold_start_time"] = now
    elif action == "hold_release":
        if entry["hold_start_time"] is not None:
            entry["hold_accumulated"] += now - entry["hold_start_time"]
            entry["hold_start_time"] = None
        progress = min(1.0, entry["hold_accumulated"] / entry["hold_seconds"])
        entry["hold_progress"] = progress
        if progress >= 1.0:
            entry["status"] = "confirmed"
    elif action == "deny":
        entry["status"] = "denied"
        entry["hold_start_time"] = None

    return jsonify({"ok": True, "status": entry["status"]})


@app.route("/ask", methods=["POST"])
def post_ask():
    """Present a multiple-choice question to the user."""
    data = request.get_json(silent=True) or {}
    question = data.get("question", "")
    choices  = data.get("choices", [])
    ttl      = float(data.get("ttl", 30))

    ask_id = str(uuid.uuid4())
    now = time.time()
    state["ask_pending"][ask_id] = {
        "question": question,
        "choices": choices,
        "ttl": ttl,
        "status": "pending",
        "selected_index": None,
        "created_at": now,
        "expires_at": now + ttl,
    }
    fire_event("ask")
    return jsonify({"ok": True, "ask_id": ask_id})


@app.route("/ask/status/<ask_id>", methods=["GET"])
def ask_status(ask_id):
    """Poll ask status. Also accepts ?id= query param."""
    ask_id = ask_id or request.args.get("id", "")
    entry = state["ask_pending"].get(ask_id)
    if not entry:
        return jsonify({"error": "not found"}), 404

    now = time.time()
    if entry["status"] == "pending" and now > entry["expires_at"]:
        entry["status"] = "timeout"

    return jsonify({
        "status": entry["status"],
        "state": entry["status"],  # alias for core2-bridge compat
        "selected_index": entry["selected_index"],
        "answer_index": entry["selected_index"],  # alias
        "answer": (
            entry["choices"][entry["selected_index"]]
            if entry["selected_index"] is not None and entry["status"] == "answered"
            else None
        ),
    })


@app.route("/ask/answer/<ask_id>", methods=["POST"])
def ask_answer(ask_id):
    """Firmware calls this when user selects a choice."""
    data = request.get_json(silent=True) or {}
    selected_index = data.get("selected_index")
    entry = state["ask_pending"].get(ask_id)
    if not entry:
        return jsonify({"error": "not found"}), 404

    entry["selected_index"] = selected_index
    entry["status"] = "answered"
    return jsonify({"ok": True})


@app.route("/tea", methods=["POST"])
def tea():
    """Activate çay saati mode for 120 seconds."""
    state["tea_mode_until"] = time.time() + 120
    fire_event("tea")
    return jsonify({"ok": True})

@app.route("/")
def index():
    recalc()
    safe_state = {k: v for k, v in state.items()
                  if k not in ("last_activity", "last_feed", "day_start", "last_event_time")}
    html = f"""
    <!doctype html><html><head><meta charset="utf-8"><title>buddy v1.0</title>
    <meta http-equiv="refresh" content="2">
    <style>
    body{{font-family:-apple-system,monospace;background:#0a0a12;color:#FD7C20;padding:24px;max-width:720px;margin:auto}}
    h1{{color:#FD7C20}}
    pre{{background:#1a1a26;padding:14px;border-radius:8px;color:#eee;overflow:auto;font-size:12px}}
    button{{padding:14px 22px;margin:4px;font-size:14px;border-radius:8px;border:0;cursor:pointer;font-weight:600}}
    .ok{{background:#2a9d2a;color:white}} .bad{{background:#c33;color:white}}
    .warn{{background:#e69500;color:white}} .neu{{background:#444;color:white}}
    .blu{{background:#2c5f9e;color:white}} .red{{background:#5a1515;color:white}}
    </style></head><body>
    <h1>🐱 buddy v1.0 — I feel what Claude feels</h1>
    <pre>{json.dumps(safe_state, indent=2)}</pre>
    <div><b>state triggers:</b></div>
    <button class="ok" onclick="fetch('/approve',{{method:'POST'}})">✅ approve</button>
    <button class="bad" onclick="fetch('/deny',{{method:'POST'}})">❌ deny</button>
    <button class="warn" onclick="fetch('/feed',{{method:'POST'}})">🍔 feed</button>
    <button onclick="fetch('/pet',{{method:'POST'}})">💝 pet</button>
    <div style="margin-top:16px"><b>session events:</b></div>
    <button class="blu" onclick="fetch('/session-start',{{method:'POST'}})">🌅 session start</button>
    <button class="red" onclick="fetch('/session-end',{{method:'POST'}})">🌙 session end</button>
    <button class="warn" onclick="fetch('/thinking',{{method:'POST'}})">🤔 thinking</button>
    <button class="neu" onclick="fetch('/thinking-end',{{method:'POST'}})">✓ thinking end</button>
    <div style="margin-top:16px"><b>tokens (breathing rate):</b></div>
    <button onclick="fetch('/tokens',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{count:500}})}})">+500 tokens</button>
    <button onclick="fetch('/tokens',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{count:5000}})}})">+5000 tokens (HEAVY)</button>
    <div style="margin-top:16px"><b>danger zone:</b></div>
    <button class="neu" onclick="fetch('/reset',{{method:'POST'}})">🔄 reset</button>
    </body></html>
    """
    return Response(html, mimetype="text/html")

# Status route for GET /confirm/status (query-param compat for core2-bridge)
@app.route("/confirm/status", methods=["GET"])
def confirm_status_compat():
    confirm_id = request.args.get("id", "")
    return confirm_status(confirm_id)


@app.route("/ask/status", methods=["GET"])
def ask_status_compat():
    ask_id = request.args.get("id", "")
    return ask_status(ask_id)


if __name__ == "__main__":
    print("=" * 50)
    print("Buddy server v2.0 on 0.0.0.0:8080")
    print("Endpoints: /state /approve /deny /tokens")
    print("           /session-start /session-end /thinking /thinking-end")
    print("           /feed /pet /reset")
    print("           /event /confirm/request /confirm/status/<id> /confirm/ack/<id>")
    print("           /ask /ask/status/<id> /ask/answer/<id> /tea")
    print("=" * 50)
    app.run(host="0.0.0.0", port=8080, debug=False)
