#!/usr/bin/env python3
"""Buddy server v1.0 — Physical reactivity + breathing-from-tokens + events."""
import json
import time
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
    out = {k: v for k, v in state.items()
           if k not in ("last_activity", "last_feed", "day_start", "last_event_time")}
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
    })
    token_samples.clear()
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

if __name__ == "__main__":
    print("=" * 50)
    print("Buddy server v1.0 on 0.0.0.0:8080")
    print("Endpoints: /state /approve /deny /tokens")
    print("           /session-start /session-end /thinking /thinking-end")
    print("           /feed /pet /reset")
    print("=" * 50)
    app.run(host="0.0.0.0", port=8080, debug=False)
