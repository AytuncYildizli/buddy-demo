#!/usr/bin/env python3
"""
auth-halo.py — Poll auth status every 5 minutes and POST halo color to buddy server.

Checks:
  - GitHub CLI: gh auth status
  - gcloud:     gcloud auth list --format=json
  - Anthropic:  ANTHROPIC_API_KEY env var

Posts to http://172.20.10.2:8080/event with topic="auth".
"""

import os
import json
import subprocess
import time
import urllib.request
import urllib.error

BUDDY_URL = os.environ.get("BUDDY_URL", "http://172.20.10.2:8080")
POLL_INTERVAL = 300  # 5 minutes


def check_gh() -> tuple[str, str]:
    """Return (color, detail) for GitHub auth status."""
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        combined = (result.stdout + result.stderr).lower()
        if "logged in" in combined:
            return "green", "gh ✓"
        return "red", "gh not logged in"
    except FileNotFoundError:
        return "yellow", "gh not installed"
    except subprocess.TimeoutExpired:
        return "yellow", "gh timeout"
    except Exception as e:
        return "red", f"gh error: {e}"


def check_gcloud() -> tuple[str, str]:
    """Return (color, detail) for gcloud auth status."""
    try:
        result = subprocess.run(
            ["gcloud", "auth", "list", "--format=json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return "red", "gcloud not authed"
        accounts = json.loads(result.stdout or "[]")
        active = [a for a in accounts if a.get("status") == "ACTIVE"]
        if active:
            return "green", f"gcloud ✓ ({active[0].get('account', '?')})"
        if accounts:
            return "yellow", "gcloud: no active account"
        return "red", "gcloud: no accounts"
    except FileNotFoundError:
        return "yellow", "gcloud not installed"
    except subprocess.TimeoutExpired:
        return "yellow", "gcloud timeout"
    except (json.JSONDecodeError, Exception) as e:
        return "red", f"gcloud error: {e}"


def check_anthropic() -> tuple[str, str]:
    """Return (color, detail) for ANTHROPIC_API_KEY."""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key and len(key) > 10:
        return "green", "anthropic ✓"
    return "red", "ANTHROPIC_API_KEY missing"


COLOR_RANK = {"red": 2, "yellow": 1, "green": 0}


def worst_color(*colors: str) -> str:
    return max(colors, key=lambda c: COLOR_RANK.get(c, 0))


def color_to_emoji(color: str) -> str:
    return {"red": "🔴", "yellow": "🟡", "green": "🟢"}.get(color, "⚪")


def post_event(halo_color: str, message: str, emoji: str) -> None:
    payload = json.dumps({
        "topic": "auth",
        "message": message,
        "emoji": emoji,
        "halo_color": halo_color,
        "ttl_seconds": 600,
    }).encode()
    req = urllib.request.Request(
        f"{BUDDY_URL}/event",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            print(f"[auth-halo] posted: {halo_color} / {message} → {resp.status}")
    except urllib.error.URLError as e:
        print(f"[auth-halo] POST failed: {e}")


def run_once() -> None:
    gh_color,    gh_detail    = check_gh()
    gc_color,    gc_detail    = check_gcloud()
    anth_color,  anth_detail  = check_anthropic()

    worst = worst_color(gh_color, gc_color, anth_color)
    parts = [gh_detail, gc_detail, anth_detail]
    # Only include failing ones in message
    if worst == "green":
        summary = "all auth OK"
    else:
        failing = [d for d, c in zip(parts, [gh_color, gc_color, anth_color]) if c == "red"]
        warning = [d for d, c in zip(parts, [gh_color, gc_color, anth_color]) if c == "yellow"]
        summary = " | ".join(failing + warning)

    emoji = color_to_emoji(worst)
    print(f"[auth-halo] status: {worst} — {summary}")
    post_event(worst, f"auth: {summary}", emoji)


def main() -> None:
    print("[auth-halo] starting, polling every 5 minutes")
    while True:
        try:
            run_once()
        except Exception as e:
            print(f"[auth-halo] unexpected error: {e}")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
