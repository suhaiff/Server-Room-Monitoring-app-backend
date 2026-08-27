# ESP32 Hardware Integration and Component Tester

## What changed

VTAB now supports one traceable hybrid packet. The ESP32 reads installed components, substitutes only components configured as **Simulation**, and publishes the combined packet to MQTT. The normal MQTT worker then stores it in PostgreSQL/TimescaleDB and runs alerts and AI. The component tester never writes directly to the database.

```
ESP32 sensors + simulated missing component -> Mosquitto :1883 -> MQTT worker
-> PostgreSQL/TimescaleDB -> alerts/incidents -> AI -> dashboard
```

Each reading includes provenance under `sources`, so developers can distinguish hardware and simulated evidence in raw data.

## Critical wiring checks

- DHT22 DATA -> GPIO4, powered at 3.3 V.
- Water module **AO -> GPIO34**. The supplied diagram labels DO, but the firmware uses `analogRead(34)`; AO is required for that code.
- MQ-2 AO -> GPIO35 only through an electrically safe output. The ESP32 ADC must never receive more than 3.3 V. Many MQ-2 boards use a 5 V heater/output; check the exact module and use a divider/level protection where required.
- GPIO34 and GPIO35 are input-only ADC1 pins and work while Wi-Fi is active.
- LEDs: red 32, yellow 33, green 25, each through 220 ohm. Active buzzer: 26.
- All grounds must be common.
- Do not use a regulator arrangement unless its input/output specifications and current rating are verified. USB powering the ESP32 is safest for initial software testing.

## Arduino IDE setup

1. Install the ESP32 board package and select **DOIT ESP32 DEVKIT V1** (or the matching ESP32-WROOM-32 profile).
2. Install libraries: `DHT sensor library`, `Adafruit Unified Sensor`, `PubSubClient`, and `ArduinoJson` version 7.
3. Open `firmware/esp32_vtab_sentinel/esp32_vtab_sentinel.ino`.
4. Copy `secrets.example.h` to `secrets.h` in the same folder.
5. Set Wi-Fi name/password. Set `VTAB_MQTT_HOST` to the Windows/Linux computer's LAN IPv4 address. **Do not use localhost**; on the ESP32, localhost means the ESP32 itself.
6. Start VTAB with `python start_vtab.py`, then allow inbound TCP port 1883 in the computer firewall for the private network.
7. Upload the sketch and open Serial Monitor at 115200 baud.
8. Open Component Tester: http://localhost:5174. Within about 15 seconds the banner should show **ESP32 hardware online**.

Find the host IP:

- Windows PowerShell: `ipconfig` (use the active Wi-Fi IPv4 address).
- Linux: `hostname -I` (use the LAN address, not 127.0.0.1).

The ESP32 and computer must be on the same reachable network. Guest Wi-Fi may block device-to-device traffic.

## Using hybrid mode

In the Component Tester, choose **Real hardware** or **Simulation** on every component card. Door/reed switch defaults to Simulation because it is not currently installed. Set its value, click **Apply source settings to ESP32**, and the retained configuration is delivered on:

`devices/00000000-0000-0000-0000-000000000101/config/sources`

The ESP32 applies the choice and publishes every three seconds on:

`devices/00000000-0000-0000-0000-000000000101/telemetry`

Use **Publish fully virtual fallback packet** only when the board is disconnected. These packets are explicitly labelled `component-tester-virtual` and all values are stored as simulated.

## Calibration

`WATER_THRESHOLD` and `SMOKE_THRESHOLD` in the sketch are starting points, not production calibration. Observe dry/wet and clean-air/test readings in Serial Monitor, then set thresholds with adequate noise margin. MQ-2 sensors require warm-up and are not certified life-safety fire detectors. VTAB server thresholds remain the authoritative alert rules.

## Troubleshooting

- Hardware offline but MQTT connected: verify PC LAN IP in `secrets.h`, same network, firewall port 1883, and Serial output.
- MQTT offline in UI: run `docker compose ps` and inspect `mosquitto` plus `simulator-api`.
- Packets in Serial but not dashboard: inspect `docker compose logs mqtt-worker --tail=100` and ensure the seeded device ID was not changed.
- DHT is `nan`: check GPIO4, power/ground, selected DHT22 type, and the data pull-up on bare sensors.
- Old virtual data appearing: keep the optional `background-simulator` profile disabled and use the existing data-wipe tool before a clean test.

## Production work still required

Development MQTT currently permits an unauthenticated LAN connection. Before deployment, configure MQTT users, TLS certificates, per-device topic ACLs, unique device credentials, secure provisioning, firmware signing/OTA policy, calibrated thresholds, sensor failure flags, and network segmentation.
