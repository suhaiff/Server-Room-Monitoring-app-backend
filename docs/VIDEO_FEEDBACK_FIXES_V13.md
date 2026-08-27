# Video Feedback Fixes – Component Expansion and Software Fault Visibility

## Findings reproduced from the 20 August feedback video

1. A controlled L1/L2 fault could create and automatically close a ticket while AI Operations continued to show the affected dependency as healthy.
2. The Devices page only supported adding a complete ESP32 controller; it did not support adding a second individual sensor to an existing ESP32.
3. Duplicate components were not numbered or tracked independently.
4. An online ESP32 caused all of its registered components to look like physical hardware, including the disconnected door sensor.
5. The Test Lab could not safely publish two sensors of the same measurement type as distinct database records.

## Corrections

- AI Operations now overlays every active controlled software fault on the matching dependency card. The card shows `CONTROLLED TEST ACTIVE` until recovery completes.
- Supported service coverage includes database, Redis, MQTT, MinIO, backend, authentication, notifications, frontend, Prometheus, Grafana, simulator transport, and all AI pipeline stages.
- Devices now provides two separate actions: `Add ESP32 device` and `Add component to this controller`.
- Every component has a unique sensor ID and a numbered label, for example `Water Leak sensor 1` and `Water Leak sensor 2`.
- Component presence is evaluated from per-sensor source metadata. Board connectivity alone no longer marks all sensors as hardware.
- A disconnected or unreported component remains in Simulation mode. This specifically keeps the current door/reed-switch input simulated.
- The Test Lab sends one correlated packet per registered component with its sensor ID. Duplicate components therefore remain separate in telemetry storage.
- Legacy firmware that does not send a sensor ID maps a physical measurement to the first registered sensor of that type. New firmware should send `sources.<type>.sensor_id` for exact mapping.

## Acceptance test

1. Rebuild and start the project.
2. Open Dashboard → Devices.
3. On the existing ESP32, select `Add component to this controller`.
4. Add one Water Leak component. Confirm Water Leak sensor 1 and 2 are shown.
5. Open Test Lab at http://localhost:5174. Confirm the new sensor is present and starts in Simulation mode.
6. Confirm Door / reed switch remains Simulation unless its MQTT source explicitly reports `mode: hardware`.
7. Publish all component tests. Confirm each registered sensor creates an independent telemetry record.
8. Open Software / AI Lab, trigger each L1/L2 scenario, then immediately open AI Operations. Confirm the matching dependency is red and marked `CONTROLLED TEST ACTIVE`, followed by automatic recovery and green status.

## Verification completed

- Backend automated tests: 23 passed.
- Simulator API automated tests: 13 passed.
- Main React dashboard production build: passed.
- Component Test Lab React production build: passed.
