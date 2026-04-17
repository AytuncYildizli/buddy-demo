#!/usr/bin/env bash
# Buddy demo bootstrap — tek komut kurulum
# curl -fsSL https://raw.githubusercontent.com/AytuncYildizli/buddy-demo/main/bootstrap.sh | bash
set -e

echo "🧠 Buddy demo bootstrap"
echo "======================="

ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
  URL="https://downloads.arduino.cc/arduino-cli/arduino-cli_latest_macOS_ARM64.tar.gz"
else
  URL="https://downloads.arduino.cc/arduino-cli/arduino-cli_latest_macOS_64bit.tar.gz"
fi
echo "Mimari: $ARCH"

echo "📥 arduino-cli indiriliyor..."
mkdir -p "$HOME/bin"
curl -fsSL -o /tmp/arduino-cli.tar.gz "$URL"
tar -xzf /tmp/arduino-cli.tar.gz -C "$HOME/bin" arduino-cli
export PATH="$HOME/bin:$PATH"

if ! grep -q 'HOME/bin:$PATH' "$HOME/.zshrc" 2>/dev/null; then
  echo 'export PATH="$HOME/bin:$PATH"' >> "$HOME/.zshrc"
fi

echo "📂 Repo klonlaniyor..."
if [ ! -d "$HOME/buddy-demo" ]; then
  git clone https://github.com/AytuncYildizli/buddy-demo.git "$HOME/buddy-demo"
else
  echo "Repo zaten var, guncelleniyor..."
  (cd "$HOME/buddy-demo" && git pull --ff-only) || true
fi
cd "$HOME/buddy-demo"

echo "⚙️  ESP32 board desteği kuruluyor (3-4 dk sürer, ~200MB)..."
arduino-cli config init --overwrite >/dev/null
arduino-cli config add board_manager.additional_urls https://espressif.github.io/arduino-esp32/package_esp32_index.json
arduino-cli core update-index
arduino-cli core install esp32:esp32

echo "📚 Library'ler kuruluyor..."
arduino-cli lib install "M5Unified"
arduino-cli lib install "ArduinoJson"

echo ""
echo "🔌 USB port kontrolü..."
arduino-cli board list

echo ""
echo "✅ HAZIR!"
echo ""
echo "Sonraki adım: ~/buddy-demo klasörüne gir, Core2Buddy.ino içindeki"
echo "WIFI_SSID / WIFI_PASS / SERVER_URL'i güncelle."
