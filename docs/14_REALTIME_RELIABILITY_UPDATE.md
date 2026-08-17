# VTAB Sentinel Real-Time Reliability Update

This release replaces the previous simulator race and static alert presentation with a correlated event pipeline.

## Updated execution flow

1. The independent Test Lab or a physical ESP32 publishes a telemetry payload to MQTT.
2. The backend rejects unknown devices, unknown sensor names and unsafe values.
3. Raw and clean telemetry are stored under one core event.
4. The MQTT worker commits telemetry to PostgreSQL/TimescaleDB before downstream alert and AI processing.
5. A new physical condition creates one alert and incident. Repeated abnormal readings do not create repeated voice messages. A normal reading resolves the active condition and permits a future alert.
6. The AI service analyzes the same event automatically and stores prediction, anomaly, risk and explanation rows linked to the core event.
7. Alert records are linked to the AI analysis for auditability.
8. The dashboard refreshes its live data every three seconds and announces only recent, previously unspoken event groups.

## Acceptance checks

- Door-open simulation creates a visible warning with a door-specific message and recommendation.
- Compound scenarios are spoken as one prioritized incident summary instead of competing temperature messages.
- The Overview and Alerts pages display the backend message, recommendation, room, device and relative event time.
- `GET /api/v1/devices` exists and rejects unauthenticated requests.
- Invalid sensor fields and out-of-range values return HTTP 422; unknown devices return HTTP 404.
- `GET /api/v1/ai/results` exposes persisted AI runs and their `core_event_id` and `telemetry_header_id` lineage.

## Retest sequence

1. Rebuild and start the stack with `python start_vtab.py --build`.
2. Sign in and enable Voice Intelligence once in the top bar.
3. Open the independent Test Lab at `http://localhost:5174` and transmit Nominal Operation to clear active conditions.
4. Transmit Unauthorized Access. Confirm one door alert appears and one door-specific message is spoken.
5. Transmit Nominal Operation again, then Fire Emergency. Confirm the fire alert and critical voice message.
6. Transmit Nominal Operation, then Compound Failure. Confirm the voice summarizes all current hazards once.
7. Check Overview, Alerts and AI Operations for the same newly generated event time and live run.
8. Open `/docs`, authorize, and verify `/api/v1/devices`, `/api/v1/ai/results` and invalid-payload behavior.

The browser speech feature requires the dashboard tab to remain open and the global Voice Intelligence control to be enabled. Production voice delivery should later use an approved server-side text-to-speech and notification channel when alerts must be announced without an open browser.
