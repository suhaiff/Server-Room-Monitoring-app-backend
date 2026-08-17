# MQTT and simulated hardware

Topic: `devices/{device_uuid}/telemetry` using QoS 1.

```json
{
  "device_id": "00000000-0000-0000-0000-000000000101",
  "timestamp": "2026-08-12T12:00:00Z",
  "readings": {"temperature": 24.3, "humidity": 48.2, "water_leak": 0, "door_open": 0, "smoke": 0},
  "health": {"rssi": -48, "uptime_seconds": 3600, "firmware": "sim-1.0"}
}
```

The simulator generates normal Gaussian readings and occasional threshold breaches. Its variables are `MQTT_HOST`, `MQTT_PORT`, `DEVICE_ID` and `INTERVAL_SECONDS`. Replace it with Arduino firmware later while retaining the contract. Production MQTT must enable TLS, per-device credentials, ACLs and certificate rotation.

