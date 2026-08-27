#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <DHT.h>

// ================================================================
// NETWORK CONFIGURATION
// Change Wi-Fi name and password.
// 192.168.1.4 is the computer running Docker and VTAB.
// ================================================================

#define VTAB_WIFI_SSID "ENTER_YOUR_WIFI_NAME"
#define VTAB_WIFI_PASSWORD "ENTER_YOUR_WIFI_PASSWORD"

#define VTAB_MQTT_HOST "192.168.1.4"
#define VTAB_MQTT_PORT 1883

// ================================================================
// ESP32 PIN CONFIGURATION
// ================================================================

#define DHT_PIN 4
#define DHT_TYPE DHT22

// Connect the water sensor AO pin to GPIO34.
#define WATER_PIN 34

// Protect GPIO35 from voltages above 3.3V.
#define MQ2_PIN 35

#define RED_LED 32
#define YELLOW_LED 33
#define GREEN_LED 25
#define BUZZER 26

// This ID must match the seeded VTAB device.
const char* DEVICE_ID =
  "00000000-0000-0000-0000-000000000101";

// ================================================================
// TRIGGER PARAMETERS - EDIT THESE VALUES WHEN REQUIRED
// Keep matching server rules in VTAB Dashboard -> Settings.
// ================================================================
#define TEMP_YELLOW_THRESHOLD       32.0
#define TEMP_RED_THRESHOLD          33.0
#define HUMIDITY_YELLOW_THRESHOLD   75.0
#define HUMIDITY_RED_THRESHOLD      80.0
#define WATER_RED_THRESHOLD         0
#define MQ2_YELLOW_THRESHOLD        1300
#define MQ2_RED_THRESHOLD           1500
#define DOOR_OPEN_WARNING           true

// ================================================================
// TIMING PARAMETERS - EDIT THESE VALUES WHEN REQUIRED
// ================================================================
#define LED_BLINK_INTERVAL          500
#define BUZZER_INTERVAL             1000
#define BUZZER_ON_TIME              150
#define PUBLISH_INTERVAL            3000
#define DHT_READ_INTERVAL           2000
#define WIFI_RETRY_INTERVAL         10000
#define MQTT_RETRY_INTERVAL         5000
// ================================================================
// OBJECTS AND STATE
// ================================================================

DHT dht(DHT_PIN, DHT_TYPE);

WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

unsigned long lastPublishTime = 0;
unsigned long previousLedMillis = 0;
unsigned long previousBuzzerMillis = 0;
bool ledState = false;
bool buzzerState = false;
float latestHardwareTemperature = 24.0;
float latestHardwareHumidity = 48.0;
int latestWaterRaw = 0;
int latestMq2Raw = 0;
bool latestDhtError = false;
unsigned long previousDhtReadMillis = 0;
unsigned long previousWifiAttemptMillis = 0;
unsigned long previousMqttAttemptMillis = 0;

// Each component can use either hardware or simulation.
struct ComponentSource {
  bool simulated;
  float simulatedValue;
};

// Default source configuration:
//
// Temperature = hardware
// Humidity    = hardware
// Water       = hardware
// Door        = simulation because no reed switch is installed
// Smoke       = hardware
ComponentSource sources[5] = {
  {false, 24.0},
  {false, 48.0},
  {false, 0.0},
  {true,  0.0},
  {false, 0.0}
};

const char* sensorNames[5] = {
  "temperature",
  "humidity",
  "water_leak",
  "door_open",
  "smoke"
};

// ================================================================
// LOCAL LED AND BUZZER CONTROL
// ================================================================

void updateIndicators(unsigned long currentTime, float temperature, float humidity, bool waterLeak, bool doorOpen, bool smokeDetected, int mq2Raw, bool smokeIsSimulated) {
  bool tempRed = temperature >= TEMP_RED_THRESHOLD;
  bool tempYellow = !tempRed && temperature >= TEMP_YELLOW_THRESHOLD;
  bool humidityRed = humidity >= HUMIDITY_RED_THRESHOLD;
  bool humidityYellow = !humidityRed && humidity >= HUMIDITY_YELLOW_THRESHOLD;
  bool waterRed = waterLeak;
  bool mq2Red = smokeDetected;
  bool mq2Yellow = !smokeIsSimulated && !mq2Red && mq2Raw >= MQ2_YELLOW_THRESHOLD;
  bool doorYellow = DOOR_OPEN_WARNING && doorOpen;
  bool redAlert = tempRed || humidityRed || waterRed || mq2Red;
  bool yellowAlert = tempYellow || humidityYellow || mq2Yellow || doorYellow;

  if (currentTime - previousLedMillis >= LED_BLINK_INTERVAL) {
    previousLedMillis = currentTime;
    ledState = !ledState;
  }
  bool alarmActive = redAlert || yellowAlert;
  if (alarmActive && currentTime - previousBuzzerMillis >= BUZZER_INTERVAL) {
    previousBuzzerMillis = currentTime;
    buzzerState = true;
  }
  if (buzzerState && currentTime - previousBuzzerMillis >= BUZZER_ON_TIME) buzzerState = false;
  if (!alarmActive) { buzzerState = false; previousBuzzerMillis = currentTime; }
  digitalWrite(BUZZER, buzzerState ? HIGH : LOW);

  if (redAlert) {
    digitalWrite(RED_LED, ledState); digitalWrite(YELLOW_LED, LOW); digitalWrite(GREEN_LED, LOW);
  } else if (yellowAlert) {
    digitalWrite(RED_LED, LOW); digitalWrite(YELLOW_LED, ledState); digitalWrite(GREEN_LED, LOW);
  } else {
    digitalWrite(RED_LED, LOW); digitalWrite(YELLOW_LED, LOW); digitalWrite(GREEN_LED, ledState);
  }
}

// ================================================================
// RECEIVE COMPONENT SETTINGS FROM VTAB
// ================================================================

void mqttMessageReceived(
  char* topic,
  byte* payload,
  unsigned int length
) {
  JsonDocument document;

  DeserializationError error =
    deserializeJson(document, payload, length);

  if (error) {
    Serial.print("Invalid configuration message: ");
    Serial.println(error.c_str());
    return;
  }

  for (int index = 0; index < 5; index++) {
    JsonObject component =
      document["components"][sensorNames[index]];

    if (component.isNull()) {
      continue;
    }

    const char* mode =
      component["mode"] | "hardware";

    sources[index].simulated =
      String(mode) == "simulated";

    if (!component["simulated_value"].isNull()) {
      sources[index].simulatedValue =
        component["simulated_value"].as<float>();
    }

    Serial.print("Source updated: ");
    Serial.print(sensorNames[index]);
    Serial.print(" = ");

    if (sources[index].simulated) {
      Serial.println("simulation");
    } else {
      Serial.println("hardware");
    }
  }
}

// ================================================================
// WI-FI CONNECTION
// ================================================================

void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;
  unsigned long now = millis();
  if (previousWifiAttemptMillis != 0 && now - previousWifiAttemptMillis < WIFI_RETRY_INTERVAL) return;
  previousWifiAttemptMillis = now;
  WiFi.mode(WIFI_STA);
  WiFi.begin(VTAB_WIFI_SSID, VTAB_WIFI_PASSWORD);
  Serial.println("Wi-Fi connection attempt started; local alarms remain active.");
}

// ================================================================
// MQTT CONNECTION
// ================================================================

void connectMQTT() {
  if (WiFi.status() != WL_CONNECTED || mqttClient.connected()) return;
  unsigned long now = millis();
  if (previousMqttAttemptMillis != 0 && now - previousMqttAttemptMillis < MQTT_RETRY_INTERVAL) return;
  previousMqttAttemptMillis = now;
  String clientId = "vtab-esp32-" + String((uint32_t)ESP.getEfuseMac(), HEX);
  Serial.print("Connecting to VTAB MQTT at "); Serial.print(VTAB_MQTT_HOST); Serial.print(":"); Serial.println(VTAB_MQTT_PORT);
  if (mqttClient.connect(clientId.c_str())) {
    String configurationTopic = "devices/" + String(DEVICE_ID) + "/config/sources";
    mqttClient.subscribe(configurationTopic.c_str(), 1);
    Serial.println("MQTT connected");
  } else {
    Serial.print("MQTT unavailable, state "); Serial.print(mqttClient.state()); Serial.println("; local alarms continue.");
  }
}

// ================================================================
// CHOOSE HARDWARE OR SIMULATED VALUE
// ================================================================

float selectedValue(
  int sensorIndex,
  float hardwareValue
) {
  if (sources[sensorIndex].simulated) {
    return sources[sensorIndex].simulatedValue;
  }

  return hardwareValue;
}

// Human-readable source label used by the compact Serial status table.
const char* sourceName(int sensorIndex) {
  return sources[sensorIndex].simulated ? "simulated" : "hardware";
}

void updateLiveAlarm(unsigned long currentTime) {
  latestWaterRaw = analogRead(WATER_PIN);
  latestMq2Raw = analogRead(MQ2_PIN);
  if (currentTime - previousDhtReadMillis >= DHT_READ_INTERVAL) {
    previousDhtReadMillis = currentTime;
    float newTemperature = dht.readTemperature();
    float newHumidity = dht.readHumidity();
    latestDhtError = isnan(newTemperature) || isnan(newHumidity);
    if (!isnan(newTemperature)) latestHardwareTemperature = newTemperature;
    if (!isnan(newHumidity)) latestHardwareHumidity = newHumidity;
  }
  float effectiveTemperature = selectedValue(0, latestHardwareTemperature);
  float effectiveHumidity = selectedValue(1, latestHardwareHumidity);
  bool effectiveWaterLeak = sources[2].simulated ? sources[2].simulatedValue >= 0.5 : latestWaterRaw > WATER_RED_THRESHOLD;
  bool effectiveDoorOpen = selectedValue(3, 0) >= 0.5;
  bool effectiveSmoke = sources[4].simulated ? sources[4].simulatedValue >= 0.5 : latestMq2Raw >= MQ2_RED_THRESHOLD;
  updateIndicators(currentTime, effectiveTemperature, effectiveHumidity, effectiveWaterLeak, effectiveDoorOpen, effectiveSmoke, latestMq2Raw, sources[4].simulated);
}

// ================================================================
// READ AND SEND SENSOR DATA
// ================================================================

void publishTelemetry() {
  float hardwareTemperature = latestHardwareTemperature;
  float hardwareHumidity = latestHardwareHumidity;
  int waterRaw = latestWaterRaw;
  int smokeRaw = latestMq2Raw;
  bool dhtError = latestDhtError;

  float temperature =
    selectedValue(0, hardwareTemperature);

  float humidity =
    selectedValue(1, hardwareHumidity);

  int waterLeak =
    selectedValue(
      2,
      waterRaw > WATER_RED_THRESHOLD ? 1 : 0
    ) >= 0.5 ? 1 : 0;

  // No physical door sensor currently installed.
  int doorOpen =
    selectedValue(3, 0) >= 0.5 ? 1 : 0;

  int smokeDetected =
    selectedValue(
      4,
      smokeRaw >= MQ2_RED_THRESHOLD ? 1 : 0
    ) >= 0.5 ? 1 : 0;

  JsonDocument document;

  document["device_id"] = DEVICE_ID;

  JsonObject readings =
    document["readings"].to<JsonObject>();

  readings["temperature"] = temperature;
  readings["humidity"] = humidity;
  readings["water_leak"] = waterLeak;
  readings["door_open"] = doorOpen;
  readings["smoke"] = smokeDetected;

  JsonObject sourceInformation =
    document["sources"].to<JsonObject>();

  for (int index = 0; index < 5; index++) {
    JsonObject source =
      sourceInformation[
        sensorNames[index]
      ].to<JsonObject>();

    source["mode"] =
      sources[index].simulated
        ? "simulated"
        : "hardware";

    source["provider"] =
      sources[index].simulated
        ? "component-tester"
        : "esp32";

    // Capability is independent from the selected source mode so the
    // Test Lab can restore a simulated component to physical hardware.
    source["hardware_available"] =
      index == 3 ? false :
      (index <= 1 ? !dhtError : true);
  }

  sourceInformation["temperature"]["pin"] =
    DHT_PIN;

  sourceInformation["temperature"]["sensor_error"] =
    dhtError;

  sourceInformation["humidity"]["pin"] =
    DHT_PIN;

  sourceInformation["humidity"]["sensor_error"] =
    dhtError;

  sourceInformation["water_leak"]["pin"] =
    WATER_PIN;

  sourceInformation["water_leak"]["raw"] =
    waterRaw;

  sourceInformation["door_open"]["pin"] =
    nullptr;

  sourceInformation["smoke"]["pin"] =
    MQ2_PIN;

  sourceInformation["smoke"]["raw"] =
    smokeRaw;

  JsonObject health =
    document["health"].to<JsonObject>();

  health["rssi"] = WiFi.RSSI();
  health["uptime_seconds"] = millis() / 1000;
  health["firmware"] = "vtab-esp32-4.4.1-compact-status";
  health["board"] = "ESP32-WROOM-32";
  health["source"] = "esp32-hardware";
  health["dht_error"] = dhtError;

  String payload;
  serializeJson(document, payload);

  String telemetryTopic =
    "devices/" +
    String(DEVICE_ID) +
    "/telemetry";

  bool successful =
    mqttClient.publish(
      telemetryTopic.c_str(),
      payload.c_str(),
      false
    );

  const char* temperatureStatus = temperature >= TEMP_RED_THRESHOLD ? "RED" : temperature >= TEMP_YELLOW_THRESHOLD ? "YELLOW" : "SAFE";
  const char* humidityStatus = humidity >= HUMIDITY_RED_THRESHOLD ? "RED" : humidity >= HUMIDITY_YELLOW_THRESHOLD ? "YELLOW" : "SAFE";
  const char* waterStatus = waterLeak ? "RED" : "SAFE";
  const char* doorStatus = doorOpen ? "YELLOW" : "SAFE";
  const char* smokeStatus = smokeDetected ? "RED" : (!sources[4].simulated && smokeRaw >= MQ2_YELLOW_THRESHOLD ? "YELLOW" : "SAFE");
  bool redActive = String(temperatureStatus) == "RED" || String(humidityStatus) == "RED" || waterLeak || smokeDetected;
  bool yellowActive = String(temperatureStatus) == "YELLOW" || String(humidityStatus) == "YELLOW" || doorOpen || String(smokeStatus) == "YELLOW";
  const char* overallStatus = redActive ? "RED ALERT" : yellowActive ? "YELLOW WARNING" : "SAFE";

  Serial.println();
  Serial.println("================ VTAB LIVE STATUS ================");
  Serial.println("SENSOR       VALUE          SOURCE       STATUS");
  Serial.println("--------------------------------------------------");
  Serial.printf("Temperature  %6.1f C       %-10s   %s\n", temperature, sourceName(0), temperatureStatus);
  Serial.printf("Humidity     %6.1f %%       %-10s   %s\n", humidity, sourceName(1), humidityStatus);
  Serial.printf("Water        raw %-5d      %-10s   %s\n", waterRaw, sourceName(2), waterStatus);
  Serial.printf("Door         %s            %-10s   %s\n", doorOpen ? "OPEN  " : "CLOSED", sourceName(3), doorStatus);
  Serial.printf("MQ-2         raw %-5d      %-10s   %s\n", smokeRaw, sourceName(4), smokeStatus);
  Serial.println("--------------------------------------------------");
  Serial.print("OVERALL      : "); Serial.println(overallStatus);
  Serial.print("TRIGGERED BY : ");
  bool reasonPrinted = false;
  if (String(temperatureStatus) != "SAFE") { Serial.printf("TEMPERATURE(%s) ", temperatureStatus); reasonPrinted = true; }
  if (String(humidityStatus) != "SAFE") { Serial.printf("HUMIDITY(%s) ", humidityStatus); reasonPrinted = true; }
  if (waterLeak) { Serial.print("WATER(RED) "); reasonPrinted = true; }
  if (doorOpen) { Serial.print("DOOR(YELLOW) "); reasonPrinted = true; }
  if (String(smokeStatus) != "SAFE") { Serial.printf("MQ-2(%s) ", smokeStatus); reasonPrinted = true; }
  if (!reasonPrinted) Serial.print("NONE");
  Serial.println();
  Serial.print("BUZZER       : "); Serial.println((redActive || yellowActive) ? "BEEPING - 150 ms every 1 second" : "OFF");
  Serial.print("MQTT         : "); Serial.println(successful ? "PACKET SENT TO VTAB" : "NOT SENT / RECONNECTING");
  Serial.println("==================================================");
}

// ================================================================
// SETUP
// ================================================================

void setup() {
  Serial.begin(115200);

  pinMode(RED_LED, OUTPUT);
  pinMode(YELLOW_LED, OUTPUT);
  pinMode(GREEN_LED, OUTPUT);
  pinMode(BUZZER, OUTPUT);

  pinMode(WATER_PIN, INPUT);
  pinMode(MQ2_PIN, INPUT);

  digitalWrite(RED_LED, LOW);
  digitalWrite(YELLOW_LED, LOW);
  digitalWrite(GREEN_LED, LOW);
  digitalWrite(BUZZER, LOW);

  analogReadResolution(12);

  dht.begin();

  mqttClient.setServer(
    VTAB_MQTT_HOST,
    VTAB_MQTT_PORT
  );

  mqttClient.setCallback(
    mqttMessageReceived
  );

  mqttClient.setBufferSize(2048);

  Serial.println();
  Serial.println(
    "=============================================="
  );
  Serial.println(
    "       VTAB SENTINEL ESP32 MONITOR"
  );
  Serial.println(
    "=============================================="
  );

  connectWiFi();
}

// ================================================================
// LOOP
// ================================================================

void loop() {
  unsigned long currentTime = millis();
  updateLiveAlarm(currentTime);
  connectWiFi();

  connectMQTT();

  if (mqttClient.connected()) mqttClient.loop();

  

  if (
    currentTime - lastPublishTime >=
    PUBLISH_INTERVAL
  ) {
    lastPublishTime = currentTime;
    publishTelemetry();
  }
}






