# Dynamic Telemetry Views Fix – Video 11:36

## Feedback and root causes

- Temperature/humidity chart reference lines remained at 30°C/70% because those values were hard-coded in React.
- Device sensor cards used the same hard-coded comparisons.
- Water and MQ-2 were displayed only as normalized alert values (0/1), although the ESP32 raw ADC evidence was preserved in raw event JSON.
- Door contact shared a generic binary chart instead of a clear access-specific view.

## Fixes

- Overview, Devices and Telemetry now consume the persisted PostgreSQL threshold rules.
- Changing and saving a threshold updates chart lines, labels, card status and alert evaluation from the same rule source.
- `/telemetry/latest` now joins clean telemetry to the matching raw event record and returns `raw_adc`, pin, source mode/provider and sensor error.
- Water and MQ-2 have a dedicated 0–4095 ADC trend chart.
- Door has a dedicated CLOSED/OPEN step chart.
- Sensor cards and the telemetry table display hardware/simulation source and ADC evidence.

## Verification

- Frontend production build passed.
- 17 backend end-to-end tests passed, including a new raw-ADC lineage regression test.
