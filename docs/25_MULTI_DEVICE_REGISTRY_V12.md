# V12 Multi-device Registry and AI Backlog Diagnostics

## AI Operations metric correction

The previous **Telemetry missing AI** value counted every historical telemetry event whose event flag was not linked, so old test records stayed red even while all five models were healthy. It did not represent seven currently failing AI jobs.

V12 replaces it with **AI processing backlog**:

- Uses the actual `core_event -> ai_analysis_header` relationship.
- Applies a 15-second processing grace period.
- Counts only unlinked telemetry within the latest five-minute operating window.
- Keeps older unlinked records as `historical_unlinked_telemetry` in the diagnostics API for audit, without presenting them as a current failure.

## Multi-device design

Each registered device now has:

- A unique UUID used in `devices/{device_id}/telemetry`.
- A board profile and firmware version.
- Its own selected component list.
- Independent last-seen and hardware-presence state.
- Independent hardware/simulation source configuration.
- A complete telemetry, alert, AI and incident trail using its device ID.

The MQTT gateway listens to wildcard device topics, so additional registered controllers do not require another worker.

## Add and test a device

1. Open `http://localhost:5173` and select **Devices**.
2. Choose **Add ESP32 device**.
3. Enter a name, select the ESP32 board and select only the sensors physically assigned to it.
4. Register the device.
5. Copy its displayed **Firmware DEVICE_ID** UUID when preparing that ESP32 firmware.
6. Open `http://localhost:5174`.
7. The new device appears automatically in **Registered device fleet** within approximately four seconds.
8. Because it has not sent a recent physical packet, all of its registered components start in **Simulation fallback**.
9. Publish a simulation packet and verify that Dashboard Devices, Telemetry, Alerts and AI results carry the new device UUID.
10. When an ESP32 publishes a physical packet using that UUID, the Test Lab changes that device to **Hardware online** and uses hardware by default. A component may still be changed to simulation independently.
11. If physical packets stop for 20 seconds, that device returns to simulation fallback without affecting other devices.

## Current supported component types

- DHT22 temperature
- DHT22 humidity
- Water/leak input
- Door/reed input
- MQ-2 smoke input

## Local registry security

The Test Lab reads a local, read-only registry endpoint on the private Compose network. For production, protect this endpoint with a service identity or API gateway policy and do not expose it publicly.

## Upgrade

```powershell
docker compose down
docker compose up -d --build
```

Then hard-refresh `http://localhost:5173` and `http://localhost:5174` with `Ctrl+Shift+R`.