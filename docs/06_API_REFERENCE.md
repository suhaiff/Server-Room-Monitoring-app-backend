# API reference

Interactive documentation is available at `http://localhost:8000/docs` and `http://localhost:8001/docs`.

Important routes include authentication, `/master/{organizations|sites|rooms|devices|sensors}`, `/users`, `/telemetry/ingest`, `/telemetry/latest`, `/ai/analyze`, `/alerts`, `/incidents`, `/integrations/dispatch`, `/reports/summary` and `/audit` under `/api/v1`.

The MQTT and HTTPS ingestion paths share the same validation/storage functions. In production, add API-gateway rate limits, IP filtering/WAF, OAuth2/OIDC and device certificate authentication.
