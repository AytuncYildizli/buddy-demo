// Core2 Buddy Demo - Claude Code companion
// Aytunc icin demo v0.1
#include <M5Unified.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// ==== EDIT BUNU (3 satir) ====
const char* WIFI_SSID = "Ayfon";
const char* WIFI_PASS = "password123";
const char* SERVER_URL = "http://172.20.10.2:8080";  // MBP on iPhone hotspot
// =============================

struct BuddyState {
  int approved = 0;
  int denied = 0;
  int tokens = 0;
  int mood = 5;
  int energy = 5;
  int level = 0;
  String nappedFor = "0h00m";
};

BuddyState buddy;
unsigned long lastPoll = 0;
bool hadWifi = false;

uint16_t rgb(uint8_t r, uint8_t g, uint8_t b) {
  return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3);
}

void drawHeart(int x, int y, uint16_t color) {
  M5.Display.fillCircle(x + 3, y + 3, 3, color);
  M5.Display.fillCircle(x + 9, y + 3, 3, color);
  M5.Display.fillTriangle(x, y + 4, x + 12, y + 4, x + 6, y + 12, color);
}

void drawBuddyFace(int x, int y, int mood) {
  uint16_t bodyColor = rgb(255, 140, 40);  // turuncu
  M5.Display.fillRoundRect(x, y, 100, 70, 8, bodyColor);
  // gozler
  M5.Display.fillRect(x + 20, y + 20, 12, 12, WHITE);
  M5.Display.fillRect(x + 68, y + 20, 12, 12, WHITE);
  M5.Display.fillRect(x + 25, y + 25, 5, 5, BLACK);
  M5.Display.fillRect(x + 73, y + 25, 5, 5, BLACK);
  // agiz mood'a gore
  if (mood >= 4) {
    M5.Display.fillRect(x + 35, y + 50, 30, 4, BLACK);
    M5.Display.fillRect(x + 30, y + 46, 5, 4, BLACK);
    M5.Display.fillRect(x + 65, y + 46, 5, 4, BLACK);
  } else if (mood >= 2) {
    M5.Display.fillRect(x + 35, y + 52, 30, 4, BLACK);
  } else {
    M5.Display.fillRect(x + 35, y + 55, 30, 4, BLACK);
    M5.Display.fillRect(x + 30, y + 50, 5, 4, BLACK);
    M5.Display.fillRect(x + 65, y + 50, 5, 4, BLACK);
  }
}

void drawUI() {
  M5.Display.fillScreen(BLACK);

  // Baslik
  M5.Display.setTextColor(WHITE);
  M5.Display.setTextSize(2);
  M5.Display.setCursor(10, 10);
  M5.Display.print("Buddy");
  M5.Display.setCursor(250, 10);
  M5.Display.printf("%d/5", buddy.mood);

  // Pixel art yuz
  drawBuddyFace(110, 35, buddy.mood);

  // Mood kalpler
  M5.Display.setTextColor(WHITE);
  M5.Display.setCursor(10, 115);
  M5.Display.print("mood ");
  for (int i = 0; i < 5; i++) {
    drawHeart(65 + i * 16, 115, i < buddy.mood ? RED : 0x4208);
  }

  // Energy
  M5.Display.setCursor(10, 140);
  M5.Display.print("nrg  ");
  for (int i = 0; i < 5; i++) {
    if (i < buddy.energy) M5.Display.fillRect(65 + i * 16, 142, 12, 12, YELLOW);
    else M5.Display.drawRect(65 + i * 16, 142, 12, 12, YELLOW);
  }

  // LV
  M5.Display.setTextSize(2);
  M5.Display.setTextColor(ORANGE);
  M5.Display.setCursor(10, 165);
  M5.Display.printf("LV %d", buddy.level);

  // Stats
  M5.Display.setTextSize(1);
  M5.Display.setTextColor(WHITE);
  M5.Display.setCursor(10, 195);
  M5.Display.printf("approved  %d", buddy.approved);
  M5.Display.setCursor(10, 207);
  M5.Display.printf("denied    %d", buddy.denied);
  M5.Display.setCursor(160, 195);
  M5.Display.printf("napped  %s", buddy.nappedFor.c_str());
  M5.Display.setCursor(160, 207);
  M5.Display.printf("tokens  %d", buddy.tokens);

  // Footer
  M5.Display.setTextColor(0x7BEF);
  M5.Display.setCursor(10, 225);
  M5.Display.print("BtnA:feed BtnB:pet BtnC:sleep");
}

void fetchState() {
  if (WiFi.status() != WL_CONNECTED) return;

  HTTPClient http;
  http.setConnectTimeout(1500);
  http.setTimeout(2000);
  http.begin(String(SERVER_URL) + "/state");
  int code = http.GET();
  if (code == 200) {
    String body = http.getString();
    StaticJsonDocument<512> doc;
    if (!deserializeJson(doc, body)) {
      buddy.approved = doc["approved"] | 0;
      buddy.denied = doc["denied"] | 0;
      buddy.tokens = doc["tokens"] | 0;
      buddy.mood = doc["mood"] | 5;
      buddy.energy = doc["energy"] | 5;
      buddy.level = doc["level"] | 0;
      buddy.nappedFor = String((const char*)(doc["napped"] | "0h00m"));
      drawUI();
    }
  }
  http.end();
}

void postAction(const char* path) {
  if (WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;
  http.setConnectTimeout(1500);
  http.begin(String(SERVER_URL) + path);
  http.POST("{}");
  http.end();
}

void setup() {
  auto cfg = M5.config();
  M5.begin(cfg);
  M5.Speaker.begin();
  M5.Display.setRotation(1);
  M5.Display.fillScreen(BLACK);
  M5.Display.setTextColor(WHITE);
  M5.Display.setTextSize(2);
  M5.Display.setCursor(20, 40);
  M5.Display.println("Buddy booting...");
  M5.Display.setTextSize(1);
  M5.Display.setCursor(20, 80);
  M5.Display.printf("WiFi: %s\n", WIFI_SSID);

  WiFi.begin(WIFI_SSID, WIFI_PASS);
  int tries = 0;
  while (WiFi.status() != WL_CONNECTED && tries++ < 60) {
    delay(250);
    M5.Display.print(".");
  }

  if (WiFi.status() == WL_CONNECTED) {
    hadWifi = true;
    M5.Display.println("\nWiFi OK");
    M5.Display.println(WiFi.localIP());
    M5.Speaker.tone(880, 120);
    delay(150);
    M5.Speaker.tone(1320, 120);
    delay(1200);
    drawUI();
  } else {
    M5.Display.println("\nWiFi FAILED");
    M5.Display.println("SSID/pass kontrol et");
  }
}

void loop() {
  M5.update();

  if (millis() - lastPoll > 2000) {
    fetchState();
    lastPoll = millis();
  }

  if (M5.BtnA.wasPressed()) {
    postAction("/feed");
    M5.Speaker.tone(1760, 80);
  }
  if (M5.BtnB.wasPressed()) {
    postAction("/pet");
    M5.Speaker.tone(1320, 80);
  }
  if (M5.BtnC.wasPressed()) {
    postAction("/sleep");
    M5.Speaker.tone(440, 200);
  }
}
