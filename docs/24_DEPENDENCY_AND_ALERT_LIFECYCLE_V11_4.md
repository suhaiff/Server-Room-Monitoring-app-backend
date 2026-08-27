# V11.4 Dependency Recovery and Full Ticket Lifecycle

## Fixed AI Operations status

The red MinIO diagnostic after an L1/L2 test was not a stale simulated ticket. MinIO was genuinely not running because the focused upgrade command first stopped the entire stack and then restarted only selected services. The backend did not previously depend on MinIO.

The backend now declares MinIO as a Compose dependency. Use the full startup command below so every supporting service starts.

## Alerts lifecycle

The Alerts API now links each alert to its incident and returns its complete ordered database history. The Alerts page displays numbered lifecycle stages:

1. Alert raised
2. Detection/classification or ticket action
3. Root-cause analysis
4. Remediation started
5. Normalization/recovery verification
6. Closure, where applicable

The same structure supports hardware alerts, manually handled tickets and automatically remediated software/AI tickets. Each stage shows its timestamp, description and audit note.

## Upgrade and start

```powershell
docker compose down
docker compose up -d --build
```

Wait until all services are running, then check:

```powershell
docker compose ps -a
```

MinIO, backend, MQTT worker, frontend and both simulator services must show `Up`. Open `http://localhost:5173`, press `Ctrl+Shift+R`, and revisit AI Operations. If MinIO remains red, run `docker compose logs minio --tail=100` because that would be a genuine MinIO startup error rather than a simulated ticket state.