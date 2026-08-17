# VTAB Sentinel — Video Review Fixes (V5)

This release addresses the findings demonstrated in the 14 August 2026 test recording.

## Completed task list

| Area | Finding from the recording | Resolution | Verification |
|---|---|---|---|
| Test Lab | MQTT showed `WAITING` even when packets were processed | Connection state now comes from the live Paho client and is refreshed by both status endpoints | Simulator Python syntax check and simulator UI production build |
| Test Lab | Manual packets did not create a realistic live signal | Added **Start live stream**, publishing the current ESP32 variables every eight seconds with an end-to-end receipt | Simulator UI production build |
| Test Lab | Header/scenario controls felt disconnected | Added a clear stream control beside the scenario selector and stronger connected/streaming visual states | Responsive UI build |
| Overview | Graph was blank at zero readings and nearly invisible after one reading | Added a useful empty state, timestamp axis, 30 °C threshold, filled live area, and a prominent dot for short series | Dashboard production build |
| Overview | Normal readings did not create an obvious pulse | The live-stream mode continuously creates validated time-series points; the dashboard refreshes every three seconds | Frontend build and existing refresh path |
| Devices | Only the ESP32 board was visible | Added an equipment inventory for ESP32-WROOM-32, DHT22, HW-038, MC-38 and MQ-2 with latest values and timestamps | Dashboard production build |
| Telemetry | Only a raw table was available | Added current sensor cards and a live temperature/humidity chart; retained the detailed table below | Dashboard production build |
| Reports | Raw JSON did not help operators or developers | Added readable KPIs, severity chart, backend/service health, AI counts and operational findings | Dashboard production build |
| Processing proof | It was unclear whether data reached database, alerts and AI | The Test Lab continues to wait for a correlation receipt showing database status, tickets created and AI status | Existing receipt contract retained |

## Data path used by every test

`Test Lab (5174) → Simulator API (8010) → Mosquitto MQTT → MQTT worker → PostgreSQL/TimescaleDB → alert/ticket engine → AI service → Dashboard (5173)`

The Test Lab never writes directly to the database and never calls the AI service. This keeps simulation behavior representative of the future ESP32 hardware.

## Six-scenario acceptance checklist

1. Nominal operation: repeated telemetry, no new alert or ticket.
2. Cooling degradation: temperature alert, incident ticket, AI analysis and voice announcement.
3. Condensation and leak: humidity and leak findings are tied to the same event.
4. Unauthorized access: door-open alert and a door-specific voice message.
5. Fire emergency: critical smoke/temperature response and priority voice announcement.
6. Compound failure: multiple findings are grouped under one correlated sensor event.

For each scenario, confirm the Test Lab receipt first, then check Overview, Alerts, Incidents, AI Operations, Telemetry and Reports.

## Validation performed for this release

- Dashboard production build: passed.
- Independent Test Lab production build: passed.
- Python compilation for backend, simulator and AI service: passed.
- The existing backend, simulator and AI test suites remain included for execution through Docker/VS Code.

The current Codex runtime did not expose the local Docker executable or a Python installation containing pytest, so the Docker integration suite could not be launched from this workspace. Run `python start_vtab.py --fresh`, followed by the checks in `docs/07_TESTING.md`, on the target development computer before release approval.
