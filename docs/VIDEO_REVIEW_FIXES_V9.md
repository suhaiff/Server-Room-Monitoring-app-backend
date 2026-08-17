# Fifth Recorded Review: Findings, Root Causes and V9 Corrections

## Accepted areas

- Hardware/ESP32 simulator behavior and animation
- Incident history and date controls
- Normal five-model AI diagnostic execution

## Findings and corrections

| Finding | Root cause | V9 correction |
|---|---|---|
| Empty ticket message remained in the left half | The empty state was still a child of the normal two-column ticket grid | Empty ticket content now spans the complete section and is centered; real ticket cards remain compact |
| AI test did not identify a model | The software console exposed one generic `ai` scenario | It now exposes baseline, anomaly, forecast, risk and explanation as separate named model tests |
| AI Operations stayed healthy during simulated AI failure | Diagnostics checked only whether the AI HTTP container answered | Active persisted `software_ai_*` alerts now overlay the matching model node, degrade AI status and create a structured error-stream entry |
| No system-log download | Audit data existed across separate database tables without one export endpoint | Settings now downloads one dated CSV combining core events, alerts, incidents, workflow actions and AI analyses |
| Hardware and software tests used separate hosts | Each simulator had an externally exposed web address | Port 5174 is now one Unified System Simulator with Hardware and Software tabs; the software lab remains an internal service |

## AI fault acceptance flow

1. Open `http://localhost:5174` and select **Software / AI Lab**.
2. Trigger **AI anomaly detector** failure.
3. Confirm the receipt contains the exact model-specific alert and ticket identifiers.
4. Open the main dashboard at `http://localhost:5173` and select **AI Operations**.
5. Confirm overall AI status is degraded, the Anomaly Detection node is red, and the event stream names the anomaly model and recommendation.
6. Return to the simulator and select **Simulate recovery**.
7. Confirm the model returns healthy while the operator ticket remains pending verification.
8. Close the ticket and confirm the main system returns healthy.

## CSV export

Open **Settings → System log export → Download current CSV**. The filename
contains the UTC date and the CSV columns are timestamp, category, source,
severity, status, record ID, core-event ID, name, message and details.
Scheduled exports remain intentionally deferred as requested in the recording.
