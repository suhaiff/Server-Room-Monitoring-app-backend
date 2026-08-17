"""Send one deterministic payload without MQTT; useful for API debugging."""
import json, urllib.request
payload={"device_id":"00000000-0000-0000-0000-000000000101","readings":{"temperature":34.5,"humidity":53.1,"water_leak":0,"door_open":0,"smoke":0}}
request=urllib.request.Request("http://localhost:8000/api/v1/telemetry/ingest",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"},method="POST")
print(urllib.request.urlopen(request).read().decode())

