# VTAB Sentinel — One-Command Startup

This is the recommended process for developers running the complete platform.

## First run or after receiving updated code

1. Start Docker Desktop and wait until **Engine running** appears.
2. Open the `vtab-sentinel` folder in VS Code.
3. Select **Terminal → New Terminal**.
4. Run:

```powershell
python start_vtab.py
```

The launcher automatically:

1. Confirms that Docker Desktop is available.
2. Creates `.env` from `.env.example` if it is missing. Existing settings are never overwritten.
3. Builds any new or changed Docker images.
4. Starts PostgreSQL/TimescaleDB, Redis, MQTT, MinIO, AI, backend, frontend, monitoring, and the independent ESP32 Test Lab.
5. Waits for the user-facing services to respond.
6. Prints all application addresses and opens the VTAB dashboard.

Docker Compose controls the internal dependency sequence, so the developer does not need to start containers individually.

## Normal daily restart

When no source code or dependency has changed, use the faster command:

```powershell
python start_vtab.py --skip-build
```

## Application addresses

| Application | Address |
|---|---|
| VTAB dashboard | http://localhost:5173 |
| Independent ESP32 Test Lab | http://localhost:5174 |
| Test Lab API | http://localhost:8010/docs |
| Backend Swagger API | http://localhost:8000/docs |
| AI service API | http://localhost:8001/docs |
| MinIO console | http://localhost:9001 |
| Grafana | http://localhost:3000 |
| Prometheus | http://localhost:9090 |

**AI Operations** is inside the VTAB dashboard. The **Independent ESP32 Test Lab** runs separately at port 5174.

Demo dashboard login: `admin@vtab.local` / `Admin123!`

## Management commands

```powershell
python start_vtab.py --status
python start_vtab.py --logs
python start_vtab.py --stop
python start_vtab.py --fresh
```

- `--status` displays every container and checks the application addresses.
- `--logs` follows combined service logs. Press `Ctrl+C` to exit log viewing; containers remain running.
- `--stop` stops all containers while preserving PostgreSQL, MinIO, AI-model, and Grafana volumes.
- `--fresh` removes local Docker volumes before startup. Use it once when a completely empty demonstration environment is required. This permanently deletes local PostgreSQL, MinIO and Grafana data.

## Troubleshooting

If the launcher reports that Docker is unavailable, start Docker Desktop and retry.

If a service remains marked `CHECK`, inspect its logs:

```powershell
python start_vtab.py --logs
```

If the browser shows an older frontend after an update, press `Ctrl+F5` for a full refresh.

Python 3 must be installed and accessible through the `python` command. The launcher itself needs no third-party Python packages.
