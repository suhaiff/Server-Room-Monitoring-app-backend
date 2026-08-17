# Fourth Recorded Review: Findings, Root Causes and V8 Corrections

## Confirmed feedback

1. The ESP32 Test Lab animation is accepted and remains unchanged.
2. Only the empty-ticket message should be centered. A single real ticket must remain a compact card rather than stretch across the page.
3. Voice must understand lifecycle state: active danger, normalized condition awaiting technician verification, and fully healthy after ticket closure.
4. Incidents need date-range filtering and newest/oldest sorting.
5. Developers need an independent software test console to test service and AI failures through the real application data path.

## Root causes and fixes

| Finding | Root cause | Correction |
|---|---|---|
| One ticket stretched full width | The single-card grid explicitly changed to one column | Restored the normal two-column compact ticket grid; mobile remains one column |
| Voice repeated an obsolete danger after recovery | Sensor recovery and human ticket closure were treated as one state | Alerts now resolve when readings normalize, while incidents remain open for verification; summary exposes alert, pending and healthy states |
| No recovery or closure announcement | Voice only watched newly created alerts | Voice now detects alert recovery, pending ticket verification and final ticket closure transitions |
| Incident history difficult to review | Incidents were always returned in one fixed visual order | Added Today, 3 months, 6 months, 1 year and All History filters plus newest/oldest sorting |
| No safe software-failure testing | Existing lab represented ESP32 hardware telemetry only | Added a separate console at port 8011 that publishes controlled platform-fault events through MQTT |

## Software reliability test flow

`Software Console -> MQTT platform/faults -> MQTT Worker -> PostgreSQL event/alert/ticket -> Dashboard/API/Voice`

Available controlled scenarios: PostgreSQL/TimescaleDB, Redis, Mosquitto MQTT,
AI anomaly models, MinIO and FastAPI backend. The console does not stop real
containers. It injects auditable test evidence so demos and developer tests are
repeatable. Recovery resolves the active alert but requires an operator to
verify and close the ticket.

## Acceptance procedure

1. Start with `python start_vtab.py --fresh` when old test data may interfere.
2. Sign in at `http://localhost:5173` and enable Voice Intelligence.
3. Open `http://localhost:8011`, select one service and choose **Simulate failure**.
4. Confirm its receipt contains `fault_recorded`, an alert ID and incident ID.
5. Confirm the dashboard becomes red, shows one dynamic ticket, and announces the correct fault.
6. Choose **Simulate recovery**. Confirm the dashboard becomes amber/pending and voice requests technician verification.
7. Close the ticket in the dashboard. Confirm the dashboard becomes green and voice announces healthy operation.
