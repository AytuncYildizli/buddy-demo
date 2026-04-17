// Core2 Buddy v1.0 — "I feel what Claude feels."
// Physical reactivity + breathing + evolution + touch + RGB halo
#include <M5Unified.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// ==== EDIT BUNU ====
const char* WIFI_SSID = "Ayfon";
const char* WIFI_PASS = "password123";
const char* SERVER_URL = "http://172.20.10.2:8080";
// ====================

#define BG       0x0000
#define FG       0xFD20   // turuncu
#define FG2      0xFBE0
#define TXT      0xFFFF
#define DIM      0x5A8E
#define PNK      0xFC1F
#define RED_     0xF800
#define GRN_     0x07E0
#define YEL_     0xFFE0
#define BLU_     0x041F

struct BuddyState {
  int approved = 0;
  int denied = 0;
  int tokens = 0;
  int today = 0;
  int mood = 5;
  int energy = 5;
  int level = 0;
  String nappedFor = "0h00m";
  
  // v1.0 additions
  int burn_rate = 0;       // tokens/sec recent (for breathing)
  bool thinking = false;   // claude is thinking (mid-tool-call)
  String last_event = "";  // "approve","deny","session_start","session_end","tool_start"
  unsigned long last_event_time = 0;
};

BuddyState buddy;
unsigned long lastPoll = 0;
unsigned long lastFrame = 0;
int lastApproved = 0;
int lastDenied = 0;
String lastEvent = "";
unsigned long lastEventTime = 0;

int page = 0;
const int TOTAL_PAGES = 2;

// Animation state
float breathPhase = 0;
int blinkCounter = 0;        // counts up, >200 → blink for 8 frames
int shakeTicks = 0;           // screen shake (approve)
int sadTicks = 0;             // sad droop (deny)
int purrTicks = 0;            // touch purr
int evolutionTicks = 0;       // level up animation
int prevLevel = 0;

// Particle hearts
struct Particle { int x, y, vy, life; uint16_t color; };
Particle particles[12];

M5Canvas canvas(&M5.Display);

int tokenHistory[32];
int histIdx = 0;

// ================ Evolution stages ================
// 0-10: egg
// 10-50: baby blob
// 50-200: cat face
// 200+: cat + crown
int getStage() {
  int total = buddy.approved;
  if (total < 10) return 0;   // egg
  if (total < 50) return 1;   // blob
  if (total < 200) return 2;  // cat
  return 3;                    // cat + crown
}

// ================ Physical reactions ================
void reactApproved() {
  M5.Speaker.tone(1760, 60);
  delay(40);
  M5.Speaker.tone(2200, 80);
  shakeTicks = 8;  // jump/shake
  spawnHearts(4);
}

void reactDenied() {
  M5.Speaker.tone(330, 200);
  delay(50);
  M5.Speaker.tone(220, 250);
  sadTicks = 30;  // droop 1 sec
}

void reactSessionStart() {
  // yawn awake
  M5.Speaker.tone(660, 80);
  delay(80);
  M5.Speaker.tone(880, 80);
  delay(80);
  M5.Speaker.tone(1320, 150);
}

void reactSessionEnd() {
  // zzz curl
  M5.Speaker.tone(880, 100);
  delay(100);
  M5.Speaker.tone(660, 100);
  delay(100);
  M5.Speaker.tone(440, 200);
}

void reactThinking() {
  M5.Speaker.tone(1200, 30);  // small beep
}

void reactPurr() {
  // low rolling tone
  for (int i = 0; i < 5; i++) {
    M5.Speaker.tone(180 + (i % 2) * 20, 60);
    delay(60);
  }
  purrTicks = 30;
}

void reactEvolution() {
  // level up fanfare
  M5.Speaker.tone(1000, 120); delay(120);
  M5.Speaker.tone(1320, 120); delay(120);
  M5.Speaker.tone(1760, 120); delay(120);
  M5.Speaker.tone(2200, 300);
  evolutionTicks = 60;  // 2 sec animation
  spawnHearts(8);
}

// ================ RGB halo ================
void setHalo(uint8_t r, uint8_t g, uint8_t b) {
  // Core2 has side RGB LEDs via M5.Display.touch? No — it's the AtomS3 thing.
  // Actual Core2 has small RGB on power button area only.
  // If available via M5 API:
  #ifdef ARDUINO_M5Stack_Core_ESP32
  // not all cores have this
  #endif
  // Fallback: use screen border color as halo simulation
  canvas.drawRect(0, 0, 320, 240, (r >> 3 << 11) | (g >> 2 << 5) | (b >> 3));
  canvas.drawRect(1, 1, 318, 238, (r >> 3 << 11) | (g >> 2 << 5) | (b >> 3));
}

uint16_t haloColorForState() {
  if (sadTicks > 0) return RED_;
  if (shakeTicks > 0) return GRN_;
  if (buddy.thinking) return YEL_;
  return BLU_;  // idle
}

// ================ Particles ================
void spawnHearts(int count) {
  for (int i = 0; i < count; i++)
    for (int p = 0; p < 12; p++)
      if (particles[p].life <= 0) {
        particles[p].x = 60 + random(-25, 25);
        particles[p].y = 110;
        particles[p].vy = -2 - random(3);
        particles[p].life = 30;
        particles[p].color = (random(3) == 0) ? PNK : FG;
        break;
      }
}

void drawHeart(int x, int y, uint16_t color) {
  canvas.fillCircle(x + 2, y + 2, 2, color);
  canvas.fillCircle(x + 6, y + 2, 2, color);
  canvas.fillTriangle(x, y + 3, x + 8, y + 3, x + 4, y + 9, color);
}
void drawHollowHeart(int x, int y, uint16_t c) {
  canvas.drawCircle(x + 2, y + 2, 2, c);
  canvas.drawCircle(x + 6, y + 2, 2, c);
  canvas.drawTriangle(x, y + 3, x + 8, y + 3, x + 4, y + 9, c);
}

void updateParticles() {
  for (int p = 0; p < 12; p++)
    if (particles[p].life > 0) {
      particles[p].y += particles[p].vy;
      particles[p].life--;
      if (particles[p].life > 0) drawHeart(particles[p].x, particles[p].y, particles[p].color);
    }
}

// ================ Buddy body (animated, evolves) ================
void drawBuddyBody(int cx, int cy, float breath, int stage, bool blinking, bool sad, int shake) {
  // Breathing scale
  int breathOffset = (int)(breath * 2);
  int xOffset = shake > 0 ? random(-2, 3) : 0;
  int yOffset = sad > 0 ? 3 : (shake > 0 ? -2 : 0);
  
  cx += xOffset;
  cy += yOffset;
  
  if (stage == 0) {
    // EGG — turuncu oval
    int w = 40 + breathOffset;
    int h = 48 + breathOffset;
    canvas.fillEllipse(cx, cy, w/2, h/2, FG);
    // crack mark
    canvas.drawLine(cx - 5, cy + 5, cx - 2, cy - 3, BG);
    canvas.drawLine(cx - 2, cy - 3, cx + 3, cy + 4, BG);
    canvas.drawLine(cx + 3, cy + 4, cx + 7, cy - 2, BG);
  } else if (stage == 1) {
    // BLOB — turuncu yuvarlak + basit gözler
    int r = 28 + breathOffset;
    canvas.fillCircle(cx, cy, r, FG);
    // eyes
    if (blinking) {
      canvas.fillRect(cx - 12, cy - 5, 8, 2, BG);
      canvas.fillRect(cx + 4, cy - 5, 8, 2, BG);
    } else {
      canvas.fillCircle(cx - 9, cy - 4, 3, BG);
      canvas.fillCircle(cx + 9, cy - 4, 3, BG);
    }
    // mouth
    if (sad > 0) canvas.drawLine(cx - 6, cy + 8, cx + 6, cy + 5, BG);
    else canvas.drawLine(cx - 6, cy + 5, cx + 6, cy + 5, BG);
  } else if (stage >= 2) {
    // CAT face — rounded square + eyes + cat mouth + ears
    int w = 54 + breathOffset;
    int h = 46 + breathOffset;
    canvas.fillRoundRect(cx - w/2, cy - h/2, w, h, 10, FG);
    // ears (triangles top)
    canvas.fillTriangle(cx - w/2 + 2, cy - h/2 + 4, cx - w/2 + 14, cy - h/2 + 4, cx - w/2 + 6, cy - h/2 - 8, FG);
    canvas.fillTriangle(cx + w/2 - 14, cy - h/2 + 4, cx + w/2 - 2, cy - h/2 + 4, cx + w/2 - 6, cy - h/2 - 8, FG);
    // eye whites
    if (blinking) {
      canvas.fillRect(cx - 14, cy - 6, 8, 2, BG);
      canvas.fillRect(cx + 6, cy - 6, 8, 2, BG);
    } else {
      canvas.fillRect(cx - 15, cy - 8, 8, 7, TXT);
      canvas.fillRect(cx + 7, cy - 8, 8, 7, TXT);
      // pupils
      canvas.fillRect(cx - 13, cy - 7, 4, 5, BG);
      canvas.fillRect(cx + 9, cy - 7, 4, 5, BG);
    }
    // nose
    canvas.fillTriangle(cx - 3, cy + 4, cx + 3, cy + 4, cx, cy + 8, PNK);
    // mouth
    if (sad > 0) {
      canvas.drawLine(cx - 7, cy + 14, cx, cy + 10, BG);
      canvas.drawLine(cx, cy + 10, cx + 7, cy + 14, BG);
    } else {
      canvas.drawLine(cx - 8, cy + 10, cx - 2, cy + 14, BG);
      canvas.drawLine(cx - 2, cy + 14, cx, cy + 12, BG);
      canvas.drawLine(cx, cy + 12, cx + 2, cy + 14, BG);
      canvas.drawLine(cx + 2, cy + 14, cx + 8, cy + 10, BG);
    }
    // whiskers
    canvas.drawLine(cx - w/2 - 4, cy + 6, cx - w/2 + 4, cy + 4, DIM);
    canvas.drawLine(cx - w/2 - 4, cy + 10, cx - w/2 + 4, cy + 10, DIM);
    canvas.drawLine(cx + w/2 - 4, cy + 4, cx + w/2 + 4, cy + 6, DIM);
    canvas.drawLine(cx + w/2 - 4, cy + 10, cx + w/2 + 4, cy + 10, DIM);
    
    // Purr wave if purring
    if (purrTicks > 0) {
      int r = 30 + (30 - purrTicks) * 2;
      canvas.drawCircle(cx, cy, r, FG);
    }
    
    // Crown if stage 3
    if (stage == 3) {
      int cw = 24;
      int chx = cx - cw/2;
      int chy = cy - h/2 - 18;
      canvas.fillTriangle(chx, chy + 8, chx + 6, chy, chx + 12, chy + 8, YEL_);
      canvas.fillTriangle(chx + 6, chy + 8, chx + 12, chy, chx + 18, chy + 8, YEL_);
      canvas.fillTriangle(chx + 12, chy + 8, chx + 18, chy, chx + 24, chy + 8, YEL_);
      canvas.fillRect(chx, chy + 8, cw, 4, YEL_);
      canvas.fillCircle(chx + 6, chy + 1, 1, PNK);
      canvas.fillCircle(chx + 18, chy + 1, 1, PNK);
    }
  }
  
  // Thinking indicator (yellow aura around)
  if (buddy.thinking) {
    canvas.drawCircle(cx, cy, 40, YEL_);
  }
  
  // Evolution sparkle
  if (evolutionTicks > 0) {
    for (int i = 0; i < 6; i++) {
      int ax = cx + cos(i * 1.0 + evolutionTicks * 0.2) * 60;
      int ay = cy + sin(i * 1.0 + evolutionTicks * 0.2) * 60;
      canvas.fillCircle(ax, ay, 3, YEL_);
    }
  }
}

// ================ Pages ================
void drawPage1() {
  canvas.fillSprite(BG);
  
  // Halo border
  uint16_t halo = haloColorForState();
  canvas.drawRect(0, 0, 320, 240, halo);
  canvas.drawRect(1, 1, 318, 238, halo);
  
  // Header
  canvas.setTextColor(TXT, BG);
  canvas.setTextSize(2);
  canvas.setCursor(12, 8);
  canvas.print("buddy");
  canvas.setCursor(268, 8);
  canvas.printf("%d/%d", page + 1, TOTAL_PAGES);
  
  // Tagline
  canvas.setTextSize(1);
  canvas.setTextColor(DIM, BG);
  canvas.setCursor(12, 28);
  canvas.print("I feel what Claude feels.");
  
  // Buddy body (left)
  int cx = 70, cy = 120;
  bool blinking = (blinkCounter > 200 && blinkCounter < 208);
  drawBuddyBody(cx, cy, sin(breathPhase), getStage(), blinking, sadTicks > 0 ? 1 : 0, shakeTicks);
  
  // Stats right side
  canvas.setTextSize(1);
  canvas.setTextColor(TXT, BG);
  canvas.setCursor(150, 50);
  canvas.print("mood");
  for (int i = 0; i < 5; i++) {
    if (i < buddy.mood) drawHeart(188 + i * 12, 48, FG);
    else drawHollowHeart(188 + i * 12, 48, DIM);
  }
  
  canvas.setCursor(150, 68);
  canvas.print("nrg ");
  for (int i = 0; i < 5; i++) {
    if (i < buddy.energy) canvas.fillRect(188 + i * 12, 66, 10, 10, YEL_);
    else canvas.drawRect(188 + i * 12, 66, 10, 10, DIM);
  }
  
  // LV badge
  canvas.fillRoundRect(150, 86, 60, 20, 4, FG2);
  canvas.setTextColor(BG, FG2);
  canvas.setCursor(158, 92);
  canvas.printf("LV %d", buddy.level);
  
  // Stats list
  canvas.setTextColor(TXT, BG);
  canvas.setCursor(150, 115);
  canvas.printf("approved  %d", buddy.approved);
  canvas.setCursor(150, 128);
  canvas.printf("denied    %d", buddy.denied);
  canvas.setCursor(150, 141);
  canvas.printf("napped    %s", buddy.nappedFor.c_str());
  canvas.setCursor(150, 154);
  canvas.printf("tokens    %d", buddy.tokens);
  canvas.setCursor(150, 167);
  canvas.printf("today     %d", buddy.today);
  canvas.setCursor(150, 180);
  canvas.setTextColor(FG, BG);
  canvas.printf("burn/s    %d", buddy.burn_rate);
  
  updateParticles();
  
  // Footer
  canvas.setTextColor(DIM, BG);
  canvas.setCursor(12, 226);
  canvas.print("A:feed  B:pet  C:next  tap:purr");
  canvas.fillCircle(310, 228, 3, WiFi.status() == WL_CONNECTED ? GRN_ : RED_);
  
  canvas.pushSprite(0, 0);
}

void drawPage2() {
  canvas.fillSprite(BG);
  uint16_t halo = haloColorForState();
  canvas.drawRect(0, 0, 320, 240, halo);
  canvas.drawRect(1, 1, 318, 238, halo);
  
  canvas.setTextColor(TXT, BG);
  canvas.setTextSize(2);
  canvas.setCursor(12, 8);
  canvas.print("session");
  canvas.setCursor(268, 8);
  canvas.printf("%d/%d", page + 1, TOTAL_PAGES);
  
  canvas.setTextSize(1);
  canvas.setTextColor(DIM, BG);
  canvas.setCursor(12, 28);
  canvas.print("token burn history (last ~64s)");
  
  // Sparkline
  int maxVal = 1;
  for (int i = 0; i < 32; i++) if (tokenHistory[i] > maxVal) maxVal = tokenHistory[i];
  
  int gy = 45, gh = 90, gx = 12, gw = 296;
  canvas.drawRect(gx, gy, gw, gh, DIM);
  for (int i = 0; i < 31; i++) {
    int x1 = gx + (i * gw) / 31;
    int x2 = gx + ((i + 1) * gw) / 31;
    int y1 = gy + gh - (tokenHistory[i] * gh) / maxVal;
    int y2 = gy + gh - (tokenHistory[i + 1] * gh) / maxVal;
    canvas.drawLine(x1, y1, x2, y2, FG);
    canvas.drawLine(x1, y1 + 1, x2, y2 + 1, FG);
  }
  
  canvas.setTextColor(TXT, BG);
  canvas.setCursor(12, 145);
  canvas.setTextSize(2);
  canvas.printf("%d tokens", buddy.tokens);
  canvas.setTextSize(1);
  canvas.setTextColor(FG, BG);
  canvas.setCursor(12, 168);
  canvas.printf("breathing @ %d/s", buddy.burn_rate);
  
  canvas.setTextColor(GRN_, BG);
  canvas.setCursor(12, 188);
  canvas.printf("approved %d", buddy.approved);
  canvas.setTextColor(RED_, BG);
  canvas.setCursor(120, 188);
  canvas.printf("denied %d", buddy.denied);
  
  int total = buddy.approved + buddy.denied;
  if (total > 0) {
    canvas.setTextColor(FG, BG);
    canvas.setCursor(12, 202);
    canvas.printf("trust: %d%%", (buddy.approved * 100) / total);
  }
  
  canvas.setTextColor(DIM, BG);
  canvas.setCursor(12, 226);
  canvas.print("C:back");
  canvas.fillCircle(310, 228, 3, WiFi.status() == WL_CONNECTED ? GRN_ : RED_);
  
  canvas.pushSprite(0, 0);
}

void drawUI() {
  if (page == 0) drawPage1();
  else drawPage2();
}

// ================ Networking ================
void fetchState() {
  if (WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;
  http.setConnectTimeout(1500);
  http.setTimeout(2000);
  http.begin(String(SERVER_URL) + "/state");
  int code = http.GET();
  if (code == 200) {
    String body = http.getString();
    StaticJsonDocument<768> doc;
    if (!deserializeJson(doc, body)) {
      int newApproved = doc["approved"] | 0;
      int newDenied = doc["denied"] | 0;
      
      buddy.approved = newApproved;
      buddy.denied = newDenied;
      buddy.tokens = doc["tokens"] | 0;
      buddy.today = doc["today"] | 0;
      buddy.mood = doc["mood"] | 5;
      buddy.energy = doc["energy"] | 5;
      buddy.level = doc["level"] | 0;
      buddy.nappedFor = String((const char*)(doc["napped"] | "0h00m"));
      buddy.burn_rate = doc["burn_rate"] | 0;
      buddy.thinking = doc["thinking"] | false;
      String newEvent = String((const char*)(doc["last_event"] | ""));
      
      // Record history
      tokenHistory[histIdx] = buddy.burn_rate > 0 ? buddy.burn_rate : buddy.tokens;
      histIdx = (histIdx + 1) % 32;
      
      // REACT to state changes
      if (newApproved > lastApproved) reactApproved();
      if (newDenied > lastDenied) reactDenied();
      
      // Level-up detection
      if (buddy.level > prevLevel && prevLevel > 0) reactEvolution();
      prevLevel = buddy.level;
      
      lastApproved = newApproved;
      lastDenied = newDenied;
      
      // Event-based reactions (from server)
      if (newEvent != lastEvent && newEvent != "") {
        if (newEvent == "session_start") reactSessionStart();
        else if (newEvent == "session_end") reactSessionEnd();
        else if (newEvent == "thinking") reactThinking();
        lastEvent = newEvent;
      }
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

// ================ Setup / Loop ================
void setup() {
  auto cfg = M5.config();
  M5.begin(cfg);
  M5.Speaker.begin();
  M5.Speaker.setVolume(180);
  M5.Display.setRotation(1);
  M5.Display.fillScreen(BG);
  
  canvas.createSprite(320, 240);
  canvas.fillSprite(BG);
  canvas.setTextColor(TXT, BG);
  canvas.setTextSize(2);
  canvas.setCursor(40, 90);
  canvas.println("buddy v1.0");
  canvas.setTextSize(1);
  canvas.setCursor(40, 120);
  canvas.printf("wifi: %s", WIFI_SSID);
  canvas.setCursor(40, 140);
  canvas.print("I feel what Claude feels.");
  canvas.pushSprite(0, 0);
  
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  int tries = 0;
  while (WiFi.status() != WL_CONNECTED && tries++ < 60) {
    delay(250);
    canvas.setCursor(40 + tries * 3, 160);
    canvas.print(".");
    canvas.pushSprite(0, 0);
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    reactSessionStart();
  }
  
  for (int p = 0; p < 12; p++) particles[p].life = 0;
  for (int i = 0; i < 32; i++) tokenHistory[i] = 0;
  
  prevLevel = 0;
}

void loop() {
  M5.update();
  
  // Poll state every 1s (faster for reactivity)
  if (millis() - lastPoll > 1000) {
    fetchState();
    lastPoll = millis();
  }
  
  // Breathing phase — rate depends on burn_rate
  // idle: 0.05, light: 0.1, heavy: 0.25
  float breathSpeed = 0.05 + (buddy.burn_rate / 100.0) * 0.2;
  if (breathSpeed > 0.3) breathSpeed = 0.3;
  breathPhase += breathSpeed;
  
  // Blink counter
  blinkCounter++;
  if (blinkCounter > 250) blinkCounter = 0;
  
  // Decay reaction ticks
  if (shakeTicks > 0) shakeTicks--;
  if (sadTicks > 0) sadTicks--;
  if (purrTicks > 0) purrTicks--;
  if (evolutionTicks > 0) evolutionTicks--;
  
  drawUI();
  
  // Buttons
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
  
  // Capacitive touch — tap buddy = purr
  auto touch = M5.Touch.getDetail();
  if (touch.wasPressed()) {
    int tx = touch.x, ty = touch.y;
    // Buddy body is around (70, 120)
    if (abs(tx - 70) < 50 && abs(ty - 120) < 60) {
      reactPurr();
      postAction("/pet");
      spawnHearts(5);
    }
  }
  
  delay(30);  // ~33fps
}
