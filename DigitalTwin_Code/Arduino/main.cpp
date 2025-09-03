#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include "Temperature.h"
#include "Light.h"
#include "Motion.h"
#include "Co2.h"
#include "Timestamp.h"

// pins
#define SDA_PIN        21
#define SCL_PIN        22
#define PIR_SENSOR_PIN 2
#define CO2_RX_PIN     4
#define CO2_TX_PIN     5

// wifi
static const char* wifiSsid     = "*******";
static const char* wifiPassword = "************";

// BLE
#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

// device name
const char* BLE_DEVICE_NAME = "ESP32_BLE_Server_2";
// const char* BLE_DEVICE_NAME = "ESP32_BLE_Server_1";    // <------Uncomment for second device


unsigned long lastPublishTime   = 0;
const unsigned long publishIntervalMs = 5000;

// sensors
Temperature    temperatureSensor;
Light          lightSensor;
Motion         motionSensor(PIR_SENSOR_PIN);
HardwareSerial co2Serial(1);
Co2            co2Sensor(co2Serial, CO2_RX_PIN, CO2_TX_PIN);

BLECharacteristic *pCharacteristic;
bool deviceConnected = false;

class MyServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer* pServer) override {
    deviceConnected = true;
    Serial.println("[BLE] Client connected.");
  }
  void onDisconnect(BLEServer* pServer) override {
    deviceConnected = false;
    Serial.println("[BLE] Client disconnected.");
    BLEDevice::startAdvertising();
  }
};

void setup() {
  Serial.begin(115200);

  // setup I2C for sensors
  Wire.begin(SDA_PIN, SCL_PIN);

  temperatureSensor.begin();
  lightSensor.begin();
  motionSensor.begin();
  co2Sensor.begin();

  // set up WiFi
  Serial.print("Connecting to Wi‑Fi for time sync");
  WiFi.begin(wifiSsid, wifiPassword);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println(" OK");
  
 // initialize timestamp (syncs with NTP server)
  initTimestamp();

  // set up BLE
  BLEDevice::init(BLE_DEVICE_NAME);
  BLEServer *pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  BLEService *pService = pServer->createService(SERVICE_UUID);
  pCharacteristic = pService->createCharacteristic(
    CHARACTERISTIC_UUID,
    BLECharacteristic::PROPERTY_READ |
    BLECharacteristic::PROPERTY_NOTIFY
  );
  pCharacteristic->addDescriptor(new BLE2902());
  pService->start();

  BLEAdvertising *pAdvertising = pServer->getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(true);
  BLEDevice::startAdvertising();

  Serial.print("BLE server advertising as: ");
  Serial.println(BLE_DEVICE_NAME);
}

void loop() {
  unsigned long now = millis();
  if (deviceConnected && (now - lastPublishTime) >= publishIntervalMs) {
    lastPublishTime = now;
    publishSensorData();
  }
  delay(10);
}

void publishSensorData() {
  // read sensors
  float temperature = temperatureSensor.getTemperature();
  float humidity    = temperatureSensor.getHumidity();
  float lightValue  = lightSensor.getLux();
  bool  motion      = motionSensor.isMotionDetected();
  float co2         = co2Sensor.getPPM();

  Serial.printf("T: %.2f  H: %.2f  L: %.2f  M: %s  CO2: %.2f\n",
                temperature, humidity, lightValue,
                motion ? "YES" : "NO", co2);

  String timestamp = getTimestamp();

  // make JSON payload
  char messageBuffer[256];
  snprintf(messageBuffer, sizeof(messageBuffer),
           "{\"time_2\":\"%s\",\"temp_2\":%.2f,\"hum_2\":%.2f,\"light_2\":%.2f,\"motion_2\":%s,\"co2_2\":%.2f}",
    //                  "{\"time_1\":\"%s\",\"temp_1\":%.2f,\"hum_1\":%.2f,\"light_1\":%.2f,\"motion_1\":%s,\"co2_1\":%.2f}",     // <----- Uncomment for second device
           timestamp.c_str(),
           temperature,
           humidity,
           lightValue,
           motion ? "true" : "false",
           co2);

  Serial.print("Publishing BLE message: ");
  Serial.println(messageBuffer);

  // send to Raspberry Pi via BLE
  pCharacteristic->setValue((uint8_t*)messageBuffer, strlen(messageBuffer));
  pCharacteristic->notify();
}
