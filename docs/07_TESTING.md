# Testing

Run backend tests with `docker compose run --rm backend pytest -q`. Run AI tests with `docker compose run --rm ai-service pytest -q`.

Included tests cover health, login, authorization, ingestion/storage, reports, anomaly detection, risk and forecasting. Before go-live add browser E2E tests, retained-message/reconnect MQTT tests, tenant-isolation tests, target load tests, dependency/container scanning, SAST/DAST and an external penetration test.

