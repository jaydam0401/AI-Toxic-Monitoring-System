#include <SoftwareSerial.h>
#include <Adafruit_NeoPixel.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// HC-06 Bluetooth
SoftwareSerial BTSerial(2, 3);

// I2C LCD
LiquidCrystal_I2C lcd(0x27, 16, 2);  // 안 뜨면 0x3F로 변경

// Pin 설정
const int potPin = A2;
const int neoPin = 4;
const int piezo = 5;
const int switchPin = 6;

// FND a,b,c,d,e,f,g = D7~D13
const int segPins[7] = {7, 8, 9, 10, 11, 12, 13};

// NeoPixel 12개
const int neoCount = 12;
Adafruit_NeoPixel pixels(neoCount, neoPin, NEO_GRB + NEO_KHZ800);

// 상태 변수
int ppm = 0;
int currentLevel = 1;
int previousLevel = -1;

// millis 타이머
unsigned long lastSensorTime = 0;
unsigned long lastBTTime = 0;
unsigned long lastLCDTime = 0;
unsigned long lastBeepTime = 0;
unsigned long lastSirenTime = 0;

// 안정성 우선 설정
const unsigned long sensorInterval = 100;   // 센서 읽기 0.1초
const unsigned long btInterval = 1000;      // 앱 전송 1초
const unsigned long lcdInterval = 300;      // LCD 갱신 0.3초

// 정지 모드
bool paused = false;
unsigned long pauseStartTime = 0;

// 부저 상태
int beepTarget = 0;
int beepCount = 0;
bool beepOn = false;

// 사이렌 상태
int sirenFreq = 700;
bool sirenUp = true;

// FND 숫자 1~4
// 공통 애노드라 출력할 때 반전 사용
byte numbers[5][7] = {
  {0,0,0,0,0,0,0}, // 0 사용 안 함
  {0,1,1,0,0,0,0}, // 1
  {1,1,0,1,1,0,1}, // 2
  {1,1,1,1,0,0,1}, // 3
  {0,1,1,0,0,1,1}  // 4
};

void setup() {
  Serial.begin(9600);
  BTSerial.begin(9600);

  pinMode(piezo, OUTPUT);
  pinMode(switchPin, INPUT);

  for (int i = 0; i < 7; i++) {
    pinMode(segPins[i], OUTPUT);
  }

  pixels.begin();
  pixels.clear();
  pixels.show();

  clearFND();

  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("PPM SYSTEM");
  lcd.setCursor(0, 1);
  lcd.print("READY");
  delay(1000);
  lcd.clear();
}

void loop() {
  unsigned long now = millis();

  // 스위치 눌림 감지
  if (!paused && digitalRead(switchPin) == HIGH) {
    startPause(now);
  }

  // 정지 모드 처리
  if (paused) {
    handlePause(now);
    return;
  }

  // 센서 읽기
  if (now - lastSensorTime >= sensorInterval) {
    lastSensorTime = now;

    ppm = analogRead(potPin);

    if (ppm <= 250) {
      currentLevel = 1; // SAFE
    }
    else if (ppm <= 500) {
      currentLevel = 2; // CAUTION
    }
    else if (ppm <= 750) {
      currentLevel = 3; // WARNING
    }
    else {
      currentLevel = 4; // DANGER
    }

    updateFND(currentLevel);
    updateNeoPixel(currentLevel);

    if (currentLevel != previousLevel) {
      startAlarm(currentLevel);
      previousLevel = currentLevel;
    }
  }

  // 블루투스 전송: 앱 밀림 방지 위해 1초마다 1번만 전송
  if (now - lastBTTime >= btInterval) {
    lastBTTime = now;

    // Python AI receiver expects PPM,<value> once per second
    Serial.print("PPM,");
    Serial.println(ppm);

    BTSerial.println(ppm);
  }

  // LCD 갱신
  if (now - lastLCDTime >= lcdInterval) {
    lastLCDTime = now;
    updateLCD(ppm, currentLevel);
  }

  // 부저 처리
  handleAlarm(now);
}

void startPause(unsigned long now) {
  paused = true;
  pauseStartTime = now;

  noTone(piezo);

  beepTarget = 0;
  beepCount = 0;
  beepOn = false;

  pixels.clear();
  pixels.show();

  clearFND();

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("SYSTEM PAUSED");
}

void handlePause(unsigned long now) {
  unsigned long elapsed = now - pauseStartTime;

  if (elapsed < 5000) {
    int remain = 5 - (elapsed / 1000);

    lcd.setCursor(0, 1);
    lcd.print("INIT IN ");
    lcd.print(remain);
    lcd.print(" SEC ");
  }
  else if (elapsed < 6000) {
    lcd.setCursor(0, 0);
    lcd.print("INITIALIZING   ");
    lcd.setCursor(0, 1);
    lcd.print("PLEASE WAIT    ");

    tone(piezo, 2000);
  }
  else {
    noTone(piezo);
    lcd.clear();

    paused = false;
    previousLevel = -1;

    lastSensorTime = now;
    lastBTTime = now;
    lastLCDTime = now;
  }
}

void updateFND(int num) {
  for (int i = 0; i < 7; i++) {
    digitalWrite(segPins[i], !numbers[num][i]);
  }
}

void clearFND() {
  for (int i = 0; i < 7; i++) {
    digitalWrite(segPins[i], HIGH);
  }
}

void updateNeoPixel(int level) {
  uint32_t color;

  if (level == 1) {
    color = pixels.Color(0, 180, 40);
  }
  else if (level == 2) {
    color = pixels.Color(220, 180, 0);
  }
  else if (level == 3) {
    color = pixels.Color(255, 70, 0);
  }
  else {
    color = pixels.Color(255, 0, 0);
  }

  for (int i = 0; i < neoCount; i++) {
    pixels.setPixelColor(i, color);
  }

  pixels.show();
}

void updateLCD(int ppmValue, int level) {
  lcd.setCursor(0, 0);
  lcd.print("PPM: ");
  lcd.print(ppmValue);
  lcd.print("     ");

  lcd.setCursor(0, 1);

  if (level == 1) {
    lcd.print("STATUS: SAFE   ");
  }
  else if (level == 2) {
    lcd.print("STATUS: CAUTION");
  }
  else if (level == 3) {
    lcd.print("STATUS: WARNING");
  }
  else {
    lcd.print("STATUS: DANGER ");
  }
}

void startAlarm(int level) {
  beepCount = 0;
  beepOn = false;
  lastBeepTime = 0;

  if (level == 1) {
    beepTarget = 1;
  }
  else if (level == 2) {
    beepTarget = 2;
  }
  else if (level == 3) {
    beepTarget = 3;
  }
  else {
    beepTarget = 0;
    sirenFreq = 700;
    sirenUp = true;
    lastSirenTime = 0;
  }
}

void handleAlarm(unsigned long now) {
  if (currentLevel == 4) {
    handleSiren(now);
    return;
  }

  if (beepTarget <= 0) return;

  if (!beepOn && beepCount < beepTarget && now - lastBeepTime >= 120) {
    tone(piezo, 1000 + currentLevel * 200);
    beepOn = true;
    lastBeepTime = now;
  }

  if (beepOn && now - lastBeepTime >= 120) {
    noTone(piezo);
    beepOn = false;
    beepCount++;
    lastBeepTime = now;
  }

  if (beepCount >= beepTarget) {
    noTone(piezo);
    beepTarget = 0;
  }
}

void handleSiren(unsigned long now) {
  if (now - lastSirenTime < 25) return;

  lastSirenTime = now;

  tone(piezo, sirenFreq);

  if (sirenUp) {
    sirenFreq += 100;
    if (sirenFreq >= 1800) {
      sirenUp = false;
    }
  }
  else {
    sirenFreq -= 100;
    if (sirenFreq <= 700) {
      sirenUp = true;
    }
  }
}