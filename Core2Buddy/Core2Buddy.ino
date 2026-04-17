// Core2 Buddy v0.3 — Boris-style ASCII face, 2 pages, flicker-free
// Aytunc icin — Claude Code companion
#include <M5Unified.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// ==== EDIT BUNU (3 satir) ====
const char* WIFI_SSID = "Ayfon";
const char* WIFI_PASS = "password123";
const char* SERVER_URL = "http://172.20.10.2:8080";
// =============================

// Boris-style palette
#define BG       0x0000   // siyah
#define FG       0xFD20   // turuncu
#define FG2      0xFBE0
#define TXT      0xFFFF
#define DIM      0x5A8E
#define PNK      0xFC1F
#define RED_     0xF800
#define GRN_     0x07E0
#define YEL_     0xFFE0

struct BuddyState {
  int approved = 0;
  int denied = 0;
  int tokens = 0;
  int mood = 5;
  int energy = 5;
  int level = 0;
  int today = 0;
  String nappedFor = "0h00m";
};

BuddyState buddy;
unsigned long lastPoll = 0;
unsigned long lastBlink = 0;
int lastApproved = 0;
int page = 0;   // 0 = stats, 1 = graph
const int TOTAL_PAGES = 2;

// History for sparkline
int tokenHistory[32];
int historyIdx = 0;

M5Canvas canvas(&M5.Display);

struct Particle { int x, y, vy, life; uint16_t color; };
Particle particles[10];

void spawnHearts(int count) {
  for (int i = 0; i < count; i++)
    for (int p = 0; p < 10; p++)
      if (particles[p].life <= 0) {
        particles[p].x = 60 + random(-20, 20);
        particles[p].y = 80;
        particles[p].vy = -2 - random(2);
        particles[p].life = 30;
        particles[p].color = (random(2) == 0) ? PNK : FG;
        break;
      }
}

void drawHeart(int x, int y, uint16_t color) {
  canvas.fillCircle(x + 2, y + 2, 2, color);
  canvas.fillCircle(x + 6, y + 2, 2, color);
  canvas.fillTriangle(x, y + 3, x + 8, y + 3, x + 4, y + 9, color);
}

void drawHollowHeart(int x, int y, uint16_t color) {
  canvas.drawCircle(x + 2, y + 2, 2, color);
  canvas.drawCircle(x + 6, y + 2, 2, color);
  canvas.drawTriangle(x, y + 3, x + 8, y + 3, x + 4, y + 9, color);
}

void updateParticles() {
  for (int p = 0; p < 10; p++)
    if (particles[p].life > 0) {
      particles[p].y += particles[p].vy;
      particles[p].life--;
      if (particles[p].life > 0) drawHeart(particles[p].x, particles[p].y, particles[p].color);
    }
}

// ASCII cat face (Boris-style), monospace rendered
// Blink state: 0=open eyes, 1=closed
void drawAsciiFace(int x, int y, int blinkState) {
  canvas.setTextColor(FG, BG);
  canvas.setTextSize(2);
  canvas.setCursor(x, y);
  canvas.print("/-----\\");
  canvas.setCursor(x, y + 16);
  canvas.print("|{ }|");
  canvas.setCursor(x, y + 32);
  if (blinkState == 1) {
    canvas.print("| -- -- |");
  } else {
    canvas.print("| o oo o |");
  }
  canvas.setCursor(x, y + 48);
  canvas.print("\\_____/");
}

void drawHorizRule(int y) {
  for (int i = 0; i < 320; i += 4) canvas.drawPixel(i, y, DIM);
}

void drawPage1() {
  canvas.fillSprite(BG);
  
  // Header: "buddy"  "1/2"
  canvas.setTextColor(TXT, BG);
  canvas.setTextSize(2);
  canvas.setCursor(10, 6);
  canvas.print("buddy");
  canvas.setCursor(268, 6);
  canvas.printf("%d/%d", page + 1, TOTAL_PAGES);
  
  // ASCII cat face (left side)
  int blink = ((millis() / 200) % 20 == 0) ? 1 : 0;
  drawAsciiFace(14, 36, blink);
  
  // Stats (right side)
  canvas.setTextSize(1);
  
  // mood hearts
  canvas.setTextColor(TXT, BG);
  canvas.setCursor(150, 40);
  canvas.print("mood");
  for (int i = 0; i < 5; i++) {
    if (i < buddy.mood) drawHeart(185 + i * 11, 38, FG);
    else drawHollowHeart(185 + i * 11, 38, DIM);
  }
  
  // fed (circles)
  canvas.setCursor(150, 58);
  canvas.print("fed");
  for (int i = 0; i < 10; i++) {
    if (i < buddy.mood * 2) canvas.fillCircle(180 + i * 10, 62, 3, TXT);
    else canvas.drawCircle(180 + i * 10, 62, 3, DIM);
  }
  
  // energy (blocks)
  canvas.setCursor(150, 76);
  canvas.print("energy");
  for (int i = 0; i < 5; i++) {
    if (i < buddy.energy) canvas.fillRect(200 + i * 14, 74, 10, 10, YEL_);
    else canvas.drawRect(200 + i * 14, 74, 10, 10, TXT);
  }
  
  // LV badge
  canvas.fillRoundRect(150, 98, 40, 18, 4, 0xFBE0);
  canvas.setTextColor(BG, 0xFBE0);
  canvas.setCursor(158, 104);
  canvas.printf("Lv %d", buddy.level);
  
  // Metrics list (bottom)
  canvas.setTextColor(TXT, BG);
  canvas.setCursor(150, 130);
  canvas.printf("approved  %d", buddy.approved);
  canvas.setCursor(150, 145);
  canvas.printf("denied    %d", buddy.denied);
  canvas.setCursor(150, 160);
  canvas.printf("napped    %s", buddy.nappedFor.c_str());
  canvas.setCursor(150, 175);
  canvas.printf("tokens    %d", buddy.tokens);
  canvas.setCursor(150, 190);
  canvas.printf("today     %d", buddy.today);
  
  updateParticles();
  
  // Footer
  canvas.setTextColor(DIM, BG);
  canvas.setCursor(10, 225);
  canvas.print("A:feed B:pet C:next>");
  canvas.fillCircle(310, 228, 3, WiFi.status() == WL_CONNECTED ? GRN_ : RED_);
  
  canvas.pushSprite(0, 0);
}

void drawPage2() {
  canvas.fillSprite(BG);
  
  canvas.setTextColor(TXT, BG);
  canvas.setTextSize(2);
  canvas.setCursor(10, 6);
  canvas.print("session");
  canvas.setCursor(268, 6);
  canvas.printf("%d/%d", page + 1, TOTAL_PAGES);
  
  // Sparkline — token history
  canvas.setTextSize(1);
  canvas.setTextColor(DIM, BG);
  canvas.setCursor(10, 40);
  canvas.print("token history (32 samples, ~2s each)");
  
  // Find max for scaling
  int maxVal = 1;
  for (int i = 0; i < 32; i++) if (tokenHistory[i] > maxVal) maxVal = tokenHistory[i];
  
  // Draw graph
  int graphY = 55;
  int graphH = 80;
  int graphX = 10;
  int graphW = 300;
  
  canvas.drawRect(graphX, graphY, graphW, graphH, DIM);
  for (int i = 0; i < 31; i++) {
    int x1 = graphX + (i * graphW) / 31;
    int x2 = graphX + ((i + 1) * graphW) / 31;
    int y1 = graphY + graphH - (tokenHistory[i] * graphH) / maxVal;
    int y2 = graphY + graphH - (tokenHistory[i + 1] * graphH) / maxVal;
    canvas.drawLine(x1, y1, x2, y2, FG);
  }
  
  // Summary boxes
  canvas.setTextColor(TXT, BG);
  canvas.setCursor(10, 150);
  canvas.setTextSize(2);
  canvas.printf("%d tokens", buddy.tokens);
  
  canvas.setTextSize(1);
  canvas.setTextColor(GRN_, BG);
  canvas.setCursor(10, 180);
  canvas.printf("approved: %d", buddy.approved);
  canvas.setTextColor(RED_, BG);
  canvas.setCursor(150, 180);
  canvas.printf("denied: %d", buddy.denied);
  
  int total = buddy.approved + buddy.denied;
  if (total > 0) {
    int pct = (buddy.approved * 100) / total;
    canvas.setTextColor(FG, BG);
    canvas.setCursor(10, 200);
    canvas.printf("approval rate: %d%%", pct);
  }
  
  // Footer
  canvas.setTextColor(DIM, BG);
  canvas.setCursor(10, 225);
  canvas.print("A:feed B:pet C:<back");
  canvas.fillCircle(310, 228, 3, WiFi.status() == WL_CONNECTED ? GRN_ : RED_);
  
  canvas.pushSprite(0, 0);
}

void drawUI() {
  if (page == 0) drawPage1();
  else drawPage2();
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
      buddy.today = doc["today"] | 0;
      buddy.nappedFor = String((const char*)(doc["napped"] | "0h00m"));
      
      // Record history
      tokenHistory[historyIdx] = buddy.tokens;
      historyIdx = (historyIdx + 1) % 32;
      
      if (buddy.approved > lastApproved) {
        spawnHearts(4);
        M5.Speaker.tone(1760, 60);
        delay(40);
        M5.Speaker.tone(2100, 80);
      }
      lastApproved = buddy.approved;
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
  M5.Display.fillScreen(BG);
  
  canvas.createSprite(320, 240);
  canvas.fillSprite(BG);
  canvas.setTextColor(TXT, BG);
  canvas.setTextSize(2);
  canvas.setCursor(40, 80);
  canvas.println("buddy v0.3");
  canvas.setTextSize(1);
  canvas.setCursor(40, 120);
  canvas.printf("wifi: %s\n", WIFI_SSID);
  canvas.pushSprite(0, 0);
  
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  int tries = 0;
  while (WiFi.status() != WL_CONNECTED && tries++ < 60) {
    delay(250);
    canvas.setCursor(40 + tries * 3, 140);
    canvas.print(".");
    canvas.pushSprite(0, 0);
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    M5.Speaker.tone(880, 100); delay(120);
    M5.Speaker.tone(1320, 100); delay(120);
    M5.Speaker.tone(1760, 150); delay(500);
  }
  
  for (int p = 0; p < 10; p++) particles[p].life = 0;
  for (int i = 0; i < 32; i++) tokenHistory[i] = 0;
  
  drawUI();
}

void loop() {
  M5.update();
  
  if (millis() - lastPoll > 2000) {
    fetchState();
    lastPoll = millis();
  }
  
  drawUI();  // redraw every frame (canvas = flicker-free)
  
  if (M5.BtnA.wasPressed()) {
    postAction("/feed");
    M5.Speaker.tone(1760, 80);
    spawnHearts(2);
  }
  if (M5.BtnB.wasPressed()) {
    postAction("/pet");
    M5.Speaker.tone(1320, 80);
    spawnHearts(3);
  }
  if (M5.BtnC.wasPressed()) {
    page = (page + 1) % TOTAL_PAGES;
    M5.Speaker.tone(660, 60);
  }
  
  delay(40);  // ~25fps
}
