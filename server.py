#!/usr/bin/env python3
"""Buddy companion server v0.3 — Core2 + Claude Code hook."""
import json
import time
from flask import Flask, jsonify, request, Response

app = Flask(__name__)

state = {
    "approved": 0,
    "denied": 0,
    "tokens": 0,
    "today": 0,
    "mood": 5,
    "energy": 5,
    "level": 0,
    "napped": "0h00m",
    "last_activity": time.time(),
    "last_feed": time.time(),
    "day_start": time.time(),
}

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
    
    state["level"] = state["approved"] // 5
    
    idle = int(now - state["last_activity"])
    state["napped"] = f"{idle//3600}h{(idle%3600)//60:02d}m"
    
    # Reset 'today' at midnight-ish (every 24h)
    if now - state["day_start"] > 86400:
        state["today"] = 0
        state["day_start"] = now

@app.route("/state")
def get_state():
    recalc()
    return jsonify({k: v for k, v in state.items() 
                    if k not in ("last_activity", "last_feed", "day_start")})

@app.route("/approve", methods=["POST", "GET"])
def approve():
    state["approved"] += 1
    state["today"] += 1
    state["last_activity"] = time.time()
    return jsonify({"ok": True, "approved": state["approved"]})

@app.route("/deny", methods=["POST", "GET"])
def deny():
    state["denied"] += 1
    state["today"] += 1
    state["last_activity"] = time.time()
    return jsonify({"ok": True, "denied": state["denied"]})

@app.route("/tokens", methods=["POST"])
def tokens():
    data = request.get_json(silent=True) or {}
    # Accept absolute count or delta
    if "set" in data:
        state["tokens"] = data["set"]
    else:
        state["tokens"] += data.get("count", 100)
    state["last_activity"] = time.time()
    return jsonify({"ok": True, "tokens": state["tokens"]})

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

@app.route("/sleep", methods=["POST", "GET"])
def sleep():
    state["energy"] = 5
    state["last_feed"] = time.time()
    return jsonify({"ok": True})

@app.route("/reset", methods=["POST", "GET"])
def reset():
    state.update({
        "approved": 0, "denied": 0, "tokens": 0, "today": 0,
        "mood": 5, "energy": 5, "level": 0, "napped": "0h00m",
        "last_activity": time.time(), "last_feed": time.time(),
        "day_start": time.time(),
    })
    return jsonify({"ok": True})

@app.route("/")
def index():
    recalc()
    safe_state = {k: v for k, v in state.items() 
                  if k not in ("last_activity", "last_feed", "day_start")}
    html = f"""
    <!doctype html><html><head><meta charset="utf-8"><title>Buddy</title>
    <meta http-equiv="refresh" content="2">
    <style>
    body{{font-family:-apple-system,monospace;background:#0f0f14;color:#FD7C20;padding:24px;max-width:600px;margin:auto}}
    h1{{color:#FD7C20}}
    pre{{background:#1a1a22;padding:14px;border-radius:8px;color:#eee;overflow:auto}}
    button{{padding:14px 22px;margin:6px;font-size:16px;border-radius:10px;border:0;cursor:pointer;font-weight:600}}
    .ok{{background:#2a9d2a;color:white}} .bad{{background:#c33;color:white}}
    .warn{{background:#e69500;color:white}} .neu{{background:#444;color:white}}
    </style></head><body>
    <h1>🐱 buddy control</h1>
    <pre>{json.dumps(safe_state, indent=2)}</pre>
    <button class="ok" onclick="fetch('/approve',{{method:'POST'}}).then(()=>location.reload())">✅ approve</button>
    <button class="bad" onclick="fetch('/deny',{{method:'POST'}}).then(()=>location.reload())">❌ deny</button>
    <button class="warn" onclick="fetch('/feed',{{method:'POST'}}).then(()=>location.reload())">🍔 feed</button>
    <button onclick="fetch('/pet',{{method:'POST'}}).then(()=>location.reload())">💝 pet</button>
    <button class="neu" onclick="fetch('/reset',{{method:'POST'}}).then(()=>location.reload())">🔄 reset</button>
    </body></html>
    """
    return Response(html, mimetype="text/html")

if __name__ == "__main__":
    print("=" * 50)
    print("Buddy server v0.3 on 0.0.0.0:8080")
    print("=" * 50)
    app.run(host="0.0.0.0", port=8080, debug=False)
