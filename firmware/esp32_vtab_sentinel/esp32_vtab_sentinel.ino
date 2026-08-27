#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include "secrets.h"

#define DHT_PIN 4
#define DHT_TYPE DHT22
#define WATER_PIN 34       // Connect the water module AO pin here (not DO).
#define MQ2_PIN 35         // Protect ADC input: it must never exceed 3.3 V.
#define RED_LED 32
#define YELLOW_LED 33
#define GREEN_LED 25
#define BUZZER 26

const char* DEVICE_ID="00000000-0000-0000-0000-000000000101";
const unsigned long PUBLISH_MS=3000;
const int WATER_THRESHOLD=1200; // Calibrate using dry/wet Serial raw values.
const int SMOKE_THRESHOLD=1500; // Calibrate after MQ-2 warm-up.
DHT dht(DHT_PIN,DHT_TYPE); WiFiClient wifi; PubSubClient mqtt(wifi);
unsigned long lastPublish=0;
struct Source { bool simulated; float value; };
Source sourceCfg[5]={{false,24},{false,48},{false,0},{true,0},{false,0}};
const char* names[5]={"temperature","humidity","water_leak","door_open","smoke"};

void setIndicators(float t,float h,bool leak,bool doorOpen,bool smoke){
 bool critical=smoke||leak||t>30; bool warning=doorOpen||h>70;
 digitalWrite(RED_LED,critical); digitalWrite(YELLOW_LED,!critical&&warning); digitalWrite(GREEN_LED,!critical&&!warning); digitalWrite(BUZZER,critical);
}
void configMessage(char*,byte* bytes,unsigned int length){
 JsonDocument doc; if(deserializeJson(doc,bytes,length)) return;
 for(int i=0;i<5;i++){ JsonObject c=doc["components"][names[i]]; if(c.isNull()) continue; sourceCfg[i].simulated=String((const char*)c["mode"])=="simulated"; if(!c["simulated_value"].isNull()) sourceCfg[i].value=c["simulated_value"].as<float>(); }
}
void connectWifi(){ WiFi.mode(WIFI_STA); WiFi.begin(VTAB_WIFI_SSID,VTAB_WIFI_PASSWORD); while(WiFi.status()!=WL_CONNECTED){delay(500);Serial.print('.');} Serial.println(" Wi-Fi connected"); }
void connectMqtt(){
 while(!mqtt.connected()){ String id="vtab-esp32-"+String((uint32_t)ESP.getEfuseMac(),HEX); if(mqtt.connect(id.c_str())){ String topic="devices/"+String(DEVICE_ID)+"/config/sources"; mqtt.subscribe(topic.c_str(),1); } else delay(2000); }
}
float chosen(int i,float hardware){ return sourceCfg[i].simulated?sourceCfg[i].value:hardware; }
void publishTelemetry(){
 float t=dht.readTemperature(),h=dht.readHumidity(); int waterRaw=analogRead(WATER_PIN),smokeRaw=analogRead(MQ2_PIN);
 if(isnan(t)) t=sourceCfg[0].value; if(isnan(h)) h=sourceCfg[1].value;
 float values[5]={chosen(0,t),chosen(1,h),chosen(2,waterRaw>=WATER_THRESHOLD),chosen(3,0),chosen(4,smokeRaw>=SMOKE_THRESHOLD)};
 JsonDocument doc; doc["device_id"]=DEVICE_ID; doc["timestamp_ms"]=millis();
 JsonObject readings=doc["readings"].to<JsonObject>(); JsonObject sources=doc["sources"].to<JsonObject>();
 for(int i=0;i<5;i++){readings[names[i]]=values[i];JsonObject s=sources[names[i]].to<JsonObject>();s["mode"]=sourceCfg[i].simulated?"simulated":"hardware";s["provider"]=sourceCfg[i].simulated?"component-tester":"esp32";s["hardware_available"]=(i!=3);}
 sources["temperature"]["pin"]=DHT_PIN;sources["humidity"]["pin"]=DHT_PIN;sources["water_leak"]["pin"]=WATER_PIN;sources["water_leak"]["raw"]=waterRaw;sources["door_open"]["pin"]=nullptr;sources["smoke"]["pin"]=MQ2_PIN;sources["smoke"]["raw"]=smokeRaw;
 JsonObject health=doc["health"].to<JsonObject>();health["rssi"]=WiFi.RSSI();health["uptime_seconds"]=millis()/1000;health["firmware"]="vtab-esp32-4.0";health["board"]="ESP32-WROOM-32";health["source"]="esp32-hardware";
 String payload;serializeJson(doc,payload);String topic="devices/"+String(DEVICE_ID)+"/telemetry";mqtt.publish(topic.c_str(),payload.c_str(),false);Serial.println(payload);
 setIndicators(values[0],values[1],values[2],values[3],values[4]);
}
void setup(){Serial.begin(115200);pinMode(RED_LED,OUTPUT);pinMode(YELLOW_LED,OUTPUT);pinMode(GREEN_LED,OUTPUT);pinMode(BUZZER,OUTPUT);analogReadResolution(12);dht.begin();connectWifi();mqtt.setServer(VTAB_MQTT_HOST,VTAB_MQTT_PORT);mqtt.setCallback(configMessage);mqtt.setBufferSize(2048);}
void loop(){if(WiFi.status()!=WL_CONNECTED)connectWifi();if(!mqtt.connected())connectMqtt();mqtt.loop();if(millis()-lastPublish>=PUBLISH_MS){lastPublish=millis();publishTelemetry();}}
