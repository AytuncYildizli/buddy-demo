#!/bin/bash
# Buddy demo starter — tek komut
set -e
cd "$(dirname "$0")"

echo "🧠 Buddy demo starter"
echo "===================="

# Deps
if ! python3 -c "import flask" 2>/dev/null; then
  echo "📦 Flask kuruluyor..."
  pip3 install --quiet flask
fi

# IP bul
IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "127.0.0.1")

echo ""
echo "✅ MBP IP: $IP"
echo "✅ Telefondan ac: http://$IP:8080"
echo "✅ Core2 icin SERVER_URL: http://$IP:8080"
echo ""
echo "🚀 Server basliyor (Ctrl+C ile durdur)..."
echo ""

python3 server.py
