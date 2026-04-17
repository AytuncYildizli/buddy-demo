#!/usr/bin/env python3
"""
core2-bridge: MCP server that exposes Core2 Buddy as an interactive tool.

Tools:
  - core2_notify(topic, message, emoji, halo_color) — push a transient notification
  - core2_confirm(action, hold_seconds, ttl) — block until screen-hold or timeout
  - core2_ask(question, choices) — show multiple-choice, return user selection

Requires the buddy server (server.py) to be running with the extended endpoints:
  /event, /confirm/request, /confirm/status, /confirm/ack, /ask, /ask/status, /ask/answer
"""

import os
import time
import requests
from typing import Optional, List
from mcp.server.fastmcp import FastMCP

# ---- Config ----
BUDDY_URL = os.environ.get("BUDDY_URL", "http://172.20.10.2:8080")
POLL_INTERVAL = 0.5  # seconds between status polls

mcp = FastMCP("core2-bridge")


def _post(path: str, data: dict, timeout: int = 5) -> dict:
    """POST to buddy server, return JSON response or raise."""
    resp = requests.post(f"{BUDDY_URL}{path}", json=data, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _get(path: str, timeout: int = 5) -> dict:
    """GET from buddy server, return JSON response or raise."""
    resp = requests.get(f"{BUDDY_URL}{path}", timeout=timeout)
    resp.raise_for_status()
    return resp.json()


# ---- Tool: core2_notify ----
@mcp.tool()
def core2_notify(
    topic: str,
    message: str,
    emoji: str = "📢",
    halo_color: str = "blue",
) -> str:
    """
    Push a transient notification to the Core2 Buddy display.

    The Buddy screen briefly shows the notification and sets the halo
    to the requested color for ~5 seconds, then returns to normal.

    Args:
        topic:      Short category label (e.g. "deploy", "ci", "alert").
        message:    Notification body text.
        emoji:      Optional leading emoji shown on device (default: 📢).
        halo_color: Halo ring color — one of: blue, yellow, green, red.

    Returns:
        Confirmation string or error description.
    """
    valid_colors = {"blue", "yellow", "green", "red"}
    if halo_color not in valid_colors:
        halo_color = "blue"

    try:
        result = _post("/event", {
            "topic": topic,
            "message": message,
            "emoji": emoji,
            "halo_color": halo_color,
        })
        return f"Notification sent — topic={topic!r}, color={halo_color}, ack={result.get('ok')}"
    except Exception as e:
        return f"Error sending notification: {e}"


# ---- Tool: core2_confirm ----
@mcp.tool()
def core2_confirm(
    action: str,
    hold_seconds: int = 2,
    ttl: int = 15,
) -> str:
    """
    Request physical confirmation from the user by holding the Core2 screen.

    Buddy displays a confirmation prompt. The user must press-and-hold the
    touchscreen for `hold_seconds` seconds to confirm, or the request times
    out after `ttl` seconds.

    Args:
        action:       Short description of what is being confirmed
                      (e.g. "delete production DB", "deploy to mainnet").
        hold_seconds: How many continuous seconds the screen must be held (default 2).
        ttl:          Timeout in seconds if no confirmation arrives (default 15).

    Returns:
        "confirmed" if the user held the screen, "timeout" otherwise.
    """
    try:
        # Send the confirm request to the server
        result = _post("/confirm/request", {
            "action": action,
            "hold_seconds": hold_seconds,
            "ttl": ttl,
        })
        request_id = result.get("request_id")
        if not request_id:
            return f"Error: server did not return request_id — {result}"
    except Exception as e:
        return f"Error requesting confirmation: {e}"

    # Poll for result
    deadline = time.time() + ttl + 2  # extra 2s grace
    while time.time() < deadline:
        time.sleep(POLL_INTERVAL)
        try:
            status = _get(f"/confirm/status?id={request_id}")
            state = status.get("state")
            if state == "confirmed":
                return "confirmed"
            if state == "timeout" or state == "expired":
                return "timeout"
            # state == "pending" → keep polling
        except Exception:
            pass  # transient network error, keep trying

    return "timeout"


# ---- Tool: core2_ask ----
@mcp.tool()
def core2_ask(
    question: str,
    choices: List[str],
) -> str:
    """
    Show a multiple-choice question on the Core2 display and wait for
    the user to select one of the options by tapping the screen.

    Args:
        question: The question to display (keep it short, ~40 chars).
        choices:  List of 2–4 answer options. Each is shown as a button
                  on the Core2 touchscreen.

    Returns:
        The text of the selected choice, or "timeout" if no answer in 30s.
    """
    if not choices:
        return "Error: choices list is empty"
    if len(choices) > 4:
        choices = choices[:4]  # Core2 screen fits max 4 choices

    TTL = 30  # seconds to wait for answer

    try:
        result = _post("/ask", {
            "question": question,
            "choices": choices,
            "ttl": TTL,
        })
        ask_id = result.get("ask_id")
        if not ask_id:
            return f"Error: server did not return ask_id — {result}"
    except Exception as e:
        return f"Error sending question: {e}"

    # Poll for answer
    deadline = time.time() + TTL + 2
    while time.time() < deadline:
        time.sleep(POLL_INTERVAL)
        try:
            status = _get(f"/ask/status?id={ask_id}")
            state = status.get("state")
            if state == "answered":
                answer_idx = status.get("answer_index", 0)
                if 0 <= answer_idx < len(choices):
                    return choices[answer_idx]
                return status.get("answer", "unknown")
            if state == "timeout" or state == "expired":
                return "timeout"
        except Exception:
            pass

    return "timeout"


if __name__ == "__main__":
    mcp.run()
