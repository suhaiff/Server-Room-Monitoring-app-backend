# V11.3 Voice and Software Reliability Update

## Voice lifecycle

Voice announcements now distinguish detection, recovery verification and closure. When a qualified sensor or L1/L2 software condition normalizes, VTAB announces that it is verifying recovery and will close the eligible ticket automatically. After verification, it announces that recovery is confirmed and the related ticket is closed. Hardware and L3 faults explicitly remain human-controlled.

The dashboard selects the best installed English voice in this order: Natural/Neural, Microsoft Aria or Jenny, Samantha, Google UK English Female, then the first available English voice. Actual voice quality depends on voices installed in Windows/browser. Cloud neural TTS is not bundled because it requires an external provider and credentials.

## Software Reliability Lab

Open `http://localhost:5174`, then select **Software / AI Lab**. Each button publishes a controlled failure through MQTT and creates genuine database evidence, an alert, an incident and AI Operations status.

- L1: localized, low-risk recovery. VTAB runs an approved repair runbook, verifies health and closes the ticket automatically.
- L2: internal service/model interruption. VTAB runs a bounded repair runbook, validates dependent stages and closes after verification.
- L3: data-integrity or high-impact failure. VTAB records evidence and requires human approval; automatic closure is prohibited.

Available tests cover PostgreSQL/TimescaleDB, Redis, MQTT, MinIO, FastAPI, authentication, notifications, React dashboard connectivity, Prometheus, Grafana, simulator transport, and all five AI pipeline stages.

## Safety boundary

The laboratory does not corrupt code, stop real containers or delete data. "Repair" means selecting and validating a predefined reversible runbook. Production deployment should connect these runbooks to an approved orchestration platform with least-privilege credentials, change approval, rollback, timeouts and complete audit logging.

## Upgrade

```powershell
docker compose down
docker compose up -d --build backend mqtt-worker software-lab simulator-ui frontend
```

Hard-refresh both browser tabs with `Ctrl+Shift+R` after the rebuild.