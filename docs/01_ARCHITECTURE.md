# Architecture and PDF traceability

This implementation follows the supplied eight-page VTAB Sentinel planner.

## End-to-end flow

1. **Data collection:** simulated Arduino UNO R4 WiFi reads BME280 temperature/humidity, leak, magnetic door and optional smoke sensors.
2. **Edge processing:** the simulator formats a timestamped payload; physical firmware will add local threshold checks and offline buffering.
3. **Transmission:** MQTT topic `devices/{device_uuid}/telemetry`, QoS 1. HTTPS ingestion is also exposed.
4. **Ingestion:** the worker validates device identity and preserves the raw payload.
5. **Processing:** readings are normalized, range checked and stored as clean telemetry.
6. **AI analysis:** the separate service provides baseline, anomaly, forecast, risk and explanation outputs.
7. **Alerts/actions:** deterministic rules create alerts and incidents; adapters dispatch to configured channels.
8. **Visibility:** the React dashboard provides live operational and historical views.

The backend is a domain-based modular monolith, as directed by the detailed backend diagram, with boundaries that can later be extracted into microservices. PostgreSQL owns transactional/master data, TimescaleDB optimizes telemetry, Redis supports caching/queues, and MinIO/S3 stores reports, attachments, exports and backups.

## Phase mapping

| PDF phase | Implemented areas |
|---|---|
| 1 Foundation & Core | Auth/RBAC, tenant/master data, devices/sensors, MQTT/HTTP ingestion, raw/clean telemetry, device state, metrics |
| 2 Application & AI | Threshold alerts, incident workflow, notification records/adapters, dashboard, AI pipeline and real-time polling |
| 3 Integrations & Production | Teams/Jira/ServiceNow/webhook adapters, reports, configuration surface, users, audit, MinIO, monitoring |
| 4 Integration & Go-Live | Unit/integration tests, Docker deployment, VS Code tasks, Prometheus/Grafana and security checklist |

