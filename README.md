# Buddy Demo — Core2 + MBP (5dk setup)

Claude Code companion Tamagotchi. Core2 ekranında buddy, MBP'de control panel.

## 🚀 Hızlı Başlangıç (taksiden iner inmez)

### 1. iPhone hotspot aç
- Settings → Personal Hotspot → ON
- SSID & password not al

### 2. MBP bu hotspot'a bağlan
```bash
# IP'yi öğren:
ipconfig getifaddr en0
# Örnek: 172.20.10.2 (iPhone hotspot'ta)
```

### 3. Server başlat
```bash
cd ~/clawd/projects/buddy-demo
./start.sh
```
Çıktıda IP görünecek. Telefondan `http://<IP>:8080` açılabilir.

### 4. Core2'yi aynı hotspot'a bağla
`Core2Buddy.ino` dosyasında **sadece 3 satırı** değiştir:
```cpp
const char* WIFI_SSID = "<iPhone SSID>";
const char* WIFI_PASS = "<iPhone password>";
const char* SERVER_URL = "http://172.20.10.2:8080";  // MBP IP
```

### 5. Flash
**Seçenek A — Arduino IDE (ilk defa, uzun):**
- Arduino IDE indir → ESP32 board → M5Stack-Core2 seç → M5Unified + ArduinoJson library
- Port seç → Upload

**Seçenek B — PlatformIO (daha hızlı, Cursor/VSCode ile):**
```bash
brew install platformio
cd ~/clawd/projects/buddy-demo
pio run -t upload
```

### 6. Şov zamanı
- Core2 ekranında buddy canlanıyor (turuncu yüz, mood kalpler, energy barlar)
- Telefondan control panel'de butonlara bas
- Core2 her 2 sn state çekip ekran günceller
- BtnA = feed, BtnB = pet, BtnC = sleep

## 🎯 Gelecek adımlar
- [ ] Claude Code gerçek MCP entegrasyonu (fastmcp ile)
- [ ] Token sayacı real-time (Anthropic API usage endpoint)
- [ ] Pixel art sprite animation (idle, happy, sad, sleep)
- [ ] Buddy ölür özelliği (0 energy + 0 mood = game over)
- [ ] WiFi manager (dinamik SSID değişimi)

## 🐛 Sorun Çıkarsa
- **Core2 port görünmüyor:** `brew install --cask silicon-labs-vcp-driver`
- **WiFi bağlanmıyor:** iPhone hotspot "Maximize Compatibility" açık olmalı
- **Core2 server göremiyor:** iPhone hotspot aynı network'te, client isolation yok
- **Derleme hatası:** Library versions → M5Unified 0.1.x+ gerekli
