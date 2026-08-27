# Video Feedback Fixes – 20 August 2026

## Feedback extracted from the recording

1. Physical DHT22 readings reach VTAB, but normal hardware readings trigger too many alerts.
2. Alert thresholds are static and must be adjustable in Settings.
3. The Test Lab must show every component with an explicit Real Hardware / Simulation source toggle and a suitable simulated control.
4. Repeated telemetry must not create repeated tickets for the same active condition.
5. When readings normalize, VTAB should verify recovery and close the associated ticket automatically.
6. AI should be visible as an operational decision layer, not only a background status display.

## Implemented fixes

- ESP32 water handling uses a calibratable raw threshold and preserves ADC evidence.
- Alert evaluation reads enabled organization rules from PostgreSQL instead of hard-coded values.
- Settings controls operator, trigger value, severity and enabled state for all five sensors.
- Active conditions are deduplicated per device and sensor.
- First safe reading resolves the alert and records `condition_normalized`. Three consecutive safe readings close the incident and record `ai_verified_recovery`. Recurrence resets recovery and records `condition_recurred`.
- Component Tester V4 displays source mode per sensor, physical readings, raw evidence, ESP32 presence and a labelled virtual fallback.

## Clean retest

1. Run `docker compose up -d --build`.
2. Use Administration → Clear all test data.
3. Set thresholds appropriate for the room under Settings.
4. Keep installed sensors on Real Hardware and the missing door contact on Simulation.
5. Raise one condition and verify exactly one ticket.
6. Return the reading to normal. The alert resolves after one safe packet.
7. After three safe packets (about nine seconds), verify the ticket closes and history includes `ai_verified_recovery`.

Automatic closure is limited to three validated safe readings. It does not operate actuators or replace fire/electrical safety procedures.
