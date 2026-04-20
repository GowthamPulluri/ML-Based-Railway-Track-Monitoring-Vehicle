#include "esp_camera.h"
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <ESP32Servo.h>

// ================= WIFI =================
const char* ssid = "Khumba";
const char* password = "dhanistha.89";

// ================= TELEGRAM =================
String BOT_TOKEN = "8505403651:AAHFtagu9q68-G84f-Mj9-bWJyk5Bi1dn3Q";
String CHAT_ID   = "5294233327";

// ================= CAMERA =================
#define CAMERA_MODEL_AI_THINKER
#include "camera_pins.h"

// ================= SERVO =================
Servo myservo;
int servoPin = 2;
int pos = 20;
bool increasing = true;

// ================= URL ENCODE =================
String urlEncode(String str)
{
  String encoded="";
  char c, code0, code1;
  for(int i=0;i<str.length();i++){
    c=str.charAt(i);
    if(isalnum(c)) encoded+=c;
    else{
      code1=(c&0xf)+'0';
      if((c&0xf)>9) code1=(c&0xf)-10+'A';
      c=(c>>4)&0xf;
      code0=c+'0';
      if(c>9) code0=c-10+'A';
      encoded+='%'; encoded+=code0; encoded+=code1;
    }
  }
  return encoded;
}

// ================= TELEGRAM =================
void sendTelegramMessage(String msg)
{
  WiFiClientSecure client;
  client.setInsecure();
  HTTPClient https;

  String url = "https://api.telegram.org/bot" + BOT_TOKEN +
               "/sendMessage?chat_id=" + CHAT_ID +
               "&text=" + urlEncode(msg);

  if (https.begin(client, url)) {
    https.GET();
    https.end();
  }
}

// ================= CAMERA =================
void startCameraServer();

void setup()
{
  Serial.begin(115200);

  // ===== SERVO =====
  ESP32PWM::allocateTimer(0);
  myservo.setPeriodHertz(50);
  myservo.attach(servoPin, 500, 2400);
  myservo.write(pos);

  // ===== CAMERA =====
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;

  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;

  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;

  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;

  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;

  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_VGA;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 10;
  config.fb_count = 2;

  if (esp_camera_init(&config) != ESP_OK) {
    Serial.println("Camera Init Failed");
    return;
  }

  // ===== WIFI =====
  WiFi.begin(ssid, password);
  Serial.print("Connecting WiFi");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi Connected!");

  // ===== START CAMERA =====
  startCameraServer();

  // ===== TELEGRAM START MESSAGE =====
  String ip = WiFi.localIP().toString();
  Serial.println("🚀 System Started");
  Serial.println("IP: http://" + ip);

  sendTelegramMessage("🚀 System Started\nIP: http://" + ip);
}

void loop()
{
  // ================= SERVO CONTINUOUS SMOOTH MOTION =================

  static unsigned long lastMove = 0;

  if (millis() - lastMove > 40) {
    lastMove = millis();

    if (increasing) {
      pos++;
      if (pos >= 150) increasing = false;
    } else {
      pos--;
      if (pos <= 20) increasing = true;
    }

    myservo.write(pos);
  }
}