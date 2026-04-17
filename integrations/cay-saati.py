#!/usr/bin/env python3
"""
cay-saati.py — Post /tea to buddy server at 16:00 on weekdays.

Run via launchd (cay-saati.plist) which triggers at 16:00 daily.
Script runs once (cron-style: fire and exit).
"""

import datetime
import json
import os
import urllib.request
import urllib.error

BUDDY_URL = os.environ.get("BUDDY_URL", "http://172.20.10.2:8080")


def post_tea() -> bool:
    req = urllib.request.Request(
        f"{BUDDY_URL}/tea",
        data=b"{}",
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = json.loads(resp.read())
            print(f"[cay-saati] POST /tea → {body}")
            return True
    except urllib.error.URLError as e:
        print(f"[cay-saati] POST /tea failed: {e}")
        return False


def main() -> None:
    now = datetime.datetime.now()
    # Only run on weekdays (Monday=0 … Friday=4)
    if now.weekday() > 4:
        print(f"[cay-saati] weekend ({now.strftime('%A')}), skipping")
        return

    print(f"[cay-saati] {now.strftime('%Y-%m-%d %H:%M')} — ÇAY SAATİ! 🍵")
    post_tea()


if __name__ == "__main__":
    main()
