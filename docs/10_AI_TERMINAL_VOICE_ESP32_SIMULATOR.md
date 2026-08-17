# AI Terminal, Voice Alerts and External ESP32 Simulation

## AI Operations

Open **AI Operations** in the main dashboard. It polls the AI status endpoint and displays the five-stage model pipeline, execution counts, errors, latency and correlated runtime events. Run the full diagnostic to execute every model with a controlled sample.

## Voice alerts

Voice is enabled once from the main dashboard header. Fresh alerts from the same core event are grouped into one prioritized message. Persistent abnormal readings do not repeat until a normal reading resolves the active condition and a later breach creates a new event.

## External ESP32 Test Lab

Open `http://localhost:5174` in a separate browser tab or computer. The Test Lab publishes MQTT messages through its isolated API. It cannot call `/api/v1/ai/analyze`, create alerts directly or write to PostgreSQL.

Use this order when demonstrating:

1. Publish Nominal Operation.
2. Publish Unauthorized Access and confirm the door-specific alert and voice message in the main dashboard.
3. Publish Nominal Operation to clear the condition.
4. Publish Fire Emergency and confirm critical processing.
5. Clear again, then publish Compound Failure and confirm one grouped multi-hazard announcement.

For complete details, see `15_INDEPENDENT_TEST_LAB.md`.
