# AI Operations and Independent Test Lab

## Operational separation

- **AI Operations** remains inside the authenticated VTAB dashboard and shows model health, run counts, latency and structured execution logs.
- **Independent Test Lab** runs at `http://localhost:5174`. It is a separate application with no dashboard token, database connection or AI-service access.
- **Voice Intelligence** remains a global dashboard preference and announces only newly created database-backed alerts.

## Real processing path

Publishing a Test Lab scenario performs:

1. Test Lab UI sends the selected ESP32 values to the isolated publisher API on port 8010.
2. The publisher creates a hardware-shaped message on `devices/{device_id}/telemetry`.
3. Mosquitto transports the message to the MQTT worker.
4. The worker validates the device and readings and commits raw and clean telemetry to PostgreSQL/TimescaleDB.
5. Alert and incident evaluation runs after the database commit.
6. The AI service executes baseline, anomaly, forecast, risk and explanation models and persists results linked to the same core event.
7. The main dashboard discovers the new records through its protected APIs and announces a grouped event message when voice is enabled.

See `15_INDEPENDENT_TEST_LAB.md` for the demonstration and hardware-replacement procedure.

## Production boundaries

The prototype AI recommends precautions but does not directly operate HVAC, electrical isolation, locks or fire systems. Physical control requires approved BMS/PLC integrations, safety interlocks, authorization and audit trails.

Browser speech remains a supplementary attention channel. Use an approved server-side speech or PA integration when announcements must work without an open dashboard.
