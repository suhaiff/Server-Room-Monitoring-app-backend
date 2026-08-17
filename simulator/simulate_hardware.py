"""ESP32/BME280/leak/door/smoke background simulator."""
import json, os, random, time
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

host=os.getenv("MQTT_HOST","localhost"); port=int(os.getenv("MQTT_PORT","1883")); device=os.getenv("DEVICE_ID","00000000-0000-0000-0000-000000000101"); interval=float(os.getenv("INTERVAL_SECONDS","3"))
client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"sim-{device[-6:]}")
while True:
    try:
        client.connect(host,port)
        break
    except OSError:
        time.sleep(2)
client.loop_start()
while True:
    incident=random.random()<0.08
    readings={"temperature":round(random.gauss(24 if not incident else 34,1.3),2),"humidity":round(random.gauss(48,5),2),"water_leak":int(incident and random.random()<0.2),"door_open":int(random.random()<0.05),"smoke":int(incident and random.random()<0.03)}
    message={"device_id":device,"timestamp":datetime.now(timezone.utc).isoformat(),"readings":readings,"health":{"rssi":random.randint(-70,-35),"uptime_seconds":int(time.monotonic()),"firmware":"esp32-sim-2.0","board":"ESP32"}}
    client.publish(f"devices/{device}/telemetry",json.dumps(message),qos=1)
    print(json.dumps(message),flush=True)
    time.sleep(interval)
