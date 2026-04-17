#!/usr/bin/env python3
"""Buddy companion server for Core2 demo.

MBP'de:
    pip3 install flask
    python3 server.py

Sonra telefondan veya Core2'den <MBP_IP>:8080 acilir.
"""
import json
import time
from flask import Flask, jsonify, request, Response

app = Flask(__name__)

state = {
    "approved": 0,
    "denied": 0,
    "tokens": 0,
    "mood": 5,
    "energy": 5,
    "level": 0,
    "napped": "0h00m",
    "last_activity": time.time(),
    "last_feed": time.time(),
}

def recalc():
    now = time.time()
    # Energy: her 30sn yemek yemezse 1 dusur
    hunger_elapsed = now - state["last_feed"]
    state["energy"] = max(0, 5 - int(hunger_elapsed / 30))

    # Mood: approved/denied oranindan
    total = state["approved"] + state["denied"]
    if total > 0:
        ratio = state["approved"] / total
        state["mood"] = max(1, min(5, int(ratio * 5)))
    else:
        state["mood"] = 5

    # Level: her 5 approved = 1 level
    state["level"] = state["approved"] // 5

    # Napped
    idle = int(now - state["last_activity"])
    state["napped"] = f"{idle//3600}h{(idle%3600)//60:02d}m"

@app.route("/state")
def get_state():
    recalc()
    out = {k: v for k, v in state.items() if k not in ("last_activity", "last_feed")}
    return jsonify(out)

@app.route("/approve", methods=["POST", "GET"])
def approve():
    state["approved"] += 1
    state["last_activity"] = time.time()
    return jsonify({"ok": True, "approved": state["approved"]})

@app.route("/deny", methods=["POST", "GET"])
def deny():
    state["denied"] += 1
    state["last_activity"] = time.time()
    return jsonify({"ok": True, "denied": state["denied"]})

@app.route("/tokens", methods=["POST"])
def tokens():
    data = request.get_json(silent=True) or {}
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
        "approved": 0, "denied": 0, "tokens": 0,
        "mood": 5, "energy": 5, "level": 0,
        "napped": "0h00m",
        "last_activity": time.time(),
        "last_feed": time.time(),
    })
    return jsonify({"ok": True})

@app.route("/")
def index():
    recalc()
    html = f"""
    <!doctype html>
    <html><head><meta charset="utf-8"><title>Buddy Control</title>
    <style>
    body {{ font-family: -apple-system; background:#111; color:#eee; padding:20px; }}
    button {{ padding:14px 22px; margin:6px; font-size:16px; border-radius:10px; border:0; cursor:pointer; }}
    .ok{{background:#2a9d2a;color:white}} .bad{{background:#c33;color:white}}
    .warn{{background:#e69500;color:white}} pre{{background:#222;padding:12px;border-radius:8px}}
    </style></head><body>
    <h1>🐱 Buddy Control Panel</h1>
    <pre>{json.dumps({k:v for k,v in state.items() if k not in ('last_activity','last_feed')}, indent=2)}</pre>
    <button class="ok" onclick="fetch('/approve',{{method:'POST'}}).then(()=>location.reload())">✅ Approve</button>
    <button class="bad" onclick="fetch('/deny',{{method:'POST'}}).then(()=>location.reload())">❌ Deny</button>
    <button class="warn" onclick="fetch('/feed',{{method:'POST'}}).then(()=>location.reload())">🍔 Feed</button>
    <button onclick="fetch('/pet',{{method:'POST'}}).then(()=>location.reload())">💝 Pet</button>
    <button onclick="fetch('/reset',{{method:'POST'}}).then(()=>location.reload())">🔄 Reset</button>
    <p><small>Auto refresh every 2s...</small></p>
    <script>setTimeout(()=>location.reload(), 2000)</script>
    </body></html>
    """
    return Response(html, mimetype="text/html")

if __name__ == "__main__":
    print("=" * 50)
    print("Buddy server starting on 0.0.0.0:8080")
    print("Telefondan: http://<MBP_IP>:8080")
    print("IP bulmak icin: ifconfig | grep 'inet 192'")
    print("=" * 50)
    app.run(host="0.0.0.0", port=8080, debug=False)
