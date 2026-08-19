
# 🛡️ VTAB Sentinel — Backend

<p align="center">
  <strong>IoT Telemetry, MQTT Ingestion & AI Operations Platform</strong>
</p>

<p align="center">
  A production-ready backend for receiving IoT telemetry,
  processing device events, storing sensor data, generating alerts,
  and integrating AI-powered analysis.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white" />
  <img src="https://img.shields.io/badge/TimescaleDB-Enabled-FDB515" />
  <img src="https://img.shields.io/badge/MQTT-Mosquitto-3C5280" />
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white" />
</p>

---

## 📌 Overview

VTAB Sentinel Backend is the core processing layer of the VTAB Sentinel
IoT monitoring platform.

It provides:

- REST APIs
- Device management
- Telemetry ingestion
- MQTT processing
- Device health tracking
- Event management
- Alert processing
- AI integration
- Authentication
- Database persistence
- Operational monitoring

The backend is designed around an event-driven telemetry pipeline.

---

# 🏗️ System Architecture


                         IoT Device
                             │
                             │ MQTT
                             ▼
                    ┌─────────────────┐
                    │    Mosquitto    │
                    │   MQTT Broker   │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   MQTT Worker   │
                    └────────┬────────┘
                             │
               ┌─────────────┼─────────────┐
               │             │             │
               ▼             ▼             ▼
          PostgreSQL        Alerts          AI
          /TimescaleDB                    Service
               │                           │
               └─────────────┬─────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   FastAPI API   │
                    └────────┬────────┘
                             │
                             ▼
                       Web Frontend

Developer-ready reference implementation of the four-phase **VTAB Sentinel AI Server Room Monitoring System** described in the supplied architecture PDF.

## What is included

- FastAPI modular-monolith API with JWT/RBAC, tenant-aware master data, telemetry, alerts, incidents, notifications, integrations, reporting, configuration, admin and audit.
- PostgreSQL/Supabase-compatible schema containing the PDF's 37 logical tables, plus a TimescaleDB hypertable upgrade.
- MQTT ingestion plus an independent ESP32 Test Lab for temperature, humidity, leak, door, smoke and device health.
- Separate FastAPI AI service implementing baseline statistics, anomaly detection, linear trend forecasting, risk scoring and explanations.
- React/Vite dashboard for overview, devices, telemetry, alerts, incidents, reports and administration.
- Immersive AI Operations Command Center with five-stage pipeline health, correlated inference runs, structured model evidence, latency, diagnostics and errors.
- Persistent system-wide Voice Intelligence with professional alert/decision phrasing and a single global enable/mute control.
- Dedicated Test Lab on its own server. It publishes ESP32 messages to MQTT and has no direct access to dashboard, database or AI APIs.
- Redis cache/queue, Mosquitto, MinIO/S3 abstraction, PostgreSQL/TimescaleDB, Prometheus and Grafana.
- Docker Compose one-command startup, sample data, tests, VS Code tasks and phase-aligned documentation.

The fixes extracted from the latest recorded acceptance test are listed in [docs/VIDEO_REVIEW_FIXES_V5.md](docs/VIDEO_REVIEW_FIXES_V5.md).

The second recorded UI review, root causes and V6 corrections are documented in [docs/VIDEO_REVIEW_FIXES_V6.md](docs/VIDEO_REVIEW_FIXES_V6.md).

Ticket history, configurable voice reminders, application settings and the pipeline redesign from the third review are documented in [docs/VIDEO_REVIEW_FIXES_V7.md](docs/VIDEO_REVIEW_FIXES_V7.md).

State-aware recovery voice, incident date controls and the independent software reliability console from the fourth review are documented in [docs/VIDEO_REVIEW_FIXES_V8.md](docs/VIDEO_REVIEW_FIXES_V8.md).

Named AI fault observability, unified simulator hosting, centered empty tickets and CSV log export from the fifth review are documented in [docs/VIDEO_REVIEW_FIXES_V9.md](docs/VIDEO_REVIEW_FIXES_V9.md).

Linear AI dependency propagation and modern internal scrollbars from the sixth review are documented in [docs/VIDEO_REVIEW_FIXES_V10.md](docs/VIDEO_REVIEW_FIXES_V10.md).

## Fastest local start (recommended)

1. Install Docker Desktop and VS Code.
2. Start Docker Desktop and wait until its engine is running.
3. From the repository root run the complete Python launcher:

```powershell
python start_vtab.py
```

The launcher creates `.env` from `.env.example` when needed, builds changed
images, starts every service including the independent ESP32 Test Lab, waits
for readiness, prints all addresses, and opens the dashboard automatically.

Useful launcher commands:

```powershell
python start_vtab.py --status       # Show containers and application addresses
python start_vtab.py --logs         # Follow logs; press Ctrl+C to leave
python start_vtab.py --stop         # Stop services but preserve stored data
python start_vtab.py --skip-build   # Faster restart when code has not changed
python start_vtab.py --no-browser   # Start without opening a browser
python start_vtab.py --fresh        # One-time clean start; deletes local stored test data
```

4. The launcher displays:

| Service | URL |
|---|---|
| Dashboard | http://localhost:5173 |
| Independent ESP32 Test Lab | http://localhost:5174 |
| Test Lab API | http://localhost:8010/docs |
| Backend API / Swagger | http://localhost:8000/docs |
| AI API / Swagger | http://localhost:8001/docs |
| MinIO console | http://localhost:9001 |
| Grafana | http://localhost:3000 |
| Prometheus | http://localhost:9090 |

Demo login: `admin@vtab.local` / `Admin123!`.

The **Independent ESP32 Test Lab** runs at `http://localhost:5174`. Its API publishes only to MQTT. For unattended random telemetry, the optional background publisher can be started separately:

```powershell
docker compose --profile background-simulator up simulator-background
```

The **Unified System Simulator** runs at `http://localhost:5174`. Use its
**Hardware / ESP32 Lab** and **Software / AI Lab** tabs to switch between both
test types without opening another host. Software tests safely simulate backend,
database, MQTT, Redis, MinIO and named AI-model interruptions. They travel
through MQTT and create real database alerts and tickets without stopping
containers or damaging data.

See `docs/02_LOCAL_SETUP.md` for non-Docker and VS Code instructions.

## Phase map

- **Phase 1 - Foundation & Core Platform:** `backend/app/modules/master_data.py`, `telemetry.py`, `mqtt/`, database schema and authentication.
- **Phase 2 - Application & AI Foundation:** alerts, incidents, notifications, React dashboard and `ai_service/`.
- **Phase 3 - Integrations & Production Features:** integrations, reporting, configuration, user/admin, audit, backups and monitoring.
- **Phase 4 - Integration, Testing & Go-Live:** tests, CI, Docker, Prometheus/Grafana, security defaults and deployment guidance.

## Configuration placeholders

Local simulation works without cloud accounts. Production requires real values for Supabase/PostgreSQL, S3/MinIO, SMTP/SendGrid, Teams webhook, Jira, ServiceNow, optional OpenAI/Azure OpenAI explanations, TLS certificates and production JWT secrets. See `.env.example` and `docs/09_PLACEHOLDERS.md`.
