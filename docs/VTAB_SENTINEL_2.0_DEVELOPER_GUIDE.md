# VTAB Sentinel 2.0 — Developer Architecture and Upgrade Guide

## Product identity

VTAB Sentinel remains the product name. Version 2.0 uses a midnight-navy operations theme with cyan intelligence, teal healthy state, blue action, amber warning and coral critical status. The product line is **Sense. Reason. Resolve.**

## What Version 2.0 adds

Version 2.0 extends the proven V14 ingestion and incident platform. It does not bypass MQTT, PostgreSQL/TimescaleDB, the alert engine, or the existing audit trail.

1. **AI Manager / Operations Copilot** reads current database evidence and answers health, incident, device and sensor questions. Every response contains evidence metadata. The built-in local provider works without an internet account.
2. **Governed remediation** records diagnosis, proposal, approval, verification and completion. L1 safe internal work may complete automatically. L2 and L3 actions wait for an authorized manager. Hardware and destructive actions must remain human-led.
3. **Predictive intelligence** calculates short-horizon trend, anomaly score and data-trust score from recent telemetry. Early samples are labelled as learning rather than presented as certainty.
4. **Digital twin foundation** exposes organization → site → room → device → component state for future floor plans, multi-site management and hardware expansion.
5. **Knowledge/runbook API** stores versioned operating procedures that future provider adapters can retrieve when explaining or planning a response.

## End-to-end data path

```text
ESP32 or Test Lab
  → Mosquitto MQTT
  → MQTT worker validation
  → PostgreSQL / TimescaleDB event + telemetry tables
  → alert / incident / AI pipeline
  → Version 2.0 evidence and prediction services
  → protected FastAPI endpoints
  → React dashboard, AI Manager, voice and audit views
```

The independent Test Lab remains at `http://localhost:5174`. It publishes through MQTT exactly like physical hardware. A registered device that has never transmitted a verified hardware packet is simulation-only. Each added component receives its own sensor ID and begins in simulation. Only a component actually reported by hardware may use the real-hardware source.

## First-time startup

1. Install and start Docker Desktop (Windows/macOS) or Docker Engine with the Compose plugin (Linux).
2. Open the extracted project folder in VS Code.
3. Copy `.env.example` to `.env`. The local demonstration values work as provided; change every password before deployment.
4. Run `python start_vtab.py` on Windows or `python3 start_vtab.py` on Linux.
5. Wait until the startup summary reports the backend healthy.
6. Open the dashboard at `http://localhost:5173`, sign in with the local seed account, and open **AI Manager** in the left navigation.
7. Open the Test Lab at `http://localhost:5174`, choose a device/component source, and send a scenario. The reading must first appear in Telemetry, then in alerts/tickets and AI evidence when it breaches a rule.

Local seed login: `admin@vtab.local` / `Admin123!`. This is demonstration-only.

## Services

| Service | Address | Purpose |
|---|---|---|
| Dashboard | http://localhost:5173 | Operator UI and AI Manager |
| Test Lab | http://localhost:5174 | Independent hardware/simulation publisher |
| Backend API | http://localhost:8000/docs | Protected application and agent APIs |
| AI model service | http://localhost:8001/docs | Baseline, anomaly, forecast, risk and explanation models |
| Grafana | http://localhost:3000 | Operational charts; local credentials come from `.env`/Compose |
| Prometheus | http://localhost:9090 | Technical service metrics |
| MinIO | http://localhost:9001 | Report/model/object storage; local credentials come from `.env` |

## Main Version 2.0 code

- `backend/app/modules/agent.py`: protected chat, intelligence, actions, knowledge and digital-twin APIs.
- `backend/app/services/operations_agent.py`: evidence retrieval, local answer engine, trend/anomaly/trust calculations and twin assembly.
- `backend/app/models.py`: original centralized event model plus agent conversation, message, action, knowledge and intelligence tables.
- `frontend/src/components/AgentCenter.jsx`: AI Manager UI with chat, prediction, governed actions and digital twin tabs.
- `frontend/src/main.jsx`: main application routing, devices, telemetry, incidents, settings and global voice behavior.
- `simulator_ui/`: independent Test Lab; do not merge it into the operations dashboard.

## External services and placeholders

No cloud LLM is required for local operation. `AGENT_PROVIDER=local` is the safe default. `LLM_API_KEY`, Teams, Jira and ServiceNow credentials are empty placeholders. Browser speech synthesis is the default voice provider; a premium cloud TTS adapter requires its own account, consent, privacy review and credentials. MinIO is the local S3-compatible implementation and can later be replaced by AWS S3 or another compatible provider. PostgreSQL/TimescaleDB can later move to Supabase PostgreSQL, but Timescale-specific hypertables require a Supabase plan/environment that supports the extension; otherwise use ordinary PostgreSQL tables and retention jobs.

## Verification checklist

Run backend tests inside the backend image: `docker compose run --rm backend pytest -q`. Run UI build: `docker compose build frontend`. Run simulator tests: `docker compose run --rm simulator-api pytest -q` if that image contains the test dependencies. Then start everything and verify login, Test Lab publish, database telemetry, alert/ticket creation, AI evidence, ticket lifecycle, L1 automatic action, L2 approval, prediction results and digital-twin component mapping.

## Production boundaries

The local evidence provider is intentionally transparent and deterministic; it is not a self-modifying autonomous model. Production remediation needs a strict allow-list, least-privilege service accounts, approval policy, idempotency keys, health verification, rollback handlers, audit retention, secret management, TLS, MQTT certificates, backups, disaster recovery, load tests and security review. Never allow a generative model to run unrestricted shell, database or infrastructure commands.
