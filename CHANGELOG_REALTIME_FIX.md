# VTAB Sentinel - Real-Time Reliability Fix

## Corrected

- Door-open readings now create a specific alert message and recommended security action.
- Alert evaluation is synchronous for simulator requests, removing the dashboard refresh race.
- Alert lifecycle suppresses repeated announcements while a condition remains active and resolves when readings return to normal.
- Voice announcements group all alerts from one event, prioritize critical hazards and use the backend-generated messages instead of repeating a temperature phrase.
- Overview and Alerts use a live three-second refresh, detailed alert cards and relative timestamps.
- AI risk and explanation logic includes door-open events.
- Simulator and MQTT hardware ingestion automatically attempt the complete AI pipeline.
- Persisted AI outputs and alerts are linked to the same core event and telemetry header.
- Added protected `GET /api/v1/devices` and persisted `GET /api/v1/ai/results` endpoints.
- Added strict validation for unknown sensor fields, invalid boolean values, unsafe numeric ranges and unknown devices.

## Verification

- Backend: 8 tests passed.
- AI service: 5 tests passed.
- Frontend: production build completed successfully.

See `docs/14_REALTIME_RELIABILITY_UPDATE.md` for the recommended retest sequence.

## Independent Test Lab architecture

- Removed Test Lab from the operational React dashboard.
- Removed the direct dashboard `/telemetry/simulate` endpoint.
- Added a standalone Test Lab UI on port 5174 and a simulator gateway on port 8010.
- The gateway publishes ESP32-compatible payloads only to MQTT.
- Database persistence, alert evaluation and AI analysis now occur behind the MQTT worker, matching the future Wi-Fi hardware path.

## Operator workflow and engineering diagnostics

- Fixed the Test Lab MQTT badge by connecting the publisher API during startup.
- Added correlation receipts from the MQTT worker back to the Test Lab, proving database commit, ticket count and AI completion for each transmitted scenario.
- Added close-ticket controls to Overview and Incidents. Closing a ticket also closes its alert.
- Added a full-dashboard healthy/alert visual state driven by open database records.
- Added an administrator test-data reset that preserves users, devices and configuration.
- Added `python start_vtab.py --fresh` for a completely clean local Docker environment.
- Expanded AI Operations with PostgreSQL, Redis, MQTT, AI-service and MinIO diagnostics, latency/error details and persisted AI-linkage evidence.
- Added automated coverage for all six Test Lab scenarios.
